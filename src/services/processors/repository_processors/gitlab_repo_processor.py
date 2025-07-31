import os
import logging
from typing import List
from collections import Counter
from src.services.clients.hrdb_clients.hrdb_client import HRDBClient

logger = logging.getLogger(__name__)


class GitLabRepoProcessor:
    """
    Handles GitLab repository owner detection and enrichment.
    Extracted from Product class to follow service layer pattern.
    """
    
    def __init__(self, product_name: str):
        """
        Initialize GitLab repository processor.
        
        Args:
            product_name: Name of the product
        """
        self.product_name = product_name
        self.gitlab_client = None
        self.hrdb_client = HRDBClient()
        
    def initialize_client(self):
        """Initialize GitLab client with product-specific configuration."""
        try:
            from src.services.clients.scm_clients.gitlab_client import GitLabClient
            from CONSTANTS import PRODUCT_SCM_TOKEN_ENV
            
            token_env = PRODUCT_SCM_TOKEN_ENV.get(self.product_name, None)
            token = os.getenv(token_env, '') if token_env else ''
            
            if not token:
                logger.warning("No SCM token found for product '%s', skipping SCM owner detection.", self.product_name)
                return False
            else:
                self.gitlab_client = GitLabClient(token)
                return True
        except ImportError as e:
            logger.error("Failed to import GitLab client: %s", str(e))
            return False
    
    def populate_repo_owners(self, repos: List) -> int:
        """
        Populate repository owners for GitLab repositories.
        Sort owners so that those with the most frequent (case-insensitive) 'vp' value appear first.
        Owners with vp=None or 'unknown' (case-insensitive) are always at the end.
        
        Args:
            repos: List of repository objects
            
        Returns:
            int: Number of repositories processed
        """
        if not self.gitlab_client:
            if not self.initialize_client():
                return 0
        
        processed_count = 0
        for repo in repos:
            self._populate_single_repo_owners(repo)
            processed_count += 1
            
        logger.info("✅ Processed GitLab repository owners for %d repositories in product '%s'", 
                   processed_count, self.product_name)
        return processed_count
    
    def _populate_single_repo_owners(self, repo):
        """
        Populate the repo_owners field for a single GitLab repo using project owners and HRDB info.
        Sort owners so that those with the most frequent (case-insensitive) 'vp' value appear first.
        Owners with vp=None or 'unknown' (case-insensitive) are always at the end.
        """
        project_id = getattr(repo.scm_info, 'id', None)
        if not project_id:
            logger.warning("No project_id found for repo '%s', skipping owner detection.", 
                          getattr(repo.scm_info, 'full_name', 'unknown'))
            repo.repo_owners = []
            return

        owners = self.gitlab_client.fetch_project_owners(project_id)
        if not owners:
            logger.warning("No owners found for GitLab project_id '%s'", project_id)
            repo.repo_owners = []
            return

        enriched_owners = []
        for owner in owners:
            username = owner.get('username')
            access_level = owner.get('access_level')
            hr_info = self.hrdb_client.get_user_data(username)
            enriched_owners.append({
                'name': username,
                'access_level': access_level,
                'general_manager': hr_info.get('general_manager'),
                'vp': hr_info.get('vp'),
                'title': hr_info.get('title'),
                'department': hr_info.get('department'),
                'manager_name': hr_info.get('manager_name'),
                'director': hr_info.get('director'),
                'vp2': hr_info.get('vp2'),
                'c_level': hr_info.get('c_level'),
                'worker_id': hr_info.get('worker_id'),
                'full_name': hr_info.get('full_name')
            })

        # Sorting logic (case-insensitive for vp)
        # 1. Group owners by vp (case-insensitive, except None/unknown)
        # 2. Count frequency of each vp (excluding None/unknown)
        # 3. Owners with most frequent vp (case-insensitive) come first
        # 4. Owners with vp None or 'unknown' (case-insensitive) always at the end

        def normalize_vp(vp):
            if vp is None:
                return None
            if isinstance(vp, str) and vp.strip().lower() == 'unknown':
                return None
            return vp.strip().lower() if isinstance(vp, str) else vp

        # Build list of normalized vps (excluding None/unknown)
        vps = [normalize_vp(owner['vp']) for owner in enriched_owners if normalize_vp(owner['vp']) is not None]
        vp_counter = Counter(vps)

        # For each owner, assign a sort key:
        #   - (-(vp_count), original_index) for owners with a valid vp
        #   - (float('inf'), original_index) for owners with vp None/unknown (always at end)
        def owner_sort_key(owner_with_index):
            idx, owner = owner_with_index
            vp_norm = normalize_vp(owner['vp'])
            if vp_norm is None:
                return (float('inf'), idx)
            # Negative count for descending sort
            return (-vp_counter[vp_norm], idx)

        # Attach original index to preserve order among ties
        owners_with_index = list(enumerate(enriched_owners))
        sorted_owners = [owner for idx, owner in sorted(owners_with_index, key=owner_sort_key)]

        repo.repo_owners = sorted_owners

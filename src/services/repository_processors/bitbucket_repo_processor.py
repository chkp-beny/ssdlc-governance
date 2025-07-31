import os
import logging
from typing import List
from collections import Counter
from src.services.hrdb_clients.hrdb_client import HRDBClient

logger = logging.getLogger(__name__)


class BitbucketRepoProcessor:
    """
    Handles Bitbucket repository owner detection and enrichment.
    Extracted from Product class to follow service layer pattern.
    """
    
    def __init__(self, product_name: str):
        """
        Initialize Bitbucket repository processor.
        
        Args:
            product_name: Name of the product
        """
        self.product_name = product_name
        self.bitbucket_client = None
        self.hrdb_client = HRDBClient()
        
    def initialize_client(self):
        """Initialize Bitbucket client with product-specific configuration."""
        try:
            from src.services.scm_clients.bitbucket_client import BitbucketClient
            from CONSTANTS import PRODUCT_SCM_TOKEN_ENV
            
            token_env = PRODUCT_SCM_TOKEN_ENV.get(self.product_name, None)
            token = os.getenv(token_env, '') if token_env else ''
            
            if not token:
                logger.warning("No SCM token found for product '%s', skipping SCM owner detection.", self.product_name)
                return False
            else:
                self.bitbucket_client = BitbucketClient(token)
                return True
        except ImportError as e:
            logger.error("Failed to import Bitbucket client: %s", str(e))
            return False
    
    def populate_repo_owners(self, repos: List) -> int:
        """
        Populate repository owners for Bitbucket repositories using PR reviewers and HRDB info.
        
        Args:
            repos: List of repository objects
            
        Returns:
            int: Number of repositories processed
        """
        if not self.bitbucket_client:
            if not self.initialize_client():
                return 0
        
        processed_count = 0
        for repo in repos:
            self._populate_single_repo_owners(repo)
            processed_count += 1
            
        logger.info("✅ Processed Bitbucket repository owners for %d repositories in product '%s'", 
                   processed_count, self.product_name)
        return processed_count
    
    def _populate_single_repo_owners(self, repo):
        """
        Populate the repo_owners field for a single Bitbucket repo using PR reviewers and HRDB info.
        """
        # Parse project_key and repo_slug from scm_info.full_name
        try:
            project_key, repo_slug = repo.scm_info.full_name.split('/', 1)
        except (ValueError, AttributeError) as e:
            logger.warning("Failed to parse project/repo from full_name '%s': %s", repo.scm_info.full_name, str(e))
            repo.repo_owners = []
            return

        reviewers = self.bitbucket_client.fetch_recent_merged_pr_reviewers(project_key, repo_slug)
        if not reviewers:
            logger.warning("No reviewers found for repo '%s'", repo.scm_info.full_name)
            repo.repo_owners = []
            return

        counts = Counter(reviewers)
        top_reviewers = counts.most_common(3)

        repo.repo_owners = []
        for username, review_count in top_reviewers:
            hr_info = self.hrdb_client.get_user_data(username)
            repo.repo_owners.append({
                'name': username,
                'review_count': review_count,
                'general_manager': hr_info['general_manager'],
                'vp': hr_info['vp'],
                'title': hr_info.get('title'),
                'department': hr_info.get('department'),
                'manager_name': hr_info.get('manager_name'),
                'director': hr_info.get('director'),
                'vp2': hr_info.get('vp2'),
                'c_level': hr_info.get('c_level'),
                'worker_id': hr_info.get('worker_id'),
                'full_name': hr_info.get('full_name')
            })

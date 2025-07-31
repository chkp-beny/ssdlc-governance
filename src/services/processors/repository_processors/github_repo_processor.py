import os
import logging
from typing import List
from collections import Counter
from src.services.clients.hrdb_clients.hrdb_client import HRDBClient

logger = logging.getLogger(__name__)


class GitHubRepoProcessor:
    """
    Handles GitHub repository owner detection and enrichment.
    Extracted from Product class to follow service layer pattern.
    """
    
    def __init__(self, product_name: str):
        """
        Initialize GitHub repository processor.
        
        Args:
            product_name: Name of the product
        """
        self.product_name = product_name
        self.github_client = None
        self.hrdb_client = HRDBClient()
        
    def initialize_client(self):
        """Initialize GitHub client with product-specific configuration."""
        try:
            from src.services.clients.scm_clients.github_client import GitHubClient
            from CONSTANTS import PRODUCT_SCM_TOKEN_ENV, PRODUCT_SCM_ORG_NAME
            
            token_env = PRODUCT_SCM_TOKEN_ENV.get(self.product_name, None)
            org = PRODUCT_SCM_ORG_NAME.get(self.product_name, None)
            token = os.getenv(token_env, '') if token_env else ''
            
            if not token or not org:
                logger.warning("No GitHub token or org found for product '%s', skipping GitHub owner detection.", self.product_name)
                return False
            else:
                self.github_client = GitHubClient(token, org)
                return True
        except ImportError as e:
            logger.error("Failed to import GitHub client: %s", str(e))
            return False
    
    def populate_repo_owners(self, repos: List) -> int:
        """
        Populate repository owners for all GitHub repositories using batch GraphQL.
        Enriches with HRDB info and sorts reviewers by review count (desc).
        
        Args:
            repos: List of repository objects
            
        Returns:
            int: Number of repositories processed
        """
        if not self.github_client:
            if not self.initialize_client():
                return 0
        
        # Collect all repo names (as expected by GitHubClient)
        repo_names = []
        repo_map = {}
        for repo in repos:
            # Assumes repo.scm_info.full_name is "org/repo"
            repo_name = getattr(repo.scm_info, 'repo_name', None)
            if repo_name:
                repo_names.append(repo_name)
                repo_map[repo_name] = repo

        if not repo_names:
            logger.warning("No GitHub repositories found for owner detection in product '%s'", self.product_name)
            return 0

        # Batch fetch reviewers for all repos in chunks of 30
        batch_size = 30
        reviewers_by_repo = {}

        for i in range(0, len(repo_names), batch_size):
            batch = repo_names[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(repo_names) + batch_size - 1) // batch_size
            
            logger.info("🔄 Fetching GitHub PR reviewers for batch %d/%d (%d repos)...", 
                       batch_num, total_batches, len(batch))
            
            batch_results = self.github_client.fetch_repo_reviewers_batch(batch)
            reviewers_by_repo.update(batch_results)

        if not reviewers_by_repo:
            logger.warning("No reviewers returned from GitHub batch queries for product '%s'", self.product_name)
            return 0

        processed_count = 0
        for repo_name, reviewers in reviewers_by_repo.items():
            repo = repo_map.get(repo_name)
            if not repo:
                continue
            if not reviewers:
                repo.repo_owners = []
                continue

            # Count reviewers by frequency
            counts = Counter(reviewers)
            top_reviewers = counts.most_common(3)

            enriched_owners = []
            for username, review_count in top_reviewers:
                # Normalize username if it starts with 'chkp-'
                if username and username.startswith('chkp-'):
                    normalized_username = username[len('chkp-'):]
                else:
                    normalized_username = username
                hr_info = self.hrdb_client.get_user_data(normalized_username)
                enriched_owners.append({
                    'name': normalized_username,
                    'review_count': review_count,
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
            repo.repo_owners = enriched_owners
            processed_count += 1
            
        logger.info("✅ Processed GitHub repository owners for %d repositories in product '%s'", 
                   processed_count, self.product_name)
        return processed_count

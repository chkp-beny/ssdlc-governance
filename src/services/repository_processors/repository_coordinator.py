import logging
from typing import List
from src.services.data_loader import DataLoader
from src.models.repo import Repo
from .github_repo_processor import GitHubRepoProcessor
from .gitlab_repo_processor import GitLabRepoProcessor
from .bitbucket_repo_processor import BitbucketRepoProcessor

logger = logging.getLogger(__name__)


class RepositoryCoordinator:
    """
    Coordinates repository loading and owner detection from multiple SCM sources.
    Extracted from Product class to follow service layer pattern.
    """
    
    def __init__(self, product_name: str, scm_type: str, organization_id: str, compass_token: str):
        """
        Initialize repository coordinator.
        
        Args:
            product_name: Name of the product
            scm_type: Source control management type (e.g., 'github', 'gitlab', 'bitbucket_server')
            organization_id: Organization ID in Compass
            compass_token: Access token for Compass API
        """
        self.product_name = product_name
        self.scm_type = scm_type
        self.organization_id = organization_id
        self.data_loader = DataLoader(compass_token=compass_token)
        
        # Initialize SCM-specific processors
        self.processors = {
            'github': GitHubRepoProcessor(product_name),
            'gitlab': GitLabRepoProcessor(product_name),
            'bitbucket_server': BitbucketRepoProcessor(product_name)
        }
    
    def load_repositories(self) -> List[Repo]:
        """
        Load repositories for the product using DataLoader and populate owners.
        Fetches repositories based on product's SCM type and organization ID.
        Adds progress logging for repo owner retrieval.
        
        Returns:
            List[Repo]: List of loaded repository objects
        """
        try:
            # Load repositories using DataLoader with product's SCM info
            repo_data = self.data_loader.load_repositories(self.scm_type, self.organization_id)

            # Parse repo_data and create Repo objects
            repos = []
            total_repos = len(repo_data)
            logger.info("📦 Found %d repositories for product '%s'. Starting repo owner retrieval...", 
                       total_repos, self.product_name)
            
            processed_repos = 0
            for repo_json in repo_data:
                try:
                    repo = Repo.from_json(repo_json, self.product_name)
                    processed_repos += 1
                    # Progress logging every 10 repos, and always for first and last
                    if processed_repos == 1 or processed_repos == total_repos or processed_repos % 10 == 0:
                        logger.info("🔄 Progress: %d/%d repositories processed for owner detection (%.1f%%)",
                                    processed_repos, total_repos, (processed_repos/total_repos)*100)
                    
                    repos.append(repo)
                except (ValueError, KeyError) as e:
                    logger.warning("Failed to create Repo from JSON for %s: %s", 
                                  repo_json.get('repo_name', 'unknown'), str(e))

            # Populate repository owners based on SCM type
            self._populate_repository_owners(repos)

            logger.info("✅ Successfully loaded %d repositories for product '%s' and completed repo owner retrieval.", 
                       len(repos), self.product_name)
            return repos
            
        except (ImportError, ValueError) as e:
            logger.error("Error loading repositories for product '%s': %s", self.product_name, str(e))
            return []
    
    def _populate_repository_owners(self, repos: List[Repo]):
        """
        Populate repository owners based on SCM type.
        
        Args:
            repos: List of repository objects to populate
        """
        processor = self.processors.get(self.scm_type)
        
        if not processor:
            logger.warning("No processor available for SCM type '%s'", self.scm_type)
            return
        
        # For individual repo processing (BitBucket and GitLab)
        if self.scm_type in ['bitbucket_server', 'gitlab']:
            # Process repos individually during the main loop
            filtered_repos = [repo for repo in repos if repo.scm_info]
            processor.populate_repo_owners(filtered_repos)
        
        # For batch processing (GitHub)
        elif self.scm_type == 'github':
            # Process all repos in batch
            processor.populate_repo_owners(repos)

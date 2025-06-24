"""
Product class - Product-level aggregation and ownership
Contains list of Repo objects and DevOps object
"""

from typing import List, Optional
import logging
import os
from dotenv import load_dotenv
from .devops import DevOps
from .repo import Repo

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Product:
    """
    Product-level aggregation containing repositories and DevOps ownership
    """
    
    def __init__(self, name: str, scm_type: str, organization_id: str, devops: Optional[DevOps] = None):
        """
        Initialize Product
        
        Args:
            name (str): Product name
            scm_type (str): Source control management type (e.g., 'github')
            organization_id (str): Organization ID in Compass
            devops (DevOps, optional): DevOps contact for this product
        """
        self.name = name
        self.scm_type = scm_type
        self.organization_id = organization_id
        self.devops = devops
        self.repos: List[Repo] = []  # Contains Repo objects
        
        # Create DataLoader instance for this product
        self._initialize_data_loader()
        
        logger.info("Product '%s' created with DataLoader", name)
    
    def _initialize_data_loader(self):
        """
        Initialize DataLoader with API credentials from environment
        """
        try:
            from src.services.data_loader import DataLoader
        except ImportError:
            # Fallback for tests
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from src.services.data_loader import DataLoader
        
        # Get credentials from environment variables
        compass_token = os.getenv('COMPASS_ACCESS_TOKEN', '')
        compass_url = os.getenv('COMPASS_BASE_URL', '')
        
        # Initialize DataLoader (other API credentials can be added later)
        self.data_loader = DataLoader(
            compass_token=compass_token,
            compass_url=compass_url
        )
        
        logger.debug("DataLoader initialized for product '%s'", self.name)
    
    def load_repositories(self):
        """
        Load repositories for this product using DataLoader
        Fetches repositories based on product's SCM type and organization ID
        """
        try:
            # Load repositories using DataLoader with product's SCM info
            repo_data = self.data_loader.load_repositories(self.scm_type, self.organization_id)
            
            # Parse repo_data and create Repo objects
            self.repos = []
            for repo_json in repo_data:
                try:
                    repo = Repo.from_json(repo_json, self.name)
                    self.repos.append(repo)
                except (ValueError, KeyError) as e:
                    logger.warning("Failed to create Repo from JSON for %s: %s", 
                                  repo_json.get('repo_name', 'unknown'), str(e))
            
            logger.info("Successfully loaded %d repositories for product '%s'", len(self.repos), self.name)
            
        except (ImportError, ValueError) as e:
            logger.error("Error loading repositories for product '%s': %s", self.name, str(e))
    
    def load_ci_data(self):
        """
        Load CI data for all repositories in this product
        Main entry point for CI data loading - calls both JFrog and Sonar data loading
        """
        logger.info("Loading CI data for product '%s'", self.name)
        
        # Load JFrog CI data
        self._load_jfrog_ci_data()
        
        # Load Sonar CI data (placeholder for future implementation)
        self._load_sonar_ci_data()
        
        logger.info("CI data loading completed for product '%s'", self.name)
    
    def _load_jfrog_ci_data(self):
        """
        Load JFrog CI data for repositories in this product
        Updates JfrogCIStatus.is_exist for matching repositories
        """
        try:
            # Import constants
            try:
                from CONSTANTS import PRODUCT_JFROG_PROJECT
            except ImportError:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
                from CONSTANTS import PRODUCT_JFROG_PROJECT
            
            # Get JFrog project name for this product
            jfrog_project = PRODUCT_JFROG_PROJECT.get(self.name, "")
            
            # Skip if no JFrog project configured
            if not jfrog_project:
                logger.info("No JFrog project configured for product '%s', skipping JFrog CI data loading", self.name)
                return
            
            # Initialize JFrog client
            jfrog_token = os.getenv('CYBERINT_JFROG_ACCESS_TOKEN', '')
            if not jfrog_token:
                logger.warning("CYBERINT_JFROG_ACCESS_TOKEN not found, skipping JFrog CI data loading")
                return
            
            from src.services.data_loader import JfrogClient
            jfrog_client = JfrogClient(jfrog_token)
            
            # Fetch build information (raw JSON)
            build_data = jfrog_client.fetch_build_info(jfrog_project)
            
            # Process the JSON to extract build names
            build_names_set = set()
            builds = build_data.get('builds', [])
            for build in builds:
                uri = build.get('uri', '')
                if uri.startswith('/'):
                    build_name = uri[1:]  # Remove leading slash
                    if build_name:
                        build_names_set.add(build_name)
            
            logger.info("Found %d builds in JFrog for project '%s'", len(build_names_set), jfrog_project)
            
            # Update repository CI status
            updated_count = 0
            for repo in self.repos:
                # Ensure CI status is initialized
                if repo.ci_status is None:
                    from .ci_status import CIStatus
                    repo.update_ci_status(CIStatus())
                
                if repo.scm_info and repo.scm_info.repo_name:
                    if repo.scm_info.repo_name in build_names_set:
                        # Update JFrog CI status using setter method
                        repo.ci_status.jfrog_status.set_exists(True)
                        updated_count += 1
                        logger.debug("Updated JFrog CI status for repo '%s'", repo.scm_info.repo_name)
            
            logger.info("Updated JFrog CI status for %d/%d repositories in product '%s'", 
                       updated_count, len(self.repos), self.name)
            
        except (ImportError, KeyError, ValueError) as e:
            logger.error("Error loading JFrog CI data for product '%s': %s", self.name, str(e))
    
    def _load_sonar_ci_data(self):
        """
        Load Sonar CI data for repositories in this product
        Updates SonarCIStatus.is_exist for matching repositories
        
        NOTE: This is a placeholder method for future implementation
        The actual Sonar API integration will be implemented later
        """
        logger.info("Sonar CI data loading not implemented yet for product '%s'", self.name)
        # Future implementation will include:
        # 1. Get Sonar project configuration from constants
        # 2. Initialize Sonar client with credentials
        # 3. Fetch project information from Sonar API
        # 4. Create set of project names
        # 5. Update repository SonarCIStatus.is_exist for matching repos

    def get_repos_count(self) -> int:
        """
        Get number of repositories in this product
        
        Returns:
            int: Repository count
        """
        return len(self.repos)
    
    def __str__(self) -> str:
        devops_name = self.devops.full_name if self.devops else "No DevOps assigned"
        return f"Product(name='{self.name}', scm='{self.scm_type}', org_id='{self.organization_id}', repos={len(self.repos)}, devops='{devops_name}')"
    
    def __repr__(self) -> str:
        return f"Product(name='{self.name}', scm_type='{self.scm_type}', organization_id='{self.organization_id}', repos={len(self.repos)}, devops={self.devops})"

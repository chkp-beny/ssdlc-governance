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
        
        # Map to store build names as keys and Repo objects as values
        self.build_name_to_repo_map = {}
        
        # Class-level attribute to track unmapped build names
        self.unmapped_build_names = set()

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

        # Initialize DataLoader (other API credentials can be added later)
        self.data_loader = DataLoader(compass_token=compass_token)
        
        logger.debug("DataLoader initialized for product '%s'", self.name)
    
    def load_repositories(self):
        """
        Load repositories for this product using RepositoryCoordinator.
        Uses RepositoryCoordinator to delegate to specialized processors.
        """
        logger.info("Loading repositories for product '%s'", self.name)
        
        try:
            from src.services.repository_processors import RepositoryCoordinator
            
            # Get compass token from environment
            compass_token = os.getenv('COMPASS_ACCESS_TOKEN', '')
            
            coordinator = RepositoryCoordinator(self.name, self.scm_type, self.organization_id, compass_token)
            self.repos = coordinator.load_repositories()
            
            logger.info("Repository loading completed for product '%s': %d repositories loaded", 
                       self.name, len(self.repos))
        except ImportError as e:
            logger.error("Failed to import RepositoryCoordinator: %s", str(e))
            raise
    
    
    def load_ci_data(self):
        """
        Load CI data for all repositories in this product.
        Uses CiCoordinator to delegate to specialized processors.
        """
        logger.info("Loading CI data for product '%s'", self.name)
        
        try:
            from src.services.ci_processors import CiCoordinator
            
            # Get compass token from environment
            compass_token = os.getenv('COMPASS_ACCESS_TOKEN', '')
            
            coordinator = CiCoordinator(self.name, self.organization_id, compass_token)
            results = coordinator.load_all_ci_data(self.repos, self)
            
            logger.info("CI data loading completed for product '%s': JFrog=%d, Sonar=%d repos updated", 
                       self.name, results['jfrog_updated'], results['sonar_updated'])
        except ImportError as e:
            logger.error("Failed to import CiCoordinator: %s", str(e))
            raise
    

    def load_vulnerabilities(self):
        """
        Load vulnerability data for repositories in this product.
        Uses VulnerabilityCoordinator to delegate to specialized processors.
        """
        logger.info("Loading vulnerability data for product '%s'", self.name)
        
        try:
            from src.services.vulnerability_processors import VulnerabilityCoordinator
            coordinator = VulnerabilityCoordinator(self.name, self.organization_id)
            results = coordinator.load_all_vulnerabilities(self.repos)
            
            logger.info("Vulnerability data loading completed for product '%s': JFrog=%d, Sonar=%d repos updated", 
                       self.name, results['jfrog_updated'], results['sonar_updated'])
        except ImportError as e:
            logger.error("Failed to import VulnerabilityCoordinator: %s", str(e))
            raise
    
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

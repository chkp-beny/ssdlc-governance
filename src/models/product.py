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
                except Exception as e:
                    logger.warning("Failed to create Repo from JSON for %s: %s", 
                                  repo_json.get('repo_name', 'unknown'), str(e))
            
            logger.info("Successfully loaded %d repositories for product '%s'", len(self.repos), self.name)
            
        except Exception as e:
            logger.error("Error loading repositories for product '%s': %s", self.name, str(e))
    
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

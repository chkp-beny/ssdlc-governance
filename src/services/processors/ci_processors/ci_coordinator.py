import logging
from typing import Dict, List
from .jfrog_ci_processor import JfrogCiProcessor
from .sonar_ci_processor import SonarCiProcessor

logger = logging.getLogger(__name__)


class CiCoordinator:
    """
    Coordinates CI data loading from multiple sources (JFrog and Sonar).
    Extracted from Product class to follow service layer pattern.
    """
    
    def __init__(self, product_name: str, organization_id: str, compass_token: str):
        """
        Initialize CI coordinator for a product.
        
        Args:
            product_name: Name of the product
            organization_id: Organization ID for API calls
            compass_token: Access token for Compass API
        """
        self.product_name = product_name
        self.organization_id = organization_id
        self.compass_token = compass_token
        
        # Initialize processors
        self.jfrog_processor = JfrogCiProcessor(product_name)
        self.sonar_processor = SonarCiProcessor(product_name, organization_id, compass_token)
    
    def load_all_ci_data(self, repos: List, product_instance=None) -> Dict:
        """
        Load CI data from all sources for repositories in the product.
        
        Args:
            repos: List of repository objects
            product_instance: Product instance to update build_name_to_repo_map
            
        Returns:
            Dict containing results from all processors
        """
        logger.info("Loading CI data for product '%s'", self.product_name)
        
        # Load JFrog CI data
        jfrog_results = self.jfrog_processor.process_ci_data(repos)
        
        # Update product instance with build mapping if provided
        if product_instance and 'build_name_to_repo_map' in jfrog_results:
            product_instance.build_name_to_repo_map.update(jfrog_results['build_name_to_repo_map'])
            product_instance.unmapped_build_names.update(jfrog_results['unmapped_build_names'])
        
        # Load Sonar CI data
        sonar_results = self.sonar_processor.process_ci_data(repos)
        
        logger.info("CI data loading completed for product '%s': JFrog=%d, Sonar=%d repos updated", 
                   self.product_name, jfrog_results['updated_count'], sonar_results['updated_count'])
        
        return {
            'jfrog_updated': jfrog_results['updated_count'],
            'sonar_updated': sonar_results['updated_count'],
            'total_repos': len(repos)
        }

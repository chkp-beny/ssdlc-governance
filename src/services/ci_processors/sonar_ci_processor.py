import logging
from typing import Dict, List
from src.services.data_loader import DataLoader

logger = logging.getLogger(__name__)


class SonarCiProcessor:
    """
    Handles Sonar CI data loading for product repositories.
    Extracted from Product class to follow service layer pattern.
    """
    
    def __init__(self, product_name: str, organization_id: str, compass_token: str):
        """
        Initialize Sonar CI processor for a product.
        
        Args:
            product_name: Name of the product
            organization_id: Organization ID for Compass API
            compass_token: Access token for Compass API
        """
        self.product_name = product_name
        self.organization_id = organization_id
        self.data_loader = DataLoader(compass_token=compass_token)
    
    def process_ci_data(self, repos: List) -> Dict:
        """
        Process Sonar CI data for all repositories in the product.
        Updates SonarCIStatus.is_exist and project_key for matching repositories.
        
        Args:
            repos: List of repository objects
            
        Returns:
            Dict containing processing results
        """
        # TODO: Extend this logic to check the scanned branches for each project with Sonar API.
        # Currently only checking if projects exist, but should also verify which branches are being scanned
        # and update the is_main_branch_scanned field accordingly.
        try:
            logger.info("Loading Sonar CI data for product '%s'", self.product_name)
            
            # Fetch Sonar projects from Compass API using "sonarqube" type
            sonar_data = self.data_loader.load_repositories("sonarqube", self.organization_id)
            
            if not sonar_data:
                logger.info("No Sonar projects found for product '%s'", self.product_name)
                return {'updated_count': 0, 'total_repos': len(repos)}
            
            # Extract project keys and detect prefix
            project_keys = []
            repo_names_set = set()
            prefix = ""
            
            for project in sonar_data:
                project_key = project.get('project_key', '')
                if project_key:
                    project_keys.append(project_key)
            
            if not project_keys:
                logger.warning("No project keys found in Sonar data")
                return {'updated_count': 0, 'total_repos': len(repos)}
            
            # Detect prefix from first project key (format: "text-")
            first_project_key = project_keys[0]
            if '-' in first_project_key:
                prefix = first_project_key.split('-')[0] + '-'
                logger.info("Detected Sonar project key prefix: '%s'", prefix)
            else:
                logger.warning("Could not detect prefix from project key: %s", first_project_key)
                return {'updated_count': 0, 'total_repos': len(repos)}
            
            # Extract repo names (remove prefix from project keys)
            for project_key in project_keys:
                if project_key.startswith(prefix):
                    repo_name = project_key[len(prefix):]  # Remove prefix
                    if repo_name:
                        repo_names_set.add(repo_name)
            
            logger.info("Found %d Sonar projects for product '%s' with prefix '%s'", 
                       len(repo_names_set), self.product_name, prefix)
            
            # Update repository CI status
            updated_count = 0
            for repo in repos:
                # Ensure CI status is initialized
                if repo.ci_status is None:
                    from src.models.ci_status import CIStatus
                    repo.update_ci_status(CIStatus())
                
                if repo.scm_info and repo.scm_info.repo_name:
                    if repo.scm_info.repo_name in repo_names_set:
                        # Create full project key (prefix + repo name)
                        full_project_key = prefix + repo.scm_info.repo_name
                        # Update Sonar CI status using setter method
                        repo.ci_status.sonar_status.set_exists(True, full_project_key)
                        updated_count += 1
                        logger.debug("Updated Sonar CI status for repo '%s' with project_key '%s'", 
                                   repo.scm_info.repo_name, full_project_key)
            
            logger.info("Updated Sonar CI status for %d/%d repositories in product '%s'", 
                       updated_count, len(repos), self.product_name)
            
            return {'updated_count': updated_count, 'total_repos': len(repos)}
            
        except (ValueError, KeyError, OSError) as e:
            logger.error("Error loading Sonar CI data for product '%s': %s", self.product_name, str(e))
            return {'updated_count': 0, 'total_repos': len(repos)}

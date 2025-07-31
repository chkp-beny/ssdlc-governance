"""
DataLoader service - Orchestrates all API calls for fetching repository data
Contains clients for Compass, JFrog, and Sonar APIs
"""

import logging
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
class DataLoader:
    """
    Central data loading service that orchestrates all API calls
    Contains clients for Compass, JFrog, and Sonar APIs
    """
    
    def __init__(self, compass_token: str = None, jfrog_token: Optional[str] = None, sonar_token: Optional[str] = None):
        """
        Initialize DataLoader with API clients
        
        Args:
            compass_token (str): Compass API access token
            jfrog_token (str, optional): JFrog API access token
            sonar_token (str, optional): Sonar API access token
        """
        import os
        from src.services.clients.compass_clients.compass_client import CompassClient
        from src.services.clients.jfrog_clients.jfrog_client import JfrogClient
        from src.services.clients.sonar_clients.sonar_client import SonarClient
        compass_url = os.environ["COMPASS_BASE_URL"]
        sonar_url = os.environ["SONAR_BASE_URL"]
        self.compass_client = CompassClient(compass_token, compass_url)
        self.jfrog_client = JfrogClient(jfrog_token) if jfrog_token else None
        self.sonar_client = SonarClient(sonar_token, sonar_url) if sonar_token and sonar_url else None
        
        logger.info("DataLoader initialized with clients")
    
    def test_all_connections(self) -> Dict[str, bool]:
        """
        Test connections to all configured APIs
        
        Returns:
            Dict[str, bool]: Connection status for each API
        """
        results = {
            "compass": self.compass_client.test_connection()
        }
        
        if self.jfrog_client:
            results["jfrog"] = self.jfrog_client.test_connection()
        
        if self.sonar_client:
            results["sonar"] = self.sonar_client.test_connection()
        
        logger.info(f"API connection test results: {results}")
        return results
    
    def load_repositories(self, type: str, organization_id: str) -> List[Dict]:
        """
        Load repository data from Compass API
        
        Args:
            type (str): Repository type from CONSTANTS (SCM types or sonarqube)
            organization_id (str): Organization ID from CONSTANTS
            
        Returns:
            List[Dict]: Repository data from Compass API
        """
        logger.info(f"Loading repositories for type: {type}, org: {organization_id}")
        
        try:
            # Fetch repository list from Compass API
            repos = self.compass_client.fetch_repositories(type, organization_id)
            
            if not repos:
                logger.warning("No repositories found")
                return []
            
            logger.info(f"Successfully loaded {len(repos)} repositories")
            return repos
            
        except Exception as e:
            logger.error(f"Error loading repositories: {str(e)}")
            return []

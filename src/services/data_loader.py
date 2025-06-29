"""
DataLoader service - Orchestrates all API calls for fetching repository data
Contains clients for Compass, JFrog, and Sonar APIs
"""

import logging
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class CompassClient:
    """
    Client for Compass API integration
    Handles repository data, vulnerabilities, and CI status fetching
    """
    
    def __init__(self, access_token: str, base_url: str):
        """
        Initialize Compass client
        
        Args:
            access_token (str): API access token
            base_url (str): Base URL for Compass API
        """
        self.access_token = access_token
        self.base_url = base_url.rstrip('/')  # Remove trailing slash
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        logger.info("CompassClient initialized")
    
    def test_connection(self, type: str = 'bitbucket_server', organization_id: str = '2') -> bool:
        """
        Test connection to Compass API
        
        Args:
            type (str): Repository type to test with (default: bitbucket_server for Cyberint)
            organization_id (str): Organization ID to test with (default: 2 for Cyberint)
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Simple GET request to test connection
            response = requests.get(
                f"{self.base_url}/repositories",
                headers=self.headers,
                params={'type': type, 'organization_id': organization_id, 'limit': 1},
                timeout=10
            )
            success = response.status_code == 200
            logger.info("Compass API connection test: %s", "SUCCESS" if success else "FAILED")
            return success
        except requests.exceptions.RequestException as e:
            logger.error("Compass API connection test failed: %s", str(e))
            return False
    
    def fetch_repositories(self, type: str, organization_id: str) -> List[Dict]:
        """
        Fetch repositories from Compass API with pagination support
        
        Args:
            type (str): Repository type (github, gitlab, bitbucket_server, sonarqube, etc.)
            organization_id (str): Organization ID
            
        Returns:
            List[Dict]: List of repository data
        """
        try:
            logger.info("Fetching repositories for type: %s, org: %s", type, organization_id)
            
            # Build the API endpoint
            url = f"{self.base_url}/repositories"
            all_repositories = []
            page = 1
            limit = 1000  # Reasonable page size
            
            while True:
                # Parameters for the API call
                params = {
                    'type': type,
                    'organization_id': organization_id,
                    'limit': limit,
                    'page': page
                }
                
                logger.debug("Fetching page %d with limit %d", page, limit)
                
                # Make the API request
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                
                # Check if request was successful
                if response.status_code == 200:
                    data = response.json()
                    repositories = data.get('repositories', [])
                    pagination = data.get('pagination', {})
                    
                    # Add repositories to our collection
                    all_repositories.extend(repositories)
                    
                    logger.debug("Page %d: fetched %d repositories", page, len(repositories))
                    
                    # Check if we have more pages
                    total_pages = pagination.get('pages', 1)
                    if page >= total_pages or len(repositories) == 0:
                        break
                    
                    page += 1
                else:
                    logger.error("API request failed with status %d: %s", 
                               response.status_code, response.text)
                    break
            
            logger.info("Successfully fetched %d repositories across %d pages", 
                       len(all_repositories), page)
            return all_repositories
                
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching repositories: %s", str(e))
            return []
        except Exception as e:
            logger.error("Unexpected error fetching repositories: %s", str(e))
            return []
    
    def fetch_jfrog_vulnerabilities(self, org_id: str) -> Dict:
        """
        Fetch JFrog vulnerabilities for an organization
        
        Args:
            org_id (str): Organization ID
            
        Returns:
            Dict: Vulnerability data mapped by artifact key
        """
        try:
            url = f"{self.base_url}/remediation/jfrog/vulnerabilities"
            params = {'organization_id': org_id}
            
            logger.info(f"Fetching JFrog vulnerabilities for org {org_id}")
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched JFrog vulnerabilities: {len(data)} artifacts")
                return data
            else:
                logger.error("JFrog vulnerabilities API request failed with status %d: %s", 
                           response.status_code, response.text)
                return {}
                
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching JFrog vulnerabilities: %s", str(e))
            return {}
        except Exception as e:
            logger.error("Unexpected error fetching JFrog vulnerabilities: %s", str(e))
            return {}
    
    def fetch_sonarqube_issues(self, org_id: str) -> Dict:
        """
        Fetch SonarQube issues/vulnerabilities for an organization
        
        Args:
            org_id (str): Organization ID
            
        Returns:
            Dict: Issues data mapped by project key
        """
        try:
            url = f"{self.base_url}/remediation/sonarqube/issues"
            params = {'organization_id': org_id}
            
            logger.info(f"Fetching SonarQube issues for org {org_id}")
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched SonarQube issues: {len(data)} projects")
                return data
            else:
                logger.error("SonarQube issues API request failed with status %d: %s", 
                           response.status_code, response.text)
                return {}
                
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching SonarQube issues: %s", str(e))
            return {}
        except Exception as e:
            logger.error("Unexpected error fetching SonarQube issues: %s", str(e))
            return {}
    
    def fetch_sonarqube_secrets(self, org_id: str) -> Dict:
        """
        Fetch SonarQube secrets count for an organization
        
        Args:
            org_id (str): Organization ID
            
        Returns:
            Dict: Secrets data mapped by project key
        """
        try:
            url = f"{self.base_url}/remediation/sonarqube/secrets"
            params = {'organization_id': org_id}
            
            logger.info(f"Fetching SonarQube secrets for org {org_id}")
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched SonarQube secrets: {len(data)} projects")
                return data
            else:
                logger.error("SonarQube secrets API request failed with status %d: %s", 
                           response.status_code, response.text)
                return {}
                
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching SonarQube secrets: %s", str(e))
            return {}
        except Exception as e:
            logger.error("Unexpected error fetching SonarQube secrets: %s", str(e))
            return {}

class JfrogClient:
    """
    Client for JFrog API integration
    Handles build information and CI status fetching
    """
    
    def __init__(self, access_token: str):
        """
        Initialize JFrog client
        
        Args:
            access_token (str): JFrog API access token
        """
        # Import constants for base URL
        try:
            from CONSTANTS import JFROG_BASE_URL
        except ImportError:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from CONSTANTS import JFROG_BASE_URL
        
        self.access_token = access_token
        self.base_url = JFROG_BASE_URL.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        logger.info("JfrogClient initialized with base URL: %s", self.base_url)
    
    def test_connection(self) -> bool:
        """
        Test connection to JFrog API using the ping endpoint
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Use ping endpoint for connection test (no auth required)
            response = requests.get(
                f"{self.base_url}/xray/api/v1/system/ping",
                timeout=10
            )
            success = response.status_code == 200
            if success:
                data = response.json()
                success = data.get('status') == 'pong'
            
            logger.info("JFrog API connection test: %s", "SUCCESS" if success else "FAILED")
            return success
        except requests.exceptions.RequestException as e:
            logger.error("JFrog API connection test failed: %s", str(e))
            return False
    
    def fetch_all_project_builds(self, project: str) -> dict:
        """
        Fetch all project builds information from JFrog API for a project
        Returns the raw JSON response for processing by the caller
        
        Args:
            project (str): Project name
            
        Returns:
            dict: Raw JSON response from JFrog API
        """
        try:
            logger.info("Fetching JFrog build info for project: %s", project)
            
            # Build the API endpoint
            url = f"{self.base_url}/artifactory/api/build"
            
            # Parameters for the API call
            params = {'project': project}
            
            # Make the API request
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully fetched build info for project %s", project)
                return data
            else:
                logger.error("JFrog API error: %s - %s", response.status_code, response.text)
                return {}
                
        except requests.exceptions.RequestException as e:
            logger.error("JFrog API request failed: %s", str(e))
            return {}
        except Exception as e:
            logger.error("Error processing JFrog build info: %s", str(e))
            return {}


class SonarClient:
    """
    Client for Sonar API integration
    Handles code quality metrics
    """
    
    def __init__(self, access_token: str, base_url: str):
        """
        Initialize Sonar client
        
        Args:
            access_token (str): API access token
            base_url (str): Base URL for Sonar API
        """
        self.access_token = access_token
        self.base_url = base_url
        
        logger.info("SonarClient initialized")
    
    def test_connection(self) -> bool:
        """
        Test connection to Sonar API
        
        Returns:
            bool: True if connection successful
        """
        # TODO: Implement connection test
        logger.info("Testing Sonar API connection...")
        return True


class DataLoader:
    """
    Central data loading service that orchestrates all API calls
    Contains clients for Compass, JFrog, and Sonar APIs
    """
    
    def __init__(self, compass_token: str, compass_url: str, 
                 jfrog_token: Optional[str] = None, jfrog_url: Optional[str] = None,
                 sonar_token: Optional[str] = None, sonar_url: Optional[str] = None):
        """
        Initialize DataLoader with API clients
        
        Args:
            compass_token (str): Compass API access token
            compass_url (str): Compass API base URL
            jfrog_token (str, optional): JFrog API access token
            jfrog_url (str, optional): JFrog API base URL
            sonar_token (str, optional): Sonar API access token
            sonar_url (str, optional): Sonar API base URL
        """
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

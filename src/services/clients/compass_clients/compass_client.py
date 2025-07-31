
import logging
import requests
from typing import List, Dict

logger = logging.getLogger(__name__)

class CompassClient:
    """
    Client for Compass API integration
    Handles repository data, vulnerabilities, and CI status fetching
    """
    
    def __init__(self, access_token: str, base_url: str = None):
        """
        Initialize Compass client
        
        Args:
            access_token (str): API access token
            base_url (str): Base URL for Compass API (optional, will use env if not provided)
        """
        self.access_token = access_token
        import os
        self.base_url = (base_url or os.environ["COMPASS_BASE_URL"]).rstrip('/')  # Remove trailing slash
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
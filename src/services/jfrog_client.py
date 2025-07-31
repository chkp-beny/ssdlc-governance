

import logging
import requests
from typing import List

logger = logging.getLogger(__name__)

class JfrogClient:
    """
    Client for JFrog API integration
    Handles build information and CI status fetching
    """
    
    def __init__(self, access_token: str, base_url: str = None):
        """
        Initialize JFrog client
        
        Args:
            access_token (str): JFrog API access token
        """
        import os
        self.access_token = access_token
        self.base_url = (base_url or os.environ["JFROG_BASE_URL"]).rstrip('/')
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
    
    def fetch_build_metadata(self, build_name: str, project: str) -> dict:
        """
        Fetch build metadata for a specific build to get build numbers and versions
        
        Args:
            build_name (str): Name of the build
            project (str): Project name
            
        Returns:
            dict: Build metadata with build numbers and timestamps
        """
        try:
            logger.info("Fetching build metadata and details for build: %s in project: %s", build_name, project)
            
            # Build the API endpoint
            url = f"{self.base_url}/artifactory/api/build/{build_name}"
            
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
                logger.debug("Successfully fetched build metadata for build %s", build_name)
                return data
            else:
                logger.error("JFrog API error fetching build metadata: %s - %s", 
                           response.status_code, response.text)
                return {}
                
        except requests.exceptions.RequestException as e:
            logger.error("JFrog API request failed for build metadata: %s", str(e))
            return {}
        except Exception as e:
            logger.error("Error processing JFrog build metadata: %s", str(e))
            return {}
    
    def fetch_build_details(self, build_name: str, build_number: str, project: str) -> dict:
        """
        Fetch detailed build information including properties and metadata
        
        Args:
            build_name (str): Name of the build
            build_number (str): Build number
            project (str): Project name
            
        Returns:
            dict: Detailed build information with properties
        """
        try:
            # Build details logging is handled in fetch_build_metadata method
            
            # Build the API endpoint
            url = f"{self.base_url}/artifactory/api/build/{build_name}/{build_number}"
            
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
                logger.debug("Successfully fetched build details for build %s/%s", 
                           build_name, build_number)
                return data
            else:
                logger.error("JFrog API error fetching build details: %s - %s", 
                           response.status_code, response.text)
                return {}
                
        except requests.exceptions.RequestException as e:
            logger.error("JFrog API request failed for build details: %s", str(e))
            return {}
        except Exception as e:
            logger.error("Error processing JFrog build details: %s", str(e))
            return {}
    
    def query_aql_artifacts(self, repo_name: str) -> dict:
        """
        Query artifacts from a single local repository using AQL API.
        Fetches artifact metadata with properties for vulnerability matching.
        
        Args:
            repo_name (str): Single local repository name to query
            
        Returns:
            dict: AQL response with artifact data
        """
        try:
            logger.info("Querying AQL artifacts for repository: %s", repo_name)
            
            # Build AQL query for single repository
            aql_query = f'items.find({{"repo": {{"$eq": "{repo_name}"}}, "type": "file"}}).include("property")'
            
            # Build the API endpoint
            url = f"{self.base_url}/artifactory/api/search/aql"
            
            # Make the API request
            response = requests.post(
                url,
                headers={**self.headers, 'Content-Type': 'text/plain'},
                data=aql_query,
                timeout=60
            )
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully queried AQL artifacts for %s: %d results", 
                           repo_name, len(data.get('results', [])))
                return data
            else:
                logger.error("Failed to query AQL artifacts for %s: %s", 
                           repo_name, response.status_code)
                return {}
                
        except (requests.RequestException, ValueError) as e:
            logger.error("Error querying AQL artifacts for %s: %s", repo_name, str(e))
            return {}
    
    def query_aql_specific_artifacts(self, repo_name: str, artifact_paths: List[tuple]) -> dict:
        """
        Query specific artifacts from a repository using AQL API with $or operator.
        Optimized for fetching only missing artifacts instead of all artifacts.
        
        Args:
            repo_name (str): Repository name to query
            artifact_paths (List[tuple]): List of (path, name) tuples for specific artifacts
            
        Returns:
            dict: AQL response with artifact data for requested artifacts only
        """
        try:
            if not artifact_paths:
                logger.warning("No artifact paths provided for specific AQL query")
                return {}
            
            logger.info("Querying AQL for %d specific artifacts in repository: %s", 
                       len(artifact_paths), repo_name)
            
            # Build $or conditions for each artifact path
            or_conditions = []
            for path, name in artifact_paths:
                or_conditions.append(f'{{"path": {{"$eq": "{path}"}}, "name": {{"$eq": "{name}"}}}}')
            
            or_clause = ', '.join(or_conditions)
            
            # Build AQL query with $or operator
            aql_query = f'items.find({{"repo": {{"$eq": "{repo_name}"}}, "$or": [{or_clause}]}}).include("property")'
            
            logger.debug("AQL query: %s", aql_query)
            
            # Build the API endpoint
            url = f"{self.base_url}/artifactory/api/search/aql"
            
            # Make the API request
            response = requests.post(
                url,
                headers={**self.headers, 'Content-Type': 'text/plain'},
                data=aql_query,
                timeout=60
            )
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully queried %d specific artifacts for %s: %d results found", 
                           len(artifact_paths), repo_name, len(data.get('results', [])))
                return data
            else:
                logger.error("Failed to query specific AQL artifacts for %s: %s", 
                           repo_name, response.status_code)
                return {}
                
        except (requests.RequestException, ValueError) as e:
            logger.error("Error querying specific AQL artifacts for %s: %s", repo_name, str(e))
            return {}
    


import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ArtifactParser:
    """
    Handles artifact path parsing and repository classification.
    Extracted from Product class to follow service layer pattern.
    """
    
    @staticmethod
    def parse_artifact_path(artifact_key: str) -> Optional[tuple]:
        """
        Parse artifact path into components
        
        Args:
            artifact_key (str): Full artifact path like 'cyberint-docker-local/staging/alert-status-update-handler/e9f884d22bfbcff6cb2e91a68815c4b07581e24c/manifest.json'
            
        Returns:
            Optional[tuple]: (repo_name, path, name, full_path) or None if malformed
        """
        try:
            # Split by '/' to get components
            parts = artifact_key.split('/')
            
            if len(parts) < 2:
                return None
            
            repo_name = parts[0]  # First part is repo name
            name = parts[-1]      # Last part is artifact name
            
            # Path is everything between repo and name (without leading/trailing slashes)
            if len(parts) > 2:
                path = '/'.join(parts[1:-1])
            else:
                path = ""
            
            return repo_name, path, name, artifact_key
            
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def is_local_repo(repo_name: str) -> bool:
        """
        Check if repository is local (contains "local" after last '-')
        
        Args:
            repo_name (str): Repository name
            
        Returns:
            bool: True if local repository
        """
        try:
            # Find the last '-' in the repo name
            last_dash_index = repo_name.rfind('-')
            if last_dash_index == -1:
                return False
            
            # Check if everything after the last '-' contains "local"
            suffix = repo_name[last_dash_index + 1:]
            return 'local' in suffix
            
        except (ValueError, IndexError):
            return False
    
    @staticmethod
    def match_build_name_to_repo(build_name: str, repo_build_names_map: dict) -> Optional[str]:
        """
        Match build name to repository
        
        Args:
            build_name (str): Build name from AQL
            repo_build_names_map (dict): Repository to build names mapping
            
        Returns:
            Optional[str]: First matching repository name or None
        """
        try:
            for repo_name, build_names_set in repo_build_names_map.items():
                if build_name in build_names_set:
                    return repo_name
            
            return None
            
        except (ValueError, KeyError) as e:
            logger.debug("Error matching build name '%s' to repository: %s", build_name, str(e))
            return None

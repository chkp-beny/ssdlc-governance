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
from .vulnerabilities import Vulnerabilities
import json

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
    
    def _parse_artifact_path(self, artifact_key: str) -> Optional[tuple]:
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
    
    def _is_local_repo(self, repo_name: str) -> bool:
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
    
    def _load_aql_cache(self, cache_file_path: str) -> Optional[dict]:
        """
        Load AQL cache from file
        
        Args:
            cache_file_path (str): Path to cache file
            
        Returns:
            Optional[dict]: AQL data or None if not found/invalid
        """
        try:
            if not os.path.exists(cache_file_path):
                return None
            
            with open(cache_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except (OSError, ValueError, KeyError) as e:
            logger.warning("Failed to load AQL cache from %s: %s", cache_file_path, str(e))
            return None
    
    def _extract_artifact_build_info_from_aql(self, aql_data: dict, path: str, name: str) -> Optional[tuple]:
        """
        Extract build info (name, number, timestamp, sha256) for artifact in AQL data
        
        Args:
            aql_data (dict): AQL response data
            path (str): Artifact path
            name (str): Artifact name
            
        Returns:
            Optional[tuple]: (build_name, build_number, build_timestamp, sha256) or None if not found
        """
        try:
            results = aql_data.get('results', [])
            for result in results:
                if result.get('path') == path and result.get('name') == name:
                    build_name = None
                    build_number = None
                    build_timestamp = None
                    sha256 = None
                    properties = result.get('properties', [])
                    for prop in properties:
                        if prop.get('key') == 'build.name':
                            build_name_value = prop.get('value')
                            if build_name_value:
                                if '/' in build_name_value:
                                    parts = build_name_value.split('/')
                                    if len(parts) >= 2:
                                        build_name = parts[1]
                                    else:
                                        build_name = parts[0]
                                else:
                                    build_name = build_name_value
                        elif prop.get('key') == 'build.number':
                            build_number = prop.get('value')
                        elif prop.get('key') == 'build.timestamp':
                            build_timestamp = prop.get('value')
                        elif prop.get('key') == 'sha256':
                            sha256 = prop.get('value')
                    return build_name, build_number, build_timestamp, sha256
            return None
        except (ValueError, KeyError, IndexError) as e:
            logger.debug("Error extracting build info in AQL data: %s", str(e))
            return None
    
    def _match_build_name_to_repo(self, build_name: str, repo_build_names_map: dict) -> Optional[str]:
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
    
    def _create_deployed_artifact(self, artifact_key: str, repo_name: str, vulnerabilities: dict, 
                                updated_at: str, build_name: str, jfrog_path: str, build_number=None, build_timestamp=None, sha256=None):
        """
        Create DeployedArtifact object from vulnerability data
        
        Args:
            artifact_key (str): Full artifact key
            repo_name (str): Repository name
            vulnerabilities (dict): Vulnerability counts
            updated_at (str): Last updated timestamp
            build_name (str): Build name
            jfrog_path (str): Full JFrog path
            build_number (str, optional): Build number from AQL properties
            build_timestamp (str, optional): Build timestamp from AQL properties
            sha256 (str, optional): sha256 from AQL properties
            
        Returns:
            DeployedArtifact: Created artifact object
        """
        from .vulnerabilities import DeployedArtifact
        
        # Extract vulnerability counts
        critical_count = vulnerabilities.get('critical', 0)
        high_count = vulnerabilities.get('high', 0)
        medium_count = vulnerabilities.get('medium', 0)
        low_count = vulnerabilities.get('low', 0)
        unknown_count = vulnerabilities.get('unknown', 0)
        
        return DeployedArtifact(
            artifact_key=artifact_key,
            repo_name=repo_name,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            unknown_count=unknown_count,
            build_name=build_name,
            updated_at=updated_at,
            jfrog_path=jfrog_path,
            build_number=build_number,
            build_timestamp=build_timestamp,
            sha256=sha256
        )
    
    def _fetch_missing_artifacts_from_aql(self, missing_artifacts_by_repo: dict, jfrog_client,
                                        aql_cache_dir: str, repo_build_names_map: dict,
                                        jfrog_vulnerabilities: dict, artifacts_by_repo: dict):
        """
        Fetch missing artifacts from AQL API and update cache using optimized approach.
        Uses specific artifact queries when cache exists, full refresh when cache is missing.
        """
        for repo_name, missing_paths in missing_artifacts_by_repo.items():
            try:
                cache_file = os.path.join(aql_cache_dir, f"{repo_name}.json")
                cache_exists = os.path.exists(cache_file)
                
                logger.info("🔍 Processing repository '%s' (%d artifacts need processing)", 
                           repo_name, len(missing_paths))

                if not cache_exists:
                    # No cache exists - do full repository query
                    logger.info("No cache found for repository '%s', performing full repository query", repo_name)
                    aql_response = jfrog_client.query_aql_artifacts(repo_name)
                    
                    if not aql_response or not aql_response.get('results'):
                        logger.warning("No AQL data returned for repository '%s'", repo_name)
                        continue

                    # Cache the AQL response (create new cache)
                    try:
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(aql_response, f, indent=2)
                        logger.info("💾 Created AQL cache for repository '%s' (%d artifacts in cache)", 
                                   repo_name, len(aql_response.get('results', [])))
                    except (OSError, ValueError) as e:
                        logger.warning("Failed to cache AQL data for repository '%s': %s", repo_name, str(e))
                        
                else:
                    # Cache exists - use optimized specific artifact query
                    logger.info("Cache exists for repository '%s', using optimized specific artifact query", repo_name)
                    
                    # Parse missing paths into (path, name) tuples
                    artifact_paths = []
                    for missing_path in missing_paths:
                        path_parts = missing_path.split('/')
                        if len(path_parts) < 2:
                            continue
                        name = path_parts[-1]
                        path = '/'.join(path_parts[1:-1]) if len(path_parts) > 2 else ""
                        artifact_paths.append((path, name))
                    
                    if not artifact_paths:
                        logger.warning("No valid artifact paths found for repository '%s'", repo_name)
                        continue
                    
                    # Query only specific missing artifacts
                    specific_aql_response = jfrog_client.query_aql_specific_artifacts(repo_name, artifact_paths)
                    
                    if not specific_aql_response or not specific_aql_response.get('results'):
                        logger.warning("No specific AQL data returned for repository '%s'", repo_name)
                        continue
                    
                    # Load existing cache
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            existing_cache = json.load(f)
                    except (OSError, ValueError) as e:
                        logger.warning("Failed to load existing cache for repository '%s': %s", repo_name, str(e))
                        # Fallback to full query if cache is corrupted
                        logger.info("Falling back to full repository query due to cache corruption")
                        aql_response = jfrog_client.query_aql_artifacts(repo_name)
                        if not aql_response or not aql_response.get('results'):
                            logger.warning("No AQL data returned for repository '%s'", repo_name)
                            continue
                        existing_cache = aql_response
                    
                    # Merge new results with existing cache
                    existing_results = existing_cache.get('results', [])
                    new_results = specific_aql_response.get('results', [])
                    
                    # Create a set of existing artifacts for deduplication (path + name combination)
                    existing_artifacts = set()
                    for result in existing_results:
                        key = (result.get('path', ''), result.get('name', ''))
                        existing_artifacts.add(key)
                    
                    # Add new results that don't already exist
                    added_count = 0
                    for new_result in new_results:
                        key = (new_result.get('path', ''), new_result.get('name', ''))
                        if key not in existing_artifacts:
                            existing_results.append(new_result)
                            existing_artifacts.add(key)
                            added_count += 1
                    
                    # Update the cache with merged results
                    merged_cache = {
                        'results': existing_results,
                        'range': {
                            'start_pos': 0,
                            'end_pos': len(existing_results),
                            'total': len(existing_results)
                        }
                    }
                    
                    # Save updated cache
                    try:
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(merged_cache, f, indent=2)
                        logger.info("💾 Updated AQL cache for repository '%s' (added %d new artifacts, total: %d)", 
                                   repo_name, added_count, len(existing_results))
                    except (OSError, ValueError) as e:
                        logger.warning("Failed to update cache for repository '%s': %s", repo_name, str(e))
                    
                    # Use merged cache for processing
                    aql_response = merged_cache

                # Process missing artifacts with the new AQL data
                processed_count = 0
                matched_count = 0

                for artifact_path in missing_paths:
                    processed_count += 1
                    try:
                        # Parse the artifact path
                        path_parts = artifact_path.split('/')
                        if len(path_parts) < 2:
                            continue

                        name = path_parts[-1]
                        path = '/'.join(path_parts[1:-1]) if len(path_parts) > 2 else ""

                        # Find build name in AQL data
                        build_info = self._extract_artifact_build_info_from_aql(aql_response, path, name)

                        if not build_info:
                            logger.debug("No build name found for artifact: %s", artifact_path)
                            continue

                        # Skip if build name is already known to be unmapped
                        if build_info[0] in self.unmapped_build_names:
                            logger.debug("Skipping build name '%s' as it is already known to be unmapped", build_info[0])
                            continue

                        # Match build name to repository
                        repo = self.build_name_to_repo_map.get(build_info[0])
                        if not repo:
                            logger.warning("❌ Build name '%s' from artifact '%s' not found in any repository's matched build names", 
                                         build_info[0], artifact_path)
                            self.unmapped_build_names.add(build_info[0])  # Add to unmapped list
                            continue

                        # Find the original artifact key and vulnerability data
                        original_artifact_key = None
                        for artifact_key in jfrog_vulnerabilities.keys():
                            if artifact_path in artifact_key:
                                original_artifact_key = artifact_key
                                break

                        if not original_artifact_key:
                            logger.debug("Original artifact key not found for path: %s", artifact_path)
                            continue

                        # Get vulnerability data
                        vuln_data = jfrog_vulnerabilities[original_artifact_key]
                        vulnerabilities = vuln_data.get('vulnerabilities', {})
                        updated_at = vuln_data.get('updated_at')

                        # Create DeployedArtifact
                        deployed_artifact = self._create_deployed_artifact(
                            original_artifact_key, repo, vulnerabilities, 
                            updated_at, build_info[0], artifact_path
                        )

                        # Add to artifacts by repo
                        if repo not in artifacts_by_repo:
                            artifacts_by_repo[repo] = []
                        artifacts_by_repo[repo].append(deployed_artifact)

                        matched_count += 1
                        logger.debug("✅ Processed missing artifact '%s' for repo '%s'", 
                                   original_artifact_key, repo)

                    except (ValueError, KeyError) as e:
                        logger.error("❌ Error processing missing artifact '%s': %s", artifact_path, str(e))
                        continue

                # Log summary for this repository
                logger.info("📊 Repository '%s' cache refresh: %d/%d artifacts successfully processed", 
                           repo_name, matched_count, processed_count)

            except (ValueError, KeyError, OSError) as e:
                logger.error("❌ Error fetching AQL data for repository '%s': %s", repo_name, str(e))
                continue
    
    def _update_repository_vulnerabilities(self, artifacts_by_repo: dict) -> int:
        """
        Update repository vulnerabilities with deployed artifacts
        
        Args:
            artifacts_by_repo (dict): Dictionary with repository objects as keys and artifact lists as values
            
        Returns:
            int: Number of repositories updated
        """
        updated_count = 0
        
        for repo, artifacts in artifacts_by_repo.items():
            try:
                # repo is already a repository object, not a name
                repo_name = repo.scm_info.repo_name if repo.scm_info else "unknown"
                
                # Initialize vulnerabilities if not already initialized
                if repo.vulnerabilities is None:
                    repo.vulnerabilities = Vulnerabilities()
                
                # Create or update DependenciesVulnerabilities
                from .vulnerabilities import DependenciesVulnerabilities
                
                if repo.vulnerabilities.dependencies_vulns is None:
                    repo.vulnerabilities.dependencies_vulns = DependenciesVulnerabilities()
                
                # Add all artifacts to the dependencies vulnerabilities
                for artifact in artifacts:
                    repo.vulnerabilities.dependencies_vulns.add_artifact(artifact)
                
                updated_count += 1
                
                logger.info("✅ Updated vulnerabilities for repo '%s' with %d artifacts", 
                           repo_name, len(artifacts))
                
            except (ValueError, KeyError) as e:
                repo_name = repo.scm_info.repo_name if repo.scm_info else "unknown"
                logger.error("❌ Error updating vulnerabilities for repo '%s': %s", repo_name, str(e))
                continue
        
        return updated_count
    
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

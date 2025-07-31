import os
import logging
from .artifact_parser import ArtifactParser
from .aql_cache_manager import AqlCacheManager
from .deployed_artifact_processor import DeployedArtifactProcessor

logger = logging.getLogger(__name__)


class ArtifactCoordinator:
    """
    Coordinates artifact processing including AQL queries, caching, and vulnerability updates.
    Extracted from Product class to follow service layer pattern.
    """
    
    def __init__(self, product_name: str):
        """
        Initialize artifact coordinator.
        
        Args:
            product_name: Name of the product
        """
        self.product_name = product_name
        self.parser = ArtifactParser()
        self.cache_manager = AqlCacheManager()
        self.artifact_processor = DeployedArtifactProcessor()
    
    def fetch_missing_artifacts_from_aql(self, missing_artifacts_by_repo: dict, jfrog_client,
                                       aql_cache_dir: str, build_name_to_repo_map: dict,
                                       unmapped_build_names: set, jfrog_vulnerabilities: dict, 
                                       artifacts_by_repo: dict):
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
                    if self.cache_manager.save_aql_cache(cache_file, aql_response):
                        logger.info("💾 Created AQL cache for repository '%s' (%d artifacts in cache)", 
                                   repo_name, len(aql_response.get('results', [])))
                        
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
                    existing_cache = self.cache_manager.load_aql_cache(cache_file)
                    if not existing_cache:
                        logger.warning("Failed to load existing cache for repository '%s'", repo_name)
                        # Fallback to full query if cache is corrupted
                        logger.info("Falling back to full repository query due to cache corruption")
                        aql_response = jfrog_client.query_aql_artifacts(repo_name)
                        if not aql_response or not aql_response.get('results'):
                            logger.warning("No AQL data returned for repository '%s'", repo_name)
                            continue
                        # Use the fallback response directly
                    else:
                        # Merge new results with existing cache
                        merged_cache = self.cache_manager.merge_aql_caches(existing_cache, specific_aql_response)
                        added_count = merged_cache.pop('added_count', 0)
                        
                        # Save updated cache
                        if self.cache_manager.save_aql_cache(cache_file, merged_cache):
                            logger.info("💾 Updated AQL cache for repository '%s' (added %d new artifacts, total: %d)", 
                                       repo_name, added_count, len(merged_cache.get('results', [])))
                        
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
                        build_info = self.cache_manager.extract_artifact_build_info_from_aql(aql_response, path, name)

                        if not build_info:
                            logger.debug("No build name found for artifact: %s", artifact_path)
                            continue

                        # Skip if build name is already known to be unmapped
                        if build_info[0] in unmapped_build_names:
                            logger.debug("Skipping build name '%s' as it is already known to be unmapped", build_info[0])
                            continue

                        # Match build name to repository
                        repo = build_name_to_repo_map.get(build_info[0])
                        if not repo:
                            logger.warning("❌ Build name '%s' from artifact '%s' not found in any repository's matched build names", 
                                         build_info[0], artifact_path)
                            unmapped_build_names.add(build_info[0])  # Add to unmapped list
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
                        deployed_artifact = self.artifact_processor.create_deployed_artifact(
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

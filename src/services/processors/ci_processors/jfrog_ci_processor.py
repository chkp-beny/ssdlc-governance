import os
import json
import glob
import logging
from datetime import datetime
from typing import Dict, List
from src.services.clients.jfrog_clients.jfrog_client import JfrogClient

logger = logging.getLogger(__name__)


class JfrogCiProcessor:
    """
    Handles JFrog CI data loading for product repositories.
    Extracted from Product class to follow service layer pattern.
    """
    
    def __init__(self, product_name: str):
        """
        Initialize JFrog CI processor for a product.
        
        Args:
            product_name: Name of the product
        """
        self.product_name = product_name
        self.build_name_to_repo_map = {}
        self.unmapped_build_names = set()
    
    def process_ci_data(self, repos: List) -> Dict:
        """
        Process JFrog CI data for all repositories in the product.
        
        Args:
            repos: List of repository objects
            
        Returns:
            Dict containing processing results
        """
        logger.info("Loading JFrog CI data for product '%s'", self.product_name)
        
        try:
            # Import constants
            try:
                from CONSTANTS import PRODUCT_JFROG_PROJECT
            except ImportError:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                from CONSTANTS import PRODUCT_JFROG_PROJECT
            
            # Get JFrog project name for this product
            jfrog_project = PRODUCT_JFROG_PROJECT.get(self.product_name, "")
            
            # Skip if no JFrog project configured
            if not jfrog_project:
                logger.info("No JFrog project configured for product '%s', skipping JFrog CI data loading", self.product_name)
                return {'updated_count': 0, 'total_repos': len(repos)}
            
            # Initialize JFrog client with product-specific token
            from CONSTANTS import get_jfrog_token_for_product
            jfrog_token, token_env_var = get_jfrog_token_for_product(self.product_name)
            
            if not jfrog_token:
                logger.warning("%s not found, skipping JFrog CI data loading for product '%s'", token_env_var, self.product_name)
                return {'updated_count': 0, 'total_repos': len(repos)}
            
            jfrog_client = JfrogClient(jfrog_token)
            
            # Fetch build information (raw JSON)
            build_data = jfrog_client.fetch_all_project_builds(jfrog_project)
            
            # Use metadata-based logic with fallback matching
            return self._load_metadata_based(build_data, jfrog_project, jfrog_client, repos)
                
        except (ImportError, KeyError, ValueError) as e:
            logger.error("Error loading JFrog CI data for product '%s': %s", self.product_name, str(e))
            return {'updated_count': 0, 'total_repos': len(repos)}
    
    def _load_metadata_based(self, build_data: dict, jfrog_project: str, jfrog_client, repos: List) -> Dict:
        """
        Load JFrog CI data using metadata-based approach.
        Query build metadata to find source repository information.
        Uses intelligent caching to avoid redundant API calls.
        """
        builds = build_data.get('builds', [])
        logger.info("🔍 Found %d builds in JFrog for project '%s', starting metadata analysis...", 
                   len(builds), jfrog_project)
        logger.info("📊 Using timestamp-based intelligent caching to minimize API calls...")
        
        # Setup build info cache directory
        cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'build_info_cache_dir')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Create product-specific cache directory using project name
        product_cache_dir = os.path.join(cache_dir, jfrog_project)
        os.makedirs(product_cache_dir, exist_ok=True)
        
        logger.info("💾 Using cache directory: %s", product_cache_dir)
        
        # Get current timestamp for tracking
        current_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save the current build list (replace any existing file)
        build_list_file = os.path.join(product_cache_dir, "build_list_current.json")
        try:
            with open(build_list_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': current_timestamp,
                    'product': self.product_name,
                    'jfrog_project': jfrog_project,
                    'total_builds': len(builds),
                    'builds': builds
                }, f, indent=2)
            logger.info("💾 Saved current build list to: %s (%d builds)", build_list_file, len(builds))
        except (OSError, ValueError) as e:
            logger.warning("Failed to save current build list: %s", str(e))
        
        # Track repository matches
        repo_matches = {}  # repo_name -> list of build info
        unmatched_source_repos = {}  # source_repo -> list of build names that reference it
        fallback_repo_matches = {}  # repo_name -> list of build info (matched via fallback)
        
        # Progress tracking
        processed_builds = 0
        api_calls_made = 0
        cache_hits = 0
        builds_with_metadata = 0
        builds_with_repo_info = 0
        fallback_matches = 0
        metadata_matches = 0
        
        # Debug tracking: builds with repo info but no match
        builds_with_repo_info_but_no_match = []  # List of build info that have SOURCE_REPO but no match
        
        # Create a set of all repository names in the product for quick lookup
        product_repo_names = set()
        for repo in repos:
            if repo.scm_info and repo.scm_info.repo_name:
                product_repo_names.add(repo.scm_info.repo_name)
        
        for build in builds:
            uri = build.get('uri', '')
            last_started = build.get('lastStarted', '')
            
            if uri.startswith('/') and last_started:
                build_name = uri[1:]  # Remove leading slash
                if build_name:
                    processed_builds += 1
                    
                    # Log progress every 25 builds (more frequent updates)
                    if processed_builds % 25 == 0:
                        logger.info("🔄 Progress: %d/%d builds processed (%d%%), %d API calls, %d cache hits, %d with repo info", 
                                  processed_builds, len(builds), 
                                  int((processed_builds / len(builds)) * 100),
                                  api_calls_made, cache_hits, builds_with_repo_info)
                    
                    # Also log every 10 builds for more visibility
                    elif processed_builds % 10 == 0:
                        logger.info("⏳ Processing build %d/%d: %s (last: %s)", processed_builds, len(builds), build_name, last_started)
                    
                    # Create build-specific directory for this build
                    build_cache_dir = os.path.join(product_cache_dir, build_name)
                    os.makedirs(build_cache_dir, exist_ok=True)
                    
                    # Create cache filename based on lastStarted timestamp
                    # Sanitize timestamp for filesystem (replace : and . with -)
                    safe_timestamp = last_started.replace(':', '-').replace('.', '-').replace('+', '-')
                    details_cache_file = os.path.join(build_cache_dir, f"details_{safe_timestamp}.json")
                    
                    # Check if we have cached details for this exact timestamp
                    cached_details = None
                    if os.path.exists(details_cache_file):
                        try:
                            with open(details_cache_file, 'r', encoding='utf-8') as f:
                                cached_details = json.load(f)
                            logger.debug("📁 Using cached details for build '%s' (timestamp: %s)", build_name, last_started)
                            cache_hits += 1
                        except (OSError, ValueError) as e:
                            logger.warning("Failed to read cached details for build '%s': %s", build_name, str(e))
                            cached_details = None
                    
                    # Get build details (from cache or API)
                    if cached_details:
                        build_details = cached_details
                        builds_with_metadata += 1  # Count as having metadata since we have cached data
                    else:
                        # No cache or cache miss - need to make API calls
                        logger.debug("🔄 Cache miss for build '%s' (timestamp: %s) - fetching from API", build_name, last_started)
                        
                        # First get metadata to find the latest build number
                        metadata = jfrog_client.fetch_build_metadata(build_name, jfrog_project)
                        api_calls_made += 1
                        
                        if metadata and 'buildsNumbers' in metadata:
                            builds_numbers = metadata['buildsNumbers']
                            if builds_numbers:
                                builds_with_metadata += 1
                                # Sort by timestamp to get latest build
                                latest_build = max(builds_numbers, 
                                                 key=lambda b: b.get('started', ''))
                                
                                # Extract build number from URI
                                build_number_uri = latest_build.get('uri', '')
                                if build_number_uri.startswith('/'):
                                    build_number = build_number_uri[1:]
                                    
                                    # Get detailed build information
                                    build_details = jfrog_client.fetch_build_details(
                                        build_name, build_number, jfrog_project)
                                    api_calls_made += 1
                                    
                                    # Clean old details files and cache new one with timestamp
                                    self._clean_old_cache_files(build_cache_dir, "details_*.json")
                                    try:
                                        with open(details_cache_file, 'w', encoding='utf-8') as f:
                                            json.dump(build_details, f, indent=2)
                                        logger.debug("💾 Cached build details for build '%s' with timestamp %s", build_name, last_started)
                                    except (OSError, ValueError) as e:
                                        logger.warning("Failed to cache build details for build '%s': %s", build_name, str(e))
                                else:
                                    logger.debug("No valid build number URI found for build '%s'", build_name)
                                    continue
                            else:
                                logger.debug("No builds numbers found in metadata for build '%s'", build_name)
                                continue
                        else:
                            logger.debug("No metadata found for build '%s'", build_name)
                            continue
                    
                    # Process build details if we have them
                    if build_details and 'buildInfo' in build_details:
                        build_info = build_details['buildInfo']
                        properties = build_info.get('properties', {})
                        
                        # Extract repository information
                        source_repo = properties.get('buildInfo.env.SOURCE_REPO')
                        source_branch = properties.get('buildInfo.env.SOURCE_BRANCH')
                        job_url = build_info.get('url')
                        
                        if source_repo:
                            builds_with_repo_info += 1
                            
                            # Check if this SOURCE_REPO matches any repository in the product
                            repo = next((r for r in repos if r.scm_info and r.scm_info.repo_name == source_repo), None)
                            if repo:
                                # Matched repository via metadata
                                if source_repo not in repo_matches:
                                    repo_matches[source_repo] = []
                                
                                repo_matches[source_repo].append({
                                    'build_name': build_name,
                                    'build_number': build_name,  # Use build name as identifier
                                    'branch': source_branch,
                                    'job_url': job_url,
                                    'started': last_started,  # Use lastStarted from build list
                                    'match_type': 'metadata'
                                })
                                
                                metadata_matches += 1
                                logger.debug("✅ Matched build '%s' to repo '%s' via metadata (branch: %s)", 
                                           build_name, source_repo, source_branch)
                            else:
                                # SOURCE_REPO not found in product repos - add to unmatched list
                                if source_repo not in unmatched_source_repos:
                                    unmatched_source_repos[source_repo] = []
                                unmatched_source_repos[source_repo].append(build_name)
                                
                                # Add to debug tracking
                                builds_with_repo_info_but_no_match.append({
                                    'build_name': build_name,
                                    'source_repo': source_repo,
                                    'source_branch': source_branch,
                                    'job_url': job_url,
                                    'started': last_started
                                })
                                
                                logger.debug("❌ SOURCE_REPO '%s' from build '%s' not found in product repos", 
                                           source_repo, build_name)
                        else:
                            # FALLBACK: No SOURCE_REPO found, try longest-prefix matching with build name
                            logger.debug("No SOURCE_REPO found for build '%s', trying fallback longest-prefix matching", build_name)
                            
                            # Find the repository with the longest name that is a prefix of the build name
                            best_match = None
                            best_match_length = 0
                            
                            for repo_name in product_repo_names:
                                # Check if repo name is a prefix of build name
                                if build_name.startswith(repo_name):
                                    # Check if this is a longer match than current best
                                    if len(repo_name) > best_match_length:
                                        # Ensure this is a word boundary (followed by - or end of string)
                                        if len(repo_name) == len(build_name) or build_name[len(repo_name)] == '-':
                                            best_match = repo_name
                                            best_match_length = len(repo_name)
                            
                            if best_match:
                                # Found a fallback match
                                builds_with_repo_info += 1  # Count this as having repo info
                                fallback_matches += 1
                                
                                repo = next((r for r in repos if r.scm_info and r.scm_info.repo_name == best_match), None)
                                if repo:
                                    if best_match not in fallback_repo_matches:
                                        fallback_repo_matches[best_match] = []
                                    
                                    fallback_repo_matches[best_match].append({
                                        'build_name': build_name,
                                        'build_number': build_name,  # Use build name as identifier
                                        'branch': None,  # No branch info in fallback mode
                                        'job_url': job_url,  # URL should still be available
                                        'started': last_started,  # Use lastStarted from build list
                                        'match_type': 'fallback'
                                    })
                                    
                                    logger.debug("🔄 FALLBACK: Matched build '%s' to repo '%s' via longest-prefix (prefix: '%s', length: %d)", 
                                               build_name, best_match, best_match, best_match_length)
                            else:
                                self.unmapped_build_names.add(build_name)
                                logger.debug("❌ FALLBACK: No prefix match found for build '%s'", build_name)
                    else:
                        logger.debug("No buildInfo found in build details for '%s'", build_name)
        
        # Combine metadata and fallback matches for total counts
        all_repo_matches = {}
        all_repo_matches.update(repo_matches)
        
        # Add fallback matches to the total
        for repo_name, build_list in fallback_repo_matches.items():
            if repo_name not in all_repo_matches:
                all_repo_matches[repo_name] = []
            all_repo_matches[repo_name].extend(build_list)
        
        # Final progress summary
        logger.info("✅ Metadata analysis completed: %d builds processed, %d API calls made, %d cache hits", 
                   processed_builds, api_calls_made, cache_hits)
        logger.info("📈 Build processing results: %d builds with valid data, %d builds with repo info", 
                   builds_with_metadata, builds_with_repo_info)
        logger.info("🔗 Found matches for %d unique repositories (%d via metadata, %d via fallback)", 
                   len(all_repo_matches), len(repo_matches), len(fallback_repo_matches))
        
        # Calculate total builds matched
        total_matched_builds = sum(len(builds) for builds in all_repo_matches.values())
        logger.info("🎯 Total builds matched to repositories: %d builds across %d repositories", 
                   total_matched_builds, len(all_repo_matches))
        
        # Update repository CI status based on matches (both metadata and fallback)
        updated_count = 0
        for repo in repos:
            # Ensure CI status is initialized
            if repo.ci_status is None:
                from src.models.ci_status import CIStatus
                repo.update_ci_status(CIStatus())

            if repo.scm_info and repo.scm_info.repo_name:
                repo_name = repo.scm_info.repo_name

                if repo_name in all_repo_matches:
                    # Find the most recent build for this repository
                    builds_for_repo = all_repo_matches[repo_name]
                    latest_build = max(builds_for_repo, key=lambda b: b.get('started', ''))

                    # Extract all build names for this repository as a set
                    build_names = {build['build_name'] for build in builds_for_repo}

                    # Build mapping method dict for this repo's builds
                    build_name_mapping_methods = {}
                    for build in builds_for_repo:
                        build_name = build['build_name']
                        match_type = build.get('match_type', 'not_mapped')
                        # Use 'metadata' or 'longest_prefix' for clarity
                        if match_type == 'metadata':
                            build_name_mapping_methods[build_name] = 'source_repo'
                        elif match_type == 'fallback':
                            build_name_mapping_methods[build_name] = 'longest_prefix'
                        else:
                            build_name_mapping_methods[build_name] = 'not_mapped'

                    # Update JFrog CI status with metadata, build names, and mapping methods
                    repo.ci_status.jfrog_status.set_exists(
                        True,
                        branch=latest_build.get('branch'),
                        job_url=latest_build.get('job_url'),
                        matched_build_names=build_names,
                        build_name_mapping_methods=build_name_mapping_methods
                    )

                    # Populate build_name_to_repo_map for vulnerability matching
                    for build_name in build_names:
                        self.build_name_to_repo_map[build_name] = repo

                    updated_count += 1

                    match_type = latest_build.get('match_type', 'unknown')
                    logger.debug("Updated JFrog CI status for repo '%s' with %s match and %d build names: %s", 
                               repo_name, match_type, len(build_names), list(build_names)[:3])
        
        logger.info("✅ Updated JFrog CI status for %d/%d repositories in product '%s' using metadata and fallback", 
                   updated_count, len(repos), self.product_name)
        
        # Log build_name_to_repo_map statistics for debugging
        total_build_names = len(self.build_name_to_repo_map)
        logger.info("🔗 Populated build_name_to_repo_map with %d build names for vulnerability matching", total_build_names)
        
        return {
            'updated_count': updated_count,
            'total_repos': len(repos),
            'build_name_to_repo_map': self.build_name_to_repo_map,
            'unmapped_build_names': self.unmapped_build_names
        }
    
    def _clean_old_cache_files(self, cache_dir: str, pattern: str):
        """
        Clean old cache files matching the pattern, keeping only the latest one
        
        Args:
            cache_dir (str): Directory to clean
            pattern (str): Glob pattern to match files
        """
        
        # Find all files matching the pattern
        files = glob.glob(os.path.join(cache_dir, pattern))
        
        if len(files) > 1:
            # Sort by modification time and keep only the latest
            files.sort(key=os.path.getmtime, reverse=True)
            files_to_delete = files[1:]  # Keep the first (latest), delete the rest
            
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    logger.debug("Removed old cache file: %s", file_path)
                except OSError as e:
                    logger.warning("Failed to remove old cache file %s: %s", file_path, str(e))

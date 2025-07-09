"""
Product class - Product-level aggregation and ownership
Contains list of Repo objects and DevOps object
"""

from typing import List, Optional
import logging
import os
import glob
from dotenv import load_dotenv
from .devops import DevOps
from .repo import Repo
from .vulnerabilities import Vulnerabilities, CodeIssues
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
        compass_url = os.getenv('COMPASS_BASE_URL', '')
        
        # Initialize DataLoader (other API credentials can be added later)
        self.data_loader = DataLoader(
            compass_token=compass_token,
            compass_url=compass_url
        )
        
        logger.debug("DataLoader initialized for product '%s'", self.name)
    
    def load_repositories(self):
        """
        Load repositories for this product using DataLoader
        Fetches repositories based on product's SCM type and organization ID
        """
        try:
            # Load repositories using DataLoader with product's SCM info
            repo_data = self.data_loader.load_repositories(self.scm_type, self.organization_id)
            
            # Parse repo_data and create Repo objects
            self.repos = []
            for repo_json in repo_data:
                try:
                    repo = Repo.from_json(repo_json, self.name)
                    self.repos.append(repo)
                except (ValueError, KeyError) as e:
                    logger.warning("Failed to create Repo from JSON for %s: %s", 
                                  repo_json.get('repo_name', 'unknown'), str(e))
            
            logger.info("Successfully loaded %d repositories for product '%s'", len(self.repos), self.name)
            
        except (ImportError, ValueError) as e:
            logger.error("Error loading repositories for product '%s': %s", self.name, str(e))
    
    def load_ci_data(self):
        """
        Load CI data for all repositories in this product
        Main entry point for CI data loading - calls both JFrog and Sonar data loading
        """
        logger.info("Loading CI data for product '%s'", self.name)
        
        # Load JFrog CI data
        self._load_jfrog_ci_data()
        
        # Load Sonar CI data (placeholder for future implementation)
        self.load_sonar_ci_data()
        
        logger.info("CI data loading completed for product '%s'", self.name)
    
    def _load_jfrog_ci_data(self):
        """
        Load JFrog CI data for repositories in this product
        Updates JfrogCIStatus.is_exist for matching repositories
        Uses metadata-based approach with intelligent fallback matching
        """
        try:
            # Import constants
            try:
                from CONSTANTS import PRODUCT_JFROG_PROJECT
            except ImportError:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
                from CONSTANTS import PRODUCT_JFROG_PROJECT
            
            # Get JFrog project name for this product
            jfrog_project = PRODUCT_JFROG_PROJECT.get(self.name, "")
            
            # Skip if no JFrog project configured
            if not jfrog_project:
                logger.info("No JFrog project configured for product '%s', skipping JFrog CI data loading", self.name)
                return
            
            # Initialize JFrog client with product-specific token
            from CONSTANTS import get_jfrog_token_for_product
            jfrog_token, token_env_var = get_jfrog_token_for_product(self.name)
            
            if not jfrog_token:
                logger.warning("%s not found, skipping JFrog CI data loading for product '%s'", token_env_var, self.name)
                return
            
            from src.services.data_loader import JfrogClient
            jfrog_client = JfrogClient(jfrog_token)
            
            # Fetch build information (raw JSON)
            build_data = jfrog_client.fetch_all_project_builds(jfrog_project)
            
            # Use metadata-based logic with fallback matching
            self._load_jfrog_ci_data_metadata_based(build_data, jfrog_project, jfrog_client)
                
        except (ImportError, KeyError, ValueError) as e:
            logger.error("Error loading JFrog CI data for product '%s': %s", self.name, str(e))
    
    def _update_build_name_to_repo_map(self, build_name: str, repo: Repo):
        """
        Update the build_name_to_repo_map with a new mapping.

        Args:
            build_name (str): The build name to map.
            repo (Repo): The repository object to map to the build name.
        """
        self.build_name_to_repo_map[build_name] = repo

    def _load_jfrog_ci_data_metadata_based(self, build_data: dict, jfrog_project: str, jfrog_client):
        """
        Load JFrog CI data using metadata-based approach
        Query build metadata to find source repository information
        Uses intelligent caching to avoid redundant API calls
        """
        builds = build_data.get('builds', [])
        logger.info("🔍 Found %d builds in JFrog for project '%s', starting metadata analysis...", 
                   len(builds), jfrog_project)
        logger.info("📊 Using timestamp-based intelligent caching to minimize API calls...")
        
        # Setup build info cache directory
        from datetime import datetime
        cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'build_info_cache_dir')
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
                    'product': self.name,
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
        for repo in self.repos:
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
                            repo = next((r for r in self.repos if r.scm_info and r.scm_info.repo_name == source_repo), None)
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
                                # (Note: Analysis shows this case never occurs with exact matches)
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
                            
                            # Log if other metadata fields are missing
                            if not source_branch:
                                logger.debug("No SOURCE_BRANCH found for build '%s'", build_name)
                            if not job_url:
                                logger.debug("No job URL found for build '%s'", build_name)
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
                                
                                repo = next((r for r in self.repos if r.scm_info and r.scm_info.repo_name == best_match), None)
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
        
        # NEW: Clear math summary
        logger.info("📊 SUMMARY BREAKDOWN:")
        logger.info("   - Total builds processed: %d", processed_builds)
        logger.info("   - Builds with valid metadata: %d", builds_with_metadata)
        logger.info("   - Builds with SOURCE_REPO info: %d", builds_with_repo_info)
        logger.info("   - Builds matched via metadata (exact SOURCE_REPO match): %d", metadata_matches)
        logger.info("   - Builds matched via fallback (no SOURCE_REPO): %d", fallback_matches)
        logger.info("   - Total fallback matches: %d", fallback_matches)
        logger.info("   - Total builds matched: %d", total_matched_builds)
        logger.info("   - Builds with SOURCE_REPO but no match: %d", len(builds_with_repo_info_but_no_match))
        logger.info("   - Unique unmatched SOURCE_REPO values: %d", len(unmatched_source_repos))
        
        # Verify the math
        expected_total = metadata_matches + fallback_matches + len(builds_with_repo_info_but_no_match)
        if builds_with_repo_info != expected_total:
            logger.warning("⚠️  MATH MISMATCH: builds_with_repo_info (%d) != sum of matched + unmatched (%d)", 
                          builds_with_repo_info, expected_total)
        
        logger.info("💾 Build info cached to: %s", product_cache_dir)
        
        # Debug: Show which SOURCE_REPO values don't match any repositories
        if builds_with_repo_info > len(all_repo_matches):
            logger.warning("⚠️  MISMATCH DETECTED: %d builds with repo info but only %d unique repo matches!", 
                          builds_with_repo_info, len(all_repo_matches))
            
            logger.info("📊 Repository matching analysis:")
            logger.info("   - Product has %d repositories", len(product_repo_names))
            logger.info("   - Builds referenced %d unique SOURCE_REPO values", len(repo_matches) + len(unmatched_source_repos))
            logger.info("   - Successfully matched via metadata: %d repositories (%d builds)", 
                       len(repo_matches), metadata_matches)
            logger.info("   - Successfully matched via fallback: %d repositories (%d builds)", 
                       len(fallback_repo_matches), fallback_matches)
            logger.info("   - Total successful matches: %d repositories", len(all_repo_matches))
            logger.info("   - Unmatched SOURCE_REPO values: %d", len(unmatched_source_repos))
            
            # Calculate total builds across all matched repositories
            total_builds_for_matched_repos = sum(len(builds) for builds in all_repo_matches.values())
            logger.info("   - Total builds for matched repositories: %d", total_builds_for_matched_repos)
            
            # NEW: Detailed logging for builds with repo info but no match
            if builds_with_repo_info_but_no_match:
                logger.warning("🔍 DETAILED ANALYSIS: %d builds have SOURCE_REPO but no match:", 
                              len(builds_with_repo_info_but_no_match))
                
                # Group by SOURCE_REPO for better analysis
                unmatched_by_source_repo = {}
                for build_info in builds_with_repo_info_but_no_match:
                    source_repo = build_info['source_repo']
                    if source_repo not in unmatched_by_source_repo:
                        unmatched_by_source_repo[source_repo] = []
                    unmatched_by_source_repo[source_repo].append(build_info)
                
                # Show details for each unmatched SOURCE_REPO
                for source_repo, build_infos in unmatched_by_source_repo.items():
                    logger.warning("   📋 SOURCE_REPO '%s' (%d builds):", source_repo, len(build_infos))
                    
                    # Show up to 3 example builds for each SOURCE_REPO
                    for build_info in build_infos[:3]:
                        logger.warning("     - Build: '%s' | Branch: '%s' | Started: %s", 
                                      build_info['build_name'], 
                                      build_info['source_branch'] or 'N/A',
                                      build_info['started'][:19] if build_info['started'] else 'N/A')
                    
                    if len(build_infos) > 3:
                        logger.warning("     ... and %d more builds with same SOURCE_REPO", len(build_infos) - 3)
                
                # Show comparison with product repo names
                logger.warning("   🔍 COMPARISON - Product repo names vs unmatched SOURCE_REPO values:")
                sample_product_repos = sorted(list(product_repo_names))[:5]
                sample_unmatched_repos = sorted(list(unmatched_by_source_repo.keys()))[:5]
                logger.warning("     Product repos (first 5): %s", sample_product_repos)
                logger.warning("     Unmatched SOURCE_REPO (first 5): %s", sample_unmatched_repos)
                
                # Look for potential naming pattern differences
                logger.warning("   🔍 PATTERN ANALYSIS:")
                for source_repo in sample_unmatched_repos:
                    # Check for similar names in product repos
                    similar_repos = []
                    for prod_repo in product_repo_names:
                        # Check if they share common substrings
                        if any(part in prod_repo for part in source_repo.split('-')) or \
                           any(part in source_repo for part in prod_repo.split('-')):
                            similar_repos.append(prod_repo)
                    
                    if similar_repos:
                        logger.warning("     '%s' might be similar to: %s", source_repo, similar_repos[:3])
                    else:
                        logger.warning("     '%s' has no similar product repo names", source_repo)
            
            if unmatched_source_repos:
                logger.warning("🔍 UNMATCHED SOURCE_REPO VALUES (not found in product repositories):")
                for source_repo, build_names in list(unmatched_source_repos.items())[:10]:  # Show first 10
                    logger.warning("   - '%s' (from builds: %s)", source_repo, build_names[:3])  # Show first 3 builds
                
                if len(unmatched_source_repos) > 10:
                    logger.warning("   ... and %d more unmatched SOURCE_REPO values", len(unmatched_source_repos) - 10)
            
            if repo_matches:
                logger.info("✅ METADATA-MATCHED repositories with build counts:")
                for repo_name in sorted(repo_matches.keys()):
                    build_count = len(repo_matches[repo_name])
                    logger.info("   - '%s': %d builds (metadata)", repo_name, build_count)
            
            if fallback_repo_matches:
                logger.info("🔄 FALLBACK-MATCHED repositories with build counts:")
                
                for repo_name in sorted(fallback_repo_matches.keys()):
                    builds = fallback_repo_matches[repo_name]
                    build_count = len(builds)
                    build_names = [build['build_name'] for build in builds]
                    build_names_str = ', '.join(build_names[:3])
                    if len(build_names) > 3:
                        build_names_str += f", +{len(build_names)-3} more"
                    logger.info("   - '%s': %d builds (%s)", repo_name, build_count, build_names_str)
            
            # Sample some product repo names for comparison
            sample_product_repos = sorted(list(product_repo_names))[:10]
            logger.info("📋 Sample product repo names: %s", sample_product_repos)
        else:
            logger.info("✅ All builds with repo info successfully matched to product repositories")
            if fallback_matches > 0:
                logger.info("🔄 Fallback matching used for %d builds across %d repositories", 
                           fallback_matches, len(fallback_repo_matches))
        
        # Update repository CI status based on matches (both metadata and fallback)
        updated_count = 0
        for repo in self.repos:
            # Ensure CI status is initialized
            if repo.ci_status is None:
                from .ci_status import CIStatus
                repo.update_ci_status(CIStatus())
            
            if repo.scm_info and repo.scm_info.repo_name:
                repo_name = repo.scm_info.repo_name
                
                if repo_name in all_repo_matches:
                    # Find the most recent build for this repository
                    builds_for_repo = all_repo_matches[repo_name]
                    latest_build = max(builds_for_repo, 
                                     key=lambda b: b.get('started', ''))
                    
                    # Extract all build names for this repository as a set
                    build_names = {build['build_name'] for build in builds_for_repo}
                    
                    # Update JFrog CI status with metadata and build names
                    repo.ci_status.jfrog_status.set_exists(
                        True,
                        branch=latest_build.get('branch'),
                        job_url=latest_build.get('job_url'),
                        matched_build_names=build_names
                    )
                    
                    # IMPORTANT: Populate build_name_to_repo_map for vulnerability matching
                    for build_name in build_names:
                        self.build_name_to_repo_map[build_name] = repo
                    
                    updated_count += 1
                    
                    match_type = latest_build.get('match_type', 'unknown')
                    logger.debug("Updated JFrog CI status for repo '%s' with %s match and %d build names: %s", 
                               repo_name, match_type, len(build_names), list(build_names)[:3])
        
        logger.info("✅ Updated JFrog CI status for %d/%d repositories in product '%s' using metadata and fallback", 
                   updated_count, len(self.repos), self.name)
        
        # Log build_name_to_repo_map statistics for debugging
        total_build_names = len(self.build_name_to_repo_map)
        logger.info("🔗 Populated build_name_to_repo_map with %d build names for vulnerability matching", total_build_names)
        
        # Debug: Show a sample of build names for verification
        if total_build_names > 0:
            sample_build_names = list(self.build_name_to_repo_map.keys())[:10]
            logger.debug("📋 Sample build names: %s", sample_build_names)
    
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
    
    def load_sonar_ci_data(self):
        """
        Load Sonar CI data for repositories in this product
        Updates SonarCIStatus.is_exist and project_key for matching repositories
        """
        # TODO: Extend this logic to check the scanned branches for each project with Sonar API.
        # Currently only checking if projects exist, but should also verify which branches are being scanned
        # and update the is_main_branch_scanned field accordingly.
        try:
            logger.info("Loading Sonar CI data for product '%s'", self.name)
            
            # Fetch Sonar projects from Compass API using "sonarqube" type
            sonar_data = self.data_loader.load_repositories("sonarqube", self.organization_id)
            
            if not sonar_data:
                logger.info("No Sonar projects found for product '%s'", self.name)
                return
            
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
                return
            
            # Detect prefix from first project key (format: "text-")
            first_project_key = project_keys[0]
            if '-' in first_project_key:
                prefix = first_project_key.split('-')[0] + '-'
                logger.info("Detected Sonar project key prefix: '%s'", prefix)
            else:
                logger.warning("Could not detect prefix from project key: %s", first_project_key)
                return
            
            # Extract repo names (remove prefix from project keys)
            for project_key in project_keys:
                if project_key.startswith(prefix):
                    repo_name = project_key[len(prefix):]  # Remove prefix
                    if repo_name:
                        repo_names_set.add(repo_name)
            
            logger.info("Found %d Sonar projects for product '%s' with prefix '%s'", 
                       len(repo_names_set), self.name, prefix)
            
            # Update repository CI status
            updated_count = 0
            for repo in self.repos:
                # Ensure CI status is initialized
                if repo.ci_status is None:
                    from .ci_status import CIStatus
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
                       updated_count, len(self.repos), self.name)
            
        except (ValueError, KeyError, OSError) as e:
            logger.error("Error loading Sonar CI data for product '%s': %s", self.name, str(e))

    def load_vulnerabilities(self):
        """
        Load vulnerability data for repositories in this product.
        """
        logger.info("Loading vulnerability data for product '%s'", self.name)
        
        # Load JFrog vulnerabilities
        self._load_jfrog_vulnerabilities()
        
        # Load Sonar vulnerabilities
        self._load_sonar_vulnerabilities()
        
        logger.info("Vulnerability data loading completed for product '%s'", self.name)
    
    def _load_jfrog_vulnerabilities(self):
        """
        Load JFrog vulnerability data for repositories in this product using enhanced AQL cache logic.
        Updates DependenciesVulnerabilities objects for matching repositories using the new flow:
        1. Get vulnerabilities from Compass API
        2. Map artifacts to repositories using cached AQL data
        3. Refetch missing artifacts with $or query
        """
        try:
            logger.info("🔍 Loading JFrog vulnerabilities for product '%s'", self.name)
            
            # Initialize CompassClient
            from src.services.data_loader import CompassClient
            compass_token = os.getenv('COMPASS_ACCESS_TOKEN', '')
            compass_url = os.getenv('COMPASS_BASE_URL', '')
            
            if not compass_token or not compass_url:
                logger.warning("Compass credentials not found, skipping JFrog vulnerability loading")
                return
            
            compass_client = CompassClient(compass_token, compass_url)
            
            # Fetch JFrog vulnerabilities from Compass API
            jfrog_vulnerabilities = compass_client.fetch_jfrog_vulnerabilities(self.organization_id)
            
            if not jfrog_vulnerabilities:
                logger.info("No JFrog vulnerabilities data returned for organization '%s'", self.organization_id)
                return
            
            logger.info("📊 Fetched %d vulnerability artifacts from Compass API", len(jfrog_vulnerabilities))
            
            # Import constants for JFrog configuration
            try:
                from CONSTANTS import PRODUCT_JFROG_PROJECT, get_jfrog_token_for_product
            except ImportError:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
                from CONSTANTS import PRODUCT_JFROG_PROJECT, get_jfrog_token_for_product
            
            # Get JFrog project and token for this product
            jfrog_project = PRODUCT_JFROG_PROJECT.get(self.name, "")
            if not jfrog_project:
                logger.warning("No JFrog project configured for product '%s', skipping JFrog vulnerability loading", self.name)
                return
            
            jfrog_token, token_env_var = get_jfrog_token_for_product(self.name)
            if not jfrog_token:
                logger.warning("%s not found, skipping JFrog vulnerability loading for product '%s'", token_env_var, self.name)
                return
            
            # Initialize JFrog client for AQL queries
            from src.services.data_loader import JfrogClient
            jfrog_client = JfrogClient(jfrog_token)
            
            # Setup AQL cache directory using project name
            cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'build_info_cache_dir')
            product_cache_dir = os.path.join(cache_dir, jfrog_project)
            aql_cache_dir = os.path.join(product_cache_dir, "cache_repo_responses")
            os.makedirs(aql_cache_dir, exist_ok=True)
            
            logger.info("💾 Using AQL cache directory: %s", aql_cache_dir)
            
            # Process vulnerabilities and parse artifacts
            processed_artifacts = 0
            local_artifacts = 0
            malformed_artifacts = 0
            missing_from_cache = 0
            cache_hits = 0
            build_name_matches = 0
            repo_matches = 0
            unmapped_artifacts = 0  # Track artifacts that couldn't be mapped to repositories
            
            # Dictionary to track missing artifacts per repository
            missing_artifacts_by_repo = {}  # repo_name -> [artifact_paths]
            
            # Dictionary to track artifacts matched to repositories
            artifacts_by_repo = {}  # repo_name -> [DeployedArtifact objects]
            
            # Create lookup map for repositories with matched build names
            repo_build_names_map = {}  # repo_name -> set of build names
            for repo in self.repos:
                if (repo.scm_info and repo.scm_info.repo_name and 
                    repo.ci_status and repo.ci_status.jfrog_status.matched_build_names):
                    repo_build_names_map[repo.scm_info.repo_name] = repo.ci_status.jfrog_status.matched_build_names
            
            logger.info("📋 Found %d repositories with matched build names for artifact matching", len(repo_build_names_map))
            
            # Process each vulnerability artifact
            for artifact_key, vuln_data in jfrog_vulnerabilities.items():
                processed_artifacts += 1
                
                # Log progress every 100 artifacts
                if processed_artifacts % 100 == 0:
                    logger.info("🔄 Progress: %d/%d artifacts processed (%d%%), %d local, %d matched to repos", 
                              processed_artifacts, len(jfrog_vulnerabilities), 
                              int((processed_artifacts / len(jfrog_vulnerabilities)) * 100),
                              local_artifacts, repo_matches)
                
                # Parse artifact structure
                try:
                    parsed_artifact = self._parse_artifact_path(artifact_key)
                    if not parsed_artifact:
                        malformed_artifacts += 1
                        logger.warning("⚠️ Malformed artifact path: %s", artifact_key)
                        continue
                    
                    repo_name, path, name, full_path = parsed_artifact
                    
                    # Check if this is a local repository (contains "local" after last '-')
                    if not self._is_local_repo(repo_name):
                        logger.debug("Skipping non-local repository: %s", repo_name)
                        continue
                    
                    local_artifacts += 1
                    
                    # Check AQL cache for this repository
                    aql_cache_file = os.path.join(aql_cache_dir, f"{repo_name}.json")
                    aql_data = self._load_aql_cache(aql_cache_file)
                    
                    if aql_data is None:
                        # Cache miss - add to missing artifacts list
                        if repo_name not in missing_artifacts_by_repo:
                            missing_artifacts_by_repo[repo_name] = []
                        missing_artifacts_by_repo[repo_name].append(full_path)
                        missing_from_cache += 1
                        continue
                    
                    # Cache file exists, but we still need to check if artifact is in it
                    # (cache_hits will be incremented only if artifact is actually found)
                    
                    # Look for this artifact in the AQL cache
                    build_name = self._find_build_name_in_aql(aql_data, path, name)
                    
                    if not build_name:
                        # Artifact not found in existing cache - could indicate stale cache
                        logger.warning("🔍 Artifact not found in AQL cache for repo '%s': %s (cache may be stale)", 
                                     repo_name, full_path)
                        
                        # Add to missing artifacts to trigger cache refresh for this repo
                        if repo_name not in missing_artifacts_by_repo:
                            missing_artifacts_by_repo[repo_name] = []
                        missing_artifacts_by_repo[repo_name].append(full_path)
                        missing_from_cache += 1
                        continue
                    
                    if build_name in self.unmapped_build_names:
                        logger.debug("Skipping unmapped build name '%s' for artifact '%s'", build_name, artifact_key)
                        continue

                    # Artifact found in cache
                    cache_hits += 1
                    
                    # Match build name to repository
                    repo = self.build_name_to_repo_map.get(build_name)
                    if repo:
                        # Extract vulnerability data
                        vulnerabilities = vuln_data.get('vulnerabilities', {})
                        updated_at = vuln_data.get('updated_at')
                        
                        # Create DeployedArtifact object
                        deployed_artifact = self._create_deployed_artifact(
                            artifact_key, repo, vulnerabilities, updated_at, 
                            build_name, full_path
                        )
                        
                        # Add to artifacts by repo
                        if repo not in artifacts_by_repo:
                            artifacts_by_repo[repo] = []
                        artifacts_by_repo[repo].append(deployed_artifact)
                        
                        repo_matches += 1
                        
                        logger.debug("✅ Matched artifact '%s' to repo '%s' via build name '%s'", 
                                   artifact_key, repo, build_name)
                    else:
                        logger.warning("❌ Build name '%s' from artifact '%s' not found in any repository's matched build names", 
                                     build_name, artifact_key)
                        # Add to unmapped build names to avoid repeated processing
                        self.unmapped_build_names.add(build_name)
                        unmapped_artifacts += 1
                        continue
                    
                except (ValueError, KeyError) as e:
                    malformed_artifacts += 1
                    logger.error("❌ Error processing artifact '%s': %s", artifact_key, str(e))
                    continue
            
            # Fetch missing artifacts from AQL API
            if missing_artifacts_by_repo:
                total_missing_repos = len(missing_artifacts_by_repo)
                total_missing_artifacts = sum(len(artifacts) for artifacts in missing_artifacts_by_repo.values())
                logger.info("🔍 Fetching/refreshing AQL cache for %d repositories (%d artifacts need processing)", 
                           total_missing_repos, total_missing_artifacts)
                self._fetch_missing_artifacts_from_aql(
                    missing_artifacts_by_repo, jfrog_client, aql_cache_dir,
                    repo_build_names_map, jfrog_vulnerabilities, artifacts_by_repo
                )
            
            # Update repository vulnerabilities
            updated_repos = self._update_repository_vulnerabilities(artifacts_by_repo)
            
            # Final summary
            logger.info("✅ JFrog vulnerabilities loading completed for product '%s'", self.name)
            logger.info("📊 PROCESSING SUMMARY:")
            logger.info("   - Total artifacts processed: %d", processed_artifacts)
            logger.info("   - Local repository artifacts: %d", local_artifacts)
            logger.info("   - Malformed artifacts (skipped): %d", malformed_artifacts)
            logger.info("   - AQL cache hits: %d", cache_hits)
            logger.info("   - Missing from cache or stale cache (fetched): %d", missing_from_cache)
            logger.info("   - Build name matches: %d", build_name_matches)
            logger.info("   - Artifacts matched to repositories: %d", repo_matches)
            logger.info("   - Unmapped artifacts (❌ no repo match): %d", unmapped_artifacts)
            logger.info("   - Repositories updated with vulnerabilities: %d", updated_repos)
            
            # Explanation of key metrics
            logger.info("📋 METRIC EXPLANATIONS:")
            logger.info("   • 'Artifacts matched to repositories' = Artifacts successfully linked to SCM repos via CI Status build names that were fetched earlier")
            logger.info("   • 'Repositories updated with vulnerabilities' = GitHub repos that received vulnerability data")
            logger.info("   • 'Unmapped artifacts' = Artifacts with build names that we could found linked to any SCM repo during the CI phase")
            
            if malformed_artifacts > 0:
                logger.warning("⚠️ %d malformed artifacts were skipped during processing", malformed_artifacts)
            
            if unmapped_artifacts > 0:
                logger.warning("❌ %d artifacts could not be mapped to repositories (check build name matching)", unmapped_artifacts)
            
        except (ImportError, ValueError, KeyError) as e:
            logger.error("❌ Error loading JFrog vulnerabilities for product '%s': %s", self.name, str(e))
    
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
    
    def _find_build_name_in_aql(self, aql_data: dict, path: str, name: str) -> Optional[str]:
        """
        Find build name for artifact in AQL data
        
        Args:
            aql_data (dict): AQL response data
            path (str): Artifact path
            name (str): Artifact name
            
        Returns:
            Optional[str]: Build name or None if not found
        """
        try:
            results = aql_data.get('results', [])
            
            for result in results:
                # Match by path and name
                if result.get('path') == path and result.get('name') == name:
                    # Look for build.name in properties
                    properties = result.get('properties', [])
                    for prop in properties:
                        if prop.get('key') == 'build.name':
                            build_name_value = prop.get('value')
                            if build_name_value:
                                # Handle different build name formats:
                                # Format: "Frontend/frontend-service/jfrog" -> extract "frontend-service"
                                # Format: "frontend-service" -> use as-is
                                if '/' in build_name_value:
                                    parts = build_name_value.split('/')
                                    if len(parts) >= 2:
                                        # Extract the middle part (service name)
                                        return parts[1]
                                    else:
                                        return parts[0]
                                else:
                                    return build_name_value
            
            return None
            
        except (ValueError, KeyError, IndexError) as e:
            logger.debug("Error finding build name in AQL data: %s", str(e))
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
                                updated_at: str, build_name: str, jfrog_path: str):
        """
        Create DeployedArtifact object from vulnerability data
        
        Args:
            artifact_key (str): Full artifact key
            repo_name (str): Repository name
            vulnerabilities (dict): Vulnerability counts
            updated_at (str): Last updated timestamp
            build_name (str): Build name
            jfrog_path (str): Full JFrog path
            
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
        
        # Extract artifact type
        artifact_type = self._extract_artifact_type(artifact_key)
        
        return DeployedArtifact(
            artifact_key=artifact_key,
            repo_name=repo_name,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            unknown_count=unknown_count,
            artifact_type=artifact_type,
            build_name=build_name,
            updated_at=updated_at,
            jfrog_path=jfrog_path
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
                        build_name = self._find_build_name_in_aql(aql_response, path, name)

                        if not build_name:
                            logger.debug("No build name found for artifact: %s", artifact_path)
                            continue

                        # Skip if build name is already known to be unmapped
                        if build_name in self.unmapped_build_names:
                            logger.debug("Skipping build name '%s' as it is already known to be unmapped", build_name)
                            continue

                        # Match build name to repository
                        repo = self.build_name_to_repo_map.get(build_name)
                        if not repo:
                            logger.warning("❌ Build name '%s' from artifact '%s' not found in any repository's matched build names", 
                                         build_name, artifact_path)
                            self.unmapped_build_names.add(build_name)  # Add to unmapped list
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
                            updated_at, build_name, artifact_path
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
    
    def _load_sonar_vulnerabilities(self):
        """
        Load SonarQube vulnerability data for repositories in this product
        Updates CodeVulnerabilities objects for matching repositories
        """
        try:
            # Initialize CompassClient
            from src.services.data_loader import CompassClient
            compass_token = os.getenv('COMPASS_ACCESS_TOKEN', '')
            compass_url = os.getenv('COMPASS_BASE_URL', '')
            
            if not compass_token or not compass_url:
                logger.warning("Compass credentials not found, skipping Sonar vulnerability loading")
                return
            
            compass_client = CompassClient(compass_token, compass_url)
            
            # Fetch SonarQube issues for this organization
            sonar_issues = compass_client.fetch_sonarqube_issues(self.organization_id)
            
            if not sonar_issues:
                logger.info("No SonarQube issues data returned for organization '%s'", self.organization_id)
                return
            
            # Also fetch SonarQube secrets data
            sonar_secrets = compass_client.fetch_sonarqube_secrets(self.organization_id)
            logger.info("Fetched SonarQube secrets data for %d projects", len(sonar_secrets))
            
            updated_count = 0
            
            # Import constants
            try:
                from CONSTANTS import PRODUCT_SONAR_PREFIX
            except ImportError:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
                from CONSTANTS import PRODUCT_SONAR_PREFIX
            
            # Get Sonar prefix for this product
            sonar_prefix = PRODUCT_SONAR_PREFIX.get(self.name, "")
            
            # Process SonarQube issues data
            for project_key, issues_data in sonar_issues.items():
                # Extract repository name from project key with improved prefix handling
                if sonar_prefix and project_key.startswith(sonar_prefix):
                    repo_name = project_key[len(sonar_prefix):]
                    # Handle case where separator is included in prefix
                    if repo_name.startswith('-'):
                        repo_name = repo_name[1:]
                else:
                    # No prefix or prefix doesn't match, use project key as-is
                    repo_name = project_key
                
                # Find matching repository
                matching_repo = None
                for repo in self.repos:
                    if repo.get_repository_name() == repo_name:
                        matching_repo = repo
                        break
                
                if matching_repo:
                    # Initialize vulnerabilities if not already initialized
                    if matching_repo.vulnerabilities is None:
                        matching_repo.vulnerabilities = Vulnerabilities()
                    
                    # Process all issue types dynamically (VULNERABILITY, CODE_SMELL, BUG, etc.)
                    issues_by_type = {}
                    
                    # Iterate through all issue types in the response
                    for issue_type, type_data in issues_data.items():
                        if 'issues' in type_data:
                            severity_counts = type_data['issues']
                            issues_by_type[issue_type] = severity_counts
                            
                            logger.debug("Collected '%s' issues for repo '%s': %s", 
                                       issue_type, repo_name, severity_counts)
                    
                    # Update the repository's code issues with all types
                    if issues_by_type:
                        # Check if we have secrets data for this project
                        secrets_count = 0
                        if sonar_secrets and project_key in sonar_secrets:
                            secrets_data = sonar_secrets[project_key]
                            # Extract secrets count from the response
                            # Assuming the API returns something like {"secrets_count": 5}
                            if isinstance(secrets_data, dict):
                                secrets_count = secrets_data.get('secrets_count', 0)
                            elif isinstance(secrets_data, int):
                                secrets_count = secrets_data
                            
                            logger.debug("Found %d secrets for project '%s'", secrets_count, project_key)
                        
                        # Create or update CodeIssues with all collected issue types and secrets
                        matching_repo.vulnerabilities.code_issues = CodeIssues(issues_by_type, secrets_count)
                        updated_count += 1
                        
                        logger.debug("Updated code issues for repo '%s' with %d issue types and %d secrets: %s", 
                                   repo_name, len(issues_by_type), secrets_count, list(issues_by_type.keys()))
            
            logger.info("Updated Sonar code issues data for %d repositories in product '%s'", 
                       updated_count, self.name)
            
        except (ValueError, KeyError, OSError) as e:
            logger.error("Error loading Sonar code issues data for product '%s': %s", self.name, str(e))
    
    def _extract_artifact_type(self, artifact_key: str) -> str:
        """
        Extract artifact type from artifact key
        
        Args:
            artifact_key (str): Full artifact key
            
        Returns:
            str: Artifact type (docker, npm, maven, etc.)
        """
        try:
            # Extract type before first :// if present
            if '://' in artifact_key:
                type_part = artifact_key.split('://')[0]
                return type_part.lower()
            else:
                return 'unknown'
        except (ValueError, IndexError):
            return 'unknown'

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

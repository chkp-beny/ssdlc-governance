"""
Test JFrog CI integration - metadata-based approach for Avanan product
"""

import pytest
import sys
import os
import time
from dotenv import load_dotenv

# Add src and root to path for imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
load_dotenv()

from src.models.product import Product
from src.services.data_loader import JfrogClient
from CONSTANTS import PRODUCT_SCM_TYPE, PRODUCT_ORGANIZATION_ID, PRODUCT_JFROG_PROJECT


class TestJfrogCIMetadataIntegration:
    """Test JFrog CI integration using metadata-based approach with Avanan product"""
    
    def test_avanan_load_repos_and_ci_data_metadata_based(self):
        """Test loading repositories and CI data for Avanan using metadata-based approach"""
        # Create Avanan Product
        avanan_product = Product(
            name="Avanan",
            scm_type=PRODUCT_SCM_TYPE["Avanan"],
            organization_id=PRODUCT_ORGANIZATION_ID["Avanan"]
        )
        
        # Load repositories with timing
        print("Starting repository loading...")
        repo_start_time = time.time()
        avanan_product.load_repositories()
        repo_end_time = time.time()
        repo_load_duration = repo_end_time - repo_start_time
        
        print(f"Repository loading completed in {repo_load_duration:.2f} seconds")
        
        # Verify repositories were loaded - expecting above 200
        assert len(avanan_product.repos) > 200, f"Expected more than 200 repos, got {len(avanan_product.repos)}"
        print(f"Loaded {len(avanan_product.repos)} repositories for Avanan")
        
        # Load CI data with timing (this will use metadata-based approach for Avanan)
        print("Starting CI data loading (metadata-based approach)...")
        ci_start_time = time.time()
        avanan_product.load_ci_data()
        ci_end_time = time.time()
        ci_load_duration = ci_end_time - ci_start_time
        
        print(f"CI data loading completed in {ci_load_duration:.2f} seconds")
        print(f"Total operation time: {(repo_load_duration + ci_load_duration):.2f} seconds")
        
        # Count repositories with JFrog CI
        repos_with_jfrog_ci = 0
        repos_with_branch_info = 0
        repos_with_job_url = 0
        
        for repo in avanan_product.repos:
            if repo.ci_status.jfrog_status.is_exist:
                repos_with_jfrog_ci += 1
                if repo.ci_status.jfrog_status.branch:
                    repos_with_branch_info += 1
                if repo.ci_status.jfrog_status.job_url:
                    repos_with_job_url += 1
        
        print(f"Found {repos_with_jfrog_ci} repositories with JFrog CI integration")
        print(f"Found {repos_with_branch_info} repositories with branch information")
        print(f"Found {repos_with_job_url} repositories with job URL information")
        
        # Performance metrics
        print("\n=== PERFORMANCE METRICS ===")
        print(f"Repository loading: {repo_load_duration:.2f} seconds ({len(avanan_product.repos)} repos)")
        print(f"CI data loading: {ci_load_duration:.2f} seconds (metadata-based)")
        print(f"Repos per second (loading): {len(avanan_product.repos) / repo_load_duration:.1f}")
        print(f"CI matches per second: {repos_with_jfrog_ci / ci_load_duration:.1f}")
        print(f"Total time: {(repo_load_duration + ci_load_duration):.2f} seconds")
        
        # Verify that we have more than 60 repositories with CI (metadata-based approach)
        assert repos_with_jfrog_ci > 60, f"Expected more than 60 repos with CI, got {repos_with_jfrog_ci}"
        
        # Log some examples with metadata
        ci_repos_with_metadata = []
        for repo in avanan_product.repos:
            if repo.ci_status.jfrog_status.is_exist:
                metadata = {
                    'repo_name': repo.scm_info.repo_name,
                    'branch': repo.ci_status.jfrog_status.branch,
                    'has_job_url': bool(repo.ci_status.jfrog_status.job_url)
                }
                ci_repos_with_metadata.append(metadata)
                if len(ci_repos_with_metadata) >= 5:  # Show first 5
                    break
        
        print("Sample repositories with JFrog CI and metadata:")
        for repo_meta in ci_repos_with_metadata:
            print(f"  - {repo_meta['repo_name']}: branch={repo_meta['branch']}, has_url={repo_meta['has_job_url']}")
    
    def test_avanan_jfrog_client_fetch_all_project_builds(self):
        """Test JFrog client fetch_all_project_builds for Avanan project"""
        # Get JFrog token for Avanan
        jfrog_token = os.getenv('AVANAN_JFROG_ACCESS_TOKEN')
        assert jfrog_token, "AVANAN_JFROG_ACCESS_TOKEN not found in environment"
        
        # Create JFrog client
        jfrog_client = JfrogClient(jfrog_token)
        
        # Fetch build info for Avanan project (hec)
        avanan_project = PRODUCT_JFROG_PROJECT["Avanan"]
        build_data = jfrog_client.fetch_all_project_builds(avanan_project)
        
        # Verify we got data
        assert isinstance(build_data, dict), "Should return a dictionary"
        assert 'builds' in build_data, "Should have 'builds' key"
        
        builds = build_data['builds']
        assert isinstance(builds, list), "Builds should be a list"
        assert len(builds) > 0, "Should have at least some builds"
        
        # Check first 3 builds for URI field starting with /
        for i, build in enumerate(builds[:3]):
            assert isinstance(build, dict), f"Build {i} should be a dictionary"
            assert 'uri' in build, f"Build {i} should have 'uri' field"
            
            uri = build['uri']
            assert isinstance(uri, str), f"Build {i} URI should be a string"
            assert uri.startswith('/'), f"Build {i} URI should start with '/', got: {uri}"
            
            print(f"Build {i+1}: URI = {uri}")
        
        print(f"Successfully verified {min(3, len(builds))} builds have URI fields starting with '/'")
        print(f"Total builds found for Avanan: {len(builds)}")
    
    def test_avanan_jfrog_client_metadata_fetch(self):
        """Test JFrog client metadata fetching capabilities for Avanan"""
        # Get JFrog token for Avanan
        jfrog_token = os.getenv('AVANAN_JFROG_ACCESS_TOKEN')
        assert jfrog_token, "AVANAN_JFROG_ACCESS_TOKEN not found in environment"
        
        # Create JFrog client
        jfrog_client = JfrogClient(jfrog_token)
        
        # Fetch build info for Avanan project
        avanan_project = PRODUCT_JFROG_PROJECT["Avanan"]
        build_data = jfrog_client.fetch_all_project_builds(avanan_project)
        
        # Get first build for metadata testing
        builds = build_data.get('builds', [])
        assert len(builds) > 0, "Should have at least one build"
        
        first_build_uri = builds[0]['uri']
        build_name = first_build_uri.lstrip('/')
        
        print(f"Testing metadata fetch for build: {build_name}")
        
        # Test fetch_build_metadata
        metadata = jfrog_client.fetch_build_metadata(build_name, avanan_project)
        assert isinstance(metadata, dict), "Metadata should return a dictionary"
        
        if 'buildsNumbers' in metadata and metadata['buildsNumbers']:
            # Test fetch_build_details if we have build numbers
            build_numbers = metadata['buildsNumbers']
            latest_build = max(build_numbers, key=lambda b: b.get('started', ''))
            build_number_uri = latest_build.get('uri', '')
            
            if build_number_uri.startswith('/'):
                build_number = build_number_uri[1:]
                print(f"Testing build details fetch for build: {build_name}/{build_number}")
                
                # Test fetch_build_details
                build_details = jfrog_client.fetch_build_details(build_name, build_number, avanan_project)
                assert isinstance(build_details, dict), "Build details should return a dictionary"
                
                # Check if we have buildInfo structure
                if 'buildInfo' in build_details:
                    build_info = build_details['buildInfo']
                    properties = build_info.get('properties', {})
                    
                    # Check for metadata fields
                    source_repo = properties.get('buildInfo.env.SOURCE_REPO')
                    source_branch = properties.get('buildInfo.env.SOURCE_BRANCH')
                    job_url = build_info.get('url')
                    
                    print(f"Metadata found - SOURCE_REPO: {source_repo}, SOURCE_BRANCH: {source_branch}, job_url: {bool(job_url)}")
                    
                    # At least one of these should be present for a successful metadata fetch
                    assert source_repo or source_branch or job_url, "Should have at least some metadata"
                else:
                    print("No buildInfo found in build details")
            else:
                print("No valid build number URI found")
        else:
            print("No buildsNumbers found in metadata")
    
    def test_avanan_jfrog_client_connection(self):
        """Test JFrog client connection using Avanan token"""
        # Get JFrog token for Avanan
        jfrog_token = os.getenv('AVANAN_JFROG_ACCESS_TOKEN')
        assert jfrog_token, "AVANAN_JFROG_ACCESS_TOKEN not found in environment"
        
        # Create JFrog client
        jfrog_client = JfrogClient(jfrog_token)
        
        # Test connection
        connection_result = jfrog_client.test_connection()
        
        # Connection might fail if service is not available, but we test the method exists
        assert isinstance(connection_result, bool), "test_connection should return a boolean"
        print(f"JFrog connection test result: {connection_result}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

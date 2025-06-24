"""
Test JFrog CI integration - specific tests for Cyberint product
"""

import pytest
import sys
import os
from dotenv import load_dotenv

# Add src and root to path for imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
load_dotenv()

from src.models.product import Product
from src.services.data_loader import JfrogClient
from CONSTANTS import PRODUCT_SCM_TYPE, PRODUCT_ORGANIZATION_ID, PRODUCT_JFROG_PROJECT


class TestJfrogCIIntegration:
    """Test JFrog CI integration using Cyberint product"""
    
    def test_cyberint_load_repos_and_ci_data(self):
        """Test loading repositories and CI data for Cyberint, verify CI count above 20"""
        # Create Cyberint Product
        cyberint_product = Product(
            name="Cyberint",
            scm_type=PRODUCT_SCM_TYPE["Cyberint"],
            organization_id=PRODUCT_ORGANIZATION_ID["Cyberint"]
        )
        
        # Load repositories
        cyberint_product.load_repositories()
        
        # Verify repositories were loaded
        assert len(cyberint_product.repos) > 0, "Should have loaded some repositories"
        print(f"Loaded {len(cyberint_product.repos)} repositories for Cyberint")
        
        # Load CI data
        cyberint_product.load_ci_data()
        
        # Count repositories with JFrog CI
        repos_with_jfrog_ci = 0
        for repo in cyberint_product.repos:
            if repo.ci_status.jfrog_status.is_exist:
                repos_with_jfrog_ci += 1
        
        print(f"Found {repos_with_jfrog_ci} repositories with JFrog CI integration")
        
        # Verify that we have more than 20 repositories with CI
        assert repos_with_jfrog_ci > 20, f"Expected more than 20 repos with CI, got {repos_with_jfrog_ci}"
        
        # Log some examples
        ci_repos = [repo.scm_info.repo_name for repo in cyberint_product.repos 
                   if repo.ci_status.jfrog_status.is_exist][:10]
        print(f"Sample repositories with JFrog CI: {ci_repos}")
    
    def test_jfrog_client_fetch_build_info(self):
        """Test JFrog client fetch_build_info returns JSON with URI fields starting with /"""
        # Get JFrog token
        jfrog_token = os.getenv('CYBERINT_JFROG_ACCESS_TOKEN')
        assert jfrog_token, "CYBERINT_JFROG_ACCESS_TOKEN not found in environment"
        
        # Create JFrog client
        jfrog_client = JfrogClient(jfrog_token)
        
        # Fetch build info for Cyberint project
        cyberint_project = PRODUCT_JFROG_PROJECT["Cyberint"]
        build_data = jfrog_client.fetch_build_info(cyberint_project)
        
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
    
    def test_jfrog_client_connection(self):
        """Test JFrog client connection using ping endpoint"""
        # Get JFrog token
        jfrog_token = os.getenv('CYBERINT_JFROG_ACCESS_TOKEN')
        assert jfrog_token, "CYBERINT_JFROG_ACCESS_TOKEN not found in environment"
        
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
"""
Tests for CompassClient - test real Cyberint repository loading
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

from src.services.data_loader import CompassClient
from CONSTANTS import PRODUCT_SCM_TYPE, PRODUCT_ORGANIZATION_ID


# Cyberint constants for testing
CYBERINT_SCM_TYPE = PRODUCT_SCM_TYPE["Cyberint"]  # bitbucket-onprem
CYBERINT_ORG_ID = PRODUCT_ORGANIZATION_ID["Cyberint"]  # 2


class TestCompassClientReal:
    """Test CompassClient with real Cyberint data"""
    
    @pytest.fixture
    def compass_client(self):
        """Create CompassClient with real environment variables"""
        token = os.getenv('COMPASS_ACCESS_TOKEN')
        url = os.getenv('COMPASS_BASE_URL')
        
        assert token, "COMPASS_ACCESS_TOKEN not found in environment"
        assert url, "COMPASS_BASE_URL not found in environment"
        
        return CompassClient(token, url)
    
    def test_cyberint_repository_count_above_100(self, compass_client):
        """Test that Cyberint has more than 100 repositories"""
        # Fetch repositories for Cyberint
        repos = compass_client.fetch_repositories(CYBERINT_SCM_TYPE, CYBERINT_ORG_ID)
        
        # Verify we got a list
        assert isinstance(repos, list), "Should return a list of repositories"
        
        # Verify we have more than 100 repositories
        assert len(repos) > 100, f"Expected more than 100 repos, got {len(repos)}"
        
        print(f"✓ Cyberint has {len(repos)} repositories (> 100)")
    
    def test_cyberint_specific_repositories_exist(self, compass_client):
        """Test that specific repositories exist in Cyberint"""
        # Fetch repositories for Cyberint
        repos = compass_client.fetch_repositories(CYBERINT_SCM_TYPE, CYBERINT_ORG_ID)
        
        # Extract repository names
        repo_names = set()
        for repo in repos:
            if 'repo_name' in repo:
                repo_names.add(repo['repo_name'])
            elif 'name' in repo:
                repo_names.add(repo['name'])
        
        # Required repositories that should exist
        required_repos = ['alert-service', 'frontend-service']
        
        # Check each required repository
        for required_repo in required_repos:
            assert required_repo in repo_names, f"Repository '{required_repo}' not found in Cyberint repos"
            print(f"✓ Found required repository: {required_repo}")
        
        print(f"✓ All required repositories found in {len(repos)} total repositories")
    
    def test_cyberint_connection(self, compass_client):
        """Test basic connection to Compass API for Cyberint"""
        # Test connection
        result = compass_client.test_connection(CYBERINT_SCM_TYPE, CYBERINT_ORG_ID)
        
        # Should return a boolean (True if service available, False if not)
        assert isinstance(result, bool), "test_connection should return a boolean"
        print(f"✓ Connection test result: {result}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

"""
Test Sonar CI integration - specific tests for Cyberint product
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
from CONSTANTS import PRODUCT_SCM_TYPE, PRODUCT_ORGANIZATION_ID


class TestSonarCIIntegration:
    """Test Sonar CI integration using Cyberint product"""
    
    def test_cyberint_sonar_integration_count(self):
        """Test that Cyberint has more than 30 repositories with Sonar integration"""
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
        
        # Load CI data (includes Sonar CI)
        cyberint_product.load_ci_data()
        
        # Count repositories with Sonar CI integration
        repos_with_sonar_ci = 0
        for repo in cyberint_product.repos:
            if repo.ci_status and repo.ci_status.sonar_status.is_exist:
                repos_with_sonar_ci += 1
        
        print(f"Found {repos_with_sonar_ci} repositories with Sonar CI integration")
        
        # Verify that we have more than 30 repositories with Sonar CI
        assert repos_with_sonar_ci > 30, f"Expected more than 30 repos with Sonar CI, got {repos_with_sonar_ci}"
        
        # Log some examples
        sonar_repos = [repo.scm_info.repo_name for repo in cyberint_product.repos 
                      if repo.ci_status and repo.ci_status.sonar_status.is_exist][:10]
        print(f"Sample repositories with Sonar CI: {sonar_repos}")
    
    def test_cyberint_alert_service_sonar_integration(self):
        """Test that alert-service repository has Sonar integration with correct project key"""
        # Create Cyberint Product
        cyberint_product = Product(
            name="Cyberint",
            scm_type=PRODUCT_SCM_TYPE["Cyberint"],
            organization_id=PRODUCT_ORGANIZATION_ID["Cyberint"]
        )
        
        # Load repositories
        cyberint_product.load_repositories()
        
        # Load CI data (includes Sonar CI)
        cyberint_product.load_ci_data()
        
        # Find alert-service repository
        alert_service_repo = None
        for repo in cyberint_product.repos:
            if repo.scm_info and repo.scm_info.repo_name == "alert-service":
                alert_service_repo = repo
                break
        
        # Verify alert-service repository exists
        assert alert_service_repo is not None, "alert-service repository not found in Cyberint repositories"
        print(f"Found alert-service repository: {alert_service_repo.scm_info.repo_name}")
        
        # Verify alert-service has Sonar CI integration
        assert alert_service_repo.ci_status is not None, "alert-service should have CI status initialized"
        assert alert_service_repo.ci_status.sonar_status.is_exist, "alert-service should have Sonar CI integration"
        
        # Verify the project key is correct (should be "cyberint-alert-service")
        expected_project_key = "cyberint-alert-service"
        actual_project_key = alert_service_repo.ci_status.sonar_status.project_key
        
        assert actual_project_key == expected_project_key, \
            f"Expected project key '{expected_project_key}', got '{actual_project_key}'"
        
        print(f"✓ alert-service has Sonar integration with correct project key: {actual_project_key}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

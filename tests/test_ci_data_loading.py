"""
Tests for CI data loading functionality
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
load_dotenv()

from src.models.product import Product
from src.models.devops import DevOps
from src.models.repo import Repo
from src.models.scm_info import SCMInfo
from src.models.ci_status import CIStatus, JfrogCIStatus
from CONSTANTS import PRODUCT_JFROG_PROJECT


class TestCIDataLoading:
    """Test cases for CI data loading functionality"""
    
    @pytest.fixture
    def mock_product(self):
        """Create a mock product with test repositories"""
        devops = DevOps("Test User", "test@test.com")
        product = Product("Cyberint", "bitbucket-onprem", "2", devops)
        
        # Add mock repositories
        repo1 = Repo(
            scm_info=SCMInfo(repo_name="discovery"),
            product_name="Cyberint"
        )
        repo2 = Repo(
            scm_info=SCMInfo(repo_name="identity-utils"),
            product_name="Cyberint"
        )
        repo3 = Repo(
            scm_info=SCMInfo(repo_name="non-existent-repo"),
            product_name="Cyberint"
        )
        
        product.repos = [repo1, repo2, repo3]
        return product
    
    @patch('src.services.data_loader.JfrogClient')
    def test_load_jfrog_ci_data_success(self, mock_jfrog_client_class, mock_product):
        """Test successful JFrog CI data loading"""
        # Mock JfrogClient instance
        mock_client = Mock()
        mock_client.fetch_build_info.return_value = ["discovery", "identity-utils", "other-repo"]
        mock_jfrog_client_class.return_value = mock_client
        
        # Mock environment variable
        with patch.dict(os.environ, {'CYBERINT_JFROG_ACCESS_TOKEN': 'test-token'}):
            # Call the method
            mock_product._load_jfrog_ci_data()
        
        # Verify JfrogClient was initialized correctly
        mock_jfrog_client_class.assert_called_once_with('test-token')
        
        # Verify fetch_build_info was called with correct project
        mock_client.fetch_build_info.assert_called_once_with('cyberint')
        
        # Verify repository CI status was updated
        assert mock_product.repos[0].ci_status.jfrog_status.is_exist is True  # discovery
        assert mock_product.repos[1].ci_status.jfrog_status.is_exist is True  # identity-utils
        assert mock_product.repos[2].ci_status.jfrog_status.is_exist is False  # non-existent-repo
    
    def test_load_jfrog_ci_data_no_project(self, mock_product):
        """Test JFrog CI data loading when no project is configured"""
        # Change product name to one without JFrog project
        mock_product.name = "Policy Insights"
        
        # Call the method
        mock_product._load_jfrog_ci_data()
        
        # Verify no repositories were updated (all should remain False)
        for repo in mock_product.repos:
            assert repo.ci_status.jfrog_status.is_exist is False
    
    def test_load_jfrog_ci_data_no_token(self, mock_product):
        """Test JFrog CI data loading when no token is available"""
        with patch.dict(os.environ, {}, clear=True):
            # Call the method
            mock_product._load_jfrog_ci_data()
        
        # Verify no repositories were updated (all should remain False)
        for repo in mock_product.repos:
            assert repo.ci_status.jfrog_status.is_exist is False
    
    @patch('src.services.data_loader.JfrogClient')
    def test_load_ci_data_integration(self, mock_jfrog_client_class, mock_product):
        """Test the main load_ci_data method"""
        # Mock JfrogClient
        mock_client = Mock()
        mock_client.fetch_build_info.return_value = ["discovery"]
        mock_jfrog_client_class.return_value = mock_client
        
        with patch.dict(os.environ, {'CYBERINT_JFROG_ACCESS_TOKEN': 'test-token'}):
            # Call the main method
            mock_product.load_ci_data()
        
        # Verify JFrog data was loaded
        assert mock_product.repos[0].ci_status.jfrog_status.is_exist is True  # discovery
        assert mock_product.repos[1].ci_status.jfrog_status.is_exist is False  # identity-utils
        assert mock_product.repos[2].ci_status.jfrog_status.is_exist is False  # non-existent-repo
    
    def test_jfrog_project_constants(self):
        """Test that JFrog project constants are properly configured"""
        assert "Cyberint" in PRODUCT_JFROG_PROJECT
        assert PRODUCT_JFROG_PROJECT["Cyberint"] == "cyberint"
        assert "Avanan" in PRODUCT_JFROG_PROJECT
        assert PRODUCT_JFROG_PROJECT["Avanan"] == "hec"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

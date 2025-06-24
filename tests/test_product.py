"""
Tests for Product and DevOps classes using real data from CONSTANTS.py
"""

import pytest
import sys
import os

# Add src and root to path for imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

from models.product import Product
from models.devops import DevOps
from CONSTANTS import PRODUCT_DEVOPS, PRODUCT_SCM_TYPE, PRODUCT_ORGANIZATION_ID


class TestDevOps:
    """Test cases for DevOps class"""
    
    @pytest.fixture
    def datatube_devops_info(self):
        """Fixture for Datatube DevOps info from CONSTANTS"""
        return PRODUCT_DEVOPS["Datatube"]
    
    def test_init_valid_email(self, datatube_devops_info):
        """Test DevOps initialization with valid email"""
        devops = DevOps(datatube_devops_info["name"], datatube_devops_info["email"])
        
        assert devops.full_name == datatube_devops_info["name"]
        assert devops.email == datatube_devops_info["email"]
        assert "@checkpoint.com" in devops.email
    
    def test_init_invalid_email(self):
        """Test DevOps initialization with invalid email raises ValueError"""
        with pytest.raises(ValueError, match="Invalid email format"):
            DevOps("Test User", "invalid-email")
    
    def test_str_representation(self, datatube_devops_info):
        """Test DevOps string representation"""
        devops = DevOps(datatube_devops_info["name"], datatube_devops_info["email"])
        result = str(devops)
        expected = f"DevOps(name='{datatube_devops_info['name']}', email='{datatube_devops_info['email']}')"
        
        assert result == expected


class TestProduct:
    """Test cases for Product class"""
    
    @pytest.fixture
    def datatube_devops_info(self):
        """Fixture for Datatube DevOps info from CONSTANTS"""
        return PRODUCT_DEVOPS["Datatube"]
    
    @pytest.fixture
    def datatube_devops(self, datatube_devops_info):
        """Fixture for Datatube DevOps contact"""
        return DevOps(datatube_devops_info["name"], datatube_devops_info["email"])
    
    def test_init_minimal(self):
        """Test Product initialization with minimal parameters"""
        product = Product("Datatube", "github", "0")
        
        assert product.name == "Datatube"
        assert product.scm_type == "github"
        assert product.organization_id == "0"
        assert product.devops is None
        assert product.repos == []
    
    def test_init_with_devops(self, datatube_devops):
        """Test Product initialization with DevOps"""
        product = Product("Datatube", "github", "0", datatube_devops)
        
        assert product.name == "Datatube"
        assert product.scm_type == "github"
        assert product.organization_id == "0"
        assert product.devops == datatube_devops
        assert product.repos == []
    
    def test_get_repos_count(self):
        """Test repository count"""
        product = Product("TestProduct", "github", "0")
        
        assert product.get_repos_count() == 0
    
    def test_str_representation(self, datatube_devops, datatube_devops_info):
        """Test string representation"""
        product = Product("Datatube", "github", "0", datatube_devops)
        result = str(product)
        expected = f"Product(name='Datatube', scm='github', org_id='0', repos=0, devops='{datatube_devops_info['name']}')"
        
        assert result == expected

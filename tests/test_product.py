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

from models.product import Product, DevOps
from CONSTANTS import PRODUCT_DEVOPS


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
        product = Product("Datatube")
        
        assert product.name == "Datatube"
        assert product.devops is None
        assert product.description is None
        assert product.repos == []
    
    def test_init_with_devops(self, datatube_devops):
        """Test Product initialization with DevOps"""
        product = Product("Datatube", datatube_devops)
        
        assert product.name == "Datatube"
        assert product.devops == datatube_devops
        assert product.description is None
        assert product.repos == []
    
    def test_set_devops_success(self, datatube_devops):
        """Test setting DevOps contact"""
        product = Product("TestProduct")
        
        product.set_devops(datatube_devops)
        
        assert product.devops == datatube_devops
    
    def test_set_devops_invalid_type(self):
        """Test setting invalid DevOps type raises TypeError"""
        product = Product("TestProduct")
        
        with pytest.raises(TypeError, match="Expected DevOps instance"):
            product.set_devops("not a devops object")
    
    def test_add_repo(self):
        """Test adding repository"""
        product = Product("TestProduct")
        mock_repo = "test-repo"
        
        product.add_repo(mock_repo)
        
        assert len(product.repos) == 1
        assert product.repos[0] == mock_repo
    
    def test_has_devops_contact(self, datatube_devops):
        """Test has_devops_contact method"""
        product_without_devops = Product("TestProduct")
        product_with_devops = Product("TestProduct", datatube_devops)
        
        assert product_without_devops.has_devops_contact() is False
        assert product_with_devops.has_devops_contact() is True
    
    def test_str_representation(self, datatube_devops, datatube_devops_info):
        """Test string representation"""
        product = Product("Datatube", datatube_devops)
        result = str(product)
        expected = f"Product(name='Datatube', repos=0, devops='{datatube_devops_info['name']}')"
        
        assert result == expected

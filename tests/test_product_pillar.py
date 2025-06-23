"""
Tests for ProductPillar class using real data from CONSTANTS.py
"""

import pytest
import sys
import os

# Add src and root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

from models.product_pillar import ProductPillar
from models.product import Product, DevOps
from CONSTANTS import PILLAR_PRODUCTS, PRODUCT_DEVOPS


class TestProductPillar:
    """Test cases for ProductPillar class"""
    
    @pytest.fixture
    def datatube_devops(self):
        """Fixture for Datatube DevOps contact"""
        devops_info = PRODUCT_DEVOPS["Datatube"]
        return DevOps(devops_info["name"], devops_info["email"])
    
    def test_init_basic(self):
        """Test basic ProductPillar initialization"""
        pillar = ProductPillar("SSDLC")
        
        assert pillar.name == "SSDLC"
        assert pillar.description is None
        assert pillar.products == []
        assert len(pillar.products) == 0
    
    def test_add_product_success(self, datatube_devops):
        """Test successfully adding a product to pillar"""
        pillar = ProductPillar("SDDLC")
        product = Product("Datatube", datatube_devops)
        
        pillar.add_product(product)
        
        assert len(pillar.products) == 1
        assert pillar.products[0] == product
        assert pillar.get_product("Datatube") == product
    
    def test_add_product_invalid_type(self):
        """Test adding invalid type raises TypeError"""
        pillar = ProductPillar("SSDLC")
        
        with pytest.raises(TypeError, match="Expected Product instance"):
            pillar.add_product("not a product")
    
    def test_remove_product_success(self, datatube_devops):
        """Test successfully removing a product"""
        pillar = ProductPillar("SDDLC")
        product = Product("Datatube", datatube_devops)
        
        pillar.add_product(product)
        result = pillar.remove_product("Datatube")
        
        assert result is True
        assert len(pillar.products) == 0
        assert pillar.get_product("Datatube") is None
    
    def test_str_representation(self, datatube_devops):
        """Test string representation"""
        pillar = ProductPillar("SDDLC")
        product = Product("Datatube", datatube_devops)
        pillar.add_product(product)
        
        result = str(pillar)
        expected = "ProductPillar(name='SDDLC', products=1)"
        
        assert result == expected
    
    def test_repr_representation_with_real_data(self):
        """Test repr representation with real data"""
        description = "Harmony pillar for cloud security services"
        pillar = ProductPillar("Harmony", description)
        
        result = repr(pillar)
        expected = f"ProductPillar(name='Harmony', description='{description}', products=0)"
        
        assert result == expected
    
    def test_all_real_devops_contacts_valid(self):
        """Test that all DevOps contacts from CONSTANTS are valid"""
        for product_name, devops_info in PRODUCT_DEVOPS.items():
            # Should not raise exception
            devops = DevOps(devops_info["name"], devops_info["email"])
            assert devops.full_name == devops_info["name"]
            assert devops.email == devops_info["email"]
            assert "@checkpoint.com" in devops.email

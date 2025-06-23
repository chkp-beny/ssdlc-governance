"""
ProductPillar class - Top-level organizational grouping
Contains a list of Product objects
"""

from typing import List, Optional
import logging
from .product import Product

logger = logging.getLogger(__name__)


class ProductPillar:
    """
    Top-level organizational grouping that contains multiple products.
    Represents a business pillar with its associated products.
    """
    
    def __init__(self, name: str, description: Optional[str] = None):
        """
        Initialize ProductPillar
        
        Args:
            name (str): Name of the product pillar
            description (str, optional): Description of the pillar's purpose
        """
        self.name = name
        self.description = description
        self.products: List[Product] = []
        
        logger.info(f"ProductPillar '{name}' created")
    
    def add_product(self, product: Product) -> None:
        """
        Add a product to this pillar
        
        Args:
            product (Product): Product instance to add
        """
        if not isinstance(product, Product):
            raise TypeError("Expected Product instance")
        
        # Check for duplicate products
        if product.name in [p.name for p in self.products]:
            logger.warning(f"Product '{product.name}' already exists in pillar '{self.name}'")
            return
        
        self.products.append(product)
        logger.info(f"Product '{product.name}' added to pillar '{self.name}'")
    
    def remove_product(self, product_name: str) -> bool:
        """
        Remove a product from this pillar
        
        Args:
            product_name (str): Name of the product to remove
            
        Returns:
            bool: True if product was removed, False if not found
        """
        for i, product in enumerate(self.products):
            if product.name == product_name:
                removed_product = self.products.pop(i)
                logger.info(f"Product '{removed_product.name}' removed from pillar '{self.name}'")
                return True
        
        logger.warning(f"Product '{product_name}' not found in pillar '{self.name}'")
        return False
    
    def get_product(self, product_name: str) -> Optional[Product]:
        """
        Get a specific product by name
        
        Args:
            product_name (str): Name of the product to retrieve
            
        Returns:
            Optional[Product]: Product instance if found, None otherwise
        """
        for product in self.products:
            if product.name == product_name:
                return product
        return None
    
    def get_total_repos_count(self) -> int:
        """
        Get total number of repositories across all products in this pillar
        
        Returns:
            int: Total repository count
        """
        return sum(len(product.repos) for product in self.products)
    
    def __str__(self) -> str:
        return f"ProductPillar(name='{self.name}', products={len(self.products)})"
    
    def __repr__(self) -> str:
        return f"ProductPillar(name='{self.name}', description='{self.description}', products={len(self.products)})"

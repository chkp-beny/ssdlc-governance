"""
Product class - Product-level aggregation and ownership
Contains list of Repo objects and DevOps object
"""

from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class DevOps:
    """
    DevOps engineer contact information
    """
    
    def __init__(self, full_name: str, email: str):
        """
        Initialize DevOps contact
        
        Args:
            full_name (str): Full name of DevOps engineer
            email (str): Email address of DevOps engineer
        """
        self.full_name = full_name
        self.email = email
        
        # Basic email validation
        if "@" not in email:
            raise ValueError(f"Invalid email format: {email}")
        
        logger.debug(f"DevOps contact created: {full_name} ({email})")
    
    def __str__(self) -> str:
        return f"DevOps(name='{self.full_name}', email='{self.email}')"
    
    def __repr__(self) -> str:
        return f"DevOps(full_name='{self.full_name}', email='{self.email}')"


class Product:
    """
    Product-level aggregation containing repositories and DevOps ownership
    """
    
    def __init__(self, name: str, devops: Optional[DevOps] = None, description: Optional[str] = None):
        """
        Initialize Product
        
        Args:
            name (str): Product name
            devops (DevOps, optional): DevOps contact for this product
            description (str, optional): Product description
        """
        self.name = name
        self.devops = devops
        self.description = description
        self.repos: List = []  # Will contain Repo objects once implemented
        
        logger.info(f"Product '{name}' created")
    
    def set_devops(self, devops: DevOps) -> None:
        """
        Set or update DevOps contact for this product
        
        Args:
            devops (DevOps): DevOps contact instance
        """
        if not isinstance(devops, DevOps):
            raise TypeError("Expected DevOps instance")
        
        old_devops = self.devops.full_name if self.devops else "None"
        self.devops = devops
        logger.info(f"Product '{self.name}' DevOps contact updated: {old_devops} -> {devops.full_name}")
    
    def add_repo(self, repo) -> None:
        """
        Add a repository to this product
        Note: Repo parameter type will be specified once Repo class is implemented
        
        Args:
            repo: Repository instance to add
        """
        # TODO: Add type checking once Repo class is implemented
        # TODO: Check for duplicate repos
        
        self.repos.append(repo)
        logger.info(f"Repository added to product '{self.name}' (total repos: {len(self.repos)})")
    
    def remove_repo(self, repo_name: str) -> bool:
        """
        Remove a repository from this product
        
        Args:
            repo_name (str): Name of the repository to remove
            
        Returns:
            bool: True if repository was removed, False if not found
        """
        # TODO: Implement once Repo class has name attribute
        logger.warning(f"remove_repo not fully implemented - Repo class needed")
        return False
    
    def get_repos_count(self) -> int:
        """
        Get number of repositories in this product
        
        Returns:
            int: Repository count
        """
        return len(self.repos)
    
    def has_devops_contact(self) -> bool:
        """
        Check if product has DevOps contact assigned
        
        Returns:
            bool: True if DevOps contact exists
        """
        return self.devops is not None
    
    def __str__(self) -> str:
        devops_name = self.devops.full_name if self.devops else "No DevOps assigned"
        return f"Product(name='{self.name}', repos={len(self.repos)}, devops='{devops_name}')"
    
    def __repr__(self) -> str:
        return f"Product(name='{self.name}', description='{self.description}', repos={len(self.repos)}, devops={self.devops})"

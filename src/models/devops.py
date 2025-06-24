"""
DevOps class - DevOps engineer contact information
"""

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
        
        logger.debug("DevOps contact created: %s (%s)", full_name, email)
    
    def __str__(self) -> str:
        return f"DevOps(name='{self.full_name}', email='{self.email}')"
    
    def __repr__(self) -> str:
        return f"DevOps(full_name='{self.full_name}', email='{self.email}')"

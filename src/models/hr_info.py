"""
HRInfo class - Organizational ownership mapping
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class HRInfo:
    """
    Organizational ownership mapping
    """
    
    def __init__(self, product_name: str, repo_vp: Optional[str] = None, repo_gm: Optional[str] = None, 
                 repo_owner: Optional[str] = None):
        """
        Initialize HRInfo
        
        Args:
            product_name (str): Product name for HR mapping
            repo_vp (str, optional): Repository VP
            repo_gm (str, optional): Repository GM  
            repo_owner (str, optional): Repository owner
        """
        self.product_name = product_name
        self.repo_vp = repo_vp
        self.repo_gm = repo_gm
        self.repo_owner = repo_owner
        
        # TODO: Implement HR mapping logic from HR_DB.csv
        logger.debug("HRInfo created for product '%s' - TODO: populate from HR_DB.csv", product_name)
    
    def __str__(self) -> str:
        return f"HRInfo(product='{self.product_name}', vp='{self.repo_vp}', gm='{self.repo_gm}', owner='{self.repo_owner}')"
    
    def __repr__(self) -> str:
        return (f"HRInfo(product_name='{self.product_name}', repo_vp='{self.repo_vp}', repo_gm='{self.repo_gm}', "
                f"repo_owner='{self.repo_owner}')")

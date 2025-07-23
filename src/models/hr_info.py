"""
HRInfo class - Organizational ownership mapping
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class HRInfo:
    """
    Organizational ownership mapping with comprehensive HR data
    """
    
    def __init__(self, product_name: str, repo_vp: Optional[str] = None, repo_gm: Optional[str] = None, 
                 repo_owner: Optional[str] = None, title: Optional[str] = None, 
                 department: Optional[str] = None, manager_name: Optional[str] = None,
                 director: Optional[str] = None, vp2: Optional[str] = None, 
                 c_level: Optional[str] = None, worker_id: Optional[str] = None,
                 full_name: Optional[str] = None):
        """
        Initialize HRInfo
        
        Args:
            product_name (str): Product name for HR mapping
            repo_vp (str, optional): Repository VP (from VP 1)
            repo_gm (str, optional): Repository GM (from Sr. Manager (GM/CM))
            repo_owner (str, optional): Repository owner username
            title (str, optional): Job title
            department (str, optional): Department description
            manager_name (str, optional): Direct manager name
            director (str, optional): Director name
            vp2 (str, optional): Secondary VP (from VP 2)
            c_level (str, optional): C-level executive
            worker_id (str, optional): Employee worker ID
            full_name (str, optional): Full employee name
        """
        # Original fields (backward compatibility)
        self.product_name = product_name
        self.repo_vp = repo_vp
        self.repo_gm = repo_gm
        self.repo_owner = repo_owner
        
        # New enhanced HR fields
        self.title = title
        self.department = department
        self.manager_name = manager_name
        self.director = director
        self.vp2 = vp2
        self.c_level = c_level
        self.worker_id = worker_id
        self.full_name = full_name
        
        logger.debug("HRInfo created for product '%s' with enhanced HR data", product_name)
    
    def __str__(self) -> str:
        return f"HRInfo(product='{self.product_name}', owner='{self.repo_owner}', title='{self.title}', dept='{self.department}')"
    
    def __repr__(self) -> str:
        return (f"HRInfo(product_name='{self.product_name}', repo_vp='{self.repo_vp}', repo_gm='{self.repo_gm}', "
                f"repo_owner='{self.repo_owner}', title='{self.title}', department='{self.department}')")

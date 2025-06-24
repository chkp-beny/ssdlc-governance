"""
SCMInfo class - Source control management details
"""

from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SCMInfo:
    """
    Source control management details
    """
    
    def __init__(self, repo_name: str, full_name: str, id: str, default_branch: str, 
                 is_private: bool, created_in_compass_at: Optional[datetime] = None, 
                 updated_in_compass_at: Optional[datetime] = None):
        """
        Initialize SCMInfo
        
        Args:
            repo_name (str): Repository name
            full_name (str): Full repository name (owner/repo)
            id (str): Repository ID
            default_branch (str): Default branch name
            is_private (bool): Whether repository is private
            created_in_compass_at (datetime, optional): When repo was created in SCM
            updated_in_compass_at (datetime, optional): When repo was last updated in SCM
        """
        self.repo_name = repo_name
        self.full_name = full_name
        self.id = id
        self.default_branch = default_branch
        self.is_private = is_private
        self.created_in_compass_at = created_in_compass_at
        self.updated_in_compass_at = updated_in_compass_at
        
        logger.debug("SCMInfo created for repository: %s", repo_name)
    
    def __str__(self) -> str:
        return f"SCMInfo(name='{self.repo_name}', full_name='{self.full_name}')"
    
    def __repr__(self) -> str:
        return (f"SCMInfo(repo_name='{self.repo_name}', full_name='{self.full_name}', "
                f"id='{self.id}', is_private={self.is_private})")

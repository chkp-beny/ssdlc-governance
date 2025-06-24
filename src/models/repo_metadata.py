"""
RepoMetadata class - Core repository information
Contains SCMInfo and HRInfo objects with production flag
"""

from typing import Optional
import logging
from .scm_info import SCMInfo
from .hr_info import HRInfo

logger = logging.getLogger(__name__)


class RepoMetadata:
    """
    Core repository information aggregating SCM and HR data
    """
    
    def __init__(self, scm_info: SCMInfo, hr_info: Optional[HRInfo] = None, 
                 is_production: bool = False):
        """
        Initialize repository metadata
        
        Args:
            scm_info (SCMInfo): Source control management information
            hr_info (Optional[HRInfo]): Human resources/organizational information
            is_production (bool): Whether this is a production repository
        """
        self.scm_info = scm_info
        self.hr_info = hr_info
        self.is_production = is_production
        
        logger.debug("RepoMetadata created for repository: %s", scm_info.scm_name)
    
    def get_repository_name(self) -> str:
        """Get the SCM repository name"""
        return self.scm_info.scm_name
    
    def get_full_name(self) -> str:
        """Get the full repository name (org/repo)"""
        return self.scm_info.full_name
    
    def is_private_repo(self) -> bool:
        """Check if repository is private"""
        return self.scm_info.is_private
    
    def has_hr_info(self) -> bool:
        """Check if HR information is available"""
        return self.hr_info is not None
    
    def get_repo_owner(self) -> Optional[str]:
        """Get repository owner from HR info if available"""
        if self.hr_info:
            return self.hr_info.repo_owner
        return None
    
    def __str__(self) -> str:
        """String representation of repository metadata"""
        return f"RepoMetadata(name={self.scm_info.scm_name}, production={self.is_production})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"RepoMetadata(scm_name='{self.scm_info.scm_name}', "
                f"is_production={self.is_production}, "
                f"has_hr_info={self.has_hr_info()})")

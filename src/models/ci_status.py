"""
CI Status classes - Continuous Integration status aggregation
Contains SonarCIStatus and JfrogCIStatus objects
"""

from typing import Optional, Set
import logging

logger = logging.getLogger(__name__)


class SonarCIStatus:
    """
    SonarQube integration status
    """
    
    def __init__(self, is_exist: bool = False, project_key: Optional[str] = None, 
                 is_main_branch_scanned: bool = False):
        """
        Initialize SonarQube CI status
        
        Args:
            is_exist (bool): Whether SonarQube integration exists
            project_key (Optional[str]): SonarQube project key
            is_main_branch_scanned (bool): Whether main branch is scanned
        """
        self.is_exist = is_exist
        self.project_key = project_key
        self.is_main_branch_scanned = is_main_branch_scanned
        
        logger.debug("SonarCIStatus created: exists=%s, scanned=%s", 
                    is_exist, is_main_branch_scanned)
    
    def is_configured(self) -> bool:
        """Check if SonarQube is properly configured"""
        return self.is_exist and self.project_key is not None
    
    def is_scanning_active(self) -> bool:
        """Check if scanning is active on main branch"""
        return self.is_configured() and self.is_main_branch_scanned
    
    def set_exists(self, exists: bool, project_key: Optional[str] = None):
        """Set Sonar CI existence status and project key"""
        self.is_exist = exists
        if project_key:
            self.project_key = project_key
        logger.debug("SonarCIStatus.is_exist updated to: %s, project_key: %s", exists, project_key)
    
    def __str__(self) -> str:
        """String representation of Sonar CI status"""
        return f"SonarCI(exists={self.is_exist}, scanned={self.is_main_branch_scanned})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"SonarCIStatus(is_exist={self.is_exist}, "
                f"project_key='{self.project_key}', "
                f"is_main_branch_scanned={self.is_main_branch_scanned})")


class JfrogCIStatus:
    """
    JFrog integration status
    """
    
    def __init__(self, is_exist: bool = False, branch: Optional[str] = None, 
                 job_url: Optional[str] = None,
                 matched_build_names: Optional[Set[str]] = None):
        """
        Initialize JFrog CI status
        
        Args:
            is_exist (bool): Whether JFrog integration exists
            branch (Optional[str]): Branch being built
            job_url (Optional[str]): CI job URL
            matched_build_names (Optional[Set[str]]): Set of build names matched to this repository
        """
        self.is_exist = is_exist
        self.branch = branch
        self.job_url = job_url
        self.matched_build_names = matched_build_names or set()
        
        logger.debug("JfrogCIStatus created: exists=%s", is_exist)
    
    def is_configured(self) -> bool:
        """Check if JFrog is properly configured"""
        return self.is_exist
    
    def set_exists(self, exists: bool, branch: Optional[str] = None, 
                   job_url: Optional[str] = None, matched_build_names: Optional[Set[str]] = None):
        """Set JFrog CI existence status and optional metadata"""
        self.is_exist = exists
        if branch:
            self.branch = branch
        if job_url:
            self.job_url = job_url
        if matched_build_names is not None:
            self.matched_build_names = matched_build_names
        logger.debug("JfrogCIStatus.is_exist updated to: %s, branch: %s, builds: %s", 
                    exists, branch, len(matched_build_names) if matched_build_names else 0)
    
    def __str__(self) -> str:
        """String representation of JFrog CI status"""
        return f"JfrogCI(exists={self.is_exist}, builds={len(self.matched_build_names)})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"JfrogCIStatus(is_exist={self.is_exist}, "
                f"branch='{self.branch}', "
                f"builds_count={len(self.matched_build_names)})")


class CIStatus:
    """
    Continuous Integration status aggregation
    """
    
    def __init__(self, sonar_status: Optional[SonarCIStatus] = None, 
                 jfrog_status: Optional[JfrogCIStatus] = None):
        """
        Initialize CI status aggregation
        
        Args:
            sonar_status (Optional[SonarCIStatus]): SonarQube status
            jfrog_status (Optional[JfrogCIStatus]): JFrog status
        """
        self.sonar_status = sonar_status or SonarCIStatus()
        self.jfrog_status = jfrog_status or JfrogCIStatus()
        
        logger.debug("CIStatus created with Sonar and JFrog status")
    
    def is_fully_integrated(self) -> bool:
        """Check if both Sonar and JFrog are configured"""
        return (self.sonar_status.is_configured() and 
                self.jfrog_status.is_configured())
    
    def has_any_integration(self) -> bool:
        """Check if any CI integration exists"""
        return (self.sonar_status.is_exist or 
                self.jfrog_status.is_exist)
    
    def get_integration_summary(self) -> str:
        """Get summary of CI integrations"""
        sonar_status = "✓" if self.sonar_status.is_configured() else "✗"
        jfrog_status = "✓" if self.jfrog_status.is_configured() else "✗"
        return f"Sonar: {sonar_status}, JFrog: {jfrog_status}"
    
    def __str__(self) -> str:
        """String representation of CI status"""
        return f"CIStatus({self.get_integration_summary()})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"CIStatus(sonar_status={repr(self.sonar_status)}, "
                f"jfrog_status={repr(self.jfrog_status)})")

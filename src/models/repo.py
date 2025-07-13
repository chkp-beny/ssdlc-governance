"""
Repo class - Central repository representation and main aggregator
Contains SCMInfo, HRInfo, CIStatus, CDStatus, Vulnerabilities, and EnforcementStatus objects
"""

from typing import Optional, Dict, Any
import logging
from datetime import datetime
from .scm_info import SCMInfo

from .ci_status import CIStatus
from .cd_status import CDStatus
from .vulnerabilities import Vulnerabilities
from .enforcement_status import EnforcementStatus

logger = logging.getLogger(__name__)


class Repo:
    """
    Central repository representation and main aggregator for all repository-related information
    Now includes repo_owners (list of dicts with owner info) instead of hr_info.
    """

    def __init__(self, scm_info: SCMInfo, product_name: str, 
                 repo_owners: Optional[list] = None, is_production: bool = False):
        """
        Initialize repository with core information

        Args:
            scm_info (SCMInfo): Source control management information
            product_name (str): Product name for HR mapping
            repo_owners (Optional[list]): List of repository owners (dicts)
            is_production (bool): Whether this is a production repository
        """
        self.scm_info = scm_info
        self.product_name = product_name
        self.repo_owners = repo_owners or []
        self.is_production = is_production

        # These will be updated later, not on init
        self.ci_status: Optional[CIStatus] = None
        self.cd_status: Optional[CDStatus] = None
        self.vulnerabilities: Optional[Vulnerabilities] = None
        self.enforcement_status: Optional[EnforcementStatus] = None

        logger.debug("Repo created: %s", self.get_repository_name())
    
    @classmethod
    def from_json(cls, repo_data: Dict[str, Any], product_name: str) -> 'Repo':
        """
        Create Repo object from JSON response data

        Args:
            repo_data (Dict[str, Any]): Repository JSON data from API response
            product_name (str): Product name for HR mapping

        Returns:
            Repo: Configured repository object
        """
        logger.debug("Creating Repo from JSON data for: %s", repo_data.get('repo_name', 'unknown'))

        # Parse SCM information from JSON
        scm_info = SCMInfo(
            repo_name=repo_data.get('repo_name', ''),
            full_name=repo_data.get('full_name', ''),
            id=repo_data.get('github_id', str(repo_data.get('id', ''))),
            default_branch=repo_data.get('default_branch', 'main'),
            is_private=repo_data.get('is_private', False),
            created_in_compass_at=cls._parse_datetime(repo_data.get('repo_created_at')),
            updated_in_compass_at=cls._parse_datetime(repo_data.get('repo_updated_at'))
        )

        # Create repository object with empty repo_owners (to be filled later)
        repo = cls(
            scm_info=scm_info,
            product_name=product_name,
            repo_owners=[],
            is_production=False  # TODO: implement production detection logic
        )

        logger.info("Successfully created Repo object for: %s", repo.get_repository_name())
        return repo
    
    @staticmethod
    def _parse_datetime(datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from JSON"""
        if not datetime_str:
            return None
        try:
            # Handle ISO format with 'Z' suffix
            if datetime_str.endswith('Z'):
                datetime_str = datetime_str[:-1] + '+00:00'
            return datetime.fromisoformat(datetime_str)
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse datetime: %s - %s", datetime_str, str(e))
            return None
    
    # Update methods for CI status and vulnerabilities (called later)
    def update_ci_status(self, ci_status: CIStatus):
        """Update CI status information"""
        self.ci_status = ci_status
        logger.debug("CI status updated for repo: %s", self.get_repository_name())
    
    def update_vulnerabilities(self, vulnerabilities: Vulnerabilities):
        """Update vulnerability information"""
        self.vulnerabilities = vulnerabilities
        logger.debug("Vulnerabilities updated for repo: %s", self.get_repository_name())
    
    def update_cd_status(self, cd_status: CDStatus):
        """Update CD status information"""
        self.cd_status = cd_status
        logger.debug("CD status updated for repo: %s", self.get_repository_name())
    
    def update_enforcement_status(self, enforcement_status: EnforcementStatus):
        """Update enforcement status information"""
        self.enforcement_status = enforcement_status
        logger.debug("Enforcement status updated for repo: %s", self.get_repository_name())
    
    # Convenience methods for accessing information
    def get_repository_name(self) -> str:
        """Get repository name"""
        return self.scm_info.repo_name
    
    def get_full_name(self) -> str:
        """Get full repository name (org/repo)"""
        return self.scm_info.full_name
    
    def is_private_repo(self) -> bool:
        """Check if repository is private"""
        return self.scm_info.is_private
    
    def is_production_repo(self) -> bool:
        """Check if repository is production"""
        return self.is_production
    
    def get_scm_id(self) -> str:
        """Get SCM ID"""
        return self.scm_info.id
    
    def get_default_branch(self) -> str:
        """Get default branch"""
        return self.scm_info.default_branch
    

    
    def has_ci_status(self) -> bool:
        """Check if CI status information is available"""
        return self.ci_status is not None
    
    def has_vulnerabilities(self) -> bool:
        """Check if vulnerability information is available"""
        return self.vulnerabilities is not None
    
    def __str__(self) -> str:
        """String representation of repository"""
        return f"Repo(name={self.get_repository_name()}, product={self.product_name})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"Repo(name='{self.get_repository_name()}', "
                f"product='{self.product_name}', "
                f"is_production={self.is_production})")

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
        self.notes = []  # List to store notes for this repo

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
    
    def add_note(self, message: str):
        """Add a note to the repo"""
        if message not in self.notes:  # Avoid duplicates
            self.notes.append(message)

    def get_notes_display(self) -> str:
        """Format notes for report display with newlines"""
        return '\n'.join(self.notes) if self.notes else ""
    
    def get_primary_owner_dict(self) -> dict:
        """
        Returns the first owner dict in repo_owners with fallback logic.
        Applies title exclusion logic and skips owners not found in HRDB.
        Handles cases:
        1. No repo owners -> DevOps fallback + note  
        2. All owners not found in HRDB or have excluded titles -> DevOps fallback + note
        3. No DevOps mapping -> unknown + note
        """
        from CONSTANTS import EXCLUDED_OWNER_TITLES
        
        # Case: We have repo owners - search for suitable candidate
        if self.repo_owners and len(self.repo_owners) > 0:
            selected_owner = None
            
            for owner in self.repo_owners:
                if owner and owner.get('name'):
                    # Check if HRDB info is missing (not found in HRDB)
                    if self._is_hrdb_info_missing(owner):
                        # Skip owners not found in HRDB - continue searching
                        logger.debug("Skipped owner %s - not found in HRDB", 
                                   owner.get('name', 'unknown'))
                        continue
                    else:
                        # Owner found in HRDB - check title exclusion
                        owner_title = owner.get('title', '').strip()
                        if owner_title in EXCLUDED_OWNER_TITLES:
                            logger.debug("Skipped owner %s with excluded title: %s", 
                                       owner.get('name', 'unknown'), owner_title)
                            continue  # Skip this owner, try next one
                        else:
                            # Found a suitable owner - current employee with valid title
                            selected_owner = owner
                            break
            
            # If we found a suitable owner, return it
            if selected_owner:
                return selected_owner
            
            # No suitable owner found - all were either not in HRDB or had excluded titles
            # Try DevOps fallback
            devops_info = self._get_devops_fallback()
            if devops_info:
                self.add_note("All repo owners not found in HRDB or have excluded titles, used ownership fallback")
                return devops_info
            else:
                # No DevOps fallback available - use unknown
                self.add_note("All repo owners not found in HRDB or have excluded titles, no ownership fallback available")
                return self._get_empty_owner_dict()
        
        # Case: No repo owners at all - try DevOps fallback
        devops_info = self._get_devops_fallback()
        if devops_info:
            self.add_note("Ownership can not be decided, used ownership fallback")
            return devops_info
        else:
            # No DevOps mapping available
            self.add_note("Ownership can not be decided, no fallback for this app")
            return self._get_empty_owner_dict()

    def _is_hrdb_info_missing(self, owner: dict) -> bool:
        """Check if all HRDB fields are empty, None, or 'unknown' (user not found in HRDB)"""
        def is_empty_or_unknown(value):
            return (value is None or 
                    value == '' or 
                    value == 'unknown' or 
                    (isinstance(value, str) and value.strip() in ['', 'unknown']))
        
        return (is_empty_or_unknown(owner.get('general_manager')) and 
                is_empty_or_unknown(owner.get('vp')) and 
                is_empty_or_unknown(owner.get('title')) and
                is_empty_or_unknown(owner.get('director')))

    def _get_devops_fallback(self) -> Optional[dict]:
        """Get DevOps info and query HRDB once for all fields"""
        try:
            from CONSTANTS import PRODUCT_DEVOPS
            from src.services.hrdb_client import HRDBClient
            
            devops_map = PRODUCT_DEVOPS.get(self.product_name)
            if devops_map and devops_map.get('user_name'):
                hrdb_client = HRDBClient()
                devops_hr_info = hrdb_client.get_user_data(devops_map['user_name'])
                logger.debug("Using DevOps fallback for %s repo %s", self.product_name, self.get_repository_name())
                return {
                    'name': devops_map['user_name'],
                    'title': devops_hr_info.get('title', 'unknown'),
                    'general_manager': devops_hr_info.get('general_manager', 'unknown'),
                    'vp': devops_hr_info.get('vp', 'unknown'),
                    'director': devops_hr_info.get('director', 'unknown')
                }
        except (ImportError, KeyError) as e:
            logger.warning("Error getting DevOps fallback for %s: %s", self.product_name, str(e))
        
        return None

    def get_primary_owner_email(self) -> str:
        """
        Returns the email of the primary repo owner.
        Since get_primary_owner_dict() now skips users not found in HRDB,
        we always add @checkpoint.com for valid users.
        """
        owner = self.get_primary_owner_dict()
        if owner and owner.get('name') and owner.get('name') != 'unknown':
            return f"{owner['name']}@checkpoint.com"
        return "unknown"

    def get_primary_owner_general_manager(self) -> str:
        """
        Returns the general_manager of the first repo owner, or 'unknown' if not present.
        """
        owner = self.get_primary_owner_dict()
        if owner and owner.get('general_manager'):
            return owner['general_manager']
        return "unknown"

    def get_primary_owner_vp(self) -> str:
        """
        Returns the vp of the first repo owner, or 'unknown' if not present.
        """
        owner = self.get_primary_owner_dict()
        if owner and owner.get('vp'):
            return owner['vp']
        return "unknown"

    def get_primary_owner_title(self) -> str:
        """
        Returns the title of the first repo owner, or 'unknown' if not present.
        """
        owner = self.get_primary_owner_dict()
        if owner and owner.get('title'):
            return owner['title']
        return "unknown"

    def get_primary_owner_director(self) -> str:
        """
        Returns the director of the first repo owner, or 'unknown' if not present.
        """
        owner = self.get_primary_owner_dict()
        if owner and owner.get('director'):
            return owner['director']
        return "unknown"
    
    @staticmethod
    def _get_empty_owner_dict():
        return {
            'name': 'unknown',
            'title': 'unknown',
            'general_manager': 'unknown',
            'vp': 'unknown',
            'director': 'unknown'
        }
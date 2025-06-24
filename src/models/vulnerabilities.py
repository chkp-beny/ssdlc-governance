"""
Vulnerability classes - Vulnerability data aggregation
Contains SecretsVulnerabilities and DependenciesVulnerabilities objects
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DependenciesVulnerabilities:
    """
    Third-party dependency vulnerabilities
    """
    
    def __init__(self, critical_count: int = 0, high_count: int = 0, 
                 medium_count: int = 0, low_count: int = 0):
        """
        Initialize dependencies vulnerabilities
        
        Args:
            critical_count (int): Number of critical vulnerabilities
            high_count (int): Number of high severity vulnerabilities
            medium_count (int): Number of medium severity vulnerabilities
            low_count (int): Number of low severity vulnerabilities
        """
        self.critical_count = critical_count
        self.high_count = high_count
        self.medium_count = medium_count
        self.low_count = low_count
        
        logger.debug("DependenciesVulnerabilities created: C=%d, H=%d, M=%d, L=%d",
                    critical_count, high_count, medium_count, low_count)
    
    def get_total_count(self) -> int:
        """Get total vulnerability count"""
        return self.critical_count + self.high_count + self.medium_count + self.low_count
    
    def get_high_and_critical_count(self) -> int:
        """Get count of high and critical vulnerabilities"""
        return self.critical_count + self.high_count
    
    def has_critical_vulnerabilities(self) -> bool:
        """Check if there are critical vulnerabilities"""
        return self.critical_count > 0
    
    def has_any_vulnerabilities(self) -> bool:
        """Check if there are any vulnerabilities"""
        return self.get_total_count() > 0
    
    def get_severity_breakdown(self) -> str:
        """Get formatted severity breakdown"""
        return f"C:{self.critical_count}, H:{self.high_count}, M:{self.medium_count}, L:{self.low_count}"
    
    def __str__(self) -> str:
        """String representation of dependencies vulnerabilities"""
        return f"DepsVuln(total={self.get_total_count()})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"DependenciesVulnerabilities(critical={self.critical_count}, "
                f"high={self.high_count}, medium={self.medium_count}, "
                f"low={self.low_count})")


class SecretsVulnerabilities:
    """
    Exposed secrets and credentials vulnerabilities
    """
    
    def __init__(self, critical_count: int = 0, high_count: int = 0, 
                 medium_count: int = 0, low_count: int = 0):
        """
        Initialize secrets vulnerabilities
        
        Args:
            critical_count (int): Number of critical secret exposures
            high_count (int): Number of high severity secret exposures
            medium_count (int): Number of medium severity secret exposures
            low_count (int): Number of low severity secret exposures
        """
        self.critical_count = critical_count
        self.high_count = high_count
        self.medium_count = medium_count
        self.low_count = low_count
        
        logger.debug("SecretsVulnerabilities created: C=%d, H=%d, M=%d, L=%d",
                    critical_count, high_count, medium_count, low_count)
    
    def get_total_count(self) -> int:
        """Get total secrets vulnerability count"""
        return self.critical_count + self.high_count + self.medium_count + self.low_count
    
    def get_high_and_critical_count(self) -> int:
        """Get count of high and critical secret exposures"""
        return self.critical_count + self.high_count
    
    def has_critical_secrets(self) -> bool:
        """Check if there are critical secret exposures"""
        return self.critical_count > 0
    
    def has_any_secrets(self) -> bool:
        """Check if there are any secret exposures"""
        return self.get_total_count() > 0
    
    def get_severity_breakdown(self) -> str:
        """Get formatted severity breakdown"""
        return f"C:{self.critical_count}, H:{self.high_count}, M:{self.medium_count}, L:{self.low_count}"
    
    def __str__(self) -> str:
        """String representation of secrets vulnerabilities"""
        return f"SecretsVuln(total={self.get_total_count()})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"SecretsVulnerabilities(critical={self.critical_count}, "
                f"high={self.high_count}, medium={self.medium_count}, "
                f"low={self.low_count})")


class Vulnerabilities:
    """
    Vulnerability data aggregation
    """
    
    def __init__(self, secrets_vulns: Optional[SecretsVulnerabilities] = None,
                 dependencies_vulns: Optional[DependenciesVulnerabilities] = None):
        """
        Initialize vulnerability aggregation
        
        Args:
            secrets_vulns (Optional[SecretsVulnerabilities]): Secrets vulnerabilities
            dependencies_vulns (Optional[DependenciesVulnerabilities]): Dependencies vulnerabilities
        """
        self.secrets_vulns = secrets_vulns or SecretsVulnerabilities()
        self.dependencies_vulns = dependencies_vulns or DependenciesVulnerabilities()
        
        logger.debug("Vulnerabilities created with secrets and dependencies data")
    
    def get_total_vulnerability_count(self) -> int:
        """Get total count across all vulnerability types"""
        return (self.secrets_vulns.get_total_count() + 
                self.dependencies_vulns.get_total_count())
    
    def get_critical_vulnerability_count(self) -> int:
        """Get total critical vulnerability count"""
        return (self.secrets_vulns.critical_count + 
                self.dependencies_vulns.critical_count)
    
    def has_critical_vulnerabilities(self) -> bool:
        """Check if there are any critical vulnerabilities"""
        return (self.secrets_vulns.has_critical_secrets() or 
                self.dependencies_vulns.has_critical_vulnerabilities())
    
    def has_any_vulnerabilities(self) -> bool:
        """Check if there are any vulnerabilities"""
        return (self.secrets_vulns.has_any_secrets() or 
                self.dependencies_vulns.has_any_vulnerabilities())
    
    def get_vulnerability_summary(self) -> str:
        """Get summary of all vulnerabilities"""
        total = self.get_total_vulnerability_count()
        critical = self.get_critical_vulnerability_count()
        return f"Total: {total} (Critical: {critical})"
    
    def get_detailed_breakdown(self) -> str:
        """Get detailed breakdown by type"""
        secrets = self.secrets_vulns.get_severity_breakdown()
        deps = self.dependencies_vulns.get_severity_breakdown()
        return f"Secrets[{secrets}], Dependencies[{deps}]"
    
    def __str__(self) -> str:
        """String representation of vulnerabilities"""
        return f"Vulnerabilities(total={self.get_total_vulnerability_count()})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"Vulnerabilities(secrets_vulns={repr(self.secrets_vulns)}, "
                f"dependencies_vulns={repr(self.dependencies_vulns)})")

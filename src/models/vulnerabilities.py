"""
Vulnerability classes - Vulnerability data aggregation
Contains SecretsVulnerabilities and DependenciesVulnerabilities objects
"""

from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class DeployedArtifact:
    """
    Represents a deployed artifact with vulnerability information
    """
    
    def __init__(self, artifact_key: str, repo_name: str, critical_count: int = 0, 
                 high_count: int = 0, medium_count: int = 0, low_count: int = 0,
                 unknown_count: int = 0, artifact_type: str = "unknown", 
                 build_name: Optional[str] = None, build_number: Optional[str] = None,
                 created_at: Optional[str] = None, updated_at: Optional[str] = None):
        """
        Initialize deployed artifact
        
        Args:
            artifact_key (str): Full artifact key (e.g., "cyberint-docker-virtual/alert-service:latest")
            repo_name (str): Repository name extracted from artifact key
            critical_count (int): Number of critical vulnerabilities
            high_count (int): Number of high severity vulnerabilities
            medium_count (int): Number of medium severity vulnerabilities
            low_count (int): Number of low severity vulnerabilities
            unknown_count (int): Number of unknown severity vulnerabilities
            artifact_type (str): Type of artifact (docker, npm, maven, etc.)
            build_name (Optional[str]): Build name if available
            build_number (Optional[str]): Build number if available
            created_at (Optional[str]): When the artifact was created
            updated_at (Optional[str]): When the artifact was last updated
        """
        self.artifact_key = artifact_key
        self.repo_name = repo_name
        self.critical_count = critical_count
        self.high_count = high_count
        self.medium_count = medium_count
        self.low_count = low_count
        self.unknown_count = unknown_count
        self.artifact_type = artifact_type
        self.build_name = build_name
        self.build_number = build_number
        self.created_at = created_at
        self.updated_at = updated_at
        
        logger.debug("DeployedArtifact created: %s (%s) - C=%d, H=%d, M=%d, L=%d, U=%d",
                    artifact_key, repo_name, critical_count, high_count, medium_count, low_count, unknown_count)
    
    def get_total_count(self) -> int:
        """Get total vulnerability count for this artifact"""
        return self.critical_count + self.high_count + self.medium_count + self.low_count + self.unknown_count
    
    def get_high_and_critical_count(self) -> int:
        """Get count of high and critical vulnerabilities"""
        return self.critical_count + self.high_count
    
    def has_critical_vulnerabilities(self) -> bool:
        """Check if artifact has critical vulnerabilities"""
        return self.critical_count > 0
    
    def has_any_vulnerabilities(self) -> bool:
        """Check if artifact has any vulnerabilities"""
        return self.get_total_count() > 0
    
    def get_severity_breakdown(self) -> str:
        """Get formatted severity breakdown"""
        return f"C:{self.critical_count}, H:{self.high_count}, M:{self.medium_count}, L:{self.low_count}, U:{self.unknown_count}"
    
    @staticmethod
    def extract_repo_name_from_artifact_key(artifact_key: str) -> str:
        """
        Extract repository name from artifact key
        
        Examples:
        - "cyberint-docker-virtual/alert-service:latest" -> "alert-service"
        - "cyberint-npm-virtual/frontend-service/1.0.0" -> "frontend-service"
        - "maven-repo/com/checkpoint/security-service/1.2.3" -> "security-service"
        - "docker://staging/scoring-manager:5f0b0100..." -> "scoring-manager"
        """
        try:
            # Handle protocol prefixes like docker://
            if '://' in artifact_key:
                # Remove protocol prefix (e.g., "docker://staging/service:tag" -> "staging/service:tag")
                artifact_key = artifact_key.split('://', 1)[1]
            
            if '/' in artifact_key:
                # Split by '/' and look for service name patterns
                parts = artifact_key.split('/')
                
                # For docker artifacts: cyberint-docker-virtual/alert-service:latest
                # Or protocol format: staging/scoring-manager:hash
                if len(parts) >= 2 and 'docker' in parts[0]:
                    service_part = parts[1]
                    # Remove tag if present
                    if ':' in service_part:
                        service_part = service_part.split(':')[0]
                    return service_part
                elif len(parts) >= 2:
                    # For protocol format like staging/scoring-manager:hash
                    service_part = parts[-1]  # Take the last part
                    # Remove tag/hash if present
                    if ':' in service_part:
                        service_part = service_part.split(':')[0]
                    return service_part
                
                # For npm artifacts: cyberint-npm-virtual/frontend-service/1.0.0
                elif len(parts) >= 2 and 'npm' in parts[0]:
                    return parts[1]
                
                # For maven artifacts: maven-repo/com/checkpoint/security-service/1.2.3
                elif len(parts) >= 4:
                    return parts[-2]  # Second to last part is usually the artifact name
                
                # Default: take the last meaningful part
                else:
                    service_part = parts[-1]
                    # Remove version/tag if present
                    if ':' in service_part:
                        service_part = service_part.split(':')[0]
                    return service_part
            else:
                # No path separator, return as-is
                return artifact_key
                
        except Exception as e:
            logger.warning("Failed to extract repo name from artifact key '%s': %s", artifact_key, e)
            return artifact_key
    
    def __str__(self) -> str:
        """String representation of deployed artifact"""
        return f"Artifact({self.repo_name}, total={self.get_total_count()})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"DeployedArtifact(artifact_key='{self.artifact_key}', "
                f"repo_name='{self.repo_name}', critical={self.critical_count}, "
                f"high={self.high_count}, medium={self.medium_count}, "
                f"low={self.low_count}, unknown={self.unknown_count}, "
                f"created_at='{self.created_at}', updated_at='{self.updated_at}')")


class DependenciesVulnerabilities:
    """
    Third-party dependency vulnerabilities
    """
    
    def __init__(self, critical_count: int = 0, high_count: int = 0, 
                 medium_count: int = 0, low_count: int = 0, unknown_count: int = 0,
                 artifacts: Optional[List[DeployedArtifact]] = None):
        """
        Initialize dependencies vulnerabilities
        
        Args:
            critical_count (int): Number of critical vulnerabilities
            high_count (int): Number of high severity vulnerabilities
            medium_count (int): Number of medium severity vulnerabilities
            low_count (int): Number of low severity vulnerabilities
            unknown_count (int): Number of unknown severity vulnerabilities
            artifacts (Optional[List[DeployedArtifact]]): List of deployed artifacts
        """
        self.critical_count = critical_count
        self.high_count = high_count
        self.medium_count = medium_count
        self.low_count = low_count
        self.unknown_count = unknown_count
        self.artifacts = artifacts or []
        
        logger.debug("DependenciesVulnerabilities created: C=%d, H=%d, M=%d, L=%d, U=%d, artifacts=%d",
                    critical_count, high_count, medium_count, low_count, unknown_count, len(self.artifacts))
    
    def add_artifact(self, artifact: DeployedArtifact):
        """Add a deployed artifact to the list"""
        self.artifacts.append(artifact)
        # Update aggregated counts
        self.critical_count += artifact.critical_count
        self.high_count += artifact.high_count
        self.medium_count += artifact.medium_count
        self.low_count += artifact.low_count
        self.unknown_count += artifact.unknown_count
        
        logger.debug("Added artifact %s, new totals: C=%d, H=%d, M=%d, L=%d, U=%d",
                    artifact.repo_name, self.critical_count, self.high_count, 
                    self.medium_count, self.low_count, self.unknown_count)
    
    def get_artifacts_by_repo_name(self, repo_name: str) -> List[DeployedArtifact]:
        """Get all artifacts for a specific repository"""
        return [artifact for artifact in self.artifacts if artifact.repo_name == repo_name]
    
    def get_total_count(self) -> int:
        """Get total vulnerability count"""
        return self.critical_count + self.high_count + self.medium_count + self.low_count + self.unknown_count
    
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
        return f"C:{self.critical_count}, H:{self.high_count}, M:{self.medium_count}, L:{self.low_count}, U:{self.unknown_count}"
    
    def __str__(self) -> str:
        """String representation of dependencies vulnerabilities"""
        return f"DepsVuln(total={self.get_total_count()}, artifacts={len(self.artifacts)})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"DependenciesVulnerabilities(critical={self.critical_count}, "
                f"high={self.high_count}, medium={self.medium_count}, "
                f"low={self.low_count}, unknown={self.unknown_count}, artifacts_count={len(self.artifacts)})")


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

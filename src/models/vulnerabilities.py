"""
Vulnerability classes - Vulnerability data aggregation
Contains CodeVulnerabilities and DependenciesVulnerabilities objects
"""

from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class DeployedArtifact:
    """
    Represents a deployed artifact with vulnerability counts
    Contains artifact metadata and vulnerability severity breakdown
    """
    
    def __init__(self, artifact_key: str, repo_name: str, critical_count: int = 0, 
                 high_count: int = 0, medium_count: int = 0, low_count: int = 0,
                 unknown_count: int = 0, artifact_type: str = "unknown", 
                 build_name: Optional[str] = None, build_number: Optional[str] = None,
                 created_at: Optional[str] = None, updated_at: Optional[str] = None,
                 build_timestamp: Optional[str] = None, sha256: Optional[str] = None,
                 jfrog_path: Optional[str] = None):
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
            build_timestamp (Optional[str]): Build timestamp for JFrog matching
            sha256 (Optional[str]): SHA256 hash for JFrog matching
            jfrog_path (Optional[str]): Full JFrog path for the artifact
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
        self.build_timestamp = build_timestamp
        self.sha256 = sha256
        self.jfrog_path = jfrog_path
        self.is_latest = self._check_if_latest(artifact_key)
        
        logger.debug("DeployedArtifact created: %s (%s) - C=%d, H=%d, M=%d, L=%d, U=%d, is_latest=%s",
                    artifact_key, repo_name, critical_count, high_count, medium_count, low_count, unknown_count, self.is_latest)
    
    def _check_if_latest(self, artifact_key: str) -> bool:
        """
        Check if the artifact has 'latest' as a suffix
        
        Args:
            artifact_key (str): Full artifact key
            
        Returns:
            bool: True if artifact has 'latest' suffix
        """
        return artifact_key.endswith(':latest')
    
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
    
 
    def __str__(self) -> str:
        """String representation of deployed artifact"""
        return f"Artifact({self.repo_name}, total={self.get_total_count()})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"DeployedArtifact(artifact_key='{self.artifact_key}', "
                f"repo_name='{self.repo_name}', critical={self.critical_count}, "
                f"high={self.high_count}, medium={self.medium_count}, "
                f"low={self.low_count}, unknown={self.unknown_count}, "
                f"is_latest={self.is_latest}, "
                f"created_at='{self.created_at}', updated_at='{self.updated_at}')")


class DependenciesVulnerabilities:
    """
    Third-party dependency vulnerabilities
    Counters reflect either the 'latest' artifact or the artifact with most vulnerabilities
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
        
        # Update counters based on artifacts if provided
        if self.artifacts:
            self._update_counters_from_artifacts()
        
        logger.debug("DependenciesVulnerabilities created: C=%d, H=%d, M=%d, L=%d, U=%d, artifacts=%d",
                    self.critical_count, self.high_count, self.medium_count, self.low_count, self.unknown_count, len(self.artifacts))
    
    def add_artifact(self, artifact: DeployedArtifact):
        """Add a deployed artifact to the list and update counters"""
        self.artifacts.append(artifact)
        # Update counters based on the new artifact list
        self._update_counters_from_artifacts()
        
        logger.debug("Added artifact %s, new totals: C=%d, H=%d, M=%d, L=%d, U=%d",
                    artifact.repo_name, self.critical_count, self.high_count, 
                    self.medium_count, self.low_count, self.unknown_count)
    
    def _update_counters_from_artifacts(self):
        """
        Update counters based on the sum of vulnerabilities from all artifacts.
        """
        if not self.artifacts:
            self.critical_count = self.high_count = self.medium_count = self.low_count = self.unknown_count = 0
            return

        # Sum vulnerabilities from all artifacts
        self.critical_count = sum(artifact.critical_count for artifact in self.artifacts)
        self.high_count = sum(artifact.high_count for artifact in self.artifacts)
        self.medium_count = sum(artifact.medium_count for artifact in self.artifacts)
        self.low_count = sum(artifact.low_count for artifact in self.artifacts)
        self.unknown_count = sum(artifact.unknown_count for artifact in self.artifacts)
        
        logger.debug("Updated total counts from %d artifacts: C=%d, H=%d, M=%d, L=%d, U=%d",
                     len(self.artifacts), self.critical_count, self.high_count,
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
    
    def _normalize_build_name(self, name):
        return name.strip().lower() if name else None

    def _get_latest_artifact(self, build_name: str):
        # Return the artifact with the maximal build_timestamp for a given build_name (normalized)
        norm_build_name = self._normalize_build_name(build_name)
        logger.debug("[_get_latest_artifact] build_name=%s (normalized=%s)", build_name, norm_build_name)
        logger.debug("[_get_latest_artifact] All artifacts: %s", [
            {
                'artifact_key': a.artifact_key,
                'build_name': a.build_name,
                'build_name_normalized': self._normalize_build_name(a.build_name),
                'build_timestamp': a.build_timestamp,
                'critical_count': a.critical_count,
                'high_count': a.high_count
            } for a in self.artifacts
        ])
        candidates = [a for a in self.artifacts if self._normalize_build_name(a.build_name) == norm_build_name and a.build_timestamp]
        logger.debug("[_get_latest_artifact] Candidates for build_name '%s' (normalized='%s'): %s", build_name, norm_build_name, [
            {
                'artifact_key': a.artifact_key,
                'build_name': a.build_name,
                'build_name_normalized': self._normalize_build_name(a.build_name),
                'build_timestamp': a.build_timestamp,
                'critical_count': a.critical_count,
                'high_count': a.high_count
            } for a in candidates
        ])
        if not candidates:
            logger.warning("[_get_latest_artifact] No candidates found for build_name '%s' (normalized='%s')", build_name, norm_build_name)
            return None
        # build_timestamp is string, convert to int for comparison
        latest = max(candidates, key=lambda a: int(a.build_timestamp))
        logger.debug("[_get_latest_artifact] Latest candidate: %r", latest)
        return latest

    def _get_latest_artifacts_by_build(self, build_names):
        # Return a dict {build_name: latest_artifact} using normalized build names
        result = {}
        for build_name in build_names:
            latest = self._get_latest_artifact(build_name)
            if latest:
                result[build_name] = latest
        return result

    def get_critical_count(self, repo_publish_artifacts_type, matched_build_names):
        logger.debug("[get_critical_count] repo_publish_artifacts_type=%s, matched_build_names=%s", repo_publish_artifacts_type, matched_build_names)
        logger.debug("[get_critical_count] All artifacts: %s", [
            {
                'artifact_key': a.artifact_key,
                'build_name': a.build_name,
                'build_name_normalized': self._normalize_build_name(a.build_name),
                'build_timestamp': a.build_timestamp,
                'critical_count': a.critical_count,
                'high_count': a.high_count
            } for a in self.artifacts
        ])
        logger.debug("[get_critical_count] Normalized matched_build_names: %s", [self._normalize_build_name(bn) for bn in matched_build_names])
        if not matched_build_names:
            logger.debug("[get_critical_count] No matched_build_names, returning 0")
            return 0
        if repo_publish_artifacts_type == "mono":
            build_name = next(iter(matched_build_names))
            latest = self._get_latest_artifact(build_name)
            logger.debug("[get_critical_count] MONO: build_name=%s, latest=%r", build_name, latest)
            return latest.critical_count if latest else 0
        elif repo_publish_artifacts_type == "multi":
            latest_artifacts = self._get_latest_artifacts_by_build(matched_build_names)
            logger.debug("[get_critical_count] MULTI: latest_artifacts=%r", latest_artifacts)
            return sum(a.critical_count for a in latest_artifacts.values())
        else:
            logger.debug("[get_critical_count] Unknown repo_publish_artifacts_type: %s, returning 0", repo_publish_artifacts_type)
            return 0

    def get_high_count(self, repo_publish_artifacts_type, matched_build_names):
        logger.debug("[get_high_count] repo_publish_artifacts_type=%s, matched_build_names=%s", repo_publish_artifacts_type, matched_build_names)
        logger.debug("[get_high_count] All artifacts: %s", [
            {
                'artifact_key': a.artifact_key,
                'build_name': a.build_name,
                'build_name_normalized': self._normalize_build_name(a.build_name),
                'build_timestamp': a.build_timestamp,
                'critical_count': a.critical_count,
                'high_count': a.high_count
            } for a in self.artifacts
        ])
        logger.debug("[get_high_count] Normalized matched_build_names: %s", [self._normalize_build_name(bn) for bn in matched_build_names])
        if not matched_build_names:
            logger.debug("[get_high_count] No matched_build_names, returning 0")
            return 0
        if repo_publish_artifacts_type == "mono":
            build_name = next(iter(matched_build_names))
            latest = self._get_latest_artifact(build_name)
            logger.debug("[get_high_count] MONO: build_name=%s, latest=%r", build_name, latest)
            return latest.high_count if latest else 0
        elif repo_publish_artifacts_type == "multi":
            latest_artifacts = self._get_latest_artifacts_by_build(matched_build_names)
            logger.debug("[get_high_count] MULTI: latest_artifacts=%r", latest_artifacts)
            return sum(a.high_count for a in latest_artifacts.values())
        else:
            logger.debug("[get_high_count] Unknown repo_publish_artifacts_type: %s, returning 0", repo_publish_artifacts_type)
            return 0
        
    def __str__(self) -> str:
        """String representation of dependencies vulnerabilities"""
        return f"DepsVuln(total={self.get_total_count()}, artifacts={len(self.artifacts)})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"DependenciesVulnerabilities(critical={self.critical_count}, "
                f"high={self.high_count}, medium={self.medium_count}, "
                f"low={self.low_count}, unknown={self.unknown_count}, artifacts_count={len(self.artifacts)})")


class CodeIssues:
    """
    Code quality issues from SonarQube analysis
    Stores all types of issues: VULNERABILITY, CODE_SMELL, BUG, etc.
    """
    
    def __init__(self, issues_by_type: Optional[dict] = None, secrets_count: int = 0):
        """
        Initialize code issues with flexible type-based storage
        
        Args:
            issues_by_type (Optional[dict]): Dictionary mapping issue types to severity counts
                Example: {
                    "VULNERABILITY": {"CRITICAL": 3, "MAJOR": 2},
                    "CODE_SMELL": {"BLOCKER": 5, "CRITICAL": 22, "INFO": 25},
                    "BUG": {"MAJOR": 1, "MINOR": 3}
                }
            secrets_count (int): Number of secrets found in the code
        """
        self.issues_by_type = issues_by_type or {}
        self.secrets_count = secrets_count
        
        logger.debug("CodeIssues created with %d issue types: %s, secrets_count: %d", 
                    len(self.issues_by_type), list(self.issues_by_type.keys()), secrets_count)
    
    def add_issue_type(self, issue_type: str, severity_counts: dict):
        """
        Add or update an issue type with its severity counts
        
        Args:
            issue_type (str): Type of issue (VULNERABILITY, CODE_SMELL, BUG, etc.)
            severity_counts (dict): Dictionary of severity to count mapping
        """
        self.issues_by_type[issue_type] = severity_counts
        logger.debug("Added issue type '%s' with counts: %s", issue_type, severity_counts)
    
    def get_issue_types(self) -> List[str]:
        """Get list of all issue types present"""
        return list(self.issues_by_type.keys())
    
    def get_counts_for_type(self, issue_type: str) -> dict:
        """Get severity counts for a specific issue type"""
        return self.issues_by_type.get(issue_type, {})
    
    def get_total_count_for_type(self, issue_type: str) -> int:
        """Get total count for a specific issue type"""
        counts = self.get_counts_for_type(issue_type)
        return sum(counts.values())
    
    def get_critical_count_for_type(self, issue_type: str) -> int:
        """Get critical/blocker count for a specific issue type"""
        counts = self.get_counts_for_type(issue_type)
        return counts.get('CRITICAL', 0) + counts.get('BLOCKER', 0)
    
    def get_total_count(self) -> int:
        """Get total count across all issue types"""
        total = 0
        for type_counts in self.issues_by_type.values():
            total += sum(type_counts.values())
        return total
    
    def get_critical_count(self) -> int:
        """Get total critical/blocker count across all issue types"""
        total = 0
        for type_counts in self.issues_by_type.values():
            total += type_counts.get('CRITICAL', 0) + type_counts.get('BLOCKER', 0)
        return total
    
    def get_vulnerability_count(self) -> int:
        """Get total vulnerability count (for backward compatibility)"""
        return self.get_total_count_for_type('VULNERABILITY')
    
    def get_critical_vulnerability_count(self) -> int:
        """Get critical vulnerability count (for backward compatibility)"""
        return self.get_critical_count_for_type('VULNERABILITY')
    
    def get_secrets_count(self) -> int:
        """
        Get the count of secrets found in the code
        
        Returns:
            int: Number of secrets
        """
        return self.secrets_count
    
    def has_issues(self) -> bool:
        """Check if there are any issues"""
        return self.get_total_count() > 0
    
    def has_critical_issues(self) -> bool:
        """Check if there are any critical/blocker issues"""
        return self.get_critical_count() > 0
    
    def has_vulnerabilities(self) -> bool:
        """Check if there are vulnerability-type issues"""
        return self.get_vulnerability_count() > 0
    
    def has_critical_vulnerabilities(self) -> bool:
        """Check if there are critical vulnerabilities"""
        return self.get_critical_vulnerability_count() > 0
    
    
    def get_severity_breakdown(self) -> str:
        """Get formatted breakdown by issue type"""
        if not self.issues_by_type:
            return "No issues"
        
        breakdown_parts = []
        for issue_type, counts in self.issues_by_type.items():
            count_str = ", ".join(f"{sev}:{count}" for sev, count in counts.items())
            breakdown_parts.append(f"{issue_type}[{count_str}]")
        
        return "; ".join(breakdown_parts)
    
    # Backward compatibility properties
    @property
    def critical_count(self) -> int:
        """Backward compatibility: return critical vulnerability count"""
        return self.get_critical_vulnerability_count()
    
    @property
    def high_count(self) -> int:
        """Backward compatibility: return high vulnerability count"""
        vuln_counts = self.get_counts_for_type('VULNERABILITY')
        return vuln_counts.get('MAJOR', 0)
    
    @property
    def medium_count(self) -> int:
        """Backward compatibility: return medium vulnerability count"""
        vuln_counts = self.get_counts_for_type('VULNERABILITY')
        return vuln_counts.get('MINOR', 0)
    
    @property
    def low_count(self) -> int:
        """Backward compatibility: return low vulnerability count"""
        vuln_counts = self.get_counts_for_type('VULNERABILITY')
        return vuln_counts.get('INFO', 0)
    
    def __str__(self) -> str:
        """String representation of code issues"""
        return f"CodeIssues(total={self.get_total_count()}, types={len(self.issues_by_type)})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return f"CodeIssues(issues_by_type={self.issues_by_type})"


class Vulnerabilities:
    """
    Vulnerability data aggregation
    """
    
    def __init__(self, code_issues: Optional[CodeIssues] = None,
                 dependencies_vulns: Optional[DependenciesVulnerabilities] = None):
        """
        Initialize vulnerability aggregation
        
        Args:
            code_issues (Optional[CodeIssues]): Code quality issues from SonarQube
            dependencies_vulns (Optional[DependenciesVulnerabilities]): Dependencies vulnerabilities
        """
        self.code_issues = code_issues or CodeIssues()
        self.dependencies_vulns = dependencies_vulns or DependenciesVulnerabilities()
        
        logger.debug("Vulnerabilities created with code issues and dependencies data")
    
    # Backward compatibility property
    @property
    def code_vulns(self) -> CodeIssues:
        """Backward compatibility property for code_vulns -> code_issues"""
        return self.code_issues
    
    def get_total_vulnerability_count(self) -> int:
        """Get total count across all vulnerability types"""
        return (self.code_issues.get_total_count() + 
                self.dependencies_vulns.get_total_count())
    
    def get_critical_vulnerability_count(self) -> int:
        """Get total critical vulnerability count"""
        return (self.code_issues.critical_count + 
                self.dependencies_vulns.critical_count)
    
    def has_critical_vulnerabilities(self) -> bool:
        """Check if there are any critical vulnerabilities"""
        return (self.code_issues.has_critical_vulnerabilities() or 
                self.dependencies_vulns.has_critical_vulnerabilities())
    
    def has_any_vulnerabilities(self) -> bool:
        """Check if there are any vulnerabilities"""
        return (self.code_issues.has_issues() or 
                self.dependencies_vulns.has_any_vulnerabilities())
    
    def get_vulnerability_summary(self) -> str:
        """Get summary of all vulnerabilities"""
        total = self.get_total_vulnerability_count()
        critical = self.get_critical_vulnerability_count()
        return f"Total: {total} (Critical: {critical})"
    
    def get_detailed_breakdown(self) -> str:
        """Get detailed breakdown by type"""
        code = self.code_issues.get_severity_breakdown()
        deps = self.dependencies_vulns.get_severity_breakdown()
        return f"Code[{code}], Dependencies[{deps}]"
    
    def __str__(self) -> str:
        """String representation of vulnerabilities"""
        return f"Vulnerabilities(total={self.get_total_vulnerability_count()})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"Vulnerabilities(code_issues={repr(self.code_issues)}, "
                f"dependencies_vulns={repr(self.dependencies_vulns)})")

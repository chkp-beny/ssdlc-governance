import logging
from typing import Dict
from src.models.vulnerabilities import Vulnerabilities, DependenciesVulnerabilities, DeployedArtifact

logger = logging.getLogger(__name__)


class DeployedArtifactProcessor:
    """
    Handles deployed artifact creation and repository vulnerability updates.
    Extracted from Product class to follow service layer pattern.
    """
    
    @staticmethod
    def create_deployed_artifact(artifact_key: str, repo_name: str, vulnerabilities: dict, 
                               updated_at: str, build_name: str, jfrog_path: str, 
                               build_number=None, build_timestamp=None, sha256=None) -> DeployedArtifact:
        """
        Create DeployedArtifact object from vulnerability data
        
        Args:
            artifact_key (str): Full artifact key
            repo_name (str): Repository name
            vulnerabilities (dict): Vulnerability counts
            updated_at (str): Last updated timestamp
            build_name (str): Build name
            jfrog_path (str): Full JFrog path
            build_number (str, optional): Build number from AQL properties
            build_timestamp (str, optional): Build timestamp from AQL properties
            sha256 (str, optional): sha256 from AQL properties
            
        Returns:
            DeployedArtifact: Created artifact object
        """
        # Extract vulnerability counts
        critical_count = vulnerabilities.get('critical', 0)
        high_count = vulnerabilities.get('high', 0)
        medium_count = vulnerabilities.get('medium', 0)
        low_count = vulnerabilities.get('low', 0)
        unknown_count = vulnerabilities.get('unknown', 0)
        
        return DeployedArtifact(
            artifact_key=artifact_key,
            repo_name=repo_name,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            unknown_count=unknown_count,
            build_name=build_name,
            updated_at=updated_at,
            jfrog_path=jfrog_path,
            build_number=build_number,
            build_timestamp=build_timestamp,
            sha256=sha256
        )
    
    @staticmethod
    def update_repository_vulnerabilities(artifacts_by_repo: Dict) -> int:
        """
        Update repository vulnerabilities with deployed artifacts
        
        Args:
            artifacts_by_repo (dict): Dictionary with repository objects as keys and artifact lists as values
            
        Returns:
            int: Number of repositories updated
        """
        updated_count = 0
        
        for repo, artifacts in artifacts_by_repo.items():
            try:
                # repo is already a repository object, not a name
                repo_name = repo.scm_info.repo_name if repo.scm_info else "unknown"
                
                # Initialize vulnerabilities if not already initialized
                if repo.vulnerabilities is None:
                    repo.vulnerabilities = Vulnerabilities()
                
                # Create or update DependenciesVulnerabilities
                if repo.vulnerabilities.dependencies_vulns is None:
                    repo.vulnerabilities.dependencies_vulns = DependenciesVulnerabilities()
                
                # Add all artifacts to the dependencies vulnerabilities
                for artifact in artifacts:
                    repo.vulnerabilities.dependencies_vulns.add_artifact(artifact)
                
                updated_count += 1
                
                logger.info("✅ Updated vulnerabilities for repo '%s' with %d artifacts", 
                           repo_name, len(artifacts))
                
            except (ValueError, KeyError) as e:
                repo_name = repo.scm_info.repo_name if repo.scm_info else "unknown"
                logger.error("❌ Error updating vulnerabilities for repo '%s': %s", repo_name, str(e))
                continue
        
        return updated_count

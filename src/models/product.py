"""
Product class - Product-level aggregation and ownership
Contains list of Repo objects and DevOps object
"""

from typing import List, Optional
import logging
import os
from dotenv import load_dotenv
from .devops import DevOps
from .repo import Repo
from .vulnerabilities import Vulnerabilities, CodeIssues

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Product:
    """
    Product-level aggregation containing repositories and DevOps ownership
    """
    
    def __init__(self, name: str, scm_type: str, organization_id: str, devops: Optional[DevOps] = None):
        """
        Initialize Product
        
        Args:
            name (str): Product name
            scm_type (str): Source control management type (e.g., 'github')
            organization_id (str): Organization ID in Compass
            devops (DevOps, optional): DevOps contact for this product
        """
        self.name = name
        self.scm_type = scm_type
        self.organization_id = organization_id
        self.devops = devops
        self.repos: List[Repo] = []  # Contains Repo objects
        
        # Create DataLoader instance for this product
        self._initialize_data_loader()
        
        logger.info("Product '%s' created with DataLoader", name)
    
    def _initialize_data_loader(self):
        """
        Initialize DataLoader with API credentials from environment
        """
        try:
            from src.services.data_loader import DataLoader
        except ImportError:
            # Fallback for tests
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from src.services.data_loader import DataLoader
        
        # Get credentials from environment variables
        compass_token = os.getenv('COMPASS_ACCESS_TOKEN', '')
        compass_url = os.getenv('COMPASS_BASE_URL', '')
        
        # Initialize DataLoader (other API credentials can be added later)
        self.data_loader = DataLoader(
            compass_token=compass_token,
            compass_url=compass_url
        )
        
        logger.debug("DataLoader initialized for product '%s'", self.name)
    
    def load_repositories(self):
        """
        Load repositories for this product using DataLoader
        Fetches repositories based on product's SCM type and organization ID
        """
        try:
            # Load repositories using DataLoader with product's SCM info
            repo_data = self.data_loader.load_repositories(self.scm_type, self.organization_id)
            
            # Parse repo_data and create Repo objects
            self.repos = []
            for repo_json in repo_data:
                try:
                    repo = Repo.from_json(repo_json, self.name)
                    self.repos.append(repo)
                except (ValueError, KeyError) as e:
                    logger.warning("Failed to create Repo from JSON for %s: %s", 
                                  repo_json.get('repo_name', 'unknown'), str(e))
            
            logger.info("Successfully loaded %d repositories for product '%s'", len(self.repos), self.name)
            
        except (ImportError, ValueError) as e:
            logger.error("Error loading repositories for product '%s': %s", self.name, str(e))
    
    def load_ci_data(self):
        """
        Load CI data for all repositories in this product
        Main entry point for CI data loading - calls both JFrog and Sonar data loading
        """
        logger.info("Loading CI data for product '%s'", self.name)
        
        # Load JFrog CI data
        self._load_jfrog_ci_data()
        
        # Load Sonar CI data (placeholder for future implementation)
        self._load_sonar_ci_data()
        
        logger.info("CI data loading completed for product '%s'", self.name)
    
    def _load_jfrog_ci_data(self):
        """
        Load JFrog CI data for repositories in this product
        Updates JfrogCIStatus.is_exist for matching repositories
        """
        # TODO: Modify the logic here so it would be generic and can handle all products according to the plan.
        # Currently this logic will retrieve partial data (not including branch) and will work on projects with naming convention only.
        # Need to:
        # 1. Make it work for all products, not just those with naming conventions
        # 2. Include branch information in the CI status
        # 3. Handle different JFrog project structures and naming patterns
        # 4. Make the matching logic more robust and configurable per product
        try:
            # Import constants
            try:
                from CONSTANTS import PRODUCT_JFROG_PROJECT
            except ImportError:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
                from CONSTANTS import PRODUCT_JFROG_PROJECT
            
            # Get JFrog project name for this product
            jfrog_project = PRODUCT_JFROG_PROJECT.get(self.name, "")
            
            # Skip if no JFrog project configured
            if not jfrog_project:
                logger.info("No JFrog project configured for product '%s', skipping JFrog CI data loading", self.name)
                return
            
            # Initialize JFrog client
            jfrog_token = os.getenv('CYBERINT_JFROG_ACCESS_TOKEN', '')
            if not jfrog_token:
                logger.warning("CYBERINT_JFROG_ACCESS_TOKEN not found, skipping JFrog CI data loading")
                return
            
            from src.services.data_loader import JfrogClient
            jfrog_client = JfrogClient(jfrog_token)
            
            # Fetch build information (raw JSON)
            build_data = jfrog_client.fetch_all_project_builds(jfrog_project)
            
            # Process the JSON to extract build names
            build_names_set = set()
            builds = build_data.get('builds', [])
            for build in builds:
                uri = build.get('uri', '')
                if uri.startswith('/'):
                    build_name = uri[1:]  # Remove leading slash
                    if build_name:
                        build_names_set.add(build_name)
            
            logger.info("Found %d builds in JFrog for project '%s'", len(build_names_set), jfrog_project)
            
            # Update repository CI status
            updated_count = 0
            for repo in self.repos:
                # Ensure CI status is initialized
                if repo.ci_status is None:
                    from .ci_status import CIStatus
                    repo.update_ci_status(CIStatus())
                
                if repo.scm_info and repo.scm_info.repo_name:
                    if repo.scm_info.repo_name in build_names_set:
                        # Update JFrog CI status using setter method
                        repo.ci_status.jfrog_status.set_exists(True)
                        updated_count += 1
                        logger.debug("Updated JFrog CI status for repo '%s'", repo.scm_info.repo_name)
            
            logger.info("Updated JFrog CI status for %d/%d repositories in product '%s'", 
                       updated_count, len(self.repos), self.name)
            
        except (ImportError, KeyError, ValueError) as e:
            logger.error("Error loading JFrog CI data for product '%s': %s", self.name, str(e))
    
    def _load_sonar_ci_data(self):
        """
        Load Sonar CI data for repositories in this product
        Updates SonarCIStatus.is_exist and project_key for matching repositories
        """
        # TODO: Extend this logic to check the scanned branches for each project with Sonar API.
        # Currently only checking if projects exist, but should also verify which branches are being scanned
        # and update the is_main_branch_scanned field accordingly.
        try:
            logger.info("Loading Sonar CI data for product '%s'", self.name)
            
            # Fetch Sonar projects from Compass API using "sonarqube" type
            sonar_data = self.data_loader.load_repositories("sonarqube", self.organization_id)
            
            if not sonar_data:
                logger.info("No Sonar projects found for product '%s'", self.name)
                return
            
            # Extract project keys and detect prefix
            project_keys = []
            repo_names_set = set()
            prefix = ""
            
            for project in sonar_data:
                project_key = project.get('project_key', '')
                if project_key:
                    project_keys.append(project_key)
            
            if not project_keys:
                logger.warning("No project keys found in Sonar data")
                return
            
            # Detect prefix from first project key (format: "text-")
            first_project_key = project_keys[0]
            if '-' in first_project_key:
                prefix = first_project_key.split('-')[0] + '-'
                logger.info("Detected Sonar project key prefix: '%s'", prefix)
            else:
                logger.warning("Could not detect prefix from project key: %s", first_project_key)
                return
            
            # Extract repo names (remove prefix from project keys)
            for project_key in project_keys:
                if project_key.startswith(prefix):
                    repo_name = project_key[len(prefix):]  # Remove prefix
                    if repo_name:
                        repo_names_set.add(repo_name)
            
            logger.info("Found %d Sonar projects for product '%s' with prefix '%s'", 
                       len(repo_names_set), self.name, prefix)
            
            # Update repository CI status
            updated_count = 0
            for repo in self.repos:
                # Ensure CI status is initialized
                if repo.ci_status is None:
                    from .ci_status import CIStatus
                    repo.update_ci_status(CIStatus())
                
                if repo.scm_info and repo.scm_info.repo_name:
                    if repo.scm_info.repo_name in repo_names_set:
                        # Create full project key (prefix + repo name)
                        full_project_key = prefix + repo.scm_info.repo_name
                        # Update Sonar CI status using setter method
                        repo.ci_status.sonar_status.set_exists(True, full_project_key)
                        updated_count += 1
                        logger.debug("Updated Sonar CI status for repo '%s' with project_key '%s'", 
                                   repo.scm_info.repo_name, full_project_key)
            
            logger.info("Updated Sonar CI status for %d/%d repositories in product '%s'", 
                       updated_count, len(self.repos), self.name)
            
        except Exception as e:
            logger.error("Error loading Sonar CI data for product '%s': %s", self.name, str(e))

    def load_vulnerabilities(self):
        """
        Load vulnerability data for repositories in this product
        Updates Vulnerabilities objects for matching repositories
        """
        logger.info("Loading vulnerability data for product '%s'", self.name)
        
        # Load JFrog vulnerabilities
        self._load_jfrog_vulnerabilities()
        
        # Load Sonar vulnerabilities
        self._load_sonar_vulnerabilities()
        
        logger.info("Vulnerability data loading completed for product '%s'", self.name)
    
    def _load_jfrog_vulnerabilities(self):
        """
        Load JFrog vulnerability data for repositories in this product
        Updates DependenciesVulnerabilities objects for matching repositories
        """
        try:
            # Initialize CompassClient
            from src.services.data_loader import CompassClient
            compass_token = os.getenv('COMPASS_ACCESS_TOKEN', '')
            compass_url = os.getenv('COMPASS_BASE_URL', '')
            
            if not compass_token or not compass_url:
                logger.warning("Compass credentials not found, skipping JFrog vulnerability loading")
                return
            
            compass_client = CompassClient(compass_token, compass_url)
            
            # Fetch JFrog vulnerabilities for this organization
            jfrog_vulnerabilities = compass_client.fetch_jfrog_vulnerabilities(self.organization_id)
            
            if not jfrog_vulnerabilities:
                logger.info("No JFrog vulnerability data returned for organization '%s'", self.organization_id)
                return
            
            updated_count = 0
            
            # Process vulnerability data
            for artifact_key, vuln_data in jfrog_vulnerabilities.items():
                # Extract repository name from artifact key
                from src.models.vulnerabilities import DeployedArtifact
                repo_name = DeployedArtifact.extract_repo_name_from_artifact_key(artifact_key)
                
                # Find matching repository
                matching_repo = None
                for repo in self.repos:
                    if repo.get_repository_name() == repo_name:
                        matching_repo = repo
                        break
                
                if matching_repo:
                    # Ensure repository has vulnerability object initialized
                    if matching_repo.vulnerabilities is None:
                        from .vulnerabilities import Vulnerabilities
                        matching_repo.vulnerabilities = Vulnerabilities()
                    
                    # Parse vulnerability counts (including unknown)
                    vuln_counts = vuln_data.get('vulnerabilities', {})
                    critical = vuln_counts.get('critical', 0)
                    high = vuln_counts.get('high', 0)
                    medium = vuln_counts.get('medium', 0)
                    low = vuln_counts.get('low', 0)
                    unknown = vuln_counts.get('unknown', 0)  # Include unknown count
                    
                    # Extract timestamps
                    created_at = vuln_data.get('created_at')
                    updated_at = vuln_data.get('updated_at')
                    
                    # Create DeployedArtifact object (keep unknown count separate)
                    artifact = DeployedArtifact(
                        artifact_key=artifact_key,
                        repo_name=repo_name,
                        critical_count=critical,
                        high_count=high,
                        medium_count=medium,
                        low_count=low,
                        unknown_count=unknown,  # Keep unknown separate
                        artifact_type=self._extract_artifact_type(artifact_key),
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    
                    # Add artifact to repository's dependencies vulnerabilities
                    matching_repo.vulnerabilities.dependencies_vulns.add_artifact(artifact)
                    updated_count += 1
                    
                    logger.debug("Added JFrog vulnerability data for repo '%s': %s", 
                               repo_name, artifact.get_severity_breakdown())
            
            logger.info("Updated JFrog vulnerability data for %d artifacts in product '%s'", 
                       updated_count, self.name)
            
        except Exception as e:
            logger.error("Error loading JFrog vulnerability data for product '%s': %s", self.name, str(e))
    
    def _load_sonar_vulnerabilities(self):
        """
        Load SonarQube vulnerability data for repositories in this product
        Updates CodeVulnerabilities objects for matching repositories
        """
        try:
            # Initialize CompassClient
            from src.services.data_loader import CompassClient
            compass_token = os.getenv('COMPASS_ACCESS_TOKEN', '')
            compass_url = os.getenv('COMPASS_BASE_URL', '')
            
            if not compass_token or not compass_url:
                logger.warning("Compass credentials not found, skipping Sonar vulnerability loading")
                return
            
            compass_client = CompassClient(compass_token, compass_url)
            
            # Fetch SonarQube issues for this organization
            sonar_issues = compass_client.fetch_sonarqube_issues(self.organization_id)
            
            if not sonar_issues:
                logger.info("No SonarQube issues data returned for organization '%s'", self.organization_id)
                return
            
            # Also fetch SonarQube secrets data
            sonar_secrets = compass_client.fetch_sonarqube_secrets(self.organization_id)
            logger.info("Fetched SonarQube secrets data for %d projects", len(sonar_secrets))
            
            updated_count = 0
            
            # Import constants
            try:
                from CONSTANTS import PRODUCT_SONAR_PREFIX
            except ImportError:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
                from CONSTANTS import PRODUCT_SONAR_PREFIX
            
            # Get Sonar prefix for this product
            sonar_prefix = PRODUCT_SONAR_PREFIX.get(self.name, "")
            
            # Process SonarQube issues data
            for project_key, issues_data in sonar_issues.items():
                # Extract repository name from project key with improved prefix handling
                if sonar_prefix and project_key.startswith(sonar_prefix):
                    repo_name = project_key[len(sonar_prefix):]
                    # Handle case where separator is included in prefix
                    if repo_name.startswith('-'):
                        repo_name = repo_name[1:]
                else:
                    # No prefix or prefix doesn't match, use project key as-is
                    repo_name = project_key
                
                # Find matching repository
                matching_repo = None
                for repo in self.repos:
                    if repo.get_repository_name() == repo_name:
                        matching_repo = repo
                        break
                
                if matching_repo:
                    # Initialize vulnerabilities if not already initialized
                    if matching_repo.vulnerabilities is None:
                        matching_repo.vulnerabilities = Vulnerabilities()
                    
                    # Process all issue types dynamically (VULNERABILITY, CODE_SMELL, BUG, etc.)
                    issues_by_type = {}
                    
                    # Iterate through all issue types in the response
                    for issue_type, type_data in issues_data.items():
                        if 'issues' in type_data:
                            severity_counts = type_data['issues']
                            issues_by_type[issue_type] = severity_counts
                            
                            logger.debug("Collected '%s' issues for repo '%s': %s", 
                                       issue_type, repo_name, severity_counts)
                    
                    # Update the repository's code issues with all types
                    if issues_by_type:
                        # Check if we have secrets data for this project
                        secrets_count = 0
                        if sonar_secrets and project_key in sonar_secrets:
                            secrets_data = sonar_secrets[project_key]
                            # Extract secrets count from the response
                            # Assuming the API returns something like {"secrets_count": 5}
                            if isinstance(secrets_data, dict):
                                secrets_count = secrets_data.get('secrets_count', 0)
                            elif isinstance(secrets_data, int):
                                secrets_count = secrets_data
                            
                            logger.debug("Found %d secrets for project '%s'", secrets_count, project_key)
                        
                        # Create or update CodeIssues with all collected issue types and secrets
                        matching_repo.vulnerabilities.code_issues = CodeIssues(issues_by_type, secrets_count)
                        updated_count += 1
                        
                        logger.debug("Updated code issues for repo '%s' with %d issue types and %d secrets: %s", 
                                   repo_name, len(issues_by_type), secrets_count, list(issues_by_type.keys()))
            
            logger.info("Updated Sonar code issues data for %d repositories in product '%s'", 
                       updated_count, self.name)
            
        except Exception as e:
            logger.error("Error loading Sonar code issues data for product '%s': %s", self.name, str(e))
    
    def _extract_artifact_type(self, artifact_key: str) -> str:
        """
        Extract artifact type from artifact key
        
        Args:
            artifact_key (str): Full artifact key
            
        Returns:
            str: Artifact type (docker, npm, maven, etc.)
        """
        try:
            # Extract type before first :// if present
            if '://' in artifact_key:
                type_part = artifact_key.split('://')[0]
                return type_part.lower()
            else:
                return 'unknown'
        except Exception:
            return 'unknown'

    def get_repos_count(self) -> int:
        """
        Get number of repositories in this product
        
        Returns:
            int: Repository count
        """
        return len(self.repos)
    
    def __str__(self) -> str:
        devops_name = self.devops.full_name if self.devops else "No DevOps assigned"
        return f"Product(name='{self.name}', scm='{self.scm_type}', org_id='{self.organization_id}', repos={len(self.repos)}, devops='{devops_name}')"
    
    def __repr__(self) -> str:
        return f"Product(name='{self.name}', scm_type='{self.scm_type}', organization_id='{self.organization_id}', repos={len(self.repos)}, devops={self.devops})"

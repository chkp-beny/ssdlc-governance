# RASOS - Repository Assessment and Security Operations System

## Architecture Overview

RASOS is a comprehensive system for assessing and managing security operations across multiple software development repositories. It provides a unified view of CI/CD status, vulnerability assessments, and security compliance across different products and repositories.

**Recent Update**: The system has been refactored from a monolithic Product class to a modular, service-oriented architecture with specialized processors and coordinators for improved maintainability and extensibility.

## Modular Architecture

### Service Layer Architecture

```
Application Layer:
    └── generate_product_report.py
        └── ReportingManager

Product Management Layer:
    └── Product
        ├── load_repositories() → RepositoryCoordinator
        ├── load_ci_status() → CIStatusCoordinator  
        └── load_vulnerabilities() → VulnerabilityCoordinator

Repository Processing Layer:
    └── RepositoryCoordinator
        ├── GitHubRepoProcessor
        ├── BitbucketRepoProcessor
        └── GitLabRepoProcessor

CI Status Processing Layer:
    └── CIStatusCoordinator
        ├── JFrogCIProcessor
        └── SonarCIProcessor

Vulnerability Processing Layer:
    └── VulnerabilityCoordinator
        ├── JFrogVulnerabilityProcessor
        └── SonarVulnerabilityProcessor

External API Layer:
    ├── CompassClient
    ├── JFrogClient
    ├── SonarClient
    ├── GitHubClient
    ├── BitbucketClient
    └── HRDBClient
```

### Data Model Hierarchy

```
ProductPillar
    └── Product (1:N)
        ├── DevOps (1:1)
        └── Repos (1:N)
            └── Repository
                ├── SCMInfo (1:1)
                ├── repo_owners (list of dicts) 
                ├── CIStatus (1:1)
                │   ├── SonarCIStatus (1:1)
                │   └── JfrogCIStatus (1:1)
                ├── CDStatus (1:1)
                ├── Vulnerabilities (1:1)
                │   ├── CodeIssues (1:1)
                │   │   ├── issues_by_type (Dict)
                │   │   └── secrets_count (int)
                │   └── DependenciesVulnerabilities (1:1)
                │       └── DeployedArtifact (1:N)
                └── EnforcementStatus (1:1)
                    ├── EnforceSonarStatus (1:1)
                    └── EnforceXrayStatus (1:1)
```

## Model Classes Documentation

### 1. ProductPillar
**Purpose**: Top-level organizational unit representing business pillars
- **Contains**: List of Products
- **Properties**: 
  - `name`: Pillar name (e.g., "Infinity", "Quantum", "Harmony")
  - `products`: List of Product objects
- **Methods**: Product management and aggregation

### 2. Product
**Purpose**: Product-level orchestration with delegated processing to specialized coordinators
- **Contains**: List of Repositories, DevOps contact
- **Uses**: Specialized coordinator services for each data type
- **Properties**:
  - `name`: Product name (e.g., "Cyberint", "SaaS")
  - `scm_type`: Source control type ("github", "bitbucket_server", "gitlab")
  - `organization_id`: Organization ID in Compass system
  - `devops`: DevOps contact information
  - `repos`: List of Repository objects
- **Key Methods**:
  - `load_repositories()`: Delegates to RepositoryCoordinator
  - `load_ci_status()`: Delegates to CIStatusCoordinator
  - `load_vulnerabilities()`: Delegates to VulnerabilityCoordinator
- **Architecture**: Orchestrator pattern - coordinates specialized services rather than implementing logic directly

## Service Layer Components

### RepositoryCoordinator
**Purpose**: Orchestrates repository data collection from multiple SCM sources
- **Processors**: GitHubRepoProcessor, BitbucketRepoProcessor, GitLabRepoProcessor
- **Key Methods**:
  - `load_repositories()`: Load repos from appropriate SCM processor
  - `_populate_repository_owners()`: Enrich repos with owner data from SCM and HRDB
- **Integration**: Uses SCM-specific processors and HRDBClient for owner mapping

### CIStatusCoordinator  
**Purpose**: Coordinates CI status data collection from build systems
- **Processors**: JFrogCIProcessor, SonarCIProcessor
- **Key Methods**:
  - `load_ci_status()`: Update repos with CI status from all sources
- **Integration**: Manages JFrog build matching and SonarQube project mapping

### VulnerabilityCoordinator
**Purpose**: Orchestrates vulnerability data collection and processing
- **Processors**: JFrogVulnerabilityProcessor, SonarVulnerabilityProcessor  
- **Key Methods**:
  - `load_vulnerabilities()`: Update repos with vulnerability data from all sources
- **Integration**: Coordinates dependency and code vulnerability processing

### JFrogVulnerabilityProcessor
**Purpose**: Specialized processor for JFrog dependency vulnerabilities with enhanced AQL cache logic
- **Key Features**:
  - AQL cache management for artifact metadata
  - Build name extraction from properties array (e.g., "Diagnostics/web-engine-testing-service/staging" → "web-engine-testing-service")
  - Artifact-to-repository matching via build names
  - Full DeployedArtifact metadata population
- **Key Methods**:
  - `process_vulnerabilities()`: Main processing pipeline
  - `_extract_build_name_from_path()`: Extract clean build names from paths
  - `_match_artifact_to_repository()`: Match artifacts to repos using AQL cache and build names

### 3. Repo (Repository)
**Purpose**: Individual repository with all associated metadata and status
- **Contains**: All repository-specific data objects
- **Properties**:
  - `product_name`: Parent product name
  - `scm_info`: Source control metadata
  - `repo_owners`: List of repository owner dictionaries (replaces hr_info)
  - `ci_status`: CI/CD pipeline status
  - `cd_status`: Deployment status
  - `vulnerabilities`: Security vulnerability data
  - `enforcement_status`: Policy enforcement status
- **Key Methods**:
  - `get_repository_name()`: Extract repository name
  - `from_json()`: Create from API response
  - `get_primary_owner_dict()`: Get primary owner with fallback logic
  - `update_*()`: Update specific data objects
- **Owner Management**: Enhanced with HRDB integration and DevOps fallback logic

## Data Objects

### 4. SCMInfo
**Purpose**: Source control management information
- **Properties**:
  - `repo_name`: Repository name
  - `repo_url`: Repository URL
  - `default_branch`: Main branch name
  - `language`: Primary programming language
  - `repo_size`: Repository size metrics
  - `contributors_count`: Number of contributors
  - `created_at`/`updated_at`: Timestamps

### 5. Repository Owners
**Purpose**: Enhanced ownership information with HRDB integration
- **Structure**: List of owner dictionaries with full HR data
- **Properties per Owner**:
  - `name`: Repository owner username
  - `title`: Job title from HRDB
  - `general_manager`: GM from HRDB hierarchy  
  - `vp`: VP from HRDB hierarchy
  - `director`: Director from HRDB hierarchy
- **Features**:
  - HRDB integration for complete organizational hierarchy
  - DevOps fallback when owners not found in HRDB
  - Title exclusion logic for certain roles
  - Primary owner selection with smart fallback

### 6. CIStatus
**Purpose**: Continuous Integration pipeline status
- **Contains**: SonarCIStatus, JfrogCIStatus
- **Subclasses**:
  - **SonarCIStatus**: SonarQube integration status
    - `is_exist`: Project exists in SonarQube
    - `project_key`: SonarQube project identifier
    - `is_main_branch_scanned`: Main branch scan status
  - **JfrogCIStatus**: JFrog Artifactory integration status
    - `is_exist`: Build exists in JFrog
    - `matched_build_names`: Set of build names matched to this repository
    - `latest_build_info`: Most recent build metadata

### 7. CDStatus
**Purpose**: Continuous Deployment status
- **Properties**: Deployment pipeline information
- **Status**: Currently placeholder for future implementation

### 8. Vulnerabilities
**Purpose**: Container for all vulnerability data types
- **Contains**: CodeIssues, DependenciesVulnerabilities
- **Properties**:
  - `code_issues`: SonarQube code quality and security issues
  - `dependencies_vulns`: JFrog dependency vulnerability data

### 9. CodeIssues (formerly CodeVulnerabilities)
**Purpose**: SonarQube code quality and security issues aggregation
- **Properties**:
  - `issues_by_type`: Dictionary of issue types and their severity counts
    - Keys: Issue types (VULNERABILITY, CODE_SMELL, BUG, SECURITY_HOTSPOT, etc.)
    - Values: Severity breakdown dictionaries (INFO, MINOR, MAJOR, CRITICAL, BLOCKER)
  - `secrets_count`: Count of detected secrets/credentials
- **Key Methods**:
  - `get_vulnerabilities()`: Get VULNERABILITY type issues (backward compatibility)
  - `get_total_issues()`: Total issues across all types
  - `get_issues_by_type()`: Get specific issue type counts
  - `has_secrets()`: Check if secrets were detected
  - **Backward Compatibility**:
    - `vulnerability_count`: Property for total vulnerability count
    - `critical_count`, `high_count`, etc.: Vulnerability severity properties

### 10. DependenciesVulnerabilities
**Purpose**: JFrog dependency vulnerability aggregation
- **Contains**: List of DeployedArtifact objects
- **Properties**:
  - `artifacts`: List of deployed artifacts with vulnerability data
- **Key Methods**:
  - `add_artifact()`: Add artifact vulnerability data
  - `get_total_vulnerabilities()`: Aggregate vulnerability counts
  - `get_critical_artifacts()`: Artifacts with critical vulnerabilities

### 11. DeployedArtifact
**Purpose**: Individual artifact vulnerability information with enhanced build metadata
- **Properties**:
  - `artifact_key`: Full artifact identifier
  - `repo_name`: Associated JFrog repository (e.g., cyberint-docker-local)
  - `critical_count`, `high_count`, `medium_count`, `low_count`, `unknown_count`: Severity counts
  - `artifact_type`: Artifact type (docker, npm, maven, etc.)
  - `build_name`: Extracted build name (e.g., "web-engine-testing-service")
  - `build_number`: Build number from properties
  - `build_timestamp`: Build timestamp for sorting
  - `sha256`: Artifact checksum
  - `created_at`, `updated_at`: Timestamps
- **Key Methods**:
  - `get_total_count()`: Total vulnerability count
  - `get_high_and_critical_count()`: High-priority vulnerabilities
  - `has_critical_vulnerabilities()`: Critical vulnerability check
  - `extract_repo_name_from_artifact_key()`: Static method for name extraction

### 12. EnforcementStatus
**Purpose**: Policy enforcement status container
- **Contains**: EnforceSonarStatus, EnforceXrayStatus
- **Subclasses**:
  - **EnforceSonarStatus**: SonarQube quality gate enforcement
  - **EnforceXrayStatus**: JFrog Xray security policy enforcement

### 13. DevOps
**Purpose**: DevOps contact and ownership information
- **Properties**:
  - `full_name`: Contact person name
  - `email`: Contact email address

## Service Layer

### External API Clients

### 14. CompassClient
**Purpose**: Compass API integration client
- **Key Methods**:
  - `fetch_repositories()`: Get repository data
  - `fetch_jfrog_vulnerabilities()`: Get JFrog vulnerability data
  - `fetch_sonarqube_issues()`: Get SonarQube issues data
  - `fetch_sonarqube_secrets()`: Get SonarQube secrets count
  - `test_connection()`: Test API connectivity

### 15. JfrogClient
**Purpose**: JFrog Artifactory API integration with enhanced AQL support
- **Key Methods**:
  - `fetch_all_project_builds()`: Get build information
  - `query_aql_artifacts()`: Query artifact metadata using AQL
  - `query_aql_specific_artifacts()`: Optimized queries for specific artifacts
  - `test_connection()`: Test JFrog connectivity
- **Enhancement**: Added AQL query support for vulnerability artifact matching

### 16. Additional Clients
- **SonarClient**: SonarQube API integration
- **GitHubClient**: GitHub API integration  
- **BitbucketClient**: Bitbucket API integration
- **HRDBClient**: Internal HR database integration for owner mapping

## Configuration Constants

### Product Mappings
- **PILLAR_PRODUCTS**: Maps business pillars to products
- **PRODUCT_DEVOPS**: Maps products to DevOps contacts  
- **PRODUCT_SCM_TYPE**: Maps products to SCM types
- **PRODUCT_JFROG_PROJECT**: Maps products to JFrog projects
- **PRODUCT_SONAR_PREFIX**: Maps products to SonarQube prefixes

### Supported SCM Types
- `github`: GitHub repositories
- `bitbucket_server`: Bitbucket Server (on-premise)
- `gitlab`: GitLab repositories
- `sonarqube`: SonarQube projects (for CI status)

## API Integration Flow

### 1. Repository Loading (Enhanced)
```
Product.load_repositories()
    └── RepositoryCoordinator.load_repositories()
        ├── GitHubRepoProcessor.load_repositories()
        ├── BitbucketRepoProcessor.load_repositories()
        └── _populate_repository_owners()
            ├── Fetch recent PR reviewers from SCM
            └── Enrich with HRDB data via HRDBClient
```

### 2. CI Data Loading (Refactored)
```
Product.load_ci_status()
    └── CIStatusCoordinator.load_ci_status()
        ├── JFrogCIProcessor.process_ci_status()
        │   ├── JfrogClient.fetch_all_project_builds()
        │   ├── Parse build metadata and extract source repo info
        │   └── Match builds to repositories → Update JfrogCIStatus
        └── SonarCIProcessor.process_ci_status()
            ├── CompassClient.fetch_repositories("sonarqube")
            └── Map projects to repositories → Update SonarCIStatus
```

### 3. Vulnerability Loading (Enhanced)
```
Product.load_vulnerabilities()
    └── VulnerabilityCoordinator.load_vulnerabilities()
        ├── JFrogVulnerabilityProcessor.process_vulnerabilities()
        │   ├── CompassClient.fetch_jfrog_vulnerabilities()
        │   ├── Load AQL cache files for artifact metadata
        │   ├── Extract build names from properties array
        │   ├── Match artifacts to repositories via build names
        │   └── Create DeployedArtifact with full metadata
        └── SonarVulnerabilityProcessor.process_vulnerabilities()
            ├── CompassClient.fetch_sonarqube_issues()
            ├── CompassClient.fetch_sonarqube_secrets()
            └── Create CodeIssues with all issue types + secrets
```

## API Endpoints

### Compass API
- **Repositories**: `/repositories?type={scm_type}&organization_id={org_id}`
- **JFrog Vulnerabilities**: `/api/remediation/jfrog/vulnerabilities?organization_id={org_id}`
- **SonarQube Issues**: `/api/remediation/sonarqube/issues?organization_id={org_id}`
- **SonarQube Secrets**: `/api/remediation/sonarqube/secrets?organization_id={org_id}`

### JFrog API
- **Project Builds**: `/artifactory/api/build?project={project_name}`
- **Build Metadata**: `/artifactory/api/build/{build_name}?project={project_name}`
- **Build Details**: `/artifactory/api/build/{build_name}/{build_number}?project={project_name}`
- **AQL Artifacts Query**: `/artifactory/api/search/aql` (POST with AQL query)
- **System Ping**: `/xray/api/v1/system/ping`
- **Specific Artifacts AQL**: `/artifactory/api/search/aql` (POST with $or operator for multiple artifacts)

## Data Flow Architecture

### 1. Initialization (Modular)
1. Create ProductPillar with products from PILLAR_PRODUCTS
2. Initialize Product with SCM type and organization ID
3. Product creates specialized coordinators (Repository, CI, Vulnerability)
4. Each coordinator initializes appropriate processors and API clients
5. Processors establish connections to external services (Compass, JFrog, Sonar, etc.)

### 2. Data Loading Pipeline (Service-Oriented)
1. **Repository Discovery**: RepositoryCoordinator → SCM Processors → Repository objects
2. **Owner Enrichment**: HRDB integration for organizational hierarchy
3. **CI Status Assessment**: CIStatusCoordinator → Build system processors
4. **Vulnerability Analysis**: VulnerabilityCoordinator → Security data processors
5. **Data Aggregation**: Compile all data into unified repository objects

### 3. Integration Points (Enhanced)
- **Compass API**: Central data source for repositories, vulnerabilities, and SonarQube data
- **JFrog Artifactory**: Build information, AQL queries, and dependency vulnerabilities
- **SonarQube**: Code quality issues and secrets detection (via Compass)
- **SCM Systems**: Repository metadata and owner information (GitHub, Bitbucket, GitLab)
- **HRDB**: Organizational hierarchy and employee data for owner mapping
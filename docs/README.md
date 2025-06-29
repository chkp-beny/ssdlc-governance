# RASOS - Repository Assessment and Security Operations System

## Architecture Overview

RASOS is a comprehensive system for assessing and managing security operations across multiple software development repositories. It provides a unified view of CI/CD status, vulnerability assessments, and security compliance across different products and repositories.

## Object Model Architecture

### Core Hierarchy

```
ProductPillar
    └── Product (1:N)
        ├── DevOps (1:1)
        └── Repos (1:N)
            └── Repository
                ├── SCMInfo (1:1)
                ├── HRInfo (1:1) 
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

Services Layer:
    └── DataLoader
        ├── CompassClient
        └── JfrogClient
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
**Purpose**: Product-level aggregation containing repositories and DevOps ownership
- **Contains**: List of Repositories, DevOps contact
- **Uses**: DataLoader service for API operations
- **Properties**:
  - `name`: Product name (e.g., "Cyberint", "SaaS")
  - `scm_type`: Source control type ("github", "bitbucket_server", "gitlab")
  - `organization_id`: Organization ID in Compass system
  - `devops`: DevOps contact information
  - `repos`: List of Repository objects
  - `data_loader`: DataLoader service instance (initialized in constructor)
- **Key Methods**:
  - `load_repositories()`: Fetch repositories from SCM using DataLoader
  - `load_ci_data()`: Load CI/CD status data using DataLoader
  - `load_vulnerabilities()`: Load vulnerability data using DataLoader
  - `_load_jfrog_ci_data()`: JFrog CI status integration
  - `_load_sonar_ci_data()`: SonarQube CI status integration
  - `_load_jfrog_vulnerabilities()`: JFrog vulnerability data
  - `_load_sonar_vulnerabilities()`: SonarQube issues and secrets data

### 3. Repo (Repository)
**Purpose**: Individual repository with all associated metadata and status
- **Contains**: All repository-specific data objects
- **Properties**:
  - `product_name`: Parent product name
  - `scm_info`: Source control metadata
  - `hr_info`: Human resources/ownership info
  - `ci_status`: CI/CD pipeline status
  - `cd_status`: Deployment status
  - `vulnerabilities`: Security vulnerability data
  - `enforcement_status`: Policy enforcement status
- **Key Methods**:
  - `get_repository_name()`: Extract repository name
  - `from_json()`: Create from API response
  - `update_*()`: Update specific data objects

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

### 5. HRInfo
**Purpose**: Human resources and ownership information
- **Properties**:
  - `owner_name`: Repository owner
  - `owner_email`: Owner contact email
  - `team_name`: Responsible team
  - `last_activity`: Last activity timestamp

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
    - `build_name`: JFrog build identifier

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
**Purpose**: Individual artifact vulnerability information
- **Properties**:
  - `artifact_key`: Full artifact identifier
  - `repo_name`: Associated repository
  - `critical_count`, `high_count`, `medium_count`, `low_count`, `unknown_count`: Severity counts
  - `artifact_type`: Artifact type (docker, npm, maven, etc.)
  - `build_name`, `build_number`: Build information
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

### 14. DataLoader (Service)
**Purpose**: Service class that orchestrates all API calls for data fetching
- **Architecture**: Service layer component used by Product objects
- **Contains**: CompassClient, JfrogClient instances
- **Initialization**: Created by Product with API credentials from environment
- **Methods**:
  - `load_repositories()`: Fetch repository data from Compass API
  - `test_connections()`: Verify API connectivity for all clients
- **Usage**: Each Product creates its own DataLoader instance during initialization

### 15. CompassClient
**Purpose**: Compass API integration client
- **Key Methods**:
  - `fetch_repositories()`: Get repository data
  - `fetch_jfrog_vulnerabilities()`: Get JFrog vulnerability data
  - `fetch_sonarqube_issues()`: Get SonarQube issues data
  - `fetch_sonarqube_secrets()`: Get SonarQube secrets count
  - `test_connection()`: Test API connectivity

### 16. JfrogClient
**Purpose**: JFrog Artifactory API integration
- **Key Methods**:
  - `fetch_all_project_builds()`: Get build information
  - `test_connection()`: Test JFrog connectivity

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

### 1. Repository Loading
```
Product.load_repositories()
    └── DataLoader.load_repositories(scm_type, org_id)
        └── CompassClient.fetch_repositories()
            └── Parse JSON → Create Repo objects
```

### 2. CI Data Loading
```
Product.load_ci_data()
    ├── _load_jfrog_ci_data()
    │   └── JfrogClient.fetch_all_project_builds()
    │       └── Update JfrogCIStatus.is_exist
    └── _load_sonar_ci_data()
        └── CompassClient.fetch_repositories("sonarqube")
            └── Update SonarCIStatus (is_exist, project_key)
```

### 3. Vulnerability Loading
```
Product.load_vulnerabilities()
    ├── _load_jfrog_vulnerabilities()
    │   └── CompassClient.fetch_jfrog_vulnerabilities()
    │       └── Create DeployedArtifact objects
    │           └── Update DependenciesVulnerabilities
    └── _load_sonar_vulnerabilities()
        ├── CompassClient.fetch_sonarqube_issues()
        ├── CompassClient.fetch_sonarqube_secrets()
        └── Create CodeIssues objects with all issue types + secrets
```

## API Endpoints

### Compass API
- **Repositories**: `/repositories?type={scm_type}&organization_id={org_id}`
- **JFrog Vulnerabilities**: `/api/remediation/jfrog/vulnerabilities?organization_id={org_id}`
- **SonarQube Issues**: `/api/remediation/sonarqube/issues?organization_id={org_id}`
- **SonarQube Secrets**: `/api/remediation/sonarqube/secrets?organization_id={org_id}`

### JFrog API
- **Project Builds**: `/artifactory/api/build?project={project_name}`

## Data Flow Architecture

### 1. Initialization
1. Create ProductPillar with products from PILLAR_PRODUCTS
2. Initialize Product with SCM type and organization ID
3. Product creates DataLoader service instance with API credentials
4. DataLoader initializes API clients (CompassClient, JfrogClient)

### 2. Data Loading Pipeline
1. **Repository Discovery**: Load repositories from SCM
2. **CI Status Check**: Verify CI pipeline existence
3. **Vulnerability Assessment**: Fetch security vulnerability data
4. **Aggregation**: Compile data into unified objects

### 3. Integration Points
- **Compass API**: Central data source for repositories and vulnerabilities
- **JFrog Artifactory**: CI builds and dependency vulnerabilities
- **SonarQube**: Code quality issues and secrets detection

## Security and Vulnerability Management

### Issue Types Supported
- **VULNERABILITY**: Security vulnerabilities in code
- **CODE_SMELL**: Code quality issues
- **BUG**: Software bugs
- **SECURITY_HOTSPOT**: Potential security issues requiring review
- **Secrets**: Detected credentials and sensitive data

### Severity Levels
- **Critical/Blocker**: Immediate action required
- **High/Major**: High priority fixes
- **Medium/Minor**: Medium priority issues
- **Low/Info**: Low priority or informational

### Vulnerability Sources
- **Dependencies**: Third-party library vulnerabilities (JFrog Xray)
- **Code**: Static analysis security issues (SonarQube)
- **Secrets**: Hardcoded credentials and sensitive data (SonarQube)

## Testing Architecture

### Test Coverage
- **Unit Tests**: Individual model classes
- **Integration Tests**: API integration and data loading
- **Mock Data**: Comprehensive mock responses for all APIs

### Test Files
- `test_product_integration.py`: Full product data loading test
- `test_*_integration.py`: Individual API integration tests
- `test_*.py`: Unit tests for model classes

### Mock Data Files
- `mock_github_repositories_response.json`: Repository data
- `mock_jfrog_vulnerabilities_response.json`: JFrog vulnerability data
- `mock_sonarqube_issues_response.json`: SonarQube issues data
- `mock_sonarqube_secrets_response.json`: SonarQube secrets data
- `mock_jfrog_build_endpoint.json`: JFrog build data

## Environment Configuration

### Required Environment Variables
- `COMPASS_ACCESS_TOKEN`: Compass API authentication
- `COMPASS_BASE_URL`: Compass API base URL
- `CYBERINT_JFROG_ACCESS_TOKEN`: JFrog API authentication

### Configuration Files
- `CONSTANTS.py`: Product mappings and configuration
- `requirements.txt`: Python dependencies
- `.env`: Environment variables (not in repository)

## Recent Changes and Evolution

### CodeIssues Refactoring
- **From**: `CodeVulnerabilities` (vulnerability-specific)
- **To**: `CodeIssues` (flexible issue type support)
- **Benefits**: 
  - Supports all SonarQube issue types
  - Backward compatibility maintained
  - Extensible for future issue types

### Secrets Integration
- **New Feature**: SonarQube secrets detection
- **Implementation**: `secrets_count` field in CodeIssues
- **API**: New `/api/remediation/sonarqube/secrets` endpoint
- **Flow**: Integrated with existing SonarQube data loading

### Flexible Architecture
- **Design**: Extensible object model
- **APIs**: Multiple data source integration
- **Configuration**: Product-specific mappings
- **Testing**: Comprehensive mock data support

## Future Enhancements

### Planned Features
1. **Branch-specific CI scanning**: Track which branches are scanned
2. **Real-time updates**: Webhook integration for live data
3. **Policy enforcement**: Automated quality gate management
4. **Reporting**: Dashboard and metrics generation
5. **Additional integrations**: More security tools and platforms

### Architecture Improvements
1. **Caching**: API response caching for performance
2. **Async processing**: Concurrent data loading
3. **Configuration management**: Dynamic product configuration
4. **Error handling**: Robust error recovery and retry logic

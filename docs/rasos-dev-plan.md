# Development Plan - OOP Architecture

## Core Data Files
- **HR.csv**: Static file containing personnel information for ownership mapping
- **CONSTANTS.py**: Mappings for pillar→product and product→DevOps relationships

## Object Model Hierarchy

### ProductPillar
- **Contains**: List of Product objects
- **Purpose**: Top-level organizational grouping

### Product
- **Contains**: List of Repo objects, DevOps object
- **Purpose**: Product-level aggregation and ownership

### DevOps
- **Fields**: full_name (string), email (string)
- **Purpose**: DevOps engineer contact information

### Repo
- **Contains**: RepoMetadata object, CIStatus object, CDStatus object, Vulnerabilities object, EnforcementStatus object
- **Purpose**: Central repository representation and main aggregator for all repository-related information

### RepoMetadata
- **Contains**: SCMInfo object, HRInfo object
- **Fields**: is_production (boolean)
- **Purpose**: Core repository information

### SCMInfo
- **Fields**: scm_name, full_name, id, default_branch, is_private
- **Fields**: created_in_compass_at (datetime), updated_in_compass_at (datetime)
- **Purpose**: Source control management details

### HRInfo
- **Fields**: repo_vp (string), repo_gm (string), repo_owner (string)
- **Purpose**: Organizational ownership mapping

### CIStatus
- **Contains**: SonarCIStatus object, JfrogCIStatus object
- **Purpose**: Continuous Integration status aggregation

### SonarCIStatus
- **Fields**: is_exist, project_key, is_main_branch_scanned
- **Purpose**: SonarQube integration status

### JfrogCIStatus
- **Fields**: is_exist, branch, ci_platform, job_url, deployed_artifacts (List[string])
- **Purpose**: JFrog integration status

### CDStatus
- **Note**: Design pending - keep empty for initial implementation
- **Purpose**: Continuous Deployment status

### Vulnerabilities
- **Contains**: SecretsVulnerabilities object, DependenciesVulnerabilities object
- **Purpose**: Vulnerability data aggregation

### DependenciesVulnerabilities
- **Fields**: critical_count, high_count, medium_count, low_count
- **Note**: Will contain list of CVE objects with detailed vulnerability data
- **Purpose**: Third-party dependency vulnerabilities

### SecretsVulnerabilities
- **Fields**: critical_count, high_count, medium_count, low_count
- **Note**: Will contain list of detailed secret finding objects
- **Purpose**: Exposed secrets and credentials

### EnforcementStatus
- **Contains**: EnforceSonarStatus object, EnforceXrayStatus object
- **Purpose**: Policy enforcement verification

### EnforceSonarStatus
- **Note**: Design pending - keep empty for initial implementation
- **Purpose**: SonarQube policy enforcement

### EnforceXrayStatus
- **Note**: Design pending - keep empty for initial implementation
- **Purpose**: JFrog Xray policy enforcement

## Technical Stack
- **Backend**: Python with object-oriented design patterns
- **API Layer**: Flask for RESTful API endpoints
- **Frontend**: Streamlit for rapid dashboard development
- **Containerization**: Docker with docker-compose for orchestration
- **Data Sources**: JFrog API, SonarQube API, Compass API (internal)

## Implementation Principles
- **Modularity**: Each object is independently testable and extendable
- **Maintainability**: Clear separation of concerns enables easy field additions
- **Scalability**: Design supports incremental feature development
- **API-First**: All data retrieval through documented API interfaces
- **Comprehensive Logging**: Implement detailed logging at all levels (DEBUG, INFO, WARNING, ERROR) with structured logs for API calls, data validation, and missing data tracking to facilitate debugging and monitoring
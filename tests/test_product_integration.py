"""
Product Integration Test - Comprehensive test for Cyberint product
Tests initialization, repositories, CI data, and vulnerabilities
"""

import pytest
import sys
import os
from dotenv import load_dotenv

# Add src and root to path for imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
load_dotenv()

from src.models.product import Product
from CONSTANTS import PRODUCT_SCM_TYPE, PRODUCT_ORGANIZATION_ID


class TestProductIntegration:
    """Comprehensive integration test for Cyberint product"""

    def test_cyberint_product_complete_integration(self):
        """Test complete Cyberint product integration: repos, CI, vulnerabilities"""
        # Get Cyberint constants
        cyberint_scm_type = PRODUCT_SCM_TYPE["Cyberint"]
        cyberint_org_id = PRODUCT_ORGANIZATION_ID["Cyberint"]
        
        # Initialize Cyberint product
        cyberint_product = Product("Cyberint", cyberint_scm_type, cyberint_org_id)
        
        # 1. Test Repositories Loading
        print("\n=== Testing Repository Loading ===")
        cyberint_product.load_repositories()
        
        # Check that more than 30 repositories are loaded
        repo_count = cyberint_product.get_repos_count()
        assert repo_count > 30, f"Expected more than 30 repositories, got {repo_count}"
        print(f"✓ Loaded {repo_count} repositories (> 30)")
        
        # Print sample of 5 repositories
        sample_repos = [repo.get_repository_name() for repo in cyberint_product.repos[:5]]
        print(f"  Sample repositories: {sample_repos}")
        
        # Check that "alert-service" repository exists
        alert_service_repo = None
        for repo in cyberint_product.repos:
            if repo.get_repository_name() == "alert-service":
                alert_service_repo = repo
                break
        
        assert alert_service_repo is not None, "alert-service repository not found"
        print("✓ Found alert-service repository")
        
        # 2. Test CI Data Loading
        print("\n=== Testing CI Data Loading ===")
        cyberint_product.load_ci_data()
        
        # Check JFrog CI: frontend-service should be true
        frontend_service_repo = None
        for repo in cyberint_product.repos:
            if repo.get_repository_name() == "frontend-service":
                frontend_service_repo = repo
                break
        
        assert frontend_service_repo is not None, "frontend-service repository not found"
        assert frontend_service_repo.ci_status is not None, "frontend-service CI status not initialized"
        assert frontend_service_repo.ci_status.jfrog_status.is_exist is True, "frontend-service should have JFrog CI integration"
        print("✓ frontend-service has JFrog CI integration")
        print(f"  JFrog CI Status: {frontend_service_repo.ci_status.jfrog_status}")
        
        # Check Sonar CI: more than 30 repositories with integration, including alert-service
        sonar_integrated_count = 0
        alert_service_has_sonar = False
        
        for repo in cyberint_product.repos:
            if repo.ci_status and repo.ci_status.sonar_status.is_exist:
                sonar_integrated_count += 1
                if repo.get_repository_name() == "alert-service":
                    alert_service_has_sonar = True
        
        assert sonar_integrated_count > 30, f"Expected more than 30 repos with Sonar CI, got {sonar_integrated_count}"
        assert alert_service_has_sonar, "alert-service should have Sonar CI integration"
        print(f"✓ {sonar_integrated_count} repositories have Sonar CI integration (> 30)")
        print("✓ alert-service has Sonar CI integration")
        print(f"  Sonar CI Status: {alert_service_repo.ci_status.sonar_status}")
        
        # 3. Test Vulnerability Data Loading
        print("\n=== Testing Vulnerability Data Loading ===")
        cyberint_product.load_vulnerabilities()
        
        # Test JFrog vulnerabilities: frontend-service should have artifacts with at least 1 critical each
        frontend_service_vulns = frontend_service_repo.vulnerabilities
        assert frontend_service_vulns is not None, "frontend-service vulnerabilities not initialized"
        
        artifacts = frontend_service_vulns.dependencies_vulns.artifacts
        assert len(artifacts) > 3, f"Expected more than 3 artifacts for frontend-service, got {len(artifacts)}"
        print(f"✓ frontend-service has {len(artifacts)} deployed artifacts (> 3)")
        
        # Check that each artifact has at least 1 critical vulnerability
        for artifact in artifacts:
            assert artifact.critical_count >= 1, f"Artifact {artifact.artifact_key} should have at least 1 critical vulnerability, got {artifact.critical_count}"
        
        print("✓ All frontend-service artifacts have at least 1 critical vulnerability")
        
        # Check that dependencies counters match the latest artifact
        latest_artifact = None
        for artifact in artifacts:
            if artifact.is_latest:
                latest_artifact = artifact
                break
        
        assert latest_artifact is not None, "frontend-service should have a :latest artifact"
        
        deps_vulns = frontend_service_vulns.dependencies_vulns
        assert deps_vulns.critical_count == latest_artifact.critical_count, f"Dependencies critical count ({deps_vulns.critical_count}) should match latest artifact ({latest_artifact.critical_count})"
        assert deps_vulns.high_count == latest_artifact.high_count, f"Dependencies high count ({deps_vulns.high_count}) should match latest artifact ({latest_artifact.high_count})"
        assert deps_vulns.medium_count == latest_artifact.medium_count, f"Dependencies medium count ({deps_vulns.medium_count}) should match latest artifact ({latest_artifact.medium_count})"
        assert deps_vulns.low_count == latest_artifact.low_count, f"Dependencies low count ({deps_vulns.low_count}) should match latest artifact ({latest_artifact.low_count})"
        assert deps_vulns.unknown_count == latest_artifact.unknown_count, f"Dependencies unknown count ({deps_vulns.unknown_count}) should match latest artifact ({latest_artifact.unknown_count})"
        
        print(f"✓ frontend-service dependencies counters match latest artifact: {latest_artifact.artifact_key}")
        print(f"  Critical: {deps_vulns.critical_count}, High: {deps_vulns.high_count}, Medium: {deps_vulns.medium_count}, Low: {deps_vulns.low_count}, Unknown: {deps_vulns.unknown_count}")
        
        # Test Sonar issues: argosv2-ui should have various types of issues including vulnerabilities
        argosv2_ui_repo = None
        for repo in cyberint_product.repos:
            if repo.get_repository_name() == "argosv2-ui":
                argosv2_ui_repo = repo
                break
        
        assert argosv2_ui_repo is not None, "argosv2-ui repository not found"
        argosv2_ui_vulns = argosv2_ui_repo.vulnerabilities
        assert argosv2_ui_vulns is not None, "argosv2-ui vulnerabilities not initialized"
        
        code_issues = argosv2_ui_vulns.code_issues
        assert code_issues.has_vulnerabilities(), "argosv2-ui should have vulnerability-type issues"
        assert code_issues.get_critical_vulnerability_count() >= 1, f"argosv2-ui should have at least 1 critical vulnerability, got {code_issues.get_critical_vulnerability_count()}"
        
        # Print detailed breakdown of all issue types
        print(f"✓ argosv2-ui has {code_issues.get_critical_vulnerability_count()} critical vulnerabilities (≥ 1)")
        print(f"  Issue types found: {code_issues.get_issue_types()}")
        print(f"  Vulnerability issues: {code_issues.get_counts_for_type('VULNERABILITY')}")
        print(f"  Secrets count: {code_issues.get_secrets_count()}")
        if 'CODE_SMELL' in code_issues.get_issue_types():
            print(f"  Code smell issues: {code_issues.get_counts_for_type('CODE_SMELL')}")
        if 'BUG' in code_issues.get_issue_types():
            print(f"  Bug issues: {code_issues.get_counts_for_type('BUG')}")
        
        # Summary
        print("\n=== Integration Test Summary ===")
        print(f"✓ Product: {cyberint_product.name}")
        print(f"✓ Repositories loaded: {repo_count}")
        print(f"✓ JFrog CI integrations: {sum(1 for r in cyberint_product.repos if r.ci_status and r.ci_status.jfrog_status.is_exist)}")
        print(f"✓ Sonar CI integrations: {sonar_integrated_count}")
        print(f"✓ Repositories with JFrog vulnerabilities: {sum(1 for r in cyberint_product.repos if r.vulnerabilities and r.vulnerabilities.dependencies_vulns.artifacts)}")
        
        # Let's debug the Sonar issues count (all types)
        sonar_issue_repos = []
        sonar_vuln_repos = []
        for r in cyberint_product.repos:
            if r.vulnerabilities and r.vulnerabilities.code_issues.has_issues():
                issue_info = {
                    'name': r.get_repository_name(),
                    'total_issues': r.vulnerabilities.code_issues.get_total_count(),
                    'vulnerabilities': r.vulnerabilities.code_issues.get_vulnerability_count(),
                    'secrets_count': r.vulnerabilities.code_issues.get_secrets_count(),
                    'issue_types': r.vulnerabilities.code_issues.get_issue_types()
                }
                sonar_issue_repos.append(issue_info)
                
                # Separate count for vulnerability-specific issues
                if r.vulnerabilities.code_issues.has_vulnerabilities():
                    sonar_vuln_repos.append((r.get_repository_name(), r.vulnerabilities.code_issues.get_vulnerability_count()))
        
        print(f"✓ Repositories with Sonar issues (all types): {len(sonar_issue_repos)}")
        print(f"✓ Repositories with Sonar vulnerabilities specifically: {len(sonar_vuln_repos)}")
        if sonar_issue_repos:
            # Show sample of first 3 repositories with detailed breakdown
            print("  Sample repos with Sonar issues:")
            for repo_info in sonar_issue_repos[:3]:
                print(f"    {repo_info['name']}: {repo_info['total_issues']} total issues, {repo_info['vulnerabilities']} vulnerabilities, {repo_info['secrets_count']} secrets, types: {repo_info['issue_types']}")
        if sonar_vuln_repos:
            print(f"  Sample repos with vulnerabilities: {sonar_vuln_repos[:3]}")
        print("✓ All integration tests passed!")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

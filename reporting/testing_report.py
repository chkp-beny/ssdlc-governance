import json
from .product_report import ProductReport
from CONSTANTS import PRODUCT_SCM_TYPE
from src.utils.serialization import serialize_recursive
import os
from datetime import datetime


class TestingReport(ProductReport):
    report_type = "testing"
    columns = [
        'product', 'scm', 'repo_name',
        'repo_owner', 'group_manager', 'director', 'vp',
        'status_scan_dependencies_jfrog', 'map_build_names_to_method',
        'status_build_names_jfrog', 'status_scan_sast_sonar',
        'repo_publish_artifacts_type',
        'critical_dependencies_vulnerabilities_jfrog',
        'high_dependencies_vulnerabilities_jfrog',
        'deployed_artifacts_dependencies_vulnerabilities',
        'critical_code_vulnerabilities_sonar',
        'critical_code_secrets_sonar',
        'prevent_on_code_push_to_scm',
        'prevent_on_artifact_push_to_registry',
        'prevent_on_artifact_pull_from_registry',
        'notes'
    ]
    output_format = "csv"

    def extract_repo_data(self, repo, product_name: str) -> dict:
        data = {col: "unhandled yet" for col in self.columns}
        data['product'] = product_name
        data['scm'] = PRODUCT_SCM_TYPE.get(product_name, 'unknown')
        data['repo_name'] = getattr(repo, 'get_repository_name', lambda: 'unknown')()
        data['repo_owner'] = repo.get_primary_owner_email() if hasattr(repo, 'get_primary_owner_email') else "unknown"
        data['group_manager'] = repo.get_primary_owner_general_manager() if hasattr(repo, 'get_primary_owner_general_manager') else "unknown"
        data['director'] = repo.get_primary_owner_director() if hasattr(repo, 'get_primary_owner_director') else "unknown"
        data['vp'] = repo.get_primary_owner_vp() if hasattr(repo, 'get_primary_owner_vp') else "unknown"
        # JFrog/CI status
        data['status_scan_dependencies_jfrog'] = False
        data['status_build_names_jfrog'] = 'None'
        data['map_build_names_to_method'] = '{}'
        # Sonar/CI status
        data['status_scan_sast_sonar'] = False
        # Vulnerabilities
        data['repo_publish_artifacts_type'] = "unhandled yet"
        data['critical_dependencies_vulnerabilities_jfrog'] = 0
        data['high_dependencies_vulnerabilities_jfrog'] = 0
        data['deployed_artifacts_dependencies_vulnerabilities'] = '{}'
        data['critical_code_vulnerabilities_sonar'] = 0
        data['critical_code_secrets_sonar'] = 0
        data['prevent_on_code_push_to_scm'] = "unhandled yet"
        data['prevent_on_artifact_push_to_registry'] = "unhandled yet"
        data['prevent_on_artifact_pull_from_registry'] = "unhandled yet"

        # JFrog/CI status
        if hasattr(repo, 'ci_status') and repo.ci_status:
            if hasattr(repo.ci_status, 'jfrog_status') and repo.ci_status.jfrog_status:
                data['status_scan_dependencies_jfrog'] = repo.ci_status.jfrog_status.is_exist
                if hasattr(repo.ci_status.jfrog_status, 'matched_build_names') and repo.ci_status.jfrog_status.matched_build_names:
                    build_names_list = sorted(list(repo.ci_status.jfrog_status.matched_build_names))
                    data['status_build_names_jfrog'] = json.dumps(build_names_list)
                elif repo.ci_status.jfrog_status.is_exist:
                    data['status_build_names_jfrog'] = '[]'
                # Map build names to method (dict: build_name -> method)
                mapping_methods = getattr(repo.ci_status.jfrog_status, 'build_name_mapping_methods', None)
                if mapping_methods and isinstance(mapping_methods, dict) and mapping_methods:
                    data['map_build_names_to_method'] = json.dumps(mapping_methods)
                else:
                    data['map_build_names_to_method'] = '{}'
                # Add mono/multi field
                data['repo_publish_artifacts_type'] = getattr(repo.ci_status.jfrog_status, 'repo_publish_artifacts_type', 'unhandled yet')
            if hasattr(repo.ci_status, 'sonar_status') and repo.ci_status.sonar_status:
                data['status_scan_sast_sonar'] = repo.ci_status.sonar_status.is_exist

        # Vulnerabilities
        if hasattr(repo, 'vulnerabilities') and repo.vulnerabilities:
            vuln = repo.vulnerabilities
            if hasattr(vuln, 'dependencies_vulns') and vuln.dependencies_vulns:
                deps_vuln = vuln.dependencies_vulns
                jfrog_status = getattr(getattr(repo, 'ci_status', None), 'jfrog_status', None)
                if jfrog_status and jfrog_status.is_exist:
                    data['critical_dependencies_vulnerabilities_jfrog'] = deps_vuln.critical_count
                    data['high_dependencies_vulnerabilities_jfrog'] = deps_vuln.high_count
                else:
                    data['critical_dependencies_vulnerabilities_jfrog'] = "Not Integrated"
                    data['high_dependencies_vulnerabilities_jfrog'] = "Not Integrated"
                deployed_artifacts_data = {}
                if hasattr(deps_vuln, 'artifacts') and deps_vuln.artifacts:
                    for artifact in deps_vuln.artifacts:
                        artifact_name = getattr(artifact, 'artifact_key', getattr(artifact, 'jfrog_path', 'unknown'))
                        critical_count = getattr(artifact, 'critical_count', 0)
                        high_count = getattr(artifact, 'high_count', 0)
                        if critical_count > 0 or high_count > 0:
                            deployed_artifacts_data[artifact_name] = {
                                'critical': critical_count,
                                'high': high_count
                            }
                data['deployed_artifacts_dependencies_vulnerabilities'] = json.dumps(deployed_artifacts_data)
            if hasattr(vuln, 'code_issues') and vuln.code_issues:
                code_issues = vuln.code_issues
                sonar_status = getattr(getattr(repo, 'ci_status', None), 'sonar_status', None)
                if sonar_status and sonar_status.is_exist:
                    data['critical_code_secrets_sonar'] = code_issues.get_secrets_count() if hasattr(code_issues, 'get_secrets_count') else 0
                    data['critical_code_vulnerabilities_sonar'] = code_issues.get_critical_vulnerability_count() if hasattr(code_issues, 'get_critical_vulnerability_count') else 0
                else:
                    data['critical_code_secrets_sonar'] = "Not Integrated"
                    data['critical_code_vulnerabilities_sonar'] = "Not Integrated"
        data['notes'] = repo.get_notes_display()
        return data

    def generate_report(self, output_dir: str) -> str:
        # Generate the CSV report as usual
        csv_path = super().generate_report(output_dir)

        # Use cached products for JSON serialization
        all_products = self.load_all_products()
        serialized = {}
        for product in all_products:
            serialized[product.name] = [serialize_recursive(repo) for repo in product.repos]

        # Save JSON file in the same output directory as the CSV
        json_filename = f"{self.report_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_path = os.path.join(output_dir, json_filename)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(serialized, f, indent=2)
        print(f"✅ Generated JSON file: {json_path}")
        return csv_path

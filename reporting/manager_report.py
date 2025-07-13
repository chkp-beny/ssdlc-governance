import json
from .product_report import ProductReport
from CONSTANTS import PILLAR_PRODUCTS, PRODUCT_SCM_TYPE


class ManagerReport(ProductReport):
    report_type = "manager"
    columns = [
        'product_pillar', 'product', 'scm', 'repo_name', 'repo_type',
        'repo_owner', 'general_manager', 'vp',
        'status_scan_dependencies_jfrog', 'status_scan_sast_sonar',
        'critical_dependencies_vulnerabilities_jfrog',
        'high_dependencies_vulnerabilities_jfrog',
        'critical_code_vulnerabilities_sonar',
        'critical_code_secrets_sonar',
        'prevent_on_code_push_to_scm',
        'prevent_on_artifact_push_to_registry',
        'prevent_on_artifact_pull_from_registry'
    ]
    output_format = "xlsx"

    def extract_repo_data(self, repo, product_name: str) -> dict:
        data = {col: "unhandled yet" for col in self.columns}
        data['product'] = product_name
        data['scm'] = PRODUCT_SCM_TYPE.get(product_name, 'unknown')
        # Pillar
        product_pillar = 'unhandled yet'
        for pillar, products in PILLAR_PRODUCTS.items():
            if product_name in products:
                product_pillar = pillar
                break
        data['product_pillar'] = product_pillar
        data['repo_name'] = getattr(repo, 'get_repository_name', lambda: 'unknown')()
        data['repo_type'] = "unhandled yet"
        data['repo_owner'] = repo.get_primary_owner_email() if hasattr(repo, 'get_primary_owner_email') else "unknown"
        data['general_manager'] = repo.get_primary_owner_general_manager() if hasattr(repo, 'get_primary_owner_general_manager') else "unknown"
        data['vp'] = repo.get_primary_owner_vp() if hasattr(repo, 'get_primary_owner_vp') else "unknown"
        # JFrog/CI status
        data['status_scan_dependencies_jfrog'] = False
        data['status_scan_sast_sonar'] = False
        # Vulnerabilities
        data['critical_dependencies_vulnerabilities_jfrog'] = 0
        data['high_dependencies_vulnerabilities_jfrog'] = 0
        data['critical_code_vulnerabilities_sonar'] = 0
        data['critical_code_secrets_sonar'] = 0
        data['prevent_on_code_push_to_scm'] = "unhandled yet"
        data['prevent_on_artifact_push_to_registry'] = "unhandled yet"
        data['prevent_on_artifact_pull_from_registry'] = "unhandled yet"

        if hasattr(repo, 'ci_status') and repo.ci_status:
            if hasattr(repo.ci_status, 'jfrog_status') and repo.ci_status.jfrog_status:
                data['status_scan_dependencies_jfrog'] = repo.ci_status.jfrog_status.is_exist
            if hasattr(repo.ci_status, 'sonar_status') and repo.ci_status.sonar_status:
                data['status_scan_sast_sonar'] = repo.ci_status.sonar_status.is_exist

        if hasattr(repo, 'vulnerabilities') and repo.vulnerabilities:
            vuln = repo.vulnerabilities
            if hasattr(vuln, 'dependencies_vulns') and vuln.dependencies_vulns:
                deps_vuln = vuln.dependencies_vulns
                jfrog_status = getattr(getattr(repo, 'ci_status', None), 'jfrog_status', None)
                if jfrog_status:
                    data['critical_dependencies_vulnerabilities_jfrog'] = deps_vuln.critical_count
                    data['high_dependencies_vulnerabilities_jfrog'] = deps_vuln.high_count
                else:
                    data['critical_dependencies_vulnerabilities_jfrog'] = 0
                    data['high_dependencies_vulnerabilities_jfrog'] = 0
            if hasattr(vuln, 'code_issues') and vuln.code_issues:
                code_issues = vuln.code_issues
                data['critical_code_secrets_sonar'] = code_issues.get_secrets_count() if hasattr(code_issues, 'get_secrets_count') else 0
                data['critical_code_vulnerabilities_sonar'] = code_issues.get_critical_vulnerability_count() if hasattr(code_issues, 'get_critical_vulnerability_count') else 0
        return data

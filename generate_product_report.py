#!/usr/bin/env python3
"""
RASOS Product Repository Report Generator

This CLI tool generates CSV reports for product repositories with comprehensive
data including CI/CD status, vulnerabilities, and security metrics.
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Configure logging to show progress messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)



# Add src and config to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))
sys.path.insert(0, current_dir)

from src.models.product import Product
from src.models.devops import DevOps
from CONSTANTS import (
    PILLAR_PRODUCTS, PRODUCT_DEVOPS, PRODUCT_SCM_TYPE, 
    PRODUCT_ORGANIZATION_ID
)

# Configure logging to show progress messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set specific logger levels for better visibility
logging.getLogger('src.models.product').setLevel(logging.INFO)
logging.getLogger('src.services.data_loader').setLevel(logging.INFO)


import argparse

# --- Report Type Abstraction ---

# --- Modular, OOP, CLI-driven Report Generator ---

from reporting.manager_report import ManagerReport
from reporting.devops_report import DevOpsReport
from reporting.testing_report import TestingReport

REPORT_TYPES = {
    'manager': ManagerReport,
    'devops': DevOpsReport,
    'testing': TestingReport,
}

def get_all_products() -> list:
    products = set()
    for pillar_products in PILLAR_PRODUCTS.values():
        products.update(pillar_products)
    return sorted(list(products))

def parse_args():
    parser = argparse.ArgumentParser(description="RASOS Modular Product Report Generator")
    parser.add_argument('--report', choices=REPORT_TYPES.keys(), required=True, help="Report type")
    parser.add_argument('--products', nargs='+', help="Product(s) to include (default: all)")
    parser.add_argument('--output-dir', default=None, help="Output directory (default: timestamped under ./reports)")
    return parser.parse_args()

def main():
    args = parse_args()
    report_cls = REPORT_TYPES[args.report]
    all_products = get_all_products()
    products = args.products if args.products else all_products
    invalid = [p for p in products if p not in all_products]
    if invalid:
        print(f"Invalid product(s): {invalid}. Valid options: {all_products}")
        sys.exit(1)
    output_dir = args.output_dir or os.path.join("reports", f"{args.report}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(output_dir, exist_ok=True)
    report = report_cls(products)
    report.generate_report(output_dir)
    print(f"\n✅ {args.report.capitalize()} report generated for products: {', '.join(products)}")
    print(f"📁 Output directory: {output_dir}")

# --- PDF/summary/statistics generation is now disabled ---



if __name__ == "__main__":
    main()
    
    def create_output_directory(self) -> str:
        """Create timestamped output directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join("reports", f"product_report_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    
    def load_product_data(self, product_name: str) -> Product:
        """Load product with all repository data"""
        print(f"\n📊 Loading data for {product_name}...")
        
        # Get product configuration
        scm_type = PRODUCT_SCM_TYPE.get(product_name, "github")
        org_id = PRODUCT_ORGANIZATION_ID.get(product_name, "0")
        devops_info = PRODUCT_DEVOPS.get(product_name)
        
        # Create DevOps contact if available
        devops = None
        if devops_info:
            devops = DevOps(devops_info["name"], devops_info["email"])
        
        # Create product instance
        product = Product(product_name, scm_type, org_id, devops)
        
        # Load all data with progress indicators
        print("⏳ Loading repositories...")
        product.load_repositories()
        repo_count = product.get_repos_count()
        print(f"✓ Loaded {repo_count} repositories")
        
        if repo_count == 0:
            print("⚠️  No repositories found for this product")
            return product
        
        print("⏳ Loading CI/CD data...")
        product.load_ci_data()
        print("✓ CI/CD data loaded")
        
        print("⏳ Loading vulnerability data...")
        product.load_vulnerabilities()
        print("✓ Vulnerability data loaded")
        
        return product
    
    def extract_repo_data(self, repo, product_name: str) -> Dict[str, Any]:
        """Extract all required data from a repository object"""
        # Get SCM type from CONSTANTS based on product name
        scm_name = PRODUCT_SCM_TYPE.get(product_name, 'unknown')
        
        # Find product pillar for this product
        product_pillar = 'Unknown'
        for pillar, products in PILLAR_PRODUCTS.items():
            if product_name in products:
                product_pillar = pillar
                break
        
        data = {
            'product_pillar': product_pillar,
            'product': product_name,
            'scm_name': scm_name,
            'repo_name': repo.get_repository_name(),
            'default_branch': 'No info',
            'hr_info': 'Unhandled Yet',
            'is_production': 'Unhandled Yet',
            'jfrog_ci_status': False,
            'build_names': 'None',
            'jfrog_cd_status': 'Unhandled Yet',
            'sonar_ci_status': False,
            'sonar_is_scanned': 'Unhandled Yet',
            'critical_dependencies_vuln': 0,
            'high_dependencies_vuln': 0,
            'deployed_artifacts_vulnerabilities': '{}',  # Default empty JSON
            'code_secrets': 0,
            'code_critical_vulnerabilities': 0,
            'enforcement_on_artifact_push': 'Unhandled Yet',
            'enforcement_on_critical_sast': 'Unhandled Yet',
            'sbom_created_per_artifact': 'Unhandled Yet',
            'sbom_kept_indefinitely': 'Unhandled Yet'
        }
        
        # SCM Info - get default_branch from repo if available
        if hasattr(repo, 'scm_info') and repo.scm_info:
            if hasattr(repo.scm_info, 'default_branch'):
                data['default_branch'] = repo.scm_info.default_branch
        
        # CI Status - using correct attribute names from test
        if hasattr(repo, 'ci_status') and repo.ci_status:
            # JFrog CI Status - using jfrog_status not jfrog_ci
            if hasattr(repo.ci_status, 'jfrog_status') and repo.ci_status.jfrog_status:
                data['jfrog_ci_status'] = repo.ci_status.jfrog_status.is_exist
                
                # Extract build names
                if hasattr(repo.ci_status.jfrog_status, 'matched_build_names') and repo.ci_status.jfrog_status.matched_build_names:
                    # Convert set to sorted list for consistent JSON output
                    build_names_list = sorted(list(repo.ci_status.jfrog_status.matched_build_names))
                    data['build_names'] = json.dumps(build_names_list)
                elif repo.ci_status.jfrog_status.is_exist:
                    # If JFrog CI exists but no build names (shouldn't happen with new logic), show empty list
                    data['build_names'] = '[]'
                # If no JFrog CI, keep default 'None'
            
            # Sonar CI Status - using sonar_status not sonar_ci
            if hasattr(repo.ci_status, 'sonar_status') and repo.ci_status.sonar_status:
                data['sonar_ci_status'] = repo.ci_status.sonar_status.is_exist
        
        # Vulnerability data
        if hasattr(repo, 'vulnerabilities') and repo.vulnerabilities:
            vuln = repo.vulnerabilities
            
            # Dependencies vulnerabilities - using correct attribute name
            if hasattr(vuln, 'dependencies_vulns') and vuln.dependencies_vulns:
                deps_vuln = vuln.dependencies_vulns
                data['critical_dependencies_vuln'] = getattr(deps_vuln, 'critical_count', 0)
                data['high_dependencies_vuln'] = getattr(deps_vuln, 'high_count', 0)
                
                # Extract deployed artifacts with critical and high vulnerabilities
                deployed_artifacts_data = {}
                if hasattr(deps_vuln, 'artifacts') and deps_vuln.artifacts:
                    for artifact in deps_vuln.artifacts:
                        # Get artifact name (use artifact_key or jfrog_path as name)
                        artifact_name = getattr(artifact, 'artifact_key', getattr(artifact, 'jfrog_path', 'unknown'))
                        
                        # Extract critical and high vulnerabilities only
                        critical_count = getattr(artifact, 'critical_count', 0)
                        high_count = getattr(artifact, 'high_count', 0)
                        
                        # Only include artifacts that have critical or high vulnerabilities
                        if critical_count > 0 or high_count > 0:
                            deployed_artifacts_data[artifact_name] = {
                                'critical': critical_count,
                                'high': high_count
                            }
                
                # Convert to JSON string
                data['deployed_artifacts_vulnerabilities'] = json.dumps(deployed_artifacts_data)
            
            # Code issues (secrets and vulnerabilities)
            if hasattr(vuln, 'code_issues') and vuln.code_issues:
                code_issues = vuln.code_issues
                
                # Secrets count - using method from test
                data['code_secrets'] = code_issues.get_secrets_count()
                
                # Critical vulnerabilities - using method from test
                data['code_critical_vulnerabilities'] = code_issues.get_critical_vulnerability_count()
        
        return data
    
    def generate_csv_report(self, product: Product, output_dir: str) -> tuple[str, str]:
        """Generate CSV and XLSX reports for the product"""
        csv_filename = f"{product.name.lower().replace(' ', '_')}_repos.csv"
        xlsx_filename = f"{product.name.lower().replace(' ', '_')}_repos.xlsx"
        csv_path = os.path.join(output_dir, csv_filename)
        xlsx_path = os.path.join(output_dir, xlsx_filename)
        
        print("\n📝 Generating CSV and XLSX reports...")
        
        # Define headers
        headers = [
            'product_pillar',
            'product',
            'scm_name',
            'repo_name', 
            'default_branch',
            'hr_info',
            'is_production',
            'jfrog_ci_status',
            'build_names',
            'jfrog_cd_status',
            'sonar_ci_status',
            'sonar_is_scanned',
            'critical_dependencies_vuln',
            'high_dependencies_vuln',
            'deployed_artifacts_vulnerabilities',  # New column for deployed artifacts
            'code_secrets',
            'code_critical_vulnerabilities',
            'enforcement_on_artifact_push',
            'enforcement_on_critical_sast',
            'sbom_created_per_artifact',
            'sbom_kept_indefinitely'
        ]
        
        # Extract data for all repositories
        repo_data = []
        for i, repo in enumerate(product.repos, 1):
            if i % 50 == 0:  # Progress indicator for large datasets
                print(f"  Processing repository {i}/{len(product.repos)}")
            repo_data.append(self.extract_repo_data(repo, product.name))
        
        # Write CSV file
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(repo_data)
        
        # Write XLSX file using pandas
        try:
            df = pd.DataFrame(repo_data)
            # Ensure columns are in the correct order
            df = df[headers]
            df.to_excel(xlsx_path, index=False, engine='openpyxl')
            print(f"✅ Generated XLSX file: {xlsx_filename}")
        except Exception as e:
            print(f"⚠️  Warning: Failed to generate XLSX file: {str(e)}")
            print(f"   (CSV file was created successfully)")
            # Return None for xlsx_path if it failed
            xlsx_path = None
        
        print(f"✅ Generated CSV file: {csv_filename}")
        
        return csv_path, xlsx_path
    
    def run(self):
        """Main execution method"""
        try:
            # Select product
            selected_product = self.display_product_menu()
            
            # Create output directory
            output_dir = self.create_output_directory()
            
            # Load product data
            product = self.load_product_data(selected_product)
            
            if product.get_repos_count() == 0:
                print(f"\n❌ No repositories found for {selected_product}")
                return
            
            # Generate CSV and XLSX reports
            csv_path, xlsx_path = self.generate_csv_report(product, output_dir)
            
            # PDF/statistics/summary generation is disabled.
            print("\n✅ Report generated successfully!")
            print(f"📁 Output directory: {output_dir}")
            print(f"📄 CSV file: {csv_path}")
            if xlsx_path:
                print(f"📊 XLSX file: {xlsx_path}")
            print(f"📈 Total repositories: {product.get_repos_count()}")
            
        except Exception as e:
            print(f"\n❌ Error generating report: {str(e)}")
            raise
    


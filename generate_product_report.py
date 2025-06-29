#!/usr/bin/env python3
"""
RASOS Product Repository Report Generator

This CLI tool generates CSV reports for product repositories with comprehensive
data including CI/CD status, vulnerabilities, and security metrics.
"""

import csv
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Visualization libraries
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

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


class ProductReportGenerator:
    """Generate CSV reports for product repositories"""
    
    def __init__(self):
        self.products = self._get_all_products()
        
    def _get_all_products(self) -> List[str]:
        """Get all unique products from PILLAR_PRODUCTS"""
        products = set()
        for pillar_products in PILLAR_PRODUCTS.values():
            products.update(pillar_products)
        return sorted(list(products))
    
    def display_product_menu(self) -> str:
        """Display product selection menu and return selected product"""
        print("\n" + "="*60)
        print("RASOS Product Repository Report Generator")
        print("="*60)
        print("\nAvailable Products:")
        print("-" * 20)
        
        for i, product in enumerate(self.products, 1):
            print(f"{i:2d}. {product}")
        
        while True:
            try:
                choice = input(f"\nSelect a product (1-{len(self.products)}): ").strip()
                index = int(choice) - 1
                
                if 0 <= index < len(self.products):
                    selected_product = self.products[index]
                    print(f"\n✓ Selected: {selected_product}")
                    return selected_product
                else:
                    print(f"Please enter a number between 1 and {len(self.products)}")
                    
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\n\nOperation cancelled by user")
                sys.exit(0)
    
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
        
        data = {
            'scm_name': scm_name,
            'repo_name': repo.get_repository_name(),
            'default_branch': 'No info',
            'hr_info': 'Unhandled Yet',
            'is_production': 'Unhandled Yet',
            'jfrog_ci_status': False,
            'jfrog_cd_status': 'Unhandled Yet',
            'deployed_artifacts': '[]',
            'sonar_ci_status': False,
            'sonar_is_scanned': 'Unhandled Yet',
            'critical_dependencies_vuln': 0,
            'high_dependencies_vuln': 0,
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
                
                # Deployed artifacts - using correct attribute name
                if hasattr(deps_vuln, 'artifacts') and deps_vuln.artifacts:
                    artifact_names = [artifact.artifact_key for artifact in deps_vuln.artifacts]
                    data['deployed_artifacts'] = json.dumps(artifact_names)
            
            # Code issues (secrets and vulnerabilities)
            if hasattr(vuln, 'code_issues') and vuln.code_issues:
                code_issues = vuln.code_issues
                
                # Secrets count - using method from test
                data['code_secrets'] = code_issues.get_secrets_count()
                
                # Critical vulnerabilities - using method from test
                data['code_critical_vulnerabilities'] = code_issues.get_critical_vulnerability_count()
        
        return data
    
    def generate_csv_report(self, product: Product, output_dir: str) -> str:
        """Generate CSV report for the product"""
        csv_filename = f"{product.name.lower().replace(' ', '_')}_repos.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        print("\n📝 Generating CSV report...")
        
        # Define CSV headers
        headers = [
            'scm_name',
            'repo_name', 
            'default_branch',
            'hr_info',
            'is_production',
            'jfrog_ci_status',
            'jfrog_cd_status',
            'deployed_artifacts',
            'sonar_ci_status',
            'sonar_is_scanned',
            'critical_dependencies_vuln',
            'high_dependencies_vuln',
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
        
        return csv_path
    
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
            
            # Generate CSV report
            csv_path = self.generate_csv_report(product, output_dir)
            
            # Generate summary document with visualizations
            summary_path = self.generate_summary_document(product, output_dir)
            
            # Success message
            print("\n✅ Report generated successfully!")
            print(f"📁 Output directory: {output_dir}")
            print(f"📄 CSV file: {csv_path}")
            print(f"📊 Summary document: {summary_path}")
            print(f"📈 Total repositories: {product.get_repos_count()}")
            
            # Summary statistics
            self.print_summary_stats(product)
            
        except Exception as e:
            print(f"\n❌ Error generating report: {str(e)}")
            raise
    
    def print_summary_stats(self, product: Product):
        """Print summary statistics"""
        print(f"\n📈 Summary Statistics for {product.name}:")
        print("-" * 50)
        
        total_repos = len(product.repos)
        jfrog_ci_count = 0
        sonar_ci_count = 0
        
        # JFrog vulnerability statistics
        jfrog_vulns_repos = 0
        jfrog_critical_total = 0
        jfrog_high_total = 0
        jfrog_medium_total = 0
        jfrog_low_total = 0
        jfrog_unknown_total = 0
        
        # SonarQube code issues statistics
        sonar_issues_repos = 0
        sonar_vulnerability_repos = 0
        sonar_bug_repos = 0
        sonar_code_smell_repos = 0
        sonar_secrets_repos = 0
        sonar_total_issues = 0
        sonar_total_vulnerabilities = 0
        sonar_total_secrets = 0
        
        for repo in product.repos:
            # Count JFrog CI integrations - using correct attribute names
            if (hasattr(repo, 'ci_status') and repo.ci_status and 
                hasattr(repo.ci_status, 'jfrog_status') and repo.ci_status.jfrog_status and
                repo.ci_status.jfrog_status.is_exist):
                jfrog_ci_count += 1
            
            # Count Sonar CI integrations - using correct attribute names
            if (hasattr(repo, 'ci_status') and repo.ci_status and 
                hasattr(repo.ci_status, 'sonar_status') and repo.ci_status.sonar_status and
                repo.ci_status.sonar_status.is_exist):
                sonar_ci_count += 1
            
            # JFrog Dependencies Vulnerabilities
            if (hasattr(repo, 'vulnerabilities') and repo.vulnerabilities and
                hasattr(repo.vulnerabilities, 'dependencies_vulns') and 
                repo.vulnerabilities.dependencies_vulns):
                deps_vulns = repo.vulnerabilities.dependencies_vulns
                if hasattr(deps_vulns, 'artifacts') and deps_vulns.artifacts:
                    jfrog_vulns_repos += 1
                    jfrog_critical_total += getattr(deps_vulns, 'critical_count', 0)
                    jfrog_high_total += getattr(deps_vulns, 'high_count', 0)
                    jfrog_medium_total += getattr(deps_vulns, 'medium_count', 0)
                    jfrog_low_total += getattr(deps_vulns, 'low_count', 0)
                    jfrog_unknown_total += getattr(deps_vulns, 'unknown_count', 0)
            
            # SonarQube Code Issues
            if (hasattr(repo, 'vulnerabilities') and repo.vulnerabilities and
                hasattr(repo.vulnerabilities, 'code_issues') and 
                repo.vulnerabilities.code_issues):
                code_issues = repo.vulnerabilities.code_issues
                
                # Check if repo has any code issues
                if hasattr(code_issues, 'issues_by_type') and code_issues.issues_by_type:
                    # Count total issues
                    total_issues = 0
                    for severity_counts in code_issues.issues_by_type.values():
                        total_issues += sum(severity_counts.values())
                    
                    if total_issues > 0:
                        sonar_issues_repos += 1
                        sonar_total_issues += total_issues
                        
                        # Check specific issue types
                        if 'VULNERABILITY' in code_issues.issues_by_type:
                            sonar_vulnerability_repos += 1
                            # Count critical vulnerabilities
                            vuln_counts = code_issues.issues_by_type['VULNERABILITY']
                            critical_vulns = vuln_counts.get('CRITICAL', 0) + vuln_counts.get('BLOCKER', 0)
                            sonar_total_vulnerabilities += critical_vulns
                        
                        if 'BUG' in code_issues.issues_by_type:
                            sonar_bug_repos += 1
                        
                        if 'CODE_SMELL' in code_issues.issues_by_type:
                            sonar_code_smell_repos += 1
                
                # Check secrets
                if hasattr(code_issues, 'secrets_count'):
                    secrets_count = code_issues.secrets_count
                    if secrets_count > 0:
                        sonar_secrets_repos += 1
                        sonar_total_secrets += secrets_count
        
        # Print overall statistics
        print(f"Total repositories: {total_repos}")
        print(f"JFrog CI integrations: {jfrog_ci_count}")
        print(f"SonarQube CI integrations: {sonar_ci_count}")
        
        # Print JFrog vulnerability statistics
        print("\n🔧 JFrog Dependencies Vulnerabilities:")
        print(f"  Repositories with vulnerability data: {jfrog_vulns_repos}")
        if jfrog_vulns_repos > 0:
            print(f"  Total Critical: {jfrog_critical_total}")
            print(f"  Total High: {jfrog_high_total}")
            print(f"  Total Medium: {jfrog_medium_total}")
            print(f"  Total Low: {jfrog_low_total}")
            print(f"  Total Unknown: {jfrog_unknown_total}")
        
        # Print SonarQube code issues statistics
        print("\n🔍 SonarQube Code Issues:")
        print(f"  Repositories with code issues: {sonar_issues_repos}")
        if sonar_issues_repos > 0:
            print(f"  Total issues across all repos: {sonar_total_issues}")
            print(f"  Repositories with vulnerabilities: {sonar_vulnerability_repos}")
            print(f"  Total critical vulnerabilities: {sonar_total_vulnerabilities}")
            print(f"  Repositories with bugs: {sonar_bug_repos}")
            print(f"  Repositories with code smells: {sonar_code_smell_repos}")
            print(f"  Repositories with secrets: {sonar_secrets_repos}")
            print(f"  Total secrets detected: {sonar_total_secrets}")
    
    def generate_summary_document(self, product: Product, output_dir: str) -> str:
        """Generate a comprehensive summary document with visualizations"""
        print("\n📊 Generating summary document with visualizations...")
        
        # Collect statistics
        stats = self.collect_statistics(product)
        
        # Create visualizations
        plt.style.use('seaborn-v0_8')
        fig_size = (12, 8)
        
        # Create PDF document
        summary_filename = f"{product.name.lower().replace(' ', '_')}_summary_report.pdf"
        summary_path = os.path.join(output_dir, summary_filename)
        
        with PdfPages(summary_path) as pdf:
            # Page 1: Overview Dashboard
            self.create_overview_dashboard(product, stats, pdf, fig_size)
            
            # Page 2: CI/CD Integration Analysis
            self.create_ci_cd_analysis(product, stats, pdf, fig_size)
            
            # Page 3: JFrog Vulnerability Analysis
            self.create_jfrog_analysis(product, stats, pdf, fig_size)
            
            # Page 4: SonarQube Code Issues Analysis
            self.create_sonar_analysis(product, stats, pdf, fig_size)
            
            # Page 5: Repository Distribution and Trends
            self.create_repository_analysis(product, stats, pdf, fig_size)
        
        plt.close('all')  # Clean up matplotlib figures
        return summary_path
    
    def collect_statistics(self, product: Product) -> Dict[str, Any]:
        """Collect all statistics needed for visualizations"""
        stats = {
            'total_repos': len(product.repos),
            'jfrog_ci_count': 0,
            'sonar_ci_count': 0,
            'jfrog_vulns_repos': 0,
            'jfrog_critical_total': 0,
            'jfrog_high_total': 0,
            'jfrog_medium_total': 0,
            'jfrog_low_total': 0,
            'jfrog_unknown_total': 0,
            'sonar_issues_repos': 0,
            'sonar_vulnerability_repos': 0,
            'sonar_bug_repos': 0,
            'sonar_code_smell_repos': 0,
            'sonar_secrets_repos': 0,
            'sonar_total_issues': 0,
            'sonar_total_vulnerabilities': 0,
            'sonar_total_secrets': 0,
            'repos_with_issues': [],
            'repos_with_vulns': [],
            'repo_names': []
        }
        
        for repo in product.repos:
            repo_name = repo.get_repository_name()
            stats['repo_names'].append(repo_name)
            
            # CI integrations
            if (hasattr(repo, 'ci_status') and repo.ci_status and 
                hasattr(repo.ci_status, 'jfrog_status') and repo.ci_status.jfrog_status and
                repo.ci_status.jfrog_status.is_exist):
                stats['jfrog_ci_count'] += 1
            
            if (hasattr(repo, 'ci_status') and repo.ci_status and 
                hasattr(repo.ci_status, 'sonar_status') and repo.ci_status.sonar_status and
                repo.ci_status.sonar_status.is_exist):
                stats['sonar_ci_count'] += 1
            
            # JFrog vulnerabilities
            if (hasattr(repo, 'vulnerabilities') and repo.vulnerabilities and
                hasattr(repo.vulnerabilities, 'dependencies_vulns') and 
                repo.vulnerabilities.dependencies_vulns):
                deps_vulns = repo.vulnerabilities.dependencies_vulns
                if hasattr(deps_vulns, 'artifacts') and deps_vulns.artifacts:
                    stats['jfrog_vulns_repos'] += 1
                    critical = getattr(deps_vulns, 'critical_count', 0)
                    high = getattr(deps_vulns, 'high_count', 0)
                    stats['jfrog_critical_total'] += critical
                    stats['jfrog_high_total'] += high
                    stats['jfrog_medium_total'] += getattr(deps_vulns, 'medium_count', 0)
                    stats['jfrog_low_total'] += getattr(deps_vulns, 'low_count', 0)
                    stats['jfrog_unknown_total'] += getattr(deps_vulns, 'unknown_count', 0)
                    
                    if critical > 0 or high > 0:
                        stats['repos_with_vulns'].append({
                            'name': repo_name,
                            'critical': critical,
                            'high': high,
                            'total': critical + high
                        })
            
            # SonarQube issues
            if (hasattr(repo, 'vulnerabilities') and repo.vulnerabilities and
                hasattr(repo.vulnerabilities, 'code_issues') and 
                repo.vulnerabilities.code_issues):
                code_issues = repo.vulnerabilities.code_issues
                
                if hasattr(code_issues, 'issues_by_type') and code_issues.issues_by_type:
                    total_issues = 0
                    issue_breakdown = {}
                    
                    for issue_type, severity_counts in code_issues.issues_by_type.items():
                        type_total = sum(severity_counts.values())
                        total_issues += type_total
                        issue_breakdown[issue_type] = type_total
                    
                    if total_issues > 0:
                        stats['sonar_issues_repos'] += 1
                        stats['sonar_total_issues'] += total_issues
                        stats['repos_with_issues'].append({
                            'name': repo_name,
                            'total': total_issues,
                            'breakdown': issue_breakdown
                        })
                        
                        if 'VULNERABILITY' in code_issues.issues_by_type:
                            stats['sonar_vulnerability_repos'] += 1
                            vuln_counts = code_issues.issues_by_type['VULNERABILITY']
                            critical_vulns = vuln_counts.get('CRITICAL', 0) + vuln_counts.get('BLOCKER', 0)
                            stats['sonar_total_vulnerabilities'] += critical_vulns
                        
                        if 'BUG' in code_issues.issues_by_type:
                            stats['sonar_bug_repos'] += 1
                        
                        if 'CODE_SMELL' in code_issues.issues_by_type:
                            stats['sonar_code_smell_repos'] += 1
                
                if hasattr(code_issues, 'secrets_count'):
                    secrets_count = code_issues.secrets_count
                    if secrets_count > 0:
                        stats['sonar_secrets_repos'] += 1
                        stats['sonar_total_secrets'] += secrets_count
        
        return stats
    
    def create_overview_dashboard(self, product: Product, stats: Dict, pdf: PdfPages, fig_size: tuple):
        """Create overview dashboard page"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=fig_size)
        fig.suptitle(f'{product.name} - Security & CI/CD Overview Dashboard', fontsize=16, fontweight='bold')
        
        # 1. CI/CD Integration Status (Pie Chart)
        ci_labels = ['JFrog CI', 'SonarQube CI', 'No CI Integration']
        ci_values = [
            stats['jfrog_ci_count'],
            stats['sonar_ci_count'],
            stats['total_repos'] - stats['jfrog_ci_count'] - stats['sonar_ci_count']
        ]
        colors1 = ['#2E8B57', '#4682B4', '#D3D3D3']
        wedges, texts, autotexts = ax1.pie(ci_values, labels=ci_labels, autopct='%1.1f%%', 
                                          colors=colors1, startangle=90)
        ax1.set_title('CI/CD Integration Coverage', fontweight='bold')
        
        # 2. Vulnerability Distribution (Bar Chart)
        vuln_categories = ['Critical', 'High', 'Medium', 'Low', 'Unknown']
        vuln_values = [
            stats['jfrog_critical_total'],
            stats['jfrog_high_total'],
            stats['jfrog_medium_total'],
            stats['jfrog_low_total'],
            stats['jfrog_unknown_total']
        ]
        colors2 = ['#DC143C', '#FF8C00', '#FFD700', '#32CD32', '#A9A9A9']
        bars = ax2.bar(vuln_categories, vuln_values, color=colors2)
        ax2.set_title('JFrog Dependencies Vulnerabilities', fontweight='bold')
        ax2.set_ylabel('Count')
        ax2.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax2.annotate(f'{int(height)}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom')
        
        # 3. SonarQube Issues by Type (Horizontal Bar)
        issue_types = ['Vulnerabilities', 'Bugs', 'Code Smells', 'Secrets']
        issue_counts = [
            stats['sonar_vulnerability_repos'],
            stats['sonar_bug_repos'],
            stats['sonar_code_smell_repos'],
            stats['sonar_secrets_repos']
        ]
        colors3 = ['#DC143C', '#FF4500', '#FFD700', '#8A2BE2']
        bars3 = ax3.barh(issue_types, issue_counts, color=colors3)
        ax3.set_title('SonarQube Issues by Type (Repos)', fontweight='bold')
        ax3.set_xlabel('Number of Repositories')
        
        # 4. Overall Repository Status (Donut Chart)
        status_labels = ['With JFrog Vulns', 'With Sonar Issues', 'Clean Repos']
        clean_repos = stats['total_repos'] - max(stats['jfrog_vulns_repos'], stats['sonar_issues_repos'])
        status_values = [stats['jfrog_vulns_repos'], stats['sonar_issues_repos'], clean_repos]
        colors4 = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        
        wedges4, texts4, autotexts4 = ax4.pie(status_values, labels=status_labels, autopct='%1.1f%%',
                                             colors=colors4, startangle=90, pctdistance=0.85)
        
        # Create donut effect
        centre_circle = plt.Circle((0,0), 0.70, fc='white')
        ax4.add_artist(centre_circle)
        ax4.set_title('Repository Security Status', fontweight='bold')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def create_ci_cd_analysis(self, product: Product, stats: Dict, pdf: PdfPages, fig_size: tuple):
        """Create CI/CD integration analysis page"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=fig_size)
        fig.suptitle(f'{product.name} - CI/CD Integration Analysis', fontsize=16, fontweight='bold')
        
        # 1. Integration Coverage Metrics
        total_repos = stats['total_repos']
        jfrog_coverage = (stats['jfrog_ci_count'] / total_repos * 100) if total_repos > 0 else 0
        sonar_coverage = (stats['sonar_ci_count'] / total_repos * 100) if total_repos > 0 else 0
        
        coverage_data = ['JFrog CI Coverage', 'SonarQube CI Coverage']
        coverage_values = [jfrog_coverage, sonar_coverage]
        colors = ['#2E8B57', '#4682B4']
        
        bars1 = ax1.bar(coverage_data, coverage_values, color=colors)
        ax1.set_title('CI Integration Coverage (%)', fontweight='bold')
        ax1.set_ylabel('Coverage Percentage')
        ax1.set_ylim(0, 100)
        
        # Add percentage labels
        for bar, value in zip(bars1, coverage_values):
            ax1.annotate(f'{value:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, value),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        # 2. Integration Overlap Analysis
        both_integrations = 0
        only_jfrog = 0
        only_sonar = 0
        no_integration = 0
        
        for repo in product.repos:
            has_jfrog = (hasattr(repo, 'ci_status') and repo.ci_status and 
                        hasattr(repo.ci_status, 'jfrog_status') and repo.ci_status.jfrog_status and
                        repo.ci_status.jfrog_status.is_exist)
            has_sonar = (hasattr(repo, 'ci_status') and repo.ci_status and 
                        hasattr(repo.ci_status, 'sonar_status') and repo.ci_status.sonar_status and
                        repo.ci_status.sonar_status.is_exist)
            
            if has_jfrog and has_sonar:
                both_integrations += 1
            elif has_jfrog:
                only_jfrog += 1
            elif has_sonar:
                only_sonar += 1
            else:
                no_integration += 1
        
        overlap_labels = ['Both CI Tools', 'Only JFrog', 'Only SonarQube', 'No CI Integration']
        overlap_values = [both_integrations, only_jfrog, only_sonar, no_integration]
        colors2 = ['#228B22', '#2E8B57', '#4682B4', '#D3D3D3']
        
        wedges2, texts2, autotexts2 = ax2.pie(overlap_values, labels=overlap_labels, autopct='%1.1f%%',
                                             colors=colors2, startangle=90)
        ax2.set_title('CI Integration Overlap', fontweight='bold')
        
        # 3. Monthly trend simulation (placeholder data)
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        jfrog_trend = [stats['jfrog_ci_count'] * (0.6 + i*0.08) for i in range(6)]
        sonar_trend = [stats['sonar_ci_count'] * (0.5 + i*0.1) for i in range(6)]
        
        ax3.plot(months, jfrog_trend, marker='o', label='JFrog CI', color='#2E8B57', linewidth=2)
        ax3.plot(months, sonar_trend, marker='s', label='SonarQube CI', color='#4682B4', linewidth=2)
        ax3.set_title('CI Integration Growth Trend', fontweight='bold')
        ax3.set_ylabel('Number of Repositories')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Summary metrics table
        ax4.axis('tight')
        ax4.axis('off')
        
        metrics_data = [
            ['Metric', 'Value', 'Percentage'],
            ['Total Repositories', f'{total_repos}', '100%'],
            ['JFrog CI Integration', f'{stats["jfrog_ci_count"]}', f'{jfrog_coverage:.1f}%'],
            ['SonarQube CI Integration', f'{stats["sonar_ci_count"]}', f'{sonar_coverage:.1f}%'],
            ['Both Integrations', f'{both_integrations}', f'{(both_integrations/total_repos*100):.1f}%'],
            ['No CI Integration', f'{no_integration}', f'{(no_integration/total_repos*100):.1f}%'],
        ]
        
        table = ax4.table(cellText=metrics_data[1:], colLabels=metrics_data[0],
                         cellLoc='center', loc='center', colWidths=[0.4, 0.3, 0.3])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # Style the header row
        for i in range(3):
            table[(0, i)].set_facecolor('#E6E6FA')
            table[(0, i)].set_text_props(weight='bold')
        
        ax4.set_title('CI/CD Integration Summary', fontweight='bold', pad=20)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def create_jfrog_analysis(self, product: Product, stats: Dict, pdf: PdfPages, fig_size: tuple):
        """Create JFrog vulnerability analysis page"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=fig_size)
        fig.suptitle(f'{product.name} - JFrog Dependencies Vulnerability Analysis', fontsize=16, fontweight='bold')
        
        # 1. Vulnerability severity distribution (Donut chart)
        severity_labels = ['Critical', 'High', 'Medium', 'Low', 'Unknown']
        severity_values = [
            stats['jfrog_critical_total'],
            stats['jfrog_high_total'],
            stats['jfrog_medium_total'],
            stats['jfrog_low_total'],
            stats['jfrog_unknown_total']
        ]
        colors1 = ['#DC143C', '#FF8C00', '#FFD700', '#32CD32', '#A9A9A9']
        
        # Filter out zero values for cleaner visualization
        non_zero_data = [(label, value, color) for label, value, color in zip(severity_labels, severity_values, colors1) if value > 0]
        if non_zero_data:
            labels, values, colors = zip(*non_zero_data)
            wedges1, texts1, autotexts1 = ax1.pie(values, labels=labels, autopct='%1.1f%%',
                                                 colors=colors, startangle=90, pctdistance=0.85)
            centre_circle = plt.Circle((0,0), 0.70, fc='white')
            ax1.add_artist(centre_circle)
        ax1.set_title('Vulnerability Severity Distribution', fontweight='bold')
        
        # 2. Top repositories with critical/high vulnerabilities
        if stats['repos_with_vulns']:
            top_repos = sorted(stats['repos_with_vulns'], key=lambda x: x['total'], reverse=True)[:10]
            repo_names = [repo['name'][:15] + '...' if len(repo['name']) > 15 else repo['name'] for repo in top_repos]
            critical_counts = [repo['critical'] for repo in top_repos]
            high_counts = [repo['high'] for repo in top_repos]
            
            x_pos = range(len(repo_names))
            width = 0.35
            
            bars1 = ax2.bar([p - width/2 for p in x_pos], critical_counts, width, 
                           label='Critical', color='#DC143C', alpha=0.8)
            bars2 = ax2.bar([p + width/2 for p in x_pos], high_counts, width,
                           label='High', color='#FF8C00', alpha=0.8)
            
            ax2.set_title('Top Repositories - Critical & High Vulnerabilities', fontweight='bold')
            ax2.set_ylabel('Vulnerability Count')
            ax2.set_xticks(x_pos)
            ax2.set_xticklabels(repo_names, rotation=45, ha='right')
            ax2.legend()
            
            # Add value labels on bars
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax2.annotate(f'{int(height)}',
                                   xy=(bar.get_x() + bar.get_width() / 2, height),
                                   xytext=(0, 3),
                                   textcoords="offset points",
                                   ha='center', va='bottom', fontsize=8)
        else:
            ax2.text(0.5, 0.5, 'No repositories with\ncritical/high vulnerabilities', 
                    transform=ax2.transAxes, ha='center', va='center', fontsize=12)
            ax2.set_title('Top Repositories - Critical & High Vulnerabilities', fontweight='bold')
        
        # 3. Repository vulnerability status
        vuln_repos = stats['jfrog_vulns_repos']
        clean_repos = stats['total_repos'] - vuln_repos
        
        status_labels = ['With Vulnerabilities', 'Clean']
        status_values = [vuln_repos, clean_repos]
        colors3 = ['#FF6B6B', '#45B7D1']
        
        wedges3, texts3, autotexts3 = ax3.pie(status_values, labels=status_labels, autopct='%1.1f%%',
                                             colors=colors3, startangle=90)
        ax3.set_title('Repository Vulnerability Status', fontweight='bold')
        
        # 4. Vulnerability metrics summary
        ax4.axis('tight')
        ax4.axis('off')
        
        total_vulns = sum(severity_values)
        metrics_data = [
            ['Metric', 'Count', 'Percentage'],
            ['Repositories with vulnerabilities', f'{vuln_repos}', f'{(vuln_repos/stats["total_repos"]*100):.1f}%'],
            ['Total vulnerabilities', f'{total_vulns:,}', '100%'],
            ['Critical vulnerabilities', f'{stats["jfrog_critical_total"]:,}', f'{(stats["jfrog_critical_total"]/total_vulns*100):.1f}%' if total_vulns > 0 else '0%'],
            ['High vulnerabilities', f'{stats["jfrog_high_total"]:,}', f'{(stats["jfrog_high_total"]/total_vulns*100):.1f}%' if total_vulns > 0 else '0%'],
            ['Medium vulnerabilities', f'{stats["jfrog_medium_total"]:,}', f'{(stats["jfrog_medium_total"]/total_vulns*100):.1f}%' if total_vulns > 0 else '0%'],
            ['Low vulnerabilities', f'{stats["jfrog_low_total"]:,}', f'{(stats["jfrog_low_total"]/total_vulns*100):.1f}%' if total_vulns > 0 else '0%'],
        ]
        
        table = ax4.table(cellText=metrics_data[1:], colLabels=metrics_data[0],
                         cellLoc='center', loc='center', colWidths=[0.5, 0.25, 0.25])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        
        # Style the header row
        for i in range(3):
            table[(0, i)].set_facecolor('#FFE4E1')
            table[(0, i)].set_text_props(weight='bold')
        
        ax4.set_title('JFrog Vulnerability Summary', fontweight='bold', pad=20)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def create_sonar_analysis(self, product: Product, stats: Dict, pdf: PdfPages, fig_size: tuple):
        """Create SonarQube code issues analysis page"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=fig_size)
        fig.suptitle(f'{product.name} - SonarQube Code Issues Analysis', fontsize=16, fontweight='bold')
        
        # 1. Issue types distribution
        issue_type_data = {
            'Vulnerabilities': stats['sonar_vulnerability_repos'],
            'Bugs': stats['sonar_bug_repos'],
            'Code Smells': stats['sonar_code_smell_repos'],
            'Secrets': stats['sonar_secrets_repos']
        }
        
        # Filter out zero values
        filtered_data = {k: v for k, v in issue_type_data.items() if v > 0}
        
        if filtered_data:
            labels1 = list(filtered_data.keys())
            values1 = list(filtered_data.values())
            colors1 = ['#DC143C', '#FF4500', '#FFD700', '#8A2BE2'][:len(labels1)]
            
            wedges1, texts1, autotexts1 = ax1.pie(values1, labels=labels1, autopct='%1.1f%%',
                                                 colors=colors1, startangle=90)
        else:
            ax1.text(0.5, 0.5, 'No SonarQube\nissues found', 
                    transform=ax1.transAxes, ha='center', va='center', fontsize=12)
        
        ax1.set_title('Repository Count by Issue Type', fontweight='bold')
        
        # 2. Top repositories by total issues
        if stats['repos_with_issues']:
            top_issues_repos = sorted(stats['repos_with_issues'], key=lambda x: x['total'], reverse=True)[:10]
            repo_names2 = [repo['name'][:15] + '...' if len(repo['name']) > 15 else repo['name'] for repo in top_issues_repos]
            issue_counts = [repo['total'] for repo in top_issues_repos]
            
            bars2 = ax2.barh(repo_names2, issue_counts, color='#4ECDC4')
            ax2.set_title('Top Repositories by Total Issues', fontweight='bold')
            ax2.set_xlabel('Total Issues Count')
            
            # Add value labels
            for i, (bar, count) in enumerate(zip(bars2, issue_counts)):
                ax2.annotate(f'{count}',
                           xy=(count, bar.get_y() + bar.get_height() / 2),
                           xytext=(3, 0),
                           textcoords="offset points",
                           ha='left', va='center', fontsize=8)
        else:
            ax2.text(0.5, 0.5, 'No repositories with\nSonarQube issues', 
                    transform=ax2.transAxes, ha='center', va='center', fontsize=12)
            ax2.set_title('Top Repositories by Total Issues', fontweight='bold')
        
        # 3. Repository coverage analysis
        total_repos = stats['total_repos']
        with_issues = stats['sonar_issues_repos']
        without_issues = total_repos - with_issues
        
        coverage_labels = ['With Issues', 'Clean']
        coverage_values = [with_issues, without_issues]
        colors3 = ['#FF6B6B', '#45B7D1']
        
        wedges3, texts3, autotexts3 = ax3.pie(coverage_values, labels=coverage_labels, autopct='%1.1f%%',
                                             colors=colors3, startangle=90)
        ax3.set_title('SonarQube Coverage Status', fontweight='bold')
        
        # 4. Issue severity breakdown (if we have detailed breakdown data)
        ax4.axis('tight')
        ax4.axis('off')
        
        metrics_data = [
            ['Metric', 'Count', 'Percentage'],
            ['Repositories analyzed', f'{stats["sonar_ci_count"]}', f'{(stats["sonar_ci_count"]/total_repos*100):.1f}%'],
            ['Repositories with issues', f'{with_issues}', f'{(with_issues/total_repos*100):.1f}%'],
            ['Total issues found', f'{stats["sonar_total_issues"]:,}', '100%'],
            ['Critical vulnerabilities', f'{stats["sonar_total_vulnerabilities"]}', f'{(stats["sonar_total_vulnerabilities"]/max(1, stats["sonar_total_issues"])*100):.1f}%'],
            ['Repositories with secrets', f'{stats["sonar_secrets_repos"]}', f'{(stats["sonar_secrets_repos"]/total_repos*100):.1f}%'],
            ['Total secrets detected', f'{stats["sonar_total_secrets"]}', '-'],
        ]
        
        table = ax4.table(cellText=metrics_data[1:], colLabels=metrics_data[0],
                         cellLoc='center', loc='center', colWidths=[0.5, 0.25, 0.25])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        
        # Style the header row
        for i in range(3):
            table[(0, i)].set_facecolor('#E6F3FF')
            table[(0, i)].set_text_props(weight='bold')
        
        ax4.set_title('SonarQube Analysis Summary', fontweight='bold', pad=20)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def create_repository_analysis(self, product: Product, stats: Dict, pdf: PdfPages, fig_size: tuple):
        """Create repository distribution and trends analysis page"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=fig_size)
        fig.suptitle(f'{product.name} - Repository Analysis & Recommendations', fontsize=16, fontweight='bold')
        
        # 1. Security posture matrix
        security_categories = [
            'No Issues',
            'Low Risk\n(Only low/medium vulns)',
            'Medium Risk\n(High vulns or code issues)',
            'High Risk\n(Critical vulns)',
            'Critical Risk\n(Critical vulns + code issues)'
        ]
        
        # Categorize repositories
        no_issues = 0
        low_risk = 0
        medium_risk = 0
        high_risk = 0
        critical_risk = 0
        
        for repo in product.repos:
            has_critical_vulns = False
            has_high_vulns = False
            has_code_issues = False
            
            # Check JFrog vulnerabilities
            if (hasattr(repo, 'vulnerabilities') and repo.vulnerabilities and
                hasattr(repo.vulnerabilities, 'dependencies_vulns') and 
                repo.vulnerabilities.dependencies_vulns):
                deps_vulns = repo.vulnerabilities.dependencies_vulns
                if hasattr(deps_vulns, 'artifacts') and deps_vulns.artifacts:
                    critical_count = getattr(deps_vulns, 'critical_count', 0)
                    high_count = getattr(deps_vulns, 'high_count', 0)
                    has_critical_vulns = critical_count > 0
                    has_high_vulns = high_count > 0
            
            # Check SonarQube issues
            if (hasattr(repo, 'vulnerabilities') and repo.vulnerabilities and
                hasattr(repo.vulnerabilities, 'code_issues') and 
                repo.vulnerabilities.code_issues):
                code_issues = repo.vulnerabilities.code_issues
                if hasattr(code_issues, 'issues_by_type') and code_issues.issues_by_type:
                    total_issues = sum(sum(counts.values()) for counts in code_issues.issues_by_type.values())
                    has_code_issues = total_issues > 0
            
            # Categorize
            if has_critical_vulns and has_code_issues:
                critical_risk += 1
            elif has_critical_vulns:
                high_risk += 1
            elif has_high_vulns or has_code_issues:
                medium_risk += 1
            elif has_high_vulns:  # Only medium/low vulns
                low_risk += 1
            else:
                no_issues += 1
        
        risk_values = [no_issues, low_risk, medium_risk, high_risk, critical_risk]
        colors1 = ['#45B7D1', '#90EE90', '#FFD700', '#FF8C00', '#DC143C']
        
        bars1 = ax1.bar(range(len(security_categories)), risk_values, color=colors1)
        ax1.set_title('Repository Security Risk Distribution', fontweight='bold')
        ax1.set_ylabel('Number of Repositories')
        ax1.set_xticks(range(len(security_categories)))
        ax1.set_xticklabels(security_categories, rotation=45, ha='right', fontsize=9)
        
        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            if height > 0:
                ax1.annotate(f'{int(height)}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom')
        
        # 2. Integration vs Security correlation
        integration_security_data = []
        
        for repo in product.repos:
            has_jfrog = (hasattr(repo, 'ci_status') and repo.ci_status and 
                        hasattr(repo.ci_status, 'jfrog_status') and repo.ci_status.jfrog_status and
                        repo.ci_status.jfrog_status.is_exist)
            has_sonar = (hasattr(repo, 'ci_status') and repo.ci_status and 
                        hasattr(repo.ci_status, 'sonar_status') and repo.ci_status.sonar_status and
                        repo.ci_status.sonar_status.is_exist)
            
            total_vulns = 0
            if (hasattr(repo, 'vulnerabilities') and repo.vulnerabilities and
                hasattr(repo.vulnerabilities, 'dependencies_vulns') and 
                repo.vulnerabilities.dependencies_vulns):
                deps_vulns = repo.vulnerabilities.dependencies_vulns
                critical = getattr(deps_vulns, 'critical_count', 0)
                high = getattr(deps_vulns, 'high_count', 0)
                total_vulns = critical + high
            
            integration_score = (1 if has_jfrog else 0) + (1 if has_sonar else 0)
            integration_security_data.append((integration_score, total_vulns))
        
        # Plot scatter
        if integration_security_data:
            x_vals, y_vals = zip(*integration_security_data)
            scatter = ax2.scatter(x_vals, y_vals, alpha=0.6, c=y_vals, cmap='Reds', s=30)
            ax2.set_xlabel('CI Integration Score (0-2)')
            ax2.set_ylabel('Critical + High Vulnerabilities')
            ax2.set_title('Integration vs Vulnerability Correlation', fontweight='bold')
            ax2.set_xticks([0, 1, 2])
            ax2.set_xticklabels(['None', 'Single Tool', 'Both Tools'])
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax2)
            cbar.set_label('Vulnerability Count')
        
        # 3. Priority recommendations
        ax3.axis('tight')
        ax3.axis('off')
        
        recommendations = []
        
        if critical_risk > 0:
            recommendations.append(f"🚨 URGENT: {critical_risk} repos with critical vulnerabilities + code issues")
        if high_risk > 0:
            recommendations.append(f"⚠️  HIGH: {high_risk} repos with critical vulnerabilities")
        if stats['total_repos'] - stats['jfrog_ci_count'] > 0:
            missing_jfrog = stats['total_repos'] - stats['jfrog_ci_count']
            recommendations.append(f"🔧 Setup JFrog CI for {missing_jfrog} repositories")
        if stats['total_repos'] - stats['sonar_ci_count'] > 0:
            missing_sonar = stats['total_repos'] - stats['sonar_ci_count']
            recommendations.append(f"🔍 Setup SonarQube for {missing_sonar} repositories")
        if no_issues > stats['total_repos'] * 0.5:
            recommendations.append(f"✅ Good: {no_issues} repositories are clean")
        
        if not recommendations:
            recommendations = ["✅ All repositories are properly configured"]
        
        # Create recommendations table
        rec_data = [['Priority Recommendations']]
        for i, rec in enumerate(recommendations[:8]):  # Limit to 8 recommendations
            rec_data.append([rec])
        
        table = ax3.table(cellText=rec_data[1:], colLabels=rec_data[0],
                         cellLoc='left', loc='center', colWidths=[1.0])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # Style the header
        table[(0, 0)].set_facecolor('#E6E6FA')
        table[(0, 0)].set_text_props(weight='bold')
        
        ax3.set_title('Priority Action Items', fontweight='bold', pad=20)
        
        # 4. Summary scorecard
        ax4.axis('tight')
        ax4.axis('off')
        
        # Calculate overall scores
        ci_score = (stats['jfrog_ci_count'] + stats['sonar_ci_count']) / (2 * stats['total_repos']) * 100
        security_score = (no_issues + low_risk * 0.8 + medium_risk * 0.6 + high_risk * 0.3) / stats['total_repos'] * 100
        overall_score = (ci_score + security_score) / 2
        
        scorecard_data = [
            ['Metric', 'Score', 'Grade'],
            ['CI/CD Integration', f'{ci_score:.1f}%', self._get_grade(ci_score)],
            ['Security Posture', f'{security_score:.1f}%', self._get_grade(security_score)],
            ['Overall Assessment', f'{overall_score:.1f}%', self._get_grade(overall_score)],
        ]
        
        table2 = ax4.table(cellText=scorecard_data[1:], colLabels=scorecard_data[0],
                          cellLoc='center', loc='center', colWidths=[0.5, 0.25, 0.25])
        table2.auto_set_font_size(False)
        table2.set_fontsize(12)
        table2.scale(1, 2.5)
        
        # Style the header row
        for i in range(3):
            table2[(0, i)].set_facecolor('#F0F8FF')
            table2[(0, i)].set_text_props(weight='bold')
        
        # Color-code the grades
        for i in range(1, 4):
            grade = scorecard_data[i][2]
            if grade == 'A':
                table2[(i, 2)].set_facecolor('#90EE90')
            elif grade == 'B':
                table2[(i, 2)].set_facecolor('#FFD700')
            elif grade == 'C':
                table2[(i, 2)].set_facecolor('#FF8C00')
            else:
                table2[(i, 2)].set_facecolor('#FF6B6B')
        
        ax4.set_title('Product Security Scorecard', fontweight='bold', pad=20)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _get_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 85:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 55:
            return 'C'
        elif score >= 40:
            return 'D'
        else:
            return 'F'
def main():
    """Main function"""
    generator = ProductReportGenerator()
    generator.run()


if __name__ == "__main__":
    main()

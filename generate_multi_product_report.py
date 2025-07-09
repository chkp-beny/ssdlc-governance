#!/usr/bin/env python3
"""
RASOS Multi-Product Repository Report Generator

This CLI tool generates combined CSV and XLSX reports for multiple products
with comprehensive data including CI/CD status, vulnerabilities, and security metrics.
"""
import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any
import csv
import pandas as pd

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

class MultiProductReportGenerator:
    """Generate combined CSV and XLSX reports for multiple products"""
    
    def __init__(self):
        self.products = self._get_all_products()
        
    def _get_all_products(self) -> List[str]:
        """Get all unique products from PILLAR_PRODUCTS"""
        products = set()
        for pillar_products in PILLAR_PRODUCTS.values():
            products.update(pillar_products)
        return sorted(list(products))
    
    def display_product_menu(self) -> List[str]:
        """Display product selection menu and return selected products"""
        print("\n" + "="*60)
        print("RASOS Multi-Product Repository Report Generator")
        print("="*60)
        print("\nAvailable Products:")
        print("-" * 20)
        
        for i, product in enumerate(self.products, 1):
            print(f"{i}. {product}")
        
        print("\nSelect products by entering their numbers separated by commas (e.g., 1,3,5):")
        while True:
            try:
                choices = input("Enter your choice: ").strip()
                selected_indices = [int(x) for x in choices.split(',')]
                selected_products = [self.products[i-1] for i in selected_indices if 1 <= i <= len(self.products)]
                if selected_products:
                    return selected_products
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")
    
    def create_output_directory(self) -> str:
        """Create timestamped output directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join("reports", f"multi_product_report_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    
    def load_product_data(self, product_name: str) -> Product:
        """Load product with all repository data"""
        logging.info("📊 Loading data for %s...", product_name)
        
        # Get product configuration
        scm_type = PRODUCT_SCM_TYPE.get(product_name, "github")
        org_id = PRODUCT_ORGANIZATION_ID.get(product_name, "0")
        devops_info = PRODUCT_DEVOPS.get(product_name)
        
        # Create DevOps contact if available
        devops = None
        # Adjust DevOps initialization to match expected arguments
        if devops_info:
            devops = DevOps(
                full_name=devops_info.get('name', 'Unknown'),
                email=devops_info.get('email', 'unknown@example.com')
            )
        
        # Create product instance
        product = Product(product_name, scm_type, org_id, devops)
        
        # Load all data with progress indicators
        product.load_repositories()
        product.load_ci_data()
        product.load_vulnerabilities()
        
        return product
    
    def extract_repo_data(self, repo, product_name: str) -> Dict[str, Any]:
        """Extract all required data from a repository object"""
        data = {
            'product': product_name,
            'repo_name': repo.get_repository_name(),
            'default_branch': repo.scm_info.default_branch if repo.scm_info else 'No info',
            'jfrog_ci_status': repo.ci_status.jfrog_status.is_exist if repo.ci_status else False,
            'build_names': ', '.join(repo.ci_status.jfrog_status.matched_build_names) if repo.ci_status else 'None',
            'sonar_ci_status': repo.ci_status.sonar_status.is_exist if repo.ci_status else False,
            'critical_dependencies_vuln': repo.vulnerabilities.dependencies_vulns.critical_count if repo.vulnerabilities else 0,
            'high_dependencies_vuln': repo.vulnerabilities.dependencies_vulns.high_count if repo.vulnerabilities else 0,
            'code_secrets': repo.vulnerabilities.code_vulns.secrets_count if repo.vulnerabilities else 0,
            'code_critical_vulnerabilities': repo.vulnerabilities.code_vulns.critical_count if repo.vulnerabilities else 0
        }
        return data
    
    def generate_combined_report(self, products: List[Product], output_dir: str) -> None:
        """Generate combined CSV and XLSX reports for multiple products"""
        csv_path = os.path.join(output_dir, "multi_product_repos.csv")
        xlsx_path = os.path.join(output_dir, "multi_product_repos.xlsx")
        
        logging.info("📝 Generating combined CSV and XLSX reports...")
        
        # Define headers
        headers = [
            'product',
            'repo_name', 
            'default_branch',
            'jfrog_ci_status',
            'build_names',
            'sonar_ci_status',
            'critical_dependencies_vuln',
            'high_dependencies_vuln',
            'code_secrets',
            'code_critical_vulnerabilities',
            'devops_name'
        ]
        
        # Extract data for all repositories across products
        repo_data = []
        for product in products:
            for repo in product.repos:
                repo_info = self.extract_repo_data(repo, product.name)
                
                # Ensure DevOps name is included in the report
                if hasattr(product.devops, 'full_name'):
                    devops_name = product.devops.full_name
                else:
                    devops_name = "No DevOps assigned"
                
                # Add DevOps name to the report data
                repo_info['devops_name'] = devops_name
                repo_data.append(repo_info)
        
        # Write CSV file
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(repo_data)
        
        # Write XLSX file using pandas
        df = pd.DataFrame(repo_data)
        df.to_excel(xlsx_path, index=False)
        
        # Fix logging format issues
        logging.info("✅ Generated CSV file: %s", csv_path)
        logging.info("✅ Generated XLSX file: %s", xlsx_path)
    
    def run(self):
        """Main execution method"""
        try:
            selected_products = self.display_product_menu()
            output_dir = self.create_output_directory()
            
            # Load data for selected products
            products = [self.load_product_data(product_name) for product_name in selected_products]
            
            # Generate combined report
            self.generate_combined_report(products, output_dir)
            
            logging.info("✅ Multi-product report generation completed.")
        # Refine exception handling
        except (ValueError, KeyError, OSError) as e:
            logging.error("❌ Error during report generation: %s", str(e))

if __name__ == "__main__":
    generator = MultiProductReportGenerator()
    generator.run()

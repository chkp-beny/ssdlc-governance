"""
App Status Report - Generates aggregated security metrics by VP-Director-Product combination
"""
from typing import List, Dict, Any
from collections import defaultdict


class AppStatusReport:
    """
    Generates an aggregated App Status sheet from Manager Report data.
    Creates one row per VP-Director-Product combination with security metrics.
    """
    
    def __init__(self, manager_data: List[Dict[str, Any]]):
        """
        Initialize with manager report data.
        
        Args:
            manager_data: List of dictionaries from ManagerReport.extract_repo_data()
        """
        self.manager_data = manager_data
    
    def generate_app_status_data(self) -> List[Dict[str, Any]]:
        """
        Generate aggregated data for the App Status sheet.
        
        Returns:
            List of dictionaries, one per VP-Director-Product combination
        """
        # Group data by VP -> Director -> Product
        grouped_data = self._group_by_hierarchy()
        
        app_status_rows = []
        for vp, directors in grouped_data.items():
            for director, products in directors.items():
                for product, repos in products.items():
                    row = self._calculate_metrics_for_group(vp, director, product, repos)
                    app_status_rows.append(row)
        
        return app_status_rows
    
    def _group_by_hierarchy(self) -> Dict[str, Dict[str, Dict[str, List[Dict]]]]:
        """
        Group manager data by VP -> Director -> Product hierarchy.
        
        Returns:
            Nested dictionary structure: {VP: {Director: {Product: [repo_data]}}}
        """
        grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        for repo_data in self.manager_data:
            vp = repo_data.get('vp', 'unknown')
            director = repo_data.get('director', 'unknown')  # This becomes AM in the report
            product = repo_data.get('product', 'unknown')
            
            # Skip unknown hierarchies
            if vp == 'unknown' or director == 'unknown' or product == 'unknown':
                continue
                
            grouped[vp][director][product].append(repo_data)
        
        return grouped
    
    def _calculate_metrics_for_group(self, vp: str, director: str, product: str, 
                                   repos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate security metrics for a VP-Director-Product group.
        
        Args:
            vp: VP name
            director: Director name (becomes AM in report)
            product: Product name  
            repos: List of repo data for this group
            
        Returns:
            Dictionary with calculated metrics
        """
        total_repos = len(repos)
        
        # Get SCM type for this product
        scm_type = repos[0].get('scm', 'unknown') if repos else 'unknown'
        
        # Calculate Sonar metrics
        sonar_metrics = self._calculate_sonar_metrics(repos, total_repos)
        
        # Calculate JFrog metrics  
        jfrog_metrics = self._calculate_jfrog_metrics(repos, total_repos)
        
        return {
            'VP': vp,
            'AM': director,  # Director mapped to AM
            'Product': product,
            'SCM': scm_type,
            'Code Integration': sonar_metrics['integration_percentage'],
            'Fail New Critical & High (Sonar)': 'TBD',
            'Secrets': sonar_metrics['secrets_count'],
            'SAST Critical Vulnerabilities': sonar_metrics['critical_vulns_count'],
            'Artifact Scan': jfrog_metrics['integration_percentage'],
            'Fail New Critical & High (JFrog)': 'TBD',
            'Deps Critical Vulnerabilities': jfrog_metrics['critical_vulns_count'],
            'Deps High Vulnerabilities': jfrog_metrics['high_vulns_count']
        }
    
    def _calculate_sonar_metrics(self, repos: List[Dict[str, Any]], total_repos: int) -> Dict[str, Any]:
        """
        Calculate Sonar (1st Party Code) metrics for a group of repos.
        
        Args:
            repos: List of repo data
            total_repos: Total number of repos in the group
            
        Returns:
            Dictionary with Sonar metrics
        """
        # Count repos with Sonar integration
        sonar_integrated_repos = [r for r in repos if r.get('status_scan_sast_sonar') is True]
        sonar_integrated_count = len(sonar_integrated_repos)
        
        # Calculate integration percentage
        integration_percentage = f"{(sonar_integrated_count / total_repos * 100):.0f}%" if total_repos > 0 else "0%"
        
        # Calculate vulnerability counts (only from integrated repos)
        if sonar_integrated_count == 0:
            secrets_count = "N/A"
            critical_vulns_count = "N/A"
        else:
            secrets_count = 0
            critical_vulns_count = 0
            
            for repo in sonar_integrated_repos:
                # Only count integer values (skip "Not Integrated" strings)
                if isinstance(repo.get('critical_code_secrets_sonar'), int):
                    secrets_count += repo['critical_code_secrets_sonar']
                    
                if isinstance(repo.get('critical_code_vulnerabilities_sonar'), int):
                    critical_vulns_count += repo['critical_code_vulnerabilities_sonar']
        
        return {
            'integration_percentage': integration_percentage,
            'secrets_count': secrets_count,
            'critical_vulns_count': critical_vulns_count
        }
    
    def _calculate_jfrog_metrics(self, repos: List[Dict[str, Any]], total_repos: int) -> Dict[str, Any]:
        """
        Calculate JFrog (3rd Party Code) metrics for a group of repos.
        
        Args:
            repos: List of repo data
            total_repos: Total number of repos in the group
            
        Returns:
            Dictionary with JFrog metrics
        """
        # Count repos with JFrog integration
        jfrog_integrated_repos = [r for r in repos if r.get('status_scan_dependencies_jfrog') is True]
        jfrog_integrated_count = len(jfrog_integrated_repos)
        
        # Calculate integration percentage
        integration_percentage = f"{(jfrog_integrated_count / total_repos * 100):.0f}%" if total_repos > 0 else "0%"
        
        # Calculate vulnerability counts (only from integrated repos)
        if jfrog_integrated_count == 0:
            critical_vulns_count = "N/A"
            high_vulns_count = "N/A"
        else:
            critical_vulns_count = 0
            high_vulns_count = 0
            
            for repo in jfrog_integrated_repos:
                # Only count integer values (skip "Not Integrated" strings)
                if isinstance(repo.get('critical_dependencies_vulnerabilities_jfrog'), int):
                    critical_vulns_count += repo['critical_dependencies_vulnerabilities_jfrog']
                    
                if isinstance(repo.get('high_dependencies_vulnerabilities_jfrog'), int):
                    high_vulns_count += repo['high_dependencies_vulnerabilities_jfrog']
        
        return {
            'integration_percentage': integration_percentage,
            'critical_vulns_count': critical_vulns_count,
            'high_vulns_count': high_vulns_count
        }
    
    def export_to_excel(self, workbook, sheet_name: str = "App Status"):
        """
        Export App Status data to an Excel sheet with proper formatting.
        
        Args:
            workbook: openpyxl Workbook object
            sheet_name: Name for the new sheet
        """
        # Generate the aggregated data
        app_status_data = self.generate_app_status_data()
        
        if not app_status_data:
            # Create empty sheet if no data
            ws = workbook.create_sheet(title=sheet_name)
            ws.append(["No data available for App Status report"])
            return
        
        # Create new sheet
        ws = workbook.create_sheet(title=sheet_name)
        
        # Define headers with parent-child structure
        headers = [
            'VP', 'AM', 'Product', 'SCM',
            'Code Integration', 'Fail New Critical & High (Sonar)', 'Secrets', 'SAST Critical Vulnerabilities',
            'Artifact Scan', 'Fail New Critical & High (JFrog)', 'Deps Critical Vulnerabilities', 'Deps High Vulnerabilities'
        ]
        
        # Write headers
        ws.append(headers)
        
        # Write data rows
        for row_data in app_status_data:
            row = [
                row_data['VP'],
                row_data['AM'], 
                row_data['Product'],
                row_data['SCM'],
                row_data['Code Integration'],
                row_data['Fail New Critical & High (Sonar)'],
                row_data['Secrets'],
                row_data['SAST Critical Vulnerabilities'],
                row_data['Artifact Scan'],  
                row_data['Fail New Critical & High (JFrog)'],
                row_data['Deps Critical Vulnerabilities'],
                row_data['Deps High Vulnerabilities']
            ]
            ws.append(row)
        
        # Optional: Add some basic formatting
        # Bold headers
        for cell in ws[1]:
            cell.font = cell.font.copy(bold=True)
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except (TypeError, AttributeError):
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

import os
import csv
import json
from datetime import datetime
from typing import Any, List
from src.models.product import Product
from src.models.devops import DevOps
from CONSTANTS import PILLAR_PRODUCTS, PRODUCT_DEVOPS, PRODUCT_SCM_TYPE, PRODUCT_ORGANIZATION_ID

class ProductReport:
    report_type = "base"
    columns: list = []
    output_format: str = "csv"

    def __init__(self, products: list):
        self.products = products
        self.data: list = []

    def load_all_products(self) -> list:
        loaded = []
        for pname in self.products:
            print(f"\n📊 Loading data for {pname}...")
            scm_type = PRODUCT_SCM_TYPE.get(pname, "github")
            org_id = PRODUCT_ORGANIZATION_ID.get(pname, "0")
            devops_info = PRODUCT_DEVOPS.get(pname)
            devops = DevOps(devops_info["name"], devops_info["email"]) if devops_info else None
            product = Product(pname, scm_type, org_id, devops)
            product.load_repositories()
            product.load_ci_data()
            product.load_vulnerabilities()
            loaded.append(product)
        return loaded

    def extract_repo_data(self, repo, product_name: str) -> dict:
        return {col: "Unhandled Yet" for col in self.columns}

    def generate_report(self, output_dir: str) -> str:
        all_rows = []
        for product in self.load_all_products():
            for repo in product.repos:
                all_rows.append(self.extract_repo_data(repo, product.name))
        if not all_rows:
            print("No data to report.")
            return ""
        if self.output_format == "xlsx":
            # Excel only, no CSV
            xlsx_filename = f"{self.report_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            xlsx_path = os.path.join(output_dir, xlsx_filename)
            try:
                import pandas as pd
                df = pd.DataFrame(all_rows)
                df = df[self.columns]
                df.to_excel(xlsx_path, index=False, engine='openpyxl')
                print(f"✅ Generated XLSX file: {xlsx_path}")
                return xlsx_path
            except Exception as e:
                print(f"❌ XLSX generation failed: {e}")
                return ""
        else:
            # CSV only
            csv_filename = f"{self.report_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.columns)
                writer.writeheader()
                writer.writerows(all_rows)
            print(f"✅ Generated CSV file: {csv_path}")
            return csv_path

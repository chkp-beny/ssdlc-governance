import os
import json
# Pillar-Product Mapping
PILLAR_PRODUCTS = {
    "Infinity": ["Datatube", "Policy Insights", "Cyberint"],
    "Quantum": ["Policy Insights"],
    "Harmony": ["SaaS", "Avanan", "SASE"],
    "CloudGuard": ["FWaaS"],
    "Inext": ["Inext"]
}

# Product-DevOps Mapping
PRODUCT_DEVOPS = json.loads(os.environ["PRODUCT_DEVOPS_MAP"])

# Excluded Owner Titles - Skip owners with these titles when selecting primary owner
EXCLUDED_OWNER_TITLES = ["Group Manager", "Architect", "Technology Leader", "Director, Email Security Area", "Group Manager, DevOps", "Architect, SASE Network"]

# Product-SCM Type Mapping - All products use GitHub
PRODUCT_SCM_TYPE = {    
    "Datatube": "github",
    "Policy Insights": "github", 
    "SaaS": "gitlab",
    "Cyberint": "bitbucket_server",
    "Avanan": "github",
    "SASE": "github",
    "FWaaS": "github",
    "Inext": "gitlab"
}

# Product-GitHub Organization Mapping
# Maps product names to their GitHub organization names
PRODUCT_SCM_ORG_NAME = {
    "Avanan": "Avanan",
    "SASE": "perimeter-81"
}

# Product-Organization ID Mapping - All organizations use ID 0
PRODUCT_ORGANIZATION_ID = {
    "Datatube": "0",
    "Policy Insights": "0",
    "SaaS": "0",
    "Cyberint": "2", 
    "Avanan": "3",
    "SASE": "4",
    "FWaaS": "0",
    "Inext": "5"
}

# Product-JFrog Project Mapping
PRODUCT_JFROG_PROJECT = {
    "Datatube": "datatube",
    "Policy Insights": "", 
    "SaaS": "",
    "Cyberint": "cyberint",
    "Avanan": "hec",
    "SASE": "hsase",
    "FWaaS": "fwaas",
    "Inext": ""
}

# JFrog API Configuration
JFROG_BASE_URL = os.environ["JFROG_BASE_URL"]


# Product-JFrog Token Mapping
# Maps products to their corresponding environment variable names for JFrog tokens
PRODUCT_JFROG_TOKEN_ENV = {
    "Datatube": "",
    "Policy Insights": "",
    "SaaS": "",
    "Cyberint": "CYBERINT_JFROG_ACCESS_TOKEN",
    "Avanan": "AVANAN_JFROG_ACCESS_TOKEN",
    "SASE": "",
    "FWaaS": ""
}

# Product-SCM Token Mapping
# Maps products to their corresponding environment variable names for SCM tokens
PRODUCT_SCM_TOKEN_ENV = {
    "Datatube": "",
    "Policy Insights": "",
    "SaaS": "",
    "Cyberint": "CYBERINT_SCM_TOKEN",
    "Avanan": "AVANAN_SCM_TOKEN",
    "SASE": "SASE_SCM_TOKEN",
    "FWaaS": "",
    "Inext": "INEXT_SCM_TOKEN"
}

# Product-Sonar Prefix Mapping
PRODUCT_SONAR_PREFIX = {
    "Datatube": "datatube-",
    "Policy Insights": "policyinsights-", 
    "SaaS": "saas-",
    "Cyberint": "cyberint-",
    "Avanan": "avanan-",
    "SASE": "sase-",
    "FWaaS": "fwaas-",
    "Inext": "inext-"
}

# Helper functions for token management
def get_jfrog_token_for_product(product_name: str) -> tuple[str, str]:
    """
    Get the JFrog token for a specific product.
    
    Args:
        product_name: Name of the product
        
    Returns:
        tuple: (token_value, token_env_var_name)
    """
    token_env_var = PRODUCT_JFROG_TOKEN_ENV.get(product_name, "CYBERINT_JFROG_ACCESS_TOKEN")
    token_value = os.getenv(token_env_var, "")
    return token_value, token_env_var

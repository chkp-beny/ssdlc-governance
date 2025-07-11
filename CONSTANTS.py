# Pillar-Product Mapping
PILLAR_PRODUCTS = {
    "Infinity": ["Datatube", "Policy Insights", "Cyberint"],
    "Quantum": ["Policy Insights"],
    "Harmony": ["SaaS", "Avanan", "SASE"],
    "CloudGuard": ["FWaaS"],
    "Inext": ["Inext"]
}

# Product-DevOps Mapping
PRODUCT_DEVOPS = {
    "Datatube": {
        "name": "Michael Shohat",
        "email": "michaels@checkpoint.com"
    },
    "Policy Insights": {
        "name": "David Shlomov",
        "email": "davids@checkpoint.com"
    },
    "SaaS": {
        "name": "Mooli Tayer",
        "email": "moolit@checkpoint.com"
    },
    "Cyberint": {
        "name": "Ronen Naor",
        "email": "ronenn@checkpoint.com"
    },
    "Avanan": {
        "name": "Shachar Aharon",
        "email": "shachara@checkpoint.com"
    },
    "SASE": {
        "name": "Nati Aviv",
        "email": "natia@checkpoint.com"
    },
    "FWaaS": {
        "name": "Menahem Ovrutski",
        "email": "menahemo@checkpoint.com"
    }
}

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
    "SASE": "",
    "FWaaS": "fwaas",
    "Inext": ""
}

# JFrog API Configuration
JFROG_BASE_URL = "https://cpart.jfrog.io"

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

# Product-Sonar Prefix Mapping
PRODUCT_SONAR_PREFIX = {
    "Datatube": "datatube-",
    "Policy Insights": "policyinsights-", 
    "SaaS": "saas-",
    "Cyberint": "cyberint-",
    "Avanan": "avanan-",
    "SASE": "sase-",
    "FWaaS": "fwaas-"
}

# Helper functions for token management
import os

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

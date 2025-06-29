# Pillar-Product Mapping
PILLAR_PRODUCTS = {
    "Infinity": ["Datatube", "Policy Insights", "Cyberint"],
    "Quantum": ["Policy Insights"],
    "Harmony": ["SaaS", "Avanan", "SASE"],
    "CloudGuard": ["FWaaS"]
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
    "FWaaS": "github"
}

# Product-Organization ID Mapping - All organizations use ID 0
PRODUCT_ORGANIZATION_ID = {
    "Datatube": "0",
    "Policy Insights": "0",
    "SaaS": "0",
    "Cyberint": "2", 
    "Avanan": "0",
    "SASE": "0",
    "FWaaS": "0"
}

# Product-JFrog Project Mapping
PRODUCT_JFROG_PROJECT = {
    "Datatube": "datatube",
    "Policy Insights": "", 
    "SaaS": "",
    "Cyberint": "cyberint",
    "Avanan": "hec",
    "SASE": "",
    "FWaaS": "fwaas"
}

# JFrog API Configuration
JFROG_BASE_URL = "https://cpart.jfrog.io"

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

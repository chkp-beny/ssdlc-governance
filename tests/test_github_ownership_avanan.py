import os
import pytest
from src.models.product import Product
from CONSTANTS import PRODUCT_SCM_TYPE, PRODUCT_ORGANIZATION_ID, PRODUCT_DEVOPS
from src.models.devops import DevOps

def test_github_ownership_avanan():
    """
    Test that loading repositories for the Avanan product (GitHub SCM) triggers the GitHub ownership mechanism
    and populates the repo_owners field for each repo.
    """
    product_name = "Avanan"
    scm_type = PRODUCT_SCM_TYPE.get(product_name, "github")
    org_id = PRODUCT_ORGANIZATION_ID.get(product_name, "0")
    devops_info = PRODUCT_DEVOPS.get(product_name)
    devops = DevOps(devops_info["name"], devops_info["email"]) if devops_info else None

    # Create the Product instance
    product = Product(product_name, scm_type, org_id, devops)
    product.load_repositories()

    # Check that repos were loaded
    assert len(product.repos) > 0, "No repositories loaded for Avanan"

    # For each repo, check that repo_owners is a list (may be empty if no reviewers)
    for repo in product.repos:
        assert hasattr(repo, "repo_owners"), f"Repo {getattr(repo, 'get_repository_name', lambda: 'unknown')()} missing repo_owners attribute"
        assert isinstance(repo.repo_owners, list), f"repo_owners is not a list for repo {getattr(repo, 'get_repository_name', lambda: 'unknown')()}"
        # Optionally, print the owners for manual inspection
        print(f"Repo: {getattr(repo, 'get_repository_name', lambda: 'unknown')()} | Owners: {repo.repo_owners}")

    # Optionally, check that at least one repo has non-empty repo_owners (if data is available)
    assert any(repo.repo_owners for repo in product.repos), "No repo_owners found for any Avanan repo (check API credentials and data)"

if __name__ == "__main__":
    # Run the test directly for quick manual check
    test_github_ownership_avanan()

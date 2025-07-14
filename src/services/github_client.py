"""
GitHubClient: Handles GitHub API and GraphQL queries for repo owner/reviewer detection
"""
import os
import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self, token: str, org: str):
        self.token = token
        self.org = org
        self.api_url = "https://api.github.com"
        self.graphql_url = "https://api.github.com/graphql"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json"
        })

    def fetch_repos(self) -> List[Dict]:
        """
        Fetch all repositories for the organization (paginated REST API)
        """
        repos = []
        page = 1
        per_page = 100
        while True:
            url = f"{self.api_url}/orgs/{self.org}/repos?page={page}&per_page={per_page}"
            resp = self.session.get(url)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch repos: {resp.status_code} {resp.text}")
                break
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            if len(data) < per_page:
                break
            page += 1
        return repos

    def fetch_repo_reviewers_batch(self, repo_names: List[str]) -> Dict[str, List[str]]:
        """
        Fetch reviewers (collaborators with push access) for multiple repos using GraphQL
        Returns: {repo_name: [reviewer_login, ...], ...}
        """
        # GitHub GraphQL allows batching via aliases
        query_parts = []
        for i, repo in enumerate(repo_names):
            alias = f"repo{i}"
            # Fetch PR reviewers (who approved PRs)
            query_parts.append(f'''{alias}: repository(owner: "{self.org}", name: "{repo}") {{\n  pullRequests(last: 20, states: MERGED) {{\n    nodes {{\n      reviews(last: 10, states: APPROVED) {{\n        nodes {{\n          author {{\n            login\n          }}\n        }}\n      }}\n    }}\n  }}\n}}''')
        graphql_query = "query {\n" + "\n".join(query_parts) + "\n}"
        # logger.debug("GitHub GraphQL query sent: %s", graphql_query)
        resp = self.session.post(self.graphql_url, json={"query": graphql_query})
        if resp.status_code != 200:
            logger.error(f"GraphQL error: {resp.status_code} {resp.text}")
            return {}
        try:
            json_resp = resp.json()
            # Save the raw GitHub GraphQL response and query to files for debugging
            import os, json as _json, datetime
            debug_dir = "github_api_debug"
            os.makedirs(debug_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            debug_file = os.path.join(debug_dir, f"graphql_response_{timestamp}.json")
            with open(debug_file, "w", encoding="utf-8") as f:
                _json.dump(json_resp, f, indent=2)
            query_file = os.path.join(debug_dir, f"graphql_query_{timestamp}.txt")
            with open(query_file, "w", encoding="utf-8") as f:
                f.write(graphql_query)
        except Exception as e:
            logger.error("Failed to parse GitHub GraphQL response as JSON: %s", str(e))
            return {}
        # logger.debug("Raw GitHub GraphQL response: %s", json_resp)
        data = json_resp.get("data", {})
        result = {}
        for i, repo in enumerate(repo_names):
            alias = f"repo{i}"
            reviewers = []
            repo_data = data.get(alias, {}) or {}
            # Traverse: repository -> pullRequests -> nodes[] -> reviews -> nodes[] -> author -> login
            pr_nodes = repo_data.get("pullRequests", {}).get("nodes", [])
            for pr in pr_nodes:
                review_nodes = pr.get("reviews", {}).get("nodes", [])
                for review in review_nodes:
                    author = review.get("author")
                    if author and author.get("login"):
                        reviewers.append(author["login"])
            result[repo] = reviewers
        return result

    # Add more methods as needed for other GitHub queries

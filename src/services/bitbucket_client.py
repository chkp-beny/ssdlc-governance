import logging
import requests
from typing import List

logger = logging.getLogger(__name__)

class BitbucketClient:
    """
    Client for Bitbucket Server REST API for repo owner detection.
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()
    BASE_URL = os.environ["BITBUCKET_BASE_URL"]

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> bool:
        url = f"{self.BASE_URL}/rest/api/1.0/projects?limit=1"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                logger.info("Bitbucket API connection test: SUCCESS")
                return True
            else:
                logger.warning(f"Bitbucket API connection test failed: {response.status_code} {response.text}")
                return False
        except Exception as e:
            logger.error(f"Bitbucket API connection test error: {e}")
            return False

    def fetch_recent_merged_pr_reviewers(self, project_key: str, repo_slug: str, limit: int = 20) -> List[str]:
        url = f"{self.BASE_URL}/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests"
        params = {"state": "MERGED", "limit": limit}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch PRs for {project_key}/{repo_slug}: {response.status_code} {response.text}")
                return []
            data = response.json()
            reviewers = []
            for pr in data.get("values", []):
                for reviewer in pr.get("reviewers", []):
                    user = reviewer.get("user", {})
                    username = user.get("name")
                    if username:
                        reviewers.append(username)
            logger.info(f"Fetched {len(reviewers)} reviewers from last {limit} merged PRs for {project_key}/{repo_slug}")
            return reviewers
        except Exception as e:
            logger.error(f"Error fetching PR reviewers for {project_key}/{repo_slug}: {e}")
            return []

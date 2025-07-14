import requests
import logging

logger = logging.getLogger(__name__)

import os
GITLAB_BASE_URL = os.environ["GITLAB_BASE_URL"]

class GitlabClient:
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })

    def test_connection(self):
        url = f"{GITLAB_BASE_URL}/api/v4/projects"
        try:
            # TODO: For production, use proper SSL verification and pass a CA bundle instead of verify=False
            resp = self.session.get(url, timeout=10, verify=False)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("GitLab connection test failed: %s", str(e))
            return False

    def fetch_project_owners(self, project_id):
        """
        Fetch all members for a project and return those with access_level == 50 (Owner)
        Handles pagination if needed.
        Returns a list of dicts with keys: username, access_level
        """
        owners = []
        page = 1
        per_page = 100
        while True:
            url = f"{GITLAB_BASE_URL}/api/v4/projects/{project_id}/members/all?page={page}&per_page={per_page}"
            try:
                resp = self.session.get(url, timeout=10, verify=False)
                resp.raise_for_status()
                members = resp.json()
                for member in members:
                    if member.get("access_level") == 50:
                        owners.append({
                            "username": member.get("username"),
                            "access_level": member.get("access_level", 0)
                        })
                if len(members) < per_page:
                    break
                page += 1
            except Exception as e:
                logger.error("Error fetching GitLab project members for project_id %s: %s", project_id, str(e))
                break
        return owners

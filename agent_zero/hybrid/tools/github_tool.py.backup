"""
GitHub Tool - Allows the agent to interact with GitHub.
Requires 'github_token' in settings.
"""
import logging
import requests
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class GitHubTool:
    """
    GitHub operations: Search, Read, Issue Management.
    """
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        } if token else {}
        
    def _check_token(self):
        if not self.token:
            raise ValueError("No GitHub Token configured. Please set 'github_token' in settings.")

    def search_repositories(self, params: dict) -> str:
        """
        Search for repositories.
        params: {"query": "language:python topic:bioinformatics"}
        """
        query = params.get("query")
        if not query: return "Error: 'query' required"
        
        try:
            url = f"{self.base_url}/search/repositories"
            resp = requests.get(url, headers=self.headers, params={"q": query, "per_page": 5})
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            for item in data.get("items", []):
                results.append(f"- {item['full_name']}: {item['description']} ({item['html_url']})")
                
            return "\n".join(results) if results else "No repositories found."
        except Exception as e:
            return f"GitHub Search Error: {e}"

    def get_repo_content(self, params: dict) -> str:
        """
        Get file content from a repo.
        params: {"repo": "owner/repo", "path": "path/to/file"}
        """
        self._check_token()
        repo = params.get("repo")
        path = params.get("path")
        if not repo or not path: return "Error: 'repo' and 'path' required"
        
        try:
            url = f"{self.base_url}/repos/{repo}/contents/{path}"
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            
            import base64
            if data.get("encoding") == "base64":
                content = base64.b64decode(data["content"]).decode('utf-8')
                return f"Content of {path}:\n{content[:2000]}..." # Truncate for safety
            return "Error: Unknown encoding or directory."
        except Exception as e:
            return f"GitHub Content Error: {e}"

    def create_issue(self, params: dict) -> str:
        """
        Create an issue in a repo.
        params: {"repo": "owner/repo", "title": "...", "body": "..."}
        """
        self._check_token()
        repo = params.get("repo")
        title = params.get("title")
        body = params.get("body", "")
        
        if not repo or not title: return "Error: 'repo' and 'title' required"
        
        try:
            url = f"{self.base_url}/repos/{repo}/issues"
            resp = requests.post(url, headers=self.headers, json={"title": title, "body": body})
            resp.raise_for_status()
            data = resp.json()
            return f"Issue created: {data['html_url']}"
        except Exception as e:
            return f"GitHub Issue Error: {e}"

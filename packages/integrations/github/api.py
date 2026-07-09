import httpx
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("chief.integrations.github.api")

GITHUB_API_BASE = "https://api.github.com"

def get_headers(pat: str) -> Dict[str, str]:
    return {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

async def list_issues(pat: str, owner: str, repo: str, state="open", labels=None, per_page=30) -> Dict[str, Any]:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
    params = {"state": state, "per_page": per_page}
    if labels:
        params["labels"] = labels
        
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=get_headers(pat), params=params)
        if response.status_code != 200:
            logger.error(f"GitHub API Error (list_issues): {response.text}")
            return {"error": f"Status {response.status_code}: {response.text}"}
            
        # Filter out pull requests which are returned by the issues endpoint
        issues = [item for item in response.json() if "pull_request" not in item]
        return {"issues": issues}

async def list_pull_requests(pat: str, owner: str, repo: str, state="open", per_page=30) -> Dict[str, Any]:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
    params = {"state": state, "per_page": per_page}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=get_headers(pat), params=params)
        if response.status_code != 200:
            logger.error(f"GitHub API Error (list_pull_requests): {response.text}")
            return {"error": f"Status {response.status_code}: {response.text}"}
        return {"pull_requests": response.json()}

async def get_repo_info(pat: str, owner: str, repo: str) -> Dict[str, Any]:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=get_headers(pat))
        if response.status_code != 200:
            logger.error(f"GitHub API Error (get_repo_info): {response.text}")
            return {"error": f"Status {response.status_code}: {response.text}"}
        return {"repo_info": response.json()}

async def list_recent_commits(pat: str, owner: str, repo: str, since_days=7) -> Dict[str, Any]:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
    
    since_date = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    params = {"since": since_date, "per_page": 100}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=get_headers(pat), params=params)
        if response.status_code != 200:
            logger.error(f"GitHub API Error (list_recent_commits): {response.text}")
            return {"error": f"Status {response.status_code}: {response.text}"}
        return {"commits": response.json()}

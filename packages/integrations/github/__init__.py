import datetime
import asyncio
from typing import Any
from .api import list_issues, list_pull_requests, get_repo_info, list_recent_commits

class GitHubIntegrationAdapter:
    def __init__(self, pat: str):
        self.provider = "github"
        self._call_log = []
        self.pat = pat

    def execute_read(self, operation: str, params: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        """Execute a read operation against GitHub API synchronously (wrapping async calls)."""
        self._call_log.append({
            "provider": self.provider,
            "operation": operation,
            "params": params,
            "tenant_id": tenant_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "type": "read",
        })
        
        # Tool Gateway calls this synchronously, so we must run the async functions in an event loop
        # We assume the Tool Gateway is running in an async context but this method is called within an async wrapper or executor
        # Since this is a simple port, we'll try to get the running loop, or create one if not running
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        owner = params.get("owner")
        repo = params.get("repo")
        
        if not owner or not repo:
            # If they passed 'Charanchandra1006/Startup_OS' as 'repository'
            repository = params.get("repository")
            if repository and "/" in repository:
                owner, repo = repository.split("/", 1)
            else:
                return {"error": "Missing owner/repo or repository parameter"}

        coro = None
        if operation == "list_issues":
            coro = list_issues(self.pat, owner, repo, params.get("state", "open"), params.get("labels"))
        elif operation == "list_pull_requests":
            coro = list_pull_requests(self.pat, owner, repo, params.get("state", "open"))
        elif operation == "get_repo_info":
            coro = get_repo_info(self.pat, owner, repo)
        elif operation == "list_recent_commits":
            coro = list_recent_commits(self.pat, owner, repo, params.get("since_days", 7))
        else:
            return {"error": f"Unknown read operation {operation}"}
            
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            
        return loop.run_until_complete(coro)
        
    def execute_write(self, operation: str, payload: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        """Not implemented for Phase 1 - PM agent only reads."""
        self._call_log.append({
            "provider": self.provider,
            "operation": operation,
            "payload": payload,
            "tenant_id": tenant_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "type": "write",
        })
        return {"error": f"Write operations not yet supported for GitHub"}
        
    def get_call_log(self):
        return self._call_log

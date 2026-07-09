import os
import sys
import uuid
import httpx
import logging
from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../packages/shared-types/python')))
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env')))

from chief_types.models import AgentInput, AgentOutput, ConfidenceLevel
from chief_types.observability import get_tracer
from chief_types.llm_client import LLMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chief.agent_project")

app = FastAPI(title="Project Management Agent (AGT-PM)")

AGENT_ID = "AGT-PM"
MODEL_USED = "gemini-2.5-flash"
PROMPT_VERSION = "1.0.0"
TOOL_GATEWAY_URL = os.environ.get("TOOL_GATEWAY_URL", "http://localhost:8002")

SYSTEM_PROMPT = """
You are the Project Management Executive Agent (AGT-PM) for the Startup OS.
Your job is to analyze the GitHub project data (issues, PRs, activity) and answer the founder's query.

CRITICAL INSTRUCTIONS:
1. You MUST use the provided GitHub data to form your analysis. Do not invent issues or PRs.
2. If you cite numbers, issue titles, or contributors, you MUST provide citations in `supporting_data`.
"""

async def fetch_github_data(tenant_id: str, scoped_token: str) -> dict[str, Any]:
    url = f"{TOOL_GATEWAY_URL}/execute/read"
    repos = os.environ.get("GITHUB_REPOS", "Charanchandra1006/Startup_OS")
    repo_list = [r.strip() for r in repos.split(",")]
    
    # Just fetch issues for the first repo for now
    target_repo = repo_list[0] if repo_list else ""
    
    if not target_repo:
        return {"error": "GITHUB_REPOS environment variable not set."}

    payload = {
        "tenant_id": tenant_id,
        "provider": "github",
        "operation": "list_issues",
        "params": {
            "repository": target_repo,
            "state": "open"
        }
    }
    
    headers = {"Authorization": f"Bearer {scoped_token}"}
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, headers=headers, timeout=10.0)
            if res.status_code == 200:
                return res.json()
            return {"error": f"Gateway returned {res.status_code}"}
    except Exception as e:
        logger.error(f"Failed to fetch github data: {e}")
        return {"error": str(e)}

@app.post("/execute", response_model=AgentOutput)
async def execute_task(payload: AgentInput):
    tracer = get_tracer("agent-project")
    
    with tracer.start_agent_span(agent_name=AGENT_ID, task_id="task", tenant_id=str(payload.tenant_id)) as span:
        github_data = await fetch_github_data(str(payload.tenant_id), payload.scoped_data_access_token)
        
        issues = github_data.get("data", {}).get("issues", [])
        
        prompt = f"""
Goal Context: {payload.goal_context}
Task: {payload.task_description}

GitHub Issues Data:
{issues[:20]}  # limit context

Analyze the data and return a JSON matching the AgentOutput schema.
"""
        
        llm = LLMClient()
        try:
            content, p_tokens, c_tokens = await llm.generate(
                provider="google",
                model_id=MODEL_USED,
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                response_format="json"
            )
            
            import json
            parsed = json.loads(content)
            parsed["model_used"] = MODEL_USED
            parsed["prompt_version"] = PROMPT_VERSION
            
            return AgentOutput(**parsed)
            
        except Exception as e:
            logger.error(f"LLM failure: {e}")
            
            return AgentOutput(
                answer=f"I failed to analyze the project data: {e}",
                confidence=ConfidenceLevel.LOW,
                caveats=["System error during LLM generation"],
                model_used=MODEL_USED,
                prompt_version=PROMPT_VERSION,
                supporting_data=[]
            )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8014)

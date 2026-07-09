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

from chief_types.models import AgentInput, AgentOutput, ConfidenceLevel, SupportingDataEntry
from chief_types.observability import get_tracer
from chief_types.llm_client import LLMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chief.agent_hiring")

app = FastAPI(title="Hiring Agent (AGT-HIR)")

AGENT_ID = "AGT-HIR"
MODEL_USED = "gemini-2.5-flash"
PROMPT_VERSION = "1.0.0"
TOOL_GATEWAY_URL = os.environ.get("TOOL_GATEWAY_URL", "http://localhost:8002")

SYSTEM_PROMPT = """
You are the Hiring Executive Agent (AGT-HIR) for the Startup OS.
Your job is to analyze the candidate pipeline and answer the founder's query.

CRITICAL INSTRUCTIONS:
1. You MUST use the provided pipeline data to form your analysis. Do not invent candidates.
2. If you cite numbers or candidate names, you MUST provide citations in `supporting_data`.
3. If the data is missing or empty, state that clearly and use low confidence.
"""

async def fetch_hiring_data(tenant_id: str, scoped_token: str) -> dict[str, Any]:
    url = f"{TOOL_GATEWAY_URL}/execute/read"
    spreadsheet_id = os.environ.get("HIRING_SPREADSHEET_ID")
    
    if not spreadsheet_id:
        logger.warning("HIRING_SPREADSHEET_ID not set.")
        return {"error": "HIRING_SPREADSHEET_ID environment variable not set."}

    payload = {
        "tenant_id": tenant_id,
        "provider": "google",
        "operation": "read_spreadsheet",
        "params": {
            "spreadsheet_id": spreadsheet_id,
            "range": "Sheet1"
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
        logger.error(f"Failed to fetch hiring data: {e}")
        return {"error": str(e)}

@app.post("/execute", response_model=AgentOutput)
async def execute_task(payload: AgentInput):
    tracer = get_tracer("agent-hiring")
    
    with tracer.start_agent_span(agent_name=AGENT_ID, task_id="task", tenant_id=str(payload.tenant_id)) as span:
        hiring_data = await fetch_hiring_data(str(payload.tenant_id), payload.scoped_data_access_token)
        
        candidates = hiring_data.get("data", {}).get("rows", [])
        
        prompt = f"""
Goal Context: {payload.goal_context}
Task: {payload.task_description}

Hiring Pipeline Data:
{candidates}

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
                answer=f"I failed to analyze the hiring pipeline: {e}",
                confidence=ConfidenceLevel.LOW,
                caveats=["System error during LLM generation"],
                model_used=MODEL_USED,
                prompt_version=PROMPT_VERSION,
                supporting_data=[]
            )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)

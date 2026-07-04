"""
Chief AI Startup OS — Executive Assistant Agent (AGT-EA)
Implements: AIDD §2 (Agent Contract), Component 16

Specialist agent for scheduling, email drafting, and routine coordination.
"""

import os
import sys
import logging
import json
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from dotenv import load_dotenv

# Ensure packages can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../packages/shared-types/python')))
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env')))

from chief_types.models import AgentInput, AgentOutput
from chief_types.observability import get_tracer
from chief_types.llm_client import LLMClient

logger = logging.getLogger("chief.agent_ea")
tracer = get_tracer("agent_ea")

app = FastAPI(title="Chief EA Agent")
llm = LLMClient()

TOOL_GATEWAY_URL = os.environ.get("TOOL_GATEWAY_URL", "http://localhost:8002")


SYSTEM_PROMPT = """
You are the Executive Assistant Agent (AGT-EA) for Chief, an AI Startup OS.
Your job is to manage scheduling, draft communications, and summarize routine information.

You must follow the AgentOutput contract EXACTLY.
{
  "answer": "Your summary or confirmation for the founder.",
  "supporting_data": [],
  "confidence": "high|medium|low",
  "caveats": ["Any missing info, e.g., 'Awaiting confirmation on CFO availability'"],
  "suggested_actions": [
    {
      "action_type": "schedule_meeting",
      "payload": {"title": "Finance Review", "attendees": ["founder@example.com"], "time": "next Tuesday 10am"},
      "risk_tier": "C",
      "rationale": "Scheduling the review as requested."
    }
  ],
  "model_used": "model_id",
  "prompt_version": "1.0.0"
}

RULES:
1. You cannot execute actions directly. You must propose them in `suggested_actions`.
2. Do not hallucinate calendar events or emails.
3. If you lack context, set confidence to "low".
"""

async def fetch_calendar_data(tenant_id: str, token: str) -> dict:
    """Fetch calendar data from the Tool Gateway."""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{TOOL_GATEWAY_URL}/tools/execute",
            headers={"X-Access-Token": token},
            json={
                "action_type": "read_calendar",
                "provider": "mock_calendar",
                "operation": "list_events",
                "params": {"tenant_id": tenant_id}
            }
        )
        if res.status_code != 200:
            logger.warning(f"Failed to fetch calendar data: {res.text}")
            return {"error": "Could not retrieve calendar data"}
        return res.json()

async def fetch_email_data(tenant_id: str, token: str) -> dict:
    """Fetch email data from the Tool Gateway."""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{TOOL_GATEWAY_URL}/tools/execute",
            headers={"X-Access-Token": token},
            json={
                "action_type": "read_emails",
                "provider": "mock_email",
                "operation": "list_emails",
                "params": {"tenant_id": tenant_id}
            }
        )
        if res.status_code != 200:
            logger.warning(f"Failed to fetch email data: {res.text}")
            return {"error": "Could not retrieve email data"}
        return res.json()


@app.post("/execute", response_model=AgentOutput)
async def execute_task(payload: AgentInput):
    with tracer.start_span("agent_ea.execute") as span:
        span.set_attribute("tenant.id", str(payload.tenant_id))
        span.set_attribute("task.description", payload.task_description)

        # 1. Fetch external data (mock calendar and email context)
        cal_data = await fetch_calendar_data(str(payload.tenant_id), payload.scoped_data_access_token)
        email_data = await fetch_email_data(str(payload.tenant_id), payload.scoped_data_access_token)
        
        # 2. Construct LLM prompt
        user_prompt = f"""
Goal Context: {payload.goal_context}
Task: {payload.task_description}

Calendar Context:
{json.dumps(cal_data, indent=2)}

Email Context:
{json.dumps(email_data, indent=2)}

Analyze the request and provide the JSON structure, including any suggested_actions (like schedule_meeting, draft_email, or create_internal_draft).
"""

        # 3. Call LLM (Gemini Flash for routine EA tasks)
        try:
            content, _, _ = await llm.generate(
                provider="google",
                model_id="gemini-2.5-flash",
                prompt=user_prompt,
                system_prompt=SYSTEM_PROMPT,
                max_tokens=2048,
                temperature=0.2
            )
            
            # Clean markdown codeblocks if present
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
                
            parsed = json.loads(content)
            
            # 4. Validate against Pydantic model
            output = AgentOutput(**parsed)
            output.model_used = "gemini-2.5-flash"
            output.prompt_version = "1.0.0"
            
            return output

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse LLM output: {e}\nRaw content: {content}")
            raise HTTPException(status_code=500, detail="LLM output did not match AgentOutput schema.")
        except Exception as e:
            logger.error(f"LLM execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)

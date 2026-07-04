"""
Chief AI Startup OS — Finance Agent (AGT-FIN)
Implements: AIDD §2 (Agent Contract), Component 15

Specialist agent for financial reasoning: runway, burn rate, anomalies.
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

from chief_types.models import AgentInput, AgentOutput, SuggestedAction, RiskTier
from chief_types.observability import get_tracer
from chief_types.llm_client import LLMClient

logger = logging.getLogger("chief.agent_finance")
tracer = get_tracer("agent_finance")

app = FastAPI(title="Chief Finance Agent")
llm = LLMClient()

TOOL_GATEWAY_URL = os.environ.get("TOOL_GATEWAY_URL", "http://localhost:8002")


SYSTEM_PROMPT = """
You are the Finance Agent (AGT-FIN) for Chief, an AI Startup OS.
Your job is to analyze financial data (burn rate, runway, transactions) and return a structured JSON response.

You must follow the AgentOutput contract EXACTLY.
{
  "answer": "Your detailed narrative analysis for the founder.",
  "supporting_data": [
    {"source_system": "quickbooks", "source_ref": "transaction_id", "value": "100.00", "retrieved_at": "ISO8601"}
  ],
  "confidence": "high|medium|low",
  "caveats": ["Any missing data or assumptions"],
  "suggested_actions": [
    {
      "action_type": "schedule_meeting",
      "payload": {"title": "Finance Review", "attendees": ["founder", "cfo"]},
      "risk_tier": "C",
      "rationale": "Burn rate is 20% higher than expected."
    }
  ],
  "model_used": "model_id",
  "prompt_version": "1.0.0"
}

RULES:
1. Every numeric claim in `answer` MUST be backed by a record in `supporting_data`.
2. Do not hallucinate transactions. Use only the provided context.
3. If you lack sufficient data to answer, set `confidence` to "low" and state what is missing in `caveats`.
"""

async def fetch_financial_data(tenant_id: str, token: str) -> dict:
    """Fetch accounting data from the Tool Gateway."""
    async with httpx.AsyncClient() as client:
        # Requesting a summary report via Tool Gateway (mock_accounting for now)
        res = await client.post(
            f"{TOOL_GATEWAY_URL}/tools/execute",
            headers={"X-Access-Token": token},
            json={
                "action_type": "read_transactions",
                "provider": "mock_accounting",
                "operation": "summary",
                "params": {"tenant_id": tenant_id}
            }
        )
        if res.status_code != 200:
            logger.warning(f"Failed to fetch financial data: {res.text}")
            return {"error": "Could not retrieve financial data"}
        return res.json()


@app.post("/execute", response_model=AgentOutput)
async def execute_task(payload: AgentInput):
    with tracer.start_span("agent_finance.execute") as span:
        span.set_attribute("tenant.id", str(payload.tenant_id))
        span.set_attribute("task.description", payload.task_description)

        # 1. Fetch external data via Tool Gateway
        fin_data = await fetch_financial_data(str(payload.tenant_id), payload.scoped_data_access_token)
        
        # 2. Construct LLM prompt
        user_prompt = f"""
Goal Context: {payload.goal_context}
Task: {payload.task_description}

Financial Data:
{json.dumps(fin_data, indent=2)}

Analyze the data and provide the requested information in the JSON structure.
"""

        # 3. Call LLM (Gemini Flash for reasoning)
        try:
            content, _, _ = await llm.generate(
                provider="google",
                model_id="gemini-2.5-flash",
                prompt=user_prompt,
                system_prompt=SYSTEM_PROMPT,
                max_tokens=2048,
                temperature=0.1
            )
            
            # Clean markdown codeblocks if present
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
                
            parsed = json.loads(content)
            
            # 4. Validate against Pydantic model
            output = AgentOutput(**parsed)
            # Ensure model_used and prompt_version are accurate to the run
            output.model_used = "gemini-2.5-flash"
            output.prompt_version = "1.0.0"
            
            return output

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse LLM output: {e}\nRaw content: {content}")
            raise HTTPException(status_code=500, detail="LLM output did not match AgentOutput schema.")
        except Exception as e:
            logger.error(f"LLM execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/cron/monitor")
async def proactive_monitor(tenant_id: str, token: str):
    """
    Cron job endpoint for proactive anomaly detection.
    Analyzes current financial data and if an anomaly is found, generates an insight.
    """
    fin_data = await fetch_financial_data(tenant_id, token)
    if "error" in fin_data:
        raise HTTPException(status_code=500, detail="Failed to fetch data")
        
    prompt = f"""
    Financial Data:
    {json.dumps(fin_data, indent=2)}
    
    Is there a critical financial anomaly (e.g. burn rate spike, runway < 6 months)?
    Respond with JSON: {{"has_anomaly": bool, "title": "...", "detail": "...", "severity": "high|medium"}}
    """
    
    content, _, _ = await llm.generate(
        provider="google",
        model_id="gemini-2.5-flash",
        prompt=prompt,
        system_prompt="You are an AI financial monitor. Keep responses factual.",
        max_tokens=1024
    )
    
    if content.startswith("```json"): content = content[7:-3]
    elif content.startswith("```"): content = content[3:-3]
    
    try:
        parsed = json.loads(content)
        if parsed.get("has_anomaly"):
            # In a real app, this would write to the 'insights' table via the execution service
            logger.info(f"Anomaly detected for tenant {tenant_id}: {parsed['title']}")
            return {"status": "anomaly_detected", "insight": parsed}
        return {"status": "ok", "message": "No anomalies"}
    except Exception as e:
        logger.error(f"Cron monitor parse error: {e}")
        return {"status": "error"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)

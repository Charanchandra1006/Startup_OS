import os
import sys
import uuid
import asyncpg
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure packages can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../packages/shared-types/python')))
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env')))

from chief_types.models import GoalStatus, AgentInput, AgentOutput
from orchestrator import Orchestrator, Task
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chief.orchestrator.server")

app = FastAPI(title="Chief Orchestrator API")

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None

@app.on_event("startup")
async def startup_event():
    global db_pool
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        if "?" in db_url: db_url = db_url.split("?")[0]
        try:
            db_pool = await asyncpg.create_pool(db_url)
            logger.info("Connected to Neon DB successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Neon DB: {e}")
    else:
        logger.warning("DATABASE_URL not found, DB persistence will be disabled.")

@app.on_event("shutdown")
async def shutdown_event():
    if db_pool:
        await db_pool.close()

from pydantic import BaseModel, Field
from dataclasses import dataclass

@dataclass
class OrchestratorContext:
    tenant_id: str
    user_id: str
    trace_id: str

class GoalRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str
    context: Dict[str, Any] = {}
    
class ClarifyRequest(BaseModel):
    clarification: str

# In-memory orchestrator instances keyed by goal_id for streaming/status (Phase 1)
# Production would use Redis + distributed locks
active_orchestrators: Dict[str, Orchestrator] = {}

async def http_dispatch_fn(task: Task) -> AgentOutput:
    """Dispatches a task to the appropriate agent microservice."""
    agent_id = task.assigned_agent
    
    # Map agent IDs to URLs
    agent_urls = {
        "AGT-FIN": "http://agent-finance:8011/execute",
        "AGT-EA": "http://agent-ea:8012/execute",
    }
    
    # Map agent IDs to what integrations they need
    agent_integrations = {
        "AGT-FIN": {"scopes": ["read:transactions", "read:accounts"], "integrations": ["mock_accounting"]},
        "AGT-EA": {"scopes": ["read:calendar", "read:emails"], "integrations": ["mock_calendar", "mock_email"]},
    }
    
    if agent_id == "AGT-ECHO":
        import sys
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agent-echo')))
        from agent_echo import process_task
        input_data = AgentInput(
            tenant_id=uuid.UUID(task.tenant_id),
            goal_context="Echo goal context",
            task_description=task.description,
            scoped_data_access_token="test_token"
        )
        return await process_task(input_data)
        
    url = agent_urls.get(agent_id)
    if not url:
        raise ValueError(f"No URL mapped for agent {agent_id}")
    
    # Request a real scoped token from the Tool Gateway
    token_value = "fallback_token"
    integration_info = agent_integrations.get(agent_id, {"scopes": ["read:*"], "integrations": ["mock_accounting"]})
    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "http://tool-gateway:8002/tokens",
                json={
                    "tenant_id": task.tenant_id,
                    "agent_id": agent_id,
                    "scopes": integration_info["scopes"],
                    "integration_ids": integration_info["integrations"]
                },
                timeout=10.0
            )
            if token_res.status_code == 200:
                token_value = token_res.json().get("token", token_value)
                logger.info(f"Got scoped token for {agent_id}")
            else:
                logger.warning(f"Token request failed ({token_res.status_code}): {token_res.text}")
    except Exception as e:
        logger.warning(f"Could not get scoped token for {agent_id}: {e}")
    
    input_data = AgentInput(
        tenant_id=uuid.UUID(task.tenant_id),
        goal_context=f"Task for {agent_id}",
        task_description=task.description,
        scoped_data_access_token=token_value
    )
    
    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=input_data.model_dump(mode='json'), timeout=120.0)
        res.raise_for_status()
        return AgentOutput(**res.json())

async def run_orchestrator(goal_id: str, request_data: GoalRequest, tenant_id: str, user_id: str):
    try:
        # Initialize context and orchestrator
        context = OrchestratorContext(
            tenant_id=tenant_id,
            user_id=user_id,
            trace_id=str(uuid.uuid4())
        )
        orchestrator = Orchestrator(db_pool=db_pool)
        orchestrator.set_agent_dispatcher(http_dispatch_fn)
        active_orchestrators[goal_id] = orchestrator
        
        logger.info(f"Starting goal processing for {goal_id}: {request_data.task_description}")
        await orchestrator.process_goal(goal_id, request_data.task_description, context)
        logger.info(f"Finished goal processing for {goal_id}")
    except Exception as e:
        logger.error(f"Orchestrator failed for {goal_id}: {e}", exc_info=True)
    finally:
        # Cleanup
        if goal_id in active_orchestrators:
            del active_orchestrators[goal_id]

def get_tenant_id(request: Request) -> str:
    # In a real microservices architecture, the API Gateway passes the verified tenant ID
    # in an x-tenant-id header.
    tenant_id = request.headers.get("x-tenant-id")
    if not tenant_id:
        # Fallback for direct local dev testing without API Gateway
        return "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    return tenant_id
    
def get_user_id(request: Request) -> str:
    user_id = request.headers.get("x-user-id")
    if not user_id:
        return "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"
    return user_id

@app.post("/goals")
async def submit_goal(req: GoalRequest, request: Request, background_tasks: BackgroundTasks):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    
    # Store initial goal in DB if available
    if db_pool:
        async with db_pool.acquire() as conn:
            # Check if exists
            exists = await conn.fetchval("SELECT id FROM goals WHERE id = $1", uuid.UUID(req.id))
            if not exists:
                await conn.execute(
                    """
                    INSERT INTO goals (id, tenant_id, submitted_by_user_id, raw_text, status)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    uuid.UUID(req.id), uuid.UUID(tenant_id), uuid.UUID(user_id), req.task_description, "received"
                )
    
    background_tasks.add_task(run_orchestrator, req.id, req, tenant_id, user_id)
    return {"status": "accepted", "goal_id": req.id}

@app.get("/goals/{goal_id}")
async def get_goal_status(goal_id: str, request: Request):
    tenant_id = get_tenant_id(request)
    
    # Check memory first
    if goal_id in active_orchestrators:
        orch = active_orchestrators[goal_id]
        return {
            "id": goal_id,
            "status": orch.state.value,
            "report": orch.final_report.dict() if orch.final_report else None
        }
        
    # Check DB
    if db_pool:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT status, raw_text FROM goals WHERE id = $1 AND tenant_id = $2", uuid.UUID(goal_id), uuid.UUID(tenant_id))
            if row:
                return {
                    "id": goal_id,
                    "status": row["status"],
                    "raw_text": row["raw_text"],
                    "report": None # Will need a separate reports table or JSON col
                }
                
    raise HTTPException(status_code=404, detail="Goal not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

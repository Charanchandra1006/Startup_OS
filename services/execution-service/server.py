import os
import sys
import uuid
import asyncpg
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../packages/shared-types/python')))
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env')))

from execution_service import ExecutionService, AuditWriter, MockExternalExecutor
from chief_types.models import SuggestedAction, RiskTier

logger = logging.getLogger("chief.execution.server")

app = FastAPI(title="Chief Execution Service")
db_pool = None

# Initialize components
audit_writer = AuditWriter()
executor = MockExternalExecutor()
exec_service = ExecutionService(audit_writer, executor)

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

@app.on_event("shutdown")
async def shutdown_event():
    if db_pool:
        await db_pool.close()

class ActionRequest(BaseModel):
    action: SuggestedAction
    goal_id: str

class ApprovalDecision(BaseModel):
    decision: str  # "approve" or "reject"
    reason: str = ""

def get_tenant_id(request: Request) -> str:
    tenant_id = request.headers.get("x-tenant-id")
    if not tenant_id:
        return "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    return tenant_id

def get_user_id(request: Request) -> str:
    user_id = request.headers.get("x-user-id")
    if not user_id:
        return "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"
    return user_id

@app.post("/actions")
async def submit_action(req: ActionRequest, request: Request):
    tenant_id = get_tenant_id(request)
    
    # Normally we use exec_service.evaluate_and_execute, but we want DB persistence for approvals
    # For Phase F, if it requires approval, persist it to DB.
    
    # Fake a user context
    import json
    
    # Check if it needs approval based on RiskTier
    if req.action.risk_tier in (RiskTier.B, RiskTier.C, RiskTier.D):
        # Save to DB
        if db_pool:
            approval_id = uuid.uuid4()
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO approval_requests (id, tenant_id, action_type, risk_tier, rationale, payload, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    approval_id, uuid.UUID(tenant_id), req.action.action_type, req.action.risk_tier.value,
                    req.action.rationale, json.dumps(req.action.payload), "pending"
                )
            return {"status": "pending_approval", "approval_id": str(approval_id)}
        else:
            return {"status": "pending_approval", "approval_id": "mock_approval_id"}
            
    # Auto-execute (Tier A or E)
    try:
        res = exec_service.execute_action(req.action, uuid.UUID(tenant_id), uuid.UUID(get_user_id(request)))
        return {"status": "executed", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approvals/{approval_id}/decide")
async def decide_approval(approval_id: str, decision: ApprovalDecision, request: Request):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    
    if db_pool:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM approval_requests WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(approval_id), uuid.UUID(tenant_id)
            )
            if not row:
                raise HTTPException(status_code=404, detail="Approval not found")
                
            new_status = "approved" if decision.decision == "approve" else "rejected"
            await conn.execute(
                "UPDATE approval_requests SET status = $1, decided_by_user_id = $2, decided_at = NOW() WHERE id = $3",
                new_status, uuid.UUID(user_id), uuid.UUID(approval_id)
            )
            
            if new_status == "approved":
                action = SuggestedAction(
                    action_type=row["action_type"],
                    payload=json.loads(row["payload"]),
                    risk_tier=RiskTier(row["risk_tier"]),
                    rationale=row["rationale"]
                )
                res = exec_service.execute_action(action, uuid.UUID(tenant_id), uuid.UUID(user_id))
                return {"status": "executed", "result": res}
            
            return {"status": "rejected"}
            
    return {"status": "error", "detail": "DB not connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

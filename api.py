import json
import uuid
import psycopg
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse

from action_executor import execute_action
from infra.gmail_client import GmailClient

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "ai_workflows",
    "user": "postgres",
    "password": "postgres",
}

# -------------------------------------------------------------------
# App Initialization
# -------------------------------------------------------------------

app = FastAPI(title="Enterprise AI Workflow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------

class CreateWorkflowRequest(BaseModel):
    text: str
    user_context: Optional[str] = None


class ApprovalRequest(BaseModel):
    decision: str
    reviewer: str
    notes: Optional[str] = None


class WorkflowResponse(BaseModel):
    id: str
    request_text: str
    state: str
    ai_output: Optional[dict]
    human_decision: Optional[dict]
    created_at: str
    updated_at: str


class WorkflowEventResponse(BaseModel):
    event_type: str
    event_data: Optional[dict]
    created_at: str

# -------------------------------------------------------------------
# Event Logger
# -------------------------------------------------------------------

def log_event(workflow_id: str, event_type: str, event_data: dict | None = None):
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflow_events (workflow_id, event_type, event_data)
                VALUES (%s, %s, %s);
                """,
                (workflow_id, event_type, json.dumps(event_data)),
            )
        conn.commit()

# -------------------------------------------------------------------
# Health Check
# -------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "Workflow API running"}

# -------------------------------------------------------------------
# Create Workflow
# -------------------------------------------------------------------

@app.post("/workflows")
def create_workflow(request: CreateWorkflowRequest):

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")

    workflow_id = str(uuid.uuid4())

    # ---- Gmail Draft Workflow ----
    if request.text.strip().startswith("gmail:"):
        payload = {
            "type": "GMAIL_DRAFT_FROM_THREAD",
            "gmail_thread_id": request.text.replace("gmail:", "").strip(),
            "user_context": request.user_context,
        }
        request_text = json.dumps(payload)

    # ---- Generic Workflow ----
    else:
        request_text = request.text.strip()

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflows (id, request_text, state)
                VALUES (%s, %s, 'RECEIVED');
                """,
                (workflow_id, request_text),
            )
        conn.commit()

    log_event(workflow_id, "WORKFLOW_CREATED", {"request_text": request_text})

    return {
        "workflow_id": workflow_id,
        "state": "RECEIVED",
    }

@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    request_text,
                    state,
                    ai_output,
                    human_decision,
                    created_at,
                    updated_at
                FROM workflows
                WHERE id = %s;
                """,
                (workflow_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "id": str(row[0]),
        "request_text": row[1],
        "state": row[2],
        "ai_output": row[3],
        "human_decision": row[4],
        "created_at": row[5].isoformat(),
        "updated_at": row[6].isoformat(),
    }


# -------------------------------------------------------------------
# Approval Endpoint
# -------------------------------------------------------------------

@app.post("/workflows/{workflow_id}/approve")
def approve_workflow(workflow_id: str, approval: ApprovalRequest):

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT state, ai_output, request_text
                FROM workflows
                WHERE id = %s;
                """,
                (workflow_id,),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Workflow not found")

            state, ai_output, request_text = row

            if state != "WAITING_FOR_APPROVAL":
                raise HTTPException(status_code=400, detail="Workflow not approvable")

            human_decision = {
                "decision": approval.decision,
                "reviewer": approval.reviewer,
                "notes": approval.notes,
                "decided_at": datetime.utcnow().isoformat(),
            }

            if approval.decision == "rejected":
                log_event(workflow_id, "WORKFLOW_REJECTED", human_decision)

                cur.execute(
                    """
                    UPDATE workflows
                    SET state = 'REJECTED',
                        human_decision = %s,
                        updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (json.dumps(human_decision), workflow_id),
                )
                conn.commit()
                return {"status": "rejected"}

            # ---- APPROVED ----
            try:
                payload = json.loads(request_text)
                workflow_type = payload.get("type")
            except Exception:
                workflow_type = "GENERIC"

            if workflow_type == "GMAIL_DRAFT_FROM_THREAD":
                execute_action(
                    action="create_gmail_draft",
                    workflow_id=workflow_id,
                    request_text=None,
                    ai_output=ai_output,
                )
            else:
                execute_action(
                    action=ai_output["recommended_action"],
                    workflow_id=workflow_id,
                    request_text=request_text,
                )

            cur.execute(
                """
                UPDATE workflows
                SET state = 'ACTION_EXECUTED',
                    human_decision = %s,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (json.dumps(human_decision), workflow_id),
            )
        conn.commit()

    return {"status": "approved"}

@app.get("/gmail/threads")
def list_gmail_threads(limit: int = 10):

    if limit < 1 or limit > 50:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 50",
        )

    gmail_client = GmailClient()
    threads = gmail_client.list_threads(limit=limit)

    return threads

@app.get("/ui")
def serve_ui():
    return FileResponse("ui/index.html")


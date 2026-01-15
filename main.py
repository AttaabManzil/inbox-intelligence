import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import uuid
import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from infra.gmail_client import GmailClient
from services.email_draft_service import EmailDraftService
from api.gmail_routes import router as gmail_router

# --------------------------------------------------
# DB CONFIG
# --------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "ai_workflows",
    "user": "postgres",
    "password": "postgres",
}

# --------------------------------------------------
# APP SETUP
# --------------------------------------------------
app = FastAPI(title="Enterprise AI Workflow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gmail_router)

# --------------------------------------------------
# SCHEMAS
# --------------------------------------------------
class CreateWorkflowRequest(BaseModel):
    text: str


class GenerateDraftRequest(BaseModel):
    user_context: str | None = None


# --------------------------------------------------
# CREATE WORKFLOW
# --------------------------------------------------
@app.post("/workflows")
def create_workflow(request: CreateWorkflowRequest):
    workflow_id = str(uuid.uuid4())

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflows (id, request_text, state)
                VALUES (%s, %s, 'RECEIVED');
                """,
                (workflow_id, request.text),
            )
        conn.commit()

    return {"workflow_id": workflow_id}


# --------------------------------------------------
# GET WORKFLOW
# --------------------------------------------------
@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, request_text, state, ai_output,
                       created_at, updated_at
                FROM workflows
                WHERE id = %s;
                """,
                (workflow_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "id": row[0],
        "request_text": row[1],
        "state": row[2],
        "ai_output": row[3],
        "created_at": row[4].isoformat(),
        "updated_at": row[5].isoformat(),
    }


# --------------------------------------------------
# LOAD CONVERSATION (ONE-TIME)
# --------------------------------------------------
@app.post("/workflows/{workflow_id}/load-conversation")
def load_conversation(workflow_id: str):
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT request_text, ai_output FROM workflows WHERE id = %s;",
                (workflow_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")

    request_text, ai_output = row

    # ✅ Already loaded → return cached data
    if ai_output and ai_output.get("thread"):
        return ai_output

    if not request_text.startswith("gmail:"):
        raise HTTPException(status_code=400, detail="Unsupported workflow type")

    gmail_thread_id = request_text.replace("gmail:", "").strip()

    gmail = GmailClient()
    thread = gmail.get_thread(gmail_thread_id)

    ai_output = {
        "type": "gmail_draft",
        "thread": thread,
        "draft": None,
    }

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE workflows
                SET ai_output = %s,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (json.dumps(ai_output), workflow_id),
            )
        conn.commit()

    return ai_output


# --------------------------------------------------
# GENERATE DRAFT (NO SIDE EFFECTS)
# --------------------------------------------------
@app.post("/workflows/{workflow_id}/generate-draft")
def generate_draft(workflow_id: str, payload: GenerateDraftRequest):

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ai_output FROM workflows WHERE id = %s;",
                (workflow_id,),
            )
            row = cur.fetchone()

    if not row or not row[0]:
        raise HTTPException(status_code=400, detail="Conversation not loaded")

    ai_output = row[0]
    thread = ai_output.get("thread")

    if not thread:
        raise HTTPException(status_code=400, detail="Conversation missing")

    draft = EmailDraftService().generate_draft(
        thread=thread["messages"],
        user_context=payload.user_context,
    )

    ai_output["draft"] = draft

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE workflows
                SET ai_output = %s,
                    state = 'WAITING_FOR_APPROVAL',
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (json.dumps(ai_output), workflow_id),
            )
        conn.commit()

    return {"status": "ok",
            "draft": draft
            }


# --------------------------------------------------
# SAVE GMAIL DRAFT
# --------------------------------------------------
@app.post("/workflows/{workflow_id}/save-gmail-draft")
def save_gmail_draft(workflow_id: str):
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ai_output FROM workflows WHERE id = %s;",
                (workflow_id,),
            )
            row = cur.fetchone()

    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Workflow not found")

    ai_output = row[0]

    gmail = GmailClient()
    draft_id = gmail.create_reply_draft(
        thread_id=ai_output["thread"]["thread_id"],
        to=ai_output["thread"]["to"],
        subject=ai_output["thread"]["subject"],
        body=ai_output["draft"]["body"],
        message_id=ai_output["thread"]["message_id"],
        references=ai_output["thread"]["references"],
    )

    return {"gmail_draft_id": draft_id}


# --------------------------------------------------
# SEND GMAIL EMAIL
# --------------------------------------------------
@app.post("/workflows/{workflow_id}/send-email")
def send_email(workflow_id: str):
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ai_output FROM workflows WHERE id = %s;",
                (workflow_id,),
            )
            row = cur.fetchone()

    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Workflow not found")

    ai_output = row[0]

    if not ai_output.get("draft"):
        raise HTTPException(status_code=400, detail="Draft missing")

    gmail = GmailClient()

    gmail.send_reply(
        thread_id=ai_output["thread"]["thread_id"],
        to=ai_output["thread"]["to"],
        subject=ai_output["thread"]["subject"],
        body=ai_output["draft"]["body"],
        message_id=ai_output["thread"]["message_id"],
        references=ai_output["thread"]["references"],
    )

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE workflows
                SET state = 'COMPLETED',
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (workflow_id,),
            )
        conn.commit()

    return {"status": "sent"}


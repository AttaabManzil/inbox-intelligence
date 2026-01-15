import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from infra.gmail_client import GmailClient
from services.email_draft_service import EmailDraftService
from api.gmail_routes import router as gmail_router

# --------------------------------------------------
# APP SETUP
# --------------------------------------------------
app = FastAPI(title="AI Email Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gmail_router)

# --------------------------------------------------
# REQUEST SCHEMAS
# --------------------------------------------------
class GenerateDraftRequest(BaseModel):
    thread_id: str
    user_context: str | None = None


class SendEmailRequest(BaseModel):
    thread_id: str
    body: str
    to: str
    subject: str
    message_id: str
    references: str


# --------------------------------------------------
# ENDPOINTS
# --------------------------------------------------
@app.post("/gmail/draft")
def generate_draft(request: GenerateDraftRequest):
    """Fetch Gmail thread and generate AI draft in one call."""
    try:
        gmail = GmailClient()
        thread = gmail.get_thread(request.thread_id)
        
        draft = EmailDraftService().generate_draft(
            thread=thread["messages"],
            user_context=request.user_context,
        )
        
        return {
            "thread": thread,
            "draft": draft
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/gmail/send")
def send_email(request: SendEmailRequest):
    """Send email reply."""
    try:
        gmail = GmailClient()
        
        gmail.send_reply(
            thread_id=request.thread_id,
            to=request.to,
            subject=request.subject,
            body=request.body,
            message_id=request.message_id,
            references=request.references,
        )
        
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/gmail/save-draft")
def save_draft(request: SendEmailRequest):
    """Save draft to Gmail without sending."""
    try:
        gmail = GmailClient()
        
        draft_id = gmail.create_reply_draft(
            thread_id=request.thread_id,
            to=request.to,
            subject=request.subject,
            body=request.body,
            message_id=request.message_id,
            references=request.references,
        )
        
        return {"draft_id": draft_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
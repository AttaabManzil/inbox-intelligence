from fastapi import APIRouter, HTTPException
from infra.gmail_client import GmailClient

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.get("/threads")
def list_threads(limit: int = 10):
    try:
        gmail = GmailClient()
        threads = gmail.list_threads(limit=limit)
        return threads
    except Exception as e:
        print("❌ Error listing threads:", str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch Gmail threads")

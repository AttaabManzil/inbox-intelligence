import os
import base64
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv()

class GmailClient:
    def __init__(self):
        self._service = self._build_service()

    def _build_service(self):
        creds = Credentials(
            token=None,
            refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GMAIL_CLIENT_ID"),
            client_secret=os.getenv("GMAIL_CLIENT_SECRET"),
            scopes=[
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.readonly",
            ],
        )
        return build("gmail", "v1", credentials=creds)

    def get_thread(self, thread_id: str) -> list[dict]:
        thread = (
            self._service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )

        messages = []

        for msg in thread.get("messages", []):
            headers = msg["payload"]["headers"]

            from_header = next(
                (h["value"] for h in headers if h["name"] == "From"),
                "Unknown",
            )

            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"),
                "",
            )

            body = self._extract_body(msg["payload"]).strip()

            messages.append(
                {
                    "from": from_header,
                    "subject": subject,
                    "content": body,
                }
            )

        return messages

    def create_draft(self, to: str, subject: str, body: str) -> str:
        raw_message = f"""To: {to}
Subject: {subject}
Content-Type: text/plain; charset="UTF-8"

{body}
"""

        encoded_message = base64.urlsafe_b64encode(
            raw_message.encode("utf-8")
        ).decode("utf-8")

        draft = (
            self._service.users()
            .drafts()
            .create(
                userId="me",
                body={
                    "message": {
                        "raw": encoded_message
                    }
                },
            )
            .execute()
        )

        return draft["id"]

    def _extract_body(self, payload):
        """
        Safely extract and decode the plain-text body from a Gmail message payload.
        """

        body = payload.get("body", {}).get("data")
        if body:
            try:
                return base64.urlsafe_b64decode(body).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                return ""

        for part in payload.get("parts", []):
            text = self._extract_body(part)
            if text:
                return text

        return ""
    
    
    def list_threads(self, limit: int = 10) -> list[dict]:
        results = (
            self._service.users()
            .threads()
            .list(
                userId="me",
                maxResults=limit,
                q="category:primary",
            )
            .execute()
        )

        threads = []

        for t in results.get("threads", []):
            thread = (
                self._service.users()
                .threads()
                .get(userId="me", id=t["id"], format="metadata")
                .execute()
            )

            headers = thread["messages"][-1]["payload"]["headers"]

            from_header = next(
                (h["value"] for h in headers if h["name"] == "From"),
                "Unknown",
            )

            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"),
                "",
            )

            snippet = thread.get("snippet", "")
            internal_date = thread["messages"][-1]["internalDate"]

            threads.append(
                {
                    "thread_id": t["id"],
                    "from": from_header,
                    "subject": subject,
                    "snippet": snippet,
                    "last_message_at": datetime.utcfromtimestamp(
                        int(internal_date) / 1000
                    ).isoformat() + "Z",
                }
            )

        return threads


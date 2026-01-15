import os
import base64
import re
from html import unescape
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.message import EmailMessage
from datetime import datetime

load_dotenv()


class GmailClient:
    def __init__(self):
        self.service = self._build_service()

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

        if not creds.refresh_token:
            raise RuntimeError("Gmail OAuth credentials missing")

        return build("gmail", "v1", credentials=creds)

    # ----------------------------
    # Helpers
    # ----------------------------

    def _extract_email(self, raw: str) -> str:
        """Extract email from 'Name <email@x.com>'"""
        match = re.search(r"<(.+?)>", raw)
        return match.group(1) if match else raw

    def _get_header(self, headers, name):
        """Extract header value safely"""
        return next(
            (h["value"] for h in headers if h["name"].lower() == name.lower()),
            ""
        )

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags and decode entities"""
        # Remove script and style tags with their content
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert common HTML elements to text equivalents
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</p>', '\n\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</div>', '\n', html, flags=re.IGNORECASE)
        
        # Remove all remaining HTML tags
        html = re.sub(r'<[^>]+>', '', html)
        
        # Decode HTML entities
        html = unescape(html)
        
        # Clean up whitespace
        lines = [line.strip() for line in html.split('\n')]
        html = '\n'.join(line for line in lines if line)
        
        return html.strip()

    def _extract_body(self, payload):
        """
        Extract and clean email body.
        Priority: text/plain > text/html (cleaned)
        """
        # Try to find text/plain part first
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode(errors="ignore")

        # Store HTML in case we need it as fallback
        html_body = None
        if payload.get("mimeType") == "text/html":
            data = payload.get("body", {}).get("data")
            if data:
                html_body = base64.urlsafe_b64decode(data).decode(errors="ignore")

        # Recursively check multipart messages
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode(errors="ignore")
            
            if part.get("mimeType") == "text/html" and not html_body:
                data = part.get("body", {}).get("data")
                if data:
                    html_body = base64.urlsafe_b64decode(data).decode(errors="ignore")
            
            # Check nested parts
            if part.get("parts"):
                text = self._extract_body(part)
                if text:
                    return text

        # Fallback to cleaned HTML if no plain text found
        if html_body:
            return self._strip_html(html_body)

        return ""

    def _build_reply_message(
        self,
        to: str,
        subject: str,
        body: str,
        message_id: str,
        references: str,
        thread_id: str,
    ) -> str:
        msg = EmailMessage()
        msg["To"] = self._extract_email(to)
        msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
        msg["In-Reply-To"] = message_id
        msg["References"] = references
        msg.set_content(body)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        return raw

    # ----------------------------
    # Public API
    # ----------------------------

    def list_threads(self, limit: int = 10):
        results = (
            self.service.users()
            .threads()
            .list(userId="me", maxResults=limit)
            .execute()
        )

        threads = []

        for t in results.get("threads", []):
            thread = (
                self.service.users()
                .threads()
                .get(userId="me", id=t["id"], format="metadata")
                .execute()
            )

            last_msg = thread["messages"][-1]
            headers = last_msg["payload"]["headers"]

            internal_date = int(last_msg["internalDate"]) / 1000

            threads.append(
                {
                    "thread_id": t["id"],
                    "from": self._get_header(headers, "From"),
                    "subject": self._get_header(headers, "Subject") or "(No subject)",
                    "snippet": thread.get("snippet", ""),
                    "last_message_at": datetime.utcfromtimestamp(
                        internal_date
                    ).isoformat()
                    + "Z",
                }
            )

        return threads

    def get_thread(self, thread_id):
        thread = self.service.users().threads().get(
            userId="me",
            id=thread_id,
            format="full"
        ).execute()

        messages = []

        for msg in thread["messages"]:
            headers = msg["payload"]["headers"]

            from_header = self._get_header(headers, "From")
            date_header = self._get_header(headers, "Date")

            body = self._extract_body(msg["payload"])
            if not body:
                continue

            # Skip system messages
            from_lower = from_header.lower()
            if any(skip in from_lower for skip in ["mailer-daemon", "postmaster", "noreply"]):
                # Still include but mark it
                pass

            messages.append({
                "from": from_header,
                "date": date_header,
                "body": body.strip(),
            })

        # Thread-level metadata (used for reply)
        last = thread["messages"][-1]
        last_headers = last["payload"]["headers"]

        return {
            "thread_id": thread_id,
            "to": self._get_header(last_headers, "From"),
            "subject": self._get_header(last_headers, "Subject"),
            "message_id": self._get_header(last_headers, "Message-ID"),
            "references": self._get_header(last_headers, "References")
                or self._get_header(last_headers, "Message-ID"),
            "messages": messages,
        }

    def create_reply_draft(
        self, thread_id, to, subject, body, message_id, references
    ):
        raw = self._build_reply_message(
            to=to,
            subject=subject,
            body=body,
            message_id=message_id,
            references=references,
            thread_id=thread_id,
        )

        draft = (
            self.service.users()
            .drafts()
            .create(
                userId="me",
                body={"message": {"raw": raw, "threadId": thread_id}},
            )
            .execute()
        )

        return draft["id"]

    def send_reply(
        self, thread_id, to, subject, body, message_id, references
    ):
        raw = self._build_reply_message(
            to=to,
            subject=subject,
            body=body,
            message_id=message_id,
            references=references,
            thread_id=thread_id,
        )

        self.service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": thread_id},
        ).execute()
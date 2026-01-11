import os
import base64
import json

from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from openai import OpenAI


# ==================================================
# LOAD ENVIRONMENT VARIABLES
# ==================================================

load_dotenv()

GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN]):
    raise RuntimeError("Missing Gmail OAuth environment variables")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")


# ==================================================
# GMAIL HELPERS
# ==================================================

def extract_body(payload):
    """
    Recursively extract plain-text email body from Gmail payload.
    """
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(
            payload["body"]["data"]
        ).decode("utf-8", errors="ignore")

    for part in payload.get("parts", []):
        text = extract_body(part)
        if text:
            return text

    return ""


def create_gmail_draft(service, to_email: str, subject: str, body: str):
    """
    Creates a Gmail draft (does NOT send).
    """
    raw_message = f"""To: {to_email}
Subject: {subject}
Content-Type: text/plain; charset="UTF-8"

{body}
"""

    encoded_message = base64.urlsafe_b64encode(
        raw_message.encode("utf-8")
    ).decode("utf-8")

    draft = (
        service.users()
        .drafts()
        .create(
            userId="me",
            body={
                "message": {
                    "raw": encoded_message
                }
            }
        )
        .execute()
    )

    return draft


# ==================================================
# AI DRAFTING
# ==================================================

client = OpenAI(api_key=OPENAI_API_KEY)


def draft_reply_email(email_thread: list[dict]) -> dict:
    """
    Draft a professional reply email using ONLY the provided email thread.
    """

    messages_text = "\n\n".join(
        f"From: {m['from']}\nMessage:\n{m['content']}"
        for m in email_thread
    )

    system_prompt = """
You are drafting a reply to an existing email thread.

Rules:
- Use ONLY the provided email thread as context.
- Do NOT invent new facts.
- Do NOT change prices, quantities, or commitments.
- Draft a professional, concise reply.
- Do NOT send the email.
- Return JSON only.

Return this exact schema:
{
  "to": string,
  "subject": string,
  "body": string,
  "tone": "professional"
}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": messages_text},
        ],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


# ==================================================
# MAIN
# ==================================================

def main():
    # ------------------------------------------------
    # Create refresh-capable Gmail credentials
    # ------------------------------------------------

    creds = Credentials(
        token=None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
    )

    service = build("gmail", "v1", credentials=creds)

    print("✅ Connected to Gmail using refresh token")

    # ------------------------------------------------
    # List recent threads
    # ------------------------------------------------

    threads_resp = service.users().threads().list(
        userId="me",
        maxResults=5
    ).execute()

    threads = threads_resp.get("threads", [])

    if not threads:
        print("No threads found.")
        return

    print("\n📨 Recent thread IDs:")
    for t in threads:
        print("-", t["id"])

    # ------------------------------------------------
    # Pick one thread (first one for now)
    # ------------------------------------------------

    THREAD_ID = threads[0]["id"]

    print(f"\n📧 Using thread: {THREAD_ID}")
    print("=" * 60)

    thread = service.users().threads().get(
        userId="me",
        id=THREAD_ID,
        format="full"
    ).execute()

    email_thread = []

    for i, msg in enumerate(thread.get("messages", []), start=1):

        headers = msg["payload"]["headers"]

        from_header = next(
            (h["value"] for h in headers if h["name"] == "From"),
            "Unknown"
        )

        subject = next(
            (h["value"] for h in headers if h["name"] == "Subject"),
            "No Subject"
        )

        body = extract_body(msg["payload"]).strip()

        print(f"\n--- Message {i} ---")
        print("From:", from_header)
        print("Subject:", subject)
        print("Body:\n", body[:1000])

        email_thread.append({
            "from": from_header,
            "content": body
        })

    # ------------------------------------------------
    # Generate AI Draft
    # ------------------------------------------------

    print("\n✍️ GENERATING AI DRAFT...")
    print("=" * 60)

    draft = draft_reply_email(email_thread)

    print("\n📨 AI EMAIL DRAFT")
    print("=" * 60)
    print("To:", draft["to"])
    print("Subject:", draft["subject"])
    print("\nBody:\n", draft["body"])
    print("\nTone:", draft["tone"])

    # ------------------------------------------------
    # Save Draft to Gmail
    # ------------------------------------------------

    print("\n📬 SAVING DRAFT TO GMAIL...")
    gmail_draft = create_gmail_draft(
        service=service,
        to_email=draft["to"],
        subject=draft["subject"],
        body=draft["body"],
    )

    print("✅ Draft saved to Gmail")
    print("Draft ID:", gmail_draft["id"])


if __name__ == "__main__":
    main()

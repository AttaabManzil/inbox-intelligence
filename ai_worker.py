import time
import json
import psycopg
from psycopg.rows import dict_row
from datetime import datetime
from openai import OpenAI

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

POLL_INTERVAL_SECONDS = 5
client = OpenAI()

# -------------------------------------------------------------------
# Event Logger
# -------------------------------------------------------------------

def log_event(cur, workflow_id, event_type, event_data=None):
    cur.execute(
        """
        INSERT INTO workflow_events (workflow_id, event_type, event_data, created_at)
        VALUES (%s, %s, %s, %s);
        """,
        (
            workflow_id,
            event_type,
            json.dumps(event_data) if event_data else None,
            datetime.utcnow(),
        ),
    )

# -------------------------------------------------------------------
# AI Draft Generator
# -------------------------------------------------------------------

def generate_gmail_draft(thread_messages: list[dict], user_context: str | None) -> dict:
    messages_text = "\n\n".join(
        f"From: {m['from']}\nMessage:\n{m['content']}"
        for m in thread_messages
    )

    system_prompt = f"""
You are drafting a reply to an existing email thread.

Rules:
- Use ONLY the provided email thread.
- Do NOT invent facts.
- Do NOT change commitments.
- Draft a professional business email.
- Do NOT send the email.
- Return JSON only.

Additional user instructions:
{user_context or "None"}

Return schema:
{{
  "to": string,
  "subject": string,
  "body": string,
  "tone": "professional"
}}
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

# -------------------------------------------------------------------
# Core Worker
# -------------------------------------------------------------------

def process_received_workflows():
    gmail_client = GmailClient()

    with psycopg.connect(**DB_CONFIG, row_factory=dict_row) as conn:
        while True:
            with conn.transaction():
                cur = conn.cursor()

                cur.execute(
                    """
                    SELECT id, request_text
                    FROM workflows
                    WHERE state = 'RECEIVED'
                    ORDER BY created_at
                    LIMIT 5;
                    """
                )

                workflows = cur.fetchall()

                for wf in workflows:
                    workflow_id = wf["id"]
                    request_text = wf["request_text"]

                    try:
                        payload = json.loads(request_text)
                        workflow_type = payload.get("type")
                    except Exception:
                        workflow_type = "GENERIC"

                    # ------------------------------------------------
                    # GMAIL DRAFT WORKFLOW
                    # ------------------------------------------------

                    if workflow_type == "GMAIL_DRAFT_FROM_THREAD":
                        gmail_thread_id = payload["gmail_thread_id"]
                        user_context = payload.get("user_context")

                        thread_messages = gmail_client.get_thread(gmail_thread_id)

                        draft = generate_gmail_draft(
                            thread_messages=thread_messages,
                            user_context=user_context,
                        )

                        required_fields = {"to", "subject", "body"}

                        if not isinstance(draft, dict) or not required_fields.issubset(draft):
                            log_event(
                                cur,
                                workflow_id,
                                "AI_DRAFT_INVALID",
                                {"raw_draft": draft},
                            )
                            continue  # do NOT transition state

                        ai_output = {
                            "type": "gmail_draft",
                            "draft": draft,
                        }

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

                        log_event(cur, workflow_id, "AI_DRAFT_CREATED", ai_output)
                        log_event(
                            cur,
                            workflow_id,
                            "STATE_TRANSITION",
                            {"from": "RECEIVED", "to": "WAITING_FOR_APPROVAL"},
                        )

            time.sleep(POLL_INTERVAL_SECONDS)

# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------

if __name__ == "__main__":
    print("AI Worker started (Gmail drafts stored, approval-gated)...")
    process_received_workflows()

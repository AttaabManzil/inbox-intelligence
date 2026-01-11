import json
import time
import psycopg
from datetime import datetime

from linear_client import create_issue
from sendgrid_client import send_email
from infra.gmail_client import GmailClient

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "ai_workflows",
    "user": "postgres",
    "password": "postgres",  # local dev only
}

MAX_LINEAR_ATTEMPTS = 3
LINEAR_BACKOFF_SECONDS = [2, 5, 10]

# -------------------------------------------------------------------
# Event Logger
# -------------------------------------------------------------------

def log_event(workflow_id: str, event_type: str, event_data=None):
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
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
        conn.commit()

# -------------------------------------------------------------------
# Idempotency Guards
# -------------------------------------------------------------------

def task_already_created(cur, workflow_id: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM workflow_events
        WHERE workflow_id = %s
          AND event_type = 'TASK_CREATED'
        LIMIT 1;
        """,
        (workflow_id,),
    )
    return cur.fetchone() is not None


def email_already_sent(cur, workflow_id: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM workflow_events
        WHERE workflow_id = %s
          AND event_type = 'EMAIL_SENT'
        LIMIT 1;
        """,
        (workflow_id,),
    )
    return cur.fetchone() is not None


def gmail_draft_already_created(cur, workflow_id: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM workflow_events
        WHERE workflow_id = %s
          AND event_type = 'GMAIL_DRAFT_CREATED'
        LIMIT 1;
        """,
        (workflow_id,),
    )
    return cur.fetchone() is not None

# -------------------------------------------------------------------
# Action Executors
# -------------------------------------------------------------------

def execute_create_task(workflow_id: str, request_text: str):
    """
    Safely creates a Linear task with retries and idempotency.
    """
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            if task_already_created(cur, workflow_id):
                return

            for attempt in range(MAX_LINEAR_ATTEMPTS):
                try:
                    issue = create_issue(
                        title="New Task from AI Workflow",
                        description=request_text,
                    )

                    log_event(
                        workflow_id,
                        "TASK_CREATED",
                        {
                            "issue_id": issue["id"],
                            "identifier": issue["identifier"],
                            "url": issue["url"],
                        },
                    )
                    conn.commit()
                    return

                except Exception as e:
                    log_event(
                        workflow_id,
                        "TASK_CREATION_FAILED",
                        {
                            "error": str(e),
                            "attempt": attempt + 1,
                        },
                    )
                    conn.commit()

                    if attempt < MAX_LINEAR_ATTEMPTS - 1:
                        time.sleep(LINEAR_BACKOFF_SECONDS[attempt])
                    else:
                        raise


def execute_send_email(workflow_id: str, request_text: str):
    """
    Sends an email exactly once.
    """
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            if email_already_sent(cur, workflow_id):
                return

            send_email(request_text)

            log_event(
                workflow_id,
                "EMAIL_SENT",
                {"content": request_text},
            )
            conn.commit()


def execute_create_gmail_draft(workflow_id: str, ai_output: dict):
    """
    Creates a Gmail draft exactly once after human approval.
    """
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            # Idempotency guard
            if gmail_draft_already_created(cur, workflow_id):
                return

            gmail_client = GmailClient()

            draft = ai_output["draft"]

            # ✅ CREATE draft + CAPTURE ID
            draft_id = gmail_client.create_draft(
                to=draft["to"],
                subject=draft["subject"],
                body=draft["body"],
            )

            # ✅ LOG correctly
            log_event(
                workflow_id,
                "GMAIL_DRAFT_CREATED",
                {
                    "draft_id": draft_id,
                    "to": draft["to"],
                    "subject": draft["subject"],
                },
            )

            conn.commit()

# -------------------------------------------------------------------
# Public Entry Point
# -------------------------------------------------------------------

def execute_action(
    action: str,
    workflow_id: str,
    request_text: str = None,
    ai_output: dict = None,
):
    """
    Executes a real-world action exactly once.
    """

    if action == "create_task":
        execute_create_task(workflow_id, request_text)

    elif action == "send_email":
        execute_send_email(workflow_id, request_text)

    elif action == "create_gmail_draft":
        execute_create_gmail_draft(workflow_id, ai_output)

    elif action == "reject":
        return

    else:
        raise ValueError(f"Unknown action: {action}")

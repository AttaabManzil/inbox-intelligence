import time
import json
import psycopg
from datetime import datetime
from psycopg.rows import dict_row

# -------------------------------------------------------------------
# Database Configuration
# -------------------------------------------------------------------

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "ai_workflows",
    "user": "postgres",
    "password": "postgres",  # local dev only
}

POLL_INTERVAL_SECONDS = 5

# -------------------------------------------------------------------
# Event Logger
# -------------------------------------------------------------------

def log_event(cur, workflow_id: str, event_type: str, event_data=None):
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
# AI Output Validation (NEW, EXPLICIT)
# -------------------------------------------------------------------

def validate_ai_output(ai_output: dict) -> tuple[bool, dict | None]:
    """
    Validates AI output against a strict contract.
    Returns (is_valid, error_details).
    """

    allowed_actions = {"create_task", "send_email", "reject"}

    if not isinstance(ai_output, dict):
        return False, {
            "reason": "invalid_type",
            "expected": "object",
            "received": type(ai_output).__name__,
        }

    if "recommended_action" not in ai_output:
        return False, {
            "reason": "missing_field",
            "field": "recommended_action",
            "message": "AI output must include 'recommended_action'",
        }

    if ai_output["recommended_action"] not in allowed_actions:
        return False, {
            "reason": "invalid_enum_value",
            "field": "recommended_action",
            "received": ai_output["recommended_action"],
            "expected": list(allowed_actions),
        }

    if "confidence" not in ai_output:
        return False, {
            "reason": "missing_field",
            "field": "confidence",
        }

    return True, None

# -------------------------------------------------------------------
# Core Processor
# -------------------------------------------------------------------

def process_ai_analyzed_workflows():
    with psycopg.connect(**DB_CONFIG, row_factory=dict_row) as conn:
        while True:
            with conn.transaction():
                cur = conn.cursor()

                cur.execute(
                    """
                    SELECT id, ai_output
                    FROM workflows
                    WHERE state = 'AI_ANALYZED'
                    ORDER BY updated_at
                    LIMIT 5;
                    """
                )

                workflows = cur.fetchall()

                for wf in workflows:
                    workflow_id = wf["id"]
                    ai_output = wf["ai_output"]

                    is_valid, error = validate_ai_output(ai_output)

                    # ---------------- INVALID AI OUTPUT ----------------

                    if not is_valid:
                        log_event(
                            cur,
                            workflow_id,
                            "AI_OUTPUT_INVALID",
                            {
                                "error": error,
                                "raw_ai_output": ai_output,
                            },
                        )

                        cur.execute(
                            """
                            UPDATE workflows
                            SET state = 'REJECTED',
                                updated_at = NOW()
                            WHERE id = %s;
                            """,
                            (workflow_id,),
                        )

                        log_event(
                            cur,
                            workflow_id,
                            "STATE_TRANSITION",
                            {
                                "from": "AI_ANALYZED",
                                "to": "REJECTED",
                                "reason": "Invalid AI output",
                            },
                        )
                        continue

                    # ---------------- VALID AI OUTPUT ----------------

                    cur.execute(
                        """
                        UPDATE workflows
                        SET state = 'WAITING_FOR_APPROVAL',
                            updated_at = NOW()
                        WHERE id = %s;
                        """,
                        (workflow_id,),
                    )

                    log_event(
                        cur,
                        workflow_id,
                        "STATE_TRANSITION",
                        {
                            "from": "AI_ANALYZED",
                            "to": "WAITING_FOR_APPROVAL",
                        },
                    )

            time.sleep(POLL_INTERVAL_SECONDS)

# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------

if __name__ == "__main__":
    print("Workflow Processor started (AI validation enabled)...")
    process_ai_analyzed_workflows()

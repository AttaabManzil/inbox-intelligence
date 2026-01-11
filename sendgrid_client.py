import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL")
TO_EMAIL = os.getenv("DEFAULT_EMAIL_TO")

if not SENDGRID_API_KEY:
    raise RuntimeError("SENDGRID_API_KEY is not set")


def send_email(content: str):
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject="AI Workflow Notification",
        plain_text_content=content,
    )

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)

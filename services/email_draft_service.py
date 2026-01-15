import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class EmailDraftService:
    """
    Generates a professional, ready-to-send email reply based on a Gmail thread.
    """

    def generate_draft(self, thread: list[dict], user_context: str | None = None):
        """
        thread: [
            { "from": "...", "body": "..." },
            ...
        ]
        """

        conversation = []

        for msg in thread:
            sender = msg.get("from", "User")
            body = msg.get("body") or msg.get("content") or ""

            if body.strip():
                conversation.append(f"{sender}:\n{body}")

        conversation_text = "\n\n".join(conversation)

        # ✅ SYSTEM PROMPT (behavior)
        system_prompt = (
            "You are a professional email assistant. "
            "Write clear, polite, and well-structured email replies suitable for sending via Gmail."
        )

        # ✅ USER PROMPT (task)
        user_prompt = f"""
Email conversation:
------------------
{conversation_text}

Instructions:
-------------
{user_context or "Write a professional and polite reply."}

Write a complete email reply including:
- A polite greeting
- Clear, concise paragraphs
- A professional closing and sign-off

Do NOT include a subject line.
Output ONLY the email content.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )

        body = response.choices[0].message.content.strip()

        return {
            "body": body
        }

import json
from openai import OpenAI

client = OpenAI()

class EmailDraftService:
    def generate_draft(self, thread: list[dict], user_context: str | None = None) -> dict:

        messages_text = "\n\n".join(
            f"From: {m['from']}\nMessage:\n{m['content']}"
            for m in thread
        )

        system_prompt = """
You are drafting a reply to an existing email thread.

Rules:
- Use ONLY the email thread for factual information.
- User preferences may guide tone or structure ONLY.
- Do NOT invent facts, dates, prices, or commitments.
- Draft a professional business email.
- Return JSON only.

Return this schema:
{
  "to": string,
  "subject": string,
  "body": string,
  "tone": "professional"
}
"""

        user_prompt = messages_text

        if user_context:
            user_prompt = (
                "User preferences (NOT facts):\n"
                f"{user_context}\n\n"
                "Email thread:\n"
                f"{messages_text}"
            )

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)

from openai import OpenAI
import json

client = OpenAI()


def draft_reply_email(email_thread: list[dict]) -> dict:
    messages_text = "\n\n".join(
        f"From: {m['from']}\nMessage: {m['content']}"
        for m in email_thread
    )

    prompt = f"""
Email thread:
{messages_text}

Draft a professional reply email.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You draft professional email replies."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)

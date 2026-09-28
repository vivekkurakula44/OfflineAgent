from groq import Groq
import os


def summarize(text: str) -> str:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a concise summarizer. Return only bullet points of key information. "
                    "No intro, no outro, no extra words."
                ),
            },
            {"role": "user", "content": f"Summarize this:\n\n{text[:6000]}"},
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content

from groq import Groq
import os


def generate_quiz(text: str) -> str:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate exactly 5 quiz questions with answers from the content. "
                    "Format: Q1: ... A1: ... Q2: ... A2: ... No extra text."
                ),
            },
            {"role": "user", "content": f"Generate quiz from:\n\n{text[:5000]}"},
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content

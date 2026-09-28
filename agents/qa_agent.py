from groq import Groq
import os


def answer_question(question: str, context: str) -> str:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer the question directly and concisely using only the provided context. "
                    "No extra words."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context[:5000]}\n\nQuestion: {question}",
            },
        ],
        max_tokens=512,
    )
    return response.choices[0].message.content

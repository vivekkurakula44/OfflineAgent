from groq import Groq
import os


def answer_exam(question: str, context: str) -> str:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer the exam question in a structured way using the provided notes. "
                    "Be thorough but concise. No padding."
                ),
            },
            {
                "role": "user",
                "content": f"Notes:\n{context[:5000]}\n\nExam Question: {question}",
            },
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content

import os

from groq import Groq
def rating(chat):
    client = Groq(
        api_key="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",
    )

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"{chat}",
            }
        ],
        model="llama3-8b-8192",
    )

    return chat_completion.choices[0].message.content
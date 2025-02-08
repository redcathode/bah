# ai_utils.py
import openai
from config import SYSTEM_PROMPT # Relative import

def generate_ai_response(prompt, api_key):
    """Generates AI response using OpenAI API."""
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )

    response = client.chat.completions.create(
        model="google/gemini-2.0-pro-exp-02-05:free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def parse_ai_response(response_text):
    """Parses the AI response to extract subject, recipients, content, and LaTeX blocks."""
    lines = [line.strip() for line in response_text.split('\n') if line.strip()]
    try:
        recipients = [addr.strip() for addr in lines[0].split('To:', 1)[-1].split(',')]
        content_lines = lines[1:]
        content = '\n'.join(content_lines)
        return recipients, content
    except IndexError:
        raise ValueError("Invalid response format from API")

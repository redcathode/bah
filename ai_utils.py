import openai
from config import SYSTEM_PROMPT
from db import truncate_history

def format_conversation_history(sender_email):
    """Formats conversation history for AI context as list of messages."""
    history = truncate_history(sender_email, 32)
    formatted_messages = []

    for message in history[-12:]:  # Consider last 12 messages (or less if history is shorter)
        role = message['role'].lower() # Convert role to lowercase for openai format
        content = message['content']
        formatted_messages.append({"role": role, "content": content})

    print("Formatted History Messages:")
    for msg in formatted_messages:
        print(f"{msg['role'].upper()}:\n{msg['content']}\n") # Print in original uppercase format for logging clarity
    return formatted_messages

def generate_ai_response(prompt, api_key, sender_email):
    """Generates AI response using OpenAI API with conversation history as separate messages."""
    client = openai.OpenAI(
        api_key=api_key,
        base_url="http://localhost:11434/v1/"
    )

    # Get formatted conversation history as list of messages
    history_messages = format_conversation_history(sender_email)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    messages.extend(history_messages) # Add history messages
    messages.append({"role": "user", "content": prompt}) # Add current user prompt

    print("Full messages payload to API:")
    for msg in messages:
        print(f"{msg['role'].upper()}:\n{msg['content']}\n") # Print in original uppercase format for logging clarity

    response = client.chat.completions.create(
        model="baitlm-24b",
        messages=messages
    )
    print(response)
    return response.choices[0].message.content

def parse_ai_response(response_text):
    """Parses the AI response to extract recipients, delay, and content."""
    lines = [line.strip() for line in response_text.split('\n') if line.strip()]
    try:
        # Extract recipients from first line
        recipients = [addr.strip() for addr in lines[0].split('To:', 1)[-1].split(',')]
        
        # Extract delay from second line
        delay_seconds = int(lines[1].split('Delay:', 1)[-1].strip())
        
        # Combine remaining lines for content
        content = '\n'.join(lines[2:])
        
        return recipients, delay_seconds, content
    except IndexError:
        print(response_text)
        raise ValueError("Invalid response format from API")

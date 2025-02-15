from ollama import chat
from pydantic import BaseModel, Field
from typing import List, Optional
import config
import json

class EmailDraft(BaseModel):
    should_skip_sending_email: bool = Field(description="Boolean indicating whether to skip sending an email")
    email_recipients: List[str] = Field(description="Who this email is to (this is usually just whoever sent the email to you)")
    email_delay: int = Field(description="Amount of time to delay sending the email, in seconds, as an integer (this is usually less than 120 and more than 20)")
    email_body: str = Field(description="Body of the email")
    descriptions_of_attached_documents: Optional[List[str]] = Field(description="Array of descriptions of attached documents - anything you specify here will be used to generate a document that will then be attached to your email", default_factory=list)
    # descriptions_of_attached_images: Optional[List[str]] = Field(description="Array of descriptions of attached images - anything you specify here will be used to generate an image that will then be attached to your email", default_factory=list)

from db import get_history_by_email

def format_conversation_history(sender_email):
    """Formats conversation history for AI context as list of messages."""
    history = get_history_by_email(sender_email)
    formatted_messages = []

    for message in history[-12:]:  # Consider last 12 messages (or less if history is shorter)
        role = message['role'].lower() # Convert role to lowercase for openai format
        content = message['content']
        formatted_messages.append({"role": role, "content": content})

    # print("Formatted History Messages:")
    # for msg in formatted_messages:
    #     print(f"{msg['role'].upper()}:\n{msg['content']}\n") # Print in original uppercase format for logging clarity
    return formatted_messages

def get_email_draft(sender_email, user_prompt):
    """
    Makes a request to ollama to generate an email draft with structured output.

    Args:
        user_prompt: The prompt for generating the email draft.

    Returns:
        EmailDraft: An EmailDraft object containing the structured output.
    """
    system_prompt = f"{config.SYSPROMPT_MAIN_STRUCTURED}\n\nHere is the JSON schema to use:\n{EmailDraft.model_json_schema()}\n"
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    messages.extend(format_conversation_history(sender_email)) # Add history messages
    messages.append({"role": "user", "content": user_prompt}) # Add current user prompt

    # print("Full messages payload to API:")
    # for msg in messages:
    #     print(f"{msg['role'].upper()}:\n{msg['content']}\n") # Print in original uppercase format for logging clarity

    response = chat(
        model='baitlm-24b-nonsys', # Or another suitable model
        messages=messages,
        format=EmailDraft.model_json_schema(),
    )
    
    email_draft = EmailDraft.model_validate_json(response.message.content)
    print(json.dumps(json.loads(response.message.content), indent=4))
    return email_draft.email_recipients, email_draft.email_delay, email_draft.email_body, email_draft.descriptions_of_attached_documents or [], email_draft.should_skip_sending_email

def generate_document_outline(email_history: str, document_request: str):
    response = chat(
        model='baitlm-24b-nonsys', # Or another suitable model
        messages=[
            {
                'role': 'system',
                'content': config.SYSPROMPT_DOCGEN,
            },
            {
                'role': 'user',
                'content': f"--- EMAIL HISTORY: ---\n{email_history}\n\n--- DOCUMENT DESCRIPTION ---\n{document_request}"
            }
        ]
    )

    return response


def generate_latex(outline: str):
    response = chat(
        model='Jotschi/dolphin-mistral-24b:24b-instruct-q5_0', # Or another suitable model
        messages=[
            {
                'role': 'system',
                'content': config.SYSPROMPT_LATEX,
            },
            {
                'role': 'user',
                'content': outline
            }
        ]
    )
    return response.message.content

if __name__ == "__main__":
    structured_email = get_email_draft_structured(cfg.EXAMPLE_EMAIL)
    print(f"Recipients:{structured_email.email_recipients}\nBody:\n{structured_email.email_body}\nDocument Descriptions: {structured_email.descriptions_of_attached_documents}")
    for doc in structured_email.descriptions_of_attached_documents or []:
        request_output = generate_document_outline(cfg.EXAMPLE_EMAIL + structured_email.email_body, doc).message.content
        print(request_output)
        texout = generate_latex(request_output)
        print(texout)
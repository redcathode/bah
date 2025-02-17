import openai
from pydantic import BaseModel, Field
from typing import List, Optional
import config
import json
from db import get_history_by_email
from latex_utils import create_pdf_from_latex_string

client = openai.OpenAI(
  base_url=config.OPENAI_API_ENDPOINT,
  api_key=config.OPENAI_API_KEY,
)


class EmailDraft(BaseModel):
    should_skip_sending_email: bool = Field(description="Boolean indicating whether to skip sending an email")
    email_recipients: List[str] = Field(description="Who this email is to (this is usually just whoever sent the email to you)")
    email_delay: int = Field(description="Amount of time to delay sending the email, in seconds, as an integer (this is usually less than 120 and more than 20)")
    email_body: str = Field(description="Body of the email")
    descriptions_of_attached_documents: Optional[List[str]] = Field(description="Array of descriptions of attached documents - anything you specify here will be used to generate a document that will then be attached to your email", default_factory=list)
    # descriptions_of_attached_images: Optional[List[str]] = Field(description="Array of descriptions of attached images - anything you specify here will be used to generate an image that will then be attached to your email", default_factory=list)



def format_conversation_history(sender_email):
    """Formats conversation history for AI context as list of messages."""
    history = get_history_by_email(sender_email)
    formatted_messages = []

    for message in history[-config.NUM_PREV_MESSAGES_IN_PROMPT:]:  # Consider last 12 messages (or less if history is shorter)
        role = message['role'].lower() # Convert role to lowercase for openai format
        content = message['content']
        formatted_messages.append({"role": role, "content": content})

    # print("Formatted History Messages:")
    # for msg in formatted_messages:
    #     print(f"{msg['role'].upper()}:\n{msg['content']}\n") # Print in original uppercase format for logging clarity
    return formatted_messages

def get_email_draft(sender_email, user_prompt):
    """
    Makes a request to OpenAI to generate an email draft with structured output.

    Args:
        user_prompt: The prompt for generating the email draft.

    Returns:
        EmailDraft: An EmailDraft object containing the structured output.
    """
    

    system_prompt = f"{config.SYSPROMPT_MAIN_STRUCTURED}\n\nHere is the JSON schema to use:\n{EmailDraft.model_json_schema()}\n"
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    messages.extend(format_conversation_history(sender_email))  # Add history messages
    messages.append({"role": "user", "content": user_prompt})  # Add current user prompt

    response = client.chat.completions.create(
        model=config.MODEL_NAME,  # Or another suitable model
        messages=messages,
        response_format={"type": "json_object"}
    )

    email_draft = EmailDraft.model_validate_json(response.choices[0].message.content)
    print(email_draft)
    print(json.dumps(json.loads(response.choices[0].message.content), indent=4))
    return email_draft.email_recipients, email_draft.email_delay, email_draft.email_body, email_draft.descriptions_of_attached_documents or [], email_draft.should_skip_sending_email

def generate_document_outline(email_history: str, document_request: str):

    response = client.chat.completions.create(
        model=config.MODEL_NAME,  # Or another suitable model
        messages=[
            {
                'role': 'system',
                'content': config.SYSPROMPT_DOCGEN,
            },
            {
                'role': 'user',
                'content': f"--- EMAIL DRAFT: ---\n{email_history}\n\n--- DOCUMENT DESCRIPTION ---\n{document_request}"
            }
        ]
    )

    return response.choices[0].message.content


def generate_latex(outline: str):
    response = client.chat.completions.create(
        model=config.MODEL_NAME,  # Or another suitable model
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
    return response.choices[0].message.content

if __name__ == "__main__":
    recipients, delay, body, descs, skip = get_email_draft("voodoodoctor@gmail.com", "Hi there\nCould you attach a PDF for me that says, 'hello world'?\nRemember to use the document attachment feature described in your system prompt.")
    print(f"Recipients:{recipients}\nBody:\n{body}\nDocument Descriptions: {descs}")
    for doc in descs:
        request_output = generate_document_outline(config.TEST_FAKE_EMAIL + body, doc)
        print(request_output)
        texout = generate_latex(request_output)
        print(create_pdf_from_latex_string(texout))

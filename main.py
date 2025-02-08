# main.py
import argparse
import os
import email
import imaplib
import json
from dotenv import load_dotenv

from config import EMAIL_ADDRESS, EMAIL_PASSWORD, OPENROUTER_API_KEY, CONVERSATION_HISTORY_FILE, MAX_HISTORY_LENGTH
from email_utils import fetch_emails, create_email_message, send_email, mark_email_as_read, validate_recipients
from email.utils import parseaddr
from ai_utils import generate_ai_response, parse_ai_response


# In main.py, add this function:
def truncate_history(history_list, max_length):
    """Truncates a list of history turns to a maximum character length."""
    total_length = 0
    truncated_history = []
    for turn in reversed(history_list): # Process from the end (most recent)
        turn_length = len(turn['content'])
        if total_length + turn_length <= max_length:
            truncated_history.insert(0, turn) # Insert at beginning to maintain order
            total_length += turn_length
        else:
            break # Stop adding older turns
    return truncated_history

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description='AI Email Autoresponder')
    parser.add_argument('--review', action='store_true', help='Review responses before sending')
    args = parser.parse_args()

    # Load configuration from .env
    email_address = os.getenv('EMAIL_ADDRESS') or EMAIL_ADDRESS
    email_password = os.getenv('EMAIL_PASSWORD') or EMAIL_PASSWORD
    api_key = os.getenv('OPENROUTER_API_KEY') or OPENROUTER_API_KEY

    if not email_address or not email_password or not api_key:
        print("Error: Email credentials or API key not configured in .env or config.py")
        return
    
          
    # In main.py, inside the main() function, before the IMAP connection:
    conversation_history = {}
    try:
        with open(CONVERSATION_HISTORY_FILE, 'r') as f:
            conversation_history = json.load(f)
    except FileNotFoundError:
        conversation_history = {} # Start with an empty history if file not found

    

    # Connect to IMAP server
    imap = imaplib.IMAP4_SSL('imap.gmail.com')
    imap.login(email_address, email_password)

    for folder in ['INBOX', '[Gmail]/Spam']:
        imap.select(folder) # Select the folder *before* fetching and processing

        # Find unread emails
        _, message_nums = imap.search(None, 'UNSEEN')
        for num in message_nums[0].split():
            # Fetch email
            _, data = imap.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])

            # Extract email details
            subject = msg['subject']
            from_ = msg['from']
            body = ''

            sender_email_address = parseaddr(from_)[1] # Get clean email address
            message_id = msg.get('Message-ID') # Extract Message-ID for threading

            current_history = conversation_history.get(sender_email_address, [])
            truncated_history = truncate_history(current_history, MAX_HISTORY_LENGTH)

            history_text = ""
            for turn in truncated_history:
                role = turn['role']
                content = turn['content']
                history_text += f"{role}: {content}\n"

            

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')

            # Generate AI response
            prompt = f"From: {from_}\n{body}\n"
            recipients, content = parse_ai_response(generate_ai_response(prompt, api_key))


            if "skip_send" in content.lower() or not from_:
                imap.store(num, '+FLAGS', '\\Seen')
                print(f"Skipped reply to {from_}")
                continue


            # User review
            if args.review:
                print(f"\nTo: {recipients}")
                print(f"Subject: Re: {subject}")
                print(f"\n{content}\n")
                choice = input("Send this response? (y/n/edit) ").lower()
                if choice == 'n':
                    imap.store(num, '+FLAGS', '\\Seen')
                    continue
                elif choice == 'edit':
                    content = input("Enter edited content: ")

            # Create and send email message
            mime_msg = create_email_message("Re:" + subject, recipients, content, sender_email=email_address, in_reply_to_message_id=message_id)
            send_email(email_address, email_password, mime_msg)

            # Mark as read and cleanup
            imap.store(num, '+FLAGS', '\\Seen')
            print(f"Replied to email from {from_}.")

            conversation_history.setdefault(sender_email_address, []).append({'role': 'user', 'content': f"From: {from_}\nSubject: {subject}\n{body}"}) # Add user message to history
            conversation_history.setdefault(sender_email_address, []).append({'role': 'assistant', 'content': f"To: {', '.join(recipients)}\n{content}" }) # Add assistant response to history

        imap.close() # Close the selected folder *after* processing all messages in it
                     # This is now inside the folder loop.
    imap.logout() # Logout and close the connection *after* processing all folders

    with open(CONVERSATION_HISTORY_FILE, 'w') as f:
        json.dump(conversation_history, f)
        # print("Conversation history saved.")

if __name__ == '__main__':
    main()

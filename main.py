import argparse
import os
import time
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from waitress import serve
import sqlite3
import imaplib
import email
from email.utils import parseaddr

# Import application modules
import config
import email_utils
import llmgen
import db
import latex_utils

def load_credentials():
    load_dotenv()

    # Load configuration from .env
    email_address = os.getenv('EMAIL_ADDRESS')
    email_password = os.getenv('EMAIL_PASSWORD')
    api_key = os.getenv('OPENAI_API_KEY')

    # Validate credentials
    missing = []
    if not email_address: missing.append("EMAIL_ADDRESS")
    if not email_password: missing.append("EMAIL_PASSWORD")
    if not api_key: missing.append("OPENAI_API_KEY")

    if missing:
        raise ValueError(f"Missing configuration for: {', '.join(missing)}")

    return email_address, email_password, api_key

def main():
    """Main email processing logic"""

    try:
        email_address, email_password, api_key = load_credentials()
    except ValueError as e:
        print(f"Configuration error: {e}")
        return

    # Connect to IMAP server
    imap = imaplib.IMAP4_SSL('imap.gmail.com')
    imap.login(email_address, email_password)
    conn = db.get_db_connection()

    for folder in ['INBOX', '[Gmail]/Spam']:
        try:
            imap.select(folder)
        except imaplib.IMAP4.error as e:
            print(f"Error selecting folder {folder}: {str(e)}")
            continue

        try:
            _, message_nums = imap.search(None, 'UNSEEN')
        except imaplib.IMAP4.error as e:
            print(f"Search failed in {folder}: {str(e)}")
            continue

        for num in message_nums[0].split():
            # Fetch email with retries
            msg = email_utils.fetch_email_by_index(imap, num, email_address, email_password, folder)
            
            subject, from_, body, sender_email, message_id = email_utils.process_email(msg)

            # Generate AI response with conversation history
            prompt = f"From: {from_}\n{body}\n"
            recipients, delay_seconds, content, skip = llmgen.get_email_draft(sender_email, prompt)
            
            if skip:
                imap.store(num, '+FLAGS', '\\Seen')
                print(f"Skipped reply to {from_}")
                continue

            # recipients, delay_seconds, content = ai_utils.parse_ai_response(ai_response)
            # Create and schedule email
            # Generate PDF attachments
            # pdf_paths = []
            # for doc in document_descs:
            #     request_output = llmgen.generate_latex(llmgen.generate_document_outline(content, doc))
            #     if request_output.strip().startswith("```latex"):
            #         request_output = request_output.strip().split("```latex")[1].split("```")[0]
            #     pdf_path = latex_utils.create_pdf_from_latex_string(request_output)
            #     pdf_paths.append(pdf_path)

            mime_msg = email_utils.create_email_message(
                f"Re: {subject}",
                recipients,
                content,
                # pdf_paths=pdf_paths,
                sender_email=email_address,
                in_reply_to_message_id=message_id
            )

            job_id = f"email_{message_id}_{datetime.now().timestamp()}"
            scheduled_time = datetime.now() + timedelta(seconds=delay_seconds)
            
            # Schedule and log email
            scheduler.add_job(
                email_utils.send_email,
                'date',
                run_date=scheduled_time,
                args=[email_address, email_password, mime_msg],
                id=job_id
            )
            # Mark as read and store history
            imap.store(num, '+FLAGS', '\\Seen')
            db.log_conversation(conn, sender_email, from_, subject, body, recipients, delay_seconds, content)

            print(f"Scheduled response to {from_} in {delay_seconds} seconds")
            imap.close()

    try:
        imap.logout() # Logout outside the loop
    finally:
        conn.close()


if __name__ == '__main__':
    load_dotenv()
    db.init_db()

    if config.TESTING:
        print("Testing mode enabled. Conversing in terminal...")
        api_key = os.getenv('OPENROUTER_API_KEY')

        sender_email = config.TEST_FAKE_EMAIL
        conn = db.get_db_connection()

        while True:
            user_input = input("You: ")
            if user_input.lower() == 'exit':
                break

            prompt = f"From: terminal_user\n{user_input}\n"
            recipients, delay_seconds, content, skip = llmgen.get_email_draft(sender_email, prompt)
            print(f"""Skip: {skip}
Recipients: {", ".join(recipients)}
Delay: {delay_seconds}
Content:
{content}""")
            # for doc in document_descs:
            #     request_output = llmgen.generate_latex(llmgen.generate_document_outline(content, doc))
            #     if request_output.strip().startswith("```latex"):
            #         request_output = request_output.strip().split("```latex")[1].split("```")[0]
            #     print(latex_utils.create_pdf_from_latex_string(request_output))
            # Log conversation in test DB
            db.log_conversation(conn, sender_email, "terminal_user", "Terminal Input", user_input, [], 0, content)

        conn.close()
    
    # Initialize scheduler and database
    scheduler = BackgroundScheduler()
    scheduler.start()
 

    # Schedule email checks every 5 minutes
    scheduler.add_job(
        main,
        'interval',
        seconds=config.SCHEDULER_INTERVAL,
        next_run_time=datetime.now()
    )

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)

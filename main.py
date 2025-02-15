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
import ai_utils
import db

def load_credentials():
    load_dotenv()

    # Load configuration from .env
    email_address = os.getenv('EMAIL_ADDRESS') or config.EMAIL_ADDRESS
    email_password = os.getenv('EMAIL_PASSWORD') or config.EMAIL_PASSWORD
    api_key = os.getenv('OPENROUTER_API_KEY') or config.OPENROUTER_API_KEY

    # Validate credentials
    missing = []
    if not email_address: missing.append("EMAIL_ADDRESS")
    if not email_password: missing.append("EMAIL_PASSWORD")
    if not api_key: missing.append("OPENROUTER_API_KEY")

    if missing:
        print(f"Error: Missing configuration for: {', '.join(missing)}")
        exit(1) # sort of a TODO

    return email_address, email_password, api_key

def main():
    """Main email processing logic"""
    email_address, email_password, api_key = load_credentials()

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
            ai_response = ai_utils.generate_ai_response(prompt, api_key, sender_email)
            if "skip_send" in ai_response.lower() or not from_:
                imap.store(num, '+FLAGS', '\\Seen')
                print(f"Skipped reply to {from_}")
                continue

            recipients, delay_seconds, content = ai_utils.parse_ai_response(ai_response)
            # Create and schedule email
            mime_msg = email_utils.create_email_message(
                f"Re: {subject}",
                recipients,
                content,
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
            conn.execute(
                "INSERT INTO conversations (sender_email, role, content) VALUES (?, ?, ?)",
                (sender_email, 'user', f"From: {from_}\nSubject: {subject}\n{body}")
            )
            conn.execute(
                "INSERT INTO conversations (sender_email, role, content) VALUES (?, ?, ?)",
                (sender_email, 'assistant', f"To: {', '.join(recipients)}\nDelay: {delay_seconds}\n{content}")
            )
            conn.commit()

            print(f"Scheduled response to {from_} in {delay_seconds} seconds")



        imap.close()
    imap.logout()
    conn.close()


if __name__ == '__main__':
    load_dotenv()
    
    # Initialize scheduler and database
    scheduler = BackgroundScheduler()
    scheduler.start()
    db.init_db()
    # Get credentials from environment variables or config
    email_address = os.getenv('EMAIL_ADDRESS') or config.EMAIL_ADDRESS
    email_password = os.getenv('EMAIL_PASSWORD') or config.EMAIL_PASSWORD
    #reschedule_pending_emails(scheduler, email_address, email_password)

    # Create and start Flask app in a separate thread

    # Schedule email checks every 5 minutes
    scheduler.add_job(
        main,
        'interval',
        minutes=1,
        next_run_time=datetime.now()
    )

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)

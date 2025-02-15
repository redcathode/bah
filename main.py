import argparse
import os
import time
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from web.app import create_app
from waitress import serve
import sqlite3
import imaplib
import email
from email.utils import parseaddr

# Import application modules
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, OPENROUTER_API_KEY, MAX_HISTORY_LENGTH
from email_utils import fetch_emails, create_email_message, send_email, mark_email_as_read, validate_recipients
from ai_utils import generate_ai_response, parse_ai_response
from db import init_db, get_db_connection, log_scheduled_email, get_scheduled_emails, truncate_history

def main():
    """Main email processing logic"""
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='AI Email Autoresponder')
    parser.add_argument('--review', action='store_true', help='Review responses before sending')
    args = parser.parse_args()

    # Load configuration from .env
    email_address = os.getenv('EMAIL_ADDRESS') or EMAIL_ADDRESS
    email_password = os.getenv('EMAIL_PASSWORD') or EMAIL_PASSWORD
    api_key = os.getenv('OPENROUTER_API_KEY') or OPENROUTER_API_KEY

    # Validate credentials
    missing = []
    if not email_address: missing.append("EMAIL_ADDRESS")
    if not email_password: missing.append("EMAIL_PASSWORD")
    if not api_key: missing.append("OPENROUTER_API_KEY")
    
    if missing:
        print(f"Error: Missing configuration for: {', '.join(missing)}")
        return

    # Connect to IMAP server
    imap = imaplib.IMAP4_SSL('imap.gmail.com')
    imap.login(email_address, email_password)
    conn = get_db_connection()

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
            for attempt in range(3):
                try:
                    _, data = imap.fetch(num, '(RFC822)')
                    msg = email.message_from_bytes(data[0][1])
                    break
                except imaplib.IMAP4.abort:
                    if attempt == 2:
                        raise
                    print("IMAP connection lost, reconnecting...")
                    imap.logout()
                    imap = imaplib.IMAP4_SSL('imap.gmail.com')
                    imap.login(email_address, email_password)
                    imap.select(folder)
            
            # Process email
            subject = msg['subject']
            from_ = msg['from']
            body = ''
            sender_email = parseaddr(from_)[1]
            message_id = msg.get('Message-ID')

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')

            # Generate AI response with conversation history
            prompt = f"From: {from_}\n{body}\n"
            recipients, delay_seconds, content = parse_ai_response(
                generate_ai_response(prompt, api_key, sender_email)
            )

            if "skip_send" in content.lower() or not from_:
                imap.store(num, '+FLAGS', '\\Seen')
                print(f"Skipped reply to {from_}")
                continue

            # User review logic
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

            # Create and schedule email
            mime_msg = create_email_message(
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
                send_email,
                'date',
                run_date=scheduled_time,
                args=[email_address, email_password, mime_msg],
                id=job_id
            )
            log_scheduled_email(job_id, email_address, recipients, content, scheduled_time)

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

def reschedule_pending_emails(scheduler, email_address_param, email_password_param):
    """Reschedule pending emails from the database on startup."""
    print("Rescheduling pending emails...")
    scheduled_emails = get_scheduled_emails()
    for scheduled_email in scheduled_emails:
        job_id = scheduled_email['id']
        recipients = scheduled_email['recipients'].split(', ')
        content = scheduled_email['content']
        scheduled_time = datetime.fromisoformat(scheduled_email['scheduled_time'])

        if scheduled_time > datetime.now():
            print(f"Rescheduling email job {job_id} for {scheduled_time}")
            scheduler.add_job(
                send_email,
                'date',
                run_date=scheduled_time,
                args=[email_address_param, email_password_param, create_email_message(
                    "Re: [Rescheduled]", # Subject will be overridden by AI response logic, adding a placeholder
                    recipients,
                    content,
                    sender_email=email_address_param
                )],
                id=job_id
            )
        else:
            print(f"Scheduled time for job {job_id} is in the past. Sending immediately.")
            send_email(
                email_address_param,
                email_password_param,
                create_email_message(
                    "Re: [Past Scheduled Email]",
                    recipients,
                    content,
                    sender_email=email_address_param
                )
            )


if __name__ == '__main__':
    load_dotenv()
    
    # Initialize scheduler and database
    scheduler = BackgroundScheduler()
    scheduler.start()
    init_db()
    # Get credentials from environment variables or config
    email_address = os.getenv('EMAIL_ADDRESS') or EMAIL_ADDRESS
    email_password = os.getenv('EMAIL_PASSWORD') or EMAIL_PASSWORD
    #reschedule_pending_emails(scheduler, email_address, email_password)

    # Create and start Flask app in a separate thread
    app = create_app(scheduler)
    flask_thread = threading.Thread(
        target=lambda: serve(app, host='0.0.0.0', port=5000),
        daemon=True
    )
    print("Starting Flask app...") # Add print statement
    flask_thread.start()

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

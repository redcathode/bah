# email_utils.py
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import parseaddr
import os

def fetch_emails(email_address, email_password, folders=['INBOX', '[Gmail]/Spam']):
    """Fetches unread emails from specified IMAP folders."""
    imap = imaplib.IMAP4_SSL('imap.gmail.com')
    imap.login(email_address, email_password)
    messages = []
    for folder in folders:
        imap.select(folder)
        _, message_nums = imap.search(None, 'UNSEEN')
        for num in message_nums[0].split():
            _, data = imap.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            messages.append((num, msg, folder)) # Include folder info for later use if needed
    imap.close()
    imap.logout()
    return messages

# In email_utils.py, modify create_email_message function:
def create_email_message(subject, recipients, content, sender_email=None, in_reply_to_message_id=None): # Add in_reply_to_message_id parameter
    """Creates a MIME message, optionally with PDF attachments and In-Reply-To header."""
    mime_msg = MIMEText(content)

    mime_msg['Subject'] = subject
    mime_msg['From'] = sender_email
    mime_msg['To'] = ', '.join(recipients)

    if in_reply_to_message_id: # Add In-Reply-To header if message ID is provided
        mime_msg['In-Reply-To'] = in_reply_to_message_id
        mime_msg['References'] = in_reply_to_message_id # Optional: Also set References for better threading

    return mime_msg

def send_email(email_address, email_password, msg):
    """Send email using SMTP with error handling and retries"""
    if not email_address or not email_password:
        raise ValueError("Missing email credentials - check EMAIL_ADDRESS/EMAIL_PASSWORD in config")
        
    try:
        smtp = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        smtp.login(email_address, email_password)
        smtp.send_message(msg)
        print(f"Successfully sent email to {msg['To']}")
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication failed: {str(e)}")
        raise
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise
    finally:
        try:
            smtp.quit()
        except: pass

def mark_email_as_read(imap_connection, message_num):
    """Marks an email as read on the IMAP server."""
    imap_connection.store(message_num, '+FLAGS', '\\Seen')

def validate_recipients(recipients):
    """Validates email recipients, ensuring they are properly formatted."""
    valid_recipients = []
    for addr in recipients:
        parsed = parseaddr(addr)[1]
        if '@' in parsed:
            valid_recipients.append(parsed)
    return valid_recipients
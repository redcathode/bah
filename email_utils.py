# email_utils.py
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import parseaddr
import os


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

def fetch_email_by_index(imap, idx, addr, passwd, folder, num_tries=3):
    for attempt in range(num_tries):
        try:
            _, data = imap.fetch(idx, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            return msg
        except imaplib.IMAP4.abort:
            if attempt == num_tries - 1:
                raise
            print("IMAP connection lost, reconnecting...")
            imap.logout()
            imap = imaplib.IMAP4_SSL('imap.gmail.com')
            imap.login(addr, passwd)
            imap.select(folder)




def process_email(msg):
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

    return subject, from_, body, sender_email, message_id
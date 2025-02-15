import unittest
import latex_utils
import email_utils
import os
from dotenv import load_dotenv

def load_credentials():
    load_dotenv()

    # Load configuration from .env
    email_address = os.getenv('EMAIL_ADDRESS')
    email_password = os.getenv('EMAIL_PASSWORD')
    api_key = os.getenv('OPENROUTER_API_KEY')

    # Validate credentials
    missing = []
    if not email_address: missing.append("EMAIL_ADDRESS")
    if not email_password: missing.append("EMAIL_PASSWORD")
    if not api_key: missing.append("OPENROUTER_API_KEY")

    if missing:
        raise ValueError(f"Missing configuration for: {', '.join(missing)}")

    return email_address, email_password, api_key

class TestLatexAndEmail(unittest.TestCase):

    def test_latex_generation_and_email(self):
        EMAIL_ADDRESS, EMAIL_PASSWORD, _ = load_credentials()
        # Define a simple LaTeX string
        latex_string = r"""
\documentclass{article}
\usepackage{amsmath}
\title{Test Document}
\author{Roo}
\date{\today}
\begin{document}
\maketitle
\section{Introduction}
This is a test document created from a LaTeX string.
\[
E=mc^2
\]
\end{document}
"""

        # Generate the PDF from the LaTeX string
        pdf_path = latex_utils.create_pdf_from_latex_string(latex_string)
        self.assertTrue(os.path.exists(pdf_path))

        # Email parameters
        subject = "Test Email with PDF Attachment"
        recipients = ["devbyte255@gmail.com"]
        content = "This is a test email with a PDF attachment generated from LaTeX."

        # Create the email message
        msg = email_utils.create_email_message(subject, recipients, content, pdf_paths=[pdf_path], sender_email=EMAIL_ADDRESS)

        # Send the email
        try:
            email_utils.send_email(EMAIL_ADDRESS, EMAIL_PASSWORD, msg)
            print("Email sent successfully!")
        except Exception as e:
            print(f"Email sending failed: {e}")
            self.fail(f"Email sending failed: {e}")

        # Clean up the PDF file
        os.remove(pdf_path)
        self.assertFalse(os.path.exists(pdf_path))


if __name__ == '__main__':
    unittest.main()
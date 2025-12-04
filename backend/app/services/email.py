from typing import Optional
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import base64
    from email.mime.text import MIMEText as GmailMIMEText
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False


class EmailClient:
    def __init__(self):
        self.provider = os.getenv("EMAIL_PROVIDER", "").lower()
        self.api_key = os.getenv("EMAIL_API_KEY", "")
        self.from_address = os.getenv("EMAIL_FROM_ADDRESS", "")
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.enabled = bool(self.provider and self.from_address)
        if self.provider == "sendgrid":
            self.enabled = self.enabled and bool(self.api_key) and SENDGRID_AVAILABLE
        elif self.provider == "gmail":
            self.enabled = self.enabled and bool(self.api_key) and GMAIL_AVAILABLE
        elif self.provider == "smtp":
            self.enabled = self.enabled and bool(self.smtp_user and self.smtp_password)

    def send_email(self, to_email: str, subject: str, body: str) -> Optional[str]:
        if not self.enabled:
            return None
        try:
            if self.provider == "sendgrid" and SENDGRID_AVAILABLE:
                sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
                message = Mail(
                    from_email=self.from_address,
                    to_emails=to_email,
                    subject=subject,
                    plain_text_content=body
                )
                response = sg.send(message)
                return str(response.status_code)
            elif self.provider == "gmail" and GMAIL_AVAILABLE:
                creds_data = json.loads(self.api_key) if self.api_key.startswith("{") else None
                if creds_data:
                    creds = service_account.Credentials.from_service_account_info(
                        creds_data,
                        scopes=['https://www.googleapis.com/auth/gmail.send']
                    )
                else:
                    return None
                service = build('gmail', 'v1', credentials=creds)
                message = GmailMIMEText(body)
                message['to'] = to_email
                message['from'] = self.from_address
                message['subject'] = subject
                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                send_message = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
                return send_message.get('id')
            elif self.provider == "smtp":
                msg = MIMEMultipart()
                msg['From'] = self.from_address
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.from_address, to_email, text)
                server.quit()
                return "smtp-sent"
            return None
        except Exception as e:
            print(f"Error sending email: {e}")
            return None



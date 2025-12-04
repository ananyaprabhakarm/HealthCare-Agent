from typing import Optional
import os
import json
import requests

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


class NotificationClient:
    def __init__(self):
        self.provider = os.getenv("NOTIFICATION_PROVIDER", "").lower()
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        self.whatsapp_api_key = os.getenv("WHATSAPP_API_KEY", "")
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "")
        self.enabled = bool(self.provider)

    def send(self, channel: str, recipient: str, message: str) -> Optional[str]:
        if not self.enabled:
            return None
        try:
            if channel == "slack" and self.slack_webhook:
                payload = {
                    "text": message,
                    "username": "Doctor Assistant"
                }
                response = requests.post(self.slack_webhook, json=payload, timeout=10)
                if response.status_code == 200:
                    return f"slack-{response.text[:20]}"
                return None
            elif channel == "whatsapp":
                if self.provider == "twilio" and TWILIO_AVAILABLE and self.twilio_account_sid and self.twilio_auth_token:
                    client = TwilioClient(self.twilio_account_sid, self.twilio_auth_token)
                    from_number = self.twilio_whatsapp_from or f"whatsapp:+{self.twilio_account_sid}"
                    to_number = recipient if recipient.startswith("whatsapp:") else f"whatsapp:{recipient}"
                    twilio_message = client.messages.create(
                        body=message,
                        from_=from_number,
                        to=to_number
                    )
                    return twilio_message.sid
                elif self.whatsapp_api_key:
                    headers = {
                        "Authorization": f"Bearer {self.whatsapp_api_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "to": recipient,
                        "message": message
                    }
                    response = requests.post(
                        "https://api.whatsapp.com/v1/messages",
                        json=payload,
                        headers=headers,
                        timeout=10
                    )
                    if response.status_code == 200:
                        return response.json().get("id")
                return None
            elif channel == "in_app":
                return f"in-app-{recipient}-{len(message)}"
            return None
        except Exception as e:
            print(f"Error sending notification: {e}")
            return None



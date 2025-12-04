from typing import Optional
import os


class NotificationClient:
    def __init__(self):
        self.provider = os.getenv("NOTIFICATION_PROVIDER", "")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        self.whatsapp_api_key = os.getenv("WHATSAPP_API_KEY", "")
        self.enabled = bool(self.provider)

    def send(self, channel: str, recipient: str, message: str) -> Optional[str]:
        if not self.enabled:
            return None
        if channel == "slack" and self.slack_webhook:
            return "mock-slack-message-id"
        if channel == "whatsapp" and self.whatsapp_api_key:
            return "mock-whatsapp-message-id"
        if channel == "in_app":
            return "mock-in-app-notification-id"
        return None



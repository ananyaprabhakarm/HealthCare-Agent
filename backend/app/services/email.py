from typing import Optional
import os


class EmailClient:
    def __init__(self):
        self.provider = os.getenv("EMAIL_PROVIDER", "")
        self.api_key = os.getenv("EMAIL_API_KEY", "")
        self.from_address = os.getenv("EMAIL_FROM_ADDRESS", "")
        self.enabled = bool(self.provider and self.api_key and self.from_address)

    def send_email(self, to_email: str, subject: str, body: str) -> Optional[str]:
        if not self.enabled:
            return None
        return "mock-email-id"



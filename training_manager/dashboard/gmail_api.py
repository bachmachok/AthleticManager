# training_manager/dashboard/gmail_api.py
from __future__ import annotations
import base64
from email.mime.text import MIMEText
from pathlib import Path

from django.conf import settings

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Файли лежать поруч із manage.py
BASE_DIR = Path(getattr(settings, "BASE_DIR"))
CLIENT_SECRET_PATH = BASE_DIR / "credentials.json"   # <- той самий файл, що у create_token.py
TOKEN_PATH = BASE_DIR / "token.json"                 # <- і той же token.json

def _load_credentials() -> Credentials | None:
    if TOKEN_PATH.exists():
        return Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    return None

def _save_credentials(creds: Credentials) -> None:
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

def ensure_gmail_service():
    """
    Валідний Gmail service або RefreshError з підказкою перевидати токен.
    """
    creds = _load_credentials()

    if creds and creds.valid:
        return build("gmail", "v1", credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(creds)
            return build("gmail", "v1", credentials=creds)
        except RefreshError as e:
            raise RefreshError(
                "Gmail refresh token is invalid or revoked. "
                "Delete token.json and recreate it (run create_token.py)."
            ) from e

    raise RefreshError(
        "No valid Gmail credentials. Create token.json first (run create_token.py)."
    )

def send_gmail(to_email: str, subject: str, body: str):
    service = ensure_gmail_service()
    msg = MIMEText(body, _charset="utf-8")
    msg["to"] = to_email
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()

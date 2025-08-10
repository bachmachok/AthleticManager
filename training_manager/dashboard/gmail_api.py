import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def send_gmail(to_email: str, subject: str, body: str):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    service = build("gmail", "v1", credentials=creds)

    msg = MIMEText(body, _charset="utf-8")
    msg["to"] = to_email
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

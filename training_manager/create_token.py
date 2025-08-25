from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS = BASE_DIR / "credentials.json"
TOKEN = BASE_DIR / "token.json"

def main():
    creds = None
    if TOKEN.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None
        if not creds:
            if not CREDENTIALS.exists():
                raise SystemExit(f"Не знайдено {CREDENTIALS}")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

        TOKEN.write_text(creds.to_json(), encoding="utf-8")
        print(f"OK: token.json створено у {TOKEN}")
    else:
        print("OK: чинний token.json вже є")

if __name__ == "__main__":
    main()

"""
Real Gmail integration via the official Gmail API (OAuth2) -- no
password automation, no scraping, nothing that could get your account
flagged. First run opens a browser for you to grant access once;
after that it refreshes silently.

ONE-TIME SETUP (you do this yourself, takes ~3 minutes):
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a project (or pick an existing one)
3. Click "+ Create Credentials" -> "OAuth client ID"
   - If prompted, configure the consent screen first (External, add
     your own email as a test user) -- takes one extra minute
   - Application type: Desktop app
4. Download the resulting JSON, save it as credentials.json in this
   same folder as main.py (~/darling/credentials.json)
5. Enable the Gmail API for the project: search "Gmail API" in the
   console and click Enable

That's it -- the first time you ask Darling to check your email, a
browser tab opens asking you to log in and approve access. After that
it's automatic.
"""
import os

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
_HERE = os.path.dirname(__file__)
CREDENTIALS_PATH = os.path.join(_HERE, "credentials.json")
TOKEN_PATH = os.path.join(_HERE, "data", "gmail_token.json")


def _get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise RuntimeError(
                    "credentials.json not found -- see gmail_helper.py for one-time setup steps"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def get_recent_subjects(n: int = 5) -> str:
    """Returns a short spoken-friendly summary of the n most recent
    emails' senders and subjects. Raises if credentials aren't set up."""
    service = _get_service()
    result = service.users().messages().list(userId="me", maxResults=n).execute()
    messages = result.get("messages", [])
    if not messages:
        return "You don't have any recent emails."

    lines = []
    for m in messages:
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        sender = headers.get("From", "someone").split("<")[0].strip()
        subject = headers.get("Subject", "(no subject)")
        lines.append(f"from {sender}: {subject}")

    return f"You have {len(lines)} recent emails. " + "; ".join(lines)

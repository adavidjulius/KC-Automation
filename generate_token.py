#!/usr/bin/env python3
"""
generate_token.py
-----------------
Run this ONCE on your local machine to authorize your YouTube account.
It will open a browser, ask you to log in, then save token.json.
Copy the contents of token.json into your GitHub Secret: YOUTUBE_TOKEN_JSON
"""

import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

CREDENTIALS_FILE = "credentials.json"   # Download from Google Cloud Console
TOKEN_FILE       = "token.json"

def main():
    if not Path(CREDENTIALS_FILE).exists():
        print(f"❌  {CREDENTIALS_FILE} not found!")
        print("    Go to: https://console.cloud.google.com/")
        print("    → APIs & Services → Credentials → Create OAuth 2.0 Client ID")
        print("    → Application type: Desktop app → Download JSON → rename to credentials.json")
        return

    flow  = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    Path(TOKEN_FILE).write_text(creds.to_json())
    print(f"\n✅  Token saved to {TOKEN_FILE}")
    print(f"\n📋  Copy the contents below into GitHub Secret: YOUTUBE_TOKEN_JSON\n")
    print("─" * 60)
    print(Path(TOKEN_FILE).read_text())
    print("─" * 60)

if __name__ == "__main__":
    main()

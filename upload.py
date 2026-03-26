import os, json, google.auth.transport.requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

creds = Credentials(
    token=os.environ['YOUTUBE_ACCESS_TOKEN'],
    refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ['YOUTUBE_CLIENT_ID'],
    client_secret=os.environ['YOUTUBE_CLIENT_SECRET']
)

# Auto refresh if token expired
request = google.auth.transport.requests.Request()
if creds.expired:
    creds.refresh(request)

youtube = build('youtube', 'v3', credentials=creds)

body = {
    "snippet": {
        "title": os.environ.get("VIDEO_TITLE", "Auto Reposted Video"),
        "description": os.environ.get("VIDEO_DESC", "Auto reposted via GitHub Actions 🤖"),
        "tags": ["repost", "auto"],
        "categoryId": "22"
    },
    "status": {
        "privacyStatus": os.environ.get("PRIVACY", "public")
    }
}

media = MediaFileUpload("video.mp4", mimetype="video/mp4", chunksize=-1, resumable=True)
req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

response = None
while response is None:
    status, response = req.next_chunk()
    if status:
        print(f"Upload progress: {int(status.progress() * 100)}%")

print(f"✅ Upload complete! Video ID: {response['id']}")
print(f"🔗 https://youtube.com/watch?v={response['id']}")

import os, json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

token_data = json.loads(os.environ['YOUTUBE_TOKEN'])
creds = Credentials(
    token=token_data['token'],
    refresh_token=token_data['refresh_token'],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=token_data['client_id'],
    client_secret=token_data['client_secret']
)

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
request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

response = None
while response is None:
    status, response = request.next_chunk()
    if status:
        print(f"Upload progress: {int(status.progress() * 100)}%")

print(f"✅ Upload complete! Video ID: {response['id']}")
print(f"🔗 https://youtube.com/watch?v={response['id']}")

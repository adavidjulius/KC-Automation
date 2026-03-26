import os
import json
import google.auth.transport.requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ── Auth ──────────────────────────────────────────────────────────────
creds = Credentials(
    token=os.environ['YOUTUBE_ACCESS_TOKEN'],
    refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ['YOUTUBE_CLIENT_ID'],
    client_secret=os.environ['YOUTUBE_CLIENT_SECRET']
)

# Auto refresh expired token
if creds.expired or not creds.valid:
    creds.refresh(google.auth.transport.requests.Request())
    print("🔄 Token refreshed successfully")

youtube = build('youtube', 'v3', credentials=creds)
print("✅ YouTube API client ready")

# ── Video Metadata ────────────────────────────────────────────────────
title       = os.environ.get('VIDEO_TITLE', 'Auto Reposted Short')
description = os.environ.get('VIDEO_DESC', 'Auto reposted via GitHub Actions 🤖 #Shorts')
privacy     = os.environ.get('PRIVACY', 'public')
next_id     = os.environ.get('NEXT_ID', '')

body = {
    "snippet": {
        "title": title,
        "description": description,
        "tags": ["shorts", "repost", "auto", "viral"],
        "categoryId": "22",
        "defaultLanguage": "en",
        "defaultAudioLanguage": "en"
    },
    "status": {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": False,
        "madeForKids": False
    }
}

# ── Upload ────────────────────────────────────────────────────────────
print(f"📤 Starting upload: {title}")
print(f"🔒 Privacy: {privacy}")

video_file = "video.mp4"

if not os.path.exists(video_file):
    print("❌ video.mp4 not found!")
    exit(1)

file_size = os.path.getsize(video_file)
print(f"📦 File size: {round(file_size / (1024 * 1024), 2)} MB")

media = MediaFileUpload(
    video_file,
    mimetype="video/mp4",
    chunksize=10 * 1024 * 1024,  # 10MB chunks
    resumable=True
)

req = youtube.videos().insert(
    part="snippet,status",
    body=body,
    media_body=media
)

# ── Upload Progress ───────────────────────────────────────────────────
response = None
while response is None:
    try:
        status, response = req.next_chunk()
        if status:
            percent = int(status.progress() * 100)
            print(f"⬆️  Upload progress: {percent}%")
    except Exception as e:
        print(f"⚠️  Chunk error (retrying): {e}")
        continue

# ── Success ───────────────────────────────────────────────────────────
video_id = response['id']
print(f"\n✅ Upload complete!")
print(f"🎬 Video ID  : {video_id}")
print(f"🔗 Short URL : https://youtube.com/shorts/{video_id}")
print(f"🔗 Watch URL : https://youtube.com/watch?v={video_id}")

# ── Save to posted.json ───────────────────────────────────────────────
posted_file = 'posted.json'

if os.path.exists(posted_file):
    with open(posted_file, 'r') as f:
        posted = json.load(f)
else:
    posted = []

if next_id and next_id not in posted:
    posted.append(next_id)
    with open(posted_file, 'w') as f:
        json.dump(posted, f, indent=2)
    print(f"\n📝 Saved {next_id} to posted.json")
else:
    print(f"\n⚠️  NEXT_ID not set or already in posted.json, skipping save")

print("\n🎉 All done!")

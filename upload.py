import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ── Auth — refresh_token only, no access_token needed ─────────────────
creds = Credentials(
    token=None,
    refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ['YOUTUBE_CLIENT_ID'],
    client_secret=os.environ['YOUTUBE_CLIENT_SECRET']
)

creds.refresh(Request())
print("✅ Auth ready — fresh token generated")

youtube = build('youtube', 'v3', credentials=creds)
print("✅ YouTube API ready")

# ── Metadata ──────────────────────────────────────────────────────────
title   = os.environ.get('VIDEO_TITLE', 'Auto Reposted Short')
desc    = os.environ.get('VIDEO_DESC',  'Auto reposted via GitHub Actions 🤖 #Shorts')
privacy = os.environ.get('PRIVACY',     'public')
next_id = os.environ.get('NEXT_ID',     '')

print(f"📝 Title   : {title}")
print(f"🔒 Privacy : {privacy}")

# ── Verify File ───────────────────────────────────────────────────────
video_file = "video.mp4"
if not os.path.exists(video_file):
    print("❌ video.mp4 not found!")
    exit(1)

size_mb = round(os.path.getsize(video_file) / (1024 * 1024), 2)
print(f"📦 File size: {size_mb} MB")

# ── Upload to YouTube ─────────────────────────────────────────────────
body = {
    "snippet": {
        "title": title,
        "description": desc,
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

media = MediaFileUpload(
    video_file,
    mimetype="video/mp4",
    chunksize=10 * 1024 * 1024,
    resumable=True
)

req = youtube.videos().insert(
    part="snippet,status",
    body=body,
    media_body=media
)

print("\n⬆️  Uploading to YouTube...")
response = None
while response is None:
    try:
        status, response = req.next_chunk()
        if status:
            print(f"   Progress: {int(status.progress() * 100)}%")
    except Exception as e:
        print(f"⚠️  Retrying chunk: {e}")
        continue

# ── Result ────────────────────────────────────────────────────────────
video_id = response['id']
print(f"\n✅ Upload complete!")
print(f"🎬 Video ID  : {video_id}")
print(f"🔗 Shorts URL: https://youtube.com/shorts/{video_id}")
print(f"🔗 Watch URL : https://youtube.com/watch?v={video_id}")

# ── Save to posted.json ───────────────────────────────────────────────
posted_file = 'posted.json'
posted = json.load(open(posted_file)) if os.path.exists(posted_file) else []

if next_id and next_id not in posted:
    posted.append(next_id)
    with open(posted_file, 'w') as f:
        json.dump(posted, f, indent=2)
    print(f"📝 Saved {next_id} to posted.json")

# ── Delete from Drive after confirmed upload ──────────────────────────
if next_id:
    try:
        drive = build('drive', 'v3', credentials=creds)
        drive.files().delete(fileId=next_id).execute()
        print(f"🗑️  Deleted from Drive: {next_id}")
        print(f"💾 Drive space freed!")
    except Exception as e:
        print(f"⚠️  Drive delete failed (file kept): {e}")

print("\n🎉 All done!")

import os
import json
import googleapiclient.http
from googleapiclient.discovery import build
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

drive = build('drive', 'v3', credentials=creds)

# ── List all videos in Drive folder ───────────────────────────────────
folder_id = os.environ['DRIVE_FOLDER_ID']
print(f"📂 Scanning Drive folder: {folder_id}")

results = drive.files().list(
    q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed=false",
    orderBy="createdTime",
    fields="files(id, name, createdTime, mimeType)",
    pageSize=100
).execute()

all_videos = results.get('files', [])
print(f"📦 Total videos in Drive: {len(all_videos)}")

if not all_videos:
    print("❌ No videos found in Drive folder!")
    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write("NO_VIDEOS=true\n")
    exit(0)

# ── Load already posted ───────────────────────────────────────────────
posted_file = 'posted.json'
posted = json.load(open(posted_file)) if os.path.exists(posted_file) else []
print(f"✅ Already posted: {len(posted)} videos")

# ── Pick next unposted video ──────────────────────────────────────────
next_video = None
for video in all_videos:
    if video['id'] not in posted:
        next_video = video
        break

if not next_video:
    print("🏁 All videos in Drive already posted!")
    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write("NO_VIDEOS=true\n")
    exit(0)

print(f"\n🎯 Next video to post:")
print(f"   Name : {next_video['name']}")
print(f"   ID   : {next_video['id']}")
print(f"   Date : {next_video['createdTime']}")

# ── Download video from Drive ─────────────────────────────────────────
print(f"\n⬇️  Downloading from Drive...")

with open('video.mp4', 'wb') as f:
    downloader = googleapiclient.http.MediaIoBaseDownload(
        f, drive.files().get_media(fileId=next_video['id'])
    )
    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"   Download: {int(status.progress() * 100)}%")

print("✅ Downloaded to video.mp4")

# ── Clean title ───────────────────────────────────────────────────────
title = os.path.splitext(next_video['name'])[0]

# Remove NA_ prefix if present
if title.upper().startswith('NA_'):
    title = title[3:]

# Replace underscores with spaces for cleaner title
title = title.replace('_', ' ').strip()

print(f"🏷️  Clean title: {title}")

# ── Write to GitHub ENV ───────────────────────────────────────────────
with open(os.environ['GITHUB_ENV'], 'a') as f:
    f.write(f"NEXT_ID={next_video['id']}\n")
    f.write(f"NEXT_TITLE={title}\n")
    f.write("NO_VIDEOS=false\n")

print(f"\n✅ Ready to upload: {title}")

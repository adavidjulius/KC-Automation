import os
import json
import isodate
import google.auth.transport.requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ── Auth ──────────────────────────────────────────────────────────────
creds = Credentials(
    token=os.environ['YOUTUBE_ACCESS_TOKEN'],
    refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ['YOUTUBE_CLIENT_ID'],
    client_secret=os.environ['YOUTUBE_CLIENT_SECRET']
)

if creds.expired or not creds.valid:
    creds.refresh(google.auth.transport.requests.Request())
    print("🔄 Token refreshed")

youtube = build('youtube', 'v3', credentials=creds)
channel_id = os.environ['SOURCE_CHANNEL_ID']

print(f"📡 Scanning channel: {channel_id}")

# ── Get Uploads Playlist ──────────────────────────────────────────────
channel_resp = youtube.channels().list(
    part="contentDetails",
    id=channel_id
).execute()

if not channel_resp['items']:
    print("❌ Channel not found. Check SOURCE_CHANNEL_ID secret.")
    exit(1)

uploads_playlist = channel_resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']
print(f"📋 Uploads playlist: {uploads_playlist}")

# ── Fetch All Videos ──────────────────────────────────────────────────
videos = []
next_page = None

while True:
    playlist_resp = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=uploads_playlist,
        maxResults=50,
        pageToken=next_page
    ).execute()

    for item in playlist_resp['items']:
        videos.append({
            'id': item['contentDetails']['videoId'],
            'title': item['snippet']['title'],
            'published_at': item['contentDetails']['videoPublishedAt'],
            'url': f"https://www.youtube.com/watch?v={item['contentDetails']['videoId']}"
        })

    next_page = playlist_resp.get('nextPageToken')
    if not next_page:
        break

print(f"📦 Total videos found: {len(videos)}")

# ── Filter Shorts (≤ 60 seconds) ──────────────────────────────────────
shorts = []
video_ids = [v['id'] for v in videos]

for i in range(0, len(video_ids), 50):
    batch = video_ids[i:i+50]
    details = youtube.videos().list(
        part="contentDetails",
        id=','.join(batch)
    ).execute()

    duration_map = {
        item['id']: isodate.parse_duration(
            item['contentDetails']['duration']
        ).total_seconds()
        for item in details['items']
    }

    for v in videos:
        if v['id'] in duration_map and duration_map[v['id']] <= 60:
            v['duration'] = duration_map[v['id']]
            shorts.append(v)

print(f"🎬 Shorts found: {len(shorts)}")

# ── Sort Oldest to Newest ─────────────────────────────────────────────
shorts.sort(key=lambda x: x['published_at'])

# ── Load Already Posted ───────────────────────────────────────────────
posted_file = 'posted.json'
if os.path.exists(posted_file):
    with open(posted_file) as f:
        posted = json.load(f)
else:
    posted = []

print(f"✅ Already posted: {len(posted)} Shorts")

# ── Pick Next Unposted Short ──────────────────────────────────────────
next_short = None
for short in shorts:
    if short['id'] not in posted:
        next_short = short
        break

# ── Write to GitHub ENV ───────────────────────────────────────────────
github_env = os.environ['GITHUB_ENV']

if next_short:
    print(f"\n🎯 Next Short to post:")
    print(f"   Title : {next_short['title']}")
    print(f"   URL   : {next_short['url']}")
    print(f"   Date  : {next_short['published_at']}")

    with open(github_env, 'a') as f:
        f.write(f"NEXT_URL={next_short['url']}\n")
        f.write(f"NEXT_TITLE={next_short['title']}\n")
        f.write(f"NEXT_ID={next_short['id']}\n")
        f.write("NO_SHORTS=false\n")
else:
    print("🏁 All Shorts have been reposted. Nothing left!")
    with open(github_env, 'a') as f:
        f.write("NO_SHORTS=true\n")

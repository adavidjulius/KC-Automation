import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import google.auth.transport.requests
import json

creds = Credentials(
    token=os.environ['YOUTUBE_ACCESS_TOKEN'],
    refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ['YOUTUBE_CLIENT_ID'],
    client_secret=os.environ['YOUTUBE_CLIENT_SECRET']
)

if creds.expired:
    creds.refresh(google.auth.transport.requests.Request())

youtube = build('youtube', 'v3', credentials=creds)

# Get all videos from source channel
def get_all_shorts(channel_id):
    # First get the uploads playlist ID
    channel_resp = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    ).execute()

    uploads_playlist = channel_resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    videos = []
    next_page = None

    # Paginate through ALL videos
    while True:
        playlist_resp = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist,
            maxResults=50,
            pageToken=next_page
        ).execute()

        for item in playlist_resp['items']:
            video_id = item['contentDetails']['videoId']
            title = item['snippet']['title']
            published_at = item['contentDetails']['videoPublishedAt']
            videos.append({
                'id': video_id,
                'title': title,
                'published_at': published_at,
                'url': f'https://www.youtube.com/watch?v={video_id}'
            })

        next_page = playlist_resp.get('nextPageToken')
        if not next_page:
            break

    # Filter only Shorts (duration <= 60 seconds)
    video_ids = [v['id'] for v in videos]
    shorts = []

    # Check duration in batches of 50
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        details_resp = youtube.videos().list(
            part="contentDetails",
            id=','.join(batch)
        ).execute()

        duration_map = {}
        for item in details_resp['items']:
            import isodate
            duration = isodate.parse_duration(item['contentDetails']['duration'])
            duration_map[item['id']] = duration.total_seconds()

        for v in videos:
            if v['id'] in duration_map and duration_map[v['id']] <= 60:
                v['duration'] = duration_map[v['id']]
                shorts.append(v)

    # Sort oldest to newest
    shorts.sort(key=lambda x: x['published_at'])

    return shorts


channel_id = os.environ['SOURCE_CHANNEL_ID']
shorts = get_all_shorts(channel_id)

# Load already posted videos to avoid duplicates
posted_file = 'posted.json'
if os.path.exists(posted_file):
    with open(posted_file) as f:
        posted = json.load(f)
else:
    posted = []

# Pick only next unposted short
next_short = None
for short in shorts:
    if short['id'] not in posted:
        next_short = short
        break

if next_short:
    print(f"NEXT_URL={next_short['url']}")
    print(f"NEXT_TITLE={next_short['title']}")
    print(f"NEXT_ID={next_short['id']}")
    # Write to GitHub env for next steps
    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write(f"NEXT_URL={next_short['url']}\n")
        f.write(f"NEXT_TITLE={next_short['title']}\n")
        f.write(f"NEXT_ID={next_short['id']}\n")
else:
    print("NO_SHORTS=true")
    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write("NO_SHORTS=true\n")

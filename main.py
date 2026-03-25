import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ========================
# ENV VARIABLES
# ========================
API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = os.getenv("SOURCE_CHANNEL_ID")

CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN")

UPLOADED_FILE = "uploaded.txt"


# ========================
# TOKEN HANDLING
# ========================
def get_access_token():
    url = "https://oauth2.googleapis.com/token"

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }

    res = requests.post(url, data=data).json()

    if "access_token" not in res:
        raise Exception(f"Token Error: {res}")

    return res["access_token"]


def get_credentials():
    access_token = get_access_token()

    creds = Credentials(
        token=access_token,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    return creds


# ========================
# TRACK UPLOADED VIDEOS
# ========================
def get_uploaded_videos():
    if not os.path.exists(UPLOADED_FILE):
        return set()
    with open(UPLOADED_FILE, "r") as f:
        return set(f.read().splitlines())


def save_uploaded(video_id):
    with open(UPLOADED_FILE, "a") as f:
        f.write(video_id + "\n")


# ========================
# FETCH VIDEOS
# ========================
def get_latest_videos():
    youtube = build("youtube", "v3", developerKey=API_KEY)

    res = youtube.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        maxResults=10,
        order="date",
        type="video"
    ).execute()

    return res["items"]


def pick_new_video(videos, uploaded):
    for item in videos:
        vid = item["id"]["videoId"]
        title = item["snippet"]["title"]

        if vid not in uploaded:
            return vid, title

    return None, None


# ========================
# DOWNLOAD VIDEO
# ========================
def download_video(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"

    cmd = [
        "yt-dlp",
        "-f", "mp4",
        "-o", "video.mp4",
        url
    ]

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise Exception("Download failed")


# ========================
# UPLOAD VIDEO
# ========================
def upload_video(title):
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"{title} (Fan Upload)",
                "description": "Credits to original creator. This is a fan-based promotion.",
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public"
            }
        },
        media_body=MediaFileUpload("video.mp4", resumable=True)
    )

    response = request.execute()

    print("Uploaded Video ID:", response["id"])
    return True


# ========================
# MAIN FLOW
# ========================
def main():
    print("Starting pipeline...")

    uploaded = get_uploaded_videos()
    videos = get_latest_videos()

    video_id, title = pick_new_video(videos, uploaded)

    if not video_id:
        print("No new video found.")
        return

    print(f"Selected video: {video_id}")

    download_video(video_id)

    success = upload_video(title)

    if success:
        save_uploaded(video_id)
        print("Done and saved.")

    # cleanup
    if os.path.exists("video.mp4"):
        os.remove("video.mp4")


if __name__ == "__main__":
    main()

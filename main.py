import os
import subprocess
import json
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ========================
# ENV (YOUR NAMES ONLY)
# ========================
CHANNEL_ID = os.getenv("SOURCE_CHANNEL_ID")

CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN")

UPLOADED_FILE = "uploaded.txt"

# ========================
# VALIDATION
# ========================
required = {
    "SOURCE_CHANNEL_ID": CHANNEL_ID,
    "YOUTUBE_CLIENT_ID": CLIENT_ID,
    "YOUTUBE_CLIENT_SECRET": CLIENT_SECRET,
    "YOUTUBE_REFRESH_TOKEN": REFRESH_TOKEN,
}

for k, v in required.items():
    if not v:
        raise Exception(f"Missing ENV: {k}")

print("ENV OK ✅")

# ========================
# TOKEN
# ========================
def get_access_token():
    res = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
            "grant_type": "refresh_token",
        }
    ).json()

    if "access_token" not in res:
        raise Exception(f"Token error: {res}")

    return res["access_token"]


def get_credentials():
    return Credentials(
        token=get_access_token(),
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )

# ========================
# TRACK UPLOADED
# ========================
def get_uploaded():
    if not os.path.exists(UPLOADED_FILE):
        return set()
    return set(open(UPLOADED_FILE).read().splitlines())


def save_uploaded(vid):
    with open(UPLOADED_FILE, "a") as f:
        f.write(vid + "\n")

# ========================
# FETCH LATEST VIDEO (NO API KEY)
# ========================
def get_latest_video():
    url = f"https://www.youtube.com/channel/{CHANNEL_ID}/videos"

    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--playlist-items", "1", url],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception("Failed to fetch video")

    data = json.loads(result.stdout.splitlines()[0])

    return data["id"], data["title"]

# ========================
# DOWNLOAD
# ========================
def download(video_id):
    subprocess.run([
        "yt-dlp",
        "-f", "mp4",
        "-o", "video.mp4",
        f"https://www.youtube.com/watch?v={video_id}"
    ], check=True)

# ========================
# UPLOAD
# ========================
def upload(title):
    creds = get_credentials()

    youtube = build("youtube", "v3", credentials=creds)

    req = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title + " (Fan Upload)",
                "description": "Credits to original creator",
                "categoryId": "22"
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload("video.mp4", resumable=True)
    )

    res = req.execute()
    print("Uploaded:", res["id"])
    return True

# ========================
# MAIN
# ========================
def main():
    print("Starting...")

    uploaded = get_uploaded()

    vid, title = get_latest_video()

    if vid in uploaded:
        print("Already uploaded")
        return

    print("Processing:", vid)

    download(vid)

    if upload(title):
        save_uploaded(vid)

    if os.path.exists("video.mp4"):
        os.remove("video.mp4")

if __name__ == "__main__":
    main()

import os
import subprocess
from googleapiclient.discovery import build

API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "TARGET_CHANNEL_ID"

UPLOADED_FILE = "uploaded.txt"

def get_uploaded_videos():
    if not os.path.exists(UPLOADED_FILE):
        return set()
    with open(UPLOADED_FILE, "r") as f:
        return set(f.read().splitlines())

def save_uploaded(video_id):
    with open(UPLOADED_FILE, "a") as f:
        f.write(video_id + "\n")

def get_latest_video():
    youtube = build("youtube", "v3", developerKey=API_KEY)

    res = youtube.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        maxResults=5,
        order="date"
    ).execute()

    return res["items"]

def pick_new_video(videos, uploaded):
    for item in videos:
        vid = item["id"]["videoId"]
        if vid not in uploaded:
            return vid, item["snippet"]["title"]
    return None, None

def download_video(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    subprocess.run([
        "yt-dlp",
        "-f", "mp4",
        "-o", "video.mp4",
        url
    ])

def upload_video(title):
    # 🚨 Placeholder: replace with OAuth upload logic
    print(f"Uploading video: {title}")
    return True

def main():
    uploaded = get_uploaded_videos()

    videos = get_latest_video()
    video_id, title = pick_new_video(videos, uploaded)

    if not video_id:
        print("No new videos found.")
        return

    print(f"Downloading: {video_id}")
    download_video(video_id)

    success = upload_video(title)

    if success:
        save_uploaded(video_id)
        print("Upload complete and saved.")

if __name__ == "__main__":
    main()

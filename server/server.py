from flask import Flask, request, jsonify
import subprocess
import os
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

app = Flask(__name__)

# 🔐 PUT YOUR REAL VALUES HERE
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REFRESH_TOKEN = "YOUR_REFRESH_TOKEN"

API_KEY = "mysecret123"  # protect API

# ================= TOKEN =================
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
        raise Exception(res)

    return res["access_token"]

def get_credentials():
    return Credentials(
        token=get_access_token(),
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )

# ================= UPLOAD =================
def upload_video(title):
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": "Auto uploaded",
                "categoryId": "22"
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload("video.mp4")
    )

    return request.execute()

# ================= API =================
@app.route("/process", methods=["POST"])
def process():
    if request.headers.get("x-api-key") != API_KEY:
        return {"error": "unauthorized"}, 403

    data = request.json
    video_id = data["video_id"]
    title = data["title"]

    url = f"https://www.youtube.com/watch?v={video_id}"

    print("Downloading:", url)

    subprocess.run([
        "yt-dlp",
        "-f", "best",
        "-o", "video.mp4",
        url
    ], check=True)

    print("Uploading...")

    res = upload_video(title)

    if os.path.exists("video.mp4"):
        os.remove("video.mp4")

    return jsonify({"status": "done", "video_id": res["id"]})

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

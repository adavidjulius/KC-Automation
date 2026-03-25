import os
import subprocess
import json
import requests

CHANNEL_ID = os.getenv("SOURCE_CHANNEL_ID")

VPS_URL = "http://YOUR_VPS_IP:5000/process"
API_KEY = "mysecret123"

UPLOADED_FILE = "uploaded.txt"

# ================= TRACK =================
def get_uploaded():
    if not os.path.exists(UPLOADED_FILE):
        return set()
    return set(open(UPLOADED_FILE).read().splitlines())

def save_uploaded(vid):
    with open(UPLOADED_FILE, "a") as f:
        f.write(vid + "\n")

# ================= FETCH =================
def get_latest_video():
    playlist_id = "UU" + CHANNEL_ID[2:]
    url = f"https://www.youtube.com/playlist?list={playlist_id}"

    result = subprocess.run(
        ["yt-dlp", "--flat-playlist", "-J", url],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)
    latest = data["entries"][0]

    return latest["id"], latest["title"]

# ================= SEND =================
def send_to_vps(video_id, title):
    res = requests.post(
        VPS_URL,
        json={"video_id": video_id, "title": title},
        headers={"x-api-key": API_KEY}
    )

    print(res.json())

# ================= MAIN =================
def main():
    uploaded = get_uploaded()

    vid, title = get_latest_video()

    if vid in uploaded:
        print("Already uploaded")
        return

    print("Sending to VPS:", vid)

    send_to_vps(vid, title)
    save_uploaded(vid)

if __name__ == "__main__":
    main()

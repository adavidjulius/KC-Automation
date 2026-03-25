#!/usr/bin/env python3
"""
repost_short.py
--------------
1. Reads the channel's Shorts playlist (oldest → newest)
2. Picks up from where it left off (tracked in progress.json)
3. Downloads the next unposted Short via yt-dlp (video + subtitles)
4. Uploads it to YOUR YouTube channel with original metadata + captions
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

import yt_dlp
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ─── CONFIG ────────────────────────────────────────────────────────────────────
SOURCE_CHANNEL_ID   = os.environ["SOURCE_CHANNEL_ID"]   # e.g. UCxxxxxxxxxxxxxx
PROGRESS_FILE       = Path("progress.json")
CREDENTIALS_FILE    = Path("credentials.json")           # OAuth2 client secret
TOKEN_FILE          = Path("token.json")                 # saved access token
DOWNLOAD_DIR        = Path("downloads")
# cookies.txt is written to the repo root by the workflow
# Path resolves relative to where the script is called from (repo root)
COOKIES_FILE        = Path(os.environ.get("COOKIES_FILE", "cookies.txt"))
SCOPES              = ["https://www.googleapis.com/auth/youtube.upload",
                       "https://www.googleapis.com/auth/youtube"]
# ───────────────────────────────────────────────────────────────────────────────


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"posted_ids": [], "last_run": None}


def save_progress(data: dict):
    PROGRESS_FILE.write_text(json.dumps(data, indent=2))


def get_youtube_client():
    """
    Authenticate using individual credential pieces from GitHub Secrets:
      YOUTUBE_ACCESS_TOKEN   — current access token
      YOUTUBE_REFRESH_TOKEN  — refresh token (used to auto-renew)
      YOUTUBE_CLIENT_ID      — OAuth2 client ID
      YOUTUBE_CLIENT_SECRET  — OAuth2 client secret
    """
    access_token   = os.environ.get("YOUTUBE_ACCESS_TOKEN", "")
    refresh_token  = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
    client_id      = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret  = os.environ.get("YOUTUBE_CLIENT_SECRET", "")

    if not refresh_token or not client_id or not client_secret:
        raise EnvironmentError(
            "Missing one or more required secrets:\n"
            "  YOUTUBE_REFRESH_TOKEN\n"
            "  YOUTUBE_CLIENT_ID\n"
            "  YOUTUBE_CLIENT_SECRET"
        )

    # Build credentials from the raw values
    creds = Credentials(
        token         = access_token or None,
        refresh_token = refresh_token,
        token_uri     = "https://oauth2.googleapis.com/token",
        client_id     = client_id,
        client_secret = client_secret,
        scopes        = SCOPES,
    )

    # Auto-refresh if expired (happens every hour — refresh_token keeps it alive forever)
    if not creds.valid:
        print("  🔄 Access token expired — refreshing automatically…")
        creds.refresh(Request())
        print("  ✅ Token refreshed.")

    return build("youtube", "v3", credentials=creds)


def fetch_all_shorts(channel_id: str) -> list[dict]:
    """
    Use yt-dlp to list ALL Shorts from the channel, sorted oldest → newest.
    Returns list of dicts with id, title, upload_date.
    """
    shorts_url = f"https://www.youtube.com/@{channel_id}/shorts"
    # Try both URL formats
    urls_to_try = [
        f"https://www.youtube.com/@{channel_id}/shorts",
        f"https://www.youtube.com/channel/{channel_id}/shorts",
    ]

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "playlistend": 9999,
        "ignoreerrors": True,
        **({"cookiefile": str(COOKIES_FILE)} if COOKIES_FILE.exists() else {}),
    }

    entries = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for url in urls_to_try:
            try:
                info = ydl.extract_info(url, download=False)
                if info and info.get("entries"):
                    entries = [
                        {
                            "id": e["id"],
                            "title": e.get("title", ""),
                            "upload_date": e.get("upload_date", "19000101"),
                            "url": f"https://www.youtube.com/watch?v={e['id']}",
                        }
                        for e in info["entries"]
                        if e and e.get("id")
                    ]
                    break
            except Exception as ex:
                print(f"  Warning: {url} → {ex}")

    # Sort oldest first (upload_date = YYYYMMDD string)
    entries.sort(key=lambda x: x["upload_date"])
    return entries


def download_short(video: dict) -> dict:
    """Download video + subtitles. Returns paths dict."""
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    video_id = video["id"]
    out_tmpl  = str(DOWNLOAD_DIR / f"{video_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": out_tmpl,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-US"],
        "subtitlesformat": "srt",
        "writethumbnail": False,
        "writedescription": True,
        "writeannotations": False,
        "quiet": False,
        "merge_output_format": "mp4",
        **({"cookiefile": str(COOKIES_FILE)} if COOKIES_FILE.exists() else {}),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video["url"], download=True)

    # Find downloaded files
    files = list(DOWNLOAD_DIR.glob(f"{video_id}*"))
    video_file = next((f for f in files if f.suffix == ".mp4"), None)
    srt_file   = next((f for f in files if f.suffix == ".srt"), None)
    desc_file  = next((f for f in files if f.suffix == ".description"), None)

    description = info.get("description", "") or ""
    if not description and desc_file and desc_file.exists():
        description = desc_file.read_text(encoding="utf-8")

    return {
        "video_path": video_file,
        "srt_path":   srt_file,
        "title":       info.get("title", video["title"]),
        "description": description,
        "tags":        info.get("tags", []),
        "category_id": str(info.get("categories", ["22"])[0] if info.get("categories") else "22"),
        "original_id": video_id,
    }


def upload_to_youtube(youtube, meta: dict) -> str:
    """Upload video to YOUR channel. Returns new video ID."""
    body = {
        "snippet": {
            "title":       meta["title"][:100],   # YouTube max title length
            "description": meta["description"][:5000],
            "tags":        meta["tags"][:500],
            "categoryId":  "22",                  # People & Blogs default
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(meta["video_path"]),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5,  # 5 MB chunks
    )

    print(f"  ⬆  Uploading: {meta['title']}")
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"     Upload progress: {pct}%", end="\r")

    new_video_id = response["id"]
    print(f"\n  ✅ Uploaded → https://youtube.com/watch?v={new_video_id}")
    return new_video_id


def upload_captions(youtube, video_id: str, srt_path: Path):
    """Upload SRT captions to the newly uploaded video."""
    if not srt_path or not srt_path.exists():
        print("  ⚠  No captions file found, skipping caption upload.")
        return

    print(f"  📝 Uploading captions from {srt_path.name}…")
    media = MediaFileUpload(str(srt_path), mimetype="application/octet-stream", resumable=False)
    youtube.captions().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId":  video_id,
                "language": "en",
                "name":     "English",
                "isDraft":  False,
            }
        },
        media_body=media,
    ).execute()
    print("  ✅ Captions uploaded.")


def cleanup(video_id: str):
    """Remove downloaded files to keep the repo clean."""
    for f in DOWNLOAD_DIR.glob(f"{video_id}*"):
        f.unlink(missing_ok=True)


# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f"  YouTube Shorts Auto-Reposter  |  {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'='*60}\n")

    progress = load_progress()
    posted   = set(progress["posted_ids"])

    print(f"📋 Fetching Shorts list from channel: {SOURCE_CHANNEL_ID}")
    all_shorts = fetch_all_shorts(SOURCE_CHANNEL_ID)
    print(f"   Found {len(all_shorts)} Shorts total.\n")

    if not all_shorts:
        print("❌ No Shorts found. Check SOURCE_CHANNEL_ID.")
        sys.exit(1)

    # Find the next unposted Short
    next_video = None
    for video in all_shorts:   # already sorted oldest → newest
        if video["id"] not in posted:
            next_video = video
            break

    if not next_video:
        print("🎉 All Shorts have been reposted! Nothing left to do.")
        sys.exit(0)

    print(f"▶  Next Short to post:")
    print(f"   Title : {next_video['title']}")
    print(f"   Date  : {next_video['upload_date']}")
    print(f"   URL   : {next_video['url']}\n")

    # Download
    print("⬇  Downloading video + captions…")
    meta = download_short(next_video)

    if not meta["video_path"] or not meta["video_path"].exists():
        print("❌ Download failed — no video file found.")
        sys.exit(1)

    # Authenticate & upload
    youtube     = get_youtube_client()
    new_vid_id  = upload_to_youtube(youtube, meta)
    upload_captions(youtube, new_vid_id, meta["srt_path"])

    # Save progress
    progress["posted_ids"].append(next_video["id"])
    progress["last_run"] = datetime.now().isoformat()
    progress["last_posted"] = {
        "original_id": next_video["id"],
        "new_id":      new_vid_id,
        "title":       meta["title"],
        "date":        datetime.now().isoformat(),
    }
    save_progress(progress)
    print(f"\n💾 Progress saved ({len(progress['posted_ids'])} posted so far).")

    # Cleanup downloads
    cleanup(next_video["id"])
    print("🧹 Cleaned up download files.")
    print("\n✅ Done!\n")


if __name__ == "__main__":
    main()

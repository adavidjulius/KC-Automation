# 📹 YouTube Shorts Auto-Reposter

Automatically reposts YouTube Shorts from a source channel to your own YouTube channel — **one Short per day**, starting from the oldest (2019) and working forward chronologically. Preserves the original title, description, tags, and captions.

---

## 📁 Repository Structure

```
.
├── .github/
│   └── workflows/
│       └── repost_shorts.yml   ← GitHub Actions (runs daily)
├── scripts/
│   ├── repost_short.py         ← Main download + upload script
│   └── generate_token.py       ← One-time local auth helper
├── progress.json               ← Auto-created; tracks what's been posted
└── README.md
```

---

## 🚀 Setup (One-Time)

### Step 1 — Enable the YouTube Data API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Go to **APIs & Services → Library**
4. Search for **YouTube Data API v3** → Enable it
5. Go to **APIs & Services → Credentials**
6. Click **Create Credentials → OAuth 2.0 Client ID**
7. Application type: **Desktop app**
8. Download the JSON file and rename it `credentials.json`

---

### Step 2 — Generate Your OAuth Token (Local)

Run this **once** on your own computer (not in GitHub Actions):

```bash
pip install google-auth-oauthlib google-api-python-client
python scripts/generate_token.py
```

- A browser window will open → log in with the **YouTube account you want to post TO**
- After authorization, `token.json` will be created
- The script will print the token contents — **copy this**

---

### Step 3 — Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|---|---|
| `SOURCE_CHANNEL_ID` | Channel ID or handle of the source channel (e.g. `UCxxxxxx` or `@channelname`) |
| `YOUTUBE_TOKEN_JSON` | The full contents of `token.json` from Step 2 |
| `YOUTUBE_CLIENT_SECRET_JSON` | The full contents of `credentials.json` from Step 1 |

---

### Step 4 — Create `progress.json`

Create an empty progress file and commit it to your repo:

```bash
echo '{"posted_ids": [], "last_run": null}' > progress.json
git add progress.json
git commit -m "init: add progress tracker"
git push
```

---

## ⚙️ How It Works

1. **Daily at 10:00 AM UTC**, the GitHub Action runs
2. It fetches the full Shorts list from the source channel
3. It compares against `progress.json` to find the **oldest unposted Short**
4. Downloads the video (MP4) + captions (SRT) via `yt-dlp`
5. Uploads video + captions to YOUR YouTube channel via the YouTube Data API
6. Updates `progress.json` and pushes it back to the repo

---

## 🧪 Testing Without Uploading

Use the manual **dry run** trigger:

1. Go to your repo → **Actions → Daily YouTube Shorts Reposter**
2. Click **Run workflow**
3. Set **dry_run** = `true`
4. This will show you what the next Short to be posted is, without actually uploading

---

## ⏰ Changing the Schedule

Edit `.github/workflows/repost_shorts.yml`:

```yaml
schedule:
  - cron: "0 10 * * *"   # 10:00 AM UTC daily
```

Cron format: `minute hour day month weekday`  
Use [crontab.guru](https://crontab.guru) to generate your preferred time.

---

## ⚠️ Important Notes

- **Only repost videos where the original creator allows it** — always get permission first
- YouTube has an **upload quota** (10,000 units/day). Each upload costs ~1,600 units, so you can safely post ~6/day. One per day is well within limits.
- If the workflow fails mid-way (e.g. upload succeeded but captions failed), simply re-run — it will not re-upload the same video since it's tracked in `progress.json`
- Token expires after some time — re-run `generate_token.py` locally and update the `YOUTUBE_TOKEN_JSON` secret if uploads start failing with auth errors

---

## 🔧 Dependencies

```
yt-dlp
google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
```

All installed automatically by the GitHub Action.

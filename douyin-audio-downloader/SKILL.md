---
name: douyin-audio-downloader
description: Extract and download audio from an open or accessible Douyin video page, saving the result as a local .m4a file. Use when the user provides a douyin.com/video URL and asks to download Douyin audio, extract only the sound, or save the audio track, assuming Chrome DevTools remote debugging is available.
---

# Douyin Audio Downloader

Download audio from a Douyin video page. The workflow connects to the existing browser session at `http://localhost:9222`, captures the player audio request, reuses the real request headers, and downloads the audio with HTTP Range chunks.

## Usage

```powershell
python C:\Users\MECHREV\.agents\skills\douyin-audio-downloader\scripts\get_douyin_audio.py "https://www.douyin.com/video/7626360252560117034"
```

Common options:

```powershell
# Choose output directory
python C:\Users\MECHREV\.agents\skills\douyin-audio-downloader\scripts\get_douyin_audio.py "<douyin-url>" --output-dir downloads

# Use a non-default CDP port
python C:\Users\MECHREV\.agents\skills\douyin-audio-downloader\scripts\get_douyin_audio.py "<douyin-url>" --port 9222

# Do not reload the page; usually less reliable
python C:\Users\MECHREV\.agents\skills\douyin-audio-downloader\scripts\get_douyin_audio.py "<douyin-url>" --no-reload
```

## Workflow

- Ensure the Douyin video is reachable in the current browser session.
- Ensure the browser was started with `--remote-debugging-port=9222`.
- Run `scripts/get_douyin_audio.py <url>`.
- The script reuses an already-open matching tab when possible; otherwise it opens a new tab.
- By default it reloads or opens the page so it can capture the actual player request for `media-audio` or `mp4a`.
- Do not bare `curl` the media URL. Douyin media URLs often require the same `Range`, `Origin`, `Referer`, `User-Agent`, and `sec-*` request context used by the player; bare downloads commonly return 403.
- After download, the script runs `ffprobe` to verify the audio track when `ffprobe` is available. If `ffprobe` is missing, the downloaded file is still kept.

## Output

- Default output directory: `downloads/` under the current working directory.
- The filename comes from the page title with Windows-invalid characters removed.
- This skill currently supports audio download only; it does not download video.

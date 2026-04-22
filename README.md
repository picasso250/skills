# skills

Reusable Codex skills for browser automation, page extraction, screenshots, note workflows, audio/video pipelines, publishing flows, and Windows local tooling.

## Install

Clone once:

```bash
git clone --depth 1 https://github.com/picasso250/skills.git ~/tmp/picasso-skills
```

Copy one skill into your local skills directory:

```bash
cp -r ~/tmp/picasso-skills/website-to-cli ~/.agents/skills/
```

Replace `~/.agents/skills/` with your actual skills directory if different.
The examples above use bash-style paths and commands; adjust them if you are installing from PowerShell or another shell.

After copying, check whether the installed skill directory contains a `README.md`. If it does, follow that README to finish installation.

## Update

Refresh the local clone:

```bash
cd ~/tmp/picasso-skills
git pull
```

Then replace the installed skill with the updated one.

## Skills

Current installable skills in this repo:

- `ai-speak`: real-time AI voice playback and self-talk mode; not for exporting wav, srt, or video assets.
- `audio-to-srt`: generate acoustically aligned `srt/json` subtitle timelines from `wav/mp3` audio.
- `bilibili-downloader`: extract audio/video streams from an already-open Bilibili page and optionally save local `m4a` or muxed `mp4`.
- `bilibili-video-maker`: generate a Bilibili-ready video pipeline from a topic, including script, AI voice, and animated subtitles.
- `continue-on-phone`: continue the current agent conversation on a phone by using the local QR flow.
- `desktop-screenshot`: capture the current Windows desktop to a PNG file.
- `douyin-manage`: extract first-screen work list data from the Douyin creator content management page.
- `gemini-img-gen`: generate high-resolution images with Gemini image generation.
- `handover`: compress the current task state into exactly five sentences and write `handover.md`.
- `materialist-dialectics`: run a fact-grounded thesis-antithesis-synthesis conversation when the user explicitly asks for that mode.
- `notes-workflow`: write notes into the local Markdown notes repository under `$HOME\Documents\notes`.
- `ollama-ocr`: run local OCR with Ollama multimodal models to extract text, tables, or document structure.
- `screenshot-webpage`: capture screenshots of web pages or local HTML files, preferably through an existing remote-debug browser session.
- `send-email`: send email to the user.
- `shared-page-md`: reuse the current browser session and convert a page DOM into Markdown.
- `text-to-wavs`: generate `wav` audio plus `srt/json` subtitle timelines from text.
- `v2ex`: read a V2EX topic and export a Markdown snapshot with metadata, body, and replies.
- `website-to-cli`: turn a repeatable browser workflow into a deterministic CLI flow by pairing Chrome DevTools with Playwright.
- `wechat-mp-publish`: automate WeChat Official Accounts publishing through a staged browser workflow.
- `windows-uac`: handle Windows tasks that require elevation, preferring direct `Start-Process -Verb RunAs` when admin rights are clearly needed.

## Notes

- The list above intentionally tracks installable skill directories that contain a `SKILL.md`.
- `website/` contains site assets, not an installable skill.
- `browser/` is helper/runtime material rather than a standalone installable skill directory.
- `message-search/` currently has no installable skill manifest and is not listed above.
- Some skills include their own `README.md` or extra setup notes. After copying a skill, read that skill's local documentation before use.

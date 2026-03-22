# skills

Reusable Codex skills for browser automation, page extraction, screenshots, local file search, email workflows, env editing, and Feishu/Douyin automation.

## Install

Clone once:

```bash
git clone --depth 1 https://github.com/picasso250/skills.git ~/tmp/picasso-skills
```

Copy one skill into your local skills directory:

```bash
cp -r ~/tmp/picasso-skills/browser-flow-to-cli ~/.agents/skills/
```

Replace `~/.agents/skills/` with your actual skills directory if different.

After copying, check whether the installed skill directory contains a `README.md`. If it does, follow that README to finish installation.

## Update

Refresh the local clone:

```bash
cd ~/tmp/picasso-skills
git pull
```

Then replace the installed skill with the updated one.

## Skills

Current skill directories in this repo:

- `browser`: browser control for interactive web tasks via remote debugging / Playwright.
- `browser-flow-to-cli`: turn repeatable browser or website workflows into CLI automation scripts.
- `douyin-publish-video`: 将本地视频发布到抖音创作者中心的浏览器自动化技能。
- `edit-env-with-tk`: update a `.env` file by collecting secret values in local Tk dialogs instead of chat.
- `everything-file-search`: fast local file search through the Everything HTTP service.
- `feishu-bitable`: use Feishu Open Platform APIs to list tables/fields/records and update Bitable records.
- `find-previous-email`: find earlier emails and matching replies to recover message context.
- `screenshot-webpage`: capture screenshots of web pages or local HTML files.
- `send-email`: send email with Markdown body and optional attachments.
- `shared-page-md`: reuse the current browser session and convert a page DOM into Markdown.

## Notes

- `website/` is part of the repo's site assets, not an installable skill directory.
- Some skills include their own `README.md` or extra setup notes. After copying a skill, read that skill's local documentation before use.

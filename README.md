# skills

Reusable skills for browser automation, file search, screenshots, page extraction, email sending, and Douyin publishing.

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

## Update

Refresh the local clone:

```bash
cd ~/tmp/picasso-skills
git pull
```

Then replace the installed skill with the updated one.

## Skills

- `browser`: browser control for interactive web tasks.
- `browser-flow-to-cli`: turn repeatable browser workflows into CLI scripts.
- `douyin-publish-video`: publish local videos to Douyin creator tools.
- `everything-file-search`: fast local file search with Everything.
- `screenshot-webpage`: capture screenshots of web pages or local HTML.
- `send-email`: send email from the agent.
- `shared-page-md`: read a web page and extract it as Markdown.

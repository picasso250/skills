---
name: screenshot-webpage
description: Capture screenshots of web pages or local HTML files. 当你做网站需要提升UI的时候，这个技能很有用。这个技能也会默认优先使用connect_over_cdp (Chrome DevTools Protocol) 连接到已经开启 --remote-debugging-port 的浏览器实例，而你的主公恰巧常开这个功能，那么这个技能就能直接利用主公的浏览器来截图，当你和主公需要信息同步的时候（你需要看到他现在到底在浏览器上看到了什么），这个技能就能派上用场了。
---

# Screenshot Skill

This skill allows you to capture screenshots of a local HTML file or a remote URL using Playwright. It supports custom viewports, scroll positions, and wait times.

## Usage

Run the script from the `.agents/skills/screenshot-webpage/` directory:

```bash
python screenshot.py --url <url> --out-file <xx.png> [options]
```
OR
```bash
python screenshot.py --file <html_file> --out-file <xx.png> [options]
```

### Parameters

- `--file <html_file>`: (Mutually exclusive with `--url`) Path to a local HTML file.
- `--url <url>`: (Mutually exclusive with `--file`) URL to visit.
- `--timeout <seconds>`: Wait time in seconds after the page loads (default: 3.0). Useful for animations or slow network resources.
- `--viewport <WxH>`: Viewport size in pixels (default: 380x420).
- `--scroll-x <n>`: Horizontal scroll position in pixels (default: 0).
- `--scroll-y <n>`: Vertical scroll position in pixels (default: 0).
- `--out-file <path>`: Path where the screenshot will be saved (required).

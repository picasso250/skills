---
name: url2md
description: 将网页内容转换为 Markdown 文件的技能。
---

# url2md Skill

This skill allows you to convert the content of a web page into a Markdown file. It uses Playwright to render the page (including dynamic content) and BeautifulSoup to parse the HTML and convert it to Markdown.

## Usage

To use this skill, run the following command:

```bash
python3 /root/.gemini/skills/url2md/url2md.py <URL> [--out-file <OUTPUT_FILE>]
```

### Parameters

- `<URL>`: The URL of the web page you want to convert.
- `--out-file`: (Optional) The path to the output Markdown file. If omitted, the output is printed to `stdout`.

## Implementation Details

- **Browser Engine**: Playwright (Chromium)
- **HTML Parser**: BeautifulSoup4
- **Features**:
  - Handles dynamic content by waiting for 5 seconds after DOM content is loaded.
  - Converts headers (h1-h4), links, paragraphs, and tables.
  - Cleans up the output by removing scripts, styles, and other non-content elements.

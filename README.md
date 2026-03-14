# Pica Skills

A collection of specialized skills for Gemini CLI to automate workflows, including web content extraction and social media automation.

## 🚀 Available Skills

### 1. [url2md](./url2md/)
Convert any web page into clean Markdown.
- **Features**: 
  - Dynamic content rendering with Playwright.
  - Automatic 5-minute caching to `.cache` directory.
  - Intelligent HTML parsing with BeautifulSoup4.
- **Usage**:
  ```bash
  python url2md/url2md.py <URL> [--out-file <OUTPUT_FILE>]
  ```

### 2. [xhs-browser-poster](./xhs-browser-poster/)
Automate Xiaohongshu (小红书) posting with AI-generated images.
- **Features**:
  - **Image Generation**: Automates Gemini to create high-quality images based on prompts.
  - **Auto-Posting**: Handles image upload, title, and content filling on XHS.
  - **Verification**: Automatically checks the Note Manager to confirm successful publishing.
- **Usage**:
  - **Generate Image**: `python xhs-browser-poster/scripts/generate_gemini_img.py "Prompt"`
  - **Post to XHS**: `python xhs-browser-poster/scripts/post_to_xhs.py "image.jpg" "Title" "Content"`

## 🛠️ Requirements

- **Python 3.8+**
- **Browser**: Chrome/Edge with remote debugging enabled (`--remote-debugging-port=9222`).
- **Dependencies**:
  - `playwright`
  - `beautifulsoup4`
  - `requests` (for some internal scripts)

Install dependencies:
```bash
pip install playwright beautifulsoup4
playwright install chromium
```

## 📂 Project Structure

```text
.
├── url2md/                 # Web to Markdown conversion
│   ├── url2md.py
│   └── SKILL.md
└── xhs-browser-poster/     # Xiaohongshu automation
    ├── scripts/
    │   ├── generate_gemini_img.py
    │   ├── get_note_manager_data.py
    │   └── post_to_xhs.py
    └── SKILL.md
```

## 📜 License
MIT

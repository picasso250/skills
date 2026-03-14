# Pica Skills

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

A collection of specialized skills for Gemini CLI to automate workflows.

### 🚀 Available Skills

#### 1. [url2md](./url2md/)
Convert web pages to clean Markdown.
- **Features**: Dynamic rendering (Playwright), 5-min caching, smart parsing.
- **Usage**: `python url2md/url2md.py <URL> [--out-file <OUTPUT_FILE>]`

#### 2. [xhs-browser-poster](./xhs-browser-poster/)
Automate Xiaohongshu (XHS) posting with AI images.
- **Features**: Gemini image generation, auto-upload, post verification.
- **Usage**:
  - **Gen Image**: `python xhs-browser-poster/scripts/generate_gemini_img.py "Prompt"`
  - **Post**: `python xhs-browser-poster/scripts/post_to_xhs.py "img.jpg" "Title" "Content"`

### 🛠️ Requirements
- Python 3.8+, Chrome/Edge with `--remote-debugging-port=9222`.
- `pip install playwright beautifulsoup4`

---

<a name="中文"></a>
## 中文

Gemini CLI 自动化工作流技能库。

### 🚀 现有技能

#### 1. [url2md](./url2md/)
将网页转换为干净的 Markdown。
- **特性**: 动态渲染 (Playwright), 5分钟缓存, 智能解析。
- **用法**: `python url2md/url2md.py <URL> [--out-file <输出文件>]`

#### 2. [xhs-browser-poster](./xhs-browser-poster/)
自动化小红书发帖（含 AI 配图）。
- **特性**: Gemini AI 绘图, 自动上传发布, 发布状态校验。
- **用法**:
  - **生图**: `python xhs-browser-poster/scripts/generate_gemini_img.py "提示词"`
  - **发帖**: `python xhs-browser-poster/scripts/post_to_xhs.py "图片路径" "标题" "正文"`

### 🛠️ 环境要求
- Python 3.8+, 需开启 Chrome/Edge 远程调试端口 (`--remote-debugging-port=9222`)。
- `pip install playwright beautifulsoup4`

## 📜 License
MIT

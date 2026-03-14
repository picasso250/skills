---
name: xhs-browser-poster
description: Automates Xiaohongshu (XHS) posting via browser. Includes two robust scripts: one for generating high-res images in Gemini (including Tool selection) and one for publishing to XHS and verifying via the Note Manager.
---

# XHS Browser Poster

Automate Xiaohongshu publishing with AI-generated images.

## Prerequisite
- Browser with remote debugging enabled (`--remote-debugging-port=9222`).
- User already logged into Xiaohongshu and Gemini.

## Core Scripts

### 1. Gemini Image Generation
Use `scripts/generate_gemini_img.py` to generate and download an image.
- **Input**: Prompt string.
- **Workflow**: Navigates to Gemini, clicks "Tools" -> "Create Image", waits 60s for generation, and downloads the high-res file.
- **Output**: Prints `RESULT_IMAGE_PATH:<path>`.

```bash
python scripts/generate_gemini_img.py "A cozy afternoon tea at a street cafe, natural lighting, shot on phone."
```

### 2. XHS Posting & Verification
Use `scripts/post_to_xhs.py` to publish and verify.
- **Input**: Image path, Title, and Content.
- **Workflow**: Navigates directly to the image publish page, uploads image, fills title/content (ensuring spaces after hashtags), clicks Publish, and navigates to the Note Manager.
- **Output**: Prints `RESULT_SCREENSHOT_PATH:<path>` showing the post in the Note Manager.

```bash
python scripts/post_to_xhs.py "image.jpg" "Title" "Content"
```

## Best Practices
- **Hashtags**: Always ensure a space after each hashtag in the content string.
- **Verification**: Always check the result screenshot to ensure the post is visible in the manager.

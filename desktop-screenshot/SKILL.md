---
name: desktop-screenshot
description: Capture the current Windows desktop to a PNG file. Use when Codex needs a screenshot of the user's desktop, taskbar, open windows, or full monitor state for debugging, remote inspection, or visual confirmation. Prefer this over webpage screenshot skills when the target is the actual desktop rather than a browser page.
---

# Desktop Screenshot

Run the script from this skill's `scripts/` directory:

```powershell
python capture_desktop.py --out "$HOME\desktop.png"
```

Default behavior:

- capture all screens
- save PNG output
- print the saved path and image size

Useful options:

```powershell
python capture_desktop.py --out "$HOME\desktop.png"
python capture_desktop.py --out "$HOME\desktop-primary.png" --single-screen
```

Notes:

- Use absolute output paths when you want predictable file locations.
- The script requires Pillow because it uses `PIL.ImageGrab`.
- After capturing, attach or send the PNG with the relevant reply workflow.

---
name: xiaohongshu-manage
description: Use Chrome DevTools Protocol to open Xiaohongshu Creator note manager in the logged-in browser, scroll the note list repeatedly, collect loaded note/list text, print a TXT report to stdout, then close the temporary tab. Use when the user asks to scrape, dump, scroll, or inspect creator.xiaohongshu.com/new/note-manager data.
---

# Xiaohongshu Manage

## Workflow

1. Require the user browser to be logged in and opened with `--remote-debugging-port=9222`.
2. Run `scripts/export_xhs_note_manager_txt.py`; it opens a new tab at `https://creator.xiaohongshu.com/new/note-manager`.
3. Wait 3 seconds, scroll down repeatedly, and accumulate visible loaded text after each scroll.
4. Print TXT to stdout by default. Use `--output` only when the user asks to save a file.
5. Wait 1 second after output, then close the temporary tab.

## Commands

```powershell
python "$HOME\.agents\skills\xiaohongshu-manage\scripts\export_xhs_note_manager_txt.py"
```

```powershell
python "$HOME\.agents\skills\xiaohongshu-manage\scripts\export_xhs_note_manager_txt.py" `
  --output "C:\temp\xhs-notes.txt" `
  --max-scrolls 80 `
  --delay-ms 900
```

## Notes

- Default CDP endpoint is `http://127.0.0.1:9222`.
- Default target URL is `https://creator.xiaohongshu.com/new/note-manager`.
- The script exports visible card/row/list text, not hidden API data.

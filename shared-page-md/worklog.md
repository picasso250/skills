# Worklog

- 2026-06-14: Old `page_to_md.py` hung when reading `https://mail.google.com/mail/u/0/#inbox` through Playwright browser-level CDP attach, while direct page-level CDP WebSocket evaluation of `document.title` succeeded.
- 2026-06-14: Updated `page_to_md.py` to prefer existing-tab page-level CDP HTML capture; verified Gmail inbox with `--timeout 3`, producing `full.md` and `page.html`.

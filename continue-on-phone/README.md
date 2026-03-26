# continue-on-phone

Minimal phone handoff stack:

- Cloudflare Worker with KV-backed session storage
- Mobile web page for user chat
- `start_scan.py` to create/reuse a session and print a QR code
- `interact.py` to append agent text and read new user replies


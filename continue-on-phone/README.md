# continue-on-phone

Minimal phone handoff stack:

- Cloudflare Worker with KV-backed session storage
- Mobile web page for user chat
- `start_scan.py` to create a server-generated session and print a QR code
- `interact.py` to append agent text and read new user replies

Security model:

- Each session gets a server-generated `session_id` and long-lived `app_token`
- `start_scan.py` prints a QR code for a one-time `exchange_url` in the form `/n/{exchange_token}`
- `exchange_token` is base62, single-use, and expires after 30 minutes
- Visiting `/n/{exchange_token}` sets `HttpOnly` auth cookies and redirects to `/s/{session_id}`
- Web API requests only trust the auth cookies; the URL alone is not enough to read or write messages
- Session KV records use a 24 hour sliding TTL and are renewed on every write
- Local scripts save `session_id` and `app_token` under `~/.continue-on-phone/` and send them back as cookies when calling the API

Operational notes:

- `start_scan.py` always creates a new session
- `interact.py` reads the active session by default, or accepts `--session-id`
- If the browser loses its cookies, the user must scan a fresh QR code

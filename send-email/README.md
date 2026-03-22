# send-email

Only tested with 163 mail SMTP.

Use `scripts/send_email.py`.

Supports `--attachments` for sending one or more local files as attachments.

Markdown is rendered to HTML with `cmarkgfm` (GitHub Flavored Markdown).

`.env` is searched upward from the script directory until the filesystem root / drive root.

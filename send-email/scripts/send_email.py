import smtplib
import argparse
import os
import sys
import mimetypes
from cmarkgfm import github_flavored_markdown_to_html
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

MAX_ATTACHMENT_BYTES = 50 * 1024 * 1024


def find_env_path() -> str | None:
    current = os.path.abspath(os.path.dirname(__file__))
    while True:
        candidate = os.path.join(current, ".env")
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def load_env():
    env_vars = {}
    env_path = find_env_path()

    if not env_path:
        print("Error: .env file not found while walking upward from the script directory.")
        sys.exit(1)

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip()
    return env_vars


def parse_attachments(raw_attachments: list[str] | None) -> list[str]:
    if not raw_attachments:
        return []

    attachments: list[str] = []
    for item in raw_attachments:
        for part in item.split(","):
            part = part.strip()
            if not part:
                continue
            attachments.append(part)
    return attachments


def attach_files(msg, attachments: list[str]):
    for attachment_path in attachments:
        if not os.path.exists(attachment_path):
            print(f"Error: Attachment file not found at {attachment_path}")
            sys.exit(1)

        file_size = os.path.getsize(attachment_path)
        if file_size > MAX_ATTACHMENT_BYTES:
            print(
                f"Error: Attachment exceeds 50MB limit: {attachment_path} "
                f"({file_size} bytes)"
            )
            sys.exit(1)

        mime_type, _ = mimetypes.guess_type(attachment_path)
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"

        with open(attachment_path, "rb") as f:
            part = MIMEBase(maintype, subtype)
            part.set_payload(f.read())

        encoders.encode_base64(part)
        filename = os.path.basename(attachment_path)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)


def send_email(subject, body_file, recipient_override, reply_ids_str, raw_attachments):
    if not os.path.exists(body_file):
        print(f"Error: Body file not found at {body_file}")
        sys.exit(1)

    ids = [id.strip() for id in reply_ids_str.split(',')] if reply_ids_str else []
    attachments = parse_attachments(raw_attachments)

    # Prepend reply IDs to the file as links if multiple IDs are provided
    with open(body_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if len(ids) > 1:
        links = " ".join([f"[#{id}](#{id})" for id in ids])
        if links not in content:
            with open(body_file, 'w', encoding='utf-8') as f:
                f.write(f"{links}\n\n" + content)

    with open(body_file, 'r', encoding='utf-8') as f:
        markdown_body = f.read()

    config = load_env()
    user = config.get('MAIL_USER')
    password = config.get('MAIL_PASS')
    recipient = recipient_override
    smtp_server = config.get('MAIL_SMTP_SERVER', 'smtp.163.com')
    smtp_port = int(config.get('MAIL_SMTP_PORT', 465))

    print(f"[*] Sending email from {user} to {recipient} (ID: {reply_ids_str})...")

    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = recipient

    html_content = github_flavored_markdown_to_html(markdown_body)

    style = """
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #24292e;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2, h3 { margin-top: 24px; margin-bottom: 16px; font-weight: 600; line-height: 1.25; }
        h1 { padding-bottom: 0.3em; border-bottom: 1px solid #eaecef; }
        h2 { padding-bottom: 0.3em; border-bottom: 1px solid #eaecef; }
        pre {
            background-color: #f6f8fa;
            border-radius: 3px;
            padding: 16px;
            overflow: auto;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        }
        code {
            background-color: rgba(27,31,35,0.05);
            border-radius: 3px;
            padding: 0.2em 0.4em;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 85%;
        }
        table { border-collapse: collapse; width: 100%; margin-top: 0; margin-bottom: 16px; }
        table th, table td { border: 1px solid #dfe2e5; padding: 6px 13px; }
        table tr { background-color: #fff; border-top: 1px solid #c6cbd1; }
        table tr:nth-child(2n) { background-color: #f6f8fa; }
        blockquote { border-left: 0.25em solid #dfe2e5; color: #6a737d; padding: 0 1em; margin: 0 0 16px 0; }
        img { max-width: 100%; }
    </style>
    """

    html_body = f"<html><head>{style}</head><body>{html_content}</body></html>"

    body_part = MIMEMultipart('alternative')
    part1 = MIMEText(markdown_body, 'plain', 'utf-8')
    part2 = MIMEText(html_body, 'html', 'utf-8')

    body_part.attach(part1)
    body_part.attach(part2)
    msg.attach(body_part)
    attach_files(msg, attachments)

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(user, password)
            server.sendmail(user, recipient, msg.as_string())
        print("[+] Email sent successfully!")
    except Exception as e:
        print(f"[-] Failed to send email: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send an email via 163 SMTP using a GitHub Flavored Markdown file."
    )
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--markdown-body-file", required=True, help="Path to the Markdown file containing the email body")
    parser.add_argument("--ids", help="Reference IDs for the reply (comma separated)")
    parser.add_argument("--to", help="Email recipient override")
    parser.add_argument("--attachments", nargs="*", help="Attachment paths. Supports multiple args or comma-separated paths.")

    args = parser.parse_args()
    send_email(args.subject, args.markdown_body_file, args.to, args.ids, args.attachments)

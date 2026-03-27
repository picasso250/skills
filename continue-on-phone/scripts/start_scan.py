from __future__ import annotations

import argparse
import sys
from pathlib import Path

import qrcode

from common import STATE_DIR, api_post, configure_stdio_utf8, save_active_session, save_session_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or reuse a continue-on-phone session and print a terminal QR code."
    )
    return parser


def print_qr(url: str) -> None:
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        qr.print_ascii(invert=True)
    except Exception:
        matrix = qr.get_matrix()
        for row in matrix:
            line = "".join("##" if cell else "  " for cell in row)
            print(line)


def save_qr_png(url: str, session_id: str) -> Path:
    qr = qrcode.QRCode(border=4, box_size=12)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    output_path = STATE_DIR / f"{session_id}.png"
    image.save(output_path)
    return output_path


def main() -> None:
    configure_stdio_utf8()
    build_parser().parse_args()

    result = api_post("/api/sessions", {})
    session_id = result["session_id"]
    session_url = result["session_url"]
    exchange_url = result["exchange_url"]
    app_token = result["app_token"]
    save_active_session(session_id, session_url, app_token)
    save_session_state(
        session_id,
        {
            "session_id": session_id,
            "app_token": app_token,
            "last_user_ts": None,
        },
    )

    print(f"session_id={session_id}")
    print(f"session_url={session_url}")
    print(f"exchange_url={exchange_url}")
    png_path = save_qr_png(exchange_url, session_id)
    print(f"qr_png={png_path}")
    print()
    print_qr(exchange_url)


if __name__ == "__main__":
    main()

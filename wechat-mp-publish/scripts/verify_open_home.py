#!/usr/bin/env python3
"""
Open a new tab to WeChat Official Accounts home in an existing Chrome DevTools session.
"""

from __future__ import annotations

import json
import logging
import sys

from playwright.sync_api import Error, sync_playwright
from urllib.request import urlopen

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_URL = "https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def resolve_ws_endpoint(cdp_url: str) -> str:
    version_url = f"{cdp_url.rstrip('/')}/json/version"
    with urlopen(version_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    ws_endpoint = payload.get("webSocketDebuggerUrl")
    if not ws_endpoint:
        raise RuntimeError(f"Missing webSocketDebuggerUrl in {version_url}")
    return ws_endpoint


def main() -> None:
    setup_logging()

    try:
        ws_endpoint = resolve_ws_endpoint(DEFAULT_CDP_URL)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(ws_endpoint)
            try:
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.new_page()
                page.set_default_timeout(30 * 1000)
                logging.info("Opening new tab: %s", DEFAULT_URL)
                page.goto(DEFAULT_URL, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
                print(f"Opened tab title: {page.title()}")
                print(f"Opened tab url: {page.url}")
            finally:
                browser.close()
    except Error as exc:
        logging.error("Failed to open WeChat MP home tab: %s", exc)
        sys.exit(1)
    except OSError as exc:
        logging.error("Failed to reach Chrome DevTools: %s", exc)
        sys.exit(1)
    except RuntimeError as exc:
        logging.error("%s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        logging.warning("Interrupted by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()

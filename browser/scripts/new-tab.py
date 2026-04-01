#!/usr/bin/env python3
"""
Open a fresh tab in an existing Chrome/Edge remote-debugging session.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import Error, sync_playwright


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open a new tab in an existing Chrome/Edge DevTools session."
    )
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    parser.add_argument(
        "--match-url",
        help="Reuse the browser context that already has a page whose URL contains this string.",
    )
    parser.add_argument("--url", required=True, help="URL to open in a new tab")
    parser.add_argument("--timeout", type=int, default=30, help="Navigation timeout in seconds")
    return parser.parse_args()


def resolve_ws_endpoint(cdp_url: str) -> str:
    version_url = f"{cdp_url.rstrip('/')}/json/version"
    with urlopen(version_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    ws_endpoint = payload.get("webSocketDebuggerUrl")
    if not ws_endpoint:
        raise RuntimeError(f"Missing webSocketDebuggerUrl in {version_url}")
    return ws_endpoint


def choose_context(browser, match_url: str | None):
    if not browser.contexts:
        raise RuntimeError("No existing browser contexts found in the DevTools session.")

    if match_url:
        for context in browser.contexts:
            for page in context.pages:
                if match_url in page.url:
                    logging.info("Reusing context matched by page URL: %s", page.url)
                    return context
        raise RuntimeError(f"No browser context has a page URL containing: {match_url}")

    if len(browser.contexts) == 1:
        return browser.contexts[0]

    raise RuntimeError(
        "Multiple browser contexts are open. Pass --match-url to select the intended context."
    )


def main() -> None:
    setup_logging()
    args = parse_args()

    try:
        ws_endpoint = resolve_ws_endpoint(args.cdp_url)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(ws_endpoint)
            try:
                context = choose_context(browser, args.match_url)
                page = context.new_page()
                page.set_default_timeout(args.timeout * 1000)
                logging.info("Opening new tab: %s", args.url)
                page.goto(args.url, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
                print(f"Opened tab title: {page.title()}")
                print(f"Opened tab url: {page.url}")
            finally:
                browser.close()
    except Error as exc:
        logging.error("Failed to open new tab: %s", exc)
        sys.exit(1)
    except URLError as exc:
        logging.error("Failed to reach Chrome DevTools: %s", exc)
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

#!/usr/bin/env python3
"""
Open a fresh tab in an existing Chrome/Edge remote-debugging session.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


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


def open_tab(cdp_url: str, url: str) -> dict:
    new_url = f"{cdp_url.rstrip('/')}/json/new?{quote(url, safe='')}"
    request = Request(new_url, method="PUT", headers={"User-Agent": "website-to-cli/new-tab"})
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    setup_logging()
    args = parse_args()

    try:
        resolve_ws_endpoint(args.cdp_url)
        if args.match_url:
            logging.info("--match-url is accepted for workflow compatibility; /json/new opens a fresh target.")
        logging.info("Opening new tab: %s", args.url)
        target = open_tab(args.cdp_url, args.url)
        print(f"Opened tab title: {target.get('title', '')}")
        print(f"Opened tab url: {target.get('url', '')}")
        print(f"Opened tab ws: {target.get('webSocketDebuggerUrl', '')}")
    except HTTPError as exc:
        logging.error("Failed to open new tab: HTTP %s %s", exc.code, exc.reason)
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

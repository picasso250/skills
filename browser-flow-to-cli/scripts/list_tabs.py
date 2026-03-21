#!/usr/bin/env python

from __future__ import annotations

import argparse
import json
import sys

from playwright.sync_api import sync_playwright

from cdp_common import DEFAULT_ENDPOINT, collect_tabs, get_ws_url


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="list_tabs.py",
        description="List existing browser tabs from a Chrome CDP endpoint.",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"Chrome CDP endpoint. Default: {DEFAULT_ENDPOINT}",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    ws_url = get_ws_url(args.endpoint)

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(ws_url)
        try:
            tabs = [tab.to_dict() for tab in collect_tabs(browser)]
        finally:
            browser.close()

    print(json.dumps(tabs, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))

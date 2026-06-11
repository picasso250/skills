#!/usr/bin/env python

from __future__ import annotations

"""Run JavaScript in an already-open tab selected by exact URL."""

import argparse
import json
import sys

from playwright.sync_api import sync_playwright

from cdp_common import DEFAULT_ENDPOINT, find_page_by_exact_url, get_ws_url


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="eval-tab-js.py",
        description="Evaluate JavaScript in an existing browser tab matched by exact URL.",
    )
    parser.add_argument("--url", required=True, help="Exact page URL to match.")
    parser.add_argument("--code", default="", help="JavaScript code to evaluate. If omitted, read from stdin.")
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"Chrome CDP endpoint. Default: {DEFAULT_ENDPOINT}",
    )
    return parser.parse_args(argv)


def read_code(args: argparse.Namespace) -> str:
    code = args.code
    if not code:
        code = sys.stdin.read()
    code = code.strip()
    if not code:
        raise RuntimeError("Missing JavaScript code. Pass --code or pipe code via stdin.")
    return code


def eval_in_tab(url: str, code: str, endpoint: str = DEFAULT_ENDPOINT):
    code = code.strip()
    if not code:
        raise RuntimeError("Missing JavaScript code.")

    ws_url = get_ws_url(endpoint)
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(ws_url)
        try:
            page = find_page_by_exact_url(browser, url)
            return page.evaluate(code)
        finally:
            browser.close()


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    code = read_code(args)
    result = eval_in_tab(args.url, code, args.endpoint)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python

from __future__ import annotations

"""Collect console messages from an already-open tab selected by exact URL."""

import argparse
import json
import sys
import time
from typing import Any

from playwright.sync_api import ConsoleMessage, sync_playwright

from cdp_common import DEFAULT_ENDPOINT, find_page_by_exact_url, get_ws_url


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="collect-console.py",
        description="Listen for console messages in an existing browser tab matched by exact URL.",
    )
    parser.add_argument("--url", required=True, help="Exact page URL to match.")
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"Chrome CDP endpoint. Default: {DEFAULT_ENDPOINT}",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=10.0,
        help="How long to listen for new console messages. Default: 10.",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Print each console message as one JSON object per line.",
    )
    parser.add_argument(
        "--include-location",
        action="store_true",
        help="Include source URL, line, and column when available.",
    )
    return parser.parse_args(argv)


def serialize_arg(value: Any) -> Any:
    try:
        return value.json_value()
    except Exception:
        return str(value)


def serialize_message(message: ConsoleMessage, include_location: bool) -> dict[str, Any]:
    item: dict[str, Any] = {
        "type": message.type,
        "text": message.text,
        "args": [serialize_arg(arg) for arg in message.args],
        "timestamp": time.time(),
    }
    if include_location:
        item["location"] = message.location
    return item


def format_message(item: dict[str, Any]) -> str:
    prefix = f"[{item['type']}]"
    text = item["text"]
    if item.get("location"):
        location = item["location"]
        url = location.get("url") or "<anonymous>"
        line = location.get("lineNumber")
        column = location.get("columnNumber")
        return f"{prefix} {text}\n    at {url}:{line}:{column}"
    return f"{prefix} {text}"


def collect_console(url: str, endpoint: str, seconds: float, include_location: bool) -> list[dict[str, Any]]:
    if seconds < 0:
        raise RuntimeError("--seconds must be 0 or greater.")

    ws_url = get_ws_url(endpoint)
    messages: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(ws_url)
        try:
            page = find_page_by_exact_url(browser, url)

            def on_console(message: ConsoleMessage) -> None:
                messages.append(serialize_message(message, include_location))

            page.on("console", on_console)
            page.wait_for_timeout(int(seconds * 1000))
            return messages
        finally:
            browser.close()


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    messages = collect_console(args.url, args.endpoint, args.seconds, args.include_location)

    if args.jsonl:
        for item in messages:
            print(json.dumps(item, ensure_ascii=False, default=str))
        return 0

    if not messages:
        print("No console messages captured.")
        return 0

    for item in messages:
        print(format_message(item))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))

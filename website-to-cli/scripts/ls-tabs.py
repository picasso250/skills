#!/usr/bin/env python3
"""
Quick helper to summarize Chrome/Edge tabs and highlight candidates for website-to-cli.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch_targets(host: str, port: int, path: str, timeout: float) -> list[dict[str, Any]]:
    url = f"http://{host}:{port}{path}"
    req = Request(url, headers={"User-Agent": "website-to-cli/ls-tabs"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8")
            data = json.loads(payload)
    except (HTTPError, URLError) as exc:
        print(f"Failed to fetch {url}: {exc}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON from {url}: {exc}", file=sys.stderr)
        sys.exit(1)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    print("Received unexpected JSON structure.", file=sys.stderr)
    sys.exit(1)


def describe_target(idx: int, target: dict[str, Any]) -> str:
    title = target.get("title") or target.get("description") or "<untitled>"
    url = target.get("url", "<no url>")
    ws = target.get("webSocketDebuggerUrl") or target.get("webSocketUrl") or "<no ws>"
    target_type = target.get("type", "<unknown>")
    return f"{idx:02d}. {title} ({target_type})\n    url: {url}\n    ws: {ws}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="List remote debugging tabs for website-to-cli.")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--path", default="/json/list")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include non-page DevTools targets.",
    )
    parser.add_argument(
        "--raw-json",
        action="store_true",
        help="Print the original JSON payload instead of the summarized tab list.",
    )
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    all_targets = fetch_targets(args.host, args.port, args.path, args.timeout)
    if not all_targets:
        print("No tabs returned by DevTools.", file=sys.stderr)
        sys.exit(1)
    targets = all_targets if args.all else [target for target in all_targets if target.get("type") == "page"]
    if not targets:
        print("No matching DevTools targets returned.", file=sys.stderr)
        sys.exit(1)
    if args.raw_json:
        print(json.dumps(targets, ensure_ascii=False, indent=2))
        return
    for idx, target in enumerate(targets, start=1):
        print(describe_target(idx, target))


if __name__ == "__main__":
    main()

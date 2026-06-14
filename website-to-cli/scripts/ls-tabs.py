#!/usr/bin/env python3
"""
Summarize Chrome/Edge DevTools endpoints and highlight candidate tabs.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch_json(host: str, port: int, path: str, timeout: float) -> Any:
    url = f"http://{host}:{port}{path}"
    req = Request(url, headers={"User-Agent": "website-to-cli/ls-tabs"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload)
    except (HTTPError, URLError) as exc:
        print(f"Failed to fetch {url}: {exc}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON from {url}: {exc}", file=sys.stderr)
        sys.exit(1)


def fetch_targets(host: str, port: int, path: str, timeout: float) -> list[dict[str, Any]]:
    data = fetch_json(host, port, path, timeout)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    print("Received unexpected JSON structure.", file=sys.stderr)
    sys.exit(1)


def describe_browser_endpoint(version: dict[str, Any]) -> str:
    browser = version.get("Browser") or version.get("browser") or "<unknown browser>"
    protocol = version.get("Protocol-Version") or "<unknown protocol>"
    ws = version.get("webSocketDebuggerUrl") or "<no browser ws>"
    return (
        "Browser target\n"
        f"    browser: {browser}\n"
        f"    protocol: {protocol}\n"
        f"    browserWsEndpoint: {ws}\n"
    )


def describe_target(idx: int, target: dict[str, Any]) -> str:
    title = target.get("title") or target.get("description") or "<untitled>"
    url = target.get("url", "<no url>")
    ws = target.get("webSocketDebuggerUrl") or target.get("webSocketUrl") or "<no ws>"
    target_type = target.get("type", "<unknown>")
    return f"{idx:02d}. {title} ({target_type})\n    url: {url}\n    pageWsEndpoint: {ws}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="List remote debugging endpoints for website-to-cli.")
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
    parser.add_argument(
        "--match",
        help="Filter targets whose title/url/description contains this substring (case-insensitive).",
    )
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    version = fetch_json("127.0.0.1", args.port, "/json/version", args.timeout)
    all_targets = fetch_targets("127.0.0.1", args.port, args.path, args.timeout)
    if not all_targets:
        print("No tabs returned by DevTools.", file=sys.stderr)
        sys.exit(1)
    targets = all_targets if args.all else [target for target in all_targets if target.get("type") == "page"]
    if args.match:
        needle = args.match.lower()
        targets = [
            target
            for target in targets
            if needle
            in " ".join(
                str(target.get(key, "")).lower() for key in ("title", "url", "description")
            )
        ]
    if not targets:
        print("No matching DevTools targets returned.", file=sys.stderr)
        sys.exit(1)
    if args.raw_json:
        print(
            json.dumps(
                {
                    "browser": version,
                    "targets": targets,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    print(describe_browser_endpoint(version))
    for idx, target in enumerate(targets, start=1):
        print(describe_target(idx, target))


if __name__ == "__main__":
    main()

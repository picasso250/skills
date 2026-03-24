#!/usr/bin/env python3
"""
List Chrome/Edge remote-debugging endpoints so the human can confirm the right webSocketDebuggerUrl.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch_json(host: str, port: int, path: str, timeout: float) -> Any:
    if not path.startswith("/"):
        path = f"/{path}"
    url = f"http://{host}:{port}{path}"
    req = Request(url, headers={"User-Agent": "website-to-cli/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload)
    except HTTPError as exc:
        print(f"HTTP {exc.code} when reaching {url}: {exc.reason}", file=sys.stderr)
    except URLError as exc:
        print(f"Unable to reach {url}: {exc}", file=sys.stderr)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON from {url}: {exc}", file=sys.stderr)
    sys.exit(1)


def format_target(idx: int, target: Any) -> str:
    title = target.get("title") or target.get("description") or "<untitled>"
    url = target.get("url", "<no url>")
    ws = (
        target.get("webSocketDebuggerUrl")
        or target.get("webSocketUrl")
        or target.get("devtoolsFrontendUrl")
        or "<no ws>"
    )
    target_type = target.get("type", "<unknown>")
    return (
        f"[{idx}] title: {title}\n"
        f"    type: {target_type}\n"
        f"    url: {url}\n"
        f"    wsEndpoint: {ws}\n"
    )


def normalize_targets(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    print("Unexpected JSON structure; expected object or array.", file=sys.stderr)
    sys.exit(1)


def filter_targets(targets: list[dict[str, Any]], match: str | None) -> list[dict[str, Any]]:
    if not match:
        return targets
    needle = match.lower()
    filtered = []
    for target in targets:
        haystack = " ".join(
            str(target.get(key, "")).lower() for key in ("title", "url", "description")
        )
        if needle in haystack:
            filtered.append(target)
    return filtered


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch remote debugging targets from Chrome/Edge for website-to-cli workflows."
    )
    parser.add_argument("--host", default="localhost", help="Remote debugging host")
    parser.add_argument("--port", type=int, default=9222, help="Remote debugging port")
    parser.add_argument(
        "--path",
        default="/json/list",
        help="JSON path (default /json/list; /json/version also works)",
    )
    parser.add_argument(
        "--match",
        help="Filter targets whose title/url/description contains this substring (case-insensitive)",
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="HTTP request timeout in seconds"
    )
    args = parser.parse_args()

    data = fetch_json(args.host, args.port, args.path, args.timeout)
    targets = normalize_targets(data)
    targets = filter_targets(targets, args.match)
    if not targets:
        print("No remote targets found. Check the browser or try a different --path.", file=sys.stderr)
        sys.exit(1)
    for idx, target in enumerate(targets, start=1):
        print(format_target(idx, target))


if __name__ == "__main__":
    main()

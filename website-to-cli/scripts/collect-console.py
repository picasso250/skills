#!/usr/bin/env python

from __future__ import annotations

"""Collect console messages from an already-open tab selected by exact URL."""

import argparse
import asyncio
import json
import sys
import time
from typing import Any
from urllib.request import Request, urlopen

import websockets


DEFAULT_ENDPOINT = "http://127.0.0.1:9222"


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


def fetch_json(endpoint: str, path: str) -> Any:
    request = Request(f"{endpoint.rstrip('/')}{path}", headers={"User-Agent": "website-to-cli/collect-console"})
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def find_page_ws(endpoint: str, url: str) -> str:
    tabs = fetch_json(endpoint, "/json/list")
    for tab in tabs:
        if tab.get("type") == "page" and tab.get("url") == url:
            ws_url = tab.get("webSocketDebuggerUrl")
            if not ws_url:
                raise RuntimeError(f"Tab has no webSocketDebuggerUrl: {url}")
            return ws_url.replace("ws://localhost:", "ws://127.0.0.1:")
    raise RuntimeError(f"Exact tab not found for URL: {url}")


def remote_object_value(remote: dict[str, Any]) -> Any:
    if "value" in remote:
        return remote["value"]
    if "unserializableValue" in remote:
        return remote["unserializableValue"]
    if "description" in remote:
        return remote["description"]
    return remote.get("type")


def runtime_message(params: dict[str, Any], include_location: bool) -> dict[str, Any]:
    item: dict[str, Any] = {
        "type": params.get("type", "log"),
        "text": " ".join(str(remote_object_value(arg)) for arg in params.get("args", [])),
        "args": [remote_object_value(arg) for arg in params.get("args", [])],
        "timestamp": time.time(),
    }
    if include_location:
        stack = params.get("stackTrace", {})
        frames = stack.get("callFrames", []) if isinstance(stack, dict) else []
        frame = frames[0] if frames else {}
        item["location"] = {
            "url": frame.get("url", ""),
            "lineNumber": frame.get("lineNumber"),
            "columnNumber": frame.get("columnNumber"),
        }
    return item


def log_message(params: dict[str, Any], include_location: bool) -> dict[str, Any]:
    entry = params.get("entry", {})
    item: dict[str, Any] = {
        "type": entry.get("level", "log"),
        "text": entry.get("text", ""),
        "args": [],
        "timestamp": time.time(),
    }
    if include_location:
        item["location"] = {
            "url": entry.get("url", ""),
            "lineNumber": entry.get("lineNumber"),
            "columnNumber": None,
        }
    return item


async def send_command(websocket, command_id: int, method: str) -> None:
    await websocket.send(json.dumps({"id": command_id, "method": method}))


async def collect_console_ws(ws_url: str, seconds: float, include_location: bool) -> list[dict[str, Any]]:
    if seconds < 0:
        raise RuntimeError("--seconds must be 0 or greater.")

    messages: list[dict[str, Any]] = []
    async with websockets.connect(ws_url, open_timeout=5, close_timeout=2, max_size=None) as websocket:
        await send_command(websocket, 1, "Runtime.enable")
        await send_command(websocket, 2, "Log.enable")
        end_time = time.monotonic() + seconds
        while True:
            remaining = end_time - time.monotonic()
            if remaining <= 0:
                return messages
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                return messages
            event = json.loads(raw)
            method = event.get("method")
            params = event.get("params", {})
            if method == "Runtime.consoleAPICalled":
                messages.append(runtime_message(params, include_location))
            elif method == "Log.entryAdded":
                messages.append(log_message(params, include_location))


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


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    ws_url = find_page_ws(args.endpoint, args.url)
    messages = asyncio.run(collect_console_ws(ws_url, args.seconds, args.include_location))

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

#!/usr/bin/env python

from __future__ import annotations

"""Run JavaScript in an already-open tab selected by exact URL."""

import argparse
import asyncio
import json
import sys
from typing import Any
from urllib.request import Request, urlopen

import websockets


DEFAULT_ENDPOINT = "http://127.0.0.1:9222"


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
    code = args.code or sys.stdin.read()
    code = code.strip()
    if not code:
        raise RuntimeError("Missing JavaScript code. Pass --code or pipe code via stdin.")
    return code


def fetch_json(endpoint: str, path: str) -> Any:
    request = Request(f"{endpoint.rstrip('/')}{path}", headers={"User-Agent": "website-to-cli/eval-tab-js"})
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


async def eval_over_cdp(ws_url: str, code: str) -> Any:
    async with websockets.connect(ws_url, open_timeout=5, close_timeout=2, max_size=None) as websocket:
        await websocket.send(
            json.dumps(
                {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": code,
                        "awaitPromise": True,
                        "returnByValue": True,
                    },
                }
            )
        )
        while True:
            message = json.loads(await asyncio.wait_for(websocket.recv(), timeout=10))
            if message.get("id") != 1:
                continue
            if "error" in message:
                raise RuntimeError(json.dumps(message["error"], ensure_ascii=False))
            result = message.get("result", {}).get("result", {})
            if result.get("subtype") == "error":
                raise RuntimeError(result.get("description") or result.get("value") or "Runtime.evaluate error")
            return result.get("value")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    code = read_code(args)
    ws_url = find_page_ws(args.endpoint, args.url)
    result = asyncio.run(eval_over_cdp(ws_url, code))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))

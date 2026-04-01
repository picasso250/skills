#!/usr/bin/env python3
"""
Reuse the WeChat article-editor tab and inspect visible cover-related controls.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any
from urllib.request import urlopen

import websocket

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
EDITOR_URL_KEYWORD = "media/appmsg_edit"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def fetch_page_targets(cdp_url: str) -> list[dict[str, Any]]:
    list_url = f"{cdp_url.rstrip('/')}/json/list"
    with urlopen(list_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected JSON from {list_url}")
    return [target for target in payload if target.get("type") == "page"]


def find_editor_target(cdp_url: str) -> dict[str, Any]:
    targets = fetch_page_targets(cdp_url)
    matched = [
        target
        for target in targets
        if EDITOR_URL_KEYWORD in str(target.get("url", ""))
    ]
    if not matched:
        raise RuntimeError("No open page target matched the article editor tab.")
    return matched[-1]


def cdp_eval(ws_endpoint: str, expression: str) -> Any:
    ws = websocket.create_connection(ws_endpoint, timeout=10, suppress_origin=True)
    try:
        message_id = 1
        ws.send(
            json.dumps(
                {
                    "id": message_id,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": expression,
                        "returnByValue": True,
                        "awaitPromise": False,
                    },
                }
            )
        )
        while True:
            raw = ws.recv()
            payload = json.loads(raw)
            if payload.get("id") != message_id:
                continue
            if "error" in payload:
                raise RuntimeError(str(payload["error"]))
            result = payload.get("result", {}).get("result", {})
            if "value" not in result:
                raise RuntimeError("CDP evaluation did not return a value.")
            return result["value"]
    finally:
        ws.close()


def main() -> None:
    setup_logging()

    try:
        target = find_editor_target(DEFAULT_CDP_URL)
        ws_endpoint = str(
            target.get("webSocketDebuggerUrl") or target.get("webSocketUrl") or ""
        )
        if not ws_endpoint:
            raise RuntimeError("Matched editor target did not have a wsEndpoint.")

        expression = r"""
(() => {
  const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
  const isVisible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return style.display !== 'none' &&
      style.visibility !== 'hidden' &&
      rect.width > 0 &&
      rect.height > 0;
  };
  const makePath = (el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 7) {
      let part = node.tagName.toLowerCase();
      if (node.id) {
        part += `#${node.id}`;
        parts.unshift(part);
        break;
      }
      if (node.classList.length) {
        part += '.' + Array.from(node.classList).slice(0, 3).join('.');
      }
      const parent = node.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
        if (siblings.length > 1) {
          part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        }
      }
      parts.unshift(part);
      node = node.parentElement;
    }
    return parts.join(' > ');
  };
  const keywords = ['封面', '题图', '图片', '上传', '裁剪', '修改'];
  const candidates = [];
  const nodes = Array.from(document.querySelectorAll('div, span, button, a, img, label, input, section'));
  for (const el of nodes) {
    if (!isVisible(el)) {
      continue;
    }
    const text = normalize(el.innerText || el.textContent || el.getAttribute('title') || el.getAttribute('aria-label') || el.getAttribute('alt') || el.getAttribute('value'));
    const html = normalize(el.outerHTML).slice(0, 400);
    const combined = `${text} ${html}`;
    if (!keywords.some((keyword) => combined.includes(keyword))) {
      continue;
    }
    const rect = el.getBoundingClientRect();
    candidates.push({
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      className: normalize(el.className),
      role: el.getAttribute('role') || '',
      type: el.getAttribute('type') || '',
      title: el.getAttribute('title') || '',
      ariaLabel: el.getAttribute('aria-label') || '',
      alt: el.getAttribute('alt') || '',
      text,
      path: makePath(el),
      rect: {
        x: Number(rect.x.toFixed(2)),
        y: Number(rect.y.toFixed(2)),
        width: Number(rect.width.toFixed(2)),
        height: Number(rect.height.toFixed(2))
      },
      outerHTML: html
    });
  }
  return candidates;
})()
"""
        results = cdp_eval(ws_endpoint, expression)
        print(f"Editor target title: {target.get('title', '<untitled>')}")
        print(f"Editor target url: {target.get('url', '<no url>')}")
        print(f"Editor target wsEndpoint: {ws_endpoint}")
        print(f"Visible cover-related candidates: {len(results)}")
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except Exception as exc:
        logging.error("%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Observe the real checkbox controls for the declaration agreement dialog.
"""

from __future__ import annotations

import json
import logging
import sys
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


def fetch_editor_ws(cdp_url: str) -> str:
    list_url = f"{cdp_url.rstrip('/')}/json/list"
    with urlopen(list_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected JSON from {list_url}")
    for target in payload:
        if target.get("type") == "page" and EDITOR_URL_KEYWORD in str(target.get("url", "")):
            ws = target.get("webSocketDebuggerUrl") or target.get("webSocketUrl")
            if ws:
                return str(ws).replace("localhost", "127.0.0.1")
    raise RuntimeError("No open editor page matched the article editor tab.")


def cdp_eval(ws_endpoint: str, expression: str):
    ws = websocket.create_connection(ws_endpoint, timeout=10, suppress_origin=True)
    try:
        ws.send(
            json.dumps(
                {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": expression,
                        "returnByValue": True,
                    },
                }
            )
        )
        while True:
            payload = json.loads(ws.recv())
            if payload.get("id") != 1:
                continue
            if "error" in payload:
                raise RuntimeError(str(payload["error"]))
            return payload["result"]["result"]["value"]
    finally:
        ws.close()


def main() -> None:
    setup_logging()

    try:
        ws_endpoint = fetch_editor_ws(DEFAULT_CDP_URL)
        expression = r"""
(() => {
  const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
  const makePath = (el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 8) {
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

  const dialog = document.querySelector('div.claim__original-dialog.original_dialog div.weui-desktop-dialog');
  if (!dialog) return [];

  const selectors = [
    "label.weui-desktop-form__check-label",
    "input.weui-desktop-form__checkbox",
    "i.weui-desktop-icon-checkbox",
    "span.weui-desktop-form__check-content"
  ];
  const out = [];
  for (const selector of selectors) {
    for (const el of dialog.querySelectorAll(selector)) {
      const rect = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      const visible = style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
      const parentText = normalize(el.parentElement?.innerText || '');
      if (!visible || !parentText.includes('我已阅读并同意')) continue;
      out.push({
        selector,
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        className: normalize(el.className),
        text: normalize(el.innerText || el.textContent || ''),
        parentText,
        checked: el instanceof HTMLInputElement ? el.checked : null,
        path: makePath(el),
        rect: {
          x: Number(rect.x.toFixed(2)),
          y: Number(rect.y.toFixed(2)),
          width: Number(rect.width.toFixed(2)),
          height: Number(rect.height.toFixed(2))
        },
        outerHTML: normalize(el.outerHTML).slice(0, 300)
      });
    }
  }
  return out;
})()
"""
        result = cdp_eval(ws_endpoint, expression)
        print(f"Editor wsEndpoint: {ws_endpoint}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        logging.error("%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Click "未声明" first, then observe declaration dialog controls before acting.
"""

from __future__ import annotations

import json
import logging
import random
import sys
from urllib.request import urlopen

import websocket
from playwright.sync_api import sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
EDITOR_URL_KEYWORD = "media/appmsg_edit"
UNSET_TEXT = "未声明"


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


def fetch_browser_ws(cdp_url: str) -> str:
    version_url = f"{cdp_url.rstrip('/')}/json/version"
    with urlopen(version_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    ws = payload.get("webSocketDebuggerUrl")
    if not ws:
        raise RuntimeError(f"Missing webSocketDebuggerUrl in {version_url}")
    return str(ws)


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


def random_point_in_center_band(box: dict[str, float]) -> tuple[float, float, float, float]:
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2
    point_x = center_x + random.uniform(-box["width"] / 8, box["width"] / 8)
    point_y = center_y + random.uniform(-box["height"] / 8, box["height"] / 8)
    return center_x, center_y, point_x, point_y


def main() -> None:
    setup_logging()

    try:
        browser_ws = fetch_browser_ws(DEFAULT_CDP_URL)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(browser_ws)
            try:
                page = None
                for context in browser.contexts:
                    for candidate in context.pages:
                        if EDITOR_URL_KEYWORD in candidate.url:
                            page = candidate
                            break
                    if page:
                        break
                if page is None:
                    raise RuntimeError("No open editor page matched the article editor tab.")
                page.bring_to_front()
                locator = page.get_by_text(UNSET_TEXT, exact=True).first
                locator.wait_for(state="visible", timeout=10000)
                rect = locator.bounding_box()
                if not rect:
                    raise RuntimeError("Could not get bounding box for '未声明'.")
                _, _, click_x, click_y = random_point_in_center_band(rect)
                wait_ms = (1 + random.uniform(-0.5, 0.5)) * 1000
                logging.info("Waiting %.2fs for pre-click pause", wait_ms / 1000)
                page.wait_for_timeout(wait_ms)
                page.mouse.click(click_x, click_y)
                page.wait_for_timeout(1200)
            finally:
                browser.close()

        ws_endpoint = fetch_editor_ws(DEFAULT_CDP_URL)
        expression = r"""
(() => {
  const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
  const makePath = (el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 6) {
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

  const matches = [];
  const pushIfVisible = (el, query, kind) => {
    if (!el || !(el instanceof Element)) return;
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    const visible = style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    if (!visible) return;
    matches.push({
      query,
      kind,
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      className: normalize(el.className),
      text: normalize(el.innerText || el.textContent || el.value || '').slice(0, 200),
      path: makePath(el),
      rect: {
        x: Number(rect.x.toFixed(2)),
        y: Number(rect.y.toFixed(2)),
        width: Number(rect.width.toFixed(2)),
        height: Number(rect.height.toFixed(2))
      },
      outerHTML: normalize(el.outerHTML).slice(0, 300)
    });
  };

  const all = Array.from(document.querySelectorAll('body *'));
  for (const el of all) {
    const text = normalize(el.innerText || el.textContent || '');
    if (text.includes('未声明')) pushIfVisible(el, '未声明', 'text');
    if (text.includes('我已阅读并同意')) pushIfVisible(el, '我已阅读并同意', 'text');
    if (text === '确定') pushIfVisible(el, '确定', 'text');
  }

  const authorSelectors = [
    '#author',
    "input[name='author']",
    "input[placeholder*='作者']",
    "input[id*='author']",
    "textarea[placeholder*='作者']"
  ];
  for (const selector of authorSelectors) {
    for (const el of document.querySelectorAll(selector)) {
      pushIfVisible(el, selector, 'author');
    }
  }

  const checkboxSelectors = [
    "input[type='checkbox']",
    "[role='checkbox']",
    ".frm_checkbox_label",
    ".weui-desktop-checkbox",
    ".weui-desktop-form__checkbox"
  ];
  for (const selector of checkboxSelectors) {
    for (const el of document.querySelectorAll(selector)) {
      const text = normalize(el.innerText || el.textContent || '');
      const combined = normalize((el.parentElement?.innerText || '') + ' ' + (el.innerText || ''));
      if (combined.includes('我已阅读并同意')) {
        pushIfVisible(el, selector, 'checkbox');
      }
    }
  }

  return matches;
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

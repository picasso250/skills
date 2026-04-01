#!/usr/bin/env python3
"""
Reuse the currently open WeChat editor tab with the AI cover dialog already visible,
and inspect the prompt field plus the "开始创作" button.
"""

from __future__ import annotations

import json
import logging
from urllib.request import urlopen

from playwright.sync_api import Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
EDITOR_URL_KEYWORD = "media/appmsg_edit"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def resolve_browser_ws_endpoint(cdp_url: str) -> str:
    version_url = f"{cdp_url.rstrip('/')}/json/version"
    with urlopen(version_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    ws_endpoint = payload.get("webSocketDebuggerUrl")
    if not ws_endpoint:
        raise RuntimeError(f"Missing webSocketDebuggerUrl in {version_url}")
    return str(ws_endpoint)


def find_editor_page(browser) -> Page:
    for context in browser.contexts:
        for page in context.pages:
            if EDITOR_URL_KEYWORD in page.url:
                return page
    raise RuntimeError("No open editor page matched the article editor tab.")


def observe_targets(page: Page) -> list[dict[str, object]]:
    return page.evaluate(
        """
() => {
  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
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
  const keywords = ['请描述你想要的创作内容', '开始创作'];
  const selectors = ['textarea', 'input', 'button', 'div', 'span', 'a'];
  const nodes = Array.from(document.querySelectorAll(selectors.join(',')));
  const results = [];
  for (const el of nodes) {
    if (!isVisible(el)) {
      continue;
    }
    const text = normalize(el.innerText || el.textContent || el.value || el.getAttribute('placeholder') || el.getAttribute('title') || el.getAttribute('aria-label'));
    const placeholder = el.getAttribute('placeholder') || '';
    const combined = `${text} ${placeholder}`;
    if (!keywords.some((keyword) => combined.includes(keyword))) {
      continue;
    }
    const rect = el.getBoundingClientRect();
    results.push({
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      className: normalize(el.className),
      type: el.getAttribute('type') || '',
      role: el.getAttribute('role') || '',
      placeholder,
      text,
      path: makePath(el),
      rect: {
        x: Number(rect.x.toFixed(2)),
        y: Number(rect.y.toFixed(2)),
        width: Number(rect.width.toFixed(2)),
        height: Number(rect.height.toFixed(2))
      }
    });
  }
  return results;
}
"""
    )


def main() -> None:
    setup_logging()
    browser_ws = resolve_browser_ws_endpoint(DEFAULT_CDP_URL)
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(browser_ws)
        try:
            page = find_editor_page(browser)
            logging.info("Reusing editor tab: %s", page.url)
            page.bring_to_front()
            targets = observe_targets(page)
            print(f"Editor tab title: {page.title()}")
            print(f"Editor tab url: {page.url}")
            print(f"Observed target elements: {len(targets)}")
            print(json.dumps(targets, ensure_ascii=False, indent=2))
        finally:
            browser.close()


if __name__ == "__main__":
    main()

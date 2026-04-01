#!/usr/bin/env python3
"""
Reuse the currently open WeChat editor tab after AI cover generation, and
inspect the visible generated images plus their corresponding insert buttons.
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


def observe_results(page: Page) -> dict[str, object]:
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

  const dialog = document.querySelector('div.ai_image_dialog');
  if (!dialog) {
    return { found: false };
  }

  const candidates = [];
  const imageNodes = Array.from(dialog.querySelectorAll('img'));
  for (const img of imageNodes) {
    if (!isVisible(img)) {
      continue;
    }
    const rect = img.getBoundingClientRect();
    const card = img.closest('li, div');
    const insertNode = card ? Array.from(card.querySelectorAll('button, a, div, span')).find((node) => normalize(node.innerText || node.textContent) === '插入') : null;
    const scoreNode = card ? Array.from(card.querySelectorAll('div, span')).find((node) => normalize(node.innerText || node.textContent).includes('AI 图片')) : null;
    candidates.push({
      imgSrc: img.getAttribute('src') || '',
      alt: img.getAttribute('alt') || '',
      path: makePath(img),
      rect: {
        x: Number(rect.x.toFixed(2)),
        y: Number(rect.y.toFixed(2)),
        width: Number(rect.width.toFixed(2)),
        height: Number(rect.height.toFixed(2))
      },
      scoreText: scoreNode ? normalize(scoreNode.innerText || scoreNode.textContent) : '',
      insert: insertNode ? {
        tag: insertNode.tagName.toLowerCase(),
        className: normalize(insertNode.className),
        text: normalize(insertNode.innerText || insertNode.textContent),
        path: makePath(insertNode),
        rect: (() => {
          const r = insertNode.getBoundingClientRect();
          return {
            x: Number(r.x.toFixed(2)),
            y: Number(r.y.toFixed(2)),
            width: Number(r.width.toFixed(2)),
            height: Number(r.height.toFixed(2))
          };
        })()
      } : null
    });
  }

  const insertButtons = Array.from(dialog.querySelectorAll('button, a, div, span'))
    .filter((node) => isVisible(node) && normalize(node.innerText || node.textContent) === '插入')
    .map((node) => {
      const rect = node.getBoundingClientRect();
      return {
        tag: node.tagName.toLowerCase(),
        className: normalize(node.className),
        text: normalize(node.innerText || node.textContent),
        path: makePath(node),
        rect: {
          x: Number(rect.x.toFixed(2)),
          y: Number(rect.y.toFixed(2)),
          width: Number(rect.width.toFixed(2)),
          height: Number(rect.height.toFixed(2))
        }
      };
    });

  return {
    found: true,
    candidateCount: candidates.length,
    candidates,
    insertButtons
  };
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
            results = observe_results(page)
            print(f"Editor tab title: {page.title()}")
            print(f"Editor tab url: {page.url}")
            print(json.dumps(results, ensure_ascii=False, indent=2))
        finally:
            browser.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Reuse the currently open WeChat editor tab after AI cover generation,
hover the first main generated image, and inspect whether a "使用" button appears.
"""

from __future__ import annotations

import json
import logging
import random
from urllib.request import urlopen

from playwright.sync_api import Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
EDITOR_URL_KEYWORD = "media/appmsg_edit"
FIRST_RESULT_IMAGE_SELECTOR = (
    "div.ai_image_dialog div.main_chat_area div.ai-image-list "
    "div.ai-image-item.r235-1:nth-of-type(1) img"
)


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


def wait_with_jitter(page: Page, base_seconds: float, reason: str) -> None:
    actual_seconds = max(0.0, base_seconds + random.uniform(-0.5, 0.5))
    logging.info("Waiting %.2fs for %s", actual_seconds, reason)
    page.wait_for_timeout(actual_seconds * 1000)


def random_point_in_center_band(box: dict[str, float]) -> tuple[float, float, float, float]:
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2
    point_x = center_x + random.uniform(-box["width"] / 8, box["width"] / 8)
    point_y = center_y + random.uniform(-box["height"] / 8, box["height"] / 8)
    return center_x, center_y, point_x, point_y


def observe_use_candidates(page: Page) -> list[dict[str, object]]:
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
    return [];
  }
  const nodes = Array.from(dialog.querySelectorAll('button, a, div, span'));
  const results = [];
  for (const el of nodes) {
    const text = normalize(el.innerText || el.textContent || el.getAttribute('title') || el.getAttribute('aria-label'));
    if (text !== '使用') {
      continue;
    }
    const rect = el.getBoundingClientRect();
    results.push({
      tag: el.tagName.toLowerCase(),
      className: normalize(el.className),
      text,
      visible: isVisible(el),
      rect: {
        x: Number(rect.x.toFixed(2)),
        y: Number(rect.y.toFixed(2)),
        width: Number(rect.width.toFixed(2)),
        height: Number(rect.height.toFixed(2))
      },
      path: makePath(el)
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

            locator = page.locator(FIRST_RESULT_IMAGE_SELECTOR).first
            locator.wait_for(state="visible", timeout=10 * 1000)
            box = locator.bounding_box()
            if not box:
                raise RuntimeError("First AI result image was found but had no bounding box.")
            center_x, center_y, hover_x, hover_y = random_point_in_center_band(box)
            before_candidates = observe_use_candidates(page)
            wait_with_jitter(page, 1.0, "pre-hover pause")
            page.mouse.move(hover_x, hover_y)
            page.wait_for_timeout(1200)
            after_candidates = observe_use_candidates(page)

            print(f"Editor tab title: {page.title()}")
            print(f"Editor tab url: {page.url}")
            print(f"First result selector: {FIRST_RESULT_IMAGE_SELECTOR}")
            print(
                f"Image box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
            )
            print(f"Hover center: x={center_x:.2f}, y={center_y:.2f}")
            print(f"Actual hover: x={hover_x:.2f}, y={hover_y:.2f}")
            print("Use candidates before hover:")
            print(json.dumps(before_candidates, ensure_ascii=False, indent=2))
            print("Use candidates after hover:")
            print(json.dumps(after_candidates, ensure_ascii=False, indent=2))
        finally:
            browser.close()


if __name__ == "__main__":
    main()

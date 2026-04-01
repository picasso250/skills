#!/usr/bin/env python3
"""
Reuse the currently open WeChat editor tab with the AI cover dialog ready,
and physically click the "开始创作" button.
"""

from __future__ import annotations

import json
import logging
import random
from urllib.request import urlopen

from playwright.sync_api import Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
EDITOR_URL_KEYWORD = "media/appmsg_edit"
START_BUTTON_SELECTOR = (
    "div.ai_image_dialog div.ft_chat_area div.chat_combine "
    "button.weui-desktop-btn.weui-desktop-btn_primary"
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


def describe_generation_state(page: Page) -> dict[str, object]:
    return page.evaluate(
        """
() => {
  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
  const keywords = ['开始创作', '创作中', '重新创作', '使用图片', '选择图片'];
  const nodes = Array.from(document.querySelectorAll('button, a, div, span'));
  const visible = [];
  for (const el of nodes) {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || rect.width <= 0 || rect.height <= 0) {
      continue;
    }
    const text = normalize(el.innerText || el.textContent || el.getAttribute('title') || el.getAttribute('aria-label'));
    if (!keywords.some((keyword) => text.includes(keyword))) {
      continue;
    }
    visible.push({
      tag: el.tagName.toLowerCase(),
      className: normalize(el.className),
      text,
      rect: {
        x: Number(rect.x.toFixed(2)),
        y: Number(rect.y.toFixed(2)),
        width: Number(rect.width.toFixed(2)),
        height: Number(rect.height.toFixed(2))
      }
    });
  }
  return visible;
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
            locator = page.locator(START_BUTTON_SELECTOR).filter(has_text="开始创作").first
            locator.wait_for(state="visible", timeout=10 * 1000)
            box = locator.bounding_box()
            if not box:
                raise RuntimeError("Start button was found but had no bounding box.")
            center_x, center_y, click_x, click_y = random_point_in_center_band(box)
            before_state = describe_generation_state(page)
            wait_with_jitter(page, 1.0, "pre-click pause")
            page.mouse.click(click_x, click_y)
            page.wait_for_timeout(1500)
            after_state = describe_generation_state(page)
            print(f"Editor tab title: {page.title()}")
            print(f"Editor tab url: {page.url}")
            print(f"Start selector: {START_BUTTON_SELECTOR}")
            print(
                f"Button box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
            )
            print(f"Click center: x={center_x:.2f}, y={center_y:.2f}")
            print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
            print("Generation state before:")
            print(json.dumps(before_state, ensure_ascii=False, indent=2))
            print("Generation state after:")
            print(json.dumps(after_state, ensure_ascii=False, indent=2))
        finally:
            browser.close()


if __name__ == "__main__":
    main()

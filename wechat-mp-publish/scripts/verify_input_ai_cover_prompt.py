#!/usr/bin/env python3
"""
Reuse the currently open WeChat editor tab with the AI cover dialog visible,
physically type into the AI prompt textarea, and inspect whether the
"开始创作" button becomes enabled.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from urllib.request import urlopen

from playwright.sync_api import Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
EDITOR_URL_KEYWORD = "media/appmsg_edit"
PROMPT_SELECTOR = "textarea#ai-image-prompt.chat_textarea"
START_BUTTON_SELECTOR = "button.weui-desktop-btn.weui-desktop-btn_primary"
DEFAULT_PROMPT_TEXT = "科技感十足的未来 AI 指挥官在控制台前工作，明亮、简洁、适合作为公众号封面。"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Type a prompt into the AI cover dialog and inspect the start button state."
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT_TEXT, help="Prompt text for the AI cover dialog.")
    return parser.parse_args()


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


def type_like_human(page: Page, text: str) -> None:
    for char in text:
        page.wait_for_timeout(random.uniform(0.1, 0.2) * 1000)
        if char == "\n":
            page.keyboard.press("Enter")
        else:
            page.keyboard.type(char)
        page.wait_for_timeout(random.uniform(0.1, 0.2) * 1000)


def random_point_in_center_band(box: dict[str, float]) -> tuple[float, float, float, float]:
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2
    point_x = center_x + random.uniform(-box["width"] / 8, box["width"] / 8)
    point_y = center_y + random.uniform(-box["height"] / 8, box["height"] / 8)
    return center_x, center_y, point_x, point_y


def describe_start_button(page: Page) -> dict[str, object]:
    return page.evaluate(
        f"""
() => {{
  const el = document.querySelector({json.dumps(START_BUTTON_SELECTOR)});
  if (!el) {{
    return {{"found": false}};
  }}
  const rect = el.getBoundingClientRect();
  return {{
    found: true,
    text: (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim(),
    className: (el.className || '').replace(/\\s+/g, ' ').trim(),
    disabledAttr: el.hasAttribute('disabled'),
    ariaDisabled: el.getAttribute('aria-disabled') || '',
    rect: {{
      x: Number(rect.x.toFixed(2)),
      y: Number(rect.y.toFixed(2)),
      width: Number(rect.width.toFixed(2)),
      height: Number(rect.height.toFixed(2))
    }}
  }};
}}
"""
    )


def main() -> None:
    args = parse_args()
    setup_logging()
    browser_ws = resolve_browser_ws_endpoint(DEFAULT_CDP_URL)
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(browser_ws)
        try:
            page = find_editor_page(browser)
            logging.info("Reusing editor tab: %s", page.url)
            page.bring_to_front()

            prompt_locator = page.locator(PROMPT_SELECTOR).first
            prompt_locator.wait_for(state="visible", timeout=10 * 1000)
            prompt_box = prompt_locator.bounding_box()
            if not prompt_box:
                raise RuntimeError("AI prompt textarea was found but had no bounding box.")
            center_x, center_y, click_x, click_y = random_point_in_center_band(prompt_box)
            before_value = prompt_locator.input_value()
            before_button = describe_start_button(page)

            wait_with_jitter(page, 1.0, "pre-focus pause")
            page.mouse.click(click_x, click_y)
            page.wait_for_timeout(200)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            type_like_human(page, args.prompt)
            page.wait_for_timeout(300)

            after_value = prompt_locator.input_value()
            after_button = describe_start_button(page)

            print(f"Editor tab title: {page.title()}")
            print(f"Editor tab url: {page.url}")
            print(f"Prompt selector: {PROMPT_SELECTOR}")
            print(
                f"Prompt box: x={prompt_box['x']:.2f}, y={prompt_box['y']:.2f}, width={prompt_box['width']:.2f}, height={prompt_box['height']:.2f}"
            )
            print(f"Click center: x={center_x:.2f}, y={center_y:.2f}")
            print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
            print(f"Prompt before: {before_value!r}")
            print(f"Prompt after: {after_value!r}")
            print("Start button before:")
            print(json.dumps(before_button, ensure_ascii=False, indent=2))
            print("Start button after:")
            print(json.dumps(after_button, ensure_ascii=False, indent=2))
        finally:
            browser.close()


if __name__ == "__main__":
    main()

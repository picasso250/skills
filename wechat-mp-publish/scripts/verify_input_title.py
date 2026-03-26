#!/usr/bin/env python3
"""
Reuse the WeChat article-editor tab and physically type into the title field.
"""

from __future__ import annotations

import json
import logging
import random
import sys
from urllib.request import urlopen

from playwright.sync_api import Error, Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
EDITOR_URL_KEYWORD = "media/appmsg_edit"
TITLE_SELECTOR = "#title"
TITLE_TEXT = "验证标题123"


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


def wait_with_jitter(page: Page, base_seconds: float, reason: str) -> None:
    actual_seconds = max(0.0, base_seconds + random.uniform(-0.5, 0.5))
    logging.info("Waiting %.2fs for %s", actual_seconds, reason)
    page.wait_for_timeout(actual_seconds * 1000)


def type_like_human(page: Page, text: str) -> None:
    for char in text:
        page.wait_for_timeout(random.uniform(0.1, 0.2) * 1000)
        page.keyboard.type(char)
        page.wait_for_timeout(random.uniform(0.1, 0.2) * 1000)


def random_point_in_center_band(box: dict[str, float]) -> tuple[float, float, float, float]:
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2
    point_x = center_x + random.uniform(-box["width"] / 8, box["width"] / 8)
    point_y = center_y + random.uniform(-box["height"] / 8, box["height"] / 8)
    return center_x, center_y, point_x, point_y


def find_editor_page(browser) -> Page:
    for context in browser.contexts:
        for page in context.pages:
            if EDITOR_URL_KEYWORD in page.url:
                return page
    raise RuntimeError("No open editor page matched the article editor tab.")


def main() -> None:
    setup_logging()

    try:
        browser_ws = resolve_browser_ws_endpoint(DEFAULT_CDP_URL)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(browser_ws)
            try:
                page = find_editor_page(browser)
                logging.info("Reusing editor tab: %s", page.url)
                page.bring_to_front()
                locator = page.locator(TITLE_SELECTOR)
                locator.wait_for(state="visible", timeout=10 * 1000)
                box = locator.bounding_box()
                if not box:
                    raise RuntimeError("Title field was found but had no bounding box.")
                center_x, center_y, click_x, click_y = random_point_in_center_band(box)
                before_value = locator.input_value()
                wait_with_jitter(page, 1.0, "pre-focus pause")
                page.mouse.click(click_x, click_y)
                page.wait_for_timeout(200)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                type_like_human(page, TITLE_TEXT)
                page.wait_for_timeout(300)
                after_value = locator.input_value()
                print(f"Editor tab title: {page.title()}")
                print(f"Editor tab url: {page.url}")
                print(f"Title selector: {TITLE_SELECTOR}")
                print(
                    f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
                )
                print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
                print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
                print(f"Value before: {before_value!r}")
                print(f"Value after: {after_value!r}")
            finally:
                browser.close()
    except Error as exc:
        logging.error("Failed while typing title in the reused editor tab: %s", exc)
        sys.exit(1)
    except OSError as exc:
        logging.error("Failed to reach Chrome DevTools: %s", exc)
        sys.exit(1)
    except RuntimeError as exc:
        logging.error("%s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        logging.warning("Interrupted by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()

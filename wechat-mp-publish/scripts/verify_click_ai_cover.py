#!/usr/bin/env python3
"""
Reuse the WeChat article-editor tab, hover the cover area, and click the
"AI 配图" entry without handling any subsequent dialog.
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
COVER_SELECTOR = "div#js_cover_area div.select-cover__btn.js_cover_btn_area.select-cover__mask"
AI_IMAGE_SELECTOR = "div#js_cover_null a.pop-opr__button.js_aiImage"


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

                cover_locator = page.locator(COVER_SELECTOR).first
                cover_locator.wait_for(state="visible", timeout=10 * 1000)
                cover_box = cover_locator.bounding_box()
                if not cover_box:
                    raise RuntimeError("Cover control was found but had no bounding box.")
                cover_center_x, cover_center_y, hover_x, hover_y = random_point_in_center_band(cover_box)
                wait_with_jitter(page, 1.0, "pre-hover pause")
                page.mouse.move(hover_x, hover_y)
                page.wait_for_timeout(800)

                ai_locator = page.locator(AI_IMAGE_SELECTOR).first
                ai_locator.wait_for(state="visible", timeout=10 * 1000)
                ai_box = ai_locator.bounding_box()
                if not ai_box:
                    raise RuntimeError("AI image entry was found but had no bounding box.")
                ai_center_x, ai_center_y, click_x, click_y = random_point_in_center_band(ai_box)
                wait_with_jitter(page, 1.0, "pre-click pause")
                page.mouse.click(click_x, click_y)
                page.wait_for_timeout(1200)

                print(f"Editor tab title: {page.title()}")
                print(f"Editor tab url: {page.url}")
                print(f"Cover selector: {COVER_SELECTOR}")
                print(
                    f"Cover box: x={cover_box['x']:.2f}, y={cover_box['y']:.2f}, width={cover_box['width']:.2f}, height={cover_box['height']:.2f}"
                )
                print(f"Hover center: x={cover_center_x:.2f}, y={cover_center_y:.2f}")
                print(f"Actual hover: x={hover_x:.2f}, y={hover_y:.2f}")
                print(f"AI selector: {AI_IMAGE_SELECTOR}")
                print(
                    f"AI box: x={ai_box['x']:.2f}, y={ai_box['y']:.2f}, width={ai_box['width']:.2f}, height={ai_box['height']:.2f}"
                )
                print(f"Click center: x={ai_center_x:.2f}, y={ai_center_y:.2f}")
                print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
            finally:
                browser.close()
    except Error as exc:
        logging.error("Failed while clicking AI cover entry: %s", exc)
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

#!/usr/bin/env python3
"""
Reuse the WeChat article-editor tab and complete the unset-original confirmation flow.
"""

from __future__ import annotations

import json
import logging
import random
import sys
from urllib.request import urlopen

from playwright.sync_api import Error, Locator, Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
EDITOR_URL_KEYWORD = "media/appmsg_edit"
UNSET_TEXT = "未声明"
AGREE_TEXT = "我已阅读并同意"
CONFIRM_TEXT = "确定"
AUTHOR_TEXT = "验证作者"
DECLARE_AUTHOR_SELECTOR = "input.frm_input.js_counter.js_author"
AGREE_LABEL_SELECTOR = "label.weui-desktop-form__check-label"


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


def find_editor_page(browser) -> Page:
    for context in browser.contexts:
        for page in context.pages:
            if EDITOR_URL_KEYWORD in page.url:
                return page
    raise RuntimeError("No open editor page matched the article editor tab.")


def click_locator(page: Page, locator: Locator, label: str) -> None:
    locator.wait_for(state="visible", timeout=10 * 1000)
    box = locator.bounding_box()
    if not box:
        raise RuntimeError(f"{label} was found but had no bounding box.")
    center_x, center_y, click_x, click_y = random_point_in_center_band(box)
    wait_with_jitter(page, 1.0, f"pre-click pause for {label}")
    page.mouse.click(click_x, click_y)
    print(f"{label} center: x={center_x:.2f}, y={center_y:.2f}")
    print(f"{label} click: x={click_x:.2f}, y={click_y:.2f}")


def find_author_locator(page: Page) -> Locator:
    candidates = [
        page.locator(DECLARE_AUTHOR_SELECTOR),
        page.locator("span.js_customerauthor_container input.frm_input.js_counter.js_author"),
        page.locator("div.original_edit_inner_box input[placeholder*='作者']"),
    ]
    for locator in candidates:
        if locator.count() and locator.first.is_visible():
            return locator.first
    raise RuntimeError("Could not find a visible author input for the declaration flow.")


def type_into_locator(page: Page, locator: Locator, label: str, text: str) -> None:
    locator.wait_for(state="visible", timeout=10 * 1000)
    box = locator.bounding_box()
    if not box:
        raise RuntimeError(f"{label} was found but had no bounding box.")
    center_x, center_y, click_x, click_y = random_point_in_center_band(box)
    before_value = locator.input_value()
    wait_with_jitter(page, 1.0, f"pre-focus pause for {label}")
    page.mouse.click(click_x, click_y)
    page.wait_for_timeout(200)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    type_like_human(page, text)
    page.wait_for_timeout(300)
    after_value = locator.input_value()
    print(f"{label} center: x={center_x:.2f}, y={center_y:.2f}")
    print(f"{label} click: x={click_x:.2f}, y={click_y:.2f}")
    print(f"{label} before: {before_value!r}")
    print(f"{label} after: {after_value!r}")


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

                unset_locator = page.get_by_text(UNSET_TEXT, exact=True).first
                click_locator(page, unset_locator, UNSET_TEXT)
                page.wait_for_timeout(1200)

                author_locator = find_author_locator(page)
                type_into_locator(page, author_locator, "author", AUTHOR_TEXT)

                agree_locator = page.locator(AGREE_LABEL_SELECTOR).filter(has_text=AGREE_TEXT).first
                click_locator(page, agree_locator, AGREE_TEXT)
                page.wait_for_timeout(600)

                confirm_locator = page.get_by_text(CONFIRM_TEXT, exact=True).first
                click_locator(page, confirm_locator, CONFIRM_TEXT)
                page.wait_for_timeout(1200)

                print(f"Editor tab title: {page.title()}")
                print(f"Editor tab url: {page.url}")
            finally:
                browser.close()
    except Error as exc:
        logging.error("Failed while completing the declaration flow: %s", exc)
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

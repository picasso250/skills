#!/usr/bin/env python3
"""
Starter CLI for the WeChat MP publish skill.

This remains intentionally small at first. Approved validation steps will be
merged into this script incrementally.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import Error, Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_HOME_URL = "https://mp.weixin.qq.com/cgi-bin/home?t=home/index&token=564490041&lang=zh_CN"
CONTENT_MANAGEMENT_TEXT = "内容管理"
DRAFT_BOX_TEXT = "草稿箱"
NEW_CREATION_TEXT = "新的创作"
WRITE_NEW_ARTICLE_TEXT = "写新文章"
TITLE_SELECTOR = "#title"
TITLE_TEXT = "验证标题123"
AUTHOR_SELECTOR = "#author"
AUTHOR_TEXT = "验证作者"
BODY_SELECTOR = "div.ProseMirror"
BODY_TEXT = "这是验证正文。\n第二行正文。"
PUBLISH_TEXT = "发表"
GO_DECLARE_TEXT = "去声明"
UNSET_TEXT = "未声明"
DECLARE_AUTHOR_SELECTOR = "div#js_original_edit_box input.frm_input.js_counter.js_author"
DECLARE_CHECKBOX_SELECTOR = "div.claim__original-dialog.original_dialog i.weui-desktop-icon-checkbox"
DECLARE_CONFIRM_SELECTOR = "div.claim__original-dialog.original_dialog button.weui-desktop-btn.weui-desktop-btn_primary"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fixed WeChat Official Accounts publishing flow."
    )
    return parser.parse_args()


def fetch_devtools_targets(cdp_url: str) -> list[dict[str, object]]:
    list_url = f"{cdp_url.rstrip('/')}/json/list"
    with urlopen(list_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected JSON from {list_url}")
    return payload


def fetch_page_targets(cdp_url: str) -> list[dict[str, Any]]:
    return [target for target in fetch_devtools_targets(cdp_url) if target.get("type") == "page"]


def resolve_ws_endpoint(cdp_url: str) -> str:
    version_url = f"{cdp_url.rstrip('/')}/json/version"
    with urlopen(version_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    ws_endpoint = payload.get("webSocketDebuggerUrl")
    if not ws_endpoint:
        raise RuntimeError(f"Missing webSocketDebuggerUrl in {version_url}")
    return ws_endpoint


def randomized_wait_seconds(base_seconds: float) -> float:
    return max(0.0, base_seconds + random.uniform(-0.5, 0.5))


def wait_with_jitter(page: Page, base_seconds: float, reason: str) -> None:
    actual_seconds = randomized_wait_seconds(base_seconds)
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


def open_home(context) -> Page:
    page = context.new_page()
    page.set_default_timeout(30 * 1000)
    logging.info("Opening WeChat MP home tab: %s", DEFAULT_HOME_URL)
    page.goto(DEFAULT_HOME_URL, wait_until="domcontentloaded")
    wait_with_jitter(page, 5.0, "initial page stabilization")
    print(f"Opened tab title: {page.title()}")
    print(f"Opened tab url: {page.url}")
    return page


def click_text_and_record_url_change(page: Page, target_text: str) -> None:
    locator = page.get_by_text(target_text, exact=False).first
    locator.wait_for(state="visible", timeout=10 * 1000)
    box = locator.bounding_box()
    if not box:
        raise RuntimeError(f"Found text but no bounding box: {target_text}")
    center_x, center_y, click_x, click_y = random_point_in_center_band(box)
    before_url = page.url
    wait_with_jitter(page, 1.0, "pre-click pause")
    page.mouse.click(click_x, click_y)
    wait_with_jitter(page, 1.0, "post-click url settle")
    after_url = page.url
    print(f"Found text: {target_text}")
    print(
        f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
    )
    print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
    print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
    print(f"URL before click: {before_url}")
    print(f"URL after click: {after_url}")
    print(f"URL changed: {'yes' if before_url != after_url else 'no'}")
    print(f"Post-click title: {page.title()}")
    print(f"Post-click url: {after_url}")


def hover_text(page: Page, target_text: str) -> None:
    locator = page.get_by_text(target_text, exact=False).first
    locator.wait_for(state="visible", timeout=10 * 1000)
    box = locator.bounding_box()
    if not box:
        raise RuntimeError(f"Found text but no bounding box: {target_text}")
    center_x, center_y, hover_x, hover_y = random_point_in_center_band(box)
    wait_with_jitter(page, 1.0, "pre-hover pause")
    page.mouse.move(hover_x, hover_y)
    page.wait_for_timeout(300)
    print(f"Found text: {target_text}")
    print(
        f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
    )
    print(f"Hover center: x={center_x:.2f}, y={center_y:.2f}")
    print(f"Actual hover: x={hover_x:.2f}, y={hover_y:.2f}")


def type_into_field(page: Page, selector: str, text: str, tab_after: bool = True) -> None:
    locator = page.locator(selector)
    locator.wait_for(state="visible", timeout=10 * 1000)
    box = locator.bounding_box()
    if not box:
        raise RuntimeError(f"Field was found but had no bounding box: {selector}")
    center_x, center_y, click_x, click_y = random_point_in_center_band(box)
    before_value = locator.input_value()
    wait_with_jitter(page, 1.0, "pre-focus pause")
    page.mouse.click(click_x, click_y)
    page.wait_for_timeout(200)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    type_like_human(page, text)
    if tab_after:
        page.wait_for_timeout(150)
        page.keyboard.press("Tab")
    page.wait_for_timeout(300)
    after_value = locator.input_value()
    print(f"Field selector: {selector}")
    print(
        f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
    )
    print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
    print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
    print(f"Value before: {before_value!r}")
    print(f"Value after: {after_value!r}")


def type_into_body(page: Page, selector: str, text: str) -> None:
    locator = page.locator(selector)
    locator.wait_for(state="visible", timeout=10 * 1000)
    box = locator.bounding_box()
    if not box:
        raise RuntimeError(f"Body editor was found but had no bounding box: {selector}")
    center_x, center_y, click_x, click_y = random_point_in_center_band(box)
    before_text = locator.inner_text()
    wait_with_jitter(page, 1.0, "pre-focus pause")
    page.mouse.click(click_x, click_y)
    page.wait_for_timeout(200)
    type_like_human(page, text)
    page.wait_for_timeout(300)
    after_text = locator.inner_text()
    print(f"Body selector: {selector}")
    print(
        f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
    )
    print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
    print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
    print(f"Text before: {before_text!r}")
    print(f"Text after: {after_text!r}")


def click_text_and_capture_new_page(
    page: Page, cdp_url: str, target_text: str
) -> dict[str, Any] | None:
    locator = page.get_by_text(target_text, exact=False).first
    locator.wait_for(state="visible", timeout=10 * 1000)
    box = locator.bounding_box()
    if not box:
        raise RuntimeError(f"Found text but no bounding box: {target_text}")
    center_x, center_y, click_x, click_y = random_point_in_center_band(box)
    before_targets = fetch_page_targets(cdp_url)
    before_url = page.url
    wait_with_jitter(page, 1.0, "pre-click pause")
    page.mouse.click(click_x, click_y)
    wait_with_jitter(page, 5.0, "post-click new-tab settle")
    after_targets = fetch_page_targets(cdp_url)
    before_ws_set = {
        str(target.get("webSocketDebuggerUrl") or target.get("webSocketUrl") or "")
        for target in before_targets
    }
    new_targets = [
        target
        for target in after_targets
        if str(target.get("webSocketDebuggerUrl") or target.get("webSocketUrl") or "")
        not in before_ws_set
    ]

    print(f"Found text: {target_text}")
    print(
        f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
    )
    print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
    print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
    print(f"URL before click: {before_url}")
    print(f"Page targets before click: {len(before_targets)}")
    print(f"Page targets after click: {len(after_targets)}")
    print(f"New page targets found: {len(new_targets)}")

    if not new_targets:
        print("New tab detected: no")
        return None

    new_target = new_targets[0]
    print("New tab detected: yes")
    print(f"New tab title: {new_target.get('title', '<untitled>')}")
    print(f"New tab url: {new_target.get('url', '<no url>')}")
    print(
        "New tab wsEndpoint: "
        f"{new_target.get('webSocketDebuggerUrl') or new_target.get('webSocketUrl') or '<not found>'}"
    )
    return new_target


def click_text_and_wait(page: Page, target_text: str, wait_seconds: float) -> None:
    locator = page.get_by_text(target_text, exact=True).first
    locator.wait_for(state="visible", timeout=10 * 1000)
    box = locator.bounding_box()
    if not box:
        raise RuntimeError(f"Found text but no bounding box: {target_text}")
    center_x, center_y, click_x, click_y = random_point_in_center_band(box)
    before_url = page.url
    wait_with_jitter(page, 1.0, "pre-click pause")
    page.mouse.click(click_x, click_y)
    page.wait_for_timeout(wait_seconds * 1000)
    print(f"Found text: {target_text}")
    print(
        f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
    )
    print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
    print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
    print(f"URL before click: {before_url}")
    print(f"URL after wait: {page.url}")


def click_selector_and_wait(page: Page, selector: str, wait_seconds: float) -> None:
    locator = page.locator(selector).first
    locator.wait_for(state="visible", timeout=10 * 1000)
    box = locator.bounding_box()
    if not box:
        raise RuntimeError(f"Found selector but no bounding box: {selector}")
    center_x, center_y, click_x, click_y = random_point_in_center_band(box)
    before_url = page.url
    wait_with_jitter(page, 1.0, "pre-click pause")
    page.mouse.click(click_x, click_y)
    page.wait_for_timeout(wait_seconds * 1000)
    print(f"Selector: {selector}")
    print(
        f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
    )
    print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
    print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
    print(f"URL before click: {before_url}")
    print(f"URL after wait: {page.url}")


def main() -> None:
    setup_logging()
    parse_args()

    try:
        ws_endpoint = resolve_ws_endpoint(DEFAULT_CDP_URL)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(ws_endpoint)
            try:
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = open_home(context)
                click_text_and_record_url_change(page, CONTENT_MANAGEMENT_TEXT)
                click_text_and_record_url_change(page, DRAFT_BOX_TEXT)
                hover_text(page, NEW_CREATION_TEXT)
                new_target = click_text_and_capture_new_page(page, DEFAULT_CDP_URL, WRITE_NEW_ARTICLE_TEXT)
                if new_target and new_target.get("url"):
                    page.goto(str(new_target["url"]), wait_until="domcontentloaded")
                    wait_with_jitter(page, 5.0, "editor page stabilization")
                    type_into_field(page, TITLE_SELECTOR, TITLE_TEXT)
                    type_into_field(page, AUTHOR_SELECTOR, AUTHOR_TEXT)
                    type_into_body(page, BODY_SELECTOR, BODY_TEXT)
                    click_text_and_wait(page, PUBLISH_TEXT, 2.5)
                    click_text_and_wait(page, GO_DECLARE_TEXT, 1.5)
                    click_text_and_wait(page, UNSET_TEXT, 1.2)
                    type_into_field(page, DECLARE_AUTHOR_SELECTOR, AUTHOR_TEXT)
                    click_selector_and_wait(page, DECLARE_CHECKBOX_SELECTOR, 0.5)
                    click_selector_and_wait(page, DECLARE_CONFIRM_SELECTOR, 1.2)
            finally:
                browser.close()
    except Error as exc:
        logging.error("Failed to run WeChat MP publish starter: %s", exc)
        sys.exit(1)
    except URLError as exc:
        logging.error("Failed to reach Chrome DevTools: %s", exc)
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

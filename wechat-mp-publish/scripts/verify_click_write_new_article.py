#!/usr/bin/env python3
"""
Reuse an existing WeChat MP tab, find "写新文章", and click near its center.
"""

from __future__ import annotations

import json
import logging
import random
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import Error, Page, TimeoutError, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
TARGET_HOST = "mp.weixin.qq.com"
NEW_CREATION_TEXT = "新的创作"
TARGET_TEXT = "写新文章"
TIMEOUT_SECONDS = 10


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def resolve_ws_endpoint(cdp_url: str) -> str:
    version_url = f"{cdp_url.rstrip('/')}/json/version"
    with urlopen(version_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    ws_endpoint = payload.get("webSocketDebuggerUrl")
    if not ws_endpoint:
        raise RuntimeError(f"Missing webSocketDebuggerUrl in {version_url}")
    return ws_endpoint


def fetch_devtools_targets(cdp_url: str) -> list[dict[str, Any]]:
    list_url = f"{cdp_url.rstrip('/')}/json/list"
    with urlopen(list_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected JSON from {list_url}")
    return payload


def fetch_page_targets(cdp_url: str) -> list[dict[str, Any]]:
    return [target for target in fetch_devtools_targets(cdp_url) if target.get("type") == "page"]


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


def find_page_with_text(browser, target_text: str) -> Page:
    candidate_pages: list[Page] = []
    for context in browser.contexts:
        for page in context.pages:
            if TARGET_HOST in page.url:
                candidate_pages.append(page)

    for page in candidate_pages:
        try:
            page.get_by_text(target_text, exact=False).first.wait_for(
                state="visible", timeout=1500
            )
            return page
        except TimeoutError:
            continue

    raise RuntimeError(f'No open WeChat MP tab contained visible text: {target_text}')


def find_page_with_any_text(browser, texts: list[str]) -> Page:
    candidate_pages: list[Page] = []
    for context in browser.contexts:
        for page in context.pages:
            if TARGET_HOST in page.url:
                candidate_pages.append(page)

    for page in candidate_pages:
        for text in texts:
            try:
                page.get_by_text(text, exact=False).first.wait_for(
                    state="visible", timeout=1000
                )
                return page
            except TimeoutError:
                continue

    raise RuntimeError(f"No open WeChat MP tab matched any visible text: {texts}")


def main() -> None:
    setup_logging()

    try:
        ws_endpoint = resolve_ws_endpoint(DEFAULT_CDP_URL)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(ws_endpoint)
            try:
                page = find_page_with_any_text(browser, [TARGET_TEXT, NEW_CREATION_TEXT])
                logging.info("Reusing tab: %s", page.url)
                page.bring_to_front()
                trigger = page.get_by_text(NEW_CREATION_TEXT, exact=False).first
                trigger.wait_for(state="visible", timeout=TIMEOUT_SECONDS * 1000)
                trigger_box = trigger.bounding_box()
                if not trigger_box:
                    raise RuntimeError(f"Found text but no bounding box: {NEW_CREATION_TEXT}")
                _, _, hover_x, hover_y = random_point_in_center_band(trigger_box)
                wait_with_jitter(page, 1.0, "pre-hover pause")
                page.mouse.move(hover_x, hover_y)
                page.wait_for_timeout(300)
                locator = page.get_by_text(TARGET_TEXT, exact=False).first
                locator.wait_for(state="visible", timeout=TIMEOUT_SECONDS * 1000)
                box = locator.bounding_box()
                if not box:
                    raise RuntimeError(f"Found text but no bounding box: {TARGET_TEXT}")
                center_x, center_y, click_x, click_y = random_point_in_center_band(box)
                before_targets = fetch_page_targets(DEFAULT_CDP_URL)
                before_url = page.url
                wait_with_jitter(page, 1.0, "pre-click pause")
                page.mouse.click(click_x, click_y)
                wait_with_jitter(page, 5.0, "post-click new-tab settle")
                after_targets = fetch_page_targets(DEFAULT_CDP_URL)
                after_url = page.url
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
                print(f"Matched tab title: {page.title()}")
                print(f"Matched tab url: {before_url}")
                print(f"Found text: {TARGET_TEXT}")
                print(
                    f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
                )
                print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
                print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
                print(f"URL before click: {before_url}")
                print(f"URL after click: {after_url}")
                print(f"URL changed: {'yes' if before_url != after_url else 'no'}")
                print(f"Page targets before click: {len(before_targets)}")
                print(f"Page targets after click: {len(after_targets)}")
                print(f"New page targets found: {len(new_targets)}")
                if new_targets:
                    new_target = new_targets[0]
                    print(f"New tab title: {new_target.get('title', '<untitled>')}")
                    print(f"New tab url: {new_target.get('url', '<no url>')}")
                    print(
                        "New tab wsEndpoint: "
                        f"{new_target.get('webSocketDebuggerUrl') or new_target.get('webSocketUrl') or '<no ws>'}"
                    )
                print(f"Post-click title: {page.title()}")
                print(f"Post-click url: {after_url}")
            finally:
                browser.close()
    except Error as exc:
        logging.error("Failed while clicking on the reused tab: %s", exc)
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

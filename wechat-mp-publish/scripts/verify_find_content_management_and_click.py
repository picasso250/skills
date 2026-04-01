#!/usr/bin/env python3
"""
Reuse an existing WeChat MP tab, find "内容管理", and click near its center.
"""

from __future__ import annotations

import json
import logging
import random
import sys
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import Error, Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
HOME_URL_PREFIX = "https://mp.weixin.qq.com/cgi-bin/home?"
TARGET_TEXT = "内容管理"
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


def find_home_page(browser) -> Page:
    for context in browser.contexts:
        for page in context.pages:
            if page.url.startswith(HOME_URL_PREFIX):
                return page
    raise RuntimeError(f"No open tab matched home page prefix: {HOME_URL_PREFIX}")


def main() -> None:
    setup_logging()

    try:
        ws_endpoint = resolve_ws_endpoint(DEFAULT_CDP_URL)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(ws_endpoint)
            try:
                page = find_home_page(browser)
                logging.info("Reusing tab: %s", page.url)
                page.bring_to_front()
                locator = page.get_by_text(TARGET_TEXT, exact=False).first
                locator.wait_for(state="visible", timeout=TIMEOUT_SECONDS * 1000)
                box = locator.bounding_box()
                if not box:
                    raise RuntimeError(f"Found text but no bounding box: {TARGET_TEXT}")
                center_x = box["x"] + box["width"] / 2
                center_y = box["y"] + box["height"] / 2
                click_x = center_x + random.uniform(-box["width"] / 8, box["width"] / 8)
                click_y = center_y + random.uniform(-box["height"] / 8, box["height"] / 8)
                page.mouse.click(click_x, click_y)
                page.wait_for_timeout(1500)
                print(f"Matched tab title: {page.title()}")
                print(f"Matched tab url: {page.url}")
                print(f"Found text: {TARGET_TEXT}")
                print(f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}")
                print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
                print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
                print(f"Post-click title: {page.title()}")
                print(f"Post-click url: {page.url}")
            finally:
                browser.close()
    except Error as exc:
        logging.error("Failed while checking the reused tab: %s", exc)
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

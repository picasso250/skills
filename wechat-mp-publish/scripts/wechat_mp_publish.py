#!/usr/bin/env python3
"""
Starter CLI for the WeChat MP publish skill.

This remains intentionally small at first. Approved validation steps will be
merged into this script incrementally.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import logging
import random
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import Error, Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_HOME_URL = "https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN"
HOME_URL_PREFIX = "https://mp.weixin.qq.com/cgi-bin/home?"
CONTENT_MANAGEMENT_TEXT = "内容管理"
DRAFT_BOX_TEXT = "草稿箱"
NEW_CREATION_TEXT = "新的创作"
WRITE_NEW_ARTICLE_TEXT = "写新文章"
TITLE_SELECTOR = "#title"
AUTHOR_SELECTOR = "#author"
DEFAULT_AUTHOR_TEXT = "言简"
BODY_SELECTOR = "div.ProseMirror"
COVER_SELECTOR = "div#js_cover_area div.select-cover__btn.js_cover_btn_area.select-cover__mask"
AI_IMAGE_SELECTOR = "div#js_cover_null a.pop-opr__button.js_aiImage"
AI_PROMPT_SELECTOR = "textarea#ai-image-prompt.chat_textarea"
AI_START_BUTTON_SELECTOR = (
    "div.ai_image_dialog div.ft_chat_area div.chat_combine "
    "button.weui-desktop-btn.weui-desktop-btn_primary"
)
PUBLISH_TEXT = "发表"
GO_DECLARE_TEXT = "去声明"
UNSET_TEXT = "未声明"
DECLARE_AUTHOR_SELECTOR = "div#js_original_edit_box input.frm_input.js_counter.js_author"
DECLARE_CHECKBOX_SELECTOR = "div.claim__original-dialog.original_dialog i.weui-desktop-icon-checkbox"
DECLARE_CONFIRM_SELECTOR = "div.claim__original-dialog.original_dialog button.weui-desktop-btn.weui-desktop-btn_primary"
DEFAULT_INPUT_PATH = r"C:\Users\MECHREV\AppData\Local\Temp\md-to-txt-40tycc39.txt"
GMEM_MOVEABLE = 0x0002
CF_UNICODETEXT = 13
DEFAULT_AI_COVER_PROMPT = "科技感十足的未来 AI 指挥官在控制台前工作，明亮、简洁、适合作为公众号封面。"


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
    parser.add_argument("--title", help="Article title to type into the editor.")
    parser.add_argument("--author", default=DEFAULT_AUTHOR_TEXT, help="Article author to type into the editor.")
    parser.add_argument("--content", help="Article body content to type into the editor.")
    parser.add_argument(
        "--input-path",
        default=DEFAULT_INPUT_PATH,
        help="Plain-text article path. First non-empty line becomes the title; the rest becomes the body.",
    )
    return parser.parse_args()


def load_article_text(input_path: str) -> tuple[str, str]:
    article_path = Path(input_path)
    if not article_path.is_file():
        raise RuntimeError(f"Article text file not found: {article_path}")

    raw_text = article_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"Article text file is empty: {article_path}")

    title = normalize_title(lines[0])
    body = "\n".join(lines[1:]).strip()
    if not body:
        body = title

    return title, body


def normalize_title(raw_title: str) -> str:
    title = raw_title.strip()
    if title.startswith("《") and title.endswith("》") and len(title) >= 2:
        return title[1:-1].strip()
    return title


def resolve_article_payload(args: argparse.Namespace) -> tuple[str, str, str]:
    if args.title or args.content:
        if not args.title or not args.content:
            raise RuntimeError("When using direct arguments, both --title and --content are required.")
        return args.title, args.author, args.content

    title, body = load_article_text(args.input_path)
    return title, args.author, body


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


def set_clipboard_text(text: str) -> None:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_int
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.c_int
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_int
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_int
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p
    if not user32.OpenClipboard(None):
        raise RuntimeError("Failed to open Windows clipboard.")
    try:
        if not user32.EmptyClipboard():
            raise RuntimeError("Failed to empty Windows clipboard.")

        text_buffer = text + "\0"
        byte_count = len(text_buffer.encode("utf-16-le"))
        global_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, byte_count)
        if not global_mem:
            raise RuntimeError("GlobalAlloc failed for clipboard text.")

        locked_mem = kernel32.GlobalLock(global_mem)
        if not locked_mem:
            kernel32.GlobalFree(global_mem)
            raise RuntimeError("GlobalLock failed for clipboard text.")

        try:
            ctypes.memmove(locked_mem, text_buffer.encode("utf-16-le"), byte_count)
        finally:
            kernel32.GlobalUnlock(global_mem)

        if not user32.SetClipboardData(CF_UNICODETEXT, global_mem):
            kernel32.GlobalFree(global_mem)
            raise RuntimeError("SetClipboardData failed for Unicode text.")
    finally:
        user32.CloseClipboard()


def random_point_in_center_band(box: dict[str, float]) -> tuple[float, float, float, float]:
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2
    point_x = center_x + random.uniform(-box["width"] / 8, box["width"] / 8)
    point_y = center_y + random.uniform(-box["height"] / 8, box["height"] / 8)
    return center_x, center_y, point_x, point_y


def open_home(context) -> Page:
    for existing_page in context.pages:
        if existing_page.url.startswith(HOME_URL_PREFIX):
            existing_page.set_default_timeout(30 * 1000)
            existing_page.bring_to_front()
            logging.info("Reusing existing WeChat MP home tab: %s", existing_page.url)
            wait_with_jitter(existing_page, 1.0, "existing page stabilization")
            return existing_page

    page = context.new_page()
    page.set_default_timeout(30 * 1000)
    logging.info("Opening WeChat MP home tab: %s", DEFAULT_HOME_URL)
    page.goto(DEFAULT_HOME_URL, wait_until="domcontentloaded")
    wait_with_jitter(page, 2.0, "initial page stabilization")

    login_locator = page.get_by_text("登录", exact=True).first
    try:
        if login_locator.is_visible(timeout=1500):
            box = login_locator.bounding_box()
            if not box:
                raise RuntimeError("Login button was visible but had no bounding box.")
            center_x, center_y, click_x, click_y = random_point_in_center_band(box)
            logging.info("Found login prompt; clicking login to restore session")
            wait_with_jitter(page, 0.8, "pre-login pause")
            page.mouse.click(click_x, click_y)
            page.wait_for_load_state("domcontentloaded", timeout=10 * 1000)
            wait_with_jitter(page, 2.5, "post-login stabilization")
    except Error:
        logging.info("Login prompt not detected; continuing with current page")

    try:
        opened_title = page.title()
    except Error:
        opened_title = "<unavailable during navigation>"
    print(f"Opened tab title: {opened_title}")
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
    try:
        page.wait_for_load_state("domcontentloaded", timeout=3000)
    except Error:
        pass
    after_url = page.url
    try:
        post_click_title = page.title()
    except Error:
        post_click_title = "<unavailable during navigation>"
    print(f"Found text: {target_text}")
    print(
        f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
    )
    print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
    print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
    print(f"URL before click: {before_url}")
    print(f"URL after click: {after_url}")
    print(f"URL changed: {'yes' if before_url != after_url else 'no'}")
    print(f"Post-click title: {post_click_title}")
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
    set_clipboard_text(text)
    wait_with_jitter(page, 1.0, "pre-focus pause")
    page.mouse.click(click_x, click_y)
    page.wait_for_timeout(200)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.wait_for_timeout(150)
    page.keyboard.press("Control+V")
    page.wait_for_timeout(300)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)
    after_text = locator.inner_text()
    print(f"Body selector: {selector}")
    print(
        f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
    )
    print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
    print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
    print(f"Clipboard length: {len(text)}")
    print(f"Text before length: {len(before_text)}")
    print(f"Text after length: {len(after_text)}")


def hover_cover_and_click_ai_image(page: Page) -> None:
    cover_locator = page.locator(COVER_SELECTOR).first
    cover_locator.wait_for(state="visible", timeout=10 * 1000)
    cover_locator.scroll_into_view_if_needed(timeout=10 * 1000)
    page.wait_for_timeout(500)
    cover_box = cover_locator.bounding_box()
    if not cover_box:
        raise RuntimeError(f"Cover control was found but had no bounding box: {COVER_SELECTOR}")
    cover_center_x, cover_center_y, hover_x, hover_y = random_point_in_center_band(cover_box)
    wait_with_jitter(page, 1.0, "pre-hover pause")
    ai_locator = page.locator(AI_IMAGE_SELECTOR).first
    ai_box = None
    for attempt in range(3):
        page.mouse.move(hover_x, hover_y, steps=12)
        page.wait_for_timeout(1200)
        try:
            ai_locator.wait_for(state="visible", timeout=2500)
            ai_box = ai_locator.bounding_box()
            if ai_box:
                break
        except Error:
            logging.info("AI image entry still hidden after hover attempt %d", attempt + 1)
            page.mouse.move(hover_x, hover_y + 24, steps=8)
            page.wait_for_timeout(300)
            continue

    if not ai_box:
        raise RuntimeError(f"AI image entry was found but had no bounding box: {AI_IMAGE_SELECTOR}")
    ai_center_x, ai_center_y, click_x, click_y = random_point_in_center_band(ai_box)
    wait_with_jitter(page, 1.0, "pre-click pause")
    page.mouse.click(click_x, click_y)
    page.wait_for_timeout(1200)
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


def input_ai_cover_prompt(page: Page, prompt_text: str) -> None:
    prompt_locator = page.locator(AI_PROMPT_SELECTOR).first
    prompt_locator.wait_for(state="visible", timeout=10 * 1000)
    prompt_box = prompt_locator.bounding_box()
    if not prompt_box:
        raise RuntimeError(f"AI prompt textarea was found but had no bounding box: {AI_PROMPT_SELECTOR}")
    prompt_center_x, prompt_center_y, prompt_click_x, prompt_click_y = random_point_in_center_band(prompt_box)
    before_value = prompt_locator.input_value()
    wait_with_jitter(page, 1.0, "pre-focus pause")
    page.mouse.click(prompt_click_x, prompt_click_y)
    page.wait_for_timeout(200)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    type_like_human(page, prompt_text)
    page.wait_for_timeout(300)
    after_value = prompt_locator.input_value()
    print(f"AI prompt selector: {AI_PROMPT_SELECTOR}")
    print(
        f"Prompt box: x={prompt_box['x']:.2f}, y={prompt_box['y']:.2f}, width={prompt_box['width']:.2f}, height={prompt_box['height']:.2f}"
    )
    print(f"Click center: x={prompt_center_x:.2f}, y={prompt_center_y:.2f}")
    print(f"Actual click: x={prompt_click_x:.2f}, y={prompt_click_y:.2f}")
    print(f"Prompt before: {before_value!r}")
    print(f"Prompt after: {after_value!r}")


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
    args = parse_args()
    title_text, author_text, body_text = resolve_article_payload(args)
    if args.title or args.content:
        logging.info("Loaded article text from direct CLI arguments")
    else:
        logging.info("Loaded article text from %s", args.input_path)
    logging.info(
        "Title length=%d, author length=%d, body length=%d",
        len(title_text),
        len(author_text),
        len(body_text),
    )

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
                    type_into_field(page, TITLE_SELECTOR, title_text)
                    type_into_field(page, AUTHOR_SELECTOR, author_text)
                    type_into_body(page, BODY_SELECTOR, body_text)
                    hover_cover_and_click_ai_image(page)
                    input_ai_cover_prompt(page, DEFAULT_AI_COVER_PROMPT)
                    logging.info("Content and AI cover prompt have been inserted. Leaving the editor tab open for manual takeover.")
                    print("Manual takeover point reached.")
                    print(f"Editor tab title: {page.title()}")
                    print(f"Editor tab url: {page.url}")
            finally:
                pass
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

#!/usr/bin/env python3
"""
Reuse the WeChat article-editor tab, paste body content from the clipboard,
and press Enter once after the paste.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import logging
import random
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import Error, Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
EDITOR_URL_KEYWORD = "media/appmsg_edit"
BODY_SELECTOR = "div.ProseMirror"
DEFAULT_INPUT_PATH = str(Path(tempfile.gettempdir()) / "md-to-txt-40tycc39.txt")
GMEM_MOVEABLE = 0x0002
CF_UNICODETEXT = 13


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reuse the WeChat editor tab and paste body text from the clipboard."
    )
    parser.add_argument(
        "--input-path",
        default=DEFAULT_INPUT_PATH,
        help="Plain-text body file to copy into the clipboard before pasting.",
    )
    return parser.parse_args()


def setup_logging() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def printable_text(text: str, limit: int = 240) -> str:
    snippet = text[:limit]
    if len(text) > limit:
        snippet += "...(truncated)"
    return ascii(snippet)


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


def load_body_text(input_path: str) -> str:
    path = Path(input_path)
    if not path.is_file():
        raise RuntimeError(f"Body text file not found: {path}")
    body_text = path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    if not body_text:
        raise RuntimeError(f"Body text file is empty: {path}")
    return body_text


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


def main() -> None:
    setup_logging()
    args = parse_args()
    body_text = load_body_text(args.input_path)
    logging.info("Loaded body text from %s", args.input_path)
    logging.info("Clipboard payload length=%d", len(body_text))
    set_clipboard_text(body_text)
    logging.info("Clipboard updated")

    try:
        browser_ws = resolve_browser_ws_endpoint(DEFAULT_CDP_URL)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(browser_ws)
            try:
                page = find_editor_page(browser)
                logging.info("Reusing editor tab: %s", page.url)
                page.bring_to_front()
                locator = page.locator(BODY_SELECTOR)
                locator.wait_for(state="visible", timeout=10 * 1000)
                box = locator.bounding_box()
                if not box:
                    raise RuntimeError("Body editor was found but had no bounding box.")
                center_x, center_y, click_x, click_y = random_point_in_center_band(box)
                before_text = locator.inner_text()
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
                print(f"Editor tab title: {page.title()}")
                print(f"Editor tab url: {page.url}")
                print(f"Body selector: {BODY_SELECTOR}")
                print(
                    f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
                )
                print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
                print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
                print(f"Clipboard length: {len(body_text)}")
                print(f"Text before length: {len(before_text)}")
                print(f"Text before preview: {printable_text(before_text)}")
                print(f"Text after length: {len(after_text)}")
                print(f"Text after preview: {printable_text(after_text)}")
            finally:
                browser.close()
    except Error as exc:
        logging.error("Failed while pasting body in the reused editor tab: %s", exc)
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

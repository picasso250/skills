#!/usr/bin/env python

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, async_playwright

DEFAULT_ENDPOINT = "http://127.0.0.1:9222"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="validate_topic_popup.py",
        description="Validate Douyin topic suggestion popup from the current publish form.",
    )
    parser.add_argument("--word", required=True, help="Topic word to type after ` #`.")
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"Chrome CDP endpoint. Default: {DEFAULT_ENDPOINT}",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path.cwd() / "artifacts" / "douyin-topic-popup"),
        help="Directory for failure screenshots and metadata.",
    )
    return parser.parse_args(argv)


def get_ws_url(endpoint: str) -> str | None:
    try:
        with urlopen(f"{endpoint}/json/version", timeout=5) as response:
            data = json.load(response)
    except (URLError, TimeoutError, ValueError):
        return None
    return data.get("webSocketDebuggerUrl")


async def connect_browser(playwright, endpoint: str):
    ws_url = get_ws_url(endpoint)
    return await playwright.chromium.connect_over_cdp(ws_url or endpoint)


async def find_douyin_page(browser) -> Page:
    for context in browser.contexts:
        for page in context.pages:
            if "creator.douyin.com" in page.url:
                return page
    raise RuntimeError("未找到已打开的抖音创作者中心页面。")


async def find_description_editor(page: Page):
    locators = [
        page.get_by_placeholder("添加作品简介"),
        page.locator("textarea[placeholder*='简介']"),
        page.locator("textarea[placeholder*='描述']"),
        page.locator(".editor-comp-publish[contenteditable='true']"),
        page.locator("[contenteditable='true']").first,
    ]
    for locator in locators:
        try:
            target = locator.first if hasattr(locator, "first") else locator
            await target.wait_for(timeout=3_000)
            return target
        except PlaywrightError:
            pass
    raise RuntimeError("未找到简介输入区域。")


async def move_cursor_to_end(page: Page) -> None:
    await page.keyboard.press("Control+End")
    await page.wait_for_timeout(300)


async def detect_topic_popup(page: Page) -> dict:
    return await page.evaluate(
        """
() => {
  const textOf = (el) => (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
  };

  const popupNodes = Array.from(
    document.querySelectorAll(
      ".mention-suggest-mount-dom, .mention-suggest-F02Ddw, .mention-suggest-item-container-TVOZMl"
    )
  )
    .filter((el) => el instanceof HTMLElement && isVisible(el))
    .map((el) => ({
      tag: el.tagName,
      cls: String(el.className || ""),
      role: el.getAttribute("role") || "",
      text: textOf(el).slice(0, 500),
    }));

  const itemNodes = Array.from(document.querySelectorAll(".tag-dVUDkJ.tag-hash-o0tpyE"))
    .filter((el) => el instanceof HTMLElement && isVisible(el))
    .map((el) => ({
      tag: el.tagName,
      cls: String(el.className || ""),
      role: el.getAttribute("role") || "",
      text: textOf(el).slice(0, 120),
    }));

  const likelyPopup = popupNodes[0] || null;

  return {
    found: Boolean(likelyPopup),
    popup: likelyPopup || null,
    candidates: popupNodes.slice(0, 10),
    items: itemNodes.slice(0, 10),
    bodyPreview: textOf(document.body).slice(0, 600),
  };
}
"""
    )


async def save_failure(page: Page, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    shot_path = output_dir / "validate-topic-popup-failure.png"
    meta_path = output_dir / "validate-topic-popup-failure.json"
    body_text = await page.locator("body").inner_text()
    await page.screenshot(path=str(shot_path), full_page=True)
    meta = {
        "url": page.url,
        "title": await page.title(),
        "bodyPreview": body_text[:1500],
        "screenshot": str(shot_path.resolve()),
    }
    meta_path.write_text(f"{json.dumps(meta, ensure_ascii=False, indent=2)}\n", encoding="utf-8")
    return {"shotPath": str(shot_path.resolve()), "metaPath": str(meta_path.resolve())}


async def main(argv: list[str]) -> int:
    args = parse_args(argv)
    browser = None
    page = None
    output_dir = Path(args.output_dir).expanduser().resolve()

    async with async_playwright() as playwright:
        try:
            print("STEP: connect browser")
            browser = await connect_browser(playwright, args.endpoint)
            page = await find_douyin_page(browser)

            print("STEP: find description editor")
            editor = await find_description_editor(page)

            print("STEP: focus description editor")
            await editor.click()
            await page.wait_for_timeout(500)

            print("STEP: move cursor to end")
            await move_cursor_to_end(page)

            text = f" #{args.word}"
            print(f"STEP: type topic trigger {text!r}")
            await page.keyboard.insert_text(text)

            print("STEP: wait 2s for popup")
            await page.wait_for_timeout(2_000)

            popup_state = await detect_topic_popup(page)
            result = {
                "url": page.url,
                "typed": text,
                "found": popup_state.get("found", False),
                "popup": popup_state.get("popup"),
                "candidates": popup_state.get("candidates", []),
            }
            print(f"RESULT_JSON:{json.dumps(result, ensure_ascii=False)}")
            return 0
        except Exception:
            if page is not None:
                failure = await save_failure(page, output_dir)
                print(f"ERROR_SCREENSHOT:{failure['shotPath']}")
                print(f"ERROR_META:{failure['metaPath']}")
            raise
        finally:
            if browser is not None:
                await browser.close()


if __name__ == "__main__":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        raise SystemExit(asyncio.run(main(sys.argv[1:])))
    except Exception as exc:
        print(f"ERROR:{exc}", file=sys.stderr)
        raise SystemExit(1)

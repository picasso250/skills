#!/usr/bin/env python

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, async_playwright

DEFAULT_ENDPOINT = "http://127.0.0.1:9222"
UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="douyin_publish.py",
        description="CLI automation for uploading Douyin creator videos with a human-in-the-loop pause.",
    )
    parser.add_argument("--video", help="Absolute or relative path to the local video file.")
    parser.add_argument("--title", default="", help="Video title.")
    parser.add_argument("--title-b64", default="", help="UTF-8 base64 encoded video title.")
    parser.add_argument("--description", default="", help="Optional video description.")
    parser.add_argument("--description-b64", default="", help="UTF-8 base64 encoded description.")
    parser.add_argument(
        "--topic",
        action="append",
        dest="topics",
        default=[],
        help="Topic word to insert into description. Pass multiple times for multiple topics.",
    )
    parser.add_argument(
        "--continue-after-upload",
        action="store_true",
        help="Continue to fill fields after upload completes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stop before the final publish click.",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"Chrome CDP endpoint. Default: {DEFAULT_ENDPOINT}",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path.cwd() / "artifacts" / "douyin-publish"),
        help="Directory for failure screenshots and metadata.",
    )

    args = parser.parse_args(argv)
    if not args.video:
        parser.error("--video is required")
    if args.dry_run and not args.continue_after_upload:
        parser.error("--dry-run requires --continue-after-upload")
    return args


def decode_text(raw: str, raw_b64: str, field_name: str) -> str:
    if raw_b64:
        try:
            return base64.b64decode(raw_b64).decode("utf-8")
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid base64 for {field_name}") from exc
    return raw or ""


def get_ws_url(endpoint: str) -> str | None:
    try:
        with urlopen(f"{endpoint}/json/version", timeout=5) as response:
            data = json.load(response)
    except (URLError, TimeoutError, ValueError):
        return None
    return data.get("webSocketDebuggerUrl")


async def connect_browser(playwright: Any, endpoint: str):
    ws_url = get_ws_url(endpoint)
    return await playwright.chromium.connect_over_cdp(ws_url or endpoint)


async def find_existing_page(browser: Any) -> Page:
    for context in browser.contexts:
        for page in context.pages:
            if "creator.douyin.com" in page.url:
                return page
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    return await context.new_page()


async def ensure_upload_page(page: Page) -> None:
    await page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_timeout(5_000)
    body_text = await page.locator("body").inner_text()
    if "登录" in body_text and "发布视频" not in body_text:
        raise RuntimeError("当前浏览器会话未登录抖音创作者中心。")
    if "发布视频" not in body_text:
        raise RuntimeError(f"未进入抖音发布页，当前 URL: {page.url}")


async def find_upload_input(page: Page):
    locator = page.locator("input[type='file']").first
    await locator.wait_for(timeout=10_000)
    return locator


async def wait_for_form(page: Page) -> None:
    candidates = [
        page.get_by_placeholder("填写作品标题，为作品获得更多流量"),
        page.get_by_placeholder("添加作品简介"),
        page.get_by_text("作品标题"),
        page.get_by_text("作品简介"),
        page.get_by_role("button", name="发布"),
        page.get_by_role("button", name="立即发布"),
    ]
    for candidate in candidates:
        try:
            await candidate.first.wait_for(timeout=5_000)
            return
        except PlaywrightError:
            pass
    raise RuntimeError("上传后未等到发布表单出现。")


async def read_cover_generation_status(page: Page) -> dict[str, Any]:
    script = """
() => {
  const bodyText = (document.body?.innerText || "").replace(/\\s+/g, " ").trim();
  const patterns = [
    /AI智能推荐封面.{0,20}?(生成中|推荐中|处理中)/i,
    /智能推荐封面.{0,20}?(生成中|推荐中|处理中)/i,
    /推荐封面.{0,20}?(生成中|推荐中|处理中)/i,
  ];
  for (const pattern of patterns) {
    const match = bodyText.match(pattern);
    if (!match || typeof match.index !== "number") {
      continue;
    }
    const start = Math.max(0, match.index - 30);
    const end = Math.min(bodyText.length, match.index + match[0].length + 30);
    return {
      found: true,
      text: match[0],
      context: bodyText.slice(start, end),
    };
  }
  return {
    found: false,
    text: "",
    context: bodyText.slice(0, 200),
  };
}
"""
    try:
        return await page.evaluate(script)
    except PlaywrightError:
        return {"found": False, "text": "", "context": ""}


async def wait_for_recommended_cover_ready(page: Page, timeout_ms: int = 180_000) -> dict[str, Any]:
    script = """
() => {
  const bodyText = (document.body?.innerText || "").replace(/\\s+/g, " ").trim();
  const normalizedText = bodyText.toLowerCase();
  const hasGenerating =
    normalizedText.includes("ai智能推荐封面生成中") ||
    normalizedText.includes("智能推荐封面生成中") ||
    normalizedText.includes("推荐封面生成中");
  const readyPatterns = [
    /AI智能推荐封面(?!.*生成中)/i,
    /智能推荐封面(?!.*生成中)/i,
  ];
  let readyMatch = "";
  for (const pattern of readyPatterns) {
    const match = bodyText.match(pattern);
    if (match) {
      readyMatch = match[0];
      break;
    }
  }
  return {
    hasGenerating,
    ready: Boolean(readyMatch) && !hasGenerating,
    text: readyMatch,
    preview: bodyText.slice(0, 400),
  };
}
"""
    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    while asyncio.get_running_loop().time() < deadline:
        snapshot = await page.evaluate(script)
        print(f"UPLOAD_COVER_WAIT:{json.dumps(snapshot, ensure_ascii=False)}")
        if snapshot.get("ready"):
            return snapshot
        await page.wait_for_timeout(3_000)
    raise RuntimeError("等待 AI 智能推荐封面完成超时。")


async def click_first_recommended_cover(page: Page) -> dict[str, Any]:
    result = await page.evaluate(
        """
() => {
  const display = document.querySelector(".recommendDisplay-OgigFx");
  if (!display) {
    return { clicked: false, reason: "recommend-display-not-found" };
  }

  const titleText = (display.textContent || "").replace(/\\s+/g, " ").trim();
  if (!/AI智能推荐封面|Ai智能推荐封面|智能推荐封面/i.test(titleText)) {
    return { clicked: false, reason: "recommend-display-text-mismatch", titleText };
  }

  const container = display.querySelector(".recommendCoverContainer-S5XRoQ");
  if (!container) {
    return { clicked: false, reason: "recommend-cover-container-not-found" };
  }

  const coverItems = Array.from(container.querySelectorAll(".recommendCover-vWWsHB"));
  if (coverItems.length < 3) {
    return { clicked: false, reason: "recommend-cover-items-not-found", itemCount: coverItems.length };
  }

  const firstItem = coverItems[0];
  const firstImage = firstItem.querySelector("img");
  if (!firstImage) {
    return { clicked: false, reason: "recommend-cover-first-image-not-found" };
  }

  firstImage.click();
  return {
    clicked: true,
    itemCount: coverItems.length,
    src: (firstImage.getAttribute("src") || "").slice(0, 160),
  };
}
"""
    )
    if not result.get("clicked"):
        raise RuntimeError(f"未找到可点击的推荐封面首图: {result.get('reason')}")
    await page.wait_for_timeout(1_000)
    return result


async def confirm_apply_recommended_cover(page: Page) -> dict[str, Any]:
    modal = page.locator(".semi-modal, .semi-modal-content").filter(has_text="是否确认应用此封面").first
    await modal.wait_for(timeout=10_000)
    confirm_button = modal.get_by_role("button", name="确定").first
    await confirm_button.wait_for(timeout=5_000)
    await confirm_button.click()
    await page.wait_for_timeout(1_000)
    return {"confirmed": True, "message": "是否确认应用此封面？"}


async def try_fill_first(page: Page, locators: list[Any], value: str) -> bool:
    if not value:
        return False
    for locator in locators:
        try:
            target = locator.first
            await target.wait_for(timeout=3_000)
            await target.click()
            await page.wait_for_timeout(1_000)
            await target.fill(value)
            await page.wait_for_timeout(1_000)
            return True
        except PlaywrightError:
            pass
    return False


async def fill_title(page: Page, title: str) -> None:
    ok = await try_fill_first(
        page,
        [
            page.get_by_placeholder("填写作品标题，为作品获得更多流量"),
            page.locator("input[placeholder*='标题']"),
            page.locator("textarea[placeholder*='标题']"),
            page.locator("input").filter(has=page.get_by_text("标题")),
        ],
        title,
    )
    if not ok:
        raise RuntimeError("未找到标题输入框。")


async def fill_description(page: Page, description: str) -> None:
    if not description:
        return
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
            await target.click()
            await page.wait_for_timeout(1_000)
            try:
                await target.fill(description)
            except PlaywrightError:
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.insert_text(description)
            await page.wait_for_timeout(1_000)
            return
        except PlaywrightError:
            pass
    raise RuntimeError("未找到简介输入框。")


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


async def wait_for_topic_popup(page: Page) -> list[dict[str, Any]]:
    deadline = asyncio.get_running_loop().time() + 5
    while asyncio.get_running_loop().time() < deadline:
        items = await page.evaluate(
            """
() => Array.from(document.querySelectorAll('.tag-dVUDkJ.tag-hash-o0tpyE'))
  .map((el, index) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    const text = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
    return {
      index,
      text,
      visible: style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0
    };
  })
  .filter((item) => item.visible)
"""
        )
        if items:
            return items
        await page.wait_for_timeout(200)
    raise RuntimeError("等待话题候选弹层超时。")


async def click_first_topic_item(page: Page) -> dict[str, Any]:
    first_item = page.locator(".tag-dVUDkJ.tag-hash-o0tpyE").first
    await first_item.wait_for(timeout=5_000)
    label = ((await first_item.inner_text()) or "").replace("\n", " ").strip()
    await first_item.click()
    await page.wait_for_timeout(1_000)
    return {"text": label}


async def add_topics(page: Page, topics: list[str]) -> list[dict[str, Any]]:
    if not topics:
        return []

    editor = await find_description_editor(page)
    await editor.click()
    await page.wait_for_timeout(500)

    results = []
    for topic in topics:
        await move_cursor_to_end(page)
        typed = f" #{topic}"
        await page.keyboard.insert_text(typed)
        popup_items = await wait_for_topic_popup(page)
        clicked = await click_first_topic_item(page)
        results.append(
            {
                "topic": topic,
                "typed": typed,
                "popupItems": popup_items[:5],
                "clicked": clicked,
            }
        )

    return results


async def click_publish(page: Page) -> None:
    buttons = [
        page.locator("button.button-dhlUZE.primary-cECiOJ.fixed-J9O8Yw"),
        page.locator("button.fixed-J9O8Yw").filter(has_text="发布"),
        page.get_by_role("button", name="发布").locator(".."),
        page.get_by_text("发布", exact=True),
    ]
    for button in buttons:
        try:
            target = button.first
            await target.wait_for(timeout=3_000)
            if await target.is_disabled():
                continue
            await target.click()
            await page.wait_for_timeout(1_500)
            return
        except PlaywrightError:
            pass
    raise RuntimeError("未找到最终发布按钮。")


async def read_short_lived_feedback(page: Page) -> list[dict[str, str]]:
    try:
        return await page.evaluate(
            """
() => Array.from(document.querySelectorAll(".semi-toast, .semi-notification, [role=dialog]"))
  .map((el) => ({
    text: (el.innerText || el.textContent || "").trim(),
    cls: String(el.className || ""),
  }))
  .filter((item) => item.text)
"""
        )
    except PlaywrightError:
        return []


async def save_failure(page: Page, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    shot_path = output_dir / "douyin-publish-failure.png"
    meta_path = output_dir / "douyin-publish-failure.json"
    body_text = await page.locator("body").inner_text()
    await page.screenshot(path=str(shot_path), full_page=True)
    meta = {
        "url": page.url,
        "title": await page.title(),
        "bodyPreview": body_text[:1000],
        "screenshot": str(shot_path.resolve()),
    }
    meta_path.write_text(f"{json.dumps(meta, ensure_ascii=False, indent=2)}\n", encoding="utf-8")
    return {"shotPath": str(shot_path.resolve()), "metaPath": str(meta_path.resolve())}


async def main(argv: list[str]) -> int:
    args = parse_args(argv)
    video_path = Path(args.video).expanduser().resolve()
    if not video_path.is_file():
        raise RuntimeError(f"Video file not found: {video_path}")

    title = decode_text(args.title, args.title_b64, "title") or video_path.stem
    description = decode_text(args.description, args.description_b64, "description")
    output_dir = Path(args.output_dir).expanduser().resolve()

    browser = None
    page = None

    async with async_playwright() as playwright:
        try:
            print("STEP: connect browser")
            browser = await connect_browser(playwright, args.endpoint)
            page = await find_existing_page(browser)

            print("STEP: open upload page")
            await ensure_upload_page(page)

            print("STEP: upload video")
            upload_input = await find_upload_input(page)
            await upload_input.set_input_files(str(video_path))
            await page.wait_for_timeout(3_000)

            print("STEP: detect cover generation status")
            cover_status = await read_cover_generation_status(page)
            print(f"UPLOAD_COVER_STATUS:{json.dumps(cover_status, ensure_ascii=False)}")

            await page.wait_for_timeout(2_000)

            print("STEP: wait for form")
            await wait_for_form(page)

            print("STEP: wait for recommended cover ready")
            recommended_cover = await wait_for_recommended_cover_ready(page)

            print("STEP: click first recommended cover")
            cover_click = await click_first_recommended_cover(page)

            print("STEP: confirm apply recommended cover")
            cover_confirm = await confirm_apply_recommended_cover(page)

            result = {
                "url": page.url,
                "video": str(video_path),
                "title": title,
                "description": description,
                "coverStatus": cover_status,
                "recommendedCover": recommended_cover,
                "coverClick": cover_click,
                "coverConfirm": cover_confirm,
                "published": False,
            }

            if not args.continue_after_upload:
                result["phase"] = "uploaded"
                result["awaitingHuman"] = True
                result["message"] = "上传成功，已停在发布表单前，等待用户继续操作。"
                print("STEP: upload complete; human-in-the-loop pause")
                print(f"RESULT_JSON:{json.dumps(result, ensure_ascii=False)}")
                return 0

            print("STEP: fill title")
            await fill_title(page, title)

            if description:
                print("STEP: fill description")
                await fill_description(page, description)

            if args.topics:
                print("STEP: add topics")
                topic_results = await add_topics(page, args.topics)
                result["topics"] = topic_results

            result["phase"] = "draft_ready"

            if args.dry_run:
                print("STEP: publish skipped; dry-run mode enabled")
            else:
                print("STEP: click publish")
                await click_publish(page)
                feedback = await read_short_lived_feedback(page)
                if feedback:
                    result["feedback"] = feedback
                    first_message = feedback[0].get("text", "")
                    if "请设置封面后再发布" in first_message:
                        raise RuntimeError(first_message)
                result["published"] = True
                result["phase"] = "published"
                result["postPublishUrl"] = page.url

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

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import Browser, Locator, Page, sync_playwright


DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_URL_CONTAINS = "/creator-micro/content/manage"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract real metrics from visible private Douyin works by opening the preview modal."
    )
    parser.add_argument("--cdp-url", default=DEFAULT_CDP_URL, help="Chrome CDP HTTP endpoint")
    parser.add_argument(
        "--url-contains",
        default=DEFAULT_URL_CONTAINS,
        help="Match the open tab whose URL contains this substring",
    )
    parser.add_argument("--exact-url", help="Match an exact page URL instead of --url-contains")
    parser.add_argument("--limit", type=int, help="Only inspect the first N visible private cards")
    parser.add_argument("--output", help="Write JSON to this file instead of stdout")
    return parser.parse_args()


def resolve_ws_endpoint(cdp_url: str) -> str:
    version_url = f"{cdp_url.rstrip('/')}/json/version"
    with urlopen(version_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    ws_endpoint = payload.get("webSocketDebuggerUrl")
    if not ws_endpoint:
        raise RuntimeError(f"Missing webSocketDebuggerUrl in {version_url}")
    return ws_endpoint


def find_target_page(browser: Browser, args: argparse.Namespace) -> Page:
    for context in browser.contexts:
        for page in context.pages:
            if args.exact_url and page.url == args.exact_url:
                return page
            if not args.exact_url and args.url_contains in page.url:
                return page
    target = args.exact_url or args.url_contains
    raise RuntimeError(f"No open page matched: {target}")


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\u00a0", " ").strip()
    return text or None


def extract_card_meta(card: Locator, index: int) -> dict[str, object]:
    def txt(selector: str) -> str | None:
        loc = card.locator(selector)
        if loc.count() == 0:
            return None
        return clean(loc.first.inner_text(timeout=3000))

    metric_names = ("播放", "点赞", "评论", "分享")
    raw_text = clean(card.inner_text(timeout=5000))
    metrics: dict[str, str | None] = {}
    for name in metric_names:
        metrics[name] = None

    return {
        "index": index,
        "duration_or_count": txt('[class*="badge-"]'),
        "privacy": txt('[class*="private-mark-"]'),
        "title": txt('[class*="info-title-text-"]'),
        "publish_time": txt('[class*="info-time-"]'),
        "status": txt('[class*="info-status-"]'),
        "list_metrics": metrics,
        "raw_text": raw_text,
    }


def wait_preview_frame(page: Page):
    modal = page.locator('[class*="douyin-creator-vmock-modal-content"]')
    modal.wait_for(state="visible", timeout=10000)
    iframe = modal.locator("iframe").first
    iframe.wait_for(state="attached", timeout=10000)
    src = iframe.get_attribute("src")
    if not src:
        raise RuntimeError("Preview iframe has no src")

    prefix = src.split("?")[0]
    for _ in range(30):
        for frame in page.frames:
            if frame.url.startswith(prefix):
                return src, frame
        page.wait_for_timeout(200)
    raise RuntimeError(f"Could not locate frame for {src}")


def frame_metric(frame, selector: str) -> str | None:
    loc = frame.locator(selector)
    if loc.count() == 0:
        return None
    return clean(loc.first.inner_text(timeout=3000))


def extract_preview_metrics(page: Page, card: Locator) -> dict[str, object]:
    cover = card.locator('[class*="video-card-cover-"]').first
    cover.click(timeout=10000, force=True)
    page.wait_for_timeout(1200)
    iframe_src, frame = wait_preview_frame(page)
    frame.wait_for_timeout(1200)

    payload = {
        "iframe_src": iframe_src,
        "author": frame_metric(frame, ".video-info-detail"),
        "title_in_preview": frame_metric(frame, ".title"),
        "like_count": frame_metric(frame, '[data-e2e="video-player-digg"]'),
        "comment_count": frame_metric(frame, '[data-e2e="feed-comment-icon"]'),
        "collect_count": frame_metric(frame, '[data-e2e="video-player-collect"]'),
        "share_text": frame_metric(frame, '[data-e2e="video-player-share"]'),
    }

    close_btn = page.locator(".esc-box-WpPp57").first
    if close_btn.count():
        close_btn.click(timeout=5000, force=True)
    else:
        page.keyboard.press("Escape")
    page.wait_for_timeout(800)
    return payload


def collect_private_items(page: Page, limit: int | None) -> dict[str, object]:
    page.bring_to_front()
    page.wait_for_timeout(800)

    cards = page.locator('[class*="video-card-zQ02ng"]')
    total = cards.count()
    items: list[dict[str, object]] = []
    inspected = 0

    for index in range(total):
        card = cards.nth(index)
        meta = extract_card_meta(card, index)
        if meta.get("privacy") != "私密":
            continue
        if limit is not None and inspected >= limit:
            break

        preview = extract_preview_metrics(page, card)
        meta["preview_metrics"] = preview
        items.append(meta)
        inspected += 1

    return {
        "page_title": clean(page.title()),
        "page_url": page.url,
        "visible_card_count": total,
        "private_card_count": len(items),
        "items": items,
    }


def write_json(payload: dict[str, object], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        output.write_text(text, encoding="utf-8")
    else:
        print(text)


def main() -> int:
    args = parse_args()
    output = Path(args.output) if args.output else None
    ws_endpoint = resolve_ws_endpoint(args.cdp_url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(ws_endpoint)
        try:
            page = find_target_page(browser, args)
            payload = collect_private_items(page, args.limit)
        finally:
            browser.close()

    write_json(payload, output)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())

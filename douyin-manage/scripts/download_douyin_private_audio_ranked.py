#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import Browser, Locator, Page, sync_playwright


DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_URL_CONTAINS = "/creator-micro/content/manage"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download audio for the best and worst visible private Douyin videos ranked by comment count."
    )
    parser.add_argument("--cdp-url", default=DEFAULT_CDP_URL, help="Chrome CDP HTTP endpoint")
    parser.add_argument(
        "--url-contains",
        default=DEFAULT_URL_CONTAINS,
        help="Match the open tab whose URL contains this substring",
    )
    parser.add_argument("--exact-url", help="Match an exact page URL instead of --url-contains")
    parser.add_argument("--count", type=int, default=3, help="How many best / worst items to download")
    parser.add_argument(
        "--output-dir",
        default=str(Path.cwd() / "cases" / "douyin-private-audio-ranked"),
        help="Output root directory",
    )
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


def safe_name(text: str) -> str:
    cleaned = re.sub(r"[\\\\/:*?\"<>|]+", "", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:80] or "untitled"


def numeric(text: str | None) -> int | None:
    if text is None:
        return None
    text = text.strip()
    if text.isdigit():
        return int(text)
    return None


def extract_card_meta(card: Locator, index: int) -> dict[str, object]:
    def txt(selector: str) -> str | None:
        loc = card.locator(selector)
        if loc.count() == 0:
            return None
        return clean(loc.first.inner_text(timeout=3000))

    return {
        "index": index,
        "duration_or_count": txt('[class*="badge-"]'),
        "privacy": txt('[class*="private-mark-"]'),
        "title": txt('[class*="info-title-text-"]'),
        "publish_time": txt('[class*="info-time-"]'),
        "status": txt('[class*="info-status-"]'),
        "raw_text": clean(card.inner_text(timeout=5000)),
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


def close_preview(page: Page) -> None:
    close_btn = page.locator(".esc-box-WpPp57").first
    if close_btn.count():
        close_btn.click(timeout=5000, force=True)
    else:
        page.keyboard.press("Escape")
    page.wait_for_timeout(700)


def extract_preview(page: Page, card: Locator) -> dict[str, object]:
    cover = card.locator('[class*="video-card-cover-"]').first
    cover.click(timeout=10000, force=True)
    page.wait_for_timeout(1200)
    iframe_src, frame = wait_preview_frame(page)
    frame.wait_for_timeout(1200)
    preview = frame.evaluate(
        r"""
        () => {
          const clean = (v) => (v == null ? null : String(v).replace(/\u00a0/g, ' ').trim()) || null;
          const text = (sel) => {
            const el = document.querySelector(sel);
            return clean(el?.innerText);
          };
          const video = document.querySelector('video');
          return {
            iframe_src: location.href,
            author: text('.video-info-detail'),
            title_in_preview: text('.title'),
            like_count: text('[data-e2e="video-player-digg"]'),
            comment_count: text('[data-e2e="feed-comment-icon"]'),
            collect_count: text('[data-e2e="video-player-collect"]'),
            share_text: text('[data-e2e="video-player-share"]'),
            video_src: video ? (video.currentSrc || video.src || null) : null,
            duration: video ? video.duration : null,
          };
        }
        """
    )
    close_preview(page)
    return preview


def fetch_binary(url: str) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.douyin.com/",
        },
    )
    with urlopen(req, timeout=60) as response:
        return response.read()


def write_audio_from_video_bytes(video_path: Path, audio_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-c:a",
        "copy",
        str(audio_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def is_video_item(meta: dict[str, object]) -> bool:
    value = meta.get("duration_or_count") or ""
    return ":" in str(value)


def collect_private_video_items(page: Page) -> list[dict[str, object]]:
    page.bring_to_front()
    page.wait_for_timeout(800)
    cards = page.locator('[class*="video-card-zQ02ng"]')
    items: list[dict[str, object]] = []
    for index in range(cards.count()):
        card = cards.nth(index)
        meta = extract_card_meta(card, index)
        if meta.get("privacy") != "私密":
            continue
        if not is_video_item(meta):
            continue
        preview = extract_preview(page, card)
        meta["preview_metrics"] = preview
        meta["comment_count_num"] = numeric(preview.get("comment_count"))
        meta["like_count_num"] = numeric(preview.get("like_count"))
        meta["collect_count_num"] = numeric(preview.get("collect_count"))
        items.append(meta)
    return items


def choose_ranked(items: list[dict[str, object]], count: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    scored = [item for item in items if item.get("comment_count_num") is not None]
    best = sorted(scored, key=lambda x: (x["comment_count_num"], x.get("like_count_num") or 0), reverse=True)[:count]
    worst = sorted(scored, key=lambda x: (x["comment_count_num"], x.get("like_count_num") or 0, x.get("publish_time") or ""))[:count]
    return best, worst


def download_group(page: Page, group_name: str, items: list[dict[str, object]], output_root: Path) -> list[dict[str, object]]:
    group_dir = output_root / group_name
    group_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    for rank, item in enumerate(items, start=1):
        preview = item["preview_metrics"]
        video_url = preview.get("video_src")
        if not video_url:
            raise RuntimeError(f"Missing video_src for {item.get('title')}")
        base = f"{rank:02d}_{safe_name(str(item.get('title') or preview.get('title_in_preview') or 'untitled'))}"
        video_tmp = group_dir / f"{base}.mp4"
        audio_out = group_dir / f"{base}.m4a"
        video_tmp.write_bytes(fetch_binary(video_url))
        write_audio_from_video_bytes(video_tmp, audio_out)
        video_tmp.unlink(missing_ok=True)
        results.append(
            {
                "rank": rank,
                "title": item.get("title"),
                "publish_time": item.get("publish_time"),
                "comment_count": item.get("comment_count_num"),
                "like_count": item.get("like_count_num"),
                "collect_count": item.get("collect_count_num"),
                "audio_path": str(audio_out),
                "video_url": video_url,
            }
        )
    return results


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    ws_endpoint = resolve_ws_endpoint(args.cdp_url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(ws_endpoint)
        try:
            page = find_target_page(browser, args)
            items = collect_private_video_items(page)
            best, worst = choose_ranked(items, args.count)
            best_results = download_group(page, "best", best, output_root)
            worst_results = download_group(page, "worst", worst, output_root)
        finally:
            browser.close()

    payload = {
        "output_root": str(output_root),
        "best": best_results,
        "worst": worst_results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import Browser, Page, sync_playwright


DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_TARGET_URL = "https://creator.xiaohongshu.com/new/note-manager"
OPERATION_LINES = {"权限设置", "置顶", "编辑", "删除"}
VISIBILITY_PATTERNS = (
    re.compile(r"^仅.*可见$"),
    re.compile(r"^私密$"),
    re.compile(r"^公开$"),
)


EXTRACT_JS = r"""
() => {
  const clean = (value) => {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/\u00a0/g, " ")
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n[ \t]+/g, "\n")
      .split("\n")
      .map((line) => line.replace(/\s+/g, " ").trim())
      .filter(Boolean)
      .join("\n")
      .trim();
  };

  const visibleEnough = (element) => {
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) {
      return false;
    }
    if (rect.width < 80 || rect.height < 18) return false;
    if (rect.bottom < -200 || rect.top > window.innerHeight + 200) return false;
    return true;
  };

  const selectors = [
    "tr",
    "article",
    "li",
    "[role='row']",
    "[role='listitem']",
    "[class*='note']",
    "[class*='Note']",
    "[class*='card']",
    "[class*='Card']",
    "[class*='item']",
    "[class*='Item']",
    "[class*='list'] > div",
    "[class*='List'] > div",
  ];

  const nodes = Array.from(document.querySelectorAll(selectors.join(",")));
  const items = [];
  const seen = new Set();

  for (const node of nodes) {
    if (!visibleEnough(node)) continue;
    const text = clean(node.innerText);
    if (text.length < 8 || text.length > 1800) continue;

    const lines = text.split("\n");
    if (lines.length > 60) continue;
    const navLike = /^(首页|发布笔记|数据|通知|设置|帮助|退出|创作中心)(\n|$)/.test(text);
    if (navLike && lines.length < 4) continue;

    const key = text.replace(/\s+/g, " ").slice(0, 500);
    if (seen.has(key)) continue;
    seen.add(key);

    const rect = node.getBoundingClientRect();
    items.push({
      tag: node.tagName.toLowerCase(),
      className: String(node.className || "").slice(0, 160),
      top: Math.round(rect.top + window.scrollY),
      text,
    });
  }

  items.sort((a, b) => a.top - b.top || a.text.localeCompare(b.text));

  const scrollElement = document.scrollingElement || document.documentElement;
  return {
    title: clean(document.title),
    url: location.href,
    scrollTop: Math.round(scrollElement.scrollTop),
    scrollHeight: Math.round(scrollElement.scrollHeight),
    clientHeight: Math.round(scrollElement.clientHeight),
    bodyText: clean(document.body?.innerText || ""),
    items,
  };
}
"""


SCROLL_JS = r"""
(stepRatio) => {
  const candidates = [document.scrollingElement, document.documentElement, document.body]
    .concat(Array.from(document.querySelectorAll("*")))
    .filter(Boolean)
    .filter((element) => {
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return (
        element.scrollHeight > element.clientHeight + 80 &&
        rect.width >= Math.min(320, window.innerWidth * 0.35) &&
        rect.height >= Math.min(240, window.innerHeight * 0.35) &&
        style.overflowY !== "hidden" &&
        style.display !== "none" &&
        style.visibility !== "hidden"
      );
    });

  candidates.sort((a, b) => {
    const aScore = (a.scrollHeight - a.clientHeight) * Math.max(1, a.clientWidth);
    const bScore = (b.scrollHeight - b.clientHeight) * Math.max(1, b.clientWidth);
    return bScore - aScore;
  });

  const target = candidates[0] || document.scrollingElement || document.documentElement;
  const before = target.scrollTop;
  const step = Math.max(240, Math.round((target.clientHeight || window.innerHeight) * stepRatio));
  target.scrollBy({ top: step, behavior: "instant" });

  return {
    before: Math.round(before),
    after: Math.round(target.scrollTop),
    max: Math.round(target.scrollHeight - target.clientHeight),
  };
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open Xiaohongshu Creator note manager via CDP, scroll it, and export loaded text to TXT."
    )
    parser.add_argument("--cdp-url", default=DEFAULT_CDP_URL, help="Chrome CDP HTTP endpoint")
    parser.add_argument("--target-url", default=DEFAULT_TARGET_URL, help="URL to open in a new tab")
    parser.add_argument("--open-wait-ms", type=int, default=3000, help="Wait after opening the page")
    parser.add_argument("--close-wait-ms", type=int, default=1000, help="Wait after output before closing the tab")
    parser.add_argument("--output", help="TXT output path; defaults to stdout")
    parser.add_argument("--max-scrolls", type=int, default=80, help="Maximum scroll steps")
    parser.add_argument("--delay-ms", type=int, default=900, help="Wait after each scroll")
    parser.add_argument("--stable-rounds", type=int, default=4, help="Stop after this many rounds with no movement/new text")
    parser.add_argument("--step-ratio", type=float, default=0.86, help="Scroll step as a fraction of container height")
    return parser.parse_args()


def resolve_ws_endpoint(cdp_url: str) -> str:
    version_url = f"{cdp_url.rstrip('/')}/json/version"
    with urlopen(version_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    ws_endpoint = payload.get("webSocketDebuggerUrl")
    if not ws_endpoint:
        raise RuntimeError(f"Missing webSocketDebuggerUrl in {version_url}")
    return ws_endpoint


def open_target_page(browser: Browser, args: argparse.Namespace) -> Page:
    if not browser.contexts:
        raise RuntimeError("No existing browser context found. Open Chrome with the logged-in profile and CDP enabled.")
    page = browser.contexts[0].new_page()
    page.goto(args.target_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(max(0, args.open_wait_ms))
    return page


def normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:700]


def clean_text_lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def is_visibility_line(line: str) -> bool:
    return any(pattern.search(line) for pattern in VISIBILITY_PATTERNS)


def parse_note_text(text: str) -> dict[str, object] | None:
    lines = clean_text_lines(text)
    if not lines or not any(line.startswith("发布于 ") for line in lines):
        return None

    publish_index = next(index for index, line in enumerate(lines) if line.startswith("发布于 "))
    before_publish = lines[:publish_index]
    after_publish = [line for line in lines[publish_index + 1 :] if line not in OPERATION_LINES]

    if not before_publish:
        return None

    duration_or_count = None
    visibility = None
    title_parts: list[str] = []

    for line in before_publish:
        if duration_or_count is None and re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", line):
            duration_or_count = line
            continue
        if visibility is None and is_visibility_line(line):
            visibility = line
            continue
        title_parts.append(line)

    title = " ".join(title_parts).strip()
    if not title:
        return None

    metrics = []
    for line in after_publish:
        if re.fullmatch(r"[\d,.万wW+-]+", line):
            metrics.append(line)

    return {
        "title": title,
        "publish_time": lines[publish_index].replace("发布于 ", "", 1).strip(),
        "duration_or_count": duration_or_count,
        "visibility": visibility,
        "metrics": metrics[:8],
    }


def notes_from_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    notes: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in items:
        note = parse_note_text(str(item.get("text") or ""))
        if not note:
            continue
        key = normalize_key(f"{note['title']} {note['publish_time']}")
        if key in seen:
            continue
        seen.add(key)
        note["round"] = item.get("round")
        notes.append(note)
    return notes


def collect(page: Page, args: argparse.Namespace) -> dict[str, object]:
    page.bring_to_front()
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    page.wait_for_timeout(800)

    seen: set[str] = set()
    items: list[dict[str, object]] = []
    last_position: tuple[int, int, int] | None = None
    stable = 0
    snapshot: dict[str, object] = {}

    for round_index in range(args.max_scrolls + 1):
        snapshot = page.evaluate(EXTRACT_JS)
        new_count = 0
        for item in snapshot.get("items", []):
            text = str(item.get("text") or "").strip()
            key = normalize_key(text)
            if not key or key in seen:
                continue
            seen.add(key)
            copied = dict(item)
            copied["round"] = round_index
            items.append(copied)
            new_count += 1

        position = (
            int(snapshot.get("scrollTop") or 0),
            int(snapshot.get("scrollHeight") or 0),
            int(snapshot.get("clientHeight") or 0),
        )
        at_bottom = position[0] + position[2] >= position[1] - 8 if position[1] else False

        if new_count == 0 and (position == last_position or at_bottom):
            stable += 1
        else:
            stable = 0
        if stable >= args.stable_rounds:
            break

        last_position = position
        scroll_result = page.evaluate(SCROLL_JS, args.step_ratio)
        page.wait_for_timeout(max(0, args.delay_ms))

        if scroll_result.get("after") == scroll_result.get("before") and new_count == 0:
            stable += 1

    if not items and snapshot.get("bodyText"):
        body_text = str(snapshot["bodyText"]).strip()
        if body_text:
            items.append({"round": 0, "tag": "body", "className": "", "top": 0, "text": body_text})

    notes = notes_from_items(items)

    return {
        "title": snapshot.get("title"),
        "url": snapshot.get("url"),
        "scroll_top": snapshot.get("scrollTop"),
        "scroll_height": snapshot.get("scrollHeight"),
        "client_height": snapshot.get("clientHeight"),
        "item_count": len(notes),
        "notes": notes,
    }


def format_txt(payload: dict[str, object]) -> str:
    lines = [
        "Xiaohongshu Creator Note Manager Export",
        f"Exported at: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Page title: {payload.get('title') or ''}",
        f"Page URL: {payload.get('url') or ''}",
        f"Note count: {payload.get('item_count')}",
        f"Scroll: {payload.get('scroll_top')} / {payload.get('scroll_height')} (client {payload.get('client_height')})",
        "Metric columns are exported in the same left-to-right order as the page.",
        "",
    ]

    for index, note in enumerate(payload.get("notes") or [], start=1):
        meta = [f"round {note.get('round')}"]
        if note.get("duration_or_count"):
            meta.append(f"badge {note.get('duration_or_count')}")
        if note.get("visibility"):
            meta.append(str(note.get("visibility")))
        lines.append(f"--- NOTE {index:03d} | {' | '.join(meta)} ---")
        lines.append(f"title: {note.get('title') or ''}")
        lines.append(f"publish_time: {note.get('publish_time') or ''}")
        lines.append(f"metrics: {' | '.join(note.get('metrics') or [])}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    output = Path(args.output).expanduser() if args.output else None

    ws_endpoint = resolve_ws_endpoint(args.cdp_url)
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(ws_endpoint)
        page: Page | None = None
        try:
            page = open_target_page(browser, args)
            payload = collect(page, args)
            text = format_txt(payload)
            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(text, encoding="utf-8-sig")
                print(f"Wrote {payload.get('item_count')} items to {output}", file=sys.stderr)
            else:
                print(text, end="")
                sys.stdout.flush()
            page.wait_for_timeout(max(0, args.close_wait_ms))
        finally:
            if page and not page.is_closed():
                page.close()
            browser.close()

    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())

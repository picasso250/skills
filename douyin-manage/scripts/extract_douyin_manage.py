#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import Browser, Page, sync_playwright


DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_URL_CONTAINS = "/creator-micro/content/manage"


EXTRACT_JS = r"""
() => {
  const clean = (value) => {
    if (value === null || value === undefined) return null;
    const text = String(value).replace(/\u00a0/g, " ").trim();
    return text || null;
  };

  const cardSelector = '[class*="video-card-zQ02ng"]';
  const cards = Array.from(document.querySelectorAll(cardSelector));

  const activeTab = Array.from(document.querySelectorAll('[class*="tab-item-"]'))
    .find((node) => node.className.includes('active-'));

  const totalText = Array.from(document.querySelectorAll('*'))
    .map((node) => clean(node.innerText))
    .find((text) => text && /^共\s*\d+\s*个作品$/.test(text));

  const items = cards.map((card, index) => {
    const metricItems = Array.from(card.querySelectorAll('[class*="metric-item-u1CAYE"]'));
    const metrics = {};
    for (const metric of metricItems) {
      const label = clean(metric.querySelector('[class*="metric-label-"]')?.innerText);
      const value = clean(metric.querySelector('[class*="metric-value-"]')?.innerText);
      if (label) {
        metrics[label] = value;
      }
    }

    const operations = Array.from(card.querySelectorAll('[class*="edit-btn-"], [class*="op-btn-ILGveS"]'))
      .map((node) => clean(node.innerText))
      .filter(Boolean);

    return {
      index,
      card_class: clean(card.className),
      duration_or_count: clean(card.querySelector('[class*="badge-"]')?.innerText),
      privacy: clean(card.querySelector('[class*="private-mark-"]')?.innerText),
      title: clean(card.querySelector('[class*="info-title-text-"]')?.innerText),
      publish_time: clean(card.querySelector('[class*="info-time-"]')?.innerText),
      status: clean(card.querySelector('[class*="info-status-"]')?.innerText),
      operations: Array.from(new Set(operations)),
      metrics,
      raw_text: clean(card.innerText),
    };
  });

  return {
    page_title: clean(document.title),
    page_url: location.href,
    active_tab: clean(activeTab?.innerText),
    total_count_text: totalText,
    visible_card_count: items.length,
    items,
  };
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract visible work list data from Douyin Creator Center content manage page."
    )
    parser.add_argument("--cdp-url", default=DEFAULT_CDP_URL, help="Chrome CDP HTTP endpoint")
    parser.add_argument(
        "--url-contains",
        default=DEFAULT_URL_CONTAINS,
        help="Match the open tab whose URL contains this substring",
    )
    parser.add_argument("--exact-url", help="Match an exact page URL instead of --url-contains")
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument("--output", help="Write output to this file instead of stdout")
    parser.add_argument("--limit", type=int, help="Keep only the first N extracted items")
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


def extract_snapshot(page: Page) -> dict[str, object]:
    snapshot = page.evaluate(EXTRACT_JS)
    if not isinstance(snapshot, dict):
        raise RuntimeError("Unexpected extraction result")
    return snapshot


def collect_items(page: Page, args: argparse.Namespace) -> dict[str, object]:
    snapshot = extract_snapshot(page)
    items = list(snapshot["items"])
    if args.limit is not None:
        items = items[: args.limit]

    return {
        "page_title": snapshot.get("page_title"),
        "page_url": snapshot.get("page_url"),
        "active_tab": snapshot.get("active_tab"),
        "total_count_text": snapshot.get("total_count_text"),
        "visible_card_count": snapshot.get("visible_card_count"),
        "extracted_count": len(items),
        "items": items,
    }


def csv_rows(payload: dict[str, object]) -> tuple[list[str], list[dict[str, str]]]:
    items = payload["items"]
    metric_names: list[str] = []
    for item in items:
        for name in item.get("metrics", {}).keys():
            if name not in metric_names:
                metric_names.append(name)

    fieldnames = [
        "page_title",
        "page_url",
        "active_tab",
        "total_count_text",
        "index",
        "duration_or_count",
        "privacy",
        "title",
        "publish_time",
        "status",
        "operations",
    ] + [f"metric_{name}" for name in metric_names]

    rows: list[dict[str, str]] = []
    for item in items:
        row = {
            "page_title": str(payload.get("page_title") or ""),
            "page_url": str(payload.get("page_url") or ""),
            "active_tab": str(payload.get("active_tab") or ""),
            "total_count_text": str(payload.get("total_count_text") or ""),
            "index": str(item.get("index") or ""),
            "duration_or_count": str(item.get("duration_or_count") or ""),
            "privacy": str(item.get("privacy") or ""),
            "title": str(item.get("title") or ""),
            "publish_time": str(item.get("publish_time") or ""),
            "status": str(item.get("status") or ""),
            "operations": " | ".join(item.get("operations") or []),
        }
        metrics = item.get("metrics") or {}
        for name in metric_names:
            row[f"metric_{name}"] = str(metrics.get(name) or "")
        rows.append(row)
    return fieldnames, rows


def write_json(payload: dict[str, object], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        output.write_text(text, encoding="utf-8")
        return
    print(text)


def write_csv_file(payload: dict[str, object], output: Path | None) -> None:
    fieldnames, rows = csv_rows(payload)
    if output:
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)


def main() -> int:
    args = parse_args()
    output = Path(args.output) if args.output else None
    ws_endpoint = resolve_ws_endpoint(args.cdp_url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(ws_endpoint)
        try:
            page = find_target_page(browser, args)
            payload = collect_items(page, args)
        finally:
            browser.close()

    if args.format == "json":
        write_json(payload, output)
    else:
        write_csv_file(payload, output)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())

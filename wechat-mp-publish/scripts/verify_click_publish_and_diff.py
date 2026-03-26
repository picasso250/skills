#!/usr/bin/env python3
"""
Reuse the WeChat article-editor tab, click publish, wait 2.5s, and diff DOM snapshots.
"""

from __future__ import annotations

import json
import logging
import random
import sys
from urllib.request import urlopen

from playwright.sync_api import Error, Page, sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
EDITOR_URL_KEYWORD = "media/appmsg_edit"
PUBLISH_TEXT = "发表"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


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


def snapshot_dom(page: Page) -> list[dict[str, object]]:
    expression = r"""
(() => {
  const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
  const makePath = (el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 6) {
      let part = node.tagName.toLowerCase();
      if (node.id) {
        part += `#${node.id}`;
        parts.unshift(part);
        break;
      }
      if (node.classList.length) {
        part += '.' + Array.from(node.classList).slice(0, 3).join('.');
      }
      const parent = node.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
        if (siblings.length > 1) {
          part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        }
      }
      parts.unshift(part);
      node = node.parentElement;
    }
    return parts.join(' > ');
  };

  const nodes = Array.from(document.querySelectorAll('body *'));
  const results = [];
  for (const el of nodes) {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    const visible = style.display !== 'none' &&
      style.visibility !== 'hidden' &&
      rect.width > 0 &&
      rect.height > 0;
    if (!visible) continue;

    const text = normalize(el.innerText || el.textContent);
    const role = el.getAttribute('role') || '';
    const title = el.getAttribute('title') || '';
    const ariaLabel = el.getAttribute('aria-label') || '';
    if (!text && !role && !title && !ariaLabel) continue;

    results.push({
      key: makePath(el),
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      className: normalize(el.className),
      role,
      title,
      ariaLabel,
      text: text.slice(0, 200),
      rect: {
        x: Number(rect.x.toFixed(2)),
        y: Number(rect.y.toFixed(2)),
        width: Number(rect.width.toFixed(2)),
        height: Number(rect.height.toFixed(2))
      }
    });
  }
  return results;
})()
"""
    return page.evaluate(expression)


def diff_snapshots(
    before: list[dict[str, object]], after: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    before_map = {str(item["key"]): item for item in before}
    after_map = {str(item["key"]): item for item in after}

    added = [after_map[key] for key in after_map.keys() - before_map.keys()]
    removed = [before_map[key] for key in before_map.keys() - after_map.keys()]

    changed: list[dict[str, object]] = []
    for key in before_map.keys() & after_map.keys():
        before_item = before_map[key]
        after_item = after_map[key]
        if before_item.get("text") != after_item.get("text"):
            changed.append(
                {
                    "key": key,
                    "before_text": before_item.get("text", ""),
                    "after_text": after_item.get("text", ""),
                    "tag": after_item.get("tag", ""),
                }
            )
    return added, removed, changed


def main() -> None:
    setup_logging()

    try:
        browser_ws = resolve_browser_ws_endpoint(DEFAULT_CDP_URL)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(browser_ws)
            try:
                page = find_editor_page(browser)
                logging.info("Reusing editor tab: %s", page.url)
                page.bring_to_front()
                locator = page.get_by_text(PUBLISH_TEXT, exact=True).first
                locator.wait_for(state="visible", timeout=10 * 1000)
                box = locator.bounding_box()
                if not box:
                    raise RuntimeError("Publish button was found but had no bounding box.")
                center_x, center_y, click_x, click_y = random_point_in_center_band(box)
                before_snapshot = snapshot_dom(page)
                before_url = page.url
                wait_with_jitter(page, 1.0, "pre-click pause")
                page.mouse.click(click_x, click_y)
                logging.info("Waiting 2.50s for post-click DOM diff")
                page.wait_for_timeout(2500)
                after_snapshot = snapshot_dom(page)
                after_url = page.url
                added, removed, changed = diff_snapshots(before_snapshot, after_snapshot)

                print(f"Editor tab title: {page.title()}")
                print(f"Editor tab url: {before_url}")
                print(f"Found text: {PUBLISH_TEXT}")
                print(
                    f"Bounding box: x={box['x']:.2f}, y={box['y']:.2f}, width={box['width']:.2f}, height={box['height']:.2f}"
                )
                print(f"Click point: x={center_x:.2f}, y={center_y:.2f}")
                print(f"Actual click: x={click_x:.2f}, y={click_y:.2f}")
                print(f"URL before click: {before_url}")
                print(f"URL after 2.5s: {after_url}")
                print(f"DOM nodes before: {len(before_snapshot)}")
                print(f"DOM nodes after: {len(after_snapshot)}")
                print(f"Added nodes: {len(added)}")
                print(f"Removed nodes: {len(removed)}")
                print(f"Changed text nodes: {len(changed)}")
                print("Added node samples:")
                print(json.dumps(added[:20], ensure_ascii=False, indent=2))
                print("Removed node samples:")
                print(json.dumps(removed[:20], ensure_ascii=False, indent=2))
                print("Changed text node samples:")
                print(json.dumps(changed[:20], ensure_ascii=False, indent=2))
            finally:
                browser.close()
    except Error as exc:
        logging.error("Failed while clicking publish in the reused editor tab: %s", exc)
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

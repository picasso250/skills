import argparse
import asyncio
import difflib
import json
import random
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

from playwright.async_api import async_playwright


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser-ws-endpoint", default="http://localhost:9222")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--url", default="https://gemini.google.com/app")
    parser.add_argument("--iterations", type=int, default=120)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


async def random_wait(base_seconds):
    await asyncio.sleep(base_seconds + random.uniform(-0.5, 0.5))


async def move_mouse_to_locator(page, locator):
    box = await locator.bounding_box()
    if box is None:
        raise RuntimeError("Locator has no bounding box.")
    x = box["x"] + box["width"] / 2 + random.uniform(-box["width"] / 8, box["width"] / 8)
    y = box["y"] + box["height"] / 2 + random.uniform(-box["height"] / 8, box["height"] / 8)
    await page.mouse.move(x, y)
    return box, x, y


async def click_locator_physically(page, locator):
    await random_wait(1)
    box, x, y = await move_mouse_to_locator(page, locator)
    await page.mouse.click(x, y)
    return box, x, y


async def type_text_physically(page, locator, text):
    await click_locator_physically(page, locator)
    for char in text:
        await asyncio.sleep(random.uniform(0.1, 0.2))
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.1, 0.2))
    await page.keyboard.press("Tab")


def summarize_diff(previous_html, current_html):
    diff_lines = list(
        difflib.unified_diff(
            previous_html.splitlines(),
            current_html.splitlines(),
            fromfile="previous",
            tofile="current",
            lineterm="",
        )
    )
    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    return diff_lines, added, removed


async def main():
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "diff_summary.jsonl"
    latest_path = output_dir / "latest_body.html"

    async with async_playwright() as p:
        browser_ws_endpoint = args.browser_ws_endpoint
        if browser_ws_endpoint.startswith("http://") or browser_ws_endpoint.startswith("https://"):
            version_url = f"{browser_ws_endpoint.rstrip('/')}/json/version"
            with urlopen(version_url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            browser_ws_endpoint = payload["webSocketDebuggerUrl"]

        browser = await p.chromium.connect_over_cdp(browser_ws_endpoint)
        context = browser.contexts[0]
        page = await context.new_page()

        print(f"OPENING_URL:{args.url}")
        await page.goto(args.url, timeout=60000)
        await random_wait(5)

        create_img_btn = page.get_by_text("Create image", exact=False).first
        if await create_img_btn.count() == 0:
            create_img_btn = page.get_by_text("创建图片", exact=False).first
        if await create_img_btn.count() > 0:
            await click_locator_physically(page, create_img_btn)
            print("CLICKED_CREATE_IMAGE:true")
            await page.wait_for_timeout(1000)
        else:
            print("CLICKED_CREATE_IMAGE:false")

        input_locator = page.locator("div[role='textbox']").first
        await input_locator.wait_for(state="visible", timeout=15000)
        await type_text_physically(page, input_locator, args.prompt)
        print(f"PROMPT_LENGTH:{len(args.prompt)}")

        send_btn = page.locator("button[aria-label*='Send'], button[aria-label*='发送']").first
        await send_btn.wait_for(state="visible", timeout=10000)
        await click_locator_physically(page, send_btn)
        print("PROMPT_SENT:true")

        previous_html = await page.locator("body").inner_html()
        latest_path.write_text(previous_html, encoding="utf-8")

        with summary_path.open("w", encoding="utf-8") as summary_file:
            for index in range(1, args.iterations + 1):
                await asyncio.sleep(args.interval_seconds)
                current_html = await page.locator("body").inner_html()
                diff_lines, added, removed = summarize_diff(previous_html, current_html)

                diff_path = output_dir / f"diff_{index:03d}.patch"
                diff_path.write_text("\n".join(diff_lines) + ("\n" if diff_lines else ""), encoding="utf-8")
                latest_path.write_text(current_html, encoding="utf-8")

                record = {
                    "index": index,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "changed": bool(diff_lines),
                    "added_lines": added,
                    "removed_lines": removed,
                    "diff_line_count": len(diff_lines),
                    "diff_file": str(diff_path),
                }
                summary_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                summary_file.flush()

                print(
                    f"DIFF {index:03d} changed={record['changed']} "
                    f"added={added} removed={removed} diff_lines={len(diff_lines)}"
                )

                previous_html = current_html

        print(f"SUMMARY_PATH:{summary_path}")
        print(f"LATEST_HTML_PATH:{latest_path}")


if __name__ == "__main__":
    asyncio.run(main())

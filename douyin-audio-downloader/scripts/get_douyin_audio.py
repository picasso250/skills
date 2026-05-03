import argparse
import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen

import requests
from playwright.async_api import async_playwright


DEFAULT_CHUNK_BYTES = 4 * 1024 * 1024


def get_ws_url(host: str = "localhost", port: int = 9222) -> str:
    url = f"http://{host}:{port}/json/version"
    with urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    ws_url = data.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError(f"No webSocketDebuggerUrl from {url}")
    return ws_url


def safe_filename(value: str, fallback: str = "douyin_audio") -> str:
    value = value.replace(" - 抖音", "")
    value = re.sub(r'[\\/:*?"<>|]+', "_", value)
    value = re.sub(r"\s+", " ", value).strip()
    return (value[:120] or fallback)


def clean_headers(headers: dict[str, str]) -> dict[str, str]:
    # Let requests set transport-specific headers; keep browser identity and CORS context.
    drop = {"host", "connection", "if-range", "range", "content-length"}
    return {k: v for k, v in headers.items() if k.lower() not in drop}


def target_in_page(url: str, page_url: str) -> bool:
    m = re.search(r"/video/(\d+)", url)
    if m:
        return m.group(1) in page_url
    return url.rstrip("/") in page_url.rstrip("/")


async def find_or_open_page(browser, url: str):
    for context in browser.contexts:
        for page in context.pages:
            if target_in_page(url, page.url):
                return page

    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = await context.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    return page


async def capture_audio_request(page, url: str, reload_page: bool, wait_ms: int) -> tuple[str, dict[str, str]]:
    hit: dict[str, object] = {}

    async def on_request(request):
        request_url = request.url
        if hit:
            return
        if re.search(r"media-audio|mp4a", request_url, re.I):
            headers = await request.all_headers()
            hit.update({"url": request_url, "headers": headers})

    page.on("request", on_request)

    if reload_page:
        if target_in_page(url, page.url):
            await page.reload(wait_until="domcontentloaded", timeout=60_000)
        else:
            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)

    loops = max(1, wait_ms // 500)
    for _ in range(loops):
        if hit:
            break
        await page.wait_for_timeout(500)

    if hit:
        return str(hit["url"]), clean_headers(dict(hit["headers"]))

    resource_urls = await page.evaluate(
        r"""() => [...new Set(
            performance.getEntriesByType('resource')
              .map(e => e.name)
              .filter(u => /media-audio|mp4a/i.test(u))
        )]"""
    )
    if not resource_urls:
        raise RuntimeError("No Douyin audio stream request found. Open/play the video and retry.")

    user_agent = await page.evaluate("navigator.userAgent")
    fallback_headers = {
        "accept": "*/*",
        "accept-encoding": "identity",
        "accept-language": "zh-CN,zh;q=0.7",
        "origin": "https://www.douyin.com",
        "referer": "https://www.douyin.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": user_agent,
    }
    return resource_urls[-1], fallback_headers


def probe_total(session: requests.Session, url: str, headers: dict[str, str]) -> tuple[int | None, str | None]:
    probe_headers = dict(headers)
    probe_headers["range"] = "bytes=0-0"
    response = session.get(url, headers=probe_headers, timeout=30)
    print(
        "probe:",
        response.status_code,
        response.headers.get("content-range"),
        response.headers.get("content-length"),
        response.headers.get("content-type"),
    )
    if response.status_code not in (200, 206):
        print(response.text[:500])
        response.raise_for_status()

    content_range = response.headers.get("content-range", "")
    match = re.search(r"/([0-9]+)$", content_range)
    if match:
        return int(match.group(1)), response.headers.get("content-type")
    return None, response.headers.get("content-type")


def download_audio(url: str, headers: dict[str, str], output_path: Path, chunk_bytes: int) -> None:
    session = requests.Session()
    total, _ = probe_total(session, url, headers)

    if total is None:
        response = session.get(url, headers=headers, timeout=120)
        if response.status_code not in (200, 206):
            print(response.text[:500])
            response.raise_for_status()
        output_path.write_bytes(response.content)
        return

    with output_path.open("wb") as file:
        position = 0
        while position < total:
            end = min(position + chunk_bytes - 1, total - 1)
            range_headers = dict(headers)
            range_headers["range"] = f"bytes={position}-{end}"
            response = session.get(url, headers=range_headers, timeout=60)
            if response.status_code not in (200, 206):
                print(f"failed chunk {position}-{end}: {response.status_code}")
                print(response.text[:500])
                response.raise_for_status()
            if not response.content:
                raise RuntimeError(f"Empty chunk at byte {position}")
            file.write(response.content)
            position += len(response.content)
            print(f"downloaded {position}/{total}")


def verify_audio(path: Path) -> None:
    if not shutil.which("ffprobe"):
        print("ffprobe not found; skipped media verification")
        return
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size,format_name",
        "-show_entries",
        "stream=codec_type,codec_name",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        print(result.stderr.strip())
        raise RuntimeError("ffprobe verification failed")
    print(result.stdout.strip())


async def run(args: argparse.Namespace) -> Path:
    ws_url = args.ws or get_ws_url(args.host, args.port)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(ws_url)
        page = await find_or_open_page(browser, args.url)
        await page.bring_to_front()
        audio_url, headers = await capture_audio_request(
            page=page,
            url=args.url,
            reload_page=not args.no_reload,
            wait_ms=args.wait_ms,
        )
        title = await page.title()

    output_path = output_dir / f"{safe_filename(title)}.m4a"
    print("title:", title)
    print("audio_url:", audio_url[:220] + ("..." if len(audio_url) > 220 else ""))
    download_audio(audio_url, headers, output_path, args.chunk_bytes)
    print("saved:", output_path.resolve())
    print("size:", output_path.stat().st_size)
    if not args.no_verify:
        verify_audio(output_path)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download audio from a Douyin video via an existing CDP browser session.")
    parser.add_argument("url", help="Douyin video URL, e.g. https://www.douyin.com/video/7626360252560117034")
    parser.add_argument("--output-dir", default="downloads", help="Directory for the .m4a output. Default: downloads")
    parser.add_argument("--host", default="localhost", help="CDP host. Default: localhost")
    parser.add_argument("--port", type=int, default=9222, help="CDP port. Default: 9222")
    parser.add_argument("--ws", help="Browser websocket URL. Overrides --host/--port.")
    parser.add_argument("--no-reload", action="store_true", help="Do not reload the target page before capturing requests.")
    parser.add_argument("--wait-ms", type=int, default=15_000, help="How long to wait for media requests. Default: 15000")
    parser.add_argument("--chunk-bytes", type=int, default=DEFAULT_CHUNK_BYTES, help="Range download chunk size. Default: 4 MiB")
    parser.add_argument("--no-verify", action="store_true", help="Skip ffprobe verification.")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))

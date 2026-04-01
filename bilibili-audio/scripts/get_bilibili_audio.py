import argparse
import asyncio
import base64
import os

from playwright.async_api import async_playwright


async def get_bilibili_audio(bvid, ws_url=None):
    async with async_playwright() as p:
        if ws_url:
            print(f"Connecting to WS: {ws_url}")
            browser = await p.chromium.connect_over_cdp(ws_url)
        else:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")

        target_page = None
        for context in browser.contexts:
            for page in context.pages:
                if bvid in page.url or "bilibili.com/video/" in page.url:
                    target_page = page
                    break
            if target_page:
                break

        if not target_page:
            raise RuntimeError("No matching Bilibili video page is open in the current browser session.")

        title = await target_page.title()
        print(f"Using page: {title}")

        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        print("Fetching video metadata...")
        video_info = await target_page.evaluate(f"fetch('{api_url}').then(res => res.json())")

        if video_info.get("code") != 0:
            raise RuntimeError(f"Failed to fetch video metadata: {video_info.get('message')}")

        video_data = video_info["data"]
        cid = video_data["cid"]
        title = video_data["title"]
        print(f"Video title: {title}")

        play_url_api = (
            "https://api.bilibili.com/x/player/wbi/playurl"
            f"?bvid={bvid}&cid={cid}&qn=16&fnver=0&fnval=16&fourk=0"
        )
        print("Fetching playback info...")
        play_info = await target_page.evaluate(f"fetch('{play_url_api}').then(res => res.json())")

        if play_info.get("code") != 0:
            raise RuntimeError(f"Failed to fetch playback info: {play_info.get('message')}")

        dash = play_info["data"].get("dash", {})
        if not dash or not dash.get("audio"):
            raise RuntimeError("No audio stream found in playback info.")

        best_audio = max(dash["audio"], key=lambda x: x.get("bandwidth", 0))
        audio_url = best_audio.get("baseUrl") or best_audio.get("base_url")
        if not audio_url:
            raise RuntimeError("No downloadable audio URL found.")

        print("Extracting audio bytes through the browser session...")
        download_script = """
        (async (url) => {
            const resp = await fetch(url, {
                headers: {
                    Referer: 'https://www.bilibili.com/'
                }
            });
            const buffer = await resp.arrayBuffer();
            const bytes = new Uint8Array(buffer);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            return btoa(binary);
        })(arguments[0])
        """
        base64_data = await target_page.evaluate(download_script, audio_url)
        audio_data = base64.b64decode(base64_data)

        safe_title = "".join([c for c in title if c.isalnum() or c in (" ", ".", "_")]).strip()
        output_file = f"{safe_title}.m4a"

        with open(output_file, "wb") as f:
            f.write(audio_data)

        size = os.path.getsize(output_file)
        print(f"Saved audio to: {output_file} ({size} bytes)")
        return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Bilibili audio via an existing browser session")
    parser.add_argument("bvid", help="Bilibili BV ID")
    parser.add_argument("--ws", help="WebSocket URL for CDP")
    args = parser.parse_args()

    asyncio.run(get_bilibili_audio(args.bvid, args.ws))

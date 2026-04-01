import argparse
import asyncio
import base64
import json
import os
import sys
from urllib.request import urlopen
from playwright.async_api import async_playwright

def get_ws_url(host="localhost", port=9222):
    """Auto-detect the browser-wide WebSocket URL."""
    url = f"http://{host}:{port}/json/version"
    try:
        with urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ws_url = data.get("webSocketDebuggerUrl")
            if ws_url:
                print(f"Auto-detected browser WS URL: {ws_url}")
                return ws_url
    except Exception as e:
        print(f"Failed to auto-detect browser WS URL from /json/version: {e}")
    return None

async def get_bilibili_audio(bvid, ws_url=None):
    if not ws_url:
        ws_url = get_ws_url()

    async with async_playwright() as p:
        if ws_url:
            print(f"Connecting to WS: {ws_url}")
            browser = await p.chromium.connect_over_cdp(ws_url)
        else:
            print("Fallback connecting to http://localhost:9222")
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
        if not dash or not dash.get("audio") or not dash.get("video"):
            raise RuntimeError("Required audio or video streams not found in playback info.")

        # 获取最佳音频流
        best_audio = max(dash["audio"], key=lambda x: x.get("bandwidth", 0))
        audio_url = best_audio.get("baseUrl") or best_audio.get("base_url")
        
        # 获取最佳视频流
        best_video = max(dash["video"], key=lambda x: x.get("bandwidth", 0))
        video_url = best_video.get("baseUrl") or best_video.get("base_url")

        if not audio_url or not video_url:
            raise RuntimeError("No downloadable URLs found for audio or video.")

        download_script = """
        async (url) => {
            const resp = await fetch(url, {
                headers: {
                    Referer: 'https://www.bilibili.com/'
                }
            });
            const buffer = await resp.arrayBuffer();
            const bytes = new Uint8Array(buffer);
            let binary = '';
            const chunkSize = 16384; 
            for (let i = 0; i < bytes.byteLength; i += chunkSize) {
                const chunk = bytes.slice(i, i + chunkSize);
                binary += String.fromCharCode.apply(null, chunk);
            }
            return btoa(binary);
        }
        """

        print("Downloading audio through the browser session...")
        audio_b64 = await target_page.evaluate(download_script, audio_url)
        audio_data = base64.b64decode(audio_b64)

        print("Downloading video through the browser session...")
        video_b64 = await target_page.evaluate(download_script, video_url)
        video_data = base64.b64decode(video_b64)

        safe_title = "".join([c for c in title if c.isalnum() or c in (" ", ".", "_")]).strip()
        audio_tmp = f"{safe_title}_tmp_audio.m4a"
        video_tmp = f"{safe_title}_tmp_video.m4s"
        final_file = f"{safe_title}.mp4"

        with open(audio_tmp, "wb") as f:
            f.write(audio_data)
        with open(video_tmp, "wb") as f:
            f.write(video_data)

        print(f"Muxing audio and video into {final_file}...")
        import subprocess
        # 使用 ffmpeg 合并音视频流
        cmd = f'ffmpeg -i "{video_tmp}" -i "{audio_tmp}" -c copy "{final_file}" -y'
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if process.returncode == 0:
            print(f"Successfully saved combined video to: {final_file}")
            # 清理临时文件
            os.remove(audio_tmp)
            os.remove(video_tmp)
        else:
            print(f"Ffmpeg muxing failed: {process.stderr}")
            print(f"Kept temporary files: {audio_tmp}, {video_tmp}")

        return final_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Bilibili audio via an existing browser session")
    parser.add_argument("bvid", help="Bilibili BV ID")
    parser.add_argument("--ws", help="WebSocket URL for CDP")
    args = parser.parse_args()

    asyncio.run(get_bilibili_audio(args.bvid, args.ws))

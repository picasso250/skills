import argparse
import asyncio
import os
import random
import subprocess
import tempfile
import time
from pathlib import Path
from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).resolve().parent
LOCK_PATH = Path(tempfile.gettempdir()) / "gemini_img_gen_clipboard.lock"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate an image in Gemini and save the copied result from the clipboard."
    )
    parser.add_argument("prompt", help="Prompt to send to Gemini image generation")
    parser.add_argument("output_path", help="Target path for the saved image")
    parser.add_argument("--keep-tab", action="store_true", help="Keep the browser tab open after generation")
    return parser.parse_args()


class FileLock:
    def __init__(self, path):
        self.path = Path(path)
        self.fd = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(self.fd, f"{os.getpid()}\n".encode("ascii"))
                break
            except FileExistsError:
                time.sleep(0.5)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


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
    box, x, y = await move_mouse_to_locator(page, locator)
    await random_wait(1)
    await page.mouse.click(x, y)
    return box, x, y


async def wait_for_full_size_download_button(page, timeout_seconds=120):
    selector = "button[aria-label='Download full size image']"
    for second in range(1, timeout_seconds + 1):
        locator = page.locator(selector).last
        if await locator.count() > 0 and await locator.is_visible():
            print(f"DOWNLOAD_BUTTON_READY_AT:{second}s")
            await page.wait_for_timeout(3000)
            return locator
        await page.wait_for_timeout(1000)
    raise RuntimeError("Timed out waiting for full size image button.")

def save_clipboard_image(output_path):
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ps_script = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$path = [System.IO.Path]::GetFullPath($env:CLIPBOARD_IMAGE_OUTPUT_PATH)
$image = [System.Windows.Forms.Clipboard]::GetImage()
if ($null -eq $image) {
    throw "Clipboard does not contain an image."
}
$extension = [System.IO.Path]::GetExtension($path).ToLowerInvariant()
$format = switch ($extension) {
    ".jpg" { [System.Drawing.Imaging.ImageFormat]::Jpeg }
    ".jpeg" { [System.Drawing.Imaging.ImageFormat]::Jpeg }
    ".bmp" { [System.Drawing.Imaging.ImageFormat]::Bmp }
    ".gif" { [System.Drawing.Imaging.ImageFormat]::Gif }
    ".tiff" { [System.Drawing.Imaging.ImageFormat]::Tiff }
    ".png" { [System.Drawing.Imaging.ImageFormat]::Png }
    default { [System.Drawing.Imaging.ImageFormat]::Png }
}
$image.Save($path, $format)
Write-Output $path
"""

    env = os.environ.copy()
    env["CLIPBOARD_IMAGE_OUTPUT_PATH"] = str(output_path)
    result = subprocess.run(
        ["powershell", "-Sta", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Failed to save clipboard image.")

    return output_path


async def run(prompt, output_path, keep_tab=False):
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    save_path = Path(output_path).resolve()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        # Reuse existing context to keep login session
        context = browser.contexts[0]
        page = await context.new_page()

        try:
            print(f"Navigating to Gemini...")
            await page.goto("https://gemini.google.com/app", timeout=60000)

            # Step 1: Wait 10s for page to settle
            print("Waiting 10s for page to settle...")
            await page.wait_for_timeout(10000)

            # Step 2: Click 'Create image' button
            print("Clicking 'Create image' button...")
            # Note: get_by_text returns a Locator (not awaitable)
            create_img_btn = page.get_by_text("Create image", exact=False).first

            # Use count() or wait_for to check visibility
            if await create_img_btn.count() == 0:
                create_img_btn = page.get_by_text("创建图片", exact=False).first

            if await create_img_btn.count() > 0:
                await create_img_btn.click()
                print("Clicked 'Create image'.")
                # Step 3: Wait 1s
                await page.wait_for_timeout(1000)
            else:
                print("Could not find 'Create image' button. Proceeding anyway...")

            # Step 4: Input prompt
            print(f"Filling prompt: {prompt}")
            input_selector = "div[role='textbox']"
            await page.wait_for_selector(input_selector, timeout=15000)
            await page.fill(input_selector, prompt)

            await page.wait_for_timeout(1000)

            send_btn_selector = "button[aria-label*='Send'], button[aria-label*='发送']"
            await page.wait_for_selector(send_btn_selector, timeout=10000)
            await page.click(send_btn_selector)
            print("Prompt sent.")

            # Step 5: Poll for the full-size download button
            print("Waiting for full-size image button...")

            # Step 6: Hover image actions and copy to clipboard
            print("Attempting to copy generated image to clipboard...")
            copy_btn_selector = (
                "button.copy-button[aria-label='Copy image'], "
                "button.copy-button[mattooltip='Copy image'], "
                "button[aria-label*='Copy image'], "
                "button[aria-label*='复制']"
            )

            # Scroll to bottom to ensure elements are updated
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            try:
                download_btn = await wait_for_full_size_download_button(page)
                print(f"Waiting for clipboard lock: {LOCK_PATH}")
                with FileLock(LOCK_PATH):
                    print(f"Clipboard lock acquired: {LOCK_PATH}")
                    await page.bring_to_front()
                    await random_wait(1)
                    await move_mouse_to_locator(page, download_btn)
                    await page.wait_for_timeout(1200)

                    copy_btn = page.locator(copy_btn_selector).last
                    await copy_btn.wait_for(state="visible", timeout=10000)
                    await click_locator_physically(page, copy_btn)

                    last_error = None
                    final_path = None
                    for _ in range(5):
                        await page.wait_for_timeout(1000)
                        try:
                            final_path = save_clipboard_image(save_path)
                            break
                        except Exception as clipboard_error:
                            last_error = clipboard_error

                    if final_path is None:
                        raise last_error

                print(f"RESULT_IMAGE_PATH:{final_path}")
            except Exception as e:
                print(f"Failed to copy image: {e}")
                # Use a specific fail name based on the target if possible
                fail_path = save_path.with_suffix(".png").with_name(save_path.stem + "_fail.png")
                await page.screenshot(path=fail_path)

        except Exception as e:
            print(f"Error in Gemini script: {e}")
            error_path = save_path.with_suffix(".png").with_name(save_path.stem + "_error.png")
            await page.screenshot(path=error_path)
        finally:
            if not keep_tab:
                await page.close()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.prompt, args.output_path, args.keep_tab))

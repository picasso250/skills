import asyncio
from playwright.async_api import async_playwright
import os
import sys
import re

def parse_tags(content):
    tags = re.findall(r'#(\S+)', content)
    content_without_tags = re.sub(r'#\S+\s*', '', content).strip()
    return content_without_tags, tags

async def run(image_path, title, content):
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = await context.new_page()
        
        try:
            print("Opening XHS image publish page directly...")
            await page.goto("https://creator.xiaohongshu.com/publish/publish?from=menu&target=image")
            await page.wait_for_load_state("networkidle")

            await page.set_input_files("input[type='file']", os.path.abspath(image_path))
            print(f"Uploaded image: {image_path}")
            await asyncio.sleep(8)

            title_input = await page.wait_for_selector("input[placeholder*='填写标题']", timeout=10000)
            await title_input.fill(title)
            
            found_editor = False
            for frame in page.frames:
                editor = await frame.query_selector("div#post-textarea, .content-input, [contenteditable='true']")
                if editor:
                    await editor.click()
                    await frame.evaluate(f"el => el.innerText = `{content}`", editor)
                    
                    await frame.evaluate("el => {"
                        "const range = document.createRange();"
                        "range.selectNodeContents(el);"
                        "range.collapse(false);"
                        "const sel = window.getSelection();"
                        "sel.removeAllRanges();"
                        "sel.addRange(range);"
                        "el.focus();"
                    "}", editor)
                    
                    print("Content filled and cursor moved to end.")
                    found_editor = True
                    break
            
            if not found_editor:
                print("Fallback fill via evaluate on main page")
                await page.evaluate(f"document.querySelector('[contenteditable=\"true\"]').innerText = `{content}`")

            content_without_tags, tags = parse_tags(content)
            
            for tag in tags:
                print(f"Adding tag: #{tag}")
                await page.keyboard.type(f"#{tag}", delay=100)
                await asyncio.sleep(2)
                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(0.3)
                await page.keyboard.press("ArrowUp")
                await asyncio.sleep(0.3)
                await page.keyboard.press("Enter")
                print(f"Tag #{tag} added.")
                await asyncio.sleep(1)

            publish_btn = await page.wait_for_selector("button:has-text('发布')", timeout=5000)
            await publish_btn.click()
            print("Clicked publish button.")
            await asyncio.sleep(10)

            print("Navigating to Note Manager...")
            await page.goto("https://creator.xiaohongshu.com/new/note-manager")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            screenshot_path = os.path.abspath("xhs_publish_proof.png")
            await page.screenshot(path=screenshot_path)
            print(f"RESULT_SCREENSHOT_PATH:{screenshot_path}")

        except Exception as e:
            print(f"Error in XHS script: {e}")
        finally:
            await page.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python post_to_xhs.py <image_path> <title> <content>")
    else:
        asyncio.run(run(sys.argv[1], sys.argv[2], sys.argv[3]))

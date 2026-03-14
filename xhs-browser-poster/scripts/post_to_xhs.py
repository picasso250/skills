import asyncio
from playwright.async_api import async_playwright
import os
import sys
import re

def parse_tags(content):
    tags = []
    parts = content.split()
    i = len(parts) - 1
    while i >= 0 and parts[i].startswith('#'):
        tags.insert(0, parts[i][1:])
        i -= 1
    content_without_tags = ' '.join(parts[:i+1]).strip()
    return content_without_tags, tags

async def run(image_path, title, content):
    if len(title) > 20:
        print(f"Error: Title '{title}' exceeds 20 characters (length: {len(title)}). Please provide a shorter title.")
        return

    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = await context.new_page()
        
        try:
            content_without_tags, tags = parse_tags(content)

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
                    # Only fill the content WITHOUT tags
                    await frame.evaluate(f"el => el.innerText = `{content_without_tags}\n\n`", editor)
                    
                    await frame.evaluate("el => {"
                        "const range = document.createRange();"
                        "range.selectNodeContents(el);"
                        "range.collapse(false);"
                        "const sel = window.getSelection();"
                        "sel.removeAllRanges();"
                        "sel.addRange(range);"
                        "el.focus();"
                    "}", editor)
                    
                    print("Base content filled and cursor moved to end.")
                    found_editor = True
                    break
            
            if not found_editor:
                print("Fallback fill via evaluate on main page")
                await page.evaluate(f"document.querySelector('[contenteditable=\"true\"]').innerText = `{content_without_tags}\n\n`")

            
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
            
            # Wait a moment to catch any immediate validation error toasts
            await asyncio.sleep(2)
            
            # Look for error messages on the page (e.g. "标题最多输入20字" or generic toast)
            error_elements = await page.query_selector_all(".el-message--error, .toast, [class*='error'], .css-toast")
            if error_elements:
                for el in error_elements:
                    # Make sure it's visible and has text
                    if await el.is_visible():
                        err_text = await el.inner_text()
                        if err_text.strip():
                            print(f"Error prompt detected: {err_text.strip()}")
                            return
            
            await asyncio.sleep(8)

            print("Navigating to Note Manager for verification...")
            await page.goto("https://creator.xiaohongshu.com/new/note-manager")
            await page.reload()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            # Use the extraction logic to verify
            verification_script = """
            () => {
                const noteElements = document.querySelectorAll('.note');
                return Array.from(noteElements).map(el => {
                    const infoEl = el.querySelector('.info');
                    let title = "";
                    if (infoEl) {
                        const textNodes = Array.from(infoEl.childNodes)
                            .map(n => n.innerText || n.textContent)
                            .filter(t => t && t.trim().length > 0);
                        if (textNodes[0] && (textNodes[0].includes("审核中") || textNodes[0].includes("未通过"))) {
                            title = textNodes[1] || textNodes[0];
                        } else {
                            title = textNodes[0] || "";
                        }
                    }
                    const statusTag = el.querySelector('.time_status .d-text, .time_status [class*="tag"], .info [class*="tag"]')?.innerText || "已发布";
                    return { 
                        title: title.split('\\n')[0].trim(),
                        status: statusTag.trim()
                    };
                });
            }
            """
            notes = await page.evaluate(verification_script)
            
            if notes:
                import json
                print("Latest 3 Notes in Manager:")
                print(json.dumps(notes[:3], indent=2, ensure_ascii=False))
                # Still output the full list for context if needed
                print(f"RESULT_NOTES_DATA:{json.dumps(notes, ensure_ascii=False)}")
            else:
                print("VERIFICATION_INFO: No notes found in the Note Manager.")

        except Exception as e:
            print(f"Error in XHS script: {e}")
        finally:
            await page.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python post_to_xhs.py <image_path> <title> <content>")
    else:
        asyncio.run(run(sys.argv[1], sys.argv[2], sys.argv[3]))

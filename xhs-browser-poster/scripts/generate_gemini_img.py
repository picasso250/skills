import asyncio
from playwright.async_api import async_playwright
import os
import sys

async def run(prompt):
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
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

            # Step 5: Wait 60s for generation
            print("Waiting 60s for image generation...")
            await asyncio.sleep(60)

            # Step 6: Download high-res image
            print("Attempting to download high-res image...")
            download_btn_selector = "button[aria-label*='Download'], button[aria-label*='下载']"
            
            # Scroll to bottom to ensure elements are updated
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            try:
                await page.wait_for_selector(download_btn_selector, timeout=20000)
                async with page.expect_download(timeout=30000) as download_info:
                    # Click the last download button found (most recent)
                    btns = await page.query_selector_all(download_btn_selector)
                    if btns:
                        await btns[-1].click()
                    else:
                        raise Exception("Download button found by selector but query_selector_all returned empty.")
                
                download = await download_info.value
                save_path = os.path.abspath("gemini_generated_output.jpg")
                await download.save_as(save_path)
                print(f"RESULT_IMAGE_PATH:{save_path}")
            except Exception as e:
                print(f"Failed to download image: {e}")
                await page.screenshot(path="gemini_download_fail.png")
            
        except Exception as e:
            print(f"Error in Gemini script: {e}")
            await page.screenshot(path="gemini_error.png")
        finally:
            await page.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_gemini_img.py <prompt>")
    else:
        asyncio.run(run(sys.argv[1]))

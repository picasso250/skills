import argparse
import asyncio
import re
import sys
import os
import hashlib
import time
import tempfile
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup, NavigableString, Tag, Comment

CACHE_DIR = os.path.join(tempfile.gettempdir(), "gemini-url2md-cache")
CACHE_EXPIRY = 300  # 5 minutes in seconds

async def get_html(url):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{url_hash}.html")

    if os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        if time.time() - mtime < CACHE_EXPIRY:
            # print(f"Using cached content for {url}...", file=sys.stderr)
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()

    async with async_playwright() as p:
        # Note: Set headless=False if running locally to see the browser window
        browser = await p.chromium.launch(headless=True)
        # Use a more realistic browser profile to avoid being blocked
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        
        # Set a timeout and wait for DOM content to ensure basic structure is there
        # print(f"Navigating to {url}...", file=sys.stderr)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            # Wait a few seconds for dynamic content to render
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Warning during navigation: {e}", file=sys.stderr)
            
        content = await page.content()
        await browser.close()

        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return content

def convert_to_md(soup):
    # Remove script, style, and other non-content elements
    for element in soup(["script", "style", "noscript", "iframe", "svg", "canvas", "template"]):
        element.decompose()

    def walk(element):
        if isinstance(element, Comment):
            return ""
            
        if isinstance(element, NavigableString):
            return element.strip()

        if not isinstance(element, Tag):
            return ""

        tag_name = element.name

        # Handle tables
        if tag_name == 'table':
            rows = element.find_all('tr')
            if not rows:
                return ""

            md_table = "\n"
            for i, row in enumerate(rows):
                cols = row.find_all(['td', 'th'])
                if not cols:
                    continue
                row_data = [walk(col).strip() for col in cols]
                md_table += "| " + " | ".join(row_data) + " |\n"

                # Add separator after header row
                if i == 0 and (row.find('th') or element.find('thead')):
                    md_table += "|" + "|".join(["---"] * len(cols)) + "|\n"

            return md_table + "\n"

        # 1. Handle headers h1-h4
        if tag_name in ['h1', 'h2', 'h3', 'h4']:
            level = int(tag_name[1])
            inner = " ".join(filter(None, [walk(c) for c in element.children]))
            return f"\n{'#' * level} {inner}\n"

        # 2. Handle links (a tags)
        if tag_name == 'a':
            href = element.get('href', '')
            inner = " ".join(filter(None, [walk(c) for c in element.children]))
            if href and inner:
                return f"[{inner}]({href})"
            return inner

        # 3. Handle paragraphs (p tags)
        if tag_name == 'p':
            inner = " ".join(filter(None, [walk(c) for c in element.children]))
            return f"\n{inner}\n"

        # 4. For all other tags, extract text from children and join with space
        return " ".join(filter(None, [walk(c) for c in element.children]))

    target = soup.body if soup.body else soup
    md_content = walk(target)

    # Post-processing:
    # Remove multiple spaces within a line
    md_content = re.sub(r' +', ' ', md_content)

    # Split by newline, strip each line, and remove empty lines to handle "p标签之间使用换行"
    # and general formatting requirements.
    lines = [line.strip() for line in md_content.split('\n')]
    return "\n".join(filter(None, lines))

async def main():
    parser = argparse.ArgumentParser(description="Convert HTML from URL to Markdown")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("--out-file", help="Output markdown file (optional, defaults to stdout)")

    args = parser.parse_args()

    try:
        # print(f"Fetching {args.url}...", file=sys.stderr)
        html = await get_html(args.url)

        # print("Parsing HTML...", file=sys.stderr)
        # Use lxml if available, otherwise fallback to html.parser
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')

        # print("Converting to Markdown...", file=sys.stderr)
        markdown = convert_to_md(soup)

        if args.out_file:
            with open(args.out_file, 'w', encoding='utf-8') as f:
                f.write(markdown)
            # print(f"Successfully saved to {args.out_file}", file=sys.stderr)
        else:
            print(markdown)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())

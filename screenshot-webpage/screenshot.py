import argparse
import os
import sys
import time
import http.server
import threading
import urllib.request
import json
from playwright.sync_api import sync_playwright

def normalize_url(url):
    return url.rstrip('/') if url else url

def start_server(file_path, port):
    """Starts a simple HTTP server to serve the file's directory."""
    directory = os.path.dirname(os.path.abspath(file_path))
    os.chdir(directory)
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(('localhost', port), handler)
    httpd.serve_forever()

def main():
    parser = argparse.ArgumentParser(description="Take a screenshot of a URL or local HTML file using Playwright.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to the local HTML file.")
    group.add_argument("--url", help="URL to visit.")
    
    parser.add_argument("--timeout", type=float, default=3.0, help="Wait time in seconds after loading (default: 3.0).")
    parser.add_argument("--viewport", default="380x420", help="Viewport size WxH (default: 380x420).")
    parser.add_argument("--scroll-x", type=int, default=0, help="Horizontal scroll position (default: 0).")
    parser.add_argument("--scroll-y", type=int, default=0, help="Vertical scroll position (default: 0).")
    parser.add_argument("--out-file", required=True, help="Output PNG file path.")

    args = parser.parse_args()

    # Parse viewport
    try:
        width, height = map(int, args.viewport.lower().split('x'))
    except ValueError:
        print(f"Error: Invalid viewport format '{args.viewport}'. Use WxH (e.g., 380x420).")
        sys.exit(1)

    with sync_playwright() as p:
        browser = None
        page = None
        is_remote = False

        # Attempt to find an existing tab if --url is provided
        if args.url:
            try:
                # Check if debugging port is active and look for exact URL match
                with urllib.request.urlopen("http://localhost:9222/json", timeout=1) as response:
                    tabs = json.loads(response.read())
                    matching_tab = next((t for t in tabs if t.get('type') == 'page' and normalize_url(t.get('url')) == normalize_url(args.url)), None)
                    
                    if matching_tab:
                        print(f"Found existing tab for {args.url}. Connecting via CDP...")
                        with urllib.request.urlopen("http://localhost:9222/json/version", timeout=1) as vresp:
                            version_info = json.loads(vresp.read())
                            ws_url = version_info["webSocketDebuggerUrl"]
                        browser = p.chromium.connect_over_cdp(ws_url)
                        # Find the specific page object in the connected browser
                        for context in browser.contexts:
                            for pge in context.pages:
                                if normalize_url(pge.url) == normalize_url(args.url):
                                    page = pge
                                    is_remote = True
                                    break
                            if is_remote: break
            except Exception:
                # Debugging port not open or other error, fallback to launch
                pass

        if not is_remote:
            print("Launching new headless browser...")
            browser = p.chromium.launch()
            context = browser.new_context(viewport={'width': width, 'height': height})
            page = context.new_page()

            target_url = args.url
            server_thread = None

            if args.file:
                if not os.path.exists(args.file):
                    print(f"Error: File not found: {args.file}")
                    sys.exit(1)
                
                port = 8999
                filename = os.path.basename(args.file)
                target_url = f"http://localhost:{port}/{filename}"
                server_thread = threading.Thread(target=start_server, args=(args.file, port), daemon=True)
                server_thread.start()
                time.sleep(0.5)

            print(f"Navigating to: {target_url}")
            page.goto(target_url, wait_until="load", timeout=60000)
        else:
            print(f"Reusing existing page: {page.url}")

        # Additional timeout for animations/dynamic content
        if args.timeout > 0:
            time.sleep(args.timeout)

        # Scroll
        if args.scroll_x != 0 or args.scroll_y != 0:
            print(f"Scrolling to: ({args.scroll_x}, {args.scroll_y})")
            page.evaluate(f"window.scrollTo({args.scroll_x}, {args.scroll_y})")
            time.sleep(0.5)

        # Take screenshot
        print(f"Saving screenshot to: {args.out_file}")
        page.screenshot(path=args.out_file)

        # Only close if we launched it ourselves
        if not is_remote and browser:
            browser.close()
        else:
            print("Disconnected from remote browser (browser remains open).")

if __name__ == "__main__":
    main()

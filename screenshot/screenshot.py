import subprocess
import time
from playwright.sync_api import sync_playwright
import os
import argparse


def run_test(output_name, target_url, server_dir=".", timeout=0, mobile=False):
    server_process = None

    # Check if we should start a local server
    if not target_url.startswith("http"):
        # Ensure url_path starts with /
        if not target_url.startswith("/"):
            target_url = "/" + target_url

        base_url = "http://localhost:8000"
        full_url = f"{base_url}{target_url}"

        # Start Python HTTP server in the background
        print(f"Starting server in directory: {server_dir}")
        server_process = subprocess.Popen(
            ["python3", "-m", "http.server", "8000", "--directory", server_dir]
        )

        # Wait a bit for the server to start
        time.sleep(2)
        target_url = full_url

    try:
        with sync_playwright() as p:
            # Use chromium in headless mode
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            if mobile:
                page.set_viewport_size({"width": 430, "height": 932})

            # Navigate to the target URL
            print(f"Navigating to {target_url}...")
            page.goto(target_url)

            if timeout > 0:
                print(f"Waiting for {timeout} seconds...")
                time.sleep(timeout)

            # Take a screenshot
            page.screenshot(path=output_name)
            print(f"Screenshot saved to {output_name}")

            # Verify the content (optional, printing for info)
            title = page.title()
            print(f"Page Title: {title}")

            browser.close()
    finally:
        # Stop the server if it was started
        if server_process:
            print("Stopping server...")
            server_process.terminate()
            server_process.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Capture a screenshot of a webpage or local server page."
    )
    parser.add_argument(
        "output", help="The name of the output image file (e.g., result.png)"
    )
    parser.add_argument(
        "url",
        help="The URL or path to capture (e.g., http://example.com or /index.html)",
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="The directory to serve local files from (default: current directory)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="The number of seconds to wait before taking the screenshot (default: 0)",
    )
    parser.add_argument(
        "--mobile",
        action="store_true",
        help="Use mobile viewport (iPhone 14 Pro Max: 430x932)",
    )

    args = parser.parse_args()

    run_test(args.output, args.url, args.dir, args.timeout, args.mobile)

#!/usr/bin/env python3
"""
Thin CLI template for the Website To Cli skill.

Customize this script with the selectors and waits that match the human-approved workflow.
Each step logs the intent, asks the human to confirm, and only executes when the user agrees.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Callable, Iterable

from playwright.sync_api import Page, sync_playwright

Step = tuple[str, Callable[[Page], None]]


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Playwright-backed CLI starter for website-to-cli.")
    parser.add_argument("--ws-endpoint", required=True, help="webSocketDebuggerUrl from Chrome DevTools")
    parser.add_argument("--url", required=True, help="Homepage or landing URL to start the flow")
    parser.add_argument("--dry-run", action="store_true", help="Log steps without executing selectors")
    parser.add_argument("--slow-mo", type=int, default=0, help="Slow motion milliseconds for human review")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout for Playwright actions in seconds")
    return parser.parse_args()


def confirm_step(label: str) -> bool:
    prompt = f"[Confirm] {label} - press Enter to execute or type 'skip' to omit: "
    response = input(prompt).strip().lower()
    if response == "skip":
        logging.info("Skipping step per user request: %s", label)
        return False
    return True


def build_steps(url: str) -> Iterable[Step]:
    def open_home(page: Page) -> None:
        page.goto(url, wait_until="networkidle")

    def sample_action(page: Page) -> None:
        page.wait_for_timeout(500)

    # Replace these placeholders with real selectors and functions.
    return [
        ("Load starting page", open_home),
        ("Perform the first interaction", sample_action),
    ]


def run_steps(page: Page, steps: Iterable[Step], dry_run: bool) -> None:
    for label, action in steps:
        logging.info("Preparing step: %s", label)
        if not confirm_step(label):
            continue
        if dry_run:
            logging.info("Dry run enabled; skipping action for '%s'", label)
            continue
        action(page)
        logging.info("Completed step: %s", label)


def attach_and_run(args: argparse.Namespace) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(args.ws_endpoint)
        try:
            context = browser.contexts[0] if browser.contexts else browser.new_context(slow_mo=args.slow_mo)
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(args.timeout * 1000)
            run_steps(page, build_steps(args.url), args.dry_run)
        finally:
            browser.close()


def main() -> None:
    setup_logging()
    args = parse_args()
    try:
        attach_and_run(args)
    except KeyboardInterrupt:
        logging.warning("Interrupted by user; closing gracefully.")
        sys.exit(1)


if __name__ == "__main__":
    main()

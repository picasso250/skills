---
name: website-to-cli
description: Guided meta workflow for converting websites into CLI automations by pairing Chrome DevTools (port 9222) + Python Playwright with human confirmations; use when each site action must become a deterministic CLI command reviewed step-by-step before execution.
---

# Website To Cli

## Overview
Guide the user through capturing the manual story, attaching Playwright to Chrome (port 9222), and translating each verified click/typing step into a CLI routine while pausing for approvals after every transformation.

## When to Use
- When the request is “Turn this browser flow into a repeatable CLI,” and Chrome/Edge can start with `--remote-debugging-port=9222`.
- When every site action must be understood, recorded, and confirmed before being codified into CLI arguments.
- When the deliverable should be runnable code (CLI + docs) instead of just prose.

## Workflow

### Step 1: Capture the story and acceptance criteria
- Read the user’s manual flow and list the pages, buttons, inputs, and outputs they care about.
- Confirm success criteria, required inputs (forms, files, credentials), and tolerable failure modes before touching the browser.
- Record the scenarios so that every subsequent CLI action maps back to a concrete story beat.

### Step 2: Attach to Chrome DevTools and pin the websocket
- Launch Chrome/Edge with `--remote-debugging-port=9222` and confirm you can reach `http://127.0.0.1:9222/json/version`.
- Run `python scripts/fetch_ws.py --host localhost --port 9222` (swap `localhost` for a remote host if necessary) to list available tabs and their `webSocketDebuggerUrl`.
- Ask the user which page/window should drive the CLI, note its title/URL, and save the matching `wsEndpoint` for later.

### Step 3: Observe the interaction with Playwright
- Start from `scripts/cli_template.py`, plugging in the confirmed `ws_endpoint` and `url`.
- Step through the user’s clicks, typing, waits, and data captures while narrating: describe the selector, why it’s needed, and the expected result.
- Freeze after each step, summarize the intended CLI effect, and ask the user “May I treat this as CLI step X?” before committing it to the template.
- When anything depends on dynamic data (tokens, IDs, timestamps), capture how the data is derived and how the CLI will accept or compute it.

### Step 4: Assemble the CLI surface
- Map the approved Playwright steps into sequential CLI arguments or subcommands, keeping each flag tied to a single action.
- Document any required environment variables (e.g., `PLAYWRIGHT_BROWSERS_PATH`, credentials, the `wsEndpoint`), and expose them through `argparse`/`click`.
- Keep the user involved by reading each new CLI flag aloud, explaining how it changes the browser automation, and confirming that it matches their mental model.

### Step 5: Validate and document with the human in the loop
- Run the CLI scenarios, show the logs or screenshots to the user, and ask them to confirm the outputs match the original manual steps.
- If the behavior drifts, note the discrepancy, adjust the script, and replay the scenario until the user signs off.
- Record each confirmation, checkbox, and assumption (see `references/human-in-loop.md`) so the next agent or developer understands what “approved” meant.

## Resources
- Use `references/human-in-loop.md` whenever you need phrasing for check-ins, progress updates, or describing trade-offs and open questions.
- Run `python scripts/fetch_ws.py --host localhost --port 9222` before touching the CLI to capture the correct `webSocketDebuggerUrl`.
- Start each refactor from `python scripts/cli_template.py --ws-endpoint <url> --url <homepage>` so you maintain a predictable entry point and keep the human confirming every change.

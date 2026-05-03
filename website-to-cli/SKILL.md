---
name: website-to-cli
description: Guided workflow for converting repeatable browser or website interaction flows into CLI automations by pairing Chrome DevTools (port 9222) + Python Playwright with human confirmations. Use when Codex needs to reuse an already-open browser tab, inspect live DOM state, validate each step in the real page, and turn the approved flow into a deterministic CLI command reviewed step-by-step before execution.
---

# Website To Cli

## Overview
Guide the user through capturing the manual story, attaching Playwright to Chrome (port 9222), and translating each verified click/typing step into a CLI routine while pausing for approvals after every transformation.

## When to Use
- When the request is “Turn this browser flow into a repeatable CLI,” and Chrome/Edge can start with `--remote-debugging-port=9222`.
- When every site action must be understood, recorded, and confirmed before being codified into CLI arguments.
- When the deliverable should be runnable code (CLI + docs) instead of just prose.

## Workflow

核心迭代流程：
- 先写验证脚本，等用户确认。
- 用户确认后，再合并到主脚本。
- 每次获得用户确认后，立即执行一次 `git add`，把当前已确认的改动加入暂存区。
- 按这个节奏持续循环，不要一开始就把整条流程一次性写完。
- 对新的复杂页面步骤，验证脚本默认先“观察”，再“行动”；先把看到的目标元素、坐标、文本和结构打印清楚，确认后再写点击/输入动作。
- 在主循环里默认优先复用已经打开的目标 tab；只有明确需要隔离状态、避免干扰或当前页面不存在时，才新开 tab。
- `verify_*` 脚本是一次性验证件，不需要设计 `--help` 或长期兼容接口。
- `verify_*` 脚本默认不要写 `try/except`；应当让异常直接抛出，以便保留现场并暴露真实失败点。
- 当对应步骤已经稳定并合并进主脚本后，相关 `verify_*` 脚本最终都要删除，不保留为长期资产。
- 打开页面后的首次稳定等待，默认按“等待 5s”处理，但实际执行应为 `5 + rand(-0.5, 0.5)` 秒。
- 任何物理点击之前，总是先“等待 1s”，但实际执行应为 `1 + rand(-0.5, 0.5)` 秒。
- 任何物理 hover 之前，也总是先“等待 1s”，但实际执行应为 `1 + rand(-0.5, 0.5)` 秒。
- 输入策略默认坚持模拟物理输入：先用物理点击聚焦输入框，再用键盘事件输入，不直接使用 `fill`、不直接改 DOM `value`。
- 模拟物理输入时，逐字输入前等待 `0.1-0.2s`，逐字输入后也等待 `0.1-0.2s`；这段节奏应抽成可复用函数。
- 对单行输入框，完成输入后默认再按一次 `Tab` 失焦，让页面校验和计数器刷新。
- 点击策略默认坚持模拟物理点击，优先使用鼠标坐标点击，而不是 DOM 级别的 `locator.click()`。
- 物理点击坐标默认取元素中心附近，并带随机偏移：`x = x0 + rand(-width/8, width/8)`，`y = y0 + rand(-height/8, height/8)`。
- 物理 hover 坐标也默认取元素中心附近，并带随机偏移：`x = x0 + rand(-width/8, width/8)`，`y = y0 + rand(-height/8, height/8)`。
- 这个技能现在也承担原先独立 `browser` skill 的 CDP 会话附着职责；涉及浏览器会话选择、tab 枚举、复用已打开页面时，统一使用本技能下的基础脚本，不再依赖独立 `browser` skill。
- 对 Chrome CDP，不要把 `http://127.0.0.1:9222` 直接传给 `connect_over_cdp()`；先读取 `/json/version`，再使用其中的 `webSocketDebuggerUrl`，否则某些运行时会反复返回 HTTP 400。

开始任何基于该技能的新自动化之前，先阅读这五个脚本：
- `scripts/fetch_ws.py`
- `scripts/ls-tabs.py`
- `scripts/new-tab.py`
- `scripts/cdp_common.py`
- `scripts/eval_tab_js.py`

其中前三个脚本是基础设施：
- `fetch_ws.py` 用来确认 DevTools 连接信息和 `wsEndpoint`。
- `ls-tabs.py` 用来确认当前有哪些标签页可复用，以及目标页面是否已经存在。
- `new-tab.py` 用来在现有 DevTools 会话里稳定打开一个新的目标标签页；若存在多个 browser context，应通过 `--match-url` 显式选中目标 context。

另外两个脚本用于现场观察：
- `cdp_common.py` 提供 `webSocketDebuggerUrl` 解析、context/page 枚举、按精确 URL 选页等共用能力。
- `eval_tab_js.py` 用来在已打开的目标 tab 上直接执行 JavaScript，快速获取 DOM 结构、文本、坐标、属性和页面状态。

### Step 1: Capture the story and acceptance criteria
- Read the user’s manual flow and list the pages, buttons, inputs, and outputs they care about.
- Confirm success criteria, required inputs (forms, files, credentials), and tolerable failure modes before touching the browser.
- Record the scenarios so that every subsequent CLI action maps back to a concrete story beat.

### Step 2: Attach to Chrome DevTools and pin the websocket
- Launch Chrome/Edge with `--remote-debugging-port=9222` and confirm you can reach `http://127.0.0.1:9222/json/version`.
- Run `python scripts/fetch_ws.py --host localhost --port 9222` (swap `localhost` for a remote host if necessary) to list available tabs and their `webSocketDebuggerUrl`.
- Never pass the raw `http://127.0.0.1:9222` endpoint straight into Playwright; resolve `/json/version` first and keep the returned `webSocketDebuggerUrl`.
- Ask the user which page/window should drive the CLI, note its title/URL, and save the matching `wsEndpoint` for later.
- If the target page is already open, prefer reusing that tab in the verification loop instead of opening a fresh one.

### Step 3: Observe the interaction with Playwright
- Start from `scripts/cli_template.py`, plugging in the confirmed `ws_endpoint` and `url`.
- Reuse the confirmed target tab whenever possible so each validation step stays attached to the same live page state.
- For a new or ambiguous UI state, split verification into an observe step first and an action step second.
- Before writing an action script for a new page state, prefer inspecting the live tab first with `python scripts/eval_tab_js.py --url <exact-url>` and pipe the JavaScript via `--code` or stdin.
- After opening a page, insert the default stabilized wait of about `5 +/- 0.5s` before treating the page as ready.
- Before every physical click, insert the default pre-click wait of about `1 +/- 0.5s`.
- Before every physical hover, insert the default pre-hover wait of about `1 +/- 0.5s`.
- For text entry, focus the field via a physical click first, then use keyboard events to type; do not mutate the DOM value directly.
- For text entry, wait about `0.1-0.2s` before each character and about `0.1-0.2s` after each character; implement this as a reusable helper.
- For single-line fields, press `Tab` after typing so blur-driven validation can run.
- Prefer physical mouse clicks over DOM-triggered clicks unless the user explicitly approves a different strategy.
- Prefer physical mouse hovers over DOM-triggered hover helpers unless there is a specific reason not to.
- Prefer keyboard-driven typing over `fill()` or script-driven value injection unless the user explicitly approves a different strategy.
- Keep every physical click near the element center with the default random jitter of about `+/- size/8`.
- Keep every physical hover near the element center with the default random jitter of about `+/- size/8`.
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
- Read `scripts/fetch_ws.py`, `scripts/ls-tabs.py`, `scripts/new-tab.py`, `scripts/cdp_common.py`, and `scripts/eval_tab_js.py` before building a new site-specific script on top of this skill.
- Run `python scripts/fetch_ws.py --host localhost --port 9222` before touching the CLI to capture the correct `webSocketDebuggerUrl`.
- Prefer reusing an existing matching tab discovered via `scripts/ls-tabs.py`; use `scripts/new-tab.py` only when no suitable page is already open.
- Use `python scripts/eval_tab_js.py --url <exact-page-url> --code "<js>"` or pipe JS via stdin when you need to inspect a live tab before deciding selectors or physical click coordinates.
- Run `python scripts/new-tab.py --url <target>` when the next verification step needs a fresh tab instead of reusing an existing page.
- Start each refactor from `python scripts/cli_template.py --ws-endpoint <url> --url <homepage>` so you maintain a predictable entry point and keep the human confirming every change.

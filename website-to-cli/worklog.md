# Worklog

- 2026-06-03: Added `scripts/collect-console.py` to capture new console messages from an existing Chrome CDP tab matched by exact URL.
- 2026-06-03: Documented `collect-console.py` in `SKILL.md`.
- 2026-06-11: Renamed `scripts/eval_tab_js.py` to `scripts/eval-tab-js.py` and updated skill references.
- 2026-06-14: Verified Playwright browser-level CDP attach can hang on the local browser; updated `eval-tab-js.py`, `collect-console.py`, and `new-tab.py` to use page-level WebSocket or DevTools HTTP paths.
- 2026-06-14: Consolidated endpoint discovery into `ls-tabs.py`, removed duplicate `fetch_ws.py`, and removed the generic `cli_template.py` in favor of starting from verified `eval-tab-js.py` observations.
- 2026-06-21: Updated `SKILL.md` to prefer deterministic low-noise physical automation: fixed waits, `0.01s` typing cadence, and element-center click/hover coordinates without random jitter.

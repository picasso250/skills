---
name: browser-flow-to-cli
description: Use when the user wants to turn a repeatable browser or website interaction flow into a CLI or automation script.
---

# Browser Flow to CLI

## 流程

- 如果要测试视频，那么使用下载文件夹最新的 mp4 文件测试。
- For Chrome CDP, do not pass `http://127.0.0.1:9222` directly into `connectOverCDP`; first fetch `/json/version` and use `webSocketDebuggerUrl`, or some runtimes will return HTTP 400 and fail repeatedly.
- 可先用 `scripts/list_tabs.py` 枚举现有标签页。
- 现有辅助脚本共用 `scripts/cdp_common.py`。
- 验证的时候，善用 `scripts/eval_tab_js.py` 获取现有的dom结构，再精确写脚本。

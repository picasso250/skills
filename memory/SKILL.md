---
name: memory
description: 从 ~/.pi/agent/sessions/ 的 JSONL 历史对话中搜索记忆。当用户提起过去聊过的事时使用；当你认为需要回顾历史才能更好地决定下一步（仅限与用户相关的事）时也应主动使用。
---

# Memory

Pi sessions：`~/.pi/agent/sessions/`
Gemini sessions：`~/.gemini/tmp/<project>/chats/session-<timestamp>-<hash>.json`

Pi 每行一条 JSON：

```json
{"type":"message","id":"d42823a7","parentId":"c50ac3a2","timestamp":"2026-05-16T02:26:21.527Z","message":{"role":"user","content":[{"type":"text","text":"新建 memory 技能"}]}}
```

```json
{"type":"message","id":"b09deb9b","parentId":"d42823a7","timestamp":"2026-05-16T02:26:36.081Z","message":{"role":"assistant","content":[{"type":"text","text":"先搜 .pi/sessions 验证"}]}}
```

Gemini 单文件 `messages` 数组：

```json
{"id":"ae79c9c1","timestamp":"2026-04-01T09:25:25.920Z","type":"user","content":[{"text":"使用bilibili技能"}]}
```

```json
{"id":"b3d3ded8","timestamp":"2026-04-01T09:25:30.094Z","type":"gemini","content":"我将激活 Bilibili 视频制作技能","model":"gemini-3-flash-preview"}
```

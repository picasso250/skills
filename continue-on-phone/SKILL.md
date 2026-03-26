---
name: continue-on-phone
description: 把当前 agent 对话接到手机上。用户用 start_scan.py 打印二维码，用 interact.py 追加 agent 文本并在 30 秒后拉取新的用户消息。
---

# Skill: continue-on-phone

当用户说“我想在手机上继续聊”“给我一个二维码让我手机接着用”“把当前 agent 对话切到手机上”这类意思时，使用这个 skill。

## Goal

部署一套最小可用的手机接力链路：

- Cloudflare Worker 提供 API 和手机网页
- Cloudflare KV 持久化 session JSON
- `start_scan.py` 新建或复用 session，并在终端打印二维码
- `interact.py --text ...` 把 agent 消息写入 session，然后等待并拉取新用户消息

## File Layout

- Worker: `worker/src/worker.js`
- Wrangler config: `worker/wrangler.toml`
- Python scripts: `scripts/start_scan.py`, `scripts/interact.py`, `scripts/common.py`
- Local state: `state/`

## Workflow

1. 在 Cloudflare 创建一个 KV namespace。
2. 把 KV namespace id 填到 `worker/wrangler.toml` 的 `[[kv_namespaces]]` 里。
3. 在 `continue-on-phone/worker` 目录运行：

```powershell
wrangler deploy
```

4. 默认使用自定义域名 `https://cop.io99.xyz`
5. 本地安装依赖：

```powershell
python -m pip install -r .\requirements.txt
```

6. 默认不需要设置环境变量；脚本会直接使用 `https://cop.io99.xyz`

如果需要临时覆盖，再设置环境变量：

```powershell
$env:CONTINUE_ON_PHONE_BASE_URL="https://continue-on-phone.<subdomain>.workers.dev"
```

7. 开启扫码：

```powershell
python .\scripts\start_scan.py
```

8. 终端会打印：
   - `session_id`
   - `session_url`
   - 一个 ASCII 二维码
9. 用户扫码后会进入 `/s/<session_id>` 对应的手机聊天页。
10. 交互时运行：

```powershell
python .\scripts\interact.py --text "你好，继续说你的问题"
```

11. 该脚本会：
   - 先把这段文字作为 `agent` 消息追加到 session
   - 默认等待 `30` 秒
   - 读取晚于本地 `last_user_ts` 的 `user` 消息
   - 将新消息打印到终端

## Session Shape

KV 里的 value 是一个 JSON 对象，最小结构如下：

```json
{
  "session_id": "abc123",
  "created_at": "2026-03-26T06:00:00.000Z",
  "updated_at": "2026-03-26T06:00:00.000Z",
  "messages": [
    {
      "id": "msg1",
      "role": "agent",
      "text": "hello",
      "ts": "2026-03-26T06:00:00.000Z"
    }
  ]
}
```

## API Contract

- `POST /api/sessions`
  - 可传 `session_id`
  - 若不存在则创建，存在则复用
- `GET /api/sessions/:session_id`
  - 读取整个 session JSON
- `POST /api/sessions/:session_id/messages`
  - body: `{ "role": "agent" | "user", "text": "..." }`
  - 追加一条消息
- `GET /api/sessions/:session_id/messages?role=user&since=<iso>`
  - 按角色和时间戳过滤消息
- `GET /s/:session_id`
  - 返回手机端网页

## Failure Handling

- `CONTINUE_ON_PHONE_BASE_URL` 没设置时，脚本默认走 `https://cop.io99.xyz`
- KV namespace id 没配置时，`wrangler deploy` 不应继续硬顶。
- 如果手机端页面打不开，先确认 Worker URL、路由和 KV 绑定。
- 这个实现是“共享 session + 轮询消息”，不是“原生无缝迁移同一个桌面会话”。

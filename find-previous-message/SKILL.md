---
name: find-previous-message
description: 查找当前消息的历史上下文与已发送回复。用于邮件和飞书消息；当你处理 gateway/processing 或 gateway/history 里的消息文件时，优先使用它基于当前文件路径回溯同一线程、同一会话或同一发件人的前几条消息，以及对应的 .reply.json / .reply.processed.json 记录。
---

# Skill: Find-Previous-Message

在 `gateway/history`、`gateway/processing`、`gateway/outbox` 中查找与当前消息相关的历史消息和已发送回复。

优先用当前消息文件路径调用脚本，而不是手工拼 sender、UID 或 message id。

## 使用 find_prev.ps1

```powershell
pwsh .agents/skills/find-previous-message/find_prev.ps1 <message_file> [Count]
```

- `message_file`: 当前正在处理的消息文件绝对路径或相对路径。
- `[Count]`: 向前回溯的历史消息数量，默认 `5`。

脚本行为：

- 邮件：按同一发件人回溯历史邮件
- 飞书单聊 / 群聊：按同一 `Conversation` 回溯历史消息
- 同时补出这些消息对应的 `gateway/outbox/*.reply.json` 与 `*.reply.processed*.json`

## 示例

```powershell
pwsh .agents/skills/find-previous-message/find_prev.ps1 C:\Users\MECHREV\my-claw\gateway\processing\feishu_xxx.txt 5
pwsh .agents/skills/find-previous-message/find_prev.ps1 gateway/processing/email_xxx.txt 8
```

## 使用要求

- 至少执行一次，默认先看前 `5` 条。
- 如果上下文仍不够，增大 `Count` 继续查。
- 读完输出的文件后，再决定快速回复和最终回复。
- 找不到足够上下文时，再用 `rg` 按关键词补查。

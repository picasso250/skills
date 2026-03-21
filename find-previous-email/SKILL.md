---
name: find-previous-email
description: 用于查找邮件的前一条消息（帮助你理解上下文）和自己的回复。当你收到邮件时，你应当至少使用一次此技能来查找前5条消息，以便更好地理解上下文。
---

# Skill: find-previous-email

在 `gateway\history` 和 `gateway\outbox` 中查找邮件的前一条消息以及回复。

## 使用 find_prev.ps1 脚本

你可以使用该目录下的 `find_prev.ps1` 脚本来快速查找之前的邮件消息。

### 参数说明

`pwsh .agents/skills/find-previous-email/find_prev.ps1 <email_address> <uid> [Count]`

- `email_address`: 用户的完整邮件地址（脚本会自动处理 `@` 为 `_at_`）。
- `uid`: 当前邮件的唯一标识符（UID）。
- `[Count]` (可选): 往前查找的消息数量，默认为 `5`。

脚本会自动在 `gateway/history` 查找前 `Count` 条消息，并同时在 `gateway/outbox` 中查找这些 UID (以及当前 UID) 对应的回复。

### 示例

```powershell
# 查找用户 alice@example.com 在 UID 1320590420 之前的 5 条消息（以及回复）
pwsh .agents/skills/find-previous-email/find_prev.ps1 alice@example.com 1320590420 5
```

## 手动查找方法

### 邮件消息
邮件的文件名格式为 `email_username_at_domain.com_datetime_uid_processed.txt`。你可以查找相同邮箱地址下，UID 较小的文件。

### 查找回复
如果你想查找自己的回复： 因为你的 `outbox/` 里的文件总是带有 `reply-<UID>` 的，你就直接查找这个 UID 就行了。

## 注意事项
- 你应当阅读查找出来的邮件内容，以便更好地理解上下文。
- 如果你查了一次还觉得上下文不足，你应该继续往前查找，直到找到足够的上下文为止。
- 你也拥有 `rg` 工具可以根据关键词搜索。

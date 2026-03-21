---
name: send-email
description: Send email to the user.
---

# Skill: send-email

此技能用于向指定用户发送电子邮件。

## 场景：发送电子邮件

用于发送正式报告、状态更新或回复电子邮件。

### 使用方法

```bash
python scripts/send_email.py --to alice@example.com --subject "Hello" --ids "1,2" --markdown-body-file gateway/outbox/email-username_at_xx.com-yyyy-mm-ddTHH-MM-SSZ-reply-id-short-name.md
```

- `--to`: 接收者邮箱。
- `--subject`: 邮件主题。
- `--ids`: (可选) 引用消息的 ID，逗号分隔。
- `--markdown-body-file`: Markdown 格式的正文文件路径。

## 通用准则

1. 在发送之前，请确保已将 Markdown 文件保存到 `gateway/outbox/` 目录中。
2. 文件命名规则：gateway/outbox/email-username_at_xx.com-yyyy-mm-ddTHH-MM-SSZ-reply-id-short-name.md (时间戳使用UTC时间)。
3. 对于包含多个 ID 的情况，脚本会自动在 Markdown 正文顶部添加引用链接。

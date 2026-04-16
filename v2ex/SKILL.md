---
name: v2ex
description: 读取 V2EX 某个主题帖，提取标题、节点、作者、点击、收藏、正文和回复，输出为 Markdown 快照。用户要求“看看这个 V2EX 帖子”“刷新读一下这个主题”“提取回复和点击收藏变化”时使用。
---

# V2EX

用于通过 Chrome DevTools `9222` 复用当前浏览器会话，读取某个 V2EX 主题帖，并直接输出一个去噪后的 Markdown 摘要。

## Usage

在本技能目录下运行：

```powershell
python .\scripts\v2ex.py -t 1206255
```

强制刷新：

```powershell
python .\scripts\v2ex.py -t 1206255 --refresh
```

## Output

脚本直接输出去噪后的 Markdown：

- 标题
- 链接
- 节点 / 点击 / 收藏 / 回复
- 正文
- 回复列表

每条回复之间使用 `---` 分隔，便于后续复制、分析或喂给其他脚本。

## Notes

- 当前脚本只针对公开可访问的 V2EX 主题页。
- 参数 `-t` / `--topic` 只接收主题 ID，例如 `1206255`。
- 脚本会先访问 `http://127.0.0.1:9222/json/version` 获取 `webSocketDebuggerUrl`，再通过 CDP 连接浏览器。
- 如果当前浏览器里已经打开目标主题页，脚本会优先复用该 tab；否则会新开 tab。
- `--refresh` 会在复用已有标签页时先 `reload`，以抓取最新页面状态。
- 如果用户主要关心的是 `点击 / 收藏 / 回复` 的变化，优先看输出顶部的统计区。

---
name: shared-page-md
description: 读取用户提供的网页 URL，并通过复用当前浏览器会话把页面 DOM 转成 Markdown。用户要求“看看这个网址在讲什么”“读取我正在看的页面”“提取网页正文/链接/表格”“同步我当前看到的网页内容”时使用；只需要语义内容时优先用它，需要视觉布局时改用 screenshot-webpage，需要点击或交互时改用 browser。
---

# Shared Page Markdown

接收用户提供的 URL，并将页面内容转成 Markdown。

## Prerequisite

确认本机浏览器已开启 CDP 远程调试端口：

```powershell
& "brave.exe" --remote-debugging-port=9222
```

如果端口不可用，先确认浏览器是否已启动；必要时使用 `everything-file-search` 找到浏览器路径。

## Workflow

1. 接收用户提供的 URL。
2. 在 `C:\Users\MECHREV\.agents\skills` 目录下运行：

```powershell
python .\browser\scripts\toMD.py --url <url> --timeout 15
```

3. 脚本会在系统临时目录下自动创建本次输出目录，并写出两个文件：
   - `full.md`: 整页 DOM 转出的 Markdown
   - `main.md`: 主内容区域转出的 Markdown
4. 从 stdout 读取这两个文件路径，再直接读取文件内容；不要依赖控制台直接承载 Markdown。
5. 默认优先读取 `main.md`；主内容判断不准时再回退到 `full.md`。
6. 根据 Markdown 继续执行用户任务：
   - 需要快速理解页面时，先总结正文和页面结构
   - 需要提取信息时，优先保留标题、列表、表格、关键链接
   - 页面很长时，先给出结构化摘要，再按用户要求展开

## Output Strategy

- 页面较短时，直接基于 Markdown 回答。
- 页面较长时，先输出页面主题、主要分段、关键链接和表格，再展开细节。
- 导航、页脚、推荐内容较多时，明确说明输出来自页面 DOM，可能包含噪音。
- 默认优先使用 `main.md`，其中会尝试提取 `main`、`article` 或近似主内容区域。
- 如果主内容判断不准，回退读取 `full.md`。
- 发现登录态相关内容时，优先按“当前浏览器会话可见内容”理解，不要假设匿名访问结果。

## Parameters

- `--url <url>`: 必填，目标页面 URL
- `--timeout <seconds>`: 可选，页面加载超时；默认用 `15`
- 输出文件路径：脚本会自动创建临时目录，并通过 stdout 返回 `full_md=<path>` 与 `main_md=<path>`

## Boundaries

- 只需要语义内容时，用这个 skill。
- 需要视觉布局、像素级对照、UI 细节时，改用 `screenshot-webpage`。
- 需要点击、输入、切换标签、处理复杂交互时，改用 `browser`。

## Failure Handling

常见失败模式和处理方式见 [references/failure-modes.md](references/failure-modes.md)。

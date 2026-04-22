---
name: shared-page-md
description: 读取用户提供的网页 URL，并通过复用当前浏览器会话把页面 DOM 转成 Markdown。用户要求“看看这个网址在讲什么”“读取我正在看的页面”“提取网页正文/链接/表格”“同步我当前看到的网页内容”时使用。默认假设该页面已经在用户浏览器中打开，并优先复用已有标签页；只需要语义内容时优先用它，需要视觉布局时改用 screenshot-webpage，需要点击或交互时改用 browser。
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
2. 默认假设该 URL 已经在用户浏览器中打开；目标是复用用户当前会话里的已有标签页，而不是新开页面。
3. 在 `shared-page-md` skill 目录下运行：

```powershell
python .\scripts\page_to_md.py --url <url>
```

4. 脚本会在系统临时目录下自动创建本次输出目录，并恒写出：
   - `full.md`: 当前页面 `body` 转出的 Markdown；若命中域名 adaptor，可能已删除该站已知噪声节点
   - `page.html`: 抓到的 HTML
   - `main.md`: 仅当页面存在 `main` 或 `article` 时才写出
5. 从 stdout 读取结果：
   - 若找到 `main` 或 `article`，最前会打印 `找到main元素` 或 `找到article元素`
   - 随后直接打印所选中的 Markdown；有主内容时打印 `main.md` 的内容，否则打印 `full.md` 的内容
   - 恒打印 `full_md=<path>`
   - 恒打印 `html=<path>`
6. 默认先取 `main` 或 `article`；若不存在，则直接使用 `body` 的 Markdown。
7. 页面抓取默认不再依赖 `domcontentloaded` 作为正文就绪信号，而是在导航完成后统一额外等待 3 秒；若命中域名 adaptor，可再追加站点专用 `ready_hint(page)` 等待。
8. 若 `scripts/adapters/<domain>.py` 存在，则会按 `hostname` 后缀动态装载，例如 `www.youtube.com -> youtube_com.py`、`jakobnielsenphd.substack.com -> substack_com.py`；adaptor 只负责等待与噪声裁剪，不参与 `main/article` 的选择。
9. 根据 Markdown 继续执行用户任务：
   - 需要快速理解页面时，先总结正文和页面结构
   - 需要提取信息时，优先保留标题、列表、表格、关键链接
   - 页面很长时，先给出结构化摘要，再按用户要求展开

## Output Strategy

- 页面较短时，直接基于 Markdown 回答。
- 页面较长时，先输出页面主题、主要分段、关键链接和表格，再展开细节。
- 导航、页脚、推荐内容较多时，明确说明输出来自页面 DOM，可能包含噪音。
- 脚本只把 `main` 或 `article` 视为主内容；若二者皆无，则直接落回 `body` 的 Markdown。
- 发现登录态相关内容时，优先按“当前浏览器会话可见内容”理解，不要假设匿名访问结果。

## Parameters

- `--url <url>`: 必填，目标页面 URL
- 输出路径策略：
  - 若找到 `main` 或 `article`，stdout 最前打印其元素名
  - stdout 总是直接承载所选中的 Markdown
  - 恒返回 `full_md=<path>`
  - 恒返回 `html=<path>`

## Boundaries

- 只需要语义内容时，用这个 skill。
- 需要视觉布局、像素级对照、UI 细节时，改用 `screenshot-webpage`。
- 需要点击、输入、切换标签、处理复杂交互时，改用 `browser`。

## Failure Handling

常见失败模式和处理方式见 [references/failure-modes.md](references/failure-modes.md)。

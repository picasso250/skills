---
name: douyin-publish-video
description: 将本地视频发布到抖音创作者中心的浏览器自动化技能。用户要把视频上传到抖音、批量复用发布流程、把手动网页发布动作改成可重复 CLI、或需要连接已登录浏览器会话填写标题/简介并点击发布时使用。
---

# Douyin Publish Video

将抖音创作者中心里的“发布视频”流程变成可重复执行的本地 CLI。
优先复用用户已经登录的 Chrome/Brave 9222 调试会话，避免重新登录。

## Workflow

先把人工流程固定成下面的顺序，不要一边写脚本一边改流程：

1. 打开 `https://creator.douyin.com/creator-micro/content/upload`。
2. 至少等待 `5s`，确认页面已经进入“发布视频”页，而不是登录页或跳转页。
3. 通过页面里的 `input[type=file]` 上传本地视频文件。
4. 至少等待 `5s`，直到上传完成并出现标题/简介/发布相关表单。
5. 填写标题；如果用户给了简介，则一起填写。
6. 如有额外标签、话题、可见性或定时参数，再逐项填写；每次可见交互后等待约 `1s`。
7. 默认会继续点击最终“发布”按钮。
8. 只有脚本传入 `--dry-run` 时，才停在最终确认前，不真正发布。
9. 等待至少 `5s`，确认出现成功跳转、成功提示，或页面进入内容管理后的稳定状态。

## Real-Page Rules

- 默认假设用户已经在创作者中心登录。
- 如果页面跳到登录、实名、资质、风控、二次确认页，先停止并把问题说清楚，不要盲点。
- 优先使用以下选择器顺序：
  1. `input[type=file]`
  2. 可访问标签、占位符、按钮文本
  3. 稳定中文文案，如“上传视频”“发布”“立即发布”“定时发布”
  4. 最后才用结构性 CSS class
- 对网络加载、上传转码、发布结果统一使用至少 `5s` 的等待。
- 对输入框聚焦、下拉切换、补充信息填写使用约 `1s` 的短等待。
- 该脚本当前默认会真正发布；测试或人工确认阶段必须显式传 `--dry-run`。
- 点击最终发布后，先在约 `1.5s` 内读取 toast / notification / dialog；不要只在 `5s` 后检查，因为抖音的 toast 可能只保留约 `3s`。

## Script

优先使用脚本 [scripts/douyin_publish.py](./scripts/douyin_publish.py)。

常用调用：

```powershell
python .\skills\douyin-publish-video\scripts\douyin_publish.py --video C:\path\video.mp4
python .\skills\douyin-publish-video\scripts\douyin_publish.py --video C:\path\video.mp4 --continue-after-upload --title "标题" --description "简介" --dry-run
python .\skills\douyin-publish-video\scripts\douyin_publish.py --video C:\path\video.mp4 --continue-after-upload --title "标题" --topic "话题A" --topic "话题B"
```

脚本约定：

- 默认连接 `http://127.0.0.1:9222`
- 默认只要进入自动填写阶段，就会继续执行到真正发布；传 `--dry-run` 才暂停
- 只做首次上传的 happy path，不处理恢复旧草稿
- 只有显式传入 `--continue-after-upload` 才会继续自动填写标题/简介/话题
- 失败时保存截图
- 成功时打印 `RESULT_JSON:<json>`

## Validation

每次修改这个技能后，至少做下面这些检查：

1. 运行 `--help`，确认 CLI 参数没坏。
2. 在真实的抖音创作者中心页面上，验证能进入上传页并找到 `input[type=file]`。
3. 默认使用 `--dry-run` 做验证；只有用户明确接受真实发布风险时再做真实发布测试。

## Failure Handling

- 找不到浏览器调试端口时，提示先用带 `--remote-debugging-port=9222` 的 Chrome/Brave 打开浏览器。
- 找不到上传输入框时，截图并输出当前 URL、标题和页面前几百字文本。
- 上传后迟迟不出现表单时，截图并报告仍停留在上传/转码阶段。
- 点击发布前如果检测到额外确认弹窗，优先记录弹窗文案，再按显式文案按钮处理。
- 如果发布后短 toast 提示 `请设置封面后再发布`，先原样上报这个提示，说明流程还没真正完成，不要误报成功。

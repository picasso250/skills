# Failure Modes

## Browser Endpoint Unavailable

现象：
- `http://127.0.0.1:9222` 不可访问
- 脚本报连接 CDP 失败

处理：
- 确认浏览器已使用 `--remote-debugging-port=9222` 启动
- 如果用户平时使用的不是 Brave，先定位实际浏览器路径再启动

## Page Requires Login

现象：
- 页面打开后是登录页、权限提示页或空白框架

处理：
- 说明该 skill 依赖当前浏览器会话
- 如果当前会话未登录，先提示用户登录，再重新运行

## SPA Or Slow DOM Stabilization

现象：
- 输出内容明显不完整
- 页面只抓到壳、导航或占位内容

处理：
- 增加 `--timeout`
- 如果仍不稳定，改用 `browser` 做更明确的等待或交互

## Wrong Tab Reuse Or New Tab Creation

现象：
- 没复用到用户正在看的 tab
- 新开页内容和用户当前上下文不一致

处理：
- 明确告诉用户当前是按 URL 匹配页面
- 如果需要“完全同步用户当前正在看的 tab 状态”，后续应扩展脚本，按更严格的 tab/context 规则匹配

## Noisy DOM Output

现象：
- Markdown 混入大量导航、推荐区、页脚、广告位

处理：
- 在回答中明确这是 DOM 直出结果
- 优先提炼标题、正文、表格、主链接
- 如果任务强依赖视觉上下文，改用 `screenshot-webpage`

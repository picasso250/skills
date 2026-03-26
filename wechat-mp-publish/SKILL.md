---
name: wechat-mp-publish / 发布到微信公众号
description: Browser automation skill for publishing to WeChat Official Accounts (mp.weixin.qq.com). 将微信公众号后台发布流程拆成逐步验证脚本，再确认后合并为主 CLI。
---

# WeChat MP Publish

将微信公众号后台的发布流程拆成一系列可验证的小脚本。
每次只推进一步：先写验证脚本，等用户确认，再合并到主脚本，然后继续下一步。

## Workflow

1. 先连接用户已经登录的 Chrome/Edge `--remote-debugging-port=9222` 会话。
2. 每一步先写一个最小验证脚本，只验证一个动作。
3. 用户确认该动作符合预期后，再把这一步合并到主脚本。
4. 重复这个循环，直到完整发布流程稳定。

## Validation Scripts

第一步验证脚本：
- [scripts/verify_open_home.py](./scripts/verify_open_home.py)
- 作用：打开新的标签页到微信公众号后台首页，供用户确认页面、登录态和目标地址正确。

第二步验证脚本：
- [scripts/verify_find_content_management_and_click.py](./scripts/verify_find_content_management_and_click.py)
- 作用：复用已经打开的微信公众号后台 tab，找到“内容管理”，并在其中心附近执行一次点击。

第三步验证脚本：
- [scripts/verify_find_draft_box_and_click.py](./scripts/verify_find_draft_box_and_click.py)
- 作用：复用已经打开的微信公众号后台 tab，找到“草稿箱”，并在点击前等待约 `1 +/- 0.5s` 后执行一次中心附近随机物理点击。

第四步验证脚本：
- [scripts/verify_find_new_creation_and_hover.py](./scripts/verify_find_new_creation_and_hover.py)
- 作用：复用已经打开的微信公众号后台 tab，找到“新的创作”，并在 hover 前等待约 `1 +/- 0.5s` 后执行一次中心附近随机物理悬停。

第五步验证脚本：
- [scripts/verify_click_write_new_article.py](./scripts/verify_click_write_new_article.py)
- 作用：复用已经打开的微信公众号后台 tab，找到“写新文章”，并在点击前等待约 `1 +/- 0.5s` 后执行一次中心附近随机物理点击，同时记录点击前后 URL 变化。

第六步验证脚本：
- [scripts/verify_list_new_tab_buttons.py](./scripts/verify_list_new_tab_buttons.py)
- 作用：复用“写新文章”新打开 tab 的 `wsEndpoint`，读取该页面里所有可见按钮类元素的关键信息并打印出来，供下一步选择目标控件。

第七步验证脚本：
- [scripts/verify_input_title.py](./scripts/verify_input_title.py)
- 作用：复用文章编辑页，物理点击标题输入框并通过键盘事件输入标题文本。

第八步验证脚本：
- [scripts/verify_input_author.py](./scripts/verify_input_author.py)
- 作用：复用文章编辑页，物理点击作者输入框并通过键盘事件输入作者文本。

第九步验证脚本：
- [scripts/verify_input_body.py](./scripts/verify_input_body.py)
- 作用：复用文章编辑页，物理点击正文编辑区并通过键盘事件输入正文文本。

第十步验证脚本：
- [scripts/verify_click_publish_and_diff.py](./scripts/verify_click_publish_and_diff.py)
- 作用：复用文章编辑页，物理点击“发表”，等待 `2.5s`，然后对点击前后的 DOM 快照做 diff，帮助识别错误提示或新弹层。

第十一步验证脚本：
- [scripts/verify_click_go_declare.py](./scripts/verify_click_go_declare.py)
- 作用：复用文章编辑页在发表后的声明来源弹层中，物理点击“去声明”。

第十二步验证脚本：
- [scripts/verify_unset_original_then_confirm.py](./scripts/verify_unset_original_then_confirm.py)
- 作用：复用文章编辑页，按顺序物理点击“未声明”、输入作者、点击“我已阅读并同意”，再点击“确定”。

第十三步验证脚本：
- [scripts/verify_observe_declare_controls.py](./scripts/verify_observe_declare_controls.py)
- 作用：在声明流程里先观察并打印“未声明”、作者输入框、“我已阅读并同意”相关 checkbox、以及“确定”按钮的候选元素，再决定下一步点击哪个。

第十四步验证脚本：
- [scripts/verify_input_declare_author.py](./scripts/verify_input_declare_author.py)
- 作用：复用声明弹框，物理点击真实作者输入框并通过键盘事件输入作者文本。

第十五步验证脚本：
- [scripts/verify_observe_declare_checkbox.py](./scripts/verify_observe_declare_checkbox.py)
- 作用：在声明弹框里只观察“我已阅读并同意”对应的 checkbox、图标、label 和文本区域，确认真正应该点击哪个节点。

第十六步验证脚本：
- [scripts/verify_click_declare_checkbox.py](./scripts/verify_click_declare_checkbox.py)
- 作用：复用声明弹框，物理点击“我已阅读并同意”对应的 checkbox 图标本体，而不是文字链接。

第十七步验证脚本：
- [scripts/verify_click_declare_confirm.py](./scripts/verify_click_declare_confirm.py)
- 作用：复用声明弹框，物理点击“确定”按钮。

第十八步验证脚本：
- [scripts/verify_input_declare_author_and_tab.py](./scripts/verify_input_declare_author_and_tab.py)
- 作用：复用声明弹框，物理输入作者后再按 `Tab` 失焦，验证校验状态是否刷新。

## Main Script

主脚本：
- [scripts/wechat_mp_publish.py](./scripts/wechat_mp_publish.py)
- 当前先保留最小能力，只合并已经被用户确认过的步骤。
- 当前主脚本不需要业务参数；除了默认的 `--help` 外，直接执行固定流程。
- 当前已合并的流程：打开微信公众号后台首页，等待约 `5 +/- 0.5s`，物理点击“内容管理”，记录点击前后 URL 变化，再物理点击“草稿箱”，再次记录点击前后 URL 变化，物理 hover “新的创作”，再物理点击“写新文章”，记录新打开 tab 的 URL 与 `wsEndpoint`，然后在文章编辑页物理输入标题、作者和正文，点击“发表”进入声明来源弹层，点击“去声明”，再点击“未声明”，并在声明弹框里输入作者、勾选协议 checkbox，最后点击“确定”。

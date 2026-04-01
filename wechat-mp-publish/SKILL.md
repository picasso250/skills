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

## Content Workflow

这个技能现在分成两段：

1. 内容生产前置流程：从主题到终稿。
2. 发布自动化流程：把终稿送进微信公众号编辑器，并停在适合人工接管的位置。

内容生产前置流程默认使用英文工作目录：

- 基础目录：`~/Documents/wechat-post-workbench`
- 每篇文章一个英文子目录，禁止中文目录名。
- 典型文件：
  - `brief.md`：用户给的主题、灵感或一句话要求。
  - `research.md`：调研结果。
  - `draft.md`：首稿。
  - `critique_round1.md`：第一轮批判。
  - `final.md` 或 `draft_round2.md`：修订稿/终稿。

辅助脚本：

- [scripts/wechat_topic_workflow.py](./scripts/wechat_topic_workflow.py)
- 作用：只负责创建英文工作目录。

建议流程：

1. 运行 `python scripts/wechat_topic_workflow.py --topic "<topic>" --slug "<english-slug>"` 创建工作目录。
2. 由 AI 调研，并把结果写入该目录下的 `research.md`。
3. 由 AI 自由决定如何调研、如何组织材料，并在需要时调用 `gemini.cmd --yolo -p "<单行长提示词>"` 生成 `draft.md`。
4. 由 AI 阅读 `draft.md`，写出 `critique_round1.md`，明确指出标题、开头、结构、事实边界、传播性、金句密度、冗余段落等问题。
5. 由 AI 自由决定是否再次调用 `gemini.cmd --yolo -p "<单行长提示词>"` 生成 `final.md` 或 `draft_round2.md`。
6. 如有必要，继续多轮批判和改稿，直到终稿成立。
7. 每次调用 `gemini.cmd` 之后，不要只相信它口头说“已写入文件”，必须检查目标文件是否真的存在、内容是否真的落盘。

边界：

- 不要向前兼容旧目录结构，直接使用 `wechat-post-workbench`。
- 不要把“如何写提示词、是否继续迭代、迭代几轮”过度脚本化，这些交给 AI 在每次任务里按上下文判断。
- 不要把“自动识别图片控件并全自动完封面”继续做深；当前技能到“打开编辑器、粘贴正文”已经足够，剩余复杂交互让用户人肉接管。

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

第十九步验证脚本：
- [scripts/verify_paste_body_from_clipboard.py](./scripts/verify_paste_body_from_clipboard.py)
- 作用：复用文章编辑页，把正文送入系统剪贴板后，物理点击正文编辑区，执行 `Ctrl+V` 粘贴，再按一次 `Enter`，验证正文改用剪贴板粘贴是否稳定。

第二十步验证脚本：
- [scripts/verify_observe_cover_controls.py](./scripts/verify_observe_cover_controls.py)
- 作用：复用文章编辑页，只观察并打印与“封面/题图/上传图片/修改图片”相关的可见候选节点和位置，先确认真正应该点击的封面入口。

第二十一步验证脚本：
- [scripts/verify_hover_cover_and_observe_ai_image.py](./scripts/verify_hover_cover_and_observe_ai_image.py)
- 作用：复用文章编辑页，物理 hover “拖拽或选择封面”区域，然后只观察 hover 后是否出现 “AI 配图” 等候选入口，先验证交互路径。

第二十二步验证脚本：
- [scripts/verify_click_ai_cover.py](./scripts/verify_click_ai_cover.py)
- 作用：复用文章编辑页，先物理 hover “拖拽或选择封面”，再物理点击弹层中的 “AI 配图” 入口，但不处理其后的弹窗或生成流程。

第二十三步验证脚本：
- [scripts/verify_observe_ai_cover_dialog.py](./scripts/verify_observe_ai_cover_dialog.py)
- 作用：复用文章编辑页，进入 “AI 配图” 后只观察 “请描述你想要的创作内容” 输入区和 “开始创作” 按钮的真实节点、位置和候选选择器。

第二十四步验证脚本：
- [scripts/verify_observe_ai_cover_dialog_open.py](./scripts/verify_observe_ai_cover_dialog_open.py)
- 作用：假设 “AI 配图” 弹框已经打开，只复用当前编辑页并观察 “请描述你想要的创作内容” 与 “开始创作” 这两个元素；脚本不包 `try/except`，直接暴露失败现场。

第二十五步验证脚本：
- [scripts/verify_input_ai_cover_prompt.py](./scripts/verify_input_ai_cover_prompt.py)
- 作用：假设 “AI 配图” 弹框已经打开，物理点击 `textarea#ai-image-prompt` 输入创作提示词，并观察 “开始创作” 是否从禁用态变为可点击。

第二十六步验证脚本：
- [scripts/verify_observe_ai_cover_start_button.py](./scripts/verify_observe_ai_cover_start_button.py)
- 作用：假设 AI 配图弹框和提示词都已就位，只观察真实的 “开始创作” 按钮节点、位置和禁用状态，不重复输入提示词。

第二十七步验证脚本：
- [scripts/verify_click_ai_cover_start.py](./scripts/verify_click_ai_cover_start.py)
- 作用：假设 AI 配图弹框和提示词都已就位，物理点击 “开始创作”，只观察点击后的生成状态变化，不处理后续选图或确认流程。

第二十八步验证脚本：
- [scripts/verify_observe_ai_cover_results.py](./scripts/verify_observe_ai_cover_results.py)
- 作用：假设 AI 配图已经生成完成，只观察新出现的候选图片、各自的分数文案，以及对应的 “插入” 入口，不执行选择动作。

第二十九步验证脚本：
- [scripts/verify_hover_first_ai_cover_result.py](./scripts/verify_hover_first_ai_cover_result.py)
- 作用：假设 AI 配图已经生成完成，物理 hover 第一张主结果图，观察是否浮现 “使用” 按钮，并确认真实节点与位置。

## Main Script

主脚本：
- [scripts/wechat_mp_publish.py](./scripts/wechat_mp_publish.py)
- 当前先保留最小能力，只合并已经被用户确认过的步骤。
- 当前主脚本支持 `--title`、`--author`、`--content`、`--input-path`；默认可直接执行固定流程。
- 当前已合并的流程：打开微信公众号后台首页，等待约 `5 +/- 0.5s`，物理点击“内容管理”，记录点击前后 URL 变化，再物理点击“草稿箱”，再次记录点击前后 URL 变化，物理 hover “新的创作”，再物理点击“写新文章”，记录新打开 tab 的 URL 与 `wsEndpoint`，然后在文章编辑页物理输入标题、作者和正文，并停在编辑页等待用户接管。

---
name: continue-on-phone
description: 把当前 agent 对话接到手机上。用户用 start_scan.py 打印二维码，你用 interact.py 追加文本并拉取新的用户消息。当用户说“我想在手机上继续聊”“给我一个二维码让我手机接着用”“把当前 agent 对话切到手机上”这类意思时，使用这个 skill。
---

# Skill: continue-on-phone

- `start_scan.py` 新建或复用 session，并在终端打印二维码
- `interact.py --text ...` 把 agent 消息写入 session，然后等待并拉取新用户消息 interact.py 会每 5 秒轮询，收到用户消息会提前返回，不一定睡满

## Usage

7. 开启扫码：

```powershell
python .\scripts\start_scan.py
```

然后给用户展示那个二维码（一般打开png图片即可），让用户扫码。扫码后用户会进入一个手机聊天页，和当前 agent（也就是你） 对话继续。

10. 扫码后继续在终端执行如下类似命令：

```powershell

# 当你认为需要通知用户的时候就可以执行这个命令，这个脚本会把文本追加到 session 里，并等待用户回复。
python .\scripts\interact.py --text "通知：我要实验A方案了" --wait-seconds 30 # 这里的 --wait-seconds 是等待用户回复的秒数，默认是30秒，你可以根据需要调整这个时间。

# 当你觉得重要的决策需要用户确认时
python .\scripts\interact.py --text "你觉得选择哪个方案更好？" --wait-seconds 300

# 当你做完了所有任务，则进入等待模式
python .\scripts\interact.py --text "任务已经完成。以下是任务简报：xxxx" --wait-seconds 3600 # 等待约1个小时

# 当你等待了1个小时，用户仍然没有回复
python .\scripts\interact.py --text "我已经等了很久了，你还在吗？如果你不回复，我将认为你已离开。" --wait-seconds 36000 # 最后等待10个小时，如果用户仍然没有回复，就认为用户离开了，agent 可以选择结束对话。
```


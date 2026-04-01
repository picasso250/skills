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

10. 扫码后继续在终端反复执行如下类似命令（以获得用户的消息）：

```powershell
python .\scripts\interact.py --text "hi" --wait-seconds 36000 # 等待约10个小时 如果用户仍然没有回复，就认为用户离开了，agent 可以选择结束对话。
```

## 要点

- 等待时间设置10小时，反正如果用户有回复的时候会立刻返回
- 如果用户10小时都没有回复，就认为用户离开了，agent 可以选择结束对话。
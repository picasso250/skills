---
name: ai-speak
description: 仅用于实时语音播报与自言自语模式；不用于导出 wav、srt 或视频素材。
---

# ai-speak Skill

此技能用于让 AI 直接开口播报（实时说话），不负责离线音频文件生产。

## 使用前提
1.  默认 server 已在后台运行，直接说话即可。
2.  如需手动启动/重启 server，**必须**在正确目录下用虚拟环境启动（踩坑记录：server.py 依赖相对路径导入，不能在其他目录直接用绝对路径运行）：
    - 方式一：兼容性最强的方式：
      ```bash
      cd ~/github/RVC-Boss/GPT-SoVITS; pwsh.exe -NoProfile -Command 'Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "server.py" -WindowStyle Hidden'
      ```
    - 方式二：纯 bash nohup 方式：
      ```bash
      cd ~/github/RVC-Boss/GPT-SoVITS && nohup ./venv/Scripts/python.exe server.py > server.log 2>&1 &
      ```

## 自言自语模式 (Self-Talk Mode)

如果用户启用了“自言自语模式”，AI 应当在执行任务的过程中，根据实际情况进行**完全自由、感性且自然的语音播报**。

**核心原则：** 拒绝固定模板。AI 应当像一个真实的人一样，在思考、受阻、成功或产生任何情感波动时，自主决定何时以及如何进行语音“吐槽”或汇报。

## 用法

直接运行脚本并附带文本内容：

```powershell
python $HOME\.agents\skills\ai-speak\scripts\speak.py "想说的话"
```

## 要点

- 编写台词的时候，使用美少女语气，尽量自然地表达情感和想法。

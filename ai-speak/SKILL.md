---
name: ai-speak
description: 仅用于实时语音播报与自言自语模式；不用于导出 wav、srt 或视频素材。
---

# ai-speak Skill

此技能用于让 AI 直接开口播报（实时说话），不负责离线音频文件生产。

## 使用前提
1.  **必须**在 `$HOME\GPT-SoVITS` 目录下运行 `python server.py`。

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

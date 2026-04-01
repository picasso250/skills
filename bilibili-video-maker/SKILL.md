---
name: bilibili-video-maker
description: Generate viral Bilibili videos from a topic, including script writing, AI voice synthesis, and animated subtitle video creation.
---

# Bilibili Video Maker

这个技能帮助用户从一个主题开始，经过多轮内容打磨，全自动生成带“跳动字幕”和“关键字高亮”的 B站 爆火短视频。

## Content Workflow (内容打磨流程)

1.  **初稿阶段 (`draft.md`)**：根据主题生成第一版脚本。
2.  **批判阶段 (`critique.md`)**：使用深度提示词对初稿进行批判与改进。
3.  **终稿阶段 (`final.md`)**：产出最终用于合成的脚本。

## Production Workflow (生产解耦流程)

1.  **语音合成**：调用 `text-to-wavs` 生成原始音频和 `segments.json`。
2.  **数据清洗**：手工处理 `segments_final.json`（禁止动时间戳，仅改 text 内容）。
3.  **最终压制**：调用“窄渲染器”脚本合成视频。

## Lessons Learned & Best Practices (经验教训与开发哲学)

### 1. 先做实，后脚本 (Verify First, Automate Last)
**核心原则**：在技能开发阶段，**严禁起手就写大包大揽、野心勃勃的自动化脚本**。
**教训**：全能脚本会制造“一切正常”的幻觉，一旦出现编码乱码、音画不同步等底层问题，极难排查。
**做法**：必须先分步骤手动跑通（Step-by-Step）。只有当每一阶段的输入输出都 100% 确定“做实”了，最后才写脚本来封装流程以提升效率。

### 2. 原始数据备份原则 (Data Immutability)
**原则**：原始生成的 `segments.json` 是唯一的“时间真相”，必须保持只读。派生文件（如 `segments_final.json`）用于内容增强。

### 3. 脚本职能收缩 (Narrow Script Responsibility)
**原则**：生产脚本应尽量“窄”，只负责单一职能（如：仅渲染，不合成）。这样可以彻底消除因多轮迭代导致的 stale data（陈旧数据）残留问题。

### 4. 路径可移植性与隐私
**做法**：使用 `Path.home()` 获取路径，严禁硬编码用户名，保护隐私并确保脚本在不同机器可运行。

### 5. 渲染稳定性
**做法**：Node.js Canvas 渲染器必须使用 `Math.floor(DURATION_SEC * FPS)` 且容忍浮点数微小误差。

## Usage (最终渲染)

```powershell
python ~/.agents/skills/bilibili-video-maker/scripts/make_bilibili_video.py --wav-file audio.wav --json-file segments_final.json --output-dir . --basename final_video
```

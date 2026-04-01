---
name: bilibili-video-maker
description: Generate viral Bilibili videos from a topic, including script writing, AI voice synthesis, and animated subtitle video creation.
---

# Bilibili Video Maker

这个技能帮助用户从一个主题开始，经过多轮内容打磨，全自动生成带“跳动字幕”和“关键字高亮”的 B站 爆火短视频。

## Content Workflow (内容打磨流程)

### Step 0: 初始化项目空间 (Mandatory)
当接收到一个新主题时，**第一步必须是**在 `~/Videos/bilibili` 下创建一个以主题英文名为名称的文件夹。所有后续产物（draft, final, audio, json）必须全部存放在该文件夹内。

### Step 1: 初稿阶段 (`draft.md`)
根据主题生成第一版脚本，保存在项目文件夹中。

### Step 2: 批判阶段 (`critique.md`)
使用深度提示词对初稿进行批判与改进。

### Step 3: 终稿阶段 (`final.md`)
产出最终用于合成的脚本。

## Production Workflow (生产解耦流程)

1.  **语音合成**：调用 `text-to-wavs` 生成原始音频和 `segments.json`。
2.  **数据清洗**：
    -   **备份**：将 `segments.json` 另存为 `segments_final.json`。
    -   **编辑**：在 `text` 字段插入 `\n` 换行和 `*关键词*` 高亮（禁止动时间戳）。
    -   **去标点**：运行 `clean_punctuation.py` 删除行末冗余标点。
3.  **最终压制**：调用“窄渲染器”脚本合成视频。

## Workspace Standard

-   **根目录**：`~/Videos/bilibili`
-   **隔离原则**：禁止在根目录下直接生成文件。每个项目必须有独立文件夹。

## Lessons Learned & Best Practices
[保持原有内容...]

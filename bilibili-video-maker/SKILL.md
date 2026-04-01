---
name: bilibili-video-maker
description: Generate viral Bilibili videos from a topic, including script writing, AI voice synthesis, and animated subtitle video creation.
---

# Bilibili Video Maker

这个技能帮助用户从一个主题开始，经过多轮内容打磨，全自动生成带“跳动字幕”和“关键字高亮”的 B站 爆火短视频。

## Content Workflow (内容打磨流程)

### Step 0: 初始化项目空间 (Mandatory)
当接收到一个新主题时，**第一步必须是**在 `~/Videos/bilibili` 下创建一个以主题英文名为名称的文件夹。所有后续产物（draft, final, audio, json）必须全部存放在该文件夹内。禁止在根目录下直接生成文件。

### Step 1: 初稿阶段 (`draft.md`)
根据主题生成第一版脚本，保存在项目文件夹中。

### Step 2: 批判阶段 (`critique.md`)
使用深度提示词对初稿进行批判与改进。

### Step 3: 终稿阶段 (`final.md`)
产出最终用于合成的脚本。

## Production Workflow (生产解耦流程)

1.  **语音合成**：调用 `text-to-wavs` 生成原始音频和 `segments.json`。
2.  **数据清洗**：
    -   **版本隔离**：将 `segments.json` 另存为 `segments_final.json`。
    -   **人工编辑**：在 `text` 字段插入 `\n` 换行和 `*关键词*` 高亮（禁止动时间戳）。
    -   **去标点**：运行以下指令删除行末冗余标点：
        ```powershell
        python ~/.agents/skills/bilibili-video-maker/scripts/clean_punctuation.py --json-file segments_final.json
        ```
3.  **最终压制**：调用“窄渲染器”脚本合成视频：
    ```powershell
    python ~/.agents/skills/bilibili-video-maker/scripts/make_bilibili_video.py --wav-file audio.wav --json-file segments_final.json --output-dir . --basename final_video
    ```

## Lessons Learned & Best Practices (经验教训与开发哲学)

### 1. 先做实，后脚本 (Verify First, Automate Last)
**核心原则**：在技能开发阶段，严禁起手就写大包大揽的自动化脚本。必须分步跑通并“做实”，最后才写脚本。

### 2. 原始数据备份原则 (Data Immutability)
**原则**：原始生成的 `segments.json` 是“时间真相”，必须保持只读。任何修改必须在派生文件（`segments_final.json`）中进行。

### 3. 字幕排版优化 (Typography)
**做法**：短视频字幕应尽量精简。通过脚本去除行末标点（逗号、句号），可以让画面更干净、居中感更强。

### 4. 路径可移植性与隐私
**做法**：使用 `Path.home()` 获取路径，严禁硬编码用户名。

### 5. 渲染稳定性
**做法**：Node.js Canvas 渲染器必须使用 `Math.floor(DURATION_SEC * FPS)` 且容忍浮点数微小误差。

## Output

-   `*_animated_final.mp4`: 最终成品视频。

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

1.  **分段与校验 (Pre-production)**：
    -   将 `final.md` 的口播内容按意群手工拆分为序列文件（如 `001.txt`, `002.txt` ...）。
    -   **硬性约束**：每个文件仅允许**纯中文**，且长度严禁超过 **106 个字符**。
    -   编写/运行校验脚本，确保所有分段均符合上述长度与字符集要求。
2.  **语音合成与预处理**：
    -   调用 `text-to-wavs` 批量生成对应的 WAV 音频。
    -   使用 `ffmpeg` 将合成的音频转码并合并为 `final_audio.mp3`。
3.  **对齐与生成 (Alignment)**：
    -   调用 `audio-to-srt` 技能，处理 `final_audio.mp3` 以生成原始 `segments.json` 和 `segments.srt`。
4.  **数据清洗与排版**：
    -   **版本隔离**：将 `segments.json` 另存为 `segments_final.json`。
    -   **手工精修**：在 `text` 字段插入 `\n` 换行、`*关键词*` 高亮，并**修正其中的错别字**（禁止动时间戳）。
    -   **去标点**：运行 `clean_punctuation.py` 删除行末冗余标点。
5.  **最终压制**：调用“窄渲染器”脚本合成视频：
    ```powershell
    python ~/.agents/skills/bilibili-video-maker/scripts/make_bilibili_video.py --wav-file final_audio.mp3 --json-file segments_final.json --output-dir . --basename final_video
    ```

## Lessons Learned & Best Practices (经验教训与开发哲学)

### 1. 意群切分与长度约束 (Chunking Strategy)
**核心原则**：为了确保 `text-to-wavs` 的稳定性，必须进行人工预处理。
- **纯净性**：输入文本严禁包含英文、数字或特殊符号，仅允许中文。
- **原子性**：单次合成文本长度控制在 **106 字符**以内（UTF-8 318 字节）。
- **意群优先**：切分时应保证每一段都是一个完整的语义片段，方便后期 `audio-to-srt` 精准识别。


### 2. 原始数据备份原则 (Data Immutability)
**原则**：原始生成的 `segments.json` 是“时间真相”，必须保持只读。任何修改必须在派生文件（`segments_final.json`）中进行。

### 3. 字幕排版优化 (Typography)
**做法**：短视频字幕应尽量精简。除了通过脚本去除行末标点（逗号、句号）外，**必须在 `segments_final.json` 中修正 ASR 识别出的错别字**，同时完成 `\n` 换行和 `*关键词*` 高亮。这能显著提升视频的专业度。

### 4. 路径可移植性与隐私
**做法**：使用 `Path.home()` 获取路径，严禁硬编码用户名。

### 5. 渲染稳定性
**做法**：Node.js Canvas 渲染器必须使用 `Math.floor(DURATION_SEC * FPS)` 且容忍浮点数微小误差。

### 6. 禁止使用 generalist 工具 (Anti-Pattern)
**核心禁令**：在处理 `segments_final.json` 或涉及精确时间对齐的文件时，**严禁使用 `generalist` 子代理**。
**原因**：`generalist` 倾向于通过“理解意图”来重写整个文件，这往往会导致其根据字数平摊时间轴或错误合并分段，彻底破坏音画同步。所有字幕修正必须通过 `replace` 进行局部精确修改，或由主 Agent 直接操作。

### 7. 预览稳定性 (Preview Stability)
**做法**：在使用 `ffplay` 预览产物时，**必须将输出重定向到空设备**（例如：`ffplay -i output.mp4 > $null 2>&1`），以免冗余的流信息污染终端空间。

## Output

-   `*_animated_final.mp4`: 最终成品视频。

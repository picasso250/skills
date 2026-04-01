---
name: bilibili-video-maker
description: Generate viral Bilibili videos from a topic, including script writing, AI voice synthesis, and subtitle video creation.
---

# Bilibili Video Maker

这个技能帮助用户从一个主题开始，全自动生成带字幕的 B站 爆火短视频。

## Workflow

1. **生成脚本**：根据用户提供的主题，撰写一段具有传播力的短视频脚本（约 30-60 秒）。
2. **生成视频**：调用脚本将文本合成为语音（WAV）、生成字幕（SRT）并压制成带字幕的黑屏视频。
3. **播放预览**：使用 `ffplay` 播放生成的视频供用户确认。

## Usage

### Step 1: 脚本创作
由 AI 根据主题生成脚本并保存到文本文件。建议风格：深度、扎心、干货。

### Step 2: 自动化生产
运行以下命令生成成品视频：

```powershell
python C:\Users\MECHREV\.agents\skills\bilibili-video-maker\scripts\make_bilibili_video.py --text-file C:\path\to\script.txt --output-dir C:\path\to\output --basename video_name
```

## Runtime Dependencies

- **TTS Server**: 必须确保 `C:\Users\MECHREV\github\RVC-Boss\GPT-SoVITS\server.py` 正在运行（默认端口 9888）。
- **FFmpeg**: 系统已安装。
- **Skill**: 依赖 `text-to-wavs` 技能提供的 `render_text_to_wav.py` 逻辑。

## Output

- `*.wav`: AI 合成的语音。
- `*.srt`: 自动对齐的字幕。
- `*.mp4`: 最终成品视频。

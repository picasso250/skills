---
name: audio-to-srt
description: 用户提供 wav/mp3 音频后，生成声学对齐的 srt 字幕和 asr 文本。
---

# Audio To Srt

## Overview

这个技能只做音频转字幕时间轴，不做语音合成。

## Workflow

1. 读取用户提供的音频文件（wav/mp3）。
2. 使用 FunASR 对音频做声学识别与时间对齐。
3. 输出 `srt`、`asr.txt`。

## Runtime

- GPT-SoVITS 根目录参考：`$HOME\github\RVC-Boss\GPT-SoVITS`
- 依赖 GPT-SoVITS `venv` 内已安装的 `funasr`。
- 如输入不是 wav，脚本会调用 `ffmpeg` 转成临时 wav 再做识别。

## Usage

```powershell
python audio-to-srt/scripts/render_audio_to_srt.py --audio-file C:\path\to\input.wav --output-dir C:\path\to\out --output-basename demo
```

`--output-basename` 为必填，用于显式指定输出文件名前缀，避免后续流程误拿错文件。

```powershell
python audio-to-srt/scripts/render_audio_to_srt.py --audio-file C:\path\to\input.mp3 --output-dir C:\path\to\out --output-basename demo
```

默认输出为安静模式，只打印产物路径和分段数。需要查看 FunASR 原始进度条、依赖 warning 或调试日志时，加 `--verbose`。

## Output

- `*.srt`: 字幕文件
- `*.asr.txt`: ASR 识别文本（每行一段）

---
name: text-to-wavs
description: 用户提供文本后生成 wav 音频与 srt/json 字幕时间轴。
---

# Text To Wavs

## Overview

这个技能会把用户文本直接合成为 wav，并同时输出 srt 与 segments.json。

## Workflow

1. 读取用户提供的原始 txt。
2. 清洗文本并整段合成 wav。
3. 基于文本语义分句生成 srt/json 时间轴。
4. 返回输出目录路径。

## Cleaning Rules

- 删除空行、编号、无意义分隔符、明显不需要朗读的注释。
- 保留正常标点，不随意改写语义。
- 字幕分句按标点切，优先语义完整。

## Input Constraints

- 文本尽量纯中文，但仍然可以有少量英文缩写和单词。
- 单次合成文本长度建议为 100 个中文字（包含标点），最多不超过 200 个中文字。

## Runtime

- GPT-SoVITS 根目录参考：`$HOME\github\RVC-Boss\GPT-SoVITS`
- 脚本直接参考该目录下 `server.py` 使用的模型配置和推理函数，但不通过 HTTP 服务批量调用。
- 当前配置固定为刘亦菲音色，因此本技能也只面向刘亦菲音色。
- 如果 `GPT-SoVITS\venv\Scripts\python.exe` 存在，脚本会优先自动切到那个解释器再执行。

## Usage

准备原始文本后，运行：

```powershell
python text-to-wavs/scripts/render_text_to_wav.py --text-file C:\path\to\raw.txt --output-dir C:\path\to\out
```

可选指定输出文件前缀：

```powershell
python text-to-wavs/scripts/render_text_to_wav.py --text-file C:\path\to\raw.txt --output-dir C:\path\to\out --output-basename demo
```

## Output

- `*.wav`: 合成语音
- `*.srt`: 字幕文件
- `*.segments.json`: 字幕分段及时间戳（秒）

脚本会打印 `OUTPUT_DIR`、`OUTPUT_WAV`、`OUTPUT_SRT`，后续直接把该目录交给用户即可。

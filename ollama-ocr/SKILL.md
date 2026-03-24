---
name: ollama-ocr
description: 本地 OCR 提取工具。使用 Ollama 运行多模态模型（默认 minicpm-v）来提取图片文字、识别表格或解析文档结构。支持通过命令行脚本批量或单张处理。
---

# Ollama OCR Skill

## Description
利用本地安装的 Ollama 运行多模态视觉模型（默认 `minicpm-v`）来提取图片内容。此技能特别适用于本地化、高隐私、无联网要求的 OCR 任务。

## Available Resources
- Ollama CLI (`ollama`)
- 模型：`minicpm-v` (已验证可运行), `qwen2.5vl:3b` (备选)
- 脚本：`scripts/ocr_tool.py` (支持 `--file` 参数)

## Instructions

### 1. 使用专用脚本进行 OCR (推荐)
通过内置 Python 脚本提取文字，支持详细参数：
- 命令：`python scripts/ocr_tool.py --file [IMAGE_PATH]`
- 进阶：可以使用 `--prompt` 自定义提示词，或使用 `--model` 切换模型。

### 2. 直接命令行调用
如果你想快速执行，可以直接使用：
- 命令：`ollama run minicpm-v "请提取这张图片中的所有文字并保持原有格式：[IMAGE_PATH]"`

### 3. 表格与排版识别
如果你需要提取表格或 Markdown 格式：
- 命令：`python scripts/ocr_tool.py --file [IMAGE_PATH] --prompt "请识别图中的表格并以 Markdown 格式输出："`

## Constraints
- 必须确保 Ollama 服务正在后台运行（托盘图标）。
- 首次使用某个模型时，Ollama 会自动下载（几 GB 大小），请确保磁盘空间充足。
- 如果遇到内存不足报错（Error 500），请关闭其他占用显存/内存的应用，或切换至更轻量的模型如 `moondream`。

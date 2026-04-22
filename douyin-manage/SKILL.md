---
name: douyin-manage
description: 从已打开的抖音创作者中心作品管理页提取第一屏作品列表数据，并导出为 JSON 或 CSV。用于用户要求“提取抖音作品管理页数据”“导出当前作品列表”“抓取 creator.douyin.com/creator-micro/content/manage 中的作品信息”这类场景；默认复用当前浏览器会话，不重新登录，也不滚动页面。
---

# Douyin Manage

## Overview

附着到已经打开并已登录的抖音创作者中心 `https://creator.douyin.com/creator-micro/content/manage` 页面，从当前作品管理列表中提取结构化数据。

默认输出每条作品的可见字段，包括：
- 时长或图文张数
- 标题/文案
- 发布时间
- 状态和私密标记
- 播放、点赞、评论、分享等指标
- 当前可见操作按钮

## Prerequisite

- 浏览器已开启 `--remote-debugging-port=9222`
- 抖音创作者中心已登录
- 目标页面已在当前浏览器会话中打开

## Workflow

1. 默认复用当前已打开的 `creator-micro/content/manage` tab。
2. 只导出第一屏当前已加载的作品卡片，不滚动页面。
3. 默认导出 JSON；如果用户要进表格软件，改用 CSV。
4. 导出后检查 `total_count`、`active_tab`、`extracted_count` 是否符合页面可见状态。

## Quick Start

导出当前已加载的作品卡片到 stdout：

```powershell
python .\skills\douyin-manage\scripts\extract_douyin_manage.py
```

保存为 JSON：

```powershell
python .\skills\douyin-manage\scripts\extract_douyin_manage.py --output C:\temp\douyin-works.json
```

导出为 CSV：

```powershell
python .\skills\douyin-manage\scripts\extract_douyin_manage.py --format csv --output C:\temp\douyin-works.csv
```

只抽前 20 条，便于快速验证：

```powershell
python .\skills\douyin-manage\scripts\extract_douyin_manage.py --limit 20
```

补充：当前 `scripts/` 下还放有两个相关脚本，分别用于点开私密作品预览后抓取真实互动指标（如评论/收藏），以及在已有 URL 清单的前提下下载私密视频音频；它们可视作本技能的临时旁支能力，后续边界再定。

## Output Notes

- JSON 输出包含页面级元数据：`page_title`、`page_url`、`active_tab`、`total_count`、`extracted_count`、`items`
- CSV 会把常见指标展开成列，例如 `metric_播放`、`metric_点赞`
- 该技能只提取第一屏当前 DOM 已加载的数据
- 页面样式类名可能随抖音前端版本变化；若脚本失效，优先重新观察当前 tab 的 DOM，再调整选择器

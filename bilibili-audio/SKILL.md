---
name: bilibili-audio
description: 从已经打开的 Bilibili 视频页里提取音频并保存为本地 m4a 文件。适用于用户已经在浏览器里打开目标视频，并且浏览器已启用 remote debugging 的场景。
---

# Skill: bilibili-audio

从用户已经打开的 Bilibili 视频页面中提取最佳音频流，并保存为本地 `.m4a` 文件。

这个技能依赖浏览器已开启 Chrome DevTools 远程调试端口，默认连接 `http://localhost:9222`。

## Usage

```powershell
python bilibili-audio/scripts/get_bilibili_audio.py BV1xxxxxxxxxx
python bilibili-audio/scripts/get_bilibili_audio.py BV1xxxxxxxxxx --ws ws://127.0.0.1:9222/devtools/browser/...
```

## Workflow

- 优先复用用户当前已经打开的 Bilibili 视频页，不主动新开视频页。
- 先通过页面内 `fetch` 请求 Bilibili 接口获取 `cid` 和播放地址。
- 选择 `dash.audio` 中带宽最高的一条音频流。
- 通过当前浏览器上下文抓取音频二进制，转成本地 `.m4a` 文件。

## Notes

- 使用前应确保目标视频页已经在浏览器中打开。
- 如果当前 DevTools 会话里没有匹配的 Bilibili 视频页，脚本会直接失败，不自动搜索站外资源。
- 输出文件名默认取视频标题并做基本文件名清洗。

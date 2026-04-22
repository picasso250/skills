---
name: bilibili-downloader
description: 从已经打开的 Bilibili 视频页里提取音频流、视频流，并可保存为本地 m4a 或合并后的 mp4 文件。适用于用户已经在浏览器里打开目标视频，并且浏览器已启用 remote debugging 的场景。
---

# Skill: bilibili-downloader

从用户已经打开的 Bilibili 视频页面中提取最佳音频、视频流，并支持合并为本地 `.mp4` 文件。

这个技能依赖浏览器已开启 Chrome DevTools 远程调试端口，默认连接 `http://localhost:9222`。

## Usage

```powershell
# 下载音频 + 视频并合并 (默认)
python bilibili-downloader/scripts/get_bilibili_media.py BV1xxxxxxxxxx

# 仅下载音频 (.m4a)
python bilibili-downloader/scripts/get_bilibili_media.py BV1xxxxxxxxxx --type audio

# 仅下载无声视频 (.mp4)
python bilibili-downloader/scripts/get_bilibili_media.py BV1xxxxxxxxxx --type video
```

## Workflow

- **自动探测**：通过 `/json/version` 自动发现浏览器的 WebSocket 调试地址。
- **页面复用**：优先复用用户当前已经打开的 Bilibili 视频页，不主动新开视频页。
- **浏览器下载**：利用浏览器已有的会话和身份验证，在页面上下文抓取媒体二进制。
- **静默合并**：调用 `ffmpeg` 在后台静默合并音频和视频。

## Notes

- 使用前应确保目标视频页已经在浏览器中打开。
- 需要系统安装 `ffmpeg`。
- 输出文件名取视频标题并做文件名清洗。

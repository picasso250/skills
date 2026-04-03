# fast-ntfs-file-search

这个技能通过 `~/bin/fast-ntfs.exe` 进行本机文件搜索。

依赖项目：

- FastNTFS: https://github.com/picasso250/FastNTFS

## 前置条件

- 已安装 `~/bin/fast-ntfs.exe`
- FastNTFS 服务已运行
- 可访问：`http://127.0.0.1:7788/status`

## 推荐用法

```powershell
~/bin/fast-ntfs.exe search --query "keyword"
~/bin/fast-ntfs.exe search --query "keyword" --match name --type file --limit 20
~/bin/fast-ntfs.exe search --query "keyword" --match path --type dir --limit 20
~/bin/fast-ntfs.exe search --query "keyword" --match all --type all --limit 20
```

参数：

- `--match`: `name|path|all`（默认 `name`）
- `--type`: `file|dir|all`（默认 `file`）
- `--limit`: 返回条数（默认 `50`）

## HTTP API 用法

```powershell
curl "http://127.0.0.1:7788/search?q=keyword"
curl "http://127.0.0.1:7788/search?q=keyword&mode=all&type=all&limit=20"
```

## 常见问题

### 搜索无结果

先确认 FastNTFS 服务状态：

```powershell
curl http://127.0.0.1:7788/status
```

如果 `rebuild_required=true`，请先执行一次重建并重启服务。

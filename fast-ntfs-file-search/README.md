# everything-file-search

这个技能只通过 Everything-Go 服务进行搜索：

1. `everything-go-mvp.exe search`（推荐）
2. HTTP API `http://127.0.0.1:7788/search`

不走 SQLite 直查路径。

## 前置条件

- Everything-Go 服务已运行
- 可访问：`http://127.0.0.1:7788/status`

## 推荐用法（go exe）

```powershell
everything-go-mvp.exe search --query "keyword"
everything-go-mvp.exe search --query "keyword" --match name --type file --limit 20
everything-go-mvp.exe search --query "keyword" --match path --type dir --limit 20
everything-go-mvp.exe search --query "keyword" --match all --type all --limit 20
```

参数：

- `--match`: `name|path|all`（默认 `name`）
- `--type`: `file|dir|all`（默认 `file`）
- `--limit`: 返回条数（默认 `50`）
- `--addr`: 服务地址（默认 `http://127.0.0.1:7788`）

## HTTP API 用法

```powershell
curl "http://127.0.0.1:7788/search?q=keyword"
curl "http://127.0.0.1:7788/search?q=keyword&mode=all&type=all&limit=20"
```

## 常见问题

### 搜索无结果

先确认服务状态：

```powershell
curl http://127.0.0.1:7788/status
```

如果 `rebuild_required=true`，请先执行一次重建并重启服务。

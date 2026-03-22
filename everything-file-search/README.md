# everything-file-search

这个技能通过 Everything 自带的 HTTP 服务搜索本机文件，并返回完整路径。

当前脚本默认连接：

```text
http://127.0.0.1:23324
```

所以第一次使用前，需要先安装并配置 Everything 的 HTTP Server。

## 目录结构

```text
everything-file-search/
  SKILL.md
  README.md
  scripts/
    search.py
```

## 前置条件

- Windows
- Python 3
- 已安装 `requests` 和 `beautifulsoup4`
- 已安装 Everything，并开启 HTTP Server

可安装依赖：

```powershell
pip install requests beautifulsoup4
```

## 1. 安装 Everything

如果电脑里还没有 Everything，先安装。

1. 打开 Everything 官网：<https://www.voidtools.com/>
2. 下载并安装最新版 Everything
3. 安装完成后启动 Everything

## 2. 开启 HTTP Server 并设置端口 23324

1. 打开 Everything
2. 进入 `Tools` -> `Options`
3. 在左侧找到 `HTTP Server`
4. 勾选 `Enable HTTP Server`
5. 将 `Port` 设置为 `23324`
6. 点击 `Apply`，再点击 `OK`

建议同时确认这两点：

- 本机访问地址可用：`http://127.0.0.1:23324`
- 如果系统防火墙弹窗，允许 Everything 的本地网络访问

## 3. 验证 HTTP 服务是否正常

配置完成后，在浏览器打开：

```text
http://127.0.0.1:23324
```

如果能看到 Everything 的网页搜索界面，说明 HTTP Server 已经启动成功。

## 4. 使用技能脚本搜索文件

在当前技能目录下执行：

```powershell
python .\scripts\search.py rg.exe
```

或者搜索任意关键词：

```powershell
python .\scripts\search.py "notepad"
python .\scripts\search.py "README.md"
```

脚本会输出匹配文件的完整路径，例如：

```text
C:\Users\MECHREV\AppData\Local\Programs\SomeApp\rg.exe
```

## 工作原理

`scripts/search.py` 会请求 Everything 的 HTTP 页面，解析搜索结果表格，并提取文件完整路径。

默认地址写在脚本里：

```python
search_everything(query, base_url="http://127.0.0.1:23324")
```

如果你把 Everything 的 HTTP 端口改成别的值，脚本也需要同步修改。

## 常见问题

### 浏览器打不开 `127.0.0.1:23324`

通常是以下原因之一：

- Everything 没有启动
- `HTTP Server` 没有启用
- 端口不是 `23324`
- 被防火墙拦截

### 脚本运行没有结果

先分别检查：

1. Everything 里直接搜索是否能搜到该文件
2. 浏览器访问 `http://127.0.0.1:23324/?s=关键词` 是否有结果
3. Python 依赖是否安装完整

## 给用户的设置指引

如果用户还没有 Everything，先让用户：

1. 安装 Everything
2. 打开 `Tools` -> `Options` -> `HTTP Server`
3. 勾选 `Enable HTTP Server`
4. 将端口设置为 `23324`
5. 保存设置并访问 `http://127.0.0.1:23324` 验证

完成后，这个技能就可以直接使用。

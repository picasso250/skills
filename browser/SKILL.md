---
name: browser
description: 让你可以操控浏览器（通过  rdp) 来实现各种功能。
---

# Browser Progressive Proxy

基于“渐进式披露”原则的浏览器自动化控制工具。

### 1. 启动环境
```
# 启动 Brave (或 Chrome)
& "brave.exe" --remote-debugging-port=9222 # 如果检查端口是死的，则使用 everything 技能 搜索 brave.exe 的路径 然后自己打开先
```

写临时的 python 脚本来实现你的各种功能（ playwright 已为你安装好）
先 curl -s http://localhost:9222/json 来获取 web socket 的地址，然后在脚本里连接它，之后你就可以通过 playwright 来控制浏览器了。
（同目录下有各种示例脚本，你可以参考它们来编写自己的脚本）

## 已有脚本

```
# 将指定url内容转换成 markdown格式的文本，会复用已有的tab，如果没有就新开一个tab
skills\browser\scripts\toMD.py --url <url> --timeout 10 --out-file <output.md>
```

## 典型用法
- 使用 盲人模式 来获取网页内容
- 使用 盲人模式 来获取网页，并找到bond链接，物理点击它

## 注意事项
- 你在用浏览器的时候，用户也在用浏览器，所以你，不应该直接 context = browser.contexts[0] 你应该获取所有 contexts 找到 匹配 的 url 这才确定context
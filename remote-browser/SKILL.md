---
name: remote-browser
description: Control a Brave/Chrome browser.
---

# Remote Browser Control

首先，你应当看看 `http://localhost:9222/json/version` 通了吗？如果不通， 提示用户先进行如下操作

1. **Start Brave with Remote Debugging**:
   ```powershell
   & "brave.exe" --remote-debugging-port=9222
   ```

作为 Agent，你需要做的操作是：

使用 Accessibility tree 来获取页面元素的信息，并且使用 DevTools Protocol 来控制浏览器。
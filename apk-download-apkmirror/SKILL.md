---
name: apk-download-apkmirror
description: 从 APKMirror 下载并安装 Android APK/APKM：Codex 通过 9222 浏览器导航到正确详情页，人类点击最终下载按钮，Codex 校验下载文件并用 ADB 安装。
---

# APKMirror APK 下载

适用：用户要从 APKMirror 给已连接的 Android 手机安装应用。

规矩：
- 使用 9222 浏览器打开 APKMirror 页面并读取 DOM。(可使用 website-to-cli 技能 的 website-to-cli\scripts\eval-tab-js.py 脚本)
- Codex 只导航到正确 variant/详情页。
- 最终 `DOWNLOAD APK` / `DOWNLOAD APK BUNDLE` 必须由用户点击。
- 下载完成后（用户会告知你），从 `$HOME\Downloads` 找最新文件。

选择：
- 先查手机：`adb shell getprop ro.product.cpu.abilist`、`adb shell getprop ro.build.version.sdk`、`adb shell wm density`。
- 优先选单 APK。
- 若只有 APKM/APK bundle，下载后解包，按设备 ABI/DPI 选择 split，用 `adb install-multiple`。

校验：
- 文件头必须是 `504B0304`。
- APKMirror 页面包名必须与目标一致。
- 安装后检查：`adb shell dumpsys package <package>`。

安装：
- APK：`adb install -r <file.apk>`
- APKM：解包后安装 `base.apk` + ABI split + DPI split。

失败：
- 若安装被 MIUI 拦截，重新执行安装，让用户在手机上点允许/继续/安装。

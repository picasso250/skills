---
name: windows-uac
description: 在 Windows 上处理需要管理员权限的本机配置操作。已知必须提权时，优先直接用 `Start-Process -Verb RunAs` 拉起新的管理员 `pwsh` 执行目标命令；只有在确实需要幂等脚本封装时才做脚本内自提权。适用于修改 hosts、绑定 80/443 端口、导入本地证书、改防火墙规则、停启系统服务或结束高权限进程等系统级动作。
---

# Skill: windows-uac

在 Windows 上，普通进程不能直接“升格”为管理员”。如果你已经确定接下来就是要管理员权限，优先用最直接的方式：

1. 直接用 `Start-Process -FilePath "pwsh.exe" -Verb RunAs` 拉起新的管理员进程
2. 用户在 UAC 弹窗里点允许
3. 在新的管理员进程里直接执行真正的系统级动作

只有当你需要把一串系统级动作封装成幂等脚本，并且需要同一个脚本既能普通运行、又能自动拉起管理员实例时，才使用“脚本内检测权限再自提权”的模式。

## 默认做法

- 优先用 `pwsh`，不要用 `powershell`
- 已知必须提权时，优先直接 `Start-Process -Verb RunAs`
- 需要多步系统改动时，再把真正的动作包进独立脚本
- 只有在需要“一份脚本双模式运行”时，才让脚本自己检测权限并自提权
- 如果动作有副作用，先做存在性检查，尽量做成幂等

## 推荐模式

### 模式 1：已知必须提权，直接 RunAs

适合：

- 停/启系统服务或计划任务
- 杀掉 SYSTEM/管理员权限进程
- 修改防火墙、hosts、证书
- 明确知道当前命令不可能在普通权限下成功

示例：

```powershell
Start-Process -FilePath "pwsh.exe" -Verb RunAs -ArgumentList @(
    "-NoProfile",
    "-Command",
    "Stop-ScheduledTask -TaskName 'FastNTFS' -ErrorAction SilentlyContinue"
)
```

### 模式 2：脚本内自提权

适合：

- 需要发给用户一份可重复执行的脚本
- 想把“检查是否已配置”和“真正写系统状态”封装在一起
- 同一脚本既可能被普通终端调用，也可能被管理员终端调用

## hosts 示例

处理 `hosts` 时，如果需要一份可重复执行的脚本，按这个模式做：

1. 用 `pwsh` 写一个临时或项目内脚本
2. 脚本先弹一个普通说明框，告诉用户接下来会出现 UAC
3. 脚本检查当前是否有管理员权限
4. 没有权限时，用 `Start-Process -FilePath "pwsh.exe" -Verb RunAs` 重新启动自己
5. 在管理员进程中把目标条目写进 `C:\Windows\System32\drivers\etc\hosts`
6. 如果条目已经存在，就不重复写入

最小结构如下：

```powershell
function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Confirm-Elevation {
    Add-Type -AssemblyName System.Windows.Forms
    $message = "接下来会弹出 UAC，用于完成本机系统配置。"
    $result = [System.Windows.Forms.MessageBox]::Show(
        $message,
        "需要管理员权限",
        [System.Windows.Forms.MessageBoxButtons]::OKCancel,
        [System.Windows.Forms.MessageBoxIcon]::Information
    )
    return $result -eq [System.Windows.Forms.DialogResult]::OK
}

if (-not (Test-IsAdministrator)) {
    if (-not (Confirm-Elevation)) {
        exit 1
    }

    Start-Process -FilePath "pwsh.exe" -Verb RunAs -ArgumentList @(
        "-ExecutionPolicy", "Bypass",
        "-File", $MyInvocation.MyCommand.Path
    ) | Out-Null
    exit 0
}
```

拿到管理员权限后，再做具体的 `hosts` 读写。

## 适用边界

- 适合：hosts、证书、端口绑定、防火墙、系统目录写入、计划任务、系统服务、高权限进程管理
- 不适合：普通项目文件编辑、仓库内代码修改

## 注意事项

- `Start-Process -Verb RunAs` 会启动一个新的进程，不是把当前进程原地升级
- UAC 必须由用户确认，不能静默越权
- 已知必须提权时，少一层包装通常更稳，优先直接 RunAs
- 如果动作有副作用，先做存在性检查，再写入

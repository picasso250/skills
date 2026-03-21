param(
    [Parameter(Mandatory=$true, Position=0)]
    $EmailAddress,

    [Parameter(Mandatory=$true, Position=1)]
    $Uid,

    [Parameter(Mandatory=$false, Position=2)]
    [int]$Count = 5
)

$historyDir = "gateway/history"
$outboxDir = "gateway/outbox"
$safeEmail = $EmailAddress -replace "@", "_at_"

# 1. 查找历史消息 (仅限 email)
$searchPattern = "^email_$($safeEmail)_"
$files = fd $searchPattern $historyDir | Sort-Object

if ($null -eq $files -or $files.Count -eq 0) {
    Write-Host "No email messages found for $EmailAddress."
    return
}

# 2. 定位当前 UID 的索引
$currentIndex = -1
for ($i = 0; $i -lt $files.Count; $i++) {
    if ($files[$i] -match "_$Uid(_processed)?\.txt$") {
        $currentIndex = $i
        break
    }
}

# 3. 确定要显示的消息范围（历史 + 当前）
$results = @()
$targetUids = @()

if ($currentIndex -ge 0) {
    $start = [Math]::Max(0, $currentIndex - $Count)
    $selectedFiles = $files[$start..$currentIndex]
    foreach ($f in $selectedFiles) {
        $results += Resolve-Path $f
        if ($f -match "_(\d+)(_processed)?\.txt$") {
            $targetUids += $Matches[1]
        }
    }
} else {
    Write-Host "Current UID $Uid not found in history. Showing latest $Count messages instead:"
    $start = [Math]::Max(0, $files.Count - $Count)
    $latestFiles = $files[$start..($files.Count - 1)]
    foreach ($f in $latestFiles) {
        $results += Resolve-Path $f
        if ($f -match "_(\d+)(_processed)?\.txt$") {
            $targetUids += $Matches[1]
        }
    }
}

# 4. 查找对应的回复 (gateway/outbox)
if ($targetUids.Count -gt 0) {
    $uniqueUids = $targetUids | Select-Object -Unique
    foreach ($tuid in $uniqueUids) {
        $replies = fd "reply-$tuid" $outboxDir -t f
        if ($replies) {
            foreach ($r in $replies) {
                $results += Resolve-Path $r
            }
        }
    }
}

# 5. 输出最终结果
$results | Select-Object -Unique | Sort-Object | ForEach-Object { $_.Path }

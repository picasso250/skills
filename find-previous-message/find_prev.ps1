param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$MessageFile,

    [Parameter(Mandatory=$false, Position=1)]
    [int]$Count = 5
)

$ErrorActionPreference = "Stop"

$historyDir = "gateway/history"
$processingDir = "gateway/processing"
$outboxDir = "gateway/outbox"

function Get-MetadataValue {
    param(
        [string[]]$Lines,
        [string]$Prefix
    )

    $line = $Lines | Where-Object { $_.StartsWith($Prefix) } | Select-Object -First 1
    if ($null -eq $line) {
        return ""
    }
    return $line.Substring($Prefix.Length).Trim()
}

function Get-ReplyPaths {
    param([string[]]$BaseNames)

    $results = @()
    if (!(Test-Path $outboxDir)) {
        return $results
    }

    $files = Get-ChildItem -Path $outboxDir -File
    foreach ($baseName in ($BaseNames | Select-Object -Unique)) {
        $results += $files |
            Where-Object { $_.Name -like "$baseName.reply*.json" } |
            ForEach-Object { $_.FullName }
    }

    return $results
}

function Normalize-MessageBaseName {
    param([string]$BaseName)

    if ($BaseName.EndsWith("_processed")) {
        return $BaseName.Substring(0, $BaseName.Length - "_processed".Length)
    }
    return $BaseName
}

if (!(Test-Path $MessageFile)) {
    throw "Message file not found: $MessageFile"
}

$resolvedMessageFile = (Resolve-Path $MessageFile).Path
$messageName = [System.IO.Path]::GetFileName($resolvedMessageFile)
$messageBaseName = [System.IO.Path]::GetFileNameWithoutExtension($resolvedMessageFile)
$messageLines = Get-Content $resolvedMessageFile

$source = ""
if ($messageName -like "email_*") {
    $source = "email"
} elseif ($messageName -like "feishu_*") {
    $source = "feishu"
} else {
    throw "Unsupported message file name: $messageName"
}

$candidates = @()
if (Test-Path $historyDir) {
    $candidates += Get-ChildItem -Path $historyDir -File | ForEach-Object { $_.FullName }
}
if (Test-Path $processingDir) {
    $candidates += Get-ChildItem -Path $processingDir -File | ForEach-Object { $_.FullName }
}
$candidates = $candidates | Select-Object -Unique

$matching = @()

if ($source -eq "email") {
    $fromLine = Get-MetadataValue -Lines $messageLines -Prefix "From: "
    if ($fromLine -match "<([^>]+)>") {
        $fromEmail = $Matches[1]
        $safeEmail = $fromEmail -replace "@", "_at_"
        $matching = $candidates |
            Where-Object { [System.IO.Path]::GetFileName($_) -like "email_$safeEmail*" } |
            Sort-Object
    }
} elseif ($source -eq "feishu") {
    $conversationId = Get-MetadataValue -Lines $messageLines -Prefix "Conversation: "
    foreach ($candidate in $candidates) {
        $candidateName = [System.IO.Path]::GetFileName($candidate)
        if ($candidateName -notlike "feishu_*") {
            continue
        }

        $lines = Get-Content $candidate
        $candidateConversationId = Get-MetadataValue -Lines $lines -Prefix "Conversation: "
        if ($candidateConversationId -eq $conversationId) {
            $matching += $candidate
        }
    }
    $matching = $matching | Sort-Object
}

if ($null -eq $matching -or $matching.Count -eq 0) {
    Write-Host "No matching history found for $resolvedMessageFile"
    return
}

$currentIndex = [Array]::IndexOf($matching, $resolvedMessageFile)
if ($currentIndex -lt 0) {
    $currentIndex = [Array]::IndexOf(($matching | ForEach-Object { [System.IO.Path]::GetFileName($_) }), $messageName)
}

if ($currentIndex -lt 0) {
    $currentIndex = $matching.Count - 1
}

$start = [Math]::Max(0, $currentIndex - $Count)
$selected = @($matching[$start..$currentIndex])

$baseNames = $selected | ForEach-Object { Normalize-MessageBaseName ([System.IO.Path]::GetFileNameWithoutExtension($_)) }
$results = @($selected + (Get-ReplyPaths -BaseNames $baseNames))

$results |
    Select-Object -Unique |
    Sort-Object |
    ForEach-Object { (Resolve-Path $_).Path }

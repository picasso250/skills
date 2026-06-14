param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[^@\s]+@[^@\s]+\.[^@\s]+$')]
  [string]$Email,

  [string]$AccountId = '7cd361e713a3e8c115f613ec88a5707f',
  [string]$PolicyId = 'eb22d018-3632-46f9-a932-5adcfa8a513b',
  [string]$CfConfigPath = "$HOME\.cf\config.toml"
)

$ErrorActionPreference = 'Stop'

function Get-CfAccessToken {
  param([string]$Path)

  if (-not [System.IO.File]::Exists($Path)) {
    throw "Cloudflare cf config not found: $Path"
  }

  $config = [System.IO.File]::ReadAllText($Path)
  $match = [regex]::Match($config, 'access_token\s*=\s*"([^"]+)"')
  if (-not $match.Success) {
    $match = [regex]::Match($config, 'oauth_token\s*=\s*"([^"]+)"')
  }
  if (-not $match.Success) {
    throw "No access_token or oauth_token found in $Path. Run: cf auth login"
  }

  return $match.Groups[1].Value
}

$token = Get-CfAccessToken -Path $CfConfigPath
$headers = @{
  Authorization = "Bearer $token"
  'Content-Type' = 'application/json'
}
$uri = "https://api.cloudflare.com/client/v4/accounts/$AccountId/access/policies/$PolicyId"

$policyResponse = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
$policy = $policyResponse.result

$emails = @($policy.include | ForEach-Object {
  if ($_.email -and $_.email.email) { $_.email.email }
})

if ($emails -contains $Email) {
  Write-Host "already_present=$Email"
  Write-Host "emails:"
  $emails
  exit 0
}

$include = @($policy.include)
$include += @{ email = @{ email = $Email } }

$body = [ordered]@{
  name = $policy.name
  decision = $policy.decision
  include = $include
  exclude = @($policy.exclude)
  require = @($policy.require)
}

foreach ($field in @(
  'session_duration',
  'approval_required',
  'isolation_required',
  'purpose_justification_required'
)) {
  if ($null -ne $policy.$field) {
    $body[$field] = $policy.$field
  }
}

$json = $body | ConvertTo-Json -Depth 20
$updated = Invoke-RestMethod -Method Put -Uri $uri -Headers $headers -Body $json

Write-Host "updated_success=$($updated.success)"
Write-Host "policy=$($updated.result.name)"
Write-Host "emails:"
@($updated.result.include | ForEach-Object {
  if ($_.email -and $_.email.email) { $_.email.email }
})

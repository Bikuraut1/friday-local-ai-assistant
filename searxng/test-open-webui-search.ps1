$ErrorActionPreference = 'Stop'

$OpenWebUiEnv = 'D:\Friday\n8n\.env'
if (Test-Path $OpenWebUiEnv) {
  Get-Content $OpenWebUiEnv | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)\s*$') {
      [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
  }
}

$OpenWebUiEmail = $env:FRIDAY_OPENWEBUI_EMAIL
$OpenWebUiPassword = $env:FRIDAY_OPENWEBUI_PASSWORD
if (-not $OpenWebUiEmail -or -not $OpenWebUiPassword) {
  throw 'Set FRIDAY_OPENWEBUI_EMAIL and FRIDAY_OPENWEBUI_PASSWORD in D:\Friday\n8n\.env.'
}

$SigninBody = @{
  email = $OpenWebUiEmail
  password = $OpenWebUiPassword
} | ConvertTo-Json

$Session = Invoke-RestMethod `
  -Uri 'http://localhost:3000/api/v1/auths/signin' `
  -Method Post `
  -Body $SigninBody `
  -ContentType 'application/json' `
  -TimeoutSec 30

$Headers = @{
  Authorization = "Bearer $($Session.token)"
}

$SearchBody = @{
  queries = @('today top news India June 27 2026')
} | ConvertTo-Json -Depth 4

$Result = Invoke-RestMethod `
  -Uri 'http://localhost:3000/api/v1/retrieval/process/web/search' `
  -Method Post `
  -Headers $Headers `
  -Body $SearchBody `
  -ContentType 'application/json' `
  -TimeoutSec 120

[ordered]@{
  status = $Result.status
  loaded_count = $Result.loaded_count
  collection_names = $Result.collection_names
  filenames = @($Result.filenames | Select-Object -First 5)
  item_titles = @($Result.items | Select-Object -First 5 | ForEach-Object { $_.title })
} | ConvertTo-Json -Depth 8

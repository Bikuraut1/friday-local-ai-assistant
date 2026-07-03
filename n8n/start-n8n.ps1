$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$N8nRoot = Join-Path $Root 'n8n'
$ComposeFile = Join-Path $N8nRoot 'docker-compose.yml'

function Test-HttpOk {
  param([string]$Uri, [int]$TimeoutSec = 5)
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec $TimeoutSec
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
  } catch {
    return $false
  }
}

New-Item -ItemType Directory -Force -Path `
  (Join-Path $N8nRoot 'data'), `
  (Join-Path $N8nRoot 'workflows'), `
  (Join-Path $N8nRoot 'scripts'), `
  (Join-Path $N8nRoot 'output'), `
  (Join-Path $N8nRoot 'logs') | Out-Null

Set-Location $N8nRoot
docker compose -f $ComposeFile up -d
if ($LASTEXITCODE -ne 0) {
  throw 'n8n failed to start.'
}

$deadline = (Get-Date).AddSeconds(180)
do {
  if (Test-HttpOk -Uri 'http://localhost:5678/healthz' -TimeoutSec 5) {
    Write-Host 'FRIDAY n8n online.'
    Write-Host 'n8n: http://localhost:5678'
    exit 0
  }
  if (Test-HttpOk -Uri 'http://localhost:5678' -TimeoutSec 5) {
    Write-Host 'FRIDAY n8n online.'
    Write-Host 'n8n: http://localhost:5678'
    exit 0
  }
  Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

docker logs --tail 120 friday-n8n
throw 'n8n did not become ready.'

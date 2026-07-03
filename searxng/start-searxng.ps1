$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$SearxngRoot = Join-Path $Root 'searxng'
$Compose = Join-Path $SearxngRoot 'docker-compose.yml'

New-Item -ItemType Directory -Force -Path (Join-Path $SearxngRoot 'data') | Out-Null

docker compose -f $Compose up -d
if ($LASTEXITCODE -ne 0) {
  throw 'Failed to start SearXNG.'
}

$deadline = (Get-Date).AddSeconds(120)
do {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8081/search?q=friday&format=json' -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
      Write-Host 'FRIDAY SearXNG online: http://localhost:8081'
      exit 0
    }
  } catch {}
  Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

docker logs --tail 120 friday-searxng
throw 'SearXNG did not become healthy.'

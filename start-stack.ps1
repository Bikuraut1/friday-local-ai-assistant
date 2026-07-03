$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'

$ComposeFiles = @(
  'mem0\docker-compose.yml'
  'searxng\docker-compose.yml'
  'voice\kokoro\docker-compose.yml'
  'open-webui\docker-compose.yml'
  'n8n\docker-compose.yml'
)

foreach ($file in $ComposeFiles) {
  $path = Join-Path $Root $file
  Write-Host "Starting $file"
  docker compose -f $path up -d
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to start $file"
  }
}

Write-Host 'FRIDAY Docker layer started.'

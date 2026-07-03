$ErrorActionPreference = 'Stop'
docker compose -f 'D:\Friday\n8n\docker-compose.yml' stop
if ($LASTEXITCODE -ne 0) {
  throw 'Failed to stop n8n.'
}
Write-Host 'FRIDAY n8n stopped.'

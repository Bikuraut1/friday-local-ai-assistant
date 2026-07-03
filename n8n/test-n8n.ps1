$ErrorActionPreference = 'Stop'

Write-Host '1. n8n container'
docker ps --filter 'name=friday-n8n' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

Write-Host '2. n8n health'
try {
  Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:5678/healthz' -TimeoutSec 10 | Select-Object StatusCode,Content
} catch {
  Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:5678' -TimeoutSec 10 | Select-Object StatusCode
}

Write-Host '3. automation service status'
Invoke-RestMethod -Uri 'http://localhost:8788/run/status' -Method Post -TimeoutSec 60 | ConvertTo-Json -Depth 8

Write-Host '4. manual Monday briefing trigger'
Invoke-RestMethod -Uri 'http://localhost:5678/webhook/friday/monday-briefing' -Method Post -TimeoutSec 240 | ConvertTo-Json -Depth 10

Write-Host 'Phase 8 n8n verification passed.'

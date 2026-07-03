$ErrorActionPreference = 'Stop'

Set-Location 'D:\Friday'
.\dashboard\start-dashboard.ps1

Write-Host '1. Health'
Invoke-RestMethod -Uri 'http://localhost:8888/health' -TimeoutSec 10 | ConvertTo-Json -Depth 4

Write-Host '2. Status payload'
$status = Invoke-RestMethod -Uri 'http://localhost:8888/api/status' -TimeoutSec 30
$status | ConvertTo-Json -Depth 8

if (-not $status.services.ollama.ok) {
  throw 'Dashboard cannot reach Ollama.'
}
if (-not $status.services.router.ok) {
  throw 'Dashboard cannot reach router.'
}
if ($null -eq $status.memory.count) {
  throw 'Dashboard memory count missing.'
}

Write-Host '3. Action endpoint'
Invoke-RestMethod -Uri 'http://localhost:8888/api/action' -Method Post -ContentType 'application/json' -Body (@{ action='router_health' } | ConvertTo-Json) -TimeoutSec 30 | ConvertTo-Json -Depth 8

Write-Host 'Phase 11 dashboard verification passed.'

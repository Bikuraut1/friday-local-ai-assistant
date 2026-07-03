$ErrorActionPreference = 'Stop'

$fact = 'Boss prefers FRIDAY to give concise, direct answers with exact commands.'

Write-Host 'Storing test memory...'
Invoke-RestMethod -Uri 'http://localhost:8765/memory' `
  -Method Post `
  -ContentType 'application/json' `
  -Body (@{
    text = $fact
    category = 'PREFERENCES'
    source = 'phase3-test-session-1'
    infer = $false
  } | ConvertTo-Json)

Start-Sleep -Seconds 2

Write-Host 'Recalling test memory...'
$result = Invoke-RestMethod -Uri 'http://localhost:8765/memory/search' `
  -Method Post `
  -ContentType 'application/json' `
  -Body (@{
    query = 'How does Boss prefer FRIDAY to answer?'
    category = 'PREFERENCES'
    top_k = 5
  } | ConvertTo-Json)

$result | ConvertTo-Json -Depth 8

$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$Python = Join-Path $Root 'voice\.venv\Scripts\python.exe'
$Script = Join-Path $Root 'router\model_router.py'

Write-Host '1. Verify required models'
$required = @(
  'friday:phi4',
  'llama3.1:70b-instruct-q4_K_M',
  'llava:13b',
  'qwen2.5:0.5b-instruct'
)
$models = (Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 10).models.name
foreach ($model in $required) {
  if ($models -notcontains $model) {
    throw "Missing model: $model"
  }
  Write-Host "OK $model"
}

Write-Host '2. Start router'
& (Join-Path $Root 'router\start-router.ps1')

Write-Host '3. Verify routes'
$tests = @(
  @{ name='simple'; prompt='Who are you?'; expectedRoute='simple_chat'; expectedModel='friday:phi4' },
  @{ name='complex'; prompt='Design a multi-step architecture strategy for a local assistant that balances memory, RAG, voice, and automation tradeoffs.'; expectedRoute='complex_reasoning'; expectedModel='llama3.1:70b-instruct-q4_K_M' },
  @{ name='code'; prompt='Debug this Python traceback and write the corrected function.'; expectedRoute='code'; expectedModel='friday:phi4' },
  @{ name='image'; prompt='Analyze this screenshot and tell me what is visible.'; expectedRoute='image'; expectedModel='llava:13b' },
  @{ name='math'; prompt='Calculate 27 * 38 + 14'; expectedRoute='quick_math'; expectedModel='friday:phi4' }
)

foreach ($test in $tests) {
  $body = @{ prompt = $test.prompt } | ConvertTo-Json
  $result = Invoke-RestMethod -Uri 'http://localhost:8790/route' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 90
  $route = $result.decision.route
  $model = $result.decision.model
  Write-Host "$($test.name): route=$route model=$model"
  if ($route -ne $test.expectedRoute) {
    throw "Route mismatch for $($test.name): expected $($test.expectedRoute), got $route"
  }
  if ($model -ne $test.expectedModel) {
    throw "Model mismatch for $($test.name): expected $($test.expectedModel), got $model"
  }
}

Write-Host '4. Verify a real quick chat response'
$chatBody = @{ prompt = 'Reply with exactly: router ready'; num_predict = 20 } | ConvertTo-Json
$chat = Invoke-RestMethod -Uri 'http://localhost:8790/chat' -Method Post -ContentType 'application/json' -Body $chatBody -TimeoutSec 120
if (-not $chat.response) {
  throw 'Router chat did not return a response.'
}
$chat | ConvertTo-Json -Depth 8

Write-Host '5. Verify routing log'
$log = Join-Path $Root 'router\logs\routing-decisions.jsonl'
if (-not (Test-Path $log)) {
  throw 'Routing log was not created.'
}
Get-Content $log -Tail 8

Write-Host 'Phase 10 router verification passed.'

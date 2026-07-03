$ErrorActionPreference = 'Continue'

$Root = 'D:\Friday'
$env:OLLAMA_MODELS = Join-Path $Root 'ollama\models'

function Get-HttpStatus {
  param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [int]$TimeoutSec = 5
  )

  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec $TimeoutSec
    return "$($response.StatusCode) $($response.Content)"
  } catch {
    return "ERROR $($_.Exception.Message)"
  }
}

Write-Host '== Docker containers =='
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

Write-Host ''
Write-Host '== Open WebUI =='
docker inspect friday-open-webui --format 'Status={{.State.Status}} Health={{if .State.Health}}{{.State.Health.Status}}{{end}} Started={{.State.StartedAt}}' 2>$null
Write-Host "Health endpoint: $(Get-HttpStatus -Uri 'http://localhost:3000/health')"

Write-Host ''
Write-Host '== Ollama =='
Write-Host "Tags endpoint: $(Get-HttpStatus -Uri 'http://localhost:11434/api/tags')"
ollama list

Write-Host ''
Write-Host '== Embeddings =='
$body = @{ model = 'nomic-embed-text'; input = 'FRIDAY status check' } | ConvertTo-Json
try {
  $result = Invoke-RestMethod -Uri 'http://localhost:11434/api/embed' -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 30
  Write-Host "nomic-embed-text: OK embeddings=$($result.embeddings.Count) dims=$($result.embeddings[0].Count)"
} catch {
  Write-Host "nomic-embed-text: ERROR $($_.Exception.Message)"
}

Write-Host ''
Write-Host '== Long-Term Memory =='
docker ps --filter 'name=friday-qdrant' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
Write-Host "Memory bridge: $(Get-HttpStatus -Uri 'http://localhost:8765/health' -TimeoutSec 15)"

Write-Host ''
Write-Host '== RAG =='
Write-Host "Reranker: $(Get-HttpStatus -Uri 'http://localhost:8770/health')"
try {
  $collections = Invoke-RestMethod -Uri 'http://localhost:6333/collections' -TimeoutSec 5
  $names = ($collections.result.collections | ForEach-Object { $_.name }) -join ', '
  Write-Host "Qdrant collections: $names"
} catch {
  Write-Host "Qdrant collections: ERROR $($_.Exception.Message)"
}

Write-Host ''
Write-Host '== Live Web Search =='
docker ps --filter 'name=friday-searxng' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
try {
  $search = Invoke-RestMethod -Uri 'http://localhost:8081/search?q=friday&format=json&language=en' -TimeoutSec 15
  Write-Host "SearXNG: OK results=$($search.results.Count)"
} catch {
  Write-Host "SearXNG: ERROR $($_.Exception.Message)"
}

Write-Host ''
Write-Host '== Voice =='
docker ps --filter 'name=friday-kokoro' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
try {
  $ttsModel = if ($env:FRIDAY_TTS_MODEL) { $env:FRIDAY_TTS_MODEL } else { 'kokoro' }
  $ttsVoice = if ($env:FRIDAY_TTS_VOICE) { $env:FRIDAY_TTS_VOICE } else { 'af_bella' }
  $ttsFallbackVoice = if ($env:FRIDAY_TTS_FALLBACK_VOICE) { $env:FRIDAY_TTS_FALLBACK_VOICE } else { 'bf_emma' }
  $allowNonEnglishTts = ($env:FRIDAY_ALLOW_NON_ENGLISH_TTS -match '^(1|true|yes)$')
  $selectedTtsVoice = $null
  foreach ($voice in (@($ttsVoice, $ttsFallbackVoice, 'af_bella') | Select-Object -Unique)) {
    if (-not $allowNonEnglishTts -and $voice -notmatch '^[ab][fm]_') {
      Write-Host "Skipping non-English TTS voice for English speech: $voice"
      continue
    }
    try {
      $body = @{ model = $ttsModel; voice = $voice; input = 'FRIDAY voice status check in Indian English.'; response_format = 'mp3' } | ConvertTo-Json
      $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8880/v1/audio/speech' -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 30
      $selectedTtsVoice = $voice
      break
    } catch {}
  }
  if (-not $selectedTtsVoice) {
    throw 'No configured Kokoro TTS voice worked.'
  }
  Write-Host "Kokoro TTS: OK voice=$selectedTtsVoice bytes=$($response.RawContentLength)"
} catch {
  Write-Host "Kokoro TTS: ERROR $($_.Exception.Message)"
}
docker exec friday-open-webui env 2>$null |
  Select-String -Pattern 'WHISPER|AUDIO_STT|AUDIO_TTS' |
  ForEach-Object { $_.Line -replace '^(AUDIO_TTS_OPENAI_API_KEY=).+$', '$1<redacted>' }

Write-Host ''
Write-Host '== Automation =='
docker ps --filter 'name=friday-n8n' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
Write-Host "n8n health: $(Get-HttpStatus -Uri 'http://localhost:5678/healthz')"
Write-Host "Automation API: $(Get-HttpStatus -Uri 'http://localhost:8788/health')"
try {
  Invoke-RestMethod -Uri 'http://localhost:8788/run/status' -Method Post -TimeoutSec 60 | ConvertTo-Json -Depth 8
} catch {
  Write-Host "n8n automation status: ERROR $($_.Exception.Message)"
}

Write-Host ''
Write-Host '== Vision =='
$visionProcesses = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'python' -and $_.CommandLine -like '*analyze_screen.py*--hotkey*'
}
if ($visionProcesses) {
  $visionProcesses | Select-Object ProcessId,Name,CommandLine | Format-Table
} else {
  Write-Host 'Vision hotkey: not running'
}
if (Test-Path 'D:\Friday\vision\logs\latest-analysis.json') {
  Get-Item 'D:\Friday\vision\logs\latest-analysis.json' | Select-Object FullName,Length,LastWriteTime | Format-Table
}

Write-Host ''
Write-Host '== Model Router =='
Write-Host "Router health: $(Get-HttpStatus -Uri 'http://localhost:8790/health')"
if (Test-Path 'D:\Friday\router\logs\routing-decisions.jsonl') {
  Write-Host 'Recent routing decisions:'
  Get-Content 'D:\Friday\router\logs\routing-decisions.jsonl' -Tail 5
}

Write-Host ''
Write-Host '== Dashboard =='
Write-Host "Dashboard health: $(Get-HttpStatus -Uri 'http://localhost:8888/health')"

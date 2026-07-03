param(
  [string]$BackupRoot = 'D:\Friday\backups',
  [switch]$IncludeVoiceRecordings,
  [switch]$IncludeVectorStores,
  [switch]$IncludeOllamaModels
)

$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stage = Join-Path $BackupRoot "stage-$stamp"
$archive = Join-Path $BackupRoot "friday-backup-$stamp.zip"

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
New-Item -ItemType Directory -Force -Path $stage | Out-Null

function Copy-IfExists {
  param(
    [Parameter(Mandatory = $true)][string]$RelativePath,
    [switch]$Directory
  )

  $source = Join-Path $Root $RelativePath
  $dest = Join-Path $stage $RelativePath
  if (-not (Test-Path $source)) {
    return
  }

  New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
  if ($Directory) {
    robocopy $source $dest /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
      throw "Robocopy failed for $RelativePath with exit code $LASTEXITCODE"
    }
  } else {
    Copy-Item -LiteralPath $source -Destination $dest -Force
  }
}

$manifest = [ordered]@{
  created_at = (Get-Date).ToString('s')
  root = $Root
  notes = @(
    'Critical FRIDAY local state backup.',
    'Ollama model blobs are excluded unless -IncludeOllamaModels is passed.',
    'Voice recordings are excluded unless -IncludeVoiceRecordings is passed.',
    'Large Qdrant vector stores are excluded unless -IncludeVectorStores is passed.'
  )
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -Path (Join-Path $stage 'manifest.json')

Copy-IfExists 'start-friday.ps1'
Copy-IfExists 'status-friday.ps1'
Copy-IfExists 'stop-friday.ps1'
Copy-IfExists 'open-webui\data\webui.db'
Copy-IfExists 'open-webui\data\webui.db-shm'
Copy-IfExists 'open-webui\data\webui.db-wal'
Copy-IfExists 'open-webui\data\uploads' -Directory
Copy-IfExists 'knowledge-base' -Directory
Copy-IfExists 'mem0\history.db'
Copy-IfExists 'mem0\bridge\memory_bridge.py'
Copy-IfExists 'mem0\open-webui-tool-friday-memory.py'
Copy-IfExists 'rag\reranker.py'
Copy-IfExists 'rag\README.md'
Copy-IfExists 'rag\start-rag.ps1'
Copy-IfExists 'rag\stop-reranker.ps1'
Copy-IfExists 'rag\test-rag.ps1'
Copy-IfExists 'router\model_router.py'
Copy-IfExists 'router\README.md'
Copy-IfExists 'router\start-router.ps1'
Copy-IfExists 'router\stop-router.ps1'
Copy-IfExists 'router\test-router.ps1'
Copy-IfExists 'router\logs\routing-decisions.jsonl'
Copy-IfExists 'voice\wake_listener.py'
Copy-IfExists 'voice\README.md'
Copy-IfExists 'voice\start-voice.ps1'
Copy-IfExists 'voice\stop-voice.ps1'
Copy-IfExists 'voice\wakewords' -Directory
Copy-IfExists 'vision\analyze_screen.py'
Copy-IfExists 'vision\README.md'
Copy-IfExists 'vision\start-vision-hotkey.ps1'
Copy-IfExists 'vision\stop-vision-hotkey.ps1'
Copy-IfExists 'vision\test-vision.ps1'
Copy-IfExists 'vision\logs\latest-analysis.json'
Copy-IfExists 'n8n\data\database.sqlite'
Copy-IfExists 'n8n\data\database.sqlite-shm'
Copy-IfExists 'n8n\data\database.sqlite-wal'
Copy-IfExists 'n8n\workflows' -Directory
Copy-IfExists 'n8n\scripts' -Directory
Copy-IfExists 'n8n\output' -Directory
Copy-IfExists 'dashboard\dashboard_server.py'
Copy-IfExists 'dashboard\README.md'
Copy-IfExists 'dashboard\start-dashboard.ps1'
Copy-IfExists 'dashboard\stop-dashboard.ps1'
Copy-IfExists 'dashboard\test-dashboard.ps1'
Copy-IfExists 'dashboard\static' -Directory
Copy-IfExists 'agent\FRIDAY_AGENT_SYSTEM_PROMPT.md'
Copy-IfExists 'agent\README.md'
Copy-IfExists 'agent\start-interpreter.ps1'
Copy-IfExists 'agent\test-phase7.ps1'
Copy-IfExists 'agent\tools' -Directory
Copy-IfExists 'searxng\settings.yml'
Copy-IfExists 'searxng\README.md'
Copy-IfExists 'searxng\start-searxng.ps1'
Copy-IfExists 'searxng\test-searxng.ps1'
Copy-IfExists 'open-webui\docker-compose.yml'
Copy-IfExists 'mem0\docker-compose.yml'
Copy-IfExists 'searxng\docker-compose.yml'
Copy-IfExists 'voice\kokoro\docker-compose.yml'
Copy-IfExists 'n8n\docker-compose.yml'
Copy-IfExists 'maintenance' -Directory

if ($IncludeVoiceRecordings) {
  Copy-IfExists 'voice\recordings' -Directory
}

if ($IncludeVectorStores) {
  Copy-IfExists 'mem0\qdrant\storage\collections' -Directory
  Copy-IfExists 'open-webui\data\vector_db' -Directory
}

if ($IncludeOllamaModels) {
  Copy-IfExists 'ollama\models' -Directory
}

if (Test-Path $archive) {
  Remove-Item -LiteralPath $archive -Force
}

Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $archive -Force
Remove-Item -LiteralPath $stage -Recurse -Force

Write-Host "Backup created: $archive"
Write-Host "Size MB: $([Math]::Round((Get-Item $archive).Length / 1MB, 2))"

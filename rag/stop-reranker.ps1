$ErrorActionPreference = 'Continue'

$PidFile = 'D:\Friday\rag\reranker.pid'

if (Test-Path $PidFile) {
  $pidValue = Get-Content $PidFile | Select-Object -First 1
  if ($pidValue) {
    Stop-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
  }
  Remove-Item $PidFile -ErrorAction SilentlyContinue
}

Write-Host 'FRIDAY RAG reranker stopped.'

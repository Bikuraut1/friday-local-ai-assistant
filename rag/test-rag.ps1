$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$TestFile = Join-Path $Root 'knowledge-base\inbox\friday-phase4-test.md'
$RagEnv = Join-Path $Root 'rag\.env'

$RerankerApiKey = 'change-me-local-dev'
if (Test-Path $RagEnv) {
  Get-Content -LiteralPath $RagEnv | ForEach-Object {
    if ($_ -match '^\s*FRIDAY_RERANKER_API_KEY=(.+)\s*$') {
      $RerankerApiKey = $Matches[1].Trim()
    }
  }
}

@'
# FRIDAY Phase 4 Test Document

The project codename is VIGIL LANTERN.

FRIDAY should answer personal knowledge base questions using local RAG backed by Qdrant.

The required verification phrase is: amber vector memory.
'@ | Set-Content -Path $TestFile -Encoding UTF8

Write-Host "Created test document: $TestFile"

Write-Host 'Qdrant collections:'
Invoke-RestMethod -Uri 'http://localhost:6333/collections' -Method Get | ConvertTo-Json -Depth 8

Write-Host 'Reranker smoke test:'
Invoke-RestMethod -Uri 'http://localhost:8770/v1/rerank' `
  -Method Post `
  -ContentType 'application/json' `
  -Headers @{ Authorization = "Bearer $RerankerApiKey" } `
  -Body (@{
    model = 'friday-local-reranker'
    query = 'verification phrase'
    documents = @(
      'unrelated text',
      'The required verification phrase is amber vector memory.'
    )
    top_n = 2
  } | ConvertTo-Json) | ConvertTo-Json -Depth 8

Write-Host ''
Write-Host 'Manual Open WebUI verification:'
Write-Host '1. Open http://localhost:3000'
Write-Host '2. Go to Knowledge or upload files.'
Write-Host "3. Upload: $TestFile"
Write-Host '4. Ask: What is the project codename and required verification phrase?'
Write-Host 'Expected answer includes: VIGIL LANTERN and amber vector memory.'

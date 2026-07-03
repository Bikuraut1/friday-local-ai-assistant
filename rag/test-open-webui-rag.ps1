$ErrorActionPreference = 'Stop'

$Base = 'http://localhost:3000'
$TestFile = 'D:\Friday\knowledge-base\inbox\friday-phase4-test.md'
$OpenWebUiEnv = 'D:\Friday\n8n\.env'

Add-Type -AssemblyName System.Net.Http

if (Test-Path $OpenWebUiEnv) {
  Get-Content $OpenWebUiEnv | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)\s*$') {
      [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
  }
}

$OpenWebUiEmail = $env:FRIDAY_OPENWEBUI_EMAIL
$OpenWebUiPassword = $env:FRIDAY_OPENWEBUI_PASSWORD
if (-not $OpenWebUiEmail -or -not $OpenWebUiPassword) {
  throw 'Set FRIDAY_OPENWEBUI_EMAIL and FRIDAY_OPENWEBUI_PASSWORD in D:\Friday\n8n\.env.'
}

if (-not (Test-Path $TestFile)) {
  powershell -ExecutionPolicy Bypass -File 'D:\Friday\rag\test-rag.ps1' | Out-Host
}

$signin = Invoke-RestMethod -Uri "$Base/api/v1/auths/signin" `
  -Method Post `
  -ContentType 'application/json' `
  -Body (@{ email = $OpenWebUiEmail; password = $OpenWebUiPassword } | ConvertTo-Json)

$token = $signin.token
if (-not $token) {
  throw 'Open WebUI signin did not return a token.'
}

$headers = @{ Authorization = "Bearer $token" }

Write-Host 'Uploading and processing RAG test document...'
$client = [System.Net.Http.HttpClient]::new()
$client.DefaultRequestHeaders.Authorization = [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $token)
$multipart = [System.Net.Http.MultipartFormDataContent]::new()
$stream = [System.IO.File]::OpenRead($TestFile)
$fileContent = [System.Net.Http.StreamContent]::new($stream)
$fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('text/markdown')
$multipart.Add($fileContent, 'file', [System.IO.Path]::GetFileName($TestFile))

try {
  $uploadResponse = $client.PostAsync("$Base/api/v1/files/?process=true&process_in_background=false", $multipart).Result
  $uploadText = $uploadResponse.Content.ReadAsStringAsync().Result
  if (-not $uploadResponse.IsSuccessStatusCode) {
    throw "Upload failed: HTTP $([int]$uploadResponse.StatusCode) $uploadText"
  }
  $uploaded = $uploadText | ConvertFrom-Json
} finally {
  $stream.Dispose()
  $multipart.Dispose()
  $client.Dispose()
}

$fileId = $uploaded.id
if (-not $fileId) {
  throw 'Upload did not return a file id.'
}

$collectionName = "file-$fileId"
Write-Host "Uploaded file id: $fileId"
Write-Host "Querying collection: $collectionName"

$query = Invoke-RestMethod -Uri "$Base/api/v1/retrieval/query/collection" `
  -Method Post `
  -Headers $headers `
  -ContentType 'application/json' `
  -Body (@{
    collection_names = @($collectionName)
    query = 'What is the project codename and required verification phrase?'
    k = 5
    k_reranker = 8
    hybrid = $true
    hybrid_bm25_weight = 0.45
    enable_enriched_texts = $true
  } | ConvertTo-Json)

$json = $query | ConvertTo-Json -Depth 12
$json

if ($json -notmatch 'VIGIL LANTERN' -or $json -notmatch 'amber vector memory') {
  throw 'RAG query did not return the expected test facts.'
}

Write-Host 'Open WebUI RAG verification passed.'

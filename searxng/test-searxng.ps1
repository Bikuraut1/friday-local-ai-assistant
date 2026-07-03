$ErrorActionPreference = 'Stop'

$query = 'today news'
$uri = 'http://localhost:8081/search?q=' + [uri]::EscapeDataString($query) + '&format=json&language=en'

$result = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 30

if (-not $result.results -or $result.results.Count -eq 0) {
  throw 'SearXNG returned no results.'
}

$result.results |
  Select-Object -First 5 title,url,engine,content |
  ConvertTo-Json -Depth 5

# FRIDAY Phase 5 - Live Web Search

Local SearXNG endpoint:

- `http://localhost:8081`

Open WebUI search endpoint configuration:

- `WEB_SEARCH_ENGINE=searxng`
- `SEARXNG_QUERY_URL=http://host.docker.internal:8081/search?q=<query>&format=json`

Commands:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Friday\searxng\start-searxng.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\searxng\test-searxng.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\searxng\test-open-webui-search.ps1
```

Configured engines:

- Google
- Bing
- DuckDuckGo

Open WebUI integration test expectation:

- `status=true`
- `loaded_count` greater than `0`
- at least one returned news URL/title
- one `web-search-*` collection created in Qdrant

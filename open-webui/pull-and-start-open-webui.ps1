$env:PATH='C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
Set-Location 'D:\Friday'
docker compose -f 'D:\Friday\open-webui\docker-compose.yml' pull *> 'D:\Friday\logs\open-webui-pull.log'
if ($LASTEXITCODE -eq 0) {
  docker compose -f 'D:\Friday\open-webui\docker-compose.yml' up -d *> 'D:\Friday\logs\open-webui-up.log'
}
exit $LASTEXITCODE

$env:PATH='C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
Set-Location 'D:\Friday'
docker pull ghcr.io/open-webui/open-webui:main-slim *> 'D:\Friday\logs\open-webui-image-pull.log'
exit $LASTEXITCODE

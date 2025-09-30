$ErrorActionPreference='Stop'
Get-Job -Name 'PA-LAN','PA-FETCHER','PA-EMAIL' -ErrorAction SilentlyContinue | Stop-Job -PassThru | Remove-Job
Write-Host "Stopped PA jobs (LAN/FETCHER/EMAIL)."

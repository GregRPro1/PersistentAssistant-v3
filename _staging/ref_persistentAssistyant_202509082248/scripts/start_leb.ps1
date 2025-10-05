param([switch]$NoWindow)
$env:PYTHONUNBUFFERED="1"
$log = "logs\leb_service.out.txt"
"Starting LEB..." | Out-File -FilePath $log -Encoding utf8
if ($NoWindow) {
  Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "tools\leb_service.py" -WindowStyle Hidden
} else {
  Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "tools\leb_service.py"
}
"LEB start invoked." | Add-Content $log

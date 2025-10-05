Get-Process | Where-Object { $_.Path -like "*\python.exe" -and $_.MainWindowTitle -like "*leb_service.py*" } | Stop-Process -Force -ErrorAction SilentlyContinue
# Fallback: kill by port would require extra tooling; skip for now.
"LEB stop attempted." | Add-Content "logs\leb_service.out.txt"

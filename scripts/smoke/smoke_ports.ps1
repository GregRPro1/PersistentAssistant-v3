$ErrorActionPreference="Stop"
$ok6060 = (Test-NetConnection 127.0.0.1 -Port 6060).TcpTestSucceeded
$ok5070 = (Test-NetConnection 127.0.0.1 -Port 5070).TcpTestSucceeded
"6060: $ok6060; 5070: $ok5070"

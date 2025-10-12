Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Read-Json($p){ try { Get-Content -Raw $p -ErrorAction Stop | ConvertFrom-Json } catch { $null } }
function To-Hashtable([object]$obj){ if ($null -eq $obj) { return @{} } if ($obj -is [hashtable]) { return $obj } $ht = @{}; foreach ($p in $obj.PSObject.Properties){ $val = $p.Value; if ($val -is [System.Management.Automation.PSCustomObject]) { $val = To-Hashtable $val }; $ht[$p.Name] = $val }; return $ht }
function Get-LanIp { try { $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notmatch '^169\.' -and $_.IPAddress -notmatch '^127\.' -and ($_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)') } | Select-Object -First 1 -ExpandProperty IPAddress); return $ip } catch { return $null } }
$opsPath = ".\reports\ops\ops_status.json"; $cfgPath = ".\pal\config\pal_watchdog.json"
$ops = To-Hashtable (Read-Json $opsPath); $cfg = Read-Json $cfgPath; $port = 8787; if ($cfg -and $cfg.web -and $cfg.web.port) { $port = [int]$cfg.web.port }
$lan = Get-LanIp; $lanUrl = if ($lan) { "http://$($lan):$($port)" } else { "" }
$tunnelUrl = ""; if ($ops.ContainsKey("tunnel") -and $ops.tunnel -and $ops.tunnel.url) { $tunnelUrl = [string]$ops.tunnel.url }
$phone = @{}; $phone.lan = $lanUrl; if ($tunnelUrl) { $phone.url = $tunnelUrl } else { $phone.url = $lanUrl }
$ops["phone"] = $phone; $ops["ts"] = (Get-Date).ToString("s")
$ops | ConvertTo-Json -Depth 8 | Set-Content $opsPath -Encoding UTF8
Write-Host ("ops_status.json updated. phone.lan={0} phone.url={1}" -f $phone.lan, $phone.url)
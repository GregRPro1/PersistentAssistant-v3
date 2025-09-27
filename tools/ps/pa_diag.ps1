Set-StrictMode -Version Latest

function Get-PortPids { param([int]$Port)
  $out = @()
  try {
    $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($conns) {
      $out = $conns | Where-Object { $_.State -in @('Listen','Established') } | Select-Object -ExpandProperty OwningProcess -Unique
    }
  } catch {
    $rows = netstat -ano | Select-String (':' + $Port + '\\b')
    foreach ($row in $rows) {
      $parts = ($row -split '\\s+') | Where-Object { $_ -ne '' }
      if ($parts.Length -ge 5) {
        $procId = [int]$parts[-1]
        if ($out -notcontains $procId) { $out += $procId }
      }
    }
  }
  return $out
}

function Kill-Port { param([int]$Port,[switch]$Force)
  $pidsList = Get-PortPids -Port $Port
  foreach ($procId in $pidsList) {
    try {
      $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
      if ($p) { if ($Force) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue } else { Stop-Process -Id $procId -ErrorAction SilentlyContinue } }
    } catch {}
  }
}

function Collect-PortSnapshot {
  $rows = @()
  try {
    $conns = Get-NetTCPConnection -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -ge 8780 -and $_.LocalPort -le 8800 }
    foreach ($c in $conns) {
      $rows += [pscustomobject]@{ port=$c.LocalPort; pid=$c.OwningProcess; proc=''; local=$c.LocalAddress; state=$c.State }
    }
  } catch {}
  foreach ($r in $rows) {
    try { $pr = Get-Process -Id $r.pid -ErrorAction SilentlyContinue; if ($pr) { $r.proc = $pr.ProcessName } } catch {}
  }
  for ($pt=8780; $pt -le 8800; $pt++) {
    if (-not ($rows | Where-Object { $_.port -eq $pt })) {
      $pidsList = Get-PortPids -Port $pt
      foreach ($procId in $pidsList) {
        $name=''; try { $pr = Get-Process -Id $procId -ErrorAction SilentlyContinue; if ($pr) { $name = $pr.ProcessName } } catch {}
        $rows += [pscustomobject]@{ port=$pt; pid=$procId; proc=$name; local='(unknown)'; state='(unknown)' }
      }
    }
  }
  return $rows
}

function Netstat-Snapshot { try { return (netstat -ano | Out-String) } catch { return '' } }

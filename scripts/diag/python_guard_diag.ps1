param(
    [string]$File = "server\agent_sidecar_wrapper.py",
    [switch]$RunSmoke # if compile OK, do a lightweight smoke test
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-Section([string]$name) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    Write-Host ">> [$name] START"
    [pscustomobject]@{ Name = $name; SW = $sw }
}
function End-Section($ctx, [bool]$ok = $true) {
    $ctx.SW.Stop()
    $status = if ($ok) { "OK" } else { "FAIL" }
    Write-Host ">> [$($ctx.Name)] $status ($($ctx.SW.Elapsed))"
}

# --- S1: Basic file sanity -----------------------------------------------------
$S1 = New-Section "S1:file-sanity"
if (!(Test-Path $File)) {
    Write-Host "file: $File  (NOT FOUND)"
    End-Section $S1 $false
    exit 1
}
$all = Get-Content $File -Raw
$lines = Get-Content $File
Write-Host "file: $File  (lines=$($lines.Count), bytes=$($all.Length))"
End-Section $S1 $true

# --- S2: Compile check ---------------------------------------------------------
$S2 = New-Section "S2:py-compile"
$pyOK = $false
$pyOut = ""
$pyErr = ""
try {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "python"
    $psi.Arguments = "-c `"import py_compile,sys; py_compile.compile(r'$File', doraise=True); print('PY_COMPILE_OK')`""
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $p = [System.Diagnostics.Process]::Start($psi)
    $pyOut = $p.StandardOutput.ReadToEnd()
    $pyErr = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    if ($pyOut -match "PY_COMPILE_OK" -and $p.ExitCode -eq 0) { $pyOK = $true }
}
catch {
    $pyErr = $_ | Out-String
}
if ($pyOK) {
    Write-Host "compile: OK"
    End-Section $S2 $true
}
else {
    Write-Host "compile: FAIL"
    if ($pyOut) { Write-Host "--- py stdout ---`n$pyOut" }
    if ($pyErr) { Write-Host "--- py stderr ---`n$pyErr" }

    # Extract error line number if present
    $m = [regex]::Match(($pyErr + $pyOut), 'File ".+agent_sidecar_wrapper\.py", line (\d+)')
    if ($m.Success) {
        $ln = [int]$m.Groups[1].Value
        Write-Host "error-line: $ln"

        $start = [Math]::Max(0, $ln - 15); $end = [Math]::Min($lines.Count - 1, $ln + 15)
        Write-Host "=== context ($start..$end) ==="
        for ($i = $start; $i -le $end; $i++) {
            $num = ($i + 1).ToString().PadLeft(5, ' ')
            $mark = if ($i -eq ($ln - 1)) { ">>" } else { "  " }
            Write-Host ("{0} {1}: {2}" -f $mark, $num, $lines[$i])
        }

        # Indentation + orphan-except heuristic at the error line
        $errLine = $lines[$ln - 1]
        $indent = ([regex]::Match($errLine, '^\s*')).Value
        $indentLen = $indent.Length
        $sameIndentTryAbove = $null
        for ($j = $ln - 2; $j -ge 0; $j--) {
            $l = $lines[$j]
            $ind = ([regex]::Match($l, '^\s*')).Value.Length
            if ($ind -lt $indentLen) { break } # exited this indent block
            if ($ind -eq $indentLen -and $l -match '^\s*try:\s*$') {
                $sameIndentTryAbove = $j + 1; break
            }
        }
        Write-Host "indent-len: $indentLen"
        Write-Host ("same-indent-try-above: " + ($(if ($sameIndentTryAbove) { $sameIndentTryAbove }else { 'NONE' })))

        if ($errLine -match '^\s*except\s+Exception' -and -not $sameIndentTryAbove) {
            Write-Host "diagnosis: likely **orphan except** at line $ln (no matching try: at same indent)."
        }
        else {
            Write-Host "diagnosis: see context; orphan not proven. We’ll need a targeted patch."
        }
    }
    else {
        Write-Host "no line number detected from compiler output"
    }

    End-Section $S2 $false
    exit 2
}

# --- S3: Optional smoke test if compile OK -------------------------------------
if ($RunSmoke) {
    $S3 = New-Section "S3:smoke-test"
    try {
        # Avoid killing unrelated Python processes; filter by repo path and no window
        Get-Process -Name "python" -ErrorAction SilentlyContinue `
        | Where-Object { $_.Path -like "*\_Repos\PersistentAssistant\*" -and $_.MainWindowTitle -eq "" } `
        | Stop-Process -Force -ErrorAction SilentlyContinue

        # Bring up
        python tools\py\pa_agent_bringup.py --host 127.0.0.1 --port 8782 --timeout 30 | Write-Host

        # Health
        $hc = (Invoke-WebRequest http://127.0.0.1:8782/health -UseBasicParsing).StatusCode
        Write-Host "health:" $hc

        # Routes
        $routes = Invoke-RestMethod http://127.0.0.1:8782/__routes__
        Write-Host ("route-count: " + $routes.Count)
        $plan = $routes | Where-Object { $_.rule -eq "/agent/plan" }
        $prop = $routes | Where-Object { $_.rule -eq "/agent/propose" }
        Write-Host ("has /agent/plan: " + ($(if ($plan) { "Y" }else { "N" })))
        Write-Host ("has /agent/propose: " + ($(if ($prop) { "Y" }else { "N" })))

        # Quick JSON calls (tolerate failure)
        try { $po = (Invoke-RestMethod http://127.0.0.1:8782/agent/plan).ok; Write-Host ("plan.ok: " + $po) } catch { Write-Host "plan.ok: ERR" }
        try { $n2 = (Invoke-RestMethod http://127.0.0.1:8782/agent/next2).ok; Write-Host ("next2.ok: " + $n2) } catch { Write-Host "next2.ok: ERR" }

        # Tail logs
        $lastOut = Get-ChildItem tmp\logs\sidecar_*_*.out.log | Sort-Object LastWriteTime | Select-Object -Last 1
        $lastErr = Get-ChildItem tmp\logs\sidecar_*_*.err.log | Sort-Object LastWriteTime | Select-Object -Last 1
        "`n--- tail OUT ---"; if ($lastOut) { Get-Content $lastOut.FullName -Tail 40 }
        "`n--- tail ERR ---"; if ($lastErr) { Get-Content $lastErr.FullName -Tail 40 }

        End-Section $S3 $true
    }
    catch {
        Write-Host "smoke-test exception: $($_ | Out-String)"
        End-Section $S3 $false
        exit 3
    }
}


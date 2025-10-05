Set-StrictMode -Version Latest
# try to enable native cmd error propagation when available
try { $script:PSNativeCommandUseErrorActionPreference = $true } catch {}
# remove fragile aliases that collide with our helpers
foreach($a in @('h','H','history','curl','wget')){ try{ if(Test-Path "alias:$a"){ Remove-Item "alias:$a" -Force } }catch{} }

function Get-TokenFromYaml {
  param([string]$Path = "config\phone_approvals.yaml")
  if(-not (Test-Path $Path)){ return "" }
  foreach($ln in (Get-Content $Path)){
    if($ln -match '^\s*token\s*:\s*'){
      $v = $ln.Split(':',2)[1].Trim().Trim('"').Trim("'")
      if($v){ return $v }
    }
  }
  return ""
}

function Invoke-JsonAuth {
  param([Parameter(Mandatory)][string]$Url,[string]$Token,[int]$TimeoutSec=10)
  try{
    $h=@{}
    if($Token){ $h['Authorization']="Bearer $Token" }
    Invoke-RestMethod -Uri $Url -TimeoutSec $TimeoutSec -Headers $h
  }catch{ $null }
}

function Invoke-TextAuth {
  param([Parameter(Mandatory)][string]$Url,[string]$Token,[int]$TimeoutSec=10)
  try{
    $h=@{}
    if($Token){ $h['Authorization']="Bearer $Token" }
    Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -Headers $h
  }catch{ $null }
}

function Write-FileUtf8 {
  param([Parameter(Mandatory)][string]$Path,[Parameter(Mandatory)][string[]]$Lines)
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllLines($Path,$Lines,$enc)
}

function Replace-Literal {
  param([Parameter(Mandatory)][string]$Text,[Parameter(Mandatory)][string]$Old,[Parameter(Mandatory)][string]$New)
  $Text.Replace($Old,$New)
}

function Kill-PortOwners {
  param([Parameter(Mandatory)][int]$Port)
  $owners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ })
  foreach($procId in $owners){
    try{ Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue }catch{}
    try{ & taskkill /PID $procId /F /T | Out-Null }catch{}
  }
  $owners
}

function Start-Detached {
  param([Parameter(Mandatory)][string]$Exe,[string[]]$Args=@(),[string]$WorkDir=".",
        [string]$OutLog="tmp\logs\proc.out.log",[string]$ErrLog="tmp\logs\proc.err.log")
  Start-Process -FilePath $Exe -ArgumentList $Args -WorkingDirectory $WorkDir `
    -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog -WindowStyle Hidden | Out-Null
}

function Parse-PasteAst {
  param([Parameter(Mandatory)][string]$ScriptText)
  $tokens=$null; $errs=@()
  [System.Management.Automation.Language.Parser]::ParseInput($ScriptText,[ref]$tokens,[ref]$errs) | Out-Null
  ,$errs
}

Export-ModuleMember -Function * -Alias *
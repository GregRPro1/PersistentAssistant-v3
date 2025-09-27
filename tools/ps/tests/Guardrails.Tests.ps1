Set-StrictMode -Version Latest
Describe 'Guardrails basic' {
  It 'Parser gate script exists' { Test-Path (Join-Path $PSScriptRoot '..\\Test-PSScripts.ps1') | Should -BeTrue }
}

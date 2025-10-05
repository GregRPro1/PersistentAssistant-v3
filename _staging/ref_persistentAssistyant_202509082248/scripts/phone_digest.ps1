param(
  [Parameter(Mandatory=$true)][string]$Token,
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8770
)
$ErrorActionPreference = "Stop"
$uri = "http://$BindHost`:$Port/phone/digest"
$headers = @{ "X-Phone-Token" = $Token }
$resp = Invoke-WebRequest -Uri $uri -Headers $headers -UseBasicParsing
$resp.Content

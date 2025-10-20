# /api/endpoints present
$code = Invoke-WebRequest "http://127.0.0.1:5070/api/endpoints" -UseBasicParsing | Select-Object -Expand StatusCode
if ($code -ne 200) { throw "/api/endpoints not 200" }
"OK: endpoints API"

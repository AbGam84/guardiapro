# Cancela deploy atascado y publica main en excalibu-sentinel (Render API).
# Una vez: Render Dashboard → Account Settings → API Keys → crear clave
# Pegar en push-cloud.env: RENDER_API_KEY=rnd_...
param(
  [string]$ServiceId = "srv-dand4drtqb8s73bgpe30",
  [string]$Commit = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envFile = Join-Path $root "push-cloud.env"
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
      $k = $matches[1].Trim()
      $v = $matches[2].Trim().Trim('"')
      if (-not [string]::IsNullOrWhiteSpace($k)) { Set-Item -Path "env:$k" -Value $v }
    }
  }
}
$key = $env:RENDER_API_KEY
if (-not $key) {
  Write-Host "Falta RENDER_API_KEY en push-cloud.env" -ForegroundColor Red
  Write-Host "Render → Account Settings → API Keys → pegue rnd_... en push-cloud.env"
  exit 1
}
$headers = @{ Authorization = "Bearer $key"; Accept = "application/json" }

function Invoke-Render($Method, $Path, $Body = $null) {
  $uri = "https://api.render.com/v1$Path"
  if ($Body) {
    return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -ContentType "application/json" -Body ($Body | ConvertTo-Json)
  }
  return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
}

Write-Host "Listando deploys..."
$deploys = Invoke-Render GET "/services/$ServiceId/deploys?limit=5"
foreach ($wrap in $deploys) {
  $d = $wrap.deploy
  if (-not $d) { continue }
  $st = $d.status
  Write-Host "  $($d.id) $st"
  if ($st -in @("build_in_progress", "update_in_progress", "queued", "created", "pre_deploy_in_progress")) {
    Write-Host "  Cancelando $($d.id)..."
    try { Invoke-Render POST "/services/$ServiceId/deploys/$($d.id)/cancel" | Out-Null } catch { Write-Host "  (cancel: $($_.Exception.Message))" }
  }
}

if (-not $Commit) {
  $Commit = (git -C $root rev-parse HEAD).Trim()
}
Write-Host "Disparando deploy commit $Commit..."
$body = @{ clearCache = "clear" }
if ($Commit) { $body.commitId = $Commit }
Invoke-Render POST "/services/$ServiceId/deploys" $body | Out-Null
Write-Host "Deploy solicitado. Espere 3-6 min."
Write-Host "Pruebe: https://excalibu-sentinel.onrender.com/health/live"
Write-Host "        https://excalibu-sentinel.onrender.com/login?empresa=grupo-gomez"

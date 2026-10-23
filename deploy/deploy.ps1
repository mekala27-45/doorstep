# Deploy the doorstep API to Fly from a Windows machine.
#
# Reads FLY_API_TOKEN, DATABASE_URL (the shared Neon database; the tables go in the `doorstep`
# schema so the other projects' tables there are never touched) or DOORSTEP_DATABASE_URL (a
# database of its own, default schema), and DOORSTEP_WRITE_TOKEN from the .env beside the
# repository (C:\Project FullTime\.env) or the environment. Installs flyctl when it is missing,
# creates the app when it does not exist (trying a second name if the first is taken), stages the
# secrets, deploys with Fly's remote builder (no local Docker), checks the live health endpoint and
# writes the transcript to deploy\deploy-log.txt. Secrets are never printed.
#
#   powershell -ExecutionPolicy Bypass -File "C:\Project FullTime\doorstep\deploy\deploy.ps1"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $repo "deploy\_env.ps1")
Start-Transcript -Path (Join-Path $repo "deploy\deploy-log.txt") -Force | Out-Null
Read-DotEnv (Join-Path (Split-Path -Parent $repo) ".env")
Read-DotEnv (Join-Path $repo ".env")

$schema = ""
if ($env:DOORSTEP_DATABASE_URL) {
    $url = $env:DOORSTEP_DATABASE_URL
    Write-Host "database: DOORSTEP_DATABASE_URL, default schema"
} elseif ($env:DATABASE_URL) {
    $url = $env:DATABASE_URL
    $schema = "doorstep"
    Write-Host "database: DATABASE_URL, schema doorstep"
} else {
    throw "neither DOORSTEP_DATABASE_URL nor DATABASE_URL (the Neon connection string) is set"
}
if ($url -notmatch '^postgresql\+psycopg://') { $url = $url -replace '^postgres(ql)?://', 'postgresql+psycopg://' }
$tokenFile = Join-Path $repo "deploy\write-token.txt"
if (-not $env:DOORSTEP_WRITE_TOKEN) {
    if (Test-Path $tokenFile) { $env:DOORSTEP_WRITE_TOKEN = (Get-Content $tokenFile -Raw).Trim() }
    else { $env:DOORSTEP_WRITE_TOKEN = [guid]::NewGuid().ToString("N") }
}

Use-Flyctl
flyctl version

$candidates = @()
if ($env:DOORSTEP_FLY_APP_NAME) { $candidates += $env:DOORSTEP_FLY_APP_NAME }
$candidates += @("doorstep-housing-api", "doorstep-housing-api-am")
$apps = flyctl apps list --json | ConvertFrom-Json
$app = $null
foreach ($name in $candidates) {
    if ($apps | Where-Object { $_.Name -eq $name }) { $app = $name; break }
}
if (-not $app) {
    foreach ($name in $candidates) {
        Write-Host "creating app $name"
        flyctl apps create $name --org personal
        if ($LASTEXITCODE -eq 0) { $app = $name; break }
    }
}
if (-not $app) { throw "could not create a Fly app under any of: $($candidates -join ', ')" }

Set-Location $repo
flyctl secrets set --app $app --stage "DATABASE_URL=$url" "DOORSTEP_WRITE_TOKEN=$env:DOORSTEP_WRITE_TOKEN" "DOORSTEP_DB_SCHEMA=$schema"
flyctl deploy --app $app --remote-only --ha=false
if ($LASTEXITCODE -ne 0) { throw "flyctl deploy failed" }

$base = "https://$app.fly.dev"
Write-Host "checking $base/v1/health"
$health = $null
for ($i = 0; $i -lt 12 -and -not $health; $i++) {
    try { $health = Invoke-RestMethod -Uri "$base/v1/health" -TimeoutSec 60 } catch { Start-Sleep -Seconds 10 }
}
if (-not $health) { throw "the API did not answer at $base/v1/health" }
Write-Host "health: status=$($health.status) database=$($health.database) model=$($health.model_version) metros=$($health.metros) latest=$($health.latest_period)"
Set-Content -Path (Join-Path $repo "deploy\live-url.txt") -Value $base
Set-Content -Path $tokenFile -Value $env:DOORSTEP_WRITE_TOKEN
Write-Host "deployed: $base"
Stop-Transcript | Out-Null

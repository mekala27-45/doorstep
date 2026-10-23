# Fill the demo queue from a separate client: one check for each of the twenty largest metros the server
# covers, at the metro's median household income, ten percent down, the default rate and a thirty year
# horizon, resting on the quarter before the latest so the latest quarter scores them; then score the log,
# so the check log is never empty. Writes what the server answered to results\deploy\replay.json.
#
#   powershell -ExecutionPolicy Bypass -File "C:\Project FullTime\doorstep\deploy\replay.ps1"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$base = (Get-Content (Join-Path $repo "deploy\live-url.txt") -Raw).Trim()
$token = (Get-Content (Join-Path $repo "deploy\write-token.txt") -Raw).Trim()
$headers = @{ Authorization = "Bearer $token" }

function Previous-Quarter($period) {
    $y = [int]$period.Substring(0, 4); $q = [int]$period.Substring(5, 1)
    if ($q -gt 1) { return "$y" + "Q" + ($q - 1) } else { return "$($y - 1)Q4" }
}

$health = Invoke-RestMethod -Uri "$base/v1/health" -TimeoutSec 120
$metros = (Invoke-RestMethod -Uri "$base/v1/metros" -TimeoutSec 90).metros | Select-Object -First 20
$made = @()
foreach ($m in $metros) {
    $body = @{ cbsa_code = $m.cbsa_code; income = ([Math]::Round($m.median_income / 1000) * 1000); down_share = 0.10; horizon_years = 30; quarter = (Previous-Quarter $m.latest_period); note = "demo queue" }
    try {
        $r = Invoke-RestMethod -Method Post -Uri "$base/v1/checks" -Headers $headers -ContentType "application/json" -TimeoutSec 120 -Body ($body | ConvertTo-Json)
        $made += [ordered]@{ metro = $m.cbsa_title; check_id = $r.check_id; payment_share = $r.payment_share; breakeven_years = $r.breakeven_years }
        Write-Host "check for $($m.cbsa_title): $($r.check_id) payment share $($r.payment_share)"
    } catch {
        Write-Host "no check for $($m.cbsa_title): $($_.Exception.Message)"
    }
}
$scored = Invoke-RestMethod -Method Post -Uri "$base/v1/score" -Headers $headers -ContentType "application/json" -TimeoutSec 180 -Body (@{ note = "demo queue" } | ConvertTo-Json)
$card = Invoke-RestMethod -Uri "$base/v1/scorecard" -TimeoutSec 90
$result = [ordered]@{
    base_url = $base
    replayed_at = (Get-Date).ToUniversalTime().ToString("o")
    latest_period = $health.latest_period
    checks_made = $made.Count
    metros = $metros.Count
    scored = $scored.scored
    unscored_share = $scored.unscored_share
    scorecard = @{ checks = $card.checks; scored = $card.scored; mean_absolute_error = $card.mean_absolute_error; mean_price_move = $card.mean_price_move; mean_rate_move = $card.mean_rate_move }
}
New-Item -ItemType Directory -Force -Path (Join-Path $repo "results\deploy") | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $repo "results\deploy\replay.json")
$result | ConvertTo-Json -Depth 5
Write-Host "replayed: $($made.Count) demo checks made and scored on the live log"

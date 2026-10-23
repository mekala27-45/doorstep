# Verify the live API from a separate client (a Windows machine, not the server, not the build
# sandbox): make a check for the largest metro at its median income, resting on the quarter before the
# latest one the server holds so the latest quarter can score it, score the log, read the check back
# with its score, read the audit log, and confirm the audit row was written before the check's response
# was served. Writes the transcript to deploy\verify-log.txt and the observation, with no secrets in it,
# to results\deploy\verification.json so the build can quote it.
#
#   powershell -ExecutionPolicy Bypass -File "C:\Project FullTime\doorstep\deploy\verify.ps1"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Start-Transcript -Path (Join-Path $repo "deploy\verify-log.txt") -Force | Out-Null
$base = (Get-Content (Join-Path $repo "deploy\live-url.txt") -Raw).Trim()
$token = (Get-Content (Join-Path $repo "deploy\write-token.txt") -Raw).Trim()
$headers = @{ Authorization = "Bearer $token" }

function Previous-Quarter($period) {
    $y = [int]$period.Substring(0, 4); $q = [int]$period.Substring(5, 1)
    if ($q -gt 1) { return "$y" + "Q" + ($q - 1) } else { return "$($y - 1)Q4" }
}

Write-Host "client: $env:COMPUTERNAME ($([Environment]::OSVersion.VersionString)), PowerShell $($PSVersionTable.PSVersion)"
Write-Host "server: $base"
$health = Invoke-RestMethod -Uri "$base/v1/health" -TimeoutSec 90
Write-Host "health: status=$($health.status) database=$($health.database) model=$($health.model_version) metros=$($health.metros) latest=$($health.latest_period) rate=$($health.rate_default)"

$metro = (Invoke-RestMethod -Uri "$base/v1/metros" -TimeoutSec 90).metros[0]
$quarter = Previous-Quarter $metro.latest_period
$income = [Math]::Round($metro.median_income / 1000) * 1000
$body = @{ cbsa_code = $metro.cbsa_code; income = $income; down_share = 0.10; horizon_years = 30; quarter = $quarter; note = "verification from a separate client" }
$check = Invoke-RestMethod -Method Post -Uri "$base/v1/checks" -Headers $headers -ContentType "application/json" -TimeoutSec 120 -Body ($body | ConvertTo-Json)
$servedAt = [DateTime]::Parse($check.served_at).ToUniversalTime()
Write-Host "check $($check.check_id): $($metro.cbsa_title), income $income, quarter $quarter, payment share $($check.payment_share), affordable price $($check.affordable_price), breakeven $($check.breakeven_years) ($($check.breakeven_low) to $($check.breakeven_high))"

$scored = Invoke-RestMethod -Method Post -Uri "$base/v1/score" -Headers $headers -ContentType "application/json" -TimeoutSec 120 -Body (@{ note = "verification from a separate client" } | ConvertTo-Json)
Write-Host "scored $($scored.scored) of $($scored.checks) checks against $($scored.latest_period), unscored share $($scored.unscored_share)"

$read = Invoke-RestMethod -Uri "$base/v1/checks/$($check.check_id)" -TimeoutSec 90
$audit = Invoke-RestMethod -Uri "$base/v1/audit?limit=50" -TimeoutSec 90
$created = $audit.entries | Where-Object { $_.action -eq "create" -and $_.resource_id -eq $check.check_id } | Select-Object -First 1
$auditBefore = ([DateTime]::Parse($created.at).ToUniversalTime()) -le $servedAt
$ok = ($read.check_id -eq $check.check_id) -and ([Math]::Abs($read.payment_share - $check.payment_share) -lt 1e-12) -and ($null -ne $read.score) -and $auditBefore -and ($read.statement.Length -gt 100)
$result = [ordered]@{
    base_url = $base
    client = "$env:COMPUTERNAME, Windows, PowerShell $($PSVersionTable.PSVersion)"
    checked_at = (Get-Date).ToUniversalTime().ToString("o")
    health = @{ status = $health.status; database = $health.database; model_version = $health.model_version; metros = $health.metros; latest_period = $health.latest_period; rate_default = $health.rate_default }
    metro = $metro.cbsa_title
    cbsa_code = $metro.cbsa_code
    income = $income
    quarter = $quarter
    check_id = $check.check_id
    payment_share = $check.payment_share
    affordable_price = $check.affordable_price
    affordable_share = $check.affordable_share
    breakeven_years = $check.breakeven_years
    breakeven_low = $check.breakeven_low
    breakeven_high = $check.breakeven_high
    read_back_payment_share = $read.payment_share
    score = $read.score
    unscored_share = $scored.unscored_share
    audit_entries = $audit.entries.Count
    audit_before_response = $auditBefore
    statement_present = ($read.statement.Length -gt 100)
    passed = $ok
}
New-Item -ItemType Directory -Force -Path (Join-Path $repo "results\deploy") | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $repo "results\deploy\verification.json")
$result | ConvertTo-Json -Depth 5
if (-not $ok) { throw "verification failed" }
Write-Host "verified: the check, its score and its audit row were read back from a separate client"
Stop-Transcript | Out-Null

# fetch-data.ps1: download the public data doorstep needs onto this PC.
#
# The build sandbox cannot reach any government host, so this script runs here, on Windows, from
# PowerShell or from Git GUI's Tools menu. It is safe to re-run: a finished file is skipped, a half
# written one is fetched again, downloads resume, and the HMDA filter is skipped once its summary
# exists. Each mode logs to fetch-log-<mode>.txt and writes fetch-status-<mode>.json, which the build
# reads to prove that the window ends at the latest release.
#
#   powershell -ExecutionPolicy Bypass -File fetch-data.ps1 all     (core, then hmda, then acs)
#   powershell -ExecutionPolicy Bypass -File fetch-data.ps1 core    (FHFA, PMMS, HUD, BPS, popest, delineations, gazetteer)
#   powershell -ExecutionPolicy Bypass -File fetch-data.ps1 acs     (the ACS one year API; probes first, stops when the API is down)
#   powershell -ExecutionPolicy Bypass -File fetch-data.ps1 hmda    (the HMDA snapshot LAR zips, filtered to gz parts)
#
# Sources and terms:
#   FHFA House Price Index master file. U.S. government work, public domain.
#   Census Bureau: ACS one year API, Building Permits Survey, population estimates, metropolitan
#     delineation files, gazetteer. U.S. government work, public domain.
#   HUD: Fair Market Rents history and income limits. U.S. government work, public domain.
#   Freddie Mac Primary Mortgage Market Survey weekly history. Free with attribution to Freddie Mac.
#   CFPB / FFIEC: HMDA snapshot national loan level dataset. U.S. government work, public domain.
#
# The optional CENSUS_API_KEY (free, instant at api.census.gov/data/key_signup.html) is read from
# the .env one folder up (C:\Project FullTime\.env) or the environment. Without a key the Census API
# allows 500 requests per day per address, which covers one full run of this script.

param([string]$Mode = "all", [switch]$DeleteZips, [int]$FirstYear = 2005, [int]$LastYear = 0)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dirs = @{}
foreach ($d in @("fhfa", "acs", "hud", "pmms", "bps", "popest", "delineations", "gazetteer", "hmda")) {
    $dirs[$d] = Join-Path $root $d
    New-Item -ItemType Directory -Force -Path $dirs[$d] | Out-Null
}
$agent = "doorstep-data-fetch/0.1 (portfolio analysis of public housing data)"
$browserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

function Read-DotEnv($path) {
    if (Test-Path $path) {
        Get-Content $path | ForEach-Object {
            if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
                $name = $matches[1]; $value = $matches[2].Trim().Trim('"').Trim("'")
                if (-not [string]::IsNullOrEmpty($value) -and -not [Environment]::GetEnvironmentVariable($name)) {
                    [Environment]::SetEnvironmentVariable($name, $value, "Process")
                }
            }
        }
    }
}
Read-DotEnv (Join-Path (Split-Path -Parent $root) ".env")

function Test-Zip($path, $minBytes) {
    if (-not (Test-Path $path)) { return $false }
    if ((Get-Item $path).Length -lt $minBytes) { return $false }
    $fs = [IO.File]::OpenRead($path)
    try { $a = $fs.ReadByte(); $b = $fs.ReadByte() } finally { $fs.Close() }
    return ($a -eq 0x50 -and $b -eq 0x4B)
}

function Test-Small($path, $minBytes) {
    # A downloaded page that says "not found" is small and starts with a tag; a real file is not.
    if (-not (Test-Path $path)) { return $false }
    $len = (Get-Item $path).Length
    if ($len -lt $minBytes) { return $false }
    $fs = [IO.File]::OpenRead($path)
    try { $head = New-Object byte[] 64; $n = $fs.Read($head, 0, 64) } finally { $fs.Close() }
    $text = [Text.Encoding]::ASCII.GetString($head, 0, $n).TrimStart()
    if ($text.StartsWith("<!DOCTYPE") -or $text.StartsWith("<html") -or $text.StartsWith("<HTML")) { return $false }
    return $true
}

function Get-File($url, $dest, $ua, $resume) {
    # Downloads to a .part file and renames on success, so a finished name is never half written.
    $part = "$dest.part"
    $args = @("-L", "--fail", "--silent", "--show-error", "--retry", "5", "--retry-delay", "15", "--connect-timeout", "60", "--max-time", "7200", "-A", $ua, "-o", $part, $url)
    if ($resume -and (Test-Path $part)) { $args = @("-C", "-") + $args } elseif (Test-Path $part) { Remove-Item $part -Force }
    & curl.exe @args
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        if (-not $resume -and (Test-Path $part)) { Remove-Item $part -Force }
        return $code
    }
    Move-Item -Force $part $dest
    return 0
}

function Fetch-First($candidates, $dest, $minBytes, $ua) {
    # Tries each candidate URL in order and keeps the first real file. Returns the URL that worked or $null.
    if (Test-Small $dest $minBytes) { Write-Host "  have $(Split-Path -Leaf $dest)"; return "kept" }
    foreach ($url in $candidates) {
        Write-Host "  $url"
        $code = Get-File $url $dest $ua $false
        if ($code -eq 0 -and (Test-Small $dest $minBytes)) { Write-Host "    ok $((Get-Item $dest).Length) bytes"; return $url }
        if (Test-Path $dest) { Remove-Item $dest -Force }
        Write-Host "    no (curl $code)"
    }
    return $null
}

function Save-Status($name, $status) {
    $status | ConvertTo-Json -Depth 8 | Set-Content -Path (Join-Path $root "fetch-status-$name.json") -Encoding UTF8
}

function Run-Core {
    $started = Get-Date
    $now = $started.ToUniversalTime()
    Start-Transcript -Path (Join-Path $root "fetch-log-core.txt") -Append | Out-Null
    Write-Host "fetch core started $($now.ToString('o')) on $env:COMPUTERNAME"
    $status = [ordered]@{ mode = "core"; machine = $env:COMPUTERNAME; started = $now.ToString("o"); sources = [ordered]@{} }

    # 1. FHFA House Price Index master file: every index, every geography, every frequency, one CSV.
    Write-Host "fhfa"
    $fhfaDest = Join-Path $dirs.fhfa "hpi_master.csv"
    $u = Fetch-First @(
        "https://www.fhfa.gov/hpi/download/monthly/hpi_master.csv",
        "https://www.fhfa.gov/DataTools/Downloads/Documents/HPI/HPI_master.csv",
        "https://www.fhfa.gov/hpi/download/quarterly/hpi_master.csv"
    ) $fhfaDest 1000000 $browserAgent
    $fhfaLatest = $null
    if (Test-Path $fhfaDest) {
        $lines = Get-Content $fhfaDest | Select-Object -Last 2000
        $fhfaLatest = ($lines | ForEach-Object { $p = $_ -split ","; if ($p.Length -ge 5 -and $p[4] -match '^\d{4}$') { "$($p[4])Q$($p[5])" } } | Sort-Object | Select-Object -Last 1)
    }
    $status.sources.fhfa = [ordered]@{ url = $u; file = "fhfa/hpi_master.csv"; bytes = $(if (Test-Path $fhfaDest) { (Get-Item $fhfaDest).Length } else { 0 }); latest_period_seen_in_tail = $fhfaLatest }

    # 2. Freddie Mac PMMS weekly history.
    Write-Host "pmms"
    $pmmsDest = Join-Path $dirs.pmms "historicalweeklydata.xlsx"
    $u = Fetch-First @(
        "https://www.freddiemac.com/pmms/docs/historicalweeklydata.xlsx",
        "https://www.freddiemac.com/pmms/docs/historicalweeklydata.xls"
    ) $pmmsDest 100000 $browserAgent
    $status.sources.pmms = [ordered]@{ url = $u; file = "pmms/historicalweeklydata.xlsx"; bytes = $(if (Test-Path $pmmsDest) { (Get-Item $pmmsDest).Length } else { 0 }) }

    # 3. HUD: the county level Fair Market Rent history (one file, 1983 to the latest fiscal year), the
    #    latest fiscal year's FMR file for the HUD area to metro map, and the income limits per fiscal year.
    Write-Host "hud fmr history"
    $fmrHist = $null
    foreach ($fy in ($now.Year + 1)..2023) {
        $dest = Join-Path $dirs.hud "FMR_All_1983_$fy.csv"
        $u = Fetch-First @(
            "https://www.huduser.gov/portal/datasets/FMR/FMR_All_1983_$fy.csv",
            "https://www.huduser.gov/portal/datasets/fmr/fmr$fy/FMR_All_1983_$fy.csv"
        ) $dest 500000 $browserAgent
        if ($u) { $fmrHist = [ordered]@{ fiscal_year = $fy; url = $u; file = "hud/FMR_All_1983_$fy.csv"; bytes = (Get-Item $dest).Length }; break }
        $dest = Join-Path $dirs.hud "FMR_All_1983_$fy.xlsx"
        $u = Fetch-First @(
            "https://www.huduser.gov/portal/datasets/FMR/FMR_All_1983_$fy.xlsx",
            "https://www.huduser.gov/portal/datasets/fmr/fmr$fy/FMR_All_1983_$fy.xlsx",
            "https://www.huduser.gov/portal/datasets/fmr/fmr$fy/FMR_All_1983_${fy}_rev.xlsx"
        ) $dest 500000 $browserAgent
        if ($u) { $fmrHist = [ordered]@{ fiscal_year = $fy; url = $u; file = "hud/FMR_All_1983_$fy.xlsx"; bytes = (Get-Item $dest).Length }; break }
    }
    Write-Host "hud fmr history readme"
    $null = Fetch-First @("https://www.huduser.gov/portal/datasets/FMR/READ_ME_FMRHIST_FY2025.docx", "https://www.huduser.gov/portal/datasets/FMR/READ_ME_FMRHIST_FY2024.docx") (Join-Path $dirs.hud "READ_ME_FMRHIST.docx") 10000 $browserAgent
    Write-Host "hud fmr latest fiscal year file"
    $fmrLatest = $null
    foreach ($fy in ($now.Year + 1)..2023) {
        $yy = $fy.ToString().Substring(2)
        $dest = Join-Path $dirs.hud "FY${yy}_FMRs.xlsx"
        $u = Fetch-First @(
            "https://www.huduser.gov/portal/datasets/fmr/fmr$fy/FY${yy}_FMRs.xlsx",
            "https://www.huduser.gov/portal/datasets/fmr/fmr$fy/FY${yy}_FMRs_revised.xlsx",
            "https://www.huduser.gov/portal/datasets/fmr/fmr$fy/FY${fy}_FMRs.xlsx",
            "https://www.huduser.gov/portal/datasets/fmr/fmr$fy/FY${yy}_4050_FMRs.xlsx",
            "https://www.huduser.gov/portal/datasets/fmr/fmr$fy/FY${yy}_4050_FMRs_rev.xlsx"
        ) $dest 100000 $browserAgent
        if ($u) { $fmrLatest = [ordered]@{ fiscal_year = $fy; url = $u; file = "hud/FY${yy}_FMRs.xlsx"; bytes = (Get-Item $dest).Length }; break }
    }
    Write-Host "hud income limits by fiscal year"
    $il = [ordered]@{}
    foreach ($fy in 2000..($now.Year + 1)) {
        $yy = $fy.ToString().Substring(2)
        $dest = Join-Path $dirs.hud "Section8-FY$yy.xlsx"
        $destXls = Join-Path $dirs.hud "Section8-FY$yy.xls"
        if ((Test-Small $dest 50000) -or (Test-Small $destXls 50000)) { $il["$fy"] = "kept"; continue }
        $u = Fetch-First @(
            "https://www.huduser.gov/portal/datasets/il/il$yy/Section8-FY$yy.xlsx",
            "https://www.huduser.gov/portal/datasets/il/il$yy/Section8_FY$yy.xlsx",
            "https://www.huduser.gov/portal/datasets/il/il$yy/Section8-FY$fy.xlsx"
        ) $dest 50000 $browserAgent
        if (-not $u) {
            $u = Fetch-First @(
                "https://www.huduser.gov/portal/datasets/il/il$yy/Section8-FY$yy.xls",
                "https://www.huduser.gov/portal/datasets/il/il$yy/Section8_FY$yy.xls",
                "https://www.huduser.gov/portal/datasets/il/il$yy/Section8.xls",
                "https://www.huduser.gov/portal/datasets/il/il$yy/section8.xls"
            ) $destXls 50000 $browserAgent
        }
        $il["$fy"] = $(if ($u) { $u } else { "missing" })
        Start-Sleep -Seconds 1
    }
    $status.sources.hud = [ordered]@{ fmr_history = $fmrHist; fmr_latest_file = $fmrLatest; income_limits = $il }

    # 4. Census Building Permits Survey: annual files by county (for the crosswalk) and by metro (as published),
    #    plus the latest year to date file of each.
    Write-Host "bps"
    $bps = [ordered]@{ county_annual = [ordered]@{}; metro_annual = [ordered]@{}; county_ytd = $null; metro_ytd = $null }
    foreach ($y in 2000..($now.Year - 1)) {
        $dest = Join-Path $dirs.bps "co${y}a.txt"
        $u = Fetch-First @("https://www2.census.gov/econ/bps/County/co${y}a.txt") $dest 20000 $agent
        $bps.county_annual["$y"] = $(if ($u) { $u } else { "missing" })
        $bps.metro_annual["$y"] = "not fetched: the county files map to every delineation vintage"
    }
    for ($m = $now.Month; $m -ge 1 -and -not $bps.county_ytd; $m--) {
        $tag = "{0}{1:D2}" -f $now.Year.ToString().Substring(2), $m
        $dest = Join-Path $dirs.bps "co${tag}y.txt"
        $u = Fetch-First @("https://www2.census.gov/econ/bps/County/co${tag}y.txt") $dest 20000 $agent
        if ($u) { $bps.county_ytd = [ordered]@{ period = "$($now.Year)-$($m.ToString('D2'))"; url = $u; file = "bps/co${tag}y.txt" } }
    }
    $status.sources.bps = $bps

    # 5. Census population estimates with components of change: the latest vintage (2020 onward), vintage 2019
    #    (2010 to 2019) and the 2000 to 2010 intercensal file, each at the metro and the county grain.
    Write-Host "popest"
    $pop = [ordered]@{}
    $latestV = $null
    foreach ($v in ($now.Year)..2024) {
        $dest = Join-Path $dirs.popest "cbsa-est$v-alldata.csv"
        $u = Fetch-First @("https://www2.census.gov/programs-surveys/popest/datasets/2020-$v/metro/totals/cbsa-est$v-alldata.csv") $dest 200000 $agent
        if ($u) { $pop["metro_2020_$v"] = $u; $latestV = $v; break }
    }
    if ($latestV) {
        $dest = Join-Path $dirs.popest "co-est$latestV-alldata.csv"
        $u = Fetch-First @("https://www2.census.gov/programs-surveys/popest/datasets/2020-$latestV/counties/totals/co-est$latestV-alldata.csv") $dest 1000000 $agent
        $pop["county_2020_$latestV"] = $(if ($u) { $u } else { "missing" })
    }
    $dest = Join-Path $dirs.popest "cbsa-est2019-alldata.csv"
    $u = Fetch-First @("https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/metro/totals/cbsa-est2019-alldata.csv") $dest 200000 $agent
    $pop["metro_2010_2019"] = $(if ($u) { $u } else { "missing" })
    $dest = Join-Path $dirs.popest "co-est2019-alldata.csv"
    $u = Fetch-First @("https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv") $dest 1000000 $agent
    $pop["county_2010_2019"] = $(if ($u) { $u } else { "missing" })
    $dest = Join-Path $dirs.popest "cbsa-est00int-alldata.csv"
    $u = Fetch-First @(
        "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/metro/cbsa-est00int-alldata.csv",
        "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/metro/CBSA-EST00INT-ALLDATA.csv",
        "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/metro/cbsa-est00int-01.csv"
    ) $dest 100000 $agent
    $pop["metro_2000_2010"] = $(if ($u) { $u } else { "missing" })
    $dest = Join-Path $dirs.popest "co-est00int-tot.csv"
    $u = Fetch-First @(
        "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/co-est00int-tot.csv",
        "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/CO-EST00INT-TOT.csv"
    ) $dest 200000 $agent
    $pop["county_2000_2010_totals"] = $(if ($u) { $u } else { "missing" })
    $dest = Join-Path $dirs.popest "co-est2009-alldata.csv"
    $u = Fetch-First @(
        "https://www2.census.gov/programs-surveys/popest/datasets/2000-2009/counties/totals/co-est2009-alldata.csv",
        "https://www2.census.gov/programs-surveys/popest/datasets/2000-2009/counties/totals/CO-EST2009-ALLDATA.csv"
    ) $dest 1000000 $agent
    $pop["county_2000_2009_components"] = $(if ($u) { $u } else { "missing" })
    $status.sources.popest = $pop

    # 6. OMB metropolitan delineation files, every vintage the window crosses, plus the CBSA gazetteer for a map.
    Write-Host "delineations"
    $del = [ordered]@{}
    $delCandidates = [ordered]@{
        "2023" = @("https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx")
        "2020" = @("https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2020/delineation-files/list1_2020.xls")
        "2018" = @("https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2018/delineation-files/list1_Sep_2018.xls", "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2018/delineation-files/list1.xls")
        "2017" = @("https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2017/delineation-files/list1.xls")
        "2015" = @("https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2015/delineation-files/list1.xls")
        "2013" = @("https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2013/delineation-files/list1.xls")
        "2009" = @("https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2009/historical-delineation-files/list3.xls", "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2009/historical-delineation-files/list1.xls")
    }
    foreach ($k in $delCandidates.Keys) {
        $ext = if ($delCandidates[$k][0].EndsWith(".xlsx")) { "xlsx" } else { "xls" }
        $dest = Join-Path $dirs.delineations "list1_$k.$ext"
        $u = Fetch-First $delCandidates[$k] $dest 50000 $agent
        $del["$k"] = $(if ($u) { $u } else { "missing" })
    }
    $status.sources.delineations = $del
    Write-Host "gazetteer"
    $gaz = $null
    foreach ($y in ($now.Year)..2022) {
        $dest = Join-Path $dirs.gazetteer "${y}_Gaz_cbsa_national.zip"
        $u = Fetch-First @("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/${y}_Gazetteer/${y}_Gaz_cbsa_national.zip") $dest 10000 $agent
        if ($u) { $gaz = [ordered]@{ year = $y; url = $u; file = "gazetteer/${y}_Gaz_cbsa_national.zip" }; break }
    }
    $status.sources.gazetteer = $gaz

    $status.finished = (Get-Date).ToUniversalTime().ToString("o")
    $status.minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
    Save-Status "core" $status
    Write-Host "fetch core finished in $($status.minutes) minutes"
    Stop-Transcript | Out-Null
}

function Get-AcsRequest($url, $timeoutSec) {
    $t0 = Get-Date
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeoutSec -UserAgent $agent
    $content = $response.Content
    $secs = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    if (-not $content.TrimStart().StartsWith("[") -and -not $content.TrimStart().StartsWith("{")) { throw "not JSON: " + $content.Substring(0, [Math]::Min(120, $content.Length)) }
    return @{ content = $content; seconds = $secs }
}

function Run-Acs {
    # The ACS one year tables, every year from 2005 to the latest release, at the metropolitan and
    # micropolitan geography (estimates and margins), from the Census API. The API has slow nights: each
    # request is tried once against api.census.gov with explicit variables (lighter than a group call) and
    # then once against Census Reporter's mirror of the same tables, and a year is abandoned after three
    # consecutive failures that are not a 404. Both response shapes are parsed by the build.
    $started = Get-Date
    $now = $started.ToUniversalTime()
    $logName = if ($LastYear -gt 0) { "fetch-log-acs-$FirstYear-$LastYear.txt" } else { "fetch-log-acs.txt" }
    Start-Transcript -Path (Join-Path $root $logName) -Append | Out-Null
    Write-Host "fetch acs started $($now.ToString('o')) on $env:COMPUTERNAME"
    $key = $env:CENSUS_API_KEY
    $keyPart = if ($key) { "&key=$key" } else { "" }
    # table -> the number of cells (variables _001 .. _NNN); margins are requested beside every estimate.
    $tables = [ordered]@{
        "B19013" = 1; "B25077" = 1; "B25064" = 1; "B25003" = 3; "B11001" = 9; "B19001" = 17; "B25070" = 11; "B25119" = 3;
        "B25071" = 1; "B25001" = 1; "B25002" = 3; "B25091" = 23; "B25007" = 21; "B25074" = 64; "B25118" = 25;
        "B25004" = 8; "B25024" = 11; "B25103" = 3; "B25106" = 46
    }
    $usTables = @("B19013", "B25064", "B25077", "B25070", "B25003", "B25119")
    $geo = "metropolitan%20statistical%20area/micropolitan%20statistical%20area:*"
    $acs = [ordered]@{ mode = "acs"; machine = $env:COMPUTERNAME; started = $now.ToString("o"); with_key = [bool]$key; years = [ordered]@{}; requests = 0; failures = @(); probe = ""; timings = @() }
    $probeUrl = "https://api.census.gov/data/2023/acs/acs1?get=NAME,B19013_001E&for=us:1$keyPart"
    if (-not $key) {
        Write-Host "CENSUS_API_KEY is not set. api.census.gov now answers every data request with a Missing Key page."
        Write-Host "Get a free key at https://api.census.gov/data/key_signup.html and add CENSUS_API_KEY=<key> to C:\Project FullTime\.env, then run this mode again."
        $acs.probe = "no key"
        $acs.finished = (Get-Date).ToUniversalTime().ToString("o")
        Save-Status "acs" $acs
        Stop-Transcript | Out-Null
        return
    }
    # The probe: a busy or slow API is waited out (the API has slow nights), a key problem stops the run.
    $probeOk = $false
    foreach ($attempt in 1..6) {
        try { $r = Get-AcsRequest $probeUrl 60; $acs.probe = "ok in $($r.seconds) s on attempt $attempt"; Write-Host "probe ok in $($r.seconds) s"; $probeOk = $true; break }
        catch {
            $acs.probe = "failed: $_"
            Write-Host "probe failed (attempt $attempt): $_"
            if ("$_" -match "Missing Key" -or "$_" -match "invalid key" -or "$_" -match "unknown key") { Write-Host "the key may not be activated yet (the activation link arrives by email); run this mode again in a few minutes"; $acs.finished = (Get-Date).ToUniversalTime().ToString("o"); Save-Status "acs" $acs; Stop-Transcript | Out-Null; return }
            if ($attempt -lt 6) { Start-Sleep -Seconds (30 * $attempt) }
        }
    }
    if (-not $probeOk) { Write-Host "the probe never answered; continuing anyway, each request retries on its own" }
    $latestYear = $null
    $yearEnd = if ($LastYear -gt 0) { $LastYear } else { $now.Year - 1 }
    foreach ($y in $FirstYear..$yearEnd) {
        if ($y -eq 2020) { $acs.years["2020"] = "no one year release (pandemic); gap carried as a gap"; continue }
        $yDir = Join-Path $dirs.acs "$y"
        New-Item -ItemType Directory -Force -Path $yDir | Out-Null
        $yearStatus = [ordered]@{}
        $anyOk = $false
        $consecutive = 0
        $names = @($tables.Keys) + ($usTables | ForEach-Object { "$($_)_us" })
        foreach ($t in $names) {
            $isUs = $t.EndsWith("_us")
            $table = $t -replace "_us$", ""
            $cells = $tables[$table]
            # B25074 carried seven cells per income group (five rent bands) through the 2013 release and nine from 2014.
            if ($table -eq "B25074" -and $y -le 2013) { $cells = 50 }
            $forPart = if ($isUs) { "us:1" } else { $geo }
            $dest = Join-Path $yDir "$t.json"
            if (Test-Path $dest) {
                if ((Get-Item $dest).Length -gt 200) { $yearStatus[$t] = "kept"; $anyOk = $true; continue }
            }
            if ($consecutive -ge 3) { $yearStatus[$t] = "skipped after three consecutive failures"; continue }
            $vars = @()
            foreach ($i in 1..$cells) { $vars += ("{0}_{1:D3}E" -f $table, $i); $vars += ("{0}_{1:D3}M" -f $table, $i) }
            $ok = $false; $last = ""; $notFound = $false
            # 1. api.census.gov with explicit variables (at most 50 per request, so wide tables are split);
            #    a transient answer (timed out, busy, maintenance, a non table body) is tried three times.
            try {
                $acs.requests += 1
                $chunks = @()
                for ($c = 0; $c -lt $vars.Count; $c += 48) { $chunks += ,($vars[$c..([Math]::Min($c + 47, $vars.Count - 1))]) }
                $merged = $null
                foreach ($chunk in $chunks) {
                    $url = "https://api.census.gov/data/$y/acs/acs1?get=NAME,$($chunk -join ',')&for=$forPart$keyPart"
                    $rows = $null
                    $attempt = 0
                    while ($true) {
                        $attempt += 1
                        try {
                            $r = Get-AcsRequest $url 120
                            $acs.timings += "$y $t census $($r.seconds)s"
                            $rows = $r.content | ConvertFrom-Json
                            if (-not $rows -or $rows.Count -lt 2) { throw "no rows" }
                            if ($rows[0] -isnot [array]) { throw "not a table: $($r.content.Substring(0, [Math]::Min(80, $r.content.Length)))" }
                            break
                        } catch {
                            $msg = "$_"
                            $transient = ($msg -match "timed out" -or $msg -match "busy" -or $msg -match "maintenance" -or $msg -match "not a table" -or $msg -match "no rows" -or $msg -match "50[023]")
                            if ($transient -and $attempt -lt 3) { Write-Host "  $y $t census api: transient ($($msg.Substring(0, [Math]::Min(60, $msg.Length)))), retry $attempt"; Start-Sleep -Seconds (10 * $attempt); continue }
                            throw
                        }
                    }
                    if ($null -eq $merged) { $merged = $rows } else {
                        # join on the trailing geography column: same order is not guaranteed, so key by the last column,
                        # and keep that column last so a third chunk can join the same way (a data value can be null and
                        # a null hashtable key is an error; the geography never is).
                        $keyIndex = $rows[0].Count - 1
                        $lookup = @{}
                        for ($i = 1; $i -lt $rows.Count; $i++) { $lookup[[string]$rows[$i][$keyIndex]] = $rows[$i] }
                        $mk = $merged[0].Count - 1
                        $newHeader = @($merged[0][0..($mk - 1)]) + @($rows[0][1..($rows[0].Count - 2)]) + @($merged[0][$mk])
                        $out = @(,$newHeader)
                        $width = $rows[0].Count - 2
                        for ($i = 1; $i -lt $merged.Count; $i++) {
                            $k = [string]$merged[$i][$mk]; $extra = $lookup[$k]
                            $values = if ($null -eq $extra) { @("") * $width } else { @($extra[1..($extra.Count - 2)]) }
                            $out += ,(@($merged[$i][0..($mk - 1)]) + @($values) + @($merged[$i][$mk]))
                        }
                        $merged = $out
                    }
                }
                $json = ConvertTo-Json -InputObject $merged -Depth 3 -Compress
                [IO.File]::WriteAllText($dest, $json)
                $yearStatus[$t] = "ok census $($merged.Count - 1) rows"
                $ok = $true; $anyOk = $true; $consecutive = 0
            } catch {
                $last = "$_"
                if ($last -match "404" -or $last -match "Not Found" -or $last -match "unknown variable" -or $last -match "error: unknown") { $notFound = $true }
                Write-Host "  $y $t census api: $($last.Substring(0, [Math]::Min(100, $last.Length)))"
            }
            # 2. Census Reporter mirror, same tables, all metros in one request (not for the national rows)
            if (-not $ok -and -not $isUs) {
                try {
                    $acs.requests += 1
                    $url = "https://api.censusreporter.org/1.0/data/show/acs${y}_1yr?table_ids=$table&geo_ids=310|01000US"
                    $r = Get-AcsRequest $url 120
                    $acs.timings += "$y $t reporter $($r.seconds)s"
                    $payload = $r.content | ConvertFrom-Json
                    if (-not $payload.data) { throw "no data block" }
                    [IO.File]::WriteAllText($dest, $r.content)
                    $yearStatus[$t] = "ok reporter"
                    $ok = $true; $anyOk = $true; $consecutive = 0
                } catch {
                    $last2 = "$_"
                    Write-Host "  $y $t census reporter: $($last2.Substring(0, [Math]::Min(100, $last2.Length)))"
                    if ($last2 -match "404" -or $last2 -match "Not Found" -or $last2 -match "isn't supported") { $notFound = $true }
                    $last = "$last | reporter: $last2"
                }
            }
            if (-not $ok) {
                $short = ($last -replace '\s+', ' ')
                if ($short.Length -gt 200) { $short = $short.Substring(0, 200) }
                $yearStatus[$t] = "missing: $short"
                $acs.failures += "$y $t"
                if (-not $notFound) { $consecutive += 1 }
            }
            Start-Sleep -Milliseconds 300
        }
        $acs.years["$y"] = $yearStatus
        if ($anyOk) { $latestYear = $y }
        Write-Host "  acs $y done ($(($yearStatus.Values | Where-Object { $_ -notmatch '^missing' -and $_ -notmatch '^skipped' }).Count) tables)"
        Save-Status $(if ($LastYear -gt 0) { "acs-$FirstYear-$LastYear" } else { "acs" }) $acs
    }
    $acs.latest_year_with_data = $latestYear
    $acs.finished = (Get-Date).ToUniversalTime().ToString("o")
    $acs.minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
    Save-Status $(if ($LastYear -gt 0) { "acs-$FirstYear-$LastYear" } else { "acs" }) $acs
    Write-Host "fetch acs finished in $($acs.minutes) minutes"
    Stop-Transcript | Out-Null
}

$hmdaSource = @'
using System;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Collections.Generic;

public static class HmdaFilter
{
    public static List<string> SplitCsv(string line)
    {
        var result = new List<string>(120);
        if (line.IndexOf('"') < 0) { result.AddRange(line.Split(',')); return result; }
        var sb = new StringBuilder();
        bool inQuotes = false;
        for (int i = 0; i < line.Length; i++)
        {
            char c = line[i];
            if (inQuotes)
            {
                if (c == '"')
                {
                    if (i + 1 < line.Length && line[i + 1] == '"') { sb.Append('"'); i++; }
                    else { inQuotes = false; }
                }
                else { sb.Append(c); }
            }
            else
            {
                if (c == ',') { result.Add(sb.ToString()); sb.Length = 0; }
                else if (c == '"') { inQuotes = true; }
                else { sb.Append(c); }
            }
        }
        result.Add(sb.ToString());
        return result;
    }

    static string Escape(string f)
    {
        if (f.IndexOfAny(new char[] { ',', '"', '\n', '\r' }) < 0) { return f; }
        return "\"" + f.Replace("\"", "\"\"") + "\"";
    }

    public static long[] Run(string zipPath, string outDir, string[] keepCols, long rowsPerPart, string actionCol, string purposeCol, string[] purposes, string headerOut)
    {
        Directory.CreateDirectory(outDir);
        long total = 0, kept = 0, malformed = 0, parts = 0, missingCols = 0;
        using (var archive = ZipFile.OpenRead(zipPath))
        {
            ZipArchiveEntry entry = null;
            foreach (var e in archive.Entries) { if (e.FullName.EndsWith(".csv", StringComparison.OrdinalIgnoreCase)) { entry = e; break; } }
            if (entry == null) { throw new Exception("no csv entry in " + zipPath); }
            using (var stream = entry.Open())
            using (var reader = new StreamReader(stream, Encoding.UTF8, true, 1 << 20))
            {
                string header = reader.ReadLine();
                if (header == null) { throw new Exception("empty csv in " + zipPath); }
                File.WriteAllText(headerOut, header);
                var cols = SplitCsv(header);
                var index = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
                for (int i = 0; i < cols.Count; i++) { var name = cols[i].Trim().Trim('"'); if (!index.ContainsKey(name)) { index[name] = i; } }
                int actionIdx, purposeIdx;
                if (!index.TryGetValue(actionCol, out actionIdx)) { throw new Exception("no column " + actionCol); }
                if (!index.TryGetValue(purposeCol, out purposeIdx)) { throw new Exception("no column " + purposeCol); }
                var keepIdx = new int[keepCols.Length];
                for (int k = 0; k < keepCols.Length; k++) { int ix; if (index.TryGetValue(keepCols[k], out ix)) { keepIdx[k] = ix; } else { keepIdx[k] = -1; missingCols++; } }
                var purposeSet = new HashSet<string>(purposes);
                int maxIdx = Math.Max(actionIdx, purposeIdx);
                foreach (var ix in keepIdx) { if (ix > maxIdx) { maxIdx = ix; } }
                StreamWriter writer = null;
                long inPart = 0;
                var outHeader = string.Join(",", keepCols);
                var sb = new StringBuilder(1024);
                string line;
                while ((line = reader.ReadLine()) != null)
                {
                    total++;
                    if (line.Length == 0) { continue; }
                    var f = SplitCsv(line);
                    if (f.Count <= maxIdx) { malformed++; continue; }
                    if (f[actionIdx] != "1") { continue; }
                    if (!purposeSet.Contains(f[purposeIdx])) { continue; }
                    if (writer == null || inPart >= rowsPerPart)
                    {
                        if (writer != null) { writer.Flush(); writer.Dispose(); }
                        parts++;
                        var partPath = Path.Combine(outDir, string.Format("lar_part{0:D3}.csv.gz", parts));
                        var fs = new FileStream(partPath, FileMode.Create, FileAccess.Write, FileShare.None, 1 << 20);
                        var gz = new GZipStream(fs, CompressionLevel.Optimal);
                        writer = new StreamWriter(gz, new UTF8Encoding(false), 1 << 20);
                        writer.Write(outHeader); writer.Write('\n');
                        inPart = 0;
                    }
                    sb.Length = 0;
                    for (int k = 0; k < keepIdx.Length; k++)
                    {
                        if (k > 0) { sb.Append(','); }
                        if (keepIdx[k] >= 0) { sb.Append(Escape(f[keepIdx[k]])); }
                    }
                    writer.Write(sb.ToString()); writer.Write('\n');
                    kept++; inPart++;
                }
                if (writer != null) { writer.Flush(); writer.Dispose(); }
            }
        }
        return new long[] { total, kept, malformed, parts, missingCols };
    }
}
'@

function Run-Hmda {
    $started = Get-Date
    $now = $started.ToUniversalTime()
    Start-Transcript -Path (Join-Path $root "fetch-log-hmda.txt") -Append | Out-Null
    Write-Host "fetch hmda started $($now.ToString('o')) on $env:COMPUTERNAME"
    Add-Type -TypeDefinition $hmdaSource -ReferencedAssemblies @("System.IO.Compression", "System.IO.Compression.FileSystem") -ErrorAction Stop
    $zipDir = Join-Path $dirs.hmda "zips"
    New-Item -ItemType Directory -Force -Path $zipDir | Out-Null
    $drive = (Get-Item $root).PSDrive
    Write-Host "free space on $($drive.Name): $([math]::Round($drive.Free / 1GB, 1)) GB"
    # Columns kept. Race, ethnicity and sex fields are not loaded by design (fair lending is not this build).
    $keep = @("activity_year", "lei", "derived_msa-md", "state_code", "county_code", "census_tract", "action_taken", "purchaser_type", "loan_type", "loan_purpose", "lien_status", "reverse_mortgage", "open-end_line_of_credit", "business_or_commercial_purpose", "loan_amount", "loan_to_value_ratio", "interest_rate", "rate_spread", "hoepa_status", "total_loan_costs", "origination_charges", "discount_points", "lender_credits", "loan_term", "intro_rate_period", "property_value", "construction_method", "occupancy_type", "total_units", "income", "debt_to_income_ratio", "applicant_age", "applicant_age_above_62", "co-applicant_age", "ffiec_msa_md_median_family_income", "tract_to_msa_income_percentage", "tract_population", "tract_owner_occupied_units")
    $status = [ordered]@{ mode = "hmda"; machine = $env:COMPUTERNAME; started = $now.ToString("o"); filter = "action_taken = 1 and loan_purpose in (1, 31, 32) at fetch; occupancy_type = 1 applied at ingest"; columns = $keep; years = [ordered]@{} }
    foreach ($y in 2018..($now.Year - 1)) {
        $yDir = Join-Path $dirs.hmda "$y"
        $summary = Join-Path $yDir "summary.json"
        if (Test-Path $summary) { $status.years["$y"] = (Get-Content $summary -Raw | ConvertFrom-Json); Write-Host "hmda ${y}: have summary"; continue }
        $zip = Join-Path $zipDir "${y}_public_lar_csv.zip"
        if (-not (Test-Zip $zip 100000000)) {
            $ok = $false
            foreach ($url in @("https://files.ffiec.cfpb.gov/static-data/snapshot/$y/${y}_public_lar_csv.zip", "https://s3.amazonaws.com/cfpb-hmda-public/prod/snapshot-data/$y/${y}_public_lar_csv.zip")) {
                for ($attempt = 1; $attempt -le 4 -and -not $ok; $attempt++) {
                    Write-Host "hmda ${y}: $url (attempt $attempt)"
                    $code = Get-File $url $zip $agent $true
                    if ($code -eq 0 -and (Test-Zip $zip 100000000)) { $ok = $true; break }
                    if ($code -eq 22) { break }
                    Start-Sleep -Seconds 30
                }
                if ($ok) { break }
            }
            if (-not $ok) { $status.years["$y"] = [ordered]@{ status = "not available" }; Write-Host "  not available"; continue }
            Write-Host "  ok $((Get-Item $zip).Length) bytes"
        } else { Write-Host "hmda ${y}: have zip" }
        Write-Host "hmda ${y}: filtering"
        $t0 = Get-Date
        $counts = $null
        try {
            $counts = [HmdaFilter]::Run($zip, $yDir, [string[]]$keep, 2000000, "action_taken", "loan_purpose", [string[]]@("1", "31", "32"), (Join-Path $yDir "source_header.txt"))
        } catch {
            Write-Host "  the zip did not read cleanly ($_); it will be fetched again on the next run"
            $counts = $null
        }
        if ($null -eq $counts -or $counts[0] -lt 4000000) {
            # A snapshot year holds well over four million records; fewer means a truncated or interleaved download.
            $bad = Join-Path $zipDir "corrupt_${y}_$(Get-Date -Format yyyyMMddHHmmss).zip"
            Move-Item -Force $zip $bad
            Get-ChildItem $yDir -Filter "lar_part*.csv.gz" | Remove-Item -Force
            $status.years["$y"] = [ordered]@{ status = "download corrupt, set aside as $(Split-Path -Leaf $bad); run again" }
            Write-Host "  rows read: $(if ($counts) { $counts[0] } else { 'none' }); set aside as $bad"
            Save-Status "hmda" $status
            continue
        }
        $ySummary = [ordered]@{ status = "filtered"; zip = "hmda/zips/${y}_public_lar_csv.zip"; zip_bytes = (Get-Item $zip).Length; rows_total = $counts[0]; rows_kept = $counts[1]; rows_malformed = $counts[2]; parts = $counts[3]; columns_missing = $counts[4]; filter_minutes = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1); part_files = @(Get-ChildItem $yDir -Filter "*.csv.gz" | Sort-Object Name | ForEach-Object { @{ name = $_.Name; bytes = $_.Length } }) }
        $ySummary | ConvertTo-Json -Depth 4 | Set-Content -Path $summary -Encoding UTF8
        $status.years["$y"] = $ySummary
        Write-Host "  rows $($counts[0]) kept $($counts[1]) parts $($counts[3]) in $($ySummary.filter_minutes) min"
        if ($DeleteZips) { Remove-Item $zip -Force }
        Save-Status "hmda" $status
    }
    $status.finished = (Get-Date).ToUniversalTime().ToString("o")
    $status.minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
    Save-Status "hmda" $status
    Write-Host "fetch hmda finished in $($status.minutes) minutes"
    Stop-Transcript | Out-Null
}

$lockName = if ($Mode -eq "acs" -and $LastYear -gt 0) { "fetch-acs-$FirstYear-$LastYear.lock" } else { "fetch-$Mode.lock" }
$lockPath = Join-Path $root $lockName
if (Test-Path $lockPath) {
    $age = (Get-Date) - (Get-Item $lockPath).LastWriteTime
    if ($age.TotalHours -lt 6) { Write-Host "another fetch-data.ps1 $Mode run started $([math]::Round($age.TotalMinutes)) minutes ago (lock: $lockPath); not starting a second one"; exit 2 }
}
Set-Content -Path $lockPath -Value "$PID $(Get-Date -Format o)"
try {
if ($Mode -eq "core") { Run-Core }
elseif ($Mode -eq "acs") { Run-Acs }
elseif ($Mode -eq "hmda") { Run-Hmda }
elseif ($Mode -eq "all") { Run-Core; Run-Hmda; Run-Acs }
else { throw "unknown mode $Mode (use all, core, acs or hmda)" }
} finally { Remove-Item $lockPath -Force -ErrorAction SilentlyContinue }

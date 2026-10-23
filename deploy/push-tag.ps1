# Push the release tag after the commits are on GitHub (the tag goes up last, once main is there).
#
#   powershell -ExecutionPolicy Bypass -File "C:\Project FullTime\doorstep\deploy\push-tag.ps1"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repo
$tag = (git describe --tags --abbrev=0 2>$null)
if (-not $tag) { throw "no tag to push" }
git push origin $tag 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { throw "git push origin $tag failed" }
Write-Host "pushed $tag"

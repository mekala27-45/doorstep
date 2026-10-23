# Push main to GitHub from the Windows machine that holds the sign in (the build sandbox has no credential
# for this repository). Run from the Git GUI Tools menu; the output shows in the tool window.
#
#   powershell -ExecutionPolicy Bypass -File "C:\Project FullTime\doorstep\deploy\push-main.ps1"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repo
# Git GUI exports its own repository as GIT_DIR to every tool it launches, so a tool started from
# another repository's window would push that repository instead of this one (found on 23 Oct 2026,
# when the turnaround window reported turnaround's tag as already up to date). Clear both first.
Remove-Item Env:GIT_DIR -ErrorAction SilentlyContinue
Remove-Item Env:GIT_WORK_TREE -ErrorAction SilentlyContinue
git remote -v
git log --oneline -1
git push origin main 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { throw "git push origin main failed" }
Write-Host "pushed main"

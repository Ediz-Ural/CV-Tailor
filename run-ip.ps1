# run-ip.ps1
# Tek bir iş paketi prompt'unu TEMIZ (cache'siz) bir Codex oturumunda calistirir.
# Her cagri yeni bir codex process'idir => oturum hafizasi / cache tasinmaz.
#
# Kullanim:
#   .\run-ip.ps1 -Prompt prompts\IP-0.1-repo-iskelet.md
#   .\run-ip.ps1 -Prompt prompts\IP-1.2-auth-jwt.md
#
# Not: Codex CLI kurulu olmali (npm i -g @openai/codex) ve PATH'te olmali.

param(
    [Parameter(Mandatory = $true)]
    [string]$Prompt
)

$ErrorActionPreference = "Stop"

# Repo kokune sabitlen (script nerede ise orasi calisma alani).
$workspace = $PSScriptRoot
$promptPath = Join-Path $workspace $Prompt

if (-not (Test-Path $promptPath)) {
    Write-Error "Prompt dosyasi bulunamadi: $promptPath"
    exit 1
}

$promptText = Get-Content -Path $promptPath -Raw

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " CODEX (temiz oturum) -> $Prompt" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# Her calistirma yeni bir process => onceki oturumdan cache/state tasinmaz.
# --cd ile repo koku calisma dizini olarak verilir.
codex exec --cd $workspace $promptText

$code = $LASTEXITCODE
Write-Host "----------------------------------------------" -ForegroundColor DarkGray
Write-Host "Codex oturumu kapandi. Cikis kodu: $code" -ForegroundColor Cyan
exit $code

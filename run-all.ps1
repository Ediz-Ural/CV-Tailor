# run-all.ps1
# Tum is paketlerini DOGRU SIRAYLA, her birini AYRI ve TEMIZ bir Codex oturumunda calistirir.
# Her paketten sonra ilgili log dosyasinin "DURUM: TAMAMLANDI" icerdigini kontrol eder.
# Bir paket tamamlanmazsa zincir DURUR (bir sonrakine gecmez).
#
# Kullanim:
#   .\run-all.ps1                 # bastan sona
#   .\run-all.ps1 -StartAt IP-2.1 # belirli paketten itibaren

param(
    [string]$StartAt = ""
)

$ErrorActionPreference = "Stop"
$workspace = $PSScriptRoot

# Calistirma sirasi (bagimlilik sirasina gore). Slug'lar prompts/ ve logs/ ile eslesir.
$order = @(
    "IP-0.1-repo-iskelet",
    "IP-0.2-docker-altyapi",
    "IP-0.3-backend-kurulum",
    "IP-0.4-frontend-kurulum",
    "IP-1.1-db-sema",
    "IP-1.2-auth-jwt",
    "IP-1.3-profil-crud",
    "IP-1.4-frontend-auth",
    "IP-2.0-llm-embedding",
    "IP-2.1-manuel-havuz",
    "IP-2.2-pdf-parser",
    "IP-2.3-github-analiz",
    "IP-2.4-itemextractor-onay",
    "IP-2.5-graph1-orkestrasyon",
    "IP-2.6-frontend-havuz",
    "IP-3.1-jobparser",
    "IP-3.2-selector",
    "IP-3.3-cvtailor",
    "IP-3.4-evaluator",
    "IP-3.5-typst-render",
    "IP-3.6-graph2-orkestrasyon",
    "IP-3.7-frontend-cv-sonuc",
    "IP-4.1-kvkk-riza",
    "IP-4.2-hesap-silme",
    "IP-4.3-veri-guvenlik",
    "IP-5.1-i18n",
    "IP-5.2-test-kalite",
    "IP-5.3-gozlemlenebilirlik-dagitim"
)

$started = ($StartAt -eq "")

foreach ($slug in $order) {
    if (-not $started) {
        if ($slug -like "$StartAt*") { $started = $true } else { continue }
    }

    $prompt = "prompts\$slug.md"
    Write-Host ""
    Write-Host "########## BASLIYOR: $slug ##########" -ForegroundColor Yellow

    & (Join-Path $workspace "run-ip.ps1") -Prompt $prompt

    # Tamamlanma kontrolu: log dosyasi var mi ve DURUM: TAMAMLANDI iceriyor mu?
    $logPath = Join-Path $workspace "logs\$slug.md"
    if (-not (Test-Path $logPath)) {
        Write-Host "DURDU: $slug icin log dosyasi olusmadi ($logPath). Zincir durduruluyor." -ForegroundColor Red
        exit 1
    }
    $logContent = Get-Content -Path $logPath -Raw
    if ($logContent -notmatch "DURUM:\s*TAMAMLANDI") {
        Write-Host "DURDU: $slug TAMAMLANDI degil. Logu incele: $logPath" -ForegroundColor Red
        exit 1
    }

    Write-Host "TAMAM: $slug dogrulandi (log: TAMAMLANDI)." -ForegroundColor Green
}

Write-Host ""
Write-Host "Tum is paketleri sirayla tamamlandi." -ForegroundColor Green

# dev.ps1
# CV-Tailor'i tek komutla ayaga kaldirir: .env'i hazirlar, PostgreSQL'i Docker'da
# baslatir, migration'lari calistirir, backend ve frontend'i ayri pencerelerde
# acar ve hazir olunca tarayiciyi http://localhost:5173 adresine yollar.
#
# Kullanim:
#   .\dev.ps1              # her seyi kur ve baslat
#   .\dev.ps1 -SkipInstall # bagimlilik kurulumunu atla (daha hizli yeniden baslatma)
#   .\dev.ps1 -NoBrowser   # tarayiciyi acma
#   .\dev.ps1 -Stop        # baslatilan her seyi (DB dahil) durdur

[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [switch]$NoBrowser,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$root = $PSScriptRoot
$envPath = Join-Path $root ".env"
$examplePath = Join-Path $root ".env.example"
$composeFile = Join-Path $root "infra\docker-compose.yml"
$toolsDir = Join-Path $root ".tools"

function Write-Step([string]$text) { Write-Host $text -ForegroundColor Cyan -NoNewline }
function Write-Ok([string]$text = "tamam") { Write-Host " $text" -ForegroundColor Green }
function Write-Warn([string]$text) { Write-Host "     ! $text" -ForegroundColor Yellow }
function Write-Fail([string]$text) { Write-Host " HATA" -ForegroundColor Red; Write-Host "     $text" -ForegroundColor Red }

# Fernet anahtari = 32 rastgele baytin url-safe base64'u; JWT gizi = 36 baytin
# padding'siz hali. Ikisi de PowerShell icinde uretilir, Python gerekmez.
function New-UrlSafeBase64([int]$byteCount, [switch]$StripPadding) {
    $bytes = New-Object byte[] $byteCount
    $rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $value = [Convert]::ToBase64String($bytes).Replace('+', '-').Replace('/', '_')
    if ($StripPadding) { $value = $value.TrimEnd('=') }
    return $value
}

function Read-EnvFile([string]$path) {
    $map = @{}
    if (-not (Test-Path $path)) { return $map }
    foreach ($line in Get-Content -Path $path) {
        $trimmed = $line.Trim()
        if ($trimmed -eq "" -or $trimmed.StartsWith("#")) { continue }
        $index = $trimmed.IndexOf("=")
        if ($index -lt 1) { continue }
        $map[$trimmed.Substring(0, $index).Trim()] = $trimmed.Substring($index + 1).Trim()
    }
    return $map
}

function Set-EnvValue([string]$path, [string]$key, [string]$value) {
    $lines = @(Get-Content -Path $path)
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^\s*$([regex]::Escape($key))\s*=") {
            $lines[$i] = "$key=$value"
            $found = $true
            break
        }
    }
    if (-not $found) { $lines += "$key=$value" }
    # .env'i BOM'suz yazmak sart: BOM ilk anahtarin adina yapisir ve hem docker
    # compose hem pydantic o satiri okuyamaz.
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($path, [string[]]$lines, $utf8NoBom)
}

# Native komutlarin stderr'i PowerShell 5.1'de ErrorRecord'a sarilir ve
# ErrorActionPreference=Stop altinda scripti dusurur; cikis kodunu kendimiz
# kontrol edebilmek icin native cagrilari buradan gecirir.
function Invoke-Native([scriptblock]$command) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $command 2>&1 | Out-Null } finally { $ErrorActionPreference = $previous }
    return $LASTEXITCODE
}

# Docker icinde uretilmis bir .venv Windows'ta calismaz ve `uv sync` onu silmeye
# calisirken lib64 symlink'inde "Erisim engellendi" ile duser. Yabanci venv'i
# bastan temizleriz.
function Remove-ForeignVenv([string]$backendDir) {
    $venv = Join-Path $backendDir ".venv"
    $config = Join-Path $venv "pyvenv.cfg"
    if (-not (Test-Path $config)) { return $false }
    $match = Select-String -Path $config -Pattern "^home\s*=\s*(.+)$" | Select-Object -First 1
    if (-not $match) { return $false }
    if ($match.Matches.Groups[1].Value.Trim() -match "^[A-Za-z]:") { return $false }

    # lib64/bin symlink'leri Remove-Item ile silinemez; reparse point'i once
    # rmdir kaldirir.
    foreach ($link in @("lib64", "bin")) {
        $path = Join-Path $venv $link
        if (Test-Path $path) { cmd /c rmdir "$path" | Out-Null }
    }
    Remove-Item $venv -Recurse -Force -ErrorAction SilentlyContinue
    return -not (Test-Path $venv)
}

function Test-Command([string]$name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Wait-Until([scriptblock]$check, [int]$timeoutSeconds, [string]$label) {
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try { if (& $check) { return $true } } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

# Portu dinleyen sureci agac olarak indirir. `uvicorn --reload` isi bir
# multiprocessing cocuguna verir; sadece parent'i oldurmek portu dinleyen
# cocugu hayatta birakir ve bir sonraki baslatma "zaten calisiyor" sanir.
function Stop-ProcessTree([int]$processId) {
    Get-CimInstance Win32_Process -Filter "ParentProcessId = $processId" |
        ForEach-Object { Stop-ProcessTree $_.ProcessId }
    try { Stop-Process -Id $processId -Force -ErrorAction Stop } catch { }
}

function Stop-Port([int]$port) {
    $owners = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($owner in $owners) {
        Write-Host "  :$port -> PID $owner sonlandiriliyor" -ForegroundColor DarkGray
        Stop-ProcessTree $owner
    }
    return $owners.Count
}

# ---------------------------------------------------------------- -Stop
if ($Stop) {
    Write-Host "Calisan surecler durduruluyor..." -ForegroundColor Cyan
    $stopped = (Stop-Port 8000) + (Stop-Port 5173)
    if ($stopped -eq 0) { Write-Host "  dinleyen backend/frontend yok" -ForegroundColor DarkGray }
    Invoke-Native { docker compose --env-file $envPath -f $composeFile stop db } | Out-Null
    Write-Host "Durduruldu." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "  CV-Tailor gelistirme ortami" -ForegroundColor White
Write-Host "  ---------------------------" -ForegroundColor DarkGray
Write-Host ""

# ---------------------------------------------------------------- 1/6 .env
Write-Step "[1/6] .env hazirlaniyor..."
$created = $false
if (-not (Test-Path $envPath)) {
    if (-not (Test-Path $examplePath)) { Write-Fail ".env.example bulunamadi."; exit 1 }
    Copy-Item $examplePath $envPath
    $created = $true
}

# Sadece hala ornek/bos olan degerler doldurulur; kendi girdiginiz hicbir sey
# ezilmez. Placeholder'lar herkese acik oldugu icin birakilamaz.
$placeholders = @(
    "change-me",
    "change-me-to-a-long-random-secret",
    "development-only-change-me",
    "replace-with-fernet-key-from-python-cryptography",
    "replace-with-github-client-id",
    "replace-with-github-client-secret",
    ""
)
$envMap = Read-EnvFile $envPath
$filled = @()

function Needs-Value([string]$key) {
    return (-not $envMap.ContainsKey($key)) -or ($placeholders -contains $envMap[$key])
}

if (Needs-Value "JWT_SECRET") {
    Set-EnvValue $envPath "JWT_SECRET" (New-UrlSafeBase64 36 -StripPadding)
    $filled += "JWT_SECRET"
}
foreach ($key in @("CREDENTIAL_ENCRYPTION_KEY", "GITHUB_TOKEN_ENCRYPTION_KEY")) {
    if (Needs-Value $key) {
        Set-EnvValue $envPath $key (New-UrlSafeBase64 32)
        $filled += $key
    }
}
if (Needs-Value "POSTGRES_PASSWORD") {
    Set-EnvValue $envPath "POSTGRES_PASSWORD" "cv_tailor_dev"
    $filled += "POSTGRES_PASSWORD"
}

$envMap = Read-EnvFile $envPath
$pgUser = if ($envMap["POSTGRES_USER"]) { $envMap["POSTGRES_USER"] } else { "cv_tailor" }
$pgPass = if ($envMap["POSTGRES_PASSWORD"]) { $envMap["POSTGRES_PASSWORD"] } else { "cv_tailor_dev" }
$pgDb = if ($envMap["POSTGRES_DB"]) { $envMap["POSTGRES_DB"] } else { "cv_tailor" }
$pgPort = if ($envMap["POSTGRES_PORT"]) { $envMap["POSTGRES_PORT"] } else { "5432" }

# .env'deki DATABASE_URL compose icin `db` host'unu gosterir; yerelde calisan
# backend ayni veritabanina localhost uzerinden baglanir. .env'i bozmamak icin
# deger dosyaya yazilmaz, sadece backend surecine ortam degiskeni olarak gecer
# (pydantic-settings'te ortam degiskeni .env'in onune gecer).
$localDatabaseUrl = "postgresql+psycopg://${pgUser}:${pgPass}@localhost:${pgPort}/${pgDb}"

if ($created) { Write-Ok "olusturuldu" } elseif ($filled.Count -gt 0) { Write-Ok "guncellendi" } else { Write-Ok "mevcut" }
if ($filled.Count -gt 0) { Write-Warn ("uretilen degerler: " + ($filled -join ", ")) }

# ---------------------------------------------------------------- 2/6 DB
Write-Step "[2/6] PostgreSQL (docker) baslatiliyor..."
if (-not (Test-Command "docker")) {
    Write-Fail "Docker bulunamadi. Docker Desktop kurup calistirin: https://docs.docker.com/desktop/"
    exit 1
}
if ((Invoke-Native { docker info }) -ne 0) {
    Write-Fail "Docker calismiyor. Docker Desktop'i acip tekrar deneyin."
    exit 1
}
if ((Invoke-Native { docker compose --env-file $envPath -f $composeFile up -d db }) -ne 0) {
    Write-Fail "docker compose up db basarisiz oldu."
    exit 1
}

$dbReady = Wait-Until {
    (Invoke-Native { docker compose --env-file $envPath -f $composeFile exec -T db pg_isready -U $pgUser -d $pgDb }) -eq 0
} 90 "db"
if (-not $dbReady) { Write-Fail "Veritabani 90 saniyede hazir olmadi."; exit 1 }
Write-Ok "hazir"

# ---------------------------------------------------------------- 3/6 backend deps
Write-Step "[3/6] Backend bagimliliklari (uv sync)..."
# uv kendini %USERPROFILE%\.local\bin altina kurar ve PATH guncellemesi ancak
# yeni bir kabukta gorunur; kurulu oldugu halde tekrar indirmemek icin once
# oraya bakariz.
$uvBin = Join-Path (Join-Path $env:USERPROFILE ".local") "bin"
if ((Test-Path (Join-Path $uvBin "uv.exe")) -and ($env:Path -notlike "*$uvBin*")) {
    $env:Path = "$uvBin;$env:Path"
}
if (-not (Test-Command "uv")) {
    Write-Host ""
    Write-Warn "uv bulunamadi, kuruluyor (astral.sh/uv)"
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$uvBin;$env:Path"
    if (-not (Test-Command "uv")) {
        Write-Fail "uv kurulamadi. Elle kurun: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
    Write-Step "[3/6] Backend bagimliliklari (uv sync)..."
}
if ($SkipInstall) {
    Write-Ok "atlandi"
} else {
    if (Remove-ForeignVenv (Join-Path $root "backend")) {
        Write-Host ""
        Write-Warn "Docker icinde uretilmis .venv silindi, yenisi kuruluyor"
        Write-Step "[3/6] Backend bagimliliklari (uv sync)..."
    }
    Push-Location (Join-Path $root "backend")
    try {
        if ((Invoke-Native { uv sync }) -ne 0) {
            Write-Fail "uv sync basarisiz oldu. 'cd backend; uv sync' ile ciktiyi gorun."
            exit 1
        }
    } finally { Pop-Location }
    Write-Ok
}

# Typst olmadan pipeline typst_renderer adiminda duser. PATH'te yoksa surumu
# .tools/ altina indirip yalnizca bu calistirma icin kullaniriz.
$typstBinary = "typst"
if (-not (Test-Command "typst")) {
    $localTypst = Join-Path $toolsDir "typst\typst.exe"
    if (Test-Path $localTypst) {
        $typstBinary = $localTypst
    } else {
        Write-Host "     Typst indiriliyor (PDF uretimi icin gerekli)..." -ForegroundColor DarkGray -NoNewline
        try {
            New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
            $zip = Join-Path $toolsDir "typst.zip"
            Invoke-WebRequest -Uri "https://github.com/typst/typst/releases/latest/download/typst-x86_64-pc-windows-msvc.zip" -OutFile $zip -UseBasicParsing
            Expand-Archive -Path $zip -DestinationPath $toolsDir -Force
            Remove-Item $zip -Force
            $found = Get-ChildItem -Path $toolsDir -Filter "typst.exe" -Recurse | Select-Object -First 1
            if ($found) {
                New-Item -ItemType Directory -Force -Path (Split-Path $localTypst) | Out-Null
                Copy-Item $found.FullName $localTypst -Force
                $typstBinary = $localTypst
                Write-Host " tamam" -ForegroundColor Green
            } else {
                Write-Host " bulunamadi" -ForegroundColor Yellow
            }
        } catch {
            Write-Host " basarisiz" -ForegroundColor Yellow
            Write-Warn "Typst kurulamadi; CV uretimi PDF adiminda duser. Elle kurun: https://github.com/typst/typst"
        }
    }
}

# ---------------------------------------------------------------- 4/6 migrations
Write-Step "[4/6] Migration'lar (alembic upgrade head)..."
Push-Location (Join-Path $root "backend")
try {
    $env:DATABASE_URL = $localDatabaseUrl
    if ((Invoke-Native { uv run alembic upgrade head }) -ne 0) {
        Write-Fail "Migration basarisiz. 'cd backend; uv run alembic upgrade head' ile ciktiyi gorun."
        exit 1
    }
} finally { Pop-Location }
Write-Ok

# ---------------------------------------------------------------- 5/6 backend
Write-Step "[5/6] Backend :8000 ..."
$backendHealthy = $false
try {
    $existing = Invoke-RestMethod "http://localhost:8000/health" -TimeoutSec 3
    if ($existing.status) { $backendHealthy = $true }
} catch { }

if ($backendHealthy) {
    Write-Ok "zaten calisiyor"
} else {
    # Docker imajindaki yollar (/app/storage, /var/cache/fastembed) Windows'ta
    # yok; yerel calistirma icin repo altindaki dizinlere yonlendirilir.
    $storageDir = Join-Path $root "backend\storage\generated_cvs"
    $cacheDir = Join-Path $root ".cache\fastembed"
    New-Item -ItemType Directory -Force -Path $storageDir, $cacheDir | Out-Null

    $backendCmd = @"
`$env:DATABASE_URL = '$localDatabaseUrl'
`$env:RENDER_OUTPUT_DIR = '$storageDir'
`$env:FASTEMBED_CACHE_PATH = '$cacheDir'
`$env:TYPST_BINARY = '$typstBinary'
`$env:LOG_FORMAT = 'console'
Set-Location '$(Join-Path $root "backend")'
Write-Host 'CV-Tailor backend -> http://localhost:8000' -ForegroundColor Cyan
uv run uvicorn app.main:app --reload --port 8000
"@
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null

    if (-not (Wait-Until { (Invoke-RestMethod "http://localhost:8000/health" -TimeoutSec 3).status -ne $null } 120 "backend")) {
        Write-Fail "Backend 120 saniyede yanit vermedi. Acilan backend penceresindeki hataya bakin."
        exit 1
    }
    Write-Ok "ok"
}

# ---------------------------------------------------------------- 6/6 frontend
Write-Step "[6/6] Frontend :5173 ..."
$frontendUp = $false
try { Invoke-WebRequest "http://localhost:5173" -TimeoutSec 3 -UseBasicParsing | Out-Null; $frontendUp = $true } catch { }

if ($frontendUp) {
    Write-Ok "zaten calisiyor"
} else {
    if (-not (Test-Command "node")) {
        Write-Fail "Node.js bulunamadi. Kurun: https://nodejs.org/ (LTS)"
        exit 1
    }
    if (-not $SkipInstall -or -not (Test-Path (Join-Path $root "frontend\node_modules"))) {
        Push-Location (Join-Path $root "frontend")
        try {
            if ((Invoke-Native { npm install --silent }) -ne 0) {
                Write-Fail "npm install basarisiz oldu. 'cd frontend; npm install' ile ciktiyi gorun."
                exit 1
            }
        } finally { Pop-Location }
    }

    $frontendCmd = @"
Set-Location '$(Join-Path $root "frontend")'
Write-Host 'CV-Tailor arayuz -> http://localhost:5173' -ForegroundColor Cyan
npm run dev
"@
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd | Out-Null

    if (-not (Wait-Until { (Invoke-WebRequest "http://localhost:5173" -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 } 120 "frontend")) {
        Write-Fail "Arayuz 120 saniyede acilmadi. Acilan frontend penceresindeki hataya bakin."
        exit 1
    }
    Write-Ok "ok"
}

# ---------------------------------------------------------------- bitis
Write-Host ""
Write-Host "  Hazir." -ForegroundColor Green
Write-Host "  Arayuz : http://localhost:5173" -ForegroundColor White
Write-Host "  API    : http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Ilk girisde 'Kayit ol' ile hesap acin. CV uretimi icin Hesap" -ForegroundColor DarkGray
Write-Host "  ekranindan kendi LLM API anahtarinizi girmeniz gerekir." -ForegroundColor DarkGray
Write-Host "  Durdurmak icin: .\dev.ps1 -Stop" -ForegroundColor DarkGray
Write-Host ""

if (-not $NoBrowser) { Start-Process "http://localhost:5173" }

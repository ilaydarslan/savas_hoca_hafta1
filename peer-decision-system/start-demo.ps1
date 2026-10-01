param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$backendPath = Join-Path $projectRoot 'backend'
$frontendPath = Join-Path $projectRoot 'frontend'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Once README kurulum adimlarini tamamlayin: .venv bulunamadi.' }
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$nodePath = if ($nodeCommand) { $nodeCommand.Source } else { Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' }
if (-not (Test-Path -LiteralPath $nodePath)) { throw 'Node.js bulunamadi. Node.js 22 LTS veya daha yeni bir surum kurun.' }
# The installed runtime works without the Codex application being open.
$env:PATH = (Split-Path -Parent $nodePath) + [IO.Path]::PathSeparator + $env:PATH
if (-not (Test-Path -LiteralPath (Join-Path $frontendPath 'node_modules\vite\bin\vite.js'))) { throw 'Frontend klasorunde npm install calistirin.' }
Push-Location $backendPath
try {
    & $pythonPath -m app.seed.demo
    if ($LASTEXITCODE -ne 0) { throw 'Demo seed tamamlanamadi.' }
} finally { Pop-Location }
foreach ($service in @(
    @{ Port = 8000; Path = $backendPath; Exe = $pythonPath; Args = @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'); Name = 'backend' },
    @{ Port = 5173; Path = $frontendPath; Exe = $nodePath; Args = @('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173'); Name = 'frontend' }
)) {
    $listener = Get-NetTCPConnection -LocalPort $service.Port -State Listen -ErrorAction SilentlyContinue
    if ($listener) { Write-Host "Port $($service.Port) zaten kullanimda; mevcut surec korundu."; continue }
    # WMI launches outside the calling terminal's process job, so closing that
    # terminal does not tear down the application. No scheduled task is created.
    $runner = Join-Path $projectRoot 'run-service.ps1'
    $command = 'powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $runner + '" -Service ' + $service.Name
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]0 }
    $result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $command; CurrentDirectory = $projectRoot; ProcessStartupInformation = $startup }
    if ($result.ReturnValue -ne 0) { throw "Servis baslatilamadi: $($service.Name), Windows hata kodu $($result.ReturnValue)." }
    Write-Host "$($service.Name) baslatildi. Islem kimligi: $($result.ProcessId)"
}
Write-Host 'Arayuz: http://localhost:5173'
Write-Host 'Swagger: http://localhost:8000/docs'
Write-Host 'Servislerin hazir olmasi bekleniyor...'
$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2
        $page = Invoke-WebRequest 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 2
        if ($health.status -eq 'ok' -and $page.StatusCode -eq 200 -and $page.Content -match '<title>.*Karar Sistemi</title>') { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
}
if (-not $ready) { throw 'Uygulama baslatilamadi. backend ve frontend klasorlerindeki stderr.log dosyalarini kontrol edin. 8000 ve 5173 portlari baska bir uygulama tarafindan kullaniliyor olabilir.' }
Write-Host 'Uygulama hazir. Codex acik olmak zorunda degil.'
if (-not $NoBrowser) { Start-Process 'http://localhost:5173' }
Write-Host 'Kapatmak icin ilgili islemi gorev yoneticisinden veya Stop-Process -Id <kimlik> ile durdurun.'

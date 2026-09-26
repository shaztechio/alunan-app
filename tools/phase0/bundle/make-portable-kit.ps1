# Assemble a copy-anywhere Phase 0 test kit: the engine bundle, the pinned Q8
# model files, and a double-click runner that verifies the models, then runs the
# short and full fixtures. Developer research tool. Output: .phase0/<Name>/
[CmdletBinding()]
param([string]$Name = 'rtx30-kit')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$phase0 = Join-Path $root '.phase0'
$kit = Join-Path $phase0 $Name
if (Test-Path $kit) { throw "Refusing to reuse existing kit $kit" }
$bundle = Join-Path $phase0 'test-bundle'
if (-not (Test-Path (Join-Path $bundle 'engine\yue-synth.exe'))) { throw 'Build .phase0/test-bundle with make-bundle.ps1 first' }
New-Item -ItemType Directory -Path $kit, (Join-Path $kit 'models') | Out-Null
Copy-Item -Recurse $bundle (Join-Path $kit 'bundle')
Copy-Item (Join-Path $PSScriptRoot 'run-test.ps1') (Join-Path $kit 'bundle\run-test.ps1') -Force

$lock = Get-Content -Raw (Join-Path $root 'docs/validation/phase0/model-profiles.lock.json') | ConvertFrom-Json
$profile = $lock.profiles | Where-Object id -eq 'yue2-cpp-q8'
$expected = @()
foreach ($asset in $profile.assets | Where-Object { $_.path -like '*.gguf' }) {
    $source = Join-Path $phase0 "models\$($asset.repository)\$($asset.revision)\$($asset.path)"
    Copy-Item $source (Join-Path $kit 'models')
    $expected += "$($asset.sha256)  $($asset.bytes)  $($asset.path)"
}
Set-Content -Path (Join-Path $kit 'models\expected.txt') -Value $expected -Encoding ascii

@'
# Verifies the model copies, then runs the short and full fixtures.
$ErrorActionPreference = 'Stop'
$kit = $PSScriptRoot
Write-Host 'Verifying model files (a minute or two)...'
foreach ($line in Get-Content (Join-Path $kit 'models\expected.txt')) {
    $sha, $bytes, $name = $line -split '\s+', 3
    $file = Join-Path $kit "models\$name"
    if (-not (Test-Path $file) -or (Get-Item $file).Length -ne [long]$bytes -or
        (Get-FileHash $file -Algorithm SHA256).Hash.ToLower() -ne $sha) {
        throw "Model file $name is missing or damaged. Copy it again."
    }
    Write-Host "  OK $name"
}
$results = Join-Path $kit 'results'
New-Item -ItemType Directory -Path $results -Force | Out-Null
foreach ($fixture in 'short', 'full') {
    Write-Host "Running the $fixture song..."
    & (Join-Path $kit 'bundle\run-test.ps1') -Bundle (Join-Path $kit 'bundle') -Models (Join-Path $kit 'models') -Results $results -Fixture $fixture
}
Write-Host "Finished. Send back the 'results' folder."
'@ | Set-Content -Path (Join-Path $kit 'run-kit.ps1') -Encoding utf8

@'
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-kit.ps1"
pause
'@ | Set-Content -Path (Join-Path $kit 'RUN-TEST.cmd') -Encoding ascii

@'
Alunan Phase 0 engine test kit (developer research, not the app)

On the test PC:
1. Only the NVIDIA driver is needed. Ideally no Visual Studio or CUDA toolkit is installed.
2. Copy this whole folder to a local drive (about 5 GB).
3. Double-click RUN-TEST.cmd. It checks the model files, then generates a short
   song (about 15-30 seconds on an RTX 30-series GPU) and a full song (about a minute).
4. When it says "Finished", send back the "results" folder. Each run has a
   result.json, logs, and audio.wav.

Nothing is installed and nothing is downloaded; the test runs offline.
'@ | Set-Content -Path (Join-Path $kit 'README.txt') -Encoding ascii

$size = (Get-ChildItem -Recurse -File $kit | Measure-Object Length -Sum).Sum
"Kit: $kit ($([math]::Round($size / 1GB, 2)) GB)"

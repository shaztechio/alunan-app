# Assemble the Phase 0 portable engine test bundle and a Windows Sandbox config.
# Developer research tool. Output: .phase0/test-bundle/ and
# .phase0/alunan-engine-test.wsb (paths are specific to this machine).
[CmdletBinding()]
param(
    [string]$Build = 'yue2-cpp-build-cuda-multi',
    [int]$SandboxMemoryMB = 16384
)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$phase0 = Join-Path $root '.phase0'
$bundle = Join-Path $phase0 'test-bundle'
if (Test-Path $bundle) { throw "Refusing to reuse existing bundle $bundle" }
$engine = Join-Path $bundle 'engine'
$cublas = Join-Path $bundle 'runtime\cublas'
$requests = Join-Path $bundle 'requests'
New-Item -ItemType Directory -Path $engine, $cublas, $requests | Out-Null

foreach ($name in 'yue-synth.exe', 'ggml.dll', 'ggml-base.dll', 'ggml-cpu.dll', 'ggml-cuda.dll') {
    Copy-Item (Join-Path $phase0 "$Build\$name") $engine
}
# App-local Visual C++ runtime and OpenMP, from the Build Tools redistributable.
$redist = Get-ChildItem 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Redist\MSVC\*\x64' -Directory |
    Sort-Object FullName | Select-Object -Last 1
foreach ($name in 'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll') {
    Copy-Item (Join-Path $redist.FullName "Microsoft.VC143.CRT\$name") $engine
}
Copy-Item (Join-Path $redist.FullName 'Microsoft.VC143.OpenMP\vcomp140.dll') $engine
# Verified cuBLAS runtime pack (see docs/validation/phase0/windows-runtime-pack.json).
$pack = Join-Path $phase0 'runtime-packs\cublas-13.6.0.2-win-x64'
$expected = Get-Content -Raw (Join-Path $pack 'files.json') | ConvertFrom-Json
foreach ($prop in $expected.PSObject.Properties) {
    $file = Join-Path $pack "files\$($prop.Name)"
    if ((Get-FileHash $file -Algorithm SHA256).Hash.ToLower() -ne $prop.Value.sha256) { throw "Runtime pack changed: $($prop.Name)" }
    Copy-Item $file $cublas
}
Copy-Item (Join-Path $phase0 'runs\windows-short-cpp-q8\request.json') (Join-Path $requests 'short.json')
Copy-Item (Join-Path $phase0 'runs\windows-full-cpp-q8\request.json') (Join-Path $requests 'full.json')
Copy-Item (Join-Path $PSScriptRoot 'run-test.ps1') $bundle

$models = Join-Path $phase0 'models\Serveurperso\YuE2-GGUF\64b030e3deb6e8150d2b7c0db641ef5a17eca8a3'
$results = Join-Path $phase0 'sandbox-results'
New-Item -ItemType Directory -Path $results -Force | Out-Null
$wsb = @"
<Configuration>
  <vGPU>Disable</vGPU>
  <Networking>Disable</Networking>
  <MemoryInMB>$SandboxMemoryMB</MemoryInMB>
  <ClipboardRedirection>Disable</ClipboardRedirection>
  <MappedFolders>
    <MappedFolder><HostFolder>$bundle</HostFolder><SandboxFolder>C:\alunan\bundle</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>
    <MappedFolder><HostFolder>$models</HostFolder><SandboxFolder>C:\alunan\models</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>
    <MappedFolder><HostFolder>$results</HostFolder><SandboxFolder>C:\alunan\results</SandboxFolder><ReadOnly>false</ReadOnly></MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File C:\alunan\bundle\run-test.ps1 -Bundle C:\alunan\bundle -Models C:\alunan\models -Results C:\alunan\results</Command>
  </LogonCommand>
</Configuration>
"@
$wsbPath = Join-Path $phase0 'alunan-engine-test.wsb'
Set-Content -Path $wsbPath -Value $wsb -Encoding utf8
Get-ChildItem -Recurse -File $bundle | ForEach-Object { '{0,12} {1}' -f $_.Length, $_.FullName.Substring($bundle.Length + 1) }
"Sandbox config: $wsbPath"

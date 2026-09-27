# Phase 0 portable engine test. Developer research tool, not an installer.
# Runs the bundled yue2.cpp engine on the short fixture and records which DLLs
# load from where. Works on a clean machine, in Windows Sandbox (CPU only), or
# on a PC with an NVIDIA GPU and its driver. Results go to -Results.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Bundle,
    [Parameter(Mandatory)][string]$Models,
    [Parameter(Mandatory)][string]$Results,
    [int]$TimeoutMinutes = 90,
    [ValidateSet('short', 'full')][string]$Fixture = 'short'
)
$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$out = Join-Path $Results "$env:COMPUTERNAME-$Fixture-$stamp"
New-Item -ItemType Directory -Path $out -Force | Out-Null
$report = [ordered]@{
    schemaVersion = 1
    computer = $env:COMPUTERNAME
    os = (Get-CimInstance Win32_OperatingSystem).Caption + ' ' + [Environment]::OSVersion.Version
    cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
    ramBytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    gpus = @(Get-CimInstance Win32_VideoController | ForEach-Object { "$($_.Name) driver $($_.DriverVersion)" })
    fixture = $Fixture
    system32Runtime = [ordered]@{}
    bundleFiles = [ordered]@{}
}
foreach ($name in 'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'vcomp140.dll', 'nvcuda.dll') {
    $report.system32Runtime[$name] = Test-Path (Join-Path $env:SystemRoot "System32\$name")
}
foreach ($file in Get-ChildItem -Recurse -File (Join-Path $Bundle 'engine'), (Join-Path $Bundle 'runtime')) {
    $report.bundleFiles[$file.Name] = (Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower()
}

# Negative control: the engine without its app-local C++ runtime DLLs.
$negative = Join-Path $env:TEMP "alunan-negative-$stamp"
New-Item -ItemType Directory -Path $negative | Out-Null
Get-ChildItem (Join-Path $Bundle 'engine') -File | Where-Object { $_.Name -like 'ggml*' -or $_.Name -eq 'yue-synth.exe' } |
    Copy-Item -Destination $negative
$runtime = Join-Path $Bundle 'runtime\cublas'
$env:PATH = "$runtime;$env:SystemRoot\System32;$env:SystemRoot;$env:SystemRoot\System32\Wbem"
Remove-Item Env:CUDA_PATH* -ErrorAction SilentlyContinue
$p = Start-Process (Join-Path $negative 'yue-synth.exe') -ArgumentList '--help' -Wait -PassThru -NoNewWindow `
    -RedirectStandardError (Join-Path $out 'negative-stderr.log') -RedirectStandardOutput (Join-Path $out 'negative-stdout.log')
$report.negativeControlExitCode = '0x{0:X8}' -f $p.ExitCode
$report.negativeControlLoaded = [bool](Select-String -Quiet -Path (Join-Path $out 'negative-stderr.log'), (Join-Path $out 'negative-stdout.log') -Pattern 'yue2\.cpp')
Remove-Item -Recurse -Force $negative

# Load check: --help loads every statically imported DLL, including cuBLAS.
$engine = Join-Path $Bundle 'engine\yue-synth.exe'
$p = Start-Process $engine -ArgumentList '--help' -Wait -PassThru -NoNewWindow `
    -RedirectStandardError (Join-Path $out 'help-stderr.log') -RedirectStandardOutput (Join-Path $out 'help-stdout.log')
$report.loadCheckExitCode = '0x{0:X8}' -f $p.ExitCode
$report.loadCheckLoaded = [bool](Select-String -Quiet -Path (Join-Path $out 'help-stderr.log'), (Join-Path $out 'help-stdout.log') -Pattern 'yue2\.cpp')
$report.exitCodeNote = '--help exits 1 after printing usage when all DLLs load; 0xC0000135 means a DLL was not found'

# Generation with module sampling.
$request = Join-Path $Bundle "requests\$Fixture.json"
$wav = Join-Path $out 'audio.wav'
$arguments = @('--model', "`"$(Join-Path $Models 'YuE2-3B-Q8_0.gguf')`"", '--vae', "`"$(Join-Path $Models 'YuE2-Vae-F32.gguf')`"",
               '--request', "`"$request`"", '--out', "`"$wav`"")
# Power source: laptops throttle the GPU on battery, which makes timings meaningless.
$battery = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select-Object -First 1
$report.power = if ($battery) {
    [ordered]@{ onAC = ($battery.BatteryStatus -eq 2); batteryStatus = $battery.BatteryStatus; chargePercent = $battery.EstimatedChargeRemaining }
} else { [ordered]@{ onAC = $true; note = 'no battery reported (desktop)' } }
if ($battery -and $battery.BatteryStatus -ne 2) { Write-Warning 'Running on battery: GPU timings will not be representative. Plug in the charger for a timing run.' }
# GPU telemetry every 5 seconds: memory, clocks, power, state and throttle reasons.
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
$telemetryFile = Join-Path $out 'gpu-telemetry.csv'
$query = 'timestamp,utilization.gpu,memory.used,memory.total,clocks.sm,clocks.max.sm,power.draw,pstate,temperature.gpu,clocks_throttle_reasons.active'
if ($smi) { Set-Content -Path $telemetryFile -Value $query -Encoding ascii }
$watch = [Diagnostics.Stopwatch]::StartNew()
$p = Start-Process $engine -ArgumentList $arguments -PassThru -NoNewWindow `
    -RedirectStandardError (Join-Path $out 'stderr.log') -RedirectStandardOutput (Join-Path $out 'stdout.log')
$null = $p.Handle  # caches the handle so ExitCode is available after exit
$modules = @{}
# Windows counters split a process's GPU memory into dedicated (VRAM) and shared
# (system RAM used when VRAM overflows); shared usage means spilling.
$gpuMemory = [ordered]@{ peakDedicatedBytes = 0; peakSharedBytes = 0; samples = 0 }
$tick = 0
while (-not $p.HasExited -and $watch.Elapsed.TotalMinutes -lt $TimeoutMinutes) {
    try { $p.Refresh(); foreach ($m in $p.Modules) { $modules[$m.FileName] = $true } } catch { }
    if ($tick % 5 -eq 0) {
        if ($smi) {
            try { & $smi.Source "--query-gpu=$query" '--format=csv,noheader,nounits' | Add-Content -Path $telemetryFile -Encoding ascii } catch { }
        }
        try {
            $samples = (Get-Counter -ErrorAction Stop "\GPU Process Memory(pid_$($p.Id)_*)\Dedicated Usage", "\GPU Process Memory(pid_$($p.Id)_*)\Shared Usage").CounterSamples
            $dedicated = ($samples | Where-Object Path -like '*dedicated usage' | Measure-Object CookedValue -Sum).Sum
            $shared = ($samples | Where-Object Path -like '*shared usage' | Measure-Object CookedValue -Sum).Sum
            $gpuMemory.peakDedicatedBytes = [math]::Max($gpuMemory.peakDedicatedBytes, [double]$dedicated)
            $gpuMemory.peakSharedBytes = [math]::Max($gpuMemory.peakSharedBytes, [double]$shared)
            $gpuMemory.samples++
        } catch { }
    }
    $tick++
    Start-Sleep -Milliseconds 1000
}
if (-not $p.HasExited) { $p.Kill(); $report.timedOut = $true } else { $report.timedOut = $false }
$p.WaitForExit()
$report.generationExitCode = '0x{0:X8}' -f $p.ExitCode
$report.generationSeconds = [math]::Round($watch.Elapsed.TotalSeconds, 2)
$report.loadedModules = @($modules.Keys | Sort-Object)
$report.gpuProcessMemory = $gpuMemory
if ($smi -and (Test-Path $telemetryFile)) {
    $rows = @(Import-Csv $telemetryFile | Where-Object { $_.'memory.used' -match '^\s*[0-9]' })
    if ($rows.Count) {
        $report.gpuTelemetry = [ordered]@{
            samples = $rows.Count
            peakMemoryUsedMiB = ($rows | ForEach-Object { [int]$_.'memory.used' } | Measure-Object -Maximum).Maximum
            memoryTotalMiB = [int]$rows[0].'memory.total'
            medianSmClockMHz = ($rows | ForEach-Object { [int]$_.'clocks.sm' } | Sort-Object)[[int]($rows.Count / 2)]
            maxSmClockMHz = [int]$rows[0].'clocks.max.sm'
            peakPowerW = ($rows | ForEach-Object { [double]$_.'power.draw' } | Measure-Object -Maximum).Maximum
            throttleReasonsSeen = @($rows | ForEach-Object { $_.'clocks_throttle_reasons.active'.Trim() } | Sort-Object -Unique)
        }
    }
}
$report.backendLines = @(Select-String -Path (Join-Path $out 'stderr.log') -Pattern '\[Load\] .* backend|ggml_cuda_init|Device 0|Pipeline\] Done|FATAL' |
    ForEach-Object { $_.Line })
if (Test-Path $wav) {
    $report.wavBytes = (Get-Item $wav).Length
    $report.wavSha256 = (Get-FileHash $wav -Algorithm SHA256).Hash.ToLower()
}
$report | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $out 'result.json')
"Done. Results in $out"

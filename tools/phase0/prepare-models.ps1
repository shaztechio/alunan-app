# Developer research tool, not the application's model downloader.
[CmdletBinding()]
param(
    [ValidateSet('yue2-reference-bf16', 'yue2-cpp-q8')]
    [string]$Profile = 'yue2-reference-bf16'
)
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskLock = Get-Content -Raw (Join-Path $taskRoot 'docs/validation/phase0/model-profiles.lock.json') | ConvertFrom-Json
$taskProfile = @($taskLock.profiles | Where-Object id -eq $Profile)
if ($taskProfile.Count -ne 1) { throw 'Expected exactly one pinned profile' }
$taskDestination = Join-Path $taskRoot '.phase0/models'
foreach ($taskAsset in $taskProfile[0].assets) {
    $taskRelative = "$($taskAsset.repository)/$($taskAsset.revision)/$($taskAsset.path)"
    $taskFile = [IO.Path]::GetFullPath((Join-Path $taskDestination $taskRelative))
    if (-not $taskFile.StartsWith($taskDestination + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Asset path escapes the research directory'
    }
    if ($taskAsset.sha256 -notmatch '^[a-f0-9]{64}$' -or $taskAsset.revision -notmatch '^[a-f0-9]{40}$') {
        throw 'Unpinned asset'
    }
    $taskExpectedUrl = "https://huggingface.co/$($taskAsset.repository)/resolve/$($taskAsset.revision)/$($taskAsset.path)"
    if ($taskAsset.url -cne $taskExpectedUrl) { throw 'Unexpected source URL' }
    New-Item -ItemType Directory -Path (Split-Path $taskFile) -Force | Out-Null
    if (Test-Path -LiteralPath $taskFile) {
        if ((Get-Item -LiteralPath $taskFile).Length -eq $taskAsset.bytes -and
            (Get-FileHash -LiteralPath $taskFile -Algorithm SHA256).Hash -eq $taskAsset.sha256) {
            Write-Output "Verified existing $($taskAsset.repository)/$($taskAsset.path)"
            continue
        }
        throw "Existing file failed verification: $taskFile"
    }
    $taskPartial = "$taskFile.partial"
    if ((Test-Path -LiteralPath $taskPartial) -and (Get-Item -LiteralPath $taskPartial).Length -eq $taskAsset.bytes) {
        if ((Get-FileHash -LiteralPath $taskPartial -Algorithm SHA256).Hash -ne $taskAsset.sha256) {
            throw "Full-size partial failed verification: $taskPartial"
        }
        Move-Item -LiteralPath $taskPartial -Destination $taskFile
        Write-Output "Verified completed partial $($taskAsset.repository)/$($taskAsset.path)"
        continue
    }
    Write-Output "Downloading $($taskAsset.repository)/$($taskAsset.path) ($($taskAsset.bytes) bytes)"
    Invoke-WebRequest -Uri $taskAsset.url -OutFile $taskPartial -Resume -TimeoutSec 120
    if ((Get-Item -LiteralPath $taskPartial).Length -ne $taskAsset.bytes -or
        (Get-FileHash -LiteralPath $taskPartial -Algorithm SHA256).Hash -ne $taskAsset.sha256) {
        throw "Downloaded file failed verification; partial retained: $taskPartial"
    }
    Move-Item -LiteralPath $taskPartial -Destination $taskFile
    Write-Output "Verified $($taskAsset.repository)/$($taskAsset.path)"
}

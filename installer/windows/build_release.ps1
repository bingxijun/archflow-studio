#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [switch]$PlanOnly
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}
$pluginRoot = Join-Path $RepoRoot "plugins\archflow-studio"
$manifestPath = Join-Path $pluginRoot ".codex-plugin\plugin.json"
if (-not (Test-Path -LiteralPath $manifestPath)) { throw "Plugin manifest missing: $manifestPath" }
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$version = [string]$manifest.version
$buildRoot = Join-Path $RepoRoot "build\release"
$stage = Join-Path $buildRoot ("ArchFlow-Studio-" + $version + "-windows")
$dist = Join-Path $RepoRoot "dist"
$archive = Join-Path $dist ("ArchFlow-Studio-" + $version + "-windows.zip")

Write-Host "ArchFlow release plan"
Write-Host "Plugin: $pluginRoot"
Write-Host "Stage: $stage"
Write-Host "Archive: $archive"
if ($PlanOnly) { Write-Host "PlanOnly set; no files were changed."; exit 0 }

python (Join-Path $RepoRoot "scripts\release_check.py") --gates (Join-Path $RepoRoot "release\release-gates.json") --channel developer-preview
if ($LASTEXITCODE -ne 0) { throw "Developer Preview release gates failed" }

$repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd("\")
$stageFull = [System.IO.Path]::GetFullPath($stage)
if (-not $stageFull.StartsWith($repoFull + "\", [System.StringComparison]::OrdinalIgnoreCase)) { throw "Stage escaped repo root" }
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $stage "payload") | Out-Null
Copy-Item -LiteralPath $pluginRoot -Destination (Join-Path $stage "payload\archflow-studio") -Recurse -Force
$stagePlugin = (Resolve-Path (Join-Path $stage "payload\archflow-studio")).Path
Get-ChildItem -Recurse -Directory -LiteralPath $stagePlugin -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "__pycache__" } |
    ForEach-Object {
        if (-not $_.FullName.StartsWith($stagePlugin + "\", [System.StringComparison]::OrdinalIgnoreCase)) { throw "Cache cleanup escaped staged plugin" }
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }
Get-ChildItem -Recurse -File -LiteralPath $stagePlugin -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "ArchFlow.Setup.ps1") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "LICENSE") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "NOTICE") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "PREVIEW_NOTICE.txt") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "THIRD_PARTY_NOTICES.md") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "release\release-gates.json") -Destination $stage -Force

python (Join-Path $RepoRoot "scripts\generate_sbom.py") --root (Join-Path $stage "payload") --name "ArchFlow Studio Plugin" --version $version --output (Join-Path $stage "sbom.spdx.json")
if ($LASTEXITCODE -ne 0) { throw "SBOM generation failed" }

$checksums = Get-ChildItem -Recurse -File $stage | Sort-Object FullName | ForEach-Object {
    $relative = $_.FullName.Substring($stage.Length + 1).Replace("\", "/")
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $relative"
}
$checksums | Set-Content -LiteralPath (Join-Path $stage "checksums.sha256") -Encoding UTF8

New-Item -ItemType Directory -Force -Path $dist | Out-Null
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $archive -CompressionLevel Optimal
$archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "Built: $archive"
Write-Host "SHA256: $archiveHash"

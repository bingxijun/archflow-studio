# SPDX-FileCopyrightText: 2026 OHDESIGN
# SPDX-License-Identifier: Apache-2.0
# Compatibility filename retained for existing installer calls.

#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PackageRoot = "",
    [string]$ProjectRoot = "",
    [string]$SketchUpPluginsPath = "",
    [string]$CodexConfigPath = "",
    [switch]$UseManualPlugin,
    [switch]$SkipPluginDeploy,
    [switch]$SkipCodexConfig,
    [switch]$PlanOnly
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($PackageRoot)) {
    $PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-SketchUpPluginDirs {
    $base = Join-Path $env:APPDATA "SketchUp"
    if (-not (Test-Path -LiteralPath $base)) { return @() }
    @(Get-ChildItem -LiteralPath $base -Recurse -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq "Plugins" })
}

function Select-PluginDir {
    param([string]$OverridePath)
    if (-not [string]::IsNullOrWhiteSpace($OverridePath)) {
        if (-not (Test-Path -LiteralPath $OverridePath)) { throw "SketchUpPluginsPath does not exist: $OverridePath" }
        return (Resolve-Path -LiteralPath $OverridePath).Path
    }
    $dirs = @(Get-SketchUpPluginDirs)
    if ($dirs.Count -eq 0) { throw "No SketchUp Plugins folder found. Pass -SketchUpPluginsPath explicitly." }
    $ranked = $dirs | ForEach-Object {
        $version = 0
        if ($_.FullName -match "SketchUp\s+(\d+)") { $version = [int]$Matches[1] }
        [pscustomobject]@{ Path = $_.FullName; Version = $version; Modified = $_.LastWriteTime }
    } | Sort-Object Version, Modified -Descending
    return $ranked[0].Path
}

function Get-BridgePackage {
    param([string]$Root)
    $path = Join-Path $Root "assets\plugins\archflow_bridge.rbz"
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing ArchFlow-owned RBZ package: $path" }
    return (Resolve-Path -LiteralPath $path).Path
}

function Assert-RbzLayout {
    param([string]$RbzPath)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($RbzPath)
    try {
        $entries = @($zip.Entries | ForEach-Object { $_.FullName.Replace("/", "\") })
        if (-not ($entries -contains "archflow_bridge.rb") -or -not ($entries -contains "archflow_bridge\main.rb")) {
            throw "Invalid ArchFlow RBZ layout. Expected archflow_bridge.rb and archflow_bridge\main.rb."
        }
        if ($entries.Count -ne 2) { throw "ArchFlow RBZ contains unexpected files." }
    } finally {
        $zip.Dispose()
    }
}

function Ensure-BridgeToken {
    $directory = Join-Path $env:LOCALAPPDATA "ArchFlow"
    $path = Join-Path $directory "bridge-token"
    if (Test-Path -LiteralPath $path) {
        $existing = (Get-Content -LiteralPath $path -Raw -Encoding UTF8).Trim()
        if ($existing.Length -ge 32) { return $path }
    }
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $token = -join ($bytes | ForEach-Object { $_.ToString("x2") })
    [System.IO.File]::WriteAllText($path, $token, (New-Object System.Text.UTF8Encoding($false)))
    return $path
}

function Deploy-Bridge {
    param([string]$RbzPath, [string]$PluginsPath)
    Assert-RbzLayout $RbzPath
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $tempBase = [System.IO.Path]::GetTempPath()
    $temp = Join-Path $tempBase ("archflow_bridge_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $temp | Out-Null
    try {
        [System.IO.Compression.ZipFile]::ExtractToDirectory($RbzPath, $temp)
        $loader = Join-Path $temp "archflow_bridge.rb"
        $folder = Join-Path $temp "archflow_bridge"
        $stamp = Get-Date -Format "yyyyMMddHHmmss"
        $destLoader = Join-Path $PluginsPath "archflow_bridge.rb"
        $destFolder = Join-Path $PluginsPath "archflow_bridge"
        if (Test-Path -LiteralPath $destLoader) { Copy-Item -LiteralPath $destLoader -Destination "$destLoader.backup_$stamp" -Force }
        if (Test-Path -LiteralPath $destFolder) { Copy-Item -LiteralPath $destFolder -Destination "$destFolder.backup_$stamp" -Recurse -Force }
        Copy-Item -LiteralPath $loader -Destination $PluginsPath -Force
        Copy-Item -LiteralPath $folder -Destination $PluginsPath -Recurse -Force
    } finally {
        $resolved = if (Test-Path -LiteralPath $temp) { (Resolve-Path -LiteralPath $temp).Path } else { $null }
        $base = (Resolve-Path -LiteralPath $tempBase).Path.TrimEnd("\")
        if ($resolved -and $resolved.StartsWith($base, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolved -Leaf).StartsWith("archflow_bridge_")) {
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
    }
}

$pluginsPath = if ($SkipPluginDeploy) { "" } else { Select-PluginDir $SketchUpPluginsPath }
$rbz = if ($SkipPluginDeploy) { "" } else { Get-BridgePackage $PackageRoot }

Write-Host "ArchFlow SketchUp Bridge deployment plan"
Write-Host "PackageRoot: $PackageRoot"
if (-not $SkipPluginDeploy) {
    Write-Host "SketchUp Plugins: $pluginsPath"
    Write-Host "RBZ: $rbz"
}
Write-Host "MCP server: bundled Plugin .mcp.json (no Git clone, pip install, or config.toml edit)"
Write-Host "Local endpoint: 127.0.0.1:9877 with a per-user random token"
if ($PlanOnly) {
    Write-Host "PlanOnly set; no files were changed."
    exit 0
}

if (-not $SkipPluginDeploy) { Deploy-Bridge -RbzPath $rbz -PluginsPath $pluginsPath }
$tokenPath = Ensure-BridgeToken
Write-Host "Bridge token ready: $tokenPath"
Write-Host "Done. Restart SketchUp and Codex, then call sketchup_bridge_status."

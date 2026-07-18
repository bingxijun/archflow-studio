# SPDX-FileCopyrightText: 2026 OHDESIGN
# SPDX-License-Identifier: Apache-2.0

#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PackageRoot = "",
    [int]$Port = 9877
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($PackageRoot)) { $PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
$script:Failures = 0
$script:Warnings = 0

function Write-Check {
    param([ValidateSet("OK", "WARN", "FAIL")][string]$Level, [string]$Message)
    if ($Level -eq "FAIL") { $script:Failures++ }
    if ($Level -eq "WARN") { $script:Warnings++ }
    Write-Host ("[{0}] {1}" -f $Level, $Message)
}

function Get-SketchUpInstalls {
    $roots = @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*", "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*")
    Get-ItemProperty $roots -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*SketchUp*" } | Select-Object DisplayName, DisplayVersion, InstallLocation
}

function Get-SketchUpPluginDirs {
    $base = Join-Path $env:APPDATA "SketchUp"
    if (-not (Test-Path -LiteralPath $base)) { return @() }
    @(Get-ChildItem -LiteralPath $base -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "Plugins" })
}

Write-Host "ArchFlow SketchUp Bridge preflight"
Write-Host "PackageRoot: $PackageRoot"
if ($IsWindows -or $env:OS -like "*Windows*") { Write-Check OK "Windows environment detected" } else { Write-Check FAIL "Windows is required" }
Write-Check OK ("PowerShell: {0} {1}" -f $PSVersionTable.PSEdition, $PSVersionTable.PSVersion)
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) { Write-Check OK "Python MCP runtime: $($python.Source)" } else { Write-Check FAIL "Python not found on PATH" }

$mcpServer = Join-Path $PackageRoot "scripts\archflow_mcp_server.py"
if (Test-Path -LiteralPath $mcpServer) { Write-Check OK "Bundled standalone ArchFlow MCP server present" } else { Write-Check FAIL "Bundled MCP server missing: $mcpServer" }

$installs = @(Get-SketchUpInstalls)
if ($installs.Count) { $installs | ForEach-Object { Write-Check OK ("SketchUp install: {0} {1}" -f $_.DisplayName, $_.DisplayVersion) } } else { Write-Check FAIL "No SketchUp install found" }
$pluginDirs = @(Get-SketchUpPluginDirs)
if ($pluginDirs.Count) { $pluginDirs | ForEach-Object { Write-Check OK "SketchUp Plugins folder: $($_.FullName)" } } else { Write-Check FAIL "No SketchUp Plugins folder found" }

$bridgeSources = @(
    (Join-Path $PackageRoot "assets\sketchup-extension\archflow_bridge.rb.txt"),
    (Join-Path $PackageRoot "assets\sketchup-extension\archflow_bridge\main.rb.txt")
)
if (@($bridgeSources | Where-Object { -not (Test-Path -LiteralPath $_) }).Count -eq 0) {
    Write-Check OK "Transparent SketchUp bridge sources are present; the RBZ will be built at apply time"
} else {
    Write-Check FAIL "One or more SketchUp bridge source files are missing"
}

try {
    if (Test-NetConnection 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue) { Write-Check OK "127.0.0.1:$Port is accepting connections" }
    else { Write-Check WARN "127.0.0.1:$Port is closed; start SketchUp after installation" }
} catch { Write-Check WARN "TCP port check failed: $($_.Exception.Message)" }

Write-Host ("Summary: {0} failure(s), {1} warning(s)" -f $script:Failures, $script:Warnings)
if ($script:Failures -gt 0) { exit 1 }
exit 0

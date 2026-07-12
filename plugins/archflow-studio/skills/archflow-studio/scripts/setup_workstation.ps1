#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PackageRoot = "",
    [switch]$Apply,
    [switch]$SkipCad,
    [switch]$SkipSketchUp,
    [string]$SketchUpPluginsPath = "",
    [string]$CodexConfigPath = (Join-Path $env:USERPROFILE ".codex\config.toml"),
    [string]$ProjectRoot = (Join-Path $env:USERPROFILE "Documents\ArchFlow")
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($PackageRoot)) {
    $PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$cadCli = Join-Path $PackageRoot "scripts\cad-cli.ps1"
$suPreflight = Join-Path $PackageRoot "scripts\preflight_check.ps1"
$suDeploy = Join-Path $PackageRoot "scripts\deploy_sketchup_mcp.ps1"

Write-Host "ArchFlow Studio workstation setup"
Write-Host "PackageRoot: $PackageRoot"
Write-Host "Mode: $(if ($Apply) { 'APPLY' } else { 'PLAN ONLY' })"
Write-Host "Changes when applied: deploy the ArchFlow-owned SketchUp RBZ with backups and create a local pairing token. The Plugin supplies its own MCP server configuration."
Write-Host "CAD source drawings and SketchUp model geometry are not modified by workstation setup."

if (-not $SkipCad) {
    if (-not (Test-Path -LiteralPath $cadCli)) { throw "Missing CAD bridge: $cadCli" }
    Write-Host "`nCAD read-only diagnostic"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $cadCli diagnose
    if ($LASTEXITCODE -ne 0) { Write-Warning "CAD diagnostic did not find a ready active bridge. Setup may continue for other components." }
}

if (-not $SkipSketchUp) {
    if (-not (Test-Path -LiteralPath $suPreflight)) { throw "Missing SketchUp preflight: $suPreflight" }
    if (-not (Test-Path -LiteralPath $suDeploy)) { throw "Missing SketchUp deployer: $suDeploy" }
    Write-Host "`nSketchUp read-only preflight"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $suPreflight -PackageRoot $PackageRoot
    if ($LASTEXITCODE -ne 0) { Write-Warning "SketchUp preflight reported blockers. Review them before applying." }

    $deployArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $suDeploy,
        "-PackageRoot", $PackageRoot,
        "-ProjectRoot", $ProjectRoot,
        "-CodexConfigPath", $CodexConfigPath
    )
    if (-not [string]::IsNullOrWhiteSpace($SketchUpPluginsPath)) {
        $deployArgs += @("-SketchUpPluginsPath", $SketchUpPluginsPath)
    }
    if (-not $Apply) { $deployArgs += "-PlanOnly" }

    Write-Host "`nSketchUp deployment $(if ($Apply) { 'execution' } else { 'plan' })"
    & powershell @deployArgs
    if ($LASTEXITCODE -ne 0) { throw "SketchUp deployment step failed with exit code $LASTEXITCODE" }
}

if (-not $Apply) {
    Write-Host "`nPlan complete. No workstation files were changed by this wrapper. Run again with -Apply only after reviewing the destinations above."
} else {
    Write-Host "`nSetup applied. Restart SketchUp and Codex, open a blank SketchUp model, then call sketchup_bridge_status and sketchup_get_selection."
}

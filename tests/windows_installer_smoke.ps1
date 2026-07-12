#Requires -Version 5.1
[CmdletBinding()]
param([string]$RepoRoot = "")

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepoRoot)) { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
$workspace = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd("\")
$testRoot = Join-Path $workspace ("build\installer-smoke\" + [guid]::NewGuid().ToString("N"))
if (-not ([System.IO.Path]::GetFullPath($testRoot).StartsWith($workspace + "\", [System.StringComparison]::OrdinalIgnoreCase))) { throw "Smoke root escaped workspace" }

$setup = Join-Path $workspace "installer\windows\ArchFlow.Setup.ps1"
$package = Join-Path $workspace "plugins\archflow-studio"
$installBase = Join-Path $testRoot "localappdata\ArchFlow"
$marketplace = Join-Path $testRoot "home\.agents\plugins\marketplace.json"
$pluginPath = Join-Path $testRoot "home\plugins\archflow-studio"

try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $setup -Action Plan -PackageRoot $package -InstallBase $installBase -MarketplacePath $marketplace -UserPluginPath $pluginPath
    if ($LASTEXITCODE -ne 0) { throw "Plan failed" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $setup -Action Install -PackageRoot $package -InstallBase $installBase -MarketplacePath $marketplace -UserPluginPath $pluginPath
    if ($LASTEXITCODE -ne 0) { throw "Install failed" }
    if (-not (Test-Path -LiteralPath (Join-Path $pluginPath ".codex-plugin\plugin.json"))) { throw "Installed plugin manifest missing" }
    $previewNotice = Join-Path $installBase "PREVIEW_NOTICE.txt"
    if (-not (Test-Path -LiteralPath $previewNotice)) { throw "Per-user Developer Preview notice missing" }
    $previewText = Get-Content -LiteralPath $previewNotice -Raw -Encoding UTF8
    foreach ($required in @("ArchFlow Studio Developer Preview", "OHDESIGN", "@heikikun", "https://archflow.best", "CAD/SketchUp")) {
        if (-not $previewText.Contains($required)) { throw "Developer Preview notice is missing required text: $required" }
    }
    $catalog = Get-Content -LiteralPath $marketplace -Raw -Encoding UTF8 | ConvertFrom-Json
    $entry = @($catalog.plugins | Where-Object {$_.name -eq "archflow-studio"}) | Select-Object -First 1
    if (-not $entry) { throw "Marketplace entry missing" }
    if ($entry.policy.installation -ne "INSTALLED_BY_DEFAULT") { throw "Plugin is not installed by default" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $setup -Action Repair -PackageRoot $package -InstallBase $installBase -MarketplacePath $marketplace -UserPluginPath $pluginPath
    if ($LASTEXITCODE -ne 0) { throw "Repair failed" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $setup -Action Uninstall -PackageRoot $package -InstallBase $installBase -MarketplacePath $marketplace -UserPluginPath $pluginPath
    if ($LASTEXITCODE -ne 0) { throw "Uninstall failed" }
    if (Get-Item -LiteralPath $pluginPath -Force -ErrorAction SilentlyContinue) { throw "Plugin junction still exists" }
    if (Test-Path -LiteralPath $previewNotice) { throw "Per-user Developer Preview notice was not removed" }
    $catalog = Get-Content -LiteralPath $marketplace -Raw -Encoding UTF8 | ConvertFrom-Json
    if (@($catalog.plugins | Where-Object {$_.name -eq "archflow-studio"}).Count -ne 0) { throw "Marketplace entry still exists" }
    Write-Host "Windows installer smoke test passed."
} finally {
    if (Test-Path -LiteralPath $testRoot) {
        $resolved = (Resolve-Path -LiteralPath $testRoot).Path
        if (-not $resolved.StartsWith($workspace + "\", [System.StringComparison]::OrdinalIgnoreCase)) { throw "Cleanup escaped workspace" }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}

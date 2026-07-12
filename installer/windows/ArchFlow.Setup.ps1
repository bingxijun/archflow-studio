#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet("Plan", "Install", "Repair", "Uninstall")]
    [string]$Action = "Plan",
    [string]$PackageRoot = "",
    [string]$InstallBase = (Join-Path $env:LOCALAPPDATA "ArchFlow"),
    [string]$MarketplacePath = (Join-Path $env:USERPROFILE ".agents\plugins\marketplace.json"),
    [string]$UserPluginPath = (Join-Path $env:USERPROFILE "plugins\archflow-studio"),
    [switch]$ConfigureApplications,
    [switch]$Purge
)

$ErrorActionPreference = "Stop"

function Resolve-PackageRoot {
    param([string]$Requested)
    if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        return (Resolve-Path -LiteralPath $Requested).Path
    }
    $releasePayload = Join-Path $PSScriptRoot "payload\archflow-studio"
    if (Test-Path -LiteralPath $releasePayload) { return (Resolve-Path -LiteralPath $releasePayload).Path }
    $repoPlugin = Join-Path $PSScriptRoot "..\..\plugins\archflow-studio"
    if (Test-Path -LiteralPath $repoPlugin) { return (Resolve-Path -LiteralPath $repoPlugin).Path }
    throw "Could not locate the ArchFlow plugin payload. Pass -PackageRoot explicitly."
}

function Resolve-PreviewNoticePath {
    param([string]$ResolvedPackageRoot)
    $candidates = @(
        (Join-Path $PSScriptRoot "PREVIEW_NOTICE.txt"),
        (Join-Path $PSScriptRoot "..\..\PREVIEW_NOTICE.txt"),
        (Join-Path $ResolvedPackageRoot "PREVIEW_NOTICE.txt")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    throw "Developer Preview notice is missing. Refusing to continue."
}

function Read-PreviewNotice {
    param([string]$Path)
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8).TrimEnd()
}

function Write-PreviewNoticeForUser {
    param([string]$Source, [string]$Destination)
    $content = Read-PreviewNotice -Path $Source
    [System.IO.File]::WriteAllText($Destination, $content + "`n", (New-Object System.Text.UTF8Encoding($false)))
}

function Assert-UnderPath {
    param([string]$Path, [string]$Parent, [string]$Label)
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd("\")
    $fullParent = [System.IO.Path]::GetFullPath($Parent).TrimEnd("\")
    if (-not $fullPath.StartsWith($fullParent + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label escaped its allowed parent: $fullPath"
    }
}

function Backup-File {
    param([string]$Path, [string]$BackupRoot)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
    $stamp = Get-Date -Format "yyyyMMddHHmmss"
    $destination = Join-Path $BackupRoot ((Split-Path $Path -Leaf) + ".backup_" + $stamp)
    Copy-Item -LiteralPath $Path -Destination $destination -Force
    return $destination
}

function Write-JsonAtomic {
    param([string]$Path, [object]$Value)
    $parent = Split-Path $Path -Parent
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $temporary = "$Path.tmp"
    $json = $Value | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText($temporary, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Update-PersonalMarketplace {
    param([string]$Path, [bool]$InstallEntry, [string]$BackupRoot)
    if (Test-Path -LiteralPath $Path) {
        Backup-File -Path $Path -BackupRoot $BackupRoot | Out-Null
        $marketplace = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($marketplace.name -and $marketplace.name -ne "personal") {
            throw "Existing default marketplace name is '$($marketplace.name)', expected 'personal'. It was not changed."
        }
    } else {
        $marketplace = [pscustomobject]@{
            name = "personal"
            interface = [pscustomobject]@{ displayName = "Personal" }
            plugins = @()
        }
    }

    $plugins = @($marketplace.plugins | Where-Object { $_.name -ne "archflow-studio" })
    if ($InstallEntry) {
        $plugins += [pscustomobject]@{
            name = "archflow-studio"
            source = [pscustomobject]@{ source = "local"; path = "./plugins/archflow-studio" }
            policy = [pscustomobject]@{ installation = "INSTALLED_BY_DEFAULT"; authentication = "ON_INSTALL" }
            category = "Productivity"
        }
    }
    if ($marketplace.PSObject.Properties.Name -contains "plugins") {
        $marketplace.plugins = $plugins
    } else {
        $marketplace | Add-Member -NotePropertyName plugins -NotePropertyValue $plugins
    }
    Write-JsonAtomic -Path $Path -Value $marketplace
}

function Remove-ManagedJunction {
    param([string]$Path, [string]$AllowedTargetRoot)
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if (-not $item) { return }
    if ($item.LinkType -ne "Junction") {
        throw "Refusing to replace or remove a non-junction path: $Path"
    }
    $targets = @($item.Target)
    if ($targets.Count -ne 1) { throw "Unexpected junction target count for $Path" }
    $target = [System.IO.Path]::GetFullPath($targets[0])
    $allowed = [System.IO.Path]::GetFullPath($AllowedTargetRoot).TrimEnd("\")
    if (-not $target.StartsWith($allowed + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove junction outside the managed install: $Path -> $target"
    }
    [System.IO.Directory]::Delete([System.IO.Path]::GetFullPath($Path), $false)
}

$PackageRoot = Resolve-PackageRoot -Requested $PackageRoot
$previewNoticeSource = Resolve-PreviewNoticePath -ResolvedPackageRoot $PackageRoot
$previewNoticePath = Join-Path $InstallBase "PREVIEW_NOTICE.txt"
$manifestPath = Join-Path $PackageRoot ".codex-plugin\plugin.json"
if (-not (Test-Path -LiteralPath $manifestPath)) { throw "Plugin manifest missing: $manifestPath" }
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.name -ne "archflow-studio") { throw "Unexpected plugin name: $($manifest.name)" }
$version = [string]$manifest.version
$versionsRoot = Join-Path $InstallBase "versions"
$versionRoot = Join-Path $versionsRoot $version
$installedPlugin = Join-Path $versionRoot "archflow-studio"
$backupRoot = Join-Path $InstallBase "backups"
$statePath = Join-Path $InstallBase "install-state.json"
Assert-UnderPath -Path $versionRoot -Parent $InstallBase -Label "Version root"

Write-Host "ArchFlow Studio Setup"
Write-Host "Action: $Action"
Write-Host "Version: $version"
Write-Host "Payload: $PackageRoot"
Write-Host "Install: $installedPlugin"
Write-Host "Codex plugin link: $UserPluginPath"
Write-Host "Marketplace: $MarketplacePath"
Write-Host "Configure CAD/SketchUp: $ConfigureApplications"
Write-Host ""
Write-Host (Read-PreviewNotice -Path $previewNoticeSource) -ForegroundColor Yellow
Write-Host ""

if ($Action -eq "Plan") {
    Write-Host "Plan complete. No files were changed."
    exit 0
}

if ($Action -in @("Install", "Repair")) {
    $existingPlugin = Get-Item -LiteralPath $UserPluginPath -Force -ErrorAction SilentlyContinue
    if ($existingPlugin) {
        Remove-ManagedJunction -Path $UserPluginPath -AllowedTargetRoot $InstallBase
    }
    if (Test-Path -LiteralPath $versionRoot) {
        if ($Action -eq "Install") { throw "Version $version is already installed. Use -Action Repair." }
        $stamp = Get-Date -Format "yyyyMMddHHmmss"
        $backupVersion = Join-Path $backupRoot ("version-" + $version + "-" + $stamp)
        New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
        Move-Item -LiteralPath $versionRoot -Destination $backupVersion
    }
    New-Item -ItemType Directory -Force -Path $versionRoot | Out-Null
    Copy-Item -LiteralPath $PackageRoot -Destination $installedPlugin -Recurse -Force

    New-Item -ItemType Directory -Force -Path (Split-Path $UserPluginPath -Parent) | Out-Null
    New-Item -ItemType Junction -Path $UserPluginPath -Target $installedPlugin | Out-Null
    Update-PersonalMarketplace -Path $MarketplacePath -InstallEntry $true -BackupRoot $backupRoot
    Write-PreviewNoticeForUser -Source $previewNoticeSource -Destination $previewNoticePath

    $state = [pscustomobject]@{
        schema_version = "0.1"
        product = "ArchFlow Studio"
        official_website = "https://archflow.best"
        version = $version
        installed_at = (Get-Date).ToUniversalTime().ToString("o")
        install_root = $installedPlugin
        user_plugin_path = $UserPluginPath
        marketplace_path = $MarketplacePath
        preview_notice_path = $previewNoticePath
        applications_configured = [bool]$ConfigureApplications
    }
    Write-JsonAtomic -Path $statePath -Value $state

    if ($ConfigureApplications) {
        $setup = Join-Path $installedPlugin "skills\archflow-studio\scripts\setup_workstation.ps1"
        if (-not (Test-Path -LiteralPath $setup)) { throw "Bundled workstation setup is missing: $setup" }
        & powershell -NoProfile -ExecutionPolicy Bypass -File $setup -Apply -ProjectRoot (Join-Path $InstallBase "native")
        if ($LASTEXITCODE -ne 0) { throw "Workstation configuration failed with exit code $LASTEXITCODE" }
    }

    Write-Host "Install complete. Restart Codex and open a new task before testing the plugin."
    exit 0
}

if ($Action -eq "Uninstall") {
    Remove-ManagedJunction -Path $UserPluginPath -AllowedTargetRoot $InstallBase
    Update-PersonalMarketplace -Path $MarketplacePath -InstallEntry $false -BackupRoot $backupRoot
    if (Test-Path -LiteralPath $versionRoot) {
        Assert-UnderPath -Path $versionRoot -Parent $InstallBase -Label "Uninstall target"
        Remove-Item -LiteralPath $versionRoot -Recurse -Force
    }
    if (Test-Path -LiteralPath $statePath) { Remove-Item -LiteralPath $statePath -Force }
    if (Test-Path -LiteralPath $previewNoticePath) { Remove-Item -LiteralPath $previewNoticePath -Force }
    if ($Purge) {
        $resolvedBase = [System.IO.Path]::GetFullPath($InstallBase).TrimEnd("\")
        $expectedBase = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "ArchFlow")).TrimEnd("\")
        if ($resolvedBase -ne $expectedBase) { throw "-Purge is limited to the default ArchFlow install root." }
        if (Test-Path -LiteralPath $InstallBase) { Remove-Item -LiteralPath $InstallBase -Recurse -Force }
    }
    Write-Host "Uninstall complete. Existing CAD/SketchUp adapter files are retained for safety in version 0.1."
    exit 0
}

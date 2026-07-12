$script:ArchFlowLicense = "Apache-2.0"

$script:DefaultCadProgIds = @(
    "AutoCAD.Application.23.1",
    "AutoCAD.Application",
    "AutoCAD.Application.23",
    "BricscadApp.AcadApplication",
    "ZWCAD.Application",
    "GstarCAD.Application"
)

$script:CadProgIdPrefixes = @(
    "AutoCAD.Application",
    "BricscadApp.AcadApplication",
    "ZWCAD.Application",
    "GstarCAD.Application"
)

function Add-UniqueString {
    param(
        [System.Collections.ArrayList]$Items,
        [hashtable]$Seen,
        [string]$Value
    )

    if ($Value -and -not $Seen.ContainsKey($Value)) {
        [void]$Items.Add($Value)
        $Seen[$Value] = $true
    }
}

function Get-RegisteredCadProgIds {
    [CmdletBinding()]
    param()

    $Roots = @(
        "HKCU:\Software\Classes",
        "HKLM:\SOFTWARE\Classes",
        "HKLM:\SOFTWARE\WOW6432Node\Classes"
    )
    $Found = New-Object System.Collections.ArrayList
    $Seen = @{}

    foreach ($Root in $Roots) {
        if (-not (Test-Path $Root)) {
            continue
        }

        foreach ($Prefix in $script:CadProgIdPrefixes) {
            $ExactPath = Join-Path $Root $Prefix
            if (Test-Path $ExactPath) {
                Add-UniqueString -Items $Found -Seen $Seen -Value $Prefix
            }
        }

        try {
            foreach ($Key in (Get-ChildItem -Path $Root -ErrorAction SilentlyContinue)) {
                foreach ($Prefix in $script:CadProgIdPrefixes) {
                    if ($Key.PSChildName -like "$Prefix.*") {
                        Add-UniqueString -Items $Found -Seen $Seen -Value $Key.PSChildName
                    }
                }
            }
        } catch {}
    }

    return @($Found)
}

function Get-CadProgIds {
    [CmdletBinding()]
    param([string[]]$ProgId)

    if ($ProgId -and $ProgId.Count -gt 0) {
        return $ProgId
    }

    $Ordered = New-Object System.Collections.ArrayList
    $Seen = @{}

    foreach ($Id in $script:DefaultCadProgIds) {
        Add-UniqueString -Items $Ordered -Seen $Seen -Value $Id
    }

    foreach ($Id in (Get-RegisteredCadProgIds)) {
        Add-UniqueString -Items $Ordered -Seen $Seen -Value $Id
    }

    return @($Ordered)
}

function Get-ComProperty {
    param(
        [object]$Object,
        [string]$Name,
        [object]$Default = $null
    )

    if ($null -eq $Object) {
        return $Default
    }

    try {
        return $Object.$Name
    } catch {
        return $Default
    }
}

function Get-ActiveCadComObject {
    param([string]$ProgId)

    try {
        return [Runtime.InteropServices.Marshal]::GetActiveObject($ProgId)
    } catch {
        return $null
    }
}

function Connect-Cad {
    [CmdletBinding()]
    param(
        [string[]]$ProgId,
        [switch]$Launch
    )

    $Errors = @()

    foreach ($Id in (Get-CadProgIds -ProgId $ProgId)) {
        $App = Get-ActiveCadComObject -ProgId $Id
        if ($null -ne $App) {
            try { $App.Visible = $true } catch {}
            return [pscustomobject]@{
                application = $App
                progId = $Id
                launched = $false
            }
        }

        if ($Launch) {
            try {
                $App = New-Object -ComObject $Id
                try { $App.Visible = $true } catch {}
                return [pscustomobject]@{
                    application = $App
                    progId = $Id
                    launched = $true
                }
            } catch {
                $Errors += "$Id launch failed: $($_.Exception.Message)"
            }
        } else {
            $Errors += "$Id has no active instance."
        }
    }

    $Hint = "Open CAD first, or rerun with -Launch if the user explicitly allows Codex to start CAD."
    throw "No supported CAD COM application found. $Hint Details: $($Errors -join ' | ')"
}

function Get-ActiveCadDocument {
    param([object]$Application)

    try {
        return $Application.ActiveDocument
    } catch {
        return $null
    }
}

function Open-CadDrawing {
    [CmdletBinding()]
    param(
        [string[]]$ProgId,
        [Parameter(Mandatory = $true)]
        [Alias("Path")]
        [string]$DrawingPath,
        [switch]$Launch
    )

    $Connection = Connect-Cad -ProgId $ProgId -Launch:$Launch
    $FullPath = [System.IO.Path]::GetFullPath($DrawingPath)

    if (-not (Test-Path $FullPath)) {
        throw "Drawing not found: $FullPath"
    }

    $Doc = $Connection.application.Documents.Open($FullPath)

    return [pscustomobject]@{
        ok = $true
        progId = $Connection.progId
        launched = $Connection.launched
        documentName = (Get-ComProperty -Object $Doc -Name "Name")
        documentPath = (Get-ComProperty -Object $Doc -Name "FullName")
    }
}

function Get-CadStatus {
    [CmdletBinding()]
    param(
        [string[]]$ProgId,
        [switch]$Launch
    )

    $Connection = Connect-Cad -ProgId $ProgId -Launch:$Launch
    $App = $Connection.application
    $Doc = Get-ActiveCadDocument -Application $App

    return [pscustomobject]@{
        ok = $true
        progId = $Connection.progId
        launched = $Connection.launched
        applicationName = (Get-ComProperty -Object $App -Name "Name")
        applicationVersion = (Get-ComProperty -Object $App -Name "Version")
        visible = (Get-ComProperty -Object $App -Name "Visible")
        hasActiveDocument = ($null -ne $Doc)
        documentName = (Get-ComProperty -Object $Doc -Name "Name")
        documentPath = (Get-ComProperty -Object $Doc -Name "FullName")
        readOnly = (Get-ComProperty -Object $Doc -Name "ReadOnly")
        saved = (Get-ComProperty -Object $Doc -Name "Saved")
    }
}

function ConvertTo-CadPathForLisp {
    param([string]$Path)

    return ([System.IO.Path]::GetFullPath($Path)).Replace("\", "/").Replace('"', '\"')
}

function Invoke-CadCommand {
    [CmdletBinding()]
    param(
        [string[]]$ProgId,
        [string]$Command,
        [string]$CommandFile,
        [switch]$Launch
    )

    if ($CommandFile) {
        $CommandFile = [System.IO.Path]::GetFullPath($CommandFile)
        if (-not (Test-Path $CommandFile)) {
            throw "Command file not found: $CommandFile"
        }
        $Command = Get-Content -Raw -LiteralPath $CommandFile
    }

    if (-not $Command) {
        throw "Missing -Command or -CommandFile."
    }

    $Connection = Connect-Cad -ProgId $ProgId -Launch:$Launch
    $Doc = Get-ActiveCadDocument -Application $Connection.application
    if ($null -eq $Doc) {
        throw "CAD is connected, but no active document is available."
    }

    if (-not $Command.EndsWith("`n")) {
        $Command = "$Command`n"
    }

    $Doc.SendCommand($Command)

    return [pscustomobject]@{
        ok = $true
        progId = $Connection.progId
        launched = $Connection.launched
        commandQueued = $true
        note = "CAD SendCommand is usually asynchronous. Verify with status/export after it completes."
    }
}

function Load-CadLispPlugin {
    [CmdletBinding()]
    param(
        [string[]]$ProgId,
        [string]$LispPath,
        [switch]$Launch
    )

    if (-not $LispPath) {
        $SkillRoot = Split-Path -Parent $PSScriptRoot
        $LispPath = Join-Path $SkillRoot "assets\codex_cad_bridge.lsp"
    }

    $FullPath = [System.IO.Path]::GetFullPath($LispPath)
    if (-not (Test-Path $FullPath)) {
        throw "AutoLISP plugin not found: $FullPath"
    }

    $CadPath = ConvertTo-CadPathForLisp -Path $FullPath
    $Command = "(load `"$CadPath`")"

    $Result = Invoke-CadCommand -ProgId $ProgId -Command $Command -Launch:$Launch
    $Result | Add-Member -NotePropertyName lispPath -NotePropertyValue $FullPath -Force
    return $Result
}

function Export-CadContext {
    [CmdletBinding()]
    param(
        [string[]]$ProgId,
        [string]$DrawingPath,
        [Parameter(Mandatory = $true)]
        [string]$OutputPath,
        [switch]$Launch
    )

    $Connection = Connect-Cad -ProgId $ProgId -Launch:$Launch
    $App = $Connection.application

    if ($DrawingPath) {
        $FullDrawingPath = [System.IO.Path]::GetFullPath($DrawingPath)
        if (-not (Test-Path $FullDrawingPath)) {
            throw "Drawing not found: $FullDrawingPath"
        }
        $Doc = $App.Documents.Open($FullDrawingPath)
    } else {
        $Doc = Get-ActiveCadDocument -Application $App
    }

    if ($null -eq $Doc) {
        throw "CAD is connected, but no active document is available."
    }

    $Layers = @()
    try {
        foreach ($Layer in $Doc.Layers) {
            $Layers += [pscustomobject]@{
                name = (Get-ComProperty -Object $Layer -Name "Name")
                color = (Get-ComProperty -Object $Layer -Name "Color")
                linetype = (Get-ComProperty -Object $Layer -Name "Linetype")
                isOn = (Get-ComProperty -Object $Layer -Name "LayerOn")
                isFrozen = (Get-ComProperty -Object $Layer -Name "Freeze")
                isLocked = (Get-ComProperty -Object $Layer -Name "Lock")
            }
        }
    } catch {}

    $Layouts = @()
    try {
        foreach ($Layout in $Doc.Layouts) {
            $Layouts += [pscustomobject]@{
                name = (Get-ComProperty -Object $Layout -Name "Name")
                tabOrder = (Get-ComProperty -Object $Layout -Name "TabOrder")
            }
        }
    } catch {}

    $Blocks = @()
    try {
        foreach ($Block in $Doc.Blocks) {
            $Blocks += [pscustomobject]@{
                name = (Get-ComProperty -Object $Block -Name "Name")
                isLayout = (Get-ComProperty -Object $Block -Name "IsLayout")
                count = (Get-ComProperty -Object $Block -Name "Count")
            }
        }
    } catch {}

    $Counts = @{}
    $Samples = @()
    $Total = 0

    try {
        foreach ($Entity in $Doc.ModelSpace) {
            $Type = Get-ComProperty -Object $Entity -Name "ObjectName" -Default "Unknown"
            if (-not $Counts.ContainsKey($Type)) {
                $Counts[$Type] = 0
            }
            $Counts[$Type] += 1
            $Total += 1

            if ($Samples.Count -lt 50) {
                $Samples += [pscustomobject]@{
                    type = $Type
                    handle = (Get-ComProperty -Object $Entity -Name "Handle")
                    layer = (Get-ComProperty -Object $Entity -Name "Layer")
                }
            }
        }
    } catch {}

    $EntityCounts = @()
    foreach ($Entry in ($Counts.GetEnumerator() | Sort-Object Name)) {
        $EntityCounts += [pscustomobject]@{
            type = $Entry.Key
            count = $Entry.Value
        }
    }

    $Context = [ordered]@{
        exportedAt = (Get-Date).ToString("o")
        progId = $Connection.progId
        launched = $Connection.launched
        application = [ordered]@{
            name = (Get-ComProperty -Object $App -Name "Name")
            version = (Get-ComProperty -Object $App -Name "Version")
        }
        document = [ordered]@{
            name = (Get-ComProperty -Object $Doc -Name "Name")
            path = (Get-ComProperty -Object $Doc -Name "FullName")
            readOnly = (Get-ComProperty -Object $Doc -Name "ReadOnly")
            saved = (Get-ComProperty -Object $Doc -Name "Saved")
        }
        layers = $Layers
        layouts = $Layouts
        blocks = $Blocks
        modelSpaceEntityTotal = $Total
        modelSpaceEntityCounts = $EntityCounts
        modelSpaceSamples = $Samples
    }

    $FullOutputPath = [System.IO.Path]::GetFullPath($OutputPath)
    $OutputDir = Split-Path -Parent $FullOutputPath
    if ($OutputDir) {
        New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    }

    $Context | ConvertTo-Json -Depth 10 | Set-Content -Path $FullOutputPath -Encoding UTF8

    return [pscustomobject]@{
        ok = $true
        outputPath = $FullOutputPath
        progId = $Connection.progId
        documentName = $Context.document.name
        documentPath = $Context.document.path
        layerCount = $Layers.Count
        layoutCount = $Layouts.Count
        blockCount = $Blocks.Count
        modelSpaceEntityTotal = $Total
    }
}

function Test-CadBridge {
    [CmdletBinding()]
    param(
        [string[]]$ProgId,
        [switch]$Launch
    )

    $Items = @()

    foreach ($Id in (Get-CadProgIds -ProgId $ProgId)) {
        $Active = $false
        $Launchable = $false
        $ErrorMessage = $null

        $App = Get-ActiveCadComObject -ProgId $Id
        if ($null -ne $App) {
            $Active = $true
        } elseif ($Launch) {
            try {
                $App = New-Object -ComObject $Id
                $Launchable = $true
                try { $App.Visible = $true } catch {}
            } catch {
                $ErrorMessage = $_.Exception.Message
            }
        }

        $Items += [pscustomobject]@{
            progId = $Id
            active = $Active
            launchTested = [bool]$Launch
            launchable = $Launchable
            applicationName = (Get-ComProperty -Object $App -Name "Name")
            applicationVersion = (Get-ComProperty -Object $App -Name "Version")
            error = $ErrorMessage
        }
    }

    $SkillRoot = Split-Path -Parent $PSScriptRoot
    $LispPath = Join-Path $SkillRoot "assets\codex_cad_bridge.lsp"

    return [pscustomobject]@{
        ok = $true
        powershell = [pscustomobject]@{
            version = $PSVersionTable.PSVersion.ToString()
            edition = $PSVersionTable.PSEdition
        }
        lispPluginExists = (Test-Path $LispPath)
        lispPluginPath = $LispPath
        preferredTarget = "AutoCAD 2020 Simplified Chinese via AutoCAD.Application.23.1"
        orderedProgIds = @(Get-CadProgIds -ProgId $ProgId)
        discoveredProgIds = @(Get-RegisteredCadProgIds)
        progIds = $Items
        hint = "If all ProgIDs are inactive, open CAD first or rerun with -Launch after user approval."
    }
}

Export-ModuleMember -Function @(
    "Connect-Cad",
    "Get-CadProgIds",
    "Get-RegisteredCadProgIds",
    "Get-CadStatus",
    "Export-CadContext",
    "Invoke-CadCommand",
    "Load-CadLispPlugin",
    "Open-CadDrawing",
    "Test-CadBridge"
)

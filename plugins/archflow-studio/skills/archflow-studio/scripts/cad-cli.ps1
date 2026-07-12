# SPDX-FileCopyrightText: 2026 OHDESIGN
# SPDX-License-Identifier: Apache-2.0

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("diagnose", "progids", "status", "export", "open", "command", "load-plugin")]
    [string]$Action = "status",

    [string]$DrawingPath,
    [string]$OutputPath,
    [string]$Command,
    [string]$CommandFile,
    [string]$LispPath,
    [string[]]$ProgId,
    [switch]$Launch
)

$ErrorActionPreference = "Stop"

$ModulePath = Join-Path $PSScriptRoot "CadBridge.psm1"
Import-Module $ModulePath -Force -DisableNameChecking -WarningAction SilentlyContinue

switch ($Action) {
    "diagnose" {
        Test-CadBridge -ProgId $ProgId -Launch:$Launch | ConvertTo-Json -Depth 8
        break
    }

    "progids" {
        [pscustomobject]@{
            preferredTarget = "AutoCAD 2020 Simplified Chinese via AutoCAD.Application.23.1"
            orderedProgIds = @(Get-CadProgIds -ProgId $ProgId)
            discoveredProgIds = @(Get-RegisteredCadProgIds)
        } | ConvertTo-Json -Depth 8
        break
    }

    "status" {
        Get-CadStatus -ProgId $ProgId -Launch:$Launch | ConvertTo-Json -Depth 8
        break
    }

    "export" {
        if (-not $OutputPath) {
            $OutputPath = Join-Path (Get-Location) "cad-context.json"
        }
        Export-CadContext -ProgId $ProgId -DrawingPath $DrawingPath -OutputPath $OutputPath -Launch:$Launch | ConvertTo-Json -Depth 8
        break
    }

    "open" {
        if (-not $DrawingPath) {
            throw "Missing -DrawingPath for open."
        }
        Open-CadDrawing -ProgId $ProgId -DrawingPath $DrawingPath -Launch:$Launch | ConvertTo-Json -Depth 8
        break
    }

    "command" {
        Invoke-CadCommand -ProgId $ProgId -Command $Command -CommandFile $CommandFile -Launch:$Launch | ConvertTo-Json -Depth 8
        break
    }

    "load-plugin" {
        Load-CadLispPlugin -ProgId $ProgId -LispPath $LispPath -Launch:$Launch | ConvertTo-Json -Depth 8
        break
    }
}

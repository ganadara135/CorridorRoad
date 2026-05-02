param(
    [string]$FreeCADExe = "D:\Program Files\FreeCAD 1.0\bin\FreeCAD.exe",
    [string]$DocumentPath = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Text)
    Write-Host ("[CorridorRoad] " + $Text)
}

if (-not (Test-Path -LiteralPath $FreeCADExe)) {
    throw "FreeCAD executable not found: $FreeCADExe"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$recordPath = Join-Path $repoRoot "docsV1\V1_MAIN_REVIEW_COMMAND_MANUAL_RECORD.md"
$checklistPath = Join-Path $repoRoot "docsV1\V1_REAL_DOCUMENT_VIEWER_CHECKLIST.md"
$roundtripPath = Join-Path $repoRoot "docsV1\V1_VIEWER_ROUNDTRIP_MANUAL_QA.md"
$quickstartPath = Join-Path $repoRoot "docsV1\V1_MANUAL_QA_QUICKSTART.md"

$arguments = @()
if ($DocumentPath) {
    if (-not (Test-Path -LiteralPath $DocumentPath)) {
        throw "Document not found: $DocumentPath"
    }
    $arguments += $DocumentPath
}

Write-Step "FreeCAD GUI: $FreeCADExe"
if ($DocumentPath) {
    Write-Step "Document: $DocumentPath"
} else {
    Write-Step "Document: open manually after FreeCAD starts."
}
Write-Step "Quickstart: $quickstartPath"
Write-Step "Manual record: $recordPath"
Write-Step "Viewer checklist: $checklistPath"
Write-Step "Roundtrip QA: $roundtripPath"
Write-Step "Check these commands in order:"
Write-Step "  1. CorridorRoad_ViewCrossSection"
Write-Step "  2. CorridorRoad_ReviewPlanProfile"
Write-Step "  3. CorridorRoad_GenerateCutFillCalc"

if ($DryRun) {
    Write-Step "DryRun enabled. FreeCAD was not launched."
    exit 0
}

Start-Process -FilePath $FreeCADExe -ArgumentList $arguments | Out-Null
Write-Step "FreeCAD launch requested."

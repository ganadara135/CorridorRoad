param([string]$FreeCADBin = "")

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "freecad_environment.ps1")

$repoRoot = Split-Path -Parent $PSScriptRoot
Assert-CorridorRoadWorkbenchLayout -RepositoryRoot $repoRoot
$binPath = Resolve-FreeCADBin -ExplicitPath $FreeCADBin
$guiPath = Resolve-FreeCADExecutable -Kind GUI -ExplicitPath $binPath
$cmdPath = Resolve-FreeCADExecutable -Kind Cmd -ExplicitPath $binPath
$pythonPath = Resolve-FreeCADExecutable -Kind Python -ExplicitPath $binPath
$packagePath = Join-Path $repoRoot "freecad\Corridor_Road\InitGui.py"

Write-Host "[CorridorRoad] Repository     : $repoRoot"
Write-Host "[CorridorRoad] FREECAD_BIN    : $binPath"
Write-Host "[CorridorRoad] FreeCAD GUI    : $guiPath"
Write-Host "[CorridorRoad] FreeCADCmd     : $cmdPath"
Write-Host "[CorridorRoad] FreeCAD Python : $pythonPath"
Write-Host "[CorridorRoad] Workbench      : $packagePath"

if (-not (Test-Path -LiteralPath $packagePath -PathType Leaf)) {
    throw "CorridorRoad workbench entry point not found: $packagePath"
}

& $cmdPath --version
if ($LASTEXITCODE -ne 0) {
    throw "FreeCADCmd version check failed with exit code $LASTEXITCODE."
}

$expectedPackagePath = Join-Path $repoRoot "freecad\Corridor_Road\__init__.py"
$escapedExpectedPackagePath = $expectedPackagePath.Replace("'", "''")
$importCheck = @"
import os
import freecad.Corridor_Road as package
actual = os.path.normcase(os.path.realpath(package.__file__))
expected = os.path.normcase(os.path.realpath(r'$escapedExpectedPackagePath'))
print('[CorridorRoad] Imported package : ' + actual)
if actual != expected:
    raise RuntimeError('CorridorRoad import path mismatch: expected=' + expected + '; actual=' + actual)
"@

& $cmdPath -c $importCheck
if ($LASTEXITCODE -ne 0) {
    throw "CorridorRoad package import-path check failed with exit code $LASTEXITCODE."
}

Write-Host "[PASS] FreeCAD development environment is available."

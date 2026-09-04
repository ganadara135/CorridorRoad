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

# Record the resolved runtime identity so an interpreter or FreeCAD upgrade is
# visible in validation logs instead of being discovered later as a test failure.
$runtimeReport = @"
import sys

print('[CorridorRoad] Python version  : ' + sys.version.split()[0])
print('[CorridorRoad] Python prefix   : ' + sys.prefix)

import FreeCAD

version = FreeCAD.Version()
print('[CorridorRoad] FreeCAD API     : ' + '.'.join(version[0:3]))
print('[CorridorRoad] FreeCAD build   : ' + str(version[5]))
"@

& $pythonPath -c $runtimeReport
if ($LASTEXITCODE -ne 0) {
    throw "FreeCAD runtime report failed for the resolved interpreter: $pythonPath"
}

# Development dependencies live in the user site directory of the resolved
# interpreter, outside the FreeCAD installation. They have been lost at least
# once without any other visible symptom, which silently disabled every
# validation tier except Compile. Fail loudly instead.
$developmentDependencyCheck = @"
import importlib

missing = []
for module_name in ('pytest', 'flake8'):
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        missing.append(module_name)
        continue
    label = '[CorridorRoad] ' + (module_name + ' version').ljust(15) + ': '
    print(label + str(getattr(module, '__version__', 'unknown')))

if missing:
    raise SystemExit('missing: ' + ', '.join(missing))
"@

& $pythonPath -c $developmentDependencyCheck
if ($LASTEXITCODE -ne 0) {
    throw @"
Development dependencies are not available in the resolved FreeCAD interpreter:
  $pythonPath

Without them the Lint, Architecture, Fast, Contracts, and Full validation tiers
cannot run, and only Compile remains usable. Reinstall through the same
interpreter before running any validation tier:

  & "$pythonPath" -m pip install -r requirements-dev.txt
"@
}

Write-Host "[PASS] FreeCAD development environment is available."

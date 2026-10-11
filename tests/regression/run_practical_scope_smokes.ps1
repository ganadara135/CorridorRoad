param(
    [string]$FreeCADCmdPath = ""
)

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $repoRoot "scripts\freecad_environment.ps1")
Assert-CorridorRoadWorkbenchLayout -RepositoryRoot $repoRoot
$resolvedFreeCADCmd = Resolve-FreeCADExecutable -Kind Cmd -ExplicitPath $FreeCADCmdPath
Set-Location $repoRoot

$tests = @(
    "tests/regression/smoke_intersection_t_slope_face_surface.py",
    "tests/regression/smoke_intersection_non_t_slope_face_readiness.py"
)

foreach ($test in $tests) {
    Write-Host "==> $test"
    & $resolvedFreeCADCmd -c "exec(open(r'$test', 'r', encoding='utf-8').read())"
    if ($LASTEXITCODE -ne 0) {
        throw "Regression failed: $test"
    }
}

Write-Host "[PASS] Practical-scope regression set completed."

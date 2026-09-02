param(
    [string]$FreeCADCmdPath = ""
)

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $repoRoot "scripts\freecad_environment.ps1")
Assert-CorridorRoadWorkbenchLayout -RepositoryRoot $repoRoot
$resolvedFreeCADCmd = Resolve-FreeCADExecutable -Kind Cmd -ExplicitPath $FreeCADCmdPath
Set-Location $repoRoot

$tests = @(
    "tests/regression/smoke_corridor_compat_aliases.py",
    "tests/regression/smoke_corridor_command_alias_boundary.py",
    "tests/regression/smoke_corridor_taskpanel_alias_boundary.py",
    "tests/regression/smoke_corridor_project_link_boundary.py",
    "tests/regression/smoke_corridor_child_link_boundary.py",
    "tests/regression/smoke_corridor_proxy_boundary.py",
    "tests/regression/smoke_corridor_fcstd_restore.py",
    "tests/regression/smoke_tree_schema.py"
)

foreach ($test in $tests) {
    Write-Host "==> $test"
    & $resolvedFreeCADCmd -c "exec(open(r'$test', 'r', encoding='utf-8').read())"
    if ($LASTEXITCODE -ne 0) {
        throw "Regression failed: $test"
    }
}

Write-Host "[PASS] Loft retirement gate regression set completed."

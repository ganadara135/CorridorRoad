param(
    [string]$FreeCADCmdPath = "FreeCADCmd"
)

$resolvedFreeCADCmd = $FreeCADCmdPath
if (-not (Get-Command $resolvedFreeCADCmd -ErrorAction SilentlyContinue)) {
    $fallbacks = @(
        "D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",
        "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
        "C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",
        "C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe"
    )
    foreach ($candidate in $fallbacks) {
        if (Test-Path -LiteralPath $candidate) {
            $resolvedFreeCADCmd = $candidate
            break
        }
    }
}

if (-not (Get-Command $resolvedFreeCADCmd -ErrorAction SilentlyContinue) -and -not (Test-Path -LiteralPath $resolvedFreeCADCmd)) {
    throw "FreeCADCmd executable not found. Pass -FreeCADCmdPath or install FreeCADCmd in a standard location."
}

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

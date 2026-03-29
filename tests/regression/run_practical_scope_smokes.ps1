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
    "tests/regression/smoke_typical_section_pipeline.py",
    "tests/regression/smoke_typical_section_pavement_report.py",
    "tests/regression/smoke_practical_subassembly_contract.py",
    "tests/regression/smoke_practical_roadside_library.py",
    "tests/regression/smoke_practical_report_contract.py",
    "tests/regression/smoke_practical_sample_driven_workflow.py",
    "tests/regression/smoke_structure_station_merge.py",
    "tests/regression/smoke_notch_profile_contract.py",
    "tests/regression/smoke_notch_neighbor_modes.py",
    "tests/regression/smoke_external_shape_earthwork_proxy.py",
    "tests/regression/smoke_cutfill_source_matrix.py",
    "tests/regression/smoke_cutfill_quality_review.py"
)

foreach ($test in $tests) {
    Write-Host "==> $test"
    & $resolvedFreeCADCmd -c "exec(open(r'$test', 'r', encoding='utf-8').read())"
    if ($LASTEXITCODE -ne 0) {
        throw "Regression failed: $test"
    }
}

Write-Host "[PASS] Practical-scope regression set completed."

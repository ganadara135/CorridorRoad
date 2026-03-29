param(
    [string]$FreeCADCmdPath = "FreeCADCmd"
)

$tests = @(
    "tests/regression/smoke_tree_schema.py",
    "tests/regression/smoke_structure_corridor_diagnostics.py",
    "tests/regression/smoke_structure_recompute_chain.py",
    "tests/regression/smoke_typical_section_pipeline.py",
    "tests/regression/smoke_structure_station_merge.py",
    "tests/regression/smoke_skip_zone_boundary_behavior.py",
    "tests/regression/smoke_legacy_simple_workflow.py",
    "tests/regression/smoke_daylight_coordinate_modes.py",
    "tests/regression/smoke_daylight_fallback_status.py"
)

foreach ($test in $tests) {
    Write-Host "==> $test"
    & $FreeCADCmdPath -c "exec(open(r'$test', 'r', encoding='utf-8').read())"
    if ($LASTEXITCODE -ne 0) {
        throw "Regression failed: $test"
    }
}

Write-Host "[PASS] Short-term regression set completed."

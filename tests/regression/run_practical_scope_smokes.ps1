param(
    [string]$FreeCADCmdPath = ""
)

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $repoRoot "scripts\freecad_environment.ps1")
Assert-CorridorRoadWorkbenchLayout -RepositoryRoot $repoRoot
$resolvedFreeCADCmd = Resolve-FreeCADExecutable -Kind Cmd -ExplicitPath $FreeCADCmdPath
Set-Location $repoRoot

$tests = @(
    "tests/regression/smoke_typical_section_pipeline.py",
    "tests/regression/smoke_typical_section_pavement_report.py",
    "tests/regression/smoke_practical_subassembly_contract.py",
    "tests/regression/smoke_practical_roadside_library.py",
    "tests/regression/smoke_practical_report_contract.py",
    "tests/regression/smoke_practical_sample_driven_workflow.py",
    "tests/regression/smoke_intersection_t_slope_face_surface.py",
    "tests/regression/smoke_intersection_non_t_slope_face_readiness.py",
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

param(
    [ValidateSet("Compile", "Lint", "Architecture", "Fast", "Contracts", "ContractsFull", "Smokes", "Full")]
    [string]$Tier = "Full",
    [string]$FreeCADBin = ""
)

# Four contract modules account for roughly three quarters of the full contract
# run. Measured on 2026-09-02: the complete suite is 1462 tests in 390s, and the
# 60 slowest tests alone consume 286s, of which these modules contribute 267s.
# The Contracts tier skips them so it stays usable as a routine gate; the
# ContractsFull tier runs everything and is the release-facing level.
# See docsV1/V1_ARCHITECTURE_DEBT_EXECUTION_PLAN.md section 5.1.
$HeavyContractModules = @(
    "tests/contracts/v1/test_intersection_command.py",
    "tests/contracts/v1/test_build_corridor_command.py",
    "tests/contracts/v1/test_drainage_editor_command.py",
    "tests/contracts/v1/test_tin_review_command.py"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "freecad_environment.ps1")

$repoRoot = Split-Path -Parent $PSScriptRoot
Assert-CorridorRoadWorkbenchLayout -RepositoryRoot $repoRoot
$pythonPath = Resolve-FreeCADExecutable -Kind Python -ExplicitPath $FreeCADBin
$cmdPath = Resolve-FreeCADExecutable -Kind Cmd -ExplicitPath $FreeCADBin
Set-Location $repoRoot

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )

    Write-Host "==> $Label"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

function Invoke-CompileValidation {
    Invoke-CheckedCommand -Label "Python compile validation" -Command {
        & $pythonPath -m compileall -q freecad tests
    }
}

function Invoke-LintValidation {
    Invoke-CheckedCommand -Label "flake8 validation" -Command {
        & $pythonPath -m flake8 freecad tests
    }
}

function Invoke-ContractValidation {
    $ignoreArguments = @()
    foreach ($module in $HeavyContractModules) {
        $ignoreArguments += "--ignore=$module"
    }
    Write-Host "    skipping long-running modules: $($HeavyContractModules -join ', ')"
    Invoke-CheckedCommand -Label "v1 contract tests (fast subset)" -Command {
        & $pythonPath scripts/run_pytest_with_qt.py -q tests/contracts/v1 @ignoreArguments
    }
}

function Invoke-FullContractValidation {
    Invoke-CheckedCommand -Label "v1 contract tests (complete)" -Command {
        & $pythonPath scripts/run_pytest_with_qt.py -q tests/contracts/v1
    }
}

function Invoke-ArchitectureValidation {
    Invoke-CheckedCommand -Label "v1 architecture boundary tests" -Command {
        & $pythonPath -m pytest -q tests/architecture
    }
}

function Invoke-FastValidation {
    Invoke-CompileValidation
    Invoke-ArchitectureValidation
    Invoke-CheckedCommand -Label "focused v1 contract tests" -Command {
        & $pythonPath scripts/run_pytest_with_qt.py -q `
            tests/contracts/v1/test_alignment_evaluation_service.py `
            tests/contracts/v1/test_profile_evaluation_service.py `
            tests/contracts/v1/test_region_resolution_service.py `
            tests/contracts/v1/test_project_tree_redesign.py `
            tests/contracts/v1/test_command_bridge.py `
            tests/contracts/v1/test_earthwork_command_v1_report.py `
            tests/contracts/v1/test_supplemental_frame_sampling.py `
            tests/contracts/v1/test_subassembly_bench_profile_service.py `
            tests/contracts/v1/test_section_preview_consistency.py `
            tests/contracts/v1/test_centerline3d_source_geometry_service.py `
            tests/contracts/v1/test_project_document_adapter.py `
            tests/contracts/v1/test_versioned_model_persistence.py `
            tests/contracts/v1/test_persistence_payload_object_adapters.py `
            tests/contracts/v1/test_incremental_rebuild_service.py `
            tests/contracts/v1/test_supported_output_traceability.py `
            tests/contracts/v1/test_station_highlight_presentation_service.py `
            tests/contracts/v1/test_structure_editor_presentation_boundary.py `
            tests/contracts/v1/test_editor_source_edit_service.py `
            tests/contracts/v1/test_phase3_editor_panel_boundaries.py `
            "tests/contracts/v1/test_v1_profile_editor.py::test_profile_editor_uses_auto_interpolate_without_random_elevation_button" `
            "tests/contracts/v1/test_v1_alignment_editor.py::test_alignment_editor_apply_snapshots_project_design_standard" `
            "tests/contracts/v1/test_subassembly_editor_command.py::test_subassembly_detail_changes_only_on_table_row_click" `
            "tests/contracts/v1/test_drainage_editor_command.py::test_drainage_editor_apply_blocks_error_validation" `
            "tests/contracts/v1/test_drainage_review_command.py::test_drainage_review_panel_loads_document_context" `
            "tests/contracts/v1/test_tin_editor_command.py::test_tin_editor_uses_apply_as_single_write_button" `
            "tests/contracts/v1/test_tin_editor_command.py::test_tin_editor_apply_applies_current_editor_state_without_rebuilding_source" `
            "tests/contracts/v1/test_tin_editor_command.py::test_tin_face_pick_observer_forwards_selection_events_to_panel" `
            tests/contracts/v1/test_xy_geometry_primitives.py `
            tests/contracts/v1/test_polygon_triangulation_service.py `
            tests/contracts/v1/test_convex_polygon_clipping_service.py `
            tests/contracts/v1/test_segment_geometry_service.py `
            tests/contracts/v1/test_polygon_relations_service.py `
            tests/contracts/v1/test_polygon_topology_service.py `
            tests/contracts/v1/test_polygon_boundary_service.py `
            tests/contracts/v1/test_corridor_surface_orchestration_service.py `
            tests/contracts/v1/test_shared_breakline_audit_service.py `
            tests/contracts/v1/test_intersection_surface_patch_build_service.py `
            tests/contracts/v1/test_intersection_patch_input_preparation_service.py `
            tests/contracts/v1/test_intersection_patch_grading_service.py `
            tests/contracts/v1/test_intersection_patch_boundary_selection_service.py `
            tests/contracts/v1/test_intersection_patch_triangulation_service.py `
            tests/contracts/v1/test_intersection_patch_shape_quality_service.py `
            tests/contracts/v1/test_intersection_patch_drainage_review_service.py `
            tests/contracts/v1/test_intersection_patch_boundary_context_service.py `
            tests/contracts/v1/test_intersection_patch_constraint_build_service.py `
            tests/contracts/v1/test_intersection_patch_tin_assembly_service.py `
            tests/contracts/v1/test_intersection_patch_pipeline_service.py `
            tests/contracts/v1/test_intersection_patch_preparation_pipeline_service.py `
            tests/contracts/v1/test_intersection_tie_in_edge_evaluation_service.py `
            tests/contracts/v1/test_intersection_boundary_segment_evaluation_service.py `
            tests/contracts/v1/test_intersection_patch_boundary_evaluation_service.py `
            tests/contracts/v1/test_intersection_boundary_loop_evaluation_service.py `
            tests/contracts/v1/test_intersection_shared_breakline_service.py `
            tests/contracts/v1/test_intersection_slope_face_topology_services.py `
            tests/contracts/v1/test_build_corridor_tin_builder_services.py `
            tests/contracts/v1/test_build_corridor_presentation_boundaries.py `
            "tests/contracts/v1/test_structure_editor_command.py::test_structure_editor_normalizes_connection_points_after_station_edits" `
            "tests/contracts/v1/test_structure_editor_command.py::test_structure_editor_reopens_with_applied_rows_and_selected_detail" `
            "tests/contracts/v1/test_structure_editor_command.py::test_apply_v1_structure_model_creates_structure_source_object_only" `
            "tests/contracts/v1/test_structure_editor_command.py::test_show_v1_structure_preview_object_creates_visible_3d_preview" `
            "tests/contracts/v1/test_v1_stationing_source_object.py::test_create_v1_stationing_samples_alignment_rows" `
            "tests/contracts/v1/test_v1_stationing_source_object.py::test_v1_stationing_location_highlight_updates_single_marker" `
            "tests/contracts/v1/test_v1_stationing_source_object.py::test_generate_v1_stations_routes_to_v1_station_folder" `
            "tests/contracts/v1/test_v1_stationing_source_object.py::test_v1_stationing_persists_source_rows_and_tree_routing_after_reopen" `
            "tests/contracts/v1/test_centerline3d_command.py::test_centerline3d_source_geometry_uses_arc_fit_for_curve_elements" `
            "tests/contracts/v1/test_centerline3d_command.py::test_centerline3d_source_geometry_rejects_poor_arc_fit" `
            "tests/contracts/v1/test_centerline3d_command.py::test_centerline3d_source_geometry_uses_part_arc_when_z_is_constant" `
            "tests/contracts/v1/test_centerline3d_command.py::test_centerline3d_source_geometry_curve_sampling_is_dense_and_unsmoothed" `
            "tests/contracts/v1/test_centerline3d_command.py::test_centerline3d_frame_service_prefers_source_geometry_when_sources_are_available" `
            "tests/contracts/v1/test_build_corridor_command.py::test_intersection_tie_in_generated_section_projects_to_nearest_alignment_span" `
            "tests/contracts/v1/test_applied_sections_command.py::test_intersection_supplemental_stations_are_added_to_applied_sections"
    }
}

function Invoke-SmokeValidation {
    Write-Host "==> Short-term FreeCAD smoke tests"
    & (Join-Path $repoRoot "tests\regression\run_short_term_smokes.ps1") -FreeCADCmdPath $cmdPath
    if ($LASTEXITCODE -ne 0) {
        throw "Short-term FreeCAD smoke tests failed with exit code $LASTEXITCODE."
    }
}

switch ($Tier) {
    "Compile" { Invoke-CompileValidation }
    "Lint" { Invoke-LintValidation }
    "Architecture" { Invoke-ArchitectureValidation }
    "Fast" { Invoke-FastValidation }
    "Contracts" { Invoke-ContractValidation }
    "ContractsFull" { Invoke-FullContractValidation }
    "Smokes" { Invoke-SmokeValidation }
    "Full" {
        Invoke-CompileValidation
        Invoke-LintValidation
        Invoke-ArchitectureValidation
        Invoke-FullContractValidation
        Invoke-SmokeValidation
    }
}

Write-Host "[PASS] Local validation tier completed: $Tier"

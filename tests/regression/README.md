# Regression Tests

This folder contains headless-friendly regression scripts intended to run with `FreeCADCmd`.

## Naming

- Use `smoke_*.py` for fast, focused regressions that verify one contract or one dependency chain.
- Prefer one clearly scoped behavior per file.
- Reuse existing sample data where possible instead of embedding large fixtures inline.

## Test Types

- `smoke`: fast contract and dependency checks intended for frequent use.
- `functional`: broader workflow checks that may use more objects or sample inputs.
- `edge-case`: targeted regressions for failure handling, warnings, and boundary conditions.

## Minimum Short-Term Regression Set

Run these before merging short-term structure/corridor validation work:

1. `smoke_tree_schema.py`
2. `smoke_structure_corridor_diagnostics.py`
3. `smoke_structure_recompute_chain.py`
4. `smoke_typical_section_pipeline.py`
5. `smoke_typical_section_pavement_report.py`
6. `smoke_practical_subassembly_contract.py`
7. `smoke_practical_roadside_library.py`
8. `smoke_practical_report_contract.py`
9. `smoke_structure_station_merge.py`
10. `smoke_skip_zone_boundary_behavior.py`
11. `smoke_legacy_simple_workflow.py`
12. `smoke_daylight_coordinate_modes.py`
13. `smoke_daylight_fallback_status.py`
14. `smoke_side_slope_bench_profile.py`
15. `smoke_side_slope_multi_bench_profile.py`
16. `smoke_side_slope_bench_daylight.py`
17. `smoke_external_shape_earthwork_proxy.py`
18. `smoke_notch_profile_contract.py`
19. `smoke_notch_neighbor_modes.py`
20. `smoke_boolean_cut_scope_guard.py`
21. `smoke_cutfill_source_matrix.py`
22. `smoke_cutfill_quality_review.py`
23. `smoke_profile_fg_tools.py`
24. `smoke_pvi_starter_defaults.py`
25. `smoke_cross_section_viewer_payload.py`
26. `smoke_centerline3d_display_segmentation.py`
27. `smoke_alignment_transition_geometry.py`
28. `smoke_alignment_transition_downstream.py`

## How To Run

Prefer using `-c "exec(open(...).read())"` so the file is executed as Python script instead of being treated like a document argument.

If `FreeCADCmd` is on `PATH`:

```powershell
FreeCADCmd -c "exec(open(r'tests/regression/smoke_tree_schema.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_structure_corridor_diagnostics.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_structure_recompute_chain.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_typical_section_pipeline.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_typical_section_pavement_report.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_practical_subassembly_contract.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_practical_roadside_library.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_practical_report_contract.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_structure_station_merge.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_skip_zone_boundary_behavior.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_legacy_simple_workflow.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_daylight_coordinate_modes.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_daylight_fallback_status.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_side_slope_bench_profile.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_side_slope_multi_bench_profile.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_side_slope_bench_daylight.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_external_shape_earthwork_proxy.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_notch_profile_contract.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_notch_neighbor_modes.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_boolean_cut_scope_guard.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_cutfill_source_matrix.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_cutfill_quality_review.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_profile_fg_tools.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_pvi_starter_defaults.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_cross_section_viewer_payload.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_centerline3d_display_segmentation.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_alignment_transition_geometry.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_alignment_transition_downstream.py', 'r', encoding='utf-8').read())"
```

If you need an explicit executable path, use your local FreeCAD installation path:

```powershell
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_tree_schema.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_structure_corridor_diagnostics.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_structure_recompute_chain.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_typical_section_pipeline.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_typical_section_pavement_report.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_practical_subassembly_contract.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_practical_roadside_library.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_practical_report_contract.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_structure_station_merge.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_skip_zone_boundary_behavior.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_legacy_simple_workflow.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_daylight_coordinate_modes.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_daylight_fallback_status.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_side_slope_bench_profile.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_side_slope_multi_bench_profile.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_side_slope_bench_daylight.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_external_shape_earthwork_proxy.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_notch_profile_contract.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_notch_neighbor_modes.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_boolean_cut_scope_guard.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_cutfill_source_matrix.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_cutfill_quality_review.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_profile_fg_tools.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_pvi_starter_defaults.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_cross_section_viewer_payload.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_centerline3d_display_segmentation.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_alignment_transition_geometry.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_alignment_transition_downstream.py', 'r', encoding='utf-8').read())"
```

For a repeatable short-term pass, you can also use:

```powershell
powershell -ExecutionPolicy Bypass -File tests/regression/run_short_term_smokes.ps1 -FreeCADCmdPath 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe'
```

## Practical-Scope Regression Set

Run these when validating Long-Term item `8. Expand practical engineering scope`:

1. `smoke_typical_section_pipeline.py`
2. `smoke_typical_section_pavement_report.py`
3. `smoke_practical_subassembly_contract.py`
4. `smoke_practical_roadside_library.py`
5. `smoke_practical_report_contract.py`
6. `smoke_practical_sample_driven_workflow.py`
7. `smoke_structure_station_merge.py`
8. `smoke_notch_profile_contract.py`
9. `smoke_notch_neighbor_modes.py`
10. `smoke_external_shape_earthwork_proxy.py`
11. `smoke_cutfill_source_matrix.py`
12. `smoke_cutfill_quality_review.py`

For a repeatable practical-scope pass, use:

```powershell
powershell -ExecutionPolicy Bypass -File tests/regression/run_practical_scope_smokes.ps1 -FreeCADCmdPath 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe'
```

See [PRACTICAL_SAMPLE_SET.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/PRACTICAL_SAMPLE_SET.md) for the maintained practical sample inventory and scenario bundles.

If `FreeCADCmd` is not on `PATH`, the runner also tries common `FreeCAD 1.0` install locations on `C:` and `D:` automatically before failing.

## Scope Notes

- These scripts should fail loudly with `Exception` when a contract breaks.
- Keep them safe for GUI-less execution.
- Prefer validating status fields, dependency propagation, and object-link contracts before adding heavier geometry cases.

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
5. `smoke_structure_station_merge.py`
6. `smoke_skip_zone_boundary_behavior.py`
7. `smoke_legacy_simple_workflow.py`
8. `smoke_daylight_coordinate_modes.py`
9. `smoke_daylight_fallback_status.py`

## How To Run

Prefer using `-c "exec(open(...).read())"` so the file is executed as Python script instead of being treated like a document argument.

If `FreeCADCmd` is on `PATH`:

```powershell
FreeCADCmd -c "exec(open(r'tests/regression/smoke_tree_schema.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_structure_corridor_diagnostics.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_structure_recompute_chain.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_typical_section_pipeline.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_structure_station_merge.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_skip_zone_boundary_behavior.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_legacy_simple_workflow.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_daylight_coordinate_modes.py', 'r', encoding='utf-8').read())"
FreeCADCmd -c "exec(open(r'tests/regression/smoke_daylight_fallback_status.py', 'r', encoding='utf-8').read())"
```

If you need an explicit executable path, use your local FreeCAD installation path:

```powershell
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_tree_schema.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_structure_corridor_diagnostics.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_structure_recompute_chain.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_typical_section_pipeline.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_structure_station_merge.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_skip_zone_boundary_behavior.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_legacy_simple_workflow.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_daylight_coordinate_modes.py', 'r', encoding='utf-8').read())"
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_daylight_fallback_status.py', 'r', encoding='utf-8').read())"
```

For a repeatable short-term pass, you can also use:

```powershell
powershell -ExecutionPolicy Bypass -File tests/regression/run_short_term_smokes.ps1 -FreeCADCmdPath 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe'
```

## Scope Notes

- These scripts should fail loudly with `Exception` when a contract breaks.
- Keep them safe for GUI-less execution.
- Prefer validating status fields, dependency propagation, and object-link contracts before adding heavier geometry cases.

# Regression Tests

This folder contains headless-friendly regression scripts intended to run with `FreeCADCmd`.

## Naming

- Use `smoke_*.py` for fast, focused checks around one contract or one dependency chain.
- Prefer one clearly scoped behavior per file.
- Reuse sample data where possible instead of embedding large fixtures inline.

## Test Types

- `smoke`: fast contract and dependency checks intended for frequent use.
- `functional`: broader workflow checks that may use more objects or sample inputs.
- `edge-case`: targeted checks for failure handling, warnings, and boundary conditions.

## Recommended Runners

Use runner scripts instead of maintaining long copied command lists in this document.

Short-term regression pass:

```powershell
powershell -ExecutionPolicy Bypass -File tests/regression/run_short_term_smokes.ps1 -FreeCADCmdPath 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe'
```

Practical engineering scope:

```powershell
powershell -ExecutionPolicy Bypass -File tests/regression/run_practical_scope_smokes.ps1 -FreeCADCmdPath 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe'
```

If `FreeCADCmd` is not on `PATH`, the practical-scope runner also tries common `FreeCAD 1.0` install locations on `C:` and `D:` before failing.

## Running One Smoke

Prefer `-c "exec(open(...).read())"` so FreeCAD runs the Python file as a script.

```powershell
FreeCADCmd -c "exec(open(r'tests/regression/smoke_tree_schema.py', 'r', encoding='utf-8').read())"
```

With an explicit executable path:

```powershell
& 'D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe' -c "exec(open(r'tests/regression/smoke_tree_schema.py', 'r', encoding='utf-8').read())"
```

## Maintained Bundles

The maintained practical sample inventory and scenario bundle mapping lives in:

- [PRACTICAL_SAMPLE_SET.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/PRACTICAL_SAMPLE_SET.md)

The runner scripts are the source of truth for exact smoke membership:

- `tests/regression/run_short_term_smokes.ps1`
- `tests/regression/run_practical_scope_smokes.ps1`

## Scope Notes

- These scripts should fail loudly with `Exception` when a contract breaks.
- Keep them safe for GUI-less execution.
- Prefer validating status fields, dependency propagation, and object-link contracts before adding heavier geometry cases.

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
powershell -ExecutionPolicy Bypass -File tests/regression/run_short_term_smokes.ps1
```

Practical engineering scope:

```powershell
powershell -ExecutionPolicy Bypass -File tests/regression/run_practical_scope_smokes.ps1
```

The runners resolve FreeCAD from an explicit parameter, `FREECAD_BIN`, `PATH`, or common install locations, in that order. Run `scripts/check_freecad_environment.ps1` to verify the selected installation.

The environment check and maintained runners stop before testing when more than one `CorridorRoad` or `Corridor-Road` workbench exists under the active FreeCAD `Mod` directory. They do not remove or rename duplicate installations automatically.

## Local Validation Tiers

Local development dependencies are listed in `requirements-dev.txt`. Install them into the selected FreeCAD Python environment when needed:

```powershell
& "$env:FREECAD_BIN\python.exe" -m pip install -r requirements-dev.txt
```

Run a single local validation tier:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_local_validation.ps1 -Tier Compile
powershell -ExecutionPolicy Bypass -File scripts/run_local_validation.ps1 -Tier Lint
powershell -ExecutionPolicy Bypass -File scripts/run_local_validation.ps1 -Tier Architecture
powershell -ExecutionPolicy Bypass -File scripts/run_local_validation.ps1 -Tier Fast
powershell -ExecutionPolicy Bypass -File scripts/run_local_validation.ps1 -Tier Contracts
powershell -ExecutionPolicy Bypass -File scripts/run_local_validation.ps1 -Tier Smokes
```

`Architecture` checks the v1 package dependency rules without importing FreeCAD modules. `Fast` runs Compile, Architecture, and a focused set of service and command contracts intended for frequent local use.

Run the complete local sequence:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_local_validation.ps1 -Tier Full
```

These are local development commands. The project CI configuration remains unchanged.

## Running One Smoke

Prefer `-c "exec(open(...).read())"` so FreeCAD runs the Python file as a script.

```powershell
FreeCADCmd -c "exec(open(r'tests/regression/smoke_tree_schema.py', 'r', encoding='utf-8').read())"
```

With an explicit executable path:

```powershell
& "$env:FREECAD_BIN\FreeCADCmd.exe" -c "exec(open(r'tests/regression/smoke_tree_schema.py', 'r', encoding='utf-8').read())"
```

## Maintained Bundles

The maintained practical sample inventory and scenario bundle mapping lives in:

- [PRACTICAL_SAMPLE_SET.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/v1-1/Mod/CorridorRoad/docs/PRACTICAL_SAMPLE_SET.md)

The runner scripts are the source of truth for exact smoke membership:

- `tests/regression/run_short_term_smokes.ps1`
- `tests/regression/run_practical_scope_smokes.ps1`

## Scope Notes

- These scripts should fail loudly with `Exception` when a contract breaks.
- Keep them safe for GUI-less execution.
- Prefer validating status fields, dependency propagation, and object-link contracts before adding heavier geometry cases.

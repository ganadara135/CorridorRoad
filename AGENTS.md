# AGENTS.md

## Project Overview

This repository contains **Parametric Road**, the CorridorRoad Workbench for FreeCAD. It is a source-driven parametric road-design, review, and output workflow implemented with Python and the FreeCAD API.

Current baseline:

- public release: `1.0.9`
- minimum package compatibility: FreeCAD `1.0.3`
- recommended and validated runtime: FreeCAD `1.1.1`
- Python: `3.10+`
- internal package and command prefix: `Corridor_Road` / `CorridorRoad_`

Required Python executable for this workspace:

```text
C:\Program Files\FreeCAD 1.1\bin\python.exe
```

This installed executable currently provides Python `3.11.14` and successfully
imports `FreeCAD` and `Part`. Its FreeCAD API reports version `1.1.3` even though
the installation directory is named `FreeCAD 1.1`.

The primary v1 workflow is:

```text
Project
  -> TIN
  -> Alignment
  -> Stations
  -> Profile
  -> Plan/Profile Review and 3D Centerline
  -> Superelevation (optional)
  -> Subassembly / Assembly
  -> Regions
  -> Intersections / Structures / Drainage
  -> Applied Sections
  -> Build Parametric (Corridor and Surface results)
  -> Cross Section / Drainage / Earthwork Review
  -> Outputs and Exchange
```

The project mainly uses Python, the FreeCAD and FeaturePython APIs, Part, Mesh, Draft, Sketcher, Qt/PySide, and versioned JSON-compatible payloads.

Use `docsV1/V1_SUPPORTED_DOMAIN_STATUS.md` for current product scope and `docsV1/V1_PROJECT_ARCHITECTURE_IMPROVEMENT_IMPLEMENTATION_PLAN.md` for the active architecture plan. Treat `docsV0/` as archived legacy reference.

## Core Architecture Rule

The v1 architecture is:

```text
Source -> Evaluation -> Result -> Output -> Presentation
```

- `v1/models/source/` owns durable user-authored intent.
- `v1/services/evaluation/` owns reusable, deterministic, UI-independent engineering rules.
- `v1/services/builders/` orchestrates construction of derived results.
- `v1/models/result/` owns rebuildable evaluated state such as Applied Sections, Corridor, and Surface results.
- `v1/models/output/` exposes normalized contracts for reports and exchange.
- `v1/ui/` edits sources or reviews results; it does not own engineering truth.
- `v1/commands/` coordinates document, service, and UI boundaries. Reusable engineering algorithms do not belong in commands.
- `v1/objects/` adapts models and payloads to FreeCAD document persistence.

Do not edit generated geometry as source intent, reverse-author source data from previews, duplicate engineering rules in UI/export code, or use display properties as hidden authoring state. Recompute flows downstream; upstream edits must make dependent results stale or rebuild them rather than requiring manual result repair.

## Current Scope Decisions

- Ramp is outside active scope. Preserve compatibility but add no new Ramp behavior unless explicitly requested.
- Watertight Solid development is paused. Only critical repairs, data-loss prevention, compatibility, and existing test preservation are in scope unless explicitly expanded.
- Drainage source editing and current review/output handoffs are supported; advanced hydraulics and automatic pipe sizing are future work.
- Corridor surfaces are the primary terrain-like Build Parametric outputs. Solids are for physical bodies with thickness, material, volume, or export identity.
- Applied Sections and supplemental station rows are generated results, never durable source rows.
- Cross Section, Plan/Profile, Drainage, and Earthwork viewers are review surfaces, not geometry editors.
- CI development is frozen by project policy. Preserve the release guard and do not expand CI without explicit instruction.

## General Development Rules

1. Prefer small, localized changes and do not refactor unrelated code.
2. Preserve existing object/property names, command IDs, stable source IDs, workflow order, and document-tree structure.
3. Do not change behavior unless the requested modification requires it.
4. Avoid unnecessary external dependencies.
5. Inspect the source owner, callers, persistence adapters, and downstream consumers before editing.
6. Fix the smallest causal code path and add a focused regression test when practical.
7. Do not opportunistically rewrite large command or service files.

## FreeCAD Object Model and Recompute

Take special care with `execute()`, `onChanged()`, `Proxy`, `ViewProvider`, properties, and `Document.recompute()`.

- Avoid `doc.recompute()` in frequently executed callbacks.
- Avoid recursive updates, recompute storms, and rebuilding unchanged geometry.
- Prefer direct links over scanning every document object.
- Keep preview refresh separate from durable source writes.
- Opening an editor or viewer must not create sample data or mutate the document unless explicitly promised.

## Units and Coordinates

FreeCAD geometry primarily uses millimeters, while engineering input commonly uses meters. Always verify the owning schema and property. Also distinguish degrees/radians and grade ratio/percent.

Check source schema, FreeCAD property type, project unit policy, CSV policy, output display units, and legacy migration rules before conversion. Never silently convert units. Prefer explicit code such as:

```python
station_mm = station_m * 1000.0
elevation_m = elevation_mm / 1000.0
```

External TIN and Alignment coordinates follow `docsV1/V1_COORDINATE_IMPORT_POLICY.md`. Never mix world coordinates, project-origin offsets, and local model coordinates implicitly.

## Road Geometry

Preserve station and tangent direction, normal vectors, left/right orientation, horizontal and vertical alignment direction, section orientation, wire topology, region boundaries, special-area ownership, and shared-breakline continuity.

Do not assume every edge has the same orientation. Derive local frames from the evaluated Alignment and shared 3D Centerline whenever possible.

### Alignment, Profile, and 3D Centerline

- Preserve usable BREP `Edge` or `Wire` geometry where downstream operations require it.
- Keep Existing Ground and Finished Grade separate.
- Preserve vertical-curve continuity at BVC/EVC; validate grades, overlaps, and zero-length curves.
- `Centerline3DResult` owns the shared evaluated station/offset/elevation baseline. Applied Sections keep only derived placement frames.
- Superelevation owns station-based crossfall intent. Applied Sections consume its evaluated state; Build Parametric must not reinterpret it independently.

Validate generated shapes:

```python
shape = getattr(source, "Shape", None)
if shape is None or shape.isNull():
    return
```

### Sections, Corridor, and Surfaces

Watch for flipped sections, duplicate stations, invalid/self-intersecting wires, inconsistent topology, loft twisting, missing boundary samples, ownership conflicts, and broken shared breaklines.

Before Sweep or Loft, validate paths, wires, topology, continuity, orientation, and station separation. Do not hide failures with excessive sampling or arbitrary tolerances. Every tolerance needs an engineering or kernel-stability reason and a focused test.

## Domain Ownership and Precedence

- Project owns units, CRS/origin policy, standards, and global references.
- TIN owns terrain source and replayable edits; preview meshes are not source.
- Alignment owns horizontal intent; Profile owns vertical intent.
- Assembly/Subassembly owns section definition and placement intent.
- Region owns continuous station spans and base Assembly assignment.
- Structure, Drainage, and Intersection own their source meaning and may reference Region; Region must not absorb their semantics.
- Applied Sections resolve intent station by station.
- Corridor and Surface consume Applied Sections and evaluated special-area results.
- Outputs retain project and source/result traceability.

Use existing resolution services for overlapping precedence. Do not add command-local precedence branches.

## Persistence and Backward Compatibility

Existing FCStd documents may contain older properties and payloads. When adding a property:

```python
if not hasattr(obj, "PropertyName"):
    obj.addProperty(...)
```

Preserve stable IDs, link targets, schema versions, compatibility aliases, and unknown legacy data. Add migration where practical. Verify save, close, reopen, restore, and recompute behavior. Consult `docsV1/V1_PERSISTENCE_SCHEMA_INVENTORY.md` before changing typed payloads or persistence adapters.

## Defensive Geometry and Diagnostics

Account for missing links, null Shapes, zero-length Edges, invalid/open Wires, invalid stations, duplicate points, failed booleans/triangulation/loft/sweep, and stale payloads.

Do not suppress exceptions without a documented compatibility reason. Diagnostics should state:

1. what failed
2. which object, source ID, or station caused it
3. what input, link, or geometry to inspect
4. whether the result is blocked, partial, stale, or using a fallback

Preserve structured diagnostics through result/output contracts rather than console text alone.

## UI and Presentation

- Editors write source objects only after explicit Apply/Save.
- Viewers inspect contracts and must not become hidden authoring paths.
- Keep UI state separate from engineering and geometry logic.
- Check dynamic widgets and alternate UI states before access.
- Cancel/close must not write unintended changes.
- Preview geometry is temporary unless a result contract owns it.
- Use workflow-oriented user labels, not migration or internal bridge terminology.

## Performance

Avoid unnecessary whole-document recomputes, excessive sampling, repeated payload parsing, rebuilding unchanged stations/surfaces, full document scans, and UI refreshes that write source state.

Cached results must remain traceable, versioned, stale-detectable, and rebuildable. Optimization must not create a second source of truth.

## Coding Style

- Prefer readable Python and descriptive engineering names such as `station_mm`, `finished_grade`, and `section_normal`.
- Keep pure calculations independent of FreeCAD and Qt where practical.
- Comment engineering assumptions, coordinate conventions, persistence constraints, unusual FreeCAD behavior, and justified tolerances.
- Avoid broad `except Exception: pass`; catch expected failures and emit useful diagnostics.

## Validation

Run the smallest relevant test first, then affected downstream boundaries.

### Required FreeCAD Python

All Python commands for this repository must use the FreeCAD-bundled interpreter
at the following absolute path:

```text
C:\Program Files\FreeCAD 1.1\bin\python.exe
```

Do not invoke `python`, `python3`, `py`, a Windows Store Python alias, a virtual
environment interpreter, or another standalone Python installation. This rule
also applies to pure-Python contract tests, helper scripts, package inspection,
formatters, and dependency installation. Using one interpreter everywhere avoids
ABI, PySide, OpenCascade, and FreeCAD module mismatches.

In PowerShell, invoke the executable with the call operator because its path
contains spaces:

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" --version
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -c "import FreeCAD, Part; print(FreeCAD.Version())"
```

Install or inspect development dependencies through the same interpreter:

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pip install -r requirements-dev.txt
```

Run focused contract tests through the same interpreter:

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\contracts\v1\path_to_focused_test.py -q
```

Development dependencies are listed in `requirements-dev.txt`.

Check the configured FreeCAD environment with:

```powershell
scripts\check_freecad_environment.ps1
```

Regression smoke guidance is under `tests/regression/`. Tests needing a GUI may
still require `FreeCAD.exe` rather than the Python interpreter; follow the
specific regression script. Do not claim GUI integration validation when only
headless Python tests ran.

Where relevant, verify:

- FreeCAD and the workbench load without Python errors
- command IDs, toolbars, and menus remain registered
- objects/properties are created and saved documents reopen
- schema migrations and compatibility aliases work
- units, coordinates, station direction, and left/right orientation are explicit
- upstream edits propagate through Profile, Centerline, Applied Sections, Corridor, and Surface consumers
- diagnostics distinguish blocked, partial, stale, and fallback results

## Agent Workflow

Before modifying code:

1. Read this file completely.
2. Inspect relevant source and current architecture/status documents.
3. Identify the durable source owner and result/output consumers.
4. Trace upstream inputs, persistence, commands, UI, and downstream dependencies.
5. Choose the smallest change and focused validation path.

When reporting a modification:

- explain the root cause or design reason
- identify changed files/functions
- explain source/result ownership and compatibility safety
- mention downstream effects
- report tests actually run and tests not run
- provide manual FreeCAD verification steps when relevant

Do not rewrite large portions of the project unless explicitly requested. Improve Parametric Road incrementally while preserving its source-driven workflow, document compatibility, and engineering traceability.

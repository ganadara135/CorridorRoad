# Codex Prompt Templates (CorridorRoad)

## Session Boot Prompt
Read `README_Codex.md` first, then follow `docs/ARCHITECTURE.md`.
Keep changes small and provide patch-like diffs.
Do not use `git grep` / `python -m compileall` as required validation steps.

## Task: FG Architecture Safety
Verify these boundaries:
- VerticalAlignment is engine/data only.
- FGDisplay owns FG display toggles.
- ProfileBundle stores data and shows EG only.
- Profile/PVI task panels must not depend on removed VA FG display props.

## Task: Practical Alignment Update
When updating practical alignment behavior:
- Preserve `Sample Alignment` command as a separate lightweight flow.
- Keep practical editing in `Edit Alignment` flow.
- Keep design standard selection synced through project property (`CorridorRoadProject.DesignStandard`).
- Keep superelevation sync: `Apply Alignment` should propagate `SuperelevationPct` to
  `AssemblyTemplate.LeftSlopePct/RightSlopePct` when available.
- For sketch import, keep conversion policy explicit:
  - require single connected open sketch path
  - convert `line-arc-line` to PI + exact arc radius (do not import TS/ST as IP rows)
  - default imported `TransitionLengths` to `0.0` unless user overrides
- For CSV flow, keep parser/writer in shared module (`objects/csv_alignment_import.py`):
  - support inspect/load/save workflow in Alignment Editor
  - keep import mapping/options explicit (encoding/delimiter/header/sort/coords)
  - keep export header mode-aware (`X/Y` vs `E/N`) and use current table PI rows
- Ensure criteria messages are actionable, not just warning labels.
- Include reverse-curve diagnostics when applicable (`[REVERSE]`, `[REVERSE-TANGENT]`, `[REVERSE-TRANSITION]`).
- Keep stationing compatibility with `point_at_station` / `tangent_at_station`.
- Keep project unit policy explicit and meter-native.
- Do not hardcode alternative runtime scales; use shared unit-policy helpers at UI/import/export boundaries.

## Task: Alignment Criteria Message Quality
For criteria violations:
- Include which segment/IP failed.
- Include numeric threshold and current value.
- Include one actionable next step (e.g., required segment length increase).

## Task: Validation (Project Policy)
1) Summarize changed files and reasoning.
2) Mention what runtime behavior should be checked in FreeCAD.

## Task: Corridor Update
When implementing corridor + parametric updates:
- Enforce section schema contract:
  - `SectionSchemaVersion = 1 or 2`
  - `v1` point order: `Left -> Center -> Right`
  - `v2` point order: `LeftOuter? -> Left -> Center -> Right -> RightOuter?`
- Stop corridor build with explicit status if section point count/order mismatch occurs.
- Keep `OutputType = Surface` only.
- Build corridor output from open section wires / matched section segments; do not generate corridor body solids in the current runtime.
- Default `AutoUpdate=True`; support manual `RebuildNow=True`.
- Source edits should mark corridor as `NEEDS_RECOMPUTE` in tree/status instead of auto corridor recompute.
- Add failure guards (precheck/orientation-fix/adaptive segmented fallback) and log failed ranges.

## Task: Section Panel UX
- In `Generate Sections` task panel, `OK` must close only.
- Actual generation must be explicit via `Generate Sections Now`.
- `UseDaylightToTerrain` must support terrain source as Mesh only.
- Daylight path must include performance guards (`DaylightMaxTriangles`, wide-triangle bucket guard).
- If daylight source is missing/fails, set explicit WARN status and fall back to fixed side widths.

## Task: Surface Comparison Prep
Before implementing `Existing/Design Surface` comparison:
<!-- - Keep model policy: `Corridor=Surface`, `DesignGradingSurface=Mesh`, `DesignTerrain=Mesh`, others `Surface/Wire`. -->
- Use design top surface extracted from `Corridor`.
- Use existing surface input as `Mesh` (phase-1).
- Keep default comparison resolution at `1.0 m` (adjustable `0.2~5.0 m`).
- Use dedicated TaskPanel flow for source selection and run control.
- TaskPanel must expose visible progress and a cancel action.
- Keep result schema fields: `DeltaMin/Max/Mean`, `CutVolume`, `FillVolume`, `NoDataArea`, `CellSize`, `Status`.
- Keep run guardrails: `EstimatedSamples <= MaxSamples`, and avoid bucket blow-up on wide triangles.
- Keep mesh quality gate: enforce `MinMeshFacets` and non-degenerate existing mesh XY bounds.
- Keep no-data governance: track `NoDataRatio` and warn when `NoDataRatio > NoDataWarnRatio`.
- Keep sign convention fixed: `delta=Design-Existing`, `+Fill`, `-Cut`.
- Keep update policy: `AutoUpdate=False` means no auto-run; `RebuildNow=True` triggers explicit run.
- Keep `CutFillCalc` meter-native for defaults and guards.
- Enforce minimum cell size policy: `CellSize >= 0.2 m`.
- Keep one fixed validation sample with tolerance: elevation +/-0.01 m, volume +/-1%.

## Task: Design Terrain UX
- `Design Terrain` command should use dedicated TaskPanel with explicit source selection.
- Do not rely on hidden auto-pick for `ExistingTerrain` (Mesh only).
- Keep meter-native defaults/guards (including minimum cell size policy).
- TaskPanel run path should expose progress and allow cancel.

## Task: Command Labels
- Toolbar/menu `MenuText` should omit `Generate` prefix.
- Keep command IDs aligned with current feature naming.

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
- Keep practical editing in `Edit Alignment (Practical)` flow.
- Ensure criteria messages are actionable, not just warning labels.
- Keep stationing compatibility with `point_at_station` / `tangent_at_station`.
- Keep project length-scale policy consistent (`LengthScale`: internal units per meter).
- Do not hardcode `s=1000`; use project/user scale UX and shared scale helper.

## Task: Alignment Criteria Message Quality
For criteria violations:
- Include which segment/IP failed.
- Include numeric threshold and current value.
- Include one actionable next step (e.g., required segment length increase).

## Task: Validation (Project Policy)
1) Summarize changed files and reasoning.
2) Mention what runtime behavior should be checked in FreeCAD.

## Task: Corridor Loft Update
When implementing Corridor Loft + parametric updates:
- Enforce section schema contract:
  - `SectionSchemaVersion = 1 or 2`
  - `v1` point order: `Left -> Center -> Right`
  - `v2` point order: `LeftOuter? -> Left -> Center -> Right -> RightOuter?`
- Stop Loft with explicit status if section point count/order mismatch occurs.
- Keep `OutputType = Solid` only.
- For `Solid`, require valid `HeightLeft/HeightRight` and build closed profiles from section wires.
- Default `AutoUpdate=True`; support manual `RebuildNow=True`.
- Source edits should mark corridor as `NEEDS_RECOMPUTE` in tree/status instead of auto corridor recompute.
- Add failure guards (precheck/orientation-fix/adaptive segmented fallback) and log failed ranges.

## Task: Section Panel UX
- In `Generate Sections` task panel, `OK` must close only.
- Actual generation must be explicit via `Generate Sections Now`.
- `UseDaylightToTerrain` must support terrain source as Mesh or Shape.
- Daylight path must include performance guards (`DaylightMaxTriangles`, wide-triangle bucket guard).
- If daylight source is missing/fails, set explicit WARN status and fall back to fixed side widths.

## Task: Surface Comparison Prep
Before implementing `Existing/Design Surface` comparison:
- Keep model policy: `CorridorLoft=Solid`, `DesignGradingSurface=Surface`, `DesignTerrain=Surface`, others `Surface/Wire`.
- Use design top surface extracted from `CorridorLoft`.
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
- Keep `SurfaceComparison` scale-aware with `Project.LengthScale` (defaults and guards).
- Enforce minimum cell size policy: `CellSize >= 0.2 m * LengthScale`.
- Keep one fixed validation sample with tolerance: elevation +/-0.01 m, volume +/-1%.

## Task: Design Terrain UX
- `Design Terrain` command should use dedicated TaskPanel with explicit source selection.
- Do not rely on hidden auto-pick for `ExistingTerrain`.
- Keep scale-aware defaults/guards (`LengthScale`, minimum cell size policy).
- TaskPanel run path should expose progress and allow cancel.

## Task: Command Labels
- Toolbar/menu `MenuText` should omit `Generate` prefix.
- Keep command IDs unchanged for backward compatibility.

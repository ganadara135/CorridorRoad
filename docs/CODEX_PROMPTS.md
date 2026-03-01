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
- Enforce `SectionSchemaVersion = 1` and fixed point order `Left -> Center -> Right`.
- Stop Loft with explicit status if section point count/order mismatch occurs.
- Keep `OutputType = Solid` only.
- For `Solid`, require valid `HeightLeft/HeightRight` and build closed profiles from section wires.
- Default `AutoUpdate=True`; support manual `RebuildNow=True`.
- Source edits should mark corridor as `NEEDS_RECOMPUTE` in tree/status instead of auto corridor recompute.
- Add failure guards (precheck/orientation-fix/adaptive segmented fallback) and log failed ranges.

## Task: Section Panel UX
- In `Generate Sections` task panel, `OK` must close only.
- Actual generation must be explicit via `Generate Sections Now`.

## Task: Surface Comparison Prep
Before implementing `Existing/Design Surface` comparison:
- Keep model policy: `CorridorLoft=Solid`, others `Surface/Wire`.
- Use design top surface extracted from `CorridorLoft`.
- Use existing surface input as `Mesh` (phase-1).
- Keep default comparison resolution at `1.0 m` (adjustable `0.2~5.0 m`).
- Use dedicated TaskPanel flow for source selection and run control.
- TaskPanel must expose visible progress and a cancel action.
- Keep result schema fields: `DeltaMin/Max/Mean`, `CutVolume`, `FillVolume`, `NoDataArea`, `CellSize`, `Status`.
- Keep run guardrails: `EstimatedSamples <= MaxSamples`, and avoid bucket blow-up on wide triangles.
- Keep update policy: `AutoUpdate=False` means no auto-run; `RebuildNow=True` triggers explicit run.
- Keep one fixed validation sample with tolerance: elevation +/-0.01 m, volume +/-1%.

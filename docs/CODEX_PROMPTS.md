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
- Keep `OutputType = Surface|Solid` but implement `Surface` first.
- Default `AutoUpdate=True`; support manual `RebuildNow=True`.
- Add failure guards (precheck/orientation-fix/segmented fallback) and log failed ranges.

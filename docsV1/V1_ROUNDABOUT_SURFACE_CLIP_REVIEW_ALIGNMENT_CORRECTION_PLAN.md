# V1 Roundabout Surface Clip and Review Alignment Correction Plan

## Purpose

Correct the roundabout ordinary-road clipping and Guided Review mismatch found during manual QA.

This plan focuses on two related failures:

- ordinary road surfaces are being clipped at approach-side rectangular handoff loops
- Guided Review objects for Lane, Shoulder, and Side Slope do not consistently match Design Surface and Subgrade ownership

The goal is to make all ordinary corridor consumers use one clear roundabout ownership policy while keeping diagnostic handoff loops separate from actual clipping truth.

## Core Rule

Roundabout diagnostic or handoff boundary loops must not automatically become ordinary-road clipping polygons.

Only accepted roundabout ownership boundaries may remove ordinary road geometry.

Guided Review previews must reflect the accepted source/result contract used by the actual surface result. They must not invent a separate clipping policy.

## Current Symptoms

Manual QA shows:

- Design Surface, Lane, Shoulder, Side Slope, and Slope Face do not always stop at the same area.
- ordinary road segments are cut in the middle of approach roads away from the roundabout.
- Lane and Shoulder double-click previews can show long or differently shaped strips compared with Design Surface.
- Side Slope can look closer to the expected boundary, but it is generated through a separate breakline-only path.
- tests currently preserve some of this behavior by expecting roundabout approach clip skips in Guided Review.

## Root Cause

Roundabout boundary evaluation creates several loop roles:

- `roundabout_outer_ownership_boundary`
- `roundabout_approach_clip_boundary`
- `roundabout_subgrade_clip_boundary`
- `roundabout_slope_handoff_boundary`

The approach, subgrade, and slope-handoff roles are currently consumed as clipping polygons by ordinary corridor surfaces and Guided Review highlights.

However, those rectangular loops are better treated as diagnostic or handoff metadata. They are not the accepted ordinary-road removal boundary.

The actual ordinary-road removal boundary should be based on roundabout ownership:

- the outer roundabout ownership boundary for ordinary surface exclusion
- dedicated roundabout outputs for roundabout-owned geometry
- shared breaklines for audit at the handoff

## Scope

This correction applies to:

- Design Surface
- Subgrade Surface
- Slope Face Surface
- Lane Guided Review
- Shoulder Guided Review
- Side Slope Guided Review
- Breakline Audit diagnostics
- Intersections diagnostics where they expose roundabout clip roles
- FreeCADCmd contract tests and smoke tests

This correction does not implement:

- full multi-lane roundabout design
- advanced entry/exit geometry
- traffic capacity or swept-path analysis
- mesh-derived repair of roundabout geometry

## Target Behavior

### Design Surface

Design Surface should stop at the accepted roundabout ownership boundary.

It should not be clipped by far approach-side rectangular loops.

### Subgrade Surface

Subgrade Surface should use the same ownership boundary policy as Design Surface unless a separate accepted roundabout subgrade ownership boundary is explicitly introduced.

It should not preserve ordinary subgrade through the roundabout interior, and it should not cut unrelated approach road segments.

### Slope Face Surface

ordinary Slope Face Surface should stop at the roundabout ownership or accepted slope ownership boundary.

It should not be clipped by rectangular slope-handoff diagnostic loops away from the actual roundabout ownership area.

### Lane and Shoulder Guided Review

Lane and Shoulder Guided Review should show review strips that match Design Surface ownership.

They may remain presentation objects, but their visible area must be governed by the same accepted clipping policy as Design Surface.

### Side Slope Guided Review

Side Slope Guided Review should either:

- show source-derived side-slope breaklines that correspond to ordinary Slope Face Surface ownership, or
- clearly report that no side-slope review geometry is available

It should not replace missing side-slope geometry with rectangular handoff-loop-only geometry.

## Implementation Phases

### Phase 1 - Contract Role Separation

Status: Completed

Implementation notes:

- ordinary surface clipping no longer uses `roundabout_approach_clip_boundary`, `roundabout_subgrade_clip_boundary`, or `roundabout_slope_handoff_boundary` as actual clipping polygons.
- these roles remain reported handoff/diagnostic roles so Breakline Audit and Results can still explain the intended boundary family.
- actual clipping roles are now exposed separately through `roundabout_actual_clip_boundary_roles` / `RoundaboutActualClipBoundaryRoles`.

Tasks:

1. Identify every consumer of:
   - `roundabout_approach_clip_boundary`
   - `roundabout_subgrade_clip_boundary`
   - `roundabout_slope_handoff_boundary`
2. Classify each consumer as:
   - accepted clipping consumer
   - shared breakline audit consumer
   - UI focus/highlight consumer
   - diagnostic-only consumer
3. Remove these rectangular loops from ordinary surface clipping unless a role is explicitly marked as accepted ownership.
4. Keep the loops available for diagnostics only when they explain a handoff condition.

Acceptance criteria:

- ordinary road clipping no longer consumes rectangular approach-side handoff loops by default.
- diagnostics still preserve the source refs and loop roles for review.

### Phase 2 - Surface Clipping Policy Correction

Status: Completed

Implementation notes:

- Design Surface, Subgrade Surface, and Slope Face Surface now use `roundabout_outer_ownership_boundary` as the accepted roundabout ordinary-surface exclusion polygon.
- boundary-loop clipping is enabled from actual clip polygon availability instead of the reported diagnostic handoff role status.
- existing handoff role metadata remains visible as reported boundary context.

Tasks:

1. Update roundabout clipping polygon selection so ordinary surfaces use accepted ownership polygons only.
2. For the current single-lane roundabout preset, use `roundabout_outer_ownership_boundary` as the primary ordinary-surface exclusion boundary.
3. Keep circle-based ownership clipping only as a diagnostic fallback when boundary-loop ownership is unavailable.
4. Add quality rows that distinguish:
   - reported handoff boundary role
   - actual clipping polygon role
   - fallback reason

Acceptance criteria:

- Design Surface, Subgrade Surface, and Slope Face Surface are not cut at unrelated approach rectangles.
- quality diagnostics show which polygon role actually clipped each surface.

### Phase 3 - Guided Review Alignment

Status: Completed

Implementation notes:

- Lane and Shoulder Guided Review now use the same actual roundabout clipping role as Design Surface.
- the Side Slope diagnostic fallback that drew only clipping-boundary geometry has been removed.
- Side Slope focus now returns a dedicated `Applied Section Highlight - Side Slope` object instead of falling back to an accepted mesh/result preview.
- Guided Review objects expose reported handoff role and actual clipping role separately through `RoundaboutReportedBoundaryRole`, `RoundaboutActualClipBoundaryRole`, and `RoundaboutReviewClipMode`.
- Side Slope Guided Review is source-breakline review geometry; it does not remove its own polylines by the roundabout ownership polygon, but it still reports the actual clipping boundary used by accepted Slope Face Surface output.
- When a Side Slope row collapses to the same side-slope/daylight point, Guided Review now draws a compact marker and records `DegenerateSideCount` instead of failing to focus the step.
- `roundabout_slope_handoff_boundary_only` has been removed from the Side Slope Guided Review display path.

Tasks:

1. Completed - Update Lane Guided Review to use the corrected Design Surface clipping policy.
2. Completed - Update Shoulder Guided Review to use the corrected Design Surface clipping policy.
3. Completed - Update Side Slope Guided Review to use the corrected Slope Face clipping policy.
4. Completed - Remove the `roundabout_slope_handoff_boundary_only` fallback display mode if it only shows diagnostic rectangles.
5. Completed - Add preview metadata:
   - `RoundaboutActualClipBoundaryRole`
   - `RoundaboutReportedBoundaryRole`
   - `RoundaboutReviewClipMode`
   - `SkippedRoundaboutSectionCount`
   - `SkippedRoundaboutStripTriangleCount`

Acceptance criteria:

- `3. Lane`, `3. Shoulder`, and `3. Side Slope` no longer show unrelated approach-middle clipping.
- Lane and Shoulder review extents are consistent with Design Surface.
- Side Slope review is consistent with ordinary Slope Face Surface.

### Phase 4 - Breakline Audit Cleanup

Status: Completed

Implementation notes:

- roundabout handoff boundary roles are now shown as diagnostic-only rows when they differ from the actual ordinary-surface clipping role.
- diagnostic-only roundabout rows do not expose graph edge refs or a breakline role filter, so double-click does not create offset alignment ghost rectangles.
- Breakline Audit notes now show both the reported handoff boundary and the actual clipping role.
- per-leg roundabout clip boundary rows are suppressed for diagnostic-only handoff boundaries.
- diagnostic rows recommend no user action because they are not used as ordinary surface clipping boundaries.

Tasks:

1. Completed - Keep shared breakline rows only for boundaries that represent real consumer handoff.
2. Completed - Hide or downgrade diagnostic-only roundabout clip loops from user-facing audit summaries.
3. Completed - Ensure Breakline Audit double-click focuses accepted source/result context, not offset alignment ghost rectangles.
4. Completed - Add notes when a loop is diagnostic-only and not used for surface clipping.

Acceptance criteria:

- Breakline Audit does not imply that diagnostic rectangles are accepted surface boundaries.
- user-facing rows explain real handoff ownership.

### Phase 5 - Regression Tests

Status: In progress

Implementation notes:

- focused FreeCADCmd checks now cover the roundabout ordinary-surface guardrail and the single-lane full smoke path.
- tests now assert that diagnostic roundabout handoff rows do not expose graph edge refs or role filters.
- Applied Sections Show All / Hide All preview now has a guardrail test confirming it is not consumed as a roundabout clipping source.
- remaining work is broader manual QA.

Tasks:

1. Completed - Update tests that currently expect Lane/Shoulder review to skip approach rectangles.
2. Completed - Update tests that currently expect Side Slope review to show `roundabout_slope_handoff_boundary_only`.
3. Completed - Add tests that assert actual clipping role is `roundabout_outer_ownership_boundary` for ordinary roundabout exclusion.
4. Completed - Add tests that Applied Sections Show All preview is not a clipping source.
5. In progress - Run focused FreeCADCmd tests:
   - roundabout ordinary surface ownership clipping
   - Lane / Shoulder Guided Review
   - Side Slope Guided Review
   - Roundabout single-lane smoke
   - Applied Sections Show All / Hide All preview

Acceptance criteria:

- tests fail if rectangular handoff loops are used as ordinary-road clipping polygons.
- tests pass for accepted roundabout ownership clipping.

### Phase 6 - Manual QA

Status: Planned

Manual QA steps:

1. Create `Roundabout - Single Lane` preset.
2. Build Applied Sections.
3. Run Build Parametric.
4. Check top view:
   - ordinary road is not cut at approach-middle rectangles
   - ordinary Design Surface and Subgrade stop only at roundabout ownership
   - Lane and Shoulder review match Design Surface area
   - Side Slope review matches Slope Face Surface area
5. Check underside/back-side view:
   - no orphan rectangular handoff surfaces remain
   - no offset alignment ghost highlight remains after double-click
6. Open Breakline Audit:
   - Design Surface, Subgrade Surface, and Slope Face Surface report actual clip boundary role
   - diagnostic-only handoff loops do not appear as accepted clipping rows

Acceptance criteria:

- manual QA captures show the same ownership area for actual surfaces and Guided Review previews.
- ordinary road approach segments are continuous outside the roundabout ownership area.

## Implementation Order

Use this order:

1. Contract Role Separation
2. Surface Clipping Policy Correction
3. Guided Review Alignment
4. Breakline Audit Cleanup
5. Regression Tests
6. Manual QA

This order avoids chasing visual symptoms before the clipping source contract is corrected.

## Risks

- Some current tests encode the wrong behavior and must be updated intentionally.
- Removing rectangular-loop clipping may reveal missing dedicated roundabout connector geometry that was previously hidden by clipping.
- Guided Review may need a clearer distinction between accepted output previews and source breakline diagnostics.
- Existing Breakline Audit rows may need renaming or filtering to avoid implying false ownership.

## Non-goals

- Do not repair ordinary corridor meshes after generation.
- Do not use generated preview objects as roundabout source truth.
- Do not merge roundabout-owned surfaces back into ordinary corridor surfaces.
- Do not keep a visual-only rectangle if it does not correspond to accepted clipping or handoff ownership.

## Done Criteria

This correction is complete when:

- ordinary Design Surface, Subgrade Surface, and Slope Face Surface are clipped only by accepted roundabout ownership boundaries
- Lane, Shoulder, and Side Slope Guided Review match their corresponding accepted surface ownership
- rectangular handoff loops remain diagnostic-only unless explicitly accepted as real boundary contracts
- Breakline Audit rows describe actual shared boundaries, not visual helper geometry
- FreeCADCmd regression tests and manual QA pass

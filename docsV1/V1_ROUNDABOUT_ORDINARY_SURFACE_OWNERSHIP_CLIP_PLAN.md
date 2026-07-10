# V1 Roundabout Ordinary Surface Ownership Clip Plan

## Purpose

Define how ordinary corridor outputs that overlap a roundabout ownership area should be clipped, reviewed, and handed off to dedicated roundabout outputs.

This plan focuses on:

- Lane review strips
- Shoulder review strips
- Design Surface
- ordinary Slope Face Surface / Side Slope review

The goal is to prevent ordinary corridor geometry from passing through the roundabout while preserving source traceability and shared breaklines at the handoff boundary.

## Core Rule

Roundabout interior geometry belongs to roundabout-specific result contracts.

Ordinary corridor geometry may approach the roundabout, but it must stop at explicit roundabout ownership boundaries.

Generated roundabout meshes, ordinary preview objects, or visual overlaps must not become source truth.

## Scope

This plan covers the first implementation sequence for `Roundabout - Single Lane`.

It includes:

- roundabout approach clip boundary selection
- ordinary Design Surface clipping
- Lane and Shoulder Guided Review clipping
- ordinary Slope Face Surface clipping
- Side Slope Guided Review clipping
- shared breakline handoff rows
- Results / Breakline Audit diagnostics
- FreeCADCmd regression smoke updates

This plan does not cover:

- multi-lane roundabout logic
- traffic capacity analysis
- vehicle swept path design
- final exact boolean TIN clipping for every non-convex case
- drainage hydraulic design

## Current Problem

Manual QA shows that ordinary corridor output can still overlap the roundabout area.

Typical symptoms:

- Lane and Shoulder review strips follow Applied Sections through the roundabout instead of stopping at the approach boundary.
- Design Surface can leave ordinary triangles inside the roundabout ownership area when clipping is not complete.
- Side Slope / Slope Face Surface can cross into the roundabout handoff zone.
- Breakline Audit can look mostly ready while visual ownership is still unclear.

The issue is not that roundabout geometry needs to be patched after the fact.

The issue is that ordinary corridor consumers and review highlights need to consume the same roundabout ownership boundaries.

## Ownership Model

### Ordinary Corridor Owns

The ordinary corridor owns:

- approach Lane strips outside the roundabout clip boundary
- approach Shoulder strips outside the roundabout clip boundary
- approach Design Surface outside the roundabout clip boundary
- ordinary Slope Face Surface outside the roundabout slope handoff boundary

### Roundabout Owns

The roundabout owns:

- central island
- circulatory pavement
- apron / roundabout shoulder
- roundabout subgrade
- roundabout slope face
- entry/exit transition source contracts where accepted

### Shared Boundary Owns the Handoff

The shared breakline system owns the auditable handoff between ordinary and roundabout outputs.

It should expose:

- which surface consumes the boundary
- which roundabout result provides the boundary
- whether geometry and mesh edges match
- whether a consumer is missing

## Boundary Roles

The implementation should use explicit boundary roles.

### `roundabout_approach_clip_boundary`

Used by:

- Design Surface
- Lane review strips
- Shoulder review strips

Meaning:

- ordinary pavement and shoulder output stops here
- roundabout circulatory / apron output continues inside

### `roundabout_subgrade_clip_boundary`

Used by:

- Subgrade Surface

Meaning:

- ordinary subgrade stops here
- roundabout subgrade owns the interior

### `roundabout_slope_handoff_boundary`

Used by:

- ordinary Slope Face Surface
- Side Slope Guided Review
- Roundabout Slope Face Surface

Meaning:

- ordinary slope output stops here
- roundabout slope face owns the ring or transition zone inside

### `roundabout_apron_handoff_boundary`

Optional later role.

Used by:

- Shoulder review
- Roundabout Apron / Shoulder Surface

Meaning:

- only needed if shoulder and apron need a separate visible handoff from the general approach clip boundary

## Implementation Phases

### Phase 1 - Boundary Contract Audit

Status: Completed

Implementation notes:

- `IntersectionRoundaboutApproachLegResult` is treated as the source contract for four physical approach legs.
- The Intersections tab now exposes a compact `roundabout_boundary_readiness` row.
- The readiness row reports approach-leg count and the three required boundary roles before ordinary surface clipping work proceeds.

Tasks:

1. [x] Confirm `IntersectionRoundaboutApproachLegResult` emits four physical approach legs:
   - primary start
   - primary end
   - secondary start
   - secondary end
2. [x] Confirm every approach leg has:
   - `roundabout_approach_clip_boundary`
   - `roundabout_subgrade_clip_boundary`
   - `roundabout_slope_handoff_boundary`
3. [x] Add diagnostics when a boundary role is missing.
4. [x] Add a compact Intersections tab row for boundary readiness.

Acceptance criteria:

- Four approach legs are reported for a four-leg roundabout.
- Missing per-leg boundary roles are visible before surface generation.

### Phase 2 - Design Surface Clip Consistency

Status: Completed

Implementation notes:

- Design Surface clipping now uses source-derived roundabout boundary-loop polygons when `roundabout_approach_clip_boundary` is ready.
- The clip polygon set includes the explicit `roundabout_outer_ownership_boundary` so ordinary Design Surface cannot pass through the roundabout interior.
- Existing ownership-circle suppression remains only as the Design Surface fallback when boundary contracts are unavailable.
- Preview metadata now reports boundary-loop clip mode, fallback reason, and boundary crossing candidate count.

Tasks:

1. [x] Route Design Surface clipping through `roundabout_approach_clip_boundary`.
2. [x] Keep current source-policy radius suppression only as a diagnostic fallback.
3. [x] Report:
   - consumed boundary role
   - clipped triangle count
   - boundary crossing candidate count
   - fallback reason when boundary is unavailable
4. [x] Ensure ordinary Design Surface does not pass through the roundabout interior.

Acceptance criteria:

- Design Surface stops at approach boundaries in all approach directions.
- Breakline Audit shows the Design Surface consuming `roundabout_approach_clip_boundary`.

### Phase 3 - Lane / Shoulder Guided Review Clip

Status: Completed

Implementation notes:

- Lane and Shoulder Guided Review highlights now consume the same source-derived `roundabout_approach_clip_boundary` used by the Design Surface.
- Applied Section strip triangles that cross the roundabout clip boundary are suppressed in the review highlight.
- Clip metadata is exposed on the generated highlight object so manual QA can confirm the consumed boundary role, status, skipped sections, and fallback state.
- The change is limited to Guided Review presentation output. It does not make generated preview geometry a source of truth.

Tasks:

1. [x] Update Lane review highlight to use the same `roundabout_approach_clip_boundary`.
2. [x] Update Shoulder review highlight to use the same boundary or `roundabout_apron_handoff_boundary` if that role is added.
3. [x] Prevent Applied Section strip stitching across roundabout-owned sections.
4. [x] Add preview metadata:
   - `RoundaboutClipBoundaryRole`
   - `RoundaboutClipBoundaryStatus`
   - `SkippedRoundaboutSectionCount`
   - `RoundaboutClipFallbackReason`
5. [x] Rebuild focus objects on double-click so stale highlight objects do not hide the current clip state.

Acceptance criteria:

- `3. Lane` shows only approach lane strips outside the roundabout.
- `3. Shoulder` shows only approach shoulder strips outside the roundabout.
- Review strips visually match the Design Surface ownership area.

### Phase 4 - Slope Face / Side Slope Clip

Status: Completed

Implementation notes:

- ordinary Slope Face Surface now uses `roundabout_slope_handoff_boundary` boundary-loop clipping instead of the ownership-circle fallback when the boundary contract is ready.
- Roundabout-ready boundary-loop clipping is treated as the accepted ownership readiness signal for Slope Face Surface diagnostics.
- `3. Side Slope` Guided Review consumes `roundabout_slope_handoff_boundary`.
- When the roundabout Applied Sections do not contain valid side-slope breaklines, the Side Slope review creates a boundary-only diagnostic highlight instead of failing the double-click focus action.

Tasks:

1. [x] Route ordinary Slope Face Surface clipping through `roundabout_slope_handoff_boundary`.
2. [x] Update `3. Side Slope` review highlight to use the same handoff boundary.
3. [x] Keep `Roundabout Slope Face Surface` as the only roundabout-owned slope output.
4. [x] Ensure generic `Intersection Slope Face Surface` remains not applicable for roundabout.
5. [x] Add diagnostics when ordinary side-slope rows exist inside the roundabout slope ownership area.

Acceptance criteria:

- ordinary Slope Face Surface stops before the roundabout slope handoff.
- `3. Side Slope` review matches ordinary Slope Face Surface ownership.
- Roundabout Slope Face Surface fills the roundabout-owned slope area without mixing with ordinary Slope Face Surface.

### Phase 5 - Shared Breakline Handoff

Status: Completed

Tasks:

1. [x] Promote roundabout clip boundaries to shared breakline rows.
2. [x] Add consumer pairs:
   - Design Surface <-> Roundabout Circulatory / Apron
   - Shoulder review / approach shoulder <-> Roundabout Apron
   - Slope Face Surface <-> Roundabout Slope Face Surface
3. [x] Add per-leg audit rows instead of only aggregate readiness.
4. [x] Hide or remove non-actionable diagnostic rows that are not user-facing handoff contracts.

Implementation notes:

- Breakline Audit now expands roundabout clip boundary handoffs into per-leg rows in the internal/detail view.
- Each leg row preserves the owning source-derived boundary role, approach role, segment refs, and consumer-pair explanation.
- The aggregate surface rows remain compact; leg rows are available for diagnosis when a specific approach boundary fails.
- This phase does not use generated mesh or preview objects as source truth. It exposes existing source-derived clip boundary metadata for handoff audit.

Acceptance criteria:

- Breakline Audit can show which approach leg has a missing or mismatched boundary.
- `geometry_mismatch`, `mesh_mismatch`, and `missing_consumer` reflect real handoff issues.

### Phase 6 - Exact Clip Upgrade

Status: Completed

Tasks:

1. [x] Replace centroid-only suppression with boundary-aware triangle split where feasible.
2. [x] Keep centroid suppression as a fallback only when exact clipping is unavailable.
3. [x] Record exact clip diagnostics:
   - exact candidate count
   - generated fragment count
   - fallback count
4. [x] Add tests for triangles crossing roundabout boundary edges.

Implementation notes:

- Boundary-loop clipping now attempts exact TIN fragment generation before suppressing an ordinary corridor triangle.
- Crossing triangles are converted to `roundabout_ownership_exact_clip` fragments outside the roundabout handoff boundary.
- Full-inside or unsupported cases remain traceable through `roundabout_clip_exact_fallback_count`.
- Preview objects expose exact candidate, generated triangle, fallback, supported, method, and part-count diagnostics.

Acceptance criteria:

- Boundary-crossing triangles are clipped or split instead of leaving visible overhangs.
- Fallback clipping is visible in diagnostics.

### Phase 7 - Tests and Manual QA

Status: Completed

Tasks:

1. Add FreeCADCmd tests for:
   - [x] Design Surface roundabout clip boundary consumption
   - [x] Lane review roundabout clip
   - [x] Shoulder review roundabout clip
   - [x] Slope Face Surface roundabout handoff clip
   - [x] Side Slope review roundabout handoff clip
2. [x] Add a smoke test for `Roundabout - Single Lane`.
3. [x] Update manual QA:
   - [x] top view
   - [x] back-side view
   - [x] Breakline Audit double-click checks
   - [x] Intersections tab double-click checks

Implementation notes:

- `Roundabout - Single Lane` smoke now validates production output ownership, object tree routing, Breakline Audit readiness, per-leg clip-boundary detail rows, and Intersections tab filtering.
- Ordinary Design Surface, Subgrade Surface, Slope Face Surface, Lane review, Shoulder review, and Side Slope review are tested against roundabout clip or slope-handoff boundaries.
- Internal diagnostic contracts remain hidden from the Intersections tab by default. Roundabout boundary readiness remains visible.
- Breakline Audit surface summary rows for roundabout-clipped ordinary surfaces focus the accepted source object instead of creating offset alignment overlays.

Manual QA checklist:

1. Build `Roundabout - Single Lane` from Intersection Presets.
2. Build Applied Sections, then run Build Parametric.
3. In top view:
   - ordinary Design Surface strips stop at the roundabout approach clip boundary
   - ordinary Lane and Shoulder review strips stop at the same approach boundary
   - ordinary Side Slope and Slope Face Surface stop at the roundabout slope-handoff boundary
   - roundabout interior is owned by dedicated roundabout outputs
4. In back-side view:
   - `Roundabout Slope Face Surface` owns the roundabout outer slope ring
   - ordinary Slope Face Surface does not pass through the roundabout ownership area
   - no obsolete entry/exit connector or splitter-island surfaces are visible
5. In Breakline Audit:
   - Design Surface, Intersection Surface, and Slope Face Surface show ready
   - ordinary surface detail rows expose roundabout clip and slope-handoff boundaries
   - detail rows expose all four physical approaches: primary-start, primary-end, secondary-start, secondary-end
   - double-clicking surface summary rows should focus accepted source/output objects, not create alignment-offset ghost geometry
6. In Intersections:
   - default rows hide internal edge-network, surface-zone, shared-boundary graph, and drainage-hint diagnostics
   - `roundabout_boundary_readiness` remains visible and ready
   - double-clicking visible rows should highlight the actual roundabout boundary context

Acceptance criteria:

- [x] FreeCADCmd smoke passes.
- [x] Manual QA steps are documented for ordinary corridor outputs stopping at roundabout boundaries.
- [x] No accepted output is generated from preview mesh reverse-reading.

## Implementation Order

Use this order:

1. Boundary Contract Audit
2. Design Surface Clip Consistency
3. Lane / Shoulder Guided Review Clip
4. Slope Face / Side Slope Clip
5. Shared Breakline Handoff
6. Exact Clip Upgrade
7. Tests and Manual QA

This order keeps the source boundary stable before changing individual surface consumers.

## Risks

- Boundary loops may be incomplete for one or more physical approach legs.
- Centroid-only suppression may still leave visual overhangs at the clip boundary.
- Lane / Shoulder review highlights may appear correct while accepted Design Surface clipping is still incomplete.
- Aggregate Breakline Audit readiness may hide per-leg failures.
- Existing first-slice roundabout outputs may still expose obsolete diagnostic objects.

## Non-goals

- Do not build roundabout geometry by repairing ordinary corridor meshes.
- Do not use generated preview objects as the source of roundabout ownership.
- Do not merge ordinary Slope Face Surface and Roundabout Slope Face Surface into one output.
- Do not treat Lane / Shoulder review highlights as accepted design outputs.

## Done Criteria

The plan is complete when:

- ordinary Design Surface, Lane review, Shoulder review, Slope Face Surface, and Side Slope review all stop at roundabout ownership boundaries
- dedicated roundabout outputs own the roundabout interior
- shared breaklines connect ordinary and roundabout outputs at the handoff
- Breakline Audit exposes per-leg status
- FreeCADCmd smoke and manual QA pass for `Roundabout - Single Lane`

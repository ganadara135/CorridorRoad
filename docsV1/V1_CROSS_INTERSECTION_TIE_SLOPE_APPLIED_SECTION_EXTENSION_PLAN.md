# V1 Cross Intersection Tie Slope Applied Section Extension Plan

Last updated: 2026-07-06

## Purpose

Define a simple source-driven plan to extend `Intersection Tie Slope` coverage for Cross intersections.

The goal is to fill the slope-side transition area from the first intersection Applied Section toward the curb-return-adjacent Applied Section, using Applied Section ordering instead of generated mesh repair.

## Problem

T intersections currently produce useful `Intersection Tie Slope` panels from Applied Section transition windows.

Cross intersections still leave visible gaps around the junction because the current Cross logic keeps only the outer `transition_pair` windows and suppresses `intersection_adjacent_pair` rows that created unwanted rectangular patches.

The suppressed `intersection_adjacent_pair` rows should not be restored as-is. They create internal rectangular slope patches rather than intentional curb-return approach strips.

## Core Rule

Cross `Intersection Tie Slope` extension must be built from Applied Section result rows and Intersection source/evaluation contracts.

Do not use generated mesh, preview object geometry, or already-created surface fragments as source truth.

## Design Direction

Use the same simple idea that works for T intersections:

- find the Applied Section where the intersection context begins
- find the Applied Section immediately before the curb-return-controlled area
- build side-slope strip panels between those Applied Sections
- repeat per participating leg and side

For Cross intersections, this rule is applied independently to:

- primary road entry, left and right
- primary road exit, left and right
- each secondary road entry and exit leg, left and right

The generated surface remains `Intersection Tie Slope`.

## Non-Goals

- Do not restore Cross `intersection_adjacent_pair` as ordinary accepted Tie Slope surface rows.
- Do not generate slope panels from `Intersection Slope Face Surface` mesh.
- Do not use Intersections tab highlight objects as geometry input.
- Do not directly triangulate from the current ordinary corridor `Slope Face Surface`.
- Do not attempt watertight solid closure in this phase.

## Source Inputs

Required source/result inputs:

- `IntersectionModel`
- `IntersectionPatchPrerequisiteResult`
- `AppliedSectionSet`
- Applied Section station ordering
- Applied Section side-slope terminal edges
- control-area and active-intersection context refs
- curb-return boundary segment metadata where available

Optional diagnostic inputs:

- `IntersectionBoundarySegmentResult`
- shared breakline result
- existing Tie Slope window diagnostics

## Proposed Row Model

Add a new Cross-only Applied Section Tie Slope row role:

`curb_return_approach_pair`

This role differs from the existing rows:

- `transition_pair`: region/control boundary to first intersection Applied Section
- `intersection_adjacent_pair`: immediate internal pair; currently suppressed for Cross because it creates unwanted rectangular patches
- `curb_return_approach_pair`: Applied Section strip from the first intersection Applied Section toward the curb-return-adjacent Applied Section

The `curb_return_approach_pair` row must carry:

- `intersection_id`
- `intersection_kind`
- `alignment_ref`
- `road_role`
- `gap_role`
- `side`
- `cell_role`
- `outer_applied_section_ref`
- `inner_applied_section_ref`
- `outer_station`
- `inner_station`
- `outer_edge_xyz`
- `inner_edge_xyz`
- `loop_points_xyz`
- `loop_area_xy`
- diagnostics

## Applied Section Selection Rule

For each leg and side:

1. Collect Applied Sections by `alignment_id`.
2. Keep rows with valid side-slope terminal edge for the side.
3. Split rows into outside, transition, and intersection-context rows using:
   - `active_intersection_id`
   - `active_intersection_control_area_id`
   - `region_id`
   - station order
4. Identify the first Applied Section with active intersection context.
5. Identify the curb-return-adjacent Applied Section by walking inward from the first intersection section until one of these is true:
   - the next section would cross the curb-return boundary envelope
   - the section no longer has a stable side-slope edge
   - the section belongs to another control area or leg context
   - the max allowed approach step count is reached
6. Build strips between consecutive accepted Applied Sections in this selected range.

The first implementation may limit this to one or two Applied Section spans per leg if that is enough to reach the curb-return-adjacent area in the preset.

## Surface Generation Rule

For each `curb_return_approach_pair` row:

1. Use the two Applied Section side-slope terminal edges as strip boundaries.
2. Orient the loop consistently.
3. Reject loops with:
   - fewer than four unique points
   - near-zero area
   - self-crossing
   - excessive span length compared with station interval
   - mismatch between leg alignment and Applied Section alignment
4. Create two triangles per quadrilateral strip.
5. Store diagnostics for suppressed or rejected rows.

## Shared Breakline Rule

Every accepted strip must produce auditable shared breaklines:

- outer edge: Tie Slope to ordinary Slope Face Surface or corridor slope face context
- inner edge: Tie Slope to Intersection Slope Face Surface or curb-return approach context
- start cap: Tie Slope local boundary
- end cap: Tie Slope local boundary

If the strip reaches a curb-return-adjacent section, the inner edge should be tagged as:

`intersection_tie_slope_to_curb_return_approach`

This is an audit role first. It does not need to force direct arc matching in the first slice.

## Implementation Phases

### Phase 1 - Diagnostics and Selection

- Add helper to collect Cross leg Applied Sections by alignment and side.
- Add helper to identify first intersection Applied Section.
- Add helper to identify curb-return-adjacent Applied Section candidate.
- Add debug metadata to show selected station windows.
- Keep geometry unchanged until the selected rows are inspectable.

Acceptance:

- Cross preset reports candidate `curb_return_approach_pair` rows.
- Candidate rows show correct alignment, side, station pair, and Applied Section refs.
- Existing `intersection_adjacent_pair` remains suppressed for Cross.

### Phase 2 - Surface Rows

- Generate `curb_return_approach_pair` rows from selected Applied Section pairs.
- Feed accepted rows into `_build_intersection_tie_slope_surface`.
- Keep `transition_pair` behavior unchanged.
- Keep Cross `intersection_adjacent_pair` suppressed.

Acceptance:

- `Intersection Tie Slope` still exists.
- Cross Tie Slope triangle count increases only by accepted `curb_return_approach_pair` strips.
- No rectangular internal patches reappear.

### Phase 3 - Shared Breakline Handoff

- [x] Add shared breakline rows for accepted `curb_return_approach_pair`.
- [x] Add role summary and diagnostics to Breakline Audit.
- [x] Confirm `geometry_mismatch`, `mesh_mismatch`, and `missing_consumer` remain zero for accepted rows.

Implementation note:

- `curb_return_approach_pair` rows now use explicit shared breakline roles:
  - `intersection_tie_slope_approach_outer`
  - `intersection_tie_slope_to_curb_return_approach`
  - `intersection_tie_slope_approach_start_cap`
  - `intersection_tie_slope_approach_end_cap`
- Existing T-intersection/transition rows keep the original `intersection_tie_slope_window_*` roles.

Acceptance:

- Breakline Audit lists Tie Slope extension edges with accepted status.
- Suppressed rows remain traceable but do not appear as generated surface geometry.

### Phase 4 - Cross Regression Smoke

- [x] Extend Cross smoke test to assert:
  - `Intersection Tie Slope` preview exists when prerequisites are accepted.
  - internal `intersection_adjacent_pair` rows are not restored as generated Tie Slope rows.
  - `curb_return_approach_pair` consumed count is greater than zero.
  - accepted approach strips emit explicit shared breakline roles.
  - total Tie Slope triangle count reflects transition plus approach strips.

Implementation note:

- The current Cross implementation does not keep `intersection_adjacent_pair` rows as suppressed rows. It omits them from generated Tie Slope row output and accepts only `curb_return_approach_pair` rows for this extension.

Acceptance:

- [x] FreeCADCmd Cross smoke passes.
- [x] Existing T intersection Tie Slope smoke is not regressed.

Current verification note:

- Cross focused smoke passes after the new assertions.
- T Tie Slope preview creation was restored for zero-span T transition windows by pairing the nearest ordinary Applied Section with the first/last intersection Applied Section.
- T Tie Slope shared breakline handoff now reports the original `intersection_tie_slope_window_*` roles separately from Cross `curb_return_approach_pair` roles.
- T upper rectangular panel candidates are subdivided from source shared breaklines when a single candidate is too broad.
- T upper panel handoff roles are exposed in Breakline Audit as `intersection_upper_slope_face_panel_*` rows and consumed by the dedicated Intersection Slope Face Surface.
- T smoke now passes.
- Full Non-T smoke now passes for Cross, Skewed, and Y presets.
- Y/Skewed degenerate curb-return envelopes are promoted to a diagnostic `source_endpoint_hull` boundary loop only when the loop comes from accepted source endpoints, not from generated mesh or preview geometry.
- Cross manual QA proxy is covered by the Non-T smoke: it checks dedicated Tie Slope preview creation, Applied Section window source ownership, object separation from ordinary Slope Face and Intersection Slope Face previews, and zero shared-breakline geometry/mesh/missing-consumer mismatch.
- Cross secondary road Tie Slope now mirrors the primary road entry/exit rule. Secondary `entry` rows use `secondary_region_start_to_intersection_start`, and Secondary `exit` rows use `secondary_intersection_end_to_region_end`.

### Phase 5 - Manual QA

Manual checks:

1. Create Cross Intersection preset.
2. Build Applied Sections.
3. Build Parametric.
4. Enable `Intersection Tie Slope`.
5. Confirm Tie Slope extends from the first intersection Applied Section toward curb-return-adjacent Applied Sections.
6. Confirm the removed upper rectangular patch does not reappear.
7. Confirm ordinary corridor `Slope Face Surface` and dedicated `Intersection Tie Slope` remain separate objects.
8. Check Breakline Audit for zero geometry and mesh mismatch.

Automated proxy:

- [x] Cross preset creates `V1CorridorIntersectionTieSlopeSurfacePreview`.
- [x] Tie Slope geometry source is `accepted_applied_section_window_rows`.
- [x] Accepted Tie Slope window count is greater than zero and each window produces two triangles.
- [x] Ordinary `Slope Face Surface`, dedicated `Intersection Slope Face Surface`, and `Intersection Tie Slope` remain separate preview objects.
- [x] Breakline Audit reports zero geometry mismatch, mesh mismatch, and missing consumer count for the Cross preset.

## Risks

- Applied Section density may be insufficient near curb returns.
- Superelevation or skewed Cross layouts may cause side-slope edge orientation changes.
- Secondary road exit handling may need a second pass if the preset only records secondary entry semantics.
- Curb-return adjacency detection may need to evolve from station-only to boundary-envelope-aware selection.

## Fallback Policy

Fallbacks are allowed only as diagnostics.

If a curb-return-adjacent Applied Section cannot be identified, report:

`intersection_tie_slope_curb_return_approach_candidate_missing`

Do not create synthetic patches from preview geometry.

## Current Status

- [x] Phase 1 - Diagnostics and Selection
- [x] Phase 2 - Surface Rows
- [x] Phase 3 - Shared Breakline Handoff
- [x] Phase 4 - Cross Regression Smoke
- [x] Phase 5 - Automated QA
- [x] Phase 6 - Manual QA Proxy
- [ ] Phase 7 - Visual Manual QA

## Phase 1 Implementation Note

Implemented diagnostic-only `curb_return_approach_pair` Applied Section window rows for Cross intersections.

Current Cross preset probe:

- `transition_pair`: 6 rows
- `intersection_adjacent_pair`: 6 rows
- `curb_return_approach_pair`: 18 candidate rows

The new rows are intentionally marked `candidate` and include `intersection_tie_slope_curb_return_approach_candidate_only`, so they are visible for review but do not yet create `Intersection Tie Slope` surface triangles.

Next step: promote selected `curb_return_approach_pair` rows to accepted surface rows with guardrails against internal rectangular patch regeneration.

## Phase 2 Implementation Note

Promoted Cross `curb_return_approach_pair` rows to accepted `Intersection Tie Slope` surface rows.

Current accepted Cross preview probe:

- `curb_return_approach_pair`: 24 accepted rows
- `Intersection Tie Slope` preview: created
- `IntersectionTieSlopeTriangleCount`: 48
- `IntersectionTieSlopeAppliedSectionWindowRowCount`: 24
- `IntersectionTieSlopeAppliedSectionWindowAcceptedCount`: 24

The implementation does not depend on a non-zero Region/control-area to Applied Section transition span. When Cross control-area STA and Applied Section intersection STA are both `96-144`, the generator now selects the first or last active intersection Applied Section directly and walks inward by Applied Section order.

Secondary road handling now follows the same entry/exit split as Primary road:

- `secondary entry left`: 3 accepted `curb_return_approach_pair` rows
- `secondary entry right`: 3 accepted `curb_return_approach_pair` rows
- `secondary exit left`: 3 accepted `curb_return_approach_pair` rows
- `secondary exit right`: 3 accepted `curb_return_approach_pair` rows
- Secondary entry window kind: `secondary_region_start_to_intersection_start`
- Secondary exit window kind: `secondary_intersection_end_to_region_end`

The previous Cross `intersection_adjacent_pair` suppress policy remains in place. It is not used to create these new surface rows.

Next step: add explicit shared breakline handoff roles for accepted `curb_return_approach_pair` rows and expose them in Breakline Audit.

# V1 Intersection Upper Slope Face Rectangular Panel Plan

Last updated: 2026-07-03

## Purpose

Define a source-driven plan to replace the current upper intersection triangular/fan surface with explicit rectangular `Intersection Slope Face Surface` panels.

The user-visible problem is:

- the upper side of the T-intersection is currently filled by triangular panels
- the desired result is a rectangular panel shape that follows the green highlight-style boundary
- the panel must share breaklines with adjacent surfaces
- the panel must remain part of the dedicated `Intersection Slope Face Surface` family, not ordinary `Slope Face Surface`

## Core Rule

Upper intersection slope-face panels must be generated from accepted source/result contracts.

Do not create the panel by:

- repairing generated mesh gaps
- reading preview object geometry as source truth
- extending edge-network review geometry
- using broad center fan triangulation
- merging ordinary `Slope Face Surface` with `Intersection Slope Face Surface`

## Scope

This plan covers the upper rectangular slope-face area between:

- the upper ordinary road side-slope or shoulder-side boundary
- the upper edge of the intersection surface/central patch
- the left and right local transition/tie-slope boundaries

It applies first to the T-intersection preset and should later generalize to skewed or cross intersections only after the T case is stable.

This plan does not cover:

- central pavement patch triangulation
- curb-return internal surface generation
- `Intersection Tie Slope Surface`
- ordinary road `Slope Face Surface`
- drainage flow hints
- edge-network preview display

## Existing Symptoms

The current upper area can show:

- triangular or fan-like panels instead of rectangular panels
- panels that visually reach toward Alignment-side geometry
- panels that do not clearly share breaklines with adjacent surfaces
- Breakline Audit warnings even when mesh, geometry, and missing-consumer counts are zero
- correct lower curb-return and tie-slope surfaces, but incomplete upper rectangular coverage

## Desired Result

For the T preset, the upper side should generate one or more rectangular `Intersection Slope Face Surface` panels.

Each panel should be bounded by four explicit edges:

- `outer_edge`: upper ordinary slope-face or shoulder-side boundary
- `inner_edge`: intersection surface or central patch upper boundary
- `left_cap`: local left transition boundary
- `right_cap`: local right transition boundary

The panel should triangulate as a strip or two-triangle rectangular cell, not as a center fan.

## Source Ownership

### Acceptable Sources

The rectangular panel may consume:

- Applied Section side-slope or slope-face boundary rows
- accepted intersection boundary-loop segment refs
- accepted shared-boundary graph edge refs
- accepted `Intersection Tie Slope Surface` boundary refs at the left and right ends
- accepted `Intersection Surface` upper boundary refs

### Rejected Sources

The rectangular panel must not consume:

- generated mesh triangles
- FreeCAD preview object edges
- edge-network highlight geometry
- broad fan fallback loops
- ordinary corridor slope-face triangles as source geometry

## Result Contract

Add or reuse a result row family named:

- `intersection_upper_slope_face_panel`

Suggested fields:

- `panel_id`
- `intersection_id`
- `road_role`
- `alignment_ref`
- `side`
- `outer_edge_ref`
- `inner_edge_ref`
- `left_cap_ref`
- `right_cap_ref`
- `outer_edge_xyz`
- `inner_edge_xyz`
- `left_cap_xyz`
- `right_cap_xyz`
- `loop_points_xyz`
- `loop_area_xy`
- `source_mode`
- `status`
- `diagnostics`
- `recommended_action`

Suggested `source_mode`:

- `accepted_upper_rectangular_panel_boundary`

## Boundary Construction

### Step 1: Find Candidate Span

For each intersection:

1. Locate the upper side of the central/intersection patch.
2. Find the nearest ordinary road upper side-slope or slope-face boundary.
3. Find the left and right transition boundaries that already delimit the successful `Intersection Tie Slope Surface` or accepted local transition cells.
4. Build a candidate quadrilateral between those four edges.

### Step 2: Normalize Edge Direction

Normalize all four boundary edges into a consistent clockwise or counter-clockwise loop.

Validation should reject:

- open loops
- self-crossing loops
- zero-area loops
- loops whose long diagonal is much larger than the local intersection envelope
- loops whose centroid is outside the expected upper intersection band

### Step 3: Snap To Shared Breaklines

The panel must publish and consume shared breakline refs for:

- `upper_panel_outer`
- `upper_panel_inner`
- `upper_panel_left_cap`
- `upper_panel_right_cap`

The same physical boundary should be visible to adjacent consumers:

- `Intersection Slope Face Surface`
- `Intersection Surface`
- ordinary `Slope Face Surface`
- `Intersection Tie Slope Surface` where it meets the panel

### Step 4: Triangulate As Rectangular Strip

Use paired-edge strip triangulation:

- split the outer and inner edges into matching point counts
- create quads between matching samples
- triangulate each quad into two triangles

Do not use centroid fan triangulation for this panel.

## UI And Review

### Intersections Tab

Show user-meaningful rows only:

- `intersection_upper_slope_face_panel`

Do not expose edge-network, surface-zone, or preview-derived helper rows as if they were generation sources.

### Results Tab

The `Intersection Slope Face Surface` row should include notes such as:

- `upper_rectangular_panels=<count>`
- `upper_rectangular_panel_source=accepted_upper_rectangular_panel_boundary`
- rejected panel diagnostics, if any

### Breakline Audit

Add or update a compact handoff row:

- `Intersection Upper Slope Face Panel Handoff`

Expected status:

- `ready` when all four boundary roles are present
- `warning` when a boundary is missing or not consumed by the expected adjacent surface

### Visibility

The temporary `Intersection Upper Slope Face Panel Highlight` review object is removed.

Review now uses:

- the generated `Intersection Slope Face Surface`
- the `Intersection Upper Slope Face Panel` Results row
- the `intersection_upper_slope_face_panel` Intersections row
- the upper panel handoff roles in Breakline Audit

## Implementation Plan

| ID | Status | Task | Acceptance Criteria |
| --- | --- | --- | --- |
| IUSF-001 | Complete | Audit current upper triangular/fan generation path. | The current visible upper panels are traced to `IntersectionSlopeFaceCellResult` rows with `upper_*_transition_cell` roles consumed by `_append_intersection_slope_face_cell_tin`; preview metadata now exposes generated cell role summary and upper cell refs for replacement diagnostics. |
| IUSF-002 | Complete | Add upper panel candidate scanner. | Candidate rows are created from accepted source/result boundaries. The scanner uses `patch_to_intersection_slope_face` as the inner edge, `intersection_slope_face_to_corridor_slope_face` as the outer edge, and endpoint-pair caps as traceable local cap candidates without consuming generated mesh or preview objects. |
| IUSF-003 | Complete | Add candidate diagnostics. | Rows report missing outer, inner, left cap, right cap, open loop, self-crossing, zero area, and remote fan risk, plus edge length, cap length, bbox diagonal, bbox aspect, and bbox fill metrics. |
| IUSF-004 | Superseded | Add highlight preview. | The temporary highlight proved the candidate location during development and has now been removed. Upper panel review is handled by generated surface output, Results/Intersections rows, and Breakline Audit handoff roles. |
| IUSF-005 | Complete | Add shared breakline handoff rows. | Breakline Audit now receives `intersection_upper_slope_face_panel_inner`, `intersection_upper_slope_face_panel_outer`, `intersection_upper_slope_face_panel_left_cap`, and `intersection_upper_slope_face_panel_right_cap` rows derived from accepted upper panel candidate loops. These rows remain handoff/audit metadata until rectangular panel triangles are generated. |
| IUSF-006 | Complete | Generate rectangular panel triangles. | Accepted upper panel candidates now emit dedicated `intersection_upper_slope_face_panel` TIN triangles as two-triangle quads, with generated panel count, triangle count, panel refs, boundary refs, and diagnostics exposed on the Intersection Slope Face Surface preview. |
| IUSF-007 | Complete | Suppress overlapping triangular fan output. | When accepted rectangular upper panels are generated, legacy `upper_*_transition_cell` visible triangles are suppressed. The suppressed cell refs and count remain exposed for diagnostics so source/result traceability is preserved without overlapping visible geometry. |
| IUSF-008 | Complete | Update Results and Intersections tabs. | Results and Intersections rows expose `intersection_upper_slope_face_panel` readiness, generated/triangle counts, source mode, and suppressed legacy upper-cell count. |
| IUSF-009 | Complete | Add FreeCADCmd regression smoke. | Smoke verifies accepted/generated panel count parity, two-triangle rectangular triangulation, no broad/remote fan accepted rows, source/boundary metadata, Results row readiness, and Intersections row readiness. |
| IUSF-010 | Complete | Update manual QA. | QA explains top/bottom view checks, Results and Intersections rows, Breakline Audit handoff roles, accepted rectangular panel metadata, and failure interpretation for the upper rectangular panel. |

## Manual QA

### Setup

1. Create a fresh T-intersection preset.
2. Build Applied Sections.
3. Build Parametric.
4. Open `Build Parametric`.
5. In `Visibility`, enable:
   - `Intersection Surface`
   - `Intersection Slope Face Surface`
   - `Intersection Tie Slope Surface`
   - `Slope Face Surface`
   - `Breaklines` when checking audit rows

### Results Tab

Open `Results`.

Confirm these rows are visible:

- `Intersection Slope Face Surface`
- `Intersection Upper Slope Face Panel`

The `Intersection Upper Slope Face Panel` row should be `ready`.

Its notes should include:

- `intersection_upper_slope_face_panel`
- `upper_panels=`
- `triangles=`
- `suppressed_legacy_upper_cells=`
- `mode=upper_rectangular_panel`
- `source=accepted_upper_rectangular_panel_boundary`

Expected interpretation:

- `upper_panels=N/N` means every accepted upper panel candidate generated a visible rectangular panel.
- `triangles=2*N` means each panel was triangulated as a two-triangle quad.
- `suppressed_legacy_upper_cells>0` means the old upper triangular/fan cells were kept as diagnostics but no longer emitted as visible surface triangles.

### Intersections Tab

Open `Intersections`.

Confirm a row exists with:

- `Contract = intersection_upper_slope_face_panel`
- `Status = ready`
- `Source Status = accepted`
- `Role = upper_rectangular_panel`

The row notes should include:

- `candidates=`
- `accepted=`
- `generated=`
- `triangles=`
- `suppressed_legacy_upper_cells=`
- `mode=upper_rectangular_panel`
- `source=accepted_upper_rectangular_panel_boundary`

Double-click the row.

Expected behavior:

- Focus should use the dedicated `Intersection Slope Face Surface` preview.
- The generated rectangular panel should appear at the actual upper slope-face panel location near the intersection, not along the remote Alignment line.
- Candidate status should be read from the Intersections row notes and Breakline Audit handoff roles, not from a temporary highlight object.

### Breakline Audit Tab

Open `Breakline Audit`.

Confirm the shared-boundary roles include:

- `intersection_upper_slope_face_panel_inner`
- `intersection_upper_slope_face_panel_outer`
- `intersection_upper_slope_face_panel_left_cap`
- `intersection_upper_slope_face_panel_right_cap`

These rows prove that the rectangular panel is bounded by source/result breaklines:

- inner edge: patch to dedicated intersection slope face
- outer edge: dedicated intersection slope face to ordinary corridor slope face
- left cap: endpoint pair between inner and outer edges
- right cap: endpoint pair between inner and outer edges

Expected behavior:

- Missing role count should be zero for accepted panels.
- Geometry and mesh mismatch counts should stay zero for the upper panel handoff rows.
- Any warning should point to a missing source boundary, open loop, self-crossing loop, zero-area loop, or remote-fan risk.

### Top View Visual Check

Set the view to top.

Confirm:

- The upper panel is rectangular or near-rectangular.
- The panel sits between the main road upper slope-face edge and the intersection patch edge.
- The panel aligns with the accepted source/result boundary described in the Intersections row.
- The panel does not appear as isolated triangles along the Alignment line.
- The panel does not overlap the central pavement patch.
- The panel does not appear inside the curb-return interior.

Failure interpretation:

- A long triangular sheet means a remote endpoint pair was accepted incorrectly.
- A missing panel means the candidate scanner did not find both inner and outer breaklines.
- A panel inside the curb-return area means the wrong boundary role was consumed.

### Bottom View Visual Check

Set the view to bottom or rotate below the intersection.

Confirm:

- No hidden upper fan sheet remains below the rectangular panel.
- The old `upper_*_transition_cell` triangles are not visible.
- The rectangular footprint from below matches the top-view footprint.
- The lower curb-return and `Intersection Tie Slope Surface` remain separate from the upper panel.

Failure interpretation:

- A hidden fan below the panel means legacy upper cell triangles were not suppressed.
- A broad underside sheet means the accepted candidate is too large or remote.
- A lower curb-return overlap means the upper panel candidate consumed a lower/interior edge.

### Pass Criteria

Manual QA passes when:

- `Results` shows `Intersection Upper Slope Face Panel` as `ready`.
- `Intersections` shows `intersection_upper_slope_face_panel` as `ready`.
- `Breakline Audit` exposes all four upper panel handoff roles.
- The upper panel is a local rectangular two-triangle panel from top and bottom views.
- No broad fan, remote Alignment-side panel, central-patch panel, or curb-return-interior panel is visible.
- `Intersection Tie Slope Surface` remains visible and separate.

### If QA Fails

Use this order:

1. Check `Intersections > intersection_upper_slope_face_panel` notes for `accepted`, `generated`, and diagnostics.
2. Check `Breakline Audit` for missing upper panel roles.
3. Double-click the upper panel contract row and inspect the generated surface location.
4. If the surface is remote, fix candidate selection before changing triangulation.
5. If candidate notes are correct but the surface is wrong, fix `_append_intersection_upper_slope_face_panel_tin`.
6. If legacy fan triangles remain, fix upper cell suppression in `_append_intersection_slope_face_cell_tin`.

## Implementation Notes

### IUSF-001

The upper triangular panels are not produced by edge-network preview geometry.

The active generation path is:

1. `SharedBreaklineResult` rows provide:
   - `patch_to_intersection_slope_face`
   - `intersection_slope_face_to_corridor_slope_face`
   - `intersection_slope_face_to_design_surface`
2. `corridor_intersection_slope_face_cell_result` combines those rows into `upper_*_transition_cell` rows.
3. `_append_intersection_slope_face_cell_tin` emits visible `intersection_slope_face_upper_transition_cell` triangles from those rows.
4. The dedicated `V1CorridorIntersectionSlopeFaceSurfacePreview` now exposes:
   - `IntersectionSlopeFaceCellRoleSummary`
   - `IntersectionSlopeFaceUpperCellRefs`

This confirms that the rectangular-panel work should replace or supersede the `upper_*_transition_cell` surface output, not the successful `Intersection Tie Slope Surface` output.

### IUSF-002

An upper rectangular panel candidate scanner now runs during dedicated `Intersection Slope Face Surface` build.

The scanner records candidates only as metadata/result rows.

Source edges:

- inner edge: `patch_to_intersection_slope_face`
- outer edge: `intersection_slope_face_to_corridor_slope_face`
- left cap: endpoint pair from the inner and outer edges
- right cap: endpoint pair from the inner and outer edges
- optional cap source reference: `intersection_slope_face_to_design_surface`

The preview exposes:

- `IntersectionUpperSlopeFacePanelCandidateCount`
- `IntersectionUpperSlopeFacePanelAcceptedCount`
- `IntersectionUpperSlopeFacePanelSourceMode`
- `IntersectionUpperSlopeFacePanelCandidateRows`

The candidate scanner does not emit visible geometry yet.

### IUSF-003

Candidate diagnostics now distinguish blocking source and geometry problems before any visible panel is emitted.

Blocking diagnostics include:

- `intersection_upper_slope_face_panel_inner_edge_missing`
- `intersection_upper_slope_face_panel_outer_edge_missing`
- `intersection_upper_slope_face_panel_outer_breakline_missing`
- `intersection_upper_slope_face_panel_cap_source_missing`
- `intersection_upper_slope_face_panel_left_cap_missing`
- `intersection_upper_slope_face_panel_right_cap_missing`
- `intersection_upper_slope_face_panel_open_loop`
- `intersection_upper_slope_face_panel_zero_area`
- `intersection_upper_slope_face_panel_self_crossing`
- `intersection_upper_slope_face_panel_remote_fan_risk:*`

Candidate audit rows now include:

- inner and outer edge length
- left and right cap length
- bbox diagonal
- bbox aspect
- bbox fill ratio

Rows with blocking diagnostics are not accepted.

### IUSF-004

The temporary `ReviewIntersectionUpperSlopeFacePanelHighlight` object has been removed after the generated rectangular panel surface became reviewable.

The parent Intersection preview now clears:

- `IntersectionUpperSlopeFacePanelHighlightRef`

Candidate counts and diagnostics remain available on the dedicated `Intersection Slope Face Surface` preview and in Results/Intersections rows.

### IUSF-010

Manual QA now checks the upper rectangular panel through four surfaces:

- `Results` row readiness
- `Intersections` contract readiness and generated-surface focus
- `Breakline Audit` handoff role coverage
- top and bottom 3D visual review

The QA procedure explicitly separates accepted rectangular panel geometry from legacy upper triangular/fan cells and from `Intersection Tie Slope Surface`.

## Acceptance Rules

The work is accepted when:

- the upper triangular/fan surface is replaced by rectangular `Intersection Slope Face Surface` panel geometry
- panel geometry is source/result driven
- panel edges are represented as shared breaklines
- top and bottom views show the same local rectangular footprint
- no broad fan, remote Alignment-side panel, or preview-derived repair geometry is created
- `Intersection Tie Slope Surface` remains unchanged and separate

## Non-goals

- Do not rewrite the full intersection boundary-loop system.
- Do not reintroduce edge-network preview geometry.
- Do not use generated meshes as source truth.
- Do not merge ordinary and dedicated slope-face surfaces.
- Do not solve skewed/cross intersection panel generalization until the T preset passes QA.

## Next Step

Run the Manual QA checklist in FreeCAD.

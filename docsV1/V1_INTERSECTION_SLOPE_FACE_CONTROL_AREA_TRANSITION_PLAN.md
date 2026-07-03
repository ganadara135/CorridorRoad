# V1 Intersection Tie Slope Region Boundary Plan

Date: 2026-07-02  
Status: Reset In Progress  
Scope: rebuild `Intersection Tie Slope` from the separated Region/control-area boundary and Applied Section intersection boundary

## Purpose

Manual QA shows that the current `Intersection Tie Slope` surface still does not fill the side-slope transition gaps at the intersection boundary.

The important source distinction is:

- Region/control-area station range can be wider than the intersection core.
- Applied Section intersection station range can represent the inner intersection patch/core.
- The difference between those two ranges is the intended transition span.

For the current T-intersection preset, the observed example is:

- Region/control-area span: `96 -> 144`
- Applied Section intersection span: `105 -> 135`
- transition spans to fill:
  - primary entry: `96 -> 105`
  - primary exit: `135 -> 144`
  - secondary road tie: its own Region/control-area boundary to Applied Section intersection boundary

The user-marked red-circle areas in the manual screenshots are these transition locations.

This plan resets the work around a new rule:

`Intersection Tie Slope` must be generated from explicit transition windows between Region/control-area boundaries and Applied Section intersection boundaries.

Do not force Region STA and Applied Section intersection STA to be identical.

## Core Rule

Do not use generated preview geometry, highlighted objects, or existing mesh fragments as source truth.

The Applied Section and Slope Face highlights are useful only as visual checks. The implementation must consume the underlying source/result contracts:

- Applied Section point/link/shape rows
- Applied Section side-slope boundary rows
- Intersection boundary rows
- control-area entry/exit rows as clipping limits
- Region/control-area station ranges as the outer transition limits
- Applied Section active intersection station ranges as the inner transition limits
- shared breakline contracts

Generated surfaces are outputs only.

The implementation must keep the two source boundaries separate:

- `transition_outer_boundary`: Region/control-area boundary
- `transition_inner_boundary`: Applied Section intersection boundary

The surface between them is owned by `Intersection Tie Slope`.

## Current Failure

The current `Intersection Tie Slope` contract can pass readiness checks while still being geometrically wrong or incomplete.

The current failures are:

- it can select a terminal Applied Section near a single target station instead of a transition span
- it does not explicitly pair Region/control-area boundary STA with Applied Section intersection boundary STA
- it can generate filler inside the intersection core while leaving the actual road/intersection side-slope gap empty
- it treats primary-road entry/exit more explicitly than secondary-road transition windows
- it can pass row readiness because a local edge exists, even when the required transition span is not represented

The pairing is too coarse when it is based on only:

- `alignment + side`
- nearest contact edge
- a single intersection station
- full control-area cap strip

It must distinguish:

- primary-road Region start to Applied Section intersection start
- primary-road Applied Section intersection end to Region end
- secondary-road Region/control-area boundary to secondary Applied Section intersection boundary
- left/right side of each participating road
- local transition span and local side-slope edge pair
- whether a candidate is inside the intersection patch/curb-return interior

## Reset Decision

The following approaches are rejected for new implementation:

- forcing Region STA and Applied Section intersection STA to be identical
- using only a single intersection target station to choose terminal sections
- full `control_area_entry` to `control_area_exit` strip pairing
- broad control-area transition panels
- interior patch/curb-return filler triangles that do not touch the transition span
- nearest curb-return closure as a substitute for a missing boundary
- broad alignment-direction fan triangles
- surface generation from `edge_network` preview rows
- surface generation from `surface_zone` preview rows
- treating `boundary_loop` highlight geometry as source
- treating `Slope Face Surface` or `Intersection Slope Face Surface` meshes as input geometry

The following previously implemented active paths should be removed or disabled before the new method is expanded:

- ready surface output that is based only on broad `alignment + side` pairing
- cap clipping that does not reference both outer Region/control-area STA and inner Applied Section intersection STA
- generated cells whose centroid is inside the intersection patch or curb-return interior
- generated cells that do not intersect the intended transition span
- diagnostics or Results rows that claim readiness without reporting the separated STA pair

The following remains valid:

- visible cleanup of obsolete edge/surface/drainage review rows from user-facing Intersections and Breakline Audit tabs
- dedicated `Intersection Tie Slope` result and preview object
- dedicated `Intersection Tie Slope` shared breakline roles
- diagnostics when a source boundary cannot be accepted

## Correct Model

`Intersection Tie Slope` is a local transition surface between ordinary corridor side slope and intersection-owned side-slope/curb-return boundary.

The transition is defined by a span, not one station:

```text
Region/control-area boundary STA  ->  Applied Section intersection boundary STA
```

For primary roads there are two spans:

```text
primary entry: Region start STA -> Applied Section intersection start STA
primary exit:  Applied Section intersection end STA -> Region end STA
```

For secondary roads there is at least one span per participating secondary leg:

```text
secondary tie: secondary Region/control-area boundary STA -> secondary Applied Section intersection boundary STA
```

The exact secondary direction must come from the secondary leg/control-area source context, not from a primary-road assumption.

Each row must represent one local closed cell.

Suggested ID format:

```text
intersection-tie-slope:<intersection_id>:<road_role>:<gap_role>:<side>
```

Examples:

```text
intersection-tie-slope:starter-t_intersection:primary:entry:left
intersection-tie-slope:starter-t_intersection:primary:exit:right
intersection-tie-slope:starter-t_intersection:secondary:entry:left
intersection-tie-slope:starter-t_intersection:secondary:entry:right
```

## Gap Cell Boundary Contract

Each `Intersection Tie Slope` cell must be closed by four logical source-owned boundaries.

| Boundary | Meaning | Primary Source |
| --- | --- | --- |
| `transition_outer_edge` | ordinary road side-slope edge at the Region/control-area outer boundary | Region/control-area station range + Applied Section side-slope rows |
| `transition_inner_edge` | side-slope or intersection boundary edge at the Applied Section intersection boundary | Applied Section active-intersection rows + Intersection boundary rows |
| `left_or_start_cap_edge` | first local connector between outer and inner edges | clipped from the two accepted station edges |
| `right_or_end_cap_edge` | second local connector between outer and inner edges | clipped from the two accepted station edges |

Only cells with all four accepted boundaries may generate visible surface triangles.

The previous `road_outer_edge` and `intersection_outer_edge` names may remain as compatibility aliases, but new code should prefer the transition boundary terms.

## Target Gap Families

The first implementation target is the T-intersection preset.

| Gap Role | Description | Required |
| --- | --- | --- |
| `primary_entry_left` | primary road `Region start -> intersection start` left side transition | yes |
| `primary_entry_right` | primary road `Region start -> intersection start` right side transition | yes |
| `primary_exit_left` | primary road `intersection end -> Region end` left side transition | yes |
| `primary_exit_right` | primary road `intersection end -> Region end` right side transition | yes |
| `secondary_entry_left` | secondary road Region/control-area boundary to secondary intersection boundary, left side | yes |
| `secondary_entry_right` | secondary road Region/control-area boundary to secondary intersection boundary, right side | yes |

Additional gap families may be added later only after the above six cells are source-owned and stable.

## Boundary Selection Rules

### Transition Outer Edge

Use the Applied Section side-slope boundary located at or nearest to the Region/control-area outer boundary for the road role and gap role.

The selector must require:

- matching `alignment_ref`
- matching road role: `primary` or `secondary`
- matching side: `left` or `right`
- matching gap role: `entry`, `exit`, or secondary tie role
- station selected from Region/control-area boundary, not from the intersection core station
- valid side-slope material or role
- valid source section ref
- finite two-point edge or traceable polyline edge

Do not use Subassembly Designer preview rows.

Do not use ordinary generated `Slope Face Surface` mesh triangles.

### Transition Inner Edge

Use the Applied Section or intersection-owned boundary at the inner intersection boundary for the same road role, gap role, and side.

The selector must prefer source/result rows that are already tagged with:

- `active_intersection_id`
- `active_intersection_control_area_id`
- leg/control-area context
- station equal or nearest to the Applied Section intersection start/end boundary

The selector must reject:

- central pavement patch interior edges
- curb-return interior fan edges
- patch triangulation edges that do not face the ordinary road side-slope gap
- generic Alignment/Profile highlights
- any edge whose centroid is outside the local gap window

Preferred roles:

- `intersection_slope_face_to_corridor_slope_face`
- `curb_return_to_slope_face`
- `patch_to_slope_face`
- explicit future `intersection_tie_slope_contact`

### Cap Edges

Use the accepted transition outer and inner edge endpoints to construct cap edges.

Use `control_area_entry` and `control_area_exit` only as secondary clipping references.

They must not be triangulated as full cross-section strips.

Each cap must be clipped to the local gap interval between:

- the accepted transition outer edge endpoint
- the accepted transition inner edge endpoint

## STA Separation Contract

Each `Intersection Tie Slope` row must record the separated station pair.

Required station fields:

- `region_start_sta`
- `region_end_sta`
- `intersection_start_sta`
- `intersection_end_sta`
- `transition_outer_sta`
- `transition_inner_sta`
- `transition_span_length`
- `transition_span_role`

For the current T-intersection example:

| Road Role | Gap Role | Outer STA | Inner STA |
| --- | --- | ---: | ---: |
| primary | entry | 96 | 105 |
| primary | exit | 144 | 135 |
| secondary | entry/tie | secondary Region/control-area boundary | secondary Applied Section intersection boundary |

The exact secondary values must be derived from the secondary leg/control-area source data.

A row cannot be `ready` unless:

- `transition_span_length > tolerance`
- both station boundaries are present
- both edge boundaries are present
- the generated cell lies between the station boundaries
- the generated cell does not lie inside the central patch or curb-return interior

## Local Gap Window

Every candidate cell must first define a local gap window.

The gap window is a 2D envelope built from:

- transition outer Applied Section side-slope edge
- transition inner Applied Section/intersection boundary edge
- nearby control-area entry/exit cap segment
- road role and side context
- separated STA pair

The window is used to reject wrong geometry.

A candidate is invalid if:

- its centroid is inside the central patch or curb-return interior
- its bbox is much larger than the local gap
- it crosses the pavement patch
- it crosses to another road role
- it points toward remote Alignment geometry
- it creates a long thin fan away from the intersection

## Shared Breakline Requirements

Each accepted Tie Slope cell must emit shared breaklines for all four edges.

| Role | Consumers |
| --- | --- |
| `intersection_tie_slope_transition_outer` | `intersection_tie_slope_surface`, ordinary `slope_face_surface` |
| `intersection_tie_slope_transition_inner` | `intersection_tie_slope_surface`, `intersection_slope_face_surface` or `intersection_surface` |
| `intersection_tie_slope_start_cap` | `intersection_tie_slope_surface`, neighboring transition cell or design/slope surface |
| `intersection_tie_slope_end_cap` | `intersection_tie_slope_surface`, neighboring transition cell or design/slope surface |

Breakline audit must report these rows separately from ordinary corridor breaklines.

Compatibility aliases may be emitted temporarily for older tests:

- `intersection_tie_slope_road_outer`
- `intersection_tie_slope_intersection_outer`

Those aliases should not be used as the preferred v1 contract names after the transition.

## Result Contract

Update `IntersectionTieSlopeRow` so each row records:

- `tie_slope_id`
- `intersection_id`
- `road_role`
- `gap_role`
- `alignment_ref`
- `leg_ref`
- `control_area_ref`
- `side`
- `region_start_sta`
- `region_end_sta`
- `intersection_start_sta`
- `intersection_end_sta`
- `transition_outer_sta`
- `transition_inner_sta`
- `transition_span_length`
- `transition_span_role`
- `transition_outer_edge_xyz`
- `transition_inner_edge_xyz`
- `start_cap_edge_xyz`
- `end_cap_edge_xyz`
- `loop_points_xyz`
- `loop_area_xy`
- `source_applied_section_ref`
- `source_intersection_boundary_ref`
- `source_control_area_cap_refs`
- `shared_breakline_refs`
- `status`
- `diagnostics`
- `recommended_action`

The previous broad `inner_boundary_points_xyz` / `outer_applied_section_points_xyz` fields may remain temporarily for compatibility, but new code should prefer the explicit transition station and four-edge fields.

## Diagnostics

Add diagnostics that explain why a cell did not generate.

Required diagnostics:

- `intersection_tie_slope_gap_window_missing`
- `intersection_tie_slope_region_boundary_missing`
- `intersection_tie_slope_intersection_station_boundary_missing`
- `intersection_tie_slope_transition_span_missing`
- `intersection_tie_slope_transition_span_too_short`
- `intersection_tie_slope_transition_outer_edge_missing`
- `intersection_tie_slope_transition_inner_edge_missing`
- `intersection_tie_slope_cap_edge_missing`
- `intersection_tie_slope_contact_inside_patch`
- `intersection_tie_slope_contact_inside_curb_return`
- `intersection_tie_slope_contact_role_mismatch`
- `intersection_tie_slope_crosses_pavement`
- `intersection_tie_slope_crosses_road_role`
- `intersection_tie_slope_open_loop`
- `intersection_tie_slope_loop_self_crossing`
- `intersection_tie_slope_long_fan_rejected`

Diagnostics must appear in:

- Results tab notes
- Intersections tab row notes
- Breakline Audit notes when shared boundaries are missing
- preview object properties for FreeCADCmd validation

Results and Intersections notes must report the station pair, for example:

```text
primary entry left: transition_sta=96.000->105.000 span=9.000m
primary exit right: transition_sta=135.000->144.000 span=9.000m
```

## UI / Review Behavior

This plan is superseded by the Applied Section window-based `Intersection Tie Slope Surface` workflow.

The Intersections tab should no longer expose legacy `intersection_tie_slope` gap-cell rows by default.
Those rows were diagnostic-only and duplicated the newer user-facing review paths.

Current user-facing review should use:

- Results row: `Intersection Tie Slope Surface`
- Intersections row: `intersection_tie_slope_window`
- Breakline Audit row: `Intersection Tie Slope Window Handoff`

Double-clicking `intersection_tie_slope_window` should focus the generated `Intersection Tie Slope Surface` preview.

## Implementation Plan

| ID | Status | Task | Acceptance |
| --- | --- | --- | --- |
| ITS-STA-001 | Complete | Disable or remove ineffective active Tie Slope generation paths. | Legacy single-station Tie Slope rows now stay warning/diagnostic-only with `sta_transition_required`, no visible `Intersection Tie Slope` preview triangles are emitted, and the smoke verifies the old shared-breakline output remains disabled. |
| ITS-STA-002 | Complete | Add separated STA diagnostics. | Each Tie Slope row now records Region/control-area STA, Applied Section intersection STA, transition span role, and span length for primary and secondary roads; Results and Intersections notes expose the separated STA diagnostics while geometry remains disabled. |
| ITS-STA-003 | Complete | Derive primary transition windows. | Primary entry now reports `Region start -> intersection start`; primary exit now reports `intersection end -> Region end`; Intersections notes expose `transition_window_sta`, `transition_window_kind`, and primary entry/exit window-ready diagnostics while geometry remains disabled. |
| ITS-STA-004 | Complete | Derive secondary transition windows. | Secondary road transition windows now report `secondary_region_boundary_to_intersection_boundary` and `intersection_tie_slope_secondary_window_ready`, keeping them diagnostic-only until edge selection is rebuilt. |
| ITS-STA-005 | Complete | Select transition outer/inner edges from Applied Section source/result rows. | Terminal Applied Section outer edges are now selected from `transition_outer_sta`, inner-edge selector STA is reported from `transition_inner_sta`, and diagnostics expose the window-aware selector path while visible geometry remains disabled. |
| ITS-STA-006 | Complete | Build cap edges from the accepted station-pair edges. | Caps now report `accepted_transition_endpoint_pair`, reject overlong full-control-area-strip candidates, and rejected caps cannot be revived by loop fallback cap reconstruction. |
| ITS-STA-007 | Complete | Generate closed transition cells. | Closed cells now run a local transition-window validation pass, report `transition_cell_window=accepted`, and reject broad panels or patch/interior-source candidates before any future surface generation can be enabled. |
| ITS-STA-008 | Complete | Emit preferred transition shared breaklines. | Tie Slope shared breakline refs now use preferred `intersection_tie_slope_transition_outer`, `intersection_tie_slope_transition_inner`, start cap, and end cap roles with `intersection_tie_slope_surface` consumers; legacy inner/outer aliases remain diagnostic only. |
| ITS-STA-009 | Superseded | Update Results, Intersections, and Breakline Audit notes. | Legacy `intersection_tie_slope` Intersections rows are no longer user-facing; the newer `intersection_tie_slope_window`, Results row, and Breakline Audit handoff carry the review information. |
| ITS-STA-010 | Superseded | Update FreeCADCmd regression smoke. | The regression now verifies that legacy `intersection_tie_slope` rows are hidden from Intersections while `intersection_tie_slope_window` remains visible. |
| ITS-STA-011 | Superseded | Update manual QA. | Manual QA should follow the Applied Section window workflow instead of the diagnostic-only transition row workflow. |
| ITS-STA-012 | Superseded | Add STA-difference highlight-only overlay. | The temporary `Intersection Tie Slope Transition Gap Highlight` object has been removed after generated `Intersection Tie Slope Surface` output became available. |

## Regression Tests

The T-intersection smoke test must verify:

- legacy `intersection_tie_slope` rows are hidden from the Intersections tab
- `intersection_tie_slope_window` remains visible as the user-facing source handoff row
- generated `Intersection Tie Slope Surface` output exists when accepted Applied Section window rows are present
- generated Tie Slope triangles consume Applied Section window rows, not preview meshes or alignment fallback geometry
- Breakline Audit exposes the compact `Intersection Tie Slope Window Handoff` row
- no full control-area cap strip is triangulated

## Manual QA Checklist

Use this checklist only as archived background for the superseded diagnostic-only transition contract stage.
For current QA, use `V1_INTERSECTION_TIE_SLOPE_APPLIED_SECTION_WINDOW_PLAN.md`.

### Build Setup

1. Create the T-intersection preset.
2. Build Applied Sections with the same station setup used for the current regression smoke.
3. Open `Build Parametric`.
4. Click `Apply`.
5. Confirm the build message no longer says `Corridor Build complete`; it should use the product-level `Build complete` wording.

### Results Tab

1. Find the `Intersection Tie Slope` readiness/result row.
2. Expected current status: `missing` or `warning`, not `ready`.
3. Confirm the notes include:
   - `generation=sta_transition_required`
   - `preferred_breakline_ready=`
   - `preferred_breakline_roles=intersection_tie_slope_transition_inner,intersection_tie_slope_transition_outer,intersection_tie_slope_start_cap,intersection_tie_slope_end_cap`
   - a recommended action that tells the user to rebuild or review separated Region/control-area and Applied Section intersection boundaries
4. Confirm the row does not claim that visible Tie Slope output has been accepted.

### Intersections Tab

1. Confirm the table does not show legacy `intersection_tie_slope` rows by default.
2. Confirm the table shows the compact `intersection_tie_slope_window` row.
3. Double-click `intersection_tie_slope_window`.
4. Expected current behavior: the generated `Intersection Tie Slope Surface` preview is focused.
5. Confirm there are no user-facing `edge_network`, `surface_zone`, or `drainage_hint` rows used as generation sources.

### Visibility Tab

1. Confirm ordinary `Slope Face Surface`, `Intersection Surface`, and `Intersection Slope Face Surface` can still be toggled independently.
2. Expected current state: `Intersection Tie Slope Surface` is independently visible when accepted Applied Section window rows are present.
3. Toggling ordinary `Slope Face Surface` must not hide or create Tie Slope diagnostic highlight rows.

### Breakline Audit Tab

1. The preferred Tie Slope shared breakline roles should not appear as accepted visible shared-breakline rows until Tie Slope rows become surface-ready.
2. The audit should not report accepted legacy roles:
   - `intersection_tie_slope_inner`
   - `intersection_tie_slope_outer`
3. If the audit reports missing consumers, the recommended action should point back to separated Region/control-area and Applied Section intersection boundary review.

### 3D Manual Review

1. Inspect top and bottom views.
2. Expected current result: no visible `Intersection Tie Slope Surface` triangles yet.
3. Confirm the diagnostic-only stage does not create:
   - broad alignment-side panels
   - long fan triangles extending away from the intersection
   - interior filler inside the central pavement patch
   - filler under the curb-return interior
4. The ordinary corridor `Slope Face Surface` and dedicated `Intersection Slope Face Surface` should remain visually separate.

### Transition Gap Highlight QA

This temporary QA path is removed.
Use the generated `Intersection Tie Slope Surface`, `intersection_tie_slope_window`, and Breakline Audit handoff rows instead.

### Future Surface-Generation QA

When the next implementation stage enables visible `Intersection Tie Slope Surface` output, repeat the checklist above and add these checks:

1. Tie Slope surfaces appear only at the primary and secondary transition gaps.
2. Each visible Tie Slope cell is bounded by the four preferred shared breakline roles.
3. No Tie Slope surface appears inside the central patch or under curb-return interior geometry.
4. Toggling ordinary `Slope Face Surface`, `Intersection Slope Face Surface`, and `Intersection Tie Slope Surface` proves they are distinct output families.

## Non-Goals

- Do not fill every visible gap with cosmetic triangles.
- Do not make generated mesh or highlight geometry source truth.
- Do not use full control-area cap strips as surfaces.
- Do not revive `edge_network` or `surface_zone` as user-facing generation sources.
- Do not merge ordinary `Slope Face Surface`, `Intersection Slope Face Surface`, and `Intersection Tie Slope`.

## Recommended Next Step

Start the next implementation plan for visible `Intersection Tie Slope Surface` generation only after the diagnostic-only contract passes manual QA.

The next code slice should consume accepted `Intersection Tie Slope` transition cells and generate visible surface output from the four preferred source-owned boundaries, while keeping ordinary `Slope Face Surface` and dedicated `Intersection Slope Face Surface` separate.

<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Cross Section Viewer Layout Plan

Date: 2026-04-01

Current implementation status:

- Initial `Phase 1 + Phase 2` work is now started in the codebase.
- `Cross Section Viewer` now builds shared:
  - `planned_title_rows`
  - `planned_label_rows`
  - `planned_dimension_rows`
- viewer, compact SVG, and sheet SVG now consume the same planned row groups.
- current planner already applies:
  - band-based placement
  - span-aware dimension text selection
  - compact fallback labels for crowded cases
- initial same-band collision handling now applies slot-based stacking for planned labels and dimensions
- initial cross-band protection now also applies between:
  - `title` and `top label` bands
  - `overall/reach` and `component dimension` bands
- initial component-aware label planning now also applies for payload-driven:
  - `lane`
  - `shoulder`
  - `ditch`
  - `berm`
  - and other section component types when span allows
- component labels now use an explicit priority order so `lane/shoulder` survive before `ditch/berm/green strip` in crowded cases
- labels that cannot be placed now fall back into `planned_summary_rows`, and the viewer summary / sheet summary can surface them as hidden graphic labels
- initial `Phase 5 + Phase 6` work is now started in the codebase
- `vertical-preferred` component types can now switch to rotated labels in crowded/narrow spans
- planned rows now also carry orientation/rotation/font-scale metadata for viewer and SVG rendering
- component labels can now shrink within bounded limits before falling back to summary
- component spans now also emit shared `planned_component_marker_rows` so viewer/SVG/sheet can draw dimension-style guide lines with consistent tick/cap styling
- remaining work is still needed for broader cross-band refinement and richer sheet-side summary formatting.

## Updated Direction

Date: 2026-04-01

The current planning baseline is now adjusted to the following user-facing rules:

1. `Reach` is not the main graphic language and should be removed from the drawing area.
2. The drawing should show `actual component subdivisions` such as:
   - `lane`
   - `shoulder`
   - `ditch`
   - `berm`
   - `median`
   - `curb`
   - `sidewalk`
   - `green_strip`
3. Component labels should prefer `vertical placement`, not horizontal placement.
4. The component guide should feel closer to a section-drawing delimiter:
   - visible vertical subdivision guides
   - guide line aligned to the component span
   - component label attached to that guide
5. Dimension rows should sit clearly `below the section line` so text does not collide with the cross-section polyline.

In short:

- remove `Left/Right Reach` from the main drawing
- promote `component subdivision` to the primary graphic
- use `vertical component labels`
- push `dimensions` farther downward
- keep `summary fallback` only for overflow cases

## Goal

Unify `Cross Section Viewer`, `Export SVG`, and `Export Sheet SVG` under one drawing-rule-based layout system so labels and dimensions are placed like a section drawing rather than ad-hoc scene text.

The target direction is:

1. keep one shared layout planner
2. let the viewer and exports consume the same planned layout rows
3. rely on user zoom/pan for detailed reading instead of viewer-only text scaling tricks

## Current Problem

The current viewer draws:

- section polylines
- structure overlays
- labels
- dimensions

but text placement is still too direct:

- labels are placed from raw payload coordinates
- dimension text does not sufficiently consider available span
- narrow component widths still try to render full labels
- multiple labels can collide in the same band
- viewer and export are close, but not yet driven by one explicit layout engine

This produces overlaps when a section has:

- many component segments
- narrow lane / shoulder / ditch spans
- multi-bench side slopes
- dense structure / daylight annotations

## Design Decision

Use `drawing-rule-based placement` as the single layout model for:

- `Cross Section Viewer`
- `Export SVG`
- `Export Sheet SVG`

Do not split into:

- viewer-only fixed-size screen text
- separate export-only drawing logic

Rationale:

- one rule set is easier to predict
- one rule set is easier to test
- viewer and export become visually consistent
- users can zoom/pan in the 2D viewer when they need detail

## Core Principles

### 1. Layout Planning Before Rendering

The renderer should not decide placement directly.

Instead:

1. payload is resolved from `SectionSet`
2. layout planner creates planned rows
3. viewer/SVG/sheet render those planned rows

This means placement logic lives in one place.

### 2. Bands, Not Free Placement

Labels and dimensions should be assigned to explicit bands.

Recommended vertical bands:

- `title band`
- `component guide band`
- `component label band`
- `component dimension band`
- `overall dimension band`
- `diagnostic note band`

Each band should have:

- a base elevation
- a stacking direction
- a minimum row spacing

### 3. Span-Aware Text Rules

Every label/dimension candidate must check whether the target span is wide enough.

Possible outcomes:

1. full vertical label inside the component span
2. compact vertical label inside the component span
3. reduced-size vertical label inside the component span
4. label moved to the component-guide band
5. label suppressed from drawing and kept only in summary

### 4. Priority-Based Conflict Resolution

Not all text has the same importance.

Suggested priority order:

1. station title
2. component subdivision guides
3. component semantic labels
4. overall width
5. component width dimensions
6. structure summary
7. daylight notes

When collisions occur:

- higher priority remains
- lower priority moves to the next available slot
- if no slot works, lower priority is abbreviated or hidden

### 5. Summary Is the Safety Net

If a label or dimension is hidden in the drawing due to congestion, it should still remain available in:

- viewer summary panel
- sheet summary block

This avoids forcing every text item into the graphic area.

## Planned Layout Contract

Add a layout-planner output layer above current payload fields.

Suggested planned result groups:

- `planned_title_rows`
- `planned_label_rows`
- `planned_dimension_rows`
- `planned_note_rows`
- `planned_summary_rows`

Each planned row should carry:

- `kind`
- `role`
- `priority`
- `band`
- `x0`
- `x1`
- `y`
- `anchor`
- `text`
- `short_text`
- `min_span`
- `placement_mode`

Recommended `placement_mode` values:

- `inside_span`
- `outside_left`
- `outside_right`
- `stacked`
- `summary_only`

## Label Rules

### Component Labels

Applies to:

- lane
- shoulder
- median
- ditch
- berm
- curb
- sidewalk
- bike lane
- green strip

Rules:

1. try full text as a `vertical label` centered in the segment
2. if span is narrow, try `short_text` as a vertical label
3. if still too narrow, reduce font size within bounded limits
4. if still too narrow, move to the component guide band
5. if collision remains, move to summary only

Examples:

- `Left Shoulder`
- `Lt Shldr`
- `Shldr`

### Vertical Label Policy

For the next implementation stage, `component labels should default to vertical placement` whenever the label belongs to an actual subdivision span.

This applies to:

- `lane`
- `shoulder`
- `median`
- `ditch`
- `berm`
- `green_strip`
- `curb`
- `sidewalk`
- `bike_lane`

Rationale:

- the user explicitly wants component names to read against the component subdivision itself
- vertical labels match common section-drawing practice for repeated narrow spans
- this keeps the interior drawing cleaner than long horizontal labels crossing multiple spans
- users can zoom when they need to read smaller labels

### Vertical Label Placement Rules

The intended visual language is:

1. draw a visible vertical guide for each component boundary pair
2. draw the component label as a vertical text item aligned to that component span
3. keep the guide line long enough to read as a subdivision delimiter
4. keep the label attached to the guide rather than floating freely across the drawing

Recommended rules:

- each component span should emit a `component marker row`
- each marker row should include:
  - left boundary guide
  - right boundary guide
  - top cap / guide
  - optional tick marks
- the label anchor should align to the component midline
- the guide should extend above the section enough that the label is visually separate from the polyline

## Dimension Rules

### Remove Reach From Main Drawing

`Left Reach` and `Right Reach` should no longer be treated as main graphic dimensions in the viewer.

They may still remain available in summary/debug output if needed, but they should not compete with:

- component subdivision guides
- component labels
- overall width

### Push Dimensions Downward

The dimension band should be clearly below the section line.

Updated intent:

- `overall width` sits below the section line with a larger offset than before
- `component width dimensions` sit below that, in their own lower band
- dimension text must not overlap the section polyline
- dimension text must not overlap component labels

### Component Width Dimensions

Component width dimensions should reflect actual section parts:

- `lane`
- `shoulder`
- `ditch`
- `berm`
- `median`
- etc.

These dimensions should be derived from `component_rows`, not from `reach`.

Recommended fallback behavior:

- if `component_rows` exist:
  - show component widths
  - hide reach dimensions
- if `component_rows` do not exist:
  - keep only `overall width`
  - do not invent misleading pseudo-component labels

## Next Implementation Steps

### Phase A

1. Remove `left_reach/right_reach` from planned main-view dimensions
2. Push `overall width` and component dimension bands farther downward
3. Reduce dimension text size and increase band spacing

### Phase B

1. Use `component_rows` as the primary subdivision source
2. Draw stronger component guides for each real component span
3. Attach vertical component labels to those guides
4. Keep labels vertical by default

### Phase C

1. Add component width dimensions beneath the main drawing
2. Keep only `overall width` plus component widths
3. Suppress crowded component width rows before they overlap the polyline

### Phase D

1. Apply the same rules to viewer, SVG, and sheet SVG
2. Add regression coverage for:
   - no-component fallback
   - dense component spans
   - narrow shoulder/ditch spans
   - multi-bench sections

When `vertical-preferred` is enabled:

1. place the label at the component midpoint
2. rotate text by `-90` or `+90` depending on side/readability convention
3. align the text so the component centerline remains the anchor
4. enforce a minimum clearance from the section polyline and from dimension bands
5. if the full vertical label still does not fit, try the compact vertical label
6. if compact vertical label still does not fit, fall back to summary-only

Suggested side convention:

- `left` side: vertical text reads bottom-to-top
- `right` side: vertical text reads top-to-bottom

This can be relaxed later if a single global vertical direction proves easier to read.

### Adaptive Label Size Rules

Because the viewer allows zoom/pan, component labels do not need to stay at a fixed nominal size.

Recommended rule:

1. start from role default font size
2. compute available span/height budget
3. shrink text gradually down to a bounded minimum size
4. if the label still does not fit, try compact text
5. if it still does not fit, use summary-only fallback

Suggested first-pass bounds:

- title: keep fixed, no adaptive shrink
- top diagnostic labels: mild shrink only
- component labels:
  - default `1.00x`
  - min `0.55x`
- component dimensions:
  - default `1.00x`
  - min `0.70x`

The goal is not to make everything tiny; it is to let narrow spans remain annotated when zooming is available.

### Structural / Diagnostic Labels

Applies to:

- structure summary
- daylight note
- top-edge notes

Rules:

1. place these in dedicated diagnostic/top bands
2. do not mix them into component label band when avoidable
3. if crowded, keep one concise line in the graphic and the full line in summary

## Dimension Rules

### Dimension Levels

Dimensions should be split into three levels.

Level 1:

- component widths

Level 2:

- left reach
- right reach

Level 3:

- overall width

This keeps large dimensions away from small local dimensions.

### Span Thresholds

Each dimension row should have a `min_span`.

Suggested first-pass thresholds:

- component width dimension:
  - full text if span >= `text_width + clearance`
  - short text if span >= `short_text_width + clearance`
  - else hide in drawing
- reach dimension:
  - always attempt on outer band
- overall width:
  - always keep unless the full section is degenerate

### Dimension Text Variants

Use standardized abbreviations:

- `LANE-LF 3.50m` -> `LF Lane 3.50m` -> `3.50m`
- `Left Shoulder 1.50m` -> `Lt Shldr 1.50m` -> `1.50m`
- `Overall 12.00m` stays full unless the whole drawing is extremely constrained

### Adaptive Dimension Size Rules

Dimension text should also support controlled shrinking before suppression.

Recommended order:

1. full text at default size
2. full text at reduced size
3. compact text at reduced size
4. numeric-only text
5. summary-only for low-priority component dimensions

Hard rules:

- `overall width` should remain visible whenever geometry is valid
- `left/right reach` should remain visible unless the drawing is degenerate
- component dimensions may shrink or disappear before reach/overall dimensions do

## Collision Strategy

Use simple deterministic collision handling, not a heavy general label solver.

Recommended algorithm:

1. sort rows by `priority desc`
2. try preferred band and preferred anchor
3. test overlap against already accepted bounding boxes in the same band
4. if overlapping:
   - try next stack slot in the same band
   - if still overlapping, try fallback band
   - if still overlapping, try rotated vertical label when allowed
   - if still overlapping, reduce text size within min-size limits
   - if still overlapping, shorten text
   - if still overlapping, set `summary_only`

This should be enough for current CorridorRoad complexity.

## Viewer / Export Integration

### Viewer

Viewer should:

- render only planned rows
- keep zoom/pan/fit behavior
- stop placing raw labels directly from payload
- allow vertical labels and adaptive font scaling using the same planner metadata as exports

### Export SVG

SVG export should:

- render the same planned rows
- preserve colors and band order
- keep compact document size
- preserve planned text rotation and planned font size

### Export Sheet SVG

Sheet SVG should:

- reuse the same planned drawing rows
- use `planned_summary_rows` for right-side summary
- use a title block and notes block outside the drawing frame
- keep the same vertical-label and adaptive-font decisions as the interactive viewer

## New Planner Metadata

To support vertical labels and adaptive font sizing, planned rows should also carry:

- `rotation_deg`
- `font_scale`
- `min_font_scale`
- `orientation`
- `fit_mode`

Suggested values:

- `orientation`:
  - `horizontal`
  - `vertical`
- `fit_mode`:
  - `fixed`
  - `span_fit`
  - `summary_only`

## Implementation Phases

## Phase 5

### Objective

Introduce vertical component labels for narrow roadside components.

### Tasks

1. Add `orientation` policy by component type
2. Add vertical text planning for preferred component classes
3. Add rotated rendering support in viewer, SVG, and sheet SVG
4. Add collision checks for vertical labels against dimension bands and neighboring labels

### Exit Criteria

- `shoulder`, `ditch`, `berm`, and similar narrow roadside components can be labeled without flooding the graphic
- viewer and exports show the same rotated-label decision

## Phase 6

### Objective

Introduce controlled `span-fit` font scaling for labels and dimensions.

### Tasks

1. Add `font_scale` planning based on available span
2. Add minimum readable size per role family
3. Allow component labels/dimensions to shrink before falling back to summary
4. Extend crowded-case regressions to verify retained annotations under shrink mode

### Exit Criteria

- narrow but important labels remain visible at reduced size
- large title text no longer dominates the graphic area
- the layout becomes more readable under user zoom

## Phase 1

### Objective

Introduce the shared layout planner without changing every rendering rule at once.

### Tasks

1. Add `resolve_viewer_layout_plan(...)` helper in [obj_section_set.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/objects/obj_section_set.py) or [task_cross_section_viewer.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/ui/task_cross_section_viewer.py)
2. Convert current raw `label_rows` and `dimension_rows` into planned rows
3. Add `priority`, `band`, `min_span`, `short_text`
4. Keep existing rendering as fallback while planned rows stabilize

### Exit Criteria

- viewer can render from planned rows
- existing smoke tests still pass

## Phase 2

### Objective

Make dimensions span-aware and band-aware.

### Tasks

1. Add dimension levels
2. Add short-text variants
3. Hide or move narrow-span dimensions
4. Keep `overall width` and `reach` stable

### Exit Criteria

- narrow sections no longer produce unreadable component dimension clusters
- overall/reach dimensions remain visible

## Phase 3

### Objective

Make labels component-aware and collision-aware.

### Tasks

1. Add band-based component labels
2. Add fallback to upper bands
3. Add summary-only fallback for the lowest priority labels
4. Separate structure/daylight notes into dedicated note bands

### Exit Criteria

- component labels do not flood the main graphic area
- structure/daylight notes remain readable

## Phase 4

### Objective

Fully unify viewer and export rendering.

### Tasks

1. Remove remaining direct-placement label logic in the viewer
2. Make compact SVG use planned rows only
3. Make sheet SVG summary draw from `planned_summary_rows`
4. Add regression coverage for crowded cases

### Exit Criteria

- viewer and export produce the same semantic layout
- crowded sections remain readable after zooming

## Required Test Scenarios

At minimum, add/extend regression for:

1. simple two-lane typical section
2. narrow lane + shoulder section
3. ditch + berm section
4. single-bench side slope
5. multi-bench side slope
6. structure overlay section
7. daylight-heavy section

For each scenario, verify:

- planned rows exist
- high-priority dimensions stay visible
- low-priority labels can fall back to summary-only
- vertical-preferred component types may switch orientation when spans are narrow
- planned rows carry stable orientation/font metadata when adaptive sizing is used
- SVG and sheet SVG still contain key expected text

## Validation Criteria

This layout plan is successful when:

1. labels no longer explode across the section drawing in common cases
2. dimensions follow consistent outer/inner bands
3. viewer and export look logically the same
4. narrow spans no longer force unreadable full labels
5. users can zoom the 2D view for more detail without the layout feeling arbitrary
6. roadside component labels can use vertical orientation when that produces a cleaner section drawing

## Non-Goals

This plan does not aim to provide:

- full CAD drafting replacement
- manual drag-and-drop annotation editing
- automatic multi-sheet layout for many stations at once
- advanced typographic kerning or publication-grade label engine

## Recommended Next Step

Start with `Phase 1 + Phase 2` together:

1. introduce planned rows
2. split dimensions into bands
3. add short-text / hide rules for narrow spans

That should deliver the biggest readability improvement with the smallest risk.

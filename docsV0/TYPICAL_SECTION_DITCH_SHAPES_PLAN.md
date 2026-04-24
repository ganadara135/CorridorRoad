<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Typical Section Ditch Shapes Plan

## Goal

Extend `Typical Section` ditch handling from the current implicit two-mode behavior into an explicit multi-shape family that supports:

- `v`
- `u`
- `trapezoid`

The implementation should preserve backward compatibility with existing CSV files, presets, and downstream consumers such as:

- `SectionSet`
- `Cross Section Viewer`
- `Corridor`
- pavement / report rows


## Current State

Today the `ditch` component is interpreted inside `TypicalSectionTemplate` from existing numeric fields:

- `Width`
- `Height`
- `ExtraWidth`
- `BackSlopePct`

Current runtime behavior is effectively:

1. `ExtraWidth <= 0`
   - treat ditch as a `V-shape`
2. `ExtraWidth > 0`
   - treat ditch as a flat-bottom/open trapezoid-like ditch

This behavior is implemented in:

- [obj_typical_section_template.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/objects/obj_typical_section_template.py)


## Design Direction

Keep `Type=ditch` and add an explicit shape mode rather than splitting ditch into multiple component types.

Recommended direction:

- `Type = ditch`
- `ShapeMode = v | u | trapezoid`

Why this is preferred:

- keeps existing workflows conceptually stable
- avoids multiplying component types
- keeps `Sections` and `Cross Section Viewer` semantics clean
- makes future shape-specific parameter growth easier


## Proposed Data Contract

### Minimum Phase-1 Contract

Add a shape field for component rows:

- `Shape`

Meaning for ditch rows:

- `v`
- `u`
- `trapezoid`

Meaning for non-ditch rows:

- blank or ignored

### Backward Compatibility

If `Shape` is missing on a ditch row:

1. if `ExtraWidth <= 0`, infer `v`
2. if `ExtraWidth > 0`, infer `trapezoid`

This keeps existing files working without migration.


## Geometry Rules

### 1. V Ditch

Inputs:

- `Width`
- `Height`

Interpretation:

- one center low point
- straight side faces from top edges to the bottom point

Recommended point pattern:

- start edge
- bottom point
- end edge

### 2. Trapezoid Ditch

Inputs:

- `Width`
- `Height`
- `ExtraWidth`
- `BackSlopePct`

Interpretation:

- inner slope down to flat bottom
- flat bottom width = `ExtraWidth`
- outer slope out using `BackSlopePct`

Recommended point pattern:

- start edge
- inner bottom-left
- bottom-right
- outer top edge

### 3. U Ditch

Inputs:

- `Width`
- `Height`
- optional `ExtraWidth`
- optional future `CornerRadius`

Interpretation:

- rounded or near-rounded ditch profile

Recommended first implementation:

- do not use true curve geometry yet
- use `polyline approximation`
- generate 5 to 9 points depending on shape width/depth

Reason:

- safer for downstream corridor/section consumption
- easier regression testing
- avoids OCC instability from introducing mixed arc/spline geometry too early


## UI Plan

The `Typical Section` component table should add a `Shape` column.

Behavior:

- for `ditch` rows, user may choose:
  - `v`
  - `u`
  - `trapezoid`
- for non-ditch rows, the value is ignored or left blank

Editing guidance:

- `ditch + Shape=v`
  - `Width` and `Height` are the main controls
- `ditch + Shape=trapezoid`
  - `ExtraWidth` is flat-bottom width
  - `BackSlopePct` is outer-side slope
- `ditch + Shape=u`
  - 1st phase uses polyline approximation and may still use `Width`/`Height` primarily


## CSV Plan

Add a new component CSV column:

- `Shape`

Examples:

- `DITCH-L,ditch,left,3.000,2.000,1.000,0.000,0.000,0.000,40,true,v`
- `DITCH-L,ditch,left,3.000,2.000,1.000,1.000,-12.000,0.000,40,true,trapezoid`
- `DITCH-L,ditch,left,2.400,2.000,0.900,0.000,0.000,0.000,40,true,u`

Backward compatibility:

- if `Shape` is missing, infer from current rules

Sample files to add later:

- `typical_section_ditch_v.csv`
- `typical_section_ditch_trapezoid.csv`
- `typical_section_ditch_u.csv`

Status:

- Implemented in `Phase D3` as focused sample CSV files under `tests/samples/`


## Runtime Consumption

### Typical Section

Update:

- `component_rows(...)`
- `_segment_profile_points(...)`
- `build_top_profile(...)`

So that ditch shape mode explicitly controls the generated point pattern.

### Sections / Corridor / Viewer

These consumers should continue to rely on the generated point pattern rather than re-deriving ditch shape logic.

This keeps the system stable:

- `TypicalSectionTemplate` owns ditch geometry interpretation
- `SectionSet` preserves ditch `shape` on station-local `component_segment` rows
- `Cross Section Viewer` can label ditch rows from the same station-local `shape` contract
- downstream objects consume resolved section geometry


## Reporting And Viewer Plan

Add shape metadata to resolved component report rows where useful.

Possible forms:

- `type=ditch|shape=v`
- `type=ditch|shape=u`
- `type=ditch|shape=trapezoid`

In `Cross Section Viewer`, labels may later remain simply `ditch`, or optionally:

- `ditch-v`
- `ditch-u`
- `ditch-trap`

This should be decided after geometry support lands and real visual density is evaluated.


## Implementation Phases

### Phase D1: Explicit V / Trapezoid Contract

Status:

- Completed

Scope:

- add `Shape` field
- support explicit `v` and `trapezoid`
- preserve old inference rules
- update UI table
- update CSV load/save

Done when:

- existing files still load unchanged
- explicit `Shape=v` and `Shape=trapezoid` work
- shape is visible in summary/report rows

### Phase D2: U Ditch

Status:

- Completed

Scope:

- add `u` mode
- implement polyline approximation
- add sample CSV
- add smoke coverage

Done when:

- `u` rows produce stable top-profile points
- `SectionSet` and `Corridor` still consume them without regression

### Phase D3: Viewer / Report Refinement

Status:

- Completed

Scope:

- update `Cross Section Viewer` naming if needed
- add report fields or display text for ditch shape
- refresh wiki and CSV docs

Done when:

- viewer and report outputs can distinguish ditch shape when useful


## Regression Plan

Add or extend smokes for:

1. `Typical Section` with `ditch shape = v`
2. `Typical Section` with `ditch shape = trapezoid`
3. `Typical Section` with `ditch shape = u`
4. `SectionSet` generated from each shape
5. `Corridor` consuming each shape

Recommended target files:

- `tests/regression/smoke_typical_section_pipeline.py`
- optional new focused smoke:
  - `tests/regression/smoke_typical_section_ditch_shapes.py`


## Risks

### 1. Too Many Shape-Specific Fields

Risk:

- the component table becomes harder to understand

Mitigation:

- start with one new field: `Shape`
- reuse existing fields where possible

### 2. Curve Geometry Instability

Risk:

- true arcs/splines may destabilize downstream corridor surface assembly

Mitigation:

- first implementation of `u` uses polyline approximation only

### 3. Backward Compatibility Breakage

Risk:

- older CSV files fail to load or change appearance unexpectedly

Mitigation:

- keep inference rules when `Shape` is blank


## Recommended Next Step

Start with `Phase D1`:

1. add `Shape` to the component contract
2. support explicit `v` and `trapezoid`
3. keep old files working through inference

This gives immediate value with minimal risk and prepares the codebase for `u` support afterward.

Current status:

- `Phase D1` implemented
- `Phase D2` implemented
- `Phase D3` implemented

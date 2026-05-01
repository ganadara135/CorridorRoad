# CorridorRoad V1 Assembly Slope Bench Plan

## 1. Purpose

This document defines how v1 should add slope bench support.

It may consult the v0 `AssemblyTemplate` bench behavior as implementation reference.

V0 is not a compatibility contract for v1 bench design.

V1 should keep only the lessons that fit the v1 source -> evaluation -> result -> output -> presentation layering.

## 2. Scope

This plan covers:

- cut and fill side-slope bench source intent
- one or more bench rows per side
- repeat-to-daylight behavior
- bench-aware applied section generation
- Cross Section Viewer and corridor surface review
- quantity and exchange traceability

This plan does not make Region own bench geometry.

## 3. Core Rule

Slope bench intent belongs to `AssemblyModel`.

`RegionModel` decides where an Assembly applies.

`AppliedSectionService` evaluates the active Assembly, terrain/daylight context, and Region context into station-specific bench result rows.

Generated section wires, viewer labels, corridor surfaces, and exchange payloads are outputs.

## 4. V0 Reference Only

The v0 implementation is useful as a reference for prior behavior and edge cases.

It should not be copied field-for-field unless a v1 contract decision explicitly adopts that field.

The main lesson from v0 is ownership: side-slope bench intent belonged with Assembly-like section intent, not with generated section wires or viewer geometry.

The v0 implementation used `AssemblyTemplate` as the owner of side-slope and bench parameters.

Relevant v0 fields that may inform v1 design included:

- `UseSideSlopes`
- `LeftSideWidth`
- `RightSideWidth`
- `LeftSideSlopePct`
- `RightSideSlopePct`
- `UseLeftBench`
- `UseRightBench`
- `LeftBenchDrop`
- `RightBenchDrop`
- `LeftBenchWidth`
- `RightBenchWidth`
- `LeftBenchSlopePct`
- `RightBenchSlopePct`
- `LeftPostBenchSlopePct`
- `RightPostBenchSlopePct`
- `LeftBenchRows`
- `RightBenchRows`
- `LeftBenchRepeatToDaylight`
- `RightBenchRepeatToDaylight`
- `UseDaylightToTerrain`
- `DaylightSearchStep`
- `DaylightMaxSearchWidth`
- `DaylightMaxWidthDelta`
- `DaylightMaxTriangles`

The v0 helper behavior normalized each bench row as:

- `drop`
- `width`
- `slope`
- `post_slope`

This row shape is an implementation reference, not a required v1 storage shape.

The v0 section/profile logic resolved a side into alternating slope and bench segments.

When repeat-to-daylight was enabled, the first bench row could repeat until the available side-slope width or daylight target was reached.

The v0 viewer work also separated side-slope semantics from typical roadway components:

- `scope=typical`
- `scope=side_slope`

Recommended side-slope labels included:

- `cut_slope`
- `fill_slope`
- `bench`
- `daylight`

## 5. V1 Ownership Mapping

### 5.1 AssemblyModel

`AssemblyModel` owns reusable bench intent.

The first v1 implementation should store bench policy on side-slope components through `TemplateComponent.parameters`.

Recommended side-slope component shape:

```json
{
  "component_id": "side_slope:left",
  "kind": "side_slope",
  "side": "left",
  "width": 12.0,
  "slope": -0.5,
  "parameters": {
    "bench_mode": "rows",
    "bench_rows": [
      {"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": -0.5}
    ],
    "repeat_first_bench_to_daylight": true,
    "daylight_mode": "terrain",
    "daylight_max_width": 80.0,
    "daylight_max_width_delta": 6.0
  }
}
```

Use side-specific rows instead of global left/right Assembly fields.

This keeps v1 source rows composable and avoids adding another parallel property family outside `TemplateComponent`.

### 5.2 RegionModel

`RegionModel` references the Assembly that contains bench intent.

Region may later override bench policy through `RegionPolicySet`, but Region should not directly store bench geometry rows.

Recommended Region usage:

- use `assembly_ref = "assembly:bench-cut-road"`
- keep `structure_ref` and `drainage_refs` separate
- use `applied_layers` only for context such as `drainage`, `guardrail`, or `widening`

### 5.3 AppliedSection

`AppliedSection` should carry evaluated bench geometry as result rows.

The first implementation can represent benches through component rows:

- `kind = "cut_slope"`
- `kind = "fill_slope"`
- `kind = "bench"`
- `kind = "daylight"`
- `scope = "side_slope"` in output/viewer payloads

If the current result model cannot store `scope` directly, the mapper should derive it from component kind until the result contract is extended.

### 5.4 Corridor Surface

The daylight/slope-face surface builder should consume evaluated side-slope and bench result geometry.

It should not recalculate bench source intent independently from raw Assembly parameters.

For the first slice, corridor surface output may continue to use simplified slope-face strips if bench result points are not yet available.

The acceptance target is to replace that fallback with bench-aware side-slope breaklines.

## 6. Source Contract

### 6.1 Component Kind

Keep `side_slope` as the durable Assembly component kind.

Do not add `bench` as a primary Assembly component kind for the first slice.

Bench rows are parameters of the side-slope component.

This follows the v1 ownership decision and is consistent with the useful v0 lesson that mid-slope benching should stay with Assembly-like side-slope intent, not with generated geometry.

### 6.2 Parameters

Recommended `TemplateComponent.parameters` keys:

- `bench_mode`
- `bench_rows`
- `repeat_first_bench_to_daylight`
- `daylight_mode`
- `daylight_search_step`
- `daylight_max_width`
- `daylight_max_width_delta`
- `daylight_max_triangles`
- `cut_slope`
- `fill_slope`

Recommended `bench_mode` values:

- `none`
- `single`
- `rows`

Recommended `daylight_mode` values:

- `off`: do not run daylight tie-in behavior.
- `terrain`: search the existing ground TIN and clip/extend to the terrain daylight point.
- `fixed_width`: keep the Assembly-defined bench/side-slope profile without terrain clipping.

Recommended bench row fields:

- `drop`
- `width`
- `slope`
- `post_slope`
- `row_id`
- `label`

`drop` and `width` are length values.

`slope` and `post_slope` should use the same decimal slope convention as v1 Assembly components.

V0 bench import and migration helpers are outside this plan.

Do not add percent-to-decimal slope conversion code for bench migration unless a separate migration contract is approved later.

### 6.3 Diagnostics

Assembly validation should warn when:

- `bench_mode` is unknown
- `daylight_mode` is unknown
- `bench_rows` cannot be parsed
- a bench row has non-positive width
- `drop` is negative
- repeat-to-daylight is enabled without daylight mode or a finite search width
- side-slope width is zero while bench rows are present
- left/right side-slope signs conflict with the evaluated cut/fill direction

Diagnostics should preserve the source row and component id.

## 7. Evaluation Rules

The bench evaluator should produce a station-local side profile.

Input:

- side-slope component
- side
- station frame
- terrain/daylight sampler if available
- Region context
- structure and drainage constraints when active

Output:

- ordered side-slope segments
- bench segment rows
- daylight marker row
- diagnostics

Recommended segment row fields:

- `segment_id`
- `side`
- `kind`
- `scope`
- `station`
- `offset_start`
- `offset_end`
- `elevation_start`
- `elevation_end`
- `width`
- `slope`
- `region_ref`
- `assembly_ref`
- `component_ref`

## 8. Cut and Fill Behavior

The evaluator should classify the active side as cut or fill after comparing design edge elevation with terrain/daylight context.

If terrain is missing:

- preserve bench rows
- use Assembly side width as fallback
- emit a warning diagnostic

If terrain intersection happens before a planned bench:

- shorten or skip downstream bench rows
- emit an info diagnostic with the skipped bench count

If terrain intersection happens inside a bench:

- shorten that bench segment
- keep the segment kind as `bench`
- emit an info diagnostic

## 9. UI Direction

The Assembly editor should add a side-slope bench helper, similar in spirit to the existing ditch helper.

Recommended controls:

- side-slope row selector
- bench mode
- bench row table
- repeat first bench to daylight toggle
- daylight mode and search limits
- validation summary

Do not expose this as a Region editor feature.

Region editor should only choose the Assembly that contains the bench policy.

## 10. Viewer Direction

Cross Section Viewer should show bench geometry as side-slope context.

Recommended display:

- typical roadway components retain higher label priority
- side-slope segments use secondary styling
- benches show labels only when there is enough space
- daylight marker remains visible or appears in summary when crowded

Viewer source rows should show:

- `region_ref`
- `assembly_ref`
- `component_ref`
- `side`
- `bench row id` when available

## 11. Output and Quantity Direction

Section output should expose bench segments with `scope=side_slope`.

Quantity output should support:

- bench surface area
- slope face area
- cut/fill earthwork areas after terrain comparison

Corridor surface output should use bench breaklines for slope-face surfaces once evaluated bench points are available.

Exchange output should carry source context:

- `region_ref`
- `assembly_ref`
- `component_ref`
- `structure_ref` when a structure constrains daylight
- `drainage_ref` when ditch or drainage context affects the bench side

## 12. Implementation Order

### Phase AB1: Document and Contract Alignment

Tasks:

- [x] document v0 bench behavior as reference only
- [x] document v1 ownership mapping
- [x] define Assembly ownership for bench intent
- [x] define Region as application layer only
- [x] register this plan in `docsV1/README.md`
- [x] update `V1_ASSEMBLY_MODEL.md` with bench parameter keys

Acceptance criteria:

- [x] docs state that Assembly owns bench source intent
- [x] docs state that Region does not own bench geometry
- [x] docs preserve useful v0 lessons without making v0 behavior mandatory

### Phase AB2: Source Model and Validation

Tasks:

- [x] add bench parameter normalization helpers
- [x] support `bench_rows` in `TemplateComponent.parameters`
- [x] add Assembly validation diagnostics for bench rows
- [x] add a `Bench Cut Road` or `Benched Slope Road` preset
- [x] add focused source model tests

Acceptance criteria:

- [x] a side-slope component can store one or more bench rows
- [x] invalid bench rows produce diagnostics
- [x] presets round-trip through the Assembly object bridge

### Phase AB3: Assembly Editor

Tasks:

- [x] add a bench helper panel for selected `side_slope` rows
- [x] keep raw `Parameters` editable for compatibility
- [x] show starter defaults for single bench and repeated bench patterns
- [x] add validation output for bench warnings
- [x] add editor command tests

Acceptance criteria:

- [x] users can assign bench rows to left and right side-slope components
- [x] applying Assembly preserves bench parameters
- [x] opening the editor remains non-destructive

### Phase AB4: Applied Section Evaluation

Tasks:

- [x] add a bench profile evaluator service
- [x] convert side-slope component parameters into station-local side-slope/bench/daylight points
- [x] classify cut/fill where terrain context is available
- [x] preserve fallback behavior when terrain is missing
- [x] add result diagnostics

Acceptance criteria:

- [x] Applied Sections contain bench-aware side-slope result geometry
- [x] bench rows can be shortened or skipped by daylight intersection
- [x] diagnostics explain terrain fallback behavior
- [x] diagnostics explain skipped or shortened bench behavior after daylight intersection is implemented

Implementation note:

- `AppliedSectionService` now expands side-slope `bench_rows` into evaluated `side_slope`, `bench`, and `daylight` component rows.
- `AppliedSectionService` now adds `side_slope_surface`, `bench_surface`, and `daylight_marker` point rows outside the finished-grade edge.
- When `daylight_mode = terrain` is requested without terrain/daylight sampling in this service, the evaluator uses Assembly side-slope width and emits a `bench_daylight_fallback` warning.
- When an existing-ground TIN is supplied to the Applied Section build request, the evaluator samples along the station-local bench profile, clips the profile at terrain daylight, and emits `bench_daylight_shortened` / `bench_daylight_skipped` diagnostics when planned rows are shortened or removed.

### Phase AB5: Viewer and Review

Tasks:

- [x] expose bench segments in Section output with `scope=side_slope`
- [x] show bench labels and source rows in Cross Section Viewer
- [x] keep typical component labels higher priority than side-slope labels
- [x] add viewer contract tests

Acceptance criteria:

- [x] Cross Section Viewer distinguishes roadway components from side-slope benches
- [x] bench source traceability is visible
- [x] crowded sections remain readable

Implementation note:

- `SectionOutputMapper` now annotates `side_slope`, `bench`, and `daylight` component rows with `scope=side_slope`.
- `CrossSectionDrawingMapper` now prefers evaluated `side_slope_surface`, `bench_surface`, and `daylight_marker` point rows over side-slope fallback geometry.
- The viewer style map now colors bench rows separately from typical finished-grade rows while preserving existing FG/subgrade/ditch priority.

### Phase AB6: Corridor Surface and Quantity

Tasks:

- [x] use bench-aware breaklines in daylight/slope-face surface generation
- [x] add bench and slope-face quantity fragments
- [x] connect bench-aware output rows to earthwork review
- [x] add focused result/output tests

Acceptance criteria:

- [x] corridor daylight surfaces include bench breaklines where available
- [x] quantities can report bench/slope-face length fragments
- [x] earthwork review can trace bench geometry back to Assembly source

Implementation note:

- `CorridorSurfaceGeometryService.build_daylight_surface` now prefers evaluated `side_slope_surface` and `bench_surface` point rows when every sampled station has matching bench breaklines.
- Duplicate daylight markers at the same terminal bench point are kept in Applied Section review rows but are not emitted as duplicate mesh vertices.
- `QuantityBuildService` now emits first-slice `slope_face_length` and `bench_surface_length` fragments from evaluated side-slope breakline points.
- Quantity fragments now preserve `assembly_ref`, and Earthwork Review handoff rows summarize bench/slope-face length traces with Assembly, Region, and component refs.

### Phase AB7: Exchange Source Traceability

Tasks:

- [x] add exchange source context rows for bench segment component rows
- [x] add exchange source context rows for bench and slope-face quantity fragments
- [x] expose side-slope and bench source context counts in exchange metadata
- [x] document v0 bench import as out of scope for this phase
- [x] add exchange contract tests

Acceptance criteria:

- [x] exchange payloads can identify bench source Assembly/component rows
- [x] exchange payloads can identify bench and slope-face quantity fragments as side-slope context
- [x] v0 bench import is not part of AB7
- [x] no migration slope-unit conversion is introduced by this phase

Implementation note:

- `SectionOutput` component rows now preserve `assembly_ref` so evaluated bench component rows can be traced back to the active Assembly.
- `ExchangeOutputMapper` now emits `section_side_slope_component` source context rows for `side_slope`, `bench`, and `daylight` section component rows.
- `ExchangeOutputMapper` now emits `side_slope_quantity_fragment` source context rows for `bench_surface_length`, `slope_face_length`, and `section_side_slope_breakline` quantity fragments.
- Exchange package metadata now reports `side_slope_source_context_count` and `bench_source_context_count`.
- V0 bench import and migration tests are intentionally not included.

### Phase AB8: Package Export End-to-End Verification

Purpose:

- verify that v1 bench source context survives the full output/export path
- confirm package JSON and handoff commands expose the same source context created by `ExchangeOutputMapper`
- keep this as an export verification step, not an import or migration step

Tasks:

- [x] identify the active Structure Output / Outputs & Exchange command path that builds exchange packages
- [x] build or reuse a v1 bench sample that produces Applied Section, Section Output, Quantity Output, and Exchange Output rows
- [x] verify package JSON includes `source_context_rows` for bench component rows
- [x] verify package JSON includes `side_slope_quantity_fragment` rows for bench/slope-face quantities
- [x] verify package metadata reports `side_slope_source_context_count` and `bench_source_context_count`
- [x] verify export-readiness diagnostics do not drop bench source context
- [x] add a focused command/export contract test for bench source context package persistence
- [x] update any user-facing handoff text or package preview rows that should expose bench source context

Acceptance criteria:

- [x] a package built through the command/export path contains bench `assembly_ref`, `region_ref`, and `component_ref`
- [x] bench source context appears in persisted JSON package data, not only in an in-memory mapper result
- [x] side-slope quantity fragments remain distinguishable from generic quantity fragments
- [x] structure/IFC handoff paths preserve exchange diagnostics and do not remove bench source context rows
- [x] no v0 bench import, v0 migration mapping, or percent-slope conversion is introduced

Implementation note:

- `AppliedSectionSet` persistence now stores and restores component rows so bench component source context is not lost when command paths rebuild from the document object.
- `build_document_structure_output_package` now includes mapped `SectionOutput` rows with structure solid and quantity outputs in the exchange package input set.
- Persisted exchange package JSON now reports source context counts through export info and keeps `source_context_rows` in the exported payload.
- Structure Output panel summary text now exposes total, side-slope, and bench source context counts.
- The focused bench export contract verifies persisted package payload, exported JSON payload, and IFC handoff non-mutation of bench source context.

## 13. Non-goals

This plan does not make bench geometry editable in the viewer.

This plan does not store bench geometry in Region rows.

This plan does not require final earthwork volume balancing before bench source and result contracts are stable.

This plan does not make Drainage own side-slope bench geometry.

Drainage may constrain or annotate bench-side behavior later through explicit refs and evaluation context.

This plan does not add v0 bench import or migration behavior.

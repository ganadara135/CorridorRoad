# Parametric Road V1 SubAssembly Side-Slope Bench Plan

Date: 2026-06-16

Status: in progress

## Purpose

This document defines how side-slope bench support should move into the SubAssembly Designer workflow.

The goal is to let users design reusable `side_slope` Subassembly definitions with bench behavior, then place and optionally override them from Assembly.

## Scope

This plan covers:

- `side_slope` bench parameters in SubAssembly Designer
- Live Preview behavior for bench points and links
- Assembly placement and row-local overrides
- Applied Sections evaluation into station-specific bench geometry
- Build Parametric Slope Face Surface handoff
- Cross Section Viewer and diagnostic requirements

This plan does not cover:

- visual scripting
- Civil 3D `.pkt` compatibility
- Region-owned bench geometry
- fully automatic design-code selection

## Core Rule

SubAssembly Designer owns reusable side-slope bench behavior.

Assembly places the `side_slope` definition and may override only placement-specific parameter values.

Applied Sections evaluates the final side-slope profile at each station.

Build Parametric consumes evaluated side-slope and bench links; it should not recalculate bench source intent.

```text
SubAssembly Designer side_slope definition
  -> Assembly placement and optional overrides
  -> Applied Sections evaluated bench points and links
  -> Build Parametric Slope Face Surface
  -> Cross Section Viewer, Quantity, Watertight Solid handoff
```

## Design Goals

- Keep bench intent reusable and source-driven.
- Avoid duplicating width, slope, thickness, and material fields in Assembly.
- Keep Assembly as a placement table.
- Support simple bench rows first.
- Preserve traceability from generated slope-face surface rows back to the source Subassembly definition.
- Keep the existing Assembly bench implementation as a compatibility reference only during the transition.

## Source Contract

### Subassembly Definition

Use `kind = "side_slope"`.

Recommended Definition fields:

- `definition_id`
- `name`
- `kind = side_slope`
- `category = grading`
- `side_behavior = both`
- `enabled = true`

### Parameters

Recommended Designer parameters:

- `side_slope_width`
- `default_slope`
- `cut_slope`
- `fill_slope`
- `bench_mode`
- `bench_rows`
- `repeat_first_bench_to_daylight`
- `daylight_mode`
- `daylight_search_step`
- `daylight_max_width`
- `daylight_max_width_delta`
- `daylight_max_triangles`

Recommended `bench_mode` values:

- `none`
- `single`
- `rows`

Recommended `daylight_mode` values:

- `off`
- `terrain`
- `fixed_width`

### Bench Rows

Use a compact row format in the first implementation.

Recommended serialized format:

```text
drop,width,slope,post_slope; drop,width,slope,post_slope
```

Example:

```text
3.0,1.5,-0.02,-0.50; 3.0,1.5,-0.02,-0.50
```

Meaning:

- run the side slope for `drop`
- create a bench with `width`
- apply bench `slope`
- continue with `post_slope`

Later versions may move this into a dedicated nested bench-row table.

## Point And Link Evaluation

Applied Sections should expand a side-slope definition into alternating slope and bench segments.

Example point sequence:

```text
P0 = side-slope start edge
P1 = slope end before bench 1
P2 = bench end 1
P3 = slope end before bench 2
P4 = bench end 2
P5 = daylight or fixed-width terminal point
```

Recommended link roles:

- slope segment: `slope_face_surface`
- bench segment: `slope_face_surface`
- daylight terminal segment: `slope_face_surface`

Bench can later receive a separate `bench_surface` role, but the first implementation should keep all side-slope bench links consumable by the current Slope Face Surface builder.

## Assembly UX

Assembly should place the Designer definition.

The Assembly table should continue to show placement fields only:

- Enabled
- Subassembly ID
- Subassembly Ref
- Side
- Index
- Target Ref
- Notes

Bench values should be edited in `Selected Subassembly Detail`.

If a placement changes `bench_mode`, `bench_rows`, `side_slope_width`, `cut_slope`, or `fill_slope`, Assembly stores only changed values as `parameter_overrides`.

## SubAssembly Designer UX

The Designer should support:

- `side_slope` preset with bench parameters
- combo-box `Kind`, `Category`, `Side`, and `Enabled`
- Live Preview while editing parameters
- mouse-wheel zoom in Live Preview
- diagnostics for invalid bench rows
- visible point/link sequence for slope and bench segments

Live Preview should show:

- side-slope start point
- each bench break point
- each bench segment
- daylight or fixed-width terminal point
- diagnostic text when row parsing fails

## Applied Sections Plan

Applied Sections should:

1. Resolve the placed `side_slope` definition from Assembly.
2. Apply Assembly row-local overrides.
3. Parse `bench_rows`.
4. Build side-specific slope and bench segment rows.
5. Resolve terrain daylight when `daylight_mode = terrain`.
6. Emit evaluated Subassembly point rows.
7. Emit evaluated Subassembly link rows with `surface_role = slope_face_surface`.
8. Preserve `definition_ref` and `subassembly_ref` traceability.

Existing Assembly-side bench helpers may be reused during the first implementation, but their source ownership should be treated as transitional.

## Build Parametric Plan

Build Parametric should:

- consume Applied Sections result rows only
- build Slope Face Surface from evaluated side-slope and bench links
- avoid recalculating bench parameters from Designer or Assembly source rows
- report missing bench point/link rows as diagnostics

## Cross Section Viewer Plan

Cross Section Viewer should show:

- side-slope Subassembly source owner
- bench point rows
- bench link rows
- effective parameter values after Assembly overrides
- diagnostics when bench rows are skipped or clipped by terrain daylight

Implementation status: Done.

Current behavior:

- `SectionOutput` carries each evaluated Subassembly row's `definition_ref` and effective `parameters`.
- `SectionOutputMapper` emits `bench_point_count`, `bench_link_count`, and `side_slope_effective_parameters` summary rows.
- Cross Section Viewer summary and Source Inspector expose bench counts, effective side-slope parameters, bench mode, and bench rows.
- Subassembly Results already lists evaluated bench points and slope-face links from the Applied Sections result contract.

## Implementation Order

| Phase | Status | Work |
| --- | --- | --- |
| 1. Preset contract | Done | Added a Designer `side_slope` bench preset with bench parameters. |
| 2. Designer detail UX | Done | Improved `bench_rows` parameter display and Live Preview bench segment rendering. |
| 3. Bench row parser | Done | Centralized parsing of compact `bench_rows` into typed rows and diagnostics. |
| 4. Applied Sections evaluation | Done | Evaluate Designer-owned `side_slope` bench definitions into point/link rows. |
| 5. Assembly override QA | Done | Confirm Assembly `Selected Subassembly Detail` stores only changed bench values. |
| 6. Build Parametric QA | Done | Confirm Slope Face Surface consumes evaluated bench links. |
| 7. Viewer diagnostics | Done | Show bench points, links, and effective parameters in Cross Section Viewer. |
| 8. Manual QA | Pending | Run FreeCAD Designer -> Assembly -> Build Sections -> Build Parametric workflow. |

## Implementation Notes

### Phase 1

`Starter Road Primitives` includes `subassembly-definition:side-slope-bench-daylight`.

The preset includes the durable bench contract fields:

- `side_slope_width`
- `default_slope`
- `cut_slope`
- `fill_slope`
- `bench_mode`
- `bench_rows`
- `repeat_first_bench_to_daylight`
- `daylight_mode`
- daylight search controls

It also includes temporary scalar preview helper parameters:

- `pre_bench_width`
- `bench_width`
- `bench_slope`
- `post_slope_width`
- `post_slope`

These helper fields keep the current SubAssembly Designer Live Preview editable before the dedicated `bench_rows` parser is introduced.

### Phase 2

SubAssembly Designer now highlights bench-related parameter rows.

`bench_rows` shows a tooltip with the compact row format:

```text
drop,width,slope,post_slope; drop,width,slope,post_slope
```

Live Preview draws slope and bench links with different line styles:

- slope links use the slope-face preview color
- bench links use the bench preview color
- link labels show the link code near each segment

This makes the side-slope break sequence reviewable before Applied Sections evaluation is expanded.

### Phase 3

`subassembly_bench_row_parser` centralizes compact bench-row parsing.

The parser accepts:

- compact text: `drop,width,slope,post_slope; drop,width,slope,post_slope`
- list or tuple rows: `[drop, width, slope, post_slope]`
- dict rows with `drop`, `width`, `slope`, and `post_slope`

The parser emits typed rows:

- `row_id`
- `drop`
- `width`
- `slope`
- `post_slope`
- optional `label`

Validation diagnostics are emitted for malformed rows, non-numeric values, negative drops, non-positive widths, and non-finite slopes.

SubAssembly Designer and Subassembly definition validation now use the same parser.

### Phase 4

Applied Sections now resolves Designer-owned side-slope bench parameters before section geometry is evaluated.

Effective parameter precedence is:

```text
SubassemblyDefinition parameter default
  -> Assembly row parameters
  -> Assembly row parameter_overrides
```

For `side_slope` definitions, `side_slope_width` becomes the effective side-slope width and `default_slope` becomes the effective slope unless Assembly or overrides supply another value.

Bench segment generation now uses the centralized `subassembly_bench_row_parser`.

Parser diagnostics are carried into bench evaluation diagnostics so invalid `bench_rows` can be reported during Build Sections.

Evaluated bench and slope segments continue to emit:

- `AppliedSectionPoint` rows for Slope Face Surface construction
- `AppliedSectionSubassemblyPoint` rows for traceability and viewer handoff

### Phase 5

Assembly/Subassembly keeps Designer definitions as the reusable source.

When a placed Subassembly has a `Subassembly Ref`, `Selected Subassembly Detail` writes only changed values to `parameter_overrides`.

`bench_rows` comparison uses the centralized parser and compact normalized text, so equivalent bench rows do not create unnecessary overrides.

The Assembly detail editor displays and stores compact bench rows with semicolon-separated rows:

```text
drop,width,slope,post_slope; drop,width,slope,post_slope
```

`Reset Overrides` clears placement-local changes without modifying the SubAssembly Designer definition.

### Phase 6

Build Parametric Slope Face Surface consumes evaluated Applied Sections output.

The Slope Face Surface builder uses `subassembly_link_rows.surface_role = slope_face_surface` first, then falls back to legacy section point roles only when linked Subassembly rows are unavailable.

Bench-aware roles consumed by Build Parametric are:

- `side_slope_surface`
- `bench_surface`
- `daylight_marker`

The generated TIN quality rows include:

- `side_slope_point_count`
- `bench_breakline_count`
- `daylight_marker_count`
- `linked_slope_face_point_count`

`linked_slope_face_point_count` records how many evaluated Subassembly slope-face points were consumed, which helps confirm that Build Parametric is using Build Sections results instead of recalculating source intent.

### Phase 7

Cross Section Viewer consumes bench data from the normalized `SectionOutput` contract.

`SectionSubassemblyRow` now carries:

- `definition_ref`
- effective `parameters`

`SectionOutputMapper` adds viewer summary rows:

- `bench_point_count`
- `bench_link_count`
- `side_slope_effective_parameters`

The Viewer summary and Source Inspector expose the selected side-slope definition, bench mode, compact bench rows, and effective parameters after Assembly overrides.

## Acceptance Criteria

- User can create or load a `side_slope` bench definition in SubAssembly Designer.
- Live Preview shows bench geometry before Apply.
- Assembly can place the definition through `Subassembly Ref`.
- Assembly can override selected bench values without duplicating the definition.
- Build Sections emits bench point and link rows.
- Build Parametric generates bench-aware Slope Face Surface from evaluated result rows.
- Cross Section Viewer shows bench source ownership and effective parameter values.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Bench row text is hard to edit | User errors | Start with compact text, then add a dedicated bench-row table. |
| Assembly and Designer both appear to own bench | Confusing UX | Keep Assembly table placement-only and hide duplicated geometry fields. |
| Terrain daylight clipping creates unexpected results | Surface gaps | Emit diagnostics and show clipped daylight points in review. |
| Build Parametric consumes source rows directly | Breaks v1 layering | Keep all surface generation result-driven from Applied Sections. |

## Non-goals

- Making Region own bench geometry.
- Creating separate `bench` Assembly rows for the first implementation.
- Creating watertight bench solids in the first side-slope bench slice.
- Automatic bench design from jurisdictional standards.

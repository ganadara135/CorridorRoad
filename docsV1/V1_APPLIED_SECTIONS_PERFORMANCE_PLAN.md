# CorridorRoad V1 Applied Sections Performance Plan

Date: 2026-05-02
Status: Implemented
Scope: Applied Sections execution speed

Depends on:

- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_TIN_SAMPLING_CONTRACT.md`
- `docsV1/V1_TIN_ENGINE_PLAN.md`

## 1. Purpose

This plan defines the first performance pass for the v1 `Applied Sections` command.

The goal is to reduce execution time without changing the v1 source -> evaluation -> result -> output -> presentation layering.

## 2. Scope

This plan includes two active changes:

- delayed `AppliedSectionSet` review shape generation
- reusable TIN sampling spatial index/cache

This plan does not include:

- incremental station rebuild
- background worker threading
- Build Corridor surface meshing changes
- v0 import behavior
- direct editing of generated section geometry

## 3. Core Rule

`Applied Sections` should build station-wise result data first.

Large review shapes and expensive TIN query preparation should run only when they are required.

Generated review wires remain presentation artifacts.

Applied Sections no longer exposes a `Fast Evaluation` mode. If an existing-ground TIN is available, terrain daylight evaluation stays on the exact terrain path.

## 4. Current Bottlenecks

### 4.1 Review Shape Cost

`V1AppliedSectionSet` currently builds an all-station 3D review shape when the result object is written.

The object is hidden by default, but the shape creation cost is still paid during Apply.

### 4.2 Terrain Daylight Cost

Bench/daylight terrain evaluation samples EG TIN at many candidate points for each station.

The original XY sampling path scanned all TIN triangles per query.

The cost pattern can become:

`station_count * side_count * sample_count * tin_triangle_count`

### 4.3 Recompute Cost

The `V1AppliedSectionSet` proxy can rebuild the review shape again during recompute.

This duplicates cost after Apply.

## 5. Change 1 - Delayed Review Shape Generation

### 5.1 Intent

Do not build the all-station `AppliedSectionSet` Part shape during normal Apply.

The result object should persist source/result rows immediately, but its visual review shape should be generated only when requested.

### 5.2 Proposed Behavior

Default Apply behavior:

- write `StationValues`, `Frame*`, `PointRows`, `ComponentRows`, diagnostics, and source refs
- set a lightweight empty shape
- set `ReviewShapeStatus = "not_built"`
- keep the object hidden

When the user unhides the object or requests full section review:

- build the review shape from persisted rows
- set `ReviewShapeStatus = "built"`
- record `ReviewShapeStationCount`

### 5.3 Code Targets

- `freecad/Corridor_Road/v1/objects/obj_applied_section.py`
- `freecad/Corridor_Road/v1/commands/cmd_generate_applied_sections.py`

### 5.4 Acceptance Criteria

- Applying `Applied Sections` does not call full `build_v1_applied_section_set_shape()` by default.
- The persisted object can still be converted back to `AppliedSectionSet`.
- Unhide or explicit review-shape command can build the same full review wires.
- Existing single-row `Applied Section Preview` still works.

## 6. Removed Change - Applied Sections Fast Mode

Fast Evaluation was removed from Applied Sections.

Reason:

- Applied Sections should remain the evaluated section result source.
- A separate fast mode made it unclear whether slope/daylight rows followed exact terrain evaluation.
- Performance should be improved by delayed review shapes and indexed TIN sampling instead of skipping terrain evaluation.

Current behavior:

- no `Fast Evaluation` checkbox
- no deferred terrain daylight diagnostic
- EG TIN daylight clipping is evaluated when an EG TIN is available

## 7. Change 2 - TIN Sampling Spatial Index/Cache

### 7.1 Intent

Avoid scanning every TIN triangle for each XY query.

TIN sampling should prepare a reusable spatial index per TIN surface and query only candidate triangles near the XY location.

### 7.2 Proposed Index

Start with a lightweight uniform grid index:

- compute XY bounding box for each triangle
- assign triangle ids to grid cells touched by the triangle bounding box
- on `sample_xy`, find the query cell and test only candidate triangles
- fall back to full scan only when no index exists or no candidate is found

### 7.3 Cache Key

Cache should be tied to the TIN surface object identity and geometry size.

Recommended initial key:

- `surface_id`
- `len(vertex_rows)`
- `len(triangle_rows)`
- optional Python object id for in-process cache

### 7.4 Code Targets

- `freecad/Corridor_Road/v1/services/evaluation/tin_sampling_service.py`

### 7.5 Acceptance Criteria

- `TinSamplingService.sample_xy()` returns the same results as the current implementation for existing contract tests.
- Dense repeated sampling reuses the prepared index.
- If index lookup has no candidates, sampling falls back safely.
- No consumer needs to know whether indexed or full-scan sampling was used.

## 8. Implementation Order

### Step AP1 - Delayed Review Shape

Implement delayed `V1AppliedSectionSet` shape generation.

Status: completed on 2026-05-02.

Acceptance:

- Apply stores result rows without building all-station wires.
- Unhide or explicit shape request can build them.

### Step AP2 - Fast Evaluation Option

Status: removed on 2026-05-02.

Applied Sections no longer has a fast evaluation option. Terrain daylight evaluation remains exact when EG TIN is available.

### Step AP3 - TIN Sampling Index

Add indexed `sample_xy` lookup with fallback.

Status: completed on 2026-05-02.

Acceptance:

- Existing TIN sampling behavior remains compatible.
- Exact Terrain mode benefits from cached candidate lookup.

### Step AP4 - Focused Validation

Run focused tests for:

- Applied Sections command
- AppliedSection service bench/daylight behavior
- TIN sampling contract
- Build Corridor drainage/daylight cases that consume AppliedSection rows

Status: completed on 2026-05-02 for the focused contracts listed above.

## 9. Diagnostics and UX

Applied Sections summary should keep performance state simple.

Recommended status text:

- `Review shape: not built`
- `Review shape: built`

The user should not need to choose between fast and exact section evaluation modes.

## 10. Non-Goals

This plan does not make Applied Sections a corridor surface builder.

It does not move final corridor surface ownership out of Build Corridor.

It does not make hidden review wires the source of engineering truth.

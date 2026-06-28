# V1 Slope Face Strip Topology Plan

Status: Draft implementation plan

Last updated: 2026-06-28

## 1. Purpose

This plan defines how Parametric Road v1 should build ordinary-road Slope Face Surface strips from Applied Sections without cross-connecting unrelated side-slope, bench, or daylight rows.

The immediate problem is visible when dense supplemental Applied Sections are enabled. Applied Section previews show side-slope breaklines at many station rows, but the generated Slope Face Surface can still show missing strips, twisted strips, or triangles that visually bridge the wrong side-slope rows.

## 2. Core Rule

Slope Face Surface must be a station-ordered strip surface built from source/evaluation-owned side-slope breakline identity.

It must not rely only on:

- left/right side
- lateral offset ordering
- polyline length ratio
- generated preview mesh cleanup

The strip builder must know which side-slope segment in one Applied Section corresponds to which side-slope segment in the next Applied Section.

## 3. Current Implementation Summary

The current implementation already respects Applied Section order.

The current build path is:

1. `CorridorSurfaceGeometryService.build_daylight_surface`
2. `_section_rows_for_request`
3. `_build_daylight_surface_from_side_slope_points`
4. `_side_slope_point_grids`
5. `_harmonized_side_slope_pair_rows`
6. `_append_side_slope_strip_triangles`

The important current behavior is:

- section rows are consumed in Applied Section station order
- left and right side-slope grids are built separately
- each station row is converted to a side-slope polyline
- adjacent station rows are meshed as strips
- if point counts differ, pair rows are harmonized using polyline length parameters

This means the current problem is not that station order is ignored.

The problem is that the strip identity is too weak.

## 4. Current Weaknesses

### 4.1 Weak strip identity

Current matching is mostly based on:

- side label
- row order
- lateral offset ordering
- harmonized polyline parameter

This is not enough when side-slope topology changes between stations.

Examples:

- one station has only `side_slope_surface -> daylight_marker`
- another station has `side_slope_surface -> bench_surface -> side_slope_surface -> daylight_marker`
- one station uses a linked `slope_face_surface` subassembly link
- another station falls back to legacy `side_slope_surface` point roles
- one station has terrain daylight hit
- another station falls back to fixed-width daylight
- a Region or Assembly changes between two adjacent station rows

### 4.2 Side-slope polyline harmonization is geometric, not semantic

`_harmonized_side_slope_pair_rows` makes two polylines have matching point counts by using normalized 3D polyline distance.

This is useful for simple shape interpolation, but it does not prove that two points represent the same engineering breakline.

### 4.3 Region and Assembly changes are not first-class strip boundaries

If adjacent Applied Sections belong to different Regions, Assemblies, Subassembly templates, or transition-generated rows, the strip builder should decide whether to:

- continue a compatible strip
- split the strip run
- generate an explicit transition strip
- report a diagnostic

The current builder can still attempt to connect rows when the topology has changed.

### 4.4 Daylight and fallback mixing is not isolated enough

Terrain daylight hits and fixed-width fallback rows should not silently share one strip run without diagnostics.

When `daylight_marker` exists in some rows but not others, or when fallback terrain adjustment creates a substitute marker, the output should record the continuity condition.

## 5. Target Design

Introduce a normalized Slope Face Strip Topology contract inside the Build Parametric pipeline.

The contract should sit between Applied Sections and TIN triangles:

```text
AppliedSection point/link rows
-> SlopeFaceStripTopologyResult
-> SlopeFaceStripRun rows
-> SlopeFaceStripSpan rows
-> TIN vertices and strip triangles
-> Slope Face Surface preview/output
```

Generated mesh remains an output.

The topology result is a result contract, not editable source intent.

## 6. Strip Identity Model

Each strip lane should have a stable identity key.

Recommended key fields:

- `alignment_id`
- `side`
- `region_id`
- `assembly_id`
- `template_id`
- `subassembly_ref`
- `surface_role`
- `link_code` or derived link identity
- `segment_role`
- `segment_index`
- `daylight_mode`

Minimum practical first slice:

```text
alignment_id
+ side
+ region_id
+ assembly_id
+ subassembly_ref
+ role_sequence_signature
```

Where `role_sequence_signature` is a compact string such as:

```text
terminal_edge|side_slope_surface|daylight_marker
terminal_edge|side_slope_surface|bench_surface|side_slope_surface|daylight_marker
```

## 7. Topology Rows

### 7.1 `SlopeFaceStripPoint`

Fields:

- `point_id`
- `station`
- `section_ref`
- `alignment_id`
- `region_id`
- `assembly_id`
- `side`
- `strip_key`
- `segment_index`
- `point_role`
- `surface_role`
- `subassembly_ref`
- `source_point_ref`
- `x`
- `y`
- `z`
- `lateral_offset`
- `source_status`
- `diagnostics`

### 7.2 `SlopeFaceStripRun`

Fields:

- `run_id`
- `strip_key`
- `alignment_id`
- `side`
- `station_start`
- `station_end`
- `section_count`
- `role_sequence_signature`
- `source_status`
- `continuity_status`
- `diagnostics`

### 7.3 `SlopeFaceStripSpan`

Fields:

- `span_id`
- `run_id`
- `from_section_ref`
- `to_section_ref`
- `station_start`
- `station_end`
- `from_point_count`
- `to_point_count`
- `mesh_mode`
- `triangle_count`
- `diagnostics`

## 8. Implementation Phases

### Phase 1: Audit Current Strip Topology

Goal:

Expose why a Slope Face span was connected, split, harmonized, or skipped.

Work:

- add an internal diagnostic collector around `_side_slope_point_grids`
- record per-section side-slope row signatures
- record point counts by side, role, subassembly ref, and daylight marker presence
- record adjacent span compatibility
- attach summary quality rows to Slope Face Surface

Quality rows:

- `slope_face_strip_run_count`
- `slope_face_strip_span_count`
- `slope_face_strip_split_count`
- `slope_face_strip_harmonized_span_count`
- `slope_face_strip_topology_mismatch_count`
- `slope_face_daylight_fallback_mix_count`

Acceptance:

- Build Parametric can report whether Slope Face strip topology is continuous, warning, or error.
- Dense supplemental Applied Sections expose mismatch locations instead of silently producing confusing strips.

### Phase 2: Stable Strip Key Builder

Goal:

Build side-slope rows into explicit strip runs instead of one broad left/right grid.

Work:

- create `_slope_face_strip_key_for_section_side`
- include alignment, side, region, assembly, subassembly refs, and role sequence
- group consecutive sections into compatible strip runs
- split runs when key changes
- do not connect incompatible rows across a split

Acceptance:

- Region or Assembly changes no longer create accidental cross-strip triangles.
- Left and right side remain isolated.
- Different side-slope topology signatures become separate runs unless an explicit transition rule handles them.

### Phase 3: Semantic Point Matching

Goal:

Match points by source identity before falling back to geometric harmonization.

Matching order:

1. same `subassembly_ref` and same `point_id`
2. same `subassembly_ref` and same point role sequence index
3. same role sequence index within the same strip run
4. harmonized polyline parameter fallback with warning

Work:

- extend `_harmonized_side_slope_pair_rows`
- add semantic pair matching before distance-parameter interpolation
- preserve source refs in generated interpolation points
- record fallback harmonization diagnostics

Acceptance:

- simple side-slope rows create deterministic strips
- bench rows match bench rows
- daylight markers match daylight markers
- mismatched rows report diagnostics instead of silently pretending to be equivalent

### Phase 4: Transition Span Handling

Goal:

Handle controlled topology changes without holes or twisted triangles.

Cases:

- no bench -> bench
- bench -> no bench
- fixed daylight -> terrain daylight
- Region transition
- Assembly transition
- surface transition generated rows

Work:

- add `mesh_mode` values:
  - `direct_semantic_strip`
  - `role_sequence_transition_strip`
  - `width_interpolation_transition`
  - `skipped_incompatible_topology`
- add transition strip generation when point roles can be safely interpolated
- skip and diagnose when topology cannot be safely connected

Acceptance:

- topology changes are visible and deterministic
- unsafe connections are not meshed
- skipped spans appear in diagnostics and Breakline Audit context

### Phase 5: Breakline Audit Integration

Goal:

Make Slope Face strip topology visible in the existing Breakline Audit workflow.

Work:

- attach strip run refs to Slope Face Surface provenance
- attach strip span refs to constraint segment metadata where applicable
- add Breakline Audit notes for:
  - strip split count
  - topology mismatch count
  - fallback harmonization count
  - skipped incompatible spans

Acceptance:

- user can identify whether Slope Face failure is a shared breakline mismatch or a strip topology mismatch
- Breakline Audit Recommended Action distinguishes source topology fixes from rebuild-only actions

### Phase 6: Tests

Focused tests:

- straight road with identical side-slope rows creates one strip run per side
- dense supplemental curved road preserves station order
- bench side-slope rows create bench-aware strips
- point-count mismatch produces topology warning
- Region change splits strip runs
- Assembly change splits strip runs
- terrain/fallback daylight mix reports warning
- incompatible topology does not create cross-strip triangles

Acceptance:

- tests verify triangle IDs or span metadata follow adjacent station pairs
- tests verify no triangle connects non-adjacent sections in ordinary Slope Face Surface
- tests verify skipped spans are explicit diagnostics, not silent holes

### Phase 7: Manual QA

Manual QA scenario:

1. Build Alignment, Profile, Stations, Assembly, Regions.
2. Enable dense Applied Section supplemental sampling.
3. Build Applied Sections.
4. Show all Applied Sections preview.
5. Build Parametric.
6. Review Slope Face Surface.
7. Open Breakline Audit.
8. Confirm Slope Face topology status.
9. Focus the problematic strip run or span if diagnostics exist.

Acceptance:

- Slope Face Surface shows continuous strips where source topology is compatible.
- No side crosses over to the opposite side.
- No Region/Assembly transition is silently bridged.
- If a strip is skipped, the user sees the station span and recommended action.

## 9. User-Facing Recommended Actions

When a topology issue exists, Build Parametric should suggest one of:

- `Review Assembly side-slope definitions, then rebuild Applied Sections`
- `Review Region boundary and Assembly assignment, then rebuild Applied Sections`
- `Review side-slope daylight mode and terrain coverage`
- `Add a Surface Transition range for this Region boundary`
- `Reduce supplemental density only for visual review; do not use this as an engineering fix`
- `Rebuild Applied Sections, then Build Parametric`

## 10. Non-Goals

- Do not repair generated Slope Face mesh after triangulation.
- Do not infer design intent from preview geometry.
- Do not merge left and right side-slope strips.
- Do not treat dense supplemental sampling as the source of design intent.
- Do not hide topology mismatch by simply smoothing the display.

## 11. Completion Criteria

The plan is complete when:

- Slope Face Surface is generated from explicit strip runs and spans.
- Adjacent Applied Section order is preserved and testable.
- Strip identity is stable across dense supplemental sampling.
- Incompatible topology is split or diagnosed.
- Build Parametric reports Slope Face strip topology health.
- Breakline Audit can distinguish strip topology problems from shared breakline geometry problems.

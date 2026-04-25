# CorridorRoad V1 Section Output Schema

Date: 2026-04-25
Branch: `v1-dev`
Status: Draft baseline, section frame summary and cut/fill quantity slices complete
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_VIEWER_PLAN.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`

## 1. Purpose

This document defines the normalized section-output contract for v1.

It exists so that:

- Cross Section Viewer
- 3D section review
- SVG and DXF section exports
- section sheets
- quantity and earthwork consumers

can all consume the same section payload family rather than recomputing section meaning independently.

## 2. Scope

This schema document covers:

- `SectionOutputSchema`
- `SectionSheetOutputSchema`
- required payload families for current-station review
- required payload families for multi-station section sheets

This document does not define:

- the source section model itself
- detailed drawing-sheet aesthetics
- every possible future export field

## 3. Core Rule

Section outputs are derived from:

- `AppliedSection`
- `AppliedSectionSet`

They are not direct authoring sources.

No consumer should assume it is allowed to persist engineering changes by mutating section output payloads.

## 4. Schema Versioning

Recommended initial versions:

- `SectionOutputSchemaVersion = 1`
- `SectionSheetOutputSchemaVersion = 1`

Each payload should expose its schema version explicitly.

## 5. Output Family Overview

### 5.1 SectionOutput

Purpose:

- represent one current or selected station section for review and export

### 5.2 SectionSheetOutput

Purpose:

- represent a collection of ordered section outputs prepared for multi-station drawing/report layouts

## 6. SectionOutput Root Structure

Recommended top-level fields:

- `schema_version`
- `section_output_id`
- `applied_section_id`
- `project_id`
- `alignment_id`
- `profile_id`
- `station`
- `station_label`
- `region_id`
- `template_id`
- `unit_context`
- `coordinate_context`
- `summary_rows`
- `geometry_rows`
- `component_rows`
- `dimension_rows`
- `terrain_rows`
- `structure_rows`
- `ownership_rows`
- `diagnostic_rows`
- `quantity_rows`
- `review_rows`

## 7. Required Root Metadata

### 7.1 Identity metadata

Required identity fields should include:

- `section_output_id`
- `applied_section_id`
- `alignment_id`
- `template_id`
- `region_id`

### 7.2 Station metadata

Required station fields should include:

- `station`
- `station_label`
- optional `station_kind`

Recommended `station_kind` examples:

- `regular`
- `key_station`
- `region_boundary`
- `event_station`
- `bookmarked_review_station`

### 7.3 Unit metadata

Required unit metadata should include:

- `linear_unit`
- `slope_unit`
- `area_unit` where relevant

### 7.4 Coordinate metadata

Required coordinate metadata should include:

- `coordinate_mode`
- optional local/world note

## 8. Geometry Rows

### 8.1 Purpose

`geometry_rows` carry the geometric primitives needed for display and export.

### 8.2 Recommended geometry row kinds

- `section_polyline`
- `component_span_polyline`
- `terrain_intersection_polyline`
- `structure_outline_polyline`
- `guide_line`
- `marker_line`

### 8.3 Recommended geometry row fields

- `row_id`
- `kind`
- `x_values`
- `z_values`
- `closed`
- `style_role`
- `source_ref`

### 8.4 Geometry rule

Geometry rows should carry enough structure for rendering but should not replace semantic rows.

## 9. Component Rows

### 9.1 Purpose

`component_rows` are the most important semantic rows for section review.

They identify what the user is actually looking at.

### 9.2 Recommended component row fields

- `component_id`
- `component_kind`
- `template_id`
- `side`
- `order`
- `enabled`
- `x0`
- `x1`
- `z0`
- `z1`
- `span`
- `parameter_summary`
- `geometry_ref`

### 9.3 Recommended component row semantics

Component rows should survive even when:

- labels are hidden
- rendering style changes
- exports use different geometry detail levels

### 9.4 Supported kinds

Initial component kinds should align with the section model, including:

- `lane`
- `shoulder`
- `median`
- `sidewalk`
- `bike_lane`
- `green_strip`
- `curb`
- `gutter`
- `ditch`
- `berm`
- `side_slope`
- `bench`
- `pavement_layer`

## 10. Dimension Rows

### 10.1 Purpose

`dimension_rows` support viewer dimensions, SVG dimensions, DXF dimensions, and section-sheet layouts.

### 10.2 Recommended dimension row fields

- `dimension_id`
- `role`
- `x0`
- `x1`
- `value`
- `display_label`
- `priority`
- `band_role`
- `related_component_id`

### 10.3 Recommended roles

- `component_width`
- `overall_width`
- `offset`
- `structure_clearance`
- `terrain_reach`

## 11. Terrain Rows

### 11.1 Purpose

`terrain_rows` describe how the section interacts with terrain.

### 11.2 Recommended terrain row fields

- `terrain_row_id`
- `kind`
- `source_surface_id`
- `side`
- `x`
- `z`
- `status`
- `geometry_ref`
- `notes`

### 11.3 Recommended terrain kinds

- `terrain_intersection`
- `daylight_hit`
- `daylight_fallback`
- `terrain_gap_warning`

## 12. Structure Rows

### 12.1 Purpose

`structure_rows` describe structure-related section behavior.

### 12.2 Recommended structure row fields

- `structure_row_id`
- `structure_id`
- `kind`
- `interaction_mode`
- `x0`
- `x1`
- `z0`
- `z1`
- `geometry_ref`
- `notes`

### 12.3 Recommended interaction modes

- `reference_only`
- `clearance_check`
- `notch`
- `skip`
- `localized_replacement`

## 13. Ownership Rows

### 13.1 Purpose

`ownership_rows` support source tracing and editor handoff.

This row family is required by the viewer model.

### 13.2 Recommended ownership row fields

- `ownership_id`
- `target_kind`
- `target_id`
- `component_id`
- `template_id`
- `region_id`
- `override_id`
- `structure_id`
- `source_owner_kind`
- `source_owner_id`
- `editable_in`

### 13.3 Recommended source owner kinds

- `template`
- `region`
- `override`
- `structure_rule`
- `superelevation`
- `profile`

### 13.4 Handoff rule

An ownership row should provide enough information for the viewer to identify the correct source editor target without re-running deep ad-hoc inference.

## 14. Diagnostic Rows

### 14.1 Purpose

`diagnostic_rows` surface engineering and review issues in a normalized way.

### 14.2 Recommended diagnostic row fields

- `diagnostic_id`
- `severity`
- `kind`
- `message`
- `related_component_id`
- `related_region_id`
- `related_structure_id`
- `related_geometry_ref`
- `action_hint`

### 14.3 Recommended severity values

- `info`
- `warning`
- `error`

### 14.4 Recommended diagnostic kinds

- `terrain_missing`
- `daylight_fallback`
- `structure_conflict`
- `override_conflict`
- `transition_warning`
- `stale_output`

## 15. Quantity Rows

### 15.1 Purpose

`quantity_rows` carry section-local quantity fragments and summaries.

### 15.2 Recommended quantity row fields

- `quantity_row_id`
- `kind`
- `component_id`
- `value`
- `unit`
- `notes`

### 15.3 Recommended quantity kinds

- `pavement_area`
- `pavement_thickness`
- `cut_area`
- `fill_area`
- `component_area`

Current implementation note:

- `SectionOutputMapper` can promote `AppliedSection.point_rows` into a `design_section` geometry row
- `SectionOutputMapper` can expose `AppliedSection.frame` through summary rows for frame `x/y/z`, tangent direction, profile grade, and alignment/profile status
- TIN section sampling can attach an `existing_ground_tin` geometry row
- `SectionEarthworkAreaService` compares `design_section` and `existing_ground_tin` polylines by offset
- computed section earthwork rows use `cut_area` and `fill_area` quantities in `m2`
- `QuantityBuildService` can convert consecutive station `cut_area` and `fill_area` rows into `cut` and `fill` volumes using the average-end-area method
- the resulting volume fragments use `m3` and are consumable by `EarthworkBalanceService` and mass-haul review

## 16. Review Rows

### 16.1 Purpose

`review_rows` support review workflow without polluting engineering source objects.

### 16.2 Recommended review row fields

- `review_row_id`
- `kind`
- `label`
- `message`
- `priority`
- `related_component_id`

### 16.3 Recommended kinds

- `bookmark`
- `review_note`
- `issue_flag`
- `candidate_comparison_hint`

## 17. Summary Rows

### 17.1 Purpose

`summary_rows` provide compact, display-friendly rollups for viewers and sheets.

### 17.2 Recommended summary row fields

- `summary_id`
- `kind`
- `label`
- `value`
- `priority`

### 17.3 Recommended summary kinds

- `station_summary`
- `template_summary`
- `region_summary`
- `frame_x`
- `frame_y`
- `frame_z`
- `frame_tangent_direction`
- `profile_grade`
- `frame_status`
- `terrain_summary`
- `structure_summary`
- `quantity_summary`

## 18. SectionSheetOutput Structure

Recommended root fields:

- `schema_version`
- `section_sheet_output_id`
- `project_id`
- `alignment_id`
- `sheet_mode`
- `station_selection_mode`
- `section_outputs`
- `sheet_summary_rows`
- `sheet_layout_hints`

## 19. SectionSheetOutput Station Selection Modes

Recommended values:

- `regular_interval`
- `key_stations_only`
- `region_boundaries_only`
- `event_stations_only`
- `custom_station_list`

## 20. Sheet Layout Hints

### 20.1 Purpose

`sheet_layout_hints` allow layout engines to behave consistently without owning engineering meaning.

### 20.2 Recommended layout hint fields

- `preferred_scale`
- `panel_order`
- `grouping_mode`
- `show_dimensions`
- `show_labels`
- `show_diagnostics`
- `summary_block_mode`

## 21. Source Mapping Rule

Every section output should retain strong mapping back to:

- `AppliedSection`
- component semantics
- source ownership rows

This is required for:

- viewer source inspector
- editor handoff
- output traceability
- debug and regression testing

## 22. Viewer Contract Minimum

The Cross Section Viewer should be able to operate using, at minimum:

- station metadata
- geometry rows
- component rows
- ownership rows
- diagnostic rows
- dimension rows
- summary rows

If those rows are incomplete, the viewer should degrade gracefully rather than inventing hidden logic.

## 23. DXF / SVG Contract Minimum

Drawing-oriented exports should be able to operate using:

- geometry rows
- dimension rows
- component rows
- summary rows
- layout hints

Exports should not need to reinterpret internal template data directly.

## 24. Earthwork and Quantity Contract Minimum

Earthwork and quantity consumers should be able to reuse:

- quantity rows
- terrain rows
- component rows
- station metadata

This reduces duplication of section meaning across systems.

## 25. Validation Rules

The output schema should be validated for:

- missing required root metadata
- duplicate component identities
- broken geometry references
- ownership rows that reference unknown targets
- invalid unit metadata
- inconsistent station metadata

## 26. Anti-Patterns to Avoid

Avoid the following:

- viewer-only fields being treated as engineering truth
- exporter-specific hidden fields that other consumers cannot see
- unlabeled geometry without semantic rows
- ownership inference that exists only in UI code
- re-deriving section meaning separately in each consumer

## 27. Recommended Follow-Up Documents

This schema document should be followed by:

1. `V1_PLAN_PROFILE_SHEET_PLAN.md`
2. `V1_EXCHANGE_PLAN.md`
3. `V1_3D_REVIEW_DISPLAY_PLAN.md`

## 28. Final Rule

If a section consumer cannot do its job using the normalized section-output payload, the answer should be to improve the schema, not to let every consumer invent its own hidden section logic.

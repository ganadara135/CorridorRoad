# CorridorRoad V1 Exchange Output Schema

Date: 2026-04-22
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_EXCHANGE_PLAN.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`
- `docsV1/V1_SECTION_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines the normalized exchange-output contract for v1.

It exists to ensure that external export paths use:

- a common package structure
- explicit unit and coordinate metadata
- explicit source and result references
- format-specific payloads wrapped in a stable internal contract

## 2. Scope

This schema covers:

- `ExchangeOutputSchema`
- format packaging rules for `LandXML`, `DXF`, and `IFC`
- common root metadata
- source/result reference rules
- diagnostic and degraded-export reporting

This schema does not define:

- full external format specifications
- import normalization rules in detail
- renderer-specific drawing aesthetics

## 3. Core Rule

An external export should be represented internally as a normalized package before or alongside final file serialization.

This means:

- exporters should not write directly from scattered runtime state
- all important exports should be traceable back to internal source/result/output contracts

## 4. Schema Versioning

Recommended initial version:

- `ExchangeOutputSchemaVersion = 1`

Every exchange package should expose its schema version explicitly.

## 5. ExchangeOutput Root Structure

Recommended top-level fields:

- `schema_version`
- `exchange_output_id`
- `format`
- `package_kind`
- `project_id`
- `source_refs`
- `result_refs`
- `output_refs`
- `unit_context`
- `coordinate_context`
- `selection_scope`
- `payload_metadata`
- `format_payload`
- `diagnostic_rows`

## 6. Required Root Metadata

### 6.1 Identity fields

Required fields should include:

- `exchange_output_id`
- `project_id`
- `format`

### 6.2 Format field

Recommended values:

- `landxml`
- `dxf`
- `ifc`

### 6.3 Package kind field

Recommended values:

- `source_exchange`
- `result_exchange`
- `drawing_exchange`
- `reference_exchange`
- `mixed_exchange`

## 7. Source References

### 7.1 Purpose

`source_refs` identify which internal source objects contributed to the export.

### 7.2 Recommended source reference fields

- `ref_id`
- `source_kind`
- `source_id`
- `label`
- `notes`

### 7.3 Recommended source kinds

- `alignment`
- `profile`
- `template`
- `region`
- `structure`
- `survey_source`

## 8. Result References

### 8.1 Purpose

`result_refs` identify which derived result objects contributed to the export.

### 8.2 Recommended result reference fields

- `ref_id`
- `result_kind`
- `result_id`
- `label`
- `notes`

### 8.3 Recommended result kinds

- `applied_section`
- `applied_section_set`
- `surface`
- `quantity_result`
- `earthwork_result`

## 9. Output References

### 9.1 Purpose

`output_refs` identify which normalized output contracts were consumed by the exporter.

### 9.2 Recommended output reference fields

- `ref_id`
- `output_kind`
- `output_id`
- `schema_version`
- `notes`

### 9.3 Recommended output kinds

- `plan_output`
- `profile_output`
- `section_output`
- `section_sheet_output`
- `surface_output`
- `quantity_output`

## 10. Unit Context

### 10.1 Purpose

`unit_context` ensures the package records how numeric values were interpreted.

### 10.2 Recommended fields

- `linear_unit`
- `area_unit`
- `volume_unit`
- `slope_unit`

### 10.3 Rule

Exports must not rely on silent unit assumptions.

## 11. Coordinate Context

### 11.1 Purpose

`coordinate_context` records spatial interpretation.

### 11.2 Recommended fields

- `coordinate_mode`
- `crs_code`
- `origin_mode`
- `north_rotation`
- `notes`

### 11.3 Rule

Major coordinate interpretation must be explicit.

## 12. Selection Scope

### 12.1 Purpose

`selection_scope` records what portion of the project was exported.

### 12.2 Recommended fields

- `scope_kind`
- `alignment_id`
- `station_start`
- `station_end`
- `station_selection_mode`
- `notes`

### 12.3 Recommended scope kinds

- `whole_project`
- `single_alignment`
- `station_range`
- `section_selection`
- `sheet_selection`

## 13. Payload Metadata

### 13.1 Purpose

`payload_metadata` carries package-level details that help diagnostics and reproducibility.

### 13.2 Recommended fields

- `entity_count`
- `omitted_entity_count`
- `export_mode`
- `generator_name`
- `generated_at`
- `degraded_export`
- `degraded_reason_rows`
- `source_context_count`
- `side_slope_source_context_count`
- `bench_source_context_count`

## 14. Format Payload Rule

`format_payload` is the format-specific content area.

The root schema should remain stable even when format payloads differ.

Architectural rule:

- common metadata stays in the root package
- format-specific shape stays inside `format_payload`

## 15. LandXML Payload Structure

### 15.1 Purpose

The `landxml` payload should represent civil-source and surface-oriented exchange.

### 15.2 Recommended payload families

- `alignment_rows`
- `profile_rows`
- `surface_rows`
- `feature_rows` where supported

### 15.3 Recommended alignment payload fields

- `alignment_id`
- `name`
- `geometry_rows`
- `station_rows`

### 15.4 Recommended profile payload fields

- `profile_id`
- `name`
- `pvi_rows`
- `curve_rows`

### 15.5 Recommended surface payload fields

- `surface_id`
- `surface_kind`
- `vertex_rows`
- `face_rows`
- `boundary_rows`
- `metadata_rows`

## 16. DXF Payload Structure

### 16.1 Purpose

The `dxf` payload should represent drawing-oriented exchange.

### 16.2 Recommended payload families

- `layer_rows`
- `entity_rows`
- `block_rows` where needed
- `sheet_rows` where needed

### 16.3 Recommended entity roles

- `plan_entity`
- `profile_entity`
- `section_entity`
- `dimension_entity`
- `annotation_entity`
- `reference_entity`

### 16.4 Source rule

DXF payloads should derive from normalized plan/profile/section outputs, not from live viewer scenes.

## 17. IFC Payload Structure

### 17.1 Purpose

The `ifc` payload should represent reference or modeled building/infrastructure exchange.

### 17.2 Recommended payload families

- `object_rows`
- `placement_rows`
- `property_rows`
- `relationship_rows`

### 17.3 Recommended object roles

- `reference_structure`
- `corridor_object`
- `surface_reference`
- `structural_object`

### 17.4 Scope rule

Early IFC payloads should remain practical and bounded rather than pretending to support every possible corridor semantic immediately.

## 18. Diagnostic Rows

### 18.1 Purpose

`diagnostic_rows` record issues and degradations associated with the exchange package.

### 18.2 Recommended fields

- `diagnostic_id`
- `severity`
- `kind`
- `message`
- `related_ref_id`
- `action_hint`

### 18.3 Recommended severity values

- `info`
- `warning`
- `error`

### 18.4 Recommended diagnostic kinds

- `unsupported_entity`
- `unit_ambiguity`
- `coordinate_ambiguity`
- `degraded_export`
- `omitted_reference`
- `format_limit_reached`

## 19. Degraded Export Rule

Not every export will be perfect in early v1.

If an export is partial or simplified, the package should say so explicitly via:

- `degraded_export = true`
- diagnostic rows
- degraded-reason metadata

This is better than silently pretending the export is complete.

## 20. Traceability Rule

An exchange package should make it possible to trace:

- which project it came from
- which internal source/result/output contracts were used
- which station or alignment scope was exported
- which parts were omitted or simplified

Current implementation note:

- `format_payload.source_context_rows` carries normalized source context rows for structure solids, section side-slope components, and quantity fragments.
- Side-slope benches use `context_kind = "section_side_slope_component"` for section component rows and `context_kind = "side_slope_quantity_fragment"` for bench/slope-face quantity rows.
- Bench source context rows must include `assembly_ref`, `region_ref`, and `component_ref` when those source refs are available.
- Package export paths should persist these rows unchanged so command-created JSON packages and downstream handoff flows can be audited against the same source context.

## 21. Validation Rules

The exchange schema should be validated for:

- missing required root metadata
- invalid format name
- empty format payload with no diagnostics
- unknown reference kinds
- inconsistent scope metadata
- unit or coordinate omissions

## 22. Consumer Rule

Export writers and export previews should consume the normalized exchange package rather than separately reconstructing export state.

This keeps:

- testing simpler
- diagnostics clearer
- format adapters more consistent

## 23. Anti-Patterns to Avoid

Avoid the following:

- one exporter writing directly from random document objects
- format-specific package roots with no shared metadata
- silent degraded export behavior
- no traceability between exported file and internal project scope
- embedding viewer-only display state into exchange payloads as engineering truth

## 24. Recommended Follow-Up Documents

This schema document should be followed by:

1. `V1_LANDXML_MAPPING_PLAN.md`
2. `V1_DXF_MAPPING_PLAN.md`
3. `V1_IFC_MAPPING_PLAN.md`

## 25. Final Rule

In v1, exchange output should be a traceable, versioned package that cleanly wraps format-specific content.

If an exporter cannot describe its result through the normalized exchange schema, it is not yet a stable v1 exchange path.

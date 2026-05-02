# CorridorRoad V1 TIN Sampling Contract

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_TIN_ENGINE_PLAN.md`
- `docsV1/V1_TIN_DATA_SCHEMA.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`

## 1. Purpose

This document defines the normalized contract for querying TIN surfaces in v1.

It exists so that profile generation, section evaluation, daylight resolution, earthwork analysis, and review systems can all rely on a common terrain-query interface.

## 2. Core Rule

TIN sampling in v1 must be:

- triangle-based
- reusable
- explicit about coordinate context
- explicit about confidence and failure state

Sampling consumers must not invent their own hidden terrain-query behavior when a shared sampling contract exists.

## 3. Scope

This contract covers:

- XY elevation queries
- line and station-range sampling
- station/offset sampling through alignment context
- daylight-oriented sampling
- surface-to-surface delta sampling

This contract does not define:

- triangulation algorithms
- UI workflows
- section rendering

## 4. Shared Query Context

Every sampling request should have access to:

- `surface_id`
- `coordinate_context`
- `unit_context`
- optional `alignment_id`
- optional `station context`
- optional clipping/range context

## 5. Common Response Rule

Every sampling response should carry:

- `status`
- `confidence`
- `value rows`
- `diagnostic rows`

Recommended status values:

- `ok`
- `warning`
- `fallback`
- `no_hit`
- `error`

## 6. XY Elevation Query

### 6.1 Purpose

Query terrain elevation at an XY location.

### 6.2 Request fields

- `query_id`
- `surface_id`
- `x`
- `y`
- `coordinate_mode`

### 6.3 Response fields

- `query_id`
- `status`
- `z`
- `face_id`
- `confidence`
- `diagnostic_rows`

### 6.4 Main consumers

- profile generation
- section evaluation
- review pick helpers

## 7. Station/Offset Query

### 7.1 Purpose

Query terrain elevation using alignment station and offset.

### 7.2 Request fields

- `query_id`
- `surface_id`
- `alignment_id`
- `station`
- `offset`
- `coordinate_mode`

### 7.3 Response fields

- `query_id`
- `status`
- `x`
- `y`
- `z`
- `face_id`
- `confidence`
- `diagnostic_rows`

### 7.4 Main consumers

- applied-section terrain intersection
- daylight search
- earthwork review

## 8. Line Sampling Query

### 8.1 Purpose

Sample a surface along a line or polyline path.

### 8.2 Request fields

- `query_id`
- `surface_id`
- `line_vertices`
- `step`
- `coordinate_mode`

### 8.3 Response fields

- `query_id`
- `status`
- `sample_rows`
- `diagnostic_rows`

### 8.4 Sample row fields

- `sample_id`
- `x`
- `y`
- `z`
- `face_id`
- `confidence`

### 8.5 Main consumers

- profile extraction
- inspection tools
- debug and validation utilities

## 9. Station Range Sampling Query

### 9.1 Purpose

Sample a surface over a station range using alignment context.

### 9.2 Request fields

- `query_id`
- `surface_id`
- `alignment_id`
- `station_start`
- `station_end`
- `station_step`
- `offsets`

### 9.3 Response fields

- `query_id`
- `status`
- `sample_rows`
- `diagnostic_rows`

### 9.4 Main consumers

- profile generation
- earthwork balance preprocessing
- review summaries

## 10. Daylight Search Query

### 10.1 Purpose

Resolve terrain hit conditions for daylight behavior from a section edge.

### 10.2 Request fields

- `query_id`
- `surface_id`
- `edge_x`
- `edge_y`
- `edge_z`
- `search_direction`
- `search_step`
- `max_distance`
- `slope_hint`
- `coordinate_mode`

### 10.3 Response fields

- `query_id`
- `status`
- `hit_found`
- `hit_x`
- `hit_y`
- `hit_z`
- `hit_distance`
- `face_id`
- `confidence`
- `diagnostic_rows`

### 10.4 Main consumers

- side-slope daylight resolution
- section diagnostics
- terrain interaction review

## 11. Surface-to-Surface Delta Query

### 11.1 Purpose

Compare two surfaces at shared query locations.

### 11.2 Request fields

- `query_id`
- `surface_a_id`
- `surface_b_id`
- `query_mode`
- `query_geometry`
- `coordinate_mode`

### 11.3 Response fields

- `query_id`
- `status`
- `delta_rows`
- `diagnostic_rows`

### 11.4 Delta row fields

- `delta_id`
- `x`
- `y`
- `z_a`
- `z_b`
- `delta`
- `confidence`

### 11.5 Main consumers

- earthwork balance
- surface comparison tools
- cut/fill analysis

## 12. Confidence Model

### 12.1 Why confidence matters

TIN sampling can fail or become weak due to sparse coverage, boundary issues, or no triangle hits.

### 12.2 Recommended confidence values

- `high`
- `medium`
- `low`
- `unknown`

### 12.3 Rule

Consumers should not treat every returned value as equally reliable.

## 13. Diagnostic Rows

Recommended fields:

- `diagnostic_id`
- `severity`
- `kind`
- `message`
- `related_face_id`
- `action_hint`

Recommended kinds:

- `no_triangle_hit`
- `outside_boundary`
- `void_area_hit`
- `sparse_coverage`
- `coordinate_mismatch`
- `surface_missing`

## 14. Coordinate Rule

Sampling requests and responses must make coordinate interpretation explicit.

Recommended fields:

- `coordinate_mode`
- `alignment_context_used`
- `transform_applied`

Consumers should never guess whether they received local or world coordinates.

## 15. Section Consumer Rule

Applied-section evaluation should use the shared sampling contract for:

- terrain edge resolution
- daylight hit search
- station-specific terrain queries

It should not embed a separate terrain query path.

## 16. Profile Consumer Rule

Profile generation should use the shared sampling contract for:

- station-range sampling
- EG extraction
- terrain debug and validation

## 17. Earthwork Consumer Rule

Earthwork systems should use the shared sampling contract or shared surface-comparison service built on top of it.

This prevents profile, section, and earthwork workflows from diverging in terrain interpretation.

## 18. Performance Rule

Sampling should support:

- batched queries
- range-limited queries
- cached spatial lookup structures
- explicit step control

Consumers should avoid many tiny repeated queries when a bounded batch query is available.

## 19. Validation Rules

Sampling requests should be validated for:

- missing surface ids
- invalid coordinate mode
- invalid station ranges
- negative step or max distance values
- missing alignment context when required

Responses should be validated for:

- missing status
- impossible hit geometry
- face references that do not exist
- inconsistent confidence signaling

## 20. Anti-Patterns to Avoid

Avoid the following:

- each subsystem inventing its own surface query shape
- treating `no_hit` as if it were the same as `z=0`
- silently swapping local and world coordinates
- returning a value without confidence or diagnostics

## 21. Recommended Follow-Up Documents

This contract should be followed by:

1. `V1_SURFACE_OUTPUT_SCHEMA.md`
2. `V1_LANDXML_MAPPING_PLAN.md`
3. `V1_PLAN_OUTPUT_SCHEMA.md`

## 22. Final Rule

In v1, TIN sampling should be a shared, explicit, confidence-aware query contract that all terrain consumers can trust and reuse.

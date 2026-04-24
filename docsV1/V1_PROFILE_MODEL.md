# CorridorRoad V1 Profile Model

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_OUTPUT_SCHEMA.md`
- `docsV1/V1_LANDXML_MAPPING_PLAN.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`

## 1. Purpose

This document defines the v1 internal source contract for vertical profile design.

It exists to make clear:

- what `ProfileModel` owns
- how profile source data relates to alignment station space
- how PVI, grade, and vertical curve intent should be preserved
- how profile data connects to sections, corridor evaluation, outputs, exchange, and earthwork review

## 2. Scope

This model covers:

- profile identity and source ownership
- station-elevation control data
- PVI and grade-transition intent
- vertical curve intent
- deterministic profile evaluation services
- validation and diagnostic rules

This model does not cover:

- horizontal alignment authoring
- superelevation authoring
- section template authoring
- final sheet layout behavior

## 3. Core Rule

`ProfileModel` is a durable vertical source-of-truth model.

This means:

- corridor evaluation reads from it
- `ProfileOutput` derives from it
- earthwork and mass-haul review may attach to it
- viewers may inspect it
- no derived output becomes the new profile truth

## 4. Relationship to Alignment

`ProfileModel` is defined in the station space established by `AlignmentModel`.

The relationship is:

- `AlignmentModel` owns horizontal station semantics
- `ProfileModel` owns vertical design intent along that station domain

`ProfileModel` must reference `alignment_id` explicitly.

It must not duplicate horizontal geometry internally.

## 5. Design Goals

The v1 profile subsystem should:

- preserve true vertical design intent
- support station-aware evaluation
- support PVI-driven authoring
- preserve vertical curve meaning where supported
- support imported and native profiles
- expose deterministic services for corridor, sheet, and earthwork consumers

## 6. Profile Scope in v1

Recommended early v1 support:

- existing ground reference profiles
- finished grade profiles
- design reference profiles
- PVI-based authoring
- tangent grades
- vertical curves
- station range queries

Deferred or later refinements may include:

- richer profile set management
- more specialized jurisdiction-specific labels
- advanced multi-profile dependency automation

## 7. Profile Object Families

Recommended primary object families:

- `ProfileModel`
- `ProfileControlSequence`
- `ProfileControlPoint`
- `VerticalCurveRow`
- `ProfileConstraintSet`
- `ProfileEvaluationResult`

## 8. ProfileModel Root

### 8.1 Purpose

`ProfileModel` is the durable container for one vertical design profile.

### 8.2 Recommended root fields

- `schema_version`
- `profile_id`
- `project_id`
- `alignment_id`
- `label`
- `profile_kind`
- `control_sequence`
- `vertical_curve_rows`
- `constraint_rows`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

### 8.3 Recommended profile kinds

- `existing_ground`
- `finished_grade`
- `design_reference`
- `temporary_candidate_profile`

## 9. ProfileControlSequence

### 9.1 Purpose

`ProfileControlSequence` preserves the ordered station-based control structure of the profile.

### 9.2 Rule

The control sequence must preserve engineering meaning, not just a sampled polyline.

### 9.3 Recommended fields

- `control_sequence_id`
- `profile_id`
- `control_rows`
- `start_station`
- `end_station`
- `notes`

## 10. ProfileControlPoint

### 10.1 Purpose

Each control point represents a meaningful vertical control location in the profile.

### 10.2 Recommended fields

- `control_point_id`
- `control_index`
- `station`
- `elevation`
- `kind`
- `grade_in`
- `grade_out`
- `source_ref`
- `notes`

### 10.3 Recommended kinds

- `pvi`
- `grade_break`
- `reference_point`
- `imported_control_with_diagnostics`

### 10.4 Rule

Control points should preserve authoring intent even when rendered consumers only show simplified profile lines.

## 11. VerticalCurveRow

### 11.1 Purpose

`VerticalCurveRow` preserves transition intent between grades.

### 11.2 Recommended fields

- `vertical_curve_id`
- `kind`
- `station_start`
- `station_end`
- `pvi_ref`
- `curve_length`
- `curve_parameter`
- `source_ref`
- `notes`

### 11.3 Recommended kinds

- `crest_curve`
- `sag_curve`
- `generic_vertical_curve`
- `imported_unknown_vertical_curve`

### 11.4 Rule

Vertical curves should remain identifiable as parametric design elements rather than being flattened into sampled points only.

## 12. ProfileConstraintSet

### 12.1 Purpose

Constraint rows capture vertical-design intent and review context.

### 12.2 Recommended fields

- `constraint_id`
- `kind`
- `value`
- `unit`
- `hard_or_soft`
- `notes`

### 12.3 Recommended kinds

- `max_grade`
- `min_grade`
- `min_vertical_curve_length`
- `protected_station_range`
- `fixed_elevation_control`

## 13. Existing Ground vs Design Profiles

### 13.1 Rule

Existing ground and design profile families should stay explicitly distinguishable.

### 13.2 Why it matters

This distinction is required for:

- corridor evaluation
- profile review
- earthwork balance analysis
- exchange behavior

### 13.3 Recommended policy

`existing_ground` profiles may come from TIN sampling or import normalization.

`finished_grade` and `design_reference` profiles should remain durable design sources.

## 14. Evaluation Services

Recommended service families:

- `ProfileEvaluationService`
- `ProfileSamplingService`
- `ProfileComparisonService`

## 15. ProfileEvaluationService

### 15.1 Purpose

This service evaluates station-based vertical geometry in deterministic form.

### 15.2 Typical queries

- station to elevation
- station to grade
- station to active control element
- station range to sampled profile line

### 15.3 Rule

Corridor, section, output, and earthwork consumers should use shared evaluation services rather than interpreting profile geometry independently.

## 16. ProfileSamplingService

### 16.1 Purpose

This service produces sampled line data for review and output without replacing the profile source contract.

### 16.2 Typical consumers

- `ProfileOutput`
- 3D profile overlay
- profile preview tools
- export packaging helpers

### 16.3 Rule

Sampled rows are derived output, not authoring truth.

## 17. ProfileComparisonService

### 17.1 Purpose

This service compares multiple profile families in aligned station space.

### 17.2 Typical comparisons

- EG vs FG
- baseline vs candidate profile
- design profile vs constrained alternative

### 17.3 Rule

Comparison results should be explicit result objects or output rows, not hidden renderer-side calculations.

## 18. Validation Rules

Validation should check for:

- broken control ordering
- duplicate or ambiguous stations
- invalid vertical curve ranges
- missing alignment reference
- inconsistent unit or vertical reference
- unsupported imported curve definitions

Validation results should be recorded in `diagnostic_rows`.

## 19. Diagnostics

Diagnostics should be produced when:

- imported profile geometry does not map cleanly
- a vertical curve must be simplified
- control points are incomplete or conflicting
- a station query lands outside a valid profile domain
- profile comparison requires degraded handling

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `source_ref`
- `message`
- `notes`

## 20. Identity and Provenance

Profile objects should preserve:

- stable `profile_id`
- referenced `alignment_id`
- external import identity where relevant
- source file reference
- import or edit provenance
- candidate-vs-approved status where applicable

This is important for:

- `LandXML` exchange
- AI alternative comparison
- earthwork scenario analysis
- profile output traceability

## 21. Relationship to Section and Corridor

`AppliedSection` evaluation depends on `ProfileModel` for:

- design elevation at station
- grade-derived context
- vertical position of section origin

`CorridorModel` must consume evaluated profile data rather than copying or re-deriving profile logic.

## 22. Relationship to Earthwork Balance

`ProfileModel` is a major driver of earthwork behavior.

Earthwork and mass-haul systems may:

- evaluate cut/fill consequences of profile changes
- compare baseline and candidate profiles
- attach derived balance rows to `ProfileOutput`

But they must not overwrite `ProfileModel` directly without explicit accepted source edits.

## 23. Relationship to Outputs

### 23.1 ProfileOutput

`ProfileOutput` should derive from `ProfileModel` plus related comparison and diagnostic context.

It must not become the new authoring source.

### 23.2 SectionOutput

`SectionOutput` depends on the evaluated elevation and station context provided through `ProfileModel`.

### 23.3 Plan/Profile Sheets

Sheet systems may consume sampled and annotated profile output rows, but should not own vertical design truth.

## 24. Relationship to LandXML

`LandXML` profile import should normalize into `ProfileModel`.

`LandXML` profile export should primarily read from:

- `ProfileModel`
- related metadata in `ExchangeOutputSchema`

`ProfileOutput` may support export packaging context, but not replace the source contract.

## 25. AI and Alternative Design

AI-assisted workflows may propose:

- PVI elevation changes
- vertical curve length changes
- profile smoothing candidates
- earthwork-aware alternative profiles

But accepted changes must still be written into normalized profile source objects.

The AI layer must not maintain a separate hidden profile representation.

## 26. Recommended Minimal Schema Version

Recommended initial version:

- `ProfileModelSchemaVersion = 1`

## 27. Anti-Patterns

The following should be avoided:

- storing only sampled FG lines as the profile truth
- letting profile display geometry become the editable source
- duplicating profile evaluation logic across corridor and output code
- hiding vertical-curve degradation
- embedding earthwork analysis results directly into the profile source contract

## 28. Summary

In v1, `ProfileModel` is the durable vertical source contract for:

- station-elevation control
- grade and vertical-curve intent
- profile constraints
- deterministic evaluation

It should remain alignment-referenced and parametric, so that:

- corridor and section evaluation can trust it
- `ProfileOutput` and sheets can derive from it
- `LandXML` exchange can normalize through it
- earthwork balance and AI alternatives can compare against it without replacing it

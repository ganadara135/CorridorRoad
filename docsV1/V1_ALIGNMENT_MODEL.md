# CorridorRoad V1 Alignment Model

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_LANDXML_MAPPING_PLAN.md`
- `docsV1/V1_PLAN_OUTPUT_SCHEMA.md`
- `docsV1/V1_SECTION_MODEL.md`

## 1. Purpose

This document defines the v1 internal source contract for horizontal alignment.

It exists to make clear:

- what `AlignmentModel` owns
- which object families belong inside the alignment subsystem
- how station evaluation should work
- how alignment interacts with profiles, sections, outputs, and exchange

## 2. Scope

This model covers:

- horizontal geometry definition
- station reference behavior
- station equations
- geometric evaluation services
- diagnostic and validation rules
- alignment identity and provenance

This model does not cover:

- vertical profile authoring
- superelevation logic
- section template authoring
- final plan sheet layout behavior

## 3. Core Rule

`AlignmentModel` is a durable source-of-truth model.

This means:

- corridor evaluation reads from it
- plan and exchange outputs derive from it
- viewers may inspect it
- no downstream output contract becomes the new alignment truth

## 4. Design Goals

The v1 alignment subsystem should:

- represent civil road alignment intentionally
- support tangent, curve, and transition geometry
- support `station` as a first-class evaluation domain
- preserve traceability to external imports such as `LandXML`
- expose deterministic evaluation services for corridor and output consumers

## 5. Alignment Scope in v1

Recommended early v1 support:

- tangent segments
- circular curves
- transition curves including `clothoid` / Euler spiral intent
- station equations
- station range queries
- plan-geometry extraction for review and output

Deferred or later refinements may include:

- richer compound alignment authoring UX
- specialized jurisdiction-specific annotations
- advanced multi-alignment corridor relationships

## 6. Alignment Object Families

Recommended primary object families:

- `AlignmentModel`
- `AlignmentGeometrySequence`
- `AlignmentElement`
- `StationEquationSet`
- `AlignmentConstraintSet`
- `AlignmentEvaluationResult`

## 7. AlignmentModel Root

### 7.1 Purpose

`AlignmentModel` is the durable container for one horizontal design alignment.

### 7.2 Recommended root fields

- `schema_version`
- `alignment_id`
- `project_id`
- `label`
- `alignment_kind`
- `geometry_sequence`
- `station_equations`
- `constraint_rows`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

### 7.3 Recommended alignment kinds

- `road_centerline`
- `offset_alignment`
- `reference_alignment`
- `temporary_candidate_alignment`

## 8. AlignmentGeometrySequence

### 8.1 Purpose

`AlignmentGeometrySequence` preserves the ordered horizontal geometry definition.

### 8.2 Rule

The sequence must preserve engineering order, not just a display polyline.

### 8.3 Recommended fields

- `geometry_sequence_id`
- `alignment_id`
- `element_rows`
- `start_station`
- `end_station`
- `notes`

## 9. AlignmentElement

### 9.1 Purpose

Each `AlignmentElement` represents one meaningful geometric element in the horizontal sequence.

### 9.2 Recommended element fields

- `element_id`
- `element_index`
- `kind`
- `station_start`
- `station_end`
- `length`
- `geometry_payload`
- `incoming_tangent_ref`
- `outgoing_tangent_ref`
- `source_ref`
- `notes`

### 9.3 Recommended element kinds

- `tangent`
- `circular_curve`
- `transition_curve`
- `imported_unknown_curve`

### 9.4 Geometry payload rule

`geometry_payload` should preserve parametric meaning rather than collapsing immediately to sampled points.

Examples of payload meaning:

- tangent start and end definition
- circular radius and rotation direction
- transition length and curvature progression intent

## 10. Transition Curve Policy

### 10.1 Purpose

Transition curves are important in v1 because road design should not treat every non-tangent geometry as a simple circular arc.

### 10.2 Recommended policy

Transition geometry should preserve:

- curve family intent
- start and end station
- transition length
- curvature progression direction

### 10.3 Recommended early family support

- `clothoid`
- `unknown_transition_with_diagnostics`

### 10.4 Rule

If imported transition geometry cannot be represented exactly, the model should preserve the best supported form and emit diagnostics.

## 11. StationEquationSet

### 11.1 Purpose

`StationEquationSet` preserves station discontinuity or remapping rules.

### 11.2 Recommended fields

- `station_equation_set_id`
- `alignment_id`
- `equation_rows`
- `notes`

### 11.3 Recommended equation row fields

- `equation_id`
- `station_back`
- `station_ahead`
- `equation_kind`
- `notes`

### 11.4 Recommended kinds

- `station_ahead`
- `station_back`
- `station_reset`

### 11.5 Rule

Evaluation services must use station equations explicitly rather than assuming monotonic simple chainage only.

## 12. AlignmentConstraintSet

### 12.1 Purpose

Constraint rows capture design intent and validation context without turning the model into a UI-only preference store.

### 12.2 Recommended fields

- `constraint_id`
- `kind`
- `value`
- `unit`
- `hard_or_soft`
- `notes`

### 12.3 Recommended kinds

- `design_speed`
- `min_radius`
- `max_deflection`
- `transition_required`
- `protected_station_range`

## 13. Evaluation Services

Recommended service families:

- `AlignmentEvaluationService`
- `StationResolutionService`
- `PlanGeometryExtractionService`

## 14. AlignmentEvaluationService

### 14.1 Purpose

This service evaluates station-based horizontal geometry in deterministic form.

### 14.2 Typical queries

- station to XY position
- station to tangent direction
- station to local frame
- station range to sampled geometry
- station to active element

### 14.3 Rule

Corridor, section, superelevation, and plan output consumers should use this service rather than implementing their own geometry interpretation.

## 15. StationResolutionService

### 15.1 Purpose

This service resolves station semantics consistently across the model.

### 15.2 Typical responsibilities

- normalize station input
- apply station equations
- validate station range membership
- report ambiguous station references

### 15.3 Rule

No major consumer should silently interpret station values outside the shared station-resolution policy.

## 16. PlanGeometryExtractionService

### 16.1 Purpose

This service produces plan-ready geometry rows from alignment source data without replacing the source contract.

### 16.2 Typical consumers

- `PlanOutput`
- 3D plan overlay
- diagnostic preview tools
- export packaging helpers

### 16.3 Rule

Extracted geometry is derived output. It must not be written back as new alignment truth.

## 17. Validation Rules

Validation should check for:

- broken element ordering
- zero-length or invalid segments
- unsupported transition encoding
- inconsistent station ranges
- ambiguous station equation behavior
- coordinate or unit ambiguity

Validation results should be recorded in `diagnostic_rows`.

## 18. Diagnostics

Diagnostics should be produced when:

- imported geometry does not map cleanly
- a transition curve is simplified
- station equations are incomplete or conflicting
- an evaluation query lands in an invalid gap
- plan extraction requires degraded sampling

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `source_ref`
- `message`
- `notes`

## 19. Identity and Provenance

Alignment objects should preserve:

- stable `alignment_id`
- imported external identity where relevant
- source file reference
- import or edit provenance
- candidate-vs-approved status where applicable

This is especially important for:

- `LandXML` exchange
- AI candidate comparison
- plan/profile linkage

## 20. Relationship to ProfileModel

`AlignmentModel` and `ProfileModel` are separate source systems.

The relationship is:

- alignment defines horizontal station space
- profile defines vertical behavior along that station space

`ProfileModel` must reference alignment identity explicitly rather than copying alignment geometry internally.

## 21. Relationship to Section and Corridor

`AppliedSection` evaluation depends on alignment for:

- station position
- local frame
- left/right orientation
- plan path continuity

`CorridorModel` must consume evaluated alignment frames rather than re-deriving them independently.

## 22. Relationship to Outputs

### 22.1 PlanOutput

`PlanOutput` may consume sampled or extracted geometry from alignment services.

It must not become the new authoring source.

### 22.2 ProfileOutput

`ProfileOutput` depends on the station domain defined by `AlignmentModel`.

### 22.3 SectionOutput

`SectionOutput` depends on the alignment-local frame and station identity resolved from `AlignmentModel`.

## 23. Relationship to LandXML

`LandXML` alignment import should normalize into `AlignmentModel`.

`LandXML` alignment export should primarily read from:

- `AlignmentModel`
- related metadata in `ExchangeOutputSchema`

`PlanOutput` may support packaging context, but not replace the source contract.

## 24. AI and Alternative Design

AI-assisted workflows may propose:

- candidate tangency revisions
- candidate transition lengths
- candidate curve radius changes
- candidate alignment alternatives

But any accepted result must still be written into normalized alignment source objects.

The AI layer must not invent a parallel alignment representation.

## 25. Recommended Minimal Schema Version

Recommended initial version:

- `AlignmentModelSchemaVersion = 1`

## 26. Anti-Patterns

The following should be avoided:

- storing only sampled polylines as the alignment truth
- letting plan display geometry become the editable source
- duplicating station logic across corridor and output code
- hiding transition-curve degradation
- embedding profile or superelevation state directly into the alignment source contract

## 27. Summary

In v1, `AlignmentModel` is the durable horizontal source contract for:

- geometry sequence
- station semantics
- design constraints
- deterministic evaluation

It should remain parametric and station-aware, so that:

- profile logic can reference it cleanly
- section and corridor evaluation can trust it
- `LandXML` exchange can normalize through it
- plan outputs and 3D overlays can derive from it without replacing it

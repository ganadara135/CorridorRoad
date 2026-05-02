# CorridorRoad V1 Drainage Model

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_PROFILE_MODEL.md`
- `docsV1/V1_SURFACE_MODEL.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`

## 1. Purpose

This document defines the v1 internal source contract for corridor drainage intent and review policy.

It exists to make clear:

- what `DrainageModel` owns
- how drainage differs from section template detail alone
- how drainage policy interacts with profile, terrain, section, and structure context
- how drainage review feeds outputs, diagnostics, and AI comparison

## 2. Scope

This model covers:

- drainage identity and source intent
- open and closed drainage element references
- minimum-grade and low-point policy
- collection, conveyance, and discharge references
- diagnostics and review traceability
- corridor interaction references to sections, ramps, and intersections

This model does not cover:

- a full hydraulic solver
- detailed pipe network analysis beyond practical source references
- municipal utility asset management
- direct editing of generated drainage geometry as the main source workflow

## 3. Core Rule

`DrainageModel` is a durable source-of-truth model for drainage intent and review constraints.

This means:

- profile, section, and surface evaluation may read from it
- review workflows may expose its effect through derived outputs
- drainage viability must not remain an implied side effect of grading alone
- generated ditch or gutter geometry does not replace drainage source policy

## 4. Why Drainage Modeling Matters

Corridor design that ignores drainage intent becomes fragile even when the geometry looks acceptable.

Drainage-aware modeling affects:

- ditch, gutter, swale, and channel treatment
- low-point and sag review
- culvert and crossing coordination
- intersection and ramp tie-in behavior
- earthwork comparison
- AI recommendations and risk scoring

`DrainageModel` exists so drainage is visible, traceable, and reviewable early.

## 5. Relationship to Section, Profile, and Structure Models

The architectural distinction is:

- `SectionModel` defines section composition and applied section results
- `ProfileModel` defines vertical intent and grade transitions
- `StructureModel` defines culvert and crossing references
- `DrainageModel` defines drainage intent, constraints, and interaction references

Drainage may influence section and profile decisions, but it should remain an explicit model instead of hidden metadata.

Ditch cross-section shape parameters used by Assembly and Applied Section evaluation are defined in `docsV1/V1_DITCH_SHAPE_CONTRACT.md`.

Drainage intent such as collection, discharge, and low-point policy remains owned by `DrainageModel`.

## 6. Design Goals

The v1 drainage subsystem should:

- make drainage intent explicit
- support both open-channel and practical structure-backed references
- support minimum-grade and low-point diagnostics
- preserve traceability into review and output payloads
- support scenario comparison without pretending to replace hydraulic software
- feed AI and earthwork systems with meaningful drainage constraints

## 7. Drainage Scope in v1

Recommended early v1 support:

- ditch, gutter, swale, and channel policy
- culvert, inlet, manhole, and outfall references where practical
- collection and discharge region references
- low-point and ponding-risk review
- drainage-aware grading diagnostics
- drainage quantity references

Deferred or later refinements may include:

- richer stormwater-network import/export
- advanced hydraulic capacity checks
- automated drainage sizing assistance

## 8. Drainage Object Families

Recommended primary object families:

- `DrainageModel`
- `DrainageElementRow`
- `DrainagePolicySet`
- `DrainageCollectionRegion`
- `DrainageConstraintSet`
- `DrainageReviewResult`

## 9. DrainageModel Root

### 9.1 Purpose

`DrainageModel` is the durable container for one project-level drainage policy set.

### 9.2 Recommended root fields

- `schema_version`
- `drainage_model_id`
- `project_id`
- `label`
- `element_rows`
- `policy_rows`
- `collection_region_rows`
- `constraint_rows`
- `unit_context`
- `source_refs`
- `diagnostic_rows`

### 9.3 Rule

`DrainageModel` should preserve stable identity for drainage intent even when geometry or grading alternatives are compared.

## 10. DrainageElementRow

### 10.1 Purpose

Each `DrainageElementRow` represents one meaningful drainage element or reference.

### 10.2 Recommended fields

- `drainage_element_id`
- `element_index`
- `element_kind`
- `alignment_ref`
- optional `ramp_ref`
- optional `intersection_ref`
- optional `structure_ref`
- `station_start`
- `station_end`
- optional `offset_rule`
- `policy_set_ref`
- `source_ref`
- `notes`

### 10.3 Recommended kinds

- `ditch`
- `gutter`
- `swale`
- `channel`
- `culvert_reference`
- `inlet_reference`
- `manhole_reference`
- `outfall_reference`

### 10.4 Rule

Drainage elements should preserve engineering role and context, not become unlabeled linework.

## 11. DrainagePolicySet

### 11.1 Purpose

`DrainagePolicySet` defines how a drainage element or region should behave.

### 11.2 Recommended fields

- `policy_set_id`
- `flow_intent`
- `min_grade_rule`
- `low_point_rule`
- `collection_rule`
- `discharge_rule`
- `maintenance_access_hint`
- `earthwork_priority`
- `notes`

### 11.3 Recommended flow intents

- `collect_and_convey`
- `edge_runoff_capture`
- `ditch_outfall`
- `cross_drainage_transfer`
- `temporary_construction_drainage`

## 12. DrainageCollectionRegion

### 12.1 Purpose

Collection regions preserve where runoff is expected to gather or discharge.

### 12.2 Recommended fields

- `collection_region_id`
- `region_kind`
- `station_start`
- `station_end`
- optional `alignment_ref`
- optional `ramp_ref`
- optional `intersection_ref`
- `expected_receiver_ref`
- `risk_level`
- `notes`

### 12.3 Recommended kinds

- `sag_region`
- `gutter_collection_region`
- `ditch_collection_region`
- `intersection_capture_region`
- `outfall_region`

## 13. Constraint Policy

### 13.1 Purpose

Drainage constraints make grading and comparison rules explicit.

### 13.2 Recommended constraint fields

- `constraint_id`
- `constraint_kind`
- `target_ref`
- `threshold_value`
- `unit`
- `severity`
- `notes`

### 13.3 Recommended kinds

- `minimum_longitudinal_grade`
- `maximum_ponding_risk`
- `must_connect_to_outfall`
- `culvert_clearance_requirement`
- `intersection_capture_requirement`

## 14. Relationship to Applied Sections

`DrainageModel` may influence:

- daylight edge treatment
- ditch and gutter interpretation
- drainage-sensitive component selection
- low-point warnings attached to section review
- output rows describing collection and discharge context

It should not directly become the editable generated section geometry.

## 15. Relationship to Earthwork and AI

Drainage-aware comparisons should be able to consider:

- whether grading preserves minimum drainage viability
- whether a candidate introduces ponding risk
- whether drainage-related structures become more complex
- whether earthwork improvements create drainage regressions

AI outputs should be required to explain drainage tradeoffs when they matter.

## 16. Review and Viewer Expectations

Drainage-aware review should be able to show:

- active drainage element identity
- low-point and sag warnings
- collection and discharge region context
- related culvert or structure references
- affected ramp or intersection context where relevant

Review UI should consume normalized payloads rather than recompute drainage logic ad hoc.

## 17. Exchange Expectations

Drainage-related exchange should support, where practical:

- feature-line or mapped reference import
- culvert and outfall reference exchange
- degraded diagnostics when exact hydraulic semantics are unavailable
- export rows that preserve drainage identity and corridor context

## 18. Diagnostics

Recommended early diagnostics include:

- unresolved outfall reference
- low-point with no collection policy
- minimum-grade violation
- drainage element overlapping incompatible policy rows
- culvert reference with missing structure context
- imported drainage reference with ambiguous ownership
- ditch component shape parameters that cannot produce a reliable drainage surface

## 19. Non-goals

`DrainageModel` should not become:

- a full storm sewer design suite
- an unbounded notes bucket for every grading issue
- a replacement for dedicated hydraulic software
- a manual patch layer for generated ditch geometry

## 20. Next Documents

This model should be followed by:

1. `docsV1/V1_SECTION_MODEL.md`
2. `docsV1/V1_SURFACE_MODEL.md`
3. `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`
4. `docsV1/V1_AI_ASSIST_PLAN.md`

In v1, drainage should be treated as explicit corridor intent with stable identity, reviewable constraints, and traceable downstream effects on grading, sections, and comparison workflows.

# CorridorRoad V1 Intersection Model

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_RAMP_MODEL.md`

## 1. Purpose

This document defines the v1 internal source contract for at-grade intersection and junction control areas.

It exists to make clear:

- what `IntersectionModel` owns
- how intersection policy differs from ordinary region switching
- how approach legs and control areas interact with corridor evaluation
- how intersection context feeds review, output, and exchange workflows

## 2. Scope

This model covers:

- at-grade junction topology
- approach and leg identity
- control-area and influence-area definitions
- turn-lane and curb-return policy references
- intersection grading context
- diagnostics and traceability

This model does not cover:

- full signal timing and traffic operations
- roundabout-specific advanced operations in initial scope
- final drafting layout rules
- direct editing of generated junction geometry

## 3. Core Rule

`IntersectionModel` is a durable source-of-truth model for junction relationship and policy intent.

This means:

- corridor-network evaluation reads from it
- section and review outputs may expose its effects
- generated geometry must not replace control-area source meaning
- special-case intersection hacks should be rejected where structured rules are possible

## 4. Why Intersection Modeling Matters

Intersections are not just short regions with widened lanes.

They often change:

- lane allocation
- curb-return behavior
- grading logic
- drainage flow concentration
- tie-in relationships between corridor legs
- review and output expectations

`IntersectionModel` exists so these transitions are explicit and inspectable.

## 5. Relationship to Ramp and Region Models

The architectural distinction is:

- `RampModel` covers grade-separated or connector ramp intent
- `IntersectionModel` covers at-grade junction topology and control areas
- `RegionModel` applies station-range policy inside a corridor context

Regions may be influenced by intersections, but `IntersectionModel` owns the cross-leg relationship meaning.

## 6. Design Goals

The v1 intersection subsystem should:

- preserve explicit leg identity
- make control-area policy structured and reviewable
- support turn-lane and curb-return references
- support grading and drainage-sensitive diagnostics
- remain compatible with corridor-network evaluation
- expose deterministic outputs for viewers and exchange

## 7. Intersection Scope in v1

Recommended early v1 support:

- simple at-grade crossings
- T and Y junctions
- multi-leg intersection topology
- turn-lane policy references
- curb-return policy references
- control-area grading context

Deferred or later refinements may include:

- roundabout-specialized models
- signal phasing metadata
- richer urban intersection drafting automation

## 8. Intersection Object Families

Recommended primary object families:

- `IntersectionModel`
- `IntersectionRow`
- `IntersectionLegRow`
- `IntersectionControlArea`
- `TurnLanePolicySet`
- `IntersectionEvaluationResult`

## 9. IntersectionModel Root

### 9.1 Purpose

`IntersectionModel` is the durable container for one project-level set of intersection definitions.

### 9.2 Recommended root fields

- `schema_version`
- `intersection_model_id`
- `project_id`
- `label`
- `intersection_rows`
- `constraint_rows`
- `unit_context`
- `source_refs`
- `diagnostic_rows`

### 9.3 Rule

One `IntersectionModel` may manage many junctions, but each junction must keep stable identity and explicit leg references.

## 10. IntersectionRow

### 10.1 Purpose

Each `IntersectionRow` represents one at-grade junction context.

### 10.2 Recommended fields

- `intersection_id`
- `intersection_index`
- `intersection_kind`
- `leg_rows`
- `control_area_ref`
- optional `grading_policy_ref`
- optional `drainage_ref`
- `design_criteria_ref`
- `source_ref`
- `notes`

### 10.3 Recommended kinds

- `cross_intersection`
- `t_intersection`
- `y_intersection`
- `staggered_intersection`
- `temporary_candidate_intersection`

## 11. IntersectionLegRow

### 11.1 Purpose

Each `IntersectionLegRow` preserves one participating corridor leg.

### 11.2 Recommended fields

- `leg_id`
- `intersection_id`
- `leg_role`
- `alignment_ref`
- optional `profile_ref`
- optional `region_ref`
- `approach_station_start`
- `approach_station_end`
- `priority`
- `notes`

### 11.3 Recommended leg roles

- `primary_through`
- `secondary_through`
- `side_road`
- `turn_channel`
- `service_road_connection`

### 11.4 Rule

Leg rows must preserve the corridor relationship, not just list touching alignments.

## 12. IntersectionControlArea

### 12.1 Purpose

`IntersectionControlArea` defines where intersection policy overrides ordinary corridor behavior.

### 12.2 Recommended fields

- `control_area_id`
- `intersection_id`
- `station_ranges`
- `influence_ranges`
- `turn_lane_policy_ref`
- `curb_return_policy_ref`
- `section_transition_refs`
- `drainage_policy_ref`
- `notes`

### 12.3 Rule

Control areas should be explicit, bounded, and traceable into applied-section results.

## 13. Turn-Lane and Curb-Return Policy

### 13.1 Purpose

Intersection behavior often depends on lane-role and edge-return policy.

### 13.2 Recommended policy fields

- `policy_id`
- `lane_role_rows`
- `storage_length_rule`
- `transition_rule`
- `curb_return_kind`
- `edge_treatment_rule`
- `drainage_edge_rule`
- `notes`

### 13.3 Rule

These policies should preserve engineering intent rather than collapse into display-only geometry.

## 14. Grading and Drainage Context

Intersection models should be able to reference:

- low-point review policy
- minimum grade constraints
- curb/gutter flow intent
- discharge-sensitive zones
- tie-in expectations to adjacent corridor legs

Detailed hydraulic solving remains outside the initial v1 scope.

## 15. Evaluation Responsibilities

`IntersectionModel` should support service inputs for:

- finding active intersection context at one station
- resolving leg-aware section transitions
- identifying control-area overrides
- exposing drainage-sensitive warnings
- driving review overlays for intersection influence zones

## 16. Relationship to Outputs and Review

Intersection-aware outputs should be able to show:

- active intersection identity
- affected leg role
- control-area boundaries
- turn-lane or curb-return policy references
- drainage and grading warnings where relevant

Review surfaces must consume normalized output payloads rather than parse junction editor widgets directly.

## 17. Exchange Expectations

Intersection-related exchange should support, where practical:

- mapped leg references from external alignments
- feature-line or reference geometry tied to control areas
- degraded diagnostics when imported data lacks explicit junction semantics
- export rows that preserve stable intersection identity and participating legs

## 18. Diagnostics

Recommended early diagnostics include:

- missing or duplicate leg reference
- overlapping control areas
- unresolved turn-lane policy reference
- incompatible grading policy between participating legs
- unresolved drainage outfall inside control area
- imported junction geometry with ambiguous ownership

## 19. Non-goals

`IntersectionModel` should not become:

- a signal controller database
- a manual drafting patch area
- a substitute for mainline alignment or profile models
- an excuse to bypass region and section contracts

## 20. Next Documents

This model should be followed by:

1. `docsV1/V1_DRAINAGE_MODEL.md`
2. `docsV1/V1_SECTION_MODEL.md`
3. `docsV1/V1_VIEWER_PLAN.md`
4. `docsV1/V1_EXCHANGE_PLAN.md`

In v1, intersections should be modeled as explicit control areas with stable leg identity, structured policy, and traceable downstream section and review effects.

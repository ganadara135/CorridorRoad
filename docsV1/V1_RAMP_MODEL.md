# CorridorRoad V1 Ramp Model

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_REGION_MODEL.md`

## 1. Purpose

This document defines the v1 internal source contract for ramp and merge/diverge design context.

It exists to make clear:

- what `RampModel` owns
- how ramps differ from ordinary mainline alignment rows
- how ramps connect to mainline and junction contexts
- how ramp policy feeds corridor, section, output, and review workflows

## 2. Scope

This model covers:

- ramp identity and topology
- parent/child corridor relationships
- merge, diverge, gore, and taper definitions
- ramp-specific design criteria
- tie-in references to alignment, profile, and region policy
- diagnostics and traceability

This model does not cover:

- detailed mainline alignment geometry authoring
- full at-grade intersection policy authoring
- signal timing or traffic simulation
- final generated 3D geometry as an edit source

## 3. Core Rule

`RampModel` is a durable source-of-truth model for ramp intent and tie-in policy.

This means:

- corridor-network evaluation reads from it
- viewers may inspect it through derived results
- generated ramp geometry must not replace ramp source intent
- local review overlays remain downstream artifacts

## 4. Why Ramp Modeling Matters

In v1, ramps must not be treated as ad-hoc extra alignments with hidden assumptions.

Ramp behavior affects:

- merge and diverge geometry
- tie-in grading
- gore-area section changes
- region and template switching
- drainage concentration and low-point risk
- earthwork and quantity comparison

`RampModel` exists so those effects are explicit rather than scattered across unrelated subsystems.

## 5. Relationship to Alignment and Intersection Models

The architectural distinction is:

- `AlignmentModel` owns durable horizontal geometry definitions
- `RampModel` owns ramp role, topology, and tie-in policy
- `IntersectionModel` owns at-grade junction control areas and leg relationships

One ramp may reference one or more alignments and profiles, but `RampModel` owns the connection meaning.

## 6. Design Goals

The v1 ramp subsystem should:

- make ramp identity explicit
- support merge, diverge, and connector intent
- preserve clear parent/child corridor relationships
- support deterministic tie-in evaluation
- expose diagnostics for taper, gore, and tie-in conflicts
- keep ramp behavior traceable into applied sections and review outputs

## 7. Ramp Scope in v1

Recommended early v1 support:

- on-ramp and off-ramp definitions
- connector ramp definitions
- merge/diverge zone definitions
- gore-area policy references
- tie-in constraints to mainline or junction context
- ramp-aware review and diagnostics

Deferred or later refinements may include:

- richer interchange-family templates
- advanced weaving diagnostics
- jurisdiction-specific automatic ramp drafting conventions

## 8. Ramp Object Families

Recommended primary object families:

- `RampModel`
- `RampRow`
- `RampTieInSet`
- `RampZoneRow`
- `RampConstraintSet`
- `RampEvaluationResult`

## 9. RampModel Root

### 9.1 Purpose

`RampModel` is the durable container for one project-level ramp policy set.

### 9.2 Recommended root fields

- `schema_version`
- `ramp_model_id`
- `project_id`
- `label`
- `ramp_rows`
- `tie_in_rows`
- `constraint_rows`
- `unit_context`
- `source_refs`
- `diagnostic_rows`

### 9.3 Rule

One `RampModel` may manage many ramps, but each ramp must have stable identity and an explicit owning network context.

## 10. RampRow

### 10.1 Purpose

Each `RampRow` represents one named ramp or connector intent.

### 10.2 Recommended fields

- `ramp_id`
- `ramp_index`
- `ramp_kind`
- `alignment_ref`
- optional `profile_ref`
- optional `superelevation_ref`
- `parent_alignment_ref`
- optional `intersection_ref`
- `station_start`
- `station_end`
- `design_criteria_ref`
- `tie_in_set_ref`
- `source_ref`
- `notes`

### 10.3 Recommended kinds

- `on_ramp`
- `off_ramp`
- `connector_ramp`
- `collector_distributor_connector`
- `temporary_candidate_ramp`

### 10.4 Rule

`RampRow` must preserve ramp meaning in the corridor network, not just reference an isolated geometry line.

## 11. RampTieInSet

### 11.1 Purpose

`RampTieInSet` preserves how a ramp joins or leaves another corridor context.

### 11.2 Recommended fields

- `tie_in_set_id`
- `ramp_id`
- `tie_in_rows`
- `notes`

### 11.3 Recommended tie-in row fields

- `tie_in_id`
- `tie_in_kind`
- `target_kind`
- `target_ref`
- `station_start`
- `station_end`
- `offset_rule`
- `grade_match_rule`
- `section_transition_ref`
- `diagnostic_hint`

### 11.4 Recommended tie-in kinds

- `merge`
- `diverge`
- `connector_join`
- `gore_transition`
- `terminal_tie_in`

## 12. RampZoneRow

### 12.1 Purpose

Ramp zones preserve important sub-ranges inside a ramp where behavior changes.

### 12.2 Recommended fields

- `zone_id`
- `ramp_id`
- `zone_kind`
- `station_start`
- `station_end`
- `region_ref`
- optional `template_ref`
- optional `drainage_ref`
- `notes`

### 12.3 Recommended kinds

- `gore_zone`
- `taper_zone`
- `merge_zone`
- `diverge_zone`
- `terminal_zone`
- `drainage_sensitive_zone`

## 13. Design Criteria Policy

### 13.1 Purpose

Ramps often use different criteria than mainline geometry.

### 13.2 Recommended design criteria fields

- `criteria_id`
- `speed_context`
- `min_radius`
- `max_grade`
- `taper_policy`
- `gore_policy`
- `superelevation_policy`
- `drainage_policy_ref`
- `notes`

### 13.3 Rule

Criteria rows should preserve engineering meaning rather than become unlabeled local numbers.

## 14. Evaluation Responsibilities

`RampModel` should support service inputs for:

- identifying active ramp context at one station
- determining merge/diverge influence ranges
- locating gore-area policy changes
- feeding applied-section evaluation with ramp-zone context
- exposing review-ready diagnostics for tie-in failures

## 15. Relationship to Region and Section Models

`RampModel` may influence:

- region switching
- template changes
- lane and shoulder composition
- gore-area component logic
- drainage edge treatment

It should not directly mutate generated section geometry.

## 16. Review and Viewer Expectations

Ramp-aware review should be able to show:

- active ramp identity
- tie-in type
- gore or taper context
- affected region or template references
- drainage-sensitive warnings where relevant

The main review surfaces should consume derived payloads rather than parse ramp editor state directly.

## 17. Exchange Expectations

Ramp-related exchange should support, where practical:

- imported alignments tagged by corridor role
- tie-in references from `LandXML` or mapped exchange rows
- exported network identity for mainline/ramp distinction
- degraded diagnostics when external data lacks explicit ramp semantics

## 18. Diagnostics

Recommended early diagnostics include:

- missing parent alignment reference
- overlapping ramp zones
- inconsistent tie-in ordering
- ramp range outside referenced alignment limits
- unsupported merge/diverge mapping from external imports
- unresolved drainage-sensitive sag near tie-in

## 19. Non-goals

`RampModel` should not become:

- a hidden alignment duplicate
- a drawing-only interchange annotation store
- a traffic operations simulator
- a place to patch generated geometry by hand

## 20. Next Documents

This model should be followed by:

1. `docsV1/V1_INTERSECTION_MODEL.md`
2. `docsV1/V1_DRAINAGE_MODEL.md`
3. `docsV1/V1_SECTION_MODEL.md`
4. `docsV1/V1_EXCHANGE_PLAN.md`

In v1, ramp design should be treated as explicit corridor-network intent with stable identity, reviewable tie-in policy, and traceable downstream effects.

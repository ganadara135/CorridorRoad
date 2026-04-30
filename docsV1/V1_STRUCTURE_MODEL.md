# CorridorRoad V1 Structure Model

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_EXCHANGE_PLAN.md`

## 1. Purpose

This document defines the v1 internal source contract for corridor-related structures and structure interaction rules.

It exists to make clear:

- what `StructureModel` owns
- how structure references differ from corridor source models
- how structure interaction affects sections and corridor results
- how reference structures and imported structures should be handled

## 2. Scope

This model covers:

- corridor-adjacent structure identity
- station-aware structure placement
- clearance and interaction rules
- reference and IFC-backed structures
- structure interaction resolution
- diagnostics and traceability

This model does not cover:

- full bridge or building authoring systems
- arbitrary BIM authoring workflows
- generated section geometry editing
- final quantity report layout behavior

## 3. Core Rule

`StructureModel` is a durable source-of-truth model for structure context and structure-driven interaction policy.

This means:

- structures are real source inputs
- structure interaction modifies corridor evaluation but does not replace section intent
- imported structure references must remain identifiable as references
- generated section or solid geometry does not become the new structure truth

## 4. Why Structures Matter

Structures affect corridor behavior in ways that cannot be modeled by template, region, or override alone.

Typical examples:

- a box culvert crossing that changes local section treatment
- a retaining wall zone that changes slope behavior
- a clearance envelope that forces local notch, skip, or replacement logic
- an IFC reference object used for clash and coordination review

## 5. Relationship to Templates, Regions, and Overrides

The architectural distinction is:

- `AssemblyModel` defines reusable section intent
- `RegionModel` defines station-range policy
- `OverrideModel` defines narrow explicit exceptions
- `StructureModel` defines structure presence and interaction context

Structures should not become:

- hidden template replacements
- broad policy containers that should really be regions
- arbitrary geometry edits attached to results

## 6. Structure Philosophy in v1

Structures in v1 should be treated as corridor interaction participants.

That means the subsystem should preserve:

- what the structure is
- where it is
- how it interacts with the corridor
- whether it is authored, referenced, or imported

## 7. Structure Scope in v1

Recommended early v1 support:

- box culvert or crossing reference structures
- retaining wall and wall-adjacent structure context
- clearance envelopes
- structure influence zones
- notch, skip, split, and replacement interaction rules
- IFC-backed reference structures

Deferred or later refinements may include:

- richer native structure authoring
- advanced property-set integration
- deeper lifecycle coordination beyond corridor-focused needs

## 8. Structure Object Families

Recommended primary object families:

- `StructureModel`
- `StructureRow`
- `StructurePlacement`
- `StructureGeometrySpec`
- `StructureInteractionRule`
- `StructureInfluenceZone`
- `StructureResolutionResult`

## 9. StructureModel Root

### 9.1 Purpose

`StructureModel` is the durable container for corridor-related structure objects and rules.

### 9.2 Recommended root fields

- `schema_version`
- `structure_model_id`
- `project_id`
- optional `alignment_id`
- `label`
- `structure_rows`
- `interaction_rule_rows`
- `influence_zone_rows`
- `source_refs`
- `diagnostic_rows`

### 9.3 Rule

Structure identity and interaction rules must remain explicit and separate from generated corridor results.

## 10. StructureRow

### 10.1 Purpose

Each `StructureRow` represents one structure or structure reference that may influence corridor behavior.

### 10.2 Recommended fields

- `structure_id`
- `structure_kind`
- `structure_role`
- `placement_ref`
- `geometry_ref`
- `geometry_spec_ref`
- `reference_mode`
- `source_ref`
- `notes`

### 10.3 Recommended kinds

- `box_culvert`
- `retaining_wall`
- `crossing_structure`
- `abutment_context`
- `ifc_reference_structure`
- `generic_reference_structure`

### 10.4 Recommended roles

- `design_structure`
- `reference_structure`
- `coordination_structure`
- `temporary_candidate_structure`

### 10.5 Rule

The structure row should preserve engineering meaning instead of collapsing everything into a generic mesh reference.

Native structure dimensions and kind-specific shape parameters are governed by `docsV1/V1_STRUCTURE_GEOMETRY_CONTRACT.md`.

`geometry_spec_ref` should point to native v1 geometry intent.

`geometry_ref` should point to external, imported, or detailed reference geometry.

## 11. StructurePlacement

### 11.1 Purpose

`StructurePlacement` preserves where the structure sits relative to the corridor station space.

### 11.2 Recommended fields

- `placement_id`
- `alignment_id`
- `station_start`
- `station_end`
- optional `station_reference`
- `offset`
- `elevation_reference`
- `orientation_mode`
- `notes`

### 11.3 Rule

Placement should remain station-aware whenever possible, even if imported geometry also provides absolute coordinates.

## 12. StructureInteractionRule

### 12.1 Purpose

This rule family defines how structures affect section and corridor evaluation.

### 12.2 Recommended fields

- `interaction_rule_id`
- `structure_ref`
- `rule_kind`
- `target_scope`
- `parameter`
- `value`
- `unit`
- `priority`
- `notes`

### 12.3 Recommended rule kinds

- `clearance_rule`
- `notch_rule`
- `skip_rule`
- `split_rule`
- `local_replacement_rule`
- `approach_treatment_rule`
- `wall_adjacent_rule`

### 12.4 Rule

Interaction rules should modify section and corridor evaluation through structured semantics, not through direct mesh surgery.

## 13. StructureInfluenceZone

### 13.1 Purpose

`StructureInfluenceZone` captures the station or spatial range over which a structure affects the corridor.

### 13.2 Recommended fields

- `influence_zone_id`
- `structure_ref`
- `zone_kind`
- `station_start`
- `station_end`
- optional `offset_min`
- optional `offset_max`
- `notes`

### 13.3 Recommended kinds

- `clearance_zone`
- `transition_zone`
- `replacement_zone`
- `structure_review_zone`

### 13.4 Rule

Influence zones should remain explicit instead of being inferred ad hoc from display geometry in every consumer.

## 14. Reference and IFC Policy

### 14.1 Reference structures

Reference structures may come from:

- native project context
- imported engineering references
- coordination geometry

### 14.2 IFC-backed structures

IFC-backed structures should preserve:

- external identity
- reference mode
- placement interpretation
- degraded-import diagnostics where needed

### 14.3 Rule

An imported IFC structure may be sufficient for coordination and clearance without becoming a full native structure authoring object.

## 15. StructureResolutionService

### 15.1 Purpose

This service resolves which structure context and interaction rules are active at a station or station range.

### 15.2 Typical queries

- station to active structures
- station to active influence zones
- structure conflict lookup
- active clearance rule lookup
- structure interaction packaging for applied sections

### 15.3 Rule

Section and corridor consumers should not implement independent structure-lookup logic.

## 16. StructureResolutionResult

### 16.1 Purpose

This result object captures the active structure context for downstream consumers.

### 16.2 Recommended fields

- `resolution_id`
- `station`
- `active_structure_ids`
- `active_rule_ids`
- `active_influence_zone_ids`
- `diagnostic_rows`
- `notes`

### 16.3 Rule

Resolution results are derived evaluation objects, not new source data.

## 17. Relationship to AppliedSection and Corridor

`AppliedSection` evaluation depends on structure context for:

- clearance checks
- local notch or skip behavior
- local component replacement behavior
- wall-adjacent treatment

`CorridorModel` must consume resolved structure interaction rather than hiding structure effects in scattered build code.

## 18. Relationship to Viewer and 3D Review

Viewer and 3D review systems may consume structure-derived context through:

- structure markers
- influence-zone highlights
- clearance diagnostics
- structure interaction rows in section review

But they must not become the new structure source.

The Viewer should be able to trace a section effect back to:

- `structure_id`
- `interaction_rule_id`
- `influence_zone_id`

## 19. Relationship to Quantities and Earthwork

Structure context may affect:

- corridor quantity grouping
- local replacement quantities
- retaining or wall-adjacent treatments
- earthwork interpretation near structures

Quantity and earthwork systems should consume normalized structure interaction results rather than recomputing their own structure semantics from geometry only.

## 20. Diagnostics

Diagnostics should be produced when:

- a structure placement cannot be resolved
- imported structure coordinates are degraded or ambiguous
- a clearance rule is impossible
- overlapping structure influence zones conflict
- a structure interaction rule targets unsupported behavior

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `source_ref`
- optional `station`
- `message`
- `notes`

## 21. Identity and Provenance

Structure objects should preserve:

- stable `structure_id`
- related `alignment_id` where relevant
- external import identity where relevant
- reference mode
- source file or edit provenance
- candidate-vs-approved status where applicable

This is important for:

- Viewer source tracing
- corridor diagnostics
- IFC coordination
- AI alternative comparison

## 22. Validation Rules

Validation should check for:

- missing placement references
- invalid station ranges
- impossible influence-zone definitions
- unsupported structure kinds
- rule conflicts by priority and target
- unresolved imported reference identity

Validation results should be recorded in `diagnostic_rows`.

## 23. AI and Alternative Design

AI-assisted workflows may propose:

- alternative retaining-wall extents
- different structure influence zones
- clearance-aware corridor alternatives
- reduced-earthwork structure-adjacent treatments

But accepted changes must still be written into normalized structure source objects or related interaction rules.

The AI layer must not keep a hidden structure patch system.

## 24. Anti-Patterns

The following should be avoided:

- treating imported IFC meshes as full engineering truth without diagnostics
- embedding structure effects directly into generated section geometry
- duplicating structure lookup and clearance logic across many consumers
- using structure rows as generic geometry buckets with no semantic role
- hiding local corridor changes in structure hacks that should be regions or overrides

## 25. Summary

In v1, `StructureModel` is the durable source contract for:

- corridor-related structures and references
- station-aware placement
- structure interaction rules
- influence zones and clearance context

It should remain explicit and interaction-focused, so that:

- `AppliedSection` and `CorridorModel` can resolve structure effects clearly
- Viewer traceability stays strong
- IFC and reference structures remain usable without polluting core source truth
- quantity, earthwork, and AI workflows can reason about structure context consistently

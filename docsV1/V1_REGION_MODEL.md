# CorridorRoad V1 Region Model

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_MODEL.md`
- `docsV1/V1_SUPERELEVATION_MODEL.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_STRUCTURE_MODEL.md`
- `docsV1/V1_RAMP_MODEL.md`
- `docsV1/V1_INTERSECTION_MODEL.md`

## 1. Purpose

This document defines the v1 internal source contract for station-range region policy.

It exists to make clear:

- what `RegionModel` owns
- how regions differ from templates and overrides
- how station ranges select active design policy
- how region resolution feeds applied-section and corridor evaluation

## 2. Scope

This model covers:

- station-range assignment
- template switching
- region-level policy selection
- overlapping design-context layers such as drainage, ditch, bridge, culvert, ramp, and intersection influence
- transition-in and transition-out behavior
- precedence and conflict handling
- diagnostics and traceability

This model does not cover:

- detailed section-template authoring
- horizontal or vertical geometry authoring
- final generated section geometry
- unbounded free-form local edits

## 3. Core Rule

`RegionModel` is a durable source-of-truth model for station-range design policy.

This means:

- corridor evaluation reads from it
- viewers may inspect its effect through applied results
- regions select and modify policy
- generated geometry does not become a substitute for region intent

## 4. Why Regions Matter

In v1, the corridor is not one uniform section repeated forever.

It changes by station because of:

- template changes
- roadside treatment changes
- structure influence
- drainage policy changes
- ramp and intersection influence
- construction-stage or design exceptions

`RegionModel` is the layer that says which policy applies where.

## 5. Relationship to Templates and Overrides

The architectural distinction is:

- `AssemblyModel` defines reusable section intent
- `RegionModel` assigns that intent over station ranges and attaches applicable design context layers
- explicit override models handle narrow exceptions

Regions should not become:

- a second template library
- a hidden generated-geometry editor
- an unlimited patch bucket for every local exception

## 5.1 Relationship to Structures, Drainage, Ramps, and Intersections

Regions are the station-range organizer for corridor behavior.

They may reference structures, drainage elements, ramp contexts, or intersection contexts, but they do not own those domain meanings.

For the planned Region application workflow, use `V1_REGION_APPLICATION_FLOW_PLAN.md`.

That plan keeps the authoring order as `Assembly -> Structure -> Region`.

It treats each `RegionRow` as the station-range application layer for one Assembly and zero or one Structure.

The ownership split is:

- `RegionModel` owns where a corridor policy interval applies
- `StructureModel` owns bridge, culvert, retaining wall, and structure interaction meaning
- `DrainageModel` owns ditch, gutter, pipe, inlet, collection, and discharge meaning
- `RampModel` owns ramp topology, merge/diverge, and ramp tie-in meaning
- `IntersectionModel` owns at-grade junction control-area meaning

A region may therefore say:

- this station range is primarily a bridge region
- this same range also has ditch and drainage layers
- this range references one bridge structure and related drainage elements

But the region must not become the hidden source model for the bridge or drainage design itself.

## 6. Relationship to Alignment, Profile, and Superelevation

`RegionModel` is defined in the station space established by `AlignmentModel`.

It may select or reference:

- active section template families
- profile-related policy modes where needed
- active superelevation set or lane-group policy context

But it does not own the underlying alignment, profile, or superelevation source definitions.

## 7. Design Goals

The v1 region subsystem should:

- make station-range policy explicit
- support template switching without geometry hacks
- support transition-aware policy changes
- preserve strong traceability into applied sections
- support localized but structured change
- expose deterministic region-resolution services

## 8. Region Scope in v1

Recommended early v1 support:

- template assignment by station range
- primary region kind by station range
- additive applied layers for overlapping design contexts
- roadway-side policy switching
- cut/fill and daylight policy selection
- structure-sensitive range handling
- drainage-sensitive range handling
- ramp and intersection context references
- transition zones between region states
- region-boundary diagnostics

Deferred or later refinements may include:

- more advanced multi-alignment sharing
- richer phased-construction region stacks
- jurisdiction-specific automated region generation

## 9. Region Object Families

Recommended primary object families:

- `RegionModel`
- `RegionRow`
- `RegionPolicySet`
- `RegionTransitionRow`
- `RegionConflictSet`
- `RegionResolutionResult`

## 10. RegionModel Root

### 10.1 Purpose

`RegionModel` is the durable container for station-range policy assignment.

### 10.2 Recommended root fields

- `schema_version`
- `region_model_id`
- `project_id`
- `alignment_id`
- `label`
- `region_rows`
- `transition_rows`
- `constraint_rows`
- `unit_context`
- `source_refs`
- `diagnostic_rows`

### 10.3 Rule

One `RegionModel` may manage many region rows for a given alignment context, but identity and ordering must remain explicit.

## 11. RegionRow

### 11.1 Purpose

Each `RegionRow` represents one station-bounded policy zone.

### 11.2 Recommended fields

- `region_id`
- `region_index`
- `primary_kind`
- `applied_layers`
- `station_start`
- `station_end`
- `assembly_ref`
- `structure_ref`
- compatibility `structure_refs`
- `drainage_refs`
- optional `ramp_ref`
- optional `intersection_ref`
- `policy_set_ref`
- `template_ref`
- optional `superelevation_ref`
- `override_refs`
- `priority`
- `source_ref`
- `notes`

### 11.3 Recommended kinds

- `normal_road`
- `bridge`
- `culvert`
- `intersection`
- `ramp`
- `drainage`
- `transition`
- `structure_influence`
- `daylight_control`
- `temporary_candidate_region`

### 11.4 Rule

Region rows must be defined in station space, not only by visual extents or 3D shapes.

One region row should reference one Assembly and zero or one Structure.

If more than one Structure is needed over the same apparent station range, use separate Region rows so each row has one clear structure owner.

`structure_refs` may remain in compatibility storage, but more than one active structure reference should produce a diagnostic.

### 11.5 Primary Kind and Applied Layers

One region should have one `primary_kind`.

The `primary_kind` answers the question:

- what is the dominant corridor behavior for this station range?

Examples:

- `normal_road`
- `bridge`
- `culvert`
- `intersection`
- `ramp`
- `drainage`

Other overlapping items should be represented as `applied_layers` and explicit references.

The following primary kinds require a `structure_ref` diagnostic if the reference is empty:

- `bridge`
- `culvert`
- `structure_influence`

This is a validation rule for source completeness. It does not make Region own Structure geometry.

Examples:

- a bridge region with `applied_layers = ["ditch", "drainage"]`
- a normal road region with `applied_layers = ["culvert", "guardrail"]`
- an intersection region with `applied_layers = ["drainage", "widening"]`
- a ramp region with `applied_layers = ["retaining_wall", "side_ditch"]`

This keeps the region readable while allowing realistic overlap.

### 11.6 Example: Bridge with Ditch and Drainage

Recommended source shape:

```json
{
  "region_id": "region:bridge-01",
  "region_index": 3,
  "primary_kind": "bridge",
  "applied_layers": ["ditch", "drainage"],
  "station_start": 120.0,
  "station_end": 180.0,
  "assembly_ref": "assembly:bridge-deck",
  "structure_ref": "structure:bridge-01",
  "structure_refs": ["structure:bridge-01"],
  "drainage_refs": ["drainage:deck-drain-left", "drainage:side-ditch-right"],
  "policy_set_ref": "region-policy:bridge-01",
  "override_refs": ["override:bridge-shoulder-narrowing"],
  "priority": 80,
  "notes": "Bridge deck region with drainage and ditch treatment."
}
```

Viewer display may compress this into one row:

`STA 120.000 - 180.000 | bridge | Assembly: bridge-deck | Layers: ditch, drainage | Structure: bridge-01`

### 11.7 Rule for Overlap

Overlapping design meaning should be expressed inside one region when:

- the station range is the same or nearly the same
- one primary corridor behavior dominates
- the extra items are additive layers or references
- the user expects to edit the range as one practical work zone

Separate region rows should be used when:

- station ranges differ meaningfully
- two primary behaviors compete
- the overlap needs a different priority or transition
- diagnostics need to isolate the behavior clearly

### 11.8 Preset Data

The Regions editor should use selectable preset data instead of a single starter-only command.

Available first-slice presets:

- `Basic Road`
- `Bridge Segment`
- `Intersection Zone`
- `Ramp Tie-In`
- `Drainage Control`

Loading a preset only fills the editable Region table.

Preset rows should scale to the current station range from v1 Stations or Alignment length.

It does not create Applied Sections, Corridor surfaces, solids, or viewer-only geometry.

## 12. RegionPolicySet

### 12.1 Purpose

`RegionPolicySet` preserves the actual policy choices applied over a region.

### 12.2 Recommended fields

- `policy_set_id`
- `template_ref`
- `assembly_ref`
- `component_policy_rows`
- `daylight_policy`
- `drainage_policy`
- `structure_policy`
- `ramp_policy`
- `intersection_policy`
- `earthwork_policy`
- `notes`

### 12.3 Rule

Policy sets should preserve engineering meaning rather than turning into arbitrary key-value blobs.

## 13. Component Policy Rows

### 13.1 Purpose

Component policy rows describe structured changes to template behavior over a region.

### 13.2 Recommended fields

- `component_policy_id`
- `component_scope`
- `parameter`
- `value`
- `unit`
- `policy_kind`
- `notes`

### 13.3 Recommended policy kinds

- `parameter_override`
- `component_enable`
- `component_disable`
- `side_specific_policy`
- `transition_policy`

### 13.4 Rule

These rows are structured region policy, not free-form geometry edits.

## 14. RegionTransitionRow

### 14.1 Purpose

`RegionTransitionRow` preserves how policy changes blend at boundaries.

### 14.2 Recommended fields

- `transition_id`
- `from_region_ref`
- `to_region_ref`
- `station_start`
- `station_end`
- `transition_kind`
- `transition_policy`
- `notes`

### 14.3 Recommended kinds

- `linear_blend`
- `step_change`
- `component_specific_blend`
- `structure_forced_transition`

### 14.4 Rule

Transition intent should remain explicit instead of being inferred later from two disconnected region rows.

## 15. Constraint Rows

### 15.1 Purpose

Constraint rows capture region-level design intent and validation context.

### 15.2 Recommended fields

- `constraint_id`
- `kind`
- `value`
- `unit`
- `hard_or_soft`
- `notes`

### 15.3 Recommended kinds

- `protected_station_range`
- `no_template_switch_zone`
- `forced_structure_clearance_zone`
- `fixed_daylight_policy`
- `earthwork_priority_zone`

## 16. Precedence Model

Recommended evaluation precedence:

1. template base definition
2. region primary kind
3. region policy set
4. region applied layers and domain references
5. region transition behavior
6. explicit override rows
7. structure interaction rules
8. drainage interaction rules
9. ramp and intersection interaction rules
10. terrain and daylight evaluation

This order should be documented and reused consistently across services.

## 17. Region vs Override Boundary

### 17.1 Region role

Regions handle structured policy over meaningful station ranges.

### 17.2 Override role

Overrides handle explicit exceptions such as:

- one narrow station range
- one event-specific condition
- one local parameter exception

### 17.3 Rule

If a change is reusable over a meaningful station range, it should probably be a region policy.

If a change is narrow and exceptional, it should probably be an explicit override.

## 18. RegionResolutionService

### 18.1 Purpose

This service resolves which region policy applies at a station or station range.

### 18.2 Typical queries

- station to active region
- station range to overlapping regions
- region boundary detection
- transition interval lookup
- conflict detection

### 18.3 Rule

Applied-section and corridor consumers should not re-implement their own region-selection logic.

## 19. RegionResolutionResult

### 19.1 Purpose

This result object captures resolved region context for downstream consumers.

### 19.2 Recommended fields

- `resolution_id`
- `station`
- `active_region_id`
- `active_primary_kind`
- `active_applied_layers`
- `active_policy_set_id`
- `active_template_ref`
- `active_assembly_ref`
- `active_transition_ref`
- `resolved_structure_ref`
- compatibility `resolved_structure_refs`
- `resolved_drainage_refs`
- `resolved_ramp_ref`
- `resolved_intersection_ref`
- `diagnostic_rows`
- `notes`

### 19.3 Rule

Resolution results are derived evaluation objects, not new durable source data.

## 20. Conflict Handling

Conflict handling should detect:

- overlapping region rows with incompatible priority
- gaps between required regions
- conflicting transition definitions
- template references that do not exist
- assembly references that do not exist
- structure or drainage references that do not exist
- illegal policy combinations
- multiple primary behaviors assigned to one row
- applied layers that should be separate primary regions

The system should prefer explicit diagnostics over silent winner-takes-all behavior.

## 21. Diagnostics

Diagnostics should be produced when:

- region rows overlap ambiguously
- transition ranges are invalid
- a station falls into a gap with no valid policy
- a policy set references missing source objects
- region policy requires degraded application

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `source_ref`
- `message`
- `notes`

## 22. Identity and Provenance

Region objects should preserve:

- stable `region_id`
- related `alignment_id`
- referenced `template_ref`
- referenced `superelevation_ref` where used
- source file or edit provenance
- candidate-vs-approved status where applicable

This is important for:

- Viewer source inspection
- applied-section traceability
- AI candidate comparison
- export and reporting diagnostics

## 23. Relationship to AppliedSection and Corridor

`AppliedSection` evaluation depends on `RegionModel` for:

- active template selection
- region-scoped parameter policy
- transition behavior at station boundaries
- structured local policy before explicit overrides

`CorridorModel` must consume resolved region context rather than embedding hidden ad-hoc region logic.

## 24. Relationship to Viewer and 3D Review

Viewer and 3D review systems may consume region-derived context through:

- region boundary markers
- active region labels
- source inspector rows
- region-based review filtering

But they must not become the new region source.

The Viewer should be able to trace a section behavior back to:

- active region
- primary kind
- applied layers
- policy set
- assembly reference
- structure and drainage references
- transition row
- override source if one exists

## 25. Relationship to Earthwork Balance

Region policy may influence earthwork by selecting:

- daylight rules
- shoulder or slope treatments
- structure-related constraints
- earthwork-priority zones

Earthwork analysis may compare region alternatives, but must not write hidden changes back into `RegionModel`.

## 26. AI and Alternative Design

AI-assisted workflows may propose:

- new region splits
- alternative template assignments
- different daylight or roadside policies
- earthwork-aware region policy changes

But accepted changes must still be written into normalized region source objects.

The AI layer must not keep a separate hidden region graph.

## 27. Recommended Minimal Schema Version

Recommended initial version:

- `RegionModelSchemaVersion = 1`

## 28. Anti-Patterns

The following should be avoided:

- using regions as unlabeled geometry patches
- hiding major design changes inside ad-hoc override piles
- treating generated section geometry as the true region definition
- duplicating region-selection logic in many consumers
- silently resolving overlapping conflicts without diagnostics

## 29. Summary

In v1, `RegionModel` is the durable source contract for:

- station-range policy assignment
- template switching
- structured local policy
- transition-aware region resolution

It should remain explicit and station-based, so that:

- `AppliedSection` can resolve the correct design intent at each station
- Viewer traceability stays strong
- overrides remain narrow and controlled
- corridor, earthwork, and AI workflows can compare alternatives without corrupting source truth

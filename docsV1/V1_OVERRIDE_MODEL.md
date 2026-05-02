# CorridorRoad V1 Override Model

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_CORRIDOR_MODEL.md`

## 1. Purpose

This document defines the v1 internal source contract for explicit design overrides.

It exists to make clear:

- what an override is
- how overrides differ from templates and regions
- which override scopes are allowed
- how overrides participate in section and corridor evaluation

## 2. Scope

This model covers:

- explicit exception rows
- override scope and target rules
- override precedence
- override resolution
- diagnostics and traceability

This model does not cover:

- reusable section-template authoring
- station-range policy authoring for broad design intent
- generated geometry editing
- viewer-side manual shape manipulation

## 3. Core Rule

`OverrideModel` is a durable source-of-truth model for narrow, explicit exceptions.

This means:

- overrides are real source data
- they are not generated geometry patches
- they are applied after region policy and before structure/terrain terminal evaluation
- they must remain traceable and bounded

## 4. Why Overrides Exist

Not every design change should require:

- a new section template
- a new broad region split

Overrides exist for cases like:

- one narrow station range with a local width change
- one event-specific condition near a structure
- one component parameter that must deviate from region policy

## 5. Relationship to Templates and Regions

The architectural distinction is:

- `AssemblyModel` defines reusable section intent
- `RegionModel` defines structured policy over meaningful station ranges
- `OverrideModel` defines narrow, explicit exceptions

Overrides should not become:

- a second template library
- an unbounded patch pile
- a hidden geometry editor

## 6. Override Philosophy in v1

Overrides are allowed, but they are intentionally constrained.

The product should prefer:

- template for reusable intent
- region for range-based policy
- override for exceptions

If overrides become the dominant way to model a corridor, the design structure is probably wrong.

## 7. Override Scope in v1

Recommended early v1 support:

- current station override
- station range override
- region-specific override
- event-specific override
- component-specific parameter override

Deferred or later refinements may include:

- richer dependency-aware override groups
- advanced approval workflows for override-heavy projects

## 8. Override Object Families

Recommended primary object families:

- `OverrideModel`
- `OverrideRow`
- `OverrideTarget`
- `OverrideScope`
- `OverrideResolutionResult`
- `OverrideConflictSet`

## 9. OverrideModel Root

### 9.1 Purpose

`OverrideModel` is the durable container for explicit exception rows.

### 9.2 Recommended root fields

- `schema_version`
- `override_model_id`
- `project_id`
- optional `alignment_id`
- `label`
- `override_rows`
- `constraint_rows`
- `source_refs`
- `diagnostic_rows`

### 9.3 Rule

Overrides must remain explicit rows with stable identity.

They should not be hidden inside arbitrary object properties or mutated result geometry.

## 10. OverrideRow

### 10.1 Purpose

Each `OverrideRow` represents one explicit exception to otherwise resolved design policy.

### 10.2 Recommended fields

- `override_id`
- `override_kind`
- `target_ref`
- `scope_ref`
- `parameter`
- `value`
- `unit`
- `priority`
- `activation_state`
- `source_ref`
- `notes`

### 10.3 Recommended override kinds

- `parameter_override`
- `component_enable`
- `component_disable`
- `target_swap`
- `policy_override`
- `station_event_override`

### 10.4 Rule

Override rows should preserve engineering meaning and should not store opaque geometry blobs as values.

## 11. OverrideTarget

### 11.1 Purpose

`OverrideTarget` identifies what the override is acting on.

### 11.2 Recommended fields

- `target_id`
- `target_kind`
- `target_ref`
- `component_ref`
- `side`
- `notes`

### 11.3 Recommended target kinds

- `template_component`
- `region_policy`
- `section_parameter`
- `superelevation_parameter`
- `structure_interaction_parameter`

### 11.4 Rule

Targets must resolve to real source-domain objects or well-defined derived inputs.

Overrides must not point to arbitrary scene geometry.

## 12. OverrideScope

### 12.1 Purpose

`OverrideScope` defines where and when an override applies.

### 12.2 Recommended fields

- `scope_id`
- `scope_kind`
- `station_start`
- `station_end`
- optional `region_ref`
- optional `event_ref`
- optional `component_side`
- `notes`

### 12.3 Recommended scope kinds

- `single_station`
- `station_range`
- `region_bound_scope`
- `event_scope`
- `component_scope`

### 12.4 Rule

Every override must have an explicit bounded scope.

No override should apply to "whatever happens later" without a defined station or event context.

## 13. Constraint Rows

### 13.1 Purpose

Constraint rows help keep overrides controlled.

### 13.2 Recommended fields

- `constraint_id`
- `kind`
- `value`
- `unit`
- `hard_or_soft`
- `notes`

### 13.3 Recommended kinds

- `max_override_span`
- `no_override_zone`
- `approval_required`
- `protected_component_rule`

## 14. Precedence Model

Recommended evaluation precedence:

1. template base definition
2. region policy
3. region transition behavior
4. explicit override rows
5. structure interaction rules
6. terrain/daylight terminal evaluation

This order must be documented consistently across section and corridor services.

## 15. OverrideResolutionService

### 15.1 Purpose

This service resolves which overrides are active for a station or station range.

### 15.2 Typical queries

- station to active overrides
- station range to overlapping overrides
- component-specific override lookup
- event-linked override lookup
- override conflict detection

### 15.3 Rule

Section and corridor consumers should not implement ad-hoc override logic independently.

## 16. OverrideResolutionResult

### 16.1 Purpose

This result object captures the active override set for downstream evaluation.

### 16.2 Recommended fields

- `resolution_id`
- `station`
- `active_override_ids`
- `resolved_target_rows`
- `diagnostic_rows`
- `notes`

### 16.3 Rule

Resolution results are derived evaluation objects, not new source data.

## 17. Conflict Handling

Conflict handling should detect:

- overlapping overrides on the same target
- contradictory values with equal priority
- scopes outside valid station domain
- target references that do not resolve
- disabled or stale overrides still being requested

The system should prefer explicit diagnostics over silent last-write-wins behavior.

## 18. Activation and Lifecycle

Overrides should support explicit lifecycle states such as:

- `active`
- `draft`
- `disabled`
- `superseded`

This helps:

- review workflows
- candidate comparison
- safer editing

## 19. Diagnostics

Diagnostics should be produced when:

- an override target is missing
- an override scope is invalid
- two overrides conflict ambiguously
- an override tries to change unsupported geometry semantics
- an override is too broad and should probably be a region policy

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `source_ref`
- `message`
- `notes`

## 20. Identity and Provenance

Override objects should preserve:

- stable `override_id`
- related `alignment_id` where relevant
- related `region_ref` or `event_ref` where relevant
- target and scope identity
- source file or edit provenance
- candidate-vs-approved status where applicable

This is important for:

- Viewer source tracing
- section diagnostics
- corridor recompute
- AI-assisted proposal review

## 21. Relationship to AppliedSection and Corridor

`AppliedSection` evaluation depends on resolved override context for:

- explicit parameter changes
- local enable/disable behavior
- event-specific exceptions

`CorridorModel` must consume normalized override resolution rather than hiding local exception logic inside random build code.

## 22. Relationship to Viewer

The Viewer should be able to trace a changed component or value back to:

- `override_id`
- target row
- scope row
- precedence position

The Viewer may hand users off to the override editor or manager, but it must not directly mutate generated section geometry.

## 23. Relationship to AI and Alternatives

AI-assisted workflows may propose:

- candidate override rows
- override consolidation suggestions
- converting repeated overrides into a region policy
- removing obsolete overrides

But accepted changes must still be written into normalized override source objects.

The AI layer must not keep its own hidden override patch system.

## 24. Validation Rules

Validation should check for:

- empty or invalid parameter names
- missing target references
- invalid scope geometry or station range
- conflicts by priority and target
- overrides exceeding allowed span
- unsupported override kinds

Validation results should be recorded in `diagnostic_rows`.

## 25. Anti-Patterns

The following should be avoided:

- editing generated section wires and calling them overrides
- using overrides for broad reusable design intent
- storing arbitrary geometry blobs inside override values
- duplicating override logic across viewers and exporters
- letting override piles replace region or template design

## 26. Summary

In v1, `OverrideModel` is the durable source contract for:

- narrow design exceptions
- explicit target-and-scope changes
- controlled precedence after region policy
- traceable local deviation from reusable intent

It should remain bounded and structured, so that:

- templates stay reusable
- regions stay meaningful
- `AppliedSection` can resolve true local exceptions clearly
- Viewer, corridor, and AI workflows can inspect and compare exceptions without corrupting source truth

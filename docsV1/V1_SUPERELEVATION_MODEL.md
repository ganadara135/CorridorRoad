# CorridorRoad V1 Superelevation Model

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`

## 1. Purpose

This document defines the v1 internal source contract for superelevation and station-based crossfall behavior.

It exists to make clear:

- what `SuperelevationModel` owns
- how crossfall behavior differs from section-template defaults
- how runoff and transition intent should be preserved
- how superelevation connects to applied-section evaluation and corridor results

## 2. Scope

This model covers:

- station-based crossfall behavior
- lane-group roll intent
- runoff and transition rules
- crossfall control rows
- deterministic superelevation evaluation services
- validation and diagnostics

This model does not cover:

- horizontal alignment authoring
- vertical profile authoring
- section-template composition
- final viewer rendering behavior

## 3. Core Rule

`SuperelevationModel` is a durable source-of-truth model for station-based crossfall behavior.

This means:

- applied-section evaluation reads from it
- viewers and outputs may inspect derived results from it
- template defaults do not replace it
- no generated section geometry becomes the new superelevation truth

## 4. Relationship to Template Defaults

Section templates may define baseline cross slopes such as:

- lane crown
- shoulder default slope
- ditch or berm fall direction

But `SuperelevationModel` owns the station-based change behavior that modifies or replaces those defaults.

The architectural rule is:

- `AssemblyModel` defines intended default section composition
- `SuperelevationModel` defines station-aware crossfall transitions
- `AppliedSection` resolves the actual effective slopes at a given station

## 5. Relationship to Alignment and Profile

`SuperelevationModel` is defined in the station space established by `AlignmentModel`.

It may also depend on profile context when design rules or transitions need vertical awareness, but it does not replace `ProfileModel`.

The relationship is:

- `AlignmentModel` defines station and local horizontal frame
- `ProfileModel` defines elevation along station
- `SuperelevationModel` defines how crossfall and roll evolve along station

## 6. Design Goals

The v1 superelevation subsystem should:

- preserve true crossfall intent instead of only storing final baked geometry
- support station-aware transition logic
- support lane-group oriented roll behavior
- remain compatible with section-template parametric evaluation
- support imported and native rules
- expose deterministic services for section and corridor consumers

## 7. Superelevation Scope in v1

Recommended early v1 support:

- lane and shoulder crossfall control
- crown-to-full-super transition logic
- runoff and runout station ranges
- left/right side differentiation
- station range queries
- explicit override rows where needed

Deferred or later refinements may include:

- more complex divided-roadway lane-group management
- jurisdiction-specific design-table automation
- advanced multi-carriageway synchronization

## 8. Superelevation Object Families

Recommended primary object families:

- `SuperelevationModel`
- `CrossfallControlSequence`
- `CrossfallControlRow`
- `LaneGroupRollRule`
- `RunoffTransitionRow`
- `SuperelevationEvaluationResult`

## 9. SuperelevationModel Root

### 9.1 Purpose

`SuperelevationModel` is the durable container for one station-based crossfall design definition.

### 9.2 Recommended root fields

- `schema_version`
- `superelevation_id`
- `project_id`
- `alignment_id`
- optional `profile_id`
- `label`
- `superelevation_kind`
- `control_sequence`
- `lane_group_rows`
- `transition_rows`
- `constraint_rows`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

### 9.3 Recommended kinds

- `roadway_superelevation`
- `reference_crossfall`
- `temporary_candidate_superelevation`

## 10. CrossfallControlSequence

### 10.1 Purpose

`CrossfallControlSequence` preserves the ordered station-based control structure for crossfall behavior.

### 10.2 Rule

The control sequence must preserve transition intent, not just sampled slope values.

### 10.3 Recommended fields

- `control_sequence_id`
- `superelevation_id`
- `control_rows`
- `start_station`
- `end_station`
- `notes`

## 11. CrossfallControlRow

### 11.1 Purpose

Each control row represents a meaningful station-based crossfall control condition.

### 11.2 Recommended fields

- `control_row_id`
- `control_index`
- `station`
- `side`
- `target_component_scope`
- `crossfall_value`
- `crossfall_unit`
- `kind`
- `source_ref`
- `notes`

### 11.3 Recommended sides

- `left`
- `right`
- `center`
- `both`

### 11.4 Recommended kinds

- `normal_crown`
- `rotation_start`
- `full_super`
- `rotation_end`
- `reference_crossfall`
- `imported_control_with_diagnostics`

## 12. LaneGroupRollRule

### 12.1 Purpose

`LaneGroupRollRule` preserves which components rotate together and how their slope behavior should be interpreted.

### 12.2 Recommended fields

- `lane_group_id`
- `group_kind`
- `component_refs`
- `pivot_policy`
- `rotation_policy`
- `notes`

### 12.3 Recommended group kinds

- `mainline_lane_group`
- `shoulder_group`
- `auxiliary_lane_group`
- `transition_group`

### 12.4 Recommended pivot policies

- `centerline_pivot`
- `crown_pivot`
- `lane_edge_pivot`
- `custom_pivot_with_diagnostics`

## 13. RunoffTransitionRow

### 13.1 Purpose

`RunoffTransitionRow` preserves transition intervals between crossfall states.

### 13.2 Recommended fields

- `transition_id`
- `kind`
- `station_start`
- `station_end`
- `from_control_ref`
- `to_control_ref`
- `transition_policy`
- `notes`

### 13.3 Recommended kinds

- `runout`
- `runoff`
- `crossfall_blend`
- `imported_transition_with_diagnostics`

### 13.4 Rule

Transition rows should remain identifiable as design elements rather than being flattened into sampled slope rows only.

## 14. Constraint Rows

### 14.1 Purpose

Constraint rows capture superelevation design intent and review context.

### 14.2 Recommended fields

- `constraint_id`
- `kind`
- `value`
- `unit`
- `hard_or_soft`
- `notes`

### 14.3 Recommended kinds

- `max_superelevation_rate`
- `min_transition_length`
- `protected_station_range`
- `fixed_crown_zone`
- `shoulder_lock_rule`

## 15. Effective Crossfall Resolution

The effective crossfall at a station should be resolved from multiple layers:

1. section-template default slope intent
2. active superelevation control state
3. lane-group roll rules
4. active transition rows
5. region policy
6. explicit overrides
7. structure or drainage interaction rules where applicable

The result of this process belongs in `AppliedSection`, not back in the superelevation source contract.

## 16. Evaluation Services

Recommended service families:

- `SuperelevationService`
- `CrossfallResolutionService`
- `SuperelevationSamplingService`

## 17. SuperelevationService

### 17.1 Purpose

This service evaluates station-based crossfall behavior in deterministic form.

### 17.2 Typical queries

- station to left/right crossfall
- station to active control row
- station to active transition interval
- station to lane-group roll state

### 17.3 Rule

Section and corridor consumers should rely on shared superelevation evaluation rather than re-implementing crossfall interpretation themselves.

## 18. CrossfallResolutionService

### 18.1 Purpose

This service resolves the final effective crossfall values that should be applied to section components.

### 18.2 Typical responsibilities

- merge template defaults with superelevation state
- apply side-specific rules
- resolve shoulder behavior
- preserve traceability to source rows

### 18.3 Rule

Resolved values must keep source ownership visible so the Viewer can point users back to the correct editor or source row.

## 19. SuperelevationSamplingService

### 19.1 Purpose

This service produces sampled crossfall rows for review and output without replacing the source contract.

### 19.2 Typical consumers

- `AppliedSection` preview
- Cross Section Viewer
- 3D review overlays
- diagnostic tools

### 19.3 Rule

Sampled rows are derived evaluation output, not authoring truth.

## 20. Validation Rules

Validation should check for:

- broken control ordering
- overlapping or contradictory transition ranges
- invalid side assignment
- missing alignment reference
- unsupported imported runoff definitions
- impossible or ambiguous pivot policy

Validation results should be recorded in `diagnostic_rows`.

## 21. Diagnostics

Diagnostics should be produced when:

- imported crossfall controls do not map cleanly
- a transition must be simplified
- pivot behavior is unsupported
- a station query lands outside a valid superelevation domain
- effective crossfall cannot be resolved without degradation

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `source_ref`
- `message`
- `notes`

## 22. Identity and Provenance

Superelevation objects should preserve:

- stable `superelevation_id`
- referenced `alignment_id`
- optional related `profile_id`
- external import identity where relevant
- source file reference
- import or edit provenance
- candidate-vs-approved status where applicable

This is important for:

- section traceability
- viewer source inspection
- AI alternative comparison
- future exchange support

## 23. Relationship to Section and Corridor

`AppliedSection` evaluation depends on `SuperelevationModel` for:

- side-specific crossfall
- station-based transition behavior
- lane-group roll state
- actual rotated section geometry intent

`CorridorModel` must consume evaluated superelevation state rather than baking custom local slope logic into unrelated services.

## 24. Relationship to Outputs and Viewer

Outputs and viewer systems may consume derived superelevation effects through:

- `AppliedSection`
- `SectionOutput`
- `ProfileOutput` annotations where relevant
- 3D review overlays

But those consumers must not become the new superelevation source.

The Viewer should be able to trace an effective slope or rotated component back to:

- template default slope
- superelevation control row
- active transition row
- override source when present

## 25. AI and Alternative Design

AI-assisted workflows may propose:

- transition length changes
- alternative full-super rates
- lane-group roll adjustments
- reduced-earthwork crossfall alternatives

But accepted changes must still be written into normalized superelevation source objects.

The AI layer must not maintain a separate hidden crossfall representation.

## 26. Recommended Minimal Schema Version

Recommended initial version:

- `SuperelevationModelSchemaVersion = 1`

## 27. Anti-Patterns

The following should be avoided:

- storing only final rotated section wires as the superelevation truth
- burying crossfall rules inside section templates only
- duplicating crossfall logic across corridor and viewer code
- hiding degraded runoff or transition behavior
- embedding final section geometry into the superelevation source contract

## 28. Summary

In v1, `SuperelevationModel` is the durable source contract for:

- station-based crossfall behavior
- runoff and transition intent
- lane-group roll rules
- deterministic crossfall evaluation

It should remain station-aware and parametric, so that:

- `AppliedSection` can resolve real station geometry correctly
- Viewer traceability stays strong
- section templates remain clean default definitions
- future AI and exchange features can build on a stable source model

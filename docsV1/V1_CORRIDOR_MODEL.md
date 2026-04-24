# CorridorRoad V1 Corridor Model

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_RAMP_MODEL.md`
- `docsV1/V1_INTERSECTION_MODEL.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_TIN_ENGINE_PLAN.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`

## 1. Purpose

This document defines the v1 internal model for corridor evaluation and corridor-derived result generation.

It exists to make clear:

- what `CorridorModel` owns
- how corridor evaluation differs from templates and sections alone
- how station sampling and `AppliedSectionSet` are organized
- how ramp, intersection, and drainage context influence corridor evaluation
- how surfaces, solids, quantities, and earthwork derive from corridor results

## 2. Scope

This model covers:

- corridor identity and scope
- corridor-network context
- station sampling policy
- applied-section orchestration
- corridor result packages
- surface and solid build orchestration
- downstream quantity and earthwork handoff

This model does not cover:

- horizontal alignment authoring
- vertical profile authoring
- template authoring
- viewer-only layout behavior

## 3. Core Rule

`CorridorModel` is a derived engineering result system built from durable source models.

This means:

- it is not the first authoring source
- it is the main orchestration layer for station-by-station corridor realization
- its outputs must remain traceable back to source contracts
- generated corridor geometry does not become new source truth

## 4. Corridor Philosophy in v1

The corridor is not a single loft-centric object or a single mainline-only chain.

In v1, the corridor is:

- a station-evaluated system
- a corridor-network result with mainline, ramp, and junction context
- an ordered set of resolved applied sections
- a generator of surfaces, solids, quantities, and earthwork inputs
- a traceable engineering result family

This keeps the architecture aligned with the parametric 3D redesign.

## 5. Main Inputs

`CorridorModel` depends on coordinated source and service inputs:

- `AlignmentModel`
- `RampModel`
- `IntersectionModel`
- `ProfileModel`
- `SuperelevationModel`
- `AssemblyModel`
- `RegionModel`
- `DrainageModel`
- explicit override models
- `StructureModel`
- TIN sampling and terrain services

It should consume those through shared evaluation services rather than copying their logic internally.

## 6. Corridor Scope in v1

Recommended early v1 support:

- one corridor per alignment/profile policy context
- one corridor result that can reference ramp, junction, and drainage context
- sampled-station corridor evaluation
- `AppliedSectionSet` generation
- corridor surface generation
- corridor solid generation
- quantity and earthwork handoff
- scenario comparison support

Deferred or later refinements may include:

- multi-baseline corridor composition
- more advanced branching corridor relationships
- staged-construction corridor stacks

## 7. Corridor Object Families

Recommended primary object families:

- `CorridorModel`
- `CorridorNetworkContext`
- `CorridorSamplingPolicy`
- `CorridorStationSet`
- `AppliedSectionSet`
- `CorridorGeometryPackage`
- `CorridorSurfaceBuildResult`
- `CorridorSolidBuildResult`
- `CorridorDiagnostics`

## 8. CorridorModel Root

### 8.1 Purpose

`CorridorModel` is the durable identity container for one corridor result definition and its derived evaluation products.

### 8.2 Recommended root fields

- `schema_version`
- `corridor_id`
- `project_id`
- `alignment_id`
- optional `ramp_ids`
- optional `intersection_ids`
- `profile_id`
- optional `superelevation_id`
- `region_model_ref`
- optional `drainage_model_ref`
- `sampling_policy_ref`
- `station_set_ref`
- `applied_section_set_ref`
- `geometry_package_ref`
- `surface_build_refs`
- `solid_build_refs`
- `source_refs`
- `diagnostic_rows`

### 8.3 Rule

`CorridorModel` should keep references to derived result families explicitly instead of hiding them inside one oversized runtime object.

## 9. CorridorSamplingPolicy

### 9.1 Purpose

`CorridorSamplingPolicy` defines how stations are selected for corridor evaluation.

### 9.2 Recommended fields

- `sampling_policy_id`
- `station_interval`
- `key_station_policy`
- `region_boundary_policy`
- `event_station_policy`
- `transition_density_policy`
- `notes`

### 9.3 Rule

Sampling policy is part of corridor result definition and must be explicit.

It should not be left to hidden UI defaults.

## 10. CorridorStationSet

### 10.1 Purpose

`CorridorStationSet` preserves the ordered station list used for evaluation.

### 10.2 Recommended fields

- `station_set_id`
- `corridor_id`
- `station_rows`
- `station_start`
- `station_end`
- `notes`

### 10.3 Recommended station row fields

- `station_row_id`
- `station`
- `kind`
- `source_reason`
- `notes`

### 10.4 Recommended kinds

- `regular_sample`
- `key_station`
- `region_boundary_station`
- `event_station`
- `transition_station`

### 10.5 Rule

The evaluated corridor should be reproducible from the same source models plus the same station set.

## 11. AppliedSectionSet Relationship

### 11.1 Role

`AppliedSectionSet` is the central corridor result family.

### 11.2 Corridor responsibility

`CorridorModel` is responsible for orchestrating the creation and ordered ownership of:

- station-local applied sections
- section traceability
- section diagnostics
- section-level quantity fragments

### 11.3 Rule

`CorridorModel` should not replace `AppliedSectionSet`.

It should own and coordinate it.

### 11.4 CorridorNetworkContext

`CorridorNetworkContext` preserves which ramp, intersection, and drainage contexts are active for one corridor result definition.

### 11.5 Recommended fields

- `network_context_id`
- `corridor_id`
- `baseline_kind`
- `baseline_alignment_ref`
- `ramp_refs`
- `intersection_refs`
- `drainage_refs`
- `event_rows`
- `notes`

### 11.6 Rule

Network context should preserve explicit source references rather than being inferred only from transient geometry overlap.

## 12. Corridor Evaluation Pipeline

Recommended evaluation pipeline:

1. resolve corridor scope and station set
2. resolve alignment frame at station
3. resolve ramp and intersection context where relevant
4. resolve profile elevation
5. resolve superelevation state
6. resolve active region policy
7. resolve explicit overrides
8. resolve drainage rules and constraints
9. resolve structure interaction
10. sample terrain and daylight context
11. build `AppliedSection`
12. append to `AppliedSectionSet`
13. derive corridor geometry packages
14. hand off to surface, solid, quantity, and earthwork consumers

This pipeline should be implemented through reusable services, not inside the viewer.

## 13. CorridorGeometryPackage

### 13.1 Purpose

`CorridorGeometryPackage` groups geometry results derived from the evaluated corridor.

### 13.2 Recommended fields

- `geometry_package_id`
- `corridor_id`
- `centerline_rows`
- `section_link_rows`
- `skeleton_rows`
- `reference_mesh_rows`
- `diagnostic_rows`

### 13.3 Rule

This package is useful for geometry consumers, but it does not replace semantic section results.

## 14. CorridorSurfaceBuildResult

### 14.1 Purpose

This result family captures surfaces generated from corridor evaluation.

### 14.2 Typical outputs

- `DesignTIN`
- `SubgradeTIN`
- `DaylightTIN`
- corridor-derived comparison surfaces

### 14.3 Rule

Surface build results must remain traceable to corridor inputs and station results.

They should not be built as isolated post-processing with lost provenance.

## 15. CorridorSolidBuildResult

### 15.1 Purpose

This result family captures solid or layered geometry generated from corridor evaluation.

### 15.2 Typical outputs

- pavement solids
- corridor body solids
- component-based solid groups
- structure-adjacent corridor cutouts where supported

### 15.3 Rule

Solid build results are engineering derivatives and export helpers, not durable source authoring objects.

## 16. Surface and Solid Build Services

Recommended service families:

- `CorridorSurfaceService`
- `CorridorSolidService`
- `CorridorGeometryService`
- `CorridorNetworkContextService`

These services should consume `AppliedSectionSet` and normalized terrain context rather than recomputing source logic independently.

## 17. Corridor and Quantity Relationship

`CorridorModel` is a major handoff source for `QuantityModel`.

It should provide:

- station-based quantity fragments
- component identity continuity
- region-aware quantity grouping
- traceable source mappings

`QuantityModel` should reuse corridor semantics rather than reverse-engineering quantities from raw meshes.

## 18. Corridor and Earthwork Relationship

`CorridorModel` is also a major handoff source for earthwork analysis.

It should provide:

- station-based section cut/fill semantics
- corridor-derived design surfaces
- daylight and boundary context
- drainage viability context
- region and scenario traceability

`EarthworkBalanceModel` should consume normalized corridor and surface results, not ad-hoc display geometry.

## 19. Scenario and Candidate Support

The corridor subsystem should support:

- baseline corridor
- candidate corridor alternatives
- scenario-linked station sets
- comparable result families across scenarios

This is important for:

- AI-assisted alternatives
- earthwork comparison
- output comparison
- design review

## 20. Recompute Rules

Recompute should be driven by source dependency changes such as:

- alignment edits
- ramp edits
- intersection edits
- profile edits
- superelevation edits
- template edits
- region or override edits
- drainage rule edits
- structure interaction changes
- terrain updates
- sampling policy changes

The corridor subsystem should support targeted invalidation where possible, but correctness comes before partial-update cleverness.

## 21. Diagnostics

Diagnostics should be produced when:

- a station cannot resolve a valid section
- region or override resolution fails
- ramp or junction context is ambiguous
- drainage constraints cannot be satisfied
- terrain daylight evaluation is degraded
- surface or solid build fails partially
- scenario comparison loses equivalence

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `station`
- `source_ref`
- `message`
- `notes`

## 22. Identity and Provenance

Corridor objects should preserve:

- stable `corridor_id`
- source model references
- sampling-policy identity
- station-set identity
- corridor-network-context identity
- applied-section-set identity
- scenario or candidate status where applicable

This is important for:

- Viewer traceability
- section and output packaging
- earthwork comparison
- exchange and reporting diagnostics

## 23. Relationship to Viewer and 3D Review

Viewer and 3D review systems may consume corridor-derived content through:

- current station section lookup
- station-series section display
- ramp and intersection event markers
- drainage-sensitive station markers
- corridor surface overlays
- structure and earthwork highlights

But they must not become the new corridor source.

The Viewer should inspect corridor results, not mutate them directly.

## 24. Relationship to Outputs

The corridor subsystem is a main upstream source for:

- `SectionOutput`
- `SectionSheetOutput`
- context review payloads for ramps, intersections, and drainage
- `SurfaceOutput`
- `QuantityOutput`
- `EarthworkBalanceOutput`
- exchange packaging for corridor-derived surfaces and solids

Output contracts should consume corridor results through normalized schemas instead of re-reading random runtime state.

## 25. Validation Rules

Validation should check for:

- missing source references
- empty or inconsistent station sets
- inconsistent ramp or intersection references
- non-monotonic section ordering
- invalid drainage-context attachment
- mismatched scenario references
- lost component identity during build
- invalid surface or solid handoff references

Validation results should be recorded in `diagnostic_rows`.

## 26. AI and Alternative Design

AI-assisted workflows may propose:

- different sampling policies
- candidate corridors based on source alternatives
- ramp, intersection, or drainage-aware corridor variants
- corridor comparison summaries
- earthwork-aware corridor selection

But accepted changes must still flow through normalized source edits and corridor recompute.

The AI layer must not maintain a separate hidden corridor geometry world.

## 27. Recommended Minimal Schema Version

Recommended initial version:

- `CorridorModelSchemaVersion = 1`

## 28. Anti-Patterns

The following should be avoided:

- treating the corridor as one opaque loft object
- mixing source edits into corridor result objects
- recomputing quantities and earthwork from unlabeled display meshes
- burying station sampling rules in UI-only preferences
- combining section, surface, quantity, and earthwork logic into one oversized class

## 29. Summary

In v1, `CorridorModel` is the derived orchestration model for:

- station sampling
- ordered applied-section evaluation
- corridor geometry packaging
- surface and solid generation
- quantity and earthwork handoff

It should remain traceable and source-driven, so that:

- `AppliedSectionSet` stays central
- surfaces and solids preserve provenance
- quantities and earthwork reuse corridor semantics
- Viewer, outputs, and AI alternatives can operate on stable, comparable corridor results

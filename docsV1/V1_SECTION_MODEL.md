# CorridorRoad V1 Section Model

Date: 2026-04-25
Branch: `v1-dev`
Status: Draft baseline, applied section frame slice complete
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_RAMP_MODEL.md`
- `docsV1/V1_INTERSECTION_MODEL.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`

## 1. Purpose

This document defines the v1 section-domain model.

It is the authoritative reference for:

- what a section means in v1
- how section intent is authored
- how station-specific sections are evaluated
- how section overrides work
- how section data is consumed by viewers, drawings, surfaces, quantities, and exchange outputs

## 2. Why the Section Model Matters

The section system is one of the central domains of CorridorRoad v1.

It sits at the boundary between:

- alignment and profile intent
- ramp and intersection policy
- region and template policy
- terrain interaction
- drainage interaction
- structure interaction
- corridor geometry generation
- quantity and earthwork behavior
- section review and drawing deliverables

If the section model is ambiguous, the rest of the corridor architecture becomes unstable.

## 3. Section Philosophy in V1

### 3.1 Section is not just a drawing

In v1, a section is not primarily a 2D picture.

It is a parametric engineering slice of the corridor.

### 3.2 Section is not a single object

The section concept is split into four distinct layers:

- `SectionTemplate`
- `AppliedSection`
- `AppliedSectionSet`
- `SectionView`

### 3.3 Generated section geometry is not an edit source

Generated section wires, outlines, and labels are outputs.

They must not become the durable place where users store design intent.

## 4. Core Section Layers

### 4.1 SectionTemplate

This is the authored section intent.

It defines what the corridor section should be under a given policy context.

It may include:

- lanes
- shoulders
- medians
- turn lanes
- sidewalks
- green strips
- curbs
- ditches
- gutters
- swales
- berms
- pavement layers
- side-slope rules
- bench rules
- daylight defaults
- structure interaction defaults

### 4.2 AppliedSection

This is the station-specific evaluated section result.

It is generated after resolving:

- alignment frame
- ramp or intersection context when relevant
- profile elevation
- superelevation
- active region
- override rows
- drainage rules
- structure interaction rules
- terrain/daylight behavior

### 4.3 AppliedSectionSet

This is the ordered corridor-wide collection of `AppliedSection` results.

It is a result cache and engineering result family, not a primary authoring object.

### 4.4 SectionView

This is the review and output representation of section results.

It may drive:

- Cross Section Viewer
- SVG output
- DXF output
- sheet layout
- review summaries

## 5. Section Ownership Rules

### 5.1 Durable ownership

Durable section intent belongs in:

- section templates
- region rules
- explicit override models
- structure interaction rules
- superelevation and profile sources where they affect the section

### 5.2 Derived ownership

Derived section results belong in:

- applied sections
- section result caches
- section output contracts

### 5.3 Viewer ownership

The viewer owns:

- inspection state
- navigation state
- display preferences
- review notes and bookmarks

The viewer does not own:

- engineering section intent
- durable geometry overrides

## 6. SectionTemplate Structure

### 6.1 Template role

`SectionTemplate` should represent reusable cross-section design intent.

It should be reusable across:

- different station ranges
- different corridors
- different scenarios

### 6.2 Template organization

A `SectionTemplate` should be composed of semantic components rather than untyped raw polylines.

Recommended internal concepts:

- `TemplateId`
- `ComponentId`
- `ComponentKind`
- `Side`
- `Order`
- `Enabled`

### 6.3 Component categories

Recommended high-level categories:

- carriageway components
- roadside components
- pavement layers
- side-slope and bench components
- daylight-related terminal behavior
- structure-aware modifiers

Terminology note:

- `side_slope` means the engineered slope face between the design edge and the surrounding terrain.
- `daylight` means the terminal condition where that slope face ties into existing ground.
- In Korean practice, the user-facing design object is the slope face; internally some v1 contracts still use `daylight` for the terrain tie-in family.

### 6.4 Recommended component kinds

Initial practical kinds may include:

- `lane`
- `shoulder`
- `median`
- `sidewalk`
- `bike_lane`
- `green_strip`
- `curb`
- `gutter`
- `ditch`
- `berm`
- `side_slope`
- `bench`
- `pavement_layer`

### 6.5 Template constraints

Templates should support:

- left/right asymmetry
- parametric widths and slopes
- optional components
- ordering rules
- component grouping
- type-specific validation

## 7. Component Parameter Model

Each component kind may have a different parameter grammar, but the section model should keep the contract explicit.

Recommended common parameters:

- `Width`
- `SlopePct`
- `Height`
- `Offset`
- `Enabled`
- `Notes`

Recommended type-specific parameters:

- `ExtraWidth`
- `BackSlopePct`
- `Shape`
- `Thickness`
- `Material`
- `BenchWidth`
- `BenchDrop`

For `ditch` components, use `docsV1/V1_DITCH_SHAPE_CONTRACT.md` as the shape-specific parameter contract.

The first-slice implementation may use simple `width` and `slope`, but U-shaped, L-shaped, trapezoidal, rectangular, and V-shaped ditches require explicit `parameters`.

### 7.1 Parameter semantics rule

The meaning of a parameter must be tied to the component kind.

Example:

- `Height` for a curb is not the same engineering meaning as `Height` for a ditch

### 7.2 Unit rule

All section parameters must resolve through the project unit policy.

## 8. SectionTemplate and AssemblyModel Relationship

V1 should avoid splitting section logic into confusing overlapping authoring systems.

Recommended rule:

- `AssemblyModel` is the broader authoring subsystem
- `SectionTemplate` is the reusable section-intent object within that subsystem

This means `AssemblyModel` may own:

- template libraries
- subassembly definitions
- validation rules
- shared defaults

And `SectionTemplate` may own:

- a concrete section recipe
- a list of section components
- template-specific defaults

## 9. Region Interaction Model

### 9.1 Region role

Regions select which section intent applies over which station range.

### 9.2 Region responsibilities

Regions may:

- choose the active template
- choose the active assembly
- declare the primary corridor behavior for the station range
- attach additive layers such as ditch, drainage, culvert, guardrail, ramp, or intersection influence
- alter parameter values
- define transition zones
- change daylight policy
- change junction-area policy
- switch roadside treatments

### 9.3 Region and section precedence

Recommended precedence:

1. template base definition
2. region primary kind
3. region-applied policy and layers
4. explicit override rows
5. structure interaction adjustments
6. drainage interaction adjustments
7. ramp and intersection adjustments
8. terrain/daylight evaluated terminal behavior

## 10. Override Model

### 10.1 Why overrides exist

Not all section changes should require a new template.

Overrides allow local design intent without corrupting reusable templates.

### 10.2 Recommended override ownership

Overrides should live in an explicit override model, not inside generated geometry.

Suggested concept:

- `SectionOverrideModel`

### 10.3 Recommended override scopes

- current station only
- station range
- region-specific override
- event-specific override

### 10.4 Recommended override row fields

- `OverrideId`
- `TargetKind`
- `TargetId`
- `Parameter`
- `Value`
- `StartStation`
- `EndStation`
- `TransitionIn`
- `TransitionOut`
- `Enabled`
- `Notes`

### 10.5 Override limits

Overrides should not become a second template system with no structure.

The architecture should prefer:

- template for reusable intent
- region for policy over ranges
- overrides for explicit exceptions

## 11. Structure Interaction Model

Structures may affect sections without becoming the primary owner of section intent.

Typical structure-driven section impacts:

- clearance envelopes
- notch or skip behavior
- local section replacement
- approach treatment changes
- retaining or wall-adjacent treatment changes

Architectural rule:

Structure interaction modifies applied-section evaluation, but the section model should preserve traceability back to both the section source and the structure source.

## 12. Superelevation and Profile Effects

The section model must explicitly support the fact that cross-section shape is not defined by template alone.

It also depends on:

- profile elevation
- superelevation state
- crossfall transitions
- drainage constraints
- ramp tie-in context
- intersection grading context

Architectural rule:

Templates define intended cross-section composition.

Applied sections resolve the actual station-specific geometry after vertical and crossfall behavior are applied.

## 13. AppliedSection Structure

### 13.1 Role

`AppliedSection` is the most important engineering result object in the section domain.

It is the corridor section as actually resolved at one station.

### 13.2 Required inputs

An applied section should be traceable to:

- `AlignmentId`
- optional `RampId`
- optional `IntersectionId`
- `ProfileId`
- `TemplateId`
- `RegionId`
- optional `DrainageId`
- relevant `OverrideId` values
- relevant `StructureId` values
- terrain source reference where applicable

### 13.3 Required result content

An applied section should contain:

- station value
- local frame reference
- evaluated centerline/elevation reference
- semantic section points
- component span definitions
- pavement interpretation
- terrain interaction results
- drainage interaction results
- structure interaction results
- diagnostics
- quantity fragments

Current implementation note:

- `AppliedSectionFrame` records the evaluated station frame for one section
- frame fields include station, centerline `x/y`, FG `z`, tangent direction, profile grade, alignment/profile evaluation status, active alignment element, active profile segment, and active vertical curve metadata
- `AppliedSectionService` now builds this frame from `AlignmentEvaluationService` and `ProfileEvaluationService`
- `V1AppliedSectionSet` now persists enough frame coordinates for downstream corridor surface preview generation
- `AppliedSectionService` now emits first-slice `AppliedSectionPoint` rows for FG and subgrade surface points from enabled Assembly components
- `V1AppliedSectionSet` persists those point rows so Corridor Build can rebuild multi-point surface TINs without re-reading UI state
- `SectionOutputMapper` exposes frame values through `SectionSummaryRow` entries so viewers and downstream outputs can inspect the same station basis

### 13.4 Required behavioral content

Applied section data should be sufficient to support:

- corridor surface generation
- section review
- section output generation
- earthwork balance
- quantity computation

### 13.5 Surface and solid contribution rule

`AppliedSection` may contribute to both surface and solid outputs, but it should not collapse them into one geometry type.

- terrain-like station points and daylight edges contribute to `SurfaceModel` and TIN-family outputs
- pavement layers, curbs, gutters, walls, structures, and drainage components contribute to later solid or component-body outputs when thickness, material, volume, or asset identity matters
- generated wires, meshes, or solids remain derived outputs and must not become the place where section intent is edited

Current implementation note:

- `AppliedSectionService` resolves first-slice left/right design-surface widths from enabled Assembly components such as lanes, shoulders, medians, curbs, gutters, sidewalks, bike lanes, and green strips
- `AppliedSectionService` resolves first-slice `subgrade_depth` from the maximum enabled Assembly component thickness for pavement-like components
- `AppliedSectionService` resolves first-slice daylight widths and slopes from enabled `side_slope` Assembly components
- `V1AppliedSectionSet` persists those left/right surface widths with the station frame so corridor surface preview can rebuild without re-reading UI state
- `V1AppliedSectionSet` also persists `subgrade_depth` so subgrade preview can rebuild from result data
- `V1AppliedSectionSet` also persists slope-face width/slope policy so the daylight/tie-in preview can rebuild from result data
- `V1AppliedSectionSet` also persists first-slice FG and subgrade point rows for component-boundary-aware corridor surface generation
- ditch components are intentionally not folded into the finished-grade width
- `AppliedSectionService` emits first-slice `ditch_surface` point rows from enabled ditch components so Corridor Build can create a separate drainage surface
- `AppliedSectionService` derives `ditch_surface` points from shape-specific ditch parameters when `shape` is `trapezoid`, `u`, `l`, `rectangular`, or `v`
- `AppliedSectionService` emits warnings when supported ditch shapes are missing required parameters or use unsupported shape names

## 14. AppliedSectionSet Structure

### 14.1 Role

`AppliedSectionSet` is the ordered collection of station results for a corridor or analysis range.

The initial v1 `Applied Sections` command builds this result from:

- `AlignmentModel`
- `ProfileModel`
- generated `Stations`
- `AssemblyModel`
- `RegionModel`

When multiple v1 `AssemblyModel` source objects exist, the command should pass all available Assembly sources to the evaluator.

Each station should use the Assembly matching the resolved `RegionRow.assembly_ref`.

Opening the command panel should not mutate the document.

Clicking `Apply` creates or updates a `V1AppliedSectionSet` result object under:

- `04_Corridor Model / Applied Sections`

This command does not generate corridor solids.

The command panel should show a station-wise review table after refresh or apply.

The review table should expose:

- station and evaluated frame coordinates
- resolved region, assembly, and template ids
- left/right surface widths
- component count
- diagnostic status

This makes the Alignment/Profile/Assembly/Region handoff visible before Corridor Build.

Double-clicking a review-table row should create or update an `Applied Section Preview` in the 3D View.

The preview is generated from the selected `AppliedSection`.

When persisted point rows are available, the preview should show FG and subgrade section point rows plus first-slice slope-face segments.

If point rows are not available, the preview may fall back to the older resolved-width section line.

It is a review artifact, not an editable source object.

### 14.2 Responsibilities

It should support:

- station-ordered access
- key-station filtering
- region-boundary inclusion
- event-station inclusion
- output contract packaging
- result caching

### 14.3 Non-goals

It should not become:

- a hidden template editor
- a long-term source of manual geometry edits

## 15. Section Evaluation Pipeline

Recommended evaluation order for one station:

1. resolve station and local frame
2. resolve profile elevation
3. resolve superelevation or crossfall state
4. resolve active template
5. apply region policy
6. apply explicit overrides
7. apply ramp or intersection context where relevant
8. apply drainage rules and constraints
9. apply structure interaction rules
10. evaluate terrain/daylight behavior
11. finalize semantic component spans
12. derive quantity fragments and diagnostics

This pipeline should be implemented in a reusable section-evaluation service, not inside the viewer.

Current implementation status:

- [x] resolve alignment local frame through `AlignmentEvaluationService`
- [x] resolve profile elevation and grade through `ProfileEvaluationService`
- [x] store the combined basis in `AppliedSection.frame`
- [x] resolve station-specific Assembly source from Region `assembly_ref` when multiple Assembly models exist
- [x] generate first-slice FG and subgrade `AppliedSectionPoint` rows from Assembly component widths and slopes
- [x] generate first-slice ditch `AppliedSectionPoint` rows as `ditch_surface` rows instead of folding ditch into FG width
- [x] derive shape-aware ditch `ditch_surface` rows from `TemplateComponent.parameters`
- [x] report first-slice diagnostics for invalid or incomplete ditch shape parameters
- [x] persist and restore Applied Section point rows through the `V1AppliedSectionSet` result object
- [x] show a compact Applied Sections review table in the command panel
- [x] show a selected Applied Section row as a 3D review preview using point rows when available
- [ ] apply superelevation/crossfall state
- [ ] apply full terrain/daylight terminal behavior
- [ ] generate complete semantic section geometry from template parameters

## 16. Semantic Geometry Model

The section domain should preserve both geometry and semantics.

### 16.1 Why semantics matter

A plain polyline is not enough for:

- output labeling
- source tracing
- quantity mapping
- earthwork diagnostics
- editor handoff

### 16.2 Recommended semantic row concepts

Each evaluated section should preserve rows such as:

- component rows
- pavement rows
- terrain interaction rows
- structure interaction rows
- diagnostic rows

### 16.3 Geometry linkage rule

Each semantic row should be linkable to the geometry span or points it represents.

## 17. Section Identity and Traceability

Recommended identities:

- `SectionTemplateId`
- `ComponentId`
- `AppliedSectionId`
- `RegionId`
- `OverrideId`
- `StructureId`

Traceability should allow the system to answer:

- which template defined this component
- which region changed it
- which override modified it
- which structure affected it
- which terrain rule finalized the edge behavior

## 18. Section Output Relationship

Section outputs should be derived from `AppliedSection` and `AppliedSectionSet`, not from raw template data alone.

Recommended downstream consumers:

- Cross Section Viewer
- SVG section export
- DXF section export
- section sheet generation
- quantity outputs
- earthwork-balance outputs

## 19. Cross Section Viewer Relationship

The viewer should operate on section outputs and source mappings, not on source mutation.

The viewer should support:

- station selection
- component inspection
- source ownership display
- editor handoff
- same-context return

The viewer should not:

- directly edit generated section geometry
- become a hidden section authoring layer

## 20. 3D Review Relationship

3D section displays should also be derived from applied-section results.

Recommended section-related 3D displays:

- current section slice
- sparse multi-section slice display
- terrain intersection highlighting
- structure interaction highlighting

## 21. Quantity and Earthwork Relationship

The section model is one of the main sources for:

- pavement quantities
- section-based corridor quantities
- cut/fill area derivation
- station-based earthwork balance

Architectural rule:

Quantity and earthwork systems should reuse section result semantics instead of recomputing meaning from raw display geometry.

## 22. Validation Rules

The section model should support validation at multiple levels.

### 22.1 Template validation

Examples:

- missing component order
- invalid parameter values
- unsupported type combinations

### 22.2 Region/override validation

Examples:

- overlapping conflicting overrides
- invalid transition lengths
- missing target references

### 22.3 Applied-section validation

Examples:

- invalid daylight resolution
- impossible structure interaction
- missing terrain data
- geometric continuity warnings

## 23. Recommended Service Families

The section subsystem should eventually expose service boundaries such as:

- `SectionTemplateValidationService`
- `SectionResolutionService`
- `AppliedSectionService`
- `SectionOutputMappingService`
- `SectionReviewMappingService`

These names are conceptual but the separation is important.

## 24. Anti-Patterns to Avoid

Avoid the following:

- storing section intent as edited result polylines
- mixing viewer layout logic with section evaluation logic
- treating overrides as unbounded free-form patches
- losing component identity during evaluation
- reducing applied sections to unlabeled geometry too early

## 25. Follow-Up Documents

This section model document should be followed by:

1. `V1_SECTION_OUTPUT_SCHEMA.md`
2. `V1_VIEWER_PLAN.md`
3. `V1_TIN_ENGINE_PLAN.md`

## 26. Final Rule

In v1, a section is best understood as:

`authored template intent + policy resolution + station evaluation + semantic output`

If any implementation collapses these into one mutable geometry artifact, it is working against the v1 architecture.

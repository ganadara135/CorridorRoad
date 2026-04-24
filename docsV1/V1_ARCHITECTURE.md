# CorridorRoad V1 Architecture

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`

## 1. Purpose

This document translates the v1 master plan into a working architecture baseline.

Its role is to define:

- major subsystems
- object boundaries
- data-flow direction
- source/result/output separation
- preferred implementation layering

This document should be treated as the main architectural reference for all follow-up v1 design work.

## 2. Architectural Intent

CorridorRoad v1 is a parametric corridor platform, not a loose collection of FreeCAD task panels.

The architecture should make it possible to:

- build and recompute a corridor from stable source data
- build and recompute a corridor network with mainline, ramp, intersection, and drainage context from stable source data
- derive sections, surfaces, quantities, and exchange outputs from one source-of-truth model
- support TIN-first workflows
- support earthwork-balance analysis and optimization
- support strong review traceability from output back to source rule

## 3. Top-Level Architecture Shape

The recommended v1 architecture is a layered model with explicit source, evaluation, result, and output boundaries.

High-level flow:

`Authoring Sources -> Evaluation Services -> Derived Results -> Output Contracts -> UI / Exchange / Reports`

This is the architectural direction:

- authoring lives in stable source objects
- evaluation happens in reusable services
- results are cached as derived engineering objects
- outputs consume result contracts
- UI should inspect and edit source objects, not mutate generated output geometry

## 4. Core Architectural Layers

### 4.1 Layer A: Source Layer

This is the durable design-intent layer.

Typical source families:

- project
- survey inputs
- alignments
- ramps
- intersections
- profiles
- superelevation rules
- section templates
- regions
- drainage rules
- structures
- explicit overrides

Rules:

- user edits happen here
- all durable intent belongs here
- nothing in this layer should depend on viewer-only formatting

### 4.2 Layer B: Evaluation Layer

This is the computational layer that interprets source data.

Typical services:

- coordinate transforms
- TIN sampling
- alignment evaluation
- ramp tie-in evaluation
- intersection control-area evaluation
- profile evaluation
- section application
- region precedence resolution
- drainage constraint evaluation
- structure interaction resolution
- earthwork balance analysis

Rules:

- reusable
- deterministic where possible
- UI-independent
- output-format-independent

### 4.3 Layer C: Result Layer

This is the derived engineering state.

Typical result families:

- applied sections
- corridor geometry packages
- junction-area evaluation packages
- design surfaces
- earthwork-balance results
- quantity results

Rules:

- derived only from source and evaluation services
- rebuildable
- may be cached for performance
- must not become hidden authoring sources

### 4.4 Layer D: Output Layer

This layer exposes normalized contracts for consumers.

Typical output families:

- section output
- section sheet output
- plan output
- profile output
- drainage review output
- surface output
- quantity output
- exchange output
- earthwork-balance output

Rules:

- output contracts should not reimplement engineering rules
- multiple consumers should reuse the same contract

### 4.5 Layer E: Presentation Layer

This layer contains:

- task panels
- viewers
- 3D review overlays
- report viewers
- export commands

Rules:

- it should consume source/result/output contracts
- it should not own engineering truth

## 5. Major Subsystems

The v1 architecture should be organized into the following major subsystems.

### 5.1 Project Subsystem

Owns:

- project identity
- unit policy
- CRS and origin policy
- document settings
- global references

Primary object family:

- `ProjectModel`

### 5.2 Survey and Terrain Subsystem

Owns:

- survey points
- breaklines
- boundaries
- holes
- TIN generation and storage
- terrain metadata

Primary object families:

- `SurveyModel`
- `ExistingGroundTIN`
- related terrain-source objects

### 5.3 Alignment Subsystem

Owns:

- horizontal alignment geometry
- station equations
- geometric checks
- station evaluation helpers

Primary object families:

- `AlignmentModel`

### 5.4 Ramp Subsystem

Owns:

- ramp identity and topology
- merge/diverge and gore context
- tie-in references to parent corridor or junction areas
- ramp-specific criteria and diagnostics

Primary object families:

- `RampModel`

### 5.5 Intersection Subsystem

Owns:

- at-grade junction topology
- leg identity
- control-area and influence-area policy
- grading and drainage-sensitive junction context

Primary object families:

- `IntersectionModel`

### 5.6 Profile Subsystem

Owns:

- EG profile references
- FG profile design
- vertical controls
- vertical constraints

Primary object families:

- `ProfileModel`

### 5.7 Superelevation Subsystem

Owns:

- station-based crossfall behavior
- runoff logic
- cross-slope application data

Primary object families:

- `SuperelevationModel`

### 5.8 Assembly and Section Template Subsystem

Owns:

- section templates
- subassembly catalog
- pavement layers
- side-slope rules
- ditch, gutter, swale, channel, berm, curb, sidewalk, median families
- ramp and junction-related component families

Primary object families:

- `AssemblyModel`
- `SectionTemplate`
- `SubassemblyCatalog`

### 5.9 Region Subsystem

Owns:

- station-range policy selection
- template switching
- transition handling
- junction-area policy switching
- local policy overrides

Primary object families:

- `RegionModel`

### 5.10 Drainage Subsystem

Owns:

- drainage intent and policy
- collection and discharge regions
- low-point and minimum-grade review constraints
- culvert, inlet, manhole, and outfall references where practical

Primary object families:

- `DrainageModel`

### 5.11 Structure Subsystem

Owns:

- corridor-related structures
- station-aware placement
- interaction rules
- culvert and crossing references
- external or IFC-backed references

Primary object families:

- `StructureModel`

### 5.12 Corridor Evaluation Subsystem

Owns:

- station sampling
- applied-section evaluation
- ramp and intersection context evaluation
- drainage-aware evaluation context
- corridor derived geometry
- local diagnostics

Primary object families:

- `CorridorModel`
- `AppliedSection`
- `AppliedSectionSet`

### 5.13 Surface Subsystem

Owns:

- design surfaces
- subgrade surfaces
- daylight surfaces
- ramp tie-in and intersection grading surfaces
- clipping and merge logic

Primary object families:

- `SurfaceModel`
- `DesignTIN`
- `SubgradeTIN`
- `DaylightTIN`

### 5.14 Earthwork Balance Subsystem

Owns:

- cut/fill totals
- material-aware balance
- mass-haul behavior
- scenario comparison
- optimization handoff

Primary object families:

- `EarthworkBalanceModel`
- `MassHaulModel`
- `BalanceOptimizationScenario`

### 5.15 Quantity Subsystem

Owns:

- quantity accumulation
- range/region summaries
- pavement and structure-related reporting
- drainage-related reporting

Primary object families:

- `QuantityModel`

### 5.16 Exchange Subsystem

Owns:

- external import normalization
- external export packaging
- schema/versioned exchange contracts
- network-aware exchange mappings

Primary object families:

- `ExchangeModel`

### 5.17 AI Assist Subsystem

Owns:

- design alternatives
- scoring
- recommendation records
- explanation logs

Primary object families:

- `AIAssistModel`

## 6. Source of Truth Rules

### 6.1 Durable source objects

Durable design intent belongs in source objects only.

Examples:

- alignment definitions
- ramp definitions
- intersection control areas
- profile controls
- section templates
- region policies
- drainage rules
- structure rules
- override rows

### 6.2 Derived result objects

Derived objects are valid engineering results but not durable design sources.

Examples:

- applied sections
- generated surfaces
- quantity tables
- section output payloads
- mass-haul curves

### 6.3 No result editing rule

Generated output geometry must not be directly edited as a source of truth.

That rule applies to:

- section wires
- viewer geometry
- drawing geometry
- exported geometry snapshots

## 7. Section-Centric Architectural Rule

The section system is central to v1.

The architecture must support these distinctions:

- `SectionTemplate` is authored intent
- `AppliedSection` is evaluated station-specific reality
- `AppliedSectionSet` is the ordered corridor-wide section result
- `SectionView` is a derived review/output representation

This means the architecture must never blur:

- template editing
- station evaluation
- review rendering
- output export

## 8. TIN-Centric Architectural Rule

The terrain architecture must be built around triangulated surfaces.

Required capabilities:

- point ingestion
- breakline enforcement
- boundary handling
- void handling
- triangle-based sampling
- surface clipping
- surface merge
- surface comparison

The TIN layer should be a foundational service used by:

- profile sampling
- section daylight logic
- corridor surfaces
- earthwork balance
- exchange outputs

## 9. Earthwork-Balance Architectural Rule

Earthwork balance is not a side report.

It is a dedicated subsystem connected to:

- applied sections
- corridor surfaces
- quantity logic
- profile and region adjustment workflows
- output and review systems

Its architecture should support:

- project summaries
- station-range summaries
- balance-point detection
- mass-haul outputs
- scenario comparison
- optimization candidates

## 10. Recommended Data Flow

### 10.1 Baseline flow

Recommended v1 evaluation sequence:

1. project context resolves units and coordinate policy
2. survey data resolves into TIN-based terrain sources
3. alignment resolves station geometry
4. ramp and intersection context resolve network-aware control conditions
5. profile resolves vertical design intent
6. superelevation resolves crossfall behavior
7. region rules resolve applicable template and local policy
8. drainage rules resolve minimum-grade, collection, and discharge constraints
9. structure rules resolve interaction conditions
10. corridor evaluates `AppliedSection` results by station
11. surfaces derive from corridor results
12. earthwork and quantity models derive analytical results
13. output contracts package results for viewers, drawings, and exchange

### 10.2 Review flow

Recommended review sequence:

1. user opens a viewer
2. viewer consumes output contracts and result payloads
3. viewer shows source ownership
4. user jumps to a source editor
5. user edits source
6. result objects rebuild
7. output contracts refresh

## 11. Service Boundaries

The evaluation layer should be organized around services rather than bloated UI classes.

Recommended service families:

- `CoordinateService`
- `TINService`
- `AlignmentEvaluationService`
- `RampEvaluationService`
- `IntersectionEvaluationService`
- `ProfileEvaluationService`
- `SuperelevationService`
- `RegionResolutionService`
- `DrainageResolutionService`
- `StructureInteractionService`
- `AppliedSectionService`
- `CorridorSurfaceService`
- `EarthworkBalanceService`
- `QuantityService`
- `ExchangeMappingService`

These names are conceptual and can be adapted, but the service separation is important.

## 12. UI Architecture Rules

### 12.1 Dedicated editors edit source objects

Editors should target durable source objects only.

Examples:

- Alignment Editor
- Ramp Editor
- Intersection Editor
- Profile Editor
- Template Editor
- Region Editor
- Drainage Editor
- Structure Editor
- Override Manager

### 12.2 Viewers inspect results and sources

Viewers should help users:

- inspect results
- understand source ownership
- navigate to the correct editor

### 12.3 No architecture driven by task panels

Task panels are delivery mechanisms, not the architecture itself.

No key engineering rule should live only inside a task panel file.

## 13. Cross Section Viewer Architecture Role

Cross Section Viewer is a presentation consumer over v1 output contracts.

It should consume:

- section output payloads
- source ownership mappings
- ramp, intersection, and drainage context rows
- related earthwork and structure diagnostics

It should support:

- station navigation
- component inspection
- ramp and junction context review
- drainage interaction review
- source tracing
- editor handoff
- review bookmarking

It should not:

- become a hidden geometry editor
- own section evaluation logic
- own durable overrides directly

## 14. 3D Review Architecture Role

3D review displays should also be treated as output consumers.

They should consume normalized result/output contracts for:

- plan overlays
- profile overlays
- current section display
- sparse multi-section display
- ramp and intersection context overlays
- drainage risk and low-point overlays
- earthwork-balance highlighting

They must not become a backdoor source-editing channel.

## 15. Output Architecture

Outputs should sit behind explicit contracts.

Recommended contract families:

- `PlanOutput`
- `ProfileOutput`
- `ContextReviewOutput`
- `SectionOutput`
- `SectionSheetOutput`
- `SurfaceOutput`
- `QuantityOutput`
- `EarthworkBalanceOutput`
- `MassHaulOutput`
- `ExchangeOutput`

All renderers and exporters should use these normalized payloads instead of re-reading internal objects ad hoc.

## 16. Exchange Architecture

The exchange subsystem should normalize external data into internal contracts and do the reverse for export.

Priority exchange direction:

1. `LandXML`
2. `DXF`
3. `IFC`

Architectural rule:

- importers should map into source-layer or result-layer objects intentionally
- exporters should consume normalized output contracts
- format-specific edge cases should stay inside the exchange subsystem

## 17. Schema and Identity Rules

The architecture should use explicit durable identities where practical.

Recommended identity concepts:

- `ProjectId`
- `AlignmentId`
- `RampId`
- `IntersectionId`
- `ProfileId`
- `TemplateId`
- `ComponentId`
- `RegionId`
- `DrainageId`
- `StructureId`
- `OverrideId`
- `AppliedSectionId`
- `SurfaceId`
- `ScenarioId`

These identities should help with:

- source tracing
- output traceability
- scenario comparison
- regression testing

## 18. Recompute and Dependency Rules

### 18.1 Recompute should flow downward

Expected dependency direction:

`Source -> Evaluation -> Results -> Outputs -> Presentation`

### 18.2 Upstream edits must not require manual downstream surgery

When a source changes, dependent results should rebuild or mark themselves stale.

### 18.3 Stale-state visibility

The architecture should support visible stale-state reporting for:

- corridor outputs
- section outputs
- earthwork outputs
- exchange outputs

## 19. Performance Strategy

The architecture should assume large scene sizes and expensive recomputation.

Recommended architectural techniques:

- separate source from derived caches
- cache expensive derived results
- support coarse and fine evaluation modes
- avoid regenerating every output on every UI gesture
- compute dense review outputs only when requested

## 20. Testing Strategy from an Architectural View

Architecture should make it possible to test:

- services without UI
- source-to-result contracts
- result-to-output contracts
- deterministic rebuild behavior
- scenario comparison logic

The service layer should be designed for contract testing first.

## 21. Proposed Documentation Tree After This File

This architecture document should be followed by more detailed documents for:

1. section model
2. TIN engine
3. viewer plan
4. section output schema
5. exchange plan
6. AI assist plan
7. earthwork output schema

## 22. Anti-Patterns to Avoid

Avoid the following:

- putting engineering logic directly in viewer code
- editing generated section or drawing geometry as source truth
- using output format needs to distort core data contracts
- copying the v0 object graph into v1 with minor renames
- baking mass-haul, section, and quantity logic into one oversized class
- using compatibility shims as the main architecture

## 23. Implementation Guidance

Recommended implementation order:

1. define source object contracts
2. define service boundaries
3. define result object contracts
4. define output contracts
5. build UI consumers on top

This order is slower at the beginning but much safer for v1.

## 24. Final Rule

If a proposed implementation cannot clearly answer:

- what source object owns the intent
- what service evaluates the intent
- what result object stores the derived state
- what output contract exposes the result

then the implementation is not yet architecturally ready for v1.

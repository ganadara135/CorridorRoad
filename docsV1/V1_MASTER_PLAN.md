# CorridorRoad V1 Master Plan

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Audience: product planning, architecture, UI/UX, implementation, testing, release

## 1. Purpose

This document is the authoritative baseline for the CorridorRoad v1 redesign.

All new documents under `docsV1/` should align with this plan unless they explicitly record and justify a change.

Legacy v0 documents are archived under `docsV0/`. They are reference material only and must not constrain the v1 redesign.

## 2. Executive Summary

CorridorRoad v1 is a deliberate product reset.

The addon listing and repository link remain in place, but the internal architecture, data contracts, workflow model, and documentation will be redesigned around a stronger parametric 3D corridor concept.

Key product decisions:

- keep the FreeCAD Addon release path and repository link structure
- stop considering backward compatibility with the legacy `0.2.9` development line
- replace DEM-centric terrain handling with TIN-centric terrain handling
- treat the product as a corridor-network platform that must handle mainline, ramps, and intersections together
- treat cross sections as parametric corridor slices, not as editable output wires
- add drainage as a first-class design and review subsystem rather than leaving it as an implied side effect
- add earthwork-balance and mass-haul analysis as a first-class v1 subsystem
- support practical import/export through `LandXML`, `DXF`, and `IFC`
- add AI-assisted design as a recommendation and alternative-generation layer, not as opaque auto-magic
- remove the dedicated Cross Section Editor concept for v1
- strengthen Cross Section Viewer as a review, traceability, and handoff hub to dedicated editors

## 3. Product Reset Policy

### 3.1 What stays

- addon publication path
- repository URL
- branch-based addon tracking model
- FreeCAD workbench identity: `CorridorRoad`
- practical road-corridor focus

### 3.2 What resets

- object model
- internal property contracts
- result schemas
- v0 workflow assumptions
- legacy compatibility aliases as a product goal
- DEM-first terrain assumptions
- direct dependence on v0 section/corridor implementation boundaries

### 3.3 Compatibility policy

v1 does not guarantee compatibility with:

- v0.2.9 object properties
- v0 FCStd restore assumptions
- v0 CSV field contracts
- v0 internal proxy names
- v0 section result payload formats

If limited migration tooling is added later, it should be explicitly marked as a utility and not as an architectural constraint.

## 4. Vision

CorridorRoad v1 should become a parametric civil-corridor workbench for concept-to-detail roadway modeling inside FreeCAD.

The product should let users:

- build a project from survey, terrain, alignments, ramps, intersections, drainage definitions, profiles, and templates
- generate a station-aware corridor network whose geometry is derived from stable source data
- derive surfaces, solids, quantities, drainage artifacts, and drawings from the same source-of-truth model
- analyze cut/fill balance and compare mass-haul behavior across alternatives
- inspect every station section with strong traceability back to its source rule
- import and export to practical civil formats
- explore AI-generated alternatives with clear reasoning and user approval

## 5. Design Principles

### 5.1 Parametric first

Generated geometry is an output, not the primary edit source.

Every meaningful design change must originate from durable source data such as:

- alignment
- ramp definition
- intersection policy
- profile
- superelevation
- section template
- region policy
- drainage rule
- structure rule
- explicit override rows

### 5.2 Corridor as a station-evaluated system

The corridor is not a single loft-centric object or a single mainline-only chain.

It is a network of evaluated station slices and junction contexts produced from:

- geometric frame
- vertical design
- applied section template
- region-specific rules
- ramp and merge/diverge rules
- intersection-area rules
- drainage interactions
- structure interactions
- terrain interactions

### 5.3 TIN as the terrain contract

Terrain processing in v1 is based on triangulated surfaces, not rasterized DEM grids.

TIN must support:

- point input
- breaklines
- boundaries
- holes
- clipped surfaces
- merged surfaces
- station/offset sampling
- surface-to-surface comparison

### 5.4 One model, many outputs

The same source model should drive:

- 3D corridor surfaces
- 3D corridor solids
- cross sections
- junction-area and ramp review displays
- profile outputs
- drainage review outputs
- earthwork-balance and mass-haul outputs
- quantity reports
- DXF sheets
- LandXML export
- IFC export

Representation rule:

- surface outputs are for terrain-like, open TIN or mesh results such as existing ground, finished grade, subgrade, daylight, clipping, and comparison surfaces
- solid outputs are for physical component bodies with thickness, material, volume, or asset identity such as pavement layers, curbs, gutters, walls, bridge elements, culverts, pipes, and IFC/export bodies
- generated viewer meshes, surfaces, and solids are outputs; durable design intent remains in source models and replayable result contracts

### 5.5 Explanation before automation

AI support must explain:

- what it changed
- what inputs it used
- what constraints were active
- what tradeoffs it optimized
- what risks remain

### 5.6 Viewer over direct output editing

The v1 workflow rejects direct editing of generated section wires.

Instead, review tools should help users find the right source editor quickly and safely.

## 6. Core User Workflows

### 6.1 Baseline design workflow

1. Create project
2. Import survey and terrain data
3. Create or import mainline alignments, ramps, and junction references
4. Create or import profiles for mainline and ramps
5. Define superelevation, drainage constraints, and design criteria
6. Author section templates, intersection assemblies, and ramp rules
7. Assign regions, junction policies, and localized rules
8. Add structures, drainage elements, and interaction rules
9. Build corridor network
10. Review sections, intersections, drainage, surfaces, and quantities
11. Export required deliverables

### 6.2 Alternative design workflow

1. Load baseline project
2. Invoke AI assist or rule-based alternative generation
3. Generate several candidate alignment/profile/section/junction/drainage combinations
4. Compare candidates by geometry, quantity, drainage viability, constraints, and risk
5. Accept a candidate
6. Rebuild corridor network and outputs

### 6.3 Review workflow

1. Open Cross Section Viewer
2. Navigate to the station of interest
3. Select a component or rule-derived area
4. Inspect source ownership and active rules
5. Jump into the appropriate dedicated editor
6. Save changes
7. Rebuild and return to the same section context

### 6.4 Junction and drainage workflow

1. Define a mainline corridor
2. Attach ramps, merge/diverge zones, or at-grade intersection legs
3. Define drainage intent such as gutters, ditches, channels, culverts, inlets, and outfalls
4. Rebuild the corridor network
5. Review tie-ins, low points, and conflict zones
6. Adjust the owning ramp, intersection, drainage, or profile source
7. Rebuild and verify the same review context

## 7. Scope

### 7.1 In scope for v1 foundation

- project model reset
- TIN terrain workflow
- alignment and profile redesign
- ramp and junction-aware corridor modeling
- section-template system redesign
- region-driven corridor evaluation
- drainage-aware corridor evaluation
- structure interaction rules
- earthwork-balance and mass-haul analysis
- surface and quantity outputs
- Cross Section Viewer as review hub
- import/export framework for `LandXML`, `DXF`, `IFC`
- AI-assisted recommendation workflow
- new v1 documentation baseline

### 7.2 Explicitly out of scope for initial v1 foundation

- v0 backward-compatibility preservation
- direct geometry editing of generated cross sections
- attempting to preserve every v0 object name and proxy path
- large migration shim layers that distort the new architecture
- UI-first work that precedes the new domain model
- full traffic simulation or signal-timing optimization
- a full hydraulic stormwater solver replacing dedicated drainage analysis tools
- one-click automatic interchange synthesis without explicit source rules

## 8. Terrain Strategy: TIN Instead of DEM

### 8.1 Why TIN

DEM-style gridded terrain is convenient for some workflows but too limiting as the base terrain contract for a civil corridor product.

TIN is the better fit for:

- surveyed breaklines
- irregular terrain density
- realistic edge control
- corridor daylight interaction
- ramp tie-ins and intersection grading
- drainage path control and low-point review
- clipping and merging
- practical exchange with civil formats

### 8.2 TIN requirements

The terrain engine must support:

- raw point sets
- breakline enforcement
- outer boundaries
- void boundaries
- triangulation diagnostics
- surface quality checks
- triangle-based sampling
- local/world coordinate handling
- local low-point and sag-review queries where practical
- comparison against design surfaces

### 8.3 TIN object families

Recommended v1 surface object families:

- `SurveyTIN`
- `ExistingGroundTIN`
- `DesignTIN`
- `SubgradeTIN`
- `DaylightTIN`
- `VolumeSurface`

### 8.4 Terrain data sources

Inputs should be allowed from:

- CSV point sets
- DXF breaklines and boundaries
- LandXML surfaces
- future direct mesh-to-TIN conversion utilities when useful

## 9. Domain Architecture

### 9.1 Overview

The v1 domain should be split into clear subsystems:

- `ProjectModel`
- `SurveyModel`
- `AlignmentModel`
- `RampModel`
- `IntersectionModel`
- `ProfileModel`
- `SuperelevationModel`
- `AssemblyModel`
- `RegionModel`
- `DrainageModel`
- `StructureModel`
- `CorridorModel`
- `SurfaceModel`
- `EarthworkBalanceModel`
- `QuantityModel`
- `ExchangeModel`
- `AIAssistModel`

### 9.2 ProjectModel

Responsibilities:

- project identity
- unit policy
- CRS and coordinate transform policy
- local/world origin handling
- document-wide references
- data provenance
- output configuration

### 9.3 SurveyModel

Responsibilities:

- survey points
- breaklines
- boundaries
- TIN generation
- survey cleanup diagnostics
- terrain source metadata

### 9.4 AlignmentModel

Responsibilities:

- horizontal geometry
- mainline and branch alignment definitions
- station equations
- geometric criteria
- design-speed-driven checks
- alignment import/export

### 9.5 RampModel

Responsibilities:

- parent/child corridor references
- gore, taper, merge, and diverge definitions
- ramp-specific design criteria
- tie-in policy to mainline or intersection control area
- ramp alignment/profile relationships

### 9.6 IntersectionModel

Responsibilities:

- at-grade junction topology
- approach and leg definitions
- curb-return and turn-lane policies
- channelization and control-area rules
- intersection grading and tie-in context

### 9.7 ProfileModel

Responsibilities:

- existing ground profile sampling
- finished grade profile
- vertical control points
- curve/grade transitions
- ramp tie-in and drainage-minimum grade constraints
- profile constraints

### 9.8 SuperelevationModel

Responsibilities:

- station-based crossfall changes
- runoff and transition logic
- lane-group roll rules
- connection to applied sections

### 9.9 AssemblyModel

Responsibilities:

- section templates
- subassembly catalog
- pavement layers
- ditch and berm families
- gutter, swale, and channel families
- curb/median/sidewalk families
- turn-lane, auxiliary-lane, and gore-area families
- side-slope and bench rules
- structure interaction defaults

### 9.10 RegionModel

Responsibilities:

- station-range assignment
- template switching
- parameter overrides
- junction-area policy switching
- transition-in / transition-out handling
- policy precedence
- conflict diagnostics

### 9.11 DrainageModel

Responsibilities:

- gutters, ditches, swales, and channels
- culverts, inlets, manholes, and outfalls where practical
- minimum-grade and low-point review rules
- collection and discharge regions
- corridor-drainage interaction references

### 9.12 StructureModel

Responsibilities:

- corridor-adjacent structures
- station-aware placement
- clearance rules
- notch/skip/split logic
- template structures
- culvert and crossing references
- IFC-backed reference structures

### 9.13 CorridorModel

Responsibilities:

- sample stations
- evaluate applied sections
- evaluate ramp, merge/diverge, and intersection contexts
- evaluate drainage interactions with terrain and corridor geometry
- build derived surfaces and solids
- maintain station-level diagnostics
- maintain corridor-network event diagnostics
- propagate change impact

### 9.14 SurfaceModel

Responsibilities:

- create design surfaces from corridor outputs
- support ramp tie-in and intersection grading surfaces
- clip and merge surfaces
- preserve source lineage
- provide sampling APIs

### 9.15 EarthworkBalanceModel

Responsibilities:

- compute cut/fill balance from corridor and TIN-derived results
- compute mass-haul and balance-point behavior
- distinguish usable and unusable cut where data allows
- preserve drainage viability during grading comparisons where practical
- support scenario comparison and optimization handoff

### 9.16 QuantityModel

Responsibilities:

- cut/fill
- pavement quantities
- drainage quantities
- structural interaction quantities
- section-wise and range-wise summaries

### 9.17 ExchangeModel

Responsibilities:

- import normalization into v1 internal schemas
- multi-alignment, ramp, intersection, and drainage-reference exchange
- export from v1 internal schemas to target formats
- versioned exchange contracts

### 9.18 AIAssistModel

Responsibilities:

- rules-and-constraint ingestion
- candidate generation
- scoring
- junction and drainage tradeoff explanation
- explanation records
- alternative comparison payloads

## 10A. UX Reset Rule

The v1 product UX should be designed from user workflow stages, not from old v0 panel preservation.

Practical rules:

- bridge flows may exist temporarily for implementation and verification
- bridge wording must not define final user-facing actions
- `Alignment Network`, `Profiles & Superelevation`, `Templates & Assemblies`, `Intersections & Ramps`, `Structures & Drainage`, `Build Corridor Network`, `Review`, and `Exchange` should be treated as explicit product stages
- review surfaces should appear when their prerequisites exist, not earlier by hidden routing

Reference:

- [V1_UX_RESET_PLAN.md](./V1_UX_RESET_PLAN.md)

## 10. Section Strategy

### 10.1 Section concept in v1

Section is not a single monolithic object.

It is split into four layers:

- `SectionTemplate`: authored source definition
- `AppliedSection`: station-specific evaluated result
- `AppliedSectionSet`: ordered collection of station-specific results
- `SectionView`: a review and export representation

These layers must work for:

- ordinary mainline stations
- ramp stations and gore areas
- intersection influence areas
- drainage-sensitive edge conditions

### 10.2 SectionTemplate

This is the authored design intent.

It contains:

- lanes
- shoulders
- medians
- turn lanes
- sidewalks
- green strips
- ditches
- gutters
- swales
- berms
- curbs
- pavement layers
- side-slope rules
- daylight defaults

### 10.3 AppliedSection

This is the actual section at one station after all active conditions are resolved.

Inputs include:

- alignment frame
- ramp or junction context
- profile elevation
- superelevation
- active region
- localized overrides
- drainage rules
- structure effects
- terrain daylight rules

Outputs include:

- section points
- semantic component spans
- material/layer interpretation
- drainage collection and discharge hints where practical
- diagnostics
- quantity fragments

### 10.4 AppliedSectionSet

This is the corridor-wide evaluated section collection.

It is an engineering result cache and not a direct edit source.

### 10.5 SectionView

This is the graphic and report representation of a section.

It may drive:

- viewer display
- SVG export
- DXF output
- sheet layout

### 10.6 Special corridor areas

V1 should treat the following as first-class evaluated contexts instead of ad-hoc exceptions:

- ramp tie-ins and gore zones
- at-grade intersection legs and influence areas
- drainage-critical sag, low-point, and discharge zones
- localized transition areas where multiple policy families overlap

## 11. Cross Section Viewer Policy

### 11.1 Viewer stays

Cross Section Viewer is required in v1.

It is the main review surface for:

- section composition
- ramp and intersection transition behavior
- drainage feature interaction
- terrain interaction
- structure interaction
- AI recommendation validation
- output readiness checking

### 11.2 Dedicated Cross Section Editor is removed

V1 will not adopt a standalone Cross Section Editor as a primary feature.

Reason:

- direct editing of generated sections conflicts with the parametric-first model
- it creates ambiguity about source-of-truth ownership
- it increases maintenance burden without improving architectural clarity

### 11.3 Viewer becomes a review-and-handoff hub

The viewer should provide:

- source ownership inspection
- affected rule inspection
- quick jump to dedicated editors
- same-context return after save/rebuild
- change-impact hints
- review notes and bookmarks

### 11.4 Supported handoff targets

The viewer should be able to open:

- `Typical Section / Assembly` editor
- `Region` editor
- future `Ramp` editor or junction manager
- future `Drainage` editor or drainage manager
- `Structure` editor
- `Override Manager`
- future `Superelevation` editor when relevant

### 11.5 Viewer rules

- viewer remains read-only for generated geometry
- selection is allowed for inspection and navigation
- drag-editing of result geometry is not the v1 model

## 12. Editing Strategy Without a Section Editor

### 12.1 Durable edit sources

Geometry and rule changes should be authored through dedicated editors:

- `Template Editor`
- `Region Editor`
- `Ramp Editor`
- `Intersection Editor / Junction Manager`
- `Drainage Editor / Drainage Manager`
- `Override Manager`
- `Structure Editor`
- `Alignment Editor`
- `Profile Editor`
- `Superelevation Editor`

### 12.2 Viewer-assisted editing workflow

1. user reviews an applied section
2. user selects a component or problem area
3. viewer resolves the owning source
4. viewer opens the relevant editor at the relevant context
5. user edits the durable source
6. corridor rebuilds
7. viewer returns to the same station and selection context

## 13. 3D Review Display Policy

### 13.1 Purpose

V1 should support practical review-oriented drawing aids directly in the FreeCAD 3D view.

These displays are not direct edit sources.

They exist to help users:

- understand the spatial relationship between plan, profile, sections, terrain, and structures
- review corridor behavior in context
- validate AI-generated alternatives
- inspect problem stations faster

### 13.2 Core rule

All plan, profile, and section outputs shown in the 3D view are review overlays.

They must not become the durable source-of-truth geometry for design editing.

### 13.3 Priority by display type

Recommended priority:

1. current cross section in 3D
2. plan-related overlays
3. sparse full-cross-section display across the corridor
4. profile-related overlays

### 13.4 Plan display

Plan display is needed in v1.

Typical content:

- horizontal alignment
- ramp branches and gore extents
- intersection control areas
- region extents
- drainage paths and drainage structures
- structure footprints or markers
- TIN boundaries
- breaklines

Its purpose is contextual review, not replacement of a dedicated 2D plan drawing workflow.

### 13.5 Profile display

Profile display is useful but lower priority than section review.

Typical content:

- existing ground longitudinal trace
- finished grade longitudinal trace
- ramp tie-in traces
- PVI markers
- drainage-critical low-point or minimum-grade indicators
- optional grade-transition indicators

Profile review remains better suited to a dedicated profile view, but a lightweight 3D profile overlay is still valuable for context.

### 13.6 Current cross section display

Current-station cross section display is strongly recommended and should be treated as a high-value v1 feature.

Typical content:

- active section plane
- applied section wire
- semantic component coloring
- gutter, ditch, or channel interpretation
- terrain intersection
- drainage interaction
- structure interaction at the active station

This should become one of the main visual bridges between Cross Section Viewer and the 3D model space.

### 13.7 Full cross section display

Displaying many cross sections across the corridor is useful, but it must be carefully controlled for readability and performance.

Typical content:

- fence-like section slices
- section sticks or frame markers
- key-station section curtains
- ramp gore or intersection event markers
- region-boundary or event-boundary section markers
- drainage-boundary or low-point markers

Required controls:

- interval filtering
- key-station-only mode
- current-range mode such as `current +/- N`
- region-boundary-only mode
- display-density controls for large scenes

### 13.8 Non-goals

These 3D displays must not be treated as:

- direct edit geometry
- a replacement for dedicated 2D drafting outputs
- a place to manually reshape generated section wires

### 13.9 Implementation rule

3D review displays should be derived from the same v1 source model and applied-section results that drive other outputs.

They should remain synchronized with:

- alignment
- ramp and intersection policies
- profile
- section templates
- region policies
- drainage rules
- structure rules
- TIN terrain

### 13.10 UX rule

All 3D review displays must be easy to toggle, sparse by default where necessary, and safe for large-scene performance.

Default behavior should favor clarity over density.

## 14. Exchange Strategy

### 14.1 Import priorities

Priority order for early v1:

1. `LandXML`
2. `DXF`
3. `IFC`

### 14.2 LandXML import

Target support:

- alignments
- multiple related alignments for mainline and ramps
- profiles
- TIN surfaces
- drainage and feature-line references where practical
- feature lines where practical

### 14.3 DXF import

Target support:

- plan geometry references
- intersection layout references
- breaklines
- boundaries
- drainage path and structure references
- drafting references
- section annotation aids where practical

### 14.4 IFC import

Target support:

- reference structures
- culverts and drainage-adjacent structures
- clash and clearance context
- future quantity/property link opportunities

### 14.5 Export priorities

Priority order for early v1:

1. `LandXML`
2. `DXF`
3. `IFC`

### 14.6 Exchange implementation rule

Importers and exporters should not embed business logic directly into UI task panels.

They must translate between external schemas and the v1 internal exchange contracts.

## 15. AI-Assisted Design Strategy

### 15.1 AI role

AI in v1 is an assistive design layer, not an unreviewed authoring engine.

### 15.2 Phase 1 AI capability

Rules-based and scoring-based recommendations:

- alignment alternatives
- ramp alternatives
- profile alternatives
- section-policy alternatives
- intersection-policy alternatives
- drainage-policy alternatives
- corridor risk flags
- quantity-aware comparisons

### 15.3 Phase 2 AI capability

Natural-language-assisted iteration:

- "reduce embankment"
- "avoid this structure zone"
- "simplify this ramp merge"
- "improve this intersection tie-in"
- "prioritize drainage stability"
- "avoid ponding near this sag"
- "minimize retaining wall length"

### 15.4 AI output requirements

Every AI action should produce:

- inputs used
- constraints used
- assumptions made
- score summary
- warnings
- editable alternative records

### 15.5 Human approval rule

No AI-generated design state should become the accepted project state without explicit user approval.

## 16. UI Strategy

### 16.1 Primary workbench flow

Recommended top-level command flow:

1. `New Project`
2. `Import Survey / TIN`
3. `Alignment Network`
4. `Profiles & Superelevation`
5. `Templates & Assemblies`
6. `Regions`
7. `Intersections & Ramps`
8. `Structures & Drainage`
9. `Build Corridor Network`
10. `Review Sections`
11. `Earthwork Balance`
12. `Surfaces, Drainage & Quantities`
13. `Exchange`
14. `AI Assist`

### 16.2 UI priorities

- clear object ownership
- safe editing pathways
- strong traceability
- quick return to review context
- good handling of large scenes

### 16.3 UI transition policy

V1 does not treat the existing v0 UI as the final product UI.

Instead:

- existing v0 source editors may remain in service during transition
- policy-heavy source editors may remain temporarily but should be expected to refactor later
- review screens should move earlier into v1-native UI
- AI, 3D review, and output-review surfaces should be built as v1 UI rather than stretched from old task panels

Working classification:

- keep as secondary transition support only: legacy `Edit Alignment`, `Edit Profiles`, `Edit PVI`
- expose as primary v1 flow: `Alignment`, `Stations`, `Profile`
- keep now, refactor later: `Typical Section`, `Region Plan`, `Structure Editor`
- replace early with v1-native review UI: `Cross Section Viewer`, `Plan/Profile Review`, `Earthwork Balance Review`
- build as v1-only UI: `Intersections & Ramps`, `Drainage`, `3D Review`, `AI Assist`, `Output Review`, `Exchange Review`

This policy is expanded in `docsV1/V1_UX_RESET_PLAN.md`.

### 16.4 Non-goal

Do not build a UI that is attractive but detached from the new core data contracts.

## 17. Data and Schema Policy

### 17.1 Versioned contracts

Important result and exchange structures should expose explicit schema versions.

### 17.2 Stable internal semantics

Component identity and rule identity must be explicit and durable.

Recommended concepts:

- `TemplateId`
- `ComponentId`
- `RegionId`
- `RampId`
- `IntersectionId`
- `DrainageId`
- `DrainageElementId`
- `OverrideId`
- `StructureId`
- `AppliedSectionId`

### 17.3 Report rows

Machine-readable report rows are allowed, but they should reflect the new v1 domain model rather than v0 payload shortcuts.

## 18. Testing Strategy

### 18.1 Test philosophy

Test the domain contracts first, then the UI.

### 18.2 Priority test groups

- TIN generation and sampling
- alignment/profile evaluation
- ramp tie-in and merge/diverge evaluation
- intersection influence-area and control-zone evaluation
- applied-section evaluation
- region precedence and transitions
- drainage minimum-grade and low-point evaluation
- structure interaction behavior
- corridor surface build
- quantity computation
- exchange import/export round-trip where practical
- viewer source-trace/handoff behavior
- AI recommendation reproducibility where deterministic

### 18.3 Sample projects

V1 should introduce a smaller number of high-value sample projects rather than many weakly maintained samples.

## 19. Delivery Plan

### 19.1 Phase A: foundation reset

- establish docs baseline
- define v1 object model
- define corridor-network scope for mainline, ramps, intersections, and drainage
- define schema and naming rules
- freeze major product decisions

### 19.2 Phase B: terrain and geometry core

- implement TIN data model
- implement terrain sampling services
- implement junction grading and drainage-critical surface queries
- refactor alignment/profile core around v1 contracts

### 19.3 Phase C: section and corridor engine

- implement section templates
- implement region application model
- implement ramp and intersection application model
- implement drainage rule application model
- implement applied-section evaluation
- implement corridor network surface/solid generation

### 19.4 Phase D: earthwork-balance subsystem

- implement earthwork totals and balance ratio
- implement mass-haul curve and balance-point logic
- implement borrow/waste summaries
- implement drainage-aware grading checks where practical
- prepare recommendation and optimization interfaces

### 19.5 Phase E: review workflow

- rebuild Cross Section Viewer around v1 payloads
- implement source inspector and editor handoff
- expose ramp, intersection, and drainage review context
- add review notes/bookmarks

### 19.6 Phase F: exchange foundation

- LandXML import/export for alignment networks and surfaces
- DXF import/export
- IFC reference import for structures and culverts, then export as practical scope allows

### 19.7 Phase G: AI assist

- recommendation payloads
- ramp, intersection, and drainage alternatives
- alternative comparison UI
- approval workflow

### 19.8 Phase H: stabilization

- sample projects including junction and drainage cases
- regression coverage
- user documentation
- release preparation

## 20. Release and Branching Strategy

### 20.1 Branch baseline

Current v1 branch: `v1-dev`

Recommended roles:

- `v1-dev`: active redesign branch
- `main`: stable addon branch

### 20.2 Addon listing policy

The addon listing should continue to track the stable branch and repository link.

V1 redesign work should not break the listing model unless a separate release decision is made.

### 20.3 Versioning

When v1 becomes the supported release line, it should move to `1.0.0` rather than continuing the `0.x` meaning.

## 21. Documentation Governance

### 21.1 Baseline rule

This file is the baseline document for `docsV1`.

### 21.2 Derived documents

Future v1 documents should be organized as derived documents such as:

- architecture
- section model
- TIN engine plan
- viewer plan
- exchange plan
- AI assist plan
- testing plan

Each such document should reference this master plan and describe only the extra detail or the approved deviation.

### 21.3 Change rule

If a later v1 document conflicts with this master plan, one of the following must happen:

- update this file first
- or explicitly record a deviation and the approval reason

## 22. Immediate Next Documents

The next recommended v1 documents are:

1. `docsV1/V1_ARCHITECTURE.md`
2. `docsV1/V1_RAMP_MODEL.md`
3. `docsV1/V1_INTERSECTION_MODEL.md`
4. `docsV1/V1_DRAINAGE_MODEL.md`
5. `docsV1/V1_SECTION_MODEL.md`
6. `docsV1/V1_TIN_ENGINE_PLAN.md`
7. `docsV1/V1_VIEWER_PLAN.md`
8. `docsV1/V1_UX_RESET_PLAN.md`
9. `docsV1/V1_OUTPUT_STRATEGY.md`
10. `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`
11. `docsV1/V1_EXCHANGE_PLAN.md`
12. `docsV1/V1_AI_ASSIST_PLAN.md`

## 23. Immediate Next Implementation Priorities

1. freeze v1 naming and object boundaries
2. define the TIN-first terrain contracts
3. define ramp, intersection, and drainage source contracts
4. define applied-section and junction-area data contracts
5. define earthwork-balance, drainage-review, and mass-haul contracts
6. define Cross Section Viewer source-inspector and handoff behavior
7. define LandXML-first network exchange contracts

## 24. Final Direction Statement

CorridorRoad v1 is not a patch release and not a compatibility maintenance cycle.

It is a new parametric 3D corridor platform direction built inside the existing addon identity.

Every v1 implementation decision should be checked against five questions:

1. Does it strengthen the parametric source-of-truth model?
2. Does it fit a TIN-first civil workflow?
3. Does it scale from mainline to ramps, intersections, and drainage without hidden special cases?
4. Does it improve traceability between output and source rule?
5. Does it help produce practical engineering outputs and exchange data?

If the answer is mostly no, it is probably a v0 habit and should be reconsidered.

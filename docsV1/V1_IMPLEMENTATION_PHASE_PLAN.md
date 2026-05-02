# CorridorRoad V1 Implementation Phase Plan

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_TIN_ENGINE_PLAN.md`
- `docsV1/V1_VIEWER_PLAN.md`

## 1. Purpose

This document translates the v1 redesign documents into an implementation sequence that can be used as the practical build baseline.

It exists to define:

- implementation phases
- dependencies between phases
- expected deliverables
- acceptance criteria
- validation checkpoints

## 2. Core Rule

Implementation should follow the v1 architectural order:

1. source contracts
2. evaluation services
3. result models
4. output contracts
5. UI and exchange consumers

If a task skips this order without a clear reason, it should be treated as high risk.

## 3. Overall Delivery Shape

Recommended delivery progression:

- Phase 0: repo and baseline reset
- Phase 1: source-model skeleton
- Phase 2: TIN and geometry core
- Phase 3: section and corridor engine
- Phase 4: surface, quantity, and earthwork results
- Phase 5: output contract implementation
- Phase 6: viewer and review workflow
- Phase 7: exchange foundation
- Phase 8: AI assist foundation
- Phase 9: stabilization and release preparation

## 4. Cross-Phase Principles

All phases should follow these rules:

- do not implement viewer-first engineering logic
- do not let exchange needs distort core contracts
- keep source/result/output boundaries visible in code
- prefer thin UI commands over fat object classes
- add contract-focused tests before convenience features

## 5. Phase 0: Repo and Baseline Reset

### 5.1 Goal

Prepare the codebase so v1 work can proceed without legacy ambiguity.

### 5.2 Main tasks

- freeze v1 naming conventions
- confirm docs baseline under `docsV1/`
- mark legacy v0 docs as archived reference only
- identify initial v1 package/module layout
- define identity and schema version conventions in code comments or baseline modules
- classify existing v0 UI into keep-for-now, refactor-later, replace-early, and v1-only groups

### 5.3 Deliverables

- stable `docsV1` baseline
- agreed source/result/output naming pattern
- initial package structure for v1 modules

### 5.4 Acceptance criteria

- there is one documented place for each core v1 subsystem
- new code can be placed without inheriting v0 object confusion
- contributors can identify where source models, services, results, and outputs belong

## 6. Phase 1: Source-Model Skeleton

### 6.1 Goal

Create the source-layer object skeletons without full behavior yet.

### 6.2 Main tasks

- implement base identity and schema helpers
- add source-model stubs for:
- `ProjectModel`
- `AlignmentModel`
- `RampModel`
- `IntersectionModel`
- `ProfileModel`
- `SuperelevationModel`
- `AssemblyModel`
- `RegionModel`
- `DrainageModel`
- `OverrideModel`
- `StructureModel`

### 6.3 Recommended implementation rule

At this stage, focus on:

- fields
- identity
- serialization-ready shape
- dependency references

Do not overbuild UI before the contracts exist.

### 6.4 Deliverables

- source-layer model classes or objects
- common identity and schema version helpers
- baseline validation entry points

### 6.5 Acceptance criteria

- source models can be instantiated and referenced consistently
- identity fields are stable and explicit
- source models do not depend on viewer or exporter code

## 7. Phase 2: TIN and Geometry Core

### 7.1 Goal

Build the terrain and geometric evaluation core that the rest of v1 depends on.

### 7.2 Main tasks

- implement normalized TIN data objects
- implement triangulation service boundaries
- implement TIN sampling queries
- implement TIN clip, merge, and comparison helpers
- implement alignment evaluation service
- implement ramp tie-in and merge/diverge evaluation service
- implement intersection control-area evaluation service
- implement profile evaluation service
- implement superelevation service
- implement drainage constraint and low-point evaluation service

### 7.3 Critical dependency

This phase must be solid before deep corridor work begins.

If TIN sampling or station evaluation are unstable, later phases will produce misleading results.

### 7.4 Deliverables

- TIN source/result contracts in code
- station-to-XY evaluation
- station-to-elevation evaluation
- station-to-crossfall evaluation
- contract tests for geometry and TIN services

### 7.5 Acceptance criteria

- terrain sampling is reusable from one shared service layer
- alignment/profile/superelevation evaluations return deterministic results
- no consumer is forced to parse raw geometry directly

## 8. Phase 3: Section and Corridor Engine

### 8.1 Goal

Implement the core parametric corridor evaluation pipeline.

### 8.2 Main tasks

- implement section-template contracts
- implement region resolution service
- implement override resolution service
- implement ramp and intersection context resolution
- implement drainage rule resolution
- implement structure interaction resolution
- implement applied-section evaluation pipeline
- implement sampled station-set generation
- implement `AppliedSectionSet`
- implement `CorridorModel` orchestration

### 8.3 Deliverables

- section resolution service
- corridor sampling policy and station set
- applied-section result objects
- corridor geometry package baseline

### 8.4 Acceptance criteria

- one station can resolve a valid `AppliedSection`
- a station range can resolve into an ordered `AppliedSectionSet`
- source traceability is preserved through template, region, override, structure, and terrain context

## 9. Phase 4: Surface, Quantity, and Earthwork Results

### 9.1 Goal

Build the analytical result families that depend on corridor evaluation.

### 9.2 Main tasks

- implement corridor surface build services
- implement `SurfaceModel`
- implement drainage-aware analytical result hooks
- implement quantity fragment and aggregate generation
- implement `QuantityModel`
- implement earthwork balance calculations
- implement mass-haul calculations
- implement scenario comparison scaffolding for quantity and earthwork

### 9.3 Deliverables

- design, subgrade, and daylight surface results
- quantity result families
- earthwork balance and mass-haul result families
- contract tests for quantity and earthwork services

### 9.4 Acceptance criteria

- surfaces derive from corridor results with provenance
- quantities derive from labeled section/corridor semantics
- earthwork analysis derives from normalized sections and surfaces, not display geometry

## 10. Phase 5: Output Contract Implementation

### 10.1 Goal

Map internal results into normalized output payloads before rebuilding major UI consumers.

### 10.2 Main tasks

- implement `SectionOutput` mapping
- implement `PlanOutput` and `ProfileOutput` mapping
- implement junction/drainage review payload support where practical
- implement `SurfaceOutput` mapping
- implement `QuantityOutput` mapping
- implement `EarthworkBalanceOutput` and `MassHaulOutput` mapping
- add output validation helpers

### 10.3 Deliverables

- output-mapping services
- reusable output payload factories
- output contract tests

### 10.4 Acceptance criteria

- viewers and exporters can consume outputs without re-reading core models ad hoc
- output payloads preserve source/result identity
- output contracts are versioned and testable

## 11. Phase 6: Viewer and Review Workflow

### 11.1 Goal

Rebuild review UX around normalized outputs and source tracing.

### 11.2 Main tasks

- rebuild Cross Section Viewer on top of `SectionOutput`
- add Source Inspector
- add editor handoff links
- add same-context return behavior
- expose ramp, intersection, and drainage review context
- add review notes and bookmarks
- implement 3D review overlays from output contracts
- promote v1 review screens ahead of full source-editor replacement where practical

### 11.3 Deliverables

- read-only Viewer with source traceability
- 3D review overlay baseline
- review navigation workflow

### 11.4 Acceptance criteria

- viewers no longer own engineering logic
- source tracing works for template, region, override, structure, and terrain context
- review displays can refresh from rebuilt outputs consistently
- the project clearly distinguishes transitional source editors from v1-native review UI

## 12. Phase 7: Exchange Foundation

### 12.1 Goal

Implement the exchange paths on top of normalized source/result/output contracts.

### 12.2 Main tasks

- implement `LandXML` alignment/profile import with network-aware mapping where practical
- implement `LandXML` TIN import/export
- implement `DXF` boundary, breakline, drainage-reference, and drawing export support
- implement `IFC` reference-structure and culvert import baseline
- implement exchange diagnostics and degraded-exchange reporting

### 12.3 Deliverables

- first working `LandXML` round-trip path for supported scope
- DXF export from normalized outputs
- IFC reference import baseline

### 12.4 Acceptance criteria

- import normalizes into intended source/result families
- export consumes output contracts and exchange packages
- unsupported data is diagnosed explicitly

## 13. Phase 8: AI Assist Foundation

### 13.1 Goal

Add AI-assisted recommendation and comparison features on top of stable contracts.

### 13.2 Main tasks

- implement AI recommendation payloads
- implement candidate and scenario comparison pipeline
- expose approval workflow hooks
- connect AI outputs to Viewer and review flows
- connect AI to ramp, intersection, and drainage alternatives where practical
- connect AI to earthwork-aware comparisons first

### 13.3 Deliverables

- recommendation payload support
- candidate comparison support
- explainable AI review flow

### 13.4 Acceptance criteria

- AI never becomes a hidden source-of-truth layer
- accepted AI changes still flow through source edits and recompute
- recommendation outputs remain explainable and traceable

## 14. Phase 9: Stabilization and Release Preparation

### 14.1 Goal

Make the v1 baseline safe to test, demo, and ship.

### 14.2 Main tasks

- add regression coverage for contracts and services
- create sample projects
- improve diagnostics and stale-state visibility
- write user-facing v1 documentation
- verify Addon packaging and release metadata

### 14.3 Deliverables

- sample v1 projects
- regression test suite baseline
- packaging and release checklist

### 14.4 Acceptance criteria

- key workflows are reproducible on sample data
- major outputs validate consistently
- release package is understandable and supportable

## 15. Recommended Near-Term Sprint Order

Recommended immediate implementation order:

1. source-model skeleton modules
2. TIN data + sampling services
3. alignment/profile/superelevation services
4. ramp/intersection/drainage source skeletons
5. region/override/structure resolution services
6. applied-section evaluation
7. corridor station-set and orchestration
8. surface build
9. quantity and earthwork services
10. output-mapping services
11. viewer rebuild

## 16. Minimum Vertical Slice

Before broad feature expansion, the team should complete one end-to-end vertical slice:

1. one alignment
2. one ramp or intersection context
3. one profile
4. one section template
5. one region
6. one drainage rule
7. one sampled station range
8. one `AppliedSectionSet`
9. one design surface
10. one quantity output
11. one earthwork output
12. one read-only viewer path

This slice should be prioritized over many half-finished panels.

## 17. Code Organization Guidance

Recommended package-level grouping:

- `models/source/`
- `services/evaluation/`
- `models/result/`
- `models/output/`
- `ui/editors/`
- `ui/viewers/`
- `exchange/`
- `tests/contracts/`

The exact folder names may vary, but the layer boundaries should remain visible in the codebase.

## 18. Testing Guidance by Phase

Recommended focus:

- Phase 1: model identity and schema tests
- Phase 2: geometry and TIN contract tests
- Phase 3: applied-section and corridor contract tests
- Phase 4: surface, quantity, and earthwork analytical tests
- Phase 5: output schema tests
- Phase 6+: UI smoke tests on top of contract-tested backends

## 19. Major Risks

Key risks to watch:

- slipping back into v0-style mixed object ownership
- building viewer logic before result contracts are stable
- encoding business logic inside export paths
- allowing overrides to absorb region or template responsibilities
- computing quantities or earthwork from display geometry

## 20. Stop Conditions

Implementation should pause and realign if:

- a new feature cannot identify its source owner
- multiple consumers implement their own station logic
- result objects start receiving direct user edits
- output payloads disagree with analytical results
- exchange code starts owning engineering truth

## 21. Done Definition for V1 Baseline

The v1 baseline should be considered implementation-ready when:

- source models exist and are stable
- evaluation services are shared and testable
- corridor results are reproducible
- output contracts are versioned and reused
- Viewer consumes outputs instead of owning logic
- `LandXML`, `DXF`, and `IFC` entry paths follow the architecture
- quantity and earthwork are analyzable from normalized contracts

## 22. Summary

The recommended implementation order for v1 is:

- build the source contracts first
- then shared evaluation services
- then corridor and analytical result models
- then output contracts
- then viewer, exchange, and AI consumers

This is the safest path to keep CorridorRoad v1 aligned with its parametric 3D, TIN-first, source-traceable architecture.

# CorridorRoad V1 Earthwork Implementation Plan

Date: 2026-05-02
Status: Draft implementation plan
Scope: v1-native earthwork analysis pipeline

Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`
- `docsV1/V1_EARTHWORK_OUTPUT_SCHEMA.md`
- `docsV1/V1_EARTHWORK_REVIEW_ROLE_AND_SCOPE.md`
- `docsV1/V1_APPLIED_SECTIONS_PERFORMANCE_PLAN.md`
- `docsV1/V1_BUILD_CORRIDOR_PERFORMANCE_PLAN.md`
- `docsV1/V1_TIN_SAMPLING_CONTRACT.md`

## 1. Purpose

This plan defines how CorridorRoad v1 should implement earthwork analysis from accepted v1 corridor results.

The goal is to calculate cut, fill, balance, and mass-haul results from v1 source/result/output contracts rather than from temporary viewer geometry.

## 2. Scope

This plan includes:

- v1-native section cut/fill area generation
- volume generation from consecutive station area rows
- earthwork balance row generation
- mass-haul row generation
- Earthwork Review consumption of real v1 outputs
- diagnostics for missing or partial earthwork inputs

This plan excludes:

- v0 connection paths
- legacy CutFillCalc dependency
- v0 import behavior
- direct editing of generated section or surface geometry
- full automatic profile optimization
- borrow/waste site authoring
- final drawing-sheet production

## 3. Core Rule

Earthwork analysis must follow the v1 source -> evaluation -> result -> output -> presentation layering.

Durable design intent remains in source models.

Earthwork calculation consumes accepted v1 corridor results and emits normalized result/output models.

Earthwork Review displays and hands off those outputs. It must not become the place where engineering meaning is recomputed.

## 4. Current State

Existing useful parts:

- `SectionEarthworkAreaService` computes `cut_area` and `fill_area` from design and existing-ground section polylines.
- `SectionEarthworkVolumeService` converts station area rows to cut/fill volume fragments using the average-end-area method.
- `QuantityBuildService` can consume station quantity fragments and create grouped quantity output.
- `EarthworkBalanceService` can consume quantity volume fragments and create station balance rows.
- `MassHaulService` can create cumulative mass curve rows and balance points.
- `Earthwork Review` can display balance and mass-haul results and hand off station context to other review screens.

Main gap:

- there is no complete v1-native pipeline that reliably creates station-level `cut_area` and `fill_area` rows from real Applied Sections and EG terrain.

## 5. Target Data Flow

The target flow is:

1. `AppliedSectionSet`
2. station design section polyline
3. station existing-ground section polyline from accepted EG TIN
4. `SectionEarthworkAreaService`
5. station-level `cut_area` and `fill_area` fragments
6. `SectionEarthworkVolumeService`
7. station-window `cut` and `fill` volume fragments
8. `QuantityModel`
9. `EarthworkBalanceModel`
10. `MassHaulModel`
11. `EarthworkBalanceOutput` and `MassHaulOutput`
12. `Earthwork Review`

## 6. Input Contracts

Required inputs:

- accepted `AppliedSectionSet`
- accepted existing-ground TIN
- station values from the active corridor sampling policy
- section design polyline rows or equivalent applied-section point rows

High-value inputs:

- accepted corridor design surface
- daylight surface rows
- subgrade surface rows
- region refs
- assembly refs
- structure exclusion or interaction refs
- material usability settings

## 7. Output Contracts

Required result/output models:

- station-level area quantity fragments
- station-window volume quantity fragments
- `QuantityModel`
- `EarthworkBalanceModel`
- `MassHaulModel`
- `EarthworkBalanceOutput`
- `MassHaulOutput`

Diagnostics should be emitted when:

- no Applied Sections result is available
- no EG TIN is available
- a station has no design section polyline
- a station has no EG section polyline
- design and EG polylines do not overlap
- fewer than two valid area stations exist
- a station window has a missing start or end area
- generated outputs are stale relative to source/result refs

## 8. Implementation Order

### Step EW1 - Document v1 Earthwork Pipeline

Create this implementation plan and register it in `docsV1/README.md`.

Status: completed on 2026-05-02.

Acceptance:

- the implementation order is explicit
- v0 connection is excluded
- required inputs and diagnostics are listed

### Step EW2 - Earthwork Analysis Service

Add a v1 builder/evaluation service that creates station-level earthwork area fragments from accepted v1 results.

Status: completed on 2026-05-02.

Proposed service:

- `freecad/Corridor_Road/v1/services/builders/earthwork_analysis_service.py`

Responsibilities:

- resolve station rows from `AppliedSectionSet`
- build or read design section polylines
- build EG section polylines from the accepted EG TIN
- call `SectionEarthworkAreaService`
- return area fragments and diagnostics

Acceptance:

- one station with valid design and EG polylines creates `cut_area` or `fill_area`
- missing EG returns diagnostics, not silent zero quantities
- no viewer code owns the calculation

### Step EW3 - Quantity Pipeline Integration

Integrate generated area fragments into the existing quantity pipeline.

Status: completed on 2026-05-02.

Options:

- extend `QuantityBuildRequest` with optional earthwork area fragments
- or create an earthwork-specific quantity build request that wraps `QuantityBuildService`

Preferred first implementation:

- keep `QuantityBuildService` general
- pass generated earthwork fragments into a dedicated earthwork builder path
- let `SectionEarthworkVolumeService` convert area fragments to volume fragments

Implemented first path:

- `EarthworkQuantityService` builds an earthwork-scoped `QuantityModel`.
- station `cut_area` and `fill_area` fragments are preserved.
- `SectionEarthworkVolumeService` adds station-window `cut` and `fill` volume fragments.
- the quantity model keeps refs to Corridor, Applied Sections, and Earthwork Analysis.

Acceptance:

- generated `cut_area` and `fill_area` fragments become `cut` and `fill` volume fragments
- volume rows keep station start and station end
- quantity output remains traceable to Applied Sections and EG TIN

### Step EW4 - Earthwork Balance and Mass-Haul Builder

Build a document-level v1 earthwork report from the generated quantity model.

Status: completed on 2026-05-02.

Responsibilities:

- create `EarthworkBalanceModel`
- create `MassHaulModel`
- map both models to normalized outputs
- preserve source/result refs

Implemented first path:

- `EarthworkReportService` runs analysis, quantity, balance, mass-haul, and output mapping.
- `QuantityOutput`, `EarthworkBalanceOutput`, and `MassHaulOutput` are produced from one v1 pipeline.
- analysis and quantity diagnostics are propagated to balance and mass-haul outputs.

Acceptance:

- total cut and fill come from generated station-window volume rows
- mass-haul curve uses generated balance rows
- balance points are available where cumulative mass crosses zero

### Step EW5 - Earthwork Command Integration

Update the Earthwork command to prefer the v1-native analysis path.

Status: completed on 2026-05-02.

Behavior:

- resolve active Applied Sections
- resolve active EG TIN
- build v1 earthwork outputs
- open Earthwork Review with real output rows
- show diagnostics if required inputs are missing

Implemented first path:

- `build_document_earthwork_report()` now delegates to the v1-native report path.
- the command resolves `V1AppliedSectionSet` through the v1 object contract.
- the command resolves EG TIN through the same corridor EG TIN resolver used by v1 terrain handling.
- `EarthworkReportService` builds the report payload consumed by Earthwork Review.
- missing EG remains visible as report/output diagnostics instead of being converted to zero earthwork silently.

Acceptance:

- the normal command path does not depend on legacy CutFillCalc
- demo output is not used when real v1 inputs are available
- missing inputs are visible in the review screen

### Step EW6 - Review UI Diagnostics

Improve Earthwork Review empty and partial-result states.

Status: completed on 2026-05-02.

Required messages:

- Applied Sections missing
- EG TIN missing
- no valid section area rows
- no station-window volume rows
- stale earthwork output

Implemented first path:

- Earthwork Review summary includes diagnostic count and diagnostic kinds.
- Earthwork Review includes a Diagnostics table.
- missing EG, missing area rows, missing volume rows, and missing balance rows produce visible empty-state guidance.
- diagnostics are deduplicated across report, quantity output, earthwork output, and mass-haul output.

Acceptance:

- users can understand why no cut/fill result was produced
- handoff to Cross Section Viewer remains available when a station context exists
- Earthwork Review remains read-only

### Step EW7 - Contract Tests

Add focused tests for the new pipeline.

Status: completed on 2026-05-02.

Required tests:

- section area fragments from design and EG polylines
- area-to-volume conversion through generated fragments
- EarthworkBalanceModel from generated volume fragments
- MassHaulModel from generated balance rows
- missing EG diagnostic
- command/report builder uses real v1 output when inputs exist

Implemented coverage:

- `test_earthwork_analysis_service.py` covers section area fragments and missing EG/design diagnostics.
- `test_earthwork_quantity_service.py` covers area-to-volume conversion, volume diagnostics, and balance service handoff.
- `test_earthwork_report_service.py` covers analysis -> quantity -> balance -> mass-haul -> output mapping.
- `test_earthwork_command_v1_report.py` covers command/report use of real v1 output instead of demo ids.
- `test_earthwork_review_handoff.py` covers review diagnostics display and handoff context.

Acceptance:

- tests validate the source -> evaluation -> result -> output path
- tests do not require v0 objects
- tests avoid UI-only validation

### Step EW8 - Real Document QA

Validate with an active corridor document.

Manual checks:

- run Applied Sections
- run Build Corridor if needed for accepted surface context
- run Earthwork Review
- confirm station-window cut/fill totals
- confirm mass-haul curve rows
- jump from Earthwork Review to Cross Section Viewer
- confirm local section geometry explains the cut/fill row

Acceptance:

- Earthwork Review opens on real v1 results
- total cut/fill is not demo data
- missing-input diagnostics are understandable

## 9. Non-Goals

This implementation pass does not attempt to:

- optimize FG profile automatically
- choose borrow or waste sites
- classify material usability beyond an initial default ratio
- generate final construction drawings
- merge v0 cut/fill behavior into v1
- use viewer display meshes as the source of earthwork truth

## 10. Acceptance Criteria for First Usable Earthwork

The first usable v1 Earthwork implementation is complete when:

- accepted Applied Sections and EG TIN can produce station-level cut/fill areas
- consecutive valid stations can produce cut/fill volumes
- Earthwork Balance and Mass Haul are generated from those volumes
- Earthwork Review displays real v1 results
- missing input states are visible and actionable
- no v0 connection is required for ordinary Earthwork Review

## 11. Final Rule

Earthwork should be treated as a v1 analytical pipeline.

The calculation source is accepted v1 corridor and terrain result data.

The review screen explains the result; it does not invent the result.

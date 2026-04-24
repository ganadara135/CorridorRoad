# CorridorRoad V1 TIN Engine Plan

Date: 2026-04-22
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`

## 1. Purpose

This document defines the v1 terrain-engine direction around TIN.

It exists to fix the architectural boundary for:

- terrain source ingestion
- triangulation
- surface storage
- sampling
- clipping and merging
- comparison
- downstream reuse in sections, corridor surfaces, earthwork, and exchange outputs

## 2. Core Direction

V1 terrain processing is TIN-first.

This means:

- TIN is the primary terrain contract
- DEM-style gridded workflows are not the base architecture
- terrain behavior should be driven by triangulated surfaces and related source constraints

## 3. Why TIN Is the Base Contract

TIN is the better fit for v1 because it supports:

- irregularly spaced survey data
- surveyed breaklines
- explicit boundaries
- holes and voids
- practical civil exchange formats
- daylight and section-edge interaction
- earthwork and surface comparison workflows

## 4. TIN Engine Responsibilities

The TIN engine should provide reusable services for:

- point ingestion
- breakline ingestion
- boundary ingestion
- triangulation
- quality checks
- triangle-based spatial indexing
- point and line sampling
- clipping
- merging
- comparison support

The TIN engine should not become:

- a UI-centric import wizard
- a hidden mesh-only fallback layer
- a one-off utility only for one command

## 5. Main TIN Object Families

Recommended object families:

- `SurveyTIN`
- `ExistingGroundTIN`
- `DesignTIN`
- `SubgradeTIN`
- `DaylightTIN`
- `VolumeSurface`

Supporting source families:

- `SurveyPointSet`
- `BreaklineSet`
- `BoundarySet`
- `VoidBoundarySet`

## 6. Source Inputs

### 6.1 Required practical input types

The engine should support these source inputs:

- point sets
- breaklines
- outer boundaries
- void boundaries

### 6.2 Expected external input channels

Primary import channels:

- CSV point data
- DXF lines and polylines for breaklines and boundaries
- LandXML surfaces and related entities

Secondary future utilities:

- mesh-to-TIN conversion helpers
- IFC-derived reference geometry where practical

## 7. TIN Data Model

### 7.1 Required conceptual parts

A TIN surface should preserve:

- `SurfaceId`
- surface kind
- source provenance
- vertices
- faces
- breakline references
- boundary references
- void references
- quality metadata
- coordinate context

### 7.2 Coordinate rule

Every TIN must carry explicit coordinate interpretation.

Minimum requirement:

- local/world context
- CRS context through project settings where available

### 7.3 Provenance rule

The engine should preserve enough metadata to answer:

- where this surface came from
- which sources contributed to it
- what generation method was used
- when triangulation or merge logic changed the result

## 8. Triangulation Model

### 8.1 Baseline triangulation behavior

The engine must support triangulation from:

- points alone
- points plus breaklines
- points plus breaklines plus outer boundary
- points plus void boundaries

### 8.2 Breakline enforcement

Breaklines are not decorative references.

They should affect triangulation topology where the algorithm supports it.

### 8.3 Boundary enforcement

Outer boundaries should constrain the valid surface extent.

Void boundaries should cut holes out of the valid surface domain.

### 8.4 Validation after triangulation

The engine should detect and report:

- insufficient points
- degenerate triangles
- duplicate or near-duplicate points
- malformed boundaries
- breakline conflicts
- poor triangulation coverage

## 9. Quality and Diagnostics

The TIN engine should produce quality diagnostics that can be reused by:

- terrain import UIs
- section daylight workflows
- earthwork analysis
- exchange exports

Recommended diagnostic families:

- point count
- triangle count
- boundary validity
- breakline validity
- hole/void consistency
- degenerate triangle count
- sparse coverage warnings
- sampling confidence notes

## 10. Sampling Services

TIN sampling is one of the most important reusable services in v1.

### 10.1 Required sampling modes

The engine should support:

- elevation at XY
- station/offset to elevation through alignment context
- line sampling
- corridor-edge daylight sampling
- surface-to-surface delta support

### 10.2 Sampling consumers

Sampling must be reusable by:

- profile generation
- applied section evaluation
- daylight resolution
- earthwork balance
- quantity analysis
- review displays

### 10.3 Sampling rule

Sampling should be triangle-based and should not depend on a DEM grid approximation.

## 11. Clipping and Merge Services

### 11.1 Clipping

The engine should support clipping a TIN by:

- outer polygon
- station-range-derived corridor zone
- review or export range

### 11.2 Merging

The engine should support merging surfaces where practical.

Important use cases:

- existing ground plus design modification areas
- corridor-generated design surface composition
- sub-surface or daylight surface generation

### 11.3 Merge rule

Merging should preserve provenance and not silently destroy source identity.

## 12. Surface Comparison Support

The TIN engine should provide the geometric basis for:

- design vs existing comparison
- cut/fill area and volume derivation
- delta statistics
- volume-surface creation

This is foundational for `EarthworkBalanceModel`.

## 13. Relationship to Applied Sections

The TIN engine directly supports the section model.

It is needed for:

- terrain intersection in `AppliedSection`
- daylight resolution
- station-specific edge conditions
- structure/terrain interaction context

Architectural rule:

Section evaluation should consume TIN sampling services rather than embedding its own terrain logic.

## 14. Relationship to Corridor Surfaces

TIN outputs are not only survey inputs.

They are also corridor-derived outputs.

Key uses:

- `FG_TIN`
- `SubgradeTIN`
- `DaylightTIN`
- temporary clipped or comparison surfaces

Architectural rule:

Corridor-derived surfaces should use the same core TIN contracts as imported surfaces wherever possible.

## 15. Relationship to Earthwork Balance

The earthwork balance subsystem depends on the TIN engine for:

- existing-ground reference
- design-surface reference
- section-edge behavior
- volume comparison support
- borrow/waste confidence context

Without a stable TIN engine, earthwork analysis will remain fragile.

## 16. Relationship to Exchange

The TIN engine should map cleanly to exchange workflows.

### 16.1 LandXML

LandXML is a priority exchange target because it commonly carries TIN surfaces.

The TIN engine should therefore preserve enough structure and metadata for reliable LandXML export and import normalization.

### 16.2 DXF

DXF is useful for boundary and breakline ingestion, and for some drawing-oriented exports.

### 16.3 IFC

IFC is not the main terrain exchange path, but TIN-derived outputs may still inform reference geometry workflows.

## 17. Recommended Service Families

Recommended conceptual service boundaries:

- `TINImportService`
- `TINTriangulationService`
- `TINValidationService`
- `TINSamplingService`
- `TINClipService`
- `TINMergeService`
- `TINComparisonService`
- `TINExportMappingService`

These names are conceptual; the important part is separation of responsibilities.

## 18. Performance Strategy

TIN operations can become expensive, so the engine should support:

- cached spatial indices
- lazy rebuild of derived structures
- range-limited sampling
- preview vs final quality modes where practical
- selective clipping rather than full-surface duplication

Performance work should not compromise correctness of the core contracts.

## 19. Validation Rules

The engine should validate both inputs and results.

### 19.1 Input validation

Examples:

- invalid point rows
- duplicate points
- malformed polylines
- non-closed boundaries where closure is required

### 19.2 Surface validation

Examples:

- degenerate triangles
- outside-boundary leakage
- void-boundary inconsistencies
- insufficient local density

### 19.3 Sampling validation

Examples:

- out-of-range sampling
- no triangle hit
- ambiguous intersection or low confidence

## 20. Anti-Patterns to Avoid

Avoid the following:

- rebuilding a DEM grid and treating it as the real terrain model
- putting triangulation logic directly in UI task panels
- creating separate ad-hoc samplers for sections, profiles, and cut/fill
- discarding breakline and boundary semantics too early
- exporting surfaces from display meshes rather than normalized TIN contracts

## 21. Recommended Follow-Up Documents

This TIN plan should be followed by:

1. `V1_TIN_DATA_SCHEMA.md`
2. `V1_TIN_SAMPLING_CONTRACT.md`
3. `V1_SECTION_OUTPUT_SCHEMA.md`
4. `V1_EXCHANGE_PLAN.md`

## 22. Final Rule

In v1, TIN is not just a terrain import feature.

It is a foundational engine shared by sections, corridor surfaces, earthwork balance, review displays, and exchange outputs.

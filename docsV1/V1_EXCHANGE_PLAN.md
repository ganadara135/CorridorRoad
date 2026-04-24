# CorridorRoad V1 Exchange Plan

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_RAMP_MODEL.md`
- `docsV1/V1_INTERSECTION_MODEL.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_TIN_ENGINE_PLAN.md`
- `docsV1/V1_SECTION_OUTPUT_SCHEMA.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`

## 1. Purpose

This document defines the v1 exchange strategy for external formats.

Its role is to specify:

- which formats matter first
- what they are used for
- how import should normalize into v1 contracts
- how export should consume v1 output contracts
- how to prevent format-specific logic from polluting the core architecture

## 2. Core Direction

Exchange in v1 is a dedicated subsystem, not a side feature attached to random task panels.

The architectural rule is:

- imports normalize external data into v1 source/result models
- exports package normalized v1 outputs into external schemas

The exchange layer should not become the place where engineering meaning is invented.

## 3. Priority Order

Recommended format priority:

1. `LandXML`
2. `DXF`
3. `IFC`

This priority reflects the strongest fit with v1 goals:

- alignments
- ramp and junction references
- profiles
- TIN surfaces
- drainage references where practical
- section-related outputs
- practical civil interoperability

## 4. Exchange Philosophy

### 4.1 Normalize on import

Imported files should be translated into internal contracts rather than kept as loosely interpreted foreign objects everywhere.

### 4.2 Package on export

Exports should start from v1 output contracts and source/result identities, not from UI widgets or display geometry.

### 4.3 Preserve provenance

The system should preserve what was imported, from where, and how it was mapped.

### 4.4 Keep core architecture clean

Format-specific quirks should remain inside the exchange subsystem whenever possible.

## 5. Exchange Subsystem Role

The exchange subsystem should own:

- external file readers and writers
- import normalization
- export packaging
- schema version handling
- format-specific mapping rules
- exchange diagnostics

It should not own:

- corridor engineering truth
- section evaluation logic
- terrain sampling logic
- viewer-only display behavior

## 6. Import vs Export Separation

### 6.1 Import side

Import should focus on creating or updating:

- source-layer objects
- selected result-layer objects when that is the proper target

### 6.2 Export side

Export should focus on reading:

- source identities
- result objects
- normalized output contracts

### 6.3 Why separation matters

Import and export should not mirror each other blindly.

Some formats are better suited for:

- source authoring exchange
- result delivery exchange
- drawing exchange
- reference-only coordination

## 7. LandXML Strategy

### 7.1 Why LandXML comes first

LandXML aligns best with the v1 product direction because it commonly carries:

- horizontal alignments
- related alignments for ramps and connectors
- profiles
- TIN surfaces
- practical civil exchange data

### 7.2 Priority import targets

Recommended early LandXML import targets:

- alignment geometry
- ramp-related alignment geometry where explicit or mappable
- profile geometry
- TIN surfaces
- junction-related feature references where practical
- drainage and feature-line references where practical
- feature lines where practical

### 7.3 Priority export targets

Recommended early LandXML export targets:

- alignment output
- profile output
- TIN surface output

### 7.4 LandXML architectural rule

LandXML import should map into:

- `AlignmentModel`
- `RampModel` when corridor role can be determined
- `ProfileModel`
- `IntersectionModel` as mapped references where practical
- `DrainageModel` as mapped references where practical
- TIN object families

LandXML export should read from:

- normalized alignment contracts
- normalized profile contracts
- normalized surface contracts

## 8. DXF Strategy

### 8.1 Why DXF matters

DXF remains important for:

- plan references
- intersection layout references
- breakline and boundary import
- drainage path and structure references
- drawing deliverables
- section and sheet exchange

### 8.2 Priority import targets

Recommended early DXF import targets:

- breaklines
- outer boundaries
- void boundaries where practical
- plan reference geometry

### 8.3 Priority export targets

Recommended early DXF export targets:

- section outputs
- section sheets
- plan outputs
- profile outputs

### 8.4 DXF architectural rule

DXF import should not be treated as if every imported entity is engineering truth automatically.

It should map intentionally to:

- reference geometry
- breakline sources
- boundary sources

DXF export should consume normalized drawing/output contracts rather than ad-hoc scene geometry.

## 9. IFC Strategy

### 9.1 Why IFC is third

IFC is valuable but should not drive the first v1 exchange architecture.

Its best early use is:

- reference structure import
- culvert and drainage-adjacent structure import
- corridor and structure export once the internal solid/result model is stable

### 9.2 Priority import targets

Recommended early IFC import targets:

- structure references
- coordination geometry
- clearance context

### 9.3 Priority export targets

Recommended early IFC export targets:

- corridor-related solids when available
- structure-related outputs
- practical property data where mapping is reliable

### 9.4 IFC architectural rule

IFC support should not distort the core v1 model.

It should layer on top of stable source/result/output contracts.

## 10. Import Mapping Targets

Recommended import mapping targets:

### 10.1 Source-layer mappings

- alignments -> `AlignmentModel`
- ramp-related alignments and tie-ins -> `RampModel` where mappable
- profiles -> `ProfileModel`
- junction control references -> `IntersectionModel` where mappable
- drainage references -> `DrainageModel` where mappable
- breaklines -> `BreaklineSet`
- boundaries -> `BoundarySet`
- structure references -> `StructureModel` reference objects

### 10.2 Result-layer mappings

These should be used carefully and only when appropriate:

- imported TIN surfaces -> terrain/result surface objects
- imported reference surfaces -> surface families with clear provenance

### 10.3 Mapping rule

Do not hide import ambiguity.

If a source cannot be mapped confidently, the import should either:

- flag it clearly
- or map it as reference-only

## 11. Export Mapping Targets

Recommended export mapping sources:

- `PlanOutput`
- `ProfileOutput`
- `SectionOutput`
- `SectionSheetOutput`
- `SurfaceOutput`
- `QuantityOutput`
- `ExchangeOutput`

Exporters should avoid scraping random live object properties when a normalized contract exists.

## 12. ExchangeOutput Contract

The exchange subsystem should ultimately expose a normalized `ExchangeOutput` family.

Recommended fields:

- `schema_version`
- `format`
- `exchange_package_id`
- `source_refs`
- `result_refs`
- `unit_context`
- `coordinate_context`
- `payload_metadata`
- `format_payload`

### 12.1 Why this matters

A normalized exchange package helps:

- testability
- traceability
- consistent diagnostics
- multiple export backends

## 13. Units and Coordinates

### 13.1 Unit rule

Every import and export path must make units explicit.

### 13.2 Coordinate rule

Every import and export path must make coordinate interpretation explicit.

Minimum concerns:

- local vs world
- CRS/EPSG context where available
- project-origin effects

### 13.3 No silent conversion rule

Major coordinate conversions should be visible and traceable.

## 14. TIN Exchange Relationship

The exchange subsystem must connect cleanly to the TIN engine.

Examples:

- LandXML surface import -> TIN objects
- DXF breakline import -> breakline source sets
- LandXML surface export <- normalized surface contracts

The exchange layer should not create a second hidden terrain model.

## 15. Section Exchange Relationship

Section-related exports should use:

- `SectionOutput`
- `SectionSheetOutput`

This supports:

- DXF section outputs
- future SVG or drawing-oriented exchange paths
- output traceability

Section exchange should not reconstruct section meaning from template files alone.

## 16. Quantity and Earthwork Exchange Relationship

Not all early exchange formats need quantity or earthwork output immediately, but the architecture should allow it.

Potential future exchange uses:

- quantity summary exports
- earthwork-balance summary exchange
- report-oriented packages

The exchange plan should leave room for these without making them mandatory in the first phase.

## 17. Import Diagnostics

Imports should report:

- file type and version where known
- imported entities count
- skipped entities count
- unsupported entity kinds
- unit interpretation
- coordinate interpretation
- ambiguous mappings

## 18. Export Diagnostics

Exports should report:

- target format
- exported object families
- omitted entities
- schema/version used
- unit context
- coordinate context
- degraded export cases

## 19. Reference vs Engineering Import

The exchange subsystem should distinguish between:

- engineering import
- reference-only import

Examples:

- LandXML alignment can be engineering import
- IFC building model near the road may be reference-only import
- DXF survey linework may be reference or engineering depending on user intent

This distinction should be visible to the user.

## 20. Performance Strategy

Exchange operations may be large, so the subsystem should support:

- staged import
- selective entity import
- export scoping by alignment or range
- progress reporting
- partial success diagnostics

## 21. Anti-Patterns to Avoid

Avoid the following:

- writing exporter logic directly against viewer scene items
- treating import geometry as engineering truth without mapping
- duplicating unit conversion logic in every format adapter
- making LandXML, DXF, and IFC each define their own internal domain model
- forcing the core architecture to follow one file format's quirks

## 22. Recommended Follow-Up Documents

This exchange plan should be followed by:

1. `V1_EXCHANGE_OUTPUT_SCHEMA.md`
2. `V1_LANDXML_MAPPING_PLAN.md`
3. `V1_DXF_MAPPING_PLAN.md`
4. `V1_IFC_MAPPING_PLAN.md`

## 23. Final Rule

In v1, exchange should act as a disciplined translation layer between external schemas and the internal parametric corridor model.

If a format integration cannot explain what internal source/result/output contract it maps to, it is not ready to be treated as a proper v1 exchange path.

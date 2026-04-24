# CorridorRoad V1 Output Strategy

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_RAMP_MODEL.md`
- `docsV1/V1_INTERSECTION_MODEL.md`
- `docsV1/V1_DRAINAGE_MODEL.md`

## 1. Purpose

This document defines how CorridorRoad v1 should approach deliverables and output artifacts.

The goal is to avoid scattered, tool-specific export behavior and instead build a stable output system derived from the v1 source-of-truth model.

## 2. Core Direction

Outputs in v1 are not separate mini-products.

They are standardized derived artifacts generated from the same internal engineering model.

The intended flow is:

`Source Models -> Applied Results -> Output Contracts -> Viewer / Reports / Drawings / Exchange Files`

This means:

- outputs are regenerated, not hand-maintained
- outputs should not become hidden sources of truth
- viewer, reports, and file exports should agree with each other
- drawing/export logic should not redefine engineering logic

## 3. Output Philosophy

### 3.1 One engineering truth, many deliverables

The same internal source model should feed:

- 3D review outputs
- engineering reports
- drawing sheets
- exchange files

### 3.2 Output contracts before renderers

Do not build exports directly from UI widgets or ad-hoc object inspection.

Define stable intermediate output contracts first, then let each renderer/exporter consume those contracts.

### 3.3 Review is also an output

Cross Section Viewer, 3D review overlays, and profile review displays should be treated as output consumers, not as separate logic islands.

### 3.4 Rebuildable by default

Every important output should be reproducible from the project state without manual patching.

## 4. Output Layers

V1 outputs should be organized into four layers.

### 4.1 Review outputs

Used for design review and validation inside the application.

Examples:

- 3D plan overlays
- 3D profile overlays
- 3D current-section display
- 3D sparse full-section display
- Cross Section Viewer
- profile review panels
- ramp and junction review panels
- drainage review panels

### 4.2 Engineering outputs

Used as derived technical results that remain close to the computational model.

Examples:

- `AppliedSectionSet`
- `FG_TIN`
- `Subgrade_TIN`
- `Daylight_TIN`
- cut/fill summaries
- pavement quantity summaries
- structure interaction summaries

### 4.3 Drawing outputs

Used for human-readable drawing deliverables.

Examples:

- plan sheets
- profile sheets
- current-section sheets
- full cross-section sheets
- combined quantity sheets

### 4.4 Exchange outputs

Used for external interoperability.

Examples:

- `LandXML`
- `DXF`
- `IFC`

## 5. Primary Output Families

The v1 output system should recognize the following output families.

### 5.1 PlanOutput

Purpose:

- plan-view geometry and annotations
- corridor context in plan
- region and structure references

Typical content:

- alignment references
- ramp and junction references where practical
- station markers
- region ranges
- drainage paths and drainage structure markers where practical
- structure markers
- terrain boundaries and breaklines where needed

### 5.2 ProfileOutput

Purpose:

- longitudinal representation of terrain and design

Typical content:

- EG profile
- FG profile
- PVI markers
- grade transition notes
- structure/profile interaction markers where relevant

### 5.3 ContextReviewOutput

Purpose:

- ramp, intersection, and drainage context rows used by review surfaces

Typical content:

- ramp and junction identity rows
- tie-in or control-area markers
- drainage interaction rows
- low-point or minimum-grade warnings
- ownership references back to source models

### 5.4 SectionOutput

Purpose:

- current station or selected station cross-section representation

Typical content:

- applied section geometry
- semantic component rows
- terrain intersection rows
- drainage interaction rows
- structure interaction rows
- dimensions and labels
- quantity fragments

### 5.5 SectionSheetOutput

Purpose:

- multi-station section sheet generation

Typical content:

- ordered section panels
- station titles
- standard annotation rows
- summary rows
- quantity snippets where required

### 5.6 SurfaceOutput

Purpose:

- terrain and design surface deliverables

Typical content:

- surface identity
- source lineage
- TIN boundaries
- quality metadata
- triangulation statistics

### 5.7 QuantityOutput

Purpose:

- practical measurement and reporting outputs

Typical content:

- cut/fill totals
- range-based summaries
- pavement quantities
- corridor component quantities
- structure-related quantity notes

### 5.8 ExchangeOutput

Purpose:

- external-file-oriented normalized export packages

Typical content:

- schema/version metadata
- normalized geometry payloads
- reference metadata
- units and CRS data

## 6. Source Models That Feed Outputs

All output families should be derived from a shared v1 source model stack.

Primary sources:

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
- `QuantityModel`

Derived result sources:

- `AppliedSection`
- `AppliedSectionSet`
- corridor surface results
- quantity summaries

## 7. Output Contracts

### 7.1 Why output contracts matter

Without explicit contracts, each viewer/exporter tends to compute its own interpretation.

That leads to:

- inconsistent labels
- mismatched dimensions
- different station sets
- quantity/report disagreement
- export-specific bugs

### 7.2 Contract rule

Every output family should have a versioned internal contract.

Minimum contract goals:

- stable field names
- clear ownership of semantic rows
- explicit unit handling
- explicit coordinate handling
- explicit schema version

### 7.3 Recommended first contracts

The first output contracts to define in v1 should be:

1. `SectionOutputSchema`
2. `SectionSheetOutputSchema`
3. `SurfaceOutputSchema`
4. `QuantityOutputSchema`
5. `ExchangeOutputSchema`

## 8. Section Outputs as the First-Class Deliverable

V1 is corridor-centric, so section outputs should be treated as the highest-priority drawing/report family.

### 8.1 Why sections first

Sections are where users verify:

- component composition
- terrain daylight behavior
- structure conflicts
- local design correctness
- corridor quantity behavior

### 8.2 Recommended section output types

- single-station review output
- key-station sheet output
- interval-based section sheet output
- region-boundary section output
- issue-focused section review output

### 8.3 Section output rules

- section output is derived from `AppliedSection`
- never edit generated section output directly
- semantic component identity must survive into output rows
- labels and dimensions should be layout-driven, not hard-coded in renderers

## 9. Whole-Corridor Section Sheets

Full cross-section output is important but must be filtered and scalable.

Recommended modes:

- regular interval
- key stations only
- region boundaries only
- event-based only
- current range only

This applies to:

- 3D sparse section review
- multi-section drawing sheets
- DXF export layouts

## 10. Plan and Profile Outputs

### 10.1 Plan outputs

Plan outputs are important for context and external communication, but they should not define corridor logic.

Use cases:

- alignment review
- structure and region context
- drawing-sheet generation
- DXF plan output

### 10.2 Profile outputs

Profile outputs are useful for longitudinal review and design communication, but they are not the first output priority for v1 foundation work.

Use cases:

- FG/EG review
- PVI communication
- structure and grade conflict context
- profile sheet generation

## 11. Surface Outputs

TIN surface outputs are a core v1 deliverable because the product is moving to a TIN-first terrain model.

Priority surfaces:

- `ExistingGroundTIN`
- `FG_TIN`
- `Subgrade_TIN`
- `Daylight_TIN`
- `VolumeSurface`

Each surface output should preserve:

- source identity
- units
- CRS/coordinate context
- triangulation metadata
- generation timestamp or revision context where practical

## 12. Quantity Outputs

Quantity outputs should be treated as first-class engineering deliverables rather than as side notes inside a GUI panel.

Priority quantity families:

- cut/fill
- pavement quantities
- section-based component quantities
- region-based quantity summaries
- structure interaction quantity notes

Recommended output modes:

- project total
- station range total
- region total
- section-level detailed breakdown

## 13. Exchange Outputs

### 13.1 Exchange priorities

Recommended implementation priority:

1. `LandXML`
2. `DXF`
3. `IFC`

### 13.2 LandXML

LandXML should become the first serious external exchange target because it aligns well with:

- alignments
- profiles
- TIN surfaces
- practical civil exchange workflows

### 13.3 DXF

DXF should focus on:

- drawing-oriented geometry
- plan/profile/section sheet outputs
- breakline and boundary reference data where practical

### 13.4 IFC

IFC should be treated first as:

- structure reference import
- practical geometry/property export target when the internal corridor solid model is stable

## 14. Drawing Layout Strategy

### 14.1 Separate engineering logic from drawing layout

The layout engine must not be the place where engineering values are invented.

The correct flow is:

`engineering result -> output contract -> layout plan -> renderer/exporter`

### 14.2 Shared layout planning

Where practical, drawing outputs should use a shared layout planning layer for:

- titles
- labels
- dimensions
- summary notes
- collision handling
- sheet grouping

### 14.3 Why this matters

This prevents `Viewer`, `SVG`, `DXF`, and future sheet exports from drifting apart visually and semantically.

## 15. Output Priority for Initial V1 Work

Recommended priority order:

1. current-station section output
2. multi-station section sheet output
3. TIN surface output
4. quantity output
5. `LandXML` export
6. plan output
7. profile output
8. `DXF` sheet export
9. `IFC` export

This ordering reflects the corridor-first nature of v1.

## 16. Output Failure and Diagnostics

Outputs should fail clearly when their sources are incomplete or inconsistent.

Diagnostics should identify:

- which source object is missing
- which station range failed
- whether terrain sampling failed
- whether section evaluation failed
- whether layout failed
- whether export serialization failed

User-facing outputs should prefer actionable diagnostics over vague "export failed" messages.

## 17. Performance Rules

Output generation must remain practical for large corridor scenes.

Recommended controls:

- preview vs final modes
- density controls for full-section outputs
- sheet batching
- deferred expensive labels/annotations
- sparse 3D review defaults

## 18. Governance Rules

### 18.1 No hidden logic duplication

If two output paths compute the same engineering meaning differently, the design should be corrected.

### 18.2 No manual geometry patching

Generated output geometry must not become a hidden manual-edit layer.

### 18.3 Schema versioning

Every important output contract should expose a schema version.

### 18.4 Traceability

Important output rows should be traceable back to:

- station
- template
- region
- structure
- override
- source terrain or surface where relevant

## 19. Recommended Next Output Documents

This strategy document should be followed by:

1. `V1_SECTION_OUTPUT_SCHEMA.md`
2. `V1_SURFACE_OUTPUT_PLAN.md`
3. `V1_QUANTITY_OUTPUT_PLAN.md`
4. `V1_PLAN_PROFILE_SHEET_PLAN.md`
5. `V1_EXCHANGE_OUTPUT_PLAN.md`

## 20. Final Rule

In v1, a deliverable is not just a file.

It is a governed, reproducible, traceable artifact derived from the parametric corridor model.

If an output path cannot be explained in terms of the source model and applied results, it is not ready to be treated as a v1 deliverable.

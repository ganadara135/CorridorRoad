# CorridorRoad V1 Plan Profile Sheet Plan

Date: 2026-04-22
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_OUTPUT_STRATEGY.md`
- `docsV1/V1_SECTION_OUTPUT_SCHEMA.md`
- `docsV1/V1_3D_REVIEW_DISPLAY_PLAN.md`
- `docsV1/V1_EXCHANGE_PLAN.md`

## 1. Purpose

This document defines how v1 should approach plan, profile, and sheet-style drawing outputs.

It exists to clarify:

- which 2D drawing families are needed
- what each drawing family is for
- how they relate to normalized output contracts
- how they differ from 3D review overlays
- how section sheets, plan sheets, and profile sheets should be organized

## 2. Core Direction

Plan and profile drawing outputs in v1 are deliverables derived from normalized output contracts.

They are not the source of engineering truth.

They should be built from:

- `PlanOutput`
- `ProfileOutput`
- `SectionOutput`
- `SectionSheetOutput`

and not from ad-hoc display state or manually patched drawing geometry.

## 3. Drawing Families

Recommended main drawing families:

- plan sheets
- profile sheets
- single-section sheets
- multi-section sheets
- combined plan/profile/section bundles where practical

## 4. Plan Sheet Role

Plan sheets should communicate:

- alignment context
- station progression
- region changes
- structure locations
- terrain/boundary context where useful

They should support:

- review-ready plan drawings
- DXF export
- future print or plotting workflows

## 5. Profile Sheet Role

Profile sheets should communicate:

- EG and FG relationships
- PVI locations
- grade transitions
- structure/profile interaction context where needed
- earthwork-balance overlays or mass-haul diagrams when applicable

They should not replace the core engineering profile model.

## 6. Section Sheet Role

Section sheets are one of the highest-priority v1 drawing families.

They should communicate:

- component composition
- dimensions
- terrain interaction
- structure interaction
- selected local diagnostics

Recommended forms:

- single-station detail sheet
- interval-based section sheet
- key-station-only section sheet
- region-boundary section sheet

## 7. Difference Between 2D Sheets and 3D Review

3D review overlays are for interactive spatial inspection.

2D sheets are for organized deliverables and human-readable communication.

Rules:

- 3D review should stay sparse and contextual
- 2D sheets should provide denser structured communication
- both should still consume shared output contracts

## 8. Output Contract Relationship

### 8.1 Plan sheets

Should derive from:

- `PlanOutput`

### 8.2 Profile sheets

Should derive from:

- `ProfileOutput`
- optional earthwork/mass-haul output where relevant

### 8.3 Section sheets

Should derive from:

- `SectionOutput`
- `SectionSheetOutput`

### 8.4 Rule

No sheet generator should re-derive engineering meaning directly from raw internal object graphs when a normalized output contract already exists.

## 9. Plan Sheet Content

Recommended content blocks:

- title block metadata
- alignment geometry
- station labeling
- region range markers
- structure markers
- breakline or terrain context where useful
- optional notes block

## 10. Profile Sheet Content

Recommended content blocks:

- title block metadata
- EG line
- FG line
- PVI markers
- grade annotation rows
- structure/profile markers where relevant
- optional mass-haul or balance block

## 11. Single-Section Sheet Content

Recommended content blocks:

- station title
- section geometry
- component labels
- dimension rows
- terrain rows
- structure rows
- diagnostics summary
- quantity snippet where needed

## 12. Multi-Section Sheet Content

Recommended content blocks:

- ordered section panels
- consistent station titles
- optional grouping by station mode
- summary rows
- optional issue highlighting

Recommended station selection modes:

- regular interval
- key stations only
- region boundaries only
- event stations only
- custom selected stations

## 13. Sheet Layout Strategy

### 13.1 Layout should be driven by layout hints

Drawing sheets should use layout hints rather than embedding engineering rules directly in renderers.

### 13.2 Recommended layout hint concerns

- scale
- panel order
- grouping mode
- label visibility
- dimension visibility
- summary placement

### 13.3 Shared layout rule

Where practical, the same planned row and layout-hint system should drive:

- viewer-friendly sheet preview
- DXF sheet export
- future SVG or print-oriented outputs

## 14. Plan/Profile/Section Linkage

Although these are separate sheet families, they should feel like one coherent deliverable system.

Recommended shared metadata:

- project identity
- alignment identity
- station range
- units
- coordinate context
- schema/version markers

## 15. Earthwork-Balance Integration

Earthwork information should be able to appear in drawing outputs where useful.

Recommended uses:

- profile sheet mass-haul block
- section sheet issue markers for cut/fill problem areas
- plan sheet borrow/waste markers where appropriate

Rule:

Earthwork overlays in sheets should remain driven by normalized earthwork outputs, not ad-hoc recalculation inside sheet generators.

## 16. Exchange Relationship

Drawing-oriented exports, especially DXF, should be treated as exchange consumers of drawing contracts.

This means:

- plan sheet export reads `PlanOutput`
- profile sheet export reads `ProfileOutput`
- section sheet export reads `SectionSheetOutput`

## 17. Title Block and Metadata Policy

Sheet generators should support consistent metadata blocks.

Recommended metadata:

- project name
- alignment name
- sheet type
- station range or station value
- unit label
- revision or generation timestamp where practical

## 18. Density and Legibility Rules

Drawing sheets are denser than 3D review overlays, but they still need clarity.

Recommended rules:

- prioritize legibility over maximum information density
- suppress low-priority labels when space is inadequate
- push overflow information into summary blocks where useful
- keep dimension and annotation systems consistent across sheets

## 19. Validation Rules

The sheet-generation system should validate:

- missing required output payloads
- invalid station selection modes
- duplicate sheet entries
- missing title metadata
- layout overflow conditions where detectable

## 20. Anti-Patterns to Avoid

Avoid the following:

- generating sheets directly from viewer scene objects
- different geometry meaning in viewer vs sheet outputs
- sheet-specific hidden recalculation of engineering values
- using sheet layout as a substitute for source/model clarity

## 21. Recommended Follow-Up Documents

This sheet plan should be followed by:

1. `V1_PLAN_OUTPUT_SCHEMA.md`
2. `V1_PROFILE_OUTPUT_SCHEMA.md`
3. `V1_SHEET_LAYOUT_HINT_SCHEMA.md`

## 22. Final Rule

In v1, plan, profile, and section sheets should be treated as organized deliverables derived from normalized contracts.

If a sheet generator cannot explain what output contract it is consuming, it is not yet aligned with the v1 architecture.

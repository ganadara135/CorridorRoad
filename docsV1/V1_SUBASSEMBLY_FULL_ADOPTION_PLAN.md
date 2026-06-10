# Parametric Road V1 Subassembly Full Adoption Plan

Date: 2026-06-11

Status: planning

## Purpose

This document defines a full Subassembly adoption plan for Parametric Road v1.

The goal is not a UI-only rename from `Component` to `Subassembly`.

The goal is to make Subassembly the authoritative reusable cross-section generator inside an Assembly, similar to the Civil 3D Assembly/Subassembly model.

## Scope

This plan covers:

- source model replacement
- Applied Section result contract replacement
- Section output contract replacement
- Assembly editor UX
- Applied Sections build service
- Build Parametric surface generation
- Superelevation integration
- Drainage and Structure references
- Cross Section Viewer review
- Watertight Solid target discovery
- Exchange and QA updates

This plan does not attempt to import Civil 3D `.pkt` files as executable Subassemblies.

`.pkt` is treated as a future import-assist or metadata reference, not as the native Parametric Road Subassembly runtime.

## Core Decision

Parametric Road should replace the current `Component` concept with `Subassembly`.

The new rule is:

```text
Assembly
  -> SectionTemplate
  -> Subassembly rows
  -> evaluated AppliedSection Subassembly rows
  -> point/link/shape/code output
  -> surfaces, solids, quantities, review
```

`Component` should not remain as a long-term user-facing or source-contract term.

## Current State

Current source/result/output contracts use `component` language:

- `TemplateComponent`
- `SectionTemplate.component_rows`
- `AppliedSectionComponentRow`
- `AppliedSection.component_rows`
- `SectionComponentRow`
- `SectionOutput.component_rows`
- `component_id`
- `component_ref`
- `component_kind`

These names are used by:

- Assembly source editor
- Applied Section builder
- Cross Section Viewer
- Superelevation resolver
- Drainage element references
- quantity builder
- corridor surface builder
- Watertight Solid target discovery
- exchange output mapper
- wiki and design documents

Because the term is already deep in contracts, full adoption is a breaking v1 contract change.

## Target Model

### Source Contract

Replace `TemplateComponent` with `TemplateSubassembly`.

Recommended source fields:

- `subassembly_id`
- `subassembly_index`
- `kind`
- `side`
- `width`
- `slope`
- `thickness`
- `material`
- `target_ref`
- `parameter_rows`
- `parameters`
- `point_code_rules`
- `link_code_rules`
- `shape_code_rules`
- `enabled`
- `notes`

`SectionTemplate` should use:

- `subassembly_rows`

instead of:

- `component_rows`

### Result Contract

Replace `AppliedSectionComponentRow` with `AppliedSectionSubassemblyRow`.

Recommended result fields:

- `subassembly_id`
- `kind`
- `source_template_id`
- `region_id`
- `side`
- `width`
- `slope`
- `thickness`
- `material`
- `override_ids`
- `structure_ids`
- `drainage_refs`
- `parameters`
- `point_refs`
- `link_refs`
- `shape_refs`
- `diagnostics`

`AppliedSection` should use:

- `subassembly_rows`

instead of:

- `component_rows`

### Geometry Result Contract

Subassembly evaluation should produce explicit point/link/shape rows.

Recommended first native contracts:

- `AppliedSectionSubassemblyPoint`
- `AppliedSectionSubassemblyLink`
- `AppliedSectionSubassemblyShape`

Point row fields:

- `point_id`
- `subassembly_ref`
- `point_code`
- `x`
- `y`
- `z`
- `lateral_offset`
- `side`
- `target_ref`
- `diagnostics`

Link row fields:

- `link_id`
- `subassembly_ref`
- `start_point_ref`
- `end_point_ref`
- `link_code`
- `surface_role`
- `material`
- `diagnostics`

Shape row fields:

- `shape_id`
- `subassembly_ref`
- `point_refs`
- `shape_code`
- `material`
- `thickness`
- `solid_family`
- `diagnostics`

### Output Contract

Replace `SectionComponentRow` with `SectionSubassemblyRow`.

`SectionOutput` should use:

- `subassembly_rows`

instead of:

- `component_rows`

Quantity rows should use:

- `subassembly_ref`

instead of:

- `component_ref`

## Subassembly Kind Families

Initial supported kind families:

- `lane`
- `shoulder`
- `median`
- `curb`
- `gutter`
- `ditch`
- `side_slope`
- `sidewalk`
- `bike_lane`
- `green_strip`
- `barrier`
- `pavement_layer`
- `subbase`
- `structure_interface`
- `intersection_transition`
- `curb_return_transition`

The first full adoption should not try to support arbitrary user-defined logic.

It should first make built-in Subassemblies explicit, deterministic, and source-traceable.

## User-Defined Subassembly Direction

Parametric Road should eventually support native user-defined Subassemblies.

Recommended native format:

- JSON source object
- parameter schema
- point rules
- link rules
- shape rules
- target rules
- diagnostics
- preview payload

Do not use `.pkt` as the native runtime format.

Future `.pkt` support should be limited to:

- reading metadata when practical
- showing unsupported import diagnostics
- offering manual conversion guidance

## UI Plan

### Existing Assembly Panel

The current Assembly panel should remain available during the Subassembly cutover.

It is the fallback editor for the existing first-slice Assembly workflow.

Do not rewrite the current panel in place as the first Subassembly implementation.

The current panel may later be retired, but only after the new Assembly/Subassembly panel passes Build Sections, Build Parametric, Drainage, Cross Section Viewer, and Watertight Solid QA.

### New Assembly/Subassembly Panel

Create a new panel for the full Subassembly workflow.

Working title:

- `Assembly / Subassembly`

The new panel should be the first panel that writes the new Subassembly source contract.

The existing Assembly panel should not write `TemplateSubassembly` rows unless it is explicitly upgraded later.

The new panel should use:

- `Components` -> `Subassemblies`
- `Component Id` -> `Subassembly Id`
- `Kind` remains `Kind`
- `Assembly Component` -> `Subassembly`

### New Panel Layout

Recommended layout:

```text
Assembly / Subassembly

Assembly
  - Assembly ID
  - Active Template
  - Preset
  - Load Preset
  - Validate
  - Apply

Subassemblies
  - table of subassembly rows

Selected Subassembly Detail
  - type-specific editor
  - point/link/shape preview
  - diagnostics
```

The `Subassemblies` table should remain compact.

Detailed editing should happen in the selected Subassembly detail area instead of forcing every parameter into the table.

### Selected Subassembly Detail

The detail area should show:

- source identity
- side
- width/slope/thickness
- material
- target refs
- parameters
- point/link/shape code preview
- diagnostics

The detail area should be dynamic by Subassembly kind.

### Ditch Subassembly Detail

The current Assembly panel has a first-slice `Ditch Parameters` helper.

In the new panel, that helper should become a native `ditch` Subassembly detail editor.

The new `ditch` detail editor should own:

- shape type
- depth
- bottom width
- top width
- side slopes
- lining material
- lining thickness
- wall thickness for structural ditch materials
- wall side
- custom polyline points
- generated point/link/shape preview
- drainage handoff refs
- diagnostics

The raw `Parameters` table cell should not be the primary user workflow for ditch editing.

It may remain as an advanced/source-inspection view.

### Side Slope Subassembly Detail

The current Assembly panel has a first-slice `Side Slope Bench` helper.

In the new panel, that helper should become a native `side_slope` Subassembly detail editor.

The new `side_slope` detail editor should own:

- side
- base slope
- design width
- bench mode
- bench row table
- repeat-to-daylight policy
- daylight mode
- daylight search step
- daylight max width
- daylight max width delta
- daylight max triangle count
- cut/fill slope overrides
- generated point/link preview
- terrain target diagnostics

The `side_slope` detail editor should make clear whether the Subassembly is fixed-width or terrain-daylight controlled.

### Lane And Shoulder Subassembly Detail

Lane and shoulder detail editors should own:

- side
- width
- default crossfall
- Superelevation target behavior
- material
- thickness
- point/link codes
- surface role
- diagnostics

Superelevation should modify evaluated Subassembly results.

It should not rewrite the source lane/shoulder Subassembly definition.

### Pavement Layer And Subbase Detail

Pavement and subbase detail editors should own:

- layer width source
- thickness
- material
- shape code
- solid target family
- quantity behavior
- diagnostics

These rows are important for Watertight Solid target discovery.

### Curb, Gutter, Barrier, And Structure Interface Detail

These detail editors should own:

- shape family
- offset and height parameters
- material
- connection behavior
- target refs
- structure/drainage handoff refs where relevant
- point/link/shape preview
- diagnostics

### New Panel Output Rule

The new panel should write only the new Subassembly source contract.

It should not write both `component_rows` and `subassembly_rows`.

The current Assembly panel may continue to write the old Component contract until it is retired.

Build Sections should select one source contract path per document:

- old Assembly panel path: old Component contract
- new Assembly/Subassembly panel path: new Subassembly contract

During the full cutover, the old Component path should be removed from active v1 workflows.

### Drainage Panel

Rename Assembly-related refs:

- `Assembly` column for ditch rows should become `Subassembly`
- drainage element fields should use `subassembly_ref`

Ditch rows may reference ditch Subassemblies.

Inlets, outlets, culverts, and pipes should continue to reference Structure or Drainage objects, not road Subassemblies.

### Cross Section Viewer

Rename review surfaces:

- `Components` table -> `Subassemblies`
- `Focused Component` -> `Focused Subassembly`
- `Component Id` -> `Subassembly Id`
- `Component Kind` -> `Subassembly Kind`

The viewer should show:

- Subassembly rows
- point/link/shape rows
- material and quantity links
- source template ref
- Superelevation-applied slope provenance

### Watertight Solids

Rename target source labels:

- `Assembly Component` -> `Subassembly`
- `component_ref` display -> `subassembly_ref`

Solid targets should remain scoped by physical output family:

- pavement layer body
- subbase body
- shoulder body
- lined ditch body
- curb/gutter body
- barrier body

## Implementation Plan

### Phase S1: Contract Inventory Freeze

Status: pending

Work:

- list every source/result/output field using `component`
- list every UI label using `Component`
- list every document using `Component`
- identify contract files that must change together

Acceptance:

- a single inventory table exists
- no code rename starts before the inventory is accepted

### Phase S2: Source Model Replacement

Status: pending

Work:

- rename `TemplateComponent` to `TemplateSubassembly`
- rename constants from `ASSEMBLY_COMPONENT_*` to `ASSEMBLY_SUBASSEMBLY_*`
- rename normalization helpers
- replace `SectionTemplate.component_rows` with `subassembly_rows`
- replace source validation messages
- add a new Assembly/Subassembly source command and task panel
- keep the existing Assembly panel available during the transition window
- ensure the new panel writes only the Subassembly source contract

Acceptance:

- Assembly presets create `TemplateSubassembly` rows
- Assembly validation no longer emits `component` terminology
- Assembly source object stores Subassembly rows
- the existing Assembly panel still opens for fallback review during the cutover
- the new Assembly/Subassembly panel can create a fresh Assembly source using Subassembly rows

### Phase S2.5: Assembly/Subassembly Detail Editors

Status: pending

Work:

- add the selected Subassembly detail area to the new panel
- move `Ditch Parameters` behavior into the `ditch` Subassembly detail editor
- move `Side Slope Bench` behavior into the `side_slope` Subassembly detail editor
- add lane and shoulder detail editors for width, default crossfall, material, thickness, and Superelevation target behavior
- add pavement layer and subbase detail editors for thickness, material, and solid target behavior
- add curb, gutter, barrier, and structure-interface detail editor placeholders
- make the raw `Parameters` view secondary or advanced-only
- show point/link/shape preview data from the selected Subassembly
- show Subassembly-specific diagnostics before Apply

Acceptance:

- ditch shape editing no longer depends on editing raw parameter text
- side-slope bench/daylight editing no longer depends on editing raw parameter text
- selected Subassembly detail updates when a table row is selected
- detail editors persist values into `TemplateSubassembly.parameters`
- preview output shows the selected Subassembly's generated point/link/shape intent
- diagnostics identify the selected Subassembly by `subassembly_id`

### Phase S3: Applied Section Result Replacement

Status: pending

Work:

- rename `AppliedSectionComponentRow` to `AppliedSectionSubassemblyRow`
- replace `AppliedSection.component_rows` with `subassembly_rows`
- update `AppliedSectionService`
- update Superelevation resolution to target Subassemblies
- update bench and ditch evaluation to emit Subassembly refs

Acceptance:

- Build Sections emits Subassembly rows
- existing lane, shoulder, ditch, side_slope, pavement_layer, and subbase behavior still works
- output point rows use `subassembly_ref`

### Phase S4: Point/Link/Shape Rows

Status: pending

Work:

- add Subassembly point/link/shape result rows
- map current generated section points into point/link rows
- define surface role codes for FG, subgrade, ditch, and Slope Face
- define shape rows for material/thickness bodies

Acceptance:

- Cross Section Viewer can show which Subassembly produced each point/link/shape
- Build Parametric can build design/subgrade/drainage surfaces from link roles
- Watertight Solid target discovery can use shape rows where available

### Phase S5: Surface Builder Refactor

Status: pending

Work:

- update corridor surface builder to consume Subassembly point/link rows
- replace `component_ref` provenance with `subassembly_ref`
- keep design, subgrade, drainage, and Slope Face outputs traceable
- make intersection surface zones reference Subassembly roles where relevant

Acceptance:

- Build Parametric still creates design, subgrade, drainage, and Slope Face surfaces
- surface vertices preserve Subassembly provenance
- intersection diagnostics can report missing Subassembly roles

### Phase S6: Drainage And Structures Update

Status: pending

Work:

- update DrainageModel refs from component to Subassembly
- keep ditch as Assembly/Subassembly-generated drainage geometry
- keep culvert, inlet, outlet, pipe, and outfall as Structure/Drainage-owned objects
- update Structure connection docs to reference Subassembly only where road-section ownership is intended

Acceptance:

- Drainage ditch elements can select Subassembly refs
- non-ditch drainage elements cannot select road Subassemblies
- Flow Routes remain Drainage-owned

### Phase S7: Cross Section Viewer And Review UX

Status: pending

Work:

- rename UI tables and labels
- update selected Subassembly inspector
- update drawing mapper labels and dimension kinds
- update focused object context
- keep the old Assembly panel out of the primary QA path once the new Assembly/Subassembly panel is accepted

Acceptance:

- no visible `Component` label remains in normal user-facing section review
- focused Subassembly row survives rebuild when its id still exists

### Phase S8: Watertight Solid And Quantity Refactor

Status: pending

Work:

- update solid target discovery from component refs to Subassembly refs
- update solid profile service
- update quantity builder
- update exchange mapper

Acceptance:

- pavement, subbase, shoulder, and lined ditch targets still discover
- target rows preserve `subassembly_ref`
- quantity rows use Subassembly terminology

### Phase S9: Documentation And Wiki Cutover

Status: pending

Work:

- update `V1_ASSEMBLY_MODEL.md`
- update `V1_SECTION_MODEL.md`
- update `V1_SECTION_OUTPUT_SCHEMA.md`
- update Drainage, Superelevation, Watertight Solid, Surface, Viewer, and wiki documents
- record the breaking terminology decision in the master plan

Acceptance:

- active docs use Subassembly for the cross-section building unit
- `Component` appears only in historical notes or explicit deprecated-term sections

### Phase S10: Removal Of Compatibility Fields

Status: pending

Work:

- remove source/result/output compatibility aliases such as `component_rows`
- remove `component_id`, `component_ref`, and `component_kind` from active v1 contracts
- remove old UI labels
- remove old mapper fallback paths

Acceptance:

- new documents created by Parametric Road no longer store active component fields
- focused tests fail if active source/result/output contracts reintroduce component fields

## Migration Position

Legacy file compatibility is not a goal for this change.

The v1 reset direction allows breaking the internal contract.

Existing test documents may need to be recreated after the Subassembly cutover.

No hidden migration layer should preserve old `component_rows` as active design state.

## Risk Analysis

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Wide contract rename breaks Build Sections | high | change source/result/output contracts in one branch and run focused builder tests |
| Cross Section Viewer loses focus behavior | medium | implement selected Subassembly id matching before removing old focus fields |
| Drainage ditch refs break | high | update Drainage and Assembly together; reject non-ditch Subassembly refs |
| Watertight Solid targets disappear | high | update target discovery immediately after Applied Section result replacement |
| Superelevation targets wrong rows | high | update effective crossfall resolver to use Subassembly kind and side |
| Intersection Slope Face diagnostics become harder to trace | medium | preserve source Subassembly refs in intersection surface-zone notes |
| Documentation drift | medium | update plan, model docs, and wiki in the same cutover phase |
| `.pkt` expectations grow too early | medium | explicitly state native Subassembly format first; `.pkt` is future import-assist only |

## Testing Plan

Required focused tests:

- Assembly preset creation emits Subassembly rows
- Assembly validation catches duplicate Subassembly ids
- Build Sections emits Applied Section Subassembly rows
- Superelevation changes lane and shoulder Subassembly slopes
- ditch Subassembly emits ditch surface point/link rows
- side_slope Subassembly emits Slope Face rows
- Cross Section Viewer displays Subassembly rows
- Drainage ditch element references Subassembly rows
- Watertight Solid discovers pavement, subbase, shoulder, and lined ditch targets
- Build Parametric design/subgrade/drainage/Slope Face outputs still build
- Intersection starter T case still builds after the Subassembly cutover

Manual QA:

- Basic Road
- Urban Curb & Gutter
- Drainage Ditch Road
- T Intersection starter
- Cross Section Viewer focused Subassembly review
- Watertight Solid target discovery

## Acceptance Criteria

The full adoption is complete when:

- active source contracts use `TemplateSubassembly`
- active result contracts use `AppliedSectionSubassemblyRow`
- active output contracts use `SectionSubassemblyRow`
- normal user-facing UI no longer says `Component` for road section parts
- Build Sections, Build Parametric, Drainage, Cross Section Viewer, Superelevation, Watertight Solid, and Exchange use Subassembly refs
- existing v1 docs describe Subassembly as the cross-section building unit
- no active v1 code path depends on `component_rows` as the authoritative contract

## Non-goals

- direct execution of Civil 3D `.pkt`
- full graphical Subassembly Composer in the first cutover
- arbitrary scriptable Subassembly runtime
- automatic conversion of all old test documents
- final intersection redesign completion

## Recommended Execution Order

Do this after the current intersection QA snapshot is stable enough to compare before/after geometry.

Then execute the Subassembly cutover as one focused breaking-change branch:

1. S1 inventory
2. S2 source model replacement
3. S2.5 Assembly/Subassembly detail editors
4. S3 Applied Section result replacement
5. S4 point/link/shape rows
6. S5 surface builder refactor
7. S6 Drainage and Structures update
8. S7 viewer UX update
9. S8 solids and quantities update
10. S9 documentation cutover
11. S10 compatibility field removal

Do not interleave this cutover with additional intersection geometry experiments.

The Subassembly cutover changes the foundation that intersection geometry will consume.

# Parametric Road V1 Subassembly Full Adoption Plan

Date: 2026-06-11

Status: implementation started

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

Status: in progress

Work:

- list every source/result/output field using `component`
- list every UI label using `Component`
- list every document using `Component`
- identify contract files that must change together

Acceptance:

- a single inventory table exists
- no code rename starts before the inventory is accepted

### Phase S2: Source Model Replacement

Status: in progress

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

Implementation note, 2026-06-11:

- Added the parallel `AssemblySubassemblyModel` source contract.
- Added `TemplateSubassembly` and `SubassemblySectionTemplate` without removing the old Component contract.
- Added a `V1AssemblySubassemblyModel` FreeCAD source object.
- Added a first-slice `Assembly / Subassembly` task panel and command.
- Registered the new panel next to the existing Assembly panel.
- Routed the new source object into `04_Parametric Model > Assemblies`.
- Downstream Build Sections, Build Parametric, Drainage, Cross Section Viewer, Watertight Solid, and Exchange still need to be moved from the old Component contract to the new Subassembly contract.

### Phase S2.5: Assembly/Subassembly Detail Editors

Status: in progress

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

Implementation note, 2026-06-11:

- Added a first-slice `Selected Subassembly Detail` area to the new `Assembly / Subassembly` panel.
- Selecting a Subassembly row refreshes the detail editor.
- `ditch` rows now expose shape and geometry parameters in the detail area.
- `side_slope` rows now expose bench/daylight parameters in the detail area.
- Detail edits are applied back into `TemplateSubassembly.parameters`.
- Added a first-slice source-level point/link/shape preview for selected Subassemblies.
- The preview is not yet the final evaluated `AppliedSectionSubassemblyPoint/Link/Shape` result contract.

### Phase S3: Applied Section Result Replacement

Status: in progress

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

Implementation note, 2026-06-11:

- Added `AppliedSectionSubassemblyRow` as a parallel result contract.
- Added `AppliedSection.subassembly_rows` without removing `component_rows`.
- Added `SubassemblyRows` and `SubassemblyCounts` persistence on `V1AppliedSectionSet`.
- Build Sections now detects `V1AssemblySubassemblyModel` sources.
- Build Sections emits Subassembly result rows from the new source contract.
- For this transition slice, Build Sections also creates a temporary Component compatibility view from Subassembly rows so existing Build Parametric, quantity, solid, and viewer services keep working until their own phases are converted.
- Added a first-slice `SectionSubassemblyRow` output contract.
- Cross Section Viewer summaries now report Subassembly counts separately from temporary compatibility Component counts.
- Applied Sections review now shows Subassembly summaries first when Subassembly rows are available.
- Added parallel `subassembly_ref` fields to Applied Section points and quantity contracts while keeping existing `component_ref` compatibility fields.
- Applied Section point persistence now preserves `subassembly_ref`.
- Surface geometry provenance now records `subassembly_refs` and `subassembly_ref_count` alongside compatibility component refs.
- Supplemental/interpolated section points preserve `subassembly_ref` when available.

### Phase S4: Point/Link/Shape Rows

Status: in progress

Work:

- add Subassembly point/link/shape result rows
- map current generated section points into point/link rows
- define surface role codes for FG, subgrade, ditch, and Slope Face
- define shape rows for material/thickness bodies

Acceptance:

- Cross Section Viewer can show which Subassembly produced each point/link/shape
- Build Parametric can build design/subgrade/drainage surfaces from link roles
- Watertight Solid target discovery can use shape rows where available

Implementation notes:

- Added parallel `AppliedSectionSubassemblyPoint`, `AppliedSectionSubassemblyLink`, and `AppliedSectionSubassemblyShape` result rows.
- Build Sections now derives first-slice Subassembly point/link/shape rows from evaluated section points with `subassembly_ref`.
- `V1AppliedSectionSet` persists and restores Subassembly point/link/shape rows.
- `SectionOutput` and Cross Section Viewer summaries expose Subassembly point/link/shape counts.
- Existing `AppliedSection.point_rows` remains the compatibility geometry path until Build Parametric is moved to consume Subassembly links directly.

### Phase S5: Surface Builder Refactor

Status: in progress

Work:

- update corridor surface builder to consume Subassembly point/link rows
- replace `component_ref` provenance with `subassembly_ref`
- keep design, subgrade, drainage, and Slope Face outputs traceable
- make intersection surface zones reference Subassembly roles where relevant

Acceptance:

- Build Parametric still creates design, subgrade, drainage, and Slope Face surfaces
- surface vertices preserve Subassembly provenance
- intersection diagnostics can report missing Subassembly roles

Implementation notes:

- SurfaceModel build relations now include Subassembly link provenance when available.
- Drainage surface discovery accepts either legacy `ditch_surface` points or Subassembly links with `surface_role=drainage_surface`.
- Surface span diagnostics compare Subassembly surface link role counts between adjacent sections.
- Span notes report Subassembly link role counts to make Build Parametric review traceable before the full geometry builder cutover.
- Surface geometry point grids now prefer Subassembly link start/end point refs when matching evaluated point rows are available.
- Drainage surface grouping now includes `subassembly_ref` in grouping/provenance, while preserving legacy point-role fallback.
- Slope Face/daylight surface rows now prefer Subassembly links with `surface_role=slope_face_surface`.
- Side-slope vertices and supplemental side-slope samples preserve `subassembly_ref`/`component_ref` provenance while keeping legacy point-role fallback.
- Surface build relations now include Subassembly provenance for subgrade and slope-face outputs.
- Build Parametric review notes now report Subassembly surface-role coverage and call out legacy point-role fallback when links are not present.
- Build Parametric surface quality/provenance now reports `subassembly_ref_count` as the active traceability count and moves old component refs under `compatibility_ref_count` / `compatibility_refs`.
- Drainage surface mismatch diagnostics now report `subassembly_mismatch` instead of user-facing component mismatch wording.
- Surface provenance now suppresses compatibility component refs when the same point/grid already carries `subassembly_ref`.
- Quantity fragments now preserve `subassembly_ref` for section quantity rows, compatibility component rows, side-slope lengths, and drainage ditch/flowline lengths.
- QuantityModel source refs now include Subassembly refs from rows, point rows, and shape rows.
- Applied Section Superelevation fallback crossfall now reads lane/shoulder `TemplateSubassembly` rows first and uses legacy `TemplateComponent` rows only when no Subassembly defaults are available.

### Phase S6: Drainage And Structures Update

Status: in progress

Work:

- update DrainageModel refs from component to Subassembly
- keep ditch as Assembly/Subassembly-generated drainage geometry
- keep culvert, inlet, outlet, pipe, and outfall as Structure/Drainage-owned objects
- update Structure connection docs to reference Subassembly only where road-section ownership is intended

Acceptance:

- Drainage ditch elements can select Subassembly refs
- non-ditch drainage elements cannot select road Subassemblies
- Flow Routes remain Drainage-owned

Implementation notes:

- Drainage Elements now present the ditch road-section reference as `Subassembly` instead of `Assembly`.
- Drainage presets now write and read `subassembly` keys for ditch refs; the old `component` preset-key fallback has been removed.
- Drainage wiki text now describes ditch rows as Subassembly-backed drainage geometry.

### Phase S7: Cross Section Viewer And Review UX

Status: in progress

Work:

- rename UI tables and labels
- update selected Subassembly inspector
- update drawing mapper labels and dimension kinds
- update focused object context
- keep the old Assembly panel out of the primary QA path once the new Assembly/Subassembly panel is accepted

Acceptance:

- no visible `Component` label remains in normal user-facing section review
- focused Subassembly row survives rebuild when its id still exists

Implementation notes:

- Cross Section Viewer summary, source inspector, table headers, and viewer context labels now use Subassembly wording.
- Cross Section Viewer context now reads `focused_subassembly` / `subassembly_rows` first and keeps old `focused_component` / `component_rows` only as fallback keys.
- Section preview text now reports focused Subassembly wording and keeps compatibility row counts out of primary Component terminology.
- SectionOutput mapping now emits compatibility component rows only for legacy-only sections with no Subassembly rows.
- Cross-section drawing labels and dimensions now emit `subassembly-label`, `dim-subassembly`, `subassembly_width`, and `subassembly:*` roles when section spans are available.
- Cross-section drawing span generation now prefers `AppliedSection.subassembly_rows` and falls back to `component_rows` only for transition compatibility.
- SectionOutput summary labels now present `subassembly_count` as the active count and describe old compatibility rows as fallback rows only.
- Applied Sections review rows now prefer Subassembly summaries and label old component-derived ditch summaries as fallback-only.
- Cross-section drawing mapper internal helpers now use Subassembly/span wording for active rows and only inspect `component_rows` when no Subassembly rows are present.

### Phase S8: Watertight Solid And Quantity Refactor

Status: in progress

Work:

- update solid target discovery from component refs to Subassembly refs
- update solid profile service
- update quantity builder
- update exchange mapper

Acceptance:

- pavement, subbase, shoulder, and lined ditch targets still discover
- target rows preserve `subassembly_ref`
- quantity rows use Subassembly terminology

Implementation notes:

- Quantity fragments now preserve Subassembly provenance for section quantity rows, compatibility component rows, side-slope length rows, and drainage ditch/flowline length rows.
- Quantity model source refs now include Subassembly refs from Applied Section rows, point rows, and shape rows.
- SolidTargetRow now includes `subassembly_ref` while retaining `component_ref` as a compatibility field.
- WatertightSolidOutputRow and the FreeCAD output object now preserve `subassembly_ref`.
- WatertightSolidOutputRow emits `component_ref` only for legacy-only targets; Subassembly-owned targets keep the old component id as diagnostic `compatibility_ref` only.
- Watertight Solid target discovery groups pavement, subbase, and shoulder targets by `subassembly_ref` first; compatibility component ids remain only as fallback/profile-dimension references.
- Watertight Solid profile building matches Subassembly-owned targets by `subassembly_ref` before falling back to the old component id.
- Watertight Solid target/profile diagnostics now use Subassembly-first diagnostic names; old component ids appear only as `compatibility_ref` notes.
- Watertight Solid target discovery/profile helper names now use Subassembly-scoped terminology for active pavement/subbase/shoulder target flow; old component wording is limited to compatibility fields and legacy fallback readers.
- Solid target discovery now propagates Subassembly refs for pavement layer, subbase, shoulder, and lined ditch targets when Applied Sections contain Subassembly rows or point provenance.
- Solid profile notes now record Subassembly provenance for component-scoped and lined-ditch profiles.
- Watertight Solid panel source/context text now shows `subassembly=...` first and uses `compatibility_ref=...` only when an old component fallback is still required.
- Watertight Solid pavement, subbase, and shoulder target families are presented as `Subassembly` targets in the panel.
- The main workflow toolbar now places `Assembly / Subassembly` before the legacy Assembly editor, and the old editor command is labeled `Assembly (Legacy)`.
- Applied Sections summary and missing-source diagnostics now name `Assembly / Subassembly` as the active source and identify old Assembly rows as legacy fallback.
- Regions now list Subassembly-based Assembly source ids before legacy Assembly ids and present the reference column as `Assembly Source`.
- Intersection starter source creation now creates `V1IntersectionStarterAssemblySubassembly` from the new Assembly/Subassembly contract when no compatible source already exists.
- Intersection and Intersection Presets panels now explain that starter/preset source creation includes Assembly/Subassembly source intent for Regions and Build Sections.
- Assembly/Subassembly source objects route to `04_Parametric Model > Assemblies` and display the Assembly id in their tree label for easier source selection.
- Exchange source-context rows and package metadata now include `subassembly_ref` so exported traceability can identify the Subassembly owner.
- Exchange source-context rows now emit `component_ref` only when no Subassembly owner exists, and side-slope section context is built from `subassembly_rows` before legacy component rows.
- Exchange side-slope source context now labels legacy component-derived rows as compatibility rows; active side-slope detection uses Subassembly terminology.
- Simulation QA/package inputs, manifest rows, and FreeCAD package objects now preserve `subassembly_refs` for packaged watertight solid outputs.
- Applied Sections review payloads now expose `compatibility_component_count` / `compatibility_component_summary` beside the old keys so new review code can avoid treating `component_rows` as active state.
- Cross Section Viewer internal focused-row helpers now use Subassembly naming; old `focused_component` context is retained only as a fallback input key.
- Section Output quantity rows now leave `component_ref` blank when `subassembly_ref` is present, preserving the old field only for legacy-only quantities.
- Quantity builder count fragments now read `AppliedSection.subassembly_rows` first and use `component_rows` only when no Subassembly rows exist.
- Quantity builder station-fragment rows now keep `subassembly_ref` and `component_ref` separate instead of copying a legacy component id into the Subassembly field.
- Surface transition and supplemental sampling sections now preserve `subassembly_rows` while relying on interpolated point `subassembly_ref` values for generated geometry provenance.
- Cross-section drawing mapper internal span helpers now use Subassembly naming and reserve `component_rows` reads for legacy-only fallback spans.
- Watertight Solid target discovery now reads `AppliedSection.subassembly_rows` directly for pavement, subbase, and shoulder targets before falling back to component compatibility rows.
- Solid profile generation now resolves Subassembly-scoped target dimensions from `subassembly_rows` before using component compatibility rows.
- Solid profile generation now stops falling through to legacy component rows when a section has Subassembly rows but no matching Subassembly target.
- Solid target discovery source summaries now use `compatibility_refs` internally for legacy component provenance while keeping `subassembly_refs` as the active target owner field.
- Corridor solid structure context helpers now inspect Subassembly `structure_ids` before legacy component `structure_ids`.
- Lined ditch solid target discovery now reads ditch Subassembly rows for material and lining thickness before falling back to component compatibility rows.
- Lined ditch solid profile generation now resolves side, material, and lining thickness from ditch Subassembly rows when the target carries `subassembly_ref`.
- Cross Section Viewer now exposes a `Subassembly Results` review table for Subassembly point/link/shape rows.
- Cross Section Viewer quantity rows now display `subassembly_ref` first and use old `component_ref` only as fallback text.
- Cross Section Viewer source-inspector detail rows now read `subassembly_id`, `subassembly_kind`, and `subassembly_side` first, with old `component_*` keys treated as compatibility fallback.
- Cross Section Viewer source-inspector fallback values from old `component_*` keys now display with a `compatibility:` prefix.
- Section viewer payload construction now keeps `component_*` inspector keys for actual compatibility rows only instead of copying active Subassembly values into them.
- Cross Section Viewer source-owner helpers now stop falling through to legacy component rows when Subassembly rows exist but do not carry a matching template, region, structure, or drainage ref.
- Simulation QA source refs now include Subassembly, Structure, FlowRoute, and original solid source refs from built watertight solid inputs, instead of only listing the output object refs.

### Phase S9: Documentation And Wiki Cutover

Status: in progress

Work:

- update `V1_ASSEMBLY_MODEL.md`
- update `V1_SECTION_MODEL.md`
- update `V1_SECTION_OUTPUT_SCHEMA.md`
- update Drainage, Superelevation, Watertight Solid, Surface, Viewer, and wiki documents
- record the breaking terminology decision in the master plan

Acceptance:

- active docs use Subassembly for the cross-section building unit
- `Component` appears only in historical notes or explicit deprecated-term sections

Implementation notes:

- `V1_ASSEMBLY_MODEL.md` now names `TemplateSubassembly` and `SubassemblySectionTemplate` as the active contracts and moves `TemplateComponent` into a deprecated compatibility section.
- `V1_SECTION_MODEL.md` and `V1_SECTION_OUTPUT_SCHEMA.md` now describe Subassembly ids/kinds/rows as the preferred contract.
- Wiki user pages for Assembly/Region, Applied Sections/Build Corridor, Drainage, and Superelevation now use Subassembly wording for current workflows.
- Exchange and Watertight Solid docs now describe `subassembly_ref` as the preferred traceability field while documenting `component_ref` as compatibility provenance.

### Phase S10: Removal Of Compatibility Fields

Status: in progress

Work:

- remove source/result/output compatibility aliases such as `component_rows`
- remove `component_id`, `component_ref`, and `component_kind` from active v1 contracts
- remove old UI labels
- remove old mapper fallback paths

Removal inventory:

| Area | Current dependency | S10 position |
| --- | --- | --- |
| Cross Section Viewer labels | Visible `Component` wording leaked from compatibility fields | Replace visible wording with `Subassembly`; keep internal compatibility keys until builders move fully |
| `AppliedSection.component_rows` | Build Sections, surface builders, solid target discovery, and exchange mappers still read it as a compatibility cache | Keep temporarily; remove after direct `subassembly_rows` consumption is verified end to end |
| `component_ref` provenance | Quantity, surface, watertight solid, and exchange rows still carry it beside `subassembly_ref` | Stop presenting it as active terminology first; remove after downstream contracts use `subassembly_ref` only |
| Old Assembly editor/object bridge | Still useful as a transition path for existing commands | Do not delete before the new Assembly / Subassembly editor is the default toolbar path |
| Drainage Subassembly reference | Drainage now carries `subassembly_ref` for ditch-related source intent; new object/editor writes do not synchronize the old assembly-component field | Keep old object-property reads only as temporary fallback, then remove the fallback field from the source model |

S10 dependency classes:

| Class | Meaning | Action |
| --- | --- | --- |
| Active Subassembly contract | `TemplateSubassembly`, `SubassemblySectionTemplate`, `AppliedSection.subassembly_rows`, Subassembly point/link/shape rows | Keep and expand |
| Compatibility cache | `AppliedSection.component_rows`, `SectionOutput.component_rows`, `component_ref` output fields | Keep readable, stop presenting as active, remove after direct Subassembly consumers are complete |
| Legacy editor bridge | old Assembly editor `TemplateComponent` table/object fields | Keep until the Assembly / Subassembly editor is the default path, then hide or remove |
| Deprecated provenance | copied `component_ref` values on rows that also have `subassembly_ref` | Suppress immediately where found |

S10 file inventory:

| File or area | Class | Next action |
| --- | --- | --- |
| `services/builders/applied_section_service.py` | Compatibility cache generator | Keep `component_rows` generation named as compatibility until all downstream consumers read Subassembly point/link rows directly |
| `commands/cmd_assembly_editor.py` | Legacy editor bridge | Keep temporarily; panel title, source label, and status text now mark it as legacy compatibility editing |
| `models/source/assembly_model.py` | Source compatibility bridge | `TemplateComponent`, `SectionTemplate`, and `AssemblyModel` docstrings now identify the old component contract as compatibility/legacy; active authoring uses `TemplateSubassembly` |
| `models/result/applied_section.py` | Result compatibility cache | Result docstrings now identify `component_rows`, `component_ref`, and `component_id` as legacy compatibility provenance/cache |
| `models/output/section_output.py` | Output compatibility cache | Keep `SectionComponentRow` as legacy output row; new outputs should prefer `SectionSubassemblyRow` and leave component rows empty when Subassemblies exist |
| Surface, Quantity, Solid, Exchange mappers | Compatibility readers | Continue converting reads to `subassembly_ref` first and emit `component_ref` only when no Subassembly owner exists |
| UI viewers | Compatibility display | Show Subassembly counts first; expose old rows only as `Compatibility Fallback Rows` |

Acceptance:

- new documents created by Parametric Road no longer store active component fields
- focused tests fail if active source/result/output contracts reintroduce component fields

Implementation notes:

- Cross Section Viewer now displays Subassembly labels and counts first, with component compatibility rows used only as fallback data.
- Cross Section Viewer Subassembly tables now mark legacy fallback rows with a `compatibility:` prefix instead of displaying old component ids as active Subassembly ids.
- Source Inspector count rows now show `subassembly_count` first and hide old Component wording behind `Compatibility Fallback Rows`.
- Cross Section preview text now labels old section output rows as `Compatibility Fallback Rows`, not Subassembly rows.
- Cross-section drawing mapper span generation now names active Subassembly rows separately from legacy compatibility fallback rows.
- Cross-section drawing mapper now isolates active-vs-compatibility span row selection in a dedicated helper, making the remaining `component_rows` fallback removable in S10.
- Cross Section Viewer summary counts now keep `Subassemblies` and `Compatibility Fallback Rows` separate instead of counting compatibility rows as Subassemblies.
- SectionOutput compatibility row docs now label `SectionComponentRow` as a legacy compatibility row, not the active output contract.
- SectionOutput mapping now builds legacy component rows through an explicit `_compatibility_component_rows` helper and returns none when Subassembly rows exist.
- The old Assembly editor panel now presents itself as `Assembly (Legacy)` and labels row operations as compatibility-row editing; new road-section authoring should use Assembly / Subassembly.
- Assembly source model docs and side-slope bench validation messages now label old `TemplateComponent` rows as compatibility rows, while Subassembly validation still reports Subassembly wording.
- Watertight Solid and Exchange docs now describe Subassembly-scoped targets and reserve old component wording for explicit compatibility notes.
- Drainage Review output notes now report ditch context and flowline traceability as `subassembly_ref` / `subassembly_refs`.
- DrainageElementRow now carries `subassembly_ref` for ditch-owned drainage elements; the old active `assembly_component_ref` field has been removed from the source row.
- Drainage validation and Build Parametric ditch-surface diagnostics now prefer `subassembly_ref` and warn when open-channel drainage elements do not reference a Subassembly.
- Drainage Review notes now separate active `subassembly_ref` values from old `compatibility_ref` values instead of displaying legacy component refs as Subassembly refs.
- Drainage validation requires a real `subassembly_ref` for open-channel elements.
- The Drainage editor table displays only the active `subassembly_ref` in the Subassembly column.
- Drainage Review flowline grouping now uses `subassembly_ref` before legacy `component_ref`, and only emits `compatibility_ref` when no Subassembly owner exists.
- Surface point-grid and side-slope provenance rows now emit compatibility component refs only when no Subassembly owner exists.
- Surface point-grid and side-slope source summaries now use `compatibility_refs` internally instead of `component_refs`, while keeping `subassembly_refs` as the active provenance field.
- Surface provenance now centralizes point `subassembly_ref` / `compatibility_ref` extraction so old `component_ref` values are suppressed whenever a Subassembly owner exists.
- Quantity fragments and Quantity output rows now keep `subassembly_ref` as the active owner reference; `component_ref` is emitted only when no Subassembly owner is available.
- Quantity drainage ditch/flowline length provenance now collects point compatibility refs only from points without a `subassembly_ref`.
- Quantity direct-row structure lookup now stops falling through to legacy Component rows when a section already has Subassembly rows.
- Quantity output mapping no longer promotes `component_ref` into `subassembly_ref` for Watertight Solid quantity rows.
- Exchange package metadata now reports `compatibility_ref_count` beside `subassembly_ref_count` so QA can verify exported source context does not expose legacy component refs when a Subassembly owner exists.
- Section output quantity rows now use only `fragment.subassembly_id` for `subassembly_ref`; old `fragment.component_id` remains compatibility provenance only.
- Applied Section ditch surface and flowline points are now generated from `TemplateSubassembly` rows first, writing `subassembly_ref` directly and leaving `component_ref` blank for Subassembly-owned ditch geometry.
- Legacy `TemplateComponent` ditch rows remain a fallback only when no ditch Subassembly rows are available.
- Applied Section ditch validation messages now use `ditch subassembly` wording and identify `subassembly_id` when available; legacy component ids appear only as compatibility identifiers.
- Applied Section side-slope daylight and terrain diagnostics now use `side-slope subassembly` wording and write `subassembly_ref` before compatibility identifiers.
- Applied Section builder docstrings now describe active geometry inputs as Subassembly or section rows instead of active Components; `component_rows` remains compatibility-only language.
- Applied Section compatibility component cache generation is now named `_build_compatibility_component_rows` so active builders do not present legacy `component_rows` as the primary contract.
- Applied Section result model docs now identify `subassembly_rows` and Subassembly point/link/shape rows as the active result contract, with `component_rows` and `component_ref` retained only for compatibility.
- The Applied Section point backfill helper is now explicitly compatibility-scoped. When a legacy point `component_ref` matches a real Subassembly id, it promotes that point to `subassembly_ref` and clears `component_ref`; unmatched legacy component refs stay compatibility-only.
- Applied Section now creates Subassembly-owned FG and subgrade endpoint rows directly from lane/shoulder/curb/gutter-style Subassembly widths, without adding duplicate legacy `point_rows`.
- These direct FG/subgrade Subassembly point rows create `design_surface` and `subgrade_surface` links while keeping legacy surface point rows stable for current Build Parametric outputs.
- Applied Section now mirrors evaluated side-slope, bench, and daylight break points into Subassembly-owned point rows when matching `side_slope` Subassembly rows exist.
- These side-slope Subassembly point rows create `slope_face_surface` links for the result contract while keeping the existing compatibility Slope Face surface generation unchanged.
- Build Parametric surface geometry now reads linked `AppliedSectionSubassemblyPoint` rows directly when Subassembly surface links exist, instead of filtering only legacy `point_rows`.
- The Slope Face surface point selection now accepts Subassembly-owned `side_slope_surface`, `bench_surface`, and `daylight_marker` points as the preferred geometry source.
- Surface transition and supplemental generated sections now drop legacy `component_rows` when Subassembly rows are present, keeping compatibility rows only for legacy-only sections.
- QuantityModel source refs now include Subassembly refs from Applied Section Subassembly point and link rows, not only row/shape summaries.
- Watertight Solid profile and target discovery compatibility helpers now resolve matching Subassembly refs from `AppliedSectionSubassemblyPoint` rows before falling back to old component provenance.
- Watertight Solid target discovery now names legacy component-to-Subassembly resolution as a compatibility-component helper.
- Simulation QA and package handoff traceability now carries Subassembly refs through the watertight-solid QA source refs and packaged solid rows.
- Structure solid context lookup now treats `AppliedSection.subassembly_rows` as authoritative. Legacy `component_rows` are inspected only when no Subassembly rows exist for that section.
- Corridor solid structure-ref lookup now uses one Subassembly-first helper, keeping the legacy `component_rows` fallback isolated.
- Build Parametric applied-section review summaries now read structure context from `subassembly_rows` before falling back to legacy compatibility rows.
- Build Parametric structure-ref review lookup now uses the same Subassembly-first helper pattern and keeps legacy component rows as fallback-only.
- Watertight Solid lined-ditch provenance diagnostics now suppress `compatibility_ref` when a `subassembly_ref` owner is present, matching the output row behavior.
- Solid profile lined-ditch lookup helper is now named as a Subassembly-or-compatibility row resolver instead of presenting ditch Component lookup as the active path.
- Solid profile Subassembly body lookup now uses a Subassembly-or-compatibility row resolver and names legacy component-to-Subassembly matching as compatibility-only.
- Watertight Solid intersection surface-zone target discovery no longer writes intersection zone ids into `component_ref`; zone identity stays in source refs and notes.
- Earthwork Review side-slope quantity source notes now report `subassembly_ref` first and expose old component provenance only as `compatibility_ref`.
- Surface interpolation now suppresses legacy `component_ref` values whenever generated/interpolated points resolve a `subassembly_ref` owner.
- Cross Section Viewer source inspector rows no longer use legacy `component_*` fields as Subassembly fallbacks; old values are displayed only as explicit Compatibility rows.
- Applied Section generation now leaves `component_rows` empty when active `subassembly_rows` are available; compatibility component cache rows are generated only for legacy-only sections.
- Cross Section Viewer inspector payloads now expose `compatibility_component_count` as the preferred count key while keeping `component_count` only as an old payload fallback.
- Quantity side-slope length fragments now use real point compatibility refs only; generated point ids are no longer written into `component_ref`.
- Watertight Solid target discovery no longer reconstructs legacy `component_ref` values for Subassembly-owned assembly and lined-ditch targets.
- Watertight Solid profile generation now ignores `component_ref` lookup/notes whenever the target already carries an active `subassembly_ref`.
- Watertight Solid panel labels and source text now display legacy-only target refs with a `compatibility:` prefix instead of presenting `component_ref` as an active Subassembly ref.
- Exchange source-context payloads now expose legacy component provenance through `compatibility_ref`; compatibility counts also use that field instead of treating `component_ref` as active context.
- Applied Sections review table now uses an explicit Subassembly summary helper and labels legacy-only row counts as `compatibility:<count>`.
- Build Parametric structure review now isolates legacy `component_rows` structure refs in a compatibility helper after Subassembly rows are checked first.
- Cross-section drawing span rows now expose active Subassembly ids as source refs and prefix legacy-only fallback span refs with `compatibility:`.
- Earthwork Review compatibility-only source tokens now prefix old component provenance with `compatibility:` while keeping active `subassembly_ref` separate.
- Exchange source-context rows now keep legacy component provenance only in `compatibility_ref`; the old `component_ref` source-context field is emitted empty.
- SectionOutput summary rows now emit `compatibility_component_count` for legacy fallback rows instead of creating new `component_count` summaries.
- Cross Section Viewer source-inspector payload generation now emits `compatibility_component_count` only; `component_count` remains a viewer-side fallback for old payloads.
- Cross Section Viewer now isolates legacy `component_rows` reads behind compatibility fallback helpers for table/count/source-row selection.
- Cross Section Viewer command payload construction now reads legacy SectionOutput and AppliedSection component rows only through compatibility fallback helpers.
- Drainage Review flowline and ditch-context notes now prefix legacy component fallback refs with `compatibility:` while keeping `subassembly_ref` as the active owner.
- Quantity and Watertight Solid output mappers now name legacy `component_ref` handling as compatibility-component provenance; Watertight Solid diagnostics display legacy refs with a `compatibility:` prefix.
- Applied Section Service now names shared drainage-ref and width helpers as section-row helpers because they serve active Subassembly rows as well as compatibility rows.
- Applied Section Service now exposes ditch section-row profile and validation helpers for active Subassembly rows; old `ditch_component_*` names remain compatibility aliases for legacy Assembly editor callers.
- Applied Section bench profile calculation now uses neutral section-row naming internally; `_bench_component_rows` remains compatibility-specific because it emits legacy `AppliedSectionComponentRow` cache rows.
- Applied Sections review payloads no longer emit new `component_count` / `component_summary` keys; the panel still reads those keys only as old-payload fallbacks.
- Cross Section Viewer source-inspector payloads now emit `compatibility_component_*` keys for legacy fallback rows instead of creating new `component_*` fields; the viewer still reads old keys only as old-payload fallback.
- Structure solid quantity fragments no longer write solid output object ids into `component_ref`; structure provenance stays in `structure_ref` and fragment ids.
- SectionOutput quantity rows now read current `QuantityFragment.subassembly_ref` / `component_ref` fields, suppressing compatibility component refs whenever a Subassembly owner exists.
- Solid target discovery now labels target row kind notes as `source_kind` instead of `compatibility_kind` for Subassembly-owned targets.
- Drainage surface grouping now uses the centralized compatibility-ref helper so legacy `component_ref` is ignored whenever a point already has `subassembly_ref`.
- Solid target discovery now emits `scope_kind=assembly_subassembly` for Subassembly-scoped road-section targets; `assembly_component` remains a legacy accepted scope kind.
- Watertight Solid panel scope text now displays both `assembly_subassembly` and legacy `assembly_component` as `Subassembly` instead of exposing raw enum names.
- Exchange source-context row builders now write `compatibility_ref` directly for legacy component provenance; `component_ref` is kept only as an old-payload normalization input and is cleared in normalized rows.
- Drainage editor preset materialization no longer reads old `component` keys; preset data must provide active `subassembly` refs directly.
- Assembly/Subassembly editor preset materialization now reads active `subassemblies` rows first; shared old Assembly `components` presets are converted only through an explicit compatibility helper.
- Shared Assembly presets now populate active `subassemblies` rows at module load, so the new Assembly/Subassembly editor can consume Subassembly rows without duplicating every preset literal.
- Applied Section bench evaluation now stores its owner as `source_row`; the old `component` accessor remains only as a compatibility alias for transitional helper code.
- Build Sections command now isolates the temporary Subassembly-to-AssemblyModel request bridge in `_request_assembly_models`; active source discovery remains `AssemblySubassemblyModel` first.
- Applied Section surface width, subgrade depth, and daylight policy calculations now read `SubassemblySectionTemplate.subassembly_rows` first and use legacy `SectionTemplate.component_rows` only as fallback.
- Applied Section FG offset, ditch point, bench evaluation, and ditch/bench validation helpers now consume active Subassembly rows first; legacy component rows remain fallback inputs only.
- Applied Section side-slope and bench `point_rows` now carry `subassembly_ref` directly for active Subassembly rows; `component_ref` is filled only for legacy compatibility rows.
- Quantity builder legacy `component_rows` reads are now isolated behind a compatibility helper and are skipped whenever active `subassembly_rows` exist.
- Solid target discovery now uses a single Subassembly-or-compatibility row helper for assembly target and lined-ditch discovery, keeping old component rows as fallback-only input.
- Solid profile generation now names active Subassembly/legacy inputs as `source_row` and reads legacy component rows only through compatibility helpers.
- Cross Section Viewer command and UI helpers now suppress legacy SectionOutput component rows whenever active Subassembly rows are present.
- Exchange output source-context mapping now reads SectionOutput component rows only through a compatibility helper that is disabled when Subassembly rows exist.
- SectionOutput model docstrings now state that `component_rows` and quantity `component_ref` are legacy compatibility provenance, not active section ownership.
- Assembly source model docstrings now mark `TemplateComponent`, `SectionTemplate`, and `AssemblyModel` as deprecated compatibility contracts, and Subassembly bench validation isolates its legacy validation proxy in a compatibility helper.
- Exchange source-context normalization now moves legacy `component_kind` into `compatibility_component_kind` and clears `component_kind`, matching the existing `component_ref` to `compatibility_ref` behavior.
- The legacy Assembly editor now labels its table id and add-row action as compatibility rows instead of presenting old Component rows as active authoring units.

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

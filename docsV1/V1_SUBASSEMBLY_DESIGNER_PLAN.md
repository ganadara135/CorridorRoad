# Parametric Road V1 SubAssembly Designer Plan

Date: 2026-06-15

Status: in progress

## Purpose

This document defines the plan for introducing a dedicated SubAssembly Designer to Parametric Road v1.

The SubAssembly Designer is the authoring surface for reusable cross-section building blocks.

It does not replace the Assembly editor.

It creates and manages Subassembly definitions that the Assembly editor can place, order, and combine.

## Scope

This plan covers:

- Subassembly definition source model
- Subassembly library and preset handling
- point, link, shape, code, and parameter authoring
- 2D preview and validation
- Assembly editor integration
- Applied Sections evaluation integration
- Build Parametric, quantity, drainage, and watertight solid handoff rules
- documentation and QA requirements

This plan does not cover:

- Civil 3D `.pkt` runtime import
- full visual scripting
- automatic engineering design-code selection
- replacing the current Assembly editor in the first implementation slice

## Core Rule

SubAssembly Designer owns reusable cross-section behavior.

Assembly owns placement and ordering.

Applied Sections owns station-based evaluation.

Build Parametric owns generated surfaces, solids, and review outputs.

```text
SubAssembly Designer
  -> SubassemblyDefinition / SubassemblyLibrary source rows
  -> Assembly TemplateSubassembly placement rows
  -> AppliedSectionSubassemblyRow evaluation
  -> SectionOutput point/link/shape rows
  -> surfaces, quantities, solids, review, exchange
```

## Design Goals

- Make Subassembly reusable instead of only row-local inside Assembly.
- Keep v1 source intent separate from generated geometry.
- Let users create simple native Subassemblies without writing Python.
- Keep first implementation practical and table-driven.
- Preserve traceability from generated points, links, shapes, quantities, surfaces, and solids back to the source Subassembly definition.
- Support later expansion into more advanced authoring modes.

## Object Families

### SubassemblyDefinition

One reusable Subassembly definition.

Recommended fields:

- `definition_id`
- `name`
- `kind`
- `category`
- `side_behavior`
- `parameter_rows`
- `point_rows`
- `link_rows`
- `shape_rows`
- `code_rows`
- `target_rows`
- `quantity_rows`
- `surface_role_rows`
- `material_rows`
- `enabled`
- `notes`

### SubassemblyLibrary

A source object that stores multiple reusable definitions.

Recommended fields:

- `schema_version`
- `project_id`
- `library_id`
- `definition_rows`
- `preset_name`
- `source_refs`
- `diagnostics`

### TemplateSubassembly

Existing Assembly placement row.

It should reference a Subassembly definition when available.

Recommended additions:

- `definition_ref`
- `parameter_overrides`
- `placement_side`
- `placement_index`
- `enabled`

Active Assembly UX rule:

- Assembly is a placement table, not a definition table.
- Show `Enabled`, `Subassembly ID`, `Subassembly Ref`, `Side`, `Index`, `Target Ref`, and `Notes`.
- Keep Kind, width, slope, thickness, and material in SubAssembly Designer or its parameter rows.
- Let `Selected Subassembly Detail` edit placement-specific overrides.
- Store only changed values as row-local `parameter_overrides`.

## Subassembly Row Families

### Parameters

Parameters define user-editable values.

Examples:

- `width`
- `slope`
- `thickness`
- `ditch_depth`
- `ditch_bottom_width`
- `curb_height`
- `material`
- `daylight_slope`

Each row should include:

- `parameter_id`
- `label`
- `value`
- `unit`
- `min_value`
- `max_value`
- `required`
- `notes`

### Points

Points define named cross-section coordinates relative to an anchor point.

Each row should include:

- `point_id`
- `x_expr`
- `z_expr`
- `code`
- `role`
- `connectable`
- `notes`

### Links

Links connect points.

Each row should include:

- `link_id`
- `start_point_ref`
- `end_point_ref`
- `surface_role`
- `code`
- `material`
- `quantity_role`
- `notes`

### Shapes

Shapes define closed areas for materials, quantities, and watertight solid profiles.

Each row should include:

- `shape_id`
- `point_refs`
- `shape_code`
- `material`
- `quantity_role`
- `solid_role`
- `closed`
- `notes`

### Targets

Targets define optional external control references.

Examples:

- terrain daylight target
- ditch flowline target
- curb-return tie-in
- structure port
- drainage element

Each row should include:

- `target_id`
- `target_kind`
- `required`
- `fallback_policy`
- `notes`

## UI Plan

Add a new toolbar stage:

```text
... -> Superelevation -> SubAssembly Designer -> Assembly -> Regions -> ...
```

The existing Assembly editor remains.

### Panel Layout

Recommended layout:

- top definition table for selecting reusable definitions
- `Selected Definition Detail` section below the definition table
- left side of `Selected Definition Detail` for source table tabs
- right side of `Selected Definition Detail` for fixed `Live Preview`
- `Auto Preview` enabled by default

Selected Definition Detail tabs:

- `Definitions`
- `Parameters`
- `Points`
- `Links`
- `Shapes`
- `Diagnostics`

Selected Definition Detail preview area:

- 2D cross-section preview
- Refresh Preview button
- Auto Preview toggle
- preview status and expression diagnostics summary

### Definitions Tab

Purpose:

- create, duplicate, rename, delete, and select Subassembly definitions
- choose stable `Kind`, `Category`, `Side`, and `Enabled` values from combo boxes

Controls:

- Preset selector
- Load Preset
- Add Definition
- Duplicate
- Delete Selected
- Apply

Combo fields:

- `Kind`: lane, shoulder, side_slope, ditch, lined_ditch, curb, gutter, pavement_layer, subbase, structure_interface, intersection_transition, curb_return_transition, custom
- `Category`: roadway, pavement, grading, drainage, roadside, structure, earthwork, custom
- `Side`: left, right, center, both, agnostic
- `Enabled`: Yes, No
- Apply

### Parameters Tab

Purpose:

- edit user-facing parameters

Table columns:

- Parameter ID
- Label
- Value
- Unit
- Required
- Min
- Max
- Notes

### Points Tab

Purpose:

- define generated cross-section points

Table columns:

- Point ID
- X Expression
- Z Expression
- Code
- Role
- Connectable
- Notes

### Links Tab

Purpose:

- define generated linework and surface ownership

Table columns:

- Link ID
- From Point
- To Point
- Surface Role
- Code
- Material
- Quantity Role
- Notes

### Shapes Tab

Purpose:

- define closed profiles for material, quantity, and solid output

Table columns:

- Shape ID
- Point Refs
- Shape Code
- Material
- Quantity Role
- Solid Role
- Closed
- Notes

### Live Preview Area

Purpose:

- show the selected Subassembly as a single 2D cross-section preview
- show point labels, link roles, shape fill, and anchor point
- expose validation diagnostics before the Subassembly is used in Assembly
- stay visible while Parameters, Points, Links, Shapes, and Targets are edited
- update immediately when `Auto Preview` is enabled

### Diagnostics Tab

Purpose:

- show blocking errors and warnings
- report downstream readiness for Assembly, Applied Sections, Build Parametric, quantities, and solids

## Initial Presets

First-slice presets should be practical and small:

- `lane`
- `shoulder`
- `subbase`
- `ditch`
- `lined_ditch`
- `curb`
- `gutter`
- `sidewalk`
- `daylight_slope`

The existing built-in Assembly rows should be converted into Subassembly definitions where practical.

## Evaluation Plan

### Designer Validation

Validate before Apply:

- duplicate ids
- missing required parameters
- invalid expressions
- missing point refs in links
- missing point refs in shapes
- open shape where `closed = true`
- surface role not recognized
- quantity role not recognized
- solid role without closed shape
- target required but no fallback policy

### Applied Sections Evaluation

Applied Sections should:

- resolve `TemplateSubassembly.definition_ref`
- apply row-local parameter overrides
- evaluate point expressions
- emit `AppliedSectionSubassemblyRow`
- emit Subassembly point/link/shape rows
- preserve source refs to definition, template row, and region

### Build Parametric Handoff

Build Parametric should consume evaluated link roles:

- `design_surface`
- `subgrade_surface`
- `slope_face_surface`
- `drainage_surface`
- `structure_interface`

It should not evaluate Subassembly expressions directly.

Designer-friendly role aliases such as `design`, `subgrade`, `slope_face`, and `drainage` are normalized during Applied Sections evaluation.

### Quantity Handoff

Quantity builders should consume evaluated shape and link rows.

They should not inspect Designer source rows directly except for source traceability.

### Watertight Solid Handoff

Watertight Solid target discovery should use evaluated closed shapes and solid roles.

Designer definitions should only declare whether a shape is eligible for solid generation.

## Data Flow

```text
SubAssembly Designer
  creates SubassemblyLibrary / SubassemblyDefinition source

Assembly
  places definitions through TemplateSubassembly rows

Regions
  choose which Assembly applies by station range

Applied Sections
  evaluates Subassemblies per station and context

Build Parametric
  builds surfaces from evaluated link roles

Quantity / Watertight Solids / Exchange
  consume evaluated rows and preserve source refs
```

## Implementation Plan

| Phase | Status | Work |
| --- | --- | --- |
| 1. Source model | Done | Add `SubassemblyDefinition`, row dataclasses, and `SubassemblyLibrary` source model. |
| 2. Object bridge | Done | Add FreeCAD object persistence for `V1SubassemblyLibrary`. |
| 3. Preset data | Done | Move built-in lane, shoulder, ditch, curb/gutter examples into reusable Subassembly presets. |
| 4. Designer command | Done | Add toolbar command and task panel skeleton after Superelevation and before Assembly. |
| 5. Definition editing | Done | Add Definitions, Parameters, Points, Links, Shapes tables with Apply persistence. |
| 6. Expression evaluator | Done | Add deterministic parameter expression evaluation for point coordinates. |
| 7. Preview | Done | Add 2D preview for selected Subassembly definition. |
| 8. Validation | Done | Add validation diagnostics for ids, refs, expressions, closed shapes, roles, and targets. |
| 9. Assembly integration | Done | Let Assembly rows select `definition_ref` and persist row-local `parameter_overrides`. |
| 10. Applied Sections integration | Done | Resolve definitions during Build Sections and emit evaluated Subassembly point/link/shape rows. |
| 11. Build Parametric QA | Done | Confirm surfaces consume evaluated link roles only. |
| 12. Quantity and solid QA | Done | Confirm shape roles feed quantities and Watertight Solid target discovery. |
| 13. Docs and Wiki | Done | Update user workflow docs and add a Wiki page for SubAssembly Designer. |
| 14. Manual QA | Pending | Run FreeCAD workflow from Designer -> Assembly -> Applied Sections -> Build Parametric -> Cross Section Viewer. |

## Acceptance Criteria

- User can create a Subassembly definition without editing code.
- User can preview a selected Subassembly definition before using it in Assembly.
- Assembly can place a Designer-created Subassembly.
- Applied Sections can evaluate placed definitions at stations.
- Cross Section Viewer shows evaluated point/link/shape rows with source traceability.
- Build Parametric surfaces are still generated from evaluated result rows, not Designer source rows.
- Quantity and Watertight Solid paths preserve `subassembly_ref`.
- Existing v1 source/evaluation/result/output layering remains intact.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Expression language becomes too complex | Hard to validate and debug | Start with simple parameter arithmetic only. |
| Designer duplicates Assembly responsibilities | Confusing UX | Designer defines reusable behavior; Assembly places and orders definitions. |
| Build Parametric starts reading Designer source directly | Breaks v1 layering | Keep Build Parametric result-driven through Applied Sections. |
| Too many presets before the contract stabilizes | Preset churn | Start with small road primitives and expand later. |
| User expects Civil 3D `.pkt` compatibility | Misleading import expectations | Document `.pkt` as non-runtime future import-assist only. |

## Implementation Notes

- Phase 1 added the reusable `SubassemblyDefinition` and `SubassemblyLibrary` source model.
- Phase 2 added `V1SubassemblyLibrary` FreeCAD object persistence.
- The bridge stores definition rows as JSON strings and restores typed parameter, point, link, shape, and target rows.
- `v1_subassembly_library` objects route to `04_Parametric Model > Assemblies`.
- Phase 3 added a starter Subassembly definition library preset with lane, shoulder, side-slope, trapezoid ditch, gutter pan, and curb definitions.
- The preset helper creates a `SubassemblyLibrary` source model for the future Designer UI without changing active Assembly placement rows yet.
- Phase 4 added the `SubAssembly Designer` toolbar command after Superelevation and before Assembly.
- The first panel slice can load reusable Subassembly presets, inspect definition details, and apply a `V1SubassemblyLibrary` source object under `04_Parametric Model > Assemblies`.
- Phase 5 made the Designer source tables editable for Definitions, Parameters, Points, Links, Shapes, and Targets.
- Phase 9 connected Assembly rows to reusable Subassembly definitions through `definition_ref` and row-local `parameter_overrides`.
- Phase 10 connected Build Sections to Subassembly libraries.
- Applied Sections now resolve `TemplateSubassembly.definition_ref`, apply `parameter_overrides`, evaluate definition point expressions, and emit definition-owned Subassembly point/link/shape result rows.
- The evaluated result rows preserve `definition_ref` on `AppliedSectionSubassemblyRow`; downstream builders should continue to consume Applied Sections results rather than Designer source rows directly.
- Phase 11 confirmed Build Parametric surface generation consumes evaluated `subassembly_link_rows.surface_role` ownership.
- Applied Sections normalize Designer link aliases such as `design` to `design_surface` before downstream surface builders consume them.
- Build Parametric surface point grids now trust link-owned Subassembly points even when Designer point codes are engineering codes such as `CROWN` or `ETW`.
- Phase 12 connected evaluated `subassembly_shape_rows` to quantity and Watertight Solid handoff.
- Quantity now emits section shape-area fragments from evaluated Subassembly shape point refs.
- Watertight Solid target discovery can create `assembly_subassembly` targets from evaluated shapes with `solid_family`, without reading Designer source definitions directly.
- Phase 13 added the `SubAssembly Designer` GitHub Wiki draft page and linked it from the wiki TOC, Home, Quick Start, Workflow, Assembly/Region, Applied Sections/Build Corridor, and docsV1 README.
- The wiki now states the active ownership chain: Designer definitions -> Assembly placement and overrides -> Applied Sections evaluation -> Build Parametric, Quantity, and Watertight Solid consumption.
- Apply now rebuilds the `SubassemblyLibrary` source model from the UI tables before persisting it to the FreeCAD object.
- Phase 6 added `SubassemblyExpressionService` for deterministic parameter arithmetic and point coordinate evaluation.
- The evaluator accepts numeric constants, parameter names, and arithmetic operators only; function calls, attributes, indexing, and other Python syntax are rejected with diagnostics.
- Phase 7 added a Designer preview that evaluates the selected definition and renders points, links, and closed shapes as a 2D cross-section preview.
- Preview uses the same expression service planned for later Applied Sections integration, keeping UI visualization separate from generated corridor geometry.
- The preview is now a right-side `Live Preview` pane inside `Selected Definition Detail` rather than a hidden tab, so parameter and geometry edits can be reviewed without changing tabs.
- Phase 8 added `SubassemblyDefinitionValidationService` and a Designer `Diagnostics` tab.
- Validation checks duplicate ids, missing required parameter values, link/shape point references, closed-shape point counts, solid-shape closure, surface-role warnings, required target fallback policy, and expression diagnostics.
- Designer `Apply` now blocks persistence when validation status is `error`.

## Non-goals

- Full Civil 3D Subassembly Composer parity.
- Running imported `.pkt` logic.
- Visual node graph authoring in the first slice.
- Direct editing of generated Applied Section geometry.
- Replacing the current Assembly editor immediately.

## Manual QA Checklist

1. Open SubAssembly Designer.
2. Load the starter `lane` preset.
3. Preview the definition.
4. Apply the definition library.
5. Open Assembly.
6. Place the `lane` definition on left and right sides.
7. Build Applied Sections.
8. Open Cross Section Viewer and confirm Subassembly source refs are visible.
9. Build Parametric and confirm Design Surface uses evaluated links.
10. Run Quantity review and confirm shape/link roles are preserved where available.

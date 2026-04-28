# CorridorRoad V1 Assembly Model

## Purpose

`AssemblyModel` defines reusable cross-section intent for corridor regions.

It is source data.

It is not generated corridor geometry.

## Scope

The first v1 Assembly slice covers:

- roadway lanes
- shoulders
- medians and curbs
- side slopes
- ditches
- barriers
- pavement and subbase layers
- structure interface placeholders

## Core Rule

Regions decide where an assembly applies.

Assemblies decide what section components are available at that station.

Applied sections and corridor solids are downstream results.

## Design Goals

- Keep component intent editable before corridor generation.
- Let `RegionRow.assembly_ref` point to a durable `AssemblyModel`.
- Keep bridge, ramp, intersection, and drainage behavior explicit through references and layers.
- Avoid storing engineering meaning inside viewer geometry.

## Object Families

- `AssemblyModel`
- `SectionTemplate`
- `TemplateComponent`
- future `AssemblyPolicySet`
- future `AssemblyVariant`

## Root Fields

`AssemblyModel` uses:

- `schema_version`
- `project_id`
- `assembly_id`
- `alignment_id`
- `active_template_id`
- `template_rows`
- `source_refs`
- `diagnostic_rows`

## Template Fields

`SectionTemplate` uses:

- `template_id`
- `template_kind`
- `template_index`
- `label`
- `component_rows`
- `notes`

## Component Fields

`TemplateComponent` uses:

- `component_id`
- `component_index`
- `kind`
- `side`
- `width`
- `slope`
- `thickness`
- `material`
- `target_ref`
- `parameters`
- `enabled`
- `notes`

For `kind = "ditch"`, shape-specific intent should be stored in `parameters`.

The governing shape contract is `docsV1/V1_DITCH_SHAPE_CONTRACT.md`.

Recommended `parameters["shape"]` values include `trapezoid`, `u`, `l`, `rectangular`, `v`, and `custom_polyline`.

The current Assembly editor preserves component parameters through a raw `Parameters` column using `key=value;key=value` text.

It also provides a first-slice `Ditch Parameters` helper panel.

The helper panel reads the selected `ditch` row, edits common shape parameters, and writes them back to the raw `Parameters` column.

It shows only the fields that are relevant to the selected ditch shape and can load starter defaults for common shapes.

It also shows a compact shape diagram so users can understand the selected cross-section before applying it.

It reads the selected component `material` and shows material-specific guidance.

Lined materials expose `lining_thickness`.

Structural materials such as concrete or precast require `wall_thickness` for U, L, and rectangular ditches.

## Relationships

`RegionRow.assembly_ref` should reference `AssemblyModel.assembly_id`.

`RegionRow.template_ref` may reference `SectionTemplate.template_id` until richer Assembly lookup is implemented.

`target_ref` may point to drainage, structure, override, or other domain sources when a component is tied to a specific external control.

The Region editor should list existing v1 Assembly ids for `assembly_ref`.

If a Region references an Assembly id that does not exist in the document, validation should show a warning and preserve the entered source value.

`AppliedSectionService` should consume Region context through `RegionResolutionService.resolve_handoff`.

If `RegionRow.template_ref` is blank and `RegionRow.assembly_ref` matches the provided `AssemblyModel.assembly_id`, the builder should use `AssemblyModel.active_template_id`.

If multiple `AssemblyModel` sources exist in the document, Applied Section generation should select the model matching `RegionRow.assembly_ref`.

If `RegionRow.assembly_ref` cannot be matched to any available Assembly source, the builder should emit diagnostics instead of silently applying the wrong Assembly.

## Diagnostics

The first editor-level validation checks:

- assembly id exists
- at least one template exists
- template id exists
- component ids are present and unique within the template
- component width is not negative
- ditch `shape` values are supported
- required ditch shape parameters such as `depth` and `bottom_width` are present and numeric
- `custom_polyline` ditch definitions provide at least two section points
- structural ditch materials provide wall thickness where the selected shape needs a future component body
- lined ditch materials provide lining thickness for quantity and review

## Preset Data

The Assembly editor should use selectable preset data instead of a single starter-only command.

Available first-slice presets:

- `Basic Road`
- `Urban Curb & Gutter`
- `Divided Road`
- `Bridge Interface`
- `Drainage Ditch Road`

`Drainage Ditch Road` uses trapezoid ditch parameters as the first shape-aware ditch preset.

Loading a preset only fills the editable Assembly table.

It does not create Applied Sections, Corridor surfaces, solids, or viewer-only geometry.

## Preview

The Assembly editor may provide a `Show` action.

`Show` reads the current editable table values and creates a generated `Assembly Show Preview` cross-section in the 3D View.

For `ditch` components, `Show` should use the same shape-aware ditch profile interpretation as Applied Section generation.

The preview should be shown in Front view.

It is presentation geometry only.

It should be rebuilt from Assembly source rows and must not become an editable design source.

## Non-goals

The Assembly editor does not build corridor solids.

The Assembly editor does not edit generated section wires.

The Assembly source object does not replace Region, Structure, Drainage, Ramp, or Intersection source models.

## Initial Workflow

1. Open `Assembly`.
2. Select an Assembly preset.
3. Click `Load Preset`.
4. Edit component rows.
5. Click `Show` to review the cross-section line when needed.
6. Click `Validate`.
7. Click `Apply`.
8. Open `Regions`.
9. Select the resulting `assembly_id` in the Region `Assembly` column.
10. Click `Validate`.
11. Click `Apply`.

Expected tree location:

- `04_Corridor Model / Assemblies`

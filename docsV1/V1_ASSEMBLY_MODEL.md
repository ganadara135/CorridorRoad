# Parametric Road V1 Assembly Model

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

Assemblies decide what section Subassemblies are available at that station.

Applied sections and corridor solids are downstream results.

## Design Goals

- Keep Subassembly intent editable before corridor generation.
- Let `RegionRow.assembly_ref` point to a durable `AssemblyModel`.
- Keep bridge, ramp, intersection, and drainage behavior explicit through references and layers.
- Avoid storing engineering meaning inside viewer geometry.

## Object Families

- `AssemblyModel`
- `SectionTemplate`
- `TemplateSubassembly`
- `SubassemblySectionTemplate`
- `TemplateComponent`
- future `AssemblyPolicySet`
- future `AssemblyVariant`

`TemplateSubassembly` and `SubassemblySectionTemplate` are the active v1 contracts.

`TemplateComponent` remains a transition compatibility contract until the Subassembly cutover is complete.

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

`SubassemblySectionTemplate` uses the same template identity fields and stores:

- `subassembly_rows`

## Subassembly Fields

`TemplateSubassembly` uses:

- `subassembly_id`
- `subassembly_index`
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

The current Subassembly editor preserves parameters through a raw `Parameters` field using `key=value;key=value` text.

The `Selected Subassembly Detail` area exposes first-slice helpers for ditch shape, side-slope bench, material, and preview rows.

It reads the selected Subassembly `material` and shows material-specific guidance.

Lined materials expose `lining_thickness`.

Structural materials such as concrete or precast require `wall_thickness` for U, L, and rectangular ditches.

For `kind = "side_slope"`, bench-specific intent should also be stored in `parameters`.

The governing slope bench plan is `docsV1/V1_ASSEMBLY_SLOPE_BENCH_PLAN.md`.

Recommended bench parameter keys include:

- `bench_mode`
- `bench_rows`
- `repeat_first_bench_to_daylight`
- `daylight_mode`
- `daylight_search_step`
- `daylight_max_width`
- `daylight_max_width_delta`
- `daylight_max_triangles`

Recommended bench row fields are:

- `drop`
- `width`
- `slope`
- `post_slope`
- `row_id`
- `label`

Recommended `daylight_mode` values are:

- `off`: do not apply terrain daylight behavior.
- `terrain`: tie bench/side-slope daylight to the existing ground TIN.
- `fixed_width`: keep the Assembly-defined side-slope/bench width without terrain clipping.

Assembly owns these reusable side-slope bench rules.

Region applies the Assembly over station ranges, but it does not own bench geometry.

## Deprecated Component Compatibility Fields

`TemplateComponent` is retained only as a transition compatibility contract.

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

New v1 source, result, output, review, watertight solid, exchange, and simulation package paths should prefer `subassembly_ref`.

`component_ref` may appear only as compatibility provenance while older documents and old editor paths remain loadable.

## Relationships

`RegionRow.assembly_ref` should reference `AssemblyModel.assembly_id`.

`RegionRow.template_ref` may reference `SectionTemplate.template_id` until richer Assembly lookup is implemented.

`target_ref` may point to drainage, structure, override, or other domain sources when a Subassembly is tied to a specific external control.

The Region editor should list existing v1 Assembly ids for `assembly_ref`.

If a Region references an Assembly id that does not exist in the document, validation should show a warning and preserve the entered source value.

`AppliedSectionService` should consume Region context through `RegionResolutionService.resolve_handoff`.

If `RegionRow.template_ref` is blank and `RegionRow.assembly_ref` matches the provided `AssemblyModel.assembly_id`, the builder should use `AssemblyModel.active_template_id`.

If multiple `AssemblyModel` sources exist in the document, Applied Section generation should select the model matching `RegionRow.assembly_ref`.

If `RegionRow.assembly_ref` cannot be matched to any available Assembly source, the builder should emit diagnostics instead of silently applying the wrong Assembly.

When the primary Assembly source object is reapplied with a new `AssemblyModel.assembly_id` or active template id, the Assembly apply command may update Region rows that referenced the previous primary Assembly/template pair.

This keeps the common single-Assembly workflow coherent after changing presets while preserving explicit Region references that point elsewhere.

## Diagnostics

The first editor-level validation checks:

- assembly id exists
- at least one template exists
- template id exists
- Subassembly ids are present and unique within the template
- Subassembly width is not negative
- ditch `shape` values are supported
- required ditch shape parameters such as `depth` and `bottom_width` are present and numeric
- `custom_polyline` ditch definitions provide at least two section points
- structural ditch materials provide wall thickness where the selected shape needs a future component body
- lined ditch materials provide lining thickness for quantity and review
- side-slope `bench_mode` values are supported
- side-slope `daylight_mode` values are supported
- side-slope `bench_rows` are parseable and have positive width
- repeated bench-to-daylight settings have daylight mode and a finite max width
- side-slope rows with bench intent have positive side-slope width

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

For `ditch` Subassemblies, `Show` should use the same shape-aware ditch profile interpretation as Applied Section generation.

The preview should be shown in Front view.

It is presentation geometry only.

It should be rebuilt from Assembly source rows and must not become an editable design source.

## Non-goals

The Assembly editor does not build corridor solids.

The Assembly editor does not edit generated section wires.

The Assembly source object does not replace Region, Structure, Drainage, Ramp, or Intersection source models.

## Initial Workflow

1. Open `Assembly / Subassembly`.
2. Select an Assembly preset.
3. Click `Load Preset`.
4. Edit Subassembly rows.
5. Click `Show` to review the cross-section line when needed.
6. Click `Validate`.
7. Click `Apply`.
8. Open `Regions`.
9. Select the resulting `assembly_id` in the Region `Assembly` column.
10. Click `Validate`.
11. Click `Apply`.

Expected tree location:

- `04_Parametric Model / Assemblies`

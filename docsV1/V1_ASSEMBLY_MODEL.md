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

## Relationships

`RegionRow.assembly_ref` should reference `AssemblyModel.assembly_id`.

`RegionRow.template_ref` may reference `SectionTemplate.template_id` until richer Assembly lookup is implemented.

`target_ref` may point to drainage, structure, override, or other domain sources when a component is tied to a specific external control.

The Region editor should list existing v1 Assembly ids for `assembly_ref`.

If a Region references an Assembly id that does not exist in the document, validation should show a warning and preserve the entered source value.

`AppliedSectionService` should consume Region context through `RegionResolutionService.resolve_handoff`.

If `RegionRow.template_ref` is blank and `RegionRow.assembly_ref` matches the provided `AssemblyModel.assembly_id`, the builder should use `AssemblyModel.active_template_id`.

If `RegionRow.assembly_ref` points to a different Assembly than the one provided to the builder, the builder should emit diagnostics instead of silently applying the wrong Assembly.

## Diagnostics

The first editor-level validation checks:

- assembly id exists
- at least one template exists
- template id exists
- component ids are present and unique within the template
- component width is not negative

## Non-goals

The Assembly editor does not build corridor solids.

The Assembly editor does not edit generated section wires.

The Assembly source object does not replace Region, Structure, Drainage, Ramp, or Intersection source models.

## Initial Workflow

1. Open `Assembly`.
2. Click `Load Starter Assembly`.
3. Edit component rows.
4. Click `Validate`.
5. Click `Apply`.
6. Open `Regions`.
7. Select the resulting `assembly_id` in the Region `Assembly` column.
8. Click `Validate`.
9. Click `Apply`.

Expected tree location:

- `04_Corridor Model / Assemblies`

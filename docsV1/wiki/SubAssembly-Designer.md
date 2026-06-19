# SubAssembly Designer

SubAssembly Designer creates reusable cross-section behavior.

Assembly places those definitions into Assembly Templates and applies row-local overrides.

Applied Sections evaluates the placed Subassemblies at stations.

Build Parametric, Quantity, and Watertight Solids consume evaluated result rows only.

## When To Use It

Use SubAssembly Designer before Assembly when you need:

- reusable lane, shoulder, ditch, side-slope, bench, pavement, or lining definitions
- parameter-driven point, link, and shape rows
- consistent surface roles for Build Parametric
- quantity or watertight solid handoff from closed shape rows

Skip it when the existing Assembly Template already provides the section intent you need.

## Workflow

1. Open `SubAssembly Designer`.
2. Select an `Assembly Row` and click `Load Row`.
3. Edit Parameters, Points, Links, Shapes, and Targets.
4. Review the Live Preview and Diagnostics.
5. Click `Save Changes`.
6. Optionally click `Save as Reusable Subassembly Template`.
7. Rebuild Applied Sections.
8. Review Cross Sections.
9. Build Parametric.
10. Run Quantity or Watertight Solids when output handoff is needed.

`Save Changes` writes to the active Assembly row when an Assembly/Subassembly object exists.

If no Assembly row is available, `Save Changes` writes the SubAssembly library source.

`Save as Reusable Subassembly Template` creates a project-level template for one reusable Subassembly definition.

Advanced template management is hidden by default. Use `Show Advanced Subassembly Template Library` only when editing, updating, duplicating, renaming, deleting, or detaching shared templates intentionally.

## Assembly Row Editing UX

The Assembly Row selector chooses which placed Assembly row is loaded into the Designer.

`Refresh Rows`, `Load Row`, `Save Changes`, and `Save as Reusable Subassembly Template` are grouped together below the Assembly Row selector so the selector remains readable on narrow task panels.

Use `Refresh Rows` after changing the Assembly/Subassembly source panel.

Use `Load Row` to copy the selected Assembly row into the Designer edit tables.

Use `Save Changes` to write the current Designer edits back to the selected Assembly row when an Assembly/Subassembly object exists.

Use `Save as Reusable Subassembly Template` only when the current definition should become a reusable project template.

In the Assembly/Subassembly panel, selected Subassembly detail changes only after an explicit table row click.

Combo-box hover in table cells should not change the selected detail row.

If hover changes the detail panel, treat it as a UI regression rather than accepted behavior.

## Template States

SubAssembly Designer and Assembly share template state so users can see whether an Assembly row still follows its reusable source.

`linked` means the row still matches the selected Reusable Subassembly Template version.

`modified` means the row has local parameter, role, shape, target, or surface-role differences from the template.

`snapshot` means the row is intentionally detached from a template and should be treated as custom source intent.

`missing_preset` means the Assembly row references a template that is not available in the project template library.

`preset_outdated` means the Assembly row references an older template version than the project library currently exposes.

Review these states before rebuilding Applied Sections. Missing or outdated templates should be corrected in Designer or Assembly before Build Corridor outputs are trusted.

## Template Terminology

`Reusable Subassembly Template` means one reusable Subassembly definition such as `Basic Shoulder`, `Trapezoid Ditch`, or `Benched Side Slope`.

`Assembly Template` means a full cross-section arrangement made from several Subassembly rows.

`Assembly Row` means one placed Subassembly instance inside an Assembly Template.

The code and object properties may still use `preset_ref`, `preset_version`, and `preset_status` internally for compatibility.

## Ownership Rules

- `SubassemblyLibrary` and `SubassemblyDefinition` own reusable source behavior.
- Assembly `TemplateSubassembly` rows own placement, side, order, and overrides.
- Applied Sections own station-based evaluated Subassembly rows.
- Build Parametric consumes evaluated `subassembly_link_rows.surface_role`.
- Quantity and Watertight Solids consume evaluated shape rows and `solid_family`.

Generated geometry is not the editing source.

The Designer preview is a temporary draft review surface. It does not save source state until `Apply` is used.

## Definition Fields

`Kind`, `Category`, `Side`, and `Enabled` are selected from combo boxes in the Definition table.

This keeps reusable definitions consistent before Assembly places them.

Width, slope, thickness, material, and similar reusable dimensions should be modeled as Designer parameters, links, shapes, or materials.

Assembly should not duplicate those fields in the main placement table.

If one Assembly placement needs a different value, edit the selected row detail in Assembly. Only changed values are stored as overrides.

If a generated surface or solid is wrong, correct the Subassembly definition or Assembly placement and rebuild.

After changing a Reusable Subassembly Template or Assembly row override, rebuild in this order:

1. Click `Save Changes` or `Update Shared Subassembly Template`.
2. Refresh or update affected Assembly rows when needed.
3. Rebuild Applied Sections.
4. Rebuild Build Corridor.
5. Re-run downstream Quantity, Exchange, or Watertight Solid outputs if they depend on those sections.

## Applied Section Handoff Expectations

The section preview and Applied Sections should use the same placed Subassembly definitions and row-local overrides.

Designer definition parameters are merged before Applied Sections evaluate point, link, and shape rows.

Percent slope parameters in reusable definitions are normalized to engineering slope values during Applied Sections evaluation.

A ditch definition with `top_width`, `bottom_width`, and `depth` can be evaluated as a trapezoid even when the legacy `shape` field is not present.

Ditch geometry should start from the finished-grade edge elevation of the preceding lane or shoulder, not from the raw frame elevation.

If the Section Preview and Applied Sections disagree at the shoulder-to-ditch connection, check:

- the selected Assembly row was saved
- the Assembly/Subassembly panel was applied
- Applied Sections were rebuilt after the save
- the ditch definition has valid width/depth parameters
- slope parameter units are correct

## Manual QA Checklist

Default flow:

- Open `Assembly / Subassembly`.
- Load an Assembly Template.
- Confirm template refs are assigned or use the approximate Subassembly Ref guess action.
- Apply the Assembly source.
- Open `SubAssembly Designer`.
- Select an Assembly Row.
- Click `Load Row`.
- Edit a parameter.
- Confirm `Changed fields` increases.
- Confirm `Save target` shows the selected Assembly row.
- Click `Save Changes`.

Reusable template flow:

- Load an Assembly Row in SubAssembly Designer.
- Edit a parameter.
- Click `Save as Reusable Subassembly Template`.
- Confirm the advanced template library contains a new row after expanding it.

Advanced flow:

- Click `Show Advanced Subassembly Template Library`.
- Select a Reusable Subassembly Template.
- Click `Edit Selected Subassembly Template`.
- Edit the main Definition or Detail table.
- Click `Update Shared Subassembly Template`.
- Confirm the dialog shows affected Assembly rows and offers `Save as Custom Copy`.

## Side-Slope Bench Definitions

Use `subassembly-definition:side-slope-bench-daylight` when a side slope needs bench behavior.

The durable bench intent belongs in Designer parameters such as `bench_mode`, `bench_rows`, daylight controls, and slope values.

Assembly should only place the definition and store row-local overrides when a specific placement must differ from the reusable definition.

In Live Preview, bench links are visually separated from ordinary slope links so the bench break sequence can be checked before Build Sections.

## Surface Roles

Designer link roles are normalized before Build Parametric consumes them.

- `design`, `finished_grade`, `fg` -> `design_surface`
- `subgrade` -> `subgrade_surface`
- `slope_face`, `daylight` -> `slope_face_surface`
- `drainage` -> `drainage_surface`

Use these roles consistently so Design Surface, Subgrade Surface, Slope Face Surface, and Drainage Surface are traceable back to Subassembly links.

## Shapes, Quantities, And Solids

Closed Designer shapes can support downstream output.

- A shape with at least three evaluated points can create a section-area quantity fragment.
- A shape with `solid_family` can appear as a Watertight Solid target after it exists at two or more stations.
- Typical families include `pavement_layer`, `subbase`, `shoulder`, and `lined_ditch`.

Shape output is evaluated through Applied Sections first.

Build Parametric, Quantity, and Watertight Solids should not re-evaluate Designer expressions directly.

## Limits

- Civil 3D `.pkt` runtime import is not supported.
- Full visual scripting is not part of the first Designer workflow.
- Automatic engineering design-code selection remains future work.

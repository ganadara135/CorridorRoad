# Assembly and Region

Assembly and Region define how reusable section intent is applied to station ranges.

## Assembly

Assembly owns Assembly Templates.

An Assembly Template is a full cross-section arrangement made from multiple Subassembly rows.

SubAssembly Designer owns reusable Subassembly definitions and Reusable Subassembly Templates.

A Reusable Subassembly Template is one reusable lane, shoulder, ditch, side slope, curb, gutter, or other single Subassembly definition.

Assembly places those definitions into templates, controls ordering and side, and stores row-local parameter overrides.

The active Assembly table is a placement table.

It should show placement fields such as:

- Enabled
- Subassembly ID
- Subassembly Ref
- Template Ref
- Template Version
- Template Status
- Side
- Index
- Target Ref
- Notes

Definition fields such as Kind, width, slope, thickness, and material should come from SubAssembly Designer.

When one placement needs a different value, edit it in `Selected Subassembly Detail`; Assembly stores only the changed values as parameter overrides.

Assembly shows template state for each Subassembly row.

`linked` rows follow the Reusable Subassembly Template contract.

`modified` rows keep a template reference but contain local overrides.

`snapshot` rows are custom rows without a live template link.

`missing_preset` rows reference a template id that is not present in the project library.

`preset_outdated` rows reference an older template version than the current library row.

Use `Refresh From Template` when a linked or outdated row should adopt the current template defaults.

Use `Detach Custom` when a row should stop following future template updates.

Examples:

- lanes
- shoulders
- ditches
- side slopes
- benches
- pavement-related intent

Assembly can define ditch shapes and side-slope bench behavior. These are source definitions, not generated corridor geometry.

Use `Assembly / Subassembly` as the active v1 editor when creating new section intent.

`Subassembly` is the user-facing term for reusable section parts. The old Assembly editor path is not part of the active v1 workflow.

When a reusable definition is needed, create or update it in [SubAssembly Designer](./SubAssembly-Designer.md) first, then place it from Assembly.

Use `Load Assembly Template` for full cross-section starter arrangements.

Use `Template Ref` for one reusable Subassembly row source.

## Region

Region owns station-range application control.

Region decides which base Assembly applies over a station range:

- one Assembly reference

Structure and Drainage do not get assigned from the Region panel. They choose their owning Region from their own panels.

## Region Table

Regions are managed by `Start STA`.

- `Start STA` is selected from generated Stationing values.
- `End STA` is derived automatically from the next Region row's `Start STA`.
- The final Region row ends at the final Stationing value.
- Region ranges should be continuous. There should be no intentional gap between Regions.

Use `Validate` before `Apply` to confirm that selected Region stations exist in Stationing.

## Templates

The Region panel includes practical starter template data.

`Drainage Control` starts the drainage-control Region at `STA 100.000` and closes the preset at the current final Stationing value.

After loading any starter template, review the Assembly assignment before applying it to the project.

After changing Reusable Subassembly Templates or Assembly row overrides, rebuild Applied Sections before rebuilding Build Corridor.

## Rule

Region should reference the base Assembly only in the active v1 workflow.

It should not hide engineering meaning in free-form notes.

## Drainage Position

Drainage follows Structures in the toolbar because Drainage Elements choose their owning Region and may reference Structure-backed nodes.

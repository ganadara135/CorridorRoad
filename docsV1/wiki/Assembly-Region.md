# Assembly and Region

Assembly and Region define how reusable section intent is applied to station ranges.

## Assembly

Assembly owns reusable section components.

Examples:

- lanes
- shoulders
- ditches
- side slopes
- benches
- pavement-related intent

Assembly can define ditch shapes and side-slope bench behavior. These are source definitions, not generated corridor geometry.

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

## Presets

The Region panel includes practical preset data.

`Drainage Control` starts the drainage-control Region at `STA 100.000` and closes the preset at the current final Stationing value.

After loading any preset, review the Assembly assignment before applying it to the project.

## Rule

Region should reference the base Assembly only in the active v1 workflow.

It should not hide engineering meaning in free-form notes.

## Drainage Position

Drainage follows Structures in the toolbar because Drainage Elements choose their owning Region and may reference Structure-backed nodes.

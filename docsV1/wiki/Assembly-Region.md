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

Region decides which source references apply over a station range:

- one Assembly reference
- one Structure reference where applicable
- Drainage references
- applied layers such as ditch, drainage, guardrail, or widening

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

After loading any preset, review the Assembly, Structure, Drainage, and layer references before applying it to the project.

## Rule

Region should reference domain models.

It should not hide engineering meaning in free-form notes.

## Drainage Position

Drainage follows Region in the toolbar because Region defines the station range context that Drainage references will use.

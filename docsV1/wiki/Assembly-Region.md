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

## Rule

Region should reference domain models.

It should not hide engineering meaning in free-form notes.

## Drainage Position

Drainage follows Region in the toolbar because Region defines the station range context that Drainage references will use.

# Troubleshooting

## Commands Do Not Appear

After updating CorridorRoad:

1. Restart FreeCAD.
2. Re-select the CorridorRoad workbench.
3. If the problem remains, check the FreeCAD report view for import errors.

Missing command registration can happen when an updated command module was not loaded in the current FreeCAD session.

## Drainage Opens An Under-Development Message

This is expected in `1.0.0`.

Drainage is visible as a planned v1 stage, but the full Drainage Editor is not complete yet.

## Applied Sections Cannot Run

Check that these source stages exist:

- Alignment
- Stations
- Profile
- Assembly
- Region

If terrain/daylight behavior is needed, also confirm that a valid TIN is available.

## Build Corridor Looks Empty Or Partial

Check:

- Applied Sections were generated first
- the correct Region and Assembly are active
- terrain is available for slope/daylight behavior
- diagnostics in Build Corridor

## Region Boundaries Show A Gap

Regions are intended to be continuous.

Check:

- Region `Start STA` values come from Stationing
- the first Region starts at the first Stationing value
- each Region's `End STA` is derived from the next Region's `Start STA`
- the final Region ends at the final Stationing value
- Applied Sections were regenerated after Region changes

## Selected Region Does Not Show Every Surface

The Region Boundary display uses built corridor objects for the selected Region.

If a selected Region only shows the design surface, check whether the Region actually generated:

- slope/daylight surface rows
- drainage surface rows
- structure references and structure output
- subgrade surface rows

Rebuild Applied Sections, then Build Corridor, and review the Build Corridor diagnostics.

## Surface Transition Spacing Does Not Change The Surface

Check:

- the intended `Region STA` is selected
- `Update` was pressed after changing `Spacing`
- the transition row is enabled
- Applied Sections exist before rebuilding Build Corridor
- Build Corridor was run again after the transition update

## Earthwork Has No Results

Check:

- Applied Sections exist
- existing-ground TIN exists
- station rows cover the corridor range
- Earthwork Viewer diagnostics

## Review Handoff Error

If a review button reports a missing command:

1. Restart FreeCAD.
2. Activate the CorridorRoad workbench.
3. Try the command again.

If it still fails, report the traceback from the FreeCAD report view.

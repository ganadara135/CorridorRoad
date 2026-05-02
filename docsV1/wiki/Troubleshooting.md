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

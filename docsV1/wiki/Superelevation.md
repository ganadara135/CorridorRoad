# Superelevation

Superelevation is the source stage for station-based roadway crossfall.

It belongs after `3D Centerline` and before `Assembly`.

## Role

Superelevation owns:

- left/right crossfall control rows
- runoff/runout transition ranges
- validation constraints
- evaluated sample rows for review

Assembly still owns the default section composition and default slopes.

Superelevation overrides lane and shoulder crossfall by station during Applied Sections generation.

## Workflow

1. Build Alignment, Stations, Profile, and 3D Centerline.
2. Open `Superelevation`.
3. Load a preset or add Control Rows.
4. Validate.
5. Use `Show Samples` to review station crossfall values.
6. Confirm the 3D crossfall bars appear along the 3D Centerline.
7. Apply.
8. Generate Applied Sections.
9. Build Corridor / Build Parametric.

## Review

`Show Samples` creates review output only.

It does not create editable road geometry.

The 3D review object shows short crossfall bars at station samples. These bars help confirm direction and magnitude before rebuilding downstream results.

Applied Sections then show the resolved Superelevation summary by station.

Cross Section Viewer can expose Superelevation source/provenance through section output summary rows and Subassembly notes.

## Build Parametric

Build Parametric does not evaluate Superelevation directly.

It consumes Applied Section `fg_surface` point rows that already include the effective Superelevation crossfall.

If the Design Surface does not reflect a Superelevation change, rebuild in this order:

1. Apply Superelevation.
2. Generate Applied Sections.
3. Build Corridor / Build Parametric.

## Current Limits

The first implementation is intentionally narrow:

- linear transition evaluation
- lane and shoulder crossfall override
- source persistence and review diagnostics
- Applied Sections and Build Parametric verification

Future work:

- automatic design-speed/radius table calculation
- ramp and intersection Superelevation automation
- jurisdiction-specific rule presets
- exchange export coverage

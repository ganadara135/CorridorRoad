# Applied Sections and Build Corridor

Applied Sections and Build Corridor are generated result stages.

## Applied Sections

Applied Sections evaluate source intent at stations.

They resolve:

- Alignment frame
- Profile elevation
- active Region
- Assembly components
- Structure context
- drainage/ditch point rows where available
- terrain/daylight behavior

Applied Sections are results. They are not the primary editing surface.

## Build Corridor

Build Corridor consumes Applied Sections and creates corridor preview surfaces and diagnostics.

Typical outputs include:

- centerline context
- design surface preview
- subgrade surface preview
- slope face / daylight preview
- drainage surface preview where ditch surface rows exist

## Diagnostics

Use Build Corridor diagnostics to find missing or partial result rows before relying on downstream review or output.

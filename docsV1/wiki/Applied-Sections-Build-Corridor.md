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

The `Validate` action checks source handoff readiness before building result rows.

Drainage readiness includes:

- every Drainage element row with an `Element ID` must have a `Region` assigned
- missing Drainage Region assignment is reported as `drainage_element_missing_region_ref`
- correction happens in the Drainage editor, not in Applied Sections

## Build Corridor

Build Corridor consumes Applied Sections and creates corridor preview surfaces and diagnostics.

Typical outputs include:

- centerline context
- design surface preview
- subgrade surface preview
- slope face / daylight preview
- drainage surface preview where ditch surface rows exist

## Region Boundaries

The Build Corridor panel includes a `Region Boundaries` table.

Each row represents one source Region range.

Double-click a Region row, or select a row and use `Highlight Region`, to display the selected Region's built objects in the 3D view.

The Region display is based on the selected Region's corridor objects, not a separate sketch-only highlight. It can include:

- design surface
- subgrade surface
- slope/daylight surface
- drainage surface
- structure object context where Applied Sections resolved active Structure rows

The Structure and Drainage columns are read-only resolved summaries from Applied Sections. They are not Region source fields.

If only part of the Region appears, rebuild Applied Sections and Build Corridor, then check the Region row's surface, structure, and drainage diagnostics.

## Surface Transitions

Surface Transitions are edited in Build Corridor.

Use `Region STA` to choose the Region boundary or Region station context to update.

Use `Spacing` to control the transition sample interval.

`Sample Count` in the Surface Transitions table is derived from the stored transition range and the current spacing.

Use `Update` to create or update the selected transition record.

Use `Toggle Enabled` to enable or disable the selected transition range.

Build Corridor uses the stored transition records when rebuilding corridor surfaces. Applied Sections should be generated first, then Build Corridor applies the transition settings during the surface build.

## Diagnostics

Use Build Corridor diagnostics to find missing or partial result rows before relying on downstream review or output.

# Troubleshooting

## Commands Do Not Appear

After updating Parametric Road:

1. Restart FreeCAD.
2. Re-select the Parametric Road workbench.
3. If the problem remains, check the FreeCAD report view for import errors.

Missing command registration can happen when an updated command module was not loaded in the current FreeCAD session.

## Drainage Flow Network Does Not Appear

Check:

- Drainage Elements reference valid Structure rows where pipe geometry is expected
- Structure rows have connection points such as `pipe_in`, `pipe_out`, `upstream`, or `downstream`
- `ditch -> inlet` Flow Routes are capture-only relationships and do not create pipe bodies
- Apply Structures, then Apply Drainage, then use `Show Flow Network`
- run 3D Centerline first when you want Drainage preview geometry to follow the shared profile frame

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

## Structure Preview Looks Too Simple

Native Structure previews are review geometry.

For drainage-ready previews, check:

- Native Type is set to `inlet`, `pipe_culvert`, `outlet`, or `headwall`
- connection points are present for pipe ports
- pipe culvert `headwall_type` or `wingwall_type` is set if endpoint headwall/wingwall details should appear
- run `Apply + Preview` from the Structures panel after editing source rows

## Surface Transition Spacing Does Not Change The Surface

Check:

- the intended `Region STA` is selected
- `Update` was pressed after changing `Spacing`
- the transition row is enabled
- Applied Sections exist before rebuilding Build Corridor
- Build Corridor was run again after the transition update

## Curved 3D Centerline Surface Looks Too Straight

Check:

- 3D Centerline was built and reviewed before Applied Sections
- Applied Sections `Supplemental Sections` is enabled
- Applied Sections summary shows supplemental sections greater than zero on curved spans
- Build Corridor Guided Review row `2a. Supplemental Sections` reports consumed supplemental sections
- if Build Corridor reports compatibility fallback, rebuild Applied Sections before trusting the surface

Build Parametric no longer owns supplemental density.

Change the density in Applied Sections, rebuild Applied Sections, then rebuild Build Corridor.

At the current default density, supplemental Applied Sections target an approximate maximum spacing of about `45 m`.

Recursive sampling should stop once an interval is already shorter than the requested maximum spacing.

If supplemental sections look too dense, lower the Applied Sections density and rebuild Applied Sections before rebuilding Build Corridor.

If the Build Parametric centerline differs from the 3D Centerline panel, inspect the generated object properties:

- `PreviewSource`
- `DisplayCurveKind`

The preferred source is `centerline3d_source_geometry`.

`centerline3d_result_fallback` means Build Parametric could not reuse Source Geometry and used a fallback preview path.

When fallback appears, rebuild or inspect 3D Centerline, then rebuild Applied Sections and Build Corridor.

## Applied Section Shape Does Not Match Assembly/Subassembly Preview

Check:

- the Assembly/Subassembly source was applied after editing
- `Save Changes` was used after loading and editing an Assembly row in SubAssembly Designer
- Applied Sections were rebuilt after the Assembly/Subassembly change
- the selected Assembly row has the expected Subassembly Ref
- percent slope parameters use the correct unit
- ditch definitions have valid `top_width`, `bottom_width`, and `depth`

The expected handoff is:

- lane and shoulder finished-grade edges connect directly
- ditch starts from the preceding finished-grade edge elevation
- side-slope/daylight rows start after the placed ditch or shoulder row

If the Section Preview is correct but Applied Sections are not, rebuild Applied Sections before investigating Build Corridor.

## Earthwork Has No Results

Check:

- Applied Sections exist
- existing-ground TIN exists
- station rows cover the corridor range
- Earthwork Viewer diagnostics

## Watertight Solids Are Disabled Or Empty

Check:

- Applied Sections were generated
- Build Corridor was run successfully
- target rows are available and enabled
- Structure or Drainage targets have the required source refs and connection point context
- `Build Selected` is used for the selected target, or `Build Enabled` is used for enabled rows

## Review Handoff Error

If a review button reports a missing command:

1. Restart FreeCAD.
2. Activate the Parametric Road workbench.
3. Try the command again.

If it still fails, report the traceback from the FreeCAD report view.

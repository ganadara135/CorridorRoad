# Drainage

Drainage is an active v1 source stage.

The current editor shell can create and update a `V1DrainageModel` with drainage elements, policy rows, and collection/discharge regions.

## Why Drainage Is In The Toolbar

Drainage belongs after Region and before Applied Sections.

Reason:

- Region defines station range context.
- Drainage will define drainage elements and intent for those ranges.
- Applied Sections will evaluate the resolved drainage/ditch context.

## Current Behavior

Current drainage-related behavior appears through:

- Drainage editor source rows
- `V1DrainageModel` document persistence
- side, Region ref, and Assembly component ref persistence on drainage elements
- Region editor Drainage selector and `Attach Drainage` handoff into `RegionRow.drainage_refs`
- Assembly ditch shapes
- Applied Section `ditch_surface` rows with `component_ref`, `side`, and `drainage_ref`
- Drainage Review read-only tables for source handoff and Applied Section context
- Build Corridor drainage diagnostics
- drainage surface preview where ditch points exist
- drainage quantity fragments for ditch length and available flowline length by `drainage_ref`
- Watertight Solid lined-ditch target ownership when a matching DrainageModel element exists

## Drainage Editor

Editable first-slice rows:

- ditch
- swale
- channel
- culvert reference
- inlet reference
- outfall reference

The editor also stores policy intent and collection/discharge context.

Element rows now include:

- Side
- Start STA and End STA
- Region ref
- Assembly Component ref
- Offset Rule
- Policy ref
- Structure ref

The `Add Left Ditch` and `Add Right Ditch` actions create first-slice ditch rows with matching side and default `ditch:left` or `ditch:right` Assembly component refs.

Watertight Solid lined-ditch target discovery uses the Drainage element `side` field first. The older id/offset text inference remains only as fallback behavior.

## Region Handoff

The Region editor can read Drainage element ids from the active `V1DrainageModel`.

To link a Region to Drainage:

- select a Region row
- choose a Drainage element id
- press `Attach Drainage`
- Validate before Apply

Validation warns when a Region references a Drainage id that is not present in the current `V1DrainageModel`.

## Applied Section Handoff

Applied Sections read the active Region drainage refs during section generation.

For ditch components, generated result rows preserve:

- component Drainage refs
- ditch surface `component_ref`
- ditch surface side
- ditch surface `drainage_ref`

The `V1AppliedSectionSet` document object stores and reloads this Drainage context so later Build Corridor, Watertight Solid, review, and exchange stages do not have to infer it from preview mesh geometry.

## Drainage Review

Drainage Review is a read-only workflow check after Drainage and before Applied Sections/Build Corridor review.

It shows:

- Drainage element rows
- Region handoff refs and missing-ref status
- Applied Section ditch surface context
- summary counts for elements, Region handoffs, ditch surface points, and Drainage ref coverage

The first slice does not edit source rows. Corrections still happen in Drainage, Region, Assembly, or Applied Sections.

When a QuantityModel is supplied to the review mapper, Drainage Review can also summarize drainage ditch length and flowline length by Drainage element id.

## Still In Progress

- hydraulic analysis
- automatic pipe sizing
- complete drainage report output
- Region and Assembly reference selectors
- multi-select Drainage handoff picker
- explicit flowline/invert point roles and related review UI
- Drainage Review issue markers and 3D focus actions

See `docsV1/V1_DRAINAGE_IMPLEMENTATION_PLAN.md` for the implementation plan.

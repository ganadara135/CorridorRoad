# Drainage

Drainage is an active v1 source stage.

The current editor shell can create and update a `V1DrainageModel` with drainage elements, policy rows, and flow routes.

## Why Drainage Is In The Toolbar

Drainage belongs after Region and before Applied Sections.

Reason:

- Region defines station range context.
- Drainage will define drainage elements and intent for those ranges.
- Applied Sections will evaluate the resolved drainage/ditch context.

## Current Behavior

Current drainage-related behavior appears through:

- Drainage editor source rows
- Drainage editor Preset data for roadside ditch, dual side ditches, and culvert crossing source sets
- `V1DrainageModel` document persistence
- side, Region ref, and Assembly component ref persistence on drainage elements
- Assembly ditch shapes
- Applied Section `ditch_surface` rows with `component_ref`, `side`, and `drainage_ref`
- Drainage Review read-only tables for source assignment and Applied Section context
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

The editor also stores policy intent and flow-route context.

Drainage uses a graph-style source model:

- Elements are nodes.
- Flow Routes are edges.
- Outlet is represented by an `outfall_reference` Element, or by an optional route-level outlet ref when a final outlet summary is needed.

Assembly-generated drainage geometry is currently limited to `ditch` components. Culverts, inlets, and outfalls remain valid Drainage elements or Structure-backed references, but they are connected through Flow Routes rather than generated as Assembly drainage components. In the Drainage Elements table, the `Assembly` cell is active only for `ditch` rows and is cleared for other element kinds.

Example:

```text
ditch:right-r2 -> culvert:01 -> outfall:right-01
```

Elements:

```text
ditch:right-r2      ditch
culvert:01          culvert_reference
outfall:right-01    outfall_reference
```

Flow Routes:

```text
edge:r2-01    from ditch:right-r2    to culvert:01
edge:r2-02    from culvert:01        to outfall:right-01
```

Available first-slice presets:

- `Roadside Ditch`
- `Dual Side Ditches`
- `Culvert Crossing`

Element rows now include:

- Region ref as a combo box populated from the active `V1RegionModel`
- Side
- Start STA and End STA
- Assembly ref
- Policy ref
- Structure Ref, disabled for `ditch` rows because open ditches are generated from Assembly drainage geometry rather than Structure references

The `Add Left Ditch` and `Add Right Ditch` actions create first-slice ditch rows with matching side and default `ditch:left` or `ditch:right` Assembly component refs.

Watertight Solid lined-ditch target discovery uses the Drainage element `side` field first. Drainage element id text remains only as fallback behavior.

## Region Assignment

Drainage owns its own Region assignment.

To link Drainage to a Region:

- open Drainage
- create or select a Drainage Element row
- choose the owning Region in the row's `Region` combo box
- validate before Apply

Drainage validation also checks Drainage element station spans against the selected Region:

- if an element has `Region` set, its `Start STA` and `End STA` must stay inside that Region's station boundary
- if the referenced Region is missing, validation reports a missing Region reference warning
- if a Flow Route connects Elements in different Regions, validation reports a cross-Region warning

Structure-backed drainage nodes use `Structure Ref`.

When a StructureModel is available, Drainage validation checks that a non-empty `Structure Ref` points to a known Structure ID.

## Applied Section Handoff

Applied Sections should resolve Drainage context from `DrainageModel` Region assignments during section generation.

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
- Region assignment status from Drainage Element `Region` values
- Applied Section ditch surface context
- summary counts for elements, Region assignments, ditch surface points, and Drainage ref coverage

The review does not read Region-owned Drainage refs. Corrections happen in Drainage, Region, Assembly, or Applied Sections depending on the source of the issue.

When a QuantityModel is supplied to the review mapper, Drainage Review can also summarize drainage ditch length and flowline length by Drainage element id.

## Still In Progress

- hydraulic analysis
- automatic pipe sizing
- complete drainage report output
- Assembly reference selectors
- multi-select Drainage assignment tools
- explicit flowline/invert point roles and related review UI
- Drainage Review issue markers and 3D focus actions

See `docsV1/V1_DRAINAGE_IMPLEMENTATION_PLAN.md` for the implementation plan.

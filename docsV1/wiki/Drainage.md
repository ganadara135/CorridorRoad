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
- Drainage editor Preset data for roadside ditch, dual side ditches, culvert crossing, and structure-backed flow source sets
- `V1DrainageModel` document persistence
- side, Region ref, and Assembly component ref persistence on drainage elements
- Assembly ditch shapes
- Applied Section `ditch_surface` rows with `component_ref`, `side`, and `drainage_ref`
- Drainage Review read-only tables for source assignment and Applied Section context
- Build Corridor drainage diagnostics
- drainage surface preview where ditch points exist
- Drainage editor `Show Flow Network` preview for the full resolved pipe network from Structure connection points
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
- Outlet is represented by an `outfall_reference` Element. In the Flow Routes table, the `Outlet` cell is editable only when `To Element` is an outlet/outfall Element; intermediate route rows keep Outlet disabled and empty.

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

For a ditch-to-inlet condition, use the Flow Route as a capture relationship, not as a pipe body:

```text
side-ditch-right-01 -> inlet-01   open ditch capture / inlet intake
side-ditch-right-02 -> inlet-02   open ditch capture / inlet intake
side-ditch-right-03 -> inlet-03   open ditch capture / inlet intake
inlet-01 -> inlet-02              collector pipe from Pipe Out to Pipe In
inlet-02 -> inlet-03              collector pipe from Pipe Out to Pipe In
inlet-03 -> culvert-01            pipe from last inlet Pipe Out to culvert Pipe In
culvert-01 -> outlet-01           pipe from culvert Pipe Out to outlet Pipe In
```

The ditch rows record that open ditch flow reaches each inlet. They are resolved as `capture_only` Flow Route relationships, not failed pipe candidates. They do not create separate 3D pipes from ditch sections to inlets. The physical 3D pipe network starts where Structure connection points exist, then continues through inlet `pipe_out` / `pipe_in` collector ports, culvert `pipe_in` / `pipe_out`, and outlet `pipe_in`.

Structure-backed pipe segments are drawn as direct 3D connections between resolved connection points. They do not sample intermediate stations along the road alignment, because buried pipe runs should connect port-to-port unless a later source model explicitly defines bends or intermediate pipe nodes.

Native inlet Structures are shown as catch-basin style bodies in 3D review. The preview adds a top grate, a ditch intake mouth, and short circular pipe port stubs for `pipe_in` / `pipe_out` connection points. Native pipe culverts with `headwall_type` or `wingwall_type` show endpoint headwall slabs and wingwalls. Native outlet/headwall Structures show a headwall slab, outfall apron, side guide walls, a pipe-in stub, and a discharge mouth. These details are review geometry for making the drainage chain readable; the durable source remains the Structure row and its connection point rows.

Available first-slice presets:

- `Roadside Ditch`
- `Dual Side Ditches`
- `Culvert Crossing`
- `Drainage Structures Flow`

`Drainage Structures Flow` is intended to be used with the Structures `Drainage Structures` preset. It creates multiple right-side ditch station bands, one inlet per ditch band, one culvert, and one outlet chain. The Drainage preset fills Structure Ref rows that match the Structures preset IDs. The pipe network is chained as inlet-01 to inlet-02 to inlet-03 to culvert-01 to outlet-01, so the last inlet connects to the culvert Pipe In port.

Element rows now include:

- Region ref as a combo box populated from the active `V1RegionModel`
- Side
- Start STA and End STA
- Assembly ref
- Policy ref
- Structure Ref, disabled for `ditch` rows because open ditches are generated from Assembly drainage geometry rather than Structure references

The Elements table does not expose a separate `Connection Point` column. Pipe In / Pipe Out ownership belongs to Structures. Drainage Elements choose the related Structure, and Flow Routes determine whether that Structure is used as an outgoing or incoming endpoint. During review and network preview, the resolver chooses the appropriate Structure connection point by route direction.

The `Add Left Ditch` and `Add Right Ditch` actions create first-slice ditch rows with matching side and default `ditch:left` or `ditch:right` Assembly component refs.

`Show Flow Network` applies the current Drainage table values, resolves Structure-backed Elements through direction-aware Structure ports, and creates a `V1DrainagePipelineNetworksPreview` object in the 3D View. It also creates linked per-segment `V1DrainagePipelineSegment_*` preview objects under the Drainage tree and linked `V1StructurePipeConnectionPoint_*` Pipe In / Pipe Out marker objects under the Structures tree. Drainage owns the pipe flow network; Structures own the connection points where pipes enter or leave a structure. Open ditch runs remain Assembly/Drainage surface geometry; pipe-like connections come from Structure connection points such as inlet Pipe Out, culvert Pipe In/Pipe Out, and outlet Pipe In. Ditch-to-inlet Flow Routes are intake/capture relationships unless a separate Structure-backed pipe element is added. If a connection point defines an invert elevation, 3D pipe previews display the circular pipe around the pipe axis by lifting the display center by the pipe radius; the stored source value remains the invert. If a connection point does not define an invert elevation, the preview uses the active 3D centerline/profile height instead of dropping the pipe to zero elevation.

Before drawing the pipe network, `Show Flow Network` also refreshes the current Structures preview from the active `V1StructureModel`. This keeps visible Structure bodies and Drainage pipes synchronized when a Structure row was edited after an earlier preview.

For final 3D display, culvert pipe endpoints are snapped once more against the same Structure preview placement used to draw the culvert body. This preview-level snap prevents an old Structure connection point station or offset from leaving a visual gap between `inlet-03 -> culvert-01` and the culvert body.

In the Drainage editor, double-clicking a Flow Routes row previews the resolved 3D pipe segment for that route when both ends resolve to Structure connection points. Capture-only rows such as ditch-to-inlet do not create a pipe segment and are not treated as pipeline warnings.

The v1 project tree keeps Drainage source and preview objects directly under `05_Drainage`. The older child folders `Ditches`, `Culverts`, `Inlets`, and `Flow Paths` are not created for new trees because those concepts are now represented as Drainage Elements and Flow Routes in one `V1DrainageModel`.

For Structure-backed flow, pipeline segment endpoints are resolved by Flow Route direction. A culvert used as the downstream target of a route resolves to a Pipe In connection point. The same culvert used as the upstream source of the next route resolves to a Pipe Out connection point. Native culvert endpoint roles are interpreted at the current culvert placement start/end, so a stale port station from an older edit does not leave a visible gap between the pipe and the culvert body. Both `pipe-in` and `pipe_in` suffixes are treated as default Pipe In port names, but the role itself is authoritative for this endpoint normalization.

Pipeline geometry preserves the Flow Route direction. The first 3D point is the resolved From Element Pipe Out connection point, and the last 3D point is the resolved To Element Pipe In connection point. Station values are not reordered just to make an increasing station range.

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

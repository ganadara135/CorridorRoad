# CorridorRoad V1 Ditch Shape Contract

Date: 2026-04-28
Status: Draft contract
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ASSEMBLY_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_SURFACE_MODEL.md`

## 1. Purpose

This document defines how v1 represents ditch, side ditch, channel, and similar open drainage cross-section shapes.

It exists so U-shaped, L-shaped, trapezoidal, rectangular, and V-shaped ditch intent can be authored consistently without hiding drainage meaning inside generated meshes.

## 2. Scope

This contract covers:

- ditch shape parameters in `TemplateComponent.parameters`
- first-slice applied-section point roles
- drainage surface generation
- later solid/component-body handoff
- validation expectations

This contract does not cover:

- full hydraulic capacity analysis
- storm sewer network sizing
- detailed reinforced concrete detailing
- manual editing of generated ditch meshes

## 3. Core Rule

Ditch shape intent belongs in source components and drainage references.

Generated `ditch_surface`, mesh previews, and future ditch solids are derived outputs.

They must not become the durable editing source.

## 4. Source Ownership

`TemplateComponent(kind="ditch")` owns the reusable section shape intent for a ditch-like component.

`DrainageModel` may own the broader drainage purpose, collection, discharge, and constraint intent.

`RegionRow.applied_layers` and `RegionRow.drainage_refs` decide where ditch and drainage behavior is active.

`AppliedSection` stores station-specific evaluated ditch points.

`SurfaceModel` stores terrain-like drainage surface outputs derived from those points.

Future solid/component-body outputs may represent lined or structural ditch bodies.

## 5. Recommended Shape Values

Use `TemplateComponent.parameters["shape"]` to choose the ditch shape.

Recommended values:

- `trapezoid`
- `u`
- `l`
- `rectangular`
- `v`
- `custom_polyline`

If `shape` is missing, the first-slice fallback should treat the ditch as a simple sloped strip using `width` and `slope`.

## 6. Common Parameters

Common ditch parameters:

- `shape`
- `top_width`
- `bottom_width`
- `depth`
- `invert_offset`
- `inner_slope`
- `outer_slope`
- `wall_thickness`
- `lining_thickness`
- `lining_material`
- `freeboard`
- `flowline_role`
- `edge_treatment`

All values should use project length units unless the parameter name explicitly carries a unit.

## 7. Shape-Specific Parameters

### 7.1 Trapezoid

Required or recommended parameters:

- `bottom_width`
- `depth`
- `inner_slope`
- `outer_slope`

`top_width` may be derived from bottom width, depth, and side slopes.

### 7.2 U

Required or recommended parameters:

- `bottom_width`
- `depth`
- `wall_thickness`
- `lining_thickness`

`u` may initially be represented as a rectangular lined channel approximation.

A later refinement may support rounded bottom geometry, but the source contract should still preserve the same `shape = u` intent.

### 7.3 L

Required or recommended parameters:

- `bottom_width`
- `depth`
- `wall_thickness`
- `wall_side`

Recommended `wall_side` values:

- `inner`
- `outer`
- `left`
- `right`

### 7.4 Rectangular

Required or recommended parameters:

- `bottom_width`
- `depth`
- `wall_thickness`
- `lining_thickness`

### 7.5 V

Required or recommended parameters:

- `depth`
- `inner_slope`
- `outer_slope`

`bottom_width` should be treated as zero.

### 7.6 Custom Polyline

Required or recommended parameters:

- `section_points`

`section_points` should be a list of local offset/elevation pairs.

This is an advanced escape hatch and should preserve semantic roles for key points where possible.

## 8. Applied Section Point Roles

Evaluated ditch points should use `AppliedSectionPoint.point_role = "ditch_surface"` for terrain-like drainage grading surfaces.

Recommended point id role names:

- `ditch:inner_edge`
- `ditch:outer_edge`
- `ditch:invert`
- `ditch:bottom_inner`
- `ditch:bottom_outer`
- `ditch:wall_top`
- `ditch:wall_bottom`
- `ditch:lining_outer`

The current first-slice implementation emits shape-aware `ditch_surface` points for supported shapes.

If `shape` is missing, it still emits the simple `width` and `slope` fallback strip for backward-compatible starter assemblies.

## 9. Surface vs Solid Rule

Use `drainage_surface` for terrain-like ditch grading, swales, and open channel earthwork surfaces.

Use future solid/component-body outputs for:

- precast U ditch
- cast-in-place concrete channel
- L-shaped concrete gutter or side channel
- lined rectangular channel
- closed culvert or pipe bodies

A single ditch source component may therefore produce both:

- `ditch_surface` points for grading review
- future physical component bodies for material and quantity review

## 10. Validation Rules

Early validation should report warnings when:

- `shape` is unknown
- required shape parameters are missing
- `width`, `top_width`, `bottom_width`, or `depth` is negative
- `u`, `l`, or `rectangular` shape has no wall or lining thickness when material is structural
- `custom_polyline` has fewer than two points
- point order crosses itself or cannot be sorted by local lateral offset

Validation should not silently convert a structural ditch into an earth grading surface without diagnostics.

## 11. Current Implementation Status

- [x] `TemplateComponent(kind="ditch")` is supported as an Assembly component kind
- [x] ditch components are excluded from FG width
- [x] first-slice `ditch_surface` applied-section point rows are generated from `width` and `slope`
- [x] `Build Corridor` can generate conditional `drainage_surface` previews from `ditch_surface` point rows
- [x] parse shape-specific ditch parameters from `TemplateComponent.parameters`
- [x] generate shape-aware ditch point roles for trapezoid, U, L, rectangular, and V shapes
- [x] preserve ditch shape parameters through the Assembly source object and a raw Assembly editor Parameters column
- [x] add first-slice Assembly validation and Applied Section diagnostics for invalid or incomplete ditch shapes
- [x] add a first-slice structured Assembly helper for common ditch shape parameters
- [x] filter Assembly helper fields and defaults by selected ditch shape
- [x] show compact visual shape diagrams in the Assembly ditch helper
- [x] add first-slice material policy hints and validation for lined or structural ditch materials
- [x] use shape-aware ditch interpretation in the Assembly `Show` preview
- [ ] add full material-specific quantity and component-body controls for ditch shape parameters
- [ ] generate future solid/component bodies for structural ditch shapes

## 12. Non-goals

This contract does not make ditch meshes editable source geometry.

This contract does not replace `DrainageModel`.

This contract does not claim hydraulic adequacy from shape geometry alone.

## 13. Acceptance Criteria

The next code slice should be accepted when:

- a `ditch` component can declare `shape = trapezoid`, `u`, `l`, `rectangular`, or `v`
- shape-specific parameters produce deterministic `ditch_surface` points
- invalid shape parameters produce diagnostics
- existing simple width/slope ditch presets still work
- Build Corridor continues to show the derived drainage surface only when ditch points exist

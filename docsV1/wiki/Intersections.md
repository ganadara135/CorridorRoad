# Intersections

Intersections define at-grade junction intent between two or more Alignments.

They are source-stage data. They do not directly edit generated corridor surfaces.

## Purpose

Use the Intersections panel to:

- choose the intersection type
- create starter source data for a simple junction
- detect or review participating Alignments
- link intersection control Regions
- create an Intersection source model for Applied Sections and Build Parametric

## Two Ways To Use Intersections

The Intersections panel supports two user workflows.

Choose the workflow based on whether the road Alignments already exist.

### 1. Use Existing Alignments

Use this mode when the primary road and side road have already been created.

This mode links existing source data into an Intersection model.

Typical use:

1. Create or import the main-road Alignment.
2. Create or import the side-road Alignment.
3. Create matching Profile, Stationing, and Region sources for each road.
4. Open `Intersections`.
5. Set `Source Mode` to `Use Existing Alignments`.
6. Select the Primary Alignment and Secondary Alignment.
7. Use `Auto Detect` to find the crossing point.
8. Review the detected control Regions.
9. Click `Apply` to create or update the Intersection source model.
10. Run `Build Sections`.
11. Run `Build Parametric`.

This mode is best for real design work where the road geometry is already known.

It does not replace your Alignment, Profile, Stationing, or Region sources.

### 2. Create Starter Sources

Use this mode when you want Parametric Road to create a starter junction for testing or early layout.

This mode creates editable source objects first, then links them into the Intersection workflow.

Typical use:

1. Open `Intersections`.
2. Select the intersection type, such as T, Cross, or Y.
3. Set `Source Mode` to `Create Starter Sources`.
4. Click `Create Starter Sources`.
5. Confirm the status message lists created Alignment, Profile, Stationing, Region, and `3D Centerline` rows.
6. Review the generated 3D Centerline.
7. Click `Apply` to create or update the Intersection source model.
8. Run `Build Sections`.
9. Run `Build Parametric`.

This mode is best for quick testing, examples, tutorials, and early concept setup.

The generated sources are normal editable v1 source objects. You can modify them after creation.

## Starter Sources

`Source Mode = Create Starter Sources` creates editable starter data for the selected intersection type.

Preset-driven starter design uses the `Intersection` panel.

Current `Intersection` preset families are:

- `T Intersection - Basic`
- `Cross Intersection - Basic`
- `Roundabout - Single Lane`

These presets should create source intent and policy rows first. Final corridor surfaces are still generated later by `Build Sections` and `Build Parametric`.

`Intersection` supports two source modes:

- `Create From Preset`
- `Use Existing Alignments`

`Create From Preset` creates editable starter source contracts.

It also creates or reuses the Assembly/Subassembly source used by the generated control Regions.

Lane, Shoulder, and Side Slope geometry should therefore come from Applied Sections resolving those source refs, not from Intersection generating standalone review geometry.

`Use Existing Alignments` links user-created Primary and Secondary Alignment sources into the same preset-driven intersection workflow.

`Preview Edge Network` is available in both modes.

In `Create From Preset` mode, click `Create Sources` first, then use `Preview Edge Network` to review the edge network created from the generated preset Alignments and control Regions.

`Preview Edge Network` uses the current preset option values.

- `Radius / Diameter` changes the curb-return preview arcs.
- `Control Length` changes the visible control-area and leg-edge station span used by the preview.
- `Design Vehicle`, `Grading Policy`, and `Drainage Mode` are stored on the preview object as source-policy context so the user can confirm which preset settings were used.

`Grading Policy = blend_primary_side` builds the Intersection Surface as a sloped grading plane from the primary and side-road Applied Section elevations.

This lets the patch tilt toward the side-road height instead of forcing the whole intersection patch to one flat elevation.

Use `Hide Edge Network` to hide that preview object from the 3D View without deleting the source data.

In existing-alignment mode, the panel can run Auto Detect, preview the edge network, and apply the resulting `IntersectionModel`.

It can also create preset-owned Superelevation and Drainage handoff sources.

The preset panel does not directly create final corridor geometry.

Build Parametric Subassembly review highlights keep same-kind Lane, Shoulder, and Side Slope patches scoped to each Alignment so preset-created intersecting roads are not stitched together as one display strip.

The existing `Intersections` panel is not removed.

It remains available for source-model review and the earlier intersection editing workflow.

Roundabout support is currently a first-slice preset workflow.

It exposes roundabout edge-network, surface-zone, grading-context, and drainage-handoff contracts for review.

It does not yet perform final roundabout operation analysis, capacity review, hydraulic design, or final roundabout mesh certification.

The starter workflow creates:

- Alignment sources for the participating roads
- Profile sources linked to each Alignment
- Stationing sources linked to each Alignment
- Region sources for approach, intersection, and departure spans
- a multi-alignment `3D Centerline` preview

The generated 3D Centerline is created after the starter source rows are created.

It is routed to the `3D Centerline` tree folder and stores the participating Alignment IDs on the preview object.

If the 3D Centerline cannot be generated, the starter sources remain in the document and the status message reports the reason.

## 3D Centerline Behavior

Intersections can use more than one Alignment.

The 3D Centerline stage therefore supports a multi-alignment result:

- each evaluated point keeps its source Alignment reference
- the preview object draws separate curves for each Alignment
- Applied Sections consume only the 3D Centerline rows that match their active Alignment

This avoids using the primary road baseline for the side road.

## Intersection-Aware Applied Sections

Applied Sections are the formal section basis for downstream intersection surfaces.

Build Parametric should consume Applied Sections. It should not create hidden section rows as a late surface patch.

When an Intersection source exists, `Build Sections` adds result-only supplemental section stations for each participating Alignment.

These supplemental stations include:

- intersection control-area start and end stations
- the detected center station on the primary Alignment
- the detected center station on each secondary Alignment
- curb-return control stations around the center station, based on the active curb-return radius
- midpoint samples inside the intersection control range

The original Stationing source is not edited.

The extra stations exist only in the generated AppliedSectionSet result so Design Surface, Slope Face Surface, Intersection Surface, Cross Section Viewer, and downstream solids can share the same station frames.

The Applied Sections review table shows these rows with `Kind = intersection_supplemental`.

Cross Section Viewer Station Navigation lists the Alignment context with each station row. Use the primary and secondary Alignment station rows to review the correct Intersection Context for each leg.

Build Parametric Guided Review reports `intersection supplemental sections=N` so users can confirm the intersection handoff stations were included before surface review.

Curb-return arc start/end and sampled arc contact points are treated as Applied Sections handoff points when the edge-network result exposes `contact_station_refs`.

If exact arc-contact station refs are not available, Applied Sections fall back to the intersection center station, control ranges, and curb-return radius to add stable main-road and side-road supplemental stations.

In Build Parametric, the `Intersections` tab is a contract review table.

Double-click an `Intersections` table row to create a bright `Intersection Contract Highlight` object in the 3D View.

The highlight focuses the selected contract row. Edge rows highlight the selected edge, Surface Zone rows highlight their source/boundary edges, and broader Topology or Corridor Clip rows highlight the available intersection boundary or exclusion loop.

During Build Parametric, the `Intersection Surface` owns its footprint.

`Slope Face Surface` triangles inside the `Intersection Surface` footprint are suppressed even when they are lower than the intersection patch.

This prevents ordinary corridor daylight faces from being generated inside the junction patch area.

Outside the `Intersection Surface` footprint, Slope Face Surface generation remains allowed.

Curb-return and Applied Section tie-in faces should be generated outside that footprint instead of being blocked only because they are near the intersection pavement strip.

Build Parametric also uses both side-road and primary-through Applied Sections as slope-face tie-in edges around curb-return bands.

Primary-through Applied Sections use a distance-based boundary extension so the opposite main-road side can fill against the intersection Slope Face boundary.

Side-road corner Slope Face boundary strips are deferred.

Nearest curb-return arc sample matching was removed because it was not reliable enough for production geometry.

The next Slope Face rule is boundary-first.

Build Parametric should derive an `Intersection Slope Face Boundary` from the `Intersection Surface` edge and nearby Applied Section end points.

That boundary defines the strip between the junction patch and the ordinary corridor daylight edge.

Users should review this boundary before trusting the generated `Intersection Slope Face Surface`.

## Region Behavior

Intersection starter sources create Region rows per participating Alignment.

Build Parametric reads all Region source models, not only the first one.

The `Region Boundaries` table includes an `Alignment` column so primary-road and side-road Regions can be reviewed separately.

Double-click a Region row to show the built object set for that Region.

## Recommended Flow

Use this sequence for the starter workflow:

1. Open `Intersections`.
2. Select the intersection type.
3. Set `Source Mode` to `Create Starter Sources`.
4. Click `Create Starter Sources`.
5. Confirm the status message includes `3D Centerline`.
6. Review the generated 3D Centerline.
7. Apply the Intersection source model.
8. Run `Build Sections`.
9. Run `Build Parametric`.
10. Review `Region Boundaries`, `Intersections`, and `Slope Face Issues`.

## Current Limits

Intersection support is a first-slice workflow.

Build Parametric can separate multi-alignment design and slope-face surface generation, but a dedicated `Intersection Surface Patch` is still future work.

Until that patch exists, the junction area should be reviewed in Build Parametric before relying on downstream solids or simulation outputs.

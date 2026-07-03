# Intersections

Intersections define at-grade junction intent between two or more Alignments.

They are source-stage data. They do not directly edit generated corridor surfaces.

## Purpose

Use the `Intersection` panel to:

- choose the intersection type
- create starter source data for a simple junction
- detect or review participating Alignments
- link intersection control Regions
- create an Intersection source model for Applied Sections and Build Parametric

## Two Ways To Use Intersection

The `Intersection` panel supports two user workflows.

Choose the workflow based on whether the road Alignments already exist.

### 1. Use Existing Alignments

Use this mode when the primary road and side road have already been created.

This mode links existing source data into an Intersection model.

Typical use:

1. Create or import the main-road Alignment.
2. Create or import the side-road Alignment.
3. Create matching Profile, Stationing, and Region sources for each road.
4. Open `Intersection`.
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

Preset-authored default and draft rows carry a `source_completeness_ref` note that points back to the preset source-completeness audit.

Y preset branch rows also carry `branch_review_ref=intersection-preset:y_intersection:branch-review` for branch geometry and diverge/merge movement review.

Skewed preset rows carry `skew_review_ref=intersection-preset:skewed_intersection:skew-review` for skew geometry, corner, and edge-family review.

Urban curb/gutter preset rows carry `urban_review_ref=intersection-preset:urban_curb_gutter_intersection:urban-curb-gutter-review` for curb, gutter, sidewalk, inlet, and low-point review.

Drainage-sensitive sag preset rows carry `sag_review_ref=intersection-preset:drainage_sag_intersection:sag-drainage-review` for sag Profile, low-point, inlet candidate, and flow-route review.

It also creates or reuses the Assembly/Subassembly source used by the generated control Regions.

Lane, Shoulder, and Side Slope geometry should therefore come from Applied Sections resolving those source refs, not from Intersection generating standalone review geometry.

`Use Existing Alignments` links user-created Primary and Secondary Alignment sources into the same preset-driven intersection workflow.

Standalone edge-network geometry is no longer exposed from the panel.

In `Create From Preset` mode, click `Create Sources`, then review the source summary and user-facing Intersection contracts in Build Parametric `Intersections`.

Current preset option values are stored on source rows and carried into result diagnostics.

- `Radius / Diameter` changes the curb-return source policy.
- `Control Length` changes the control-area and leg-edge station span used by evaluation.
- `Design Vehicle`, `Grading Policy`, and `Drainage Mode` are stored as source-policy context for Build Parametric diagnostics.

`Grading Policy = blend_primary_side` builds the Intersection Surface as a sloped grading plane from the primary and side-road Applied Section elevations.

This lets the patch tilt toward the side-road height instead of forcing the whole intersection patch to one flat elevation.

Standalone edge-network geometry is not exposed as a panel command.
Low-level edge-network, surface-zone, drainage-hint, slope-face-cell, and shared-boundary-graph rows are hidden from the normal Build Parametric `Intersections` table.
Use the higher-level topology, boundary loop, Intersection Tie Slope window, upper slope-face panel, Results, and Breakline Audit rows for review.

In existing-alignment mode, the panel can run Auto Detect and apply the resulting `IntersectionModel`.

It can also create preset-owned Superelevation and Drainage handoff sources.

The preset panel does not directly create final corridor geometry.

Build Parametric Subassembly review highlights keep same-kind Lane, Shoulder, and Side Slope patches scoped to each Alignment so preset-created intersecting roads are not stitched together as one display strip.

The older `Intersections` command is no longer exposed in the workbench workflow.

Use the single `Intersection` panel for starter source creation, existing Alignment linking, edge-network preview, and source-model application.

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

The highlight focuses the selected contract row when a row still has explicit review geometry.
Rows that represent accepted generated outputs, such as `intersection_tie_slope_window` or the upper slope-face panel, focus the generated preview surface instead.

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

Visible boundary strip generation is currently suppressed.

Build Parametric records the boundary metadata but does not force rectangular strip patches into the `Slope Face Surface`.

The active Slope Face fill path uses the pre-clip Side Slope TIN and evaluated Applied Section side-slope edges.

After intersection footprint clipping, Build Parametric first restores missing `intersection_side_slope_strip` triangles from the pre-clip Side Slope TIN when the triangle is outside the `Intersection Surface` footprint.

Build Parametric may also add a narrow Applied Section edge strip only when:

- the candidate strip comes from adjacent `AppliedSection` slope-face edge rows
- the strip is not already covered by the current Slope Face TIN
- the strip is outside the Intersection Surface footprint
- the strip is adjacent to the current Slope Face TIN boundary

This keeps the green Side Slope result and the generated `Slope Face Surface` aligned without restoring forced white boundary patches.

Users should review this boundary and the side-slope strip count before trusting future generated `Intersection Slope Face Surface` output.

## Intersection Tie Slope And Upper Slope Face

Build Parametric now separates three slope-face output families near intersections:

- ordinary `Slope Face Surface`
- dedicated `Intersection Slope Face Surface`
- dedicated `Intersection Tie Slope Surface`

`Intersection Tie Slope Surface` is generated from accepted Applied Section window rows.
It uses the transition between ordinary-corridor Applied Sections and active-intersection Applied Sections as its source.
Temporary `Intersection Tie Slope Highlight` objects are no longer generated.

The Build Parametric `Intersections` tab shows the compact `intersection_tie_slope_window` row for this handoff.
Double-clicking that row focuses the generated `Intersection Tie Slope Surface` preview.

The upper rectangular slope-face panel is reviewed through `Intersection Slope Face Surface` metadata and Breakline Audit rows.
Temporary `Intersection Upper Slope Face Panel Highlight` objects are no longer generated.

Review these outputs in this order:

1. Results: confirm `Intersection Slope Face Surface` and `Intersection Tie Slope Surface` are `ready`.
2. Intersections: confirm `intersection_tie_slope_window` is present and low-level legacy rows are hidden.
3. Breakline Audit: confirm shared breakline counts are consumed with no geometry or mesh mismatch.
4. Visibility: toggle ordinary `Slope Face Surface`, `Intersection Slope Face Surface`, and `Intersection Tie Slope Surface` independently.

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

Topology evaluation now reports first-slice source-completeness diagnostics for missing leg Profile refs, 3D Centerline refs, Region refs, control Region refs, and missing curb-return, grading, or drainage policy rows.

Edge Network rows also carry first-slice source status for unresolved edge policy refs and incomplete curb-return policy context.

Surface Zone rows carry first-slice source status from the Edge Network rows they consume, so a zone can warn when its source edges are unresolved, defaulted, or incomplete.

Slope Face Loop rows also carry consumed Surface Zone refs and consumed Edge Network source status, so an intersection-owned Slope Face loop can report source warnings or errors before surface output is trusted.

Applied Sections carry active intersection source status and named source diagnostics for station-level review.

Cross Section Viewer shows a `source_status` context row before topology, edge, surface-zone, clip, grading, and drainage rows.

Intersection Context rows include Handoff Owner, Handoff Target, and Lineage fields so a station warning can point back to `Intersection`, `Applied Sections`, or `Build Parametric` without editing generated section output.

The Cross Section Viewer handoff summary also includes these Intersection Context targets, so source-stage warnings, frame-source fallback rows, and Build Parametric result rows share the same station handoff context.

Build Parametric's `Intersections` review rows expose source status and source diagnostics in the table columns so missing source intent is visible before trusting surface or solid outputs.

For Slope Face Loop rows, the review notes also include source lineage, consumed Surface Zone status, and consumed Edge Network status when those values are not accepted.

Intersection output previews store consumed contract diagnostics, including row-level source diagnostics from warning/error Slope Face loops that were skipped from surface triangulation.

These diagnostics are result warnings unless a required source relationship is missing badly enough to block topology.

Intersection preset drainage is source-stage handoff metadata.

Build Parametric does not use `drainage:intersection-preset-*` models as Drainage Flow highlight sources.

Create real Drainage source rows before using Drainage Flow review highlights.

Build Parametric now exposes a dedicated `Intersection Surface Patch` result contract with boundary, triangulation, and quality rows normalized from the current patch output.

That contract is marked `output_contract_status=transitional_normalized` with `digital_twin_handoff=review_required` until accepted intersection surface-zone output replaces the legacy patch surface path.

Its `IntersectionSurfacePatchFootprintSummary` is derived from normalized boundary and triangulation rows and summarizes footprint, curb-return, and tie-in evidence without restoring legacy patch-only review details.

Build Parametric also exposes accepted Intersection Surface Zone output rows that consume `IntersectionSurfaceZoneResult` and `IntersectionEdgeNetworkResult` directly.

Those rows are marked `contract_status=accepted_surface_zone` and `digital_twin_handoff=accepted_zone_candidate`; their geometry backend remains `planned_edge_network_zone_surface` until the accepted zone-surface builder replaces the transitional patch surface.

Accepted Surface Zone output rows preserve result lineage including source/boundary/inner/outer/tie edge refs, leg refs, alignment refs, control-area refs, vertical policy ref, source status, and diagnostics.

Build Parametric review notes summarize the same accepted Surface Zone output lineage, so review does not depend on legacy patch-only properties.

`V1CorridorIntersectionSurfaceZoneOutputPreview` is no longer created by default.

The earlier linework preview could expose accepted Surface Zone edges outside the actual intersection control area, so the visible FreeCAD object was removed while the normalized Surface Zone output contract remains available on the main Intersection preview.

`V1CorridorIntersectionSurfaceZoneSurfacePreview` is no longer created by default.

The earlier TIN preview could expose fan-triangulated edge strips outside the actual intersection control area, so the visible FreeCAD object was removed while the normalized Surface Zone output contract remains available.

`IntersectionSurfaceReplacementGateStatus` records that comparison gate on the transitional patch preview.

The current gate is `blocked` until a control-area-safe accepted zone-surface builder is implemented.

In Build Parametric output review, `Intersection Surface` remains the transitional patch row.

Output path labels distinguish `contract_consumed`, `legacy_output`, `inferred_fallback`, `review_gate`, and `missing_source` so missing source rows are not reported as consumed contracts.

Intersection Contract summaries also show `source status=...` distributions so accepted, warning, error, and missing source states remain visible even before opening the detailed contract rows.

Build Parametric also shows `Intersection Replacement Readiness` as a separate review row.

That row uses `output_path=review_gate` and reports whether the accepted zone-surface path is `review_only`, `ready_to_replace`, or `blocked`, along with patch/zone triangle comparison and the current replacement recommendation.

The same readiness is copied onto accepted zone output previews as downstream handoff metadata.

While the gate is review-only, the transitional patch is labeled `fallback_review_required` and the accepted zone-surface is labeled `preferred_candidate_review_only`.

Downstream handoff selection follows the same gate.

While readiness is `review_only` or `blocked`, the selected handoff remains the transitional patch fallback.

When readiness becomes `ready_to_replace`, the selected handoff can move to the accepted zone-surface.

The handoff decision is also available as a reusable output contract helper, so preview metadata and later output/export consumers can apply the same `review_only`, `ready_to_replace`, or `blocked` rule.

The replacement gate also records acceptance evidence diagnostics.

For the current review-only gate, those diagnostics require accepted zone-surface review, boundary lineage verification, and triangle-delta review before the accepted zone-surface may replace the transitional patch.

For slope-face output, Guided Review prefers `Intersection Slope Face Boundary` metadata when it is available and labels that path as `boundary_review=intersection_slope_face_boundary_result`.

Intersection-owned Slope Face review rows also report consumed Slope Face Loop contract summary and diagnostic counts, so review does not rely only on generated ready/skipped loop counts.

When Slope Face output has consumed contract refs, Build Parametric labels it `output_path=contract_consumed` even if the consumed contract rows are warning-only and no ready loop geometry is produced.

Legacy `Patch*` metrics remain on the preview object for compatibility and focused diagnostics.

When normalized `IntersectionSurfacePatch*` rows are available, Build Parametric review notes mark those legacy details as `legacy_patch_review=metadata_only` and show the normalized Surface Patch summary, row statuses, replacement gate, and accepted zone-surface handoff instead.

The preview also stores `IntersectionLegacyPatchCompatibilityAudit` rows that map compatibility `Patch*` properties to the normalized Surface Patch metadata that replaces them in review.

When reviewing intersections, Guided Review and intersection-specific preferred focus choose the accepted zone-surface preview first.

The transitional patch row remains visible as fallback context until the replacement gate passes.

Watertight Solids may expose an `intersection_patch_body` target for the current patch handoff.

That target is marked transitional with `quality_status=transitional` and `digital_twin_handoff=review_required` until accepted edge-network zone solid contracts replace the thin patch-prism path.

The Watertight and Simulation Package handoff also carries the replacement gate, readiness, downstream selected role, and legacy patch audit summary.

This keeps transitional patch-body blockers aligned with the Build Parametric replacement gate instead of treating the patch prism as final-quality output.

Package diagnostics distinguish `review_only`, `blocked`, and `ready_to_replace` replacement states with readiness-specific diagnostic kinds alongside the broad final-handoff blocker.

Persisted Simulation Package objects expose the selected readiness-specific kind as `IntersectionHandoffReplacementBlockerKind`, and JSON package export exposes the same value as `intersection_handoff.replacement_blocker_kind`.

Simulation QA exposes the same replacement blocker before package build through `V1SimulationQaOutput.IntersectionReplacementBlockerKind`.

When Simulation Package output is wrapped into an ExchangePackage, a `simulation_package_intersection_handoff` source-context row carries the same blocker and readiness values for downstream exchange review.

ExchangePackage metadata also carries a compact Intersection handoff count and replacement blocker summary for automation that does not inspect every source-context row.

JSON exchange export preserves the same compact metadata and returns the blocker summary in the export result.

IFC exchange export and Structure Output preview summaries also surface the blocker when a package still depends on transitional Intersection patch fallback.

Build Parametric preview objects expose `IntersectionSurfaceReplacementBlockerKind` from the shared surface output-contract rule, so later Watertight and Exchange steps do not reinterpret legacy patch metadata independently.

<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Parametric Road addon. -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses Semantic Versioning.

## [Unreleased]

### Added
- Added first-slice Intersection source-completeness diagnostics in topology, edge-network, and surface-zone evaluation for missing leg Profile, 3D Centerline, Region, control Region, and source policy context.
- Added Intersection contract source status and source diagnostics to Build Parametric review rows and panel columns, including source warning counts in the compact summary.
- Added Applied Sections intersection source status handoff and Cross Section Viewer `source_status` context rows for station-level review.
- Added Applied Sections intersection source-stage handoff rows so Cross Section Viewer can show Anchor, Control Areas, and Edge Families source ownership for station warnings.
- Added explicit Applied Section frame source mode/status rows so Cross Section Viewer can distinguish source-geometry Centerline3D frames from fallback station frames.
- Added Cross Section Viewer Intersection Context handoff owner and target columns for routing station warnings back to Intersection, Applied Sections, or Build Parametric review surfaces.
- Added Watertight Solids transitional diagnostics for `intersection_patch_body` targets so users must review them before Digital Twin handoff use.
- Added first-slice `IntersectionAnchorRow` source contracts with FreeCAD object persistence and panel-created draft anchor rows.
- Added first-slice intersection anchor topology result rows so accepted station/point mappings carry source status, tolerance, station refs, and diagnostics into Build Parametric source review.
- Added first-slice intersection control-area intent result lineage so topology and corridor clipping rows carry source refs, intent status, Region lineage status, and source diagnostics.
- Added first-slice intersection lane-connection result lineage so topology rows carry source refs, movement lineage status, leg source status rollups, and edge-family source status.
- Added first-slice intersection grading-context source lineage so rows carry source grading policy refs, Profile lineage status, Superelevation source status, vertical handoff status, and fallback/default status.
- Added first-slice intersection drainage accepted-vs-hint result status so hint rows carry source drainage policy refs, accepted handoff status, review status, and source-owned drainage refs.
- Added first-slice staged Intersection panel source-completeness summary for Participants, Anchor, Legs, Control Areas, Corners, Edge Families, Lane Connections, Grading, Drainage, and Preview.
- Added actionable Intersection source-completeness summary counts, next-stage guidance, and preview/apply readiness text to the staged panel workflow.
- Added first-slice same-context Intersection source-stage targets and panel focus helper so source-completeness rows can be selected by stable handoff target.
- Added first-slice Intersection source approval states in the staged panel so missing, draft, accepted, and locked source stages remain visually distinct from source status.
- Added first-slice read-only Intersection preview sequence rows for source validation, topology, edge network, surface zones, grading, drainage, and slope loops.
- Added first-slice Intersection leg source method, approval status, span source, and diagnostic rows with topology and station-context source warnings.
- Added first-slice Intersection control-area source method, approval status, intent status, source Region refs, and diagnostics so Region-derived ranges are not silently treated as accepted source intent.
- Added first-slice `IntersectionCornerRow` source contracts, corner-based curb-return policy refs, object persistence, and edge-network corner lineage diagnostics.
- Added first-slice Intersection edge-family source intent fields for Assembly/Subassembly lineage, approval status, subassembly kind, and edge-network diagnostics.
- Added first-slice `IntersectionLaneConnectionRow` source contracts, object persistence, starter default lane movement rows, and topology lane-connection diagnostics.
- Added first-slice Intersection grading source intent fields for controlling profile, crown behavior, tie-in rule, crossfall transition, low-point strategy, and grading-context source diagnostics.
- Added first-slice Intersection drainage source intent fields for accepted drainage elements, flow routes, inlet candidates, low-point refs, hint-only status, and drainage-hint source diagnostics.
- Added Build Parametric Intersection output-path labels for `contract_consumed`, `inferred_fallback`, and `legacy_output` review rows.
- Added Build Parametric Intersection consumed-contract metadata for Surface and Slope Face output previews.
- Added first-slice `IntersectionSurfacePatchResult` rows for normalized boundary, triangulation, and patch quality review.
- Added Intersection Slope Face Boundary result metadata to generated strip output and review previews.
- Added accepted Intersection zone Watertight Solid target handoff metadata from surface-zone and edge-network contracts.
- Added Simulation Package final-quality blocking for transitional-only Intersection patch solids, with persisted/exported handoff status metadata.
- Added Intersection trim/fuse handoff status to Simulation QA, including trim pair counts, max gap, fuse status, accepted/fallback status, and diagnostics.
- Added row-level Watertight Solid source lineage preservation through object roundtrip, Simulation Package rows, package JSON export, and Exchange source-context rows.
- Added T/Cross Intersection preset source-completeness markers so preset-created default/draft source rows carry explicit review-required diagnostics.
- Added a source-driven Y Intersection starter preset with primary/left/right branch roles and review-required branch diagnostics.
- Added a source-driven skewed Intersection starter preset with non-orthogonal Alignment geometry and skew review diagnostics.
- Added a source-driven urban curb/gutter Intersection starter preset with curb, gutter, sidewalk, and inlet handoff source rows.
- Added a source-driven drainage-sensitive sag Intersection starter preset with sag Profile controls, low-point refs, inlet candidates, and flow-route review diagnostics.
- Added Intersection source object reload coverage for anchor, corner, lane-connection, edge-family, grading, and drainage intent rows.
- Added staged Intersection panel smoke coverage for preset-created warning source rows without applying output geometry.
- Added Intersection manual QA records for T, Cross, Skewed, Urban Curb/Gutter, Drainage-Sensitive Sag, Y, and Roundabout presets.
- Added Intersection manual regression QA for Lane, Shoulder, and Side Slope stitching across unrelated alignment scopes.
- Added Intersection Anchor source validation diagnostics for unknown source methods and approval statuses.
- Added Intersection Leg source validation diagnostics for unknown source methods, approval statuses, and span sources.
- Added Intersection Control Area source validation diagnostics for unknown source methods, approval statuses, and intent statuses.
- Added Intersection Corner source validation diagnostics for unknown source methods, approval statuses, missing control-area or side refs, and curb-return policy mismatches.
- Added Intersection Edge Family source validation diagnostics for unknown family intents, source methods, approval statuses, missing source policy refs, and Subassembly kind mismatches.
- Added Intersection Lane Connection source validation diagnostics for unknown movement types, source methods, approval statuses, and missing edge-policy refs.
- Added Intersection Grading Policy source validation diagnostics for unknown grading modes, source methods, approval statuses, crown behavior, tie-in rules, crossfall transitions, and low-point strategies.
- Added Intersection Drainage Policy source validation diagnostics for unknown capture modes, intent statuses, source methods, and approval statuses.
- Added Intersection Slope Face loop result source lineage fields for consumed surface-zone status, source diagnostics, and lineage status.
- Added Intersection Anchor result station-lineage status and source-stage handoff target fields.
- Added Intersection Control Area result Region/clipping handoff status and source-stage handoff target fields.
- Added Intersection Lane Connection result leg/edge handoff status and source-stage handoff target fields.
- Added Intersection Grading Context result profile/superelevation handoff status and grading review handoff target fields.
- Added Intersection Drainage Hint result source-lineage status and drainage source-stage handoff target fields.
- Added Applied Sections Intersection source summary counts and warning metadata on `V1AppliedSectionSet` result objects.
- Added Build Parametric Intersection Contract source-lineage warning propagation for Slope Face Loop rows.
- Added clearer transitional reason and accepted-zone replacement guidance for Watertight `intersection_patch_body` targets.
- Added Intersection final handoff package validation for transitional patch blockers and accepted zone candidates.

## [1.0.7] - 2026-06-23

### Changed
- Updated the local development and QA documentation for FreeCAD 1.1.1, including the `v1-1` AppData workbench path and FreeCADCmd location.
- Renamed the user-facing `Intersection Presets` command to `Intersection` and removed the older `Intersections` command from workbench registration and workflow exposure.
- Clarified the active intersection workflow so starter source creation remains source-driven through Assembly/Subassembly, Region, Applied Sections, and Build Parametric contracts.

### Fixed
- Fixed Subassembly kind review highlight continuity so Lane, Shoulder, and Side Slope review geometry does not stitch across unrelated intersection alignment scopes.

## [1.0.5] - 2026-06-15

### Added
- Added the active Subassembly editor path as the practical replacement for the old Assembly Component workflow.
- Added Subassembly-focused contract coverage for Applied Sections, Build Parametric, Cross Section Viewer, quantity, watertight solid, and output mapper handoff paths.
- Added Intersection review refinements for edge-network preview, tree routing, contract visibility, and Build Parametric review handoff.

### Changed
- Changed v1 cross-section and output terminology from Component-centered wording to Subassembly-centered wording across active source/result/output/viewer paths.
- Changed Cross Section Viewer handoff actions to open the Subassembly-based Assembly workflow and report focused Subassembly context.
- Changed documentation and Wiki drafts to describe Subassembly as the active v1 cross-section building block.

### Fixed
- Fixed Applied Sections build failures caused by stale Component-to-Subassembly rename leftovers.
- Fixed Cross Section Viewer panel creation so missing focused Subassembly context and optional empty review rows no longer fall back to a summary-only error dialog.
- Fixed 3D Centerline Apply feedback so successful generation is reported to the user.

## [1.0.4] - 2026-06-04

### Added
- Added first-slice Intersections starter-source workflow support for multi-alignment T/cross/Y junction setup.
- Added automatic multi-alignment 3D Centerline generation after Intersections `Create Starter Sources`.
- Added multi-alignment 3D Centerline preview support so primary and side-road baselines are drawn as separate curves in one review object.
- Added Build Parametric Region Boundary support for all participating Region source models, with an Alignment column for primary-road and side-road Region review.
- Added local Wiki documentation for Intersections, starter sources, multi-alignment 3D Centerline behavior, and Build Parametric Region review.

### Changed
- Changed Applied Sections generation so multi-alignment Centerline3DResult rows are filtered by the active Alignment before station frames are resolved.
- Changed Build Parametric surface generation so Design, Subgrade, and Slope Face surfaces are built per Alignment group before being merged into one preview result.
- Changed Region preview creation to filter by both Region and Alignment, avoiding cross-alignment Region preview mixing.
- Changed Intersections starter status reporting so 3D Centerline generation success or failure is visible in the panel status text.

### Fixed
- Fixed side-road Intersections workflows where downstream Applied Sections could fall back to Alignment/Profile because only the primary 3D Centerline was available.
- Fixed Build Parametric Region Boundaries showing only the first RegionModel in multi-alignment intersection projects.
- Fixed Slope Face Surface generation that could connect unrelated Alignment section rows across a junction.

## [1.0.3] - 2026-05-31

### Added
- Added a first-slice v1 Superelevation source workflow with a dedicated toolbar stage after `3D Centerline`, persisted `V1SuperelevationSource` objects, validation, Apply, station sample review, and 3D crossfall-bar preview.
- Added Superelevation evaluation and sampling services so station-based crossfall intent is resolved through shared v1 service contracts rather than task-panel-local logic.
- Added Applied Sections integration for Superelevation, including effective lane/shoulder crossfall storage, source provenance, review-table summaries, Cross Section Viewer notes, and persisted round-trip context.
- Added Build Parametric verification for Superelevation-resolved Design Surface output, ensuring Design Surface TIN generation consumes Applied Section `fg_surface` rows instead of evaluating Superelevation directly.
- Added Superelevation `Auto Calculate`, which generates traceable Crossfall Control Rows and Transitions from Alignment curve radius, design speed, side friction, maximum superelevation, and transition-length criteria.
- Added a Superelevation Apply completion message so successful persistence is clear to the user.
- Added `Smooth Curve` / `Polyline` display mode options to the 3D Centerline panel.
- Added Superelevation manual QA and Wiki draft documentation covering source ownership, rebuild order, review behavior, and current limitations.

### Changed
- Changed the recommended v1 workflow order to place `Superelevation` after `3D Centerline` and before `Assembly`, `Regions`, and `Applied Sections`.
- Changed Superelevation authoring so legacy preset data is removed in favor of Auto Calculate or explicit manual table rows.
- Changed 3D Centerline preview display so `Smooth Curve` uses B-Spline presentation with polyline fallback while downstream calculations still use `Centerline3DResult` station/frame data.
- Changed Drainage editor first-entry behavior so Elements, Policies, and Flow Routes start empty when no `V1DrainageModel` exists; presets still load only after explicit selection.
- Changed Drainage editor row action buttons into a two-line layout to reduce horizontal crowding.
- Changed README and Wiki workflow descriptions so Assembly remains the default crossfall source while Superelevation is described as the station-based override source.

### Fixed
- Fixed Superelevation validation false positives at displayed station-range boundaries caused by three-decimal table rounding.
- Fixed minimum transition-length validation so equal-length generated transitions are not reported as shorter because of floating-point noise.

## [1.0.2] - 2026-05-28

### Added
- Added a Build Parametric stabilization plan covering surface preview reliability, Region Boundary review, Surface Transition rebuild behavior, Drainage handoff, tree-visible outputs, and Watertight Solids prerequisites.
- Added a dedicated Watertight Solids toolbar icon that reflects simulation-ready watertight solid output.

### Changed
- Changed Build Parametric generated preview and diagnostic objects so they are routed under `04_Corridor Model / Build Parametric Outputs` for tree-based hide/show and property inspection.
- Changed the Watertight Solids panel so existing `V1WatertightSolidOutput` objects are routed under `09_Outputs & Exchange / Watertight Solids` when the panel opens or refreshes.
- Changed Drainage Elements so the `Connection Point` column is no longer user-facing; Flow Routes now resolve Pipe In / Pipe Out endpoints from Structure-owned connection points by route direction.
- Changed Drainage Flow Network preview so Structure connection point endpoints with implicit elevation use the shared `3D Centerline` height instead of falling back to a zero-elevation Alignment plane.
- Changed the Drainage preset selector so it opens with an empty preset choice and only loads preset data after an explicit user selection.
- Changed Applied Sections row double-click preview to display only the selected Assembly section line, using wire linework instead of marker geometry.

### Fixed
- Fixed Drainage Flow Network previews that could appear along the Alignment plane when older Structure connection point rows contained implicit `0.0` invert values.
- Fixed Applied Sections 3D review clutter by removing the station marker from selected Assembly section previews.

## [1.0.1] - 2026-05-15

### Added
- Added current release-preparation documentation covering the post-`1.0.0` v1 scope, manual QA checklist, release-note draft, and tag readiness items.
- Added a v1 centerline ownership consolidation plan that makes `Centerline3DResult` the shared baseline owner and defines how Applied Sections should consume it without owning a second 3D centerline.
- Added `Centerline3DFrameService` and changed Applied Sections frame generation to prefer the shared `Centerline3DResult` while keeping legacy Alignment/Profile fallback diagnostics during transition.
- Added Applied Sections validation for required source availability and shared `Centerline3DResult` station coverage before section generation.
- Changed Structures, Drainage, and Build Corridor shared-centerline preview paths to use `Centerline3DFrameService` for station and station/offset lookup instead of command-local interpolation.
- Changed ambiguous `3d_centerline` provenance to explicit `centerline3d_result` or `applied_section_frame` path-source labels for Structures and structure solid outputs.
- Removed Build Corridor's Applied Sections frame fallback for corridor centerline preview creation; the centerline review object now requires the shared `Centerline3DResult`.
- Added persisted Watertight Solid row `path_source`/`PathSources` provenance so road, structure, and drainage solid outputs retain their baseline or coordinate source through object round-trip.
- Updated Cross Section Viewer and output documentation so `Centerline3DResult` is the shared baseline owner and `AppliedSection.frame` is a derived station placement snapshot.
- Changed the `3D Centerline` preview object routing so generated centerline objects appear under `02_Alignment & Profile -> 3D Centerline` in the v1 project tree.
- Changed the `3D Centerline` preview shape from station-to-station polyline display to BSpline interpolation, with polyline retained only as a fallback.
- Added optional `3D Centerline` station marker display so users can show or hide evaluated station markers separately from the smooth centerline curve.
- Changed optional `3D Centerline` station markers from round spheres to high-contrast 3-axis cross markers so station points are easier to distinguish in 3D review.
- Added a high-visibility selected station marker for Applied Sections row double-click review so the chosen STA is visible in the 3D View alongside the section preview.
- Added a v1 `3D Centerline` toolbar-stage implementation plan for promoting the evaluated centerline into a read-only common baseline review stage after `Review Plan/Profile`.
- Added the first v1 `3D Centerline` toolbar implementation with `Centerline3DResult`, Alignment/Profile/Stationing evaluation, read-only task panel, preview object routing, and contract tests.
- Changed Structures preview and connection point preview to prefer the shared `Centerline3DResult` station/offset/elevation frame when available.
- Changed Drainage pipeline geometry, segment preview, and Flow Route review output to prefer the shared `Centerline3DResult` station/offset frame before falling back to Alignment-only sampling.
- Changed Build Corridor centerline preview and guided review to prefer the shared `Centerline3DResult` while preserving Applied Sections fallback behavior.
- Added first-slice Drainage pipeline segment candidates that resolve Flow Route endpoints through Structure connection points and expose candidate status in Drainage Review.
- Added a Drainage Review 3D preview for selected pipeline segment candidates, routed under Drainage in the v1 project tree.
- Added `DrainagePipelineResult` and dedicated Drainage output segment rows so ready Flow Route candidates are promoted into traceable pipeline segment results.
- Added a Drainage Review `Pipeline Segments` tab and 3D preview for resolved pipeline segment output rows.
- Added Alignment station/offset frame support for Drainage pipeline candidate and segment previews, with `CoordinateMode` recorded on preview objects.
- Added Drainage pipeline geometry output rows that derive centerline polylines from resolved pipeline segments and feed the segment preview path.
- Added Drainage pipeline solid candidate output rows with capped pipe metadata, derived length, candidate volume, and Flow Route review status.
- Added `drainage_pipeline_body` Watertight Solid target discovery and first-slice capped pipe solid build support for ready Drainage pipeline segments.
- Added Drainage pipeline network output rows, a Drainage Review `Pipeline Networks` tab, and `drainage_pipeline_network_body` Watertight Solid target/build support using first-slice compound pipe solids.
- Added a Drainage Review 3D preview for selected pipeline network rows, including project-tree routing under Drainage and recorded segment/Flow Route provenance.
- Added best-effort boolean fuse for Drainage pipeline network Watertight Solid builds, with `single_segment` and `compound_fallback` fuse-mode provenance when full fuse is not applicable or robust.
- Added Drainage pipeline junction output rows and a Drainage Review `Pipeline Junctions` tab to expose network junction/terminal degree, point, segment refs, Flow Route refs, and pending trim status.
- Added first-slice Drainage pipeline junction connector bodies during network Watertight Solid builds, with `connector_count` provenance before boolean fuse/fallback.
- Added Structure connection point provenance on Drainage pipeline junction rows and terminal connector bodies for Structure-backed pipe endpoints during network Watertight Solid builds.
- Added Structure ref and connection point ref propagation from Drainage pipeline terminal rows into Watertight pipeline network output provenance.
- Added reuse of already built `structure_body` Watertight Solid output shapes during Drainage pipeline network builds, with `structure_body_count`, `structure_body_object_refs`, and `structure_fuse_status` provenance.
- Added direct first-slice `structure_body` Watertight Solid builds from StructureModel native geometry specs through the Structure solid output service.
- Added automatic Structure body dependency builds for Drainage pipeline network Watertight Solid builds and ordered `Build Enabled` execution so Structure targets run before pipeline network targets.
- Added first-slice Structure port bridge connector bodies for Drainage pipeline network builds, with `port_connector_count` and `port_connector_status` provenance when pipe terminals need overlap volume to fuse with Structure bodies.
- Changed Structure port bridge connector generation to prefer Structure connection point diameter/width/height and direction before falling back to pipe diameter and Structure body center targeting.
- Added first-slice Drainage pipeline endpoint trimming for Structure-backed terminals that start inside a matched Structure body, with `endpoint_trim_count` and `endpoint_trim_status` provenance.
- Changed native `inlet`, `outlet`, and `headwall` Structure body placement to use source connection point offset and invert/elevation when the Structure placement has no explicit offset, reducing unnecessary Drainage port bridge connectors.
- Added first-slice native Drainage endpoint body details: inlet bodies get an internal chamber cut, and outlet/headwall bodies get a pipe opening cut from connection point diameter when available.
- Changed `pipe_culvert` and circular culvert `structure_body` Watertight Solid builds to use cylindrical Part geometry instead of rectangular envelope solids.
- Added hollow circular culvert wall `structure_body` builds when `wall_thickness` is set, using an inner-cylinder cut from the outer pipe body.
- Added External Ref Structure body reuse for Watertight Solids, allowing `structure_body` targets to reuse a referenced FreeCAD object's Shape via `geometry_ref`.
- Added Watertight Solid target validation that blocks Drainage-ready External Ref Structures until they have at least one mapped Structure connection point.
- Added External Ref Structure body validation that blocks Watertight Solid builds when mapped connection points are outside the referenced Shape bounding box tolerance.
- Added a first-slice Watertight Solids `Simulation QA` status summary that reports built output family coverage, terrain readiness, invalid/zero-volume outputs, total volume, and first road + terrain + drainage readiness.
- Added `SimulationQaOutput` and `WatertightSimulationQaService` so simulation-readiness reporting is reusable outside the Watertight Solids panel.
- Added first-slice Simulation QA bounding-box contact diagnostics between road-body solids and drainage/structure solids.
- Added a persisted `V1SimulationQaOutput` report object that stores Watertight Solids Simulation QA family coverage, readiness status, contact diagnostics, and source refs after build actions.
- Added read-only Watertight Solids `Simulation QA` family and diagnostic tables for reviewing simulation-readiness coverage inside the panel.
- Added first-slice Simulation QA terrain-domain bounding-box diagnostics for built solids when a terrain Shape extent is available.
- Added first-slice Simulation QA pipe/structure port diagnostics that require Drainage pipeline Structure refs to have built `structure_body` outputs and connection point provenance.
- Added first-slice `SimulationPackageOutput` and a Watertight Solids `Build Package` action that persists a `V1SimulationPackageOutput` manifest under Exchange Packages.
- Added Watertight Solids Simulation Package JSON export for the persisted simulation hand-off manifest.
- Added terrain context refs and optional terrain bounding-box metadata to Simulation Package manifests and JSON export.
- Added generic BREP geometry file export refs to Simulation Package JSON export for packaged watertight solid outputs, with the export folder path reported in the Watertight Solids panel.
- Changed Simulation Package terrain context resolution to prefer actual terrain Shape/Mesh objects over metadata-only surface model records when geometry is available.
- Added a Structure Connection Node plan for upgrading Structures into Drainage-ready nodes with explicit Native/External geometry source modes, connection point mapping, invert context, validation, UI, and 3D review before Drainage Pipeline work.
- Added the first Structures source-contract slice for explicit `geometry_source_mode`, `native_type`, and persisted `StructureConnectionPoint` rows.
- Added a first-slice Structures editor `Connection Points` table with manual point editing and default derivation for drainage-ready Structure rows.
- Added a first-slice Structures `Pick From 3D` action that maps the current FreeCAD 3D selection into connection point STA, offset, elevation, and invert fields.
- Added a Structures connection point 3D review preview with `Preview Points`, row double-click focus, and project-tree routing under Structures.
- Added Drainage Element `connection_point_ref` persistence, editor selection, and validation against Structure connection points.
- Added a detailed Drainage Flow Route graph implementation plan covering Element nodes, Flow Route edges, Outlet terminology, UI behavior, validation, review handoff, and obsolete property removal.
- Added Stationing-based Region editing where Region `Start STA` values are selected from generated station values and `End STA` is derived from the next Region start.
- Added Build Corridor Region Boundary review support for displaying the selected Region's built corridor objects, including design, subgrade, slope/daylight, drainage, and structure context where available.
- Added Surface Transition controls in Build Corridor for selecting a Region STA, adjusting transition spacing, reviewing derived sample counts, enabling/disabling transition ranges, and updating transition records.
- Added a separate Build Corridor Guided Review `Drainage Flow` row that summarizes Flow Route IDs and linked Structure refs, with double-click 3D highlight handoff.
- Changed Build Parametric Drainage Surface generation so left/right ditch surface point groups are triangulated as separate strips instead of being bridged into one cross-road mesh.
- Added Build Parametric surface preview diagnostics so missing or failed Design/Subgrade/Slope/Drainage surface creation records a visible review-table note instead of failing silently.
- Added wiki documentation for Region continuity, Region Boundary review, Surface Transition spacing/update workflow, and troubleshooting guidance.
- Added v1 topology-first Watertight Solid planning and implementation sequencing for final toolbar placement, Build Corridor prerequisite gating, closed semantic profiles, edge networks, shell validation, target families, UI, tests, and output flow.
- Added a v1 representation strategy baseline table covering semantic-first, geometry-first, topology-first, and contract-first subsystem decisions.
- Added the initial `Watertight Solids` final-stage command placeholder after `AI Assist`, with Build Corridor prerequisite checks and a disabled WS0 panel shell.
- Added `SolidTargetModel` and target discovery for Watertight Solids so whole-corridor and Region body targets appear in the final-stage panel with availability and diagnostic status.
- Added Applied Section solid profile contracts and a closed-profile builder for Watertight Solids, including Region boundary interpolation and fallback-depth diagnostics without mutating Applied Sections.
- Added Watertight Solid edge-network contracts and topology validation for deterministic face rows, canonical edge usage, closed shell readiness, and profile-order blocking before geometry mapping.
- Added Watertight Solid Part mapping for validated topology networks, producing positive-volume FreeCAD Part solids while blocking invalid topology before shape creation.
- Added Watertight Solid output contracts, output mapping, segment metadata, diagnostic preservation, and a v1 output object bridge that can store generated Part solid shapes and round-trip summary rows.
- Added Region-body Watertight Solid generation support that filters Applied Section profiles to the selected Region, inserts capped boundary profiles, skips other-Region station profiles with diagnostics, and produces independent watertight Region outputs.
- Added first-slice Watertight Solid component target expansion for pavement-layer/subbase targets, component-scoped profile building from Applied Section width/thickness semantics, independent component solid validation/output, and StructureModel body target discovery for review.
- Added Watertight Solid quantity and exchange handoff, including accepted solid volume fragments, total volume aggregation, separate exchange payload rows/segments, source context rows, and metadata that keeps watertight solids distinct from structure solids.
- Added first-slice Watertight Solids panel interaction for selecting a discovered target row, enabling `Validate` only for available targets, and tracking per-target `Enabled` state.
- Added Watertight Solids panel validation execution that runs closed-profile and edge-network builders for the selected target and displays validation status plus profile, face, and edge counts without creating Part geometry.
- Added Watertight Solids `Build Selected` execution for validated targets, creating/updating `V1WatertightSolidOutput` objects with generated Part solid shapes, volume, output object, and build status displayed in the panel.
- Added Watertight Solids `Build Enabled` execution for bulk-building enabled available targets independently, with per-target output objects and a bulk summary of built, failed, target, and volume totals.
- Added Watertight Solids display controls for showing, hiding, and focusing built output solids, including row double-click focus and headless-safe status reporting when GUI visibility APIs are unavailable.
- Added a dedicated `Watertight Solids` project-tree group under `09_Outputs & Exchange` and routed `v1_watertight_solid_output` objects there.
- Added Watertight Solid topology quality warnings for short topology edges and tiny face areas without blocking otherwise closed shell validation.
- Added Watertight Solid Part-face triangulation fallback for validated topology faces that FreeCAD cannot create as a single polygon face.
- Added a Watertight Solid target expansion plan that separates the road body envelope from physical component, drainage, and structure solid targets.
- Added terrain-inclusive whole-road simulation as a master-plan goal for Watertight Solid output, including independent target validation before optional final composition.
- Added separated Watertight Solid component target families for subbase and shoulder bodies, with blocked diagnostics for invalid component dimensions and clearer panel labels for target families.
- Added first TS3 lined-ditch Watertight Solid target discovery from `ditch_surface` rows, including blocked diagnostics when lining material or thickness policy is missing.
- Added first-slice lined-ditch Watertight Solid profile/build support from `ditch_surface` endpoints and preserved lining policy.
- Added lined-ditch Watertight Solid provenance diagnostics and exchange source-context refs for drainage, component, material, lining thickness, profile counts, and source ditch points.
- Added side-specific Watertight Solids panel display/focus context for built lined-ditch solids.
- Added optional DrainageModel ownership handoff for lined-ditch Watertight Solid target discovery.
- Added lined-ditch lining join controls with optional miter joins, miter-limit fallback diagnostics, and output provenance for join policy.
- Added first-slice `V1DrainageModel` document object persistence and connected persisted DrainageModel ownership into Watertight Solid target discovery.
- Added DrainageModel validation diagnostics for duplicate ids, invalid station ranges, missing policy ids, and missing policy references.
- Added the first Drainage editor task panel with editable element, policy, and flow-route tables plus Validate/Apply persistence.
- Added first-slice Drainage element authoring fields for side, Region ref, Assembly component ref, and side-specific ditch defaults, with persistence into `V1DrainageModel` and Watertight Solid lined-ditch ownership.
- Added first-slice Region-to-Drainage handoff in the Region editor, including row-level Drainage selection and missing `drainage_ref` validation.
- Added first-slice Applied Section Drainage handoff so resolved Drainage Element refs are preserved on ditch component rows, generated `ditch_surface` points, Applied Section source refs, and `V1AppliedSectionSet` persistence.
- Added first-slice Drainage Review with a read-only task panel, normalized `DrainageOutput` mapping, Region missing-ref warnings, Applied Section ditch context tables, and toolbar placement after Drainage.
- Added first-slice Build Corridor drainage surface source handoff so drainage TIN vertices, provenance, quality rows, and surface build relations preserve Applied Section `drainage_ref` context.
- Added first-slice Drainage quantity handoff so ditch and flowline lengths can be reported by `drainage_ref` with missing source diagnostics and Drainage Review summary support.
- Added Drainage editor Preset data for roadside ditch, dual side ditches, and culvert crossing source sets.

### Changed
- Changed the Structures editor so common native geometry is edited in `Selected Structure Detail` instead of a separate visible `Geometry Specs` table, while preserving `StructureGeometrySpec` as the internal source contract.
- Changed the Structures editor detail form to filter Native geometry fields by `Native Type`, including pipe culvert diameter fields and box culvert opening fields.
- Changed Structure preview and default connection point derivation so circular/pipe culvert Native geometry uses pipe diameter instead of a rectangular envelope.
- Changed Structures presets and default connection point derivation so inlet, outlet, and headwall Native rows produce pipeline-ready roles such as `pipe_out`, `pipe_in`, and `discharge`.
- Renamed the user-facing product/workbench brand from `Corridor Road` / `CorridorRoad` to `Parametric Road` while keeping the internal Python package, FreeCAD Mod folder, command ids, and v1 source ids unchanged.
- Documented Drainage Flow Routes as graph edges between Element nodes and standardized final discharge wording on `Outlet`.
- Changed Build Corridor `Drainage Flow` focus to use only a linear route-span highlight instead of adding separate cross marker geometry.
- Documented the Region domain ownership redesign plan where Region owns station spans and Assembly only, while Structure and Drainage own their own Region assignments.
- Changed the v1 workflow toolbar order so Structures appears after Regions and before Drainage.
- Changed the Region editor to author Assembly-only Region rows by removing active Structure and Drainage columns and validation paths from the Region panel.
- Changed the Structure editor to own Structure-to-Region assignment with a row-level Region combo, persisted placement `region_ref`, and Region-boundary station validation.
- Renamed the Drainage `Collections` editor tab to `Flow Routes` to separate drainage targets from connection/routing intent.
- Changed the Drainage source contract from `collection_region_rows` to `flow_route_rows`, removed obsolete `Collection*` route fallback from active Drainage code, and replaced Flow Route receiver persistence with `FlowRouteOutletRefs`.
- Changed the Drainage Flow Routes editor column from `Receiver` to `Outlet`.
- Changed Drainage Flow Routes editing so `From Element`, `To Element`, and `Outlet` use row-level selectors populated from current Drainage Elements, with a route preview for the selected row.
- Added Drainage Flow Route graph validation for missing From/To refs, broken Element refs, invalid Outlet refs, self-loops, cycles, and missing outlet context warnings.
- Added Drainage Review Flow Routes handoff rows and a dedicated review tab showing From, To, Outlet, risk, chain preview, Region ownership, and Policy ownership context.
- Added Flow Route provenance handoff into drainage quantities, quantity outputs, lined-ditch watertight solid targets, watertight solid outputs, persisted solid output objects, and exchange source-context rows.
- Removed the optional `Offset Rule` field from the Drainage Elements editor and internal `DrainageElementRow` source contract.
- Changed Applied Sections validation to report Drainage element rows that have an Element ID but no Region assignment.
- Changed Drainage validation so element `Start STA` and `End STA` are checked against the selected Region boundary.
- Changed Drainage Region-boundary validation to honor the editor's station display precision and avoid false outside-range errors at matching Region endpoints.
- Changed Drainage Elements so `ditch` rows disable and clear the Structure cell in the editor.
- Changed Drainage Elements so non-`ditch` rows disable and clear the Assembly cell in the editor.
- Changed Drainage Elements so Structure cells hide the `structure:` prefix in table rows while preserving source refs internally.
- Changed Drainage Flow Routes so Flow Route ID, From Element, To Element, and Outlet hide source prefixes in table rows while preserving source refs internally.
- Changed Drainage Elements so the Policy column uses row-level combos populated from the Policy tab's Policy ID rows while preserving source refs internally.
- Changed Drainage Elements so the Region column sits next to Kind and uses a row-level Region combo populated from the active RegionModel.
- Changed Drainage Elements `Structure` column label to `Structure Ref` and added validation for missing referenced Structure IDs when a StructureModel is available.
- Added Drainage Flow Route cross-Region diagnostics when From/To Elements belong to different Regions.
- Changed Applied Sections to resolve active Structure and Drainage context from StructureModel/DrainageModel Region assignments instead of Region-owned Structure/Drainage refs.
- Changed Build Corridor Region Boundaries, Drainage Review, and Region-body Watertight Solid target discovery to display/use resolved domain-owned Structure/Drainage context instead of Region-owned Structure/Drainage refs.
- Changed Drainage quantity diagnostics and Cross Section Viewer source ownership rows to align with Drainage Element Region assignment.
- Removed Region source compatibility fields for Region-owned Structure/Drainage refs, including `RegionRow.structure_ref`, `RegionRow.structure_refs`, `RegionRow.drainage_refs`, and the corresponding `V1RegionModel` persistence rows.
- Added the first shared `StationContextResolver` slice so Applied Sections resolve Region, Structure, Drainage Element, and Flow Route context through one evaluation service.
- Changed Build Corridor Region Boundaries to use `StationContextResolver` for live Structure, Drainage Element, and Flow Route summaries when source models are available.
- Changed Cross Section Viewer source ownership rows to use `StationContextResolver` for selected-station Structure, Drainage Element, and Flow Route context when source models are available.
- Changed Watertight Solid target discovery to use `StationContextResolver` for Region target context summaries and Region-aware lined-ditch Drainage owner selection.
- Changed the Structures editor so Structure ID table rows hide the `structure:` prefix while preserving source refs internally.
- Changed the Structures editor so optional external `Geometry Ref` values move out of the main table and into the selected Structure detail area.
- Changed the Structures editor selected detail area to expose `Geometry Source` and `Native Type` controls while preserving Native specs and External Ref values separately.
- Changed the Structures editor so selecting a Structure table row by single click refreshes `Selected Structure Detail`, including rows clicked through combo-box cells.
- Changed Structures `Preview Points` connection markers to use larger solid high-contrast markers with thicker outlines for clearer 3D review.
- Changed Structures editor action buttons from `Save` / `Save + Preview` to `Apply` / `Apply + Preview`.
- Changed the Structures editor to reload applied `V1StructureModel` data back into the table/detail panel after Apply so reopening the panel shows the persisted rows.
- Changed the Structures `Drainage Structures` preset into a more practical ditch inlet/catch basin, pipe culvert/cross-drain, and outlet headwall/outfall example with matching connection points.
- Changed Drainage Elements `Structure Ref` cells to use Structure ID combos populated from the active Structures model while preserving source refs internally.
- Removed the Region Boundary structure placeholder preview boxes so selected Regions no longer create repeated purple `V1CorridorRegionStructure_*` marker objects.
- Changed Drainage preset Flow Route IDs to use `flowId-01` style values while preserving the internal `flow-route:` prefix.
- Increased the Structures `Drainage Structures` preset preview sizes for inlet, culvert, outlet, and their pipe connection diameters so the drainage chain is easier to inspect in 3D.
- Changed the Structures `Drainage Structures` preset culvert connection point offsets to `0.000` for both upstream and downstream ports.
- Changed circular pipe culvert Structure previews to use one start-to-end cylinder instead of segmented cylinders, avoiding broken-looking overlapping faces in 3D.
- Changed Structure and Drainage Flow Network connection point previews to simple sphere markers so Pipe In / Pipe Out points read cleanly in 3D.
- Changed Drainage Flow Network previews to display circular pipes on the pipe axis above invert elevation, matching Structure culvert previews and connection point markers.
- Changed the `Drainage Structures Flow` preset so the culvert Element leaves its connection point blank and lets Flow Route direction resolve upstream/downstream ports.
- Changed the Structures `Drainage Structures` and Drainage `Drainage Structures Flow` presets to use station-banded ditch sections with three matched inlet Structures before a shared culvert-to-outlet pipe chain.
- Changed the `Drainage Structures Flow` pipe routes to chain `inlet-01 -> inlet-02 -> inlet-03 -> culvert-01 -> outlet-01`, with Pipe In ports on intermediate inlets so the last inlet connects directly to the culvert Pipe In port.
- Changed the last inlet `pipe_out` in the Structures `Drainage Structures` preset to match the culvert pipe diameter, so `flowId-06` connects cleanly into the culvert Pipe In port in 3D.
- Changed Drainage pipeline resolution so native culvert Pipe In/Pipe Out roles snap to the current culvert placement start/end regardless of the saved connection point ID, preventing stale connection point station values from leaving `inlet-03 -> culvert-01` preview gaps.
- Changed Drainage `Show Flow Network` to refresh the current Structures preview first, so pipe previews and visible Structure bodies are drawn from the same source state.
- Changed Drainage network preview geometry to snap culvert pipe endpoints to the Structure preview placement used for the culvert body, eliminating visual gaps caused by stale connection point station/offset values.
- Changed Structure-backed Drainage pipeline geometry to use direct port-to-port 3D segments instead of sampling intermediate stations along the Alignment.
- Changed the Watertight Solids panel action area to wrap `Export Package` and later visibility/focus/close actions onto a second row for narrower panel widths.
- Changed Watertight Solid Build for Applied Section based targets, including lined ditch bodies, to reproject closed solid profiles onto the active 3D Centerline frame before topology and Part shape creation.
- Added Flow Routes table double-click preview in the Drainage editor so a Structure-backed route highlights its 3D pipe segment directly.
- Changed Drainage pipeline geometry to preserve Flow Route From/To direction, so 3D pipe endpoints stay attached to the resolved Structure Pipe Out and Pipe In connection points even when station order is reversed.
- Changed Drainage pipeline resolution so `ditch -> inlet` Flow Routes are reported as `capture_only` open-channel intake relationships instead of failed pipe candidates, keeping pipe warnings focused on Structure-backed routes.
- Changed native inlet Structure previews to add catch-basin review details: top grate bars, ditch intake mouth geometry, and short pipe port stubs for `pipe_in` / `pipe_out` connection points.
- Changed native outlet/headwall Structure previews to add drainage review details: headwall slab, outfall apron, side guide walls, pipe-in stub, and discharge mouth geometry.
- Changed native pipe culvert Structure previews to add endpoint headwall slabs and wingwalls when source `headwall_type` or `wingwall_type` values are set.
- Changed Drainage Flow Routes so the `Outlet` cell is enabled only when `To Element` is an outlet/outfall element; intermediate route rows now keep Outlet empty.
- Documented that `ditch -> inlet` Flow Routes are open-channel capture relationships, while 3D pipe geometry starts from Structure-owned Pipe In / Pipe Out connection points.
- Added a Drainage editor `Drainage Structures Flow` preset aligned with the Structures `Drainage Structures` preset, including ditch, inlet, culvert, outlet, Structure refs, connection points, and Flow Routes.
- Added Drainage editor `Show Flow Network`, which applies the current Drainage source rows and creates a 3D full-network pipe preview from resolved Structure connection points.
- Changed Drainage pipeline network preview geometry so missing invert elevations fall back to the active 3D centerline/profile height instead of zero elevation.
- Added linked tree-visible preview objects for individual Structure rows and Drainage pipeline segments, while keeping the aggregate preview objects available.
- Removed the default v1 Drainage tree child folders `Ditches`, `Culverts`, `Inlets`, and `Flow Paths`; Drainage source/preview objects now route directly under `05_Drainage`.
- Changed Drainage pipeline resolution so multi-connection Structures such as culverts use direction-aware endpoints: upstream/inlet when targeted by a route and downstream/outlet when starting the next route.
- Added tree-visible Structure-owned Pipe In / Pipe Out connection point markers for `Show Flow Network`, routed under `06_Structures` while remaining linked to the generated Drainage pipe segment endpoints.
- Added a Structures editor `Drainage Structures` preset with culvert, inlet, and outlet/headwall Structure refs for Drainage Structure Ref selection.
- Removed Region `Primary Kind` and `Layers` from the Region source workflow; Region intent now comes from station spans and base Assembly assignment, while Structures and Drainage own their Region assignments.
- Changed Profile `Preset Data` so selected example profiles are sampled onto the current station rows instead of replacing them with fixed preset stations.
- Changed Build Corridor Drainage row focus to draw selected station ditch/drainage line highlights instead of large sphere diagnostic markers.
- Updated the `Drainage Control` Region preset to use `STA 100.000` as the drainage-control start station and the current final Stationing value as the closing Region start.
- Renamed the Surface Transition action button in Build Corridor from `Create / Update Transition` to `Update`.
- Clarified Region and Surface Transition design documentation so transition intent remains source-level and generated geometry remains output.
- Changed lined-ditch Watertight Solid profile generation from vertical lining offset to section-normal polyline offset, preserving intermediate ditch surface points as solid profile nodes.
- Updated README, Addon overview, and Wiki draft pages so Drainage is described as an active source stage with Flow Routes and Structure-backed network preview instead of an under-development placeholder.

## [1.0.0] - 2026-05-02

### Added
- Introduced the v1 source-driven corridor workflow as the supported release direction.
- Added v1-native TIN, Alignment, Stations, Profile, Assembly, Region, Applied Sections, Build Corridor, review, Earthwork, Structure Output, Outputs & Exchange, and AI Assist stage framing.
- Added a Drainage toolbar/menu entry with a clear under-development message and dedicated drainage icon.
- Added v1 release, drainage implementation, and release-overview documentation for the `1.0.0` release.
- Added v1-native Earthwork report flow from Applied Sections and existing-ground terrain into cut/fill area, quantity, balance, mass-haul, and review outputs.

### Changed
- Rewrote `README.md` and `ADDON_OVERVIEW.md` around the v1 workflow, current release scope, and known in-progress areas.
- Updated the workbench command registration so v1 review and Earthwork handoff commands are available from the active workbench session.
- Clarified Drainage as a planned v1 stage after Region and before Applied Sections.
- Refined Earthwork Review handoff behavior to avoid deleted Qt object access after closing the task panel.

### Known Limitations
- Full Drainage Editor functionality is not complete in `1.0.0`.
- Advanced hydraulic analysis, automatic pipe sizing, complete drawing-sheet production, and full exchange output coverage remain future work.
- Some workflows still retain legacy support paths during the v1 transition, but v1 source/result/output layering is the intended direction.

## [0.2.8] - 2026-04-20

### Changed
- Retired the legacy proxy module `obj_corridor_loft.py` and its internal `CorridorLoft` proxy type, establishing `obj_corridor.py` and `Corridor` as the canonical standard.
- Established backwards compatibility module mappings in `virtual_paths.py` so legacy `.FCStd` files containing `CorridorLoft` and its historical module paths restore transparently to the new `Corridor` proxy.
- Retired the legacy command alias `CorridorRoad_GenerateCorridorLoft` and removed the legacy command-wrapper module.
- Retired the legacy task-panel alias path/class (`task_corridor_loft.py`, `CorridorLoftTaskPanel`) and updated the Loft-retirement gate docs/tests accordingly.
- Retired the hidden project-link property name `CorridorLoft` and switched `CorridorRoadProject` to the canonical hidden `Corridor` link.
- Retired the child ownership property name `ParentCorridorLoft` and switched generated corridor children to `ParentCorridor`.

## [0.2.7] - 2026-04-15

### Added
- Spline-based `3D Centerline` visible wire mode with `SmoothSpline` as the default display path and `Polyline` retained for debug/comparison review.
- Semantic boundary-marker child objects and task-panel diagnostics for region/structure-aware 3D centerline display review.
- Regression coverage for 3D centerline display segmentation, task-panel default-source selection, and alignment transition geometry/downstream behavior.
- Design notes for segmented 3D centerline display and horizontal transition geometry stabilization.

### Changed
- Refined `3D Centerline` task-panel defaults so existing `Stationing`, `VerticalAlignment`, `ProfileBundle`, `RegionPlan`, and `StructureSet` objects are auto-selected when available.
- Removed legacy `Sampled*` / `Sampling*` compatibility-shadow properties from `Centerline3DDisplay` and standardized on `Display*` result properties.
- Updated `README.md` and wiki documentation to reflect project-level local/world coordinate transforms, spline-based 3D centerline display, and the current display-versus-engineering-source-of-truth policy.
- Clarified the recent visible zig-zag / wiggly 3D centerline issue as a display-side geometry/rendering problem rather than a station-based design-model error.

## [0.2.4] - 2026-04-07

### Added
- `Typical Section` now supports explicit ditch `Shape=v`, `Shape=u`, and `Shape=trapezoid` modes, plus focused ditch-shape sample CSVs and regression coverage.
- `Typical Section` gained manual `Refresh Preview` driven 3D live preview with selected-row highlight overlay and separate `PavementDisplay` / `SelectedComponentPreview` support.

### Changed
- `Typical Section` task-panel UX was refined: helper buttons were simplified, row action layout was cleaned up, hover-driven row activation was removed, and `Shape` is now active only on `ditch` rows.
- `Sections`, `Cross Section Viewer`, and report contracts now preserve station-local ditch shape information so downstream review keeps the intended ditch mode visible.
- README/wiki/developer documentation were synchronized with the current `Typical Section` CSV schema, preview workflow, and ditch-shape behavior.

## [0.2.3] - 2026-04-05

### Added
- `Cross Section Viewer` station-review workflow with station-local component segments, scope-aware rendering for `typical`, `side_slope`, and `daylight`, plus PNG/SVG/Sheet SVG export support.
- `Sections` bench convenience workflow with `Repeat first row to daylight` controls on both left/right bench tables.

### Changed
- `Cross Section Viewer` annotation and summary behavior was expanded so component guides, labels, dimensions, daylight markers, and grouped review summary blocks better reflect `SectionSet` runtime contracts.
- `Cross Section Viewer` task-panel layout was reorganized for faster station navigation and section refresh during review.
- `Edit Structures` task-panel UX was refined, including preset placement, profile-table action layout, and preset-driven station-profile point loading for the sample presets.
- `Sections` and `Cross Section Viewer` now preserve resolved daylight-bound side-slope/bench component extents per station instead of reusing fixed-width viewer assumptions.
- Wiki and developer documentation were synchronized with the current `Cross Section Viewer`, `Sections`, and `Edit Structures` behavior.

## [0.2.2] - 2026-04-01

### Added
- Surface-first corridor workflow with practical grading/cut-fill expansion, including structure-aware notch/skip diagnostics and richer section/corridor report contracts.
- Manual FG productivity tools in `Edit Profiles`, including FG CSV import, FG wizard generation modes, and starter FG sample files.
- Starter-default and inline-guided `Edit PVI` workflow with BVC/EVC-aware summaries.
- Side-slope bench workflow with daylight-aware bench shaping, multi-bench support, table-based bench-row editing, and expanded headless smoke coverage.
- Practical-scope and short-term regression runners plus new sample-driven smoke tests for structures, typical sections, cut/fill, FG tools, and bench workflows.

### Changed
- `CorridorLoft` now uses surface output as the primary corridor representation instead of closed solid generation.
- Structure, section, grading, and cut/fill status wording was expanded for validation, trust/quality reporting, and mixed-workflow diagnostics.
- Wiki and developer documentation were updated for practical engineering scope, FG/PVI workflows, and bench-row editing.

## [0.2.0] - 2026-03-28

### Added
- Typical Section workflow with component presets, pavement layer presets, CSV import/export, and section/corridor integration.
- Expanded structure workflow with template, external-shape, and station-profile support.
- Alignment presets and project-driven coordinate workflow defaults for faster setup.

### Changed
- Improved task panel UX for Typical Section, Edit Structures, Alignment, and Profiles/PVI workflows.
- Clarified terminology by using `berm` for road-edge platforms and reserving `bench` for future earthwork mid-slope use.
- Adopted branch-based addon listing with release/version management on `main` using `package.xml`, `CHANGELOG.md`, tags, and GitHub Releases.

## [0.1.0] - 2026-03-08

### Added
- Initial public release of the CorridorRoad FreeCAD workbench.
- Fixed Civil3D-style project tree schema under `CorridorRoadProject`.
- Horizontal alignment workflow:
  - Sample alignment creation.
  - Practical alignment editing (PI/radius/transition).
  - Design standards selector (`KDS` / `AASHTO`).
  - Sketch import and CSV import/export for alignment PI data.
- Stationing generation from alignment.
- Profile/PVI workflow:
  - Profile data editing and terrain sampling.
  - PVI-based vertical alignment.
  - FG display and profile bundle integration.
- 3D modeling workflow:
  - Centerline3D display generation.
  - Assembly template and section generation.
  - Corridor loft generation.
  - Design grading surface generation.
  - Design terrain generation.
- Cut/Fill analysis workflow with progress and guardrails.
- Namespaced addon structure under `freecad/Corridor_Road`.
- Qt compatibility layer (`qt_compat.py`) for Qt5/Qt6 runtime handling.
- Release automation assets:
  - `.github/workflows/release-guard.yml`
  - `.github/pull_request_template/release.md`


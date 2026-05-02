# CorridorRoad V1 Build Corridor Performance Plan

Date: 2026-05-02
Status: In progress
Scope: Build Corridor execution speed

Depends on:

- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_SURFACE_MODEL.md`
- `docsV1/V1_APPLIED_SECTIONS_PERFORMANCE_PLAN.md`
- `docsV1/V1_TIN_SAMPLING_CONTRACT.md`

## 1. Purpose

This plan defines the next performance pass for the v1 `Build Corridor` command.

The goal is to reduce execution time while keeping the v1 source -> evaluation -> result -> output -> presentation layering intact.

## 2. Scope

This plan includes:

- delayed corridor preview mesh generation
- reuse of built corridor TIN surfaces for preview output
- reduced document recompute during preview updates
- daylight existing-ground sampling optimization
- delayed daylight contact marker generation

This plan excludes:

- Supplemental Sampling behavior changes
- lowering default corridor geometry quality
- changing Applied Sections source/result ownership
- moving final slope-face ownership out of Build Corridor
- v0 corridor surface behavior

## 3. Core Rule

Build Corridor should build durable corridor results first.

Heavy preview meshes, diagnostic marker solids, and repeated FreeCAD recomputes should run only when required for review.

Generated preview objects remain presentation artifacts.

## 4. Current Bottlenecks

### 4.1 Eager Preview Mesh Generation

`apply_v1_corridor_model()` currently creates design, subgrade, daylight, and drainage preview objects during Apply.

Each preview converts a `TINSurface` into a FreeCAD `Mesh::Feature`.

This can dominate runtime when station count, supplemental samples, or side-slope breaklines are high.

### 4.2 Surface Geometry Rebuilds

Preview creation calls `CorridorSurfaceGeometryService` again for each review surface.

This can repeat work already done while creating the corridor surface result.

### 4.3 Recompute Cost

`TINMeshPreviewMapper.create_or_update_preview_object()` calls `document.recompute()`.

Build Corridor creates several preview objects, so recompute can happen multiple times before the final recompute.

### 4.4 Daylight EG Sampling Cost

Slope-face tie-in checks call `TinSamplingService.sample_xy()` repeatedly.

The TIN spatial index reduces per-query triangle scans, but query count can still be high.

### 4.5 Daylight Marker Geometry Cost

Daylight contact markers are represented as sphere compounds.

Large station sets can create many marker spheres even when the user does not need marker review immediately.

## 5. Change 1 - Delayed Corridor Preview Mesh Generation

### 5.1 Intent

Do not generate all corridor preview meshes during normal Build Corridor Apply.

Persist the corridor model and surface model first.

Generate each preview mesh only when:

- the user selects a review row
- the user clicks Show for that layer
- guided review focuses that layer
- Show All is requested

### 5.2 Proposed Behavior

Default Apply behavior:

- build and persist `CorridorModel`
- build and persist `SurfaceModel`
- set preview status rows as `not_built` or `available`
- keep old preview objects hidden or mark them stale when inputs changed

On-demand review behavior:

- build the requested preview mesh
- update the target preview object
- set preview status as `built`
- focus or show the object if requested

### 5.3 Code Targets

- `freecad/Corridor_Road/v1/commands/cmd_build_corridor.py`
- `freecad/Corridor_Road/v1/services/mapping/tin_mesh_preview_mapper.py`

### 5.4 Acceptance Criteria

- Build Corridor Apply does not eagerly build every mesh preview.
- Review rows still show which outputs are available.
- Selecting a review layer can build and show that layer.
- Show All can build missing previews before making them visible.

## 6. Change 2 - Reuse Built Corridor TIN Surfaces

### 6.1 Intent

Avoid rebuilding the same design, subgrade, daylight, and drainage `TINSurface` objects for preview output.

### 6.2 Proposed Behavior

Build Corridor should create one in-memory surface build bundle during Apply.

Preview creation should consume the bundle when available.

If the bundle is not available, preview creation can fall back to rebuilding from persisted source/result objects.

### 6.3 Code Targets

- `build_document_corridor_surface_model()`
- `apply_v1_corridor_model()`
- `create_corridor_design_surface_preview()`
- `create_corridor_subgrade_surface_preview()`
- `create_corridor_daylight_surface_preview()`
- `create_corridor_drainage_surface_preview()`

### 6.4 Acceptance Criteria

- A surface used for `SurfaceModel` output can also be used for preview creation.
- Preview creation does not recompute the same TIN when the in-memory surface is available.
- Fallback rebuild still works after reopening a document.

## 7. Change 3 - Batch FreeCAD Recompute

### 7.1 Intent

Avoid recomputing the document after every preview object update.

### 7.2 Proposed Behavior

Add a mapper option such as:

- `recompute: bool = True`

Build Corridor should call preview mappers with `recompute=False`.

The command should call `doc.recompute()` once after all requested output objects are written.

### 7.3 Code Targets

- `freecad/Corridor_Road/v1/services/mapping/tin_mesh_preview_mapper.py`
- `freecad/Corridor_Road/v1/commands/cmd_build_corridor.py`

### 7.4 Acceptance Criteria

- Existing non-Build-Corridor callers keep current behavior by default.
- Build Corridor preview generation avoids per-preview recompute.
- Final document state is still recomputed once after Apply or preview build.

## 8. Change 4 - Daylight EG Sampling Optimization

### 8.1 Intent

Reduce the number of EG TIN queries made by slope-face tie-in resolution.

This does not skip terrain evaluation.

### 8.2 Proposed Behavior

Use the existing indexed `TinSamplingService`, then reduce query count by:

- caching slope orientation samples by rounded XY
- caching fallback outer-edge samples by rounded XY
- using fewer initial search steps for short daylight widths
- only running bisection when a sign change is detected

### 8.3 Code Targets

- `freecad/Corridor_Road/v1/services/builders/corridor_surface_geometry_service.py`

### 8.4 Acceptance Criteria

- Daylight tie-in results remain compatible with existing contract tests.
- Repeated station-side sampling can reuse cached EG samples.
- `eg_intersection_count`, `eg_outer_edge_sample_count`, and fallback diagnostics remain meaningful.

## 9. Change 5 - Delayed Daylight Contact Marker Generation

### 9.1 Intent

Avoid creating marker sphere compounds unless the user has requested marker display.

### 9.2 Proposed Behavior

If `show_daylight_contact_markers` is false:

- remove stale marker objects if needed
- keep issue rows and diagnostic summary on the daylight preview
- do not build marker sphere compounds

If the user enables marker display later:

- build marker objects from daylight surface diagnostic rows
- show them according to the marker checkbox

### 9.3 Code Targets

- `_create_slope_face_diagnostic_markers()`
- `set_corridor_build_daylight_contact_marker_visibility()`
- guided review focus helpers in `cmd_build_corridor.py`

### 9.4 Acceptance Criteria

- Marker checkbox off means no marker sphere compound creation during Apply.
- Marker checkbox on preserves current marker visibility behavior.
- Slope-face issue table still works without marker objects until focus is requested.

## 10. Implementation Order

### Step BC1 - Recompute Batching

Add `recompute=False` support to `TINMeshPreviewMapper` and use it from Build Corridor.

Status: completed on 2026-05-02.

Acceptance:

- focused Build Corridor tests still pass
- preview objects update correctly after one final recompute

### Step BC2 - Delayed Marker Creation

Skip marker geometry creation when marker display is off.

Status: completed on 2026-05-02.

Acceptance:

- marker checkbox off does not create marker objects
- marker checkbox on creates markers as before

### Step BC3 - Delayed Preview Mesh Generation

Change Apply to persist results first and defer preview mesh creation to review actions.

Acceptance:

- Apply completes without eager mesh generation
- review row selection can build the requested preview

### Step BC4 - Surface Build Bundle Reuse

Pass built `TINSurface` results into preview creation when available.

Acceptance:

- preview creation can reuse in-memory surfaces
- fallback rebuild remains available

### Step BC5 - Daylight Sampling Cache

Add a local EG sample cache inside daylight surface building.

Acceptance:

- existing daylight surface tests remain compatible
- repeated sample points reuse cached TIN sample results

### Step BC6 - Focused Validation

Run focused tests for:

- Build Corridor command
- TIN mesh preview mapper
- corridor design/subgrade/daylight/drainage surface builders
- slope-face diagnostic marker behavior

## 11. Diagnostics and UX

Build Corridor review rows should distinguish:

- result data available
- preview mesh not built
- preview mesh built
- marker geometry not built
- marker geometry built

The user should be able to build the corridor result quickly, then spend time only on the review layers they choose.

## 12. Non-Goals

This plan does not disable Supplemental Sampling.

It does not make Build Corridor ignore Applied Section rows.

It does not replace the existing TIN mesh preview mapper with a new rendering engine.

It does not change corridor engineering results for the sake of display speed.

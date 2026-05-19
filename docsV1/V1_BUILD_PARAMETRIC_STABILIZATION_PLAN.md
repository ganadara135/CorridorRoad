# Parametric Road V1 Build Parametric Stabilization Plan

Date: 2026-05-19
Status: Draft
Scope: Build Parametric / Build Corridor reliability

Depends on:

- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_SURFACE_MODEL.md`
- `docsV1/V1_REGION_SURFACE_TRANSITION_PLAN.md`
- `docsV1/V1_CENTERLINE_OWNERSHIP_CONSOLIDATION_PLAN.md`
- `docsV1/V1_PROJECT_TREE_REDESIGN_PLAN.md`
- `docsV1/V1_BUILD_CORRIDOR_PERFORMANCE_PLAN.md`

## 1. Purpose

This plan defines the stabilization pass for the v1 `Build Corridor` command, currently used by the user as the `Build Parametric` stage.

The goal is to make the Build Parametric result dependable enough for:

- Region Boundary review
- Surface Transition review
- Drainage surface and flow review
- downstream Watertight Solids target discovery
- tree-based hide/show and property inspection

This is a stability plan, not a feature expansion plan.

## 2. Current Code Baseline

The current implementation is centered in:

- `freecad/Corridor_Road/v1/commands/cmd_build_corridor.py`
- `freecad/Corridor_Road/objects/obj_project.py`
- `freecad/Corridor_Road/v1/objects/obj_corridor.py`
- `freecad/Corridor_Road/v1/objects/obj_surface.py`

`apply_v1_corridor_model()` currently performs this sequence:

1. Ensure the v1 project tree exists.
2. Build or accept a `CorridorModel`.
3. Build a `SurfaceModel` when surface build is enabled.
4. Persist the `V1CorridorModel` object.
5. Persist the `V1SurfaceModel` object.
6. Create/update generated preview and review objects:
   - centerline preview, when shared 3D Centerline data is available
   - design surface preview
   - Region surface preview objects
   - subgrade surface preview
   - daylight / slope face preview
   - drainage surface preview
   - Surface Transition span markers
7. Record missing or failed surface preview diagnostics.
8. Route generated Build Parametric objects under:

`04_Corridor Model / Build Parametric Outputs`

## 3. Core Rule

Build Parametric should produce traceable result and preview outputs.

It must not silently skip geometry, hide failures in the task panel, or make generated preview geometry the source of design intent.

Source ownership remains:

- Alignment/Profile/Stationing own baseline source intent.
- `Centerline3DResult` owns the shared station/offset/elevation baseline result.
- Assembly owns reusable section components.
- Region owns station-span and base Assembly assignment.
- Structures and Drainage own their own Region assignments and domain references.
- Applied Sections own station-wise evaluated section result rows.
- Build Parametric owns corridor-level result and preview output generation.

## 4. Stabilization Targets

### 4.1 Surface Creation Reliability

Build Parametric currently creates several surface families from Applied Sections and SurfaceModel rows.

Stabilization work:

- verify every expected surface role has a clear outcome: `ready`, `missing`, `warning`, or `error`
- keep failed preview creation from aborting the entire build when a diagnostic object can represent the failure
- preserve role-specific object properties:
  - `SurfaceRole`
  - `SurfaceKind`
  - vertex/triangle counts
  - source refs
  - diagnostic summaries
- ensure left/right drainage ditch strips are not bridged across the road
- confirm supplemental sampling does not create duplicate or invalid surface faces

Acceptance:

- Design, Subgrade, Daylight/Slope Face, and Drainage rows report an explicit status.
- Missing drainage input produces a clear diagnostic, not a traceback.
- A partial surface build still leaves useful review output and diagnostics.

### 4.2 Region Boundary Review Stability

Region Boundary rows now use Applied Sections plus source Region ranges.

Stabilization work:

- keep Region start/end display aligned with the active `V1RegionModel`
- detect gaps, overlaps, and missing source rows before highlighting
- keep selected Region display based on the actual built Region objects, not temporary sketch-only geometry
- include Design, Subgrade, Daylight/Slope, Drainage, and Structure context where those outputs exist
- preserve Region object routing under Build Parametric Outputs

Acceptance:

- Double-clicking a Region row displays the selected Region's built objects.
- Region diagnostics explain why any expected object is missing.
- Region row Start STA / End STA matches the source Region model and Applied Section resolution.

### 4.3 Surface Transition Stability

Surface Transition intent is source-level transition data consumed by Build Parametric.

Stabilization work:

- keep the UI control model as `Region STA + Spacing + Update`
- maintain per-boundary transition spacing independently
- show `Sample Count` as derived from the stored spacing and transition range
- record generation diagnostics when transition sections are skipped
- keep transition span marker objects tree-visible under Build Parametric Outputs

Acceptance:

- Updating spacing changes the stored transition range and derived sample count.
- Rebuilding Build Parametric regenerates transition-aware surfaces.
- Transition marker visibility can be managed from the tree.

### 4.4 Drainage Handoff Stability

Build Parametric consumes Drainage context from Applied Sections and source Drainage models.

Stabilization work:

- keep ditch surface generation separate by side
- preserve Drainage refs in surface source/provenance rows
- show Drainage Surface only when ditch surface rows exist
- keep `Drainage Flow` review focus from creating unrelated cross-marker geometry
- ensure Flow Route and Structure context summaries are read from source/result contracts, not Region-owned legacy fields

Acceptance:

- Drainage Surface row is `ready` when ditch surface points are available.
- Missing ditch points produce a clear diagnostic.
- Drainage Flow focus highlights the intended route span or resolved flow geometry without adding confusing marker shapes.

### 4.5 Tree Visibility And Object Inspection

The current tree target is:

`04_Corridor Model / Build Parametric Outputs`

Stabilization work:

- keep all Build Parametric generated preview and diagnostic objects routed to this folder
- ensure existing generated objects are updated in place instead of creating duplicate stale objects
- keep properties useful for inspection from FreeCAD's property view
- keep generated outputs distinct from source models

Acceptance:

- Users can hide/show Build Parametric generated objects from the tree.
- Users can inspect surface role, counts, diagnostics, and source refs from object properties.
- No generated Build Parametric object is routed as source intent.

### 4.6 Downstream Watertight Solids Readiness

Watertight Solids depends on accepted Build Parametric prerequisites.

Stabilization work:

- keep `V1CorridorModel` and `V1SurfaceModel` persistence reliable
- make blocking Build Parametric diagnostics discoverable before Watertight Solids opens
- preserve source/result refs needed by road body, Region body, drainage, and structure solid targets
- keep 3D Centerline provenance explicit where Build Parametric output depends on station/offset/elevation frames

Acceptance:

- Watertight Solids opens only after required Build Parametric prerequisites exist.
- Solid target discovery can identify missing Build Parametric context with a clear diagnostic.
- Build Parametric output object refs remain stable across rebuilds.

## 5. Implementation Order

### Step BP-S1 - Diagnostic Outcome Matrix

Status: Pending

Work:

- define the expected status values for each Build Parametric row
- map missing source/result conditions to diagnostic records
- add focused tests for missing design, subgrade, daylight, and drainage preview conditions

Acceptance:

- every guided review row has deterministic status text
- surface preview diagnostic objects are created for missing or failed preview families

### Step BP-S2 - Surface Preview Contract Hardening

Status: Pending

Work:

- audit `create_corridor_design_surface_preview()`
- audit `create_corridor_subgrade_surface_preview()`
- audit `create_corridor_daylight_surface_preview()`
- audit `create_corridor_drainage_surface_preview()`
- normalize output object properties and diagnostic fields

Acceptance:

- role-specific properties are consistent across preview objects
- failed Part/Mesh conversion records a diagnostic object
- existing successful preview tests still pass

### Step BP-S3 - Region Boundary Object Completeness

Status: Pending

Work:

- verify selected Region display includes all available generated object families
- add diagnostics for missing Region-family objects
- confirm no temporary placeholder structure boxes are recreated
- add tests for Region output tree routing and selected Region focus behavior

Acceptance:

- Region row double-click highlights actual built Region objects
- selected Region diagnostics identify missing surface/drainage/structure context

### Step BP-S4 - Surface Transition Rebuild Verification

Status: Pending

Work:

- test per-boundary spacing persistence
- test derived sample count after spacing update
- test rebuild behavior after transition update
- test transition span marker routing and property inspection

Acceptance:

- transition spacing is not global unless explicitly designed that way
- Build Parametric rebuild uses the stored transition records

### Step BP-S5 - Drainage Surface And Flow Review Hardening

Status: Pending

Work:

- add focused tests for left/right ditch strip separation
- add missing ditch point diagnostics
- verify Flow Route context summaries are source-owned
- keep Drainage Flow focus as line/span highlight without stray cross markers

Acceptance:

- drainage surface preview is visually and contractually side-separated
- Flow Route review does not generate misleading extra marker geometry

### Step BP-S6 - Tree Routing Regression Coverage

Status: In progress

Completed baseline:

- Build Parametric generated preview and diagnostic objects route under `04_Corridor Model / Build Parametric Outputs`.
- Manual UI confirmation was completed for tree hide/show and property inspection.

Remaining work:

- add focused coverage for stale-object update rather than duplicate creation
- add focused coverage for diagnostic objects and transition markers

Acceptance:

- rerunning Build Parametric updates existing objects in place
- tree contents remain stable after repeated builds

### Step BP-S7 - Downstream Prerequisite Check

Status: Pending

Work:

- identify which Build Parametric diagnostics should block Watertight Solids target families
- expose a compact prerequisite summary that Watertight Solids can consume
- preserve non-blocking warnings for review without blocking all target discovery

Acceptance:

- Watertight Solids can distinguish missing prerequisites from unsupported target families
- target-specific diagnostics identify the owning Build Parametric output row or object

## 6. Manual QA Checklist

Use a project with Alignment, Stations, Profile, 3D Centerline, Assembly, Regions, Applied Sections, Structures, and Drainage where available.

1. Run Applied Sections.
2. Open Build Corridor / Build Parametric.
3. Build corridor outputs.
4. Confirm Design Surface row is `ready` or shows a clear diagnostic.
5. Confirm Subgrade Surface row is `ready` or shows a clear diagnostic.
6. Confirm Slope Face Surface row is `ready`, `warning`, or `error` with visible notes.
7. Confirm Drainage Surface row is `ready` when ditch rows exist, otherwise diagnostic-only.
8. Double-click Region Boundary rows and confirm actual built Region objects display.
9. Update one Surface Transition spacing value and click `Update`.
10. Rebuild Build Parametric and confirm sample count and surface output update.
11. Confirm generated objects appear under `04_Corridor Model / Build Parametric Outputs`.
12. Hide/show generated objects from the tree.
13. Inspect generated object properties in FreeCAD's property view.
14. Open Watertight Solids and confirm target discovery reports Build Parametric prerequisite status clearly.

## 7. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Surface preview code keeps mixing result generation and presentation | hard-to-debug failures | keep `CorridorModel` and `SurfaceModel` persistence separate from preview object generation |
| Region highlight creates temporary geometry instead of showing built outputs | user confusion | only route and focus actual generated output objects |
| Drainage surface generation bridges left/right ditch geometry | visually wrong surfaces and bad downstream solids | keep side-separated drainage strips and test both sides |
| Transition spacing is treated as global | incorrect local transition density | persist and test spacing per selected transition range |
| Diagnostics are only visible in task panel text | failures disappear after closing panel | persist diagnostic objects or properties on generated outputs |
| Tree routing duplicates stale objects | clutter and wrong hide/show behavior | update objects in place by stable object name |

## 8. Non-goals

This stabilization pass does not implement advanced hydraulic analysis.

This stabilization pass does not replace Drainage or Structures source models.

This stabilization pass does not convert corridor preview meshes into source geometry.

This stabilization pass does not build final watertight solids directly inside Build Parametric.

This stabilization pass does not optimize every performance issue. Performance work remains tracked in `V1_BUILD_CORRIDOR_PERFORMANCE_PLAN.md`.

## 9. Definition Of Done

Build Parametric stabilization is done when:

- repeated builds update stable output objects without duplicate clutter
- each surface/review row has deterministic status and diagnostics
- Region Boundary review shows actual built Region object families
- Surface Transition spacing is preserved and reflected after rebuild
- Drainage Surface and Drainage Flow review are visually trustworthy
- generated objects are tree-visible and property-inspectable
- Watertight Solids receives clear prerequisite signals from Build Parametric results
- focused contract tests cover the stabilized behavior

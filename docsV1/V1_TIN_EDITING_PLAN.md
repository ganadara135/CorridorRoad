# CorridorRoad V1 TIN Editing Plan

Date: 2026-04-27
Branch: `v1-dev`
Status: Draft implementation plan
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_TIN_ENGINE_PLAN.md`
- `docsV1/V1_TIN_DATA_SCHEMA.md`
- `docsV1/V1_TIN_CORE_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_TIN_REVIEW_NEXT_STEP_PLAN.md`

## 1. Purpose

This document defines the next practical TIN step before continuing deeper into Profile, Corridor, drainage, or earthwork workflows.

The goal is to let users correct and refine an imported or generated TIN surface without breaking the v1 source-of-truth model.

## 2. Core Decision

TIN editing must not directly mutate the display mesh as the durable source.

The user-facing workflow may feel like "editing the TIN result", but the internal contract should be:

1. preserve the imported source surface or source rows
2. store explicit TIN edit operations
3. rebuild a derived edited `TINSurface`
4. refresh the mesh preview and downstream sampling from the edited result

This keeps Profile EG sampling, section terrain sampling, earthwork, and export consumers deterministic.

## 3. Why This Is Needed Now

Profile and future corridor consumers depend on existing ground TIN quality.

Without TIN editing, users cannot correct common practical terrain issues:

- stray survey points creating spikes
- bad triangles across gaps or outside the intended survey area
- missing outer boundary constraints
- voids such as ponds, buildings, pits, or excluded areas
- local bad elevations that affect EG profile sampling
- rough edge triangles that distort section or earthwork results

## 4. Editing Model

Recommended source hierarchy:

- `TIN Source`: imported point rows, source CSV, or source mesh reference
- `TIN Base Result`: first generated triangulation result
- `TIN Edit Set`: ordered list of user edit operations
- `TIN Edited Result`: regenerated TIN surface after applying edit operations
- `TIN Mesh Preview`: display-only visualization of the selected TIN result

The edited result should become the default terrain candidate for Profile EG Reference and downstream section/corridor sampling.

## 5. Initial User Workflow

Recommended early workflow:

1. Open `TIN`.
2. Use the `Source` tab to select a point-cloud CSV or sample CSV.
3. Review summary, extents, and diagnostics.
4. Add edit operations such as boundary, void, delete triangles, or elevation fixes.
5. Click `Apply` to create or update the base TIN when needed, apply the current edit settings, and focus the edited result in the 3D View.
6. Click `Show Preview` to refresh and focus the edited mesh preview without opening review diagnostics.
7. Click `Review Result` to inspect the current edited TIN result without creating duplicate review geometry.
8. Profile `EG Reference` uses the edited TIN result when selected.

## 6. MVP Editing Tools

### 6.1 Boundary Clip

Purpose:

- remove triangles outside the intended terrain footprint

First implementation:

- rectangular XY boundary from numeric min/max fields
- optional "Use current TIN extents" starter values
- keep triangles whose centroids fall inside the boundary
- record removed triangle count

Later implementation:

- polyline boundary from selected sketch/wire
- boundary validity diagnostics
- boundary source object link

### 6.2 Void Clip

Purpose:

- remove triangles inside excluded areas

First implementation:

- rectangular XY void from numeric min/max fields
- keep triangles whose centroids are outside the void
- record removed triangle count

Later implementation:

- multiple void polygons
- selected sketch/wire voids
- named exclusion zones

### 6.3 Delete Selected Triangle or Face Range

Purpose:

- remove obvious bad triangles after review

First implementation:

- table-based triangle id deletion
- comma-separated triangle ids or ranges
- no direct mesh-face picking required yet

Later implementation:

- 3D face picking
- highlight candidate triangles before apply
- undoable edit operation rows

### 6.4 Elevation Override

Purpose:

- fix local bad point elevations without editing the original CSV file

First implementation:

- table rows with `vertex_id`, `new_z`, and `notes`
- update affected vertices and keep triangle topology
- record changed vertex count

Later implementation:

- nearest-vertex pick from XY
- bulk offset by selection/window
- local smoothing tools

## 7. Deferred Editing Tools

The following are useful but should not be first:

- constrained Delaunay retriangulation with breakline enforcement
- point insertion and deletion with automatic local retriangulation
- full polygon sketch editing
- smoothing by slope/curvature criteria
- merge two TIN surfaces
- LandXML surface edit roundtrip
- interactive 3D drag editing

These can come after the source/edit/result pipeline is stable.

## 8. Data Contract

Recommended `TINEditOperation` fields:

- `operation_id`
- `operation_kind`
- `enabled`
- `target_surface_id`
- `parameters`
- `source_ref`
- `created_at`
- `notes`
- `diagnostic_rows`

Recommended operation kinds:

- `boundary_clip_rect`
- `void_clip_rect`
- `delete_triangles`
- `override_vertex_elevation`

Recommended edited result metadata:

- `surface_kind = existing_ground_tin`
- `source_refs` includes the base TIN result and edit set id
- `provenance_rows` include edit operation summaries
- `quality_rows` include base and edited vertex/triangle counts

## 9. Suggested Code Placement

Recommended new or updated files:

- `freecad/Corridor_Road/v1/models/source/tin_edit_model.py`
- `freecad/Corridor_Road/v1/services/editing/tin_edit_service.py`
- `freecad/Corridor_Road/v1/commands/cmd_edit_tin.py`
- `freecad/Corridor_Road/v1/ui/editors/tin_editor.py`
- `tests/contracts/v1/test_tin_edit_service.py`
- `tests/contracts/v1/test_tin_editor_command.py`

Existing files likely to update:

- `freecad/Corridor_Road/init_gui.py`
- `freecad/Corridor_Road/objects/obj_project.py`
- `freecad/Corridor_Road/v1/commands/cmd_review_tin.py`
- `freecad/Corridor_Road/v1/services/mapping/tin_mesh_preview_mapper.py`
- `freecad/Corridor_Road/v1/commands/cmd_profile_editor.py`

## 10. Tree Routing

Recommended tree placement:

- base source rows under `03_Surfaces / Existing Ground TIN / Source`
- base TIN result under `03_Surfaces / Existing Ground TIN / TIN Result`
- edit set under `03_Surfaces / Existing Ground TIN / Source` or `TIN Result`
- edited result under `03_Surfaces / Existing Ground TIN / TIN Result`
- mesh preview under `03_Surfaces / Existing Ground TIN / Mesh Preview`
- diagnostics under `03_Surfaces / Existing Ground TIN / Diagnostics`

The edited result should be visually labeled so users can distinguish:

- base result
- edited result
- display mesh preview

## 11. UI Shape

Recommended `TIN` task panel tabs:

- `Source`: CSV/sample source selection, base TIN build, and selected/base/edited TIN summary
- `Boundary`: rectangle boundary MVP, later sketch boundary
- `Voids`: rectangle void MVP, later polygon voids
- `Triangles`: delete triangle ids/ranges
- `Vertices`: elevation override rows
- `Vertices`: elevation override rows and nearest-vertex pick mode
- `Diagnostics`: before/after counts and warnings

Recommended bottom actions:

- `Apply`
- `Show Preview`
- `Review Result`
- `Close`

Opening the panel should not modify the document.

`Apply` is the single write action. It should build or replace the source TIN only when the selected CSV source changes, apply the current edit settings, refresh the edited result, focus the 3D preview, and show a completion message.

`Show Preview` should rebuild the current preview state and focus the mesh preview.

`Review Result` should open diagnostics/review for the current edited result without creating a second mesh preview.

## 12. Implementation Phases

### Phase K: TIN Edit Service Contract

Status: Initial service slice complete

Tasks:

- [x] add `TINEditOperation` model
- [x] add service functions for rectangular boundary clipping, void clipping, triangle deletion, and vertex elevation overrides
- [x] keep all logic FreeCAD-GUI independent
- [x] add focused contract tests

Acceptance criteria:

- [x] base TIN can produce an edited TIN without mutating the original
- [x] removed triangle and changed vertex counts are reported
- [x] sampling works against the edited TIN

Implemented initial files:

- `freecad/Corridor_Road/v1/models/source/tin_edit_model.py`
- `freecad/Corridor_Road/v1/services/editing/tin_edit_service.py`
- `tests/contracts/v1/test_tin_edit_service.py`

### Phase L: Edited Result and Mesh Preview

Status: Initial mesh-preview slice complete

Tasks:

- [x] map edited `TINSurface` into a FreeCAD mesh preview
- [x] label edited result distinctly through preview label and metadata
- [x] route edited preview to the v1 surface tree through `CRRecordKind=tin_mesh_preview`
- [x] create dedicated edited-result metadata records from the unified `TIN` command
- [x] make completion and focus behavior consistent between source build and edited preview refresh

Acceptance criteria:

- [x] applying an edit can create or update an edited TIN preview
- [x] repeated preview generation updates the existing mesh instead of duplicating it
- [x] 3D View focuses the edited TIN from the unified `TIN` command
- [x] edited result and edit diagnostics records route to the v1 Existing Ground TIN result/diagnostics folders
- [x] existing TIN review tests still pass

Implemented initial files:

- `freecad/Corridor_Road/v1/services/mapping/tin_mesh_preview_mapper.py`
- `tests/contracts/v1/test_tin_mesh_preview_mapper.py`
- `freecad/Corridor_Road/v1/commands/cmd_review_tin.py`
- `tests/contracts/v1/test_tin_review_command.py`

### Phase M: Unified TIN Task Panel

Status: Unified CSV source, preview, review, and practical editing flow complete

Tasks:

- [x] add unified `TIN` command
- [x] add `Source` tab for point-cloud CSV and sample CSV base TIN creation
- [x] provide tabs for boundary, void, triangle deletion, vertex overrides, and diagnostics
- [x] make opening non-destructive
- [x] make `Apply` the only write action by merging source build and edit apply behavior
- [x] register only the unified `TIN` command in the `Survey & Surface` workflow group
- [x] keep legacy PointCloud TIN command available as compatibility code but remove it from the active toolbar/menu flow
- [x] add full-extent and two-corner 3D pick workflow for rectangular boundary clipping
- [x] add two-corner 3D pick workflow and clear action for rectangular void clipping
- [x] show temporary and final 3D rectangle previews while picking boundary and void regions
- [x] add reset actions for boundary and void editing state
- [x] separate `Show Preview` as 3D display refresh from `Review Result` as diagnostics/review
- [x] add multi-row vertex override editing
- [x] add nearest-vertex 3D pick workflow for vertex elevation overrides
- [x] support triangle deletion by id ranges such as `t10-t15`
- [x] add Pick Mode for selected 3D mesh face triangle deletion

Acceptance criteria:

- [x] selected TIN preview/result opens in the panel
- [x] user can create the base TIN from the same panel before editing
- [x] user can apply at least one rectangle boundary clip
- [x] user can set a rectangle boundary by picking two 3D View corner points
- [x] user can apply at least one void clip
- [x] user can set a rectangular void by picking two 3D View corner points
- [x] user can delete triangle ids from a string input
- [x] user can start Pick Mode and add selected 3D mesh faces into the triangle deletion field
- [x] user can override at least one vertex elevation
- [x] user can override multiple vertex elevations in one apply operation
- [x] user can pick a TIN point in the 3D View and populate the nearest vertex id
- [x] applying edits creates or updates an edited mesh preview

Implemented initial files:

- `freecad/Corridor_Road/v1/commands/cmd_edit_tin.py`
- `freecad/Corridor_Road/init_gui.py`
- `freecad/Corridor_Road/v1/commands/__init__.py`
- `tests/contracts/v1/test_tin_editor_command.py`

### Phase N: Downstream Selection Rule

Status: Initial edited-TIN preference complete

Tasks:

- [x] make Profile `EG Reference` prefer selected edited TIN when available
- [x] make Profile fallback TIN resolution prefer edited TIN when no explicit source is selected
- [x] ensure Plan/Profile Review and section sampling can use edited TIN through the shared document TIN resolver
- [x] keep base TIN available for comparison when explicitly selected
- [x] avoid treating Profile Show preview geometry as a terrain candidate

Acceptance criteria:

- [x] Profile EG sampling can use the edited TIN when selected or when it is the preferred document terrain candidate
- [x] base and edited TIN can be reviewed separately through explicit selection
- [x] no downstream consumer silently prefers Profile/Alignment display geometry as terrain

Implemented initial files:

- `freecad/Corridor_Road/v1/commands/cmd_review_tin.py`
- `freecad/Corridor_Road/v1/commands/cmd_profile_editor.py`
- `tests/contracts/v1/test_tin_review_command.py`
- `tests/contracts/v1/test_v1_profile_editor.py`

## 13. Stop Conditions

Pause and realign if:

- direct mesh edits become the only durable record
- TIN editing mutates imported CSV/source rows without provenance
- Profile or Section sampling reads a display mesh when an edited `TINSurface` is available
- edit operations cannot be replayed deterministically
- the first editor tries to solve full Delaunay/breakline enforcement before MVP edits work

## 14. Recommended Next Step

Implement Phase K first.

The first coding slice should be:

1. add a GUI-independent `TINEditOperation` model
2. add `TINEditService.apply_operations(surface, operations)`
3. support rectangular boundary clipping
4. support rectangular void clipping
5. support triangle-id deletion
6. support vertex elevation override
7. add contract tests

Only after that should additional advanced editing widgets be added to the unified `TIN` panel.

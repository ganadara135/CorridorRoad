# Parametric Road V1 Watertight Solid Plan

Status: Draft plan
Owner: Parametric Road v1 output and geometry pipeline
Baseline: `docsV1/V1_MASTER_PLAN.md`

Detailed implementation sequence: `docsV1/V1_WATERTIGHT_SOLID_IMPLEMENTATION_PLAN.md`

Target-family expansion sequence: `docsV1/V1_WATERTIGHT_SOLID_TARGET_EXPANSION_PLAN.md`

## 1. Purpose

This document defines how Parametric Road v1 should produce watertight solid outputs from accepted corridor results.

The final goal is to let users generate valid, reviewable watertight solids for selected areas such as:

- the whole road body
- a selected Region
- a drainage Subassembly or Structure-backed drainage body
- a structure such as a retaining wall or culvert
- a specific Assembly Subassembly such as pavement, curb, gutter, barrier, shoulder, or lined ditch

## 2. Core Rule

Watertight solids are generated outputs.

They are not source models and they are not edited directly.

Design changes must return to the owning source models:

- `AlignmentModel`
- `ProfileModel`
- `AssemblySubassemblyModel`
- `RegionModel`
- `DrainageModel`
- `StructureModel`
- explicit override rows where supported

## 3. Topology-First Rule

Watertight Solid generation is topology-first.

This follows the representation strategy table in `docsV1/V1_MASTER_PLAN.md`.

The solid pipeline must prove the body topology before accepting the final Part solid geometry.

Required topology chain:

```text
SolidTarget
  -> closed semantic profiles
  -> deterministic edge network
  -> face adjacency
  -> closed shell
  -> watertight validation
  -> Part solid geometry
```

Geometry is still required, but geometry is not the first authority.

The first authority is the semantic topology:

- which profile nodes exist
- which semantic edges connect them
- which faces use each edge
- whether every shell edge is shared exactly twice
- whether start and end caps close the target
- whether the shell is manifold before solid conversion

TIN surfaces and viewer meshes may help review or diagnostics, but they must not become the topology source for watertight solid generation.

## 4. Workflow Placement

Watertight Solid generation belongs after `Build Corridor`.

It should not be hidden inside the initial corridor surface build.

The workflow is:

```text
Project Setup
  -> TIN / Existing Ground
  -> Alignment
  -> Stations
  -> Profile
  -> Assembly
  -> Structures
  -> Region
  -> Drainage
  -> Applied Sections
  -> Build Corridor
       -> CorridorModel
       -> SurfaceModel
       -> Region Boundary review
       -> Surface Transition review
  -> AI Assist
  -> Watertight Solids
       -> Solid Target selection
       -> Closed Profile build
       -> Edge Network build
       -> Face / Shell build
       -> Watertight validation
       -> Solid Output
  -> Outputs / Exchange
```

`Build Corridor` produces the prerequisite evaluated corridor state.

`Watertight Solids` consumes that accepted state and creates final solid outputs.

## 5. Toolbar Placement

The UI should expose a separate top-level toolbar stage named:

`Watertight Solids`

Toolbar order:

```text
... -> Exchange -> AI Assist -> Watertight Solids
```

`Watertight Solids` is the final toolbar stage.

It should be disabled until Build Corridor has completed successfully.

Minimum activation prerequisites:

- a `V1AppliedSectionSet` exists
- a `V1CorridorModel` exists
- a `V1SurfaceModel` exists or the Build Corridor result explicitly records that surface output was intentionally skipped
- Build Corridor diagnostics do not contain blocking errors for the selected solid target family

When disabled, the command should show a clear tooltip or status message:

`Run Build Corridor before generating watertight solids.`

## 6. UI Plan

The `Watertight Solids` task panel should be separate from Build Corridor.

It should focus only on solid targets, validation, preview, and output readiness.

Recommended panel sections:

1. `Prerequisites`
2. `Solid Targets`
3. `Target Scope`
4. `Profile / Topology Preview`
5. `Watertight Validation`
6. `Solid Output`
7. `Diagnostics`

### 6.1 Prerequisites

Show whether the current document has:

- Applied Sections
- CorridorModel
- SurfaceModel
- RegionModel
- StructureModel where required
- DrainageModel or ditch point rows where required

### 6.2 Solid Targets

Show a table of available solid target families:

| Target Family | Scope | Source Owner | Status |
|---|---|---|---|
| Whole Road Body | corridor | Applied Sections / Assembly | available or blocked |
| Region Body | selected Region | Region / Applied Sections | available or blocked |
| Pavement Layer | Assembly Subassembly | Assembly / Applied Sections | available or blocked |
| Drainage Body | lined ditch, channel, culvert | Drainage / Assembly / Structure | available or blocked |
| Structure Body | wall, culvert, bridge deck | StructureModel | available or blocked |

### 6.3 Target Scope

Target scope controls should include:

- whole corridor
- selected Region
- station range
- Assembly Subassembly
- Structure reference
- Drainage reference

Region and station-range controls must use source Region and Stationing values rather than generated viewer object extents.

### 6.4 Build Actions

Recommended actions:

- `Refresh Targets`
- `Validate`
- `Build Selected`
- `Build Enabled`
- `Show Solid`
- `Hide Solid`
- `Export Ready Summary`

`Build Selected` should generate only the selected target.

`Build Enabled` should generate all enabled target rows that pass prerequisite checks.

## 7. Target Families

### 7.1 Whole Road Body

Purpose:

- create a corridor-level watertight envelope for review
- verify overall closed-profile and shell generation behavior

Initial scope:

- design top profile
- subgrade or simplified bottom profile
- left and right side faces
- start and end caps

Non-goal for the first slice:

- merging every drainage, structure, daylight, and earthwork body into one boolean solid

### 7.2 Region Body

Purpose:

- generate a watertight solid only for a selected Region
- support Region Boundary review and localized output

Rules:

- Region start and end positions must produce cap profiles
- Region source range controls must come from `RegionModel`
- transition sections may be inserted inside the Region range when Surface Transition or future Solid Transition intent exists

### 7.3 Drainage Body

Purpose:

- generate physical drainage Subassembly or Structure-backed solids

Valid first targets:

- lined ditch
- concrete channel
- culvert barrel
- headwall / wingwall
- inlet / outlet structure

Rule:

Open drainage grading surfaces are not solid targets.

Only drainage Subassemblies or Structures with thickness, material, volume, or asset identity should become watertight solids.

### 7.4 Structure Body

Purpose:

- generate structure-specific solids such as retaining walls, culverts, bridge decks, and approach slabs

Rules:

- `StructureModel` remains the source owner
- generated structure solids remain outputs
- corridor-following structures may be segmented by Applied Section frames
- boolean union with road-body solids is deferred until independent solids are stable

### 7.5 Assembly Subassembly Body

Purpose:

- generate Subassembly-level physical bodies from Assembly and Applied Section semantics

Valid first targets:

- pavement layer
- base layer
- shoulder body
- curb / gutter
- barrier
- lined ditch

## 8. Internal Build Pipeline

All target families should share one pipeline:

```text
SolidTarget
  -> AppliedSectionSolidProfile
  -> SolidProfileValidation
  -> EdgeNetwork
  -> FaceSet
  -> Shell
  -> WatertightValidation
  -> SolidOutput
```

### 8.1 SolidTarget

Defines what should be built.

Recommended fields:

- `target_id`
- `target_family`
- `scope_kind`
- `region_ref`
- `station_start`
- `station_end`
- `assembly_ref`
- `subassembly_ref`
- `structure_ref`
- `drainage_ref`
- `enabled`
- `material_ref`
- `notes`

### 8.2 AppliedSectionSolidProfile

Stores the closed semantic profile generated at one station for one target.

Recommended fields:

- `profile_id`
- `target_id`
- `station`
- `applied_section_ref`
- `region_ref`
- `profile_role`
- `node_rows`
- `edge_rows`
- `is_closed`
- `orientation`
- `diagnostic_refs`

### 8.3 EdgeNetwork

Connects matching semantic nodes along station direction.

Rules:

- longitudinal edges follow increasing station
- cross-section profile edges use one fixed orientation per target family
- semantic node ids must match across station profiles
- generated edge ids must be deterministic
- edge identity and adjacency are validated before FreeCAD Part shape construction

### 8.4 FaceSet

Creates:

- side faces between adjacent station profiles
- top and bottom faces where applicable
- start cap
- end cap
- transition faces where target profiles change

### 8.5 WatertightValidation

Validation must run before a result is accepted as watertight.

Required checks:

- all profile rows are closed
- start and end caps exist
- every shell edge is shared by exactly two faces
- no dangling boundary edges remain
- no non-manifold edges exist
- face normals are consistent
- shell is closed
- generated solid is valid
- volume is positive

Optional checks:

- self-intersection warning
- minimum face area warning
- short-edge warning
- tolerance merge warning

Implemented quality warnings:

- `short_topology_edge` warns when a generated topology edge is shorter than the configured warning threshold.
- `tiny_topology_face_area` warns when a generated topology face area is below the configured warning threshold.
- `part_face_triangulated` warns when a validated topology face must be split into triangular FreeCAD `Part.Face` objects because the direct polygon face is not accepted by Part.

These warnings do not block a closed shell by themselves.

## 9. Result And Output Contracts

Recommended result/output families:

- `SolidTargetModel`
- `AppliedSectionSolidProfileSet`
- `SolidEdgeNetwork`
- `WatertightSolidResult`
- `WatertightSolidOutput`

`WatertightSolidOutput` should preserve:

- source refs
- target refs
- Applied Section refs
- Region refs
- Assembly refs
- Structure refs
- Drainage refs
- validation status
- volume
- face count
- shell edge count
- diagnostics
- generated object refs

## 10. Relationship To Existing Systems

### 10.1 Applied Sections

Applied Sections are the primary semantic section basis.

They must provide semantic point rows rich enough to build closed profiles.

### 10.2 Build Corridor

Build Corridor remains the prerequisite result stage.

It builds corridor state, surfaces, Region Boundary review, and Surface Transition review.

It does not become the main Watertight Solid UI.

### 10.3 SurfaceModel

SurfaceModel remains the open surface result family.

SurfaceModel may help with review or target diagnostics, but watertight solids should not be generated by editing or stitching viewer meshes.

SurfaceModel remains geometry-first.

Watertight Solid generation is topology-first.

### 10.4 Structure Output

Existing structure solid work should become a compatible target family.

Structure-specific output can remain under Structure Output while also feeding the final Watertight Solids review stage.

## 11. Implementation Order

1. Add this plan to the v1 documentation index.
2. Add `Watertight Solids` to the master toolbar direction after `AI Assist`.
3. Follow `V1_WATERTIGHT_SOLID_IMPLEMENTATION_PLAN.md` for command, model, service, UI, validation, and test implementation.
4. Map accepted solids into quantity and exchange outputs after target validation is stable.

## 12. Acceptance Criteria

The first usable slice is accepted when:

- `Watertight Solids` appears after `AI Assist` in the top-level toolbar
- the command is disabled or blocked with a clear message before Build Corridor prerequisites exist
- the command opens after Build Corridor produces accepted prerequisites
- at least one `road_body_envelope` target can be validated
- generated profiles are closed
- topology validation runs before any Part solid is accepted
- shell validation reports zero dangling edges for the accepted target
- every accepted shell edge is shared by exactly two faces
- the generated solid is valid and has positive volume
- diagnostics identify the owning source rows when generation fails
- generated solids are outputs and are not treated as editable source geometry

## 13. Non-goals

This plan does not make generated solids editable design source.

This plan does not replace SurfaceModel, TIN previews, or earthwork surfaces.

This plan does not require boolean-unioning every road, drainage, and structure body into a single monolithic solid in the first implementation.

This plan does not perform advanced hydraulic analysis or automatic pipe sizing.

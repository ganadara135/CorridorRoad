# CorridorRoad V1 Project Tree Redesign Plan

Date: 2026-04-25
Branch: `v1-dev`
Status: Active implementation plan, v1-only root routing active
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_TIN_CORE_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_TIN_REVIEW_NEXT_STEP_PLAN.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_RAMP_MODEL.md`
- `docsV1/V1_INTERSECTION_MODEL.md`

## 1. Purpose

This document defines the v1 project tree structure for CorridorRoad.

The tree should express the project information model, not the old command layout.

The immediate reason for this redesign is the new TIN workflow:

- CSV source data is now an input asset
- `TINSurface` is a project surface result
- Mesh preview is a view artifact
- section, drainage, and earthwork must all reference the same terrain source

If this structure is not settled before downstream TIN consumers are added, later features may create parallel and inconsistent terrain references.

## 2. Current Tree Baseline

The current project tree in `freecad/Corridor_Road/objects/obj_project.py` is organized around:

- `01_Inputs`
- `02_Alignments`
- `03_Surfaces`
- `04_Analysis`
- optional `05_References`

Input subtrees include:

- `Terrains`
- `Survey`
- `Structures`
- `Regions`

This was useful for v0/v0.5 transition work, but it is not expressive enough for the v1 product model.

Current implementation note:

- new project trees are now v1-only by default; transition-era roots such as `01_Inputs`, `02_Alignments`, `04_Analysis`, and per-alignment `ALN_* / Horizontal` branches are no longer created
- `03_Surfaces` now uses the final v1 label because the legacy surface root is no longer created alongside it
- sample/new horizontal alignment objects route to `02_Alignment & Profile / Alignments`
- `V1Alignment` source objects are the preferred alignment objects for new v1 work
- the legacy `Sample Alignment` command now creates a v1 alignment source object and routes it to `02_Alignment & Profile / Alignments`
- vertical/profile objects route to `02_Alignment & Profile / Profiles`
- `V1Profile` source objects are the preferred profile objects for new v1 work
- the v1 `Create Profile` command creates a matched `V1Profile` and routes it to `02_Alignment & Profile / Profiles`
- stationing objects route to `02_Alignment & Profile / Stations`
- `V1Stationing` source/result objects are the preferred station-grid objects for new v1 work
- the v1 `Generate Stations` command creates a `V1Stationing` object and routes it to `02_Alignment & Profile / Stations`
- TIN source, result, diagnostics, and mesh preview records are routed under the v1 tree when a project tree exists
- v1 corridor-network routing helpers can resolve ramps, intersections, drainage, assemblies, regions, and applied sections to their preferred v1 folders
- v1 review, output/exchange, and AI assist routing helpers can resolve objects to their preferred v1 folders

Main limitations:

- source data and derived results are not clearly separated
- TIN source points, TIN result data, and mesh preview can be confused
- ramp, intersection, and drainage do not have first-class project locations
- review state is not separate from engineering source/result state
- output/exchange artifacts do not have a stable home
- AI assist outputs do not have an explicit project location

## 3. V1 Tree Principles

The v1 tree should follow these rules:

- durable source data and generated results must be visually distinct
- TIN terrain is a first-class surface contract
- mesh preview is never the terrain source of truth
- mainline, ramps, intersections, and drainage must be first-class project areas
- review artifacts should not become source data
- outputs and exchange packages should be separated from engineering models
- future AI-generated suggestions should be traceable but not silently applied
- object names may keep stable internal ids, but visible labels should be workflow-friendly

## 4. Proposed V1 Project Tree

Recommended visible tree:

```text
CorridorRoad Project
  00_Project Setup
    Project Settings
    Coordinate System
    Units
    Standards
  01_Source Data
    Survey Points
      Source CSV
      Filtered Ground Points
      Control Points
    Source Files
      CSV
      DXF
      LandXML
      IFC
    Existing References
      Existing Alignments
      Existing Structures
      Existing Utilities
  02_Alignment & Profile
    Alignments
    Stations
    Profiles
    Superelevation
  03_Surfaces
    Existing Ground TIN
      Source
      TIN Result
      Mesh Preview
      Diagnostics
    Design TIN
      Corridor Surface
      Subgrade Surface
      Daylight Surface
    Comparison TIN
      Cut Fill Surface
      Difference Surface
  04_Corridor Model
    Assemblies
    Regions
    Applied Sections
    Ramps
    Intersections
    Overrides
  05_Drainage
    Ditches
    Culverts
    Inlets
    Flow Paths
    Drainage Diagnostics
  06_Structures
    Retaining Walls
    Bridges
    Barriers
    Structure Interactions
  07_Quantities & Earthwork
    Quantities
    Cut Fill
    Mass Haul
    Earthwork Diagnostics
  08_Review
    Plan Profile Review
    Section Review
    TIN Review
    Issues
    Bookmarks
  09_Outputs & Exchange
    Sheets
    Reports
    DXF
    LandXML
    IFC
    Exchange Packages
  10_AI Assist
    Suggestions
    Checks
    Generated Alternatives
    User Decisions
```

## 5. Group Responsibilities

### 5.1 `00_Project Setup`

Owns project-wide configuration.

Examples:

- coordinate context
- unit policy
- design criteria
- project metadata

This group should not contain generated geometry.

### 5.2 `01_Source Data`

Owns imported or measured input data.

`Survey Points` specifically means raw or filtered point inputs before they become a `TINSurface`.

Examples:

- original point-cloud CSV
- filtered point rows
- control points
- field survey points

Important distinction:

- `Survey Points` are source data
- `Existing Ground TIN` is a surface result
- `Mesh Preview` is visual output

### 5.3 `02_Alignment & Profile`

Owns horizontal and vertical control.

Examples:

- alignments
- profiles
- station equations
- station markers
- superelevation source rows

### 5.4 `03_Surfaces`

Owns terrain and design surface contracts.

`Existing Ground TIN` should become the primary home for TIN terrain state.

TIN import placement:

```text
01_Source Data
  Survey Points
    pointcloud_tin_mountain_valley_plain.csv

03_Surfaces
  Existing Ground TIN
    Source
      pointcloud_tin_mountain_valley_plain.csv reference
    TIN Result
      TINSurface contract
    Mesh Preview
      TINPreview_pointcloud_tin_mountain_valley_plain
    Diagnostics
      extent, spacing, no-hit, degenerate triangle checks
```

Rules:

- `TINSurface` is the source of truth for terrain sampling
- mesh preview must be replaceable and regenerable
- surface diagnostics should be inspectable without opening exchange tools

### 5.5 `04_Corridor Model`

Owns the parametric corridor network.

Examples:

- assembly templates
- regions
- applied section sets
- ramps
- intersections
- explicit overrides

Ramps and intersections are first-class because the master plan treats v1 as a corridor-network platform rather than a mainline-only tool.

### 5.6 `05_Drainage`

Owns drainage design and review state.

Examples:

- ditches
- culverts
- inlets
- flow paths
- drainage diagnostics

Drainage should reference TIN surfaces and corridor geometry; it should not own terrain source data.

### 5.7 `06_Structures`

Owns structures and their corridor interactions.

Examples:

- retaining walls
- bridges
- barriers
- structure interaction rules

### 5.8 `07_Quantities & Earthwork`

Owns derived quantity and earthwork results.

Examples:

- quantity summaries
- cut/fill windows
- mass-haul results
- earthwork diagnostics

### 5.9 `08_Review`

Owns review artifacts, not source data.

Examples:

- review sessions
- issues
- bookmarks
- saved review contexts

The review tree can reference source/result objects elsewhere, but should not move those objects under review folders.

### 5.10 `09_Outputs & Exchange`

Owns deliverables and exchange packages.

Examples:

- sheets
- reports
- DXF exports
- LandXML exports
- IFC exports

### 5.11 `10_AI Assist`

Owns AI-generated suggestions and user decisions.

Examples:

- suggested alternatives
- design checks
- explanation records
- accepted/rejected decision rows

AI output should be traceable and reviewable; it should not silently become source data.

## 6. Object Placement Rules

Recommended routing:

- point-cloud CSV import -> `01_Source Data / Survey Points / Source CSV`
- `TINSurface` result -> `03_Surfaces / Existing Ground TIN / TIN Result`
- TIN mesh preview -> `03_Surfaces / Existing Ground TIN / Mesh Preview`
- TIN diagnostics -> `03_Surfaces / Existing Ground TIN / Diagnostics`
- alignment/profile source -> `02_Alignment & Profile`
- applied section set -> `04_Corridor Model / Applied Sections`
- ramp model -> `04_Corridor Model / Ramps`
- intersection model -> `04_Corridor Model / Intersections`
- drainage model -> `05_Drainage`
- cut/fill and mass-haul -> `07_Quantities & Earthwork`
- issue/bookmark -> `08_Review`
- reports and exchange packages -> `09_Outputs & Exchange`
- AI suggestions -> `10_AI Assist`

## 7. Compatibility Strategy

The active implementation now favors the v1 tree as the primary structure.

Legacy-to-v1 mapping for old files and code references:

```text
01_Inputs        -> 01_Source Data
02_Alignments    -> 02_Alignment & Profile
03_Surfaces      -> 03_Surfaces
04_Analysis      -> 07_Quantities & Earthwork
05_References    -> 01_Source Data / Existing References
Inputs/Survey    -> 01_Source Data / Survey Points
Inputs/Terrains  -> 03_Surfaces / Existing Ground TIN or Source Data / Existing References
Inputs/Regions   -> 04_Corridor Model / Regions
Inputs/Structures -> 06_Structures
```

Migration policy:

- new projects should not create legacy root groups
- known alignment/profile/stationing objects should be adopted into the v1 tree
- empty legacy tree folders may be removed during tree cleanup
- unknown user objects should still be preserved and routed to v1 references rather than deleted

## 8. Implementation Phases

### 8.1 Phase A: Document tree constants

Status: Complete, superseded by v1-only root creation

Goal:

- define v1 tree keys and visible group labels

Tasks:

- add v1 tree definition constants
- keep constants available for migration references, but do not create visible legacy roots for new projects
- add tests for required group names

### 8.2 Phase B: Ensure v1 tree folders

Status: Complete, v1-only root creation active

Goal:

- make `ensure_project_tree()` able to create the v1 structure

Tasks:

- create root groups `00` through `10`
- create first-level subgroups needed by TIN import
- avoid destructive migration
- preserve existing objects while removing empty transition-era tree folders when possible

### 8.3 Phase C: Route TIN import outputs

Status: Complete for first metadata-record routing slice

Goal:

- place TIN-related objects in the new tree

Tasks:

- place source CSV reference under `01_Source Data / Survey Points`
- place mesh preview under `03_Surfaces / Existing Ground TIN / Mesh Preview`
- record TIN result/diagnostic placeholders under surface subfolders where practical

Current implementation:

- mesh preview objects created by TIN Review are routed to `03_Surfaces / Existing Ground TIN / Mesh Preview`
- source CSV metadata records are routed to `01_Source Data / Survey Points`
- surface-source metadata records are routed to `03_Surfaces / Existing Ground TIN / Source`
- TIN result metadata records are routed to `03_Surfaces / Existing Ground TIN / TIN Result`
- TIN diagnostics metadata records are routed to `03_Surfaces / Existing Ground TIN / Diagnostics`

### 8.4 Phase D: Route corridor-network objects

Status: Complete for resolver/helper layer and alignment/profile/stationing command routing

Goal:

- make ramps, intersections, regions, sections, and overrides first-class in the tree

Tasks:

- route ramp objects to `04_Corridor Model / Ramps`
- route intersection objects to `04_Corridor Model / Intersections`
- route drainage objects to `05_Drainage`

Current implementation:

- `resolve_v1_target_container()` resolves preferred v1 folders for alignment, profile, stationing, corridor-network, drainage, review, output/exchange, and AI-assist objects
- `route_to_v1_tree()` can add a child to its preferred v1 folder when called by a v1 command or object creator
- `CorridorRoadProject.adopt()` now prefers v1 folders for known object families
- v1 sample alignment creation adopts `V1Alignment` into `02_Alignment & Profile / Alignments`
- v1 sample profile creation adopts `V1Profile` into `02_Alignment & Profile / Profiles`

### 8.5 Phase E: Review and output routing

Status: Complete for resolver/helper layer; automatic object-command integration remains future work

Goal:

- separate review artifacts and deliverables from engineering source/result objects

Tasks:

- route review contexts to `08_Review`
- route exchange packages to `09_Outputs & Exchange`
- route AI suggestions to `10_AI Assist`

Current implementation:

- review objects resolve to `08_Review` subfolders such as `Plan Profile Review`, `Section Review`, `TIN Review`, `Issues`, and `Bookmarks`
- output and exchange objects resolve to `09_Outputs & Exchange` subfolders such as `Sheets`, `Reports`, `DXF`, `LandXML`, `IFC`, and `Exchange Packages`
- AI assist objects resolve to `10_AI Assist` subfolders such as `Suggestions`, `Checks`, `Generated Alternatives`, and `User Decisions`
- global adoption now prefers v1 folders for known CorridorRoad object families

## 9. Manual QA Scenario

TIN tree QA should eventually verify:

1. Create a new project.
2. Run `PointCloud TIN`.
3. Select `tests/samples/pointcloud_tin_mountain_valley_plain.csv`.
4. Confirm source CSV appears under `01_Source Data / Survey Points`.
5. Confirm mesh preview appears under `03_Surfaces / Existing Ground TIN / Mesh Preview`.
6. Confirm TIN Review opens and reports the same source, extents, and mesh facet count.
7. Confirm deleting/recreating mesh preview does not delete source CSV or TIN result state.

## 10. Stop Conditions

Pause and realign if:

- tree routing requires deleting user objects
- mesh preview becomes the terrain source of truth
- review folders start owning source/result objects
- drainage, ramps, or intersections are folded back into generic analysis folders
- legacy compatibility starts overriding the v1 tree model

## 11. Definition of Done

The v1 tree redesign is done when:

- the project tree visually communicates source data, model data, results, review, and outputs
- TIN import places source, surface result, preview, and diagnostics in separate logical homes
- ramps, intersections, and drainage have first-class folders
- tests cover creation of required v1 tree folders
- no unknown user objects are destructively moved during migration

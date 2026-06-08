# Parametric Road V1 Watertight Solid Target Expansion Plan

Date: 2026-05-08  
Status: Draft implementation plan  
Scope: target families beyond `road_body_envelope`

Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_SURFACE_MODEL.md`
- `docsV1/V1_WATERTIGHT_SOLID_PLAN.md`
- `docsV1/V1_WATERTIGHT_SOLID_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_ASSEMBLY_MODEL.md`
- `docsV1/V1_DRAINAGE_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_STRUCTURE_GEOMETRY_CONTRACT.md`

## 1. Purpose

`Build Corridor` already creates surface outputs such as `Design Surface`.

`Watertight Solids` must not stop at a duplicate of that surface.

The higher-level goal is to support terrain-inclusive whole-road simulation.

That means the final output must be able to represent the road body, terrain boundary, drainage bodies, structure bodies, and physical component bodies as validated watertight solids where the simulation domain requires them.

The Watertight Solids panel now includes a first-slice `Simulation QA` summary backed by `SimulationQaOutput` and `WatertightSimulationQaService`. It scans built `V1WatertightSolidOutput` objects and reports:

- built output count and target-family coverage
- road body, terrain, drainage, and structure readiness
- invalid or zero-volume output counts
- first-slice bounding-box contact diagnostics between road-body solids and drainage/structure solids
- first-slice terrain-domain bounding-box diagnostics when a terrain shape provides a usable domain extent
- first-slice pipe/structure port diagnostics that require built `structure_body` outputs and connection point provenance when Drainage pipeline solids reference Structures
- total built solid volume
- whether the current set is simulation-ready for the first road + terrain + drainage gate

After a Watertight Solid build action, the same QA summary is persisted as a `V1SimulationQaOutput` report object routed under `Outputs & Exchange / Reports`. This keeps simulation-readiness evidence separate from generated solid geometry while preserving source refs back to the built watertight output objects.

The panel also exposes this contract directly through `Simulation QA / Families` and `Simulation QA / Diagnostics` tables. The tables are read-only review surfaces; they do not edit generated geometry or source intent.

The first simulation hand-off object is `SimulationPackageOutput`. It is a manifest, not a new geometric boolean result. It groups built `V1WatertightSolidOutput` object refs with the current `SimulationQaOutput`, records package status as `ready` or `blocked`, and routes the persisted `V1SimulationPackageOutput` object under `Outputs & Exchange / Exchange Packages`.

The first hand-off export format is JSON. `Export Package` writes the persisted manifest with package status, QA ref, terrain context, packaged solid rows, target families, volume, diagnostics, and traceability refs. It also writes generic BREP files for included `V1WatertightSolidOutput` objects when their FreeCAD `Shape` is available, then records the relative geometry file path, object ref, format, and export status on each solid row. It does not export solver-specific meshes yet.

When both a v1 surface model record and an actual terrain Shape/Mesh object are present, the package terrain context should prefer the terrain object that owns geometry. The v1 surface model can still satisfy workflow readiness, but the hand-off manifest should point to the geometric terrain reference and its bounding box when available.

This plan defines how to expand solid targets from the current `road_body_envelope` baseline into physical corridor bodies:

- road body envelope
- Region body envelope
- pavement and subbase layer bodies
- shoulder, curb, gutter, barrier, and other Assembly component bodies
- lined ditch and channel bodies
- drainage structure bodies
- StructureModel bodies such as retaining walls, culverts, slabs, and bridge-related objects

## 2. Core Distinction

`Design Surface` is a terrain-like top surface output.

`road_body_envelope` is a closed solid envelope built from top and bottom section profiles.

They overlap visually at the top face, but they are not the same product object.

`Design Surface` answers:

- what is the finished grade surface?
- how does the corridor tie into terrain?
- what should be reviewed as a surface?

`road_body_envelope` answers:

- can the road body range be closed as a watertight volume?
- can the system validate profile, edge, face, and shell topology?
- can the corridor produce a solid handoff baseline?

The real target expansion is physical component solids.

## 3. Target Principle

Create solids only for bodies that have at least one of these properties:

- thickness
- material
- volume
- asset identity
- IFC or exchange identity
- structure or drainage ownership

Do not create solids for open grading surfaces unless a source model defines a physical lining, wall, slab, pipe, channel, or other body.

## 4. Target Family Matrix

| Target family | Source owner | Current state | Solid strategy | Priority |
|---|---|---:|---|---:|
| `road_body_envelope` | Applied Sections / CorridorModel | first path implemented | closed top and bottom envelope | P0 baseline |
| `region_body` | RegionModel / Applied Sections | first path implemented | clipped envelope with Region start/end cap profiles | P0 baseline |
| `pavement_layer_body` | Assembly component rows / Applied Sections | first slice available | component closed profiles from width and thickness | P1 |
| `subbase_body` | Assembly component rows / Applied Sections | first slice available | component closed profiles from width and thickness | P1 |
| `shoulder_body` | Assembly component rows / Applied Sections | first slice available | same component body pipeline with shoulder semantics | P2 |
| `curb_gutter_body` | Assembly component rows / Applied Sections | not yet implemented | shape-specific closed component profile | P2 |
| `barrier_body` | Assembly component rows / Applied Sections | not yet implemented | shape-specific closed component profile or structure-style body | P2 |
| `lined_ditch_body` | Assembly ditch shape / DrainageModel | first slice available | offset ditch profile by lining thickness and material | P1 |
| `drainage_channel_body` | DrainageModel / Assembly ditch shape | deferred | closed channel lining or precast channel section | P2 |
| `pipe_body` | DrainageModel / StructureModel | deferred | swept circular or box profile along drainage alignment | P2 |
| `culvert_body` | StructureModel / DrainageModel | target discovery exists for structures | reuse Structure Output first, then corridor-aware target | P1 |
| `headwall_body` | StructureModel | deferred | native structure solid output | P2 |
| `retaining_wall_body` | StructureModel | target discovery exists for structures | reuse Structure Output first, then segment by station where needed | P1 |
| `bridge_deck_body` | StructureModel | deferred | native structure body, not road envelope | P3 |
| `intersection_pavement_body` | IntersectionSurfaceZoneResult | planned handoff | zone-scoped closed body from accepted pavement zone boundaries | P1 |
| `intersection_subgrade_body` | IntersectionSurfaceZoneResult | planned handoff | zone-scoped subgrade body under pavement and curb-return zones | P1 |
| `intersection_slope_body` | IntersectionSurfaceZoneResult | planned handoff | exterior Slope Face zone body from daylight/pavement/curb-return edge contracts | P1 |
| `intersection_curb_return_body` | IntersectionSurfaceZoneResult | planned handoff | curb-return zone body from curb-return edge and adjacent pavement boundaries | P1 |

## 5. Implementation Approach

### 5.1 Keep One Shared Pipeline

Every target family should use the same acceptance chain:

```text
SolidTargetRow
  -> closed semantic profiles or native structure body reference
  -> topology edge network
  -> face rows
  -> closed shell validation
  -> FreeCAD Part solid mapping
  -> WatertightSolidOutput
```

Target-specific code should only decide how to create closed profiles or import a native structure body.

Validation, output persistence, diagnostics, quantity handoff, and exchange handoff should stay shared.

### 5.2 Do Not Boolean-Union Everything First

The first expansion should produce independent watertight solids.

Examples:

- `road_body_envelope`
- `pavement_layer_body:lane-left`
- `pavement_layer_body:lane-right`
- `subbase_body:main`
- `lined_ditch_body:left`
- `retaining_wall_body:wall-1`
- `culvert_body:culvert-1`

Boolean union, subtraction, and clash trimming should be later steps.

Independent solids are easier to validate, easier to diagnose, and better for quantity and IFC identity.

They are also the safer path for simulation.

The recommended simulation workflow is:

```text
independent target solids
  -> target validation
  -> interface diagnostics
  -> simulation package
  -> optional boolean composition
```

The system should not hide a failed component, drainage body, structure body, or terrain boundary inside one large boolean result.

Final composition can be offered after each participating solid is valid and its source identity is preserved.

## 6. Source Ownership Rules

### 6.1 Road And Region Envelope

Owner:

- `AppliedSectionSet`
- `CorridorModel`
- `RegionModel` when scoped by Region

Use:

- top points from finished grade or design surface roles
- bottom points from subgrade roles
- fallback depth only as a diagnostic-backed temporary rule

Do not use:

- generated viewer mesh triangles as source truth

### 6.2 Assembly Component Bodies

Owner:

- `AssemblyModel`
- evaluated `AppliedSection.component_rows`

Use:

- component id
- component kind
- side
- offset range
- width
- thickness
- material
- station range

Valid first targets:

- pavement layer
- subbase
- shoulder where width and thickness exist

Shape-specific later targets:

- curb
- gutter
- barrier
- median component

### 6.3 Drainage Bodies

Owner:

- `DrainageModel`
- Assembly ditch or channel component
- `StructureModel` for culvert-like drainage structures

Use:

- ditch shape contract
- flowline or drainage alignment
- lining thickness
- material
- left/right side
- station start/end
- inlet/outlet references

Open drainage surfaces remain surface outputs.

Only lined, piped, boxed, precast, or structural drainage objects become solid targets.

### 6.4 Structure Bodies

Owner:

- `StructureModel`
- existing Structure Output pipeline

First rule:

- `Watertight Solids` should discover and list structure targets
- `Build Selected` should first reuse compatible existing structure solid outputs where available
- direct corridor-following structure profile generation comes after this handoff is stable

Valid targets:

- retaining wall
- culvert
- headwall
- wingwall
- bridge deck
- approach slab

## 7. UI Plan

### 7.1 Target Table

Keep the current `Solid Targets` table, but group targets by family.

Recommended columns:

- `Enabled`
- `Target`
- `Family`
- `Scope`
- `Source`
- `Material`
- `STA Range`
- `Readiness`
- `Output`

Recommended family labels:

- `Envelope`
- `Region`
- `Assembly Component`
- `Drainage`
- `Structure`

### 7.2 Naming

Rename user-facing `road_body_envelope` label to:

`Road Body Envelope`

Tooltip:

`Closed baseline body from finished grade and subgrade profiles. This is not the Design Surface object.`

### 7.3 Target Filters

Add a compact target-family filter:

- `All`
- `Envelope`
- `Components`
- `Drainage`
- `Structures`

The filter should not change source data.

It only helps the user select which solid family to build.

### 7.4 Build Behavior

`Build Selected` builds one selected target.

`Build Enabled` builds checked targets independently.

If one target fails, other enabled targets should continue.

The panel should show:

- built count
- failed count
- total volume
- output object refs
- first diagnostics per failed target

## 8. Implementation Phases

### Phase TS1: Clarify Target Discovery

Goal:

- make target family readiness explicit
- avoid presenting surface-only objects as solid-ready bodies

Tasks:

- keep `road_body_envelope` and `region_body`
- keep existing pavement/subbase component discovery
- mark unsupported component kinds as blocked with clear diagnostics
- list structure targets as available only when compatible native geometry or Structure Output exists
- keep drainage body targets blocked until material/thickness/shape rules exist

Acceptance:

- user can see why a target is available or blocked
- `Design Surface` is not listed as a solid target

Status:

- In progress.
- `Road Body Envelope` is now presented as a user-facing target label instead of exposing only `road_body_envelope`.
- Solid target rows separate `pavement_layer_body`, `subbase_body`, and `shoulder_body`.
- Component targets with invalid width or thickness are blocked with readiness diagnostics instead of being silently ignored.

### Phase TS2: Assembly Component Solid Profiles

Goal:

- make pavement and subbase bodies useful beyond the envelope target

Tasks:

- extend component profile creation to preserve component family and material
- add support for shoulder components when width and thickness exist
- add diagnostics for missing thickness, missing material, or discontinuous station coverage
- keep component bodies independent from `road_body_envelope`

Acceptance:

- pavement/subbase/shoulder targets validate and build as separate solids
- output rows preserve component refs and material refs

Status:

- In progress for rectangular component-profile bodies.
- Pavement, subbase, and shoulder targets share the closed component-profile pipeline.
- Shape-specific curb, gutter, and barrier profile rules remain deferred.

### Phase TS3: Lined Ditch Solid

Goal:

- create the first drainage-owned solid target.

Tasks:

- read ditch surface/profile roles from Applied Sections
- read lining thickness and material from Assembly or Drainage policy
- build closed lining profiles by offsetting ditch shape
- cap station start/end
- block unlined ditch surfaces

Acceptance:

- lined ditch targets appear only when lining thickness and material are known
- open drainage surfaces remain blocked as non-solid targets

Status:

- In progress.
- `ditch_surface` rows can now discover `lined_ditch_body` target candidates by side.
- A ditch candidate without material and positive lining thickness is blocked with `lined_ditch_missing_lining_policy`.
- A ditch candidate with surface rows and lining policy is available for first-slice solid generation.
- The profile builder uses the side-specific ditch surface polyline and a section-normal lining-thickness offset to create a closed profile.
- If intermediate ditch surface points are present, the builder keeps them as profile nodes and records `lined_ditch_polyline_normal_offset`.
- Open drainage surface rows are not treated as buildable solids by themselves.

### Phase TS4: Structure Solid Handoff

Goal:

- bring structure solids into the final `Watertight Solids` stage without duplicating structure logic.

Tasks:

- discover compatible Structure Output solids
- map them into `WatertightSolidOutput`
- preserve `structure_ref`, material, volume, and diagnostics
- keep generated objects under the `Watertight Solids` output group or cross-reference existing Structure Output objects

Acceptance:

- retaining wall or culvert targets can be reviewed from the final solid panel
- structure solids remain owned by StructureModel / Structure Output logic

### Phase TS5: Drainage Structures

Goal:

- support culvert, pipe, headwall, inlet, and outlet body targets.

Tasks:

- connect DrainageModel elements to StructureModel where applicable
- generate swept pipe or box profiles where native specs exist
- preserve inlet/outlet asset identity
- keep drainage network solids separate from road envelope solids

Acceptance:

- drainage structures are buildable as separate target rows
- exchange output can identify them as drainage/structure bodies

### Phase TS6: Composition And Conflict Review

Goal:

- review relationships between independent solids.

Tasks:

- detect overlaps between road envelope, component solids, drainage solids, and structures
- report gap/overlap diagnostics
- provide optional clipping or boolean operation planning
- keep boolean union out of the default first build path

Acceptance:

- user can identify where solids touch, overlap, or leave gaps
- independent solids remain exportable even when composition warnings exist

## 9. Risk Analysis

| Risk | Impact | Mitigation |
|---|---|---|
| Treating Design Surface as a solid source | incorrect closed bodies | use Applied Section semantic profiles, not surface mesh triangles |
| Building one monolithic boolean solid too early | fragile failures and poor diagnostics | build independent solids first |
| Missing material/thickness on components | fake volumes | block target or warn with explicit fallback policy |
| Open ditch surfaces accidentally become solids | misleading drainage quantities | require lining/channel/pipe/structure identity |
| Structure Output and Watertight Solids duplicate ownership | conflicting objects | StructureModel remains source; Watertight stage references or maps outputs |
| Region boundaries split component bodies incorrectly | gaps or duplicate caps | use Region only as scope unless component ownership changes |
| Non-planar corridor faces fail Part creation | build failure | keep Part mapper triangulation fallback with diagnostics |

## 10. Contract Tests

Add focused tests for:

- unsupported surface-only target is not discovered as buildable
- pavement and subbase targets preserve material and component refs
- shoulder target appears only with width and thickness
- lined ditch target is blocked without lining thickness
- lined ditch target builds when ditch shape, material, and thickness are present
- structure target maps existing structure output without re-owning source logic
- `Build Enabled` continues after one target failure
- exchange handoff preserves target family and source owner

## 11. Immediate Next Step

The next implementation should continue TS3.

Completed TS3 follow-up:

- lined ditch output diagnostics include `lined_ditch_shape_provenance`
- provenance records drainage ref, component ref, side, material, lining thickness, offset method, profile/node counts, station list, and top source point refs
- exchange source-context rows preserve watertight solid drainage and material refs
- the Watertight Solids panel source column and show/hide/focus status preserve lined ditch drainage, side, component, and material context
- target discovery can accept `DrainageModel` and promote matching ditch/channel elements to the lined ditch target owner
- when a DrainageModel owner is present, the target keeps the drainage element id, drainage model id, and policy ref in source refs while still using Applied Section ditch geometry for the first solid slice
- lined ditch component parameters can request `lining_join_policy=miter`
- `lining_miter_limit` limits sharp corner miter length; when exceeded, the profile builder falls back to normal-average offset and records `lined_ditch_miter_limit_fallback`
- output provenance records `join_policy` and `miter_limit`
- `V1DrainageModel` document objects can now feed Watertight Solid discovery, so persisted DrainageModel ditch/channel elements can own lined ditch targets

Drainage solids should start after the component body path is stable because lined ditch solids need explicit thickness and material policy.

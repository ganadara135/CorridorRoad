# Parametric Road V1 Region Domain Ownership Redesign Plan

## Purpose

Define the detailed v1 plan for simplifying `Region` ownership.

The target workflow is:

`Region` owns station spans and the base `Assembly` only.

`Structure` and `Drainage` own their own domain intent and reference `Region` from their own panels.

This removes the confusing pattern where the Region panel appears to own Assembly, Structure, and Drainage at the same time.

The active toolbar order should place Structures after Regions:

`Assembly -> Regions -> Structures -> Drainage -> Applied Sections -> Build Corridor`

## Scope

This plan covers:

- Region source contract simplification
- Region editor UI changes
- Structure editor Region assignment
- Drainage editor Region assignment
- Applied Section evaluation changes
- Build Corridor, Review, Quantity, and Watertight Solid handoff changes
- validation and tests

Legacy migration is out of scope.

## Core Rule

Region is the station-range and base Assembly application layer.

Structure and Drainage are first-class source domains.

They must reference Region when they need station context.

Region must not store active Structure or Drainage ownership in the active v1 workflow.

## Intentional Deviation

Some existing v1 documents and first-slice code describe `RegionRow.structure_ref`, `RegionRow.structure_refs`, and `RegionRow.drainage_refs` as Region handoff fields.

This plan supersedes that direction for active v1 work.

The new direction is:

- `RegionRow.assembly_ref` remains active.
- `RegionRow.structure_ref` and `RegionRow.structure_refs` have been removed from active authoring, persistence, and downstream active context.
- `RegionRow.drainage_refs` has been removed from active authoring, persistence, and downstream active context.
- Structure and Drainage source models carry `region_ref` ownership instead.

## Target Ownership Table

| Domain | Owns | References |
|---|---|---|
| Region | station span, priority, base Assembly | Assembly |
| Assembly | reusable section Subassemblies and ditch Subassembly shape where applicable | none or Subassembly-local refs |
| Structure | bridge, culvert, retaining wall, wall, headwall, inlet/outlet body intent | Region, geometry specs, optional alignment/profile context |
| Drainage Element | ditch, gutter, swale, channel, culvert reference, inlet reference, outfall reference | Region, Policy, optional Assembly Subassembly for ditch, optional Structure ref for structure-backed drainage nodes |
| Drainage Flow Route | connection graph between Drainage Elements and final Outlet context | Drainage Elements, optional Structure or Outlet ref |
| Applied Sections | evaluated station section result | Region, Assembly, resolved Structure, resolved Drainage |
| Build Corridor | generated corridor surfaces and review previews | Applied Sections and resolved context |
| Watertight Solids | selected physical solid targets | Applied Sections, StructureModel, DrainageModel, CorridorModel |

## Target User Workflow

1. Create stationing and profile.
2. Create Assemblies.
3. Open Regions.
4. Define Region start stations.
5. Select one base Assembly per Region.
6. Apply Regions.
7. Open Structures.
8. Create structure rows and choose the owning Region for each row.
9. Validate Structure station ranges against the selected Region.
10. Open Drainage.
11. Create Drainage Elements and choose the owning Region for each Element.
12. Create Flow Routes between Elements and Outlets.
13. Validate Drainage Element station ranges against selected Regions.
14. Build Applied Sections.
15. Build Corridor.
16. Review surfaces, drainage, structures, quantities, and Watertight Solids.

## Toolbar Order Plan

The source-authoring toolbar should follow the ownership dependency order:

`Assembly -> Regions -> Structures -> Drainage -> Applied Sections -> Build Corridor`

Reason:

- Assembly defines reusable section Subassemblies.
- Regions assign base Assembly over station spans.
- Structures then choose their owning Region.
- Drainage Elements and Flow Routes then choose their owning Region and optional Structure refs.
- Applied Sections evaluates all accepted source models into station results.
- Build Corridor creates surfaces and review outputs from Applied Sections.

The workbench toolbar and menu command group should place `CorridorRoad_V1EditStructures` immediately after `CorridorRoad_V1EditRegions`.

## Region Editor UI Plan

The Region table should become a compact base-section table.

Target columns:

| Column | Role |
|---|---|
| Start STA | user-selected Region start station |
| End STA (Auto) | derived from next Region start or final station |
| Assembly | row-level combo from Assembly IDs |
| Priority | conflict ordering for overlapping or future advanced Region cases |

Remove from active Region table:

- Structure
- Drainage
- Attach Drainage button
- Region-side Structure validation
- Region-side Drainage validation

The Region panel should not expose Structure or Drainage selection controls.

## Structure Editor UI Plan

Structure is responsible for Region assignment.

Add or confirm these Structure editor fields:

| Field | Role |
|---|---|
| Structure ID | durable structure source id |
| Kind | bridge, culvert, retaining wall, custom, etc. |
| Region | row-level combo from active Region IDs |
| Start STA | structure influence start |
| End STA | structure influence end |
| Geometry Spec | linked structure geometry definition |
| Interaction Rule | how structure affects corridor sections and surfaces |

Validation:

- Region is required for corridor-affecting structures.
- Structure station span must be inside the selected Region boundary.
- A structure can reference the same Region as other structures when they are independent.
- Multiple structures in one Region are allowed.
- A warning should appear when a structure spans multiple Regions. The user should split the structure placement or explicitly choose a multi-Region behavior later.

Terminology:

- Region panel no longer has `Structure`.
- Structure editor owns `Structure ID`.
- Drainage can still reference a Structure ID for culverts, inlets, outfalls, or headwalls, but this is a Drainage relationship, not Region ownership.

## Drainage Editor UI Plan

Drainage is responsible for Region assignment.

Element rows remain the primary Region ownership surface.

Target Elements columns:

| Column | Role |
|---|---|
| Element ID | durable drainage node id |
| Kind | ditch, gutter, swale, channel, culvert reference, inlet reference, outfall reference |
| Region | row-level combo from active Region IDs |
| Side | left, right, both, center |
| Start STA | element start |
| End STA | element end |
| Assembly | active only for `ditch` rows |
| Policy | combo from Policy tab IDs |
| Structure Ref | active only for non-ditch rows when a drainage node is backed by a Structure |

Flow Routes should not be selected from the Region panel.

Flow Routes connect Elements:

| Column | Role |
|---|---|
| Flow Route ID | durable route id |
| From Element | upstream or source Element |
| To Element | downstream Element |
| Outlet | final outlet or structure-backed outlet ref |
| Direction | route meaning |
| Risk | review priority |
| Notes | source notes |

Validation:

- Element Region is required when Element ID is present.
- Element station span must stay inside the selected Region boundary.
- Flow Route From/To refs must exist.
- Flow Routes may connect Elements in different Regions, but this should produce an informational or warning diagnostic that explains the cross-Region flow.
- Structure Ref on Drainage Elements should be validated against known Structure IDs when available.

Terminology:

- Use `Structure Ref` or `Drainage Structure Ref` in the Drainage panel.
- Do not call this column simply `Structure` if it causes confusion with the Structure editor.

## Source Model Plan

### RegionModel

Active `RegionRow` fields:

- `region_id`
- `station_start`
- `station_end`
- `region_index`
- `assembly_ref`
- `priority`
- `policy_set_ref`
- `notes`

Remove from active v1 use:

- `structure_ref`
- `structure_refs`
- `drainage_refs`

No legacy migration is required.

Implementation may delete these fields from the active dataclass once all active tests and consumers have moved to the new resolution path.

### StructureModel

Structure rows or placements need explicit Region ownership.

Required or target field:

- `region_ref`

The active structure placement should carry station start/end and Region context.

### DrainageModel

Drainage Element rows already carry `region_ref`.

This becomes the only active Region linkage for Drainage.

Flow Routes derive Region context from their From/To Elements.

## Evaluation Plan

Introduce or update an active context resolver.

Input:

- RegionModel
- AssemblySubassemblyModel
- StructureModel
- DrainageModel
- station

Output:

- active Region
- active Assembly
- active Structures for that station and Region
- active Drainage Elements for that station and Region
- active Flow Routes linked to active Drainage Elements

Applied Sections should no longer read Structure or Drainage refs from Region rows.

Applied Sections should resolve:

1. Region by station.
2. Assembly from Region.
3. Structures from StructureModel by `region_ref` and station span.
4. Drainage Elements from DrainageModel by `region_ref` and station span.
5. Flow Routes from DrainageModel by active Element refs.

## Downstream Handoff Plan

### Applied Sections

Change source context:

- keep `region_ref`
- keep `assembly_ref`
- populate `structure_refs` from StructureModel resolution
- populate `drainage_refs` from DrainageModel Element resolution
- populate `flow_route_refs` where result contracts support it

Existing output result rows may keep `structure_refs` and `drainage_refs`.

The source of those refs changes from Region handoff to domain resolution.

### Build Corridor

Region Boundaries review should show:

- Region ID
- STA range
- Assembly
- resolved Structures from Applied Sections or StructureModel
- resolved Drainage from Applied Sections or DrainageModel

The Region table in Build Corridor review may still display Structure/Drainage summaries, but they must be read-only resolved summaries, not Region source fields.

### Drainage Review

Drainage Review should read Region ownership from Drainage Elements.

It should no longer report missing Region `drainage_refs`.

It should report:

- Drainage Elements missing Region
- Drainage Elements outside selected Region
- Flow Routes crossing Regions
- Flow Routes with missing Outlet context

### Quantity

Drainage quantities should continue to use Applied Section `drainage_ref` and `flow_route_ref`.

Those refs must come from DrainageModel resolution, not Region rows.

### Watertight Solids

Structure targets should come from StructureModel and resolved Applied Section structure refs.

Lined ditch and drainage targets should come from DrainageModel Elements and Flow Routes.

Region body targets should use Region and Assembly only.

## Implementation Phases

### Phase 0: Contract Decision

Status target: documentation and tests first.

Tasks:

- Add this plan.
- Update docsV1 README rule text.
- Add tests that document Region editor target columns.
- Add tests that document active consumers do not require Region Structure or Drainage source fields.

Acceptance:

- The project has one explicit plan for Region/Structure/Drainage ownership.
- No new active test should require editing Structure or Drainage from the Region panel.

### Phase 1: Region Editor Cleanup

Status: Implemented for active Region editor authoring.

Tasks:

- [x] Remove Structure column from Region editor.
- [x] Remove Drainage column from Region editor.
- [x] Remove Attach Drainage UI.
- [x] Remove Region editor known Structure and known Drainage validation paths.
- [x] Update Region presets so they only assign Assembly.
- [x] Keep Region start-only workflow and auto End STA.

Acceptance:

- [x] Region panel table shows Start STA, End STA (Auto), Assembly, Priority, and Notes.
- [x] Region editor-created rows carry no Structure or Drainage refs.
- [x] Region validation from the editor checks continuity, station order, Assembly refs, and priority only.

Completed cleanup:

- `RegionRow.structure_ref`, `RegionRow.structure_refs`, and `RegionRow.drainage_refs` have been removed from the active source dataclass.
- `V1RegionModel` no longer persists `StructureRefs`, `StructureRefRows`, or `DrainageRefRows`.

### Phase 2: Structure Region Ownership

Status: Implemented for Structure source persistence, editor assignment, and Region-boundary validation.

Tasks:

- [x] Add Region combo to Structure editor placement rows.
- [x] Persist `region_ref` in Structure placement rows.
- [x] Validate referenced Region exists when a RegionModel is available.
- [x] Validate Structure station range stays inside selected Region.
- [ ] Update Structure output and review to show Region context through the shared station resolver.

Acceptance:

- [x] A user can assign a Structure to a Region without editing the Region panel.
- [x] Structure source object round-trips placement Region ownership.
- [x] Structure Validate/Apply blocks outside-Region station ranges from the Structure panel.
- [ ] Structure output still finds active structures for corridor sections through domain resolution.
- [ ] Cross Section Viewer can show active Structure context from resolved StructureModel data.

Implemented notes:

- `StructurePlacement.region_ref` is the active Structure-to-Region ownership field.
- `V1StructureModel` stores placement Region refs in `PlacementRegionRefs`.
- The Structure editor table includes a row-level `Region` combo populated from the active RegionModel.
- Region-boundary validation uses a small station tolerance to match displayed station precision.

Deferred:

- Structure output/review Region context belongs with Phase 4 resolver work so Applied Sections, Build Corridor review, Cross Section Viewer, and Watertight Solid handoff all use one shared resolution path.

### Phase 3: Drainage Region Ownership

Status: Implemented for Drainage editor ownership fields, validation, and Flow Route Region diagnostics.

Tasks:

- [x] Keep Drainage Elements Region combo as the active Region ownership field.
- [x] Rename Drainage Elements `Structure` column to `Structure Ref`.
- [x] Keep Policy combo populated from Policy tab.
- [x] Keep Flow Routes prefix-hidden display with source refs preserved internally.
- [x] Add cross-Region Flow Route diagnostics.
- [x] Validate Drainage Element Structure refs against StructureModel when available.
- [x] Remove remaining Region-side Drainage reference assumptions from Applied Section and review consumers in Phase 4/5.

Acceptance:

- [x] A user can assign Drainage Elements to Regions without editing the Region panel.
- [x] Drainage validation catches missing Region and outside-Region station ranges.
- [x] Flow Routes remain valid graph edges between Elements.
- [x] Flow Routes that connect Elements in different Regions report a warning diagnostic.

Implemented notes:

- `Structure Ref` in the Drainage Elements table is a drainage relationship to a Structure source row, not a Region-owned structure assignment.
- Ditch rows continue to disable and clear `Structure Ref`.
- Non-ditch rows can use `Structure Ref` for culverts, inlets, outfalls, and other structure-backed drainage nodes.

### Phase 4: Applied Section Resolver Rewrite

Status: Implemented first slice inside Applied Section builder.

Tasks:

- [x] Combine Region, Structure, and Drainage source models at each Applied Section station.
- [x] Update Applied Section builder to resolve Structures by `StructurePlacement.region_ref` and station span.
- [x] Update Applied Section builder to resolve Drainage Elements by `DrainageElementRow.region_ref` and station span.
- [x] Stop using Region-side Structure and Drainage refs for active Applied Section context.
- [x] Preserve existing result output fields where they are still useful.
- [ ] Extract the station context logic into a named shared resolver service before widening review/output consumers.

Acceptance:

- [x] Applied Sections still contain structure and drainage context.
- [x] That context comes from StructureModel and DrainageModel.
- [x] Existing corridor surface, quantity, and solid consumers continue to receive source refs.

Implemented notes:

- `AppliedSectionBuildRequest` and `AppliedSectionSetBuildRequest` now accept `drainage_model`.
- Structure context is resolved from StructureModel rows whose placement covers the station and whose `region_ref` matches the active Region.
- Drainage context is resolved from DrainageModel Elements whose station span covers the station and whose `region_ref` matches the active Region.
- Ditch/gutter/swale/channel Subassembly rows and `ditch_surface` points keep `drainage_refs`/`drainage_ref`, but the source of those refs is DrainageModel, not RegionModel.

Deferred:

- Region result and review services still need cleanup where they display older Region handoff wording.
- A formal `StationContextResolver` should replace the current builder-local helpers once Build Corridor, Drainage Review, Cross Section Viewer, and Watertight Solids all consume the same station context.

### Phase 5: Review And Output Alignment

Status: Implemented first slice for Build Corridor Region Boundaries, Drainage Review, and Region body Watertight Solid target discovery.

Tasks:

- [x] Update Build Corridor Region Boundaries review to show resolved Structure/Drainage summaries.
- [x] Update Drainage Review diagnostics to stop reading Region drainage refs.
- [x] Update quantity diagnostics that currently mention Region/Drainage handoff.
- [x] Update Watertight Solid target discovery for Region body targets to use Region+Assembly only.
- [x] Keep structure and drainage solid targets domain-owned.

Acceptance:

- [x] Region body target does not claim Structure or Drainage ownership.
- [x] Structure body target is discovered from StructureModel.
- [x] Lined ditch and drainage body targets are discovered from DrainageModel.
- [x] Review labels explain resolved context without implying Region source ownership.

Implemented notes:

- Build Corridor Region Boundaries now uses Applied Section result context for Structure and Drainage summaries instead of Region source Structure/Drainage fields.
- Drainage Review shows `Region Assignments` from Drainage Element `region_ref` values.
- Drainage Review summary/status wording now reports Drainage Element Region assignment issues, not missing Region-owned Drainage refs.
- Region-body Watertight Solid targets now keep Region/Assembly scope and do not copy Region-side Structure or Drainage fields.
- Drainage quantity diagnostics now direct users to rebuild Applied Sections after assigning Drainage Elements to Regions.
- Cross Section Viewer source ownership and editor target rows can expose DrainageModel/Drainage Element context when it is present.

Remaining:

- A shared station context resolver should replace the remaining local helpers before broader Cross Section Viewer and output expansion.

### Phase 6: Documentation And Manual QA

Tasks:

- Update Region model documentation.
- Update Drainage implementation documentation.
- Update Structure model documentation.
- Update wiki pages for Region, Structure, Drainage, Applied Sections.
- Add a manual QA sequence.

Manual QA:

1. Create Regions with Assembly only.
2. Apply Regions.
3. Create a Structure and assign it to a Region.
4. Create Drainage Elements and assign them to Regions.
5. Create a Flow Route.
6. Validate Structure and Drainage.
7. Build Applied Sections.
8. Build Corridor.
9. Confirm Build Corridor review shows resolved Structure and Drainage summaries.

### Phase 7: Shared Station Context Resolver

Status: Implemented first slice for Applied Sections.

Purpose:

Create one shared evaluation service that resolves station context from Region, Structure, and Drainage source models.

The resolver prevents each downstream stage from re-implementing slightly different rules for:

- active Region by station
- active Assembly from Region
- active Structures by `StructurePlacement.region_ref` and station span
- active Drainage Elements by `DrainageElementRow.region_ref` and station span
- active Flow Routes connected to active Drainage Elements

Tasks:

- [x] Add `StationContextResolver`.
- [x] Add a `StationContext` result contract.
- [x] Move Applied Section Structure/Drainage station lookup to the shared resolver.
- [x] Preserve existing Applied Section result fields for downstream compatibility.
- [x] Update Build Corridor Region Boundary review helpers to consume the shared resolver where source models are available.
- [x] Update Cross Section Viewer source ownership rows to use the shared resolver directly.
- [x] Update Watertight Solid target discovery diagnostics to use the shared resolver for station-context summaries where needed.
- [ ] Add Manual QA that compares Applied Sections, Build Corridor, Cross Section Viewer, and Watertight Solid context for the same station.

Acceptance:

- [x] Applied Sections no longer owns local Region+Structure+Drainage lookup rules.
- [x] Station context tests prove Region-owned Structure/Drainage refs are not required.
- [ ] Review/output stages use the same station-context source when they need live source context.

Implemented notes:

- `StationContextResolver` lives under `services/evaluation`.
- First-slice context includes Region context, Structure resolution result, active Drainage Elements, Drainage refs by side, and Flow Route refs.
- Build Corridor Region Boundaries now keep Applied Section result values as fallback while using live Station Context to summarize Structure, Drainage Element, and Flow Route source ownership when Region, Structure, and Drainage source models are present.
- Cross Section Viewer now resolves selected-station Structure, Drainage Element, and Flow Route context from the same Station Context service before building source ownership rows; persisted Applied Section refs remain fallback context.
- Watertight Solid target discovery now keeps Region body target ownership as Region+Assembly only, while adding Station Context summaries for overlapping Structure/Drainage/Flow Route context and using Station Context to choose lined-ditch Drainage owners when RegionModel and DrainageModel are available.
10. Confirm Region panel has no Structure or Drainage source controls.

Acceptance:

- User-facing docs match the active UI.
- Manual QA can complete without editing Structure or Drainage from the Region panel.

## Code Areas To Touch

Expected files:

- `freecad/Corridor_Road/v1/commands/cmd_region_editor.py`
- `freecad/Corridor_Road/v1/models/source/region_model.py`
- `freecad/Corridor_Road/v1/services/evaluation/region_resolution_service.py`
- `freecad/Corridor_Road/v1/commands/cmd_structure_editor.py`
- `freecad/Corridor_Road/v1/models/source/structure_model.py`
- `freecad/Corridor_Road/v1/services/evaluation/structure_interaction_service.py`
- `freecad/Corridor_Road/v1/commands/cmd_drainage_editor.py`
- `freecad/Corridor_Road/v1/services/evaluation/drainage_resolution_service.py`
- `freecad/Corridor_Road/v1/services/builders/applied_section_service.py`
- `freecad/Corridor_Road/v1/commands/cmd_build_corridor.py`
- `freecad/Corridor_Road/v1/services/mapping/drainage_review_mapper.py`
- `freecad/Corridor_Road/v1/services/builders/quantity_build_service.py`
- `freecad/Corridor_Road/v1/services/builders/solid_target_discovery_service.py`

Expected tests:

- `tests/contracts/v1/test_region_editor_command.py`
- `tests/contracts/v1/test_v1_region_source_object.py`
- `tests/contracts/v1/test_structure_editor_command.py`
- `tests/contracts/v1/test_v1_structure_source_object.py`
- `tests/contracts/v1/test_drainage_editor_command.py`
- `tests/contracts/v1/test_v1_drainage_source_object.py`
- `tests/contracts/v1/test_applied_sections_command.py`
- `tests/contracts/v1/test_build_corridor_command.py`
- `tests/contracts/v1/test_solid_target_discovery_service.py`

## Risk Analysis

| Risk | Impact | Mitigation |
|---|---|---|
| Applied Sections lose Structure/Drainage refs | downstream review and output regressions | implement resolver before deleting downstream context fields |
| Drainage Flow Routes span Regions | user may not know cross-boundary behavior | add explicit cross-Region diagnostic |
| Structure and Drainage both reference the same Structure ID | user confusion | rename Drainage column to `Structure Ref` and document that it is a link, not ownership |
| Region body solids omit structure/drainage context | expected behavior may change | label Region body targets as Region+Assembly only |
| Tests rely on RegionRow Structure/Drainage fields | broad test churn | update tests by phase and keep result contracts stable |

## Final Target

Region becomes a clean station-span and Assembly assignment tool.

Structure and Drainage become independent domain editors that reference Regions.

Applied Sections becomes the evaluation point where Region, Assembly, Structure, and Drainage source models are resolved into one station context.

This keeps source ownership explicit and reduces user confusion in the active v1 workflow.

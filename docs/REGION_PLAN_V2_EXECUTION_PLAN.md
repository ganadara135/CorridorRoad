<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Region Plan V2 Execution Plan

Date: 2026-04-10

## Purpose

This document turns [REGION_PLAN_V2.md](c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/REGION_PLAN_V2.md) into an execution sequence.

The target is not a small UI cleanup.
The target is a structural migration from:

1. flat runtime-row authoring
2. row-oriented `Edit Regions`
3. `Inputs/Regions` tree placement

to:

1. `Region Plan` authoring
2. `Base / Overrides / Hints` workflow
3. alignment-owned region design
4. runtime compatibility through an adapter layer

## Delivery Strategy

Do this as a staged migration, not a big-bang rewrite.

Recommended order:

1. rename and reframe the feature
2. relocate tree ownership
3. introduce `RegionPlan` root object
4. add adapter output to current runtime format
5. build grouped authoring UI
6. convert `Auto-seed` into `Hints`
7. switch section/corridor linking to `RegionPlan`
8. retire the old flat editor into advanced mode
9. remove legacy compatibility paths once `RegionPlan` is established

## Current Status

Current implementation status on 2026-04-10:

1. `PR-1` completed
2. `PR-2` completed
3. `PR-3` completed
4. `PR-4` completed
5. `PR-5` completed
6. `PR-6` completed
7. `PR-7` completed

Notes:

1. `PR-2` is complete because `RegionPlan` can now be created independently, exposes grouped mirror properties for `Base / Overrides / Hints`, stores grouped raw row bundles alongside the flat runtime lists, and validates records at the plan level.
2. `PR-4` is complete because the main authoring flow is now grouped around `Base Regions`, `Overrides`, and `Hints`, base-region split / merge actions are available, override editing uses structured controls instead of exposing raw policy strings in the common path, and the old flat runtime table survives only under `Advanced`.
3. `PR-5` is complete because project seeding now lands in the `Hints` workflow instead of silently becoming design data, hint source / status / reason are stored as explicit metadata, `Accept / Accept and Edit / Ignore` actions are available, accepted hints deterministically become overrides, and managed hint refresh does not wipe confirmed base or override rows.
4. `PR-3` is effectively complete through shared `RegionPlan` runtime methods, even though the originally proposed adapter helper names were not introduced as separate APIs.
5. `PR-7` is now complete because the active workflow and runtime use `RegionPlan` only, section/project linking resolves `RegionPlan` directly, `Advanced` stays preview-first, and the old compatibility wrapper plus migration-specific paths have been removed.

## High-Level Deliverables

Required:

1. new `RegionPlan` object model
2. new tree placement under alignment
3. grouped authoring UI
4. hint workflow
5. runtime adapter
6. compatibility with current `SectionSet` and `Corridor`
8. regression coverage

Deferred:

Deferred work is now tracked in [REGION_PLAN_V2_DEFERRED_ITEMS.md](c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/REGION_PLAN_V2_DEFERRED_ITEMS.md).

Summary:

1. no required deferred items remain

## New Target Architecture

### User-facing objects

1. `RegionPlan`
2. `BaseRegionSpan`
3. `OverrideRegionSpan`
4. `RegionHint`

### Runtime-facing objects

1. adapter output equivalent to current region records
2. current `SectionSet` station merge
3. current station-local region resolution
4. current corridor policy consumption

### Tree ownership

Old:

1. `Inputs/Regions`

New:

1. `Alignments/<Alignment>/Regions`

## PR Breakdown

### PR-1. Terminology and tree migration

Status: completed

Goal:

1. align names and tree placement with the new mental model

Tasks:

1. rename UI strings:
   - `Edit Regions` -> `Manage Region Plan`
   - `Region Integration` -> `Region Plan Integration`
2. add alignment-owned `Regions` folder in the alignment subtree
3. move region adoption from `Inputs/Regions` to alignment-owned `Regions`
4. keep backward-safe fallback adoption during transition
5. update menu text, tooltips, and status text

Primary files:

1. `freecad/Corridor_Road/commands/cmd_edit_regions.py`
2. `freecad/Corridor_Road/init_gui.py`
3. `freecad/Corridor_Road/objects/obj_project.py`
4. `freecad/Corridor_Road/objects/project_links.py`

Acceptance:

1. tree shows region design under alignment
2. no existing `Stationing`, `VerticalProfiles`, `Assembly`, `Sections`, or `Corridor` nodes are removed
3. command names and text match the new concept

### PR-2. Introduce `RegionPlan`

Status: completed

Goal:

1. create the new user-facing root object without breaking runtime

Tasks:

1. add `obj_region_plan.py`
2. define plan-level properties
3. store base spans, overrides, and hints separately
4. add validation at the plan level
5. keep flat runtime export available for section and corridor consumption

Suggested properties on `RegionPlan`:

1. `Alignment`
2. `BaseIds`
3. `BaseNames`
4. `BasePurposes`
5. `BaseStartStations`
6. `BaseEndStations`
7. `BaseTemplateRefs`
8. `BaseAssemblyRefs`
9. `BaseNotes`
10. `OverrideIds`
11. `OverrideNames`
12. `OverrideKinds`
13. `OverrideSides`
14. `OverrideStartStations`
15. `OverrideEndStations`
16. `OverrideActions`
17. `OverrideTransitionIns`
18. `OverrideTransitionOuts`
19. `OverrideNotes`
20. `HintIds`
21. `HintSourceKinds`
22. `HintSourceRefs`
23. `HintKinds`
24. `HintSides`
25. `HintStartStations`
26. `HintEndStations`
27. `HintReasons`
28. `HintConfidences`
29. `HintStatuses`
30. `Status`
31. `ValidationRows`

Primary files:

1. `freecad/Corridor_Road/objects/obj_region_plan.py`
2. `freecad/Corridor_Road/objects/doc_query.py`
3. `freecad/Corridor_Road/objects/obj_project.py`

Acceptance:

1. `RegionPlan` can be created independently
2. base/override/hint data stays separate
3. validation messages are user-readable

### PR-3. Runtime adapter

Status: completed

Goal:

1. make `RegionPlan` usable without rewriting section and corridor runtime first

Tasks:

1. add adapter helpers:
   - `region_plan_to_records(...)`
2. map base spans to base runtime rows
3. map overrides to overlay runtime rows
4. ignore non-accepted hints in runtime export
5. keep runtime export in-memory and authoring-independent

Primary files:

1. `freecad/Corridor_Road/objects/obj_region_plan.py`
2. `freecad/Corridor_Road/objects/obj_section_set.py`
3. `freecad/Corridor_Road/objects/obj_corridor.py`

Acceptance:

1. current runtime consumes Region Plan through the adapter
2. no user-facing raw policy entry is required for common workflows
3. existing region runtime smokes still pass

### PR-4. New authoring UI

Status: completed

Goal:

1. replace flat row-first authoring with grouped plan authoring

Tasks:

1. replace the current main panel with grouped sections:
   - `Base Regions`
   - `Overrides`
   - `Hints`
2. keep the old raw table under an `Advanced` expander or secondary tab
3. add dedicated add actions:
   - `Add Base Region`
   - `Add Override`
4. add split and merge operations for base spans
5. make override editing use structured controls instead of raw policy strings

Primary files:

1. `freecad/Corridor_Road/ui/task_region_editor.py`
2. new helper widgets if needed under `freecad/Corridor_Road/ui/`

Acceptance:

1. user can understand what is base vs override vs hint without reading docs
2. common editing does not expose raw `SidePolicy`, `DaylightPolicy`, `CorridorPolicy`
3. advanced mode still exists for debugging and migration

### PR-5. Hint workflow

Status: completed

Goal:

1. convert current auto-generated rows into explicit hints

Tasks:

1. replace `Auto-seed [New]` row injection with hint generation
2. route `Seed From Project` into the `Hints` panel
3. show hint source and reason
4. add actions:
   - `Accept`
   - `Accept and Edit`
   - `Ignore`
5. create real overrides only from accepted hints
6. persist hint metadata independently from free-form notes

Primary files:

1. `freecad/Corridor_Road/ui/task_region_editor.py`
2. `freecad/Corridor_Road/objects/obj_region_plan.py`
3. possibly helper logic extracted from current seed code

Acceptance:

1. project seed proposals do not silently become design data
2. accepted hints produce deterministic overrides
3. ignored hints remain traceable
4. hint source, status, and reason are stored as explicit metadata rather than note prefixes
5. `Seed From Project` refreshes managed hints without wiping confirmed base or override rows

### PR-6. Section and corridor linking

Status: completed

Goal:

1. switch linking from the old flat-region concept to `RegionPlan`

Tasks:

1. add `RegionPlan` link property to project and `SectionSet`
2. update `Generate Sections` UI to prefer `RegionPlan`
3. update `Corridor` status text and diagnostics to say `Region Plan`

Primary files:

1. `freecad/Corridor_Road/objects/obj_project.py`
2. `freecad/Corridor_Road/objects/project_links.py`
3. `freecad/Corridor_Road/objects/obj_section_set.py`
4. `freecad/Corridor_Road/ui/task_section_generator.py`
5. `freecad/Corridor_Road/objects/obj_corridor.py`
6. `freecad/Corridor_Road/ui/task_corridor_loft.py`

Acceptance:

1. new documents use `RegionPlan`
2. station merge and runtime rule resolution remain intact

### PR-7. Legacy retirement and advanced mode

Status: completed

Goal:

1. remove old compatibility paths after `RegionPlan` becomes the only active model
2. keep flat runtime inspection off the main workflow unless the user is authoring a brand-new plan

Tasks:

1. collapse project and section linking onto `RegionPlan` only
2. remove hidden legacy fallback properties from active runtime paths
3. delete the old wrapper and migration-only smoke coverage
4. keep the flat runtime table as preview/export diagnostics only

Decision:

1. migrated or existing `RegionPlan` objects stay preview-only in `Advanced`
2. direct flat-row legacy editing remains available only during `[New]` plan authoring
3. this is the intended end state for `PR-7`, not a temporary restriction

Acceptance:

1. active runtime and authoring paths resolve `RegionPlan` only
2. advanced mode is preview-first, not a second primary editor
3. main workflow stays clean

## UI Mapping Rules

### Base Regions

User fields:

1. `Name`
2. `Purpose`
3. `Start`
4. `End`
5. `Template`
6. `Assembly`
7. `Notes`

Runtime mapping:

1. `Layer = base`
2. `RegionType` from base purpose

### Overrides

User fields:

1. `Name`
2. `Kind`
3. `Applies To`
4. `Start`
5. `End`
6. `Action`
7. `Transition`
8. `Notes`

Runtime mapping examples:

1. `Kind = Ditch / Berm`, `Applies To = Left`
   -> overlay row with `RegionType = ditch_override`
   -> `SidePolicy = left:berm`
2. `Kind = Urban Edge`, `Applies To = Right`
   -> overlay row with `RegionType = retaining_wall_zone`
   -> `DaylightPolicy = right:off`
3. `Action = Split Corridor`
   -> `CorridorPolicy = split_only`
4. `Action = Skip Corridor`
   -> `CorridorPolicy = skip_zone`

### Hints

User fields:

1. `Source`
2. `Reason`
3. `Suggested Kind`
4. `Suggested Side`
5. `Suggested Span`
6. `Status`

Runtime rule:

1. only accepted hints participate in adapter output

## Tree Work Details

### Required project-tree changes

1. add alignment-owned `Regions` folder
2. resolve target container for `RegionPlan`
3. keep old `Inputs/Regions` only as a transition bucket if absolutely necessary

### Recommendation

Do not keep `Inputs/Regions` as the long-term home.
At most, keep a temporary compatibility path while migrating old docs.

## Validation Work Details

### Plan-level validation

1. base overlaps
2. base gaps
3. invalid span ordering
4. override span outside base coverage
5. duplicate hint proposals

### Adapter-level validation

1. invalid runtime action mapping
2. unsupported override kind
3. multiple accepted hints producing the same override meaning

## Regression Plan

Add or update regression coverage in this order.

### 1. Tree and linking

1. region design object is adopted under alignment
2. project links resolve `RegionPlan`

### 2. Plan authoring

1. base region creation
2. override creation
3. split and merge behavior

### 3. Hint flow

1. `TypicalSectionTemplate` -> hint generation
2. `StructureSet` -> hint generation
3. accept / ignore transitions

### 4. Adapter behavior

1. base plan to runtime rows
2. override mapping to runtime rows
3. accepted hints only

### 5. Runtime continuity

1. station merge still works
2. section rule consumption still works
3. corridor rule consumption still works

## Suggested Test Files

New or updated tests:

1. `tests/regression/smoke_region_plan_tree.py`
2. `tests/regression/smoke_region_plan_basics.py`
3. `tests/regression/smoke_region_plan_hints.py`
4. `tests/regression/smoke_region_plan_adapter.py`
5. keep current:
   - `smoke_region_station_merge.py`
   - `smoke_region_rule_consumption.py`
   - `smoke_region_corridor_policy.py`
   - `smoke_region_structure_corridor_precedence.py`
   - `smoke_region_project_seed.py`
   - `smoke_region_editor_combo_ids.py`

## File-Level Change Map

### New files

1. `freecad/Corridor_Road/objects/obj_region_plan.py`
2. optionally `freecad/Corridor_Road/ui/task_region_plan_editor.py`
3. `docs/REGION_PLAN_V2_EXECUTION_PLAN.md`

### Major modifications

1. `freecad/Corridor_Road/objects/obj_project.py`
2. `freecad/Corridor_Road/objects/project_links.py`
3. `freecad/Corridor_Road/ui/task_region_editor.py`
4. `freecad/Corridor_Road/commands/cmd_edit_regions.py`
5. `freecad/Corridor_Road/ui/task_section_generator.py`
6. `freecad/Corridor_Road/objects/obj_section_set.py`
7. `freecad/Corridor_Road/objects/obj_corridor.py`

### Removed legacy compatibility files

1. `freecad/Corridor_Road/objects/obj_region_set.py` was retired during `PR-7`

## Risks and Controls

### Risk 1. Tree migration breaks object discovery

Control:

1. keep dual-resolution during migration
2. add tree regression early

### Risk 2. New UX delays runtime stability

Control:

1. adapter first
2. keep current runtime records alive until the new model is stable

### Risk 3. Hints become another hidden state machine

Control:

1. explicit `pending / accepted / ignored`
2. visible source and reason columns

### Risk 4. Flat runtime export becomes hard to debug

Control:

1. advanced raw table remains available
2. adapter output is inspectable

## Definition of Done

This execution plan is complete when:

1. Region is authored as a plan, not a raw table
2. tree placement matches alignment design workflow
3. hints are clearly separated from confirmed regions
4. current runtime still works through an adapter
5. old data remains readable

## Recommended Immediate Next Step

Start with PR-1 and PR-2 only.

That means:

1. rename and re-tree Region
2. introduce `RegionPlan`
3. do not rebuild the whole editor and hint flow in one jump

This keeps risk manageable while still moving the design in the right direction.

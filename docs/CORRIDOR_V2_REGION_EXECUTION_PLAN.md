<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Corridor V2 + Region Execution Plan

Date: 2026-04-10

## Purpose

This document turns [CORRIDOR_V2_REGION_PLAN.md](c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/CORRIDOR_V2_REGION_PLAN.md) into an implementation sequence.

The main goals are:

1. move `CorridorLoft` runtime away from loft-centric thinking
2. make corridor connectivity follow the same section contract used by `DesignGradingSurface`
3. make `RegionPlan` a first-class corridor segmentation and policy source
4. rename the user-facing command and panel from `Corridor Loft` to `Corridor`

## Delivery Strategy

Do this as a staged migration.

Recommended order:

1. make the section-profile contract explicit
2. extract shared strip-assembly builders
3. stabilize `DesignGradingSurface` on the shared builder
4. migrate corridor runtime to segment-based strip assembly
5. integrate `RegionPlan` directly into corridor segmentation
6. rename the user-facing command and panel to `Corridor`
7. tighten diagnostics and reduce legacy loft wording
8. review whether internal `CorridorLoft` names should remain or be renamed later

## Current Status

Current status on 2026-04-10:

1. new design document exists
2. runtime already moved part of corridor surface generation toward strip-style assembly
3. `RegionPlan` already exists and is active in section/corridor workflows
4. user-facing wording still says `Corridor Loft`
5. shared `SectionProfile` / `SectionStripBuilder` architecture is not yet formalized as a clean common layer

Interpretation:

1. the project already contains useful migration work
2. the remaining work is to make the architecture explicit, stable, and easier to reason about

## High-Level Deliverables

Required:

1. explicit `SectionProfile` contract
2. shared `SectionStripBuilder`
3. `CorridorSegmentBuilder`
4. direct `RegionPlan` corridor integration
5. user-facing `Corridor` naming
6. corridor diagnostics that separate connectivity from span packaging
7. regression coverage for section-faithful corridor behavior

Deferred:

1. child-object corridor segment tree UI
2. broad internal symbol rename
3. external-shape direct boolean corridor cutting

## Working Definitions

### SectionProfile contract

One normalized section profile at one station.

Expected fields:

1. `station`
2. `points`
3. `schema_version`
4. `point_count`
5. `profile_tags`
6. station-local metadata:
   - region state
   - structure state
   - warnings

### SectionStripBuilder

Shared builder that:

1. connects adjacent profiles point-to-point
2. creates deterministic triangles per quad span
3. optionally harmonizes pair mismatches in a controlled way
4. returns either:
   - mesh facets
   - `Part.Face` collections

### CorridorSegmentBuilder

Corridor-specific orchestration that:

1. resolves final kept ranges
2. splits by region and structure boundaries
3. applies corridor policy precedence
4. assembles final segment compounds

## PR Breakdown

### PR-1. Extract explicit SectionProfile contract

Status: planned

Goal:

1. make ordered section profiles first-class runtime data

Tasks:

1. define a normalized section-profile structure in `obj_section_set.py`
2. add a shared profile export helper
3. expose section-profile diagnostics on `SectionSet`
4. stop relying on downstream wire re-reading in the normal path

Primary files:

1. `freecad/Corridor_Road/objects/obj_section_set.py`
2. `freecad/Corridor_Road/objects/obj_design_grading_surface.py`
3. `freecad/Corridor_Road/objects/obj_corridor_loft.py`

Acceptance:

1. `SectionSet` can report normalized ordered section profiles
2. downstream objects can consume profile data without re-deriving point order from wires
3. section/profile diagnostics are visible enough for debugging

Regression targets:

1. `tests/regression/smoke_typical_section_pipeline.py`
2. `tests/regression/smoke_side_slope_bench_profile.py`
3. `tests/regression/smoke_side_slope_bench_daylight.py`

### PR-2. Add shared SectionStripBuilder

Status: planned

Goal:

1. use one shared connectivity builder for grading and corridor

Tasks:

1. add a shared strip builder module or helper set
2. support:
   - mesh-facet output
   - `Part.Face` output
3. centralize:
   - pairwise point correspondence
   - degenerate triangle filtering
   - optional pair harmonization
4. make `DesignGradingSurface` consume the shared builder explicitly

Primary files:

1. `freecad/Corridor_Road/objects/obj_design_grading_surface.py`
2. `freecad/Corridor_Road/objects/obj_corridor_loft.py`
3. new shared helper under `freecad/Corridor_Road/objects/`

Acceptance:

1. `DesignGradingSurface` uses the shared strip contract
2. face/facet counts remain stable for existing regression scenarios
3. the shared builder can be used without corridor-specific logic

Regression targets:

1. `tests/regression/smoke_corridor_loft_section_strip_surface.py`
2. `tests/regression/smoke_corridor_loft_typical_bench_contract.py`
3. grading-surface smokes already covering face counts and schema

### PR-3. Introduce CorridorSegmentBuilder

Status: planned

Goal:

1. make corridor packaging explicit and segment-based

Tasks:

1. add a corridor segment resolver
2. split corridor by:
   - structure boundaries
   - region boundaries
   - skip/notch boundaries
3. call `SectionStripBuilder` per kept range
4. package final results as segment compounds
5. expose segment summary rows and diagnostics

Primary files:

1. `freecad/Corridor_Road/objects/obj_corridor_loft.py`
2. optional shared helper module for segment range resolution

Acceptance:

1. corridor output is segment-oriented rather than whole-loft-oriented
2. segment count and reasons are visible in diagnostics
3. connectivity remains section-faithful inside each kept range

Regression targets:

1. `tests/regression/smoke_region_corridor_policy.py`
2. `tests/regression/smoke_region_structure_corridor_precedence.py`
3. `tests/regression/smoke_typical_section_pipeline.py`

### PR-4. RegionPlan-first corridor integration

Status: planned

Goal:

1. make `RegionPlan` a first-class corridor segment and policy source

Tasks:

1. use resolved region rows directly in corridor segment building
2. split corridor on region boundaries
3. apply region corridor policies with deterministic precedence
4. expose region-driven segment diagnostics
5. keep structure policy precedence above region policy

Primary files:

1. `freecad/Corridor_Road/objects/obj_corridor_loft.py`
2. `freecad/Corridor_Road/objects/obj_region_plan.py`
3. `freecad/Corridor_Road/objects/obj_section_set.py`

Acceptance:

1. region boundaries appear in corridor segmentation
2. region-driven skip/split behavior is visible in status rows
3. structure vs region precedence is deterministic and testable

Regression targets:

1. `tests/regression/smoke_region_corridor_policy.py`
2. `tests/regression/smoke_region_structure_corridor_precedence.py`
3. any corridor status smoke covering region diagnostics

### PR-5. User-facing rename: Corridor Loft -> Corridor

Status: planned

Goal:

1. align user-facing naming with the new runtime direction

Tasks:

1. rename menu text:
   - `Corridor Loft` -> `Corridor`
2. rename task-panel title:
   - `CorridorRoad - Corridor Loft` -> `CorridorRoad - Corridor`
3. rename action/button text:
   - `Build Corridor Loft` -> `Build Corridor`
4. rename target labels:
   - `Target Corridor Loft` -> `Target Corridor`
5. rename default object label:
   - `Corridor Loft` -> `Corridor`
6. update wiki/help text/screenshots references where user-visible

Primary files:

1. `freecad/Corridor_Road/commands/cmd_generate_corridor_loft.py`
2. `freecad/Corridor_Road/ui/task_corridor_loft.py`
3. `freecad/Corridor_Road/init_gui.py`
4. docs/wiki pages mentioning the command name

Acceptance:

1. users see `Corridor`, not `Corridor Loft`, in normal UI flow
2. object creation and selection still work
3. screenshots/wiki wording stay consistent

Migration rule:

1. keep internal command id and file name unchanged for now if that lowers risk
2. do not mix internal symbol rename with geometry migration in the same patch

### PR-6. Diagnostics rewrite

Status: planned

Goal:

1. make corridor failures easier to classify

Tasks:

1. add diagnostics distinguishing:
   - connectivity failures
   - packaging failures
   - region policy effects
   - structure policy effects
2. report segment summaries in status/report rows
3. reduce ambiguous `loft failed` language in user-facing status
4. keep any remaining loft-centric fallback clearly marked as legacy compatibility

Primary files:

1. `freecad/Corridor_Road/objects/obj_corridor_loft.py`
2. `freecad/Corridor_Road/ui/task_corridor_loft.py`
3. docs troubleshooting pages

Acceptance:

1. user can tell whether a failure came from section connectivity or corridor packaging
2. status/report rows mention segments and active corridor policies
3. legacy fallback wording is clearly marked as compatibility-only

Regression targets:

1. corridor failure-path smokes
2. region precedence smokes
3. workflow/task-panel summary checks where available

### PR-7. Compatibility review

Status: planned

Goal:

1. decide what legacy `CorridorLoft` naming and fallback should remain internally

Tasks:

1. review whether to keep:
   - proxy type `CorridorLoft`
   - command id `CorridorRoad_GenerateCorridorLoft`
   - file names under `cmd_generate_corridor_loft.py` and `task_corridor_loft.py`
2. if internal rename is chosen, do it only after geometry/runtime stabilization
3. document retained legacy names if they remain intentionally

Primary files:

1. command/ui/object files using `CorridorLoft`
2. architecture and developer docs

Acceptance:

1. internal naming policy is explicit
2. unnecessary churn is avoided during geometry migration

## Command Rename Schedule

Recommended schedule:

### Stage A

During PR-1 through PR-4:

1. keep internal names stable
2. focus on geometry correctness and region segmentation

### Stage B

During PR-5:

1. rename all user-facing command/panel/button text to `Corridor`
2. keep internal ids and file names stable unless a low-risk alias is easy

### Stage C

During PR-7:

1. decide whether internal symbol rename is worth the churn
2. if yes, do it as a dedicated cleanup pass
3. if not, document the intentional compatibility names

## Testing Strategy

### Core geometry

1. compare corridor face counts against grading-strip expectations in controlled scenarios
2. verify bench and richer section schemas remain stable
3. verify point-count harmonization only occurs in controlled fallback cases

### Region integration

1. verify region boundaries create expected corridor split candidates
2. verify region corridor policy precedence against structure policy
3. verify status/report rows mention region-driven packaging

### User-facing rename

1. verify menu and panel titles
2. verify build button/action wording
3. verify docs and screenshots use `Corridor`

## Risks

1. mixing user-facing rename with deep geometry refactor can hide regressions
2. section-profile extraction may reveal hidden assumptions in current wire-centric code
3. region and structure precedence may become hard to debug without strong segment diagnostics
4. internal `CorridorLoft` names may continue to confuse developers if not documented clearly

## Recommended First Move

Start with:

1. PR-1 `SectionProfile` extraction
2. PR-2 shared `SectionStripBuilder`

Reason:

1. these steps create the geometric foundation
2. they reduce ambiguity before segment and region packaging are rewritten
3. they make later `Corridor` naming changes safer and easier to explain

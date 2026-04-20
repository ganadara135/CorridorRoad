<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Corridor V2 + Region Integration Plan

Date: 2026-04-10

Historical note:
This plan was written during the transition from user-facing `Corridor Loft` wording to `Corridor`.
References to `Corridor Loft` or `Corridor` in this document should be read as historical naming or internal compatibility naming unless the text explicitly discusses migration work.

## Purpose

This document defines the next corridor runtime direction:

1. keep corridor output as a range-aware `Part` shape result
2. make corridor connectivity follow the same section contract used by `DesignGradingSurface`
3. integrate `RegionPlan` as a first-class corridor segmentation and policy source
4. rename user-facing `Corridor Loft` command/title wording to `Corridor`

This is a design and execution plan, not a commit log.

## Problem Statement

The current corridor runtime still carries legacy loft-era assumptions:

1. the object is named `Corridor`
2. parts of the runtime still think in terms of profile lofting rather than deterministic section assembly
3. users expect the corridor result to follow generated sections the same way `DesignGradingSurface` does
4. region-aware corridor behavior exists, but it is not yet the center of the corridor mental model

This causes two different kinds of confusion:

1. geometric confusion
   - users see `Sections` and `DesignGradingSurface` agree, but `Corridor Loft` looks different
2. terminology confusion
   - the command title says `Loft` even though the preferred runtime direction is no longer "trust a loft engine"

## Target Outcome

The target corridor system should satisfy all of the following.

### Geometry contract

1. `SectionSet` owns the ordered section-point contract
2. `DesignGradingSurface` uses that contract directly as the reference surface
3. `Corridor` uses that same contract directly for section-to-section connectivity
4. the corridor result must not invent a second interpretation of the same section points

### Corridor packaging contract

1. corridor output must remain range-aware
2. structure and region boundaries may split corridor segments
3. `skip_zone`, `split_only`, notch-aware spans, and later corridor rules remain visible in diagnostics
4. downstream `Part`-based inspection/export remains possible

### User-facing naming contract

1. the main command/panel should say `Corridor`
2. the build action should say `Build Corridor`
3. documentation should explain that `Corridor` is a range-aware shape result
4. `Loft` may remain as an internal legacy implementation term only during migration

## Design Principles

### 1. Section connectivity is deterministic

Do not let the corridor runtime infer point correspondence from a loft engine when the section contract already exists.

### 2. Region is a corridor policy source

`RegionPlan` should affect:

1. where corridor segments start/end
2. which corridor policy is active inside each span
3. what diagnostics and segment labels should report

It should not invent a different point-to-point section connection rule.

### 3. DesignGradingSurface is the reference

When debugging connectivity:

1. if `DesignGradingSurface` is wrong, inspect `SectionSet`
2. if `DesignGradingSurface` is correct and `Corridor` is wrong, inspect corridor packaging/runtime behavior

### 4. Naming should match implementation intent

If the runtime is no longer "mainly a loft engine", user-facing command labels should not keep emphasizing `Loft`.

## Scope

This plan covers:

1. corridor runtime structure
2. region integration
3. diagnostics
4. user-facing command/title rename

This plan does not yet include:

1. direct boolean-cut earthwork from imported external solids
2. full child-object corridor segment tree authoring UI
3. a new analysis object beyond current `DesignTerrain` / `CutFillCalc`

## Object Roles

### SectionSet

Owns:

1. station list
2. ordered section profiles
3. section schema/version
4. station-local region and structure metadata

Recommended output contract:

1. `StationValues`
2. `SectionProfiles`
3. `SectionProfileSchema`
4. `SectionProfileRows`
5. station-local metadata rows for:
   - active base region
   - active overrides
   - active structure state
   - section-local warnings

### DesignGradingSurface

Role:

1. reference surface for section-faithful connectivity
2. mesh-oriented grading/review result

Builder direction:

1. use the ordered `SectionProfiles`
2. connect adjacent profiles point-to-point as strip facets
3. do not package corridor span meaning

### Corridor

Role:

1. range-aware downstream `Part` result
2. same section-to-section connectivity contract as `DesignGradingSurface`
3. additional corridor segment packaging for region/structure/notch/skip behavior

Builder direction:

1. consume the same ordered `SectionProfiles`
2. segment the corridor by structure and region rules
3. build each kept segment through deterministic section-strip assembly
4. keep final output as `Part` shape segments / compounds

## Proposed Runtime Architecture

### 1. SectionProfile contract

Introduce a shared section-profile model:

1. `station`
2. `points`
3. `schema_version`
4. optional profile tags
5. station-local region and structure state

Each profile should be treated as primary data.

Do not re-read wires later to recover point order unless entering a controlled compatibility fallback.

### 2. Shared builder: SectionStripBuilder

Add a shared builder layer used by both `DesignGradingSurface` and `Corridor`.

Responsibilities:

1. connect adjacent section profiles point-to-point
2. create two triangles per quad span
3. optionally harmonize local point-count mismatches in a controlled way
4. skip degenerate triangles
5. return:
   - mesh facets for grading
   - `Part.Face` collections for corridor

This makes `DesignGradingSurface` and `Corridor` agree on connectivity while still allowing different output packaging.

### 3. CorridorSegmentBuilder

Add a corridor-specific orchestration layer above `SectionStripBuilder`.

Responsibilities:

1. resolve active keep-ranges
2. split by structure boundaries
3. split by region boundaries
4. apply skip/split/notch corridor policy
5. call `SectionStripBuilder` for each kept range
6. package results as segment compounds

### 4. Final shape packaging

Recommended default:

1. segment result = `Part.Compound` of strip faces
2. whole corridor result = `Part.Compound` of segment compounds

Optional future layer:

1. exposed child segment objects for inspection/debug

## Region Integration

`RegionPlan` should become a first-class corridor segmentation input.

### Region affects corridor in these ways

1. boundary creation
   - region starts/ends become potential corridor split stations
2. policy activation
   - active region rows contribute corridor mode/policy
3. diagnostics
   - each segment should know which region rows contributed to it

### Region does not affect corridor in this way

1. it does not redefine section point correspondence
2. it does not create a second geometry contract separate from `SectionSet`

### Recommended precedence

1. structure corridor policy
2. region corridor policy
3. corridor default behavior

When policies conflict:

1. stronger "remove/skip" style policies win over weaker packaging policies
2. segment diagnostics should record both the chosen and overridden sources

### Recommended corridor metadata per segment

1. `SegmentId`
2. `StartStation`
3. `EndStation`
4. `SourceReason`
5. `ActiveBaseRegionIds`
6. `ActiveOverrideRegionIds`
7. `ActiveStructureIds`
8. `ResolvedCorridorMode`
9. `Warnings`

## New Corridor Data Flow

1. `SectionSet` generates station list and ordered section profiles
2. `RegionPlan` contributes boundary stations and corridor policy rows
3. `StructureSet` contributes boundary stations and structure corridor policy rows
4. `CorridorSegmentBuilder` resolves final segment ranges
5. `SectionStripBuilder` converts each kept segment into `Part` faces
6. corridor runtime packages faces into range-aware segment compounds
7. project/object diagnostics expose segment and policy summaries

## Diagnostics and Validation

The new corridor runtime should expose diagnostics that help separate:

1. section contract problems
2. region packaging problems
3. structure packaging problems
4. shape assembly failures

Recommended status/report additions:

1. `ConnectivitySource=section_profiles`
2. `SegmentCount`
3. `SegmentReasonRows`
4. `RegionSegmentCount`
5. `StructureSegmentCount`
6. `ConnectivityWarnings`
7. `PackagingWarnings`
8. `FallbackUsed`

Recommended debugging policy:

1. compare against `DesignGradingSurface`
2. if grading is correct, debug segment packaging
3. only use compatibility loft fallback as a last-resort temporary path

## Naming Plan: Corridor -> Corridor

User-facing naming should move from `Corridor Loft` to `Corridor`.

### Why rename

1. `Loft` over-emphasizes an implementation detail that is no longer the target runtime direction
2. the corridor object is broader than a loft result
3. users already think of the result as the corridor output, not as a generic loft experiment

### What should change in user-facing UI

1. menu text
   - `Corridor Loft` -> `Corridor`
2. task panel window title
   - `CorridorRoad - Corridor Loft` -> `CorridorRoad - Corridor`
3. primary action button
   - `Build Corridor Loft` -> `Build Corridor`
4. target selector labels
   - `Target Corridor Loft` -> `Target Corridor`
5. new-object label
   - `Corridor Loft` -> `Corridor`
6. wiki and screenshots
   - `Generate Corridor Loft` -> `Generate Corridor`

### What may stay internal during migration

For compatibility and code stability, the following may stay internal for one migration cycle:

1. command id `CorridorRoad_GenerateCorridor`
2. file name `cmd_generate_corridor_loft.py`
3. object proxy type `Corridor`
4. project hidden link property `Corridor`

Current decision:

1. keep all four items above for the current cycle
2. move callers to helper-based access instead of direct property-name coupling
3. revisit broad internal rename only after corridor geometry/runtime work is fully stable

### Internal rename policy

Use a staged rename:

1. user-facing wording first
2. shared runtime architecture second
3. internal symbol rename only after runtime stabilization

This avoids mixing geometry migration and broad naming churn in the same risky step.

## Execution Plan

### PR-1. Design contract and shared builders

Status: planned

Scope:

1. define `SectionProfile` contract
2. add `SectionStripBuilder`
3. move `DesignGradingSurface` to consume the shared builder explicitly

Acceptance:

1. `DesignGradingSurface` remains stable
2. shared connectivity contract is explicit in code and diagnostics

### PR-2. Corridor segment architecture

Status: planned

Scope:

1. add `CorridorSegmentBuilder`
2. replace whole-loft-centric orchestration with segment orchestration
3. keep output as `Part` shape compounds

Acceptance:

1. corridor shape is built from segment compounds
2. connectivity follows `SectionProfile` order
3. diagnostics expose segment count and reasons

### PR-3. Region-driven corridor integration

Status: planned

Scope:

1. make `RegionPlan` a first-class corridor segment source
2. split corridor at region boundaries
3. apply region corridor policies in segment packaging

Acceptance:

1. region boundaries are visible in corridor segmentation
2. region diagnostics show in corridor status/report rows
3. structure vs region precedence is deterministic

### PR-4. User-facing rename: Corridor Loft -> Corridor

Status: planned

Scope:

1. rename menu text to `Corridor`
2. rename task-panel labels and build button
3. rename wiki/workflow wording and screenshots

Acceptance:

1. normal users see `Corridor`, not `Corridor Loft`
2. old internal command ids may still work
3. docs consistently describe the object as `Corridor`

### PR-5. Compatibility tightening

Status: planned

Scope:

1. reduce or remove loft-centric fallback language from status text
2. mark any remaining `loft` fallback as legacy compatibility
3. clarify debug policy around `DesignGradingSurface` vs `Corridor`

Acceptance:

1. user-visible status is corridor-oriented, not loft-oriented
2. fallback paths are clearly marked as compatibility only

### PR-6. Internal rename review

Status: planned

Scope:

1. decide whether to keep `Corridor` as an internal proxy/type name
2. if safe, rename internal symbols in a separate low-risk pass

Acceptance:

1. either:
   - internal legacy names are intentionally retained and documented
   - or internal renames are completed with compatibility coverage

## Command Rename Schedule

Recommended schedule:

1. immediately after PR-2 is stable, complete PR-4 user-facing rename
2. do not wait for every internal symbol rename before changing user-facing wording
3. internal rename review should happen later as PR-6

Reason:

1. users are blocked by naming confusion now
2. internal symbol rename is not required to deliver a clearer UX
3. separating the two lowers migration risk

## Risks

1. mixing section-contract changes and internal renaming in one patch can hide geometry regressions
2. region/structure precedence can become hard to debug if segment diagnostics are weak
3. temporary compatibility fallbacks may mask real contract drift unless clearly reported

## Recommended First Step

Start with:

1. `SectionProfile` contract extraction
2. shared `SectionStripBuilder`
3. user-facing rename plan approval

This gives one geometry foundation and one UX direction before deeper corridor migration begins.

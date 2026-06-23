<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Corridor Structure Notch Plan

## Purpose
This document defines the next corridor-level expansion after structure-aware sections:
1. `split_only`
2. `skip_zone`
3. `notch`
4. later `boolean_cut`

The current implementation already supports:
1. `StructureSet`
2. structure-aware stations
3. structure-aware child sections and overlays
4. segmented loft at structure boundaries

What is still missing is direct corridor-shape behavior in structure zones.

## Current Baseline

Current corridor behavior:
1. corridor loft can split at structure boundaries
2. structure metadata is available from `SectionSet`
3. section overrides can constrain side slopes/daylight
4. structure solids are still reference geometry only

Current limitation:
1. the corridor solid is still built as if the structure is not a true void/cut object
2. structure zones do not yet create openings, omitted spans, or boolean cuts

## Recommended Expansion Order

Implement corridor consumption in this order:
1. `split_only`
2. `skip_zone`
3. `notch`
4. `boolean_cut`

Reason:
1. `split_only` is already the safest stabilization step
2. `skip_zone` is the lowest-risk corridor geometry change
3. `notch` is more useful visually but needs profile rules
4. `boolean_cut` is the most powerful and the least stable

## Recommended New Terms

### Corridor behavior mode
Add a corridor-consumption policy that is separate from section behavior.

Suggested values:
1. `none`
2. `split_only`
3. `skip_zone`
4. `notch`
5. `boolean_cut`

### Why separate this from `BehaviorMode`
Current `BehaviorMode` values:
1. `tag_only`
2. `section_overlay`
3. `assembly_override`

Those values answer:
1. should the structure affect sections
2. should the structure constrain daylight

They do not clearly answer:
1. should the corridor solid be omitted in the structure zone
2. should a notch/opening be created
3. should a later boolean cut be attempted

So corridor consumption should be its own explicit property.

## Proposed Data Model

### StructureSet additions
Suggested per-record fields:
1. `CorridorModes`
2. `VoidWidths`
3. `VoidHeights`
4. `VoidBottomElevations`
5. `CorridorMargins`

Meaning:
1. `CorridorModes`
   - corridor handling policy for the structure record
2. `VoidWidths`
   - transverse opening/notch width used by corridor logic
3. `VoidHeights`
   - opening/notch height used by corridor logic
4. `VoidBottomElevations`
   - optional bottom elevation for the notch/void envelope
5. `CorridorMargins`
   - extra tolerance around the structure zone for conservative corridor trimming

### Corridor additions
Suggested object properties:
1. `UseStructureCorridorModes`
2. `DefaultStructureCorridorMode`
3. `SkipZoneCaps`
4. `NotchTransitionScale`
5. `BooleanCutEnabled`
6. `ResolvedStructureCorridorRanges`
7. `ResolvedStructureNotchCount`

Meaning:
1. `UseStructureCorridorModes`
   - lets `Corridor` consume structure corridor policy from `StructureSet`
2. `DefaultStructureCorridorMode`
   - fallback when a record has no corridor mode
3. `SkipZoneCaps`
   - optional end-cap creation for omitted corridor spans
4. `NotchTransitionScale`
   - controls how quickly notch depth/width ramps near structure start/end
5. `BooleanCutEnabled`
   - reserved explicit switch for later boolean cut stage

## Corridor Mode Semantics

### 1. `none`
Behavior:
1. do not change corridor geometry
2. structure still participates in sections if enabled there

Use when:
1. the structure is informational only
2. the team wants section tagging before corridor-level changes

### 2. `split_only`
Behavior:
1. split loft at structure boundaries
2. keep corridor solid continuous
3. do not omit any span

Use when:
1. loft stability is the main goal
2. structure-aware geometry cutting is not ready yet

This is the current baseline.

### 3. `skip_zone`
Behavior:
1. split the corridor at structure start/end
2. do not loft the structure-active station span
3. return a compound of the pre-structure and post-structure corridor solids

Effect:
1. the corridor contains a clean gap where the structure zone exists
2. useful for crossings, culverts, or bridge openings when the corridor should not occupy that zone

Advantages:
1. stable
2. simple
3. easy to understand in the tree and status output

Risks:
1. visible open gap may need separate cap handling
2. not suitable if users expect a recessed notch instead of a full omission

### 4. `notch`
Behavior:
1. corridor remains present through the structure zone
2. section profiles are modified to create an internal recess/opening
3. the loft is built from those notch-aware closed profiles

Effect:
1. more realistic than `skip_zone`
2. especially useful for culvert or buried crossing cases

Advantages:
1. one continuous corridor result
2. no hard gap in the main corridor object

Risks:
1. profile point contract becomes more complex
2. notch topology must stay stable across all neighboring sections
3. retaining-wall and bridge-zone use cases need different notch logic

### 5. `boolean_cut`
Behavior:
1. build corridor normally
2. build structure solid or void solid
3. subtract using Part boolean cut

Advantages:
1. most flexible
2. can support very detailed structure geometry later

Risks:
1. highest chance of topological failure
2. very sensitive to invalid or near-coplanar geometry
3. expensive to compute

Recommendation:
1. keep this for a later opt-in mode only
2. start `boolean_cut` only after notch regression is stable across standalone and mixed corridor-mode cases
3. keep `boolean_cut` status/result tokens separate from notch schema reporting
4. do not extend notch-specific profile schema to simulate imported-solid subtraction

### Handoff boundary from `notch` to `boolean_cut`
Treat the work as `boolean_cut` and not a notch extension when any of the following becomes necessary:
1. the void/cut shape must come from a true 3D solid rather than the closed-profile notch schema
2. imported or external structure geometry is expected to participate directly in corridor subtraction
3. status output would need to imply solid boolean consumption instead of section-schema-based recession
4. failure handling must distinguish boolean-topology errors from notch profile/segmentation errors

## Recommended First Implementation: `skip_zone`

This should be the next actual coding step.

### Why `skip_zone` first
1. it uses the current segmented loft architecture naturally
2. it does not require changing section point count contracts
3. it provides immediate visible corridor-level structure handling

### Skip-zone algorithm
1. resolve active structure spans from `StructureSet`
2. classify each span whose corridor mode is `skip_zone`
3. derive section index ranges outside active skip zones
4. loft only those outside ranges
5. combine the surviving solids into one compound

### Station/range rules
1. use structure `StartStation` and `EndStation` as the primary skip envelope
2. allow `CorridorMargins` to expand that envelope
3. keep split stations shared across neighboring kept ranges
4. if a skip zone fully covers all sections, fail with a clear message

### Status/reporting
Suggested status additions:
1. `skipZones=<n>`
2. `skippedRanges=<n>`
3. `corridorMode=skip_zone`

Suggested result properties:
1. `ResolvedStructureCorridorRanges`
2. `ResolvedSkippedStationRanges`

## Recommended Second Implementation: `notch`

This should come after `skip_zone` is stable.

### Notch design principle
Do not try to boolean-cut the corridor first.
Instead, generate a stable notch directly in the closed section profiles used for lofting.

### Suitable first target
1. `culvert`
2. `crossing`

### Notch profile contract
To remain loft-safe, notch-aware sections should all share a single explicit schema.

Recommended notch schema:
1. outer left top
2. carriage left edge
3. notch left top
4. notch left bottom
5. notch right bottom
6. notch right top
7. carriage right edge
8. outer right top

Implication:
1. this should be a separate schema version, not a hidden mutation of the current profile

Suggested approach:
1. keep current schema for `none`, `split_only`, `skip_zone`
2. add a new section schema only when `notch` is enabled for at least one active structure

### Notch parameters
Recommended inputs:
1. `VoidWidth`
2. `VoidHeight`
3. `VoidBottomElevation`
4. `NotchTransitionScale`

Recommended defaults:
1. if `VoidWidth` is missing, fall back to structure `Width`
2. if `VoidHeight` is missing, fall back to structure `Height`
3. if `VoidBottomElevation` is missing, derive from `BottomElevation`, then `Cover`, then centerline Z

### Transition behavior
Near structure boundaries:
1. notch depth and width should ramp in gradually
2. transition stations are the natural control points for this ramp

Recommended default:
1. zero notch at `transition_before`
2. partial notch at `start`
3. full notch inside the active zone
4. partial notch at `end`
5. zero notch at `transition_after`

This keeps the profile contract stable while avoiding abrupt openings.

## Retaining Wall Behavior

`retaining_wall` should not use the same notch logic as `culvert`.

Recommended corridor behavior:
1. default to `split_only` or `none`
2. optionally support `skip_zone` later for wall gap use cases
3. do not make it a notch target in the first notch sprint

Reason:
1. retaining walls are side constraints, not usually internal corridor voids

## Bridge / Abutment Behavior

`bridge_zone` and `abutment_zone` should default conservatively.

Recommended defaults:
1. `bridge_zone` -> `skip_zone`
2. `abutment_zone` -> `split_only` or `skip_zone`

Reason:
1. a bridge-related structure zone often means the ground/corridor body should not remain as one uninterrupted prism

## Implementation Sequence

### Sprint A: corridor mode plumbing
1. add corridor-mode fields to `StructureSet`
2. add corridor-mode fields to `Edit Structures`
3. add `Corridor` properties for structure corridor consumption
4. resolve station spans by corridor mode

### Sprint B: `skip_zone`
1. classify skip spans
2. build keep-ranges outside the spans
3. loft only the keep-ranges
4. report skipped ranges in status/result properties

### Sprint C: notch schema
1. introduce a new notch-aware section schema version
2. generate notch-ready closed profiles
3. use structure transition stations to ramp the notch
4. restrict first implementation to `culvert` and `crossing`

### Sprint D: boolean-cut prototype
1. opt-in only
2. use simple structure solids first
3. fail gracefully back to `skip_zone` if boolean cut fails

## File-Level Impact

Main files expected to change:
1. `freecad/Corridor_Road/objects/obj_structure_set.py`
2. `freecad/Corridor_Road/ui/task_structure_editor.py`
3. `freecad/Corridor_Road/objects/obj_section_set.py`
4. `freecad/Corridor_Road/objects/obj_corridor.py`
5. `freecad/Corridor_Road/ui/task_corridor_loft.py`

Docs expected to change:
1. `docs/STRUCTURE_SECTION_PLAN.md`
2. `docs/STRUCTURE_SECTION_EXECUTION_PLAN.md`
3. `docs/wiki/Menu-Reference.md`
4. `docs/wiki/Workflow.md`
5. `docs/wiki/Troubleshooting.md`

## Acceptance Criteria

### For `skip_zone`
1. corridor solid is omitted across structure-active spans whose corridor mode is `skip_zone`
2. kept spans remain loft-stable
3. start/end boundaries are readable in status output
4. existing non-structure corridor workflows remain unchanged

### For `notch`
1. notch-aware corridor sections keep a stable schema across all contributing stations
2. notch ramps are controlled by transition stations
3. `culvert` and `crossing` become visibly corridor-aware without boolean operations

## Recommendation

The next coding target should be:
1. `skip_zone`

Not:
1. immediate boolean cut

That gives the project a true corridor-level structure response with much lower geometry risk, and it fits the current segmented loft architecture naturally.

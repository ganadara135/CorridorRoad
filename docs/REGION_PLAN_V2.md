<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Region Plan V2

Date: 2026-04-10

## Purpose

This document replaces the earlier Region / Station planning notes.

The old approach treated Region authoring mainly as:

1. a flat row editor
2. a station-span rule table
3. a low-level policy entry point

That approach was implementable, but it is not the right long-term user experience.
From the user point of view, `Region` should feel like an alignment design plan, not like a raw runtime table.

This document redefines Region around:

1. user workflow
2. tree placement
3. object model
4. UI mental model
5. compatibility with current `SectionSet` and `Corridor`

## Problem Statement

The current Region workflow causes confusion because several concerns are mixed into one table:

1. span definition
2. design meaning
3. override semantics
4. corridor behavior
5. hint vs confirmed design data

The user currently has to understand all of the following at once:

1. `Layer = base / overlay`
2. `RegionType`
3. `Priority`
4. `SidePolicy`
5. `DaylightPolicy`
6. `CorridorPolicy`
7. `Enabled`

This is too much internal machinery exposed too early.

The result is:

1. Region authoring feels technical instead of visual
2. `Auto-seed` looks like final data even though it is often only a proposal
3. `Inputs > Regions` makes Region look like imported source data rather than alignment design intent
4. users cannot easily tell which regions are the main corridor plan and which are local exceptions

## Design Principles

Region V2 should follow these principles.

### 1. Region is an alignment design plan

Region is not a generic input table.
It is a design layer attached to one alignment.

### 2. Base and Override are different concepts

Users should not think of them as just two values in one column.

Instead:

1. `Base Regions` define the main corridor regime
2. `Overrides` define local exceptions
3. `Hints` are proposals generated from other project data

### 3. Hints are not design until accepted

`Auto-seed` output should not silently become equivalent to confirmed authoring.

Hints must be clearly separated from authored data.

### 4. Runtime serialization should be downstream

The user-facing model should be simple and explicit.
The low-level row structure consumed by current runtime can remain as an adapter target.

### 5. Tree placement must match user mental model

`Region` belongs with alignment design objects like:

1. `Stationing`
2. `VerticalProfiles`
3. `Assembly`
4. `Sections`
5. `Corridor`

It should not primarily live under generic inputs.

## Region and Station Relationship

This part remains valid from the previous design and should be preserved.

### Station

`Station` is the evaluation position.

Use it for:

1. section generation
2. corridor sampling
3. diagnostics
4. viewer navigation

### Region

`Region` is a continuous span that owns design meaning.

Use it for:

1. base corridor regime
2. local section overrides
3. local corridor overrides
4. design intent around structures and roadside conditions

### Rule

`Region` remains span-based.
`Station` remains sample-based.

The change in V2 is not the underlying semantics.
The change is how users author and understand the data.

## Recommended Tree Structure

### Current tree impression

Current project placement makes Region appear like an input source:

1. `01_Inputs`
2. `Terrains`
3. `Survey`
4. `Structures`
5. `Regions`
6. `02_Alignments`
7. `<Alignment>`
8. `Horizontal`
9. `Stationing`
10. `VerticalProfiles`
11. `Assembly`
12. `Sections`
13. `Structure Sections`
14. `Corridor`

This is the wrong mental model for most users.

### Recommended tree

Keep `Stationing`, `VerticalProfiles`, `Assembly`, `Sections`, and `Corridor`.
Only move Region into the alignment design context.

Recommended structure:

1. `01_Inputs`
2. `Terrains`
3. `Survey`
4. `Structures`
5. `02_Alignments`
6. `<Alignment>`
7. `Horizontal`
8. `Stationing`
9. `VerticalProfiles`
10. `Assembly`
11. `Regions`
12. `Sections`
13. `Structure Sections`
14. `Corridor`

Inside `Regions`, use:

1. `Region Plan`
2. `Base Regions`
3. `Overrides`
4. `Hints`

### Why this is better

This matches the actual design flow:

1. make or select an alignment
2. define stationing
3. define vertical design
4. define assembly / typical section behavior
5. define where those rules change along the alignment
6. generate sections and corridor

## User-Facing Region Model

The user-facing model should no longer be a single flat runtime row table.

### 1. Region Plan

`Region Plan` is the root design object for one alignment.

It owns:

1. one base plan
2. zero or more overrides
3. zero or more hints

### 2. Base Region

Base Regions represent the primary corridor design spans.

Examples:

1. roadway
2. widening
3. bridge approach
4. earthwork zone

Rules:

1. base regions are contiguous or nearly contiguous
2. base regions normally do not overlap
3. each station should resolve to one base region

### 3. Override Region

Overrides represent local design exceptions.

Examples:

1. ditch / berm override
2. urban edge override
3. structure influence override
4. corridor split zone
5. corridor skip zone

Rules:

1. overrides may overlap
2. overrides are local
3. overrides should be understandable without reading raw policy strings

### 4. Hint

Hints are generated proposals from:

1. `TypicalSectionTemplate`
2. `StructureSet`
3. future roadside or standards logic

Each hint should have a status:

1. `pending`
2. `accepted`
3. `ignored`

Pending hints should not be treated as design data.

## Replace Raw Policy Strings With User Actions

The current editor exposes low-level policy fields directly.
That should become an advanced or diagnostic view, not the main editing surface.

### Current low-level fields

1. `SidePolicy`
2. `DaylightPolicy`
3. `CorridorPolicy`
4. `Priority`
5. `RuleSet`

### Recommended user-facing fields

For Base Regions:

1. `Name`
2. `Purpose`
3. `Start`
4. `End`
5. `Template`
6. `Assembly`
7. `Notes`

For Override Regions:

1. `Name`
2. `Kind`
3. `Applies To`
4. `Left / Right / Both`
5. `Start`
6. `End`
7. `Action`
8. `Transition`
9. `Notes`

For Hints:

1. `Source`
2. `Suggested Kind`
3. `Suggested Span`
4. `Reason`
5. `Confidence`
6. `Accept`
7. `Ignore`

### Mapping examples

Instead of showing:

1. `SidePolicy = left:berm`

Show:

1. `Kind = Ditch / Berm`
2. `Applies To = Left`

Instead of showing:

1. `DaylightPolicy = right:off`

Show:

1. `Kind = Urban Edge`
2. `Suppress Daylight = Right`

Instead of showing:

1. `CorridorPolicy = skip_zone`

Show:

1. `Action = Skip Corridor`

## RegionType Redesign

`RegionType` currently mixes:

1. semantic classification
2. runtime origin
3. structure-domain naming

That should be split.

### Recommended split

#### Base purpose

1. `Roadway`
2. `Widening`
3. `Bridge Approach`
4. `Earthwork`
5. `Other`

#### Override kind

1. `Ditch / Berm`
2. `Urban Edge`
3. `Structure Influence`
4. `Corridor Split`
5. `Corridor Skip`
6. `Other`

#### Hint source

1. `Typical Section`
2. `Structure Set`
3. `Manual`
4. `Future Rule Engine`

### Recommendation

Do not make users choose from low-level values like:

1. `ditch_override`
2. `retaining_wall_zone`
3. `culvert`
4. `bridge_zone`

in the main authoring UI.

Those can remain internal or advanced values.

## Proposed UI

The main Region UI should become plan-first, not row-first.

### Main layout

1. top: station timeline
2. left: region list grouped by `Base`, `Overrides`, `Hints`
3. right: selected item properties
4. bottom: validation and runtime preview summary

### Timeline

The timeline should let users:

1. split base regions
2. merge adjacent base regions
3. drag boundaries
4. place local overrides visually

This is much more intuitive than entering all spans in a grid first.

### Base Regions panel

Show:

1. ordered spans
2. coverage gaps
3. overlap warnings

### Overrides panel

Show:

1. local items
2. side and action badges
3. whether each override affects section, corridor, or both

### Hints panel

Show:

1. source
2. reason
3. proposed span
4. one-click `Accept`
5. one-click `Ignore`

### Advanced view

Keep the existing flat row table concept only as:

1. `Advanced Table`
2. `Bulk Edit`
3. `Debug / Import`

It should not be the primary user workflow.

## Auto-seed Redesign

### Current problem

The current auto-seed behavior inserts rows into the main data immediately.
Some are disabled, but they still look like real region records.

This makes it unclear whether a row is:

1. authored
2. imported
3. suggested

### Recommended behavior

`Auto-seed` should populate `Hints`, not the authored region list.

#### Example from Typical Section

Detected:

1. `ditch_edge:left`
2. `urban_edge:right`

Create hints:

1. `Create Ditch / Berm Override on Left`
2. `Create Urban Edge Override on Right`

#### Example from StructureSet

Detected:

1. culvert span `20 ~ 30`

Create hint:

1. `Create Structure Influence Override 20 ~ 30`

### User decision

The user can:

1. accept as-is
2. accept and edit
3. ignore

Only accepted hints become real overrides.

## Runtime Strategy

We already have working code that consumes flat runtime region records.
That runtime does not need to be thrown away immediately.

### Recommended architecture

1. new user-facing `RegionPlan` model
2. adapter layer that converts `RegionPlan` into current flat runtime records
3. current `SectionSet` and `Corridor` keep consuming the adapted runtime form during transition

### Why use an adapter

This gives:

1. lower migration risk
2. cleaner separation between authoring and runtime
3. a path to improve UX without blocking runtime progress

## Runtime Compatibility

### Existing `SectionSet` and `Corridor`

Keep the current runtime contract until Region Plan V2 is stable.

That means:

1. `SectionSet` still resolves station-local region context
2. `Corridor` still consumes resolved region corridor policy
3. the source of those rows changes from direct authoring to adapter output

## Recommended Data Model

### User-facing objects

#### `RegionPlan`

Fields:

1. `Alignment`
2. `BaseRegions`
3. `OverrideRegions`
4. `RegionHints`
5. `Status`
6. `ValidationRows`

#### `BaseRegionSpan`

Fields:

1. `Name`
2. `Purpose`
3. `StartStation`
4. `EndStation`
5. `TemplateRef`
6. `AssemblyRef`
7. `Notes`

#### `OverrideRegionSpan`

Fields:

1. `Name`
2. `Kind`
3. `SideScope`
4. `StartStation`
5. `EndStation`
6. `Action`
7. `TransitionIn`
8. `TransitionOut`
9. `Notes`

#### `RegionHint`

Fields:

1. `SourceKind`
2. `SourceRef`
3. `SuggestedKind`
4. `SuggestedSideScope`
5. `StartStation`
6. `EndStation`
7. `Reason`
8. `Confidence`
9. `Status`

### Runtime adapter output

The adapter may still emit fields equivalent to:

1. `Id`
2. `RegionType`
3. `Layer`
4. `StartStation`
5. `EndStation`
6. `Priority`
7. `TransitionIn`
8. `TransitionOut`
9. `TemplateName`
10. `AssemblyName`
11. `RuleSet`
12. `SidePolicy`
13. `DaylightPolicy`
14. `CorridorPolicy`
15. `Enabled`
16. `Notes`

These should become serialization detail, not the primary authoring model.

## Validation Model

Validation should also be expressed in user language.

### Base validation

1. base regions overlap
2. base region coverage has gaps
3. start station is greater than end station

### Override validation

1. override span is invalid
2. override conflicts with another override on the same side and action
3. override does not intersect any base region

### Hint validation

1. hint overlaps an existing confirmed override
2. hint duplicates an already accepted hint
3. hint source is stale

## Migration Plan

### Phase 1. Documentation and naming reset

1. replace old Region / Station documents with this document
2. rename the mental model from `Edit Regions` to `Manage Region Plan`
3. align all future work with `Base / Overrides / Hints`

### Phase 2. Tree relocation

1. move Region ownership from `Inputs/Regions` to `Alignment/Regions`
2. keep compatibility aliases if needed during migration

### Phase 3. New RegionPlan object

1. create a new `RegionPlan` root object
2. keep flat runtime export as an internal adapter target

### Phase 4. New authoring UI

1. build plan-first editor
2. keep the old table as advanced mode

### Phase 5. Hint workflow

1. move current `Auto-seed` into hint generation
2. add `Accept` and `Ignore`

### Phase 6. Runtime adapter

1. emit the current flat records from the new model
2. keep `SectionSet` and `Corridor` working

### Phase 7. Runtime cleanup

1. gradually remove direct user dependence on the old flat runtime table
2. make advanced mode preview-first

## Immediate Recommendations For Code Work

The next code changes should follow this order.

### 1. Change terminology

1. `Edit Regions` -> `Manage Region Plan`
2. flat runtime row labels in the UI should stop being the primary user concept

### 2. Move tree ownership

1. remove region authoring from `Inputs/Regions`
2. place region design objects under the owning alignment

### 3. Split current editor into grouped sections

Before building the full timeline UI, introduce three visible groups:

1. `Base Regions`
2. `Overrides`
3. `Hints`

### 4. Convert Auto-seed rows into hints

1. stop inserting disabled override rows directly into the main list
2. show them as proposals

### 5. Add runtime adapter

1. continue using current flat record runtime internally
2. generate those records from the new user-facing model

## Definition of Done

Region V2 is complete when:

1. users see Region as an alignment design plan, not an input table
2. the tree places Region alongside alignment design objects
3. users author base spans and local overrides separately
4. `Auto-seed` generates hints, not ambiguous disabled rows
5. `SectionSet` and `Corridor` still consume resolved station-local region behavior reliably
6. runtime export remains reliable and inspectable

## Summary

The key shift is this:

1. old model: flat runtime rule table
2. new model: `Region Plan` as a user-facing alignment design layer

And within that plan:

1. `Base Regions` are the main corridor definition
2. `Overrides` are local exceptions
3. `Hints` are auto-generated proposals

This is the recommended foundation for all future Region work.

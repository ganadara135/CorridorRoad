# Cross Section Component Scope Plan

Date: 2026-04-02

## Progress

- `Phase 1. Contract extension`: completed
- `Phase 2. Viewer input normalization`: completed
- `Phase 3. Scope-aware label policy`: completed
- `Phase 4. Daylight semantics`: completed
- `Phase 5. Cut / Fill slope distinction`: completed

## Goal

Make `Cross Section Viewer` show both:

- `Typical Section Components`
- `Side Slope Components`

in the same station view, while keeping their roles clear and avoiding the current ambiguity where all segments are treated as if they were the same kind of component.

The target user experience is:

1. Roadway-related components from `Typical Section` are shown with their actual `type` names.
2. Side-slope/bench/daylight-related parts created by `Sections` are also shown.
3. The viewer clearly distinguishes between:
   - designed standard-section components
   - terrain-connection / earthwork-side components
4. If a component contract is missing, the viewer should avoid inventing misleading labels.

## Current State

### 1. Typical Section path

`TypicalSectionTemplate` serializes enabled rows into `SectionComponentSummaryRows`.

Each row carries at least:

- `id`
- `type`
- `side`
- `width`
- `order`

Then `SectionSet` converts those summary rows into station-specific `SectionComponentSegmentRows`.

This is the current source-of-truth path for viewer-friendly segment rendering.

### 2. Sections / Assembly path

When `UseTypicalSectionTemplate` is off, `SectionSet` builds fallback station-specific segment rows from `AssemblyTemplate`.

These currently represent:

- `carriageway`
- `side_slope`
- `bench`

This is useful, but it is still too coarse and mixes roadway and earthwork semantics.

### 3. Viewer path

`Cross Section Viewer` currently reads station-local `component_segment` rows and renders:

- component guide lines
- component labels
- component width values

However, the viewer still needs a clearer distinction between:

- `Typical Section components`
- `Side Slope / Daylight components`

## Design Principle

The viewer should render two conceptual groups:

1. `Typical Section Components`
   - lane
   - shoulder
   - median
   - curb
   - sidewalk
   - bike_lane
   - ditch
   - berm
   - green_strip

2. `Side Slope Components`
   - cut_slope
   - fill_slope
   - bench
   - daylight

Important distinction:

- `Typical Section` ends at the designed outer edge of the standard section.
- `Side Slope` begins after that edge.
- `Daylight` is the terrain-intersection end point of the side slope.

So the viewer should not treat all outward geometry as one flat “component” category.

## Proposed Contract

Add explicit component-scope metadata to station-specific rows.

Each station-level row should support:

- `station`
- `side`
- `id`
- `type`
- `label`
- `scope`
- `source`
- `order`
- `x0`
- `x1`
- `width`

Where:

- `scope=typical`
  means the segment comes from `TypicalSectionTemplate`
- `scope=side_slope`
  means the segment belongs to slope/bench/daylight interpretation

Recommended examples:

- `lane`, `shoulder`, `ditch`, `berm` -> `scope=typical`
- `side_slope`, `cut_slope`, `fill_slope`, `bench`, `daylight` -> `scope=side_slope`

## Label Rules

### Typical Section Components

Use actual `Typical Section type` names whenever available.

Examples:

- `lane`
- `shoulder`
- `ditch`
- `berm`
- `green_strip`

These labels should not be renamed to generic viewer-only names such as `roadway` or `roadside`.

### Side Slope Components

Use slope-specific names only for geometry that is actually outside the standard section.

Examples:

- `side_slope`
- `bench`
- `daylight`

Later refinement:

- split `side_slope` into:
  - `cut_slope`
  - `fill_slope`

once the section generator exposes that distinction reliably.

## Viewer Rendering Rules

### 1. Separate scope-aware styling

The viewer should style the two groups differently.

- `Typical Section Components`
  - primary guide set
  - stronger label priority
  - always preferred when overlap happens

- `Side Slope Components`
  - secondary guide set
  - slightly lower label priority
  - can fall back to summary sooner

### 2. Scope-aware ordering

Recommended render order:

1. section polyline
2. component guides
3. typical component labels
4. side-slope component labels
5. dimensions
6. summary/diagnostic text

### 3. Scope-aware suppression

If the station is crowded:

- keep `Typical Section` labels first
- suppress low-priority side-slope labels first
- keep `bench` only when space allows or when explicitly enabled later
- keep `daylight` as note/summary if a full in-graphic label does not fit

## Implementation Plan

### Phase 1. Contract extension

Extend `SectionComponentSegmentRows` generation to include `scope`.

Tasks:

1. Add `scope=typical` in `_component_segment_rows_from_summary_rows(...)`
2. Add `scope=side_slope` in `_component_segment_rows_from_assembly(...)`
3. Preserve `source`
4. Keep backward compatibility for rows that do not yet include `scope`

Done when:

- station-level component rows always include `scope`
- old documents still load safely

### Phase 2. Viewer input normalization

Update `Cross Section Viewer` payload handling so each segment is normalized with:

- `type`
- `label`
- `scope`
- `source`

Tasks:

1. Normalize missing `scope`
2. Prefer explicit `label`
3. Fall back to `type`
4. Never invent generic labels if no valid component data exists

Done when:

- `Typical Section` stations show real type names
- non-typical stations do not invent misleading pseudo-typical labels

### Phase 3. Scope-aware label policy

Apply separate display rules for the two scopes.

Tasks:

1. Add scope-aware label priority
2. Add scope-aware guide color/style
3. Keep `Typical Section` labels before side-slope labels
4. Suppress low-priority side-slope labels first in crowded cases

Done when:

- crowded sections remain readable
- `Typical Section` and `Side Slope` are both visible when space allows

### Phase 4. Daylight semantics

Introduce explicit daylight representation.

Tasks:

1. Add a station-level `daylight` marker row or pseudo-segment
2. Keep it distinct from `side_slope`
3. Render it as:
   - point/marker
   - short label
   - or summary fallback

Done when:

- users can tell where the side slope ends and terrain connection occurs

### Phase 5. Cut / Fill slope distinction

Optionally split side slopes into `cut_slope` and `fill_slope`.

Tasks:

1. Determine cut/fill side from daylight solution
2. Store `type=cut_slope` or `type=fill_slope`
3. Reflect this in viewer labels and optional color policy

Done when:

- the viewer distinguishes excavation vs embankment slope semantics

## Regression Plan

Add or update tests for:

1. `Typical Section` station payload includes `scope=typical`
2. assembly-based station payload includes `scope=side_slope`
3. viewer uses actual `type` labels for typical components
4. viewer does not invent generic labels when no valid component data exists
5. crowded station keeps typical labels before side-slope labels

## Success Criteria

This work is successful when:

1. A `Typical Section`-driven station shows real component names from the template.
2. A side-slope/bench station shows slope-related components distinctly.
3. The viewer can show both scopes in one station without collapsing them into generic labels.
4. Missing component contracts no longer cause misleading fallback labels.

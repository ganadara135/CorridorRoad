# CorridorRoad V1 3D Review Display Plan

Date: 2026-04-22
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_VIEWER_PLAN.md`
- `docsV1/V1_SECTION_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines how v1 should use the FreeCAD 3D view for review-oriented overlays.

It exists to clarify:

- which 3D review displays are needed
- what each display type is for
- what payloads they consume
- how they connect to Cross Section Viewer
- what interaction is allowed
- what performance limits must be respected

## 2. Core Direction

3D review displays in v1 are read-only review overlays.

They exist to help users understand corridor behavior in spatial context.

They do not exist to provide direct editing of generated geometry.

## 3. Product Role

The 3D review system should help users answer questions like:

- Where is the alignment relative to terrain, structures, and region changes?
- What does the current section look like in corridor context?
- Where do key section changes happen along the corridor?
- Where do earthwork or daylight conditions become problematic?
- How does the current viewer station relate to the 3D model?

## 4. Display Priority

Recommended implementation priority:

1. current cross section in 3D
2. plan-related overlays
3. sparse full-cross-section display
4. profile-related overlays
5. earthwork-balance highlighting extensions

## 5. Core Rule

All 3D review displays must remain derived from v1 source/result/output contracts.

They must not become:

- geometry edit surfaces
- hidden authoring layers
- isolated display systems with their own engineering logic

## 6. Main Display Families

Recommended 3D review families:

- `PlanOverlay3D`
- `ProfileOverlay3D`
- `CurrentSectionOverlay3D`
- `SectionSeriesOverlay3D`
- `EarthworkOverlay3D`

## 7. Plan Overlay 3D

### 7.1 Role

Plan overlays provide topological and corridor-context review in model space.

### 7.2 Typical content

- horizontal alignment
- station markers
- region extents
- structure markers or footprints
- TIN boundaries
- breaklines

### 7.3 Main use cases

- verify alignment location
- understand region changes
- inspect structure context
- review terrain coverage and breakline context

## 8. Profile Overlay 3D

### 8.1 Role

Profile overlays provide lightweight longitudinal context inside the 3D view.

### 8.2 Typical content

- EG trace
- FG trace
- PVI markers
- optional grade-transition markers

### 8.3 Rule

Profile overlay in 3D is a contextual aid, not a replacement for a dedicated profile view.

## 9. Current Section Overlay 3D

### 9.1 Role

This is the highest-priority 3D review display.

It should visually connect the active viewer station to the actual 3D corridor environment.

### 9.2 Typical content

- section plane
- applied section wire
- component-colored section spans
- terrain intersection markers
- structure interaction markers

### 9.3 Main use cases

- inspect one station in context
- validate what Cross Section Viewer is showing
- understand terrain and structure interaction at the active section

## 10. Section Series Overlay 3D

### 10.1 Role

This display shows multiple sections across the corridor.

It is useful for reviewing broader behavior but must remain sparse and controlled.

### 10.2 Typical content

- fence-style section slices
- key-station curtains
- section sticks or frames
- region-boundary section markers

### 10.3 Required controls

- regular interval mode
- key-station-only mode
- region-boundary-only mode
- event-only mode
- current-range mode such as `current +/- N`

## 11. Earthwork Overlay 3D

### 11.1 Role

Earthwork-related 3D overlays should visually connect local geometry to balance conditions.

### 11.2 Typical content

- surplus/deficit range coloring
- borrow/waste candidate markers
- mass-haul-related highlight ranges
- daylight problem ranges

### 11.3 Rule

This overlay should extend review behavior, not replace the dedicated Earthwork Balance workflow.

## 12. Payload Sources

3D review displays should consume normalized payloads instead of re-reading raw source objects ad hoc.

Recommended inputs:

- `PlanOutput`
- `ProfileOutput`
- `SectionOutput`
- `SectionSheetOutput` selection subsets where useful
- earthwork-balance output families
- ownership and diagnostic mappings where selection support exists

## 13. Relationship to Cross Section Viewer

The 3D review system and Cross Section Viewer should behave as connected review surfaces.

Recommended interactions:

- selecting a station in the viewer highlights the current 3D section
- selecting a section-related overlay in 3D can open or focus the viewer at that station
- both systems share station identity and source ownership context

## 14. Selection Model

### 14.1 Allowed selection targets

Recommended selectable overlay targets:

- current section wire
- section series slice
- terrain-intersection marker
- structure-interaction marker
- earthwork problem marker

### 14.2 Selection purpose

Selection is allowed for:

- inspection
- viewer synchronization
- source tracing
- review highlighting

Selection is not allowed for:

- direct geometry editing

## 15. Interaction Rules

Allowed interactions:

- show or hide overlays
- change overlay density
- highlight selected stations
- navigate from 3D to viewer
- navigate from viewer to 3D

Not allowed:

- dragging section geometry as an engineering edit
- editing plan/profile/section overlays as source truth

## 16. Visual Language

The 3D review system should use a clear visual language.

Recommended distinctions:

- alignment overlays: stable reference color
- current section: strongest highlight
- section series: lighter and sparser style
- terrain interaction: distinct warning/interaction style
- structure interaction: distinct structural style
- earthwork overlays: surplus/deficit or issue-based color logic

The goal is clarity, not decorative complexity.

## 17. Density and Clutter Rules

Default behavior should prioritize readability.

Recommended defaults:

- show current section only
- keep labels sparse
- keep section series off by default
- show key markers only when requested

Dense review modes should require explicit activation.

## 18. Performance Strategy

3D review displays can become expensive quickly.

Recommended controls:

- current-only rendering by default
- sparse section series sampling
- level-of-detail behavior
- lazy rebuild of optional overlays
- explicit user control over high-density displays

The system should avoid generating all possible overlays automatically on every rebuild.

## 19. Synchronization Rules

The 3D review system should track result freshness.

Recommended sync rules:

- if underlying section outputs are stale, section overlays should show stale state
- if earthwork outputs are stale, earthwork overlays should not pretend to be current
- viewer and 3D highlight context should stay consistent when possible

## 20. Diagnostics Relationship

3D review overlays should help users see where issues are, not replace diagnostic systems.

Recommended diagnostic display uses:

- highlight sections with daylight fallback
- highlight structure conflict ranges
- highlight terrain gaps or sampling problem ranges
- highlight earthwork problem regions

## 21. Data Contract Minimum

At minimum, 3D review displays should have access to:

- stable station identity
- geometry references or geometry rows
- component or overlay semantics
- diagnostic links
- ownership links when selection should support handoff

If these are missing, the correct fix is to improve the shared output contract, not to hide special logic only in the 3D renderer.

## 22. Anti-Patterns to Avoid

Avoid the following:

- using 3D display meshes as export or engineering truth
- creating a separate station identity system only for 3D
- mixing interactive editing with review overlays
- enabling every dense display by default
- rebuilding expensive full-section fences during every small UI action

## 23. Recommended Follow-Up Documents

This 3D review plan should be followed by:

1. `V1_PLAN_PROFILE_SHEET_PLAN.md`
2. `V1_EXCHANGE_OUTPUT_SCHEMA.md`
3. `V1_REVIEW_NOTES_SCHEMA.md`

## 24. Final Rule

In v1, 3D review displays should explain the corridor in space.

They should not become a shortcut around the parametric source-of-truth architecture.

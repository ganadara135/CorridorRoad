# CorridorRoad V1 Viewer Plan

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_RAMP_MODEL.md`
- `docsV1/V1_INTERSECTION_MODEL.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`

## 1. Purpose

This document defines the v1 direction for Cross Section Viewer and related review behavior.

Its job is to clarify:

- what the viewer is for
- what it is not for
- what data it consumes
- how it connects to source editors
- how it supports review, diagnostics, and handoff without becoming a geometry editor

## 2. Core Direction

In v1, `Cross Section Viewer` stays and becomes stronger.

However, it is explicitly a:

- review surface
- source inspector
- editor handoff hub

It is not:

- a direct section-geometry editor
- a replacement for the underlying section model
- a hidden override authoring surface

## 3. Product Role

The viewer exists to let users answer questions like:

- What does the section look like at this station?
- Which template, region, override, or structure rule produced this geometry?
- Is this station influenced by a ramp, intersection, or drainage rule?
- Where does terrain or structure interaction begin to affect the section?
- Which editor should I open to change this result safely?
- Did the rebuilt result actually change after I edited the source?

## 3.1 UI transition position

The v1 viewer should be treated as an early replacement target, not as a long-term bridge to the existing v0 review UI.

Practical interpretation:

- existing v0 source editors may remain in use during transition
- but review screens should move earlier to v1-native UI
- `Cross Section Viewer` is the first major candidate to become a primary v1 review surface

This means the existing v0 viewer may remain available temporarily, but it should be treated as transition support rather than the final v1 viewer direction.

## 4. Viewer Position in the Architecture

The viewer belongs to the presentation layer.

It should consume:

- `SectionOutput`
- source ownership mappings
- related diagnostics
- optional earthwork-balance context
- optional ramp/intersection context
- optional drainage review context
- optional structure context

It should not own:

- section evaluation logic
- terrain sampling logic
- durable section overrides
- engineering source-of-truth geometry

## 5. Viewer Principles

### 5.1 Read-only geometry

Generated section geometry shown in the viewer is read-only.

### 5.2 Source traceability first

Every selectable section element should be traceable back to its source rule when possible.

### 5.3 Safe handoff over direct manipulation

The viewer should prefer:

- inspect
- explain
- navigate to source editor

over:

- drag geometry
- patch result polylines

### 5.4 Same-context return

After editing in a dedicated editor and rebuilding, the user should be able to return to the same station and selection context.

## 6. Primary Viewer Responsibilities

The viewer should provide:

- station navigation
- current-section display
- component inspection
- ramp and junction context review
- drainage interaction review
- terrain interaction review
- structure interaction review
- source ownership inspection
- editor handoff
- review notes and bookmarks
- stale/current result status

## 7. Data Inputs

The viewer should consume a normalized section-view payload rather than ad-hoc object inspection.

Minimum input families:

- section geometry rows
- semantic component rows
- dimension rows
- summary rows
- source ownership rows
- ramp/intersection context rows
- terrain interaction rows
- drainage interaction rows
- structure interaction rows
- diagnostics rows

Optional high-value input families:

- earthwork-balance hints
- scenario comparison hints
- recommendation hints

## 8. Station Navigation Model

### 8.1 Navigation goals

Users should move quickly among:

- current station
- previous/next station
- key stations
- region boundaries
- event stations
- bookmarked review stations

### 8.2 Recommended navigation modes

- slider or stepped station navigation
- station text entry
- next/previous key station
- next/previous review issue
- jump from 3D or tree selection

### 8.3 Identity rule

The viewer should operate on stable station values and applied-section identities, not on arbitrary transient scene items only.

## 9. Selection Model

### 9.1 Selectable entities

Recommended selectable entities:

- section component span
- component edge or terminal behavior
- ramp or intersection event marker
- terrain-intersection marker
- drainage-interaction marker
- structure interaction marker
- diagnostic region of interest

### 9.2 Selection purpose

Selection is for:

- inspection
- source tracing
- review annotation
- editor handoff

Selection is not for:

- result-geometry editing

### 9.3 Selection result

A selection should resolve to:

- component identity
- component kind
- side
- span or point reference
- source owner
- related ramp if any
- related intersection if any
- related drainage owner if any
- related region
- related override
- related structure if any

## 10. Source Inspector

The viewer should include a strong `Source Inspector` panel.

### 10.1 Inspector goals

The inspector should explain:

- what was selected
- what source owns it
- what policies affect it
- what downstream scope is likely to change if edited

### 10.2 Typical inspector fields

- `ComponentId`
- `ComponentKind`
- `SectionTemplateId`
- `RegionId`
- `OverrideId`
- `RampId`
- `IntersectionId`
- `DrainageId`
- `StructureId`
- active station
- side
- parameter summary
- impact-scope hint

### 10.3 Explanation rule

The inspector should prefer explicit, low-ambiguity text over vague labels.

Example:

- "Owned by Template `Rural-2Lane`, modified by Region `BASE_03`, no explicit station override."

## 11. Editor Handoff Model

### 11.1 Why handoff matters

The viewer must help users reach the correct durable source editor without making them reverse-engineer ownership manually.

### 11.2 Supported handoff targets

The viewer should support opening:

- `Template Editor`
- `Region Editor`
- `Structure Editor`
- `Override Manager`
- future `Superelevation Editor`
- future profile editor when a vertical issue is the real owner

### 11.3 Handoff payload

The viewer should pass enough context to the target editor, such as:

- station
- selected component id
- region id
- structure id
- side
- likely parameter focus

### 11.4 Return rule

After save and rebuild, the viewer should be able to return to:

- the same station
- the same selected component when still valid
- the same zoom or review context where practical

### 11.5 Relationship to source editors during transition

During transition:

- existing v0 source editors may still perform durable edits
- the v1 viewer should remain the preferred place to review rebuilt results
- handoff and return behavior should be designed to make this mixed workflow feel deliberate rather than accidental

## 12. Diagnostics Integration

The viewer should surface diagnostics without taking ownership of the diagnostic logic itself.

Priority diagnostic families:

- missing terrain interaction
- daylight fallback or failure
- structure conflict
- invalid override state
- region transition issue
- stale result state

The viewer should show:

- what happened
- where it happened
- what source is related
- which editor is relevant

## 13. Earthwork-Balance Integration

The viewer should not become the Earthwork Balance command, but it should expose local context where useful.

Recommended integrations:

- show whether the current station falls in surplus or deficit context
- show local cut/fill hints where available
- show links to the Earthwork Balance workflow
- surface recommendation hints when they are tied to the current section

Example:

- "This station is inside a deficit range."
- "Profile adjustment, not template change, is the likely balance driver here."

## 14. Structure and Terrain Review

The viewer should help users review:

- terrain intersection
- daylight resolution
- structure clearance behavior
- local section replacement or notch logic

This should be done through overlays, semantic rows, and source inspector content, not through direct shape editing.

## 15. 3D Review Relationship

The viewer should connect naturally with 3D review displays.

Recommended integrations:

- highlight current section in 3D
- jump from viewer station to 3D context
- jump from 3D pick to viewer station
- link sparse multi-section displays to key-station navigation

The 3D review remains a read-only review overlay system.

## 16. Layout and Rendering Strategy

### 16.1 Shared layout rule

Viewer drawing should be driven by the shared section-output and layout-planning system.

### 16.2 Rendering concerns

The viewer may own:

- scene rendering
- zoom/pan behavior
- display toggles
- selection highlighting

It should not own:

- section engineering interpretation
- ad-hoc label semantics not found in output contracts

## 17. Display Controls

Recommended viewer toggles:

- labels on/off
- dimensions on/off
- terrain interaction on/off
- structure interaction on/off
- diagnostics on/off
- review notes on/off

Recommended density behavior:

- clear defaults
- clutter reduction by default
- optional richer overlays for detailed review

## 18. Review Notes and Bookmarks

The viewer should support lightweight review workflow features.

Recommended features:

- bookmark current station
- add short review note
- mark as issue to revisit
- jump across bookmarked stations

These are review aids, not engineering source data.

## 19. Stale-State and Rebuild Feedback

The viewer should make rebuild state visible.

Recommended states:

- current
- stale
- rebuild needed
- blocked by error

After source edits, the viewer should clearly indicate whether the displayed result is current or outdated.

## 20. Performance Strategy

The viewer must remain usable for large corridor projects.

Recommended strategies:

- render only current section by default
- lazy-load rich overlays
- avoid full-document scans during every selection event
- cache normalized payloads where appropriate
- keep dense full-section review in separate, explicit modes

## 21. Anti-Patterns to Avoid

Avoid the following:

- turning the viewer into a general-purpose geometry editor
- putting section evaluation logic directly in viewer code
- storing durable edits as viewer-local state
- hiding ownership ambiguity behind vague labels
- overloading the canvas with too much default text

## 22. Suggested Follow-Up Documents

This viewer plan should be followed by:

1. `V1_SECTION_OUTPUT_SCHEMA.md`
2. `V1_REVIEW_NOTES_SCHEMA.md`
3. `V1_3D_REVIEW_DISPLAY_PLAN.md`

## 23. Final Rule

In v1, the viewer should help users understand and safely change the corridor by revealing the right source owner.

If a proposed viewer feature bypasses source traceability and edits generated geometry directly, it should be treated as contrary to the v1 model.

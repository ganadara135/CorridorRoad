# CorridorRoad V1 Cross Section Viewer Execution Plan

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_VIEWER_PLAN.md`
- `docsV1/V1_UX_RESET_PLAN.md`
- `docsV1/V1_REVIEW_STAGE_SPLIT_PLAN.md`
- `docsV1/V1_SECTION_OUTPUT_SCHEMA.md`
- `docsV1/V1_IMPLEMENTATION_PHASE_PLAN.md`
- `docsV1/V1_REVIEW_VIEWER_ROLE_DECISION.md`
- `docsV1/V1_CROSS_SECTION_2D_VIEWER_DESIGN.md`
- `docsV1/V1_CROSS_SECTION_2D_MANUAL_QA.md`

## 1. Purpose

This document turns the v1 viewer direction into an execution plan for making `Cross Section Viewer` the first primary v1-native review UI at the corridor-review stage.

It exists to define:

- what "viewer promotion" means in practical terms
- which capabilities must land before the v1 viewer becomes the default review path
- how the existing v0 viewer should be treated during transition
- what acceptance criteria should be used before switching user emphasis to the v1 viewer

## 2. Product Goal

The goal is not just to keep a working preview.

The goal is to promote the v1 cross-section review path into the main review experience for:

- station-by-station section inspection
- source ownership tracing
- editor handoff
- rebuild verification
- terrain and structure interaction review
- section-linked earthwork context

The main user-facing experience should be a detailed 2D section view by station.

Tables, diagnostics, source inspector rows, and corridor result rows are supporting panels.

## 3. Definition of Promotion

`Cross Section Viewer` is considered promoted when:

- users can open it directly as the preferred review surface
- it consumes normalized v1 payloads rather than ad-hoc object inspection
- it supports source inspector and same-context return
- the existing v0 viewer is no longer the preferred review path for normal use

## 4. Transition Position

During transition:

- the existing v0 viewer may remain available
- temporary implementation bridges may continue to exist in code
- but the v1 viewer should steadily become the center of review workflow

Practical product rule:

- existing v0 source editors may stay for a while
- existing v0 review screens should become secondary support paths

## 5. Scope of the First Promoted Viewer

The first promoted v1 viewer should include:

- current station section display
- station label and full station navigation
- component table
- quantity summary table
- viewer context summary
- source row summary
- source inspector baseline
- handoff to `Typical Section`, `Region`, and `Structure` editors
- same-context return after save/rebuild
- visible stale/current state

The current station section display should be a drawing-style 2D section preview.

It should preserve the visual expectations of the v0 `Cross Section Viewer`:

- section shape is drawn as a review drawing, not only as rows or a tiny plot
- component labels and values appear on or near section spans
- dimensions appear in a lower drawing band
- ditch, slope, subgrade, drainage, FG, and EG have distinct visual treatment
- labels and dimension text should use placement rules rather than ad-hoc fixed positions

The first promoted v1 viewer should reuse the v0 viewer as a visual reference only.

It should consume v1 payloads derived from `AppliedSectionSet`, `SectionOutput`, and corridor review rows.

The first promoted viewer does not yet need:

- full multi-panel report layout
- full 3D embedding
- every possible downstream editor target
- full scenario comparison
- full review notes workflow

## 6. Minimum Functional Milestones

### 6.1 Milestone A: Stable read-only viewer shell

Required outcomes:

- open v1 viewer directly from command
- show `SectionOutput`-based summary
- show stable station context
- no engineering logic in viewer code

Completion signal:

- the viewer can open without using the existing v0 viewer as an intermediate step

### 6.2 Milestone B: Source-inspector baseline

Required outcomes:

- selected component resolves to source owner
- viewer shows source fields clearly
- viewer can distinguish template, region, structure, and section-set context

Completion signal:

- a user can tell where to edit without reading raw object internals

### 6.3 Milestone C: Editor handoff and return

Required outcomes:

- open relevant existing v0 source editor from v1 viewer
- pass station and component context
- return to the same station after save/rebuild

Completion signal:

- `viewer -> editor -> viewer` roundtrip feels intentional and reliable

### 6.4 Milestone D: Review-quality improvements

Required outcomes:

- terrain interaction rows visible
- structure interaction rows visible
- focused component highlighting
- local earthwork hint attachment where available

Completion signal:

- the v1 viewer is useful for real section review, not only for migration validation

### 6.5 Milestone E: Preferred review path switch

Required outcomes:

- commands and workflow documentation favor v1 viewer first
- existing v0 viewer remains secondary
- users can complete normal section review without depending on the old review screen

Completion signal:

- the v1 viewer is the default recommended review path in docs and workflow

## 7. Execution Order

Recommended implementation order:

1. stabilize v1 section preview command and task panel
2. define a v1 `CrossSectionDrawingPayload` contract
3. map `AppliedSectionSet` station rows into drawing geometry, labels, and dimensions
4. port or reuse v0 drawing-rule placement concepts for label and dimension layout
5. replace small preview rendering with dominant drawing-style section canvas
6. improve current-section payload rendering and selection behavior
7. complete source inspector baseline
8. complete editor handoff and same-context return
9. attach terrain, structure, and earthwork context
10. expose v1 viewer as the preferred review command
11. demote the existing v0 viewer to bridge/support status

## 8. Data Contract Requirements

The promoted viewer must rely on:

- `SectionOutput`
- `station_row`
- source ownership data
- terrain rows
- structure rows
- diagnostic rows
- optional earthwork hint rows

It must not depend on:

- direct section-wire mutation
- hidden parsing of display-only geometry
- deep object probing as the primary data source

## 9. UI Requirements

The promoted v1 viewer should visibly present:

- station
- station label
- selected component
- source owner
- current/old result state
- available handoff targets

Recommended layout:

- top summary
- section canvas or section summary block
- component table
- source inspector panel
- context/diagnostic panel
- handoff button row

## 10. Command Strategy

During transition:

- keep the standalone v1 viewer command
- prefer opening the v1 viewer from new workflow documentation
- describe the v1 viewer as the normal starting point for section review
- describe the existing v0 viewer as a secondary continuity path

Longer term:

- the main cross-section review command should resolve directly to the v1 viewer
- user-facing review walkthroughs should start with the v1 viewer, not the old review screen

## 11. Relationship to Existing v0 Viewer

The existing v0 viewer should be treated as:

- useful for continuity during transition
- useful for comparison during validation
- not the long-term review center
- not the preferred user-facing entry point for normal review work

The existing v0 viewer should not absorb major new review logic if that logic belongs in the v1 viewer.

## 12. Testing and Validation

The promoted viewer should be validated through:

- contract tests for preview payload and context merge
- handoff tests
- same-context return tests
- focused component tests
- smoke tests for opening the v1 viewer command
- manual review of at least one real corridor document

Current implementation notes:

- [x] Cross Section Viewer can show Build Corridor result rows for `3D Centerline`, `Design Surface`, `Subgrade Surface`, `Slope Face Surface`, and `Drainage Surface` when corridor preview objects are available
- [x] Cross Section Viewer summary reports corridor build result readiness so missing corridor surfaces are visible during station-level section review
- [x] Cross Section Viewer can double-click a corridor build result row to select and fit the related 3D preview object
- [x] Cross Section Viewer has a v1 `CrossSectionDrawingPayload` contract for drawing-style section geometry
- [x] Cross Section drawing payload can be generated from v1 `AppliedSectionSet`
- [x] Cross Section drawing payload includes label/value rows and lower-band dimension rows
- [x] Cross Section Viewer renders v1 `CrossSectionDrawingPayload` in the 2D canvas
- [x] Cross Section Viewer shows component labels and values directly in the 2D drawing
- [x] Cross Section Viewer shows lower-band dimension annotations from v1 drawing payload rows
- [x] Cross Section Viewer shows ditch, slope-face, subgrade, drainage, FG, and EG with distinct drawing styles
- [x] Cross Section Viewer shows explicit source-owner rows for `Section Set`, `Template`, `Region`, and `Structure`
- [x] Cross Section Viewer distinguishes `resolved`, `source_ref`, and `unresolved` source-owner states
- [x] Cross Section Viewer applies screen-space text layout to reduce label and dimension overlap
- [x] Cross Section 2D v0-style manual QA procedure is documented
- [ ] Cross Section 2D v0-style manual QA has passed on a real document

Minimum manual scenarios:

1. open viewer at a selected station
2. inspect component ownership
3. open `Typical Section`
4. save and return
5. verify same station context
6. repeat with `Region` and `Structure`

## 13. Acceptance Criteria for Promotion

The v1 viewer is ready to become the preferred section review UI when:

- it opens reliably on real project documents
- source inspector is clear enough for ordinary editing decisions
- handoff to key source editors works
- same-context return works
- users do not need the existing v0 viewer for ordinary review tasks
- the viewer remains read-only and output-driven

## 14. Non-Goals

Do not block promotion on:

- full replacement of all source editors
- completion of every review-note feature
- final 3D review integration
- final AI integration
- final output/export review integration

## 15. Follow-Up Documents

After this plan, the next natural execution documents are:

1. `V1_PLAN_PROFILE_REVIEW_EXECUTION_PLAN.md`
2. `V1_EARTHWORK_REVIEW_EXECUTION_PLAN.md`
3. `V1_REVIEW_NOTES_SCHEMA.md`

## 16. Final Rule

`Cross Section Viewer` should be the first screen where CorridorRoad clearly feels like v1.

If the team must choose between preserving the old review UX and strengthening the v1 review path, the v1 review path should win.

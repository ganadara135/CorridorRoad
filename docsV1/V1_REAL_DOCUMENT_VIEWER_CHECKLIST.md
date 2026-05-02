# CorridorRoad V1 Real Document Viewer Checklist

Date: 2026-04-23
Branch: `v1-dev`
Status: Active manual validation checklist
Depends on:

- `docsV1/V1_VIEWER_ROUNDTRIP_MANUAL_QA.md`
- `docsV1/V1_CROSS_SECTION_2D_MANUAL_QA.md`
- `docsV1/V1_UX_RESET_PLAN.md`
- `docsV1/V1_MAIN_REVIEW_COMMAND_MANUAL_RECORD.md`

## 1. Purpose

This checklist is the short version of manual validation for one real FreeCAD project document.

Use it when checking whether the current v1 viewers are strong enough to be treated as the preferred review surfaces.

## 2. Document Setup

- [x] a real project file is open
- [x] alignment exists
- [x] profile exists
- [ ] v1 AppliedSectionSet exists
- [x] region plan exists or is intentionally absent
- [ ] v1 StructureModel exists or is intentionally absent
- [ ] earthwork-related result object exists or is intentionally absent

## 2A. Preferred Start Rule

- [x] section review was started from the v1 `Cross Section Viewer`
- [x] plan/profile review was started from the v1 `Plan/Profile Viewer`
- [ ] earthwork review was started from the v1 `Earthwork Viewer`
- [x] no existing v0 viewer was needed as the first review screen

## 3. Cross Section Viewer

- [x] opens directly
- [x] title uses `Viewer`
- [ ] `Current Focus` is visible
- [x] `Result State` is visible
- [ ] viewer is not limited to `demo section viewer payload`
- [x] 2D section drawing is visually dominant and readable
- [x] FG, EG when available, subgrade, ditch, and slope-face styles are distinguishable
- [x] component labels are visible near the relevant section spans
- [x] dimension annotations are visible in the lower drawing band
- [ ] label and dimension overlap is acceptable in normal panel size
- [x] `Source Inspector` is visible
- [x] `Source Inspector` shows `Section Set`, `Assembly`, `Region`, and `Structure` owner rows
- [ ] unresolved source owners are visible when source tracing is incomplete
- [x] `Station Navigation` shows the full station list
- [x] moving to another station changes the focus as expected
- [x] `Open Assembly` opens the v1 Assembly editor
- [x] `Open Regions` opens the v1 Regions editor
- [x] `Open Structures` opens the v1 Structures editor
- [ ] v1 Structures editor creates a visible `V1StructureShowPreview` in the 3D view
- [ ] return from editor comes back to the intended station context

## 4. Plan/Profile Viewer

- [x] opens directly
- [x] title uses `Viewer`
- [ ] `Current Focus` is visible
- [ ] `Viewer Context` is visible
- [x] `Station Navigation` shows the full station list
- [ ] moving to another station changes the focus as expected
- [ ] `Profile Controls` row emphasis matches the focus station
- [x] `Open Alignment` opens the correct existing v0 editor
- [x] `Open Profiles` opens the correct existing v0 editor
- [x] `Open PVI` opens the correct existing v0 editor
- [ ] return from editor comes back with understandable station context

## 5. Earthwork Viewer

- [ ] opens directly
- [ ] title uses `Viewer`
- [ ] `Current Focus` is visible
- [ ] `Station Navigation` shows the full station list
- [ ] moving to another station changes the focus as expected
- [ ] `Focused Window` changes when appropriate
- [ ] `Open Alignment` opens the correct existing v0 editor
- [ ] `Open Profiles` opens the correct existing v0 editor
- [ ] `Open PVI` opens the correct existing v0 editor
- [ ] return path keeps the station understandable

## 6. Common Focus Rules

- [x] the displayed focus station matches the actual selected station
- [x] the focused row/table emphasis matches the focus station
- [ ] no silent station drift happened during viewer roundtrip
- [x] no wrong source object was opened during handoff

## 7. Promotion Signal

The current real document should be considered a pass only if:

- [ ] all three viewers opened successfully
- [ ] at least one roundtrip succeeded for each viewer family
- [ ] no major context mismatch occurred
- [ ] no fallback to an old review screen was needed just to recover context
- [ ] the v1 viewers felt usable as the first review surfaces
- [ ] the cross-section review used real document data rather than demo payload only

## 8. Record

- Document:
- Date: 4.30.26
- Tester:
- Cross Section Viewer: pass / fail
- Plan/Profile Viewer: pass / fail
- Earthwork Viewer: pass / fail
- Notes:

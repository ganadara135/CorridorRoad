# CorridorRoad V1 Cross Section 2D Manual QA

Date: 2026-04-29
Status: Manual QA procedure, execution pending real document
Depends on:

- `docsV1/V1_CROSS_SECTION_2D_VIEWER_DESIGN.md`
- `docsV1/V1_CROSS_SECTION_VIEWER_EXECUTION_PLAN.md`
- `docsV1/V1_CROSS_SECTION_VIEWER_WORK_CHECKLIST.md`
- `docsV1/V1_REAL_DOCUMENT_VIEWER_CHECKLIST.md`

## 1. Purpose

This document defines the manual QA procedure for comparing the v1 `Cross Section Viewer` 2D drawing against the expected v0-style section review behavior.

The goal is not to prove that v1 reuses v0 data ownership.

The goal is to confirm that v1 preserves the useful visual behavior:

- large readable 2D section drawing
- component labels near their owning spans
- dimension annotations in the lower drawing band
- dark-mode readable colors
- source ownership and handoff context visible beside the drawing

## 2. Required Setup

Use a real CorridorRoad project document with:

- Alignment generated
- Stations generated
- Profile generated
- TIN or terrain context available when possible
- Assembly applied
- Regions applied
- Applied Sections generated
- Build Corridor run at least once when corridor result rows should be reviewed

Do not count a demo fallback payload as a visual QA pass.

If the viewer says `Built from demo section viewer payload.`, record the command as opened but mark this QA as blocked.

## 3. Launch Steps

1. Open FreeCAD.
2. Open the real CorridorRoad project document.
3. Run the v1 `Cross Section Viewer` command.
4. Confirm the viewer opens without falling back to the old v0 review screen.
5. Select or navigate to at least three stations:
   - start or near-start station
   - middle ordinary roadway station
   - station with ditch, side slope, structure, or other non-basic context if available

## 4. Drawing Canvas Checks

Pass conditions:

- The section drawing is visually dominant enough to review before reading tables.
- FG is visible as a strong warm line.
- EG or terrain line is visible when terrain sampling is available.
- Subgrade is visually distinct from FG.
- Ditch or drainage geometry is cyan/blue when present.
- Slope-face geometry is visually distinct from FG and subgrade.
- Centerline reference is visible.
- Offset and elevation context are understandable from the drawing.

Fail conditions:

- The section can only be understood by reading tables.
- FG, EG, subgrade, ditch, or slope-face styles are visually indistinguishable.
- The drawing is too small to review in normal panel size.
- Text or line colors are unreadable in dark mode.

## 5. Label And Dimension Checks

Pass conditions:

- `CL`, `FG`, `Subgrade`, ditch, and slope labels appear when their source rows exist.
- Label values are near the relevant section span.
- Overall width dimension appears in the lower dimension band.
- Component width dimensions appear when generated.
- Labels and dimension text are shifted enough to reduce obvious overlap.
- Text stays within the drawing frame in ordinary panel sizes.

Known acceptable first-pass limitation:

- The current v1 layout reduces overlap but is not yet a full sheet-grade drafting engine.

Fail conditions:

- Labels stack on top of each other so the section cannot be read.
- Dimension text covers the main section geometry in normal cases.
- Important labels are clipped outside the drawing frame.
- The lower dimension band is missing when dimension rows exist.

## 6. Source Inspector Checks

Pass conditions:

- `Source Ownership` status is visible.
- `Section Set`, `Template`, `Region`, and `Structure` owner rows are visible.
- Owner rows distinguish:
  - `resolved`
  - `source_ref`
  - `unresolved`
- Unresolved owner fields are visible when source tracing is incomplete.
- The user can infer which editor to open next without reading raw object properties.

Fail conditions:

- Source ownership is hidden in generic table rows.
- Missing source owners are silent.
- Template, Region, Structure, and Section Set cannot be distinguished.

## 7. Handoff Checks

For at least one station:

1. Open `Typical Section` from the viewer.
2. Return to the viewer.
3. Open `Regions` from the viewer.
4. Return to the viewer.
5. Open `Structures` from the viewer when a structure context exists.

Pass conditions:

- The opened editor is the expected source editor.
- The station context remains understandable after return.
- No unrelated v0 review screen is required just to recover context.

Fail conditions:

- The wrong source object opens.
- The viewer loses station context after a handoff.
- A v0 review screen is needed to understand or recover the workflow.

## 8. Comparison To V0 Visual Behavior

Use the v0 viewer as visual reference only.

The v1 viewer passes this comparison when:

- the v1 drawing communicates the same section-review intent as v0
- labels and dimensions are present in the drawing, not only in tables
- the lower dimension band concept is preserved
- dark-mode readability is at least as clear as v0
- v1 source ownership is clearer than v0

The v1 viewer does not need to match v0 pixel-for-pixel.

## 9. Record Template

Document:

Date:

Tester:

Stations checked:

Canvas readability: pass / fail

FG/EG/subgrade style: pass / fail

Ditch/slope display: pass / fail / not applicable

Labels: pass / fail

Dimensions: pass / fail

Source Inspector: pass / fail

Handoff: pass / fail

Demo payload fallback occurred: yes / no

Notes:

## 10. Promotion Signal

The v1 `Cross Section Viewer` should be treated as ready for ordinary station-by-station review when:

- this QA passes on at least one real document
- no demo fallback is used for the pass
- labels and dimensions are readable in dark mode
- source ownership is understandable without inspecting raw FreeCAD objects


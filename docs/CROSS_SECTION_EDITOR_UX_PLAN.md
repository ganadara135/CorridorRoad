<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Cross Section Editor UX Plan

Date: 2026-04-21

Related architecture:

- [CROSS_SECTION_EDITOR_ARCHITECTURE.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/CROSS_SECTION_EDITOR_ARCHITECTURE.md)
- [CROSS_SECTION_VIEWER_LAYOUT_PLAN.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/CROSS_SECTION_VIEWER_LAYOUT_PLAN.md)
- [CROSS_SECTION_COMPONENT_SCOPE_PLAN.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/CROSS_SECTION_COMPONENT_SCOPE_PLAN.md)

## Non-Removal Decision

`Cross Section Viewer` must remain available as the read-only review and export experience.

`Cross Section Editor` must be developed as a separate editing experience, not as a replacement for the viewer.

Do not remove or hide the existing viewer command while adding editor UX. Users should be able to choose either `Cross Section Viewer` or `Cross Section Editor`.

## Current Implementation Status

Updated: 2026-04-21

- Stage marker: `PH-3 CURRENT`
- `Cross Section Viewer` remains available and is not being retired.
- Current development step: `PH-3 Impact Analyzer UX`.
- Completed before PH-3: target selector, canvas click selection, selected component highlight, source owner display, generated/raw row preview, read-only details, read-only parameter table, impact-preview scaffold.
- Completed in PH-3 so far: computed affected range, affected station count, timeline, boundary station preview, region owner, structure overlap, downstream status, warnings, and blocked-state text.
- Next development step: `PH-4 Safe Apply UX`.
- `PH-2 Review Mode`: inherited from the existing `Cross Section Viewer`.
- `PH-2 Select Mode`: in progress.
  - Added `Cross Section Editor` command and task panel.
  - Added a right-side target selector driven by current station component segments.
  - Added canvas click selection for visible component guides in `Select` / `Edit` modes.
  - Added selected component highlight overlay for the selected target.
  - Added read-only target detail, source owner, generated/raw row preview, and parameter panels.
- `PH-2 Edit Mode`: scaffolded only.
  - Scope selector and impact-preview text area exist.
  - `Apply` is disabled until edit persistence and recompute integration are implemented.
- `PH-3 Impact Preview`: in progress.
  - Shows parameter class.
  - Shows affected range and station count.
  - Shows previous/current/next timeline.
  - Shows boundary stations, region owner, structure overlap, downstream recompute/stale text, warnings, and blocked states.
- Editable fields and before/after overlay are still pending.

### PH Status Map

| Phase | Status | UX Meaning |
| --- | --- | --- |
| `PH-1` | Deferred | Viewer UX remains intact; no viewer replacement. |
| `PH-2` | Implemented / GUI check pending | Editor shell, target selector, canvas click selection, selected highlight, source/raw row visibility, read-only inspector. |
| `PH-3` | Current / In progress | Impact preview becomes computed rather than text scaffold. |
| `PH-4` | Next / Pending | First safe apply flow through existing source owners. |
| `PH-5` | Pending | Station/range override UX backed by `CrossSectionEditPlan`. |
| `PH-6` | Pending | Range, transition, and adjacent-station visualization. |
| `PH-7` | Pending | Drag handles, before/after overlay, and conflict-resolution UX. |

## Goal

Design a practical user experience for editing cross sections without making generated section geometry look like hand-editable CAD linework.

The editor should feel like:

- a section review workspace
- a semantic component selector
- a controlled parameter editor
- an impact preview tool

It should not feel like:

- a freeform wire editor
- a mesh editor
- a hidden direct mutation of `SectionSet` result rows

## UX Principles

1. Show generated geometry clearly, but edit source intent.
2. Make the selected edit target obvious.
3. Separate review, selection, and edit states.
4. Geometry edits must ask for scope.
5. Adjacent-station impact must be visible before apply.
6. Dangerous station-only geometry edits must be explicit.
7. Region-based edits should be the default for design-intent changes.
8. Recompute and stale downstream results should be visible, not silent.

## Window Structure

Recommended first implementation: one task panel with a split layout.

```text
+--------------------------------------------------------------+
| Header: SectionSet, Station, Region, Structure, Display Unit  |
+------------------------------+-------------------------------+
|                              | Selection / Edit Panel         |
|  Cross Section Canvas        |                               |
|                              | - Target                      |
|  - section line              | - Source                      |
|  - component guides          | - Parameters                  |
|  - selected highlight        | - Scope                       |
|  - before/after preview      | - Impact Preview              |
|                              | - Apply / Cancel              |
+------------------------------+-------------------------------+
| Station Navigator / Timeline / Warnings / Summary            |
+--------------------------------------------------------------+
```

Minimum viable layout:

- top source bar
- central 2D canvas
- right inspector/edit panel
- bottom summary and warnings panel

## Top Source Bar

Contents:

- `SectionSet` selector
- `Station` selector
- `Previous` / `Next`
- `Use Selected Section`
- `Fit View`
- mode switch: `Review`, `Select`, `Edit`
- display unit text

Recommended status line:

```text
SectionSet: Section Set (SectionSet001) | STA 25.000 m | Region: BASE_02 / DITCH_OVR_L | Structure: CULV-1 | Unit: m
```

When no section is available:

```text
No SectionSet found. Run Generate Sections first.
```

When station payload is missing:

```text
No section payload is available for the selected station. Recompute Sections and try again.
```

## Canvas UX

The canvas reuses the current viewer drawing language.

Always show:

- section polyline
- center axis
- station title
- component subdivision guides

Optional toggles:

- structure overlays
- dimensions
- diagnostics
- typical components
- side-slope components
- daylight markers
- before/after overlay

### Selection Visuals

When a component is hovered:

- brighten the component guide
- show a small tooltip
- keep the section line stable

Tooltip example:

```text
LANE-L | lane | left | typical | width 3.500 m
```

When selected:

- selected guide uses active highlight color
- selected span gets a subtle translucent band
- selected row appears in the inspector
- previous selection is cleared unless multi-select is later added

Do not resize the layout when selecting. Highlighting must be visual-only.

### Before / After Preview

When a pending geometry edit exists:

- current geometry remains solid
- preview geometry is dashed
- changed component span is highlighted
- affected range is shown in the station timeline

Suggested colors:

- current geometry: existing section color
- preview geometry: green or cyan dashed line
- warning span: amber
- blocked conflict: red

## Mode Model

### Review Mode

Purpose:

- inspect stations
- export drawings
- read summaries

Available actions:

- navigate stations
- zoom/pan
- toggle layers
- export PNG/SVG/Sheet SVG
- use selected 3D section

No editing controls are active.

### Select Mode

Purpose:

- choose a semantic edit target

Available actions:

- hover component guides
- click component guide
- click daylight marker
- click structure overlay for context only
- inspect source row

Inspector is read-only until user clicks `Edit Target`.

### Edit Mode

Purpose:

- modify a selected parameter with explicit scope and preview

Available actions:

- change parameter value
- choose scope
- run impact preview
- apply
- cancel

Station navigation remains available, but navigating with unsaved edits must prompt:

```text
Discard the pending edit and move to another station?
```

## Right Inspector Panel

The right panel has four stacked sections.

### 1. Target

Shows selected semantic target.

Fields:

- target id
- type
- side
- scope
- source
- station span
- current width or value
- raw row preview

Example:

```text
Target
  Id: LANE-L
  Type: lane
  Side: left
  Scope: typical
  Source: TypicalSectionTemplate
  Current span: 3.500 m
```

If the user selects generated linework with no semantic row:

```text
This line has no editable component contract. Use the owning template, assembly, or region editor.
```

### 2. Parameters

Shows editable parameters for the selected target.

For typical components:

- width
- cross slope
- height
- extra width
- back slope
- shape for ditch
- enabled
- order

For side slope:

- side slope width
- side slope percentage
- cut/fill policy if available

For bench:

- drop
- width
- slope
- post-bench slope
- repeat-to-daylight

For daylight:

- daylight enabled
- max search width
- left/right disable policy

For structure overlay:

- read-only context in MVP
- link to StructureSet or Region editor

### 3. Scope

Scope selector should be required for geometry edits.

Options:

- `Global Source`
- `Active Region`
- `Station Range`
- `Current Station Only`

Recommended default:

- presentation edit: no scope needed
- metadata edit: current station
- typical component geometry: active region if available
- side-slope/daylight geometry: active region if available
- structure-affected edit: active structure span or active region

### Scope Cards

Show each scope as a compact card with impact text.

`Global Source`:

```text
Applies to every section using this template or assembly.
```

`Active Region`:

```text
Applies to region BASE_02 from STA 20.000 to STA 50.000.
Region boundaries and transitions will be included.
```

`Station Range`:

```text
Applies from STA 20.000 to STA 50.000 with transition-in/out.
Boundary stations may be added.
```

`Current Station Only`:

```text
Advanced. May create a kink between adjacent stations.
```

Current station only should require an extra confirmation for geometry edits.

### 4. Impact Preview

Before `Apply` is enabled for geometry edits, preview must show:

- affected station count
- previous/current/next station
- start/end station
- transition-in/out
- boundary stations to add
- active region owner
- structure overlap
- topology warning
- downstream recompute status

Example:

```text
Impact Preview
  Affected range: STA 20.000 to STA 50.000
  Transition: 5.000 m in / 5.000 m out
  Stations affected: 9
  Boundary stations to add: 15.000, 20.000, 50.000, 55.000
  Region owner: BASE_02
  Structure overlap: none
  Downstream: Corridor will be marked stale
```

Warning example:

```text
Warning
  This edit changes component topology at one station only.
  The corridor surface may kink between STA 20.000, STA 25.000, and STA 30.000.
```

Blocked example:

```text
Blocked
  This edit overlaps CULV-1 where structure policy disables daylight.
  Choose a Region override or edit the StructureSet policy first.
```

## Bottom Timeline

The bottom area should show station context.

MVP version:

- previous station
- current station
- next station
- active region span
- edit affected span
- structure span if present

Text-first implementation is acceptable:

```text
STA 20.000 | STA 25.000* | STA 30.000
Region BASE_02: 20.000 -> 50.000
Pending edit: 20.000 -> 50.000, transition 5.000 / 5.000
```

Later visual version:

- horizontal station ruler
- current station marker
- region band
- structure band
- edit band
- warning markers

## Main User Flows

### Flow 1: Review Existing Section

1. Open Cross Section Editor.
2. Select SectionSet.
3. Select station.
4. Pan/zoom canvas.
5. Toggle dimensions or overlays.
6. Export if needed.

No edit model is touched.

### Flow 2: Inspect Component

1. Switch to `Select`.
2. Hover a component guide.
3. Click `LANE-L`.
4. Inspector shows id, type, side, scope, source, width.
5. User clicks `Edit Target`.

No recompute yet.

### Flow 3: Edit Lane Width By Active Region

1. Select lane component.
2. Change width from `3.500 m` to `3.750 m`.
3. Scope defaults to `Active Region`.
4. Impact preview shows region span and affected stations.
5. User clicks `Apply`.
6. Editor writes Region or EditPlan override.
7. SectionSet recomputes.
8. Viewer refreshes at current station.
9. Status shows applied edit summary.

Success message:

```text
Applied width override for LANE-L over BASE_02. Sections recomputed.
```

### Flow 4: Edit Side Slope Over Station Range

1. Select side-slope component.
2. Change slope from `-33.000 %` to `-25.000 %`.
3. Scope defaults to `Station Range`.
4. User sets start/end and transition.
5. Impact preview warns about daylight recompute.
6. User applies.
7. EditPlan stores override.
8. SectionSet recomputes.
9. Corridor is marked stale.

### Flow 5: Current Station Only Exception

1. Select ditch component.
2. Change ditch depth at current station.
3. User chooses `Current Station Only`.
4. Editor shows strong warning.
5. User confirms advanced station-only edit.
6. EditPlan stores station override.
7. SectionSet recomputes.
8. Timeline marks station as local exception.

Confirmation text:

```text
This geometry edit applies only to STA 25.000.
Adjacent stations will not be changed. This may create abrupt corridor geometry.
Apply station-only override?
```

### Flow 6: Structure Conflict

1. Select daylight marker near a culvert.
2. Try to enable daylight where structure policy disables it.
3. Impact preview marks conflict.
4. Apply is disabled.
5. User can open StructureSet or create Region override if allowed.

## Editing Controls

### Numeric Fields

Use spin boxes with display unit labels.

Rules:

- show display unit
- store values in model units according to existing unit policy
- show min/max where known
- support reset to source value

Example:

```text
Width: [ 3.750 ] m
```

### Enumerations

Use combo boxes.

Examples:

- ditch shape: `v`, `u`, `trapezoid`
- scope: `global`, `region`, `range`, `station`
- daylight mode: `auto`, `off`, `manual future`

### Checkboxes

Use for boolean flags:

- component enabled
- repeat first bench to daylight
- disable left daylight
- disable right daylight

### Apply Buttons

Buttons:

- `Preview Impact`
- `Apply`
- `Cancel`
- `Revert Target`

Rules:

- `Apply` disabled until preview is current.
- Changing any field invalidates preview.
- Blocked preview disables `Apply`.
- Warnings allow apply only after confirmation.

## Status And Messages

Use plain, specific messages.

Good:

```text
Width change affects 7 stations and will add 2 boundary stations.
```

Avoid:

```text
Edit may affect model.
```

### Status Types

- `Info`
- `Warning`
- `Blocked`
- `Applied`
- `Stale`

### Common Messages

No target:

```text
Select a component guide or daylight marker to inspect it.
```

Read-only target:

```text
This item is generated geometry. Edit the owning template, assembly, region, or edit plan instead.
```

Preview stale:

```text
Preview is stale. Run Preview Impact again before applying.
```

Downstream stale:

```text
Sections were updated. Corridor result is now stale and should be regenerated.
```

## Safety Rules

1. Never silently change all stations from a current-station edit.
2. Never silently change current station only for a geometry edit.
3. Never write directly to generated `SectionComponentSegmentRows`.
4. Never hide structure or region conflicts.
5. Always show the source owner before editing.
6. Always show affected stations before applying geometry edits.
7. Always show whether downstream corridor output is recomputed or stale.

## MVP UX

Current status: `PH-3 Impact Analyzer UX` is in progress.

The MVP should include:

- `Review` and `Select` modes: in progress
- component guide hit testing: implemented for visible marker rows in `Select` / `Edit` modes
- selected component highlight: implemented for target selector selection
- source owner/raw row visibility: implemented
- right-side read-only inspector: started
- edit mode for one parameter: component width: pending
- scope choices:
  - global source: scaffolded
  - active region: scaffolded
  - station range: scaffolded
  - current station only: scaffolded
- impact preview: scaffolded
- apply through existing source where possible: pending
- clear warning for station-only geometry edits: started

MVP can defer:

- drag handles
- visual station ruler
- before/after geometry overlay
- multi-select
- editing every parameter
- conflict resolution wizard

## Later UX Enhancements

### Drag Handles

Add drag handles only after parameter editing is stable.

Recommended first drag handles:

- component width boundary
- overall side width
- bench width

Rules:

- drag creates pending parameter change
- drag does not immediately apply
- impact preview is still required

### Before / After Split

Add a toggle:

- `Current`
- `Preview`
- `Overlay`

### Edit History

Show applied edits:

- edit id
- target
- parameter
- scope
- stations
- enabled flag

### Region Creation Wizard

When active region is missing:

1. choose span
2. choose base or overlay region
3. choose transition
4. name region
5. create and apply

## UX Acceptance Criteria

Review:

- user can open editor and inspect a station without needing edit setup
- existing export workflow remains available

Selection:

- user can identify selected component by highlight and inspector
- selected source owner is visible

Editing:

- geometry edit cannot apply without scope
- geometry edit cannot apply without preview
- current-station-only geometry edit shows warning
- region/range edit lists affected stations

Recompute:

- after apply, viewer refreshes to the edited station
- status says what was changed
- downstream stale state is visible

Error handling:

- read-only generated geometry is clearly explained
- structure conflict blocks unsafe apply
- missing SectionSet or payload gives actionable text

## Implementation Notes

The UX should be implemented incrementally.

Recommended order:

1. Extract viewer rendering core without changing UX.
2. Add hover and selection highlight.
3. Add read-only inspector.
4. Add parameter edit form.
5. Add impact preview.
6. Add safe apply path for one parameter.
7. Expand supported parameters.

Do not start with drag editing. Drag editing looks attractive, but it hides the important scope and adjacent-station decisions. Start with explicit parameter editing first.

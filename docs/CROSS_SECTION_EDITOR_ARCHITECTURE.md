<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Cross Section Editor Architecture

Date: 2026-04-21

## Non-Removal Decision

`Cross Section Viewer` must remain as a separate review and export command.

`Cross Section Editor` must be developed as a separate command and workspace that reuses viewer capabilities where appropriate.

Do not replace, remove, or rename `CorridorRoad_ViewCrossSection` as part of the editor work. The editor command, currently `CorridorRoad_EditCrossSection`, is additive.

## Current Implementation Status

Updated: 2026-04-21

- Stage marker: `PH-5 CURRENT`
- `Cross Section Viewer` remains active and is not being retired.
- Current development step: `PH-5 Typical Cross Slope Runtime Override`.
- Completed before PH-3: target selector, canvas click selection, selected component highlight, source owner display, generated/raw row preview, read-only inspector, impact-preview scaffold.
- Completed in PH-3 so far: parameter classification, affected station resolver, region owner summary, structure overlap preview, boundary station preview, downstream recompute/stale preview.
- Completed in PH-4: guarded width apply paths for `Global Source` + linked `TypicalSectionTemplate`, `AssemblyTemplate` carriageway widths, simple and bench-aware `AssemblyTemplate` side-slope widths, simple and bench-aware `AssemblyTemplate` side-slope percent edits, guarded `Active Region` `RegionPlan` side/daylight policy edits, undo-friendly transactions, applied edit summary rows, PH-4 validation rows, downstream stale validation, and downstream recompute marking.
- Completed in PH-5 so far: added `CrossSectionEditPlan` object skeleton, edit row parser/serializer, active-station lookup, boundary-station listing, SectionSet link properties, SectionSet edit-plan summary rows, `resolve_station_values(...)` boundary-station merge, section-build runtime override consumption for side-slope width / slope edits plus typical-component width / `cross_slope_pct` edits, editor apply paths for `Station Range` and `Current Station Only`, and persistence/runtime/editor smoke coverage.
- Next development step: extend typical/local runtime overrides beyond width and `cross_slope_pct` into richer component parameters such as height / extra width / back slope.
- `PH-1 Refactor Viewer Core`: deferred. The current implementation still reuses [task_cross_section_viewer.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/ui/task_cross_section_viewer.py) directly.
- `PH-2 Selection And Inspection`: implementation complete; FreeCAD GUI manual check pending.
  - Added `CorridorRoad_EditCrossSection`.
  - Added [task_cross_section_editor.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/ui/task_cross_section_editor.py).
  - The editor currently wraps the existing viewer and adds a right-side `Selection / Edit Panel`.
  - Current capability is read-only component target selection, canvas click selection for visible component guides, selected component canvas highlight, source owner display, generated/raw row preview, parameter inspection, and impact-preview scaffolding.
- `PH-3 Impact Analyzer`: implemented for MVP text preview; GUI manual check pending.
  - Added parameter classification.
  - Added affected-station resolver for global source, active region, station range scaffold, and current-station-only scopes.
  - Added region owner, structure overlap, boundary station, downstream recompute, warning, and blocked-state preview text.
- `PH-4 Safe Edits Through Existing Sources`: in progress.
  - Added guarded `PH-4 Width Edit` control.
  - Added guarded `PH-4 Slope Edit` control.
  - Apply is enabled only for guarded source-owner cases.
  - Current `TypicalSectionTemplate` apply writes `TypicalSectionTemplate.ComponentWidths[index]`, touches the source and SectionSet, recomputes the document, and refreshes the editor at the current station.
  - Current `AssemblyTemplate` apply writes `AssemblyTemplate.LeftWidth` or `AssemblyTemplate.RightWidth` for assembly carriageway targets.
  - Current side-slope apply writes `AssemblyTemplate.LeftSideWidth` or `AssemblyTemplate.RightSideWidth`; when bench rows are configured, they are preserved and PH-4 validation emits a bench-aware warning.
  - Current side-slope percent apply writes `AssemblyTemplate.LeftSideSlopePct` or `AssemblyTemplate.RightSideSlopePct`; when bench rows are configured, they are preserved and PH-4 validation emits a bench-aware warning.
  - Current RegionPlan apply writes `RegionPlan.SidePolicy` or `RegionPlan.DaylightPolicy` on the active base region when scope is `Active Region`.
  - PH-4 apply now opens a FreeCAD document transaction where available.
  - Applied edits are recorded on the SectionSet as `CrossSectionEditorEditRows` and `CrossSectionEditorLastEditSummary`.
  - PH-4 validation rows are shown in the editor and recorded on successful apply as `CrossSectionEditorValidationRows` and `CrossSectionEditorLastValidationSummary`.
  - Linked downstream `Corridor`, `DesignGradingSurface`, `DesignTerrain`, and `CutFillCalc` outputs are listed in PH-4 validation and marked stale after successful apply.
- Editing/apply remains disabled except for the guarded PH-4 source-owner paths described above.

### PH Status Map

| Phase | Status | Meaning |
| --- | --- | --- |
| `PH-1` | Deferred | Viewer core split is deferred. Viewer behavior must remain unchanged. |
| `PH-2` | Implemented / GUI check pending | Editor shell, selection, inspection, click selection, highlight, and source/raw row visibility. |
| `PH-3` | Implemented / GUI check pending | Impact analyzer and affected-station resolver. |
| `PH-4` | Implemented / GUI check pending | Safe edits through existing source owners. |
| `PH-5` | Current / In progress | Dedicated `CrossSectionEditPlan` object. |
| `PH-6` | Pending | Range and transition edits. |
| `PH-7` | Pending | Advanced editing UX. |

## Goal

Extend `Cross Section Viewer` into a controlled `Cross Section Editor`.

The editor should let users inspect a generated station section, select semantic section elements, and apply edits through stable source data or explicit overrides.

Core principles:

- Keep the current viewer payload, layout, and export pipeline.
- Do not edit generated section wires as source geometry.
- Store edits in source objects or explicit edit override objects.
- Treat geometry edits as span-aware by default.
- Require an impact preview for edits that can affect adjacent stations or downstream corridor surfaces.

## Recommendation

Do not rebuild the viewer from scratch.

Refactor the existing viewer first, then add editor behavior.

The current viewer already provides useful foundation:

- `SectionSet.resolve_viewer_station_rows(...)`
- `SectionSet.resolve_viewer_payload(...)`
- station-local `component_segment` rows
- scope-aware filtering for `typical`, `side_slope`, and `daylight`
- shared layout plan rows
- Qt scene rendering
- PNG / SVG / Sheet SVG export
- display-unit conversion
- regression smoke tests

The main problem is organization. [task_cross_section_viewer.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/ui/task_cross_section_viewer.py) currently owns UI, layout planning, summary generation, Qt rendering, SVG rendering, export, and navigation. Editor behavior should not be added directly into that file without first separating the core pieces.

## Source Of Truth

The following `SectionSet` properties are generated results or result summaries:

- `StationValues`
- `SectionComponentSegmentRows`
- `SectionProfileRows`
- generated `Shape`
- child `SectionSlice` objects
- viewer payload

The editor must not treat these as durable edit sources. They are rebuilt during recompute.

Durable edits should be stored in one of these owners:

- `TypicalSectionTemplate`
- `AssemblyTemplate`
- `RegionPlan`
- future `CrossSectionEditPlan`
- future station/range override rows

## Architecture Overview

### Viewer Core

Split current viewer logic into reusable modules.

Proposed files:

- `freecad/Corridor_Road/ui/cross_section/payload.py`
- `freecad/Corridor_Road/ui/cross_section/layout.py`
- `freecad/Corridor_Road/ui/cross_section/qt_renderer.py`
- `freecad/Corridor_Road/ui/cross_section/svg_renderer.py`
- `freecad/Corridor_Road/ui/cross_section/summary.py`

Responsibilities:

- display-unit conversion
- payload normalization
- layout plan generation
- Qt rendering
- SVG and Sheet SVG rendering
- summary text generation

### Editor Task Panel

Proposed file:

- `freecad/Corridor_Road/ui/task_cross_section_editor.py`

Responsibilities:

- active `SectionSet` and station selection
- 2D selection and hit testing
- selected component inspector
- edit form
- scope selection
- adjacent-station impact preview
- apply / cancel / revert
- recompute and refresh

### Edit Data Model

Add an explicit edit source for fine-grained local edits.

Recommended object:

- `CrossSectionEditPlan`

Recommended row lists:

- `ComponentOverrideRows`
- `SideSlopeOverrideRows`
- `BenchOverrideRows`
- `DaylightOverrideRows`
- `PavementOverrideRows`
- `StationNoteRows`
- `ValidationRows`

Every geometry override row should include:

- `EditId`
- `TargetKind`
- `TargetId`
- `Side`
- `StartStation`
- `EndStation`
- `TransitionIn`
- `TransitionOut`
- `ApplyMode`
- `RegionId`
- `Parameter`
- `Value`
- `Source`
- `Enabled`
- `Notes`

Example row:

```text
kind=component_override|id=EDIT_001|target=LANE-L|side=left|parameter=Width|value=3.750|start=20.000|end=40.000|tin=5.000|tout=5.000|apply=range|region=BASE_02|enabled=true
```

## Edit Scope Model

Every edit must have an explicit scope.

### Presentation

Use for visual-only settings:

- label visibility
- dimension visibility
- export options
- annotation color
- diagnostics visibility

Rules:

- Store as UI preference or viewer state.
- No recompute.
- No adjacent-station analysis.

### Current Station Only

Use for rare station-specific exceptions or review metadata.

Rules:

- Safe for notes and review flags.
- Risky for geometry edits.
- Geometry edits must show a warning that corridor surfaces may kink or twist.
- Store as an explicit station override, never by editing generated wire vertices.

Recommended storage:

```text
apply=station|station=25.000|transition=none
```

### Station Range

Use for local design changes across a known interval:

- local widening
- local side-slope change
- ditch treatment over a span
- bench behavior over a span
- daylight behavior over a span

Rules:

- Require `StartStation` and `EndStation`.
- Support `TransitionIn` and `TransitionOut`.
- Include boundary and transition stations in section generation.
- Show affected previous/current/next stations before apply.

Recommended storage:

```text
apply=range|start=20.000|end=50.000|tin=5.000|tout=5.000
```

### Active Region

Use for design-intent edits.

Good examples:

- this region uses another typical section
- this region widens
- this bridge approach disables daylight
- this retaining-wall zone uses a special side policy
- this zone should split or skip corridor generation

Rules:

- Resolve the active base and overlay regions at the current station.
- Prefer `RegionPlan` fields when the edit maps to existing region semantics.
- If multiple overlay regions are active, the editor must ask the user to choose the owner.
- Ensure region boundaries and transitions are included in `StationValues`.

Recommended storage:

```text
apply=region|region=BASE_02|parameter=TemplateName|value=urban_complete_street
```

### New Region From Edit

Use when the user edits from a station view but the change clearly needs a durable design span.

Rules:

- Create a new overlay region or split an existing base region.
- Derive the initial span from nearest stations or explicit user range.
- Add transition-in/out defaults.
- Store the design intent in `RegionPlan` when possible.
- Use `CrossSectionEditPlan` only for parameters not supported by `RegionPlan`.

## Parameter Impact Classes

### Class A: Presentation Only

Does not affect section geometry.

Examples:

- labels on/off
- dimensions on/off
- export scale
- summary diagnostics
- selected station navigation

Handling:

- No recompute.
- No adjacent-station check.
- Store outside engineering source data.

### Class B: Local Metadata

Does not change generated geometry, but belongs to station review.

Examples:

- station note
- review status
- issue tag
- approval flag

Handling:

- Store in `CrossSectionEditPlan` or a future review-note object.
- Station-only scope is safe.
- No corridor recompute required.

### Class C: Component Geometry

Changes finished-grade top profile or component subdivision.

Examples:

- lane width
- shoulder width
- median width
- curb width
- ditch width
- ditch shape
- ditch depth
- ditch back slope
- berm width
- berm slope
- cross slope
- component enabled flag
- component order

Handling:

- Do not edit `SectionComponentSegmentRows` directly.
- Global edit: update `TypicalSectionTemplate`.
- Local edit: use active `RegionPlan` or `CrossSectionEditPlan`.
- Require scope: active region, station range, or explicit station-only exception.
- Run adjacent-station impact analysis before apply.

### Class D: Side Slope / Bench / Daylight Geometry

Changes roadside or terrain tie-in behavior.

Examples:

- side slope width
- side slope percentage
- cut/fill slope policy
- bench drop
- bench width
- bench slope
- repeat bench to daylight
- daylight auto on/off
- daylight max search width
- left/right daylight disable

Handling:

- Global edit: update `AssemblyTemplate`.
- Local policy edit: prefer `RegionPlan`.
- Fine-grained local edit: use `CrossSectionEditPlan`.
- Always show adjacent-station impact.
- Mark downstream corridor and earthwork results stale if daylight behavior changes.

### Class E: Structure-Affected Geometry

Changes or conflicts with structure interaction.

Examples:

- culvert crossing section treatment
- bridge approach treatment
- retaining-wall zone behavior
- skip zone around structure
- structure-driven daylight disable

Handling:

- `StructureSet` remains the structure source.
- Editor can propose Region or EditPlan overrides around the structure span.
- Do not edit structure overlay linework as source geometry.
- Show conflict and precedence if edit overlaps a structure span.

Recommended precedence:

1. structure safety override
2. Region overlay override
3. Region base override
4. `CrossSectionEditPlan` range override
5. `CrossSectionEditPlan` station override
6. `TypicalSectionTemplate`
7. `AssemblyTemplate`

### Class F: Alignment / Station Frame

Changes the station coordinate frame.

Examples:

- horizontal alignment
- vertical profile
- station equation
- centerline frame
- normal vector

Handling:

- Out of scope for Cross Section Editor.
- Editor may navigate to alignment/profile tools.
- Do not modify from the cross-section canvas.

## Adjacent Station Impact Design

Geometry edits must be evaluated as corridor edits, not isolated drawing edits.

### Why Adjacent Stations Matter

Corridor surfaces are built by connecting consecutive station sections. If only one station changes, the surface between previous/current/next stations may:

- twist
- kink
- self-intersect
- produce abrupt daylight transitions
- create unstable cut/fill quantities
- lose component topology consistency

### Impact Analyzer Inputs

- active `SectionSet`
- active station
- selected target row
- parameter name
- old value
- new value
- source object
- active region metadata
- active structure metadata
- existing `StationValues`
- downstream object list

### Impact Analyzer Steps

1. Classify parameter impact class.
2. Resolve recommended edit scope.
3. Resolve active base and overlay regions.
4. Resolve affected station span.
5. Detect missing boundary stations.
6. Detect transition requirements.
7. Detect structure overlap.
8. Compare previous/current/next station geometry.
9. Report downstream recompute requirements.
10. Produce an apply plan.

### Default Scope Rules

Recommended defaults:

- Class A: presentation
- Class B: current station
- Class C: active region if available, otherwise station range
- Class D: active region if available, otherwise station range
- Class E: active structure span or active region
- Class F: blocked

### Affected Span

For range and region edits:

```text
effective_start = StartStation - TransitionIn
effective_end   = EndStation + TransitionOut
```

Affected stations include:

- existing stations inside `[effective_start, effective_end]`
- start station
- end station
- transition-in start
- transition-in end
- transition-out start
- transition-out end
- region boundary stations
- structure boundary stations if overlapped

### Boundary Station Strategy

If an edit boundary is missing from `StationValues`, do not rely on coarse interval sampling.

For Region edits:

- enable or preserve `IncludeRegionBoundaries`
- enable or preserve `IncludeRegionTransitions`

For EditPlan edits:

- add `EditBoundaryStationRows`
- merge those stations in `SectionSet.resolve_station_values(...)`

This prevents a local edit from being invisible at the exact start/end stations.

### Transition Evaluation

Numeric parameters can interpolate.

For parameter `p`:

```text
if station < StartStation:
    t = (station - (StartStation - TransitionIn)) / TransitionIn
    value = lerp(base_value, target_value, clamp(t, 0, 1))
elif StartStation <= station <= EndStation:
    value = target_value
else:
    t = (station - EndStation) / TransitionOut
    value = lerp(target_value, base_value, clamp(t, 0, 1))
```

Non-numeric parameters should not interpolate.

Examples:

- ditch shape
- component type
- enabled flag
- daylight mode
- corridor policy

For non-numeric changes:

- switch at boundary
- require boundary stations
- warn if topology changes between adjacent stations

### Topology Change Detection

The impact analyzer should compare previous/current/next station payloads.

Detect:

- component added
- component removed
- component order changed
- left/right extent changed
- daylight side appears
- daylight side disappears
- structure overlay begins or ends
- section polyline point count changes sharply

Recommended warning thresholds:

- width delta: `0.50 m`
- elevation delta: `0.20 m`
- component topology change: any add/remove/reorder
- daylight topology change: any side appears/disappears

### Preview Output

Before apply, show:

- active station
- previous station
- next station
- affected range
- affected station count
- boundary stations to add
- active region owner
- structure overlap
- topology warnings
- downstream objects to recompute or mark stale

## Region Strategy

Region should be the preferred unit for design-intent edits.

Use Region when the edit means:

- this span has a different typical section
- this span has widening
- this span disables daylight
- this span changes side policy
- this span has bridge/retaining-wall/ditch behavior
- this span should split or skip corridor generation

Do not use Region for:

- temporary station notes
- annotation placement
- export settings
- visual labels
- one-off diagnostics

### Mapping Editor Actions To RegionPlan

| Editor operation | Preferred RegionPlan field |
| --- | --- |
| apply different typical section | `TemplateName` |
| apply different assembly | `AssemblyName` |
| disable left daylight | `DaylightPolicy=left:off` |
| disable right daylight | `DaylightPolicy=right:off` |
| replace roadside with berm | `SidePolicy=left:berm` or `right:berm` |
| split corridor only | `CorridorPolicy=split_only` |
| omit corridor body | `CorridorPolicy=skip_zone` |

If no RegionPlan field exists, store the edit in `CrossSectionEditPlan`.

## Editable Items

### Editable Through Existing Sources

- Assembly simple widths
- Assembly side slope widths
- Assembly side slope percentages
- Assembly bench rows
- Typical section component rows
- Typical section pavement rows
- Region side policy
- Region daylight policy
- Region corridor policy
- Region template/assembly references
- viewer/export settings

### Editable Through New Override Model

- local component width override
- station range widening
- station range ditch shape override
- station range cross slope override
- local daylight on/off
- local bench override
- station review notes
- transition-aware component parameter changes

### Not Editable In Cross Section Editor

- generated section wire vertices as source geometry
- `SectionProfileRows` as source data
- `SectionComponentSegmentRows` as source data
- terrain mesh vertices
- horizontal alignment geometry
- vertical alignment geometry
- structure source geometry
- final corridor surface mesh

The editor may display these items and link to their owner tools, but should not mutate them directly.

## UI Modes

### Review Mode

Equivalent to current viewer:

- station navigation
- section rendering
- scope toggles
- dimensions
- summaries
- export

### Select Mode

Adds semantic selection:

- component marker hit testing
- section segment hit testing
- selected component highlight
- source owner display
- raw row display

### Edit Mode

Adds controlled editing:

- parameter form
- scope selector
- impact preview
- apply / cancel
- recompute and refresh

## Edit Panel

The edit panel should show:

- selected station
- selected component id
- selected component type
- side
- scope
- source owner
- editable parameters
- current value
- new value
- display unit
- edit scope
- affected stations
- warnings

## Data Flow

### Review Flow

```text
SectionSet
  -> resolve_viewer_payload
  -> display payload
  -> layout plan
  -> Qt/SVG render
```

### Edit Flow

```text
User selects component
  -> editor resolves editable target
  -> user changes parameter
  -> impact analyzer classifies change
  -> user confirms scope
  -> edit writes to source or override
  -> SectionSet recompute
  -> viewer refreshes payload
```

### Recompute Flow

For source edits:

```text
TypicalSectionTemplate / AssemblyTemplate / RegionPlan
  -> mark SectionSet stale
  -> recompute SectionSet
  -> recompute dependent Corridor or mark it stale
```

For edit-plan edits:

```text
CrossSectionEditPlan
  -> SectionSet reads active overrides during build_section_wires
  -> SectionSet merges edit boundary stations
  -> SectionSet produces updated wires and component segment rows
```

## Required SectionSet Extensions

### EditPlan Link

Add optional properties:

```text
SectionSet.CrossSectionEditPlan
SectionSet.UseCrossSectionEditPlan
```

### Station Merge

Extend station resolution:

```text
SectionSet.resolve_station_values(...)
  + edit boundary stations
  + edit transition stations
```

### Runtime Override Context

Extend runtime context merging:

```text
runtime_context = merge(
    region_context,
    structure_context,
    cross_section_edit_context,
)
```

### Component Segment Rows

When edit overrides affect components, generated rows should preserve edit metadata:

```text
kind=component_segment|station=25.000|side=left|id=LANE-L|type=lane|scope=typical|x0=-3.750|x1=0.000|width=3.750|source=cross_section_edit|editId=EDIT_001|override=true
```

## Persistence Models

### Global Template Edit

Use when the user intentionally edits all sections using a template.

Pros:

- simple
- existing toolchain supports it
- all sections update consistently

Cons:

- affects every user of the template
- unsuitable for local widening

### Region Edit

Use for most design-intent local edits.

Pros:

- span-aware
- boundary-aware
- compatible with current RegionPlan workflow
- suitable for corridor behavior

Cons:

- current RegionPlan does not cover every fine-grained component parameter

### CrossSectionEditPlan

Use for station/range edits not expressible through current RegionPlan.

Pros:

- precise
- explicit
- auditable
- can support future migration to RegionPlan

Cons:

- requires new SectionSet integration
- requires validation and conflict rules

## Conflict Handling

Conflicts should be reported before apply and after recompute.

Conflict examples:

- edit enables daylight where structure disables daylight
- edit changes side slope inside retaining-wall zone
- station-only component topology differs from adjacent stations
- RegionPlan and EditPlan both target the same component parameter

Conflict output should appear in:

- impact preview
- `CrossSectionEditPlan.ValidationRows`
- `SectionSet.Status` or related diagnostic rows

## Validation Rules

Before apply:

- numeric values must be finite
- widths must be non-negative
- component order must be unique within side and scope
- ditch shape must be allowed
- transition length must be non-negative
- start station must be less than or equal to end station
- range must overlap the SectionSet station domain
- station-only geometry edit must show a warning

After apply:

- recompute `SectionSet`
- verify payload exists for edited station
- verify section bounds are non-empty
- verify component rows have valid spans
- verify required boundary stations are present
- verify downstream corridor object is recomputed or marked stale

## Development Phases

### PH-1: Refactor Viewer Core

Status: not started.

- split layout planner from task panel
- split SVG rendering from task panel
- split summary builder from task panel
- preserve current viewer behavior
- keep existing smoke tests passing

### PH-2: Selection And Inspection

Status: in progress. This is the current active development stage.

- add hit testing for planned component marker rows
- highlight selected component
- show source owner and raw component row
- expose read-only parameter table

Implemented so far:

- editor command and task panel shell
- target selector sourced from station-local component segments
- canvas click selection for visible planned component marker rows in `Select` / `Edit` modes
- selected component highlight overlay for combo-selected targets
- source owner display
- generated row and raw row preview
- read-only target details
- read-only parameter table
- impact-preview scaffold with previous/current/next station context

Remaining in this phase:

- finalize after FreeCAD GUI manual check

### PH-3: Impact Analyzer

Status: in progress. This is the current active development stage.

- implement parameter classification
- implement affected station resolver
- implement region ownership resolver
- implement structure overlap warnings
- show preview panel

Implemented so far:

- parameter classification: `geometry`, `topology`, `daylight`
- affected station resolver:
  - global source: all station rows
  - active region: contiguous station rows with matching region summary
  - station range: previous/current/next scaffold until range controls exist
  - current station only: selected station only
- region owner summary
- structure overlap warning and daylight/structure blocked-state preview
- boundary station and downstream stale/recompute preview

### PH-4: Safe Edits Through Existing Sources

Status: in progress. This is the current active development stage.

- allow global `TypicalSectionTemplate` edits
- allow global `AssemblyTemplate` edits
- allow `RegionPlan` policy edits
- recompute and refresh viewer

Implemented so far:

- first guarded apply path:
  - scope must be `Global Source`
  - selected component scope must be `typical`
  - generated source must be `typical_summary` or `assembly_template`
  - `typical_summary` edits require a linked `TypicalSectionTemplate`
  - `assembly_template` carriageway edits require a linked `AssemblyTemplate` and a left/right `carriageway` target
  - `assembly_template` side-width edits require a linked `AssemblyTemplate` and a primary left/right side-slope target
  - `assembly_template` side-slope percent edits require a linked `AssemblyTemplate`, selected edit parameter `Slope %`, and a primary left/right side-slope target
  - bench-aware side edits preserve configured bench rows and do not edit individual bench row width/drop/slope values yet
  - `RegionPlan` side/daylight policy edits require `Active Region` scope, a linked RegionPlan, enabled `ApplyRegionOverrides`, and an active base-region id at the current station
  - component type must be width-like and not topology/extra-width driven
- write path:
  - update `TypicalSectionTemplate.ComponentWidths[index]`
  - or update `AssemblyTemplate.LeftWidth` / `AssemblyTemplate.RightWidth`
  - or update `AssemblyTemplate.LeftSideWidth` / `AssemblyTemplate.RightSideWidth`
  - or update `AssemblyTemplate.LeftSideSlopePct` / `AssemblyTemplate.RightSideSlopePct`
  - or update the active base region `SidePolicy` / `DaylightPolicy` through `RegionPlan.apply_records(...)`
  - touch edited source object and SectionSet
  - recompute active document
  - refresh editor at the current station
- edit record path:
  - append `cross_section_editor_edit|...` rows to `SectionSet.CrossSectionEditorEditRows`
  - update `SectionSet.CrossSectionEditorLastEditSummary`
  - keep only the latest 100 edit rows
- validation row path:
  - show `validation|phase=PH-4|...` rows in the editor before apply
  - record the latest successful apply validation rows to `SectionSet.CrossSectionEditorValidationRows`
  - update `SectionSet.CrossSectionEditorLastValidationSummary`
- downstream stale path:
  - detect objects linked through `SourceSectionSet`
  - detect secondary outputs linked through `SourceCorridor` or `SourceDesignSurface`
  - show `validation|phase=PH-4|level=warn|code=downstream_stale|...` before apply
  - set `NeedsRecompute=True` where available after successful apply
  - keep `Corridor` stale state internal, and use `Status=NEEDS_RECOMPUTE...` / `[Recompute]` label marking for downstream generated outputs

Still pending:

- individual bench-row width/drop/slope edits
- station range edits through `CrossSectionEditPlan`
- richer conflict validation against downstream object geometry/content conflicts

### PH-5: CrossSectionEditPlan Object

Status: in progress. This is the current active development stage.

- add object and properties: implemented
- add row parser/serializer: implemented
- link from `SectionSet`: implemented
- add edit boundary station merge: implemented
- add runtime override context: implemented for side-slope `width` / `slope_pct` and typical-component `width` / `cross_slope_pct`

Implemented so far:

- added [obj_cross_section_edit_plan.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/objects/obj_cross_section_edit_plan.py)
- stores edit ids, enabled flags, scopes, start/end stations, transition distances, target metadata, parameter, value, unit, source scope, and notes
- writes structured `cross_section_edit|...` rows to `CrossSectionEditPlan.EditRows`
- validates duplicate ids, missing target/parameter, invalid scope, reversed ranges, and station-scope range mismatch
- exposes active-record lookup at a station
- exposes boundary station values including transition-in and transition-out stations
- added `SectionSet.CrossSectionEditPlan`
- added `SectionSet.UseCrossSectionEditPlan`
- added `SectionSet.ResolvedCrossSectionEditCount`
- added `SectionSet.ResolvedCrossSectionEditSummaryRows`
- merges edit-plan boundary and transition stations into `SectionSet.resolve_station_values(...)`
- applies active edit-plan side-slope `width` / `slope_pct` overrides during `build_section_wires`
- applies active edit-plan typical-component `width` / `cross_slope_pct` overrides during `build_section_wires`
- marks edited side-slope component rows as `source=cross_section_edit` with `editId=...`
- marks edited typical component rows as `source=cross_section_edit` with `editId=...`
- records active override hit count on `SectionSet.CrossSectionEditOverrideHitCount`
- adds editor-side `Station Range` / `Current Station Only` apply paths that create or update linked `CrossSectionEditPlan` rows
- extends PH-5 editor apply to local typical-component width / `cross_slope_pct` edits
- auto-creates and links `CrossSectionEditPlan` from `Cross Section Editor` when needed
- records PH-5 editor applies on `SectionSet` edit/validation summary rows
- adds editor smoke coverage for range + station-only apply flows, including typical-component width / `cross_slope_pct` edits

Still pending:

- extend typical/local runtime overrides beyond width and `cross_slope_pct` into richer component parameters

### PH-6: Range And Transition Edits

Status: pending.

- implement numeric interpolation
- add boundary station rows
- add station/range visualization
- validate adjacent station continuity

### PH-7: Advanced Editing

Status: pending.

- before/after overlay
- drag handles for width-like parameters
- daylight override preview
- conflict resolution UI
- migration from EditPlan override to RegionPlan override

## MVP Scope

The first useful editor should support:

- component selection in the current viewer drawing
- read-only source/parameter inspector
- edit width for a selected component
- choose scope:
  - global template
  - active region
  - station range
- impact preview
- apply through existing source where possible
- recompute `SectionSet`
- refresh viewer

Do not include in the MVP:

- freeform vertex editing
- direct mesh editing
- drag editing for every parameter
- structure geometry editing
- alignment/profile editing

## Open Questions

1. Should `CrossSectionEditPlan` be one object per project, per SectionSet, or per editor workflow?
2. Should station-only geometry edits be hidden behind an advanced option?
3. Should RegionPlan gain generic component override fields?
4. Should downstream Corridor recompute automatically or only be marked stale?
5. How much visual before/after diff is required for the MVP?

## Summary

`Cross Section Editor` should be a controlled parameter editor, not a generated-wire editor.

The durable workflow should be:

```text
view generated station payload
  -> select semantic component
  -> edit source or explicit override
  -> analyze adjacent station impact
  -> apply with scope and transition policy
  -> recompute and refresh
```

For geometry-affecting edits, active Region or station range should be the default unit. Current-station-only edits should remain explicit exceptions with warnings and audit rows.

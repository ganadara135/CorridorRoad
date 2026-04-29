# CorridorRoad V1 Cross Section Viewer Work Checklist

Date: 2026-04-23
Branch: `v1-dev`
Status: Active implementation checklist, refreshed after viewer promotion work
Depends on:

- `docsV1/V1_CROSS_SECTION_VIEWER_EXECUTION_PLAN.md`
- `docsV1/V1_CROSS_SECTION_2D_MANUAL_QA.md`
- `docsV1/V1_VIEWER_PLAN.md`
- `docsV1/V1_SECTION_OUTPUT_SCHEMA.md`

## 1. Purpose

This checklist translates the cross-section viewer execution plan into concrete code tasks.

It should be used as the short-horizon implementation checklist for the first promoted v1 review UI.

## 2. Current Code Baseline

Current implementation entry points:

- command bridge: `freecad/Corridor_Road/v1/commands/cmd_view_sections.py`
- v1 viewer task panel: `freecad/Corridor_Road/v1/ui/viewers/cross_section_viewer.py`
- existing v0 viewer bridge: `freecad/Corridor_Road/ui/task_cross_section_viewer.py`
- handoff helper: `freecad/Corridor_Road/v1/ui/common/legacy_handoff.py`
- preview contract tests: `tests/contracts/v1/test_section_command_bridge.py`

## 3. Milestone A: Stable Read-Only Viewer Shell

- [x] standalone v1 section review command exists
- [x] v1 viewer task panel opens from command
- [x] current station summary is shown
- [x] station label is shown
- [x] component rows are shown
- [x] quantity rows are shown
- [x] focused component summary line is supported
- [x] rename visible UI strings from `Preview` toward `Viewer` when promotion begins
- [x] add explicit stale/current result indicator in the v1 viewer UI
- [x] add direct open path from preferred review command without relying on existing v0 viewer bridge wording

## 4. Milestone B: Source Inspector Baseline

- [x] viewer context rows are shown
- [x] viewer source rows are shown
- [x] focused source-row selection is supported
- [x] add dedicated `Source Inspector` section instead of only mixed context tables
- [x] show explicit source owner fields:
  - `Template`
  - `Region`
  - `Structure`
  - `Section Set`
- [x] show selected component id, kind, side, and ownership in one compact panel
- [x] show unresolved ownership state explicitly when source tracing is incomplete
- [x] add source-inspector-specific contract tests

## 5. Milestone C: Editor Handoff and Return

- [x] handoff to `Typical Section` editor exists
- [x] handoff to `Region` editor exists
- [x] handoff to `Structure` editor exists
- [x] station context is passed through handoff
- [x] component context is passed through handoff
- [x] same-context return path exists through existing v0 editors
- [x] show active handoff context more clearly in the v1 viewer status area
- [ ] verify structure handoff selects linked `StructureSet` consistently in real documents
- [ ] add explicit return-state tests for `viewer -> editor -> viewer`
- [x] document preferred handoff flow in a short manual QA scenario note

## 6. Milestone D: Review-Quality Improvements

- [x] focused component highlighting exists
- [x] structure summary can be shown in viewer context
- [x] render terrain interaction rows in the main viewer UI
- [x] render structure interaction rows in the main viewer UI
- [x] render diagnostic rows as first-class review content
- [x] attach earthwork hint rows where available
- [x] add `Previous/Next` navigation controls using full station rows
- [x] add bookmark or issue marker placeholder state in the viewer

## 6A. Milestone D2: Drawing-Style 2D Section Preview

- [x] define v1 `CrossSectionDrawingPayload`
- [x] generate drawing payload from `AppliedSectionSet`
- [x] map `AppliedSectionPoint` rows into offset/elevation section geometry
- [x] generate FG drawing line from station-local applied section data
- [x] generate subgrade drawing line from station-local applied section data
- [x] generate ditch/drainage drawing spans from `ditch_surface` points
- [x] generate slope-face drawing spans from daylight policy/result rows
- [x] generate component label rows from v1 component or point roles
- [x] generate value rows for component dimensions when available
- [x] generate lower-band dimension rows for total width and component widths
- [x] port v0-style label collision/placement rules into v1 drawing payload rendering
- [x] render the 2D drawing in a dominant canvas area
- [x] keep `Show dimensions` behavior
- [x] keep dark-mode readable drawing colors
- [x] add contract tests for geometry rows, label rows, and dimension rows
- [x] add manual QA procedure against v0-style expected section drawing behavior
- [ ] execute manual QA against v0-style expected section drawing behavior on a real document

## 7. Command and Workflow Promotion

- [x] standalone command `CorridorRoad_V1ViewSections` exists
- [x] existing v0 viewer can open the v1 viewer
- [x] decide whether the main review command should now route to v1 first
- [x] update command labels/tooltips from `Preview` to `Viewer` when switch happens
- [x] update workflow docs to recommend v1 viewer first
- [x] mark existing v0 viewer as secondary review path in user-facing docs

## 8. Testing Checklist

- [x] contract test for basic section preview
- [x] contract test for extra-context merge
- [x] contract test for focused component summary
- [x] add contract test for stale/current status payload
- [x] add contract test for source-inspector ownership fields
- [ ] add contract test for terrain/structure/diagnostic rows rendering
- [x] add manual QA checklist for one real corridor document

## 9. Immediate Next Coding Order

Recommended next implementation order:

1. execute manual QA against v0-style expected section drawing behavior on a real document
2. verify structure handoff selects linked `StructureSet` consistently in real documents
3. add explicit return-state tests for `viewer -> editor -> viewer`

## 10. Promotion Gate

The viewer should be treated as ready for default-path promotion when all of the following are true:

- [x] source inspector is explicit and readable
- [ ] terrain/structure/diagnostic review data is visible
- [ ] handoff and return are stable on real documents
- [ ] stale/current state is visible
- [x] workflow docs recommend the v1 viewer first

## 11. Final Rule

Do not spend the next viewer cycle adding more bridge complexity before the v1 viewer clearly presents source ownership, review diagnostics, and state.

Those three items are the shortest path from "working preview" to "real v1 viewer."

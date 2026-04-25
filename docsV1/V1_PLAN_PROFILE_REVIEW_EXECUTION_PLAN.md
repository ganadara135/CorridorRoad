# CorridorRoad V1 Plan Profile Review Execution Plan

Date: 2026-04-25
Branch: `v1-dev`
Status: Draft baseline, station interval review control complete
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_UX_RESET_PLAN.md`
- `docsV1/V1_REVIEW_STAGE_SPLIT_PLAN.md`
- `docsV1/V1_PLAN_OUTPUT_SCHEMA.md`
- `docsV1/V1_PROFILE_OUTPUT_SCHEMA.md`
- `docsV1/V1_IMPLEMENTATION_PHASE_PLAN.md`

## 1. Purpose

This document defines how `Plan/Profile Review` should become an early v1-native review UI for the stationing/profile stage.

It exists to define:

- what the v1 plan/profile review screen is responsible for
- how it differs from source editors and sheet outputs
- what implementation milestones are needed before it becomes the preferred review path
- how it should interact with source editors during transition

## 2. Product Goal

The goal is to create one coherent v1 review surface for:

- horizontal alignment review
- profile review
- station-focused context review after stationing exists
- editor handoff and same-context return
- issue detection and rebuild verification

This screen should become the preferred place to inspect rebuilt stationing/profile results, while source editors continue to handle durable source editing during transition.

## 3. Definition of Promotion

`Plan/Profile Review` is considered promoted when:

- users can open a v1-native plan/profile review panel directly
- the review panel consumes normalized `PlanOutput` and `ProfileOutput`
- station focus and selected-row context are preserved through editor handoff
- ordinary plan/profile review no longer depends on existing v0 review logic

## 4. Relationship to Other UI

`Plan/Profile Review` is:

- a review surface
- a rebuild verification surface
- a source-trace and handoff surface

It is not:

- the main alignment authoring editor
- the main vertical profile authoring editor
- a drawing sheet generator

Practical relationship:

- existing v0 `Edit Alignment`, `Edit Profiles`, and `Edit PVI` remain source editors for now
- v1 `Plan/Profile Review` becomes the preferred place to inspect results after stationing/profile context exists
- `Review Alignment` should remain a separate earlier-stage concept

## 5. Difference From Sheet Outputs

This execution plan is about interactive review UI, not deliverable sheets.

Rules:

- review UI is interactive and context-aware
- sheets remain deliverables derived from normalized output contracts
- review UI may use the same outputs as sheets, but it should not be organized like a drawing layout engine

## 6. Scope of the First Promoted Review UI

The first promoted v1 plan/profile review screen should include:

- alignment summary
- profile summary
- plan geometry row inspection
- profile control row inspection
- focused station context
- source context summary
- handoff to `Edit Alignment`, `Edit Profiles`, and `Edit PVI`
- same-context return after save/rebuild
- current/stale result visibility

It does not yet need:

- full drawing-sheet presentation
- full mass-haul review integration
- advanced alternative comparison
- final AI review integration

## 7. Minimum Functional Milestones

### 7.1 Milestone A: Stable read-only review shell

Required outcomes:

- v1 review command opens reliably
- `PlanOutput` and `ProfileOutput` render in a readable review panel
- station focus appears in summary and row selection
- missing-stationing state is explicit when prerequisites are absent

Completion signal:

- users can inspect plan/profile outputs without opening a source editor first

### 7.2 Milestone B: Focused context review

Required outcomes:

- focused station is visible
- selected row context is visible
- row highlighting follows station focus where practical

Completion signal:

- a user can tell what station or row is under review without reading raw object properties

### 7.3 Milestone C: Editor handoff and return

Required outcomes:

- handoff to `Edit Alignment`
- handoff to `Edit Profiles`
- handoff to `Edit PVI`
- same-context return after save/rebuild

Completion signal:

- `review -> editor -> review` roundtrip is reliable for ordinary workflow

### 7.4 Milestone D: Review-quality improvements

Required outcomes:

- clearer plan/profile status summary
- profile issue rows or diagnostic rows where available
- optional earthwork attachment hints in profile context

Completion signal:

- the review screen is useful for real design verification, not just bridge testing

### 7.5 Milestone E: Preferred review path switch

Required outcomes:

- documentation and workflow favor v1 plan/profile review first
- existing v0 source editors remain available but are no longer treated as the main review surface

Completion signal:

- normal plan/profile result review can be done in the v1 screen without depending on old review behavior

## 8. Data Contract Requirements

The promoted screen must rely on:

- `PlanOutput`
- `ProfileOutput`
- optional earthwork attachment rows
- source context payload
- station focus payload
- evaluated alignment frame rows from `AlignmentEvaluationService`

It must not rely on:

- direct parsing of source editor table widgets
- drawing-sheet layout logic
- raw FreeCAD document inspection as the primary review data source

## 9. UI Requirements

Recommended first layout:

- top summary block
- plan summary table
- profile summary table
- context panel
- handoff button row

The UI should visibly present:

- alignment identity
- profile identity
- focused station
- selected row context
- source panel context
- stale/current result state

## 10. Command Strategy

During transition:

- keep the v1 plan/profile review command as a standalone entry
- keep editor connections only as temporary implementation support
- use the v1 review screen as the preferred post-edit verification target
- expose a main `Plan/Profile Viewer` review command that opens the v1 viewer first
- use source editors as authoring tools, not as the normal review center

Longer term:

- plan/profile review should be the normal review command
- existing v0 editors should remain authoring tools until a full v1 editor replacement exists

## 11. Testing and Validation

The promoted review screen should be validated through:

- contract tests for preview payload and extra-context merge
- focused-station tests
- selected-row summary tests
- handoff tests
- same-context return tests
- manual testing with a real document

Current implementation status:

- [x] key station rows are enriched with evaluated `x`, `y`, `tangent_direction_deg`, and active element metadata when an `AlignmentModel` exists
- [x] the Plan/Profile viewer shows an `Alignment Frame` table for evaluated station rows
- [x] the text summary reports evaluated alignment station count
- [x] `PlanOutput.station_rows` are generated from the shared `AlignmentStationSamplingService`
- [x] key station navigation uses the sampled station grid while keeping the visible list compact around the current station
- [x] `ProfileOutput.line_rows` can include a TIN-sampled `existing_ground_line`
- [x] the Plan/Profile viewer shows profile line rows, including FG and EG when available
- [x] FG/EG profile comparison can attach `profile_cut_depth` and `profile_fill_depth` hint rows
- [x] explicit-width profile area hints can attach `profile_cut_area` and `profile_fill_area` rows
- [x] Plan/Profile viewer can apply `earthwork_area_width` through viewer context and reopen the v1 review
- [x] Plan/Profile viewer can display Earthwork Review handoff context for earthwork window, cut/fill, and haul-zone summaries
- [x] Earthwork attachment rows show their `kind` in the Plan/Profile viewer
- [x] Preview payload reports whether it is using the active document bridge or demo fallback through `preview_source_kind`
- [x] Plan/Profile viewer shows `Alignment/Profile Bridge Diagnostics` rows for source mode, legacy object resolution, model build status, alignment/profile ID link, and profile station range fit
- [x] text summary reports bridge diagnostic counts so document-vs-demo and link issues are visible without inspecting raw payloads
- [x] `ProfileEvaluationService` evaluates station-based FG elevation, grade, active segment, status, and active vertical-curve metadata
- [x] `ProfileEvaluationService` now evaluates PVI-centered parabolic vertical curves for FG elevation and grade
- [x] key station rows now carry both alignment frame data and profile evaluation data for the same station domain
- [x] Plan/Profile viewer shows a `Profile Evaluation` table for station, elevation, grade, active segment, active curve, and status
- [x] document preview now prefers native `V1Stationing` rows for `PlanOutput.station_rows` and key-station navigation when available
- [x] document preview now prefers native `V1Alignment` source objects before legacy horizontal alignment adapters
- [x] document preview now prefers native `V1Profile` source objects before legacy vertical alignment adapters
- [x] sample v1 profile creation feeds Plan/Profile Review with a matched alignment/profile pair and reports an `alignment_profile_link` diagnostic status of `ok`
- [x] Plan/Profile viewer's alignment handoff now opens the single v1 `Alignment` command for native alignment-source edits
- [x] v1 alignment editing intentionally excludes direct `Review Plan/Profile` and `Next: Generate Stations` actions from the alignment-stage editor
- [x] Plan/Profile viewer's profile handoff now opens `Edit Profile (v1)` for native profile-source edits
- [x] `Edit Profile (v1)` can apply edited PVI rows and reopen Plan/Profile Review with focused station context
- [x] configurable station interval is available in Plan/Profile Review and feeds plan station rows, key station rows, and TIN-based EG sampling
- [x] sampled FG profile lines now use the same profile evaluation service, so vertical curves affect Profile Lines and EG/FG hints
- [x] `Generate Stations (v1)` creates a routed `V1Stationing` object under `02_Alignment & Profile / Stations`

Focused validation:

```powershell
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_v1_alignment_source_object.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_v1_alignment_editor.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_v1_stationing_source_object.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_v1_profile_source_object.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_v1_profile_editor.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_alignment_station_sampling_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_profile_evaluation_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_profile_tin_sampling_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_profile_earthwork_hint_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_profile_earthwork_area_hint_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "ns={}; exec(open(r'tests\contracts\v1\test_alignment_profile_bridge_diagnostics.py', 'r', encoding='utf-8').read(), ns); [fn() for name, fn in sorted(ns.items()) if name.startswith('test_') and callable(fn)]; print('[PASS] v1 alignment/profile bridge diagnostics contract tests completed.')"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "ns={}; exec(open(r'tests\contracts\v1\test_plan_profile_command_bridge.py', 'r', encoding='utf-8').read(), ns); [fn() for name, fn in sorted(ns.items()) if name.startswith('test_') and callable(fn)]; print('[PASS] v1 plan/profile command bridge contract tests completed.')"
```

Current manual interval check:

1. open `Plan/Profile Review`
2. change `Station Interval`
3. click `Apply Station Interval`
4. confirm the viewer reopens and the summary reports the new interval
5. confirm plan station count and EG sampling density change when TIN is available

Minimum manual scenarios:

1. open review from `Edit Alignment`
2. confirm focused row and station context
3. return to `Edit Alignment`
4. save and reopen review
5. repeat with `Edit Profiles`
6. repeat with `Edit PVI`

## 12. Acceptance Criteria for Promotion

The v1 plan/profile review screen is ready to become the preferred review path when:

- it opens reliably on real documents
- station and selected-row context are clear
- editor handoff works for alignment, profile, and PVI
- same-context return works after save/rebuild
- the screen remains output-driven and read-only
- ordinary result review no longer depends on ad-hoc old review behavior

## 13. Non-Goals

Do not block promotion on:

- full editor replacement
- final drawing-sheet layout
- full 3D integration
- full earthwork review parity
- final AI candidate comparison

## 14. Follow-Up Documents

The next natural execution document after this one is:

1. `V1_EARTHWORK_REVIEW_EXECUTION_PLAN.md`

## 15. Final Rule

`Plan/Profile Review` should become the normal place to inspect rebuilt linear design results.

If the team must choose between preserving old review habits and strengthening output-driven v1 review, the v1 review path should win.

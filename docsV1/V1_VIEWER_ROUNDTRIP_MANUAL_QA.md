# CorridorRoad V1 Viewer Roundtrip Manual QA

Date: 2026-04-23
Branch: `v1-dev`
Status: Active manual QA note
Depends on:

- `docsV1/V1_CROSS_SECTION_VIEWER_EXECUTION_PLAN.md`
- `docsV1/V1_PLAN_PROFILE_REVIEW_EXECUTION_PLAN.md`
- `docsV1/V1_EARTHWORK_REVIEW_EXECUTION_PLAN.md`

## 1. Purpose

This note defines the manual QA scenarios for the current viewer roundtrip workflow:

- `v1 Viewer -> existing v0 editor -> v1 Viewer`

The goal is to verify that station context, selected object context, and return flow remain understandable and stable while the source editors are still shared with the existing v0 UI.

## 2. Scope

This note covers:

- `Cross Section Viewer`
- `Plan/Profile Viewer`
- `Earthwork Viewer`

It does not cover:

- final v1-only editors
- final 3D review
- AI review workflows
- export/output review workflows

## 3. Preconditions

Before running the scenarios:

1. open a real CorridorRoad FreeCAD document
2. confirm the document has at least:
   - alignment
   - vertical profile
   - section set
3. if possible, also confirm:
   - region plan
   - structure set
   - cut/fill or earthwork-related result objects

Recommended environment:

- FreeCAD executable: `D:\Program Files\FreeCAD 1.0\bin\FreeCAD.exe`
- command-line validation executable: `D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe`

Important interpretation note:

- if a viewer opens after creating a new project but before enough source objects exist, it may show demo payload text such as `Built from demo section viewer payload.`
- treat that as a valid command-routing check, but not as a successful real-document review pass

## 4. Cross Section Viewer Roundtrip

### 4.1 Open path

1. open `Cross Section Viewer`
2. verify:
   - the window title uses `Viewer`
   - `Current Focus` is visible
   - `Result State` is visible
   - `Key Stations` is visible
   - `Source Inspector` is visible
   - if `Built from demo section viewer payload.` is shown, record that separately and do not mark real-document data review as passed

### 4.2 Station navigation

1. select a different station in `Key Stations`
2. click `Open Selected Station`
3. verify:
   - the viewer reopens
   - `Current Focus` changed to the selected station
   - the selected station row is now marked as current
   - `Focused Component`, if present, still makes sense

### 4.3 Handoff to Typical Section

1. click `Open Typical Section`
2. verify:
   - the existing v0 `Edit Typical Section` task panel opens
   - the relevant source object is selected
   - station context is visible in the editor if supported

### 4.4 Return from editor

1. use `Open v1 Preview` or `Apply + v1 Preview` from the editor
2. verify:
   - the v1 `Cross Section Viewer` opens again
   - the station is still the expected station
   - the same section set is still in context
   - source ownership still points to the same template/region/structure family

### 4.5 Region / Structure repeat

Repeat the same roundtrip with:

- `Open Regions`
- `Open Structures`

Pass condition:

- all three handoff targets return to the expected station context

## 5. Plan/Profile Viewer Roundtrip

### 5.1 Open path

1. open `Plan/Profile Review (v1)`
2. verify:
   - the window title uses `Viewer`
   - `Current Focus` is visible
   - `Viewer Context` is visible
   - `Key Stations` is visible

### 5.2 Station navigation

1. choose another key station
2. click `Open Selected Station`
3. verify:
   - the viewer reopens
   - `Current Focus` shows the new station
   - `Profile Controls` selects the nearest row

### 5.3 Handoff to source editors

Run the following one by one:

- `Open Alignment`
- `Open Profiles`
- `Open PVI`

For each one verify:

- the intended existing v0 editor opens
- the relevant alignment/profile object is selected
- station context is carried if the editor supports it

### 5.4 Return from editor

From the editor, use:

- `Open v1 Preview`
- or `Apply + v1 Preview`
- or `Generate + v1 Preview`

Verify:

- `Plan/Profile Viewer` reopens
- the station remains close to the selected station
- `Current Focus` remains understandable
- the selected row summary still matches the user action

## 6. Earthwork Viewer Roundtrip

### 6.1 Open path

1. open `Earthwork Balance (v1)`
2. verify:
   - the window title uses `Viewer`
   - `Current Focus` is visible
   - `Key Stations` is visible
   - `Focused Window` appears in the summary when data exists

### 6.2 Station navigation

1. move to another key station
2. click `Open Selected Station`
3. verify:
   - the viewer reopens
   - `Focus Station` changed
   - `Focused Window` changed if a different balance row becomes nearest

### 6.3 Handoff to source editors

Run:

- `Open Alignment`
- `Open Profiles`
- `Open PVI`

Verify:

- the correct editor opens
- the station row is still carried through

### 6.4 Return path

From the opened editor, use the available return action and verify:

- a v1 viewer opens again
- if the flow returns through `Plan/Profile Viewer`, the station is still understandable
- if the user reopens `Earthwork Viewer`, the same station can be found again through `Key Stations`

## 7. Failure Signals

Mark the scenario as failed if any of the following happens:

- station changes unexpectedly after return
- a different source object opens than the one implied by the viewer
- `Current Focus` and actual selected row disagree
- `Key Stations` opens the same station repeatedly when a different station was selected
- handoff opens the correct editor but loses all usable context
- return path depends on the old review screen to recover context

## 8. Expected Temporary Limitations

The following are acceptable for now:

- some existing v0 editors may only partially show the station context
- return may come back through a bridge command rather than a fully native workflow
- the viewer may rely on normalized payloads plus bridge context instead of full live synchronization

These are not acceptable:

- silent station drift
- wrong object handoff
- wrong section/profile row emphasis after return

## 9. Recording Rule

When a real document scenario is run, record:

- document name
- viewer used
- station tested
- editor target used
- pass/fail
- short note about any context mismatch

## 10. Exit Rule

Do not promote any viewer as the preferred real-document review path until at least one successful real-document roundtrip has been recorded for that viewer family.

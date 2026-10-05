# Parametric Road V1 Unreleased Changes Manual QA

Date: 2026-09-28
Branch: `ganada_0902`
Status: Manual QA procedure. Execution is a FreeCAD GUI activity and is not covered by the headless gate.
Depends on:

- `CHANGELOG.md`, the `[Unreleased]` block this procedure verifies
- `docsV1/V1_INTERSECTION_SCOPE_AND_IMPROVEMENT_PLAN.md`
- `docsV1/V1_PROJECT_TREE_REDESIGN_PLAN.md`
- `docsV1/V1_LEGACY_COMMAND_RETIREMENT_BOUNDARY.md`

## 1. Purpose

Everything in the `[Unreleased]` changelog block passed the headless gate: 9 architecture
tests, 1,360 contract tests with 18 skipped and no failure, and all three smoke runners.
None of that opens a window. This lists what only a real FreeCAD session can answer, and
says for each check what was already proved headlessly so nothing is repeated for its own
sake.

`AGENTS.md` is explicit that GUI integration must not be claimed when only headless tests
ran, which is why this exists as a separate procedure.

## 2. What the headless gate already proved

Do not re-check these by hand:

- the workbench module imports, resolves 11 command groups and 24 toolbar command ids, and
  maps 15 proxy modules
- the project tree orders `02_Surfaces` before `03_Alignment & Profile`, relabels a document
  saved with the earlier labels, and keeps `CRV1_03_Surfaces` and
  `CRV1_02_Alignment_Profile` as the stored object names
- each of the three Intersection presets creates 18 source rows with an `IntersectionModel`,
  and the four retired kinds are refused by name
- the Intersection review table lists 18 rows for a T preset and reaches 18 of 18 reviewed
- the preset-default checklist reports a review state for all five values, and both the
  curb return radius and the design vehicle reach `reviewed`
- Applied Sections skips an Alignment missing a Profile, Region or Stationing, and names it
- superelevation is paired per Alignment, and a preset writes one source per road

## 3. Environment

- FreeCAD `1.1.1`, launched as the GUI, not `FreeCADCmd`
- exactly one `CorridorRoad` workbench under the active `Mod` directory; run
  `scripts\check_freecad_environment.ps1` first if unsure
- start from a fresh user profile if a previous session left a stale workbench cached

## 4. Workbench load

The session removed 7 v0 task panels, 11 legacy command modules, 9 placeholder modules and
2 icons. Nothing should be missing, because none of the removed commands was registered,
but a registration error would only appear here.

1. Start FreeCAD and switch to the `Parametric Road` workbench.
2. Open the Report view before switching, so the load output is captured.

Expected:

- no Python traceback and no `ImportError` in the Report view
- the `Parametric Road` toolbar appears with **24 buttons**
- the `Parametric Road` menu has 11 submenus: Project, Survey & Surface, Alignment,
  Stations & Profile, Assembly & Regions, Drainage, Corridor, Review, Outputs & Exchange,
  AI Assist, Watertight Solids
- **every toolbar button shows an icon**, none blank. This is the check for the two deleted
  icons, `cross_section_viewer.svg` and `new_project.svg`; a blank button means something
  still asks for one of them
- no warning naming a removed module: `task_cross_section_editor`, `task_structure_editor`,
  `task_section_generator`, `task_design_terrain`, `task_centerline3d`,
  `task_pointcloud_dem`, `task_station_generator`, `cmd_import_pointcloud_tin`

## 5. Existing document restore, the one change that touches saved files

This is the highest-risk check of the session. The tree root swap relabels and reorders
folders in documents that already exist.

1. Open an `.FCStd` saved **before** this session, one that has a Parametric Road project.
2. Look at the Tree view without touching anything else.

Expected:

- the roots read, in this order: `00_Project Setup`, `01_Source Data`, `02_Surfaces`,
  `03_Alignment & Profile`, `04_Parametric Model`, `05_Drainage`, `06_Structures`,
  `07_Quantities & Earthwork`, `08_Review`, `09_Outputs & Exchange`, `10_AI Assist`
- **exactly one** folder for each: no `02_Alignment & Profile` left beside
  `03_Alignment & Profile`, and no duplicate Surfaces folder
- everything that was inside the Surfaces and Alignment folders is still inside them, with
  the same objects
- the old objects still restore: no object shows the broken-proxy marker, and the Report
  view has no "unresolved proxy" or `Proxy` attribute error

3. Save, close, reopen the same document.

Expected: the order holds and nothing moved again.

If a document from before the 1.1.0 release is available, repeat with that one too, since it
predates more of the tree work.

## 6. Intersection preset, three kinds

1. `Assembly & Regions` -> `Intersection`.
2. Read the `Preset` combo.

Expected: **exactly three** entries, `T Intersection - Basic`,
`Cross Intersection - Basic`, `Roundabout - Single Lane`. No Skewed, Urban Curb/Gutter,
Drainage-Sensitive Sag or Y entry.

3. Choose `T Intersection - Basic`, leave the defaults, press `Create Sources`.

Expected in the Tree view:

- two roads under `03_Alignment & Profile`: Alignment, FG Profile and Stations for each
- two Region objects under `04_Parametric Model / Regions`
- **two** superelevation objects under `03_Alignment & Profile / Superelevation`, labelled
  `Intersection Preset Superelevation (primary)` and `(secondary)`. One only is the old
  behaviour and means the per-road change did not take effect
- one Drainage object, one `Intersections` object
- a `3D Centerline` preview

## 7. Intersection source review, new panel surface

The table and its two buttons are new. Headless construction and the handler calls passed,
but not real clicks, and the confirmation dialog was stubbed in the harness.

With the T preset sources from section 6 still open, and the Intersection panel still open:

1. Read the `Source review (legs, anchors, control areas, policies)` table.

Expected:

- **18 rows**: 2 `leg`, 1 `anchor`, 2 `control_area`, 1 `curb_return_policy`, 2 `arm_policy`,
  and the five families plan item 5.10 added: 2 `corner`, 4 `edge_policy`,
  2 `lane_connection`, 1 `grading_policy`, 1 `drainage_policy`. Eight rows here means
  item 5.10 is not in the build under test
- the `Approval` column reads `draft` on every row
- the `Missing` column reads `profile_ref, centerline3d_ref` on both leg rows and
  `tolerance` on the anchor row
- the summary line under the table reads `0 of 18 row(s) reviewed; 3 still missing source fields.`
- the table is **readable without resizing the task panel**, and its columns are not clipped

2. Press `Refresh Review`.

Expected: the same 18 rows, no flicker into an error message, summary unchanged.

3. Press `Accept Reviewed Rows`.

Expected:

- a dialog appears reading `Accepted 18 row(s).`
- after closing it, the summary reads `18 of 18 row(s) reviewed; 0 still missing source fields.`
- the `Approval` column reads `accepted` on every row and `Missing` is empty
- the four `edge_policy` rows still read `subassembly_default` in the `Note` column
- no traceback in the Report view

4. Press `Adopt Edge Families From Subassembly`.

Expected:

- a confirmation dialog asks whether to mark the edge policies as derived from the Assembly;
  answering `No` changes nothing
- after answering `Yes`, a dialog reads `Adopted 4 edge policy row(s) from the Subassembly.`
- the four `edge_policy` rows now read `subassembly_derived` in the `Note` column and every
  other row is unchanged
- the button is its own step: `Accept Reviewed Rows` never changes the method

4. Press `Accept Reviewed Rows` a second time.

Expected: it stays at 8 of 8 and reports `Accepted 8 row(s).` again. Accepting twice must not
error or double anything.

5. Close the panel with `Close`, then reopen `Intersection`.

Expected: the table still reads 8 of 8, because acceptance was written to the document.

6. Read the `Preset defaults in the document:` block in the status text.

Expected: five lines, one for each preset value, each naming the row family carrying it.
After the acceptance above, `Design vehicle`, `Curb return radius` and `Control length`
read `reviewed`, while `Grading policy` and `Drainage mode` still read `review required`.
Those last two are the families plan item 5.10 covers, so that is the measured state and
not a defect. A line reading `no review state on this row family` means a row family lost
its `approval_status`, which is worth recording.

## 8. Applied Sections panel, two new summary sections

1. `Corridor` -> `Applied Sections` on the document from section 6.
2. Read the summary text area.

Expected:

- a `Superelevation sources:` section listing both preset sources, each with
  `alignment=alignment:intersection-primary` or `...-secondary` and `0 control row(s)`
- no `Skipped Alignments:` section, because both roads are complete
- **the whole summary is reachable**: the text area is 190 px minimum and now carries more
  lines, so confirm it scrolls rather than hiding the last line

3. Press `Build Sections`, then reopen the panel.

Expected: it completes without error and the summary still reads as above.

### 8.1 The skipped-Alignment report

1. In the Tree view, delete the **side road's** Region object, the one labelled
   `Intersection Side Road Regions`.
2. Reopen `Applied Sections`.

Expected: a `Skipped Alignments:` section naming that Alignment with `missing Regions`, and
the main road still builds.

3. Undo the deletion and confirm the section disappears.

### 8.2 The shadowed superelevation report

1. `Stations & Profile` -> `Superelevation`, and apply anything so the editor writes its own
   source object.
2. Reopen `Applied Sections`.

Expected: the `Superelevation sources:` list now has three entries, and **one of them is
marked `<- not read`**. Which one depends on crossfall rows: a source carrying rows wins
over one without, so if the editor's source has rows then a preset placeholder is the one
marked, and if it has none then the editor's own source is marked.

## 9. Build Parametric, end to end

1. With the reviewed T preset document, run `Corridor` -> `Build Parametric`.

Expected:

- it completes with no traceback
- the intersection review table in the build panel reports its rows
- a `V1CorridorIntersectionSurfacePreview` and a
  `V1CorridorIntersectionSlopeFaceSurfacePreview` appear under
  `04_Parametric Model / Build Parametric Outputs`
- `IntersectionBoundaryOwnerStatus` on the slope face preview reads `ready` with 15 owners
  once both `Accept Reviewed Rows` and `Adopt Edge Families From Subassembly` have been
  pressed, and not before: with only the first it stays short of `ready`

2. Repeat sections 6, 7 and 9 for `Cross Intersection - Basic`.

Expected: the same as T, with **30 review rows** rather than 18, because a Cross has four
legs, so four arm policies, four corners, eight edge policies and four lane connections.
`IntersectionBoundaryOwnerStatus` stays `missing` for a Cross even after adoption: its corner
arcs are not built (`cross_intersection_corner_arc_gap:missing=4`), which is a separate gap
from the review.

3. Repeat for `Roundabout - Single Lane`.

Expected: **no** slope face preview object is created, and the `intersection_slope` review
row reads `missing`. This is the measured Roundabout gap, not a regression.

## 10. Legacy surfaces that must still work

These are v0-backed and were deliberately kept.

1. `Project` -> `Project Setup` opens and applies. It is the one surfaced workflow stage
   still driven by a v0 task panel.
2. `Review` -> `Review Cross Sections` opens a viewer. It prefers the v1 viewer and falls
   back to the v0 one; a Report view warning reading `v1 cross-section viewer unavailable`
   means the fallback was taken and should be recorded.
3. `Outputs & Exchange` -> `Outputs and Exchange` opens.
4. `AI Assist` -> `AI Assist` opens.

## 11. Recording the result

For each section, record pass or fail with the FreeCAD version and the document used. A
failure in section 5 is the one that blocks: it means a saved document does not survive the
tree change. Everything else is a defect to file rather than a stop.

When the pass is complete, tick
`- [ ] FreeCAD manual smoke QA for the published tag.` in
`docsV1/V1_RELEASE_CURRENT_PREP.md` only if the tag itself was exercised; this procedure
covers the unreleased branch state, which is a different claim.

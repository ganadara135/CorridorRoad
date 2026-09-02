# V1 Side Slope Review UX Plan

Date: 2026-07-14

Status: implementation complete; FreeCAD 1.1.1 manual QA pending

## Purpose

Replace the current point/breakline-based `Side Slope` Guided Review highlight with a result-backed Side Slope review workflow.

The change addresses misleading isolated point markers shown when a user double-clicks the existing Side Slope row, especially inside Intersection control areas.

## Scope

This plan covers the Build Parametric review UI for both ordinary road and Intersection contexts:

- remove the current Guided Review `subassembly_kind:side_slope` row and its temporary point/breakline highlight
- rename the Guided Review `Slope Face Diagnostics` step to `Side Slope`
- rename the `Slope Diagnostics` tab to `Side Slope Diagnostics`
- focus the appropriate accepted result surface for ordinary road or Intersection context
- preserve diagnostic marker review only for explicit warning or error conditions
- update automated contracts and FreeCAD 1.1.1 manual QA

This plan does not change Side Slope source authoring, Assembly placement, Applied Sections evaluation, terrain/daylight policy, Intersection grading policy, surface topology, Ramp, Watertight Solid, or CI behavior.

## Core Rule

`side_slope` Subassembly rows remain source/evaluation context. Their partial Applied Section point rows must not be presented as accepted corridor surface geometry.

Build Parametric review must display result-owned surfaces:

```text
ordinary road: Applied Sections -> Slope Face Surface (daylight result)
Intersection:  IntersectionModel + Applied Sections -> Intersection Slope Face Surface
diagnostic:    typed fallback/issue result -> explicit marker only when a warning or error exists
```

The UI may use the shared `Side Slope` language, but it must not merge ordinary-road and Intersection engineering ownership.

## Current Issue

The current `subassembly_kind:side_slope` Guided Review action creates a temporary object from `side_slope_surface`, `bench_surface`, and `daylight_marker` point rows.

When an Intersection-controlled station retains fewer than two usable points on a side, the presentation fallback creates a point/cross marker. These markers are not a valid Side Slope surface and can look like unrelated points in the 3D view.

This is a presentation defect. It must be removed without changing accepted source or result data.

## Target UX

| Surface context | Guided Review label | Focus result | Diagnostic behavior |
| --- | --- | --- | --- |
| Ordinary road | `5. Side Slope` | `Slope Face Surface` / daylight result | Show a specific fallback marker only when an ordinary-road Side Slope diagnostic exists |
| Cross/T Intersection | `5. Side Slope` | `Intersection Slope Face Surface` together with the clipped ordinary `Slope Face Surface` approach-road result | Show a specific Intersection diagnostic marker only when a typed Intersection slope diagnostic exists |
| No accepted result | `5. Side Slope` with missing/warning status | no fabricated geometry | show typed diagnostic and recommended source/result action |

The table tab label becomes `Side Slope Diagnostics`.

The underlying result labels, roles, object names, and source references remain stable:

- ordinary result role: `daylight` / `slope_face_surface`
- Intersection result role: `intersection_slope` / `intersection_slope_face_surface`
- existing diagnostic IDs and result contracts remain compatible

## Architecture Boundaries

- `models/source` keep Side Slope and Intersection design intent unchanged.
- `services/evaluation` keep ordinary daylight and Intersection slope evaluation separate.
- `models/result` remain the owner of Slope Face and Intersection Slope Face results and diagnostics.
- `objects` persist only accepted source/result data and must not persist temporary review highlights as design truth.
- `commands` route the Guided Review selection through a thin presentation request.
- `ui/viewers` own labels, deferred loading, selection state, and result-backed review presentation.

No layer may reconstruct a Side Slope surface from partial point markers, preview geometry, or mesh repair.

## Implementation Steps

### 1. Retire the temporary Side Slope Guided Review path

1. Remove `subassembly_kind:side_slope` from `corridor_subassembly_kind_guided_review_rows`.
2. Remove the special Side Slope point/breakline highlight from the standard Guided Review route.
3. Clean up any stale `ReviewIssueSubassemblyKind_side_slope` object when the new Side Slope review action is used.
4. Retain the underlying source/evaluated `side_slope` rows and their traceability; this is a presentation retirement only.
5. Keep a clearly named isolated compatibility adapter only if an external legacy caller requires it; it must route to a result surface and must not create marker-only geometry.

### 2. Establish result-backed Side Slope focus

1. Rename the Guided Review step title from `Slope Face Diagnostics` to `Side Slope` while retaining a stable internal step ID until callers migrate.
2. For an ordinary-road focus, select and fit `V1CorridorDaylightSurfacePreview` only when its result status is usable.
3. When accepted Cross/T Intersection slope output and ordinary daylight output are both available, show and fit `V1CorridorIntersectionSlopeFaceSurfacePreview` together with `V1CorridorDaylightSurfacePreview`; retain the Intersection object as the primary selection/return value.
4. If neither result is usable, return a typed missing/result diagnostic and do not create a surrogate shape.
5. Continue to expose ordinary and Intersection diagnostics separately in notes and result ownership fields.

### 3. Clarify diagnostics without normalizing markers

1. Rename the panel tab from `Slope Diagnostics` to `Side Slope Diagnostics`.
2. Keep station-side issue rows for actual daylight fallback, but label their owner and context as ordinary road or Intersection.
3. Double-clicking an issue row may select its marker only when the row is warning or error and the marker is traceable to that typed diagnostic.
4. A ready Side Slope result must select the result surface, never a diagnostic marker.

### 4. Preserve general-road behavior

1. Apply the new review action to ordinary roads as well as Intersections.
2. Verify ordinary terrain/daylight Side Slope surfaces still show continuous result geometry.
3. Verify bench and Side Slope Subassembly source rows remain available through Assembly/Subassembly and Applied Section review, not through a fabricated Build Parametric highlight.
4. Verify mixed Region projects select the correct result surface as review context changes.

### 5. Validation and documentation

1. Add focused controller/presentation contracts for removed Side Slope point highlights, ordinary result focus, Intersection result priority, and typed missing-result behavior.
2. Update existing Guided Review and panel-label contracts without changing result ownership contracts.
3. Run Compile, architecture boundary tests, focused Build Parametric contracts, and changed-file lint.
4. Run FreeCAD 1.1.1 manual QA with ordinary road, T/Cross Intersection, and a project containing a real Side Slope fallback diagnostic.
5. Update current release/status documentation only if user-visible labels are documented there.

## Acceptance Criteria

- Double-clicking the Guided Review Side Slope row never creates or focuses isolated point/cross geometry as normal review output.
- Ordinary road Side Slope review focuses the accepted Slope Face Surface result.
- Cross/T Intersection Side Slope review shows the accepted Intersection Slope Face Surface together with Primary/Secondary approach-road Slope Face Surface results when available.
- A diagnostic marker appears only for a typed warning/error row and identifies its owner/context.
- `side_slope` source, Applied Sections, result refs, and output traceability are unchanged.
- No preview object becomes source truth.
- Ramp remains removed, Watertight Solid remains paused, and CI remains unchanged.

## Implementation Record

- The `subassembly_kind:side_slope` Guided Review row and its Applied Section point/breakline highlight were removed.
- The stable `slope_issues` action now displays `Intersection Slope Face Surface` together with the accepted ordinary approach-road `Slope Face Surface` result for Cross/T intersections; the Intersection result remains primary.
- The action removes stale `ReviewIssueSubassemblyKind_side_slope` objects and never creates a replacement point/cross marker.
- The panel tab and diagnostic heading now use `Side Slope Diagnostics`; ordinary-road diagnostic rows identify their owner context.
- Focused contract validation passed with FreeCAD 1.1.1. The final manual QA cases below remain required.

## Manual QA

### Ordinary road

1. Build Applied Sections and Build Parametric for a road with a valid terrain/daylight Side Slope.
2. Double-click `5. Side Slope` in Guided Review.
3. Confirm the Slope Face Surface is selected and fitted with continuous geometry.
4. Confirm no temporary Side Slope point cloud or cross-marker object is created.

### Intersection

1. Build Applied Sections and Build Parametric for a T/Cross Intersection with accepted Intersection slope output.
2. Double-click `5. Side Slope`.
3. Confirm the Intersection Slope Face Surface and the Primary/Secondary approach-road Slope Face Surface results are selected, visible, and fitted together.
4. Confirm isolated green point/cross geometry is absent.
5. Open `Side Slope Diagnostics`; confirm markers appear only for actual warning/error rows.

### Regression

1. Verify Lane and Shoulder Guided Review remain unchanged.
2. Verify Side Slope source rows remain editable in their owning editor workflow.
3. Save, reopen, and confirm result surfaces and review labels remain intact.

## Out of Scope and Deferred Work

- changing Side Slope/bench engineering algorithms
- automatic terrain repair for missing daylight results
- Intersection topology or grading-policy redesign
- any Ramp, Watertight Solid, or CI expansion

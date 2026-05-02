<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Cross Section Editor GUI Checklist

Date: 2026-04-22

Purpose:

- Track real FreeCAD GUI validation that smoke tests cannot fully cover.
- Provide a single place to close `GUI check pending` status by phase.

Current stage marker: `PH-8 CURRENT`

Current GUI validation focus: `PH-8 Manual GUI Validation And Workflow Polish`

## Status Legend

- `Pending`: not yet validated in interactive FreeCAD GUI
- `Pass`: validated in interactive FreeCAD GUI
- `Pass with notes`: validated, but polish notes remain
- `Fail`: issue reproduced and needs a fix

## Before You Start

Recommended setup:

1. Open a document that already contains:
   - `SectionSet`
   - `AssemblyTemplate`
   - optional `RegionPlan`
   - optional `CrossSectionEditPlan`
2. Open `Cross Section Editor`.
3. Keep the Python console or report view visible if available.
4. Record results immediately in the note format at the bottom of this file.

Recommended validation order:

1. `PH-2`
2. `PH-3`
3. `PH-8`
4. `PH-4`
5. `PH-5`
6. `PH-6`
7. `PH-7`

This order reduces confusion because it validates base selection/preview behavior before apply and migration flows.

## PH Status Map

| Phase | GUI Status | Notes |
| --- | --- | --- |
| `PH-2` | Pending | Selection, highlight, and inspector workflow |
| `PH-3` | Pending | Impact preview baseline readability |
| `PH-4` | Pending | Guarded source-owner apply flows |
| `PH-5` | Pending | EditPlan station/range apply flows |
| `PH-6` | Pending | Range/transition preview behavior |
| `PH-7` | Pending | Overlay, drag handle, conflict, handoff, migration UX |
| `PH-8` | Pending | Preview freshness, apply gating, and workflow polish |

## PH-2 Checklist

### PH-2-A Open And Load

- [Pass] Action:
  Open `Cross Section Editor` and select a `SectionSet` with visible section content.
  Expected:
  station list and target list populate without manual refresh.
  Fail signs:
  empty station list, empty target list, or panel opens with stale/incorrect document selection.

### PH-2-B Station Selection

- [Pass] Action:
  Change station from one value to another with clearly different section geometry.
  Expected:
  canvas refreshes, target list updates, and target details correspond to the new station.
  Fail signs:
  target list does not change, previous station highlight remains, or inspector shows old station data.

### PH-2-C Canvas Selection

- [Pass] Action:
  Switch to `Select` mode and click a visible component guide.
  Expected:
  target combo follows the clicked guide and the inspector updates to the clicked component.
  Fail signs:
  click is ignored, wrong target is selected, or selection jumps unpredictably.

### PH-2-D Highlight Stability

- [Pass] Action:
  Select a target from the combo, then switch mode between `Review`, `Select`, and `Edit`.
  Expected:
  selected component highlight stays on the same semantic target when it should remain valid.
  Fail signs:
  highlight disappears unexpectedly, moves to another component, or flickers after mode change.

### PH-2-E Inspector Content

- [Pass] Action:
  Inspect one `typical` target and one `side_slope` or `daylight` target.
  Expected:
  inspector shows source owner, generated row, raw row preview, and parameter table entries that match the selected target.
  Fail signs:
  source owner is blank, generated/raw rows look unrelated to the selected target, or table values do not match.

## PH-3 Checklist

### PH-3-A Baseline Impact Preview

- [ ] Action:
  Select an editable target, change one parameter, and click `Preview Impact`.
  Expected:
  impact panel shows affected range, affected station count, timeline, region owner, and downstream status.
  Fail signs:
  missing core rows, obviously stale data, or preview text that does not reflect the current target.

### PH-3-B Structure And Region Feedback

- [ ] Action:
  Move between a structure-affected target and a non-structure target.
  Expected:
  structure overlap text changes with the target and remains readable.
  Fail signs:
  overlap text does not change, remains stuck on old values, or wraps badly enough to become unreadable.

### PH-3-C Boundary Readability

- [ ] Action:
  Use a station/range case with boundary station injection.
  Expected:
  boundary station lines remain readable at normal panel width without truncating the key numbers.
  Fail signs:
  clipped station values, overlapping lines, or unreadable dense wrapping.

## PH-4 Checklist

### PH-4-A Global Width Apply

- [ ] Action:
  Pick a PH-4-supported `Global Source` width target, change the value, run `Preview Impact`, then click `Apply`.
  Expected:
  apply succeeds, current station refreshes, and the edited source owner reflects the new value.
  Fail signs:
  apply remains disabled after current preview, apply succeeds but geometry does not change, or selection resets unexpectedly.

### PH-4-B Global Slope Apply

- [ ] Action:
  Pick a PH-4-supported `Global Source` side-slope target, change `Slope %`, run preview, then apply.
  Expected:
  apply succeeds without corridor-contract breakage and the current station refreshes.
  Fail signs:
  apply path claims success but geometry does not move, or later build fails immediately from this edit.

### PH-4-C Active Region Policy Apply

- [ ] Action:
  Switch to `Active Region`, choose `Region Side Policy` or `Region Daylight Policy`, run preview, then apply.
  Expected:
  policy combo is enabled, apply succeeds, and the active region is the written owner.
  Fail signs:
  policy combo stays disabled for a valid case, apply writes to the wrong owner, or region-scoped feedback is missing.

### PH-4-D Downstream Visibility

- [ ] Action:
  After a successful PH-4 apply, inspect validation/apply messages.
  Expected:
  downstream stale messaging is visible and not silent.
  Fail signs:
  no stale message even though downstream outputs exist, or stale wording is too vague to act on.

## PH-5 Checklist

### PH-5-A Station Range Flow

- [ ] Action:
  Choose `Station Range`, set start/end/transition, click `Preview Impact`, then `Apply`.
  Expected:
  apply succeeds, range override is visible in refreshed section behavior, and the same semantic target remains selected if still valid.
  Fail signs:
  preview/apply ignores range values, selection jumps to another target, or refreshed state becomes unusable.

### PH-5-B Current Station Only Flow

- [ ] Action:
  Choose `Current Station Only` for a geometry edit and click `Apply`.
  Expected:
  confirmation dialog appears first; apply proceeds only after confirmation.
  Fail signs:
  no confirmation appears, or cancel still applies the edit.

### PH-5-C Post-Apply Stability

- [ ] Action:
  After PH-5 apply, continue editing the same target without reopening the editor.
  Expected:
  panel remains stable, preview becomes stale again, and user can continue with a new preview/apply cycle.
  Fail signs:
  controls disable permanently, wrong target becomes selected, or panel text no longer matches the target.

### PH-5-D EditPlan Ownership Visibility

- [ ] Action:
  Revisit a station driven by `CrossSectionEditPlan`.
  Expected:
  source owner and target details clearly indicate edit-plan ownership.
  Fail signs:
  target still looks like plain generated geometry, or edit-plan ownership is not discoverable.

## PH-6 Checklist

### PH-6-A Station Preview Readability

- [ ] Action:
  Use `Station Range` with non-zero transitions and review `Station preview`.
  Expected:
  adjacent before/current/range/transition/adjacent after rows are readable and ordered logically.
  Fail signs:
  roles are missing, duplicated, or visually confusing.

### PH-6-B Transition Correctness

- [ ] Action:
  Change `Transition In/Out` values and rerun preview.
  Expected:
  transition rows and midpoint values change accordingly.
  Fail signs:
  transition text stays unchanged, or values do not match the edited transition distances.

### PH-6-C Before/After Samples

- [ ] Action:
  Use a longer range and inspect `Before / after samples`.
  Expected:
  rows remain readable and clearly show `before`, `after`, `delta`, and role.
  Fail signs:
  overly dense wrapping, clipped values, or ambiguous sample roles.

### PH-6-D Boundary Injection Warning

- [ ] Action:
  Pick a range that requires a non-sampled boundary station.
  Expected:
  missing boundary warning appears when expected.
  Fail signs:
  no warning for a known non-sampled boundary, or warning appears when nothing is missing.

## PH-7 Checklist

### PH-7-A Before/After Overlay

- [ ] Action:
  Enter `Edit` mode, change a width-like value, and observe the canvas before applying.
  Expected:
  dashed preview overlay appears on the selected target and follows the pending value.
  Fail signs:
  no overlay, overlay on the wrong component, or overlay lags behind the current value.

### PH-7-B Drag Handle Behavior

- [ ] Action:
  Use a supported width-like target and drag the handle.
  Expected:
  handle appears only when supported and dragging updates the pending numeric value without breaking selection.
  Fail signs:
  unsupported targets show handles, dragging changes the wrong field, or selection breaks mid-drag.

### PH-7-C Conflict Readability

- [ ] Action:
  Reproduce a warning conflict and a blocked conflict.
  Expected:
  overlay color, inspector label, and impact text all agree on the state.
  Fail signs:
  color/state mismatch, unreadable label contrast, or blocked case still looks like a warning.

### PH-7-D Resolution And Handoff

- [ ] Action:
  Use a conflict case that exposes resolution buttons.
  Expected:
  action buttons appear when expected, and handoff text matches the selected side and scope.
  Fail signs:
  buttons missing for valid cases, wrong side token, or handoff text contradicts the actual prepared action.

### PH-7-E Override Migration

- [ ] Action:
  Open a local override target, prepare region handoff, then disable the local override.
  Expected:
  local override can be retired cleanly and target ownership changes accordingly after refresh.
  Fail signs:
  disable action appears to succeed but override remains active, or ownership text does not change.

## PH-8 Checklist

### PH-8-A Preview Freshness

- [ ] Action:
  Change target, parameter, scope, or value without rerunning preview.
  Expected:
  preview immediately becomes stale, status label says stale, and button text changes to `Preview Impact (Stale)`.
  Fail signs:
  stale state is not obvious, old impact analysis stays looking current, or button text does not change.

### PH-8-B Apply Gating

- [ ] Action:
  Try to apply while preview is stale, then rerun preview and try again.
  Expected:
  `Apply` is disabled while stale and enables only after current preview is available.
  Fail signs:
  apply remains enabled while stale, or stays disabled after a valid current preview.

### PH-8-C Blocked Preview Gating

- [ ] Action:
  Reproduce a blocked conflict and rerun preview.
  Expected:
  preview state shows blocked and `Apply` stays disabled.
  Fail signs:
  blocked preview still allows apply, or blocked state is only visible in one place.

### PH-8-D After-Apply Reset

- [ ] Action:
  Perform a successful apply and inspect the panel immediately after refresh.
  Expected:
  preview returns to stale, and the panel explains that preview must be rerun for the new state.
  Fail signs:
  preview incorrectly remains current, or user cannot tell why apply is disabled again.

### PH-8-E Narrow Layout Readability

- [ ] Action:
  Use the panel at its minimum practical width.
  Expected:
  preview label, action buttons, and impact text remain readable without severe clipping.
  Fail signs:
  important state text is truncated, buttons overlap, or line wrapping makes the state unreadable.

## Result Template

Use one line per checked item:

```text
2026-04-22 | PH-8-A | Pass | Preview label changed to stale/current correctly.
2026-04-22 | PH-7-E | Fail | Disable Local Override button worked, but ownership text did not refresh until panel reopen.
```

## Recording Notes

Use short entries with date and outcome:

```text
2026-04-22 | PH-8 | Pass with notes | Preview status label is clear; blocked-state button text still needs a final wording pass.
```

# V1 SubAssembly Designer UX Simplification Plan

Date: 2026-06-18
Status: Draft plan
Audience: product planning, UI/UX, implementation, testing

## 1. Purpose

This document defines a simpler user-facing workflow for SubAssembly Designer and Assembly/Subassembly preset usage.

The goal is to keep the reusable preset source contracts internally, while reducing the normal user workflow to a small number of understandable actions.

Terminology rule:

- `Reusable Subassembly Template` means one reusable lane, shoulder, ditch, side slope, curb, gutter, or other single Subassembly definition.
- `Assembly Template` means a full cross-section arrangement made from multiple Subassembly rows.

## 2. Scope

This plan covers:

- SubAssembly Designer action simplification
- project preset library visibility
- safer save semantics for Assembly row edits
- terminology cleanup from `Preset` to user-facing Reusable Subassembly Templates and Assembly Templates
- advanced preset management placement
- manual QA expectations for the simplified workflow

This plan does not cover:

- removing the source model classes immediately
- changing Applied Sections result contracts
- changing Build Corridor output contracts
- automatic rebuilds after template edits

## 3. Core Rule

Preset data remains source intent.

The normal UI should not require users to understand `SubassemblyPreset`, `definition_ref`, `preset_status`, or version metadata before they can edit a shoulder, ditch, lane, or side slope.

Advanced preset metadata should remain available for review and diagnostics, but it should not dominate the primary editing path.

## 4. UX Problem

The current workflow exposes too many source concepts at once:

- Assembly row
- Subassembly Definition
- Subassembly Preset
- project preset library
- Apply to Assembly
- Save as New Preset
- Update Preset
- Detach as Custom
- Edit/Duplicate/Rename/Delete selected preset

This makes users unsure whether they are editing:

- the active Assembly row
- a Reusable Subassembly Template
- a local snapshot
- a read-only library row

The read-only project preset table is especially confusing because it looks selectable and important, but it is not the primary edit surface.

## 5. Product Direction

Keep preset contracts internally.

Hide preset library management from the default workflow.

Expose the feature as Reusable Subassembly Templates only when the user intentionally asks for reuse.

Recommended user-facing language:

- `Reusable Subassembly Template` instead of `Preset` for one lane, shoulder, ditch, side slope, curb, gutter, or other single Subassembly reusable definition
- `Assembly Template` for a road cross-section made from multiple Subassembly rows
- `Editing Source` instead of `Preset state`
- `Save Changes` instead of choosing between multiple persistence actions
- `Save as Reusable Subassembly Template` instead of `Save as New Preset`
- `Advanced Subassembly Template Library` instead of `Project preset library`

## 6. Target Default Workflow

The default SubAssembly Designer workflow should be:

```text
1. Select or load an Assembly row.
2. Edit the definition/detail tables.
3. Click Save Changes.
4. Optionally click Save as Reusable Subassembly Template.
```

The default screen should answer three questions:

- What am I editing?
- Are there unsaved changes?
- Where will Save Changes write?

Suggested status copy:

```text
Editing: shoulder:right
Save target: selected Assembly row
Unsaved changes: 5
Reusable Subassembly Template: Basic Shoulder
```

## 7. Target UI Layout

### 7.1 Primary Header

Replace the current mixed preset/action area with:

```text
Editing Source:
[Assembly Row combo] [Refresh] [Load Row]

[Save Changes] [Save as Reusable Subassembly Template]

Editing: Shoulder Right
Save target: Assembly row shoulder:right
Unsaved changes: 5
Reusable Subassembly Template: Basic Shoulder
```

### 7.2 Advanced Area

Move the current project preset library table and management actions into a collapsed advanced section:

```text
Advanced Subassembly Template Library
[Show]

[Edit Selected Subassembly Template]
[Update Shared Subassembly Template]
[Duplicate]
[Rename]
[Delete]
[Detach as Custom]
```

Default state: collapsed.

The advanced section should include this warning:

```text
Shared Reusable Subassembly Template changes may affect Assembly rows that reference the template after refresh/rebuild.
```

### 7.3 Definition/Detail Editing

Keep the main editable Definition and Detail tables.

The top table remains the actual editing surface.

The advanced library table is a management/review surface only.

## 8. Save Semantics

### 8.1 Save Changes

`Save Changes` should be the primary action.

Behavior:

- If loaded from an Assembly row, write the current definition back to that Assembly row.
- If no Assembly row is available, apply the SubAssembly library source.
- If editing a shared Reusable Subassembly Template directly, show a confirmation before updating the shared template.

Confirmation for shared template update:

```text
This Reusable Subassembly Template may be used by other Assembly rows.
Update the shared Subassembly Template?
```

Options:

- `Update Shared Subassembly Template`
- `Save as Custom Copy`
- `Cancel`

### 8.2 Save as Reusable Subassembly Template

Creates a new project-level Reusable Subassembly Template from the current single Subassembly definition.

After saving, ask whether to link the current Assembly row to the new template if an Assembly row is active.

### 8.3 Update Shared Subassembly Template

Move to Advanced by default.

It should remain explicit and confirmation-gated.

### 8.4 Detach as Custom

Move to Advanced by default.

It should be described as:

```text
Keep this Assembly row independent from Reusable Subassembly Template updates.
```

## 9. Data Model Policy

Do not remove the preset source models in this UX pass.

Keep:

- `SubassemblyPreset`
- `SubassemblyPresetLibrary`
- Assembly row `preset_ref`
- Assembly row `preset_version`
- Assembly row `preset_status`
- Applied Section preset trace fields

Reason:

- reuse still matters
- linked/outdated diagnostics still matter
- Applied Sections and Build Corridor already consume this traceability
- removing contracts would create avoidable source/result churn

The UX pass should change exposure and wording first, not delete the architecture.

## 10. Implementation Phases

### Phase 1: Rename and regroup actions

Tasks:

- Rename primary button labels.
- Add `Save Changes`.
- Keep old methods internally as compatibility helpers.
- Move preset management buttons under an Advanced container.
- Collapse Advanced by default.
- Change status labels from preset-centric copy to editing-source copy.

Acceptance criteria:

- A user can load an Assembly row, edit values, and save with one primary button.
- The project preset library table is not visible by default.
- Existing save/update/detach behavior still works through Advanced.

### Phase 2: Simplify default state labels

Tasks:

- Replace `Preset state` with `Editing Source`.
- Replace `Preset differences` with `Subassembly Template differences` only when a template is linked.
- Keep changed-field count.
- Show save target explicitly.

Acceptance criteria:

- The header clearly says whether Save Changes writes to Assembly row, SubAssembly library, or shared template.
- Missing/outdated template metadata remains available without dominating the screen.

### Phase 3: Safer template edit flow

Tasks:

- Add confirmation when saving to a shared Reusable Subassembly Template.
- Provide `Save as Custom Copy` path.
- Show affected Assembly row count before shared template update where available.

Acceptance criteria:

- Shared Subassembly Template updates cannot happen silently.
- Users can avoid global changes by saving a copy.

### Phase 4: Assembly/Subassembly panel alignment

Tasks:

- Rename `Preset Ref` UI wording where practical to `Template Ref`.
- Keep persisted field names unchanged for compatibility.
- Keep diagnostics readable for missing/outdated template links.
- Keep the automatic Subassembly Ref guess action, but mark it as approximate.

Acceptance criteria:

- Assembly/Subassembly panel and SubAssembly Designer use consistent user-facing language.
- Users can still inspect technical refs when needed.

### Phase 5: Documentation and QA

Tasks:

- Update `docsV1/wiki/SubAssembly-Designer.md`.
- Update `docsV1/wiki/Assembly-Region.md` if terminology appears there.
- Add a short manual QA checklist for the simplified flow.

Acceptance criteria:

- Documentation describes the two-button default workflow.
- Advanced template management is documented as optional.

## 11. Manual QA Checklist

Default workflow:

- Open SubAssembly Designer with an Assembly/Subassembly object present.
- Confirm Advanced Subassembly Template Library is collapsed by default.
- Load `shoulder:right` from Assembly row.
- Edit a parameter.
- Confirm unsaved change count increases.
- Click `Save Changes`.
- Confirm the Assembly row is updated.

Reusable Subassembly Template workflow:

- Load an Assembly row.
- Edit a parameter.
- Click `Save as Reusable Subassembly Template`.
- Confirm a Reusable Subassembly Template row is created.
- Confirm current Assembly row can be linked or kept custom.

Advanced workflow:

- Expand Advanced Subassembly Template Library.
- Select a Reusable Subassembly Template.
- Load it for editing.
- Confirm editing happens in the main Definition/Detail tables.
- Update shared template only after confirmation.

Regression checks:

- Applied Sections still resolves linked template rows.
- Missing/outdated diagnostics still appear.
- Snapshot/custom rows still build.
- Build Corridor subassembly highlights still include preset/template trace metadata.

## 12. Non-goals

This plan does not remove source traceability.

This plan does not make generated Applied Sections editable source data.

This plan does not auto-refresh all linked Assembly rows after a shared template update.

This plan does not remove advanced template management; it hides it from the default path.

## 13. Terminology Reference

### 13.1 Reusable Subassembly Template

A Reusable Subassembly Template stores one reusable Subassembly definition contract.

Examples:

- `Basic Lane`
- `Basic Shoulder`
- `Trapezoid Ditch`
- `Benched Side Slope`

It typically owns:

- kind
- parameter defaults
- point roles
- link roles
- shape roles
- target expectations

It does not represent a full road cross-section by itself.

### 13.2 Assembly Template

An Assembly Template stores a full road cross-section arrangement made from multiple Subassembly rows.

Example:

```text
Benched Ditch Road Assembly Template
- lane:left
- lane:right
- shoulder:left
- shoulder:right
- ditch:left
- ditch:right
- side_slope:left
- side_slope:right
```

It owns placement and ordering intent for several Subassemblies.

### 13.3 Assembly Row

An Assembly Row is one placed Subassembly instance inside an Assembly Template.

It may reference:

- one Reusable Subassembly Template
- one Subassembly Definition
- local custom override values

### 13.4 Internal compatibility terms

The code may continue to use existing persisted field names for compatibility:

- `preset_ref`
- `preset_version`
- `preset_status`
- `SubassemblyPreset`
- `SubassemblyPresetLibrary`

The user-facing UI should prefer:

- `Reusable Subassembly Template`
- `Template Ref`
- `Template Version`
- `Template Status`

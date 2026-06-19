# V1 Subassembly Preset Integration Plan

Date: 2026-06-16
Status: Draft plan; Phase 1 source contracts started
Audience: product planning, architecture, UI/UX, implementation, testing

Implementation note:

- 2026-06-16: Added initial source contracts in `subassembly_preset_model.py` and preset linkage metadata on `TemplateSubassembly`.
- 2026-06-16: Added initial FreeCAD object persistence for `SubassemblyPresetLibrary` and Assembly preset linkage metadata.
- 2026-06-16: Added first SubAssembly Designer to Assembly roundtrip helpers and panel actions: `Load from Assembly` and `Apply to Assembly`.
- 2026-06-16: Added `Save as New Preset` from SubAssembly Designer into the project-level `SubassemblyPresetLibrary`.
- 2026-06-16: Added `Update Preset` confirmation flow and `Detach as Custom` snapshot flow for the active Assembly Subassembly.
- 2026-06-16: Added Assembly panel preset columns, preset selector values, version/status display, override status updates, and preset linkage diagnostics.
- 2026-06-16: Connected Applied Sections evaluation to project-level Subassembly preset libraries so preset defaults resolve before definition fallbacks and Assembly overrides.
- 2026-06-17: Added Applied Section Subassembly result traceability fields for preset ref, preset version, preset status, and source Assembly instance ref.
- 2026-06-17: Added Applied Sections review preset summary, Subassembly diagnostic aggregation, and preset diagnostic visibility.
- 2026-06-17: Added pre-build Applied Sections validation diagnostics for missing, outdated, modified, and snapshot Subassembly preset links.
- 2026-06-17: Added Assembly panel `Refresh from Preset` action to relink a selected Subassembly row to current preset defaults and clear local overrides.
- 2026-06-17: Added Assembly panel `Detach as Custom` action to convert a selected preset-linked Subassembly row into a local snapshot.
- 2026-06-17: Added Assembly panel preset selection default-fill behavior for kind, definition ref, version, dimensions, material, and source instance trace.
- 2026-06-17: Added SubAssembly Designer Assembly row selector so `Load from Assembly` and `Apply to Assembly` can target a specific Subassembly row instead of only the first active row.
- 2026-06-17: Added Build Corridor Subassembly review preset metadata on highlight objects, guided summary notes, and kind-level review rows.
- 2026-06-17: Added Build Parametric surface-role review notes for Subassembly preset refs and preset status counts.
- 2026-06-17: Added Applied Section preset surface-role coverage diagnostics for missing expected surface roles after Subassembly links are evaluated.
- 2026-06-17: Added Assembly panel `Refresh Outdated Presets` action to update linked outdated rows while skipping modified, missing, and snapshot rows.
- 2026-06-17: Added Assembly panel preset-status row styling so linked, modified, snapshot, missing, and outdated rows are visually distinguishable.
- 2026-06-17: Added SubAssembly Designer preset-state badge for linked, modified, snapshot, and missing workflows.
- 2026-06-17: Added first SubAssembly Designer changed-field indicator by marking locally edited definition/detail cells.
- 2026-06-17: Added SubAssembly Designer preview surface-role summary for link surface roles and shape solid roles.
- 2026-06-17: Added SubAssembly Designer preview warning for missing expected surface roles by Subassembly kind.
- 2026-06-17: Added Assembly panel preset-status legend and action tooltips for refresh, detach, reset, and apply workflows.
- 2026-06-18: Added Assembly panel automatic preset status indicators for missing and outdated preset versions on model load.
- 2026-06-18: Added SubAssembly Designer Assembly row selector labels with preset status and preset version.
- 2026-06-18: Added SubAssembly Designer Assembly row selector automatic missing/outdated preset status display from preset library versions.
- 2026-06-18: Added SubAssembly Designer read-only project preset library summary with preset count and representative versions.
- 2026-06-18: Added first Preset library management UI slice with a read-only Designer preset list table.
- 2026-06-18: Added Preset library management `Duplicate Selected Preset` action in SubAssembly Designer.
- 2026-06-18: Added Preset library management `Rename Selected Preset` action with affected Assembly row diagnostics and source ref updates.
- 2026-06-18: Added Preset library management `Delete Selected Preset` action with affected Assembly row warning and missing-preset preservation.
- 2026-06-18: Added Preset library management version/history display columns in the SubAssembly Designer preset list.
- 2026-06-18: Added first Changed-field refinement with a Designer `Changed fields` count badge for local edits.
- 2026-06-18: Added Changed-field marker clearing after preset load, save, update, and library apply workflows.
- 2026-06-18: Added Designer `Preset differences` badge for parameter values that differ from matching project preset defaults.
- 2026-06-18: Expanded Designer `Preset differences` comparison to preset point roles, link roles, surface roles, quantity roles, and shape roles.
- 2026-06-18: Added preset target-row contract support and included target rows in Designer `Preset differences` comparison.
- 2026-06-18: Fixed Subassembly preset creation to persist shape solid roles for accurate preset difference comparison.

## 1. Purpose

This document defines how `SubAssembly Designer` preset data should integrate with `Assembly` source rows in Parametric Road v1.

The goal is to make reusable lane, shoulder, ditch, side slope, and future Subassembly definitions easy for users to manage without hiding design changes or mutating accepted corridor output unexpectedly.

## 2. Scope

This plan covers:

- shared Subassembly preset storage
- Assembly placement of preset-backed Subassembly instances
- user-facing load, apply, save, update, and detach workflows
- explicit override handling
- Applied Sections consumption of resolved Subassembly definitions
- surface role preservation for design, subgrade, drainage, and slope-face outputs

This plan does not cover:

- automatic geometric corridor rebuilds on preset edit
- editing generated Applied Section geometry as source truth
- migration compatibility for legacy v0 section definitions
- final watertight solid generation

## 3. Core Rule

Subassembly preset intent belongs in source models.

Assembly rows should reference presets and record placement or override intent.

Applied Sections should consume resolved definitions and remain result data.

Generated preview wires, meshes, surfaces, and solids must not become the durable source of Subassembly design intent.

## 4. Recommended Model

Use a shared preset library with Assembly-level instance overrides.

```text
Project Preset Library
  -> SubassemblyPreset rows
  -> AssemblyPreset rows

Assembly Source
  -> preset_ref
  -> placement fields
  -> explicit overrides

Evaluation
  -> resolved Subassembly definition
  -> Applied Sections
  -> corridor surfaces and output previews
```

This keeps reusable defaults centralized while allowing each Assembly to make local, traceable changes.

## 5. User Experience Goals

The workflow should feel predictable to non-technical users.

The user should always know whether an Assembly row is:

- using a preset exactly
- modified from a preset
- detached from a preset
- affected by a newer preset version

The editor should avoid silent global updates.

SubAssembly Designer should expose simple actions:

- `Load from Assembly`
- `Apply to Assembly`
- `Save as New Preset`
- `Update Preset`
- `Detach as Custom`

## 6. User Workflow

### 6.1 Start from Assembly

The user selects an Assembly row or Assembly preset and opens SubAssembly Designer.

SubAssembly Designer loads the referenced preset and visible Assembly overrides.

The header should show:

```text
Preset: Rural Shoulder + Ditch + Side Slope
Source: Project Preset
Status: Linked
```

### 6.2 Edit Locally

When the user edits lane width, shoulder slope, ditch shape, side slope bench rows, or surface roles, the status becomes:

```text
Status: Modified from Preset
```

No other Assembly should change at this point.

### 6.3 Apply to Assembly

`Apply to Assembly` writes the resolved local edit into the active Assembly instance.

The Assembly instance records only changed fields as overrides where practical.

The original preset remains unchanged.

### 6.4 Save as New Preset

`Save as New Preset` creates a new project preset from the current designer state.

The user can optionally relink the active Assembly instance to the new preset.

### 6.5 Update Preset

`Update Preset` writes the current designer state back to the referenced preset.

This action should require confirmation because it may affect other linked Assembly instances on their next refresh.

Linked Assemblies should not be silently rebuilt.

### 6.6 Detach as Custom

`Detach as Custom` removes the preset reference from the active Assembly instance and stores the current resolved values as local source data.

The status becomes:

```text
Status: Snapshot
```

## 7. Source Model Additions

Add source model contracts under:

```text
freecad/Corridor_Road/v1/models/source/
```

Recommended source families:

- `SubassemblyPreset`
- `AssemblyPreset`
- `AssemblySubassemblyInstance`
- `SubassemblyPresetLibrary`

### 7.1 SubassemblyPreset

Suggested fields:

- `preset_id`
- `name`
- `kind`
- `version`
- `parameters`
- `point_roles`
- `link_roles`
- `shape_roles`
- `surface_roles`
- `quantity_roles`
- `diagnostic_rules`

### 7.2 AssemblyPreset

Suggested fields:

- `preset_id`
- `name`
- `version`
- `subassembly_refs`
- `layout_rules`
- `default_side_policy`
- `default_region_policy`

### 7.3 AssemblySubassemblyInstance

Suggested fields:

- `instance_id`
- `preset_ref`
- `preset_version`
- `kind`
- `side`
- `station_range_ref`
- `placement_order`
- `overrides`
- `status`
- `locked`

## 8. Preset Status Contract

Use explicit status values:

| Status | Meaning |
|---|---|
| `linked` | Instance matches the referenced preset plus no local overrides. |
| `modified` | Instance references a preset but has local overrides. |
| `snapshot` | Instance is detached and stores its own source data. |
| `preset_outdated` | Referenced preset has a newer version than the instance snapshot. |
| `missing_preset` | Instance references a preset that cannot be found. |

These statuses should be visible in Assembly and SubAssembly Designer.

## 9. Surface Role Contract

Preset data must preserve enough semantic role information to drive corridor surfaces.

Required role mappings:

| Subassembly kind | Point/link role | Surface role |
|---|---|---|
| `lane` | `fg_surface` | `design_surface` |
| `lane` | `subgrade_surface` | `subgrade_surface` |
| `shoulder` | `fg_surface` | `design_surface` |
| `shoulder` | `subgrade_surface` | `subgrade_surface` |
| `ditch` | `ditch_surface` | `drainage_surface` |
| `side_slope` | `side_slope_surface` | `slope_face_surface` |
| `side_slope` | `bench_surface` | `slope_face_surface` |
| `side_slope` | `daylight_marker` | `slope_face_surface` |

This prevents the common failure mode where cross-section lines exist but corridor surface builders cannot discover stable Subassembly-owned links.

## 10. Evaluation Flow

Evaluation should be deterministic.

```text
SubassemblyPreset
  + AssemblySubassemblyInstance.overrides
  + Region context
  + Superelevation/Profile/Drainage context
  -> Resolved Subassembly Definition
  -> AppliedSectionSubassemblyRow
  -> AppliedSectionSubassemblyPoint
  -> AppliedSectionSubassemblyLink
  -> AppliedSectionSubassemblyShape
  -> Corridor SurfaceModel outputs
```

Applied Sections should record the resolved source references for traceability.

Applied Sections should not own editable preset state.

## 11. UI Plan

### 11.1 Assembly Panel

Assembly should expose:

- preset selector
- instance status
- local override indicator
- command to open selected instance in SubAssembly Designer
- command to refresh from preset
- command to detach as custom

### 11.2 SubAssembly Designer

SubAssembly Designer should expose:

- preset selector
- source indicator
- status indicator
- changed-field indicator
- surface role preview
- `Load from Assembly`
- `Apply to Assembly`
- `Save as New Preset`
- `Update Preset`
- `Detach as Custom`

### 11.3 Confirmation Rules

Require confirmation for:

- updating a shared preset
- applying preset changes to multiple Assemblies
- detaching a modified instance
- discarding local overrides

Do not require confirmation for:

- preview-only parameter edits
- loading a preset into the designer scratch state
- saving as a new preset

## 12. Implementation Order

### Phase 1: Source contracts

Add preset and instance source dataclasses.

Acceptance criteria:

- presets can represent lane, shoulder, ditch, and side slope definitions
- surface roles are present in preset data
- Assembly instances can reference presets and store overrides

### Phase 2: Library persistence

Add project-level preset library serialization.

Acceptance criteria:

- project presets survive document save/load
- preset ids remain stable
- missing preset references produce diagnostics

### Phase 3: Designer integration

Connect SubAssembly Designer to Assembly selected rows.

Acceptance criteria:

- designer can load from the active Assembly instance
- designer can apply edits back to the active Assembly instance
- designer can save current state as a new preset
- status changes are visible

### Phase 4: Assembly integration

Add preset selection and override state to Assembly.

Acceptance criteria:

- Assembly can place preset-backed Subassemblies
- local overrides are visible
- detach and refresh actions are available

### Phase 5: Applied Sections evaluation

Resolve preset plus overrides before building Applied Sections.

Acceptance criteria:

- Applied Sections contain Subassembly rows, points, links, and shapes from resolved definitions
- lane and shoulder feed design/subgrade surfaces
- ditch feeds drainage surface
- side slope feeds slope-face surface
- generated output remains traceable to source preset and Assembly instance

### Phase 6: Review and diagnostics

Add review rows for preset linkage health.

Acceptance criteria:

- missing preset references are reported
- outdated preset versions are reported
- modified instances are distinguishable from linked instances
- surface role coverage is reported before Build Corridor

## 13. Remaining Work

### R1: Focused validation for latest Designer helpers

Validate the latest UI helper changes.

Acceptance criteria:

- Designer Assembly row selector reports `missing_preset` when a preset ref is not present in the project preset library
- Designer Assembly row selector reports `preset_outdated vOld->vNew` when row and library preset versions differ
- Designer Assembly row selector preserves `modified` status
- Designer project preset library summary reports no-library, empty-library, populated-library, and overflow preview states

### R2: Preset library management UI

Add an explicit project preset library management surface after the read-only summary.

Recommended order:

- preset list table
- duplicate preset
- rename preset with reference update diagnostics
- delete preset with reference impact warning
- version/history display

Acceptance criteria:

- users can inspect all project Subassembly presets without opening generated FreeCAD properties
- destructive actions are confirmation-gated
- rename/delete reports affected Assembly rows before changing source state
- preset management remains source-model owned and does not mutate generated Applied Sections or Corridor outputs directly

### R3: Changed-field indicator refinement

Improve the first changed-cell marker into a preset/default comparison indicator.

Acceptance criteria:

- fields changed from preset defaults are distinguishable from merely edited cells
- changed-field count is visible in Designer
- refresh/save/update clears stale visual markers
- comparison works for parameters, links, shapes, target rows, and surface roles
- target row comparison uses the explicit `target_specs` preset contract

### R4: End-to-end preset-linked corridor validation

Run a full workflow validation using lane, shoulder, ditch, and side slope Subassemblies.

Acceptance criteria:

- preset-linked Assembly rows generate Applied Sections with preset trace fields
- lane and shoulder links feed design/subgrade surfaces
- ditch links feed drainage surface
- side slope links feed slope-face surface
- side slope uses the Applied Sections geometry, not the default fallback section
- Build Corridor creates Subassembly highlight surfaces and guided review preset metadata
- missing/outdated/modified/snapshot diagnostics appear before output generation

Progress notes:

- 2026-06-18: Ran a focused FreeCADCmd AppliedSectionService E2E validation with preset-linked lane, shoulder, ditch, and side slope rows.
- 2026-06-18: Confirmed preset trace fields survive into Applied Section subassembly rows.
- 2026-06-18: Confirmed design, subgrade, drainage, and slope-face surface roles are emitted when source geometry has valid width/thickness/profile inputs.
- 2026-06-18: Recorded fixture requirement: ditch needs a valid width/profile such as `shape=trapezoid` and `top_width`; side slope needs a positive `width`.
- 2026-06-18: Ran a focused FreeCADCmd Build Corridor highlight E2E validation with two preset-linked Applied Sections.
- 2026-06-18: Confirmed ditch and side slope highlight objects carry preset refs, linked status, surface roles, and nonzero surface patch counts.
- 2026-06-18: Fixed side slope subassembly-owned geometry to preserve the start edge point, allowing slope-face links and patches to come from Applied Sections instead of fallback/default geometry.
- 2026-06-18: Ran a focused FreeCADCmd pre-output review validation for linked, modified, missing_preset, preset_outdated, and snapshot states.
- 2026-06-18: Confirmed Build Corridor guided review summary exposes preset status counts before output generation.

### R5: Documentation cleanup after E2E

Update user-facing and architecture documentation after the final E2E result is known.

Acceptance criteria:

- `docsV1/README.md` links any new preset-management document if added
- user workflow docs describe linked, modified, snapshot, missing, and outdated states
- docs describe when generated outputs must be rebuilt after preset changes

Progress notes:

- 2026-06-18: Updated README workflow guidance to treat Subassembly presets as source contracts with reviewable states.
- 2026-06-18: Updated user-facing wiki docs for SubAssembly Designer, Assembly/Region, and Applied Sections/Build Corridor.
- 2026-06-18: Documented preset states, rebuild order, preset trace fields, and Build Corridor review properties.

## 14. Diagnostics

Diagnostics should include:

- missing preset reference
- preset version mismatch
- invalid override field
- unsupported subassembly kind
- missing point role
- missing link role
- missing surface role
- width or slope outside allowed range
- side slope without daylight-capable endpoint
- ditch without drainage surface role

## 15. Non-goals

This plan does not require:

- live rebuilding all corridor outputs while editing a preset
- automatically updating every Assembly when a shared preset changes
- treating generated preview geometry as editable preset data
- adding v0 compatibility behavior
- finalizing watertight solids for all Subassembly bodies

## 16. Architectural Effect

This plan keeps v1 ownership boundaries clear.

SubAssembly Designer becomes a source editor for reusable or instance-level Subassembly intent.

Assembly becomes the owner of where resolved Subassembly intent is placed.

Applied Sections remain evaluated station-wise result data.

Build Corridor remains responsible for generating output surfaces from Applied Section contracts.

## 17. Completion Status

Implementation status as of 2026-06-18:

- R1 complete: Designer and Assembly expose linked preset state, default application, local overrides, and stale state indicators.
- R2 complete: project preset library review, duplicate, rename, delete, and impact reporting are implemented.
- R3 complete: changed-field and preset difference indicators cover parameters, roles, shapes, targets, and surface contracts.
- R4 complete: FreeCADCmd E2E validation confirmed preset trace, surface roles, Build Corridor highlight surfaces, side-slope Applied Sections geometry, and pre-output preset status review.
- R5 complete: user-facing docs describe preset states, rebuild order, Applied Section trace fields, and Build Corridor review properties.

Follow-up candidates:

- add a short manual QA checklist for a full user click-through workflow
- add persistent automated contract tests from the focused FreeCADCmd validation scripts
- extend preset conflict handling for multi-user or imported library merge cases

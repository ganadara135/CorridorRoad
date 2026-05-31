# Parametric Road V1 Superelevation Implementation Plan

Date: 2026-05-31
Status: First implementation complete; manual QA pending
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_SUPERELEVATION_MODEL.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_MODEL.md`
- `docsV1/V1_3D_CENTERLINE_TOOLBAR_PLAN.md`
- `docsV1/V1_SECTION_MODEL.md`

## Purpose

This document defines how Superelevation should be introduced into the current Parametric Road v1 workflow.

The goal is to make station-based crossfall and roadway roll a durable source model that drives Applied Sections, Build Parametric surfaces, review panels, and later Watertight Solid outputs.

## Scope

This plan covers:

- Superelevation source object persistence
- Superelevation evaluation service
- Superelevation task panel and toolbar placement
- Applied Sections integration
- Cross Section Viewer and Build Parametric review handoff
- diagnostics and tests

This plan does not cover:

- jurisdiction-specific automatic design-table calculation
- full divided-highway lane-group synchronization
- ramp and intersection superelevation automation
- hydraulic or vehicle-dynamics analysis
- final IFC/LandXML superelevation export

## Core Rule

Superelevation is a source-owned station control model.

It must not be stored only as edited Assembly slopes, generated section wires, or Build Parametric mesh geometry.

The workflow rule is:

`Alignment + Profile + 3D Centerline + Superelevation + Assembly + Regions -> Applied Sections -> Build Parametric -> Review/Outputs`

## Current Code Baseline

The current project already has first-slice placeholders:

- `SuperelevationModel`
- `CrossfallControlRow`
- `RunoffTransitionRow`
- `SuperelevationConstraint`
- `superelevation_service.py`
- `V1_SUPERELEVATION_MODEL.md`

The first implementation now includes:

- FreeCAD source object persistence
- user-facing Superelevation editor
- deterministic station evaluation implementation
- Applied Sections integration
- Applied Sections review rows, Cross Section Viewer trace fields, and 3D preview bars
- Build Parametric Design Surface verification
- focused contract tests for effective crossfall behavior

## Toolbar Placement

Add `Superelevation` as a first-class v1 source stage after `3D Centerline` and before `Assembly`.

Recommended toolbar order:

`Project -> TIN -> Alignment -> Stations -> Profile -> Review Plan/Profile -> 3D Centerline -> Superelevation -> Assembly -> Regions -> Structures -> Drainage -> Applied Sections -> Build Parametric -> Review -> Outputs -> AI Assist -> Watertight Solids`

Reason:

- Alignment and Profile establish station/elevation context.
- `3D Centerline` creates the shared station/offset/elevation baseline.
- Superelevation modifies crossfall, not the centerline path.
- Assembly remains the default section composition source.
- Applied Sections consume the resolved combination.

## User Workflow

1. Build or import Alignment.
2. Generate Stations.
3. Build Profile.
4. Review Plan/Profile and apply `3D Centerline`.
5. Open `Superelevation`.
6. Click `Auto Calculate` or add control rows manually.
7. Validate station coverage and transition ranges.
8. Apply Superelevation source object.
9. Open Assembly and Regions.
10. Generate Applied Sections.
11. Review effective slopes in Cross Section Viewer and Build Parametric.

## UI Plan

### Main Panel

The `Superelevation` task panel should expose:

| Area | Purpose |
|---|---|
| Model ID | Identifies the persisted Superelevation source object. |
| Auto Calculate | Generates traceable Crossfall rows from Alignment curve criteria without auto-applying. |
| Control Rows | Defines station-specific left/right crossfall targets. |
| Transition Rows | Defines runout/runoff ranges and interpolation policy. |
| Constraints | Defines maximum rate, fixed crown zones, and warnings. |
| Review Samples | Shows evaluated crossfall at generated Stations. |
| Diagnostics | Shows validation and evaluation status. |

### Control Rows Table

Recommended columns:

| Column | Meaning |
|---|---|
| Control ID | Stable row identity, displayed without prefix. |
| STA | Station control location. |
| Side | `left`, `right`, `both`, or `center`. |
| Target | Target component group, such as lane, shoulder, or paved surface. |
| Crossfall % | Desired crossfall value. |
| Kind | `normal_crown`, `rotation_start`, `full_super`, `rotation_end`, or `reference_crossfall`. |
| Notes | Optional explanation. |

### Transition Rows Table

Recommended columns:

| Column | Meaning |
|---|---|
| Transition ID | Stable row identity, displayed without prefix. |
| Start STA | Transition start. |
| End STA | Transition end. |
| From Control | Source control row. |
| To Control | Target control row. |
| Policy | Initially `linear`; later `spiral_weighted` or design-standard policies. |
| Status | Valid, warning, or error. |

### Review Samples Table

Recommended columns:

| Column | Meaning |
|---|---|
| STA | Evaluated station. |
| Left Crossfall % | Effective left-side value. |
| Right Crossfall % | Effective right-side value. |
| Active Transition | Active transition row, if any. |
| Source | Control row or interpolation source. |
| Diagnostics | Degraded or missing state. |

### Buttons

Recommended button order:

`Auto Calculate -> Validate -> Apply -> Show Samples -> Close`

`Apply` stores source intent only.

`Show Samples` and `Show 3D Review` create review outputs, not source truth.

## Data Model Plan

### Extend Source Model

Add fields to the existing model as needed:

- `label`
- `lane_group_rows`
- `unit_context`
- `source_refs`
- `diagnostic_rows`

Keep first implementation focused on:

- control rows
- transition rows
- constraints

### FreeCAD Object

Add a persisted `V1SuperelevationSource` object.

Recommended properties:

- `SchemaVersion`
- `SuperelevationId`
- `AlignmentId`
- `ProfileId`
- `ControlRowsJson`
- `TransitionRowsJson`
- `ConstraintRowsJson`
- `DiagnosticRowsJson`
- `LastValidationStatus`

The object should be routed under:

`02_Alignment & Profile / Superelevation`

## Evaluation Plan

### SuperelevationService

Implement deterministic station queries:

- `evaluate_station(model, station)`
- `sample_stations(model, stations)`
- `validate(model, station_range)`

The first-slice station result should include:

- `station`
- `left_crossfall`
- `right_crossfall`
- `active_control_ids`
- `active_transition_id`
- `status`
- `diagnostic_rows`

### Transition Behavior

First implementation:

- linear interpolation between control rows
- exact control station match uses the control row value
- outside covered range falls back to Assembly default and emits warning

Deferred:

- runoff/runout auto generation
- design speed / radius table calculation
- spiral-weighted transition

## Applied Sections Integration

### Request Contract

Extend `AppliedSectionBuildRequest` and `AppliedSectionSetBuildRequest` with:

- `superelevation_model: SuperelevationModel | None`

### Component Resolution

During Applied Section build:

1. evaluate Superelevation at station
2. resolve Assembly default slopes
3. apply Superelevation to target components
4. persist effective slopes in component rows
5. preserve source provenance in parameters or dedicated fields

First-slice target components:

- `lane`
- `shoulder`

Do not apply Superelevation to:

- gutter and drainage collection geometry
- ditch shape interior geometry
- side-slope/daylight slope
- structure bodies
- drainage pipe geometry

These may react later through interaction rules, but they should not be directly rolled by the first implementation.

### Result Contract

Add derived Superelevation context to `AppliedSection`:

- active Superelevation ID
- left/right effective crossfall
- active transition ID
- crossfall source rows
- diagnostics

This context allows Cross Section Viewer, Build Parametric, and Watertight Solids to trace the effective geometry back to source rows.

Current implementation:

- `AppliedSectionBuildRequest` and `AppliedSectionSetBuildRequest` accept `superelevation_model`.
- `AppliedSectionService` evaluates Superelevation per station.
- `lane` and `shoulder` template component slopes are replaced with effective crossfall values before point/component rows are generated.
- original Assembly slope, effective source, transition ID, and crossfall percent are stored in component parameters.
- `AppliedSection` stores active Superelevation ID, left/right crossfall, active transition ID, and source rows.
- `V1AppliedSectionSet` stores and restores Superelevation context so generated state survives panel reopen and downstream builds.

## Build Parametric Integration

Build Parametric should not evaluate Superelevation directly.

It should consume the already resolved Applied Section point rows and component rows.

Expected effects:

- Design Surface reflects rolled lane/shoulder elevations.
- Surface Transition continues to operate on generated section point rows.
- Slope Face and Drainage Surface remain driven by their own resolved source context.

Current implementation:

- `CorridorSurfaceGeometryService.build_design_surface()` consumes `fg_surface` point rows from Applied Sections.
- Superelevation-resolved `fg_surface` elevations are therefore carried directly into the Design Surface TIN.
- Design Surface TIN source refs include `AppliedSectionSet.source_refs`, so Superelevation source provenance remains visible downstream.
- `CorridorSurfaceService` also carries `AppliedSectionSet.source_refs` into the surface model source refs.

## Viewer And Review Plan

### 3D Review

The first 3D review should show:

- station sample markers along the 3D Centerline
- short left/right crossfall bars at selected stations
- color by status:
  - green: valid
  - yellow: warning or fallback
  - red: error

Do not create solid or surface geometry for Superelevation review.

Current implementation:

- `Show Samples` fills the station sample table.
- `Show Samples` also creates or updates `V1SuperelevationReview`.
- `V1SuperelevationReview` draws short left/right crossfall bars from evaluated 3D Centerline station frames.
- the review object stores Superelevation ID, sample count, station labels, and bar width for traceability.

### Cross Section Viewer

Show:

- effective left/right crossfall
- active Superelevation control row
- active transition row
- whether slope came from Assembly default or Superelevation

Double-click behavior should focus the source stage, not edit generated section output.

## Preset Policy

Superelevation preset data is removed.

The source truth should come from one of two paths:

- `Auto Calculate` from Alignment design speed, radius, side friction, transition length, and max superelevation.
- Manual Control Rows and Transition Rows authored by the user.

## Validation Rules

Validation should report errors for:

- missing Alignment ID
- control station outside available station range
- transition start/end outside available station range
- transition end before start
- transition row references missing control rows
- side value outside accepted enum
- non-numeric crossfall

Validation should report warnings for:

- missing full station coverage
- duplicate control rows at the same station/side
- very high crossfall value
- transition shorter than minimum constraint
- no generated Stations available for review samples

## Implementation Phases

| Phase | Status | Work |
|---|---|---|
| 1. Source object | Done | Add `V1SuperelevationSource` persistence, JSON round-trip, tree routing, and model conversion helpers. |
| 2. Evaluation service | Done | Implement validation, station interpolation, sample rows, and diagnostics. |
| 3. Task panel | Done | Add Superelevation command, toolbar icon, tables, Auto Calculate, Validate/Apply/Show actions. |
| 4. Applied Sections integration | Done | Pass Superelevation model into build requests and resolve effective slopes into component/point rows. |
| 5. Review integration | Done | Applied Sections review rows, Cross Section Viewer output trace fields, and 3D crossfall bar preview are in place. |
| 6. Build Parametric verification | Done | Confirm Design Surface and output routing consume Superelevation-resolved Applied Sections without separate logic. |
| 7. Tests | Done | Source object, service, UI helper, Applied Sections, review, and Build Parametric verification tests are in place. |
| 8. Docs and QA | Done | Master workflow, wiki drafts, manual QA checklist, and implementation status are updated. |

## Acceptance Criteria

The first implementation is acceptable when:

- Superelevation has a dedicated toolbar command after `3D Centerline`.
- Opening the panel does not create source data automatically.
- Auto Calculate fills table rows only; it does not persist until `Apply`.
- `Validate` catches out-of-range and malformed rows.
- `Apply` creates or updates a persisted source object.
- Applied Sections change lane/shoulder point elevations according to evaluated crossfall.
- Build Parametric Design Surface reflects the changed Applied Sections.
- Cross Section Viewer can show effective crossfall provenance.
- 3D review can show evaluated crossfall bars at stations.
- Tests cover normal crown, simple transition, out-of-range controls, and Applied Section slope application.

## Testing Plan

Recommended focused tests:

- `tests/contracts/v1/test_v1_superelevation_source_object.py`
- `tests/contracts/v1/test_superelevation_service.py`
- `tests/contracts/v1/test_superelevation_editor_command.py`
- `tests/contracts/v1/test_result_builders.py`
- `tests/contracts/v1/test_applied_sections_command.py`
- `tests/contracts/v1/test_v1_applied_section_set_object.py`

Manual QA:

1. Create Alignment, Stations, Profile, and 3D Centerline.
2. Open Superelevation.
3. Confirm no source rows are created on open.
4. Click `Auto Calculate`.
5. Validate and Apply.
6. Generate Applied Sections.
7. Double-click a section inside full-super range.
8. Confirm lane/shoulder elevations are rolled.
9. Build Parametric.
10. Confirm Design Surface reflects the rolled crossfall.
11. Confirm no unexpected traceback appears in Report View.

## Risk Analysis

| Risk | Impact | Mitigation |
|---|---|---|
| Superelevation logic duplicates Assembly slope logic | Confusing source ownership | Keep Assembly as default slope source and Superelevation as station override source. |
| Build Parametric evaluates Superelevation again | Divergent geometry | Build Parametric must consume Applied Section results only. |
| Ditch or side slope geometry rolls incorrectly | Drainage and daylight errors | First implementation targets lane/shoulder only. |
| Transition rows become sampled-only data | Loss of design intent | Store transition rows as source and generate samples as review output. |
| UI becomes too engineering-table-heavy | Poor usability | Provide Auto Calculate and Review Samples. |
| Existing tests assume static Assembly slopes | Regression failures | Add Superelevation-specific tests and keep no-model behavior identical. |

## Non-goals

- automatic AASHTO or Korean standard table design
- vehicle speed/radius-based design automation
- full interchange/ramp crossfall synchronization
- direct editing of generated Applied Section geometry
- storing Superelevation inside Build Parametric output objects

## Summary

Superelevation should enter Parametric Road v1 as a dedicated source stage after `3D Centerline`.

It should evaluate station-based crossfall into Applied Sections, while Assembly continues to define default section composition.

The first implementation should be deliberately narrow:

- source rows
- linear transitions
- lane/shoulder effective crossfall
- Applied Sections integration
- Build Parametric verification
- clear review diagnostics

This keeps the feature aligned with the v1 source -> evaluation -> result -> output -> presentation architecture and prepares the project for more advanced roadway design automation later.

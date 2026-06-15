# Parametric Road V1 Superelevation Auto Calculation Plan

Date: 2026-05-31
Status: Draft implementation plan
Depends on:

- `docsV1/V1_SUPERELEVATION_MODEL.md`
- `docsV1/V1_SUPERELEVATION_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_MODEL.md`
- `docsV1/V1_3D_CENTERLINE_TOOLBAR_PLAN.md`
- `docsV1/V1_SECTION_MODEL.md`

## Purpose

This document defines how Parametric Road v1 should generate Superelevation and effective Crossfall control rows automatically from the current Alignment, Profile, 3D Centerline, Stationing, and design criteria.

The goal is to reduce manual station-by-station crossfall editing while preserving the v1 rule that design intent remains in source models and generated geometry remains a result.

## Scope

This plan covers:

- automatic Superelevation control-row generation
- automatic effective left/right Crossfall generation
- use of Alignment curve radius, curve direction, design speed, side friction, and maximum Superelevation
- use of Profile and 3D Centerline as station/elevation context
- Superelevation panel UX for calculation, review, validation, and Apply
- Applied Sections handoff after automatic calculation
- diagnostics and tests

This plan does not cover:

- jurisdiction-specific design table libraries beyond a first practical formula-based calculation
- ramp and intersection Superelevation automation
- multi-lane divided-highway rotation policies
- vehicle dynamics simulation
- final LandXML/IFC Superelevation export

## Core Rule

Superelevation owns station-based effective Crossfall.

Assembly owns default crossfall and section Subassembly geometry. Superelevation reads those defaults and overrides lane and shoulder crossfall by station when active.

The ownership rule is:

```text
Assembly default crossfall
        +
Alignment curve / radius / design speed / side friction / policy
        ↓
Superelevation auto calculation
        ↓
Superelevation control rows + effective Crossfall rows
        ↓
Applied Sections
        ↓
Build Parametric
```

Build Parametric must not calculate Superelevation. It consumes Applied Section point rows that already contain the resolved effective Crossfall.

## Terminology

| Term | Meaning |
| --- | --- |
| Assembly Default Crossfall | Base lane/shoulder slope from Assembly. Used when no Superelevation override is active. |
| Superelevation | Station-based curve rollover policy and transition source. |
| Effective Crossfall | Final left/right crossfall applied at a station after Assembly defaults and Superelevation overrides are resolved. |
| Runout | Transition from normal crown to zero crossfall on the rotating side. |
| Runoff | Transition from zero crossfall to full Superelevation. |
| Full Super | Curve segment where the target Superelevation rate is fully applied. |

## Input Data

The auto calculator should read:

| Source | Use |
| --- | --- |
| `AlignmentModel` / `V1Alignment` | Curve radius, curve start/end station, curve direction, PI geometry, transition length if available. |
| Alignment criteria | `DesignSpeedKph`, `SuperelevationPct`, `SideFriction`, `MinRadius`, `CriteriaStandard`. |
| `ProfileModel` | Profile availability and grade context for diagnostics. |
| `Centerline3DResult` | Station frame, tangent direction, elevation, and final sampled station context. |
| `V1Stationing` | Candidate station list for sample review and QA. |
| `AssemblySubassemblyModel` | Default lane/shoulder crossfall and available target Subassembly sides. |

If no Assembly is available, the calculator may still generate Superelevation control rows, but it should warn that effective Crossfall cannot be verified against target Subassemblies.

## Calculation Policy

### Curve Detection

The first implementation should detect horizontal curve segments from Alignment geometry rows or PI rows.

For each curve:

1. Determine start STA and end STA.
2. Determine radius.
3. Determine left/right curve direction.
4. Determine available transition length if Alignment has spiral or transition rows.
5. Flag short or overlapping curve areas.

### Target Superelevation Rate

Use the common first-slice relationship:

```text
e + f = V^2 / (127R)
```

Where:

- `e` = Superelevation rate
- `f` = side friction
- `V` = design speed in km/h
- `R` = curve radius in m

Then:

```text
target_e = clamp((V^2 / (127R)) - f, 0, max_e)
```

For the first implementation:

- read `V` from `Alignment.DesignSpeedKph`
- read `f` from `Alignment.SideFriction`
- read `max_e` from `Alignment.SuperelevationPct`
- keep all output Crossfall values in percent
- emit diagnostics when radius is missing, zero, too small, or below `MinRadius`

### Crossfall Direction

Normal crown uses Assembly defaults or a configured default such as:

```text
left = -2.0%
right = -2.0%
```

Full Superelevation should rotate both target sides toward the curve inside/downhill direction.

The first implementation should support:

| Curve Direction | Full Super Intent |
| --- | --- |
| right curve | right side becomes downhill; left side follows same plane. |
| left curve | left side becomes downhill; right side follows same plane. |

Exact sign convention must match the current Applied Sections side convention:

- left side uses positive lateral offset
- right side uses negative lateral offset
- effective slope is written into lane/shoulder Subassembly parameters before point rows are generated

### Transition Rows

For each curve, generate source rows for:

1. normal crown before transition
2. runout start
3. crown removed
4. full super start
5. full super end
6. return transition
7. normal crown after transition

If available curve length is too short:

- still generate a conservative row sequence when possible
- mark diagnostics as `warning`
- avoid silently overwriting the user's existing rows without confirmation

## Generated Source Rows

The calculator writes proposed rows into the Superelevation panel tables, not directly into generated geometry.

Example:

```text
STA        Left Crossfall     Right Crossfall     Kind
0.000      -2.000%            -2.000%             normal_crown
40.000     -2.000%             0.000%             crown_removed
70.000      2.000%             2.000%             reverse_crown
100.000     6.000%             6.000%             full_super
160.000     6.000%             6.000%             full_super
190.000    -2.000%            -2.000%             normal_crown
```

Current `CrossfallControlRow` stores one `side` and one `crossfall_percent` per row. Therefore the generated model should produce paired left/right rows where needed:

```text
control:right-full:left    STA 100.000    left     6.000    full_super
control:right-full:right   STA 100.000    right    6.000    full_super
```

The sample table should continue to show the resolved effective left/right values together.

## Superelevation Panel UX

Add a new action:

```text
Auto Calculate
```

Recommended button order:

```text
Auto Calculate | Validate | Apply | Show Samples | Close
```

`Auto Calculate` behavior:

1. Read Alignment, Profile, 3D Centerline, Stationing, and Assembly.
2. Find candidate curve segments.
3. Calculate target Superelevation and effective Crossfall rows.
4. Fill the Superelevation control and transition tables.
5. Show diagnostics in the status area.
6. Do not persist changes until the user clicks `Apply`.

If user-edited rows already exist, show a non-destructive overwrite warning in the status area before replacing rows. A later implementation may add an explicit confirmation dialog.

## Workflow

Recommended user flow:

```text
Alignment
-> Stations
-> Profile
-> Review Plan/Profile
-> 3D Centerline
-> Superelevation
   -> Auto Calculate
   -> Validate
   -> Show Samples
   -> Apply
-> Assembly
-> Regions
-> Applied Sections / Build Sections
-> Build Parametric
```

When Superelevation is changed:

1. Click `Apply` in Superelevation.
2. Click `Build Sections` in Applied Sections.
3. Rebuild Build Parametric.
4. Review Cross Section Viewer and Design Surface.

## Service Design

Add a dedicated service:

```text
freecad/Corridor_Road/v1/services/evaluation/superelevation_auto_calculation_service.py
```

Suggested classes:

```text
SuperelevationAutoCalculationRequest
SuperelevationCurveCandidate
SuperelevationAutoCalculationResult
SuperelevationAutoCalculationService
```

`SuperelevationAutoCalculationResult` should contain:

- generated `SuperelevationModel`
- curve candidate rows
- calculation diagnostics
- input criteria snapshot
- source refs

The task panel should call the service and then update table rows from the generated model.

## Diagnostics

The service should report:

| Kind | Severity | Meaning |
| --- | --- | --- |
| `missing_alignment` | error | No Alignment source is available. |
| `missing_centerline3d` | warning/error | 3D Centerline is unavailable for station frame review. |
| `missing_profile` | warning | Profile context is unavailable. |
| `missing_assembly` | warning | Default crossfall cannot be compared to Assembly target Subassemblies. |
| `curve_radius_missing` | error | Curve cannot be calculated without radius. |
| `curve_radius_below_minimum` | warning | Radius is below the selected design criteria. |
| `transition_length_short` | warning | Curve does not have enough available length for the target transition policy. |
| `curve_overlap` | warning | Generated transition windows overlap neighboring curve windows. |
| `criteria_default_used` | info | Design speed, side friction, or max e used fallback defaults. |

## UI Acceptance Criteria

- Superelevation panel has `Auto Calculate`.
- Clicking `Auto Calculate` does not create or update a FreeCAD source object by itself.
- Generated rows appear in the existing Control Rows and Transitions tables.
- Status area lists the number of detected curves and generated rows.
- `Validate` runs on the generated rows.
- `Show Samples` displays effective left/right Crossfall values from the generated model.
- `Apply` persists the generated Superelevation source object.

## Applied Sections Acceptance Criteria

- Applied Sections consume the auto-generated Superelevation model with no special Build Parametric logic.
- `Build Sections` stores active Superelevation ID, left/right Crossfall, transition ID, and source rows.
- Cross Section Viewer shows Superelevation summary rows.
- Build Parametric Design Surface changes after auto-generated Superelevation is applied and Applied Sections are rebuilt.

## Implementation Phases

| Phase | Status | Work |
| --- | --- | --- |
| 1. Plan and contract | Done | Add this plan, service request/result contracts, and test fixtures. |
| 2. Curve candidate extraction | Done | Read Alignment rows and produce curve candidates with station range, radius, and direction. |
| 3. Calculation service | Done | Compute target `e`, runoff/full-super stations, paired Crossfall rows, and diagnostics. |
| 4. Panel action | Done | Add `Auto Calculate` button and table population. |
| 5. Validation integration | Done | Reuse existing Superelevation validation against generated rows. |
| 6. Applied Sections verification | Pending | Confirm generated rows produce effective crossfall in Applied Sections and Cross Section Viewer. |
| 7. Manual QA | Pending | Verify a right curve and left curve in FreeCAD with 3D review and Build Parametric output. |

## Test Plan

Add focused tests for:

- curve candidate extraction from a simple Alignment
- target Superelevation formula using design speed, radius, side friction, and max e
- right-curve row generation
- left-curve row generation
- short transition diagnostics
- panel `Auto Calculate` fills rows without applying
- Applied Sections consume the generated rows
- Cross Section Viewer exposes generated Superelevation summary rows

## Risk Table

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Sign convention is wrong | Crossfall tilts the wrong direction | Add left/right curve tests and compare with Applied Section point rows. |
| Design criteria vary by jurisdiction | Formula-only result may not match local standards | Treat first version as recommendation and keep criteria explicit. |
| Auto rows overwrite user edits | User loses manual control | Do not persist until `Apply`; show overwrite warning before replacing panel rows. |
| Transition windows overlap | Invalid or confusing Crossfall sequence | Emit diagnostics and keep generated rows reviewable. |
| Build Parametric recalculates Superelevation | Divergent results | Keep Build Parametric consuming Applied Sections only. |

## Non-goals

- Superelevation does not edit Alignment geometry.
- Superelevation does not replace Assembly Subassembly definitions.
- Superelevation does not directly build corridor surfaces.
- Superelevation auto calculation does not silently overwrite accepted source state.

## Summary

Superelevation auto calculation should generate both Superelevation and effective Crossfall controls.

Assembly remains the default crossfall source. Superelevation becomes the station-based override source, and Applied Sections remain the place where final station geometry is resolved.

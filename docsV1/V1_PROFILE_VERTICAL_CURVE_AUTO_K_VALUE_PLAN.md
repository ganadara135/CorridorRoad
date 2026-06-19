# V1 Profile Vertical Curve K-Value Auto Generation Plan

## Purpose

Replace the current simple `Auto from PVI` vertical curve generator with a more practical K-value based workflow.

The Profile editor should generate parabolic vertical curve rows from PVI geometry, design speed, minimum K values, and spacing constraints.

## Scope

- Applies to the v1 `Profile` panel.
- Focuses on the `Vertical Curves` tab.
- Keeps `VerticalCurveRow.kind` internally fixed as `parabolic_vertical_curve`.
- Lets Crest/Sag be inferred from grade change, not selected by the user.
- Produces diagnostics when generated curve lengths are clamped or skipped.

## Core Rule

Vertical curve shape intent belongs in the Profile source model.

The UI may generate source rows, but it must not hide engineering assumptions inside preview drawing.

## Current Behavior

`Auto from PVI` currently creates rows from a fixed length:

```text
Start STA = PVI station - Auto curve length / 2
End STA   = PVI station + Auto curve length / 2
Length    = Auto curve length
```

This is useful for sample data, but it does not reflect design-speed or sight-distance driven practice.

## Target Behavior

For each internal PVI:

```text
g1 = incoming grade
g2 = outgoing grade
A  = g2 - g1
type = Crest if A < 0
type = Sag   if A > 0
K = required K value for design speed and type
L_required = K * abs(A * 100)
```

The generated vertical curve row remains:

```python
{
    "kind": "parabolic_vertical_curve",
    "station_start": ...,
    "station_end": ...,
    "length": ...,
    "parameter": 0.0,
}
```

## User Experience

### Vertical Curves tab

Keep the table simple:

```text
Start STA | End STA | Length | Parameter
```

Add compact K-value auto controls above the table:

```text
Auto method: K-value Design
Design speed: [Project default / numeric]
Min length: [30 m]
Max length: [300 m]
Auto from PVI
```

Do not add Crest/Sag selection.

Crest/Sag appears in:

- Curve Preview labels
- Curve Preview info panel
- Auto generation diagnostics

## K-Value Defaults

Initial placeholder defaults:

```python
K_VALUE_DEFAULTS = {
    40: {"crest": 7.0, "sag": 8.0},
    50: {"crest": 12.0, "sag": 13.0},
    60: {"crest": 18.0, "sag": 18.0},
    70: {"crest": 28.0, "sag": 24.0},
    80: {"crest": 44.0, "sag": 32.0},
    90: {"crest": 60.0, "sag": 40.0},
    100: {"crest": 84.0, "sag": 52.0},
}
```

These defaults are implementation placeholders.

The first implementation routes K-value lookup through `design_standards.py` and reads the active Project Setup design standard in the Profile panel.

Future work should replace the placeholder K tables with reviewed KDS/AASHTO source tables.

## Clamp Rules

Generated length must fit available spacing:

```text
left_available  = PVI station - previous station
right_available = next station - PVI station
spacing_limit   = 2 * min(0.8 * left_available, 0.8 * right_available)
```

Final length:

```text
L_final = min(L_required, max_length, spacing_limit)
L_final = max(L_final, min_length) when spacing allows
```

If `min_length` cannot fit spacing, clamp to spacing and warn.

## Diagnostics

Auto generation should report:

- generated curve count
- crest count
- sag count
- skipped PVI count
- clamped curve count

Diagnostic examples:

```text
[PVI STA 80.000] Crest required L=142.000m, clamped to 56.000m by adjacent PVI spacing.
[PVI STA 160.000] Sag required L=96.000m, clamped to 80.000m by max length.
[PVI STA 240.000] Skipped: grade difference below threshold.
```

## Implementation Steps

| Step | Status | Task |
| --- | --- | --- |
| 1 | Done | Add K-value lookup helper for crest/sag and design speed. |
| 2 | Done | Extend vertical curve auto generator to compute grade-in, grade-out, A, curve type, K, and required length. |
| 3 | Done | Add min/max length and design speed controls to the Vertical Curves tab. |
| 4 | Done | Update `Auto from PVI` to use K-value generation and show summary diagnostics. |
| 5 | Done | Keep all generated rows as `parabolic_vertical_curve`; do not expose Kind selection. |
| 6 | Done | Add contract tests for K lookup, Crest/Sag detection, length generation, clamp rules, and diagnostics. |
| 7 | Done | Run FreeCADCmd validation for Profile preview and Centerline3D consistency. |
| 8 | Done | Add manual QA checklist for K-value auto generation. |
| 9 | Done | Route K-value lookup through `design_standards.py` and active Project Setup design standard. |

## Acceptance Criteria

- `Auto from PVI` generates vertical curve length from grade difference and K value.
- Crest/Sag is inferred automatically from grade change.
- Generated rows are always stored as `parabolic_vertical_curve`.
- Vertical Curves table has no editable `Kind` column.
- Clamp warnings are visible when required length cannot fit spacing or max length.
- Preview labels show `Parabola Crest` and `Parabola Sag`.
- Existing Profile curve preview tests pass.
- Existing Centerline3D consistency tests pass.

## Manual QA Checklist

- [ ] Create a profile with at least five PVI rows.
- [ ] Set a design speed and min/max length.
- [ ] Click `Auto from PVI`.
- [ ] Confirm generated curve count matches internal PVI count with meaningful grade change.
- [ ] Confirm Crest/Sag labels appear in Curve Preview.
- [ ] Reduce max length and confirm clamp diagnostics appear.
- [ ] Create closely spaced PVI rows and confirm spacing clamp diagnostics appear.
- [ ] Build 3D Centerline and confirm it follows the generated Profile curve.

## Non-goals

- Do not implement full KDS/AASHTO standards tables in this first pass.
- Do not store Crest/Sag as editable source fields.
- Do not generate 3D Centerline or Applied Sections directly from the Profile editor.
- Do not turn Curve Preview into an editor.

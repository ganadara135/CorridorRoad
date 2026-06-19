# V1 Alignment/Profile Curve Preview Plan

## Purpose

Add a curve-information preview to the Alignment and Profile panels.

The preview should show which curve definitions are applied to the current source line and whether those curves are being evaluated by downstream results such as 3D Centerline and Applied Sections.

## Scope

This plan covers:

- Alignment panel curve preview
- Profile panel vertical-curve preview
- shared curve diagnostics
- 2D preview widgets inside each source panel
- optional 3D review highlight handoff
- validation that 3D Centerline consumes the same curve evaluation

This plan does not replace the dedicated `Review Plan/Profile` or `3D Centerline` stages.

## Core Rule

Alignment and Profile remain source editors.

Curve Preview is a read-only review aid inside those editors.

It must not generate corridor geometry, Applied Sections, or Build Corridor outputs.

## Design Goals

- Let users see curve definitions before downstream build steps.
- Make missing or invalid curve rows visible immediately.
- Distinguish source PVI/tangent lines from evaluated curve geometry.
- Explain why 3D Centerline may appear broken, tangent-only, or sparse.
- Keep the preview close to the data table that controls it.
- Reuse the same evaluation services used by 3D Centerline.

## User Experience

### Alignment Panel

Add a `Curve Preview` area below the Alignment element table.

Show:

- current alignment polyline/source points
- evaluated horizontal curve sample line
- selected element highlight
- curve metadata for selected element
- horizontal curve start/end markers
- PI/PC/PT markers when available
- circular curve center point when available
- radius line from curve center to selected sample point
- tangent-in/tangent-out helper lines
- curve direction and station labels
- warning banner when an element looks curved but is evaluated as tangent/polyline only

Recommended display:

- source sample points: yellow markers
- evaluated alignment path: cyan line
- selected curve element: orange line
- PC/PT markers: yellow square markers
- PI marker: white marker
- circular curve center: small magenta marker
- radius helper line: faint magenta line
- tangent helper lines: faint gray dashed lines
- invalid/unsupported curve: red dashed line

### Profile Panel

Add a `Curve Preview` area below the PVI and Vertical Curve tables.

Show:

- PVI tangent lines
- evaluated vertical profile curve
- BVC/PVI/EVC markers
- BVC and EVC station/elevation labels
- vertical curve length label
- incoming and outgoing grade labels
- high/low point marker when it falls inside the curve
- vertical offset/deviation indicator between tangent chord and evaluated curve
- selected vertical curve highlight
- grade-in/grade-out labels
- warning banner when a vertical curve row cannot be evaluated as parabolic

Recommended display:

- source PVI tangent line: orange/red
- evaluated profile curve: cyan
- BVC/EVC: yellow markers
- PVI: white marker
- high/low point: green marker
- chord deviation helper: faint blue vertical indicator
- active selected curve: thicker cyan/orange overlay
- invalid curve: red dashed segment

## Required Curve Annotations

Curve Preview must expose the engineering terms that explain the displayed line.

### Profile Vertical Curve Annotations

Show these annotations when a vertical curve row is selected or visible:

| Label | Meaning | Required |
| --- | --- | --- |
| `BVC` | Beginning of Vertical Curve | yes |
| `PVI` | Point of Vertical Intersection | yes, when known |
| `EVC` | End of Vertical Curve | yes |
| `L` | Vertical curve length | yes |
| `g1` | Incoming grade | yes |
| `g2` | Outgoing grade | yes |
| `A` | Algebraic grade difference, `g2 - g1` | yes |
| `K` | Curve length divided by grade difference, when computable | optional first release |
| `HP/LP` | High point or low point inside curve | yes, when it exists inside BVC/EVC |
| `Max deviation` | Maximum offset from tangent chord to evaluated curve | yes |

### Alignment Horizontal Curve Annotations

Show these annotations when a horizontal curve element is selected or visible:

| Label | Meaning | Required |
| --- | --- | --- |
| `PC` | Point of Curvature | yes, when available |
| `PI` | Point of Intersection | yes, when available |
| `PT` | Point of Tangency | yes, when available |
| `R` | Radius | yes for circular curves |
| `Delta` | Deflection/central angle | yes for circular curves |
| `L` | Arc length | yes |
| `T` | Tangent length | optional first release |
| `E` | External distance | optional first release |
| `M` | Middle ordinate | optional first release |
| `Center` | Circle center point | yes for circular curves |
| `Direction` | Left/right or clockwise/counterclockwise curve direction | yes |

If exact PC/PI/PT data is unavailable, show `estimated` in the label and include a diagnostic row.

## Preview Controls

Use compact controls above each preview canvas:

| Control | Alignment | Profile | Purpose |
| --- | --- | --- | --- |
| `Refresh Preview` | yes | yes | Re-evaluate current unsaved table values in memory. |
| `Show Source` | yes | yes | Toggle source points/tangent chord. |
| `Show Evaluated Curve` | yes | yes | Toggle evaluated curve line. |
| `Show Labels` | yes | yes | Toggle station, radius, grade, and curve labels. |
| `Sample Interval` | yes | yes | Controls preview sampling density only. |
| `Highlight Selected Row` | yes | yes | Sync table selection to preview highlight. |

The default should show source and evaluated curve together.

## Information Panel

Show a small read-only info panel beside or below the preview.

### Alignment Curve Info

Display:

- element id
- kind
- station start/end
- length
- PC station and coordinate when available
- PI station and coordinate when available
- PT station and coordinate when available
- radius for circular curves
- central angle for circular curves
- curve direction
- circle center coordinate when available
- point count
- radius or curve parameter when available
- evaluation status
- diagnostic summary

### Profile Curve Info

Display:

- vertical curve id
- kind
- station start/end
- length
- BVC station/elevation
- PVI station/elevation
- EVC station/elevation
- grade in
- grade out
- algebraic grade difference
- K value when computable
- high/low point station/elevation when it exists
- maximum chord deviation
- evaluation status
- diagnostic summary

## Evaluation Contracts

Add small result contracts for preview data instead of drawing directly from UI tables.

Recommended result rows:

```text
AlignmentCurvePreviewResult
AlignmentCurvePreviewPointRow
AlignmentCurvePreviewDiagnosticRow

ProfileCurvePreviewResult
ProfileCurvePreviewPointRow
ProfileCurvePreviewDiagnosticRow
```

These should live near result/viewer contracts, not inside the task panel.

The task panel should only:

- collect current table state
- call the preview service
- render the returned rows
- display diagnostics

## Service Placement

Preferred services:

```text
freecad/Corridor_Road/v1/services/evaluation/alignment_curve_preview_service.py
freecad/Corridor_Road/v1/services/evaluation/profile_curve_preview_service.py
```

These services should reuse:

- `AlignmentEvaluationService`
- `ProfileEvaluationService`
- `Centerline3DEvaluationService` where relevant for consistency checks

## Diagnostics

Add user-visible diagnostics.

| Diagnostic kind | Severity | Meaning |
| --- | --- | --- |
| `alignment_curve_preview_ok` | info | Alignment curve preview was evaluated. |
| `alignment_curve_missing_geometry` | warning | Alignment element has insufficient geometry payload. |
| `alignment_curve_polyline_only` | warning | Alignment curve is represented by sampled polyline points only. |
| `alignment_curve_pc_pi_pt_estimated` | warning | PC/PI/PT labels were estimated from available geometry. |
| `alignment_circular_curve_center_missing` | warning | Circular curve center could not be resolved. |
| `alignment_circular_curve_radius_missing` | warning | Circular curve radius could not be resolved. |
| `profile_curve_preview_ok` | info | Profile curve preview was evaluated. |
| `profile_vertical_curve_missing_pvi` | warning | Vertical curve row has no usable PVI control. |
| `profile_vertical_curve_linear_fallback` | warning | Profile curve fell back to linear interpolation. |
| `profile_vertical_curve_parabolic_evaluated` | info | Vertical curve was evaluated as parabolic. |
| `profile_vertical_curve_bvc_evc_labeled` | info | BVC/EVC labels were resolved. |
| `profile_vertical_curve_high_low_point` | info | High/low point was resolved inside the curve. |
| `profile_vertical_curve_high_low_point_outside` | warning | Computed high/low point falls outside BVC/EVC. |
| `centerline3d_curve_sample_mismatch` | warning | 3D Centerline samples do not reflect the displayed curve preview. |

## Implementation Order

| Step | Status | Work |
| --- | --- | --- |
| 1 | Done | Add Profile curve preview result rows and service using `ProfileEvaluationService`. |
| 2 | Done | Add Profile BVC/PVI/EVC, grade, high/low point, and max deviation annotations to preview result rows. |
| 3 | Done | Add Profile panel preview canvas below PVI/Vertical Curve tables. |
| 4 | Done | Add Profile curve info panel, legend, and diagnostics banner. |
| 5 | Done | Add FreeCADCmd validation for parabolic profile preview points, BVC/EVC labels, and linear fallback diagnostics. |
| 6 | Done | Add Alignment curve preview result rows and service using `AlignmentEvaluationService`. |
| 7 | Done | Add Alignment PC/PI/PT, radius, center, delta, tangent helper, and curve direction annotations to preview result rows. |
| 8 | Done | Add Alignment panel preview canvas below element table. |
| 9 | Done | Add Alignment curve info panel, legend, and diagnostics banner. |
| 10 | Pending | Add FreeCADCmd validation for alignment preview sampling, circular curve labels, and unsupported geometry diagnostics. |
| 11 | Done | Add shared `Centerline3D consistency` check comparing curve preview samples with 3D Centerline samples. |
| 12 | Done | Add manual QA checklist for Profile curve, Alignment curve, 3D Centerline consistency, and annotation readability. |

## Acceptance Criteria

- Profile panel shows both PVI tangent chord and evaluated vertical curve.
- Profile panel labels BVC, PVI, EVC, grades, curve length, and high/low point where applicable.
- Alignment panel shows source points and evaluated alignment path.
- Alignment panel labels PC, PI, PT, radius, circle center, delta angle, and curve direction where applicable.
- Selecting a table row highlights the corresponding preview segment.
- Invalid or unsupported curve rows show warnings before Apply.
- Profile preview uses the same parabolic evaluation as 3D Centerline.
- Alignment preview uses the same station evaluation as 3D Centerline.
- 3D Centerline consistency diagnostics identify when the preview curve and 3D result diverge.
- Preview controls do not modify source data until the user clicks Apply.

## Manual QA Checklist

### Profile curve QA

- [ ] Create a Profile with three PVI rows and one parabolic vertical curve.
- [ ] Confirm the Profile preview shows a cyan evaluated curve distinct from the red/orange tangent chord.
- [ ] Confirm BVC, PVI, EVC, grade-in, grade-out, length, K value, and max-deviation labels are readable.
- [ ] Confirm high/low point appears when it falls inside the vertical curve.
- [ ] Move the vertical curve start/end so the PVI is not exactly centered.
- [ ] Confirm the preview still evaluates a parabolic curve or shows a clear warning.
- [ ] Remove the vertical curve row.
- [ ] Confirm the preview shows tangent-only behavior and warning text.

### Alignment curve QA

- [ ] Create an Alignment with curved sampled geometry.
- [ ] Confirm the Alignment preview shows cyan evaluated path and orange source points.
- [ ] Confirm PC, PI, PT, radius, center, delta, tangent helper, and curve direction appear when circular curve data exists.
- [ ] Confirm estimated labels are clearly marked when exact circular curve data is unavailable.
- [ ] Confirm missing source geometry produces a visible warning instead of silently drawing a misleading curve.

### 3D Centerline consistency QA

- [ ] Build 3D Centerline after Profile and Alignment previews look correct.
- [ ] Confirm the 3D Centerline follows the same evaluated Profile/Alignment curve preview at common stations.
- [ ] Confirm consistency diagnostics report `centerline3d_preview_consistency_ok` when common samples match.
- [ ] Intentionally change one source curve or rebuild from stale data.
- [ ] Confirm consistency diagnostics can report `centerline3d_curve_sample_mismatch`.

### Annotation readability QA

- [ ] Confirm labels remain readable on the dark task-panel theme.
- [ ] Confirm cyan/orange/yellow legend text matches the canvas colors.
- [ ] Confirm long element IDs do not make the preview info panel unusable.
- [ ] Confirm the preview remains read-only and does not create FreeCAD geometry objects.

## Risks

| Risk | Mitigation |
| --- | --- |
| Preview becomes another hidden geometry generator. | Keep it read-only and route all geometry through preview result rows. |
| Preview uses different math from 3D Centerline. | Reuse existing evaluation services and add consistency diagnostics. |
| Panel becomes too tall. | Use collapsible preview group or fixed-height canvas. |
| Users confuse source chord with evaluated curve. | Use explicit colors, legend, and labels. |

## Non-goals

- Do not generate Applied Sections from this preview.
- Do not generate Build Corridor outputs from this preview.
- Do not edit curve geometry directly from the preview canvas in the first implementation.
- Do not duplicate independent curve math inside the task panel.

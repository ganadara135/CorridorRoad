# Parametric Road V1 Applied Section Supplemental Sampling Manual QA

Date: 2026-06-19
Status: manual QA procedure; execution pending real FreeCAD document

Depends on:

- [V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md](./V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md)
- [V1_CENTERLINE_OWNERSHIP_CONSOLIDATION_PLAN.md](./V1_CENTERLINE_OWNERSHIP_CONSOLIDATION_PLAN.md)
- [wiki/Applied-Sections-Build-Corridor.md](./wiki/Applied-Sections-Build-Corridor.md)

## Purpose

This checklist verifies that supplemental sampling is owned by `Applied Sections`.

The goal is to confirm that curved 3D Centerline spans receive complete supplemental `AppliedSection` rows before Build Parametric creates surfaces.

Build Parametric should consume those rows.

It should not create hidden supplemental frames during normal surface generation.

## Scope

This QA covers:

- curved 3D Centerline detection
- strong sag and crest vertical curve detection
- Applied Sections supplemental section count
- density change behavior
- Build Parametric consumed section summary
- design surface following the 3D Centerline
- lane, shoulder, ditch, and side slope continuity
- temporary compatibility fallback messaging for old AppliedSectionSet data

This QA does not certify final watertight solids.

## Preconditions

Use a real FreeCAD document with:

- Project created
- Alignment with at least one visible horizontal curve or 3D curved Centerline path
- Profile with at least one visibly strong sag or crest vertical curve when testing vertical supplemental sampling
- Stations sparse enough that the curve is visibly under-sampled without supplemental sections
- Profile generated
- 3D Centerline generated and visible
- SubAssembly Designer definitions or Assembly/Subassembly rows including lane, shoulder, ditch, and side_slope where possible
- Regions generated
- Existing-ground TIN available when daylight or ditch terrain interaction is being checked

Do not count a synthetic or demo fallback document as a pass.

## Baseline Off Check

1. Open `Applied Sections`.
2. Disable `Supplemental Sections`.
3. Click `Build Sections`.
4. Confirm the summary reports `Supplemental sections: 0`.
5. Open `Build Parametric`.
6. Click `Apply`.
7. Confirm the generated Build Parametric preview object properties report zero consumed supplemental sections.
8. Inspect the design surface near the curve.
9. Record whether the surface visibly cuts the curve or appears faceted.

Pass conditions:

- Applied Sections can build with supplemental sections disabled.
- Build Parametric reports consumed source sections only.
- No Python traceback appears.

## Low Density Check

1. Open `Applied Sections`.
2. Enable `Supplemental Sections`.
3. Set Density to a low or medium value.
4. Click `Build Sections`.
5. Confirm the summary reports supplemental sections greater than zero on the curved span.
6. Confirm the review table includes `curve_supplemental` rows.
7. Double-click at least one supplemental row.
8. Confirm the preview section lies on or near the 3D Centerline curve.
9. Open `Build Parametric`.
10. Click `Apply`.
11. Confirm the generated Build Parametric preview object properties report consumed supplemental sections.

Pass conditions:

- Supplemental rows are created in Applied Sections, not Build Parametric.
- Supplemental rows contain normal section geometry, not only frame markers.
- Build Parametric does not expose a supplemental density slider.

## High Density Check

1. Open `Applied Sections`.
2. Increase Density.
3. Click `Build Sections`.
4. Record source, supplemental, and total section counts.
5. Rebuild `Build Parametric`.
6. Compare the curve surface against the Low Density result.

Pass conditions:

- Supplemental section count increases.
- Total Applied Section count increases.
- Design surface follows the 3D Centerline more closely.
- Straight spans do not become unnecessarily dense if they are not curved.

Fail conditions:

- Density changes only Build Parametric output but not Applied Sections counts.
- Supplemental section count stays zero on a visibly curved 3D Centerline.
- Straight spans become excessively dense while curved spans remain sparse.

## Strong Vertical Curve Check

Use a corridor with a strong sag or crest Profile curve and little or no horizontal curvature.

1. Build and review `3D Centerline`.
2. Confirm the 3D Centerline visibly bends in elevation.
3. Open `Applied Sections`.
4. Enable `Supplemental Sections`.
5. Set a density and vertical threshold suitable for the test document.
6. Click `Build Sections`.
7. Confirm supplemental sections are generated inside the vertical curve span.
8. Confirm diagnostics include vertical curve trigger rows when implemented.
9. Rebuild `Build Parametric`.
10. Confirm the design surface follows the vertical curve instead of the straight endpoint chord.

Pass conditions:

- Supplemental sections appear in the strong vertical curve span.
- Surface geometry follows the 3D Centerline elevation curve.
- Build Parametric preview object properties report consumed supplemental sections.

Fail conditions:

- Supplemental sections appear on horizontal curves but not on a strong vertical curve.
- Surface geometry follows a straight profile chord through the vertical curve.
- Build Parametric uses compatibility fallback instead of consumed Applied Sections after Applied Sections was rebuilt.

## Ditch Continuity Check

Use a corridor with ditch Subassemblies on at least one side.

1. Rebuild Applied Sections with supplemental sections enabled.
2. Confirm ditch rows exist at source and supplemental stations.
3. Rebuild Build Parametric.
4. In Guided Review, double-click `Ditch`.
5. Confirm the ditch highlight follows the curve continuously.
6. Confirm Drainage Surface, if present, uses the same expanded section series.

Pass conditions:

- Ditch geometry is connected station-to-station through supplemental sections.
- Ditch highlight does not appear only at source stations.
- Drainage Surface does not show unexplained gaps caused by missing supplemental section payload.

Fail conditions:

- Supplemental stations show frames but no ditch geometry.
- Ditch surface is still built only between sparse source stations.
- Drainage Surface is denser or sparser than the ditch highlight without diagnostics.

## Side Slope Continuity Check

Use a corridor with side_slope Subassemblies and slope-face surface roles.

1. Rebuild Applied Sections with supplemental sections enabled.
2. Confirm side_slope rows exist at source and supplemental stations.
3. Rebuild Build Parametric.
4. In Guided Review, double-click `Side Slope`.
5. Review `Slope Face` or `Side Slope Diagnostics`.
6. Confirm slope-face geometry follows the curve and remains tied to the side_slope rows.

Pass conditions:

- Side slope and slope-face review geometry use the same expanded AppliedSectionSet.
- Slope-face triangles do not bridge across unrelated left/right sides.
- Slope-face diagnostics follow the side slope instead of drifting away from it.

Fail conditions:

- Slope-face geometry appears only as a Build Parametric-only interpolation artifact.
- Left and right side slope faces are incorrectly connected.
- Diagnostics show slope-face geometry that does not match side_slope geometry.

## Compatibility Fallback Check

Use only when testing an older document or a deliberately stale AppliedSectionSet.

1. Open a document with no supplemental Applied Section rows.
2. Keep a visibly curved 3D Centerline.
3. Run Build Parametric.
4. Confirm the summary or Guided Review reports compatibility fallback.
5. Rebuild Applied Sections with `Supplemental Sections` enabled.
6. Run Build Parametric again.
7. Confirm compatibility fallback disappears.

Pass conditions:

- Fallback appears only for stale AppliedSectionSet data.
- Rebuilding Applied Sections removes the fallback warning.
- Normal current workflow does not rely on hidden Build Parametric supplemental frames.

## Final Acceptance

This QA passes when:

- Applied Sections owns supplemental section creation.
- Build Parametric consumes source and supplemental Applied Sections.
- Curved surfaces respond to Applied Sections density.
- Lane, shoulder, ditch, and side slope review objects remain continuous through supplemental sections.
- Compatibility fallback is visible and disappears after rebuilding Applied Sections.
- No Report View traceback appears during the workflow.

## Recording Template

Use this record format:

```text
Document:
Date:
FreeCAD version: 1.1.1
Parametric Road build:

3D Centerline reviewed: yes/no
Supplemental off total sections:
Low density supplemental sections:
High density supplemental sections:
Build Parametric consumed supplemental sections:
Compatibility fallback observed: yes/no

Design surface follows curve: pass/fail
Ditch continuity: pass/fail/n/a
Side slope continuity: pass/fail/n/a
Drainage surface continuity: pass/fail/n/a

Notes:
```

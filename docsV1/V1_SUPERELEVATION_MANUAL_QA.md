# Parametric Road V1 Superelevation Manual QA

Date: 2026-05-31
Status: manual QA procedure; execution pending real FreeCAD document

## Purpose

This checklist verifies the first Superelevation workflow from source authoring through Applied Sections and Build Parametric output.

## Scope

This QA covers:

- Superelevation toolbar placement
- Superelevation source object creation
- automatic Alignment-based row calculation and validation
- 3D crossfall review bars
- Applied Sections effective crossfall
- Cross Section Viewer trace fields
- Build Parametric Design Surface response

This QA does not cover automatic design-speed/radius table calculation, ramp superelevation automation, or final exchange export.

## Preconditions

- FreeCAD starts without command registration errors.
- Parametric Road workbench is active.
- A test document can run the v1 workflow through Build Parametric.

Recommended source setup:

1. Project Setup.
2. TIN if terrain review is needed.
3. Alignment.
4. Stations.
5. Profile.
6. Review Plan/Profile.
7. 3D Centerline.
8. Assembly.
9. Regions.

## Manual QA Steps

1. Open `Superelevation`.
2. Confirm the panel opens after `3D Centerline` in the toolbar order.
3. Confirm opening the panel does not create or overwrite source rows automatically.
4. Confirm there is no Superelevation preset selector.
5. Click `Auto Calculate`.
6. Confirm Control Rows and Transition Rows are populated inside the current station range.
7. Confirm the status area lists detected curves, generated control rows, and generated transitions.
8. Click `Validate`.
9. Confirm validation is `ok` or an understandable warning.
10. Click `Show Samples`.
11. Confirm `Review Samples` shows station rows with left/right crossfall values.
12. Confirm a `Superelevation Crossfall Review` object appears in the 3D View.
13. Confirm the 3D preview bars follow the 3D Centerline station positions.
14. Click `Apply`.
15. Confirm a `V1SuperelevationSource` object appears under the Superelevation tree folder.
16. Generate `Applied Sections`.
17. Confirm the Applied Sections review table includes the `Superelevation` column.
18. Confirm stations inside the transition/full-super range show changed left/right crossfall values.
19. Double-click an Applied Section row in the affected range.
20. Confirm the section preview shows rolled lane/shoulder geometry.
21. Open `Cross Section Viewer`.
22. Confirm Subassembly notes or summary rows expose Superelevation source/provenance.
23. Run `Build Corridor` / `Build Parametric`.
24. Confirm Design Surface preview reflects the rolled lane/shoulder elevations.
25. Confirm generated Build Parametric objects remain under `04_Parametric Model / Build Parametric Outputs`.
26. Confirm Report View has no traceback.

## Expected Result

The QA passes when:

- Superelevation is edited as a source model.
- Applied Sections consume Superelevation and store effective crossfall context.
- Build Parametric consumes Applied Sections only; it does not ask the user to reapply Superelevation.
- Design Surface output changes when Superelevation changes and Applied Sections are rebuilt.
- Review surfaces expose enough provenance to explain the effective crossfall.

## Failure Notes

If the Design Surface does not change:

1. Re-run `Apply` in Superelevation.
2. Re-run `Applied Sections`.
3. Re-run `Build Corridor`.
4. Check that the Applied Sections review table has non-empty Superelevation rows.

If 3D review bars are missing:

1. Confirm 3D Centerline exists.
2. Confirm Stations exist.
3. Click `Show Samples` again.

## Follow-Up

Future QA should add:

- left-curve preset coverage
- out-of-range station warning coverage
- manual comparison of Cross Section Viewer dimensions before and after Superelevation changes
- regression scenario with Drainage and Structures enabled

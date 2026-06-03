# Intersections

Intersections define at-grade junction intent between two or more Alignments.

They are source-stage data. They do not directly edit generated corridor surfaces.

## Purpose

Use the Intersections panel to:

- choose the intersection type
- create starter source data for a simple junction
- detect or review participating Alignments
- link intersection control Regions
- create an Intersection source model for Applied Sections and Build Parametric

## Starter Sources

`Source Mode = Create Starter Sources` creates editable starter data for the selected intersection type.

The starter workflow creates:

- Alignment sources for the participating roads
- Profile sources linked to each Alignment
- Stationing sources linked to each Alignment
- Region sources for approach, intersection, and departure spans
- a multi-alignment `3D Centerline` preview

The generated 3D Centerline is created after the starter source rows are created.

It is routed to the `3D Centerline` tree folder and stores the participating Alignment IDs on the preview object.

If the 3D Centerline cannot be generated, the starter sources remain in the document and the status message reports the reason.

## 3D Centerline Behavior

Intersections can use more than one Alignment.

The 3D Centerline stage therefore supports a multi-alignment result:

- each evaluated point keeps its source Alignment reference
- the preview object draws separate curves for each Alignment
- Applied Sections consume only the 3D Centerline rows that match their active Alignment

This avoids using the primary road baseline for the side road.

## Region Behavior

Intersection starter sources create Region rows per participating Alignment.

Build Parametric reads all Region source models, not only the first one.

The `Region Boundaries` table includes an `Alignment` column so primary-road and side-road Regions can be reviewed separately.

Double-click a Region row to show the built object set for that Region.

## Recommended Flow

Use this sequence for the starter workflow:

1. Open `Intersections`.
2. Select the intersection type.
3. Set `Source Mode` to `Create Starter Sources`.
4. Click `Create Starter Sources`.
5. Confirm the status message includes `3D Centerline`.
6. Review the generated 3D Centerline.
7. Apply the Intersection source model.
8. Run `Build Sections`.
9. Run `Build Parametric`.
10. Review `Region Boundaries`, `Intersections`, and `Slope Face Issues`.

## Current Limits

Intersection support is a first-slice workflow.

Build Parametric can separate multi-alignment design and slope-face surface generation, but a dedicated `Intersection Surface Patch` is still future work.

Until that patch exists, the junction area should be reviewed in Build Parametric before relying on downstream solids or simulation outputs.

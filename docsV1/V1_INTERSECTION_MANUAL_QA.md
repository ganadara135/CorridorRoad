# Parametric Road V1 Intersection Manual QA

Date: 2026-10-09
Status: manual QA procedure for the parametric intersection kernel (plan phases R7c-1 to R7c-3).
The procedure for the earlier pipeline (Slope Face loops, surface zones, source row review) is in
git history before `8fbbae0`; that pipeline no longer exists.

## Purpose

Check in a real FreeCAD window what the headless gate cannot: that an intersection made in the
Intersection panel builds through Applied Sections and Build Parametric, and that its review
surfaces show the kernel's result. The specification is
[V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md](./V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md).

## Scope

- the starter T, Cross and Roundabout presets, and an intersection made from existing Alignments
- the Parametric Spec group of the Intersection panel
- the Build Parametric Intersections, Drainage, Guided Review and Visibility tabs
- the cross section viewer's intersection rows
- save, close and reopen

Out of scope: Watertight Solids (paused), hydraulics, kinds other than T, Cross and Roundabout.

## Preconditions

- FreeCAD 1.1 with the workbench loaded and no Python errors in the Report view.
- A new, empty document for each preset.

## Common acceptance rules

- The Intersection panel shows no source review table and no `Refresh Review`,
  `Accept Reviewed Rows` or `Adopt Edge Families From Subassembly` buttons.
- The spec's Kind cannot be edited; it follows the Preset, then the Intersection source.
- The `Intersections` tree folder holds an object labelled `Intersection Source`, not
  `Intersections001`.
- The tree shows one `Intersection Surface` and one `Intersection Slope Face Surface` per built
  intersection, and no legacy previews (boundary loops, tie-in edges, exclusion zones, tie slope).
- The corridor surfaces leave no triangles inside the intersection and no gap at the mouths.

## 1. Panel and spec

1. Open the Intersection panel in an empty document.
2. Switch the Preset between T, Cross and Roundabout: the Parametric Spec Kind becomes `t`,
   `cross`, `roundabout`, and the Roundabout Ring group appears only for `roundabout`.
3. Choose `T Intersection - Basic`, `Create Sources`. The spec group fills by itself: Kind `t`,
   the primary and secondary roads, the anchor stations, the corner radius of the preset.
4. Close and reopen the panel: the Preset is `T Intersection - Basic` and the spec is filled.

## 2. Build each preset

For each of `T Intersection - Basic`, `Cross Intersection - Basic` and `Roundabout - Single Lane`,
in its own document:

1. Create Sources from the preset.
2. Run Applied Sections (Build Sections).
3. In the panel, `Check Spec`: the status lists `Kernel status: ready`, the resolved values with
   their origin, and the legs; the leg table has 3 rows for a T, 4 for a Cross and a Roundabout.
4. Run Build Parametric.
5. Results tab: `intersection` and `intersection_slope` are `ready`, and their notes start with
   `Built by the intersection kernel` and report `skinny=0`.
6. Intersections tab: the first row is `intersection` / `ready`; there is one `leg` row per leg
   with its mouth station, a `boundary` row and `corridor_clip` rows.
7. Select a `leg` row: a yellow `Intersection Contract Highlight` line lies on that leg's mouth.
   Select the `boundary` row: the highlight follows the intersection boundary (and the central
   island for a Roundabout).
8. Guided Review, Intersections step: the kernel status, the leg count and the triangle counts.
9. Visibility tab: hide the corridor's design surface and show `Intersection Surface`, then
   `Intersection Slope Face Surface`: each fills the intersection only, with no overlap on the
   corridor and no gap at the mouths.

## 3. Spec edits

On the built T:

1. Set Corner Radius to 15 m, `Apply Spec`, rerun Applied Sections and Build Parametric: the
   corners widen; the Intersections tab `corner` rows read `radius 15.000 m (spec)`.
2. Untick a side road leg in the leg table (`Open`), `Check Spec`: the kernel reports the leg
   closed; on a T this blocks (`intersection_leg_count`), on a Cross it is `partial` and builds.
3. On the Roundabout: change Inscribed Radius, `Apply Spec`, rebuild: the ring follows.

## 4. Existing Alignments

1. In a document with two crossing Alignments (with Profiles and Regions), choose
   `Use Existing Alignments`, pick the primary and secondary roads, `Auto Detect`, `Apply`.
2. The spec group fills with the detected roads and anchor.
3. Run Applied Sections and Build Parametric: as in section 2.

## 5. Drainage review

1. On a built preset, open the Build Parametric Drainage tab.
2. An intersection drainage row shows the kernel's low point (`low_point_z`) and the Drainage
   Elements that cover it. The presets create a Drainage source with elements at the low point,
   so the row is `ready`.
3. Focusing the row creates a `Suggested Inlet - <intersection id>` marker at the low point.
4. In a document whose Drainage source has no element at the low point (for example one made from
   existing Alignments without drainage), the row is `missing`.

## 6. Cross section viewer

1. Open the cross section viewer and go to a station inside the intersection's clip span.
2. The intersection rows include `kernel` (`ready`), `active_leg` with the leg role,
   `corridor_clip` `inside`, and the `drainage_candidate` of this road if it has one.
3. At a station outside the span, `corridor_clip` reads `outside`.

## 7. Save and reopen

1. Save, close and reopen a built preset document.
2. `Load Spec` shows the stored spec, including any edit from section 3.
3. Rebuild Build Parametric: the same `Intersection Surface` as before saving.
4. A Roundabout document created before 2026-10-09 (plan phase R7c-3) rebuilds the same ring.

## Failure notes

If an intersection does not build:

1. Run `Check Spec` and read the kernel diagnostics: each names what failed, where (road,
   station), what to inspect and the effect (blocked, partial).
2. `pavement_edge_owner_missing`: Applied Sections have no section near the leg; rerun them.
3. `leg_too_short_for_corner` or `corner_fillet_no_solution`: the corner radius does not fit the
   leg; lower it in the spec.
4. `roundabout_flares_overlap` or `roundabout_approach_wider_than_ring`: the ring is too small for
   the approaches; raise the inscribed radius or set the entry and exit radii.

If corridor triangles remain inside the intersection, rerun Applied Sections, then Build
Parametric: the mouth sections must exist before the corridor is clipped.

## Result record

| Date | Section | Preset or document | Result | Notes |
| --- | --- | --- | --- | --- |
| 2026-10-08 | 2 | T, Cross, Roundabout | pass | user, after R7c-1 |
| 2026-10-09 | 2 (steps 6, 7) | presets | pass | user, after R7c-2 |
| 2026-10-09 | 2 (step 6) | presets | pass | user, after R7c-3: Intersections tab `ready` |
| 2026-10-10 | Common rules | preset (Create Sources) | pass | user, at `567bad1`: the `Intersections` folder holds `Intersection Source` |
| 2026-10-10 | 6 | Roundabout | **fail** | user, at `567bad1`, a station inside the clip span: no intersection rows in the cross section viewer; Intersection Context reads `No active intersection context rows`. Cause: the viewer listed rows only for sections with a source control area (`active_intersection_id`); with the panel's roundabout defaults (36 m, control length 30 m) the kernel clip span (STA 74.5-185.5) is far longer than the control area (STA 111.25-148.75). Fixed: a section inside the kernel clip span gets the kernel rows, with `source_status` role `kernel_clip_span` |
| 2026-10-10 | 6 | Roundabout | pass | user, after the kernel clip span fix: intersection rows shown inside the clip span |
| 2026-10-10 | 6 | presets | pass | user, after `cf80c0d`: Station Navigation lists the primary road first, then the secondary road |
| 2026-10-10 | 2 (step 5) | presets | pass | user, after `7997082`: Results tab `intersection` and `intersection_slope` Output Path `contract_consumed` |
| 2026-10-10 | Breakline Audit | presets | pass | user, after `7997082`: one row per surface and no errors after a rebuild |

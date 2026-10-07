# Parametric Road V1 Intersection Scope and Improvement Plan

Date: 2026-09-26
Branch: `ganada_0902`
Status: Active plan. Section 3 is done; sections 5 to 11 are proposed and unscheduled.
Depends on:

- `docsV1/V1_INTERSECTION_MODEL.md`
- `docsV1/V1_INTERSECTION_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_INTERSECTION_PRESET_DATA_PLAN.md`
- `docsV1/V1_INTERSECTION_REMAINING_WORK_PLAN.md`
- `docsV1/V1_ROUTE_SEPARATION_AND_REGION_CRITERIA.md`
- `docsV1/V1_ARCHITECTURE_DEBT_EXECUTION_PLAN.md`

## 1. Purpose

Two things belong in one document, because the second follows from the first:

- the intersection scope is now three kinds, and four starter kinds were removed
- what the three remaining kinds need before the flow is even across them

It exists because the flow measured end to end is not uniform. Only the T path
has a completed Slope Face Surface; Cross carries an unresolved rule conflict,
and Roundabout approximates its ownership area with a circle.

## 2. Scope Decision

The supported intersection kinds are:

| Panel preset | Kind | Legs | Starter alignments |
| --- | --- | --- | --- |
| T Intersection - Basic | `t_intersection` | 3 | 2 |
| Cross Intersection - Basic | `cross_intersection` | 4 | 2 |
| Roundabout - Single Lane | `roundabout` | 4 | 2 |

Nothing else. `SUPPORTED_INTERSECTION_KINDS` in
`v1/commands/cmd_intersection_editor.py` is the single list, and
`starter_intersection_source_specs` refuses anything outside it by name.

## 3. What Was Removed, on 2026-09-26

Four starter kinds were defined in the source builder but never offered by the
Intersection panel: `skewed_intersection`, `urban_curb_gutter_intersection`,
`drainage_sag_intersection` and `y_intersection`. `Y` was the only one that used
three alignments; the other three were a Cross starter with different corner
labels and a different default curb-return radius.

Removed with them:

- their branches in `starter_intersection_source_specs`
- their entries in the corner label table, the curb-return radius defaults, the
  curb-return quadrant sign table, and the arc radius default
- the Y branch in `_leg_connection_kind`, which returned `diverge`/`merge`
  instead of `turn`
- the Y branch in `_default_radius` and the Y quadrant entry in
  `intersection_boundary_segment_evaluation_service`
- the Y corner-label branch in `intersection_evaluation_service`
- the `using_source_endpoint_hull` flag, which could only be true for Y and
  Skewed. Its four dependent branches now take the path they took for every
  other kind, so a traced loop is still `ready` and an untraced one still warns
  with `intersection_boundary_convex_hull_fallback`.

Tests: the Y case left the arc-count parametrisation; the skew boundary-loop test
was retargeted to `cross_intersection` and renamed to
`..._for_non_orthogonal_edges`, because what it guards is envelope tracing over
non-orthogonal edges rather than a retired preset; a persistence round-trip test
that used the Sag kind as a data string now uses Cross.

`intersection_kind` stays a free-form persisted string, so a document written
against a removed kind still opens. Its rows fall through to the default corner
and radius behaviour, which is the T-shaped default. Making that visible is
improvement 5.1.

Not removed: `V1_INTERSECTION_SKEWED_EXCLUSION_UNION_PLAN.md` stays active. Its
subject is exclusion-footprint robustness for non-orthogonal tie-in geometry,
which a Cross intersection on two roads that do not meet at 90 degrees still
needs. It is about geometry, not about the retired preset.

Validation: 9 architecture tests, contract suite at 1,336 passed, 18 skipped and
its one known failure, 78 in the intersection command module, all three smoke
runners, and each of the three presets creating 18 source rows with an
`IntersectionModel`.

## 4. How the Flow Works Today

```text
Create from preset
  per participating road:  Alignment -> Profile -> Stationing -> Region (intersection-tagged)
  detect XY crossing, resolve a station on each axis
  IntersectionModel: anchor, legs, control areas, corners, arm/edge/curb-return/drainage policies
  Superelevation and Drainage starter sources
  multi-alignment 3D Centerline preview
        |
Applied Sections
  one bundle per Alignment, paired by alignment_id
  intersection supplemental stations merged in and tagged as results
        |
Build Parametric
  prerequisite gate: IntersectionModel + Applied Sections + intersection Region rows
  topology -> edge network -> surface zones -> slope face loops -> boundary loops -> corridor clipping
  T and Cross: boundary loop polygon, constrained triangulation, patch TIN
  Roundabout: ownership circle from source policy, approach legs
  corridor surfaces clipped where the intersection owns the area
  slope faces fill patch boundary to daylight, shared breaklines hold continuity
```

Everything the preset writes starts at `approval_status="draft"` with a
`source_completeness_ref`, so the values a real design must replace are marked in
the data rather than in a comment.

## 5. Improvements

Every item below was checked against the code after the first draft was written,
and four of the nine did not survive that check. What follows is the corrected
set. Items marked **already implemented** are kept, with what was found, so the
same proposal is not made again.

### 5.1 Diagnose an unsupported intersection kind: already implemented

The first draft said `evaluate_topology` carries `intersection_kind` through
without validating it. It does validate it. `IntersectionRow.is_supported_kind`
tests membership of `INTERSECTION_KIND_PRESETS` in the source model, and topology
appends `warning:intersection_kind_not_first_slice_supported:<kind>` when it
fails, or `error:intersection_kind_missing` when the kind is empty. Measured with
a row holding `banana_intersection`: the warning appears and the kind is carried
through unchanged.

`INTERSECTION_KIND_PRESETS` already held exactly `t_intersection`,
`cross_intersection` and `roundabout`, which means the four retired starters were
never in it and always produced that warning. The scope reduction of section 3
brought the starter builder into line with a list the model layer had already
settled.

One thing did come out of this check: the `SUPPORTED_INTERSECTION_KINDS` tuple
added by that scope change restated the three kinds instead of reading them, so
it was a second source of truth. It now derives with
`tuple(INTERSECTION_KIND_PRESETS)`.

### 5.2 The Cross boundary loop failure: closed on 2026-09-27, no decision needed

This was recorded as the one product decision in the plan, between keeping the
authoritative source edge rule and accepting a complete envelope loop. Both readings
were wrong. The rule was right and the test did not supply its inputs.

The test called `evaluate_boundary_loops(model)` with the model alone, so the edge
network was derived internally, and an `IntersectionModel` carries no alignment
geometry. The four curb return edges came out zero-length at the origin with
`source_status` `error`, all four were excluded, and
`intersection_boundary_authoritative_source_edges_missing` fired exactly as intended.
Every other boundary loop test in that file supplies `edge_network_result` explicitly.

Supplying four well-formed pavement edges, with the rule untouched, makes all nine of
the test's assertions pass: `warning`, `ready_count` 1, a ready closed loop of 32
points and area 312.1 from `candidate_source=curb_return_envelope`. The loop is
identical either way, because the envelope is built from the curb return policy radius
and never from the edges.

The contract baseline is 0. The record is in section 10 of
`V1_ARCHITECTURE_DEBT_EXECUTION_PLAN.md`.

### 5.3 Give the panel the review controls the flow requires: done on 2026-09-27

The first draft framed this as Slope Face Surface completeness for Cross and
Roundabout, on the strength of the non-T smoke's own docstring, which says it does
not claim non-T dedicated Slope Face Surface completion and only guards against
build errors and misleading `ready` states. That docstring is still the evidence,
and a probe that tried to reproduce the T smoke's preview creation did not produce
an intersection surface preview for any of the three presets, so **the per-kind
completeness claim is not independently verified here** and should be measured
before it is acted on.

What the same check did establish is more actionable. The T smoke reaches its
surface only after `_accept_t_intersection_preset_prerequisites`, which does by
hand what a review step would do: it sets every leg to `approval_status="accepted"`
with `span_source="explicit"`, fills each leg's `profile_ref` and
`centerline3d_ref`, accepts the anchor rows with a tolerance, and accepts the
control areas with station and influence ranges.

Measured on a T preset with the panel's control length spin set to 24 m: the leg's
`approach_station_start/end` are filled, at 108 and 132, but `profile_ref` and
`centerline3d_ref` are empty strings and `approval_status` is `draft`. Topology,
edge network and surface zones all rest at `warning`, before and after filling the
refs and accepting the rows.

The Intersection panel offers a source mode combo, a preset combo, a design
vehicle combo, a radius spin, a control length spin, a grading combo, a drainage
combo, two alignment combos, and the buttons Create Sources, Refresh Alignments,
Auto Detect, Apply, Close, Hide and Show Preset Sources. There is no leg table, no
anchor editor and no control-area editor, so there is no control that sets a leg's
`profile_ref`, its `centerline3d_ref` or any row's `approval_status`.

The first half is done. `services/editing/intersection_review_service.py` reports
every leg, anchor and control area with what it still needs, and accepts the rows
that are complete. It refuses to fill a ref it was not given: inventing one would
make the source look reviewed while leaving the same gap, so an incomplete row keeps
its draft status and carries `warning|leg_review_incomplete:<leg_id>:<fields>`.

`resolve_intersection_review_leg_refs` in `cmd_intersection_editor` supplies the refs
the document actually holds: the Profile whose `alignment_id` is the leg's
`alignment_ref`, and the 3D Centerline object covering that alignment, which on a
preset is the shared `centerline3d:multiple`. Note that the T smoke fabricates
`profile:{alignment_ref}`, which matches no object, so nothing downstream was ever
validating those refs.

The Intersection panel gained a source review table over the five preset rows, a
summary line, a Refresh Review button and an Accept Reviewed Rows button. Measured on
a T preset: 0 of 5 reviewed with three rows missing fields, then 5 of 5 after Accept,
with `profile:V1Profile` and `profile:V1Profile001` resolved per road.

The remaining half is measured. The same sequence the T slope-face smoke runs was run
for all three kinds, using the review service above instead of the smoke's private
accept helper, so what was measured is what a user can now do in the document:
preset, review, Applied Sections, corridor model, surface model, then the
intersection, design and daylight surface previews, which is what creates
`V1CorridorIntersectionSlopeFaceSurfacePreview` as a side effect.

| | T | Cross | Roundabout |
| --- | --- | --- | --- |
| rows reviewed | 5 of 5 | 7 of 7 | 5 of 5 |
| patch prerequisite | ready | ready | ready |
| applied sections | 32 | 38 | 42 |
| slope face preview | present | present | **missing** |
| tie slope preview | present | present | missing |
| `intersection_slope` review row | ready | ready | missing |
| `TriangleCount` | 4 | 4 | n/a |
| `IntersectionBoundaryOwnerStatus` | missing | missing | n/a |
| `IntersectionSlopeFaceOwnerFillReadinessStatus` | warning | warning | n/a |

Two answers, and one of them contradicts what this item was written on.

**Cross is not behind T.** Every marker is identical for the two kinds. The claim that
only T has a completed Slope Face Surface came from the non-T readiness smoke's
docstring, and for the preset path this measurement does not support it. What is true
is that neither kind reaches the state the T smoke asserts, so the smoke is not
measuring the preset path.

**Roundabout genuinely differs.** No slope face preview object is created at all, no tie
slope preview, and the `intersection_slope` review row is `missing` rather than `ready`.
That is a real gap and it belongs with item 5.4.

Why neither T nor Cross reaches `IntersectionBoundaryOwnerStatus` `ready`: the review
surface covers three of the eight reviewable row families. The T smoke's helper also
accepts `corner_rows`, `edge_policy_rows`, `lane_connection_rows`, `grading_policy_rows`
and `drainage_policy_rows`, and with it the same document reports owner `ready` with 15
owners and fill readiness `ready`. A field-by-field diff of the two accepted models
showed no difference in the three families the service covers, apart from the refs and
the provenance markers, and matching those did not reproduce `ready`; the five families
the service does not touch are what does. Each of them carries a `*_source_defaulted`
marker, and the edge-authority filter excludes any edge whose diagnostics contain
`defaulted`. That is item 5.10.

One change came out of the measurement. Acceptance now resolves the markers that say
nobody reviewed a row, `approval_pending` and `review_required`, and keeps the ones that
record where it came from, `leg_source_region_derived` and
`control_area_region_derived`. The smoke clears `diagnostic_rows` outright, which drops
provenance with them. This changed no measured outcome and makes an accepted row honest.

### 5.4 Give each roundabout approach its own geometry

An earlier revision of this section asked for a boundary loop that already
exists, and the correction matters because it changes what the work is.

`clip_tin_surface_by_roundabout_ownership` sets `clip_mode` to
`roundabout_boundary_loop` and clips against the polygons of the
`roundabout_outer_ownership_boundary` loop rows whenever they are ready and
closed. `circle_intersection` is the fallback it takes when they are not, and it
says so: the surface carries a `roundabout_ownership_clip_mode` quality row and a
`roundabout_clip_boundary_unavailable` reason. The 1.1.0 fix was not a missing
boundary but a silently taken fallback, where the loops were resolved and then
passed where a document was expected.

The circle keeps three jobs, and they are the right ones: the precondition that
`ownership_radius > 0`, the fallback clip, and the ownership-intrusion guardrail.
The radius also belongs in the source. A roundabout is circular, so radius-based
intent is correct and should not become a hand-drawn polyline; what the result
needs is a discretised loop, which it already builds.

The real limit is upstream of the clip. The source carries four single scalars,
`roundabout_central_island_radius`, `roundabout_circulatory_outer_radius`,
`roundabout_outer_apron_width` and `roundabout_slope_face_width`, plus a
connector length derived as `max(outer_radius * 1.25, 12.0)`. Every approach
therefore shares one apron width and one outer radius, and no approach has an
entry or exit radius of its own, so a roundabout with a wider entry on the major
road cannot be expressed at all.

Acceptance: per-approach policy rows keyed by leg for entry radius, exit radius
and apron width, consumed by `evaluate_roundabout_approach_legs` so the outer
ownership loop reflects them, with the single-valued rows kept as the default
where no per-approach row exists.

#### Outcome, first part: apron width per approach, done on 2026-10-07

Apron width is done here. Entry radius and exit radius are done in the next part.

- **Source.** No new row family. A per-approach apron is an `IntersectionEdgePolicyRow` of the
  `roundabout` intent with the rule `roundabout_approach_apron_width`, keyed by `leg_ref` and by
  `side`: `start`, `end`, or `both`. An endpoint row beats a `both` row, which beats the
  intersection default `roundabout_outer_apron_width`. Nothing in the stored schema changes, so
  an older document loads as before. A value of 0 or less is ignored with a
  `roundabout_approach_apron_width_invalid` warning and the approach falls back to the default.
- **Result.** `IntersectionRoundaboutApproachLegRow` gained `apron_width` and
  `apron_width_source` (`approach_policy` or `roundabout_default`), resolved in
  `_roundabout_approach_leg_rows`.
- **Geometry.** The `roundabout_outer_ownership_boundary` loop is the circulatory outer radius plus
  the apron width interpolated linearly, round the circle, between the approach directions. It is
  built from the same 32 angles as the circulatory outer loop, which the apron builder relies on
  to pair the two point by point. When every approach has the same width the loop is the circle
  it was, point for point, and a test pins that.
- **Guardrail.** The ownership-intrusion circle (`_roundabout_ownership_boundary_spec`) now uses the
  narrowest resolved apron, so it flags only intrusions into area the roundabout owns in every direction.
- **Tests.** `test_roundabout_approach_apron.py`: the default case, a leg row that widens its two
  approaches with a smooth loop, endpoint beats both and the invalid fallback, and the persisted round trip.

Not done, and stated so it is not mistaken for done:

- **Authoring.** There is no editor field for the new rows. They exist as source rows, as the
  existing roundabout policy rows do.
- **GUI.** Everything above was checked headless, against the evaluation results. Nothing was looked
  at in FreeCAD, and the apron TIN was not rebuilt with a widened loop; only its loop pairing was checked.

#### Outcome, second part: entry and exit radius, done on 2026-10-07

The connector now has a flare. The two open decisions were answered by the user on 2026-10-07:
**right-hand traffic circulating counter-clockwise, fixed in code**, and a flare tangent to the
connector's edge line. Nothing in the project records a circulation direction (a search for drive
side, traffic direction, circulation and handedness finds nothing), so the fixed assumption is stated
here and in the code, and a project setting would be a separate item.

- **Source.** Edge policy rows of the `roundabout` intent with the rules
  `roundabout_approach_entry_radius` and `roundabout_approach_exit_radius`, keyed by `leg_ref` and
  `side` (`start`, `end`, `both`) exactly like the per-approach apron. There is no default but 0,
  which means no flare, so every existing document and the preset are unchanged. A value of 0 or
  less warns (`roundabout_approach_entry_radius_invalid`, `..._exit_radius_invalid`) and means no flare.
- **Result.** `IntersectionRoundaboutApproachLegRow` gained `entry_radius`, `exit_radius` and their sources.
- **Geometry.** A flare of radius R is the arc tangent to the connector edge line and externally
  tangent to the circulatory outer circle: its centre is at lateral distance half-width + R, at
  distance outer radius + R from the roundabout centre, so its centre's distance along the approach
  is `sqrt((r0 + R)^2 - (h + R)^2)`. The connector polygon replaces the ring end of that side with
  the arc, 9 points from the ring tangent to the edge tangent. Entry is the side the outward direction
  turned a quarter turn counter-clockwise points to; exit is the other. A flare whose edge tangent lies
  beyond the end of the connector, or that has no real centre, is refused with
  `roundabout_connector_flare_unavailable` and the side keeps its rectangle corner.
- **Surface.** `build_roundabout_entry_exit_connector_surface_tin` kept its two-triangle rectangle for a
  four-point loop and ear-clips a flared one, because the outline is concave at the flare. The triangles
  are given the winding the rectangle's two already have, so one surface does not mix windings.
- **Tests.** `test_roundabout_connector_flare.py`: no radius gives the four-point rectangle, the entry
  flare is on the entry side only and tangent to both curves, an exit flare is on the other side and
  an oversized flare falls back, and the flared triangles add up to the loop's polygon area.

Things to know before relying on it:

- **The connector surface preview is not in the build.** `create_corridor_intersection_surface_preview`
  reports the roundabout entry/exit connector surface `not_applicable` ("disabled for generalization").
  A flare changes the boundary loop, and the shared breaklines and graph edges derived from it, but not
  a surface you can see in the built document today.
- **Nothing was looked at in FreeCAD.** The checks are headless, on the evaluation and the builder.
- **Neighbouring flares can meet.** Two flares on adjacent approaches are not checked against each
  other; with a small ring and large radii they could overlap.
- **Authoring.** There is still no editor field for any per-approach row.

### 5.5 Let the side road have superelevation: done on 2026-09-28

The first draft said a main road and a side road cannot have different standard
sections because the Assembly is resolved first-found. That is wrong for the
Assembly. `AppliedSectionSetService._resolve_assembly_model` and
`_resolve_subassembly_model` match a Region row's `assembly_ref` against every
assembly model in the document, and the command passes all of them, so a Region
row already selects its own Assembly per road. The first-found lookup is only the
fallback identity when no model matches.

Structure and Drainage are also fine: their rows carry `alignment_id` and
`alignment_ref`, so one model object serves several roads.

Superelevation is the real limit. `SuperelevationModel.alignment_id` is one value
for the whole model, `SuperelevationService` raises `missing_alignment_id` when it
is empty, `find_v1_superelevation_source` returns the first model in the document,
and the preset writes that model with `alignment_id = primary_alignment_ref`. The
same model is then handed to every bundle in the per-alignment loop, so the side
road's sections consume a superelevation model that belongs to the main road, and
nothing diagnoses the mismatch.

Done. Superelevation is paired by `alignment_id` the way Profile and Region already
are, through `_superelevation_for_alignment`, and each bundle carries its own model.
A model belonging to another Alignment is no longer read at this road's stations, so
the mismatch the acceptance asked to diagnose is now impossible to produce.

The measurement turned up a second defect the item had not named. The Intersection
preset wrote `V1IntersectionPresetSuperelevation` while the Superelevation editor
writes `V1SuperelevationSource`, and `find_v1_superelevation_source` returned the
first in document order, so on a preset document an edit landed in a source nothing
read. Two sources can still claim one Alignment, and the rule is now explicit: one
carrying crossfall control rows wins over one without, because the preset's handoff
placeholder has none and must not shadow something a user authored. When both carry
rows document order stands and `superelevation_source_rows` reports the one that is
not read, which the Applied Sections panel lists under `Superelevation sources:`.

The preset now writes one handoff source per participating road, so a T gives
`V1IntersectionPresetSuperelevationPrimary` and `...Secondary`, each naming its own
Alignment. Measured on a T preset with a curve authored for the side road: the side
road reaches -7 and +7 percent at its station 60 and the main road stays at the
template crossfall.

One attempt inside this item was wrong and is recorded because the mistake is easy to
repeat. A road with no source used to record 0.0 in `superelevation_left_crossfall`,
which reads as a flat section, so the service was changed to return the template
default instead. That result is not merely recorded: the caller feeds it into the
subassembly template and it becomes geometry, and a 2 percent lane moved to 3 percent,
which `test_section_preview_consistency` caught. The service returns `None` again.
An absent source is visible through an empty `active_superelevation_id` and through
the source report, not by inventing a crossfall.

### 5.6 Warn when a road drops out of Applied Sections: done on 2026-09-26

`_applied_section_source_bundles` skips an Alignment that lacks a Profile, a
Region model or a Stationing, with `continue` and no diagnostic. Deleting the side
road's Region silently removes its sections, and the intersection then evaluates
against a half-built document.

Done. `_applied_section_alignment_bundles` now resolves one bundle per Alignment,
complete or not, and records which of Profile, Regions and Stations each one lacks.
`_applied_section_source_bundles` filters that to the complete bundles, so the build
and the report read one resolution and cannot drift apart.

`incomplete_alignment_bundle_rows(document)` reports the rest, and the Applied
Sections panel shows them under `Skipped Alignments:` with the label, the alignment
id and what is missing. It is deliberately not part of the blocking validation: a
stray incomplete Alignment should not stop a complete road from building.

On the Build Parametric side,
`intersection_leg_section_coverage_rows(intersection_model, applied_section_set)` in
`ui/presentation` adds one review row per participating leg whose Alignment has no
sections, carrying
`warning:leg_alignment_has_no_applied_sections:<alignment_ref>`. An empty section set
reports nothing, because Applied Sections not having run is a different message.

`tests/contracts/v1/test_intersection_leg_section_coverage.py` locks both ends,
including a T preset whose secondary Region is deleted and which then reports that
one Alignment as missing `Regions` while the main road still builds.

### 5.7 Cache the intersection evaluation chain: closed without a cache, on 2026-10-05

The first draft said the chain runs seven times per build. Seven is the number of
call sites in `cmd_build_corridor`, not the number of runtime calls, and the two
functions that build the corridor and surface models call the chain zero times.

Measured on a T preset, over `build_document_corridor_model`,
`build_document_corridor_surface_model`, `corridor_build_review_rows`,
`corridor_intersection_contract_review_rows`, `corridor_shared_breakline_audit_rows`
and the three surface preview builders: `evaluate_topology` 4,
`evaluate_edge_network` 2, `evaluate_surface_zones` 2, `evaluate_boundary_loops` 2,
`evaluate_slope_face_loops` 2, `evaluate_corridor_clipping` 1, thirteen calls in
all. The repetition is in the review-row and preview helpers, each of which
resolves the chain from the document on its own. Incremental rebuild keys its
stages on `corridor_model` and `surface_model`, so none of this is cached.

Acceptance: one chain evaluation per unchanged IntersectionModel across a review
and preview pass, proved by a call counter in a focused test, with the same result
rows as today.

#### Outcome: the chain is not where the time goes

The count was right and the premise was not. Timing each method over a full pass
(`build_document_applied_section_set` through the three surface previews, then
`corridor_build_review_rows`, `corridor_intersection_contract_review_rows` and
`corridor_shared_breakline_audit_rows`):

| kind | whole build + previews | the six chain methods together | the review passes |
| --- | --- | --- | --- |
| T | 5.9 s | 0.32 s (`evaluate_slope_face_loops` 0.24 s) | 0.08 s |
| Cross | 9.0 s | 0.77 s (`evaluate_slope_face_loops` 0.65 s) | 0.15 s |

`evaluate_topology`, `evaluate_edge_network` and `evaluate_surface_zones` together cost
1 to 2 ms per call chain, about what a deep copy of their results costs, and the counts
including nested calls are higher than the 13 above (47, 26 and 23). A cache over them
would save nothing measurable, and the two methods that do take time also depend on the
Applied Section Set, so a correct key would have to cover that too. Their results are
mutable dataclasses shared by many callers, so a cache would also introduce the second
source of truth that `AGENTS.md` warns about. No cache was built.

What does take the time, from a profile of the same T pass:

- `SharedBreaklineAuditService.audit`: 5 calls, about 1.2 s each. Nearly all of it is
  `_boundary_edge_matches` and `_boundary_chain_matches`, which test every boundary point
  against every segment (300,160 `_project_to_segment` calls on a T).
- `intersection_patch_constraint_build_service.constraint_rows`: 5 calls, about 0.7 s each,
  through `_existing_edges_cover_segment` and `_boundary_coverage_matches`, the same
  point-to-polyline pattern (144,252 projections).
- the TIN clip against the Intersection exclusion: about 1 s per call.

So the real item is the point-to-polyline matching in those two services, which is
quadratic in boundary points times segments and runs five times over unchanged inputs.

#### Follow-up: the matching, done on 2026-10-07

Done as its own change, with the constraint that no answer may change. Before touching
anything, every `SharedBreaklineAuditService.audit` result and every
`constraint_rows` output of a full T, Cross and Roundabout build was recorded; after it,
all of them were identical. That comparison was a one-off check on those three builds;
no permanent test holds the matchers to the earlier algorithm, so a later change to them
should repeat it.

What changed, in the order it mattered:

- the audit rebuilt each consumer surface's vertex lookup, edge list and parsed constraint
  rows for every breakline x consumer pair, 245 times on a T. They are built once per audit;
- `_boundary_edge_matches` evaluated `_boundary_min_distance`, a scan of every vertex
  against every segment, as the default argument of a `dict.get`, so it ran whenever a
  breakline was not matched. It is now evaluated only when the coverage pass gave no distance;
- a vertex's projection onto a breakline, and whether it is near it, were recomputed for
  each of the six or so edges sharing it. They are computed once per vertex;
- a vertex outside the breakline's bounding box widened by the tolerance and a margin well
  above floating-point error is certainly not near it, so the exact distance is skipped. The
  constraint build applies the same box to the edges it tests a segment against, which is
  exact because it reads only `matched`, and the audit's coverage pass does not skip
  vertices because it also reports the minimum distance;
- the constraint build recomputed the edge rows of every triangle for each segment. They are
  rebuilt only when a support triangle is appended;
- the point-to-segment projection built a tuple, a generator and a dict per call. It is
  written per axis with the same arithmetic order, so results are bit-identical to the
earlier form.

Measured on the same machine, which varies by about 30% run to run, so read the ratios:

| kind | whole build + previews | audit | constraint build |
| --- | --- | --- | --- |
| T | 7.0 s to 4.5 s | 2.8 s to 0.3 s | 1.6 s to 0.5 s |
| Cross | 10.5 s to 6.7 s | 4.3 s to 0.6 s | 2.1 s to 0.6 s |
| Roundabout | 17.0 s to 6.4 s | 10.0 s to 1.2 s | 3.3 s to 0.9 s |

What remains of a build is mostly the TIN clip against the Intersection exclusion (about
1 s a call) and the breakline TIN builder, neither of which was touched.

### 5.8 Make the starter geometry usable on a real route: done on 2026-10-06

The starter alignments are hardcoded straight lines: the T is a 240 m main road
and a 100 m side road, with no curve, no superelevation and a generated flat
profile. Any real job goes through `Use Existing Alignments`, and that mode is
thinner than the first draft said.

`create_intersection_from_existing_alignments` creates the IntersectionModel and
nothing else: no Region, no Superelevation source, no Drainage source, where the
preset path creates all three. `build_existing_alignment_intersection_model`
raises `No intersection-tagged control Regions were found.` unless the user has
already authored those Region rows by hand, which the Region panel does not do for
intersections.

Acceptance: `Use Existing Alignments` creates the same source set the preset does,
minus the alignments and profiles it is given, including the intersection-tagged
Region rows it currently demands as a precondition.

#### Outcome

`create_intersection_from_existing_alignments` now writes the IntersectionModel and
then the rest of the preset's source set around the two roads the user selected.

**Control Regions are overlay rows.** A real route already has a Region model the user
wrote, so editing or splitting its rows would change authored source. The decision, taken
with the user, was to add a row and leave the others alone. `build_control_region_overlay`
(`services/editing/intersection_control_region_service.py`, no document access) builds a
row centred on the detected crossing station, one control length wide and clipped to the
span the Regions cover, with `intersection_ref` set and a priority of at least 80 and above
every existing row. `RegionResolutionService` therefore makes it the active row there, and
every other station resolves exactly as before. The overlay copies the Assembly, Template,
Superelevation and policy-set refs of the row that was active at the crossing, so the
section a station resolves to does not change.

What it refuses, with a message that names the cause, because an invented row would claim
an Assembly nobody chose: a road with no Region model, a crossing station outside the
Regions, a control length of zero, two roads that neither cross nor come within one
control length of each other, and detection that could not place the roads at all. Both
roads' rows are built before either is written, so a refusal changes nothing.

Existing intersection-tagged Regions are kept and nothing is added, so applying twice, or
applying after hand-authored control Regions, is a no-op for Region source.

**Superelevation and Drainage.** One Superelevation handoff source per road, as the
preset writes, except that a road which already has a Superelevation source of its own
keeps it and gets none. The Drainage handoff source is written as for the preset.

The apply dialog lists what was created. `Control Length` from the panel sets the overlay
width, falling back to 24 m, the panel default.

**Not covered.** The overlay is placed from the detected crossing, so the roads must
actually have been detected against each other; the starter preset's Profile, Stations
and Assembly are still the user's to supply on a real route, because this mode takes
Alignments the user already has.

### 5.9 Expose the control values the preset guesses: done on 2026-09-28

Done. `intersection_preset_default_rows` reports the five values the preset decided,
each with what it became in the document, the row family carrying it, and that family's
review state. The Intersection panel lists them under `Preset defaults in the document:`,
so the panel now shows both halves: the combos say what will be sent, and this says what
landed and what still needs review.

Measured on a T preset with every option set by hand:

| value | landed as | carrier | review state |
| --- | --- | --- | --- |
| Design vehicle | `single_unit_truck` | `arm_policy_rows` | none |
| Curb return radius | `11.000 m` | `curb_return_policy_rows` | none |
| Control length | `30.000 m, 15.000 m` | `control_area_rows` | review required, then `reviewed` after Accept |
| Grading policy | `preserve_primary_crown` | `grading_policy_rows` | review required |
| Drainage mode | `curb_gutter_inlets` | `drainage_policy_rows` | review required |

The checklist also makes the shape of item 5.10 visible from the panel: after
`Accept Reviewed Rows`, control length reads `reviewed` while grading and drainage still
read `review required`, because those two are among the five families the review does not
yet cover.

Two of the five cannot be reviewed at all, which the item had not anticipated and which
is now item 5.11.

### 5.10 Extend the review to the five remaining row families: done on 2026-10-05

The review surface covers legs, anchors, control areas and, since item 5.11, the curb
return and arm policies. Five families are left:
`corner_rows`, `edge_policy_rows`, `lane_connection_rows`, `grading_policy_rows` and
`drainage_policy_rows`. Measured on a T preset: 2, 4, 2, 1 and 1 rows, every one `draft`
with `source_method` `preset_default` or `subassembly_default`, and every one carrying a
`*_source_defaulted` or `*_hint_only` marker beside its `approval_pending` and
`review_required` markers.

#### What is actually required

Measured rather than reasoned, by varying one thing at a time on a T preset and reading
`IntersectionBoundaryOwnerStatus` off the slope face preview:

| five families accepted with diagnostics cleared | `edge_policy` `source_method` rewritten | `drainage_policy` `intent_status` rewritten | owner |
| --- | --- | --- | --- |
| yes | yes | yes | ready, 15 owners |
| yes | yes | no | ready, 15 owners |
| yes | no | no | missing |
| no | yes | yes | missing |

Both of the first two columns are necessary and neither alone is sufficient. The third is
irrelevant to the outcome.

Two earlier guesses were wrong and are recorded so they are not repeated. Accepting the
five families without touching their diagnostics does nothing. Rewriting each
`*_defaulted` marker to an adopted form such as `*_default_accepted`, which was the
proposal in the first draft of this item, also does nothing: the markers have to be
cleared. The edge-authority filter is not the rule that governs this, since none of its
exclusion tokens match `default_accepted`, so something else reads these rows and was not
located. Whoever implements this should find that rule first.

#### Decisions

These were delegated and are taken here.

**`edge_policy_rows.source_method`, `subassembly_default` to `subassembly_derived`:
allowed, but as its own action.** It is required, and it is a claim about where the edge
family comes from. The preset does create a starter Assembly and Subassembly, so the claim
can be true, but only once a user has looked at that Assembly and decided it is the one
they want. It must therefore not ride along inside `Accept Reviewed Rows`. Give it a
separate, separately-labelled action, so the claim belongs to the user and is visible in
the review.

**`drainage_policy_rows.intent_status`, `hint_only` to `accepted_drainage`: not touched.**
It is measured irrelevant to the surface, and promoting a drainage hint to drainage intent
inside an intersection review would have the intersection absorb Drainage's meaning, which
`V1_REGION_MODEL.md` and the domain ownership rule both forbid. Drainage owns that, from
its own editor, through `region_ref`.

**Diagnostics on the five families: cleared, with provenance kept where it belongs.** The
marker transition does not work, so clearing is the only measured option. Clearing loses
nothing that matters, because `source_method` already records where each row came from:
`preset_default` for the four non-edge families. A diagnostic list is for conditions that
are still unresolved; provenance belongs in the structured field that already holds it.
The three families the review covers today keep their `*_region_derived` markers, which
have no `source_method` equivalent.

Acceptance: the five families reviewable in the panel, with the edge-family adoption as its
own action; `IntersectionBoundaryOwnerStatus` reaching `ready` for T and Cross from preset
plus review alone; and the rule that reads these rows identified in the commit message, so
the next person does not have to find it again.

#### Outcome

**The rule was located.** The edge-authority filter *is* the reader, and the earlier note
that none of its tokens match was wrong. The chain is:

1. The preset writes `source_method="subassembly_default"` on its edge policy rows.
2. `_VALID_EDGE_POLICY_SOURCE_METHODS` in `intersection_evaluation_service.py` lists
   `manual`, `detected`, `preset_default`, `subassembly`, `subassembly_bridge`,
   `subassembly_derived` and `imported`, and not `subassembly_default`.
3. The edge network builder therefore appends `source_edge_family_method_unknown` to every
   edge row's diagnostics, and `_edge_family_source_status` turns that into `warning`.
4. `_intersection_boundary_edge_authority_exclusion_reason` lowercases the row's
   `source_diagnostic_rows` and matches the token `method_unknown`, so the row is excluded
   as `method_unknown`. The `default_accepted` guess missed it because it never touched the
   method itself.

That also explains the measured table: clearing the diagnostics removes the stored
`edge_family_subassembly_defaulted` and `approval_pending` markers, but the method-unknown
diagnostic is regenerated on every evaluation from `source_method`, so only rewriting the
method removes it.

**What was built.** `intersection_review_rows` and `apply_intersection_review` now cover
all five families (`POLICY_FAMILY_SPECS`), accepting a row only when the fields it governs
are present and clearing its diagnostics. `adopt_edge_families_from_subassembly` rewrites
`subassembly_default` to `subassembly_derived` as its own action, refusing a row without a
`subassembly_kind`, and the panel exposes it as `Adopt Edge Families From Subassembly` with
a confirmation. `drainage_policy_rows.intent_status` is untouched, as decided.

Review rows are now **T 18, Cross 30, Roundabout 24**, all reaching `n of n` from
`Accept Reviewed Rows`.

**Measured result.** For a T preset, accepting alone leaves `IntersectionBoundaryOwnerStatus`
short of `ready`; accepting and then adopting gives `ready` with 15 owners. (That was true while the T
boundary was a rectilinear perimeter built from the edge rows. Since the T fillet of 2026-10-07 the T takes the
curb return envelope and is `ready` with 4 owners either way; see "Curb return fillet for a T".)

**Cross did not reach `ready`, for a reason that was not the review.** The same document
measured through the T smoke's manual acceptance also read `missing`, with zero owners. A
strict `xfail` pinned it until the Cross owner change below. The acceptance line above was
therefore met for T and not for Cross at the time of the review change.

The first explanation written here, that the corner arcs are not built, was wrong and is
corrected on 2026-10-07 after measuring both kinds. The evaluation is sound for a Cross:
topology reports 4 corners and 4 curb return arcs, and the boundary loop is a `ready` closed
loop of 33 points and 32 segments, the curb return envelope. The two kinds take different
paths through `evaluate_boundary_loops`:

| | T | Cross |
| --- | --- | --- |
| boundary source | `rectilinear_edge_network_envelope` | `curb_return_envelope_ready` (4 corners, 32 points) |
| graph edges carrying an `intersection-boundary-owner:` ref | 18 of 18 | 0 of 32 |
| graph edges consumed by the slope face surface | 18 of 18 | 0 of 32 (`GraphMissingEdgeCount` 32) |
| slope face fill | upper panel triangles | strip triangles |

Owner refs are assigned only by the rectilinear path
(`_intersection_boundary_rectilinear_side_owner_refs`, which matches a loop side to the
side of a perimeter rectangle). The curb return envelope path never assigns one, and the
slope face surface built for a Cross consumes none of the loop's edges. So the missing
owners are a missing feature of the curb return envelope path, not a regression and not
something the review can supply: it needs a decision about what owns each envelope segment,
and a slope face fill that consumes the envelope. The `curb_return_arcs=0/4` and
`cross_intersection_corner_arc_gap` diagnostics belong to the intersection surface patch
triangulation, which counts arcs by its own rule, and are a separate observation.

#### What "filled" and "owner" mean, and what a Cross lacks

Measured on 2026-10-07 while scoping a fix, because the first reading above, that giving
the envelope owner refs would be enough, did not survive it.

- `IntersectionBoundaryOwnerStatus` is `ready` when owner rows exist and no owner is missing
  an expected consumer. The rows are the graph edges of the shared boundary graph, grouped by
  their `intersection-boundary-owner:` refs.
- A boundary-loop graph edge is "filled" when it appears in the `boundary_edge_refs` of one of
  the graph's `upper_*` cells, or among the transition strip refs
  (`_intersection_boundary_loop_graph_fill_coverage`). The code marks those cells
  `graph_upper_cell_metadata_only`: for a T, `ready` is a consistency check between the
  graph, the loop and the panel metadata, not a measurement of a slope face mesh. The T
  slope face preview is 4 triangles, one upper panel.
- A Cross has 32 loop edges and none appear in any upper cell's refs, so 0 are filled.
- The T-only guard `_intersection_upper_slope_face_panel_supported` is not the cause. Lifting
  it, tried without committing the change, makes the same generator produce its 4 upper
  panel triangles for a Cross, and the numbers do not move: 0 of 32 filled, 0 owners.
- The inputs are not smaller for a Cross. The shared breakline set holds one
  `patch_to_intersection_slope_face`, one `intersection_slope_face_to_corridor_slope_face`
  and one `intersection_slope_face_to_design_surface` for both kinds, all on the primary
  alignment's left side; the panel generator groups by alignment and side, so for a Cross it
  would panel one side of one road.

That scoping note over-stated what `ready` needs, and the next section corrects it.

#### Cross boundary owners: done on 2026-10-07

Reading the owner status derivation again showed that it does not depend on "filled". The
rows come from graph edges whose `source_refs` carry an `intersection-boundary-owner:` ref
(`_boundary_loop_owner_summary_display_rows`), and a row is `ready` when the edge's role has all
its expected consumers. The curb return envelope segments already had the consumers; they only
lacked the owner ref. So the change is the owner definition alone.

`_intersection_boundary_join_ordered_corner_arcs` now adds
`intersection-boundary-owner:<corner ref>:arc` to each arc segment, and `:connector` to a
connector, in the same `intersection-boundary-owner:<group>:<side>` form the rectilinear path
uses. A curved span has no rectangle side to own it, so a corner's curb return arc is one owner.
A Cross has 4 corners and so 4 owners of 8 edges each.

Measured, with the starter Cross after Accept Reviewed Rows: `IntersectionBoundaryOwnerStatus`
`ready`, 4 owners, 4 ready, 0 warning. Nothing about T changes, since it takes the rectilinear path.

Two facts to keep in mind:

- **The Cross owner does not wait for adoption.** The envelope is built from the topology's corner
  arcs, not from the edge rows, so the `method_unknown` edge-authority filter that holds a T at
  `missing` until `Adopt Edge Families From Subassembly` does not apply. The Cross owner is `ready`
  before and after adoption. This is stated as measured; whether the envelope should also respect
  edge authority is a separate question and is not decided here.
- **Nothing fills the arcs yet, for either kind.** The Cross slope face preview is 4 triangles
  (a boundary strip) and the T one is 4 triangles (one upper panel); the curb return perimeter strip
  is empty for both (`curb_return_slope_face_perimeter_outer_point_missing`). The loop coverage
  `IntersectionBoundaryLoopGraphFilledEdgeCount` is therefore still 0 of 32 for a Cross, with
  `IntersectionBoundaryLoopGraphCoverageStatus` `warning`, and the change does not touch it. The
  three design questions of the earlier note, graph upper cells over the envelope, the owner
  definition, and panel coverage across the four arms, reduce to the second one for the owner
  status. The first and third would change the surface and would be checked only by metadata,
  so they are left as a candidate and not started.

`test_boundary_owner_reaches_ready_from_the_preset_plus_review_and_adoption` is now T only, and
`test_cross_boundary_owner_is_one_curb_return_arc_per_corner` pins the Cross result, including that
the filled count stays 0 and the coverage stays `warning`.

#### Curb return arc fill: stopped on 2026-10-07, the arcs are not fillets

Starting the fill showed that it should not be built on the arcs as they are. Measured with
`evaluate_topology` on the starter presets:

- The curb return perimeter strip (`_append_intersection_curb_return_slope_face_perimeter_tin`)
  looks for an Applied Section side-slope point 0.25 m to 4-8 m radially outside each arc point.
  The nearest candidate to a Cross arc is 2.83 m away and 0.1 m *inside* the arc, so every point
  reports `outer_point_missing`. It is the same for a T.
- The reason is the arc. For a Cross the four corner arcs are quarter circles of radius 10 centred
  on the intersection centre (0, 0): `(10, 0) -> (0, 10)`, `(0, 10) -> (-10, 0)`, and so on. Joined,
  they are one circle of radius 10, and their end points lie on the leg centre lines. For a T, the
  two arcs are both of radius 12, `(-12, 0) -> (0, 12)` and back. A curb return is a fillet tangent
  to the two leg edges, with its centre out in the corner; these are not.
- A radial strip outward from such a circle would run across the arms' roadway, so a fill would put
  slope face triangles on pavement. It would make the coverage read 32 of 32 while the surface got
  worse.

So the fill is not the next step; the arc geometry is. That is the topology's corner arc
(`IntersectionTopologyCornerRow.arc_points_xyz`) and everything built on it: the boundary loop and
its owners, the patch, the shared breaklines. Deriving a tangent fillet from the leg edge lines and
the curb return radius changes all of those, so it needs its own decision, a regression review of
the built surfaces, and a GUI check. The Cross owner change above is unaffected: it labels whatever
arcs the topology gives, and the labels would stay one per corner.

Update, 2026-10-07: a Cross's arcs are now fillets (the section "Curb return fillet" below); the text
above records what was found and why the fill waited for it.

Not verified here: whether this is a deliberate starter simplification or an unfinished evaluation,
since no document or plan text states the intended geometry. Check `evaluate_topology` and the
curb return policy rows before assuming either.

How the arc is built, read on 2026-10-07 so the next step does not have to rediscover it:
`_intersection_curb_return_edge_endpoints` puts each arc end on a leg axis at a distance equal to
the curb return radius from the anchor, so the ends are on the centre lines, and
`_intersection_curb_return_arc_points` sweeps between them around `arc_center_xyz`, which
`evaluate_edge_network` sets to the anchor. Nothing in that path reads a leg half-width.

A fillet needs three inputs the path does not have: which edge it is tangent to (the pavement edge
or the curb or shoulder line), that edge's lateral offset on each leg (the lane count, lane width,
shoulder width and median of the arm policy rows are the candidates, and the starter writes them
as defaults), and which side of each leg the corner is on. The tangent points and centre then follow
from the radius. The last one is already in the corner row (`side`, `quadrant`) but the existing
`left` / `right` handling in `_intersection_curb_return_edge_endpoints` only negates one end.
The first two are decisions, and they set where the boundary loop goes.

#### Curb return fillet for a Cross: done on 2026-10-07

The user decided on 2026-10-07 that the arc should be a fillet tangent to the pavement edge. The
offset the user named, lane count times lane width from the arm policy rows, is not what the leg edge
rows use, so it was not used as written; see the second point.

- **Geometry.** For a corner between two arms, the arc of radius R (the curb return policy's) tangent
  to the pavement edge of each arm, on the side of the corner: its centre is R beyond each edge, its
  end points are the tangent points. For the starter Cross that is centres at (+-14.5, +-14.5) and
  end points such as (14.5, 4.5) and (4.5, 14.5). The old arcs were centred on the intersection centre
  with end points on the centre lines. Implemented in `_intersection_curb_return_fillet`, called by
  both `evaluate_topology` (the corner rows) and `evaluate_edge_network` (the curb return edge rows,
  whose `arc_center_xyz` is now the fillet centre), with the old arc kept as the fallback.
- **Pavement edge offset.** It is taken from the edge policy row of each arm's `pavement_edge`
  through `_intersection_edge_lateral_offset`, the function the leg edge rows use, so the arc is
  tangent to the very line the boundary and the patch are built from. When this was written that was
  4.5 m because the starter rows carry the rule `lane_width_from_arm_policy` with `offset_value` 0 and the
  function fell back to a constant: the rule did not read the arm policy. Reading lane count x lane width / 2
  alone (3.5 m for the default arm) would have put the arc 1 m inside the edge it is meant to touch. The
  rule now reads it; see "The pavement edge rule reads the arm policy" below.
- **Not applied to a T.** A T's primary arm is a through leg, one span covering both directions, so a
  corner of it has no single direction, and its source edge rows describe one side of each arm only
  (the north edge of the primary, the west edge of the stem). Its boundary is built from a rectilinear
  perimeter of those rows; with fillets in place the perimeter no longer closed and the boundary
  fell to the convex hull, which lost the owners (`ready` with 15 owners became `missing`). So a corner
  with a through leg, or an arm without a pavement edge policy row, keeps the earlier arc, and a T's
  boundary is unchanged. Doing a T needs its edge rows made two-sided first.
- **A T's corners are also inconsistent.** Found on the way, and left alone: the T's second corner
  ends on the same side as its first (`side` right negates the wrong end), and the stem is placed at
  +y by the corner code and at -y by the leg edge rows. The fillet reads the direction from the leg's
  station span, as the edge rows place it, which is why it is correct for the stem.
- **Boundary loop.** The fillets leave the four arm mouths open, so the envelope joins them with
  `curb_return_envelope_connector` segments, which the envelope code already supported. They are
  cut to the average arc segment length, because the patch quality check flags an edge more than 2.5
  times the average (`intersection_surface_patch_long_boundary_edges` appeared with a 9 m connector).
  Cross owners are now 7: 4 arcs and 3 connectors.
- **Measured against the starter Cross before the change.** The patch status was `warning` before and
  is `warning` now, with the same two diagnostics (`curb_return_radius_large`,
  `cross_intersection_corner_arc_gap`). The long edge count is 0 in both. The triangle quality is worse:
  skinny triangles 122 to 172 and the minimum triangle quality 0.012 to 0.0029, because the boundary
  is now the real intersection area (reaching 14.5 m from the centre rather than a circle of
  radius 10) and the patch is triangulated from boundary points alone. That is dealt with in the
  next section.
- **Not verified.** Nothing was looked at in FreeCAD. The Cross patch, slope face and breaklines were
  checked through the preview properties and the contract tests only.
- **Tests.** `test_curb_return_fillet.py`: each corner is tangent to both edges with its centre at
  (+-(4.5+R), +-(4.5+R)), the loop closes with evenly cut connectors, a T keeps its arcs, an arm without
  a pavement edge policy keeps the arc. The Cross owner test now expects 7.

#### The pavement edge rule reads the arm policy: done on 2026-10-07

The starter edge policy rows name the rule `lane_width_from_arm_policy` with `offset_value` 0, and
`_intersection_edge_lateral_offset` ignored the name and returned a constant 4.5 m. It now reads the
arm policy row of the leg.

- **Definition.** `_intersection_arm_pavement_half_width`: half of `lane_count` times `lane_width`, plus
  `shoulder_width`, plus half of `median_width`. `lane_count` is the arm's total lane count (the editor
  default is 2 for a two-lane road). The pavement edge is taken outside the shoulder, which is why the
  shoulder is in it. The starter arm (2 lanes, 3.5 m, 1.0 m shoulder, no median) gives 4.5 m: the
  old constant is exactly this sum, which is the evidence for the definition, so **the starter
  documents do not move**. Lane width alone, 3.5 m, was the first reading and was wrong by the shoulder.
- **Precedence.** An explicit `offset_value` still wins. Only the rule `lane_width_from_arm_policy` on a
  pavement or lane edge reads the arm; the daylight rows and every other rule are untouched.
- **Fallback.** An arm with no row, or a row with no lane count or lane width, keeps 4.5 m and
  `evaluate_edge_network` adds `info:edge_network_arm_policy_width_missing_default_offset_used:<policy>:<leg>`.
  It is an info line, not a warning on the edge row, so the edge status of existing documents does not change.
- **Consumers.** The leg edge rows and the curb return fillet read the same function, so an arm that is
  changed (lanes, lane width, shoulder, median) moves its pavement edge and the fillets tangent to it
  together. The daylight edge stays at its own offset, so a very wide arm can reach it; there is no check
  for that.
- **Not verified.** Only the starter T and Cross and hand-built arms were run; nothing was looked at in
  FreeCAD. The Applied Sections and Assembly widths are separate sources and are not tied to the arm policy
  here, so an arm policy that disagrees with the Assembly's pavement width is not detected.
- **Tests.** `test_edge_offset_arm_policy.py`: the formula, the starter edges unchanged and a changed arm
  moving only its own edge, explicit offset wins and the fallback note, and the fillet following the arm.

#### Patch triangulation quality after the fillet: done on 2026-10-07

Measured by wrapping `IntersectionPatchShapeQualityService.evaluate` and splitting the triangles by kind.
Of the starter Cross patch's 207 triangles, **160 are `constraint_support_triangle` rows from the shared
breakline constraint (`shared_breakline_constraint_edge`) and all 160 are skinny, with a minimum quality of
0.0122**; they were skinny before the fillet and are not part of this change. The other 47 are the boundary
polygon (`intersection_surface_patch`, `ordered_polygon`), and 12 of them were skinny, the worst at 0.0029.
So the fillet's own contribution was 12 triangles, not the 50 the totals suggested.

- **Cause.** `ordered_polygon_triangulation` ear-clips the boundary points only. Ear clipping takes
  the first ear it finds, which on a long outline leaves slivers.
- **Change.** `delaunay_flip_triangulation_indices` (in `services/geometry/polygon_triangulation.py`)
  flips interior diagonals while the opposite vertex lies inside the circumcircle and the quadrilateral is
  strictly convex, so the new diagonal stays inside the polygon. No vertex is added, no boundary edge changes
  and the triangle count and area are kept; edges are visited in sorted order, so it is deterministic.
  `ordered_polygon_triangulation` runs it on the ear clip.
- **Result on the starter Cross.** The boundary polygon's skinny triangles go from 12 to 0 and its smallest
  quality from 0.0029 to 0.1885, against the service's threshold of 0.08. A T does not take this path, so it is
  unchanged.
- **Not changed.** The 160 constraint support triangles; the patch status is still `warning` for the same two
  reasons as before (`curb_return_radius_large`, `cross_intersection_corner_arc_gap`). The structured strip
  triangulation also ear-clips and was not changed, since the starter documents do not use it.
- **Tests.** `test_polygon_triangulation_service.py` (a thin ellipse is improved with the polygon, its boundary
  edges, its area and its triangle count kept, a Delaunay input is left alone, an L shape keeps its area) and
  `test_curb_return_fillet.py` (the Cross patch's boundary triangles are all above the skinny threshold).

#### Curb return fillet for a T: done on 2026-10-07

The user supplied Build Parametric captures of the starter T on 2026-10-07 that showed what the earlier
T work had left: a heavy arc about the intersection centre cutting across the stem's pavement, an empty area
between the stem, the through road and that arc, and patch and panel pieces on one side of the through road
only. The plan agreed with the user was (1) make the T's edge rows two-sided, (2) fix the T's corner
direction, (3) apply the fillet. Step 1 was dropped after measuring.

- **Why step 1 was dropped.** The T boundary was the outline of the union of rectangles built from the
  edge rows (the north strip, the stem's west strip and two corner rectangles), an 18-point rectilinear
  loop reaching 35 m down the stem, which is the shape in the captures. Completing the edge rows would add the
  south and east strips, and the union of those strips around the junction is a ring with the pavement as its
  hole, not one closed outline, so the rectilinear perimeter would not have closed. The Cross already had a
  construction that suits any junction, the curb return envelope, so the T now uses it.
- **Corner direction (step 2).** The primary leg is one span with two ends, so
  `_intersection_curb_return_leg_direction` takes its end from the corner's `side` (`left` is the negative end)
  and the stem's direction from where its station span lies against the anchor (the stem runs to -y, as its
  leg edge rows place it). The corners are now (-16.5, -4.5) to (-4.5, -16.5) and (4.5, -16.5) to (16.5, -4.5).
  The earlier defect, both corners ending on the same side and the stem at +y, is gone with it.
- **Fillet and closure (step 3).** A T has two fillets and a straight side. The topology corner row gained
  `arc_kind` (`fillet` or `centre_arc`) and `start_far_edge_xyz` / `end_far_edge_xyz`, the points on the through
  road's opposite pavement edge. With two fillet corners the envelope joins them across the stem mouth and
  closes the loop through those two far edge points, which is the through road's north edge. Connectors
  are cut to the arc spacing as for the Cross.
- **Measured on the starter T.** The boundary loop is `ready`, closed, 43 points, extent x -16.5 to 16.5,
  y -16.5 to 4.5, area 468 against 467 for the exact outline. Before it was 18 points reaching y -35.
  Owners are 4: the two arcs, the stem mouth connector and a `closure` owner for the straight side
  (the Cross has 8, its closing connector now also a `closure` owner). The patch has no long boundary
  edges and its status is `warning` for `curb_return_radius_large` only. The shared breakline audit stays
  `ready` with zero geometry, mesh and reversed mismatches, and the count goes from 49 to 92: the 43 loop
  segments are now breaklines (`intersection_boundary=43`).
- **A consequence to know.** The T owner status no longer depends on the review or on adopting the edge
  families, as for the Cross, because the envelope is built from the corners and not from the edge rows. The
  5.10 measurement above ("accepting alone leaves it short of `ready`, adopting gives 15 owners") was true of
  the rectilinear boundary and is not true of the presets now: the owner is `ready` with 4 owners
  either way. The edge-authority filter still holds a boundary built from edge rows back, which is what a document
  without pavement edge policies, or a hand-built model, still gets.
- **What the regression runner found.** `smoke_intersection_t_slope_face_surface.py` (the practical-scope runner)
  failed on the first run of this change, and the failures were real:
  - The Design Surface stopped consuming boundary-loop breaklines, because the envelope connectors carried
    the role `curb_return_to_intersection_slope_face`, whose consumers do not include the design surface. A
    connector closes the loop across an arm mouth or along the straight side, where the corridor's design
    surface meets the patch as a pavement edge does, so `_intersection_boundary_segment_role_from_edge_role`
    now gives a connector the role `patch_to_design_surface`. The Design Surface consumes 27 of them.
  - The ordinary Slope Face Surface stopped consuming boundary-loop breaklines although the loop clips it
    (112 triangles tested, 64 clipped). The corridor's slope face meets the curb return arc, since the dedicated
    intersection slope face is a handful of triangles beside it. So the role `curb_return_to_intersection_slope_face`
    now lists `slope_face_surface` among its consumers (`_intersection_boundary_expected_consumers` and the shared
    breakline service's `EXPECTED_CONSUMERS`), and the ordinary Slope Face Surface consumes the 16 arc segments. This
    applies to a Cross's arcs too. The shared breakline audit stays `ready` with zero mismatches.
  - Seven assertions of that smoke described the old rectilinear T: owners on the main and side road legs, the role
    `main_road_tie`, and a boundary loop coverage of `ready`. The smoke now asserts the new truth: the owners are
    the two arcs, the stem mouth connector and the closure; the roles are `patch_to_design_surface` and the curb
    return role with its three consumers; and the coverage is `warning` with **exactly the 16 arc edges unfilled and
    nothing else** (27 of 43 filled). The coverage was `ready` before only because the old T boundary had no arcs in it.
    So the T now shows the open item below; it is not a new defect and not hidden.
- **Not done.** The T's leg edge rows are still one-sided, since the envelope does not need the other sides; the
  zone surfaces and slope face loops that are built from them are unchanged. The Roundabout is not touched. The
  curb return perimeter strip still builds nothing for a T or a Cross (`outer_point_missing`, the nearest Applied
  Section slope point is not found 0.25 to 4-8 m outside the arc), so the arcs stay unfilled, which is the
  item "the slope face fill of the curb return arcs".
- **Not verified.** Nothing was looked at in FreeCAD. The captures are the reason for the change and a new capture of
  the same view is the way to check it: the arc should now hug the stem's two edges and the area inside it should
  be covered.
- **Tests.** `test_curb_return_fillet.py` (the T's two fillets and their far edge points; the loop's extent,
  area, straight side and owner kinds), the T breakline preview test (92 breaklines, `intersection_boundary=43`),
  and the two owner tests.

#### The arcs the build draws: the patch boundary's curb returns are fillets, done on 2026-10-07

The user's Build Parametric captures of the starter T after the T fillet above still showed the heavy arc
about the intersection centre. Measuring found why: **curb return arcs come from three places**, and the
work above had changed two of them.

| source | used by | before this |
| --- | --- | --- |
| topology corner rows (`evaluate_topology`) | the boundary loop, its owners, its breaklines | fillet (above) |
| edge network curb return rows | the edge rows | fillet (above) |
| patch boundary segments (`IntersectionBoundarySegmentEvaluationService`) | the arc the build draws, the intersection exclusion, the patch's curb return parts, the curb return slope face strip, the curb return breaklines | arc about the centre |

The third is built from the tie-in edges, which come from the Applied Sections, so it is in the real
directions of the alignments. The first two work in a fixed frame whose axes are (1, 0) and (0, 1)
(`_intersection_alignment_axis`): the intersection source and topology carry no alignment bearing at
all. That is why the captures showed the patch rectangles level while the road leans. It is recorded
under "Not done" and is the next item.

- **Change.** `_curb_return_fillet_points` in `intersection_boundary_segment_evaluation_service.py`
  makes each quadrant's arc the fillet of the curb return radius tangent to the two roads' pavement
  edges. Each road's direction, centre line and pavement half width come from its left and right tie-in
  edges (`_tie_in_road_frames`), and the intersection origin is where the two centre lines cross, rather
  than the source point, which at the coordinate origin reads as unset (the old code then used the mean of
  the tie-in end points, (0, -1.5) for the starter T). A road without both edges keeps the arc about the
  centre and the result carries `warning:intersection_curb_return_fillet_unavailable`. Each arc's notes
  say `arc_kind=fillet` or `centre_arc`. `center_xyz` stays the intersection centre, because every
  consumer uses it as the patch's inward reference (the blend and core fans, the slope face strip's
  outward ray).
- **Measured on the starter documents.** The real pavement half width is 5 m (the fixed-frame
  evaluation's 4.5 m is its own default). T arcs run (17, -5) to (5, -17) and its mirror; Cross arcs (15, 5)
  to (5, 15) in each quadrant.
- **The arc fill now builds.** The curb return slope face strip, empty for both kinds until now with
  `outer_point_missing`, builds 2 strips of 40 triangles on the T and 4 strips of 64 on the Cross. The
  arcs had been cutting across the roadway, where no slope point is near. Each strip reaches at most
  7.66 m (T) or 6.01 m (Cross) out from its fillet, takes its heights from slope points within 2.5 m of
  its ray, and drops 1.7 to 1.95 m, a side slope.
- **The T smoke guard changed with it.** `smoke_intersection_t_slope_face_surface.py` asserted that the
  strip stays empty, as a guard against a strip built from slope points far along the road. With the old
  arcs that was the only kind it could build. It now asserts that the strip is built for both corners with
  no missing outer point, and `test_boundary_segment_curb_return_fillet.py` pins the guard's real intent:
  every outer point within 8 m of its fillet and every slope point it used within 3 m of the ray.
- **What does not change.** The boundary loop coverage metric is still 27 of 43 on the T: it counts the
  fixed-frame envelope's edges (at 4.5 m), and the strip fills the real arcs (at 5 m). They are not the same
  line, so the strip is not counted against the envelope's arcs, and linking them would hide the frame
  difference.
- **Not done.** The fixed frame of the topology, edge network and envelope. They need each alignment's
  real direction at the intersection, which only the commands can read from the document; about 50
  calls of `evaluate_topology`, `evaluate_edge_network` and `evaluate_boundary_loops` across four command
  modules and the builders would carry it. Until then, on a document whose roads are not on the X and Y
  axes, the boundary loop, its owners and breaklines, and the patch rectangles it shapes are placed in the
  wrong directions, as the captures show. Nothing was looked at in FreeCAD after this change.
- **Tests.** `test_boundary_segment_curb_return_fillet.py`: a 30 degree rotated Cross off the origin gets
  fillets tangent to its rotated edges and outside both pavements, a road missing an edge keeps the centre
  arc with the warning, and the starter T strip's locality.

#### The fixed frame reproduced on a turned T: 2026-10-07

The user's captures after the patch boundary fillet showed the two fillets and their slope face strips in
place, and three remaining defects: side slopes that end in a wedge beside the stem and the through road,
slivers on the clipped edges of the design surface, and the through road's upper slope face panel standing
apart. The roads in the captures lean about 4.7 degrees. The step agreed with the user was to reproduce
before changing the evaluation.

The starter T was built headless with its alignment points turned about the intersection (the starter
specs patched in the test), at 0, 5 and 30 degrees:

| turn | loop straight sides off the road | loop arcs to the real fillets | design surface clipped / kept near the boundary | ordinary slope face clipped |
| --- | --- | --- | --- | --- |
| 0 | 0.00 degrees | 1.05 m | 140 / 221 | 64 (all by control sections) |
| 5 | 5.00 degrees | 1.96 m | 132 / 209 | 64 (all by control sections) |
| 30 | 30.00 degrees | 9.36 m | 112 / 133 | 64 (all by control sections) |

- **Reproduced.** The boundary loop stays on the X and Y axes whatever the roads do, off them by exactly the
  turn, and so do its owners and its 43 boundary breaklines. At 0 degrees the arcs are still 1.05 m from the real
  fillets, because the fixed-frame evaluation's pavement half width is 4.5 m and the real one is 5 m.
- **Not reproduced: the side slope wedge.** The ordinary slope face is clipped by the control sections, 64
  triangles at every turn, not by the loop. Measured across the stem in the stem's own frame, the side slope is
  absent from the junction to about 49 m along the stem and then full width (4 m) at once, a step, at both 0
  and 30 degrees. So the wedge in the captures does not come from the fixed frame, and the starter T does not show
  it; the captured document differs from the starter in a way not yet known. The long stretch with no side slope
  beside the stem is real in the starter too, and is why the fillet strips stand apart from the road side slopes.
- **Pinned.** `test_intersection_rotated_frame.py`: on the 30 degree T the patch boundary's fillets follow the roads
  (passes), and the loop's straight sides follow the roads (strict xfail until the evaluation gets the directions).

### 5.11 Two preset values land where no review state exists: done on 2026-09-28

`IntersectionCurbReturnPolicyRow` and `IntersectionArmPolicyRow` were the only two of
the eleven row families in `intersection_model.py` without `approval_status` or
`diagnostic_rows`. The curb return radius lands on the first and the design vehicle on
the second, so neither could carry `preset_*_review_required`, be accepted, or appear
in the review table. The curb return radius sets the corner arcs, so of the five preset
defaults it was the one most directly responsible for the shape and the one with no
record that it was an unreviewed default.

Both now carry the two fields with the defaults the other nine use. The two default
constructors write `draft` with a `*_source_defaulted` and a `*_approval_pending`
marker, the way every other default family already did; the preset adds
`preset_curb_return_policy_review_required` and `preset_arm_policy_review_required`;
and the review lists and accepts them, keeping the `*_source_defaulted` provenance,
which is where these two record where they came from since neither has a
`source_method` field.

Measured, with the preset options set by hand:

| preset | review rows before | after | added |
| --- | --- | --- | --- |
| T | 5 | 8 | 1 curb return, 2 arm |
| Cross | 7 | 12 | 1 curb return, 4 arm |
| Roundabout | 5 | 8 | 1 curb return, 2 arm |

All three reach `n of n reviewed` from `Accept Reviewed Rows` alone, and the checklist
the previous item added now reads a real state for all five values: three `reviewed`
and two still `review required`, which are grading and drainage, the two of the five
that belong to item 5.10.

Nothing in evaluation reads `approval_status` on either family. The curb return lookup
filters on `intersection_id` alone and the arm policies are read only for the existence
of their ids, so marking a row `draft` changes no geometry. That is what made this item
small.

Compatibility: an old document's JSON has neither key, and both readers fall back the
same way the other nine do, to `accepted` with no diagnostics. A row written before this
change therefore restores as reviewed rather than as pending. Inventing `draft` for it
would be a guess about a history the document does not record, and the fallback rule
here is the one the rest of the family already follows.

`V1_PERSISTENCE_SCHEMA_INVENTORY.md` did not mention either row and now records how
the Intersection row families are stored and what an absent key means.

## 6. Order

5.1 needs nothing and 5.2, 5.3, 5.5, 5.6, 5.8, 5.9, 5.10 and 5.11 are done. 5.7 is closed
without a cache; the time it was about is in the shared breakline audit and the patch
constraint coverage matching, which is a candidate for its own item. The Cross corner arc
gap found by 5.10 is another. 5.8 is what a real route needs. 5.4 is
the largest and is what the Roundabout needs to be more than a symmetric starter; its apron
width and flare parts are done; the editor field for the per-approach rows remains.

## 7. Out of Scope

- reinstating the four removed kinds
- Ramp interaction, which is outside the active product scope
- advanced hydraulics at the intersection, which belongs to Drainage
- any change that makes generated patch geometry editable as source intent

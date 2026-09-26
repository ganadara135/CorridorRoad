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

### 5.2 Settle the Cross boundary loop rule: confirmed

`test_intersection_boundary_loop_prefers_topology_curb_return_envelope_for_cross`
builds a closed, ready loop of 32 points and area 312 through the curb-return
envelope path, and the result is `error` because
`intersection_boundary_authoritative_source_edges_missing` fires. The rule landed
2026-07-02; the envelope path and this test landed 2026-07-06. The sibling test
asserts the same error for an incomplete edge set, so the rule is doing its job
there. This is the only reason the contract baseline is 1 and not 0.

Two exits, and the choice is a product decision:

- keep the rule, and restate the test as `error` with no loops, accepting that a
  Cross whose envelope closes will not become `ready`
- accept a complete envelope loop as authoritative, and change the rule without
  breaking the sibling test

Acceptance: the contract baseline reaches 0 with both tests stating the chosen
rule explicitly.

### 5.3 Give the panel the review controls the flow requires: partly verified

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

Acceptance: a leg, anchor and control-area review surface in the panel that sets
those fields, so what the T smoke does in code can be done in the document; and,
separately, a measurement of whether a dedicated Slope Face Surface is reachable
for Cross and Roundabout once it can.

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

### 5.5 Let the side road have superelevation

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

Acceptance: superelevation resolved per alignment, whether by several models keyed
on `alignment_id` or by per-alignment row groups inside one; a diagnostic when a
section's alignment does not match the superelevation model it was given; and the
T preset writing a superelevation source for both starter roads.

### 5.6 Warn when a road drops out of Applied Sections: confirmed

`_applied_section_source_bundles` skips an Alignment that lacks a Profile, a
Region model or a Stationing, with `continue` and no diagnostic. Deleting the side
road's Region silently removes its sections, and the intersection then evaluates
against a half-built document.

Acceptance: a source-status row naming the Alignment and the missing piece, and an
intersection topology diagnostic when a participating leg's Alignment has no
sections.

### 5.7 Cache the intersection evaluation chain: confirmed, with a measured count

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

### 5.8 Make the starter geometry usable on a real route: confirmed, and wider

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

### 5.9 Expose the control values the preset guesses: confirmed

Design vehicle, curb-return radius, control length, grading policy and drainage
mode all arrive as preset defaults. The panel's status text lists what was created
and a generic next-workflow note; it does not name the defaulted values or the
review refs that will carry them. Its own closing line says that final
surface-zone and roundabout geometry expansion remain planned follow-up phases,
which is the only place the user is told the shape may be incomplete.

Acceptance: the preset summary lists each defaulted value with the review ref that
will carry it, so the review step has a checklist rather than a note.

## 6. Order

5.1 needs nothing. 5.6 is small and makes a silent drop-out visible; do it first.
5.3 is the one that decides whether the flow is completable in the document at all,
and its first half does not depend on the unverified half. 5.2 is the only item
that changes the contract baseline. 5.5 and 5.8 are the two that block a real
route. 5.4 is what the Roundabout needs to be more than a symmetric starter. 5.7
is measurable on its own and 5.9 is workflow quality.

## 7. Out of Scope

- reinstating the four removed kinds
- Ramp interaction, which is outside the active product scope
- advanced hydraulics at the intersection, which belongs to Drainage
- any change that makes generated patch geometry editable as source intent

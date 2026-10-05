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
short of `ready`; accepting and then adopting gives `ready` with 15 owners.

**Cross does not reach `ready`, and this item does not explain why.** The same document
measured through the T smoke's manual acceptance also reads `missing`, with zero owners. Its
slope face preview reports `curb_return_arcs=0/4` and `cross_intersection_corner_arc_gap:
missing=4`, and the Design and Daylight previews report `boundary_loop_refs_missing`. The
corner arcs are not built for a Cross, so the boundary loop carries no owners whatever the
review state. That is a separate gap, pinned by a strict `xfail` in
`test_intersection_policy_family_review.py` so that fixing it forces the test to be updated.
The acceptance line above is therefore met for T and not for Cross.

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

5.1 needs nothing and 5.2, 5.3, 5.5, 5.6, 5.9, 5.10 and 5.11 are done. 5.7 is next and
is measurable on its own. The Cross corner arc gap found by 5.10 is a candidate for its own
item. 5.8 is what a real route needs. 5.4 is
the largest and is what the Roundabout needs to be more than a symmetric starter.

## 7. Out of Scope

- reinstating the four removed kinds
- Ramp interaction, which is outside the active product scope
- advanced hydraulics at the intersection, which belongs to Drainage
- any change that makes generated patch geometry editable as source intent

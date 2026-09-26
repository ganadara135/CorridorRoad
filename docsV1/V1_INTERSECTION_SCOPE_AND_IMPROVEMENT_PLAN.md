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

Ordered by what unblocks the most. None of these is scheduled; each names its
own acceptance check so it can be picked up alone.

### 5.1 Diagnose an unsupported intersection kind

`evaluate_topology` carries `intersection_kind` through without validating it. A
row holding a removed or misspelled kind silently takes the T-shaped defaults:
two corners, radius 12, two quadrants.

Add one source diagnostic, `warning:source_intersection_kind_unsupported:<kind>`,
where the kind is not in `SUPPORTED_INTERSECTION_KINDS`. It must be a warning,
not an error, so an old document still builds.

Acceptance: a topology result for an unknown kind reports the diagnostic, keeps
its other rows, and its status is not worse than `warning`.

### 5.2 Settle the Cross boundary loop rule

`test_intersection_boundary_loop_prefers_topology_curb_return_envelope_for_cross`
builds a closed, ready loop of 32 points and area 312 through the curb-return
envelope path, and the result is `error` because
`intersection_boundary_authoritative_source_edges_missing` fires. The rule landed
2026-07-02; the envelope path and this test landed 2026-07-06. This is the only
reason the contract baseline is 1 and not 0.

Two exits, and the choice is a product decision:

- keep the rule, and restate the test as `error` with no loops, accepting that a
  Cross whose envelope closes will not become `ready`
- accept a complete envelope loop as authoritative, and change the rule without
  breaking its sibling test, which asserts that an incomplete edge set stays an
  error

Acceptance: the contract baseline reaches 0 with both tests stating the chosen
rule explicitly.

### 5.3 Complete the Slope Face Surface for Cross and Roundabout

`tests/regression/smoke_intersection_non_t_slope_face_readiness.py` says in its
own docstring that it does not claim non-T Slope Face Surface completion; it only
guards against build errors and misleading `ready` states. So the dedicated
Slope Face Surface is finished for T alone.

Acceptance: a Cross and a Roundabout smoke that assert a dedicated Slope Face
Surface the way the T smoke does, not a readiness check.

### 5.4 Give the Roundabout a boundary instead of a circle

Roundabout ownership is a circle: centre plus circulatory outer radius plus
apron width, from `_roundabout_ownership_boundary_spec`. A real roundabout has
per-approach entry and exit geometry, and an apron that need not be uniform. The
1.1.0 fix for clipping that ran without its boundary shows how thin this path
is.

Acceptance: roundabout ownership comes from a boundary loop like the other two
kinds, with the circle kept only as the fallback when no loop closes, and the
existing circle-based smoke still passing against the fallback.

### 5.5 Let each road choose its own Assembly

Applied Section generation is per Alignment, but the Assembly, Structure,
Drainage and Superelevation models are still resolved first-found and therefore
shared by every road in the document. A main road and a side road cannot have
different standard sections, which is why the preset gives both roads the same
starter Assembly.

Acceptance: a Region row's `assembly_ref` selects among several Assembly models
in one document, and a T preset built with a wide main road and a narrow side
road produces different section widths per road.

### 5.6 Warn when a road drops out of Applied Sections

`_applied_section_source_bundles` skips an Alignment that lacks a Profile, a
Region model or a Stationing, with `continue` and no diagnostic. Deleting the
side road's Region silently removes its sections, and the intersection then
evaluates against a half-built document.

Acceptance: a source-status row naming the Alignment and the missing piece, and
an intersection topology diagnostic when a participating leg's Alignment has no
sections.

### 5.7 Cache the intersection evaluation chain

`evaluate_topology` is called from seven places in `cmd_build_corridor`, and each
one re-runs the chain from the model. Incremental rebuild covers two stages,
`corridor_model` and `surface_model`, so the intersection chain is outside it.

Acceptance: one evaluation per build for an unchanged IntersectionModel, proved
by a call counter in a focused test, with the same result rows as today.

### 5.8 Make the starter geometry usable on a real route

The starter alignments are hardcoded straight lines: the T is a 240 m main road
and a 100 m side road, with no curve, no superelevation and a generated flat
profile. Any real job goes through `Use Existing Alignments`, and that mode
leaves the user to create the Region, Superelevation and Drainage sources the
preset would have made.

Acceptance: `Use Existing Alignments` creates the same source set the preset
does, minus the alignments and profiles it is given.

### 5.9 Expose the control values the preset guesses

Design vehicle, curb-return radius, control length, grading policy and drainage
mode all arrive as preset defaults. The panel accepts them, but nothing tells the
user which of those defaults is load-bearing for the shape they are about to see.

Acceptance: the preset summary lists each defaulted value with the review ref
that will carry it, so the review step has a checklist rather than a note.

## 6. Order

5.1 and 5.6 are small and make wrong input visible; do them first. 5.2 is the
only item that changes the contract baseline. 5.3 depends on 5.2 for Cross. 5.4
and 5.5 are the two that change what the product can express. 5.7 is measurable
on its own. 5.8 and 5.9 are workflow quality and can follow at any point.

## 7. Out of Scope

- reinstating the four removed kinds
- Ramp interaction, which is outside the active product scope
- advanced hydraulics at the intersection, which belongs to Drainage
- any change that makes generated patch geometry editable as source intent

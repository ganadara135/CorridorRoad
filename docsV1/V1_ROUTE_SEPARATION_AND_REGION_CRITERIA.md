# Parametric Road V1 Route Separation and Region Criteria

Date: 2026-09-24
Branch: `ganada_0902`
Status: Decision record. No code is changed by this document.
Depends on:

- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_REGION_APPLICATION_FLOW_PLAN.md`
- `docsV1/V1_REGION_DOMAIN_OWNERSHIP_REDESIGN_PLAN.md`
- `docsV1/V1_INTERSECTION_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROJECT_TREE_REDESIGN_PLAN.md`

## 1. Purpose

Two questions come up as soon as a job has more than one road, and the answer to
one has been mistaken for the answer to the other:

- when does a road belong in a document of its own?
- when does a stretch of road deserve a Region row?

Regions are not a way to keep two roads apart. This document states where the
boundary actually is, what the code supports today, and which criteria decide
each case.

## 2. Scope

This document covers:

- the choice between one document with several Alignments and one document per road
- the criteria for adding, splitting, or not adding a Region row
- Region precedence, overlap, gap, and boundary continuity rules as the services enforce them
- what is inactive in a single-road document

This document does not cover:

- Assembly or Subassembly authoring
- Structure, Drainage, Ramp, or Intersection domain design
- multi-document reference or federation, which the addon does not have

## 3. Core Rule

Three layers, and they are not interchangeable:

| Layer | Unit | Separates |
| --- | --- | --- |
| Document (`.FCStd`) | one project | independent routes |
| `AlignmentModel` | one road axis | roads that meet |
| `RegionRow` | one station span | policy inside one road axis |

`V1_INTERSECTION_IMPLEMENTATION_PLAN.md` section 4.1 already fixes the middle
row: each road axis remains its own `AlignmentModel`. A Region is a station span
on one such axis, so it can never stand in for a second road.

## 4. What the Code Supports Today

Measured on 2026-09-24.

### 4.1 One project per document

`find_project` in `objects/obj_project.py` returns the first project object in
the document. There is no second project, and the addon holds no cross-document
references: a separate route means a separate `.FCStd` file, and the only
transfer between files is LandXML, DXF, or IFC through `09_Outputs & Exchange`.

### 4.2 Regions are scoped to one Alignment

`RegionModel.alignment_id` is one value per model, and `RegionRow` carries only
`station_start` and `station_end`. Concatenating two roads into one station
space would collapse their centerlines, profiles, superelevation, and
intersection references into a single axis.

### 4.3 Multi-road work that already functions

| Area | Evidence |
| --- | --- |
| Intersections | `primary_alignment_ref` and `secondary_alignment_refs` are required; missing either is an error diagnostic in `intersection_evaluation_service`. The editor lists the document's Alignments, can create one, and writes a Region model per participating road. |
| 3D Centerline | `cmd_centerline3d` iterates every Alignment and pairs each with its own Profile and Stationing by `alignment_id`. |
| Build Parametric review | `_document_region_models` collects every Region model; `_sections_for_region_model` filters Applied Sections by `alignment_id`. |
| Cross Section Viewer | filters intersection clip context by the active section's `alignment_id`. |

### 4.4 What is and is not alignment-aware

Applied Section generation is alignment-aware, and an earlier revision of this
document said otherwise. `_applied_section_source_bundles` walks every Alignment
in the document and pairs it with its own Profile, Region model and Stationing by
`alignment_id`. An Alignment missing any of those three is skipped without a
diagnostic. With two or more complete bundles the build loops per Alignment and
merges the partials into one set labelled `alignment:multiple`; the first-found
`find_v1_*` path runs only as the single-bundle fallback. Measured on the
T Intersection preset, the set carries 32 sections across both starter roads.

What is not alignment-aware: about twenty `find_v1_*(document)` lookups return
the first object of their kind, which is what the single-bundle fallback uses and
what the Assembly, Structure, Drainage and Superelevation models resolve through
even on the multi-alignment path, so those are shared across roads rather than
chosen per road. Quantities and the design surface models carry no alignment
field at all and are document-wide. Incremental rebuild keys its stages on
`corridor_model` and `surface_model` only, so editing one road restages both.

## 5. When To Create a Separate Route Document

Use one document per road when any of these hold:

- the roads never meet: no intersection, no ramp, no shared edge or boundary
- the roads belong to different contracts, sections, or delivery packages
- they use different design standards or unit policy
- more than one person works on them at the same time, since locking is per document
- one road is already heavy enough that rebuild time is a problem

This matches the `find_v1_*` singleton assumption exactly, which is why it is the
most stable arrangement the current code offers. The costs are real and should be
accepted knowingly:

- the existing ground TIN must be imported into each document, through LandXML
- earthwork and quantity totals are per document; combining them is manual
- if the roads later meet, one of them has to be moved into the other's document

## 6. When To Keep Roads in One Document

Use one document with one `AlignmentModel` per road when:

- the roads intersect, or a ramp ties one into the other; this is not a
  preference but a requirement, since an intersection source cannot reference an
  Alignment in another file
- they share one existing ground surface, coordinate system, and standards
- earthwork must balance across them

In that arrangement, give every road its own Profile, Stationing and Region model,
and keep `alignment_id` filled on each. That triple is what makes an Alignment a
complete bundle; one missing piece drops the road out of Applied Sections without
a diagnostic. The Assembly, Structure, Drainage and Superelevation models are
still resolved first-found and therefore shared by every road in the document.

## 7. What a Region Is

`V1_REGION_DOMAIN_OWNERSHIP_REDESIGN_PLAN.md` settled the ownership: Region owns
station spans and the base Assembly only. Structure and Drainage own their own
domain intent and reference Region from their own panels.

`RegionRow.structure_ref`, `structure_refs`, and `drainage_refs` were removed.
The active row carries `region_id`, `station_start`, `station_end`,
`region_index`, `assembly_ref`, `ramp_ref`, `intersection_ref`, `policy_set_ref`,
`template_ref`, `superelevation_ref`, `override_refs`, `priority`, `source_ref`,
`notes`, and `policy_rows`. `StructureModel` and `DrainageModel` carry
`region_ref` on their side.

One row means one Assembly. That is what keeps resolution deterministic.

## 8. When To Create a Region Row

| Situation | Row needed | Note |
| --- | --- | --- |
| The active Assembly changes | required | the only absolute rule |
| A structure occupies a span (bridge, culvert, retaining wall) | yes | Structure needs a `region_ref` target |
| Drainage treatment changes over a span | yes | Drainage needs a `region_ref` target |
| The superelevation set changes | yes | `superelevation_ref` is per row |
| A transition between two states | yes, its own row | pair it with a `RegionTransition` (`linear_blend`) |
| Cut/fill or daylight policy changes | yes | through `policy_set_ref` |
| A construction stage or design exception | yes, overlapping | give it a higher `priority` |

The Region editor presets show the intended shapes: `Basic Road`,
`Bridge Segment`, `Drainage Control`, `Ramp Tie-In`, and `Intersection Zone`.
They scale by ratio across the Alignment station range, so they are usable as a
starting layout with the stations adjusted afterwards.

## 9. When Not To Use a Region

| Intent | Correct owner |
| --- | --- |
| A small width difference | Assembly parameters or `override_refs` |
| The bridge or culvert itself | `StructureModel` |
| Pipes, inlets, discharge | `DrainageModel` |
| A vertical geometry change | `Profile` |
| Superelevation values | `SuperelevationModel`; a Region only selects a set |
| Another road | a separate Alignment, or a separate document |
| One or two local exceptions | `RegionPolicySet` or `override_refs` |

`V1_REGION_MODEL.md` section 5 states the failure modes to avoid: a Region model
must not become a second template library, a hidden geometry editor, or an
unbounded patch bucket.

## 10. Boundary Rules the Services Enforce

### 10.1 Validation

`RegionValidationService` reports:

- error: missing or duplicate `region_id`, `station_start >= station_end`, non-numeric `priority`
- warning: neither `assembly_ref` nor `template_ref` set, a reference to an unknown assembly, an overlap between two rows of equal priority
- warning: a station that no row covers, raised as `no_active_region` during resolution

### 10.2 Precedence

Candidates are sorted by priority descending, then row order (`region_index`),
then the narrower span, then `region_id`. Overlaps are legitimate as long as the
priorities differ; equal priorities make the outcome depend on row order and are
reported.

The preset priority ladder is a usable convention:

```text
normal_road 10  <  transition 30  <  drainage 65  <  intersection 70  <  ramp 75  <  bridge 80
```

Region kind is not a stored field. It lives in the `region_id` and the notes, so
consistent naming is what makes a model readable; behavior comes from
`assembly_ref` and `priority`.

### 10.3 Continuity

`region_boundary_continuity_evaluation_service` compares adjacent Applied
Sections across a Region boundary and reports a diagnostic when a jump exceeds:

| Quantity | Threshold |
| --- | --- |
| Surface width | 1.0 m |
| Subgrade depth | 0.15 m |
| Daylight width | 1.0 m |
| Daylight slope | 0.05 |

Crossing one of these is the signal that the boundary needs a transition span
rather than a butt joint.

## 11. The Independent-Route Profile

In a document holding one road, two Region facets are inactive:

- `intersection_ref`, because an intersection requires a second Alignment
- `ramp_ref`, because `RampRow.alignment_ref` is required and a ramp is its own axis

Region then reduces to its base meaning: which Assembly is active over which
station span, with superelevation, policy set, and override context attached. It
is also the only segmentation left inside the document, so the naming and
priority conventions above carry more weight than they would otherwise.

## 12. Authoring Order

```text
Alignment / Stations / Profile / TIN
  -> Assembly            reusable section intent
  -> Regions             station span x Assembly
  -> Structures          reference a Region by region_ref
  -> Drainage            reference a Region by region_ref
  -> Applied Sections
  -> Build Parametric
```

Assembly comes first because a Region with nothing to point at raises
`missing_assembly_or_template` immediately.

## 13. Worked Example

One independent route, one document:

```text
region:normal-01       0 - 350     assembly:2lane-fill    priority 10
region:transition-in   350 - 380   assembly:2lane-fill    priority 30
region:bridge-01       380 - 520   assembly:bridge-deck   priority 80   <- Structure references this
region:transition-out  520 - 550   assembly:2lane-cut     priority 30
region:normal-02       550 - 1200  assembly:2lane-cut     priority 10
region:drainage-01     700 - 840   assembly:2lane-cut     priority 65   <- Drainage references this
```

`drainage-01` overlaps `normal-02` and wins on priority. The only thing to check
is that the rows cover the whole range; an uncovered station produces
`no_active_region` and no section there.

## 14. What Would Have To Change

Not scheduled, recorded so the cost is known if one document should ever carry
several roads end to end:

1. An active-road concept, stored on the project or taken from the tree
   selection, extending the `preferred_*` argument that today reaches only the
   Alignment, Profile, and Stations review commands.
2. `find_v1_*(document, alignment_id=...)` in place of first-match lookup, across
   roughly twenty finders that share one shape.
3. Per-road Assembly, Structure, Drainage and Superelevation selection. Applied
   Section generation already loops per Alignment; these four are still resolved
   first-found and shared across every road in the document.
4. Per-road grouping under `03_Alignment & Profile` in the project tree.
5. `alignment_id` in the incremental rebuild stage key, so editing one road does
   not invalidate the others.

Items 1 and 2 are the entry point; the rest depend on them.

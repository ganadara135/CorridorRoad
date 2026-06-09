# Parametric Road V1 Intersection Preset Data Plan

Date: 2026-06-09
Branch: `v1-0503`
Status: Phase IP1-IP7 first code slice implemented
Depends on:

- [V1_MASTER_PLAN.md](./V1_MASTER_PLAN.md)
- [V1_INTERSECTION_MODEL.md](./V1_INTERSECTION_MODEL.md)
- [V1_INTERSECTION_REDESIGN_PLAN.md](./V1_INTERSECTION_REDESIGN_PLAN.md)
- [V1_INTERSECTION_ENHANCEMENT_PLAN.md](./V1_INTERSECTION_ENHANCEMENT_PLAN.md)
- [V1_ALIGNMENT_MODEL.md](./V1_ALIGNMENT_MODEL.md)
- [V1_REGION_MODEL.md](./V1_REGION_MODEL.md)
- [V1_SECTION_MODEL.md](./V1_SECTION_MODEL.md)
- [V1_SUPERELEVATION_MODEL.md](./V1_SUPERELEVATION_MODEL.md)
- [V1_DRAINAGE_MODEL.md](./V1_DRAINAGE_MODEL.md)
- [V1_WATERTIGHT_SOLID_PLAN.md](./V1_WATERTIGHT_SOLID_PLAN.md)

## 1. Purpose

This document defines the next Preset Data plan for Intersections.

The goal is to make T-intersection, cross intersection, and roundabout presets behave like engineering starter contracts, not only visual examples.

Each preset should create enough source and policy data for:

- multi-alignment source creation
- control-area and leg identity
- curb-return or circular edge-network intent
- Applied Sections supplemental station creation
- surface priority and clipping review
- intersection grading and crossfall review
- drainage low-point handoff
- topology validation
- future watertight solid target discovery

## 2. Core Rule

Intersection preset data must create source intent first.

Generated surfaces must be derived from source rows and result contracts.

Do not use preset data to hide mesh repair rules inside Build Parametric.

## 3. Preset Families

### 3.1 T-Intersection

Purpose:

- model one primary through road and one side road
- create two curb-return corners on the approach side
- create a central junction patch
- create side-road tie-in and slope-face handoff points

Recommended preset id:

- `intersection-preset:t-basic`

Required source rows:

- one primary Alignment
- one secondary Alignment
- primary approach, intersection, and departure Regions
- side-road approach and intersection Regions
- one `IntersectionRow` with `intersection_kind = t_intersection`
- two leg rows: `primary_through`, `side_road`
- two curb-return edge policies
- one intersection grading policy
- one drainage policy

Geometry starter values:

| Item | Default |
| --- | --- |
| Primary length | 240 m |
| Side length | 120 m |
| Intersection station on primary | 120 m |
| Intersection station on side | 60 m |
| Control length each side | 24 m |
| Curb-return radius | 12 m |
| Arc samples | 12 or more |
| Lane width | 3.5 m |
| Shoulder width | 1.5 m |

Expected outputs:

- primary pavement strip
- side-road pavement strip
- two curb-return edge arcs
- two curb-return slope-face bands
- central blended intersection surface
- low-point candidate near the curb-return or gutter edge

### 3.2 Cross Intersection

Purpose:

- model a four-leg at-grade crossing
- create four curb-return corners
- support primary and secondary through-road identity
- test surface priority on both sides of both alignments

Recommended preset id:

- `intersection-preset:cross-basic`

Required source rows:

- one primary Alignment
- one secondary Alignment
- primary approach, intersection, and departure Regions
- secondary approach, intersection, and departure Regions
- one `IntersectionRow` with `intersection_kind = cross_intersection`
- four leg rows: primary in/out, secondary in/out, or two through legs with direction metadata
- four curb-return edge policies
- one grading policy
- one drainage policy

Geometry starter values:

| Item | Default |
| --- | --- |
| Primary length | 260 m |
| Secondary length | 220 m |
| Intersection station on primary | 130 m |
| Intersection station on secondary | 110 m |
| Control length each side | 28 m |
| Curb-return radius | 10 m |
| Arc samples | 12 or more |
| Lane width | 3.5 m |
| Shoulder width | 1.5 m |

Expected outputs:

- primary through pavement strip
- secondary through pavement strip
- four curb-return edge arcs
- four curb-return slope-face bands
- central blended intersection surface
- topology diagnostics for all four corners

### 3.3 Roundabout

Purpose:

- model a compact single-lane roundabout starter
- expose circular edge-network behavior
- separate circulatory roadway, splitter islands, entries, exits, and drainage low-point intent

Recommended preset id:

- `intersection-preset:roundabout-single-lane`

Required source rows:

- two crossing Alignments or four approach-leg centerline references
- one `IntersectionRow` with `intersection_kind = roundabout`
- four leg rows
- one circular island policy
- one circulatory roadway policy
- four entry/exit edge policies
- four splitter-island hint policies
- one grading policy
- one drainage policy

Geometry starter values:

| Item | Default |
| --- | --- |
| Inscribed circle diameter | 36 m |
| Central island diameter | 18 m |
| Circulatory lane width | 7 m |
| Entry radius | 12 m |
| Exit radius | 14 m |
| Approach control length | 30 m |
| Circle samples | 48 or more |

Expected outputs:

- central island boundary
- circulatory roadway ring
- entry and exit transition edges
- splitter island preview edges
- roundabout grading zone
- low-point candidate and inlet hints around the outside gutter

Roundabout advanced operation, capacity analysis, and yield-control simulation remain non-goals for this preset slice.

## 4. Common Source Contract

Every preset should populate the same contract families.

| Family | Required Meaning |
| --- | --- |
| `AlignmentModel` | participating road centerlines |
| `ProfileModel` | initial FG elevation control for each alignment |
| `Stationing` | station rows for each alignment |
| `RegionModel` | ordinary corridor spans and intersection-controlled spans |
| `IntersectionModel` | junction type, legs, policies, and control areas |
| `SuperelevationModel` | normal approach crossfall and optional intersection override context |
| `DrainageModel` | low-point handoff candidates and optional inlet/flow-route starter rows |
| `StructureModel` | optional inlet/outlet/culvert refs for drainage-oriented presets |

Preset data should not directly create final corridor meshes.

## 5. Geometry Considerations To Encode

### 5.1 Design Vehicle Intent

Each preset should store a design-vehicle hint.

First supported values:

- `passenger_car`
- `single_unit_truck`
- `bus_or_small_truck`

The first slice does not need full swept-path analysis.

It should use the design-vehicle hint to choose default curb-return radius, entry radius, and warning thresholds.

### 5.2 Lane And Edge Network

Each preset should create explicit edge families:

- centerline
- lane edge
- pavement edge
- shoulder edge
- gutter or ditch edge
- curb-return edge
- daylight hinge edge
- exclusion boundary edge

Build Parametric should use these edges as source-derived topology.

### 5.3 Vertical Control

Each preset should define:

- primary profile tie-in station
- secondary profile tie-in station
- intersection target elevation policy
- allowed maximum z adjustment
- approach profile transition length

Default policy:

- T and Cross: `blend_primary_side`
- Roundabout: `flatten_circulatory_ring`

### 5.4 Crossfall And Superelevation

Normal approach crossfall should remain in Superelevation.

Intersection policy should override only inside the control area.

Preset options:

| Policy | Meaning |
| --- | --- |
| `keep_primary_crown` | preserve primary road crown through the intersection |
| `flatten_intersection` | flatten the central control area |
| `blend_primary_side` | blend primary and side-road crossfalls |
| `roundabout_radial_crossfall` | slope circulatory roadway toward inside or outside drainage |

### 5.5 Surface Priority

Every preset must define surface priority.

Recommended priority:

1. explicit intersection pavement zone
2. curb-return zone
3. primary/secondary ordinary design surface outside control area
4. shoulder/ditch transition zone
5. slope-face/daylight zone
6. existing ground

If two generated surfaces overlap, the higher-priority owner wins.

Clipping should use source/result boundary edges, not display mesh color or object label.

### 5.6 Drainage

Each preset should define drainage intent, even if hydraulic analysis is deferred.

Required rows:

- low-point search zone
- gutter or ditch edge family
- inlet candidate side
- outlet hint
- warning if no Drainage Element covers the intersection low point

Roundabout presets should support outside-gutter and central-island drainage options.

### 5.7 Topology QA

Each preset should define expected topology checks:

- edge loops are closed
- curb-return arcs connect to both approach edges
- supplemental Applied Sections exist at control boundaries and contact points
- intersection surface zones do not self-intersect
- ordinary corridor design and slope surfaces do not intrude into higher-priority intersection zones
- gap and overlap counts are reported
- triangle quality is above the configured threshold

## 6. UX Plan

### 6.1 Separate Intersection Presets Panel

Keep the existing `Intersections` panel as-is.

The current panel remains the source-model editor and review surface for:

- using existing Alignments
- reviewing detected participating Alignments
- applying or editing an accepted `IntersectionModel`
- checking source-level intersection rows and control Regions

Create a separate panel for preset-driven starter design.

Recommended command name:

- `Intersection Presets`

Recommended panel title:

- `Intersection Presets`

The separate panel should provide preset selector entries:

- `T Intersection - Basic`
- `Cross Intersection - Basic`
- `Roundabout - Single Lane`

For each preset, show a short capability note:

- source objects created
- number of legs
- curb-return or roundabout edge count
- grading policy
- drainage handoff status

The preset panel creates editable source objects and policy rows.

It should not replace the existing Intersections panel and should not directly create final corridor geometry.

### 6.2 Preset Options

Expose compact options below the preset selector:

- Design vehicle
- Curb-return radius or roundabout diameter
- Control length
- Default grading policy
- Drainage mode

Use defaults first.

Advanced values can be edited later in source panels.

### 6.3 Preview

Preview should show:

- participating alignments
- control area
- edge network
- curb-return or circulatory edges
- low-point hints
- surface priority boundaries

Preview should not create final corridor geometry.

### 6.4 Build Parametric Review

Guided Review should report:

- intersection kind
- leg count
- edge-network row count
- curb-return or roundabout edge count
- supplemental Applied Sections count
- surface priority conflicts
- gap/overlap count
- drainage low-point coverage

## 7. Implementation Phases

### Phase IP1: Document And Contract Alignment

Status: Done

Work:

- added this plan to `docsV1/README.md`
- aligned preset names with `IntersectionModel` kinds
- kept the existing `Intersections` panel type list unchanged
- added Roundabout as an `Intersection Presets` source-builder kind only for this slice
- kept advanced roundabout operation as a documented non-goal

Acceptance:

- docs describe T, Cross, and Roundabout preset scope clearly
- unsupported roundabout advanced behavior is explicit

### Phase IP2: Preset Data Source Builders

Status: First code slice done

Work:

- added a separate `Intersection Presets` command and task panel
- keep the existing `Intersections` command and panel behavior unchanged
- added preset source builders for T, Cross, and Roundabout starter alignments
- generate Alignment/Profile/Stationing/Region rows through the existing starter-source service
- generated `IntersectionModel` rows and first-slice policy rows are now created from preset control Regions
- Superelevation handoff source and Drainage low-point handoff source are now created as preset-owned source objects
- full hydraulic Drainage design rows remain planned follow-up work

Acceptance:

- opening the existing `Intersections` panel still follows the current workflow
- opening `Intersection Presets` shows preset-driven starter options
- selecting a preset creates editable source objects only
- no final corridor mesh is created by preset load

First-slice implementation note:

- `Intersection Presets` is placed after `Intersections` and before `Structures` in the Assembly & Regions workflow.
- The panel exposes T, Cross, and Roundabout starter presets.
- The panel now has two source modes:
  - `Create From Preset`
  - `Use Existing Alignments`
- `Preview Edge Network` is available in both source modes.
- In `Create From Preset`, the preview uses the preset-created Alignment and control Region source rows, so users run `Create Sources` before previewing.
- `Use Existing Alignments` lets users select Primary and Secondary Alignment refs, run Auto Detect, preview the edge network, and apply an `IntersectionModel` from the same preset panel.
- The existing `Intersections` panel remains available as the source-model editor and review surface.
- Roundabout is not yet promoted into the existing `Intersections` editor's final `IntersectionModel` kind workflow.
- The first code slice creates source objects and a stored `IntersectionModel` contract only.
- The stored model includes leg, control-area, arm, edge, curb-return, grading, and drainage-policy rows.
- Presets also create separated `Intersection Preset Superelevation` and `Intersection Preset Drainage` source objects.
- Superelevation preset rows intentionally avoid hard-coded crossfall controls; they store constraints and require Auto Calculate review.
- Drainage preset rows create low-point/outlet handoff intent only; users should replace them with real inlet/outfall Structures during drainage design.
- Final surface-zone generation is intentionally left to later phases.

### Phase IP3: Edge Network Evaluation

Status: First code slice done

Work:

- expand `IntersectionEvaluationService` to emit typed edge families for each preset
- keep curb-return contact stations for T and Cross
- add first-slice Roundabout edge-family rows:
  - `central_island_edge`
  - `circulatory_outer_edge`
  - `entry_exit_edge`

Acceptance:

- Preview Edge Network has stable edge roles and source refs
- Build Sections can read contact station refs for supplemental section rows

First-slice implementation note:

- T and Cross continue to use `leg_edge` and `curb_return` families.
- Roundabout presets now emit `roundabout` edge-family rows for source review.
- Roundabout edge rows are marked as first-slice source contracts, not final roundabout geometry.

### Phase IP4: Surface Zone And Priority

Status: First code slice done

Work:

- produce zone rows for pavement, curb-return, central patch, transition, and slope-face zones
- apply surface priority before ordinary corridor surfaces are merged
- report unresolved overlaps instead of silently drawing both surfaces
- add first-slice roundabout zone contracts for central island, circulatory pavement, and entry/exit pavement

Acceptance:

- T preset does not leave ordinary slope-face triangles inside the intersection pavement zone
- Cross preset clips all four approach conflicts consistently
- Roundabout preset builds separate circulatory and approach zones

First-slice implementation note:

- `IntersectionSurfaceZoneRow` now carries `surface_priority`.
- Priority is source/result contract data only; final mesh clipping still remains a later build phase.
- T and Cross surface zones now expose ordered priority for central pavement, curb-return, ordinary pavement, and exterior slope-face zones.
- Roundabout presets now expose separate source-zone contracts for:
  - `roundabout_central_island`
  - `roundabout_circulatory_pavement`
  - `roundabout_entry_exit_pavement`
- Roundabout surface zones are first-slice contracts and are not yet final roundabout triangulation.

### Phase IP5: Grading And Crossfall

Status: First code slice done

Work:

- apply intersection grading policy inside the control area
- keep normal Superelevation outside the control area
- expose grading policy and max z adjustment in Guided Review
- create grading/crossfall context rows from source grading policy and surface-zone priority
- pass user-selected preset grading policy into the created `IntersectionModel`

Acceptance:

- Cross Section Viewer shows intersection grading context
- Build Parametric diagnostics identify the active grading policy

First-slice implementation note:

- `IntersectionGradingContextResult` now records grading/crossfall review contracts per intersection surface zone.
- The context rows distinguish `intersection_override` from `normal_superelevation`.
- Central pavement, curb-return, ordinary intersection pavement, and roundabout zones use the active intersection grading policy.
- Exterior slope-face rows keep the normal Superelevation/Assembly crossfall context.
- Preset-created `IntersectionModel` grading policy rows now retain the panel's selected grading policy.
- Preset-created Superelevation handoff constraints now record the selected grading policy as review context.
- This slice does not generate final graded intersection meshes; it exposes the source/result contract that later build steps should consume.

### Phase IP6: Drainage Handoff

Status: First code slice done

Work:

- compute low-point candidates per preset
- add optional inlet candidate starter rows
- show missing coverage diagnostics when Drainage Elements are absent
- attach drainage mode and grading context refs to drainage hint rows
- add outlet handoff hints for outside-gutter and central-island modes

Acceptance:

- Guided Review separates roadside drainage from intersection drainage
- Roundabout preset reports the chosen drainage mode

First-slice implementation note:

- `IntersectionDrainageHintRow` now records:
  - `drainage_mode`
  - `grading_context_ref`
  - `crossfall_context`
- Low-point hints are generated from central pavement and roundabout circulatory zones.
- Inlet recommendations are generated from curb-return, roundabout entry/exit, and slope-face zones.
- Outside-gutter and central-island drainage modes now create outlet handoff hints.
- Missing explicit Drainage Element coverage is reported as review warning data.
- This slice does not create final inlet, outlet, pipe, or hydraulic sizing geometry automatically.

### Phase IP7: Manual QA

Status: First code slice done

Work:

- create manual QA steps for T, Cross, and Roundabout presets
- include screenshot checkpoints for edge network, Applied Sections, surfaces, drainage, and topology diagnostics
- update the user-facing wiki to describe the active `Intersection Presets` panel
- document current Roundabout preset limitations clearly

Acceptance:

- each preset has a repeatable smoke test
- known limitations are visible in QA notes

First-slice implementation note:

- `V1_INTERSECTION_MANUAL_QA.md` now includes a shared `Intersection Presets` smoke QA flow.
- T and Cross presets reuse the existing detailed intersection QA sections.
- Roundabout has a dedicated preset QA section for:
  - edge-network rows
  - roundabout surface-zone rows
  - radial grading context
  - outside-gutter drainage handoff
  - known first-slice limitations
- `wiki/Intersections.md` now describes `Intersection Presets` as an active workflow, not a future feature.

## 8. Non-Goals

This plan does not include:

- signal timing
- full swept-path simulation
- automatic legal design standard compliance
- final roadway marking and signing
- roundabout capacity analysis
- hydraulic pipe sizing
- automatic watertight solid generation for every intersection zone

These can be added after the source and surface topology contracts are stable.

## 9. Immediate Next Step

Run the Phase IP7 manual QA checklist in a real FreeCAD document.

After manual QA, record pass/warning/fail results and decide whether the next slice should focus on preset UI polish, Cross preset geometry review, or Roundabout geometry expansion.

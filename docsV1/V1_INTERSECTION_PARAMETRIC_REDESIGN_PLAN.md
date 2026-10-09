# V1 Intersection Parametric Redesign Plan

Date: 2026-10-08
Branch: `ganada_0902` (starting head `f8543bd`)
Status: **active**. This is the single specification for Intersection work. Every other
`V1_INTERSECTION_*_PLAN.md`, `V1_CROSS_INTERSECTION_*_PLAN.md` and `V1_ROUNDABOUT_*_PLAN.md` is a
historical proposal (see `V1_SUPPORTED_DOMAIN_STATUS.md`, Document Classification).

## 1. Purpose

Rebuild intersection generation so that an intersection is produced by **passing data**: a
small parametric spec plus the evaluated upstream results go in, a deterministic geometry
result comes out.

```text
IntersectionGeometryResult = build_intersection_geometry(IntersectionSpec, RoadContext)
```

- Same inputs, same result. No document, GUI or review state takes part in the geometry.
- Any input change makes the result stale; the result is rebuilt, never repaired by hand.
- T, Cross and Roundabout are parameter sets of one kernel, not separate code paths.

## 2. Hard constraint: ordinary roads must not change

The redesign must not alter any behaviour of a document without an intersection, and must not
alter the current intersection output until the switch phase (R5) is explicitly taken.

- New code lives in new modules. Existing intersection services are not edited during R1 to R4.
- The only hook into Build Parametric is a shadow comparison inside
  `create_corridor_intersection_surface_preview`, which returns early for a document without an
  `IntersectionModel`. It writes three diagnostic properties and nothing else.
- A failure inside the shadow comparison is caught and recorded as `IntersectionKernelShadowStatus =
  error` with its message. The documented reason for the catch: a shadow computation must never
  block or change the production build it observes.
- Every phase runs the full validation gate of `SESSION_HANDOFF_1009.md` §7 (contract suite, intersection
  command chunk, three smoke runners) before it is closed.

## 3. Decisions (taken 2026-10-08, not open)

| # | Question | Decision |
| --- | --- | --- |
| D1 | Owner of the pavement edge | **Applied Sections** (`surface_left_width` / `surface_right_width`, produced from the Assembly). The kernel reads it through `RoadContext`; the arm policy's lane count, lane width, shoulder and median no longer define geometry. |
| D2 | Lane connection, edge policy, surface zone rows | **Removed** from the source at the switch, **without** a legacy migration or preserved copy. |
| D3 | How a T is recognised | Automatic: a road whose start or end lies at the anchor contributes one leg. Otherwise `kind="t"` closes the secondary road's shorter side. |
| D4 | Design standard for radii | **Constants** in the kernel (§5.3). No Project standard table for now. |
| D5 | Migration style | **Shadow mode**: the new kernel runs beside the current pipeline and only reports differences until the switch. |
| D6 | Documentation | This plan is the single intersection specification; the others are historical. |

## 4. Problems this redesign removes

Measured on `f8543bd`.

| # | Problem | Evidence |
| --- | --- | --- |
| P1 | The source is expanded data, not parameters. The preset copies defaults into 12 row families that must then be reviewed and accepted. | T 18, Cross 30, Roundabout 24 review rows, all `draft` at creation |
| P2 | The pavement edge has two owners. | arm policy 4.5 m vs Applied Sections 5.0 m (1.05 m gap); constants `9.0 / 4.5 / 6.0` in `_intersection_edge_lateral_offset` |
| P3 | Legs are straight rays from one tangent at the anchor, on a frame derived from role names. | `_LEG_GRAPH_ROLE_ANGLE_DEG`, `_intersection_fixed_alignment_axis` |
| P4 | Role strings decide geometry. | `"primary" in role`, `before/after` substring tests, span-sign inference |
| P5 | Ten-plus intermediate result families, each re-evaluated by its consumers; results scattered over string properties. | 32 `models/result/intersection_*` modules; 341 distinct `Intersection*` preview properties |
| P6 | Engineering logic in commands. | 349 intersection functions in `cmd_build_corridor.py` (20,389 lines) |
| P7 | Review state inside the geometry path. | 70 `approval_status` references in `intersection_evaluation_service.py` |
| P8 | Roundabout is a separate world. | `roundabout_surface_builder_service.py` 1,158 lines, `roundabout_tin_clip_service.py` 882 lines |
| P9 | Open defects are symptoms of stitching partial graphs: unfilled curb return slope faces (Cross 0 of 32), 160 skinny constraint triangles, about 49 m of missing side slope. | `SESSION_HANDOFF_1009.md` §5 |

## 5. Interfaces

### 5.1 Boundaries

```text
(source)                 (evaluation, pure)                         (result)
IntersectionSpec ──┐
                   ├─> resolve_intersection() ─> ResolvedIntersection ─> build_intersection_geometry()
RoadContext ───────┘        (value origins)                                    │
     ▲                                                                         ▼
     │ built by a builder service from AlignmentModel + AppliedSectionSet     IntersectionGeometryResult
     │ (the command only fetches those models from the document)              (versioned, fingerprinted)
```

| Module | Layer | Content |
| --- | --- | --- |
| `v1/models/source/intersection_spec.py` | source | `IntersectionSpec`, `AnchorSpec`, `LegOverride`, `CornerOverride`, `RoundaboutSpec` |
| `v1/models/result/intersection_geometry.py` | result | `IntersectionGeometryResult`, `LegGeometry`, `CornerGeometry`, `KernelDiagnostic`, `ResolvedValue` |
| `v1/services/evaluation/intersection_kernel/road_context.py` | evaluation | `RoadContext` protocol, `PolylineRoad`, `PolylineRoadContext` |
| `v1/services/evaluation/intersection_kernel/resolve.py` | evaluation | `resolve_intersection()` |
| `v1/services/evaluation/intersection_kernel/planar.py` | evaluation | K1 to K3 and the planar part of K7 |
| `v1/services/evaluation/intersection_kernel/kernel.py` | evaluation | `build_intersection_geometry()`, fingerprint |
| `v1/services/builders/intersection_kernel_context_service.py` | builder | `RoadContext` from `AlignmentModel` and `AppliedSectionSet`; `spec_from_intersection_model()` for shadow mode |
| `v1/services/evaluation/intersection_kernel_shadow_service.py` | evaluation | comparison of the kernel boundary with the current patch boundary |

The kernel imports nothing from FreeCAD, Qt, `objects`, `commands` or `ui`.

Units: every station, offset, radius and coordinate in the kernel is in **metres**, in Project local
coordinates, the units `AlignmentModel.geometry_sequence` and `AppliedSection` already carry.

### 5.2 Source: `IntersectionSpec`

```python
@dataclass(frozen=True)
class IntersectionSpec:
    intersection_id: str
    kind: str                                  # "t" | "cross" | "roundabout"
    road_refs: tuple[str, ...]                 # Alignment ids; the first is the primary road
    anchor: AnchorSpec = AnchorSpec()
    corner_radius_m: float | None = None       # None: kind constant (§5.3)
    grading_mode: str | None = None            # None: kind constant
    leg_overrides: tuple[LegOverride, ...] = ()
    corner_overrides: tuple[CornerOverride, ...] = ()
    roundabout: RoundaboutSpec | None = None
    schema_version: int = 1

@dataclass(frozen=True)
class AnchorSpec:
    method: str = "detected"                   # "detected" | "manual"
    station_by_road: tuple[tuple[str, float], ...] = ()   # manual stations
    search_hint_xy: tuple[float, float] | None = None     # which crossing when there are several

@dataclass(frozen=True)
class LegOverride:
    road_ref: str
    side: str                                  # "ahead" | "back", along increasing station
    enabled: bool = True

@dataclass(frozen=True)
class CornerOverride:
    corner_key: str                            # "<from leg id>|<to leg id>" in CCW order
    radius_m: float | None = None
    treatment: str | None = None               # "fillet" | "none"

@dataclass(frozen=True)
class RoundaboutSpec:
    inscribed_radius_m: float
    circulatory_width_m: float
    apron_width_m: float = 0.0
    entry_radius_m: float | None = None
    exit_radius_m: float | None = None
    circulation: str = "ccw"
```

- Legs are not stored. They are derived as `road_refs x {ahead, back}`; only overrides are stored.
- Edge, arm, lane connection and surface zone data do not exist in the spec (D1, D2).
- Control length is not an input: the leg mouth station follows from the corner geometry.
- No `approval_status`: review state, if needed, belongs to a UI review record.

### 5.3 Constants (D4)

| Constant | Value | Origin |
| --- | --- | --- |
| `T_CORNER_RADIUS_M` | 12.0 | current preset default |
| `CROSS_CORNER_RADIUS_M` | 10.0 | current preset default |
| `ROUNDABOUT_INSCRIBED_RADIUS_M` | 18.0 | current preset default |
| `DEFAULT_GRADING_MODE` | `flatten_intersection` | current preset default |
| `MOUTH_CLEARANCE_M` | 0.0 | the mouth is the curb return tangent point |
| `ARC_MAX_STEP_DEG` | 5.0 | chord error `R (1 - cos 2.5 deg)` = 0.1 % of R, 12 mm at R = 12 m |
| `EDGE_SAMPLE_STEP_M` | 1.0 | captures width changes between Applied Section stations; alignment vertices are always kept |
| `ROUNDABOUT_CIRCULATORY_WIDTH_RATIO` | 0.55 of the inscribed radius | current preset (island 0.45) |
| `ROUNDABOUT_APRON_WIDTH_RATIO` | 0.15 of the circulatory width | current preset |
| `ROUNDABOUT_ENTRY_RADIUS_RATIO`, `..._EXIT_...` | 0.5 and 0.6 of the ring's outer edge radius | R6, see below |
| `ROUNDABOUT_RING_CROSSFALL` | 0.02, falling outward | the current `roundabout_radial_crossfall` intent |

The flare radii are the one place R6 departs from "the current preset's value" (D4): the preset has
no flare (a square corner where the approach edge meets the ring, which leaves no room for a side
slope there). A fixed radius cannot suit every ring, since a flare of radius R meets a ring of outer
radius r at asin((w + R) / (r + R)) off the approach: 15 m and 20 m flares overlap on the starter's
13 m ring. A fraction of the ring keeps them apart (36 and 38 of the 90 degrees between the
starter's approaches). A spec or per-approach value replaces them.

### 5.4 `RoadContext`

```python
class RoadContext(Protocol):
    def road_refs(self) -> tuple[str, ...]: ...
    def station_range(self, road_ref) -> tuple[float, float]: ...
    def point_xy(self, road_ref, station) -> tuple[float, float]: ...
    def tangent_xy(self, road_ref, station) -> tuple[float, float]: ...     # unit, increasing station
    def crossings(self, road_a, road_b) -> tuple[Crossing, ...]: ...
    def pavement_half_width(self, road_ref, station, side) -> float | None: ...   # side "left" | "right"
    def finished_grade_z(self, road_ref, station) -> float | None: ...
    def vertex_stations(self, road_ref, start, end) -> tuple[float, ...]: ...
    def fingerprint_rows(self, road_ref) -> tuple[str, ...]: ...
    def surface_profile(self, road_ref, station) -> SurfaceProfile | None: ...   # R5
```

`SurfaceProfile` is the finished grade cut across the road at a station: the `fg_surface` points
`(lateral offset, z)` from right to left, and per side the daylight point (`daylight_marker`, else
the outermost `side_slope_surface` point). Between two Applied Sections it is linear point by point,
which is what the corridor surface between two sections is; when their points do not pair up the
nearer section is returned with `exact = False` (diagnostic `mouth_section_points_do_not_pair`).

`PolylineRoadContext` implements it from plain data: one `PolylineRoad` per road (stations and XY
of the alignment's sampled geometry; station rows of the pavement half width left and right; FG
centreline elevation rows). Tests build it analytically; the builder service builds it from
`AlignmentModel` and `AppliedSectionSet` (sections grouped by `alignment_id`, half width from
`surface_left_width` / `surface_right_width`, elevation from `frame.z`). A road with no Applied
Section returns `None` for the half width and the kernel blocks with
`pavement_edge_owner_missing` (D1: there is no fallback width).

### 5.5 Resolve

`resolve_intersection(spec, context) -> ResolvedIntersection`

1. **Anchor**: manual stations, or the crossing of the first two roads nearest to the search hint.
2. **Legs**: for each road and each side, a leg exists when the road extends beyond the anchor by
   more than `LEG_MIN_LENGTH_M` (0.5 m, a station-noise guard). Leg id `"<road_ref>:<side>"`.
   Bearing = road tangent at the anchor, negated for `back`.
3. **T rule (D3)**: if `kind == "t"` and four legs exist, the secondary road's side with less
   remaining length is closed (`origin = "derived:t_rule"`). A leg override wins over the rule.
4. **Order**: legs sorted by bearing, counter-clockwise. No role names are used.
5. **Corners**: between each leg and its CCW successor. Two legs of the same road meet with
   treatment `none` (the road edge runs straight through); otherwise `fillet`. Radius from a
   corner override, else the spec, else the kind constant.
6. Every resolved value carries its origin: `spec`, `override`, `constant`, or `derived:<rule>`.

### 5.6 Kernel stages

| # | Stage | In -> out | Replaces |
| --- | --- | --- | --- |
| K1 | corner fillet | two legs' real pavement edge curves -> centre, two tangent points with stations, arc | curb return endpoints, fillet, arc |
| K2 | leg mouth | outermost tangent station of a leg + clearance -> mouth station and mouth section points | control length, edge network |
| K3 | boundary | mouth sections + fillet arcs + pass-through edges -> one closed CCW polygon | zones, loops, segments, shared graph, patch boundary |
| K4 | vertical | Applied Section heights at the mouths + grading mode -> fixed breaklines | tie-in edge, patch grading |
| K5 | patch surface | boundary + breaklines -> constrained triangulation | constraint build, triangulation, TIN assembly |
| K6 | side slope | fillet offsets + mouth daylight points -> slope faces | slope face cell, boundary, tie slope |
| K7 | handoff | mouth stations -> clip spans, supplemental stations, drainage candidates | corridor clipping, supplemental stations, hints |

**K1, fillet on real edges.** For a corner from leg A to its CCW successor B, the fillet touches
A's edge on its left (outward-looking) side and B's edge on its right side. Its centre lies at
distance `w + R` from both centrelines, so it is the first crossing, outward from the anchor, of
the two offset polylines `C(s) + n(s) (w(s) + R)`. Each tangent point is the edge point at the
station where the centre was found. Sampling follows the alignment vertices plus
`EDGE_SAMPLE_STEP_M`; on straight roads the result is exact. Failure diagnostics:
`corner_fillet_no_solution` (radius too large for the legs), `pavement_edge_owner_missing`.

**K2, mouth.** Mouth station of a leg = the outermost tangent station among its fillet corners,
plus `MOUTH_CLEARANCE_M`. A leg with no fillet corner (impossible for T and Cross) blocks.

**K3, boundary.** Walk the legs CCW. For each leg: its right edge from the inner station to the
mouth, across the mouth, its left edge back to the inner station, then the corner to the next
leg: the fillet arc, or nothing for a `none` corner (the two edge pieces meet at the anchor
station on the same edge line). The inner station is the tangent station of the fillet corner on
that side, or the anchor station for a `none` corner. Checks: closed, positive CCW area, no self
crossing (`boundary_self_crossing` blocks).

**K3 heights (R5).** A boundary vertex on a pavement edge takes the edge height of the road's
surface profile at its station; the mouth is crossed through every `fg_surface` point of the cut
there. The boundary is therefore the corridor surface's own edge, point for point.

**K4, vertical (R5).** The boundary is never graded. One crown breakline per leg runs from the
road's crown at the mouth to the anchor:

| grading mode | primary road crown | other crowns | anchor height |
| --- | --- | --- | --- |
| `blend_primary_side`, `keep_primary_crown`, `use_normal_superelevation` | its own profile | straight from the mouth crown | primary profile at the anchor |
| `flatten_intersection` | straight from the mouth crown | straight from the mouth crown | mean of the mouth crowns |

The three primary-crown modes give the same surface: the current pipeline told them apart only by
moving boundary heights (a plane fit, an average), which tore the patch from the corridor at the
mouths. An unknown mode falls back to `blend_primary_side` (`grading_mode_unknown`).

**K5, patch (R5).** Constrained Delaunay triangulation of the boundary with the crown lines as
breaklines (`intersection_kernel/cdt.py`: Bowyer-Watson, constraint recovery by flips, outside
triangles dropped, Delaunay flips on the free edges). Coordinates are centred and scaled to about
1 first, so the fixed tolerances are relative and world coordinates lose no precision. Checks: the
triangles cover the boundary area to 1e-6 relative (`patch_area_mismatch`), a crown that cannot be
recovered (`patch_breakline_not_recovered`). Quality rows use the current review's skinny threshold,
0.08.

**K6, side slope (R5).** The boundary is split at the mouths into runs, one per pair of
neighbouring legs. Each run gets a strip from the boundary to an outer toe line:

- on a pavement edge: the road's daylight point at that station, so at a mouth the strip ends on
  the corridor's own side slope line;
- on a curb return: the two joined roads' side slopes (width and fall) blended along the arc, laid
  toward the fillet centre; where wider than the distance to the centre it stops there
  (`corner_side_slope_wider_than_radius`, partial).

The corner daylight is the blend of the legs' daylight, not a fresh intersection with the existing
ground; that refinement is not in R5.

**K7 (planar part).** Clip span per road: from the `back` mouth to the `ahead` mouth (the anchor
station where a side has no leg). Supplemental stations: the mouth stations.

**Roundabout (R6).** The same stages, with the ring as K1's partner. The ring is a circle about the
anchor: its paved outer edge is the inscribed radius plus the outer apron, its central island the
inscribed radius less the circulatory width. Between two neighbouring approaches the corner (treatment
`ring`) runs from the first approach's flare onto the ring, counter-clockwise round the ring's outer
edge, and off it by the second approach's flare. Each flare is the circle tangent to the approach's
real pavement edge and outside tangent to the ring (found on the edge offset by R, at r + R from the
centre); radius 0 is a square corner. Circulating counter-clockwise a driver enters on the approach's
left side looking outward, so that side takes the entry radius and the right side the exit radius;
`circulation = "cw"` swaps them. The central island is a hole in the boundary.

- K2: the mouth is the outer of the approach's two flare tangent points.
- K4: whatever the grading mode, the circulatory roadway falls outward from the island's edge (the
  primary profile at the anchor) at `ROUNDABOUT_RING_CROSSFALL`. Each approach crown runs straight
  from its mouth to where the road crosses the ring's outer edge; across each approach's throat the
  outer edge is a breakline (`ring_throat`), sampled evenly either side of the crown's end.
- K6: round a flare the strip runs toward the flare's centre as at a curb return; beyond the ring it
  runs straight out from the roundabout centre.

Diagnostics: `roundabout_flares_overlap` (two flares pass each other on the ring),
`roundabout_flare_no_solution`, `roundabout_approach_wider_than_ring`,
`roundabout_island_not_positive`, `roundabout_island_outside_boundary`; all block.

### 5.7 Result

```python
@dataclass(frozen=True)
class IntersectionGeometryResult:
    schema_version: int
    intersection_id: str
    kind: str
    input_fingerprint: str        # sha1 of the spec and the context's fingerprint rows
    status: str                   # ready | partial | blocked | not_implemented
    anchor_xy: tuple[float, float]
    anchor_station_by_road: tuple[tuple[str, float], ...]
    legs: tuple[LegGeometry, ...]
    corners: tuple[CornerGeometry, ...]
    boundary_xyz: tuple[tuple[float, float, float], ...]   # closed CCW, first point not repeated
    boundary_area_m2: float
    clip_spans: tuple[tuple[str, float, float], ...]
    supplemental_stations: tuple[tuple[str, float], ...]
    resolved_values: tuple[ResolvedValue, ...]
    diagnostics: tuple[KernelDiagnostic, ...]
    patch_vertices_xyz / patch_triangles      # K5
    slope_vertices_xyz / slope_triangles      # K6
    breaklines: tuple[(role, subject, points)] # crown, boundary, slope_toe
    quality_rows: tuple[(name, value)]        # triangle counts, minimum quality, skinny counts

@dataclass(frozen=True)
class KernelDiagnostic:
    code: str
    severity: str                 # error | warning | info
    subject: str                  # leg id, corner key or road ref
    station: float | None
    inspect: str                  # what input to look at
    effect: str                   # blocked | partial | fallback | none
```

### 5.8 Consumers after the switch

| Consumer | Reads | Stops doing |
| --- | --- | --- |
| Applied Sections | supplemental stations, clip spans | synthesising intersection tie-in sections |
| Corridor and Surface | clip spans, patch TIN, slope faces, breaklines | re-evaluating the chain, guessing boundaries |
| Drainage review | drainage candidates | intersection-local low point rules |
| Viewers and export | the whole result, read only | reverse-authoring source |
| Build Parametric | one `build_intersection_geometry()` call | the 349 intersection functions |

Order with Applied Sections: the mouth stations depend only on plan geometry and the pavement
widths, never on heights, so `Applied Sections -> kernel -> Applied Sections (mouth stations
only) -> Corridor` converges in two passes.

## 6. Shadow mode (D5)

`intersection_kernel_shadow_comparison()` (builder) runs the kernel on the document's Alignments
and Applied Sections and `IntersectionKernelShadowService.compare()` measures it against two
outputs of the current pipeline:

| Target | Current output | Measure |
| --- | --- | --- |
| fillets | curb return arcs of the boundary segment result (drawn from the Applied Sections' tie-in edges) | largest Hausdorff distance between each kernel fillet and the build's arc at that corner |
| envelope | `outer_intersection_boundary` loop of the evaluation chain (straight sides from the arm policy) | Hausdorff distance between the closed polygons |

The central patch boundary (`IntersectionPatchBoundaryResult`) is not a target: it covers only the
core square (130 m2 for the starter T), not the curb return envelope the kernel builds.

- `status`: `agree` (every compared target within `SHADOW_AGREE_TOLERANCE_M` = 0.05 m, a review
  threshold well above the micrometre noise of the sampled alignments), `differ`, `skipped`
  (roundabout, or no target), `blocked` (kernel blocked), `error`.
- rows: kernel status and fingerprint, legs and mouth stations, corners, every resolved value with
  its origin, clip spans, kernel diagnostics, both deviations and areas; since R5 also `patch|`
  (kernel triangles, minimum quality and skinny count next to the current patch's
  `PatchTriangleMinQuality` / `PatchTriangleSkinnyCount`), `slope|` (kernel strip figures) and
  `clip_compare|` (kernel clip span next to the current control area ranges). These are measured,
  not judged: the status still comes from the fillet and envelope targets.

A roundabout is compared ring for ring (R6): the central island against the current
`roundabout_central_island_boundary` loop and the ring's paved outer edge against
`roundabout_outer_ownership_boundary`, each as the largest distance of the current loop's vertices
from the kernel's circle, so the polygons' chord sag is not counted. The worst of the two goes into
`IntersectionKernelShadowEnvelopeDeviationM`; the fillet deviation is -1. The approaches have no
current counterpart (the current connectors are fixed-width rectangles that build no surface), so
their widths are recorded as `approach|` rows.

Build Parametric writes `IntersectionKernelShadowStatus`, `IntersectionKernelShadowFilletDeviationM`,
`IntersectionKernelShadowEnvelopeDeviationM` (-1 = not compared) and `IntersectionKernelShadowRows`
to `V1CorridorIntersectionSurfacePreview`. Nothing reads them back. A `differ` is expected where the
current pipeline is known to be wrong; each one is explained in §8 before the switch.

## 7. Phases

| Phase | Content | Done when |
| --- | --- | --- |
| R0 | this plan; classification of the older plans | committed |
| R1 | spec, result, `RoadContext`, `PolylineRoadContext`, `resolve_intersection` | analytic tests for T, Cross, skewed T, side-road T rule |
| R2 | K1 to K3 and K7 planar on curved and straight roads | analytic tests: straight T and Cross exact, 60 degree skew, curved primary road, radius too large |
| R3 | builder context service from `AlignmentModel` + `AppliedSectionSet`; `spec_from_intersection_model` | starter T, Cross, turned T resolve with the Applied Sections' 5 m |
| R4 | shadow comparison in Build Parametric | starter T and Cross report their difference; full gate green |
| R5 | K4 to K6 (heights, patch TIN, side slope) in the kernel, still shadow | unfilled arcs, skinny triangles and the clip span measured on the kernel output (done, §8) |
| R6 | roundabout in the kernel | roundabout shadow `agree` or explained (done, §8) |
| R7a | the kernel engine, selectable per intersection (`GeometryEngine` = `kernel`), default `legacy`: mouth sections in Applied Sections, corridor clipped by station span, kernel patch and side slope as the intersection surfaces | full gate; the user's GUI comparison of both engines (done, §8, GUI pending) |
| R7b | the spec becomes the stored source (`SpecJson` on the Intersection object) and the panel edits it | full gate and GUI (done, §8, GUI pending) |
| R7c-1 | the kernel is the only engine: the legacy build in Build Parametric and Applied Sections, the code only it reached, and the tests of it are deleted | full gate and GUI (done, §8) |
| R7c-2 | the review surfaces still reading the legacy evaluation chain (the Build Parametric Intersections, Breakline Audit and Drainage tabs) read the kernel result; the chain and the services only it feeds are deleted; the kernel's drainage candidates (K7) feed the drainage review | full gate and GUI (done, §8, GUI: tab and highlight checked) |
| R7c-3 | the lane connection and edge policy rows (D2) leave the source, and the panel's row review gives way to the spec group | full gate and GUI manual QA (done, §8, GUI: Intersections tab ready) |

R1 to R7c-3 are implemented. R7 is split because the switch and the deletion cannot be one step:
the legacy previews carry 341 metadata properties that the review rows, the 78 command tests and
the regression smokes read, so replacing them breaks all of that at once. R7a puts the kernel
engine next to the legacy one, selectable per intersection, so the two can be compared in the GUI on
the same document before R7c deletes the legacy one.

## 8. Shadow measurements

### R1 to R4, 2026-10-08

Starter presets after `Accept Reviewed Rows`, built headless (`test_intersection_kernel_shadow.py`).

| Document | Kernel | Mouth stations | Fillets | Envelope | Status |
| --- | --- | --- | --- | --- | --- |
| T | ready, 3 legs (side road ends at the anchor: no rule needed), 2 fillets R 12 | main 103 / 137, side 83 | 0.000 m | 0.707 m | differ |
| Cross | ready, 4 legs, 4 fillets R 10 | 105 / 135 on both roads | 0.000 m | 0.707 m | differ |
| T turned 30 degrees | ready | as the T | 0.000 m | 0.717 m | differ |
| Roundabout | not_implemented | - | - | - | skipped |

Explanation of every `differ`: the envelope loop of the evaluation chain puts the pavement edge
4.5 m from the centreline (arm policy) where the Applied Sections put it 5.0 m (P2). Its sides are
therefore 0.5 m inside and its mouths, at 4.5 m + R, 0.5 m short, so its mouth corners are off by
0.5 m in both directions, 0.5 sqrt(2) = 0.707 m. The turned T adds up to 11 mm of chord sag where
the two arcs' sample points do not line up. The kernel's fillets coincide with the arcs the build
already draws from the Applied Sections. Under D1 the kernel is right and the loop is not.

Kernel figures on analytic roads (`test_intersection_kernel.py`): the straight T and Cross reproduce
the exact paved areas within the arc chord error; a 60 degree skewed Cross has every fillet centre
exactly R + w from both centrelines; on a 300 m curve the tangent point is on the real edge within
the alignment's own 2.8 mm chord sag.

Cost: the shadow adds 0.04 s to a 2.9 s T build and 0.05 s to a 3.2 s Cross build, of which the
kernel is 0.014 s and 0.020 s; the rest is re-evaluating the chain's loop for the comparison.

Validation at R4: flake8 clean, architecture 9 passed, kernel 13 and shadow 5 contract tests,
`test_intersection_command.py` 78 passed, all three smoke runners PASS, full contract suite (without
the command chunk) 1,429 passed / 18 skipped / 0 failed. No GUI check was run.

### R5, 2026-10-08

Kernel heights, patch and side slope against the current pipeline, starter presets after `Accept
Reviewed Rows`, full headless build (`test_intersection_kernel_shadow.py`, figures from the shadow
rows and the slope face preview):

| | T current | T kernel | Cross current | Cross kernel |
| --- | --- | --- | --- | --- |
| patch triangles | 164 | 178 | 207 | 200 |
| patch minimum quality | 0.0080 | 0.179 | 0.0122 | 0.170 |
| skinny patch triangles (< 0.08) | 125 | 0 | 160 | 0 |
| boundary edges with a side slope | 27 of 43 (the 16 arc edges unfilled) | every edge but the mouths | 20 of 52 (32 arc edges unfilled) | every edge but the mouths |
| curb return vertices with a side slope | 0 | 34 | 0 | 68 |
| side slope triangles, minimum quality | 44, not recorded | 140, 0.291 | 64, not recorded | 144, 0.221 |
| corridor clipped beyond the mouths | main 14 m (96 to 144), side 18 m (65 to 100) | 0 (103 to 137, 83 to 100) | 18 m on each road (96 to 144) | 0 (105 to 135) |

Kernel time 0.06 s (T) and 0.08 s (Cross).

Reading the three open defects of `SESSION_HANDOFF_1009.md` §5 against this:

1. **Unfilled curb return slope faces**: the kernel's strip runs round every arc; there is no
   unfilled edge to report because the strip is built along the boundary, not fitted to it.
2. **Skinny triangles**: the current 125 and 160 are the patch's fan and constraint-support
   triangles; the kernel's constrained Delaunay has none, minimum quality 0.17.
3. **Side slope missing beside the stem**: not re-measured, since the 49 m comes from the user's GUI
   capture. What is measured: the current pipeline clips the corridor over the control area (48 m
   on the main road, 35 m on the side road) while the intersection's own surfaces end at the
   curb return tangent points, so 14 m and 18 m of corridor side slope are clipped with nothing in
   their place. The kernel's clip spans end exactly at its mouths, where its strips meet the
   corridor's side slope line, so after the switch the gap cannot occur by construction.

Validation at R5: flake8 clean, architecture 9 passed, kernel 13 + surfaces 11 + shadow 7 contract
tests, `test_intersection_command.py` 78 passed, all three smoke runners PASS, full contract suite
(without the command chunk) 1,442 passed / 18 skipped / 0 failed. No GUI check was run.

### R6, 2026-10-08

The starter roundabout (`Roundabout - Single Lane`): 12 m inscribed radius, 6.6 m circulatory
roadway, 0.99 m outer apron, two 10 m roads crossing at its centre.

| | current | kernel |
| --- | --- | --- |
| shadow status | | agree |
| central island radius | 5.4 m | 5.4 m, deviation 0.0000 m |
| paved outer edge radius | 12.99 m | 12.99 m, deviation 0.0000 m |
| approaches | four 6.6 m rectangles, 15 m long, no surface built (0 triangles) | 10 m wide (the Applied Sections), joined to the ring by 6.5 m entry and 7.8 m exit flares |
| patch | ring and apron (apron surface 128 triangles); the connectors build none; minimum quality 0.265, none skinny | ring, flares and approaches in one TIN with the island as a hole, 340 triangles, minimum quality 0.102, none skinny |
| side slope | `RoundaboutSlopeFaceSurface` 64 triangles | 216 triangles round flares and ring, minimum quality 0.092 |
| corridor clipped beyond the mouths | 19.2 m on each road (104 to 156) | 0 (113.6 to 146.4) |

Kernel time 0.25 s. The ring is the same design; everything that differs is something the current
pipeline does not build (the approaches and their joins to the ring) or builds with a width that
is not the road's (6.6 m connectors on 10 m roads, a third case of problem P2).

Two things found on the way and fixed in the kernel: crown samples within a centimetre of the ring
crossing made slivers (now samples within half a step of it are dropped), and the throat breakline
sampled from the flare tangent left a 0.35 m interval next to the crown's end (now each side of the
crown end is sampled evenly). Before: 8 skinny triangles, minimum 0.023; after: none, minimum 0.102.

Validation at R6: flake8 clean on the touched files, architecture 9 passed, kernel 12 + surfaces 11 +
roundabout 8 + shadow 7 contract tests, `test_intersection_command.py` 78 passed, all three smoke
runners PASS, full contract suite (without the command chunk) 1,449 passed / 18 skipped / 0 failed.
No GUI check was run.

### R7a, 2026-10-08

`GeometryEngine = "kernel"` on the Intersection object (empty or `legacy`: unchanged behaviour)
changes Build Parametric in four places, all driven by the one kernel result:

| Step | Legacy | Kernel |
| --- | --- | --- |
| Applied Sections | intersection supplemental stations from control areas, curb return contacts, centre +- radius | first pass without them; the kernel's leg mouth stations; a second pass only if a mouth has no section yet |
| corridor design / slope / subgrade surfaces | tie-in sections added; exclusion polygon clip; roundabout ownership clip; daylight suppressed, trimmed and patched against the intersection surfaces | each road's triangles between its two mouths removed, read from the vertices' Applied Section; nothing else |
| intersection surfaces | patch build, slope face loops, tie slope, roundabout apron / subgrade / slope face | the kernel's patch (`V1CorridorIntersectionSurfacePreview`) and side slope (`V1CorridorIntersectionSlopeFaceSurfacePreview`) |
| review rows | readiness, tie-in continuity, grading, drainage handoff gate, roundabout rows | one row per kernel surface: status, triangles, minimum quality, skinny count, diagnostics |

Measured on the starter presets (`test_intersection_kernel_engine.py`):

- every mouth has an Applied Section (T 3, Cross 4, roundabout 4 intersection supplemental rows);
- no design, slope or (roundabout) subgrade triangle lies inside the kernel boundary;
- at every mouth the corridor's design surface has the kernel's edge vertices at the same height,
  and the slope surfaces share their daylight points: the joins are vertex for vertex;
- the full build reports `ready` for design, subgrade, slope, intersection and intersection slope
  surfaces, none skinny; a roundabout's subgrade ownership check finds 0 intruding triangles;
- a kernel document saves and reopens with its engine and surfaces;
- full Build Parametric with every preview: T 2.6 s, roundabout 3.6 s.

Not built by the kernel yet, and so absent in kernel mode: an intersection subgrade surface (a
T's and a Cross's subgrade overlapped under the legacy engine too), the drainage handoff gate row
(K7's drainage candidates), the shared breakline audit of the intersection.

Validation at R7a: flake8 clean on the new and changed lines (three unused variables in
`cmd_generate_applied_sections.py` predate this change), architecture 9 passed, kernel engine 17
contract tests, `test_intersection_command.py` 78 passed, all three smoke runners PASS, full
contract suite (without the command chunk) 1,466 passed / 18 skipped / 0 failed. No GUI check
was run.

#### GUI check for R7a

**T, 2026-10-08, done by the user.** Legacy first, then `GeometryEngine = kernel` on the same
document, with captures of the whole intersection, the design surface and the slope surface. With
the kernel the design surface ends in straight cuts at the three mouths; the side slope runs as one
strip along the closed side, joined to the roads' slopes at both ends, and round both curb returns
into the side road's slope; the wedge-shaped gap beside the side road and the partial curb return
slope of the legacy capture are gone. The Cross and the roundabout are still to be checked.

Found on the way: the tree has two objects labelled `Intersections`, the result folder under
`04_Parametric Model` and, inside it, the Intersection source object (`Intersections001`); the
engine is set on the second. `GeometryEngine` is a drop-down since then.

1. Create a T, a Cross and a Roundabout from the Intersection presets, accept the reviewed rows.
2. Run Applied Sections and Build Parametric: the legacy result.
3. Select the Intersection object, set the property `GeometryEngine` (group Intersections) to
   `kernel`, run Applied Sections and Build Parametric again.
4. Look at the joins at the curb return tangent points and the mouths, the side slope round the
   curb returns and along a T's closed side, and the roundabout's flares; and at the Results tab rows.
5. Set it back to `legacy` and rebuild: the legacy result returns.

### R7b, 2026-10-08

**Stored source.** `SpecJson` on the Intersection object holds the `IntersectionSpec`
(`intersection_spec_to_dict` / `intersection_spec_from_dict`). Creating an intersection from a preset
or from existing Alignments writes it, read from the rows just created. With the kernel engine the
two-pass Applied Sections and Build Parametric take the stored spec; a document without one (or with
one that does not read) falls back to the spec read from the rows. The legacy engine still reads the
rows until R7c.

**Panel.** The Intersection panel has a Parametric Spec group:

| Field | Spec |
| --- | --- |
| Geometry Engine | the object's `GeometryEngine` |
| Kind, Primary Road, Secondary Road | `kind`, `road_refs` |
| Anchor (detected / manual), Primary / Secondary Station | `anchor` |
| Corner Radius (0 = default) | `corner_radius_m` |
| Grading Mode ((default) = constant) | `grading_mode` |
| Roundabout Ring: inscribed radius, circulatory width, outer apron, entry / exit radius (0 = default), circulation | `roundabout` |
| Legs table: open, entry R, exit R | `leg_overrides`; a row that changes nothing is not stored |

`Load Spec` reads the stored spec, or the rows' one; `Check Spec` runs the kernel on the form with
the current Applied Sections and lists the legs with their mouth stations, the corners, every value
with its origin (`spec`, `override`, `constant`, `derived:...`), the quality figures and the
diagnostics, and fills the legs table; `Apply Spec` stores the spec and the engine. Corner overrides
and the anchor search hint are not shown and are kept as loaded. The form logic is widget-free
(`services/editing/intersection_spec_editing_service.py`).

Measured (`test_intersection_spec_editing.py`): a spec survives its JSON round trip and the form's;
the form names what is wrong (one road twice, a negative radius, a circulatory width that leaves no
island); a newly created T stores the spec its rows give; with the kernel, storing a 15 m radius moves
the main road's mouth sections from 103 / 137 to 100 / 140; the panel loads, checks (3 legs, `ready`,
`corner_radius_m ... (spec)`), applies and closes a leg.

Validation at R7b: flake8 clean on the touched files, architecture 9 passed, R7b 7 contract tests,
all three smoke runners PASS, full contract suite (command chunk included) 1,552 passed / 18
skipped / 0 failed. No GUI check was run.

#### GUI check for R7b

1. New document, Intersection panel, Preset `T Intersection - Basic`, Create Sources, Accept Reviewed
   Rows; Applied Sections, Build Sections.
2. In the panel's Parametric Spec group press Load Spec: Kind `t`, both roads, Corner Radius 12.
3. Press Check Spec: the status lists 3 legs with mouth stations 137, 103 and 83, `corner_radius_m ...
   = 12.000 (spec)`, and the legs table fills.
4. Set Corner Radius 15 and Geometry Engine `kernel`, press Apply Spec; run Build Sections and Build
   Parametric: the curb returns are larger and the mouths move to 100 / 140 and 80.
5. Untick the side road's leg in the table, Apply Spec, Check Spec: the kernel blocks, with
   `intersection_leg_count` and `leg_mouth_without_corner` (a T without its side road has no corner
   to end the main road's legs at). Tick it again and Apply. On a Cross, closing one leg gives
   `partial` with `intersection_leg_count` and still builds.
6. Save, close and reopen: Load Spec shows the 15 m radius.

### R7c-1, 2026-10-08

The kernel is the only engine. `GeometryEngine` and its panel field are gone; a document with an
Intersection source is built by the kernel, one without is untouched.

What went, found by an AST reference graph rather than by name: a definition of
`cmd_build_corridor.py` goes when nothing in production code reaches it any more and something did
before this phase (so code that only tests reached before is left alone, unless it is legacy
intersection code that now calls into deleted code). The graph counts a name as used wherever a
production module names it, as a Name, an attribute or a string, which keeps the functions the
Build Parametric viewer binds by name.

| | lines |
| --- | --- |
| `cmd_build_corridor.py`: the legacy branches and the 170 definitions only they reached | +26 / -6,747 |
| `cmd_generate_applied_sections.py`: the legacy intersection stations | +10 / -122 |
| ten patch pipeline / grading / drainage review modules nothing reached | -1,235 |
| the shadow comparison (its service, and its part of the context service) | -312 |
| production, all told | +45 / -8,515 |
| tests: 6 files of deleted modules, the legacy frame test, 77 tests of the legacy build | +143 / -7,428 |

The two intersection regression smokes keep their names and runner slots and now check the kernel:
the starter T, Cross and roundabout built end to end, both surfaces ready with no skinny triangle,
no missing daylight, no corridor triangle inside the intersection, the mouths' vertices shared.
The architecture ratchet lists the deleted roundabout wrappers as names that must not return.
`scripts/run_local_validation.ps1`'s Fast set drops the five deleted test files and takes the three
pure kernel test files.

Known gaps, left for R7c-2: the intersection drainage review and its handoff gate row read the
legacy chain's drainage hints, which nothing produces now (four tests of them went); the kernel's
K7 drainage candidates are to replace them. The Build Parametric Intersections and Breakline Audit
tabs still evaluate the legacy chain from the rows. Watertight Solids' intersection patch body reads
the intersection surface object, which keeps its name; its tests pass unchanged.

Validation at R7c-1: flake8 clean on the touched files, architecture 9 passed, all three smoke
runners PASS (with the rewritten intersection smokes), full contract suite (command chunk included)
1,440 passed / 18 skipped / 0 failed. GUI: the user built the starter T, Cross and roundabout
with the kernel as the only engine and reported all three as working (2026-10-09).

### R7c-2, 2026-10-09

The review surfaces read the kernel result, and the legacy evaluation chain is gone.

- K7 drainage candidates: `IntersectionGeometryResult.drainage_candidates`, the lowest vertices of
  the intersection surface (within `LOW_POINT_TOLERANCE_M` = 1 mm of the minimum), each with its
  nearest road and station (`PolylineRoadContext.nearest_station`).
- Build Parametric Intersections tab: `ui/presentation/intersection_kernel_review_presentation.py`
  lists the intersection, each leg and its mouth, each corner and its radius origin, the boundary,
  both surfaces with their quality, the clip spans, the drainage candidates, the resolved values and
  the diagnostics. Selecting a row draws its linework (mouth line, corner arc, boundary, low point).
- The guided review's Intersections step, the absent-preview notes, the drainage review (K7's low
  points against the Drainage Elements), the roundabout ownership intrusion check and the lane and
  shoulder review clip all read the kernel result. The lane and shoulder review now skips a strip
  only when its midpoint lies strictly inside the kernel boundary, so the strips on the mouth
  sections, which lie on the boundary, are kept.
- The cross section viewer's intersection rows: the kernel's status, this road's legs, whether the
  station is inside the span the intersection surface replaces, the low points nearest this road,
  the kernel diagnostics, and the section's own leg (`active_leg`).
- The Intersection editor panel the Presets panel replaced is deleted with its helpers.

What went was found by a whole-program reachability analysis this time, not by name: roots are the
module-level code of every module (command registration), modules named in string tables, and the
names a viewer declares as `name = None` placeholders that `configure_*_runtime(globals())` fills
from a command module; names resolve through the real imports and package re-exports. Deleted: every
wholly unreachable module of the legacy intersection chain, and every definition that became
unreachable since R7c-1 (shared geometry primitives excepted). An import check over the package and
the tests (every `from X import name` must exist) guards the result.

| | lines |
| --- | --- |
| 35 unreachable modules: the patch boundary / triangulation / TIN assembly pipeline, the boundary segment and loop, tie-in edge, slope face boundary and cell, tie slope and shared breakline evaluation, the exclusion / TIN clip / roundabout builders, the two legacy review presentations | -17,252 |
| `cmd_build_corridor.py` | +269 / -3,306 |
| `cmd_intersection_editor.py`: the editor panel and its helpers | +2 / -1,485 |
| production, all told (kernel K7 and the review presentation included) | +546 / -22,823 |
| tests: 14 files of deleted modules; the legacy review tests replaced by kernel ones | +250 / -7,175 |

Kept on purpose: `AlignmentIntersectionDetectionService` (the Presets panel's Auto Detect), the
shared boundary graph audit (read by the preview audit mapper), and the Breakline Audit tab's
parsers; nothing produces intersection rows for that tab any more, so it lists the corridor's own
breaklines. Watertight Solids keep reading the intersection surface object.

Validation at R7c-2: flake8 clean on the touched files, architecture 9 passed, all three smoke
runners PASS, full contract suite 1,297 passed / 18 skipped / 0 failed (143 fewer tests than at
R7c-1, those of the deleted chain). GUI checks still to do: the Intersections tab rows and
highlights, the drainage review's low point, and the cross section viewer's intersection rows, on
the starter T, Cross and roundabout.

### R7c-3, 2026-10-09

The lane connection and edge policy rows are gone from the source (D2), and with them the row
review. Measured first: the review buttons changed nothing the kernel builds. The starter T and
roundabout built with and without Accept Reviewed Rows have the same kernel fingerprint, boundary
area and triangle count, and the same Build Parametric review rows; only the Applied Sections'
diagnostic text differed, and accepting even added two `*_policy_ref_missing` warnings.

- Intersection panel: the source review table and Refresh Review, Accept Reviewed Rows and Adopt
  Edge Families From Subassembly are removed, with the "preset defaults ... review state" status
  lines. The flow is Preset, Create Sources (or Apply), then Check Spec / Apply Spec. The spec's
  Kind follows the Preset and then the created source, and cannot be edited on its own.
- Source: `IntersectionEdgePolicyRow`, `IntersectionLaneConnectionRow`, the model's
  `edge_policy_rows` / `lane_connection_rows` and the legs' `edge_policy_refs` are deleted, and the
  presets no longer stamp review states on their rows. Persistence: see
  `V1_PERSISTENCE_SCHEMA_INVENTORY.md`; old documents keep the properties unread.
- The roundabout ring of a source without a stored spec comes from its curb return radius with the
  preset's proportions (island 0.45 of the outer radius, apron 15 % of the ring width, at least
  0.5 m), which reproduces the ring the roundabout edge policy rows carried (checked at 12, 20 and
  36 m).
- Applied Sections' intersection source diagnostics report only what the build uses: a leg not
  found for the section's alignment, a control area naming no control Region. The source stages
  are Legs and Control Areas.
- `IntersectionEvaluationService` keeps `resolve_station` only (7,460 to 178 lines): topology, edge
  network, surface zones, grading context, drainage hints, corridor clipping, boundary and slope
  loops and roundabout approach legs are deleted with nine result modules and the review service.
- Watertight Solids (paused): each intersection gets planned, disabled targets for its pavement with
  the subgrade under it and its side slope, instead of one per edge-network surface zone. Their
  handoff now reports `candidate` where it reported `blocked` for lack of zones; the two tests of
  the blocked path keep it by emptying the zone table.

| | lines |
| --- | --- |
| production | +66 / -9,544 (10 files deleted, -1,225) |
| `intersection_evaluation_service.py` | +10 / -7,292 |
| `cmd_intersection_presets.py` | +2 / -455 |
| tests: 6 files and the tests of the deleted rows, review and evaluation | +59 / -6,349 |

Validation at R7c-3: flake8 clean on the touched files, architecture 9 passed, all three smoke
runners PASS, full contract suite 1,179 passed / 18 skipped / 0 failed. GUI: the user built the
intersections after this phase and the Build Parametric Intersections tab reports ready
(2026-10-09). Not checked in the GUI: a roundabout created before this phase rebuilding the same
ring.

### Legacy cleanup after R7c-3, 2026-10-09

The Build Parametric command, the Breakline Audit and two service modules still carried code for
previews and metadata that only the deleted pipeline produced. It is removed; nothing it read is
written any more, so no build or review result changes.

- `cmd_build_corridor.py`: the exclusion zone, exclusion clip, slope loop suppression and Slope
  Face boundary strip metadata, the Slope Face overlap preview, the shared boundary graph and
  exclusion near-boundary highlights, the boundary loop ownership metadata, the no-op tie-in
  wrapper and about 25 private geometry helpers. The daylight surface is clipped by the kernel's
  station spans like the other corridor surfaces. A rebuild removes the legacy preview and
  highlight objects an older document may still hold.
- Breakline Audit: one row per audited surface (and per breakline role for diagnostics); the
  intersection cell, graph, boundary loop and roundabout clip rows and their parsers are gone.
- Deleted: `intersection_shared_boundary_graph_evaluation_service`,
  `intersection_daylight_tin_service`, `models/result/intersection_shared_boundary_graph`.

| | lines |
| --- | --- |
| production | +45 / -3,924 (3 files deleted) |
| tests: 2 files and 9 tests of the deleted code; the Breakline Audit test rewritten | +18 / -1,008 |

Validation: flake8 clean on the touched files, architecture 9 passed, all three smoke runners
PASS, full contract suite 1,163 passed / 18 skipped / 0 failed. Not checked in the GUI.

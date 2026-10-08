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
- Every phase runs the full validation gate of `SESSION_HANDOFF.md` §7 (contract suite, intersection
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
| P9 | Open defects are symptoms of stitching partial graphs: unfilled curb return slope faces (Cross 0 of 32), 160 skinny constraint triangles, about 49 m of missing side slope. | `SESSION_HANDOFF.md` §5 |

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
```

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

**K7 (planar part).** Clip span per road: from the `back` mouth to the `ahead` mouth (the anchor
station where a side has no leg). Supplemental stations: the mouth stations.

**Roundabout** uses the same K2 to K7 with K1's partner replaced by the circulatory ring (R6). Until
R6 it resolves but its geometry status is `not_implemented`, and the shadow reports `skipped`.

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
  its origin, clip spans, kernel diagnostics, both deviations and areas.

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
| R5 | K4 to K6 (heights, patch TIN, side slope) in the kernel, still shadow | unfilled arcs, skinny triangles and the 49 m gap measured on the kernel output |
| R6 | roundabout in the kernel | roundabout shadow `agree` or explained |
| R7 | switch: Build Parametric consumes the kernel; the spec becomes the stored source (`SpecJson`); the panel edits the spec; lane connection, edge policy and surface zone rows and the services only they feed are deleted (D2) | full gate and GUI manual QA |

R1 to R4 are implemented with this plan. R5 onwards each start from the measurements R4 records.

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

### Next: R5

K4 to K6 move heights, the patch TIN and the side slope into the kernel, still in shadow. The
first measurements to take are the three open defects of `SESSION_HANDOFF.md` §5 on the kernel's
output: the curb return slope face fill, the skinny constraint triangles, and the 49 m side slope
gap beside the stem.

## 9. Out of scope

Signals, lane operation and turn lane design (taper widths belong to Assembly and Region), Ramp,
Watertight Solid, grade separation.

"""Evaluate Intersection boundary segments from accepted tie-in results."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ...models.result.intersection_boundary_segment import (
    IntersectionBoundarySegmentResult,
    IntersectionBoundarySegmentRow,
)


@dataclass(frozen=True)
class IntersectionBoundarySegmentEvaluationRequest:
    tie_in_result: object
    intersection_model: object | None = None


class IntersectionBoundarySegmentEvaluationService:
    """Map tie-in rows and curb-return source policy into boundary results."""

    def evaluate(
        self,
        request: IntersectionBoundarySegmentEvaluationRequest,
    ) -> IntersectionBoundarySegmentResult:
        tie_in_result = request.tie_in_result
        intersection_id = str(
            getattr(tie_in_result, "intersection_id", "") or ""
        ).strip()
        source_row = _intersection_row_by_id(
            request.intersection_model,
            intersection_id,
        )
        intersection_kind = str(
            getattr(source_row, "intersection_kind", "") or "t_intersection"
        )
        policy = _curb_return_policy_for(
            request.intersection_model,
            intersection_id,
        )
        raw_radius = float(getattr(policy, "radius", 0.0) or 0.0)
        radius = raw_radius
        diagnostics: list[str] = []
        if policy is not None and raw_radius <= 0.0:
            diagnostics.append(
                "warning:intersection_curb_return_radius_invalid: radius "
                f"{raw_radius:.3f} is not positive; default radius used."
            )
        elif 0.0 < raw_radius < 1.0:
            diagnostics.append(
                "warning:intersection_curb_return_radius_small: radius "
                f"{raw_radius:.3f} may be too small for a stable curb return."
            )
        if radius <= 0.0:
            radius = _default_radius(intersection_kind)

        rows = [_tie_in_segment_row(edge, intersection_id, index) for index, edge in enumerate(
            list(getattr(tie_in_result, "edge_rows", []) or []),
            start=1,
        )]
        tie_in_rows = [row for row in rows if row.segment_kind == "tie_in"]
        center = _boundary_center(source_row, rows)
        primary_ref = (
            str(getattr(source_row, "primary_alignment_ref", "") or "")
            if source_row is not None
            else ""
        )
        secondary_refs = (
            list(getattr(source_row, "secondary_alignment_refs", []) or [])
            if source_row is not None
            else []
        )
        secondary_ref = str(secondary_refs[0] if secondary_refs else "")
        primary_candidate = _tie_in_alignment_direction(tie_in_result, primary_ref)
        secondary_candidate = _tie_in_alignment_direction(
            tie_in_result,
            secondary_ref,
        )
        if primary_candidate is None:
            diagnostics.append(
                "warning:intersection_boundary_direction_fallback: primary "
                "tie-in direction fallback used for "
                f"{primary_ref or 'primary'}."
            )
        if secondary_candidate is None:
            diagnostics.append(
                "warning:intersection_boundary_direction_fallback: secondary "
                "tie-in direction fallback used for "
                f"{secondary_ref or 'secondary'}."
            )
        primary_dir = _unit_xyz(primary_candidate or (1.0, 0.0, 0.0))
        secondary_dir = _unit_xyz(secondary_candidate or (0.0, 1.0, 0.0))
        primary_dir = primary_dir or (1.0, 0.0, 0.0)
        secondary_dir = secondary_dir or (0.0, 1.0, 0.0)
        quadrants = _curb_return_quadrants(intersection_kind)
        if len(rows) < 4:
            diagnostics.append(
                "intersection_boundary_tie_in_edges_incomplete: expected at "
                f"least 4 tie-in segments, found {len(rows)}."
            )
        tie_in_span = _tie_in_boundary_span(tie_in_rows)
        if tie_in_span > 1.0e-9 and radius > tie_in_span * 0.75:
            diagnostics.append(
                "warning:intersection_curb_return_radius_large: radius "
                f"{radius:.3f} exceeds 75% of tie-in span {tie_in_span:.3f}."
            )
        sample_count = _curb_return_arc_sample_count(radius, policy)
        road_frames = _tie_in_road_frames(tie_in_rows, primary_ref, secondary_ref, primary_dir, secondary_dir)
        fillet_count = 0
        for index, (primary_sign, secondary_sign) in enumerate(
            quadrants,
            start=1,
        ):
            chord_points = _curb_return_fillet_points(
                road_frames,
                center_z=float(center[2]),
                radius=radius,
                primary_sign=primary_sign,
                secondary_sign=secondary_sign,
                sample_count=sample_count,
            )
            arc_kind = "fillet"
            if chord_points:
                fillet_count += 1
            else:
                arc_kind = "centre_arc"
                chord_points = _curb_return_chord_points(
                    center,
                    primary_dir,
                    secondary_dir,
                    radius=radius,
                    primary_sign=primary_sign,
                    secondary_sign=secondary_sign,
                    sample_count=sample_count,
                )
            if len(chord_points) < 2:
                diagnostics.append(
                    "intersection_curb_return_radius_invalid: boundary arc "
                    f"{index} could not be sampled."
                )
                continue
            endpoint_gap = _boundary_arc_endpoint_gap(chord_points, tie_in_rows)
            endpoint_limit = max(15.0, radius * 1.5)
            if endpoint_gap is not None and endpoint_gap > endpoint_limit:
                diagnostics.append(
                    "warning:intersection_curb_return_arc_endpoint_gap: "
                    f"boundary arc {index} endpoint gap {endpoint_gap:.3f} "
                    f"exceeds limit {endpoint_limit:.3f}."
                )
            rows.append(
                IntersectionBoundarySegmentRow(
                    boundary_segment_id=(
                        f"boundary:{intersection_id}:curb-return:{index}"
                    ),
                    intersection_id=intersection_id,
                    segment_kind="arc",
                    segment_role="curb_return",
                    source_ref=str(getattr(policy, "policy_id", "") or ""),
                    start_xyz=chord_points[0],
                    end_xyz=chord_points[-1],
                    center_xyz=center,
                    radius=radius,
                    chord_points_xyz=tuple(chord_points),
                    status="candidate",
                    notes=(
                        f"kind={intersection_kind}; "
                        f"quadrant={primary_sign:+.0f},{secondary_sign:+.0f}; "
                        f"arc_samples={len(chord_points)}; "
                        f"arc_segments={max(len(chord_points) - 1, 0)}; "
                        f"arc_kind={arc_kind}"
                    ),
                )
            )

        if quadrants and fillet_count < len(quadrants):
            diagnostics.append(
                "warning:intersection_curb_return_fillet_unavailable: "
                f"{len(quadrants) - fillet_count} of {len(quadrants)} curb returns keep the arc about the "
                "intersection centre; each needs a left and a right tie-in edge on both alignments."
            )
        arc_count = sum(row.segment_kind == "arc" for row in rows)
        tie_in_count = sum(row.segment_kind == "tie_in" for row in rows)
        status = (
            "ready"
            if rows and not _diagnostics_include_error(diagnostics)
            else ("warning" if rows else "missing")
        )
        return IntersectionBoundarySegmentResult(
            schema_version=1,
            project_id=str(getattr(tie_in_result, "project_id", "") or ""),
            label=f"Intersection Boundary Segments - {intersection_id}",
            boundary_segment_result_id=(
                f"intersection-boundary-segments:{intersection_id or 'unknown'}"
            ),
            intersection_id=intersection_id,
            status=status,
            segment_count=len(rows),
            tie_in_segment_count=tie_in_count,
            arc_segment_count=arc_count,
            diagnostic_rows=diagnostics,
            segment_rows=rows,
        )

    def evaluate_context(
        self,
        tie_in_result,
        *,
        intersection_model=None,
    ) -> IntersectionBoundarySegmentResult:
        """Adapt the boundary-context evaluator signature to the typed request."""

        return self.evaluate(
            IntersectionBoundarySegmentEvaluationRequest(
                tie_in_result=tie_in_result,
                intersection_model=intersection_model,
            )
        )


def _intersection_row_by_id(intersection_model, intersection_id: str):
    target = str(intersection_id or "").strip()
    if intersection_model is None or not target:
        return None
    return next(
        (
            row
            for row in list(getattr(intersection_model, "intersection_rows", []) or [])
            if str(getattr(row, "intersection_id", "") or "").strip() == target
        ),
        None,
    )


def _curb_return_policy_for(intersection_model, intersection_id: str):
    target = str(intersection_id or "").strip()
    for row in (
        list(getattr(intersection_model, "curb_return_policy_rows", []) or [])
        if intersection_model is not None
        else []
    ):
        if (
            str(getattr(row, "intersection_id", "") or "") == target
            and str(getattr(row, "status", "") or "active") != "disabled"
        ):
            return row
    return None


def _default_radius(intersection_kind: str) -> float:
    if intersection_kind == "cross_intersection":
        return 10.0
    return 12.0


def _tie_in_segment_row(edge, intersection_id: str, index: int):
    edge_id = str(getattr(edge, "tie_in_edge_id", "") or "")
    return IntersectionBoundarySegmentRow(
        boundary_segment_id=f"boundary:{edge_id or index}",
        intersection_id=intersection_id,
        segment_kind="tie_in",
        segment_role="pavement_edge",
        source_ref=edge_id,
        alignment_ref=str(getattr(edge, "alignment_ref", "") or ""),
        side=str(getattr(edge, "side", "") or ""),
        start_xyz=tuple(
            getattr(edge, "start_xyz", (0.0, 0.0, 0.0))
            or (0.0, 0.0, 0.0)
        ),
        end_xyz=tuple(
            getattr(edge, "end_xyz", (0.0, 0.0, 0.0))
            or (0.0, 0.0, 0.0)
        ),
        status=str(getattr(edge, "status", "") or "candidate"),
        notes=str(getattr(edge, "notes", "") or ""),
    )


def _boundary_center(source_row, segment_rows) -> tuple[float, float, float]:
    if source_row is not None:
        point = tuple(
            float(getattr(source_row, name, 0.0) or 0.0)
            for name in (
                "intersection_point_x",
                "intersection_point_y",
                "intersection_point_z",
            )
        )
        if any(abs(value) > 1.0e-9 for value in point):
            return point
    points = [
        tuple(getattr(row, name, (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
        for row in segment_rows
        for name in ("start_xyz", "end_xyz")
    ]
    if not points:
        return (0.0, 0.0, 0.0)
    return tuple(
        sum(float(point[index]) for point in points) / len(points)
        for index in range(3)
    )


def _tie_in_alignment_direction(tie_in_result, alignment_ref: str):
    target = str(alignment_ref or "").strip()
    for row in list(getattr(tie_in_result, "edge_rows", []) or []):
        if target and str(getattr(row, "alignment_ref", "") or "") != target:
            continue
        start = tuple(
            getattr(row, "start_xyz", (0.0, 0.0, 0.0))
            or (0.0, 0.0, 0.0)
        )
        end = tuple(
            getattr(row, "end_xyz", (0.0, 0.0, 0.0))
            or (0.0, 0.0, 0.0)
        )
        vector = tuple(float(end[index]) - float(start[index]) for index in range(3))
        if _xyz_length(vector) > 1.0e-9:
            return vector
    return None


def _curb_return_quadrants(intersection_kind: str):
    return {
        "cross_intersection": (
            (1.0, 1.0),
            (1.0, -1.0),
            (-1.0, 1.0),
            (-1.0, -1.0),
        ),
        "t_intersection": ((1.0, -1.0), (-1.0, -1.0)),
    }.get(intersection_kind, ((1.0, 1.0), (-1.0, 1.0)))


def _curb_return_arc_sample_count(radius: float, policy=None) -> int:
    explicit = int(
        float(
            getattr(policy, "arc_sample_count", 0)
            or getattr(policy, "sample_count", 0)
            or 0
        )
    )
    if explicit > 0:
        return max(5, min(explicit, 49))
    spacing = float(
        getattr(policy, "arc_sample_spacing", 0.0)
        or getattr(policy, "sample_spacing", 0.0)
        or 2.0
    )
    spacing = max(spacing, 0.5)
    arc_length = max(float(radius), 0.0) * (math.pi / 2.0)
    segment_count = int(math.ceil(arc_length / spacing)) if arc_length > 0.0 else 4
    return max(4, min(segment_count, 48)) + 1


def _tie_in_road_frames(tie_in_rows, primary_ref, secondary_ref, primary_dir, secondary_dir):
    """Return each road's direction, centre line offset and pavement half width, from its tie-in edges.

    A road's left and right tie-in edges are its two pavement edges near the intersection. In the
    XY plane, with n the road direction turned a quarter turn counter-clockwise, each edge lies at a
    signed offset along n; the centre line is their mean and the half width half their difference.
    The two centre lines cross at the intersection's own origin, which is found here rather than taken
    from the source point (a source point at the coordinate origin reads as unset). None when either
    road lacks a left and a right edge.
    """

    frames = {}
    for key, alignment_ref, direction in (
        ("primary", primary_ref, primary_dir),
        ("secondary", secondary_ref, secondary_dir),
    ):
        ux, uy = float(direction[0]), float(direction[1])
        length = math.hypot(ux, uy)
        if length <= 1.0e-9:
            return None
        ux, uy = ux / length, uy / length
        nx, ny = -uy, ux
        offsets = {}
        for row in tie_in_rows:
            if alignment_ref and str(getattr(row, "alignment_ref", "") or "") != alignment_ref:
                continue
            side = str(getattr(row, "side", "") or "").lower()
            if side not in ("left", "right") or side in offsets:
                continue
            start = tuple(getattr(row, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
            end = tuple(getattr(row, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
            mid_x = (float(start[0]) + float(end[0])) * 0.5
            mid_y = (float(start[1]) + float(end[1])) * 0.5
            offsets[side] = mid_x * nx + mid_y * ny
        if len(offsets) != 2:
            return None
        half_width = abs(offsets["left"] - offsets["right"]) * 0.5
        if half_width <= 1.0e-9:
            return None
        frames[key] = {
            "direction": (ux, uy),
            "normal": (nx, ny),
            "centre_offset": (offsets["left"] + offsets["right"]) * 0.5,
            "half_width": half_width,
        }
    primary, secondary = frames["primary"], frames["secondary"]
    origin = _solve_xy(
        primary["normal"], primary["centre_offset"], secondary["normal"], secondary["centre_offset"]
    )
    if origin is None:
        return None
    frames["origin"] = origin
    return frames


def _curb_return_fillet_points(road_frames, *, center_z, radius, primary_sign, secondary_sign, sample_count):
    """Return the curb return of one quadrant as a fillet tangent to both roads' pavement edges.

    The arms are the primary road in the direction `primary_sign` and the secondary road in the
    direction `secondary_sign`. The fillet of radius R is tangent to the pavement edge of each road on
    the side of the other arm, so its centre is R beyond each edge. The points run from the tangent
    point on the primary road's edge to the one on the secondary road's edge, the order the arc about
    the centre had. An empty list means no fillet: no road frames, roads in line, or a radius so large
    that a tangent point falls behind the intersection.
    """

    if not road_frames or float(radius) <= 0.0:
        return []
    primary, secondary = road_frames["primary"], road_frames["secondary"]
    ox, oy = road_frames["origin"]
    ax, ay = primary_sign * primary["direction"][0], primary_sign * primary["direction"][1]
    bx, by = secondary_sign * secondary["direction"][0], secondary_sign * secondary["direction"][1]
    na = _unit_xy(bx - (bx * ax + by * ay) * ax, by - (bx * ax + by * ay) * ay)
    nb = _unit_xy(ax - (ax * bx + ay * by) * bx, ay - (ax * bx + ay * by) * by)
    if na is None or nb is None:
        return []
    r = float(radius)
    centre = _solve_xy(na, primary["half_width"] + r, nb, secondary["half_width"] + r)
    if centre is None:
        return []
    cx, cy = centre
    start = (cx - r * na[0], cy - r * na[1])
    end = (cx - r * nb[0], cy - r * nb[1])
    if start[0] * ax + start[1] * ay < 0.0 or end[0] * bx + end[1] * by < 0.0:
        return []
    start_angle = math.atan2(start[1] - cy, start[0] - cx)
    end_angle = math.atan2(end[1] - cy, end[0] - cx)
    delta = end_angle - start_angle
    while delta > math.pi:
        delta -= math.tau
    while delta < -math.pi:
        delta += math.tau
    count = max(int(sample_count), 2)
    points = []
    for step in range(count):
        angle = start_angle + delta * (step / max(count - 1, 1))
        points.append((ox + cx + math.cos(angle) * r, oy + cy + math.sin(angle) * r, float(center_z)))
    points[0] = (ox + start[0], oy + start[1], float(center_z))
    points[-1] = (ox + end[0], oy + end[1], float(center_z))
    return points


def _solve_xy(first_normal, first_value, second_normal, second_value):
    """Solve first_normal . p = first_value and second_normal . p = second_value for p in XY."""

    determinant = first_normal[0] * second_normal[1] - first_normal[1] * second_normal[0]
    if abs(determinant) <= 1.0e-9:
        return None
    return (
        (first_value * second_normal[1] - first_normal[1] * second_value) / determinant,
        (first_normal[0] * second_value - first_value * second_normal[0]) / determinant,
    )


def _unit_xy(x, y):
    length = math.hypot(x, y)
    if length <= 1.0e-9:
        return None
    return (x / length, y / length)


def _curb_return_chord_points(
    center,
    primary_dir,
    secondary_dir,
    *,
    radius,
    primary_sign,
    secondary_sign,
    sample_count,
):
    output = []
    count = max(int(sample_count), 2)
    denominator = max(count - 1, 1)
    for step in range(count):
        theta = (math.pi / 2.0) * (step / denominator)
        primary_scale = float(primary_sign) * float(radius) * math.cos(theta)
        secondary_scale = float(secondary_sign) * float(radius) * math.sin(theta)
        output.append(
            tuple(
                center[index]
                + primary_dir[index] * primary_scale
                + secondary_dir[index] * secondary_scale
                for index in range(3)
            )
        )
    return output


def _tie_in_boundary_span(tie_in_rows) -> float:
    points = [
        tuple(getattr(row, name, (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
        for row in tie_in_rows
        for name in ("start_xyz", "end_xyz")
    ]
    if not points:
        return 0.0
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return max(max(xs) - min(xs), max(ys) - min(ys))


def _boundary_arc_endpoint_gap(chord_points, tie_in_rows):
    endpoints = [
        tuple(getattr(row, name, (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
        for row in tie_in_rows
        for name in ("start_xyz", "end_xyz")
    ]
    if len(chord_points) < 2 or not endpoints:
        return None
    return max(
        min(
            math.hypot(
                float(arc_point[0]) - float(endpoint[0]),
                float(arc_point[1]) - float(endpoint[1]),
            )
            for endpoint in endpoints
        )
        for arc_point in (chord_points[0], chord_points[-1])
    )


def _unit_xyz(vector):
    length = _xyz_length(vector)
    if length <= 1.0e-9:
        return None
    return tuple(float(value) / length for value in vector)


def _xyz_length(vector) -> float:
    return math.sqrt(sum(float(value) ** 2 for value in vector))


def _diagnostics_include_error(diagnostics) -> bool:
    return any(
        text and not text.startswith("warning:")
        for text in (str(value or "").strip().lower() for value in diagnostics or [])
    )

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
        for index, (primary_sign, secondary_sign) in enumerate(
            quadrants,
            start=1,
        ):
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
                        f"arc_segments={max(len(chord_points) - 1, 0)}"
                    ),
                )
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
    if intersection_kind == "y_intersection":
        return 15.0
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
        "y_intersection": ((1.0, 1.0), (-1.0, 1.0)),
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

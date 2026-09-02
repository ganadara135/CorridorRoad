"""Evaluate Intersection slope-face boundary handoffs from result contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math

from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.intersection_boundary_segment import (
    IntersectionBoundarySegmentResult,
)
from ...models.result.intersection_slope_face_boundary import (
    IntersectionSlopeFaceBoundaryResult,
    IntersectionSlopeFaceBoundaryRow,
)
from ...models.result.intersection_tie_in_edge import IntersectionTieInEdgeResult
from ...services.geometry import (
    xy_distance,
    xy_point_segment_distance_with_ratio,
    xy_segment_projection_ratio,
    xyz_point,
)
from .intersection_boundary_segment_evaluation_service import (
    IntersectionBoundarySegmentEvaluationRequest,
    IntersectionBoundarySegmentEvaluationService,
)
from .intersection_evaluation_service import IntersectionPatchPrerequisiteResult
from .intersection_tie_in_edge_evaluation_service import (
    IntersectionTieInEdgeEvaluationRequest,
    IntersectionTieInEdgeEvaluationService,
)


INTERSECTION_SLOPE_FACE_BOUNDARY_EXTENSION_LENGTH = 5.0


@dataclass(frozen=True)
class IntersectionSlopeFaceBoundaryEvaluationRequest:
    """Typed input for slope-face boundary evaluation."""

    applied_section_set: AppliedSectionSet | None
    prerequisite: IntersectionPatchPrerequisiteResult
    intersection_model: object | None = None


class IntersectionSlopeFaceBoundaryEvaluationService:
    """Build traceable boundary candidates without document or preview state."""

    def evaluate(
        self,
        request: IntersectionSlopeFaceBoundaryEvaluationRequest,
    ) -> IntersectionSlopeFaceBoundaryResult:
        return _evaluate_intersection_slope_face_boundary(
            request.applied_section_set,
            prerequisite=request.prerequisite,
            intersection_model=request.intersection_model,
        )


def intersection_slope_face_boundary_target_segments(
    boundary_result,
    *,
    intersection_model=None,
    intersection_id: str = "",
):
    """Return accepted target segments for compatibility and focused review."""

    return _intersection_slope_face_boundary_target_segments(
        boundary_result,
        intersection_model=intersection_model,
        intersection_id=intersection_id,
    )


def _station_ordered_applied_sections(applied_section_set) -> list[object]:
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    output: list[object] = []
    for row in sorted(
        list(getattr(applied_section_set, "station_rows", []) or []),
        key=lambda item: float(getattr(item, "station", 0.0) or 0.0),
    ):
        section = sections.get(str(getattr(row, "applied_section_id", "") or ""))
        if section is not None:
            output.append(section)
    if output:
        return output
    return sorted(list(getattr(applied_section_set, "sections", []) or []), key=lambda section: _section_station(section))


def _section_station(section) -> float:
    frame = getattr(section, "frame", None)
    try:
        return float(getattr(frame, "station", getattr(section, "station", 0.0)) or 0.0)
    except Exception:
        try:
            return float(getattr(section, "station", 0.0) or 0.0)
        except Exception:
            return 0.0


def _lerp_value(first, second, ratio: float) -> float:
    return float(first or 0.0) + (float(second or 0.0) - float(first or 0.0)) * float(ratio)


def _intersection_row_by_id(intersection_model, intersection_id: str):
    target = str(intersection_id or "").strip()
    if intersection_model is None or not target:
        return None
    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        if str(getattr(row, "intersection_id", "") or "").strip() == target:
            return row
    return None


def _interpolate_region_boundary_section(first, second, ratio: float, *, station: float, region_id: str, boundary_role: str):
    t = max(0.0, min(1.0, float(ratio)))
    source = _region_boundary_context_source(first, second, station=station, region_id=region_id)
    frame = _interpolate_region_boundary_frame(getattr(first, "frame", None), getattr(second, "frame", None), t, station=station, source_frame=getattr(source, "frame", None))
    point_rows = _interpolate_region_boundary_points(first, second, t)
    if not point_rows:
        point_rows = list(getattr(source, "point_rows", []) or [])
    return _replace_region_boundary_section(
        source,
        station=station,
        frame=frame,
        region_id=region_id,
        boundary_role=boundary_role,
        point_rows=point_rows,
        first=first,
        second=second,
        ratio=t,
    )


def _project_region_boundary_section(section, *, station: float, region_id: str, boundary_role: str):
    frame = getattr(section, "frame", None)
    if frame is None:
        return None
    try:
        import math as _math

        delta = float(station) - _section_station(section)
        angle_rad = _math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
        projected_frame = replace(
            frame,
            station=float(station),
            x=float(getattr(frame, "x", 0.0) or 0.0) + _math.cos(angle_rad) * delta,
            y=float(getattr(frame, "y", 0.0) or 0.0) + _math.sin(angle_rad) * delta,
            notes=_append_frame_note(frame, "region_boundary_virtual"),
        )
    except Exception:
        projected_frame = replace(frame, station=float(station), notes=_append_frame_note(frame, "region_boundary_virtual"))
    return _replace_region_boundary_section(
        section,
        station=station,
        frame=projected_frame,
        region_id=region_id,
        boundary_role=boundary_role,
        point_rows=list(getattr(section, "point_rows", []) or []),
    )


def _region_boundary_context_source(first, second, *, station: float, region_id: str):
    target = str(region_id or "")
    for section in (first, second):
        if str(getattr(section, "region_id", "") or "") == target:
            return section
    return first if abs(_section_station(first) - float(station)) <= abs(_section_station(second) - float(station)) else second


def _interpolate_region_boundary_frame(first_frame, second_frame, ratio: float, *, station: float, source_frame=None):
    source = source_frame or first_frame or second_frame
    if source is None:
        return None
    if first_frame is None:
        first_frame = source
    if second_frame is None:
        second_frame = source
    t = max(0.0, min(1.0, float(ratio)))
    return replace(
        source,
        station=float(station),
        x=_lerp_value(getattr(first_frame, "x", 0.0), getattr(second_frame, "x", 0.0), t),
        y=_lerp_value(getattr(first_frame, "y", 0.0), getattr(second_frame, "y", 0.0), t),
        z=_lerp_value(getattr(first_frame, "z", 0.0), getattr(second_frame, "z", 0.0), t),
        tangent_direction_deg=_lerp_angle_degrees(
            float(getattr(first_frame, "tangent_direction_deg", 0.0) or 0.0),
            float(getattr(second_frame, "tangent_direction_deg", 0.0) or 0.0),
            t,
        ),
        profile_grade=_lerp_value(getattr(first_frame, "profile_grade", 0.0), getattr(second_frame, "profile_grade", 0.0), t),
        notes=_append_frame_note(source, "region_boundary_virtual"),
    )


def _replace_region_boundary_section(
    source,
    *,
    station: float,
    frame,
    region_id: str,
    boundary_role: str,
    point_rows: list[object],
    first=None,
    second=None,
    ratio: float = 0.0,
):
    try:
        return replace(
            source,
            applied_section_id=f"{str(getattr(source, 'applied_section_id', '') or 'section')}:region-boundary:{boundary_role}:{float(station):.3f}",
            station=float(station),
            frame=frame,
            region_id=str(region_id or getattr(source, "region_id", "") or ""),
            surface_left_width=_interpolate_attr(first, second, "surface_left_width", ratio, source),
            surface_right_width=_interpolate_attr(first, second, "surface_right_width", ratio, source),
            subgrade_depth=_interpolate_attr(first, second, "subgrade_depth", ratio, source),
            daylight_left_width=_interpolate_attr(first, second, "daylight_left_width", ratio, source),
            daylight_right_width=_interpolate_attr(first, second, "daylight_right_width", ratio, source),
            daylight_left_slope=_interpolate_attr(first, second, "daylight_left_slope", ratio, source),
            daylight_right_slope=_interpolate_attr(first, second, "daylight_right_slope", ratio, source),
            point_rows=point_rows,
            structure_diagnostic_rows=list(getattr(source, "structure_diagnostic_rows", []) or [])
            + [f"info|region_boundary_virtual|{region_id}|{boundary_role}:{float(station):.3f}"],
        )
    except Exception:
        return source


def _interpolate_attr(first, second, attr: str, ratio: float, fallback) -> float:
    if first is None or second is None:
        return float(getattr(fallback, attr, 0.0) or 0.0)
    return _lerp_value(getattr(first, attr, 0.0), getattr(second, attr, 0.0), max(0.0, min(1.0, float(ratio))))


def _interpolate_region_boundary_points(first, second, ratio: float) -> list[object]:
    first_points = list(getattr(first, "point_rows", []) or [])
    second_points = list(getattr(second, "point_rows", []) or [])
    t = max(0.0, min(1.0, float(ratio)))
    if len(first_points) == len(second_points):
        output = []
        for index, first_point in enumerate(first_points):
            second_point = second_points[index]
            first_role = str(getattr(first_point, "point_role", "") or "")
            if first_role != str(getattr(second_point, "point_role", "") or ""):
                output = []
                break
            output.append(_interpolate_region_boundary_point(first_point, second_point, t, point_role=first_role, index=index))
        if output:
            return output
    output: list[object] = []
    for role in ("fg_surface", "subgrade_surface", "ditch_surface", "side_slope_surface", "bench_surface", "daylight_marker"):
        left = _role_points_for_region_boundary(first, role)
        right = _role_points_for_region_boundary(second, role)
        if not left or len(left) != len(right):
            continue
        for index, first_point in enumerate(left):
            output.append(_interpolate_region_boundary_point(first_point, right[index], t, point_role=role, index=index))
    return output


def _role_points_for_region_boundary(section, role: str) -> list[object]:
    rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == str(role or "")
    ]
    return sorted(rows, key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))


def _interpolate_region_boundary_point(first_point, second_point, ratio: float, *, point_role: str, index: int):
    t = max(0.0, min(1.0, float(ratio)))
    try:
        return replace(
            first_point,
            point_id=f"region-boundary:{point_role}:{index}:{float(t):.6g}",
            x=_lerp_value(getattr(first_point, "x", 0.0), getattr(second_point, "x", 0.0), t),
            y=_lerp_value(getattr(first_point, "y", 0.0), getattr(second_point, "y", 0.0), t),
            z=_lerp_value(getattr(first_point, "z", 0.0), getattr(second_point, "z", 0.0), t),
            point_role=point_role,
            lateral_offset=_lerp_value(getattr(first_point, "lateral_offset", 0.0), getattr(second_point, "lateral_offset", 0.0), t),
        )
    except Exception:
        return first_point


def _append_frame_note(frame, note: str) -> str:
    existing = str(getattr(frame, "notes", "") or "")
    token = str(note or "")
    if not existing:
        return token
    if token in existing:
        return existing
    return f"{existing};{token}"


def _lerp_angle_degrees(first: float, second: float, ratio: float) -> float:
    delta = (float(second) - float(first) + 180.0) % 360.0 - 180.0
    return float(first) + delta * float(ratio)


def corridor_intersection_tie_in_edge_result(
    applied_section_set,
    *,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
) -> IntersectionTieInEdgeResult:
    """Compatibility wrapper for typed tie-in edge evaluation."""

    return IntersectionTieInEdgeEvaluationService().evaluate(
        IntersectionTieInEdgeEvaluationRequest(
            applied_section_set=applied_section_set,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
        )
    )


def corridor_intersection_boundary_segment_result(
    tie_in_result: IntersectionTieInEdgeResult,
    *,
    intersection_model=None,
) -> IntersectionBoundarySegmentResult:
    """Compatibility wrapper for typed boundary-segment evaluation."""

    return IntersectionBoundarySegmentEvaluationService().evaluate(
        IntersectionBoundarySegmentEvaluationRequest(
            tie_in_result=tie_in_result,
            intersection_model=intersection_model,
        )
    )


def _evaluate_intersection_slope_face_boundary(
    applied_section_set,
    *,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
) -> IntersectionSlopeFaceBoundaryResult:
    """Build reviewable slope-face boundary candidates around an intersection."""

    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "").strip()
    diagnostics: list[str] = []
    if applied_section_set is None:
        diagnostics.append("intersection_slope_face_boundary_missing: Applied Sections are required.")
        return IntersectionSlopeFaceBoundaryResult(
            schema_version=1,
            project_id="",
            label=f"Intersection Slope Face Boundary - {intersection_id or 'unknown'}",
            intersection_id=intersection_id,
            status="missing",
            diagnostic_rows=diagnostics,
        )

    tie_in_result = corridor_intersection_tie_in_edge_result(
        applied_section_set,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )
    boundary_result = corridor_intersection_boundary_segment_result(
        tie_in_result,
        intersection_model=intersection_model,
    )
    tie_in_edges_by_id = {
        str(getattr(edge, "tie_in_edge_id", "") or ""): edge
        for edge in list(getattr(tie_in_result, "edge_rows", []) or [])
        if str(getattr(edge, "tie_in_edge_id", "") or "")
    }
    diagnostics.extend(str(value or "") for value in list(getattr(tie_in_result, "diagnostic_rows", []) or []) if str(value or ""))
    diagnostics.extend(str(value or "") for value in list(getattr(boundary_result, "diagnostic_rows", []) or []) if str(value or ""))

    grouped_sections: dict[str, list[object]] = {}
    for section in list(getattr(applied_section_set, "sections", []) or []):
        alignment_id = str(getattr(section, "alignment_id", "") or "").strip()
        if not alignment_id:
            continue
        active_intersection = str(getattr(section, "active_intersection_id", "") or "").strip()
        if intersection_id and active_intersection and active_intersection != intersection_id:
            continue
        grouped_sections.setdefault(alignment_id, []).append(section)
    for alignment_id in list(grouped_sections):
        grouped_sections[alignment_id] = sorted(
            grouped_sections[alignment_id],
            key=lambda section: float(getattr(section, "station", 0.0) or 0.0),
        )

    slope_boundary_segments = _intersection_slope_face_boundary_target_segments(
        boundary_result,
        intersection_model=intersection_model,
        intersection_id=intersection_id,
    )
    rows: list[IntersectionSlopeFaceBoundaryRow] = []
    for segment in slope_boundary_segments:
        if str(getattr(segment, "segment_kind", "") or "") != "tie_in":
            continue
        alignment_ref = str(getattr(segment, "alignment_ref", "") or "").strip()
        side = str(getattr(segment, "side", "") or "").strip()
        if not alignment_ref or side not in {"left", "right"}:
            continue
        inner_points = (
            _xyz_tuple(getattr(segment, "start_xyz", (0.0, 0.0, 0.0))),
            _xyz_tuple(getattr(segment, "end_xyz", (0.0, 0.0, 0.0))),
        )
        source_tie_in_edge = tie_in_edges_by_id.get(str(getattr(segment, "source_ref", "") or ""))
        source_section_refs = {
            str(getattr(source_tie_in_edge, "section_start_ref", "") or ""),
            str(getattr(source_tie_in_edge, "section_end_ref", "") or ""),
        }
        source_section_refs = {value for value in source_section_refs if value}
        candidate_sections = list(grouped_sections.get(alignment_ref, []) or [])
        if source_section_refs:
            candidate_sections = [
                section for section in candidate_sections
                if str(getattr(section, "applied_section_id", "") or "") in source_section_refs
            ]
        if not candidate_sections:
            candidate_sections = _nearest_applied_sections_to_xy_segment(
                grouped_sections.get(alignment_ref, []) or [],
                inner_points[0],
                inner_points[1],
                max_count=2,
            )
        active_station_range = _intersection_slope_face_boundary_active_station_range(
            grouped_sections.get(alignment_ref, []) or [],
            intersection_id=intersection_id,
        )
        candidate_sections = _intersection_slope_face_boundary_extended_sections(
            grouped_sections.get(alignment_ref, []) or [],
            candidate_sections,
            source_tie_in_edge=source_tie_in_edge,
            intersection_id=intersection_id,
            side=side,
            extension_length=INTERSECTION_SLOPE_FACE_BOUNDARY_EXTENSION_LENGTH,
            active_station_range=active_station_range,
        )
        applied_inner_points: list[tuple[float, float, float]] = []
        outer_points: list[tuple[float, float, float]] = []
        source_refs: list[str] = []
        projected_outer_rows: list[tuple[float, tuple[float, float, float], str, tuple[float, float, float]]] = []
        for section in candidate_sections:
            edge = _applied_section_slope_face_edge_points(
                section,
                side_label=side,
                fallback_band_width=6.0,
                fallback_band_slope=0.33,
            )
            if edge is None:
                continue
            section_inner, outer = edge
            outer_xyz = _xyz_tuple(outer)
            projection = _xy_segment_projection_ratio(
                outer_xyz,
                inner_points[0],
                inner_points[1],
            )
            projected_outer_rows.append((projection, outer_xyz, str(getattr(section, "applied_section_id", "") or ""), _xyz_tuple(section_inner)))
        for _projection, outer_xyz, source_ref, section_inner in sorted(projected_outer_rows, key=lambda item: item[0]):
            if applied_inner_points and _xy_distance((applied_inner_points[-1][0], applied_inner_points[-1][1]), (section_inner[0], section_inner[1])) <= 1.0e-6:
                continue
            if outer_points and _xy_distance((outer_points[-1][0], outer_points[-1][1]), (outer_xyz[0], outer_xyz[1])) <= 1.0e-6:
                continue
            applied_inner_points.append(section_inner)
            outer_points.append(outer_xyz)
            source_refs.append(source_ref)
        if len(outer_points) == 1 and projected_outer_rows:
            _projection, outer_xyz, source_ref, section_inner = sorted(projected_outer_rows, key=lambda item: abs(item[0] - 0.5))[0]
            vector = (
                float(outer_xyz[0]) - float(section_inner[0]),
                float(outer_xyz[1]) - float(section_inner[1]),
                float(outer_xyz[2]) - float(section_inner[2]),
            )
            outer_points = [
                (
                    float(inner_points[0][0]) + vector[0],
                    float(inner_points[0][1]) + vector[1],
                    float(inner_points[0][2]) + vector[2],
                ),
                (
                    float(inner_points[1][0]) + vector[0],
                    float(inner_points[1][1]) + vector[1],
                    float(inner_points[1][2]) + vector[2],
                ),
            ]
            source_refs = [source_ref, source_ref]
            applied_inner_points = list(inner_points)
        if len(applied_inner_points) >= 2:
            inner_points = tuple(applied_inner_points)
        row_diagnostics: list[str] = []
        if len(outer_points) < 2:
            row_diagnostics.append(
                f"warning:intersection_slope_face_boundary_outer_points_missing: {alignment_ref} {side} requires at least two Applied Section slope-face outer points."
            )
        if len(inner_points) < 2:
            row_diagnostics.append(
                f"warning:intersection_slope_face_boundary_inner_points_missing: {alignment_ref} {side} requires an Intersection Surface boundary edge."
            )
        status = "ready" if len(outer_points) >= 2 and len(inner_points) >= 2 else "warning"
        boundary_family = _intersection_slope_face_boundary_family(
            alignment_ref,
            intersection_model=intersection_model,
            intersection_id=intersection_id,
        )
        diagnostics.extend(row_diagnostics)
        rows.append(
            IntersectionSlopeFaceBoundaryRow(
                boundary_id=f"slope-face-boundary:{intersection_id or 'unknown'}:{_safe_id_fragment(alignment_ref)}:{side}",
                intersection_id=intersection_id,
                alignment_ref=alignment_ref,
                side=side,
                inner_points_xyz=tuple(inner_points),
                outer_points_xyz=tuple(outer_points),
                start_tie_edge_xyz=(inner_points[0], outer_points[0]) if outer_points else (),
                end_tie_edge_xyz=(inner_points[-1], outer_points[-1]) if outer_points else (),
                source_applied_section_refs=tuple(source_refs),
                source_intersection_surface_ref=str(getattr(segment, "boundary_segment_id", "") or ""),
                status=status,
                diagnostics=tuple(row_diagnostics),
                notes=(
                    f"inner=intersection_surface_boundary; outer=applied_sections:{len(source_refs)}; "
                    f"boundary_family={boundary_family}"
                ),
            )
        )
    ready_count = len([row for row in rows if str(getattr(row, "status", "") or "") == "ready"])
    warning_count = len([row for row in rows if str(getattr(row, "status", "") or "") == "warning"])
    status = "ready" if rows and warning_count == 0 and not _diagnostics_include_error(diagnostics) else ("warning" if rows else "missing")
    return IntersectionSlopeFaceBoundaryResult(
        schema_version=1,
        project_id=str(getattr(applied_section_set, "project_id", "") or ""),
        label=f"Intersection Slope Face Boundary - {intersection_id or 'unknown'}",
        boundary_result_id=f"intersection-slope-face-boundary:{intersection_id or 'unknown'}",
        intersection_id=intersection_id,
        status=status,
        boundary_count=len(rows),
        ready_count=ready_count,
        warning_count=warning_count,
        diagnostic_rows=diagnostics,
        boundary_rows=rows,
    )


def _xyz_tuple(point) -> tuple[float, float, float]:
    return xyz_point(point)


def _diagnostics_include_error(diagnostics: list[str] | tuple[str, ...]) -> bool:
    for value in list(diagnostics or []):
        text = str(value or "").strip().lower()
        if text and not text.startswith("warning:"):
            return True
    return False


def _safe_id_fragment(value: str) -> str:
    text = str(value or "").strip()
    for token in (":", "/", "\\", " ", "|"):
        text = text.replace(token, "-")
    return text.strip("-") or "unknown"


def _point_segment_distance_with_ratio(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[float, float]:
    return xy_point_segment_distance_with_ratio((px, py), (x1, y1), (x2, y2))


def _xy_segment_projection_ratio(
    point_xyz,
    start_xyz,
    end_xyz,
) -> float:
    return xy_segment_projection_ratio(
        _xyz_tuple(point_xyz),
        _xyz_tuple(start_xyz),
        _xyz_tuple(end_xyz),
    )


def _nearest_applied_sections_to_xy_segment(
    sections,
    start_xyz,
    end_xyz,
    *,
    max_count: int = 2,
) -> list[object]:
    ranked: list[tuple[float, float, object]] = []
    start = _xyz_tuple(start_xyz)
    end = _xyz_tuple(end_xyz)
    for section in list(sections or []):
        frame = getattr(section, "frame", None)
        if frame is None:
            continue
        x = float(getattr(frame, "x", 0.0) or 0.0)
        y = float(getattr(frame, "y", 0.0) or 0.0)
        distance, ratio = _point_segment_distance_with_ratio(x, y, start[0], start[1], end[0], end[1])
        ranked.append((float(distance), abs(float(ratio) - 0.5), section))
    ranked.sort(key=lambda item: (item[0], item[1], float(getattr(item[2], "station", 0.0) or 0.0)))
    return [section for _distance, _center_bias, section in ranked[: max(1, int(max_count or 1))]]


def _intersection_slope_face_boundary_target_segments(
    boundary_result,
    *,
    intersection_model=None,
    intersection_id: str = "",
) -> list[object]:
    tie_in_segments = [
        segment
        for segment in list(getattr(boundary_result, "segment_rows", []) or [])
        if str(getattr(segment, "segment_kind", "") or "") == "tie_in"
        and str(getattr(segment, "segment_role", "") or "") == "pavement_edge"
    ]
    if not tie_in_segments:
        return []
    source_row = _intersection_row_by_id(intersection_model, intersection_id) if intersection_model is not None else None
    primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "").strip() if source_row is not None else ""
    secondary_refs = {
        str(ref or "").strip()
        for ref in list(getattr(source_row, "secondary_alignment_refs", []) or []) if str(ref or "").strip()
    } if source_row is not None else set()
    ordered_refs = [ref for ref in [primary_ref, *sorted(secondary_refs)] if ref]
    center = _intersection_boundary_result_center_xyz(boundary_result)

    def score(segment) -> tuple[float, float]:
        start = _xyz_tuple(getattr(segment, "start_xyz", (0.0, 0.0, 0.0)))
        end = _xyz_tuple(getattr(segment, "end_xyz", (0.0, 0.0, 0.0)))
        midpoint = _midpoint_xyz(start, end)
        distance = _xy_distance((midpoint[0], midpoint[1]), (center[0], center[1]))
        length = _xy_distance((start[0], start[1]), (end[0], end[1]))
        return (float(distance), float(length))

    def alignment_order(segment) -> int:
        alignment_ref = str(getattr(segment, "alignment_ref", "") or "").strip()
        if alignment_ref in ordered_refs:
            return ordered_refs.index(alignment_ref)
        return len(ordered_refs)

    side_order = {"left": 0, "right": 1}
    selected_by_key: dict[tuple[str, str, str], object] = {}
    for segment in tie_in_segments:
        alignment_ref = str(getattr(segment, "alignment_ref", "") or "").strip()
        side = str(getattr(segment, "side", "") or "").strip()
        source_ref = str(getattr(segment, "source_ref", "") or getattr(segment, "boundary_segment_id", "") or "").strip()
        if not alignment_ref or side not in {"left", "right"}:
            continue
        key = (alignment_ref, side, source_ref)
        current = selected_by_key.get(key)
        if current is None or score(segment) > score(current):
            selected_by_key[key] = segment

    return sorted(
        selected_by_key.values(),
        key=lambda segment: (
            alignment_order(segment),
            side_order.get(str(getattr(segment, "side", "") or ""), 99),
            -score(segment)[0],
            str(getattr(segment, "boundary_segment_id", "") or ""),
        ),
    )


def _intersection_slope_face_boundary_extended_sections(
    alignment_sections,
    candidate_sections,
    *,
    source_tie_in_edge=None,
    intersection_id: str = "",
    side: str = "",
    extension_length: float = INTERSECTION_SLOPE_FACE_BOUNDARY_EXTENSION_LENGTH,
    active_station_range: tuple[float, float] | None = None,
) -> list[object]:
    ordered = _station_ordered_applied_sections(
        AppliedSectionSet(
            schema_version=1,
            project_id="",
            applied_section_set_id="intersection-slope-face-boundary:alignment-sections",
            corridor_id="",
            sections=list(alignment_sections or []),
        )
    )
    candidates = list(candidate_sections or [])
    if not ordered:
        return candidates
    if source_tie_in_edge is not None:
        start_station = float(getattr(source_tie_in_edge, "station_start", 0.0) or 0.0)
        end_station = float(getattr(source_tie_in_edge, "station_end", start_station) or start_station)
    else:
        stations = [float(getattr(section, "station", 0.0) or 0.0) for section in candidates]
        if not stations:
            stations = [float(getattr(section, "station", 0.0) or 0.0) for section in ordered]
        start_station = min(stations)
        end_station = max(stations)
    if active_station_range is not None:
        low_station = float(active_station_range[0])
        high_station = float(active_station_range[1])
    else:
        low_station = min(start_station, end_station) - max(0.0, float(extension_length or 0.0))
        high_station = max(start_station, end_station) + max(0.0, float(extension_length or 0.0))
    region_id = str(getattr(candidates[0], "region_id", "") or getattr(ordered[0], "region_id", "") or "")
    start_section = _section_at_station_for_intersection_slope_boundary(
        ordered,
        station=low_station,
        region_id=region_id,
        boundary_role=f"intersection-slope-face-start:{intersection_id}:{side}",
    )
    end_section = _section_at_station_for_intersection_slope_boundary(
        ordered,
        station=high_station,
        region_id=region_id,
        boundary_role=f"intersection-slope-face-end:{intersection_id}:{side}",
    )
    output = []
    for section in [start_section, *candidates, end_section]:
        if section is None:
            continue
        station_key = round(float(getattr(section, "station", 0.0) or 0.0), 6)
        if any(round(float(getattr(existing, "station", 0.0) or 0.0), 6) == station_key for existing in output):
            continue
        output.append(section)
    return sorted(output, key=lambda section: float(getattr(section, "station", 0.0) or 0.0))


def _intersection_slope_face_boundary_active_station_range(
    alignment_sections,
    *,
    intersection_id: str = "",
) -> tuple[float, float] | None:
    if not intersection_id:
        return None
    stations = [
        float(getattr(section, "station", 0.0) or 0.0)
        for section in list(alignment_sections or [])
        if str(getattr(section, "active_intersection_id", "") or "").strip() == intersection_id
    ]
    if len(stations) < 2:
        return None
    return (min(stations), max(stations))


def _intersection_slope_face_boundary_family(
    alignment_ref: str,
    *,
    intersection_model=None,
    intersection_id: str = "",
) -> str:
    source_row = _intersection_row_by_id(intersection_model, intersection_id) if intersection_model is not None else None
    primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "").strip() if source_row is not None else ""
    if primary_ref and str(alignment_ref or "").strip() == primary_ref:
        return "main_transition_strip"
    return "side_transition_strip"


def _section_at_station_for_intersection_slope_boundary(
    ordered_sections,
    *,
    station: float,
    region_id: str,
    boundary_role: str,
):
    ordered = list(ordered_sections or [])
    if not ordered:
        return None
    value = float(station)
    for section in ordered:
        if abs(float(getattr(section, "station", 0.0) or 0.0) - value) <= 1.0e-6:
            return section
    for index in range(len(ordered) - 1):
        first = ordered[index]
        second = ordered[index + 1]
        first_station = float(getattr(first, "station", 0.0) or 0.0)
        second_station = float(getattr(second, "station", 0.0) or 0.0)
        low = min(first_station, second_station)
        high = max(first_station, second_station)
        if low - 1.0e-6 <= value <= high + 1.0e-6:
            ratio = 0.0 if abs(second_station - first_station) <= 1.0e-9 else (value - first_station) / (second_station - first_station)
            return _interpolate_region_boundary_section(
                first,
                second,
                ratio,
                station=value,
                region_id=region_id,
                boundary_role=boundary_role,
            )
    nearest = min(ordered, key=lambda section: abs(float(getattr(section, "station", 0.0) or 0.0) - value))
    return _project_region_boundary_section(
        nearest,
        station=value,
        region_id=region_id,
        boundary_role=boundary_role,
    )


def _intersection_boundary_result_center_xyz(boundary_result) -> tuple[float, float, float]:
    centers: list[tuple[float, float, float]] = []
    points: list[tuple[float, float, float]] = []
    for row in list(getattr(boundary_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") == "arc":
            centers.append(_xyz_tuple(getattr(row, "center_xyz", (0.0, 0.0, 0.0))))
        points.append(_xyz_tuple(getattr(row, "start_xyz", (0.0, 0.0, 0.0))))
        points.append(_xyz_tuple(getattr(row, "end_xyz", (0.0, 0.0, 0.0))))
    source = centers or points
    if not source:
        return (0.0, 0.0, 0.0)
    return (
        sum(float(point[0]) for point in source) / len(source),
        sum(float(point[1]) for point in source) / len(source),
        sum(float(point[2]) for point in source) / len(source),
    )


def _applied_section_slope_face_edge_points(
    section,
    *,
    side_label: str,
    fallback_band_width: float,
    fallback_band_slope: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    frame = getattr(section, "frame", None)
    if frame is None:
        return None
    inner_offset, inner_z = _applied_section_terminal_edge(section, side_label=side_label, fallback_half_width=6.0)
    inner = _applied_section_xyz_at_offset(frame, inner_offset, inner_z)
    explicit_outer = _applied_section_explicit_slope_outer_point(section, side_label=side_label, inner_offset=inner_offset)
    if explicit_outer is not None:
        return inner, explicit_outer
    width_attr = "daylight_left_width" if side_label == "left" else "daylight_right_width"
    slope_attr = "daylight_left_slope" if side_label == "left" else "daylight_right_slope"
    width = max(float(getattr(section, width_attr, 0.0) or 0.0), 0.0)
    if width <= 1.0e-9:
        return None
    slope = abs(float(getattr(section, slope_attr, 0.0) or 0.0))
    if slope <= 1.0e-9:
        slope = abs(float(fallback_band_slope or 0.0))
    normal_x, normal_y = _applied_section_outward_normal(frame, side_label=side_label)
    return inner, (
        float(inner[0]) + normal_x * width,
        float(inner[1]) + normal_y * width,
        float(inner[2]) - abs(float(slope)) * width,
    )


def _applied_section_terminal_edge(section, *, side_label: str, fallback_half_width: float) -> tuple[float, float]:
    frame = getattr(section, "frame", None)
    frame_z = float(getattr(frame, "z", 0.0) or 0.0)
    left_width = float(getattr(section, "surface_left_width", 0.0) or 0.0)
    right_width = float(getattr(section, "surface_right_width", 0.0) or 0.0)
    if left_width <= 0.0 and right_width <= 0.0:
        left_width = right_width = float(fallback_half_width)
    elif left_width <= 0.0:
        left_width = right_width
    elif right_width <= 0.0:
        right_width = left_width
    edge = (max(left_width, 0.1), frame_z) if side_label == "left" else (-max(right_width, 0.1), frame_z)
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"fg_surface", "ditch_surface"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        z = float(getattr(point, "z", frame_z) or frame_z)
        if side_label == "left":
            if offset > edge[0] or (abs(offset - edge[0]) <= 1.0e-9 and z > edge[1]):
                edge = (offset, z)
        elif offset < edge[0] or (abs(offset - edge[0]) <= 1.0e-9 and z > edge[1]):
            edge = (offset, z)
    return edge


def _applied_section_explicit_slope_outer_point(section, *, side_label: str, inner_offset: float) -> tuple[float, float, float] | None:
    direction = 1.0 if side_label == "left" else -1.0
    candidates: list[object] = []
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"daylight_marker", "side_slope_surface", "bench_surface"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        if (offset - float(inner_offset)) * direction < -1.0e-9:
            continue
        candidates.append(point)
    if not candidates:
        return None
    chosen = max(
        candidates,
        key=lambda point: abs(float(getattr(point, "lateral_offset", 0.0) or 0.0) - float(inner_offset)),
    )
    return (
        float(getattr(chosen, "x", 0.0) or 0.0),
        float(getattr(chosen, "y", 0.0) or 0.0),
        float(getattr(chosen, "z", 0.0) or 0.0),
    )


def _applied_section_xyz_at_offset(frame, offset: float, z: float) -> tuple[float, float, float]:
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    return (
        float(getattr(frame, "x", 0.0) or 0.0) + normal_x * float(offset),
        float(getattr(frame, "y", 0.0) or 0.0) + normal_y * float(offset),
        float(z),
    )


def _applied_section_outward_normal(frame, *, side_label: str) -> tuple[float, float]:
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    if side_label == "right":
        return -normal_x, -normal_y
    return normal_x, normal_y


def _midpoint_xyz(first: tuple[float, float, float], second: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        (float(first[0]) + float(second[0])) * 0.5,
        (float(first[1]) + float(second[1])) * 0.5,
        (float(first[2]) + float(second[2])) * 0.5,
    )


def _xy_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return xy_distance(a, b)


__all__ = [
    "IntersectionSlopeFaceBoundaryEvaluationRequest",
    "IntersectionSlopeFaceBoundaryEvaluationService",
    "intersection_slope_face_boundary_target_segments",
]

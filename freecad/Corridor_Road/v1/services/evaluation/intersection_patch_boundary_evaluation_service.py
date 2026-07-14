"""Evaluate ordered Intersection patch-boundary result contracts."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ...models.result.intersection_patch_boundary import (
    IntersectionPatchBoundaryPointRow,
    IntersectionPatchBoundaryResult,
)
from ..geometry import (
    xy_distance,
    xy_point_in_polygon,
    xy_polygon_boundaries_intersect,
    xy_polygon_self_intersects,
    xy_polygon_signed_area,
    xyz_point,
    xyz_polygon_union_outer_boundary,
)


@dataclass(frozen=True)
class IntersectionPatchBoundaryEvaluationRequest:
    boundary_segment_result: object


class IntersectionPatchBoundaryEvaluationService:
    """Build ordered patch rings from accepted boundary-segment results."""

    def evaluate(
        self,
        request: IntersectionPatchBoundaryEvaluationRequest,
    ) -> IntersectionPatchBoundaryResult:
        boundary_result = request.boundary_segment_result
        intersection_id = str(
            getattr(boundary_result, "intersection_id", "") or ""
        ).strip()
        diagnostics = [
            str(value or "")
            for value in list(getattr(boundary_result, "diagnostic_rows", []) or [])
            if str(value or "")
        ]
        union_result = _from_tie_in_union(boundary_result, diagnostics)
        if union_result is not None:
            return union_result

        ring_raw_points: dict[
            str,
            list[tuple[tuple[float, float, float], str, str, str, str]],
        ] = {}
        for segment in list(getattr(boundary_result, "segment_rows", []) or []):
            segment_id = str(
                getattr(segment, "boundary_segment_id", "") or ""
            )
            segment_kind = str(getattr(segment, "segment_kind", "") or "")
            segment_role = _ring_role(segment)
            ring_id = _ring_id(segment, segment_role)
            ring_points = ring_raw_points.setdefault(ring_id, [])
            chord_points = list(
                getattr(segment, "chord_points_xyz", ()) or ()
            )
            if chord_points:
                for point in chord_points:
                    ring_points.append(
                        (
                            xyz_point(point),
                            segment_id,
                            segment_kind,
                            segment_role,
                            ring_id,
                        )
                    )
                continue
            for attribute in ("start_xyz", "end_xyz"):
                ring_points.append(
                    (
                        xyz_point(
                            getattr(segment, attribute, (0.0, 0.0, 0.0))
                        ),
                        segment_id,
                        segment_kind,
                        segment_role,
                        ring_id,
                    )
                )

        ordered_rings = []
        for ring_id, raw_points in ring_raw_points.items():
            ordered = _ordered_ring_points(raw_points)
            if ordered:
                ring_role = str(ordered[0][5] or "outer")
                ordered_rings.append((ring_id, ring_role, ordered))
        ordered_rings.sort(key=_ring_sort_key)
        outer_ordered = [
            point
            for _ring_id, ring_role, points in ordered_rings
            if ring_role == "outer"
            for point in points
        ]
        if len(outer_ordered) < 3:
            diagnostics.append(
                "intersection_patch_boundary_too_few_points: ordered outer "
                "boundary requires at least 3 unique points, found "
                f"{len(outer_ordered)}."
            )

        point_rows = _point_rows(intersection_id, ordered_rings)
        outer_rows = [
            row
            for row in point_rows
            if str(getattr(row, "ring_role", "") or "outer") == "outer"
        ]
        polygon_area = _multiring_area(point_rows)
        outer_area = abs(xy_polygon_signed_area(outer_rows))
        self_crossing = xy_polygon_self_intersects(outer_rows)
        diagnostics.extend(_multiring_diagnostics(point_rows))
        if outer_area <= 1.0e-6 and len(outer_rows) >= 3:
            diagnostics.append(
                "intersection_patch_boundary_zero_area: ordered boundary "
                "polygon area is too small."
            )
        if self_crossing:
            diagnostics.append(
                "intersection_patch_boundary_self_crossing: ordered boundary "
                "candidate has crossing XY edges."
            )
        closed = len(outer_rows) >= 3 and not _diagnostics_include_error(
            diagnostics
        )
        status = "ready" if closed else ("warning" if outer_rows else "missing")
        counts = _ring_counts(point_rows)
        return IntersectionPatchBoundaryResult(
            schema_version=1,
            project_id=str(getattr(boundary_result, "project_id", "") or ""),
            label=f"Intersection Patch Boundary - {intersection_id}",
            patch_boundary_result_id=(
                f"intersection-patch-boundary:{intersection_id or 'unknown'}"
            ),
            intersection_id=intersection_id,
            status=status,
            boundary_point_count=len(point_rows),
            source_segment_count=int(
                getattr(boundary_result, "segment_count", 0) or 0
            ),
            ring_count=sum(counts.values()),
            outer_ring_count=counts["outer"],
            hole_ring_count=counts["hole"],
            island_ring_count=counts["island"],
            closed=closed,
            polygon_area=polygon_area,
            self_crossing=self_crossing,
            diagnostic_rows=diagnostics,
            point_rows=point_rows,
        )

    def evaluate_context(self, boundary_segment_result):
        """Adapt the boundary-context evaluator signature to the typed request."""

        return self.evaluate(
            IntersectionPatchBoundaryEvaluationRequest(
                boundary_segment_result=boundary_segment_result,
            )
        )


def _from_tie_in_union(boundary_result, diagnostics):
    tie_in_rows = [
        row
        for row in list(getattr(boundary_result, "segment_rows", []) or [])
        if str(getattr(row, "segment_kind", "") or "") == "tie_in"
    ]
    grouped = {}
    for row in tie_in_rows:
        alignment_ref = str(getattr(row, "alignment_ref", "") or "").strip()
        if alignment_ref:
            grouped.setdefault(alignment_ref, []).append(row)
    polygons = []
    for alignment_ref, rows in grouped.items():
        polygon = _tie_in_strip_polygon(rows)
        if polygon is None:
            diagnostics.append(
                "warning:intersection_tie_in_strip_incomplete: "
                f"{alignment_ref} cannot form a pavement strip boundary."
            )
            continue
        polygons.append(polygon)
    if len(polygons) < 2:
        return None
    union_points = xyz_polygon_union_outer_boundary(polygons)
    if len(union_points) < 3:
        diagnostics.append(
            "warning:intersection_patch_boundary_union_failed: tie-in strip "
            "union could not produce an outer boundary."
        )
        return None
    intersection_id = str(
        getattr(boundary_result, "intersection_id", "") or ""
    ).strip()
    point_rows = [
        IntersectionPatchBoundaryPointRow(
            boundary_point_id=(
                f"patch-boundary:{intersection_id or 'unknown'}:"
                f"tie-in-union:{index}"
            ),
            intersection_id=intersection_id,
            order_index=index,
            x=float(point[0]),
            y=float(point[1]),
            z=float(point[2]),
            source_segment_ref="tie-in-strip-union",
            source_kind="tie_in_union",
            ring_id="outer",
            ring_role="outer",
            status="candidate",
            notes="intersection patch boundary from pavement strip union",
        )
        for index, point in enumerate(union_points, start=1)
    ]
    polygon_area = abs(xy_polygon_signed_area(point_rows))
    self_crossing = xy_polygon_self_intersects(point_rows)
    output_diagnostics = list(diagnostics or [])
    output_diagnostics.extend(_multiring_diagnostics(point_rows))
    if polygon_area <= 1.0e-6:
        output_diagnostics.append(
            "intersection_patch_boundary_zero_area: tie-in union boundary "
            "polygon area is too small."
        )
    if self_crossing:
        output_diagnostics.append(
            "intersection_patch_boundary_self_crossing: tie-in union boundary "
            "has crossing XY edges."
        )
    closed = len(point_rows) >= 3 and not _diagnostics_include_error(
        output_diagnostics
    )
    return IntersectionPatchBoundaryResult(
        schema_version=1,
        project_id=str(getattr(boundary_result, "project_id", "") or ""),
        label=f"Intersection Patch Boundary - {intersection_id}",
        patch_boundary_result_id=(
            f"intersection-patch-boundary:{intersection_id or 'unknown'}"
        ),
        intersection_id=intersection_id,
        boundary_mode="tie_in_strip_union",
        status="ready" if closed else "warning",
        boundary_point_count=len(point_rows),
        source_segment_count=len(tie_in_rows),
        ring_count=1,
        outer_ring_count=1,
        hole_ring_count=0,
        island_ring_count=0,
        closed=closed,
        polygon_area=polygon_area,
        self_crossing=self_crossing,
        diagnostic_rows=output_diagnostics,
        point_rows=point_rows,
    )


def _tie_in_strip_polygon(rows):
    if len(rows) < 2:
        return None
    ordered_rows = sorted(
        rows,
        key=lambda row: float(getattr(row, "station_start", 0.0) or 0.0),
    )
    first, second = ordered_rows[:2]
    first_start = xyz_point(getattr(first, "start_xyz", (0.0, 0.0, 0.0)))
    first_end = xyz_point(getattr(first, "end_xyz", (0.0, 0.0, 0.0)))
    second_start = xyz_point(getattr(second, "start_xyz", (0.0, 0.0, 0.0)))
    second_end = xyz_point(getattr(second, "end_xyz", (0.0, 0.0, 0.0)))
    candidates = (
        [first_start, first_end, second_end, second_start],
        [first_start, second_start, second_end, first_end],
    )
    normalized = [
        polygon
        for polygon in (_normalize_strip_polygon(candidate) for candidate in candidates)
        if polygon is not None
    ]
    valid = [
        polygon
        for polygon in normalized
        if abs(xy_polygon_signed_area(polygon)) > 1.0e-6
        and not xy_polygon_self_intersects(polygon)
    ]
    if valid:
        return max(valid, key=lambda polygon: abs(xy_polygon_signed_area(polygon)))
    if not normalized:
        return None
    best = max(
        normalized,
        key=lambda polygon: abs(xy_polygon_signed_area(polygon)),
    )
    return best if abs(xy_polygon_signed_area(best)) > 1.0e-6 else None


def _normalize_strip_polygon(points, *, tolerance=1.0e-6):
    normalized = []
    for point in list(points or []):
        xyz = xyz_point(point)
        if normalized and xy_distance(xyz, normalized[-1]) <= tolerance:
            continue
        if any(xy_distance(xyz, existing) <= tolerance for existing in normalized):
            continue
        normalized.append(xyz)
    if len(normalized) >= 2 and xy_distance(
        normalized[0], normalized[-1]
    ) <= tolerance:
        normalized.pop()
    if len(normalized) < 3:
        return None
    area = xy_polygon_signed_area(normalized)
    if abs(area) <= 1.0e-6:
        return None
    if area < 0.0:
        normalized.reverse()
    return normalized


def _ring_role(segment) -> str:
    text = " ".join(
        (
            str(getattr(segment, "segment_role", "") or ""),
            str(getattr(segment, "segment_kind", "") or ""),
            str(getattr(segment, "notes", "") or ""),
        )
    ).strip().lower()
    if any(token in text for token in ("hole", "void", "opening")):
        return "hole"
    if "island" in text:
        return "island"
    return "outer"


def _ring_id(segment, ring_role: str) -> str:
    text = str(getattr(segment, "segment_role", "") or "").strip()
    if ":" in text:
        return text
    role = str(ring_role or "outer").strip() or "outer"
    if role == "outer":
        return "outer"
    source_ref = str(getattr(segment, "source_ref", "") or "").strip()
    if source_ref:
        return f"{role}:{_safe_id_fragment(source_ref)}"
    segment_id = str(
        getattr(segment, "boundary_segment_id", "") or ""
    ).strip()
    if segment_id:
        prefix = f"boundary:{role}-"
        if segment_id.startswith(prefix):
            return f"{role}:{segment_id[len(prefix):].split(':')[0]}"
        return f"{role}:{_safe_id_fragment(segment_id)}"
    return role


def _ordered_ring_points(raw_points):
    unique_points = {}
    for point, segment_id, segment_kind, segment_role, ring_id in raw_points:
        key = (round(float(point[0]), 6), round(float(point[1]), 6))
        unique_points.setdefault(
            key,
            (
                point[0],
                point[1],
                point[2],
                segment_id,
                segment_kind,
                segment_role,
                ring_id,
            ),
        )
    if len(unique_points) < 3:
        return list(unique_points.values())
    center_x = sum(point[0] for point in unique_points.values()) / len(
        unique_points
    )
    center_y = sum(point[1] for point in unique_points.values()) / len(
        unique_points
    )
    return sorted(
        unique_points.values(),
        key=lambda point: math.atan2(point[1] - center_y, point[0] - center_x),
    )


def _ring_sort_key(item):
    role_order = {"outer": 0, "hole": 1, "island": 2}
    return (role_order.get(item[1], 2), item[0])


def _point_rows(intersection_id, ordered_rings):
    output = []
    order_index = 1
    for ring_id, ring_role, ordered in ordered_rings:
        for point in ordered:
            output.append(
                IntersectionPatchBoundaryPointRow(
                    boundary_point_id=(
                        f"patch-boundary:{intersection_id or 'unknown'}:"
                        f"{ring_id}:{order_index}"
                    ),
                    intersection_id=intersection_id,
                    order_index=order_index,
                    x=float(point[0]),
                    y=float(point[1]),
                    z=float(point[2]),
                    source_segment_ref=str(point[3] or ""),
                    source_kind=str(point[4] or ""),
                    ring_id=str(point[6] or ring_id),
                    ring_role=str(point[5] or ring_role),
                    status="candidate",
                )
            )
            order_index += 1
    return output


def _ring_counts(point_rows):
    return {
        role: len(
            {
                str(getattr(row, "ring_id", "") or "")
                for row in point_rows
                if str(getattr(row, "ring_role", "") or "") == role
            }
        )
        for role in ("outer", "hole", "island")
    }


def _group_rings(point_rows):
    grouped = {}
    roles = {}
    for row in list(point_rows or []):
        ring_id = str(getattr(row, "ring_id", "") or "outer")
        grouped.setdefault(ring_id, []).append(row)
        roles[ring_id] = str(getattr(row, "ring_role", "") or "outer")
    return grouped, roles


def _multiring_area(point_rows) -> float:
    grouped, roles = _group_rings(point_rows)
    area = 0.0
    for ring_id, rows in grouped.items():
        ordered = sorted(rows, key=lambda row: int(row.order_index or 0))
        ring_area = abs(xy_polygon_signed_area(ordered))
        area += -ring_area if roles.get(ring_id, "outer") == "hole" else ring_area
    return max(area, 0.0)


def _multiring_diagnostics(point_rows):
    grouped, roles = _group_rings(point_rows)
    diagnostics = []
    outer_rows = _primary_outer_ring(grouped, roles)
    outer_polygon = [(float(row.x), float(row.y)) for row in outer_rows]
    for ring_id, rows in grouped.items():
        ordered = sorted(rows, key=lambda row: int(row.order_index or 0))
        role = roles.get(ring_id, "outer")
        if len(ordered) < 3:
            diagnostics.append(
                "intersection_patch_boundary_ring_too_few_points: "
                f"{ring_id} has fewer than 3 point(s)."
            )
            continue
        if abs(xy_polygon_signed_area(ordered)) <= 1.0e-6:
            diagnostics.append(
                f"intersection_patch_boundary_ring_zero_area: {ring_id} "
                "area is too small."
            )
        if xy_polygon_self_intersects(ordered):
            diagnostics.append(
                "intersection_patch_boundary_ring_self_crossing: "
                f"{ring_id} has crossing XY edges."
            )
        if role == "outer":
            continue
        if len(outer_polygon) >= 3:
            centroid = _ring_centroid(ordered)
            if not xy_point_in_polygon(centroid, outer_polygon):
                diagnostics.append(
                    "intersection_patch_boundary_inner_ring_outside_outer: "
                    f"{ring_id} is outside the outer ring."
                )
            elif _rings_intersect(ordered, outer_rows):
                diagnostics.append(
                    "intersection_patch_boundary_inner_ring_intersects_outer: "
                    f"{ring_id} intersects the outer ring."
                )
    inner_ids = [
        ring_id
        for ring_id, role in roles.items()
        if role in {"hole", "island"}
    ]
    for index, ring_id in enumerate(inner_ids):
        first = sorted(
            grouped.get(ring_id, []),
            key=lambda row: int(row.order_index or 0),
        )
        for other_id in inner_ids[index + 1 :]:
            second = sorted(
                grouped.get(other_id, []),
                key=lambda row: int(row.order_index or 0),
            )
            if _rings_intersect(first, second):
                diagnostics.append(
                    "intersection_patch_boundary_inner_rings_intersect: "
                    f"{ring_id} intersects {other_id}."
                )
    return diagnostics


def _primary_outer_ring(grouped, roles):
    candidates = [
        sorted(rows, key=lambda row: int(row.order_index or 0))
        for ring_id, rows in grouped.items()
        if roles.get(ring_id, "outer") == "outer"
    ]
    return (
        max(candidates, key=lambda rows: abs(xy_polygon_signed_area(rows)))
        if candidates
        else []
    )


def _ring_centroid(point_rows):
    if not point_rows:
        return (0.0, 0.0)
    return (
        sum(float(row.x) for row in point_rows) / len(point_rows),
        sum(float(row.y) for row in point_rows) / len(point_rows),
    )


def _rings_intersect(first, second) -> bool:
    return xy_polygon_boundaries_intersect(first, second)


def _diagnostics_include_error(diagnostics) -> bool:
    return any(
        text and not text.startswith("warning:")
        for text in (str(value or "").strip().lower() for value in diagnostics or [])
    )


def _safe_id_fragment(value: str) -> str:
    text = str(value or "").strip()
    for token in (":", "/", "\\", " ", "|"):
        text = text.replace(token, "-")
    return text.strip("-") or "unknown"

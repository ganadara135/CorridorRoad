"""Select a traceable non-roundabout Intersection patch boundary."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ...models.result.intersection_patch_boundary_selection import (
    IntersectionPatchBoundarySelectionResult,
)
from ...models.result.tin_surface import TINVertex


@dataclass(frozen=True)
class IntersectionPatchBoundarySelectionRequest:
    source_vertices: tuple[object, ...]
    patch_boundary_result: object | None = None
    boundary_loop_result: object | None = None
    grading_plane: tuple[float, float, float] | None = None
    grading_mode: str = ""
    boundary_evaluation_failed: bool = False


class IntersectionPatchBoundarySelectionService:
    """Apply boundary priority and source-preserving elevation rules."""

    def select(
        self,
        request: IntersectionPatchBoundarySelectionRequest,
    ) -> IntersectionPatchBoundarySelectionResult:
        patch = request.patch_boundary_result
        point_count = int(getattr(patch, "boundary_point_count", 0) or 0)
        source_segment_count = int(
            getattr(patch, "source_segment_count", 0) or 0
        )
        closed = bool(getattr(patch, "closed", False))
        diagnostics = list(getattr(patch, "diagnostic_rows", []) or [])
        diagnostic_count = len(diagnostics)
        if request.boundary_evaluation_failed:
            diagnostic_count = max(diagnostic_count, 1)
        polygon_area = float(getattr(patch, "polygon_area", 0.0) or 0.0)
        self_crossing = bool(getattr(patch, "self_crossing", False))
        ring_count = int(getattr(patch, "ring_count", 0) or 0)
        hole_count = int(getattr(patch, "hole_ring_count", 0) or 0)
        island_count = int(getattr(patch, "island_ring_count", 0) or 0)
        boundary_source = "convex_hull_fallback"
        boundary_loop_source = ""
        boundary_loop_point_count = 0
        boundary_loop_segment_count = 0
        vertices: list[TINVertex] = []
        loop_row = self.ready_outer_loop(request.boundary_loop_result)
        if loop_row is not None:
            candidate = self.boundary_loop_vertices(
                loop_row,
                source_vertices=list(request.source_vertices),
                grading_plane=request.grading_plane,
                grading_mode=request.grading_mode,
            )
            if len(candidate) >= 3:
                vertices = candidate
                boundary_source = "authoritative_boundary_loop"
                boundary_loop_source = "intersection_boundary_loop"
                boundary_loop_point_count = int(
                    getattr(loop_row, "point_count", 0) or len(candidate)
                )
                boundary_loop_segment_count = int(
                    getattr(loop_row, "segment_count", 0) or 0
                )
        if boundary_source != "authoritative_boundary_loop" and closed and point_count >= 3:
            candidate = self.patch_boundary_vertices(
                patch,
                source_vertices=list(request.source_vertices),
                grading_plane=request.grading_plane,
                grading_mode=request.grading_mode,
            )
            if len(candidate) >= 3:
                vertices = candidate
                boundary_source = "ordered_patch_boundary"
        if not vertices:
            vertices = self.convex_hull(list(request.source_vertices))
        if len(vertices) < 3:
            message = (
                "intersection_patch_boundary_too_few_points: at least three "
                "unique patch boundary points are required."
            )
            return IntersectionPatchBoundarySelectionResult(
                status="error",
                boundary_source=boundary_source,
                vertex_rows=tuple(vertices),
                patch_boundary_point_count=point_count,
                patch_boundary_source_segment_count=source_segment_count,
                patch_boundary_closed=closed,
                patch_boundary_diagnostic_count=diagnostic_count,
                patch_boundary_polygon_area=polygon_area,
                patch_boundary_self_crossing=self_crossing,
                patch_boundary_ring_count=ring_count,
                patch_boundary_hole_ring_count=hole_count,
                patch_boundary_island_ring_count=island_count,
                diagnostic_rows=("intersection_patch_boundary_too_few_points",),
                error_message=message,
            )
        output_diagnostics = (
            ("intersection_patch_boundary_fallback:convex_hull_fallback",)
            if boundary_source == "convex_hull_fallback"
            else ()
        )
        return IntersectionPatchBoundarySelectionResult(
            status="ready",
            boundary_source=boundary_source,
            vertex_rows=tuple(vertices),
            patch_boundary_point_count=point_count,
            patch_boundary_source_segment_count=source_segment_count,
            patch_boundary_closed=closed,
            patch_boundary_diagnostic_count=diagnostic_count,
            patch_boundary_polygon_area=polygon_area,
            patch_boundary_self_crossing=self_crossing,
            patch_boundary_ring_count=ring_count,
            patch_boundary_hole_ring_count=hole_count,
            patch_boundary_island_ring_count=island_count,
            boundary_loop_point_count=boundary_loop_point_count,
            boundary_loop_segment_count=boundary_loop_segment_count,
            boundary_loop_source=boundary_loop_source,
            fallback_used=boundary_source == "convex_hull_fallback",
            diagnostic_rows=output_diagnostics,
        )

    def ready_outer_loop(self, boundary_loop_result: object | None):
        candidates = [
            row
            for row in list(getattr(boundary_loop_result, "loop_rows", []) or [])
            if str(getattr(row, "loop_role", "") or "")
            == "outer_intersection_boundary"
            and str(getattr(row, "status", "") or "") == "ready"
            and bool(getattr(row, "closed", False))
        ]
        candidates.sort(
            key=lambda row: (
                -float(getattr(row, "area_xy", 0.0) or 0.0),
                str(getattr(row, "loop_id", "") or ""),
            )
        )
        return candidates[0] if candidates else None

    def patch_boundary_vertices(
        self,
        patch_boundary_result: object,
        *,
        source_vertices: list[object],
        grading_plane: tuple[float, float, float] | None = None,
        grading_mode: str = "",
    ) -> list[TINVertex]:
        output = []
        seen_xy = set()
        for row in list(getattr(patch_boundary_result, "point_rows", []) or []):
            x = float(getattr(row, "x", 0.0) or 0.0)
            y = float(getattr(row, "y", 0.0) or 0.0)
            key = (round(x, 6), round(y, 6))
            if key in seen_xy:
                continue
            seen_xy.add(key)
            nearest = _nearest_vertex(source_vertices, x, y)
            z, elevation_ref, elevation_notes = _boundary_elevation(
                x,
                y,
                fallback_z=float(getattr(row, "z", 0.0) or 0.0),
                nearest=nearest,
                grading_plane=grading_plane,
                grading_mode=grading_mode,
            )
            output.append(
                TINVertex(
                    vertex_id=f"v{len(output) + 1}",
                    x=x,
                    y=y,
                    z=z,
                    source_point_ref=str(
                        getattr(row, "boundary_point_id", "") or ""
                    ),
                    notes=(
                        "ordered_patch_boundary; "
                        f"source_segment={getattr(row, 'source_segment_ref', '')}; "
                        f"source_kind={getattr(row, 'source_kind', '')}; "
                        f"elevation_source={elevation_ref}; "
                        f"elevation_source_notes={elevation_notes}"
                    ),
                )
            )
        return output

    def boundary_loop_vertices(
        self,
        boundary_loop_row: object,
        *,
        source_vertices: list[object],
        grading_plane: tuple[float, float, float] | None = None,
        grading_mode: str = "",
    ) -> list[TINVertex]:
        raw_points = [
            _xyz_point(point)
            for point in list(
                getattr(boundary_loop_row, "loop_points_xyz", ()) or []
            )
        ]
        if len(raw_points) >= 2 and _xy_key(raw_points[0]) == _xy_key(
            raw_points[-1]
        ):
            raw_points = raw_points[:-1]
        output = []
        seen_xy = set()
        loop_id = str(getattr(boundary_loop_row, "loop_id", "") or "")
        for point in raw_points:
            x, y, fallback_z = point
            key = (round(x, 6), round(y, 6))
            if key in seen_xy:
                continue
            seen_xy.add(key)
            nearest = _nearest_vertex(source_vertices, x, y)
            z, elevation_ref, elevation_notes = _boundary_elevation(
                x,
                y,
                fallback_z=fallback_z,
                nearest=nearest,
                grading_plane=grading_plane,
                grading_mode=grading_mode,
                zero_nearest_uses_fallback=True,
            )
            output.append(
                TINVertex(
                    vertex_id=f"v{len(output) + 1}",
                    x=x,
                    y=y,
                    z=z,
                    source_point_ref=f"{loop_id}:point:{len(output) + 1:02d}",
                    notes=(
                        f"authoritative_boundary_loop; loop={loop_id}; "
                        f"elevation_source={elevation_ref}; "
                        f"elevation_source_notes={elevation_notes}"
                    ),
                )
            )
        return output

    def convex_hull(self, vertices: list[object]) -> list[object]:
        unique = {}
        for vertex in vertices:
            key = (
                round(float(getattr(vertex, "x", 0.0) or 0.0), 6),
                round(float(getattr(vertex, "y", 0.0) or 0.0), 6),
            )
            unique.setdefault(key, vertex)
        points = sorted(unique.items())
        if len(points) <= 3:
            return _angle_sorted_vertices(points)

        def cross(origin, first, second):
            return (
                (first[0] - origin[0]) * (second[1] - origin[1])
                - (first[1] - origin[1]) * (second[0] - origin[0])
            )

        lower = []
        for item in points:
            while len(lower) >= 2 and cross(
                lower[-2][0], lower[-1][0], item[0]
            ) <= 0.0:
                lower.pop()
            lower.append(item)
        upper = []
        for item in reversed(points):
            while len(upper) >= 2 and cross(
                upper[-2][0], upper[-1][0], item[0]
            ) <= 0.0:
                upper.pop()
            upper.append(item)
        hull = lower[:-1] + upper[:-1]
        return (
            [vertex for _key, vertex in hull]
            if len(hull) >= 3
            else _angle_sorted_vertices(points)
        )


def _boundary_elevation(
    x: float,
    y: float,
    *,
    fallback_z: float,
    nearest: object | None,
    grading_plane: tuple[float, float, float] | None,
    grading_mode: str,
    zero_nearest_uses_fallback: bool = False,
) -> tuple[float, str, str]:
    if grading_plane is not None:
        a, b, c = grading_plane
        return (
            float(a) * x + float(b) * y + float(c),
            "intersection_grading_plane",
            f"intersection_grading={grading_mode}; "
            "blend_basis=primary_side_plane",
        )
    if nearest is not None:
        nearest_z = getattr(nearest, "z", fallback_z)
        if zero_nearest_uses_fallback:
            nearest_z = nearest_z or fallback_z
        return (
            float(nearest_z or 0.0),
            str(getattr(nearest, "source_point_ref", "") or ""),
            str(getattr(nearest, "notes", "") or ""),
        )
    return (fallback_z, "", "")


def _nearest_vertex(vertices: list[object], x: float, y: float):
    nearest = None
    nearest_distance = None
    for vertex in vertices:
        dx = float(getattr(vertex, "x", 0.0) or 0.0) - x
        dy = float(getattr(vertex, "y", 0.0) or 0.0) - y
        distance = dx * dx + dy * dy
        if nearest_distance is None or distance < nearest_distance:
            nearest = vertex
            nearest_distance = distance
    return nearest


def _xyz_point(value: object) -> tuple[float, float, float]:
    values = tuple(value or ())
    return (
        float(values[0]) if len(values) > 0 else 0.0,
        float(values[1]) if len(values) > 1 else 0.0,
        float(values[2]) if len(values) > 2 else 0.0,
    )


def _xy_key(point: tuple[float, float, float]) -> tuple[float, float]:
    return (round(point[0], 6), round(point[1], 6))


def _angle_sorted_vertices(points):
    if not points:
        return []
    center_x = sum(
        float(getattr(vertex, "x", 0.0) or 0.0) for _key, vertex in points
    ) / len(points)
    center_y = sum(
        float(getattr(vertex, "y", 0.0) or 0.0) for _key, vertex in points
    ) / len(points)
    return sorted(
        [vertex for _key, vertex in points],
        key=lambda vertex: math.atan2(
            float(getattr(vertex, "y", 0.0) or 0.0) - center_y,
            float(getattr(vertex, "x", 0.0) or 0.0) - center_x,
        ),
    )

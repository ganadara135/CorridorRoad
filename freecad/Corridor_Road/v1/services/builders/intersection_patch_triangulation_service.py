"""Select a non-roundabout Intersection patch triangulation path."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Mapping

from ...models.result.intersection_boundary_segment import (
    IntersectionBoundarySegmentRow,
)
from ...models.result.intersection_patch_triangulation import (
    IntersectionPatchTriangulationResult,
)
from ...models.result.tin_surface import TINTriangle, TINVertex
from ..geometry import (
    ear_clip_triangulation_indices,
    xy_closed_edges,
    xy_distance,
    xy_point_in_polygon_strict,
    xy_polygon_self_intersects,
    xy_polygon_signed_area,
    xy_triangle_signed_area,
    xyz_point,
    xyz_segment_intersection_point,
)


TriangulationBuilder = Callable[..., Mapping[str, object]]


@dataclass(frozen=True)
class IntersectionPatchTriangulationRequest:
    boundary_source: str
    boundary_vertices: tuple[object, ...]
    center_vertex: object
    intersection_id: str
    policy: Mapping[str, float] | None = None
    tie_in_result: object | None = None
    intersection_model: object | None = None
    boundary_segment_result: object | None = None


class IntersectionPatchTriangulationService:
    """Own triangulation priority, fallback, and normalized result metadata."""

    def __init__(
        self,
        *,
        ordered_polygon_builder: TriangulationBuilder | None = None,
        structured_strip_builder: TriangulationBuilder | None = None,
    ) -> None:
        self.ordered_polygon_builder = ordered_polygon_builder
        self.structured_strip_builder = structured_strip_builder

    def triangulate(
        self,
        request: IntersectionPatchTriangulationRequest,
    ) -> IntersectionPatchTriangulationResult:
        policy = dict(request.policy or {})
        fallback_used = False
        if request.boundary_source == "authoritative_boundary_loop":
            selection_path = "ordered_polygon_authoritative"
            result = self._run_ordered(request, policy)
        else:
            if self.structured_strip_builder is None:
                structured_builder = self.structured_strip_triangulation
            else:
                structured_builder = self.structured_strip_builder
            selection_path = "structured_strip"
            try:
                result = structured_builder(
                    request.tie_in_result,
                    source_vertices=list(request.boundary_vertices),
                    center=request.center_vertex,
                    intersection_model=request.intersection_model,
                    boundary_segment_result=request.boundary_segment_result,
                    intersection_id=request.intersection_id,
                    policy=policy,
                )
            except Exception as exc:
                return self._builder_error(exc)
            if not list(result.get("triangles", []) or []):
                selection_path = "ordered_polygon_fallback"
                fallback_used = True
                result = self._run_ordered(request, policy)
        if isinstance(result, IntersectionPatchTriangulationResult):
            return result
        triangles = tuple(result.get("triangles", ()) or ())
        default_vertices = (*request.boundary_vertices, request.center_vertex)
        vertices = tuple(result.get("vertices", default_vertices) or default_vertices)
        if not triangles:
            return IntersectionPatchTriangulationResult(
                status="error",
                selection_path=selection_path,
                vertex_rows=vertices,
                fallback_used=fallback_used,
                diagnostic_rows=("intersection_patch_degenerate_triangle",),
                error_message=(
                    "intersection_patch_degenerate_triangle: ordered patch "
                    "boundary did not produce usable triangles."
                ),
            )
        diagnostics = (
            ("intersection_patch_triangulation_fallback:ordered_polygon",)
            if fallback_used
            else ()
        )
        return IntersectionPatchTriangulationResult(
            status="ready",
            selection_path=selection_path,
            vertex_rows=vertices,
            triangle_rows=triangles,
            degenerate_count=int(result.get("degenerate_count", 0) or 0),
            max_edge_length=float(result.get("max_edge_length", 0.0) or 0.0),
            long_edge_count=int(result.get("long_edge_count", 0) or 0),
            long_edge_factor=float(result.get("long_edge_factor", 2.5) or 2.5),
            long_edge_limit=float(result.get("long_edge_limit", 0.0) or 0.0),
            max_boundary_edge_length_policy=float(
                result.get("max_boundary_edge_length_policy", 0.0) or 0.0
            ),
            boundary_strategy=str(
                result.get("boundary_strategy", "ordered_polygon")
                or "ordered_polygon"
            ),
            structured_strip_count=int(
                result.get("structured_strip_count", 0) or 0
            ),
            curb_return_surface_edge_count=int(
                result.get("curb_return_surface_edge_count", 0) or 0
            ),
            curb_return_arc_count=int(
                result.get("curb_return_arc_count", 0) or 0
            ),
            curb_return_arc_sample_count=int(
                result.get("curb_return_arc_sample_count", 0) or 0
            ),
            curb_return_arc_segment_count=int(
                result.get("curb_return_arc_segment_count", 0) or 0
            ),
            edge_blend_face_count=int(
                result.get("edge_blend_face_count", 0) or 0
            ),
            boundary_role_summary=str(
                result.get("boundary_role_summary", "") or ""
            ),
            pavement_tie_in_edge_count=int(
                result.get("pavement_tie_in_edge_count", 0) or 0
            ),
            stem_tie_in_edge_count=int(
                result.get("stem_tie_in_edge_count", 0) or 0
            ),
            overlap_cut_edge_count=int(
                result.get("overlap_cut_edge_count", 0) or 0
            ),
            curb_return_edge_count=int(
                result.get("curb_return_edge_count", 0) or 0
            ),
            fallback_used=fallback_used,
            diagnostic_rows=diagnostics,
        )

    def _run_ordered(self, request, policy):
        try:
            builder = (
                self.ordered_polygon_builder
                or self.ordered_polygon_triangulation
            )
            return builder(
                list(request.boundary_vertices),
                request.center_vertex,
                intersection_id=request.intersection_id,
                policy=policy,
            )
        except Exception as exc:
            return self._builder_error(exc)

    def ordered_polygon_triangulation(
        self,
        vertices: list[object],
        center: object,
        *,
        intersection_id: str,
        policy: Mapping[str, float] | None = None,
    ) -> dict[str, object]:
        """Triangulate an ordered boundary and return legacy-compatible metrics."""

        policy_values = dict(policy or {})
        long_edge_factor = max(
            float(policy_values.get("long_edge_factor", 2.5) or 2.5),
            1.0,
        )
        max_boundary_edge_length = float(
            policy_values.get("max_boundary_edge_length", 0.0) or 0.0
        )
        triangles: list[TINTriangle] = []
        degenerate_count = 0
        max_edge_length = 0.0
        edge_lengths: list[float] = []
        for index, current in enumerate(vertices):
            nxt = vertices[(index + 1) % len(vertices)]
            edge_length = xy_distance(_xy(current), _xy(nxt))
            edge_lengths.append(edge_length)
            max_edge_length = max(max_edge_length, edge_length)
        polygon_indices = ear_clip_triangulation_indices(vertices)
        if polygon_indices:
            for first_index, second_index, third_index in polygon_indices:
                first = vertices[first_index]
                second = vertices[second_index]
                third = vertices[third_index]
                area = abs(xy_triangle_signed_area(first, second, third))
                if area <= 1.0e-6:
                    degenerate_count += 1
                    continue
                triangles.append(
                    TINTriangle(
                        triangle_id=f"t{len(triangles) + 1}",
                        v1=_vertex_id(first),
                        v2=_vertex_id(second),
                        v3=_vertex_id(third),
                        triangle_kind="intersection_surface_patch",
                        quality_ref="ordered_polygon",
                        notes=(
                            f"intersection={intersection_id}; area={area:.6f}"
                        ),
                    )
                )
        else:
            for index, current in enumerate(vertices):
                nxt = vertices[(index + 1) % len(vertices)]
                area = abs(xy_triangle_signed_area(center, current, nxt))
                if area <= 1.0e-6:
                    degenerate_count += 1
                    continue
                triangles.append(
                    TINTriangle(
                        triangle_id=f"t{len(triangles) + 1}",
                        v1=str(
                            getattr(center, "vertex_id", "v:center")
                            or "v:center"
                        ),
                        v2=_vertex_id(current),
                        v3=_vertex_id(nxt),
                        triangle_kind="intersection_surface_patch",
                        quality_ref="ordered_fan_fallback",
                        notes=(
                            f"intersection={intersection_id}; area={area:.6f}"
                        ),
                    )
                )
        if edge_lengths:
            average = sum(edge_lengths) / len(edge_lengths)
            long_edge_limit = (
                max_boundary_edge_length
                if max_boundary_edge_length > 0.0
                else max(average * long_edge_factor, 1.0)
            )
            long_edge_count = len(
                [length for length in edge_lengths if length > long_edge_limit]
            )
        else:
            long_edge_limit = 0.0
            long_edge_count = 0
        return {
            "triangles": triangles,
            "degenerate_count": degenerate_count,
            "max_edge_length": max_edge_length,
            "long_edge_count": long_edge_count,
            "long_edge_factor": long_edge_factor,
            "long_edge_limit": long_edge_limit,
            "max_boundary_edge_length_policy": max_boundary_edge_length,
            "boundary_strategy": "ordered_polygon",
            "structured_strip_count": 0,
            "curb_return_surface_edge_count": 0,
        }

    def structured_strip_triangulation(
        self,
        tie_in_result: object | None,
        *,
        source_vertices: list[object],
        center: object,
        intersection_model: object | None = None,
        boundary_segment_result: object | None = None,
        intersection_id: str,
        policy: Mapping[str, float] | None = None,
    ) -> dict[str, object]:
        """Build structured pavement strips and curb-return surface parts."""

        empty = _empty_structured_result(source_vertices, center, policy)
        if tie_in_result is None:
            return empty
        grouped: dict[str, list[IntersectionBoundarySegmentRow]] = {}
        for edge in list(getattr(tie_in_result, "edge_rows", []) or []):
            alignment_ref = str(
                getattr(edge, "alignment_ref", "") or ""
            ).strip()
            if not alignment_ref:
                continue
            grouped.setdefault(alignment_ref, []).append(
                IntersectionBoundarySegmentRow(
                    boundary_segment_id=(
                        f"structured:{getattr(edge, 'tie_in_edge_id', '')}"
                    ),
                    intersection_id=intersection_id,
                    segment_kind="tie_in",
                    alignment_ref=alignment_ref,
                    side=str(getattr(edge, "side", "") or ""),
                    start_xyz=tuple(
                        getattr(edge, "start_xyz", (0.0, 0.0, 0.0))
                        or (0.0, 0.0, 0.0)
                    ),
                    end_xyz=tuple(
                        getattr(edge, "end_xyz", (0.0, 0.0, 0.0))
                        or (0.0, 0.0, 0.0)
                    ),
                )
            )
        if len(grouped) < 2:
            return empty
        source_row = _intersection_row(intersection_model, intersection_id)
        primary_ref = str(
            getattr(source_row, "primary_alignment_ref", "") or ""
        ).strip()
        if not primary_ref or primary_ref not in grouped:
            primary_ref = next(iter(grouped.keys()))
        primary_polygon = self.tie_in_strip_polygon(grouped.get(primary_ref, []))
        if primary_polygon is None:
            return empty
        polygons = [primary_polygon]
        for alignment_ref, rows in grouped.items():
            if alignment_ref == primary_ref:
                continue
            polygon = self.tie_in_strip_polygon(rows)
            if polygon is None:
                continue
            outside = self.polygon_outer_difference_candidate(
                polygon,
                primary_polygon,
            )
            if outside is not None:
                polygons.append(outside)
        if len(polygons) < 2:
            return empty
        arc_surface_parts = self.curb_return_surface_parts(
            boundary_segment_result
        )
        arc_stats = self.curb_return_surface_arc_stats(
            boundary_segment_result
        )
        edge_blend_face_count = len(
            [part for part in arc_surface_parts if str(part[1]) == "curb_return_blend"]
        )
        role_counts = _boundary_role_counts(
            grouped,
            primary_ref,
            arc_count=int(arc_stats["arc_count"]),
            overlap_cut_count=max(len(polygons) - 1, 0),
        )
        vertices: list[TINVertex] = []
        vertex_by_key: dict[tuple[float, float], TINVertex] = {}

        def vertex_for(point: tuple[float, float, float]) -> TINVertex:
            key = _xy_key(point)
            existing = vertex_by_key.get(key)
            if existing is not None:
                return existing
            nearest = _nearest_vertex(
                source_vertices,
                float(point[0]),
                float(point[1]),
            )
            z = (
                float(getattr(nearest, "z", point[2]) or point[2])
                if nearest is not None
                else float(point[2])
            )
            vertex = TINVertex(
                vertex_id=f"v{len(vertices) + 1}",
                x=float(point[0]),
                y=float(point[1]),
                z=z,
                source_point_ref=(
                    f"{intersection_id}:structured-strip:{len(vertices) + 1}"
                ),
                notes="intersection structured strip triangulation",
            )
            vertices.append(vertex)
            vertex_by_key[key] = vertex
            return vertex

        triangles: list[TINTriangle] = []
        degenerate_count = 0
        edge_lengths: list[float] = []
        surface_parts = [
            (polygon, "structured_strip") for polygon in polygons
        ]
        surface_parts.extend(arc_surface_parts)
        for polygon_index, (polygon, quality_role) in enumerate(
            surface_parts,
            start=1,
        ):
            cleaned = _unique_xyz_points(polygon)
            if len(cleaned) < 3 or xy_polygon_self_intersects(cleaned):
                continue
            if xy_polygon_signed_area(cleaned) < 0.0:
                cleaned.reverse()
            local_vertices = [vertex_for(point) for point in cleaned]
            edge_pairs = (
                xy_closed_edges([(v.x, v.y, v.z) for v in local_vertices])
                if polygon_index <= len(polygons)
                else []
            )
            for first, second in edge_pairs:
                edge_lengths.append(xy_distance(first, second))
            indices = ear_clip_triangulation_indices(local_vertices)
            if not indices and len(local_vertices) == 4:
                indices = [(0, 1, 2), (0, 2, 3)]
            for first_index, second_index, third_index in indices:
                first = local_vertices[first_index]
                second = local_vertices[second_index]
                third = local_vertices[third_index]
                area = abs(xy_triangle_signed_area(first, second, third))
                if area <= 1.0e-6:
                    degenerate_count += 1
                    continue
                triangles.append(
                    TINTriangle(
                        triangle_id=f"t{len(triangles) + 1}",
                        v1=_vertex_id(first),
                        v2=_vertex_id(second),
                        v3=_vertex_id(third),
                        triangle_kind="intersection_surface_patch",
                        quality_ref=quality_role,
                        notes=(
                            f"intersection={intersection_id}; "
                            f"surface_part={polygon_index}; area={area:.6f}"
                        ),
                    )
                )
        if not triangles:
            return empty
        policy_values = dict(policy or {})
        long_edge_factor = max(
            float(policy_values.get("long_edge_factor", 2.5) or 2.5),
            1.0,
        )
        max_boundary_edge_length = float(
            policy_values.get("max_boundary_edge_length", 0.0) or 0.0
        )
        max_edge_length = max(edge_lengths) if edge_lengths else 0.0
        if edge_lengths:
            average = sum(edge_lengths) / len(edge_lengths)
            long_edge_limit = (
                max_boundary_edge_length
                if max_boundary_edge_length > 0.0
                else max(average * long_edge_factor, 1.0)
            )
            long_edge_count = len(
                [length for length in edge_lengths if length > long_edge_limit]
            )
        else:
            long_edge_limit = 0.0
            long_edge_count = 0
        if edge_blend_face_count:
            boundary_strategy = "structured_strip_curb_return_blend"
        elif arc_stats["arc_count"]:
            boundary_strategy = "structured_strip_curb_return"
        else:
            boundary_strategy = "structured_strip_union"
        return {
            "vertices": vertices,
            "triangles": triangles,
            "degenerate_count": degenerate_count,
            "max_edge_length": max_edge_length,
            "long_edge_count": long_edge_count,
            "long_edge_factor": long_edge_factor,
            "long_edge_limit": long_edge_limit,
            "max_boundary_edge_length_policy": max_boundary_edge_length,
            "boundary_strategy": boundary_strategy,
            "structured_strip_count": len(polygons),
            "curb_return_surface_edge_count": int(arc_stats["arc_count"]),
            "curb_return_arc_count": int(arc_stats["arc_count"]),
            "curb_return_arc_sample_count": int(arc_stats["sample_count"]),
            "curb_return_arc_segment_count": int(arc_stats["segment_count"]),
            "edge_blend_face_count": edge_blend_face_count,
            "boundary_role_summary": _boundary_role_summary(role_counts),
            "pavement_tie_in_edge_count": int(role_counts["pavement_tie_in"]),
            "stem_tie_in_edge_count": int(role_counts["stem_tie_in"]),
            "overlap_cut_edge_count": int(role_counts["overlap_cut"]),
            "curb_return_edge_count": int(role_counts["curb_return"]),
        }

    def tie_in_strip_polygon(
        self,
        rows: list[object],
    ) -> list[tuple[float, float, float]] | None:
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
        candidates = [
            [first_start, first_end, second_end, second_start],
            [first_start, second_start, second_end, first_end],
        ]
        valid = [
            polygon
            for polygon in (
                self.normalize_tie_in_strip_polygon(candidate)
                for candidate in candidates
            )
            if polygon is not None
        ]
        valid = [
            polygon
            for polygon in valid
            if abs(xy_polygon_signed_area(polygon)) > 1.0e-6
            and not xy_polygon_self_intersects(polygon)
        ]
        if valid:
            return max(valid, key=lambda row: abs(xy_polygon_signed_area(row)))
        normalized = [
            polygon
            for polygon in (
                self.normalize_tie_in_strip_polygon(candidate)
                for candidate in candidates
            )
            if polygon is not None
        ]
        if not normalized:
            return None
        best = max(normalized, key=lambda row: abs(xy_polygon_signed_area(row)))
        return best if abs(xy_polygon_signed_area(best)) > 1.0e-6 else None

    def normalize_tie_in_strip_polygon(
        self,
        points: list[tuple[float, float, float]],
        *,
        tolerance: float = 1.0e-6,
    ) -> list[tuple[float, float, float]] | None:
        normalized = []
        for point in list(points or []):
            xyz = xyz_point(point)
            if normalized and xy_distance(xyz, normalized[-1]) <= tolerance:
                continue
            if any(
                xy_distance(xyz, existing) <= tolerance
                for existing in normalized
            ):
                continue
            normalized.append(xyz)
        if (
            len(normalized) >= 2
            and xy_distance(normalized[0], normalized[-1]) <= tolerance
        ):
            normalized.pop()
        if len(normalized) < 3:
            return None
        area = xy_polygon_signed_area(normalized)
        if abs(area) <= 1.0e-6:
            return None
        if area < 0.0:
            normalized.reverse()
        return normalized

    def polygon_outer_difference_candidate(
        self,
        polygon: list[tuple[float, float, float]],
        clip_polygon: list[tuple[float, float, float]],
    ) -> list[tuple[float, float, float]] | None:
        output = [
            point
            for point in polygon
            if not xy_point_in_polygon_strict(point, clip_polygon)
        ]
        for start, end in xy_closed_edges(polygon):
            for clip_start, clip_end in xy_closed_edges(clip_polygon):
                intersection = xyz_segment_intersection_point(
                    start,
                    end,
                    clip_start,
                    clip_end,
                )
                if intersection is not None:
                    output.append(intersection)
        output = _unique_xyz_points(output)
        if len(output) < 3:
            return None
        center_x = sum(point[0] for point in output) / len(output)
        center_y = sum(point[1] for point in output) / len(output)
        ordered = sorted(
            output,
            key=lambda point: math.atan2(
                point[1] - center_y,
                point[0] - center_x,
            ),
        )
        if (
            abs(xy_polygon_signed_area(ordered)) <= 1.0e-6
            or xy_polygon_self_intersects(ordered)
        ):
            return None
        return ordered

    def curb_return_surface_arc_stats(self, boundary_result: object | None):
        if boundary_result is None:
            return {"arc_count": 0, "sample_count": 0, "segment_count": 0}
        arc_count = 0
        max_sample_count = 0
        segment_count = 0
        for row in list(getattr(boundary_result, "segment_rows", []) or []):
            if str(getattr(row, "segment_kind", "") or "") != "arc":
                continue
            if str(getattr(row, "segment_role", "") or "") != "curb_return":
                continue
            chord_points = list(getattr(row, "chord_points_xyz", []) or [])
            if len(chord_points) < 2:
                continue
            arc_count += 1
            max_sample_count = max(max_sample_count, len(chord_points))
            segment_count += max(len(chord_points) - 1, 0)
        return {
            "arc_count": arc_count,
            "sample_count": max_sample_count,
            "segment_count": segment_count,
        }

    def curb_return_surface_parts(self, boundary_result: object | None):
        if boundary_result is None:
            return []
        output = []
        for row in list(getattr(boundary_result, "segment_rows", []) or []):
            if str(getattr(row, "segment_kind", "") or "") != "arc":
                continue
            if str(getattr(row, "segment_role", "") or "") != "curb_return":
                continue
            chord_points = [
                xyz_point(point)
                for point in list(getattr(row, "chord_points_xyz", []) or [])
            ]
            center = xyz_point(
                getattr(row, "center_xyz", (0.0, 0.0, 0.0))
            )
            if len(chord_points) < 2:
                continue
            inner_points = [
                self.lerp_xyz(center, point, 0.58) for point in chord_points
            ]
            for index in range(len(chord_points) - 1):
                polygon = _unique_xyz_points(
                    [
                        chord_points[index],
                        chord_points[index + 1],
                        inner_points[index + 1],
                        inner_points[index],
                    ]
                )
                if _surface_part_is_valid(polygon):
                    output.append((polygon, "curb_return_blend"))
            core = _unique_xyz_points([center, *inner_points])
            if _surface_part_is_valid(core):
                output.append((core, "curb_return_core"))
        return output

    @staticmethod
    def boundary_role_counts(grouped, primary_ref, *, arc_count, overlap_cut_count):
        return _boundary_role_counts(
            grouped,
            primary_ref,
            arc_count=arc_count,
            overlap_cut_count=overlap_cut_count,
        )

    @staticmethod
    def boundary_role_summary(role_counts):
        return _boundary_role_summary(role_counts)

    @staticmethod
    def surface_part_is_valid(polygon):
        return _surface_part_is_valid(polygon)

    @staticmethod
    def lerp_xyz(start, end, factor: float):
        active = max(0.0, min(float(factor), 1.0))
        return tuple(
            float(start[index])
            + (float(end[index]) - float(start[index])) * active
            for index in range(3)
        )

    @staticmethod
    def _builder_error(exc: Exception) -> IntersectionPatchTriangulationResult:
        return IntersectionPatchTriangulationService._error(
            "error",
            f"intersection_patch_triangulation_failed:{type(exc).__name__}:{exc}",
            str(exc),
        )

    @staticmethod
    def _error(status: str, diagnostic: str, message: str):
        return IntersectionPatchTriangulationResult(
            status=status,
            selection_path="",
            diagnostic_rows=(diagnostic,),
            error_message=message,
        )


def _xy(vertex: object) -> tuple[float, float]:
    return (
        float(getattr(vertex, "x", 0.0) or 0.0),
        float(getattr(vertex, "y", 0.0) or 0.0),
    )


def _vertex_id(vertex: object) -> str:
    return str(getattr(vertex, "vertex_id", "") or "")


def _empty_structured_result(source_vertices, center, policy):
    values = dict(policy or {})
    return {
        "vertices": [*list(source_vertices or []), center],
        "triangles": [],
        "degenerate_count": 0,
        "max_edge_length": 0.0,
        "long_edge_count": 0,
        "long_edge_factor": max(
            float(values.get("long_edge_factor", 2.5) or 2.5),
            1.0,
        ),
        "long_edge_limit": 0.0,
        "max_boundary_edge_length_policy": float(
            values.get("max_boundary_edge_length", 0.0) or 0.0
        ),
        "boundary_strategy": "ordered_polygon",
        "structured_strip_count": 0,
        "curb_return_surface_edge_count": 0,
        "curb_return_arc_count": 0,
        "curb_return_arc_sample_count": 0,
        "curb_return_arc_segment_count": 0,
        "edge_blend_face_count": 0,
        "boundary_role_summary": "",
        "pavement_tie_in_edge_count": 0,
        "stem_tie_in_edge_count": 0,
        "overlap_cut_edge_count": 0,
        "curb_return_edge_count": 0,
    }


def _intersection_row(intersection_model, intersection_id: str):
    target = str(intersection_id or "").strip()
    if intersection_model is None or not target:
        return None
    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        if str(getattr(row, "intersection_id", "") or "").strip() == target:
            return row
    return None


def _boundary_role_counts(
    grouped: dict[str, list[object]],
    primary_ref: str,
    *,
    arc_count: int,
    overlap_cut_count: int,
) -> dict[str, int]:
    pavement_tie_in = len(list(grouped.get(primary_ref, []) or []))
    stem_tie_in = sum(
        len(list(rows or []))
        for alignment_ref, rows in grouped.items()
        if str(alignment_ref or "") != str(primary_ref or "")
    )
    return {
        "pavement_tie_in": int(pavement_tie_in),
        "stem_tie_in": int(stem_tie_in),
        "overlap_cut": int(max(overlap_cut_count, 0)),
        "curb_return": int(max(arc_count, 0)),
    }


def _boundary_role_summary(role_counts: dict[str, int]) -> str:
    roles = ("pavement_tie_in", "stem_tie_in", "overlap_cut", "curb_return")
    return "; ".join(
        f"{role}={int(role_counts.get(role, 0) or 0)}" for role in roles
    )


def _unique_xyz_points(points, *, tolerance: float = 1.0e-6):
    output = []
    for point in list(points or []):
        if any(_xyz_distance(point, existing) <= tolerance for existing in output):
            continue
        output.append(point)
    return output


def _xyz_distance(first, second) -> float:
    return math.sqrt(
        sum(
            (float(first[index]) - float(second[index])) ** 2
            for index in range(3)
        )
    )


def _surface_part_is_valid(polygon) -> bool:
    return (
        len(polygon) >= 3
        and abs(xy_polygon_signed_area(polygon)) > 1.0e-6
        and not xy_polygon_self_intersects(polygon)
    )


def _xy_key(point) -> tuple[float, float]:
    return (round(float(point[0]), 6), round(float(point[1]), 6))


def _nearest_vertex(vertices, x: float, y: float):
    nearest = None
    nearest_distance = None
    for vertex in list(vertices or []):
        dx = float(getattr(vertex, "x", 0.0) or 0.0) - float(x)
        dy = float(getattr(vertex, "y", 0.0) or 0.0) - float(y)
        distance = dx * dx + dy * dy
        if nearest_distance is None or distance < nearest_distance:
            nearest = vertex
            nearest_distance = distance
    return nearest

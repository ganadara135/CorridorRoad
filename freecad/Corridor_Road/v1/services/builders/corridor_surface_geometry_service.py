"""Corridor surface geometry builder service for CorridorRoad v1."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex
from ..evaluation.tin_sampling_service import TinSamplingService


@dataclass(frozen=True)
class _SectionPointLite:
    point_id: str
    x: float
    y: float
    z: float
    lateral_offset: float
    point_role: str = ""


@dataclass(frozen=True)
class CorridorDesignSurfaceGeometryRequest:
    """Input bundle for a minimal corridor surface ribbon."""

    project_id: str
    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    surface_id: str
    fallback_half_width: float = 6.0
    existing_ground_surface: TINSurface | None = None


class CorridorSurfaceGeometryService:
    """Build first-slice corridor surface geometry from evaluated station frames."""

    def build_design_surface(self, request: CorridorDesignSurfaceGeometryRequest) -> TINSurface:
        """Build a simple design-surface ribbon from applied-section frames."""

        return self._build_surface_ribbon(
            request,
            surface_kind="design_surface",
            label_prefix="Design Surface",
            z_offset_resolver=lambda _section: 0.0,
            triangle_kind="corridor_design_strip",
            point_role="fg_surface",
        )

    def build_subgrade_surface(self, request: CorridorDesignSurfaceGeometryRequest) -> TINSurface:
        """Build a simple subgrade-surface ribbon below the design surface."""

        return self._build_surface_ribbon(
            request,
            surface_kind="subgrade_surface",
            label_prefix="Subgrade Surface",
            z_offset_resolver=lambda section: -max(float(getattr(section, "subgrade_depth", 0.0) or 0.0), 0.0),
            triangle_kind="corridor_subgrade_strip",
            point_role="subgrade_surface",
        )

    def build_drainage_surface(self, request: CorridorDesignSurfaceGeometryRequest) -> TINSurface:
        """Build first-slice ditch/drainage grading strips from AppliedSection point rows."""

        return self._build_surface_ribbon(
            request,
            surface_kind="drainage_surface",
            label_prefix="Drainage Surface",
            z_offset_resolver=lambda _section: 0.0,
            triangle_kind="corridor_drainage_strip",
            point_role="ditch_surface",
            allow_width_fallback=False,
        )

    def build_daylight_surface(self, request: CorridorDesignSurfaceGeometryRequest) -> TINSurface:
        """Build first-slice slope-face strips from design edges and side-slope policy."""

        frame_rows = _frame_rows(request.applied_section_set)
        sections = _section_rows(request.applied_section_set)
        if len(frame_rows) < 2:
            raise ValueError("At least two applied-section frames are required to build a corridor slope-face surface.")
        fallback_half_width = max(float(request.fallback_half_width or 0.0), 0.1)
        point_surface = _build_daylight_surface_from_side_slope_points(
            request,
            sections=sections,
            fallback_half_width=fallback_half_width,
        )
        if point_surface is not None:
            return point_surface
        edge_rows = _daylight_inner_edge_rows(request.applied_section_set, fallback_half_width=fallback_half_width)
        daylight_rows = _daylight_rows(request.applied_section_set)
        sampling_service = TinSamplingService()
        vertices: list[TINVertex] = []
        triangles: list[TINTriangle] = []
        eg_hit_count = 0
        eg_miss_count = 0
        eg_intersection_count = 0
        eg_outer_edge_sample_count = 0
        fallback_count = 0
        no_existing_ground_count = 0
        no_eg_hit_count = 0

        for index, frame in enumerate(frame_rows):
            angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
            nx = -math.sin(angle_rad)
            ny = math.cos(angle_rad)
            x = float(getattr(frame, "x", 0.0) or 0.0)
            y = float(getattr(frame, "y", 0.0) or 0.0)
            z = float(getattr(frame, "z", 0.0) or 0.0)
            left_edge, right_edge = edge_rows[index]
            left_daylight_width, right_daylight_width, left_slope, right_slope = daylight_rows[index]
            if left_daylight_width > 0.0:
                inner_x = x + nx * left_edge[0]
                inner_y = y + ny * left_edge[0]
                inner_z = left_edge[1]
                outer = _resolve_slope_face_outer_point(
                    sampling_service=sampling_service,
                    surface=request.existing_ground_surface,
                    edge_x=inner_x,
                    edge_y=inner_y,
                    edge_z=inner_z,
                    normal_x=nx,
                    normal_y=ny,
                    max_width=left_daylight_width,
                    slope=left_slope,
                )
                eg_hit_count += 1 if outer.sampled else 0
                eg_miss_count += 0 if outer.sampled or request.existing_ground_surface is None else 1
                eg_intersection_count += 1 if outer.intersected else 0
                eg_outer_edge_sample_count += 1 if outer.status == "sampled_outer_edge" else 0
                fallback_count += 1 if not outer.sampled else 0
                no_existing_ground_count += 1 if outer.status == "fallback:no_existing_ground_tin" else 0
                no_eg_hit_count += 1 if outer.status == "fallback:no_eg_hit_in_search_width" else 0
                vertices.extend(
                    [
                        TINVertex(f"v{index}:left:inner", inner_x, inner_y, inner_z),
                        TINVertex(
                            f"v{index}:left:outer",
                            outer.x,
                            outer.y,
                            outer.z,
                            source_point_ref=f"{request.applied_section_set.applied_section_set_id}:frame:{index + 1}:left:slope_face_outer",
                            notes=outer.status,
                        ),
                    ]
                )
            if right_daylight_width > 0.0:
                inner_x = x + nx * right_edge[0]
                inner_y = y + ny * right_edge[0]
                inner_z = right_edge[1]
                outer = _resolve_slope_face_outer_point(
                    sampling_service=sampling_service,
                    surface=request.existing_ground_surface,
                    edge_x=inner_x,
                    edge_y=inner_y,
                    edge_z=inner_z,
                    normal_x=-nx,
                    normal_y=-ny,
                    max_width=right_daylight_width,
                    slope=right_slope,
                )
                eg_hit_count += 1 if outer.sampled else 0
                eg_miss_count += 0 if outer.sampled or request.existing_ground_surface is None else 1
                eg_intersection_count += 1 if outer.intersected else 0
                eg_outer_edge_sample_count += 1 if outer.status == "sampled_outer_edge" else 0
                fallback_count += 1 if not outer.sampled else 0
                no_existing_ground_count += 1 if outer.status == "fallback:no_existing_ground_tin" else 0
                no_eg_hit_count += 1 if outer.status == "fallback:no_eg_hit_in_search_width" else 0
                vertices.extend(
                    [
                        TINVertex(f"v{index}:right:inner", inner_x, inner_y, inner_z),
                        TINVertex(
                            f"v{index}:right:outer",
                            outer.x,
                            outer.y,
                            outer.z,
                            source_point_ref=f"{request.applied_section_set.applied_section_set_id}:frame:{index + 1}:right:slope_face_outer",
                            notes=outer.status,
                        ),
                    ]
                )

        for index in range(len(frame_rows) - 1):
            if daylight_rows[index][0] > 0.0 and daylight_rows[index + 1][0] > 0.0:
                li0 = f"v{index}:left:inner"
                lo0 = f"v{index}:left:outer"
                li1 = f"v{index + 1}:left:inner"
                lo1 = f"v{index + 1}:left:outer"
                triangles.append(TINTriangle(f"span:{index}:left:a", li0, lo0, lo1, triangle_kind="corridor_daylight_strip"))
                triangles.append(TINTriangle(f"span:{index}:left:b", li0, lo1, li1, triangle_kind="corridor_daylight_strip"))
            if daylight_rows[index][1] > 0.0 and daylight_rows[index + 1][1] > 0.0:
                ri0 = f"v{index}:right:inner"
                ro0 = f"v{index}:right:outer"
                ri1 = f"v{index + 1}:right:inner"
                ro1 = f"v{index + 1}:right:outer"
                triangles.append(TINTriangle(f"span:{index}:right:a", ri0, ri1, ro1, triangle_kind="corridor_daylight_strip"))
                triangles.append(TINTriangle(f"span:{index}:right:b", ri0, ro1, ro0, triangle_kind="corridor_daylight_strip"))

        if not vertices or not triangles:
            raise ValueError("No slope-face strips were generated from applied-section side-slope data.")

        z_values = [vertex.z for vertex in vertices]
        left_values = [row[0] for row in daylight_rows]
        right_values = [row[1] for row in daylight_rows]
        return TINSurface(
            schema_version=1,
            project_id=request.project_id,
            surface_id=request.surface_id,
            surface_kind="daylight_surface",
            label=f"Slope Face Surface - {request.corridor.corridor_id}",
            source_refs=[
                str(getattr(request.corridor, "corridor_id", "") or ""),
                str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
            ],
            vertex_rows=vertices,
            triangle_rows=triangles,
            boundary_refs=[f"{request.surface_id}:daylight-boundary"],
            quality_rows=[
                TINQualityRow(f"{request.surface_id}:station_count", "station_count", len(sections), "count"),
                TINQualityRow(f"{request.surface_id}:left_daylight_width_max", "left_daylight_width_max", max(left_values), "m"),
                TINQualityRow(f"{request.surface_id}:right_daylight_width_max", "right_daylight_width_max", max(right_values), "m"),
                TINQualityRow(f"{request.surface_id}:eg_tie_in_hit_count", "eg_tie_in_hit_count", eg_hit_count, "count"),
                TINQualityRow(f"{request.surface_id}:eg_tie_in_miss_count", "eg_tie_in_miss_count", eg_miss_count, "count"),
                TINQualityRow(f"{request.surface_id}:eg_intersection_count", "eg_intersection_count", eg_intersection_count, "count"),
                TINQualityRow(f"{request.surface_id}:eg_outer_edge_sample_count", "eg_outer_edge_sample_count", eg_outer_edge_sample_count, "count"),
                TINQualityRow(f"{request.surface_id}:slope_face_fallback_count", "slope_face_fallback_count", fallback_count, "count"),
                TINQualityRow(f"{request.surface_id}:slope_face_no_existing_ground_count", "slope_face_no_existing_ground_count", no_existing_ground_count, "count"),
                TINQualityRow(f"{request.surface_id}:slope_face_no_eg_hit_count", "slope_face_no_eg_hit_count", no_eg_hit_count, "count"),
                TINQualityRow(f"{request.surface_id}:z_min", "z_min", min(z_values), "m"),
                TINQualityRow(f"{request.surface_id}:z_max", "z_max", max(z_values), "m"),
            ],
            provenance_rows=[
                TINProvenanceRow(
                    provenance_id=f"{request.surface_id}:provenance:applied-sections",
                    source_kind="applied_section_side_slope",
                    source_ref=str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
                    notes=_daylight_provenance_notes(request.existing_ground_surface, eg_hit_count, eg_miss_count, eg_intersection_count),
                )
            ],
        )

    def _build_surface_ribbon(
        self,
        request: CorridorDesignSurfaceGeometryRequest,
        *,
        surface_kind: str,
        label_prefix: str,
        z_offset_resolver,
        triangle_kind: str,
        point_role: str = "",
        allow_width_fallback: bool = True,
    ) -> TINSurface:
        """Build a two-edge ribbon from applied-section frames."""

        frame_rows = _frame_rows(request.applied_section_set)
        if len(frame_rows) < 2:
            raise ValueError("At least two applied-section frames are required to build a corridor surface.")

        fallback_half_width = max(float(request.fallback_half_width or 0.0), 0.1)
        sections = _section_rows(request.applied_section_set)
        point_grid = _section_point_grid(sections, point_role=point_role)
        if point_grid:
            return _build_surface_from_point_grid(
                request,
                sections=sections,
                point_grid=point_grid,
                surface_kind=surface_kind,
                label_prefix=label_prefix,
                triangle_kind=triangle_kind,
            )
        if not allow_width_fallback:
            raise ValueError(f"No {surface_kind} section point rows are available.")

        vertices: list[TINVertex] = []
        triangles: list[TINTriangle] = []
        width_rows = _surface_width_rows(request.applied_section_set, fallback_half_width=fallback_half_width)
        for index, frame in enumerate(frame_rows):
            section = sections[index]
            angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
            nx = -math.sin(angle_rad)
            ny = math.cos(angle_rad)
            x = float(getattr(frame, "x", 0.0) or 0.0)
            y = float(getattr(frame, "y", 0.0) or 0.0)
            z = float(getattr(frame, "z", 0.0) or 0.0) + float(z_offset_resolver(section) or 0.0)
            left_width, right_width = width_rows[index]
            left_id = f"v{index}:left"
            right_id = f"v{index}:right"
            vertices.append(
                TINVertex(
                    vertex_id=left_id,
                    x=x + nx * left_width,
                    y=y + ny * left_width,
                    z=z,
                    source_point_ref=f"{request.applied_section_set.applied_section_set_id}:frame:{index + 1}:left",
                )
            )
            vertices.append(
                TINVertex(
                    vertex_id=right_id,
                    x=x - nx * right_width,
                    y=y - ny * right_width,
                    z=z,
                    source_point_ref=f"{request.applied_section_set.applied_section_set_id}:frame:{index + 1}:right",
                )
            )

        for index in range(len(frame_rows) - 1):
            left0 = f"v{index}:left"
            right0 = f"v{index}:right"
            left1 = f"v{index + 1}:left"
            right1 = f"v{index + 1}:right"
            triangles.append(TINTriangle(f"span:{index}:a", left0, right0, right1, triangle_kind=triangle_kind))
            triangles.append(TINTriangle(f"span:{index}:b", left0, right1, left1, triangle_kind=triangle_kind))

        z_values = [vertex.z for vertex in vertices]
        left_values = [left for left, _right in width_rows]
        right_values = [right for _left, right in width_rows]
        return TINSurface(
            schema_version=1,
            project_id=request.project_id,
            surface_id=request.surface_id,
            surface_kind=surface_kind,
            label=f"{label_prefix} - {request.corridor.corridor_id}",
            source_refs=[
                str(getattr(request.corridor, "corridor_id", "") or ""),
                str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
            ],
            vertex_rows=vertices,
            triangle_rows=triangles,
            boundary_refs=[f"{request.surface_id}:ribbon-boundary"],
            quality_rows=[
                TINQualityRow(f"{request.surface_id}:station_count", "station_count", len(frame_rows), "count"),
                TINQualityRow(f"{request.surface_id}:left_width_min", "left_width_min", min(left_values), "m"),
                TINQualityRow(f"{request.surface_id}:left_width_max", "left_width_max", max(left_values), "m"),
                TINQualityRow(f"{request.surface_id}:right_width_min", "right_width_min", min(right_values), "m"),
                TINQualityRow(f"{request.surface_id}:right_width_max", "right_width_max", max(right_values), "m"),
                TINQualityRow(f"{request.surface_id}:z_min", "z_min", min(z_values), "m"),
                TINQualityRow(f"{request.surface_id}:z_max", "z_max", max(z_values), "m"),
            ],
            provenance_rows=[
                TINProvenanceRow(
                    provenance_id=f"{request.surface_id}:provenance:applied-sections",
                    source_kind="applied_section_frames",
                    source_ref=str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
                    notes=f"First-slice corridor {surface_kind} ribbon built from evaluated applied-section frames.",
                )
            ],
        )


def _build_surface_from_point_grid(
    request: CorridorDesignSurfaceGeometryRequest,
    *,
    sections: list[object],
    point_grid: list[list[object]],
    surface_kind: str,
    label_prefix: str,
    triangle_kind: str,
) -> TINSurface:
    vertices: list[TINVertex] = []
    triangles: list[TINTriangle] = []
    for section_index, points in enumerate(point_grid):
        section = sections[section_index]
        for point_index, point in enumerate(points):
            vertices.append(
                TINVertex(
                    vertex_id=f"v{section_index}:p{point_index}",
                    x=float(getattr(point, "x", 0.0) or 0.0),
                    y=float(getattr(point, "y", 0.0) or 0.0),
                    z=float(getattr(point, "z", 0.0) or 0.0),
                    source_point_ref=f"{getattr(section, 'applied_section_id', '')}:{getattr(point, 'point_id', '')}",
                )
            )
    for section_index in range(len(point_grid) - 1):
        for point_index in range(len(point_grid[section_index]) - 1):
            p00 = f"v{section_index}:p{point_index}"
            p01 = f"v{section_index}:p{point_index + 1}"
            p10 = f"v{section_index + 1}:p{point_index}"
            p11 = f"v{section_index + 1}:p{point_index + 1}"
            triangles.append(TINTriangle(f"span:{section_index}:p{point_index}:a", p00, p01, p11, triangle_kind=triangle_kind))
            triangles.append(TINTriangle(f"span:{section_index}:p{point_index}:b", p00, p11, p10, triangle_kind=triangle_kind))

    z_values = [vertex.z for vertex in vertices]
    left_values = [max(float(getattr(point, "lateral_offset", 0.0) or 0.0) for point in points) for points in point_grid]
    right_values = [abs(min(float(getattr(point, "lateral_offset", 0.0) or 0.0) for point in points)) for points in point_grid]
    return TINSurface(
        schema_version=1,
        project_id=request.project_id,
        surface_id=request.surface_id,
        surface_kind=surface_kind,
        label=f"{label_prefix} - {request.corridor.corridor_id}",
        source_refs=[
            str(getattr(request.corridor, "corridor_id", "") or ""),
            str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
        ],
        vertex_rows=vertices,
        triangle_rows=triangles,
        boundary_refs=[f"{request.surface_id}:section-point-boundary"],
        quality_rows=[
            TINQualityRow(f"{request.surface_id}:station_count", "station_count", len(point_grid), "count"),
            TINQualityRow(f"{request.surface_id}:section_point_count", "section_point_count", len(point_grid[0]), "count"),
            TINQualityRow(f"{request.surface_id}:left_width_min", "left_width_min", min(left_values), "m"),
            TINQualityRow(f"{request.surface_id}:left_width_max", "left_width_max", max(left_values), "m"),
            TINQualityRow(f"{request.surface_id}:right_width_min", "right_width_min", min(right_values), "m"),
            TINQualityRow(f"{request.surface_id}:right_width_max", "right_width_max", max(right_values), "m"),
            TINQualityRow(f"{request.surface_id}:z_min", "z_min", min(z_values), "m"),
            TINQualityRow(f"{request.surface_id}:z_max", "z_max", max(z_values), "m"),
        ],
        provenance_rows=[
            TINProvenanceRow(
                provenance_id=f"{request.surface_id}:provenance:applied-section-points",
                source_kind="applied_section_points",
                source_ref=str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
                notes=f"Corridor {surface_kind} TIN built from evaluated AppliedSection point rows.",
            )
        ],
    )


def _build_daylight_surface_from_side_slope_points(
    request: CorridorDesignSurfaceGeometryRequest,
    *,
    sections: list[object],
    fallback_half_width: float,
) -> TINSurface | None:
    side_grids = _side_slope_point_grids(
        sections,
        fallback_half_width=fallback_half_width,
        existing_ground_surface=request.existing_ground_surface,
    )
    if not side_grids:
        return None
    vertices: list[TINVertex] = []
    triangles: list[TINTriangle] = []
    bench_breakline_count = 0
    side_slope_point_count = 0
    daylight_marker_count = 0
    for side_label, grid in side_grids.items():
        if len(grid) < 2:
            continue
        for section_index, points in enumerate(grid):
            for point_index, point in enumerate(points):
                role = str(getattr(point, "point_role", "") or "")
                bench_breakline_count += 1 if role == "bench_surface" else 0
                side_slope_point_count += 1 if role == "side_slope_surface" else 0
                daylight_marker_count += 1 if role == "daylight_marker" else 0
        for section_index in range(len(grid) - 1):
            span_rows = _resampled_side_slope_span_rows(grid[section_index], grid[section_index + 1])
            if len(span_rows[0]) < 2 or len(span_rows[1]) < 2:
                continue
            for row_index, points in enumerate(span_rows):
                for point_index, point in enumerate(points):
                    vertices.append(
                        TINVertex(
                            vertex_id=f"v{section_index}:{side_label}:r{row_index}:p{point_index}",
                            x=float(point.x),
                            y=float(point.y),
                            z=float(point.z),
                            source_point_ref=f"{getattr(sections[section_index + row_index], 'applied_section_id', '')}:{point.point_id}",
                            notes=str(getattr(point, "point_role", "") or ""),
                        )
                    )
            for point_index in range(len(span_rows[0]) - 1):
                p00 = f"v{section_index}:{side_label}:r0:p{point_index}"
                p01 = f"v{section_index}:{side_label}:r0:p{point_index + 1}"
                p10 = f"v{section_index}:{side_label}:r1:p{point_index}"
                p11 = f"v{section_index}:{side_label}:r1:p{point_index + 1}"
                triangles.append(TINTriangle(f"span:{section_index}:{side_label}:p{point_index}:a", p00, p01, p11, triangle_kind="corridor_daylight_bench_strip"))
                triangles.append(TINTriangle(f"span:{section_index}:{side_label}:p{point_index}:b", p00, p11, p10, triangle_kind="corridor_daylight_bench_strip"))
    if not vertices or not triangles:
        return None
    z_values = [vertex.z for vertex in vertices]
    offset_values = [
        abs(float(point.lateral_offset))
        for grid in side_grids.values()
        for points in grid
        for point in points
    ]
    return TINSurface(
        schema_version=1,
        project_id=request.project_id,
        surface_id=request.surface_id,
        surface_kind="daylight_surface",
        label=f"Slope Face Surface - {request.corridor.corridor_id}",
        source_refs=[
            str(getattr(request.corridor, "corridor_id", "") or ""),
            str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
        ],
        vertex_rows=vertices,
        triangle_rows=triangles,
        boundary_refs=[f"{request.surface_id}:bench-daylight-boundary"],
        quality_rows=[
            TINQualityRow(f"{request.surface_id}:station_count", "station_count", len(sections), "count"),
            TINQualityRow(f"{request.surface_id}:section_point_count", "section_point_count", len(vertices), "count"),
            TINQualityRow(f"{request.surface_id}:side_slope_point_count", "side_slope_point_count", side_slope_point_count, "count"),
            TINQualityRow(f"{request.surface_id}:bench_breakline_count", "bench_breakline_count", bench_breakline_count, "count"),
            TINQualityRow(f"{request.surface_id}:daylight_marker_count", "daylight_marker_count", daylight_marker_count, "count"),
            TINQualityRow(f"{request.surface_id}:offset_abs_max", "offset_abs_max", max(offset_values), "m"),
            TINQualityRow(f"{request.surface_id}:z_min", "z_min", min(z_values), "m"),
            TINQualityRow(f"{request.surface_id}:z_max", "z_max", max(z_values), "m"),
        ],
        provenance_rows=[
            TINProvenanceRow(
                provenance_id=f"{request.surface_id}:provenance:applied-section-bench-points",
                source_kind="applied_section_side_slope_points",
                source_ref=str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
                notes="Corridor slope-face surface built from evaluated side_slope_surface, bench_surface, and daylight_marker breaklines.",
            )
        ],
    )


def _side_slope_point_grids(
    sections: list[object],
    *,
    fallback_half_width: float,
    existing_ground_surface: TINSurface | None = None,
) -> dict[str, list[list[_SectionPointLite]]]:
    grids: dict[str, list[list[_SectionPointLite]]] = {}
    for side_label in ("left", "right"):
        grid: list[list[_SectionPointLite]] = []
        section_rows = list(sections or [])
        for section in section_rows:
            rows = _side_slope_points_for_section(
                section,
                side_label=side_label,
                fallback_half_width=fallback_half_width,
            )
            if len(rows) < 2:
                grid = []
                break
            rows = _terrain_adjusted_side_slope_points_for_section(
                section,
                rows,
                side_label=side_label,
                existing_ground_surface=existing_ground_surface,
            )
            grid.append(rows)
        if len(grid) >= 2:
            grids[side_label] = grid
    return grids


def _resampled_side_slope_span_rows(
    first: list[_SectionPointLite],
    second: list[_SectionPointLite],
) -> tuple[list[_SectionPointLite], list[_SectionPointLite]]:
    distances = _merged_side_slope_distances(first, second)
    if len(distances) < 2:
        return ([], [])
    return (
        [_interpolate_side_slope_point_at_distance(first, distance) for distance in distances],
        [_interpolate_side_slope_point_at_distance(second, distance) for distance in distances],
    )


def _merged_side_slope_distances(*rows: list[_SectionPointLite], tolerance: float = 1.0e-6) -> list[float]:
    values: list[float] = []
    for row in rows:
        if not row:
            continue
        start = float(row[0].lateral_offset)
        for point in row:
            values.append(abs(float(point.lateral_offset) - start))
    values = sorted(max(float(value), 0.0) for value in values)
    output: list[float] = []
    for value in values:
        if not output or abs(value - output[-1]) > tolerance:
            output.append(value)
    return output


def _interpolate_side_slope_point_at_distance(
    row: list[_SectionPointLite],
    distance: float,
) -> _SectionPointLite:
    if not row:
        return _SectionPointLite("", 0.0, 0.0, 0.0, 0.0, "")
    if len(row) == 1:
        return row[0]
    distances = _side_slope_row_distances(row)
    target = max(float(distance), 0.0)
    if target <= distances[0] + 1.0e-9:
        return row[0]
    if target >= distances[-1] - 1.0e-9:
        return row[-1]
    for index in range(len(row) - 1):
        start_distance = distances[index]
        end_distance = distances[index + 1]
        if target < start_distance - 1.0e-9 or target > end_distance + 1.0e-9:
            continue
        span = max(end_distance - start_distance, 1.0e-12)
        ratio = (target - start_distance) / span
        start = row[index]
        end = row[index + 1]
        role = _side_slope_interpolated_role(start, end, target, end_distance)
        return _SectionPointLite(
            point_id=f"{start.point_id}->{end.point_id}@{target:.6g}",
            x=float(start.x) + (float(end.x) - float(start.x)) * ratio,
            y=float(start.y) + (float(end.y) - float(start.y)) * ratio,
            z=float(start.z) + (float(end.z) - float(start.z)) * ratio,
            lateral_offset=float(start.lateral_offset) + (float(end.lateral_offset) - float(start.lateral_offset)) * ratio,
            point_role=role,
        )
    return row[-1]


def _side_slope_row_distances(row: list[_SectionPointLite]) -> list[float]:
    if not row:
        return []
    start = float(row[0].lateral_offset)
    return [abs(float(point.lateral_offset) - start) for point in row]


def _side_slope_interpolated_role(
    start: _SectionPointLite,
    end: _SectionPointLite,
    target: float,
    end_distance: float,
) -> str:
    end_role = str(getattr(end, "point_role", "") or "")
    start_role = str(getattr(start, "point_role", "") or "")
    if abs(float(target) - float(end_distance)) <= 1.0e-6:
        return end_role
    if end_role == "bench_surface" or start_role == "bench_surface":
        return "bench_surface"
    if end_role == "daylight_marker":
        return "side_slope_surface"
    return end_role or start_role


def _side_slope_points_for_section(
    section,
    *,
    side_label: str,
    fallback_half_width: float,
) -> list[_SectionPointLite]:
    edge_offset, edge_z = _section_terminal_edge(section, side_label=side_label, fallback_half_width=fallback_half_width)
    frame = getattr(section, "frame", None)
    edge_x, edge_y, edge_z = _xy_at_offset(frame, edge_offset, edge_z)
    direction = 1.0 if side_label == "left" else -1.0
    rows = [
        _SectionPointLite(
            point_id=f"{side_label}:terminal-edge",
            x=edge_x,
            y=edge_y,
            z=edge_z,
            lateral_offset=edge_offset,
            point_role="terminal_edge",
        )
    ]
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"side_slope_surface", "bench_surface", "daylight_marker"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        if side_label == "left" and offset < edge_offset - 1.0e-9:
            continue
        if side_label == "right" and offset > edge_offset + 1.0e-9:
            continue
        rows.append(
            _SectionPointLite(
                point_id=str(getattr(point, "point_id", "") or role),
                x=float(getattr(point, "x", 0.0) or 0.0),
                y=float(getattr(point, "y", 0.0) or 0.0),
                z=float(getattr(point, "z", 0.0) or 0.0),
                lateral_offset=offset,
                point_role=role,
            )
        )
    rows.sort(key=lambda point: (float(point.lateral_offset) - edge_offset) * direction)
    output: list[_SectionPointLite] = []
    for point in rows:
        if output:
            previous = output[-1]
            if (
                abs(float(point.lateral_offset) - float(previous.lateral_offset)) <= 1.0e-9
                and abs(float(point.z) - float(previous.z)) <= 1.0e-9
            ):
                continue
        output.append(point)
    return output


def _terrain_adjusted_side_slope_points_for_section(
    section,
    rows: list[_SectionPointLite],
    *,
    side_label: str,
    existing_ground_surface: TINSurface | None,
) -> list[_SectionPointLite]:
    if existing_ground_surface is None or len(rows) < 1:
        return rows
    terminal = rows[0]
    daylight_width, slope = _section_daylight_policy_for_side(section, side_label=side_label)
    if daylight_width <= 1.0e-9 or abs(float(slope or 0.0)) <= 1.0e-12:
        return rows
    frame = getattr(section, "frame", None)
    normal_x, normal_y = _outward_normal_for_side(frame, side_label=side_label)
    sampling_service = TinSamplingService()
    outer = _resolve_slope_face_outer_point(
        sampling_service=sampling_service,
        surface=existing_ground_surface,
        edge_x=float(terminal.x),
        edge_y=float(terminal.y),
        edge_z=float(terminal.z),
        normal_x=normal_x,
        normal_y=normal_y,
        max_width=daylight_width,
        slope=slope,
    )
    outer_offset = float(terminal.lateral_offset) + (1.0 if side_label == "left" else -1.0) * _distance_xy(
        terminal.x,
        terminal.y,
        outer.x,
        outer.y,
    )
    slope_sign = _slope_sign_from_points(terminal.z, outer.z)
    adjusted: list[_SectionPointLite] = [terminal]
    has_bench_breakline = any(
        str(getattr(point, "point_role", "") or "") == "bench_surface"
        for point in list(rows[1:] or [])
    )
    for point in list(rows[1:] or []):
        if str(getattr(point, "point_role", "") or "") == "daylight_marker":
            continue
        if not _point_between_offsets(
            float(point.lateral_offset),
            float(terminal.lateral_offset),
            outer_offset,
        ):
            continue
        point = _terrain_oriented_side_slope_point(
            point,
            terminal=terminal,
            slope_sign=slope_sign,
            preserve_wrong_direction=has_bench_breakline,
        )
        if point is None:
            continue
        adjusted.append(point)
    if (
        abs(float(adjusted[-1].lateral_offset) - outer_offset) > 1.0e-6
        or abs(float(adjusted[-1].z) - float(outer.z)) > 1.0e-6
    ):
        adjusted.append(
            _SectionPointLite(
                point_id=f"{side_label}:terrain-daylight",
                x=float(outer.x),
                y=float(outer.y),
                z=float(outer.z),
                lateral_offset=outer_offset,
                point_role="daylight_marker",
            )
        )
    return adjusted


def _terrain_oriented_side_slope_point(
    point: _SectionPointLite,
    *,
    terminal: _SectionPointLite,
    slope_sign: int,
    preserve_wrong_direction: bool,
) -> _SectionPointLite | None:
    """Preserve bench breaklines while matching the terrain cut/fill direction."""

    if slope_sign == 0:
        return point
    terminal_z = float(terminal.z)
    point_z = float(point.z)
    wrong_fill_or_cut_direction = (
        (slope_sign > 0 and point_z < terminal_z - 1.0e-6)
        or (slope_sign < 0 and point_z > terminal_z + 1.0e-6)
    )
    if not wrong_fill_or_cut_direction:
        return point
    if not preserve_wrong_direction:
        return None
    oriented_z = terminal_z + float(slope_sign) * abs(point_z - terminal_z)
    return _SectionPointLite(
        point_id=point.point_id,
        x=point.x,
        y=point.y,
        z=oriented_z,
        lateral_offset=point.lateral_offset,
        point_role=point.point_role,
    )


def _section_daylight_policy_for_side(section, *, side_label: str) -> tuple[float, float]:
    if side_label == "left":
        return (
            max(float(getattr(section, "daylight_left_width", 0.0) or 0.0), 0.0),
            float(getattr(section, "daylight_left_slope", 0.0) or 0.0),
        )
    return (
        max(float(getattr(section, "daylight_right_width", 0.0) or 0.0), 0.0),
        float(getattr(section, "daylight_right_slope", 0.0) or 0.0),
    )


def _outward_normal_for_side(frame, *, side_label: str) -> tuple[float, float]:
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    nx = -math.sin(angle_rad)
    ny = math.cos(angle_rad)
    if side_label == "right":
        return -nx, -ny
    return nx, ny


def _distance_xy(x0: float, y0: float, x1: float, y1: float) -> float:
    return math.hypot(float(x1) - float(x0), float(y1) - float(y0))


def _slope_sign_from_points(start_z: float, end_z: float, *, tolerance: float = 1.0e-6) -> int:
    delta = float(end_z) - float(start_z)
    if delta > tolerance:
        return 1
    if delta < -tolerance:
        return -1
    return 0


def _point_between_offsets(value: float, start: float, end: float, *, tolerance: float = 1.0e-6) -> bool:
    low = min(float(start), float(end)) - tolerance
    high = max(float(start), float(end)) + tolerance
    return low <= float(value) <= high


def _section_terminal_edge(section, *, side_label: str, fallback_half_width: float) -> tuple[float, float]:
    left_width, right_width = _surface_width_rows_for_section(section, fallback_half_width=fallback_half_width)
    frame = getattr(section, "frame", None)
    frame_z = float(getattr(frame, "z", 0.0) or 0.0)
    edge = (left_width, frame_z) if side_label == "left" else (-right_width, frame_z)
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


def _xy_at_offset(frame, offset: float, z: float) -> tuple[float, float, float]:
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    base_x = float(getattr(frame, "x", 0.0) or 0.0)
    base_y = float(getattr(frame, "y", 0.0) or 0.0)
    return base_x + normal_x * float(offset), base_y + normal_y * float(offset), float(z)


def _frame_rows(applied_section_set: AppliedSectionSet) -> list[object]:
    return [getattr(section, "frame", None) for section in _section_rows(applied_section_set) if getattr(section, "frame", None) is not None]


def _section_rows(applied_section_set: AppliedSectionSet) -> list[object]:
    sections = list(getattr(applied_section_set, "sections", []) or [])
    section_by_id = {str(getattr(section, "applied_section_id", "") or ""): section for section in sections}
    output = []
    for row in list(getattr(applied_section_set, "station_rows", []) or []):
        section = section_by_id.get(str(getattr(row, "applied_section_id", "") or ""))
        if section is not None and getattr(section, "frame", None) is not None:
            output.append(section)
    return output


def _section_point_grid(sections: list[object], *, point_role: str) -> list[list[object]]:
    if not point_role:
        return []
    grid: list[list[object]] = []
    reference_offsets: list[float] | None = None
    for section in list(sections or []):
        rows = [
            point
            for point in list(getattr(section, "point_rows", []) or [])
            if str(getattr(point, "point_role", "") or "") == point_role
        ]
        rows.sort(key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
        if len(rows) < 2:
            return []
        offsets = [round(float(getattr(point, "lateral_offset", 0.0) or 0.0), 6) for point in rows]
        if reference_offsets is None:
            reference_offsets = offsets
        elif offsets != reference_offsets:
            return []
        grid.append(rows)
    return grid if len(grid) >= 2 else []


def _surface_width_rows(applied_section_set: AppliedSectionSet, *, fallback_half_width: float) -> list[tuple[float, float]]:
    widths: list[tuple[float, float]] = []
    for section in _section_rows(applied_section_set):
        left_width = float(getattr(section, "surface_left_width", 0.0) or 0.0)
        right_width = float(getattr(section, "surface_right_width", 0.0) or 0.0)
        if left_width <= 0.0 and right_width <= 0.0:
            left_width = fallback_half_width
            right_width = fallback_half_width
        else:
            if left_width <= 0.0:
                left_width = right_width
            if right_width <= 0.0:
                right_width = left_width
        widths.append((max(left_width, 0.1), max(right_width, 0.1)))
    return widths


def _daylight_inner_edge_rows(
    applied_section_set: AppliedSectionSet,
    *,
    fallback_half_width: float,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Return left/right slope-face start offsets and elevations.

    The slope face starts at the outermost built section edge. Ditch/drainage
    points are separate from FG, but they are still part of the Assembly
    terminal geometry and must move the slope-face start outward.
    """

    rows: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for section in _section_rows(applied_section_set):
        frame = getattr(section, "frame", None)
        frame_z = float(getattr(frame, "z", 0.0) or 0.0)
        left_width, right_width = _surface_width_rows_for_section(
            section,
            fallback_half_width=fallback_half_width,
        )
        left_edge = (left_width, frame_z)
        right_edge = (-right_width, frame_z)
        for point in list(getattr(section, "point_rows", []) or []):
            role = str(getattr(point, "point_role", "") or "")
            if role not in {"fg_surface", "ditch_surface"}:
                continue
            offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
            z = float(getattr(point, "z", frame_z) or frame_z)
            if offset > left_edge[0] or (abs(offset - left_edge[0]) <= 1.0e-9 and z > left_edge[1]):
                left_edge = (offset, z)
            if offset < right_edge[0] or (abs(offset - right_edge[0]) <= 1.0e-9 and z > right_edge[1]):
                right_edge = (offset, z)
        rows.append((left_edge, right_edge))
    return rows


def _surface_width_rows_for_section(section, *, fallback_half_width: float) -> tuple[float, float]:
    left_width = float(getattr(section, "surface_left_width", 0.0) or 0.0)
    right_width = float(getattr(section, "surface_right_width", 0.0) or 0.0)
    if left_width <= 0.0 and right_width <= 0.0:
        left_width = fallback_half_width
        right_width = fallback_half_width
    else:
        if left_width <= 0.0:
            left_width = right_width
        if right_width <= 0.0:
            right_width = left_width
    return max(left_width, 0.1), max(right_width, 0.1)


def _daylight_rows(applied_section_set: AppliedSectionSet) -> list[tuple[float, float, float, float]]:
    rows: list[tuple[float, float, float, float]] = []
    for section in _section_rows(applied_section_set):
        rows.append(
            (
                max(float(getattr(section, "daylight_left_width", 0.0) or 0.0), 0.0),
                max(float(getattr(section, "daylight_right_width", 0.0) or 0.0), 0.0),
                float(getattr(section, "daylight_left_slope", 0.0) or 0.0),
                float(getattr(section, "daylight_right_slope", 0.0) or 0.0),
            )
        )
    return rows


@dataclass(frozen=True)
class _SlopeFaceOuterPoint:
    x: float
    y: float
    z: float
    sampled: bool = False
    intersected: bool = False
    status: str = "fallback"


def _resolve_slope_face_outer_point(
    *,
    sampling_service: TinSamplingService,
    surface: TINSurface | None,
    edge_x: float,
    edge_y: float,
    edge_z: float,
    normal_x: float,
    normal_y: float,
    max_width: float,
    slope: float,
) -> _SlopeFaceOuterPoint:
    max_width = max(float(max_width or 0.0), 0.0)
    slope = _terrain_oriented_slope(
        sampling_service=sampling_service,
        surface=surface,
        edge_x=edge_x,
        edge_y=edge_y,
        edge_z=edge_z,
        slope=slope,
    )
    fallback_x = float(edge_x) + float(normal_x) * max_width
    fallback_y = float(edge_y) + float(normal_y) * max_width
    fallback_z = float(edge_z) + float(slope) * max_width
    if surface is None:
        return _SlopeFaceOuterPoint(fallback_x, fallback_y, fallback_z, status="fallback:no_existing_ground_tin")

    intersection = _find_slope_face_tin_intersection(
        sampling_service=sampling_service,
        surface=surface,
        edge_x=float(edge_x),
        edge_y=float(edge_y),
        edge_z=float(edge_z),
        normal_x=float(normal_x),
        normal_y=float(normal_y),
        max_width=max_width,
        slope=float(slope),
    )
    if intersection is not None:
        return _SlopeFaceOuterPoint(*intersection, sampled=True, intersected=True, status="intersection")

    sample = sampling_service.sample_xy(surface=surface, x=fallback_x, y=fallback_y)
    if bool(getattr(sample, "found", False)) and getattr(sample, "z", None) is not None:
        return _SlopeFaceOuterPoint(fallback_x, fallback_y, float(sample.z), sampled=True, status="sampled_outer_edge")
    return _SlopeFaceOuterPoint(fallback_x, fallback_y, fallback_z, status="fallback:no_eg_hit_in_search_width")


def _terrain_oriented_slope(
    *,
    sampling_service: TinSamplingService,
    surface: TINSurface | None,
    edge_x: float,
    edge_y: float,
    edge_z: float,
    slope: float,
    tolerance: float = 1.0e-6,
) -> float:
    slope_value = float(slope or 0.0)
    if surface is None or abs(slope_value) <= 1.0e-12:
        return slope_value
    sample = sampling_service.sample_xy(surface=surface, x=float(edge_x), y=float(edge_y))
    if not bool(getattr(sample, "found", False)) or getattr(sample, "z", None) is None:
        return slope_value
    delta = float(sample.z) - float(edge_z)
    if delta > tolerance:
        return abs(slope_value)
    if delta < -tolerance:
        return -abs(slope_value)
    return slope_value


def _find_slope_face_tin_intersection(
    *,
    sampling_service: TinSamplingService,
    surface: TINSurface,
    edge_x: float,
    edge_y: float,
    edge_z: float,
    normal_x: float,
    normal_y: float,
    max_width: float,
    slope: float,
    steps: int = 24,
    tolerance: float = 1.0e-6,
) -> tuple[float, float, float] | None:
    if max_width <= tolerance:
        return None

    previous_distance: float | None = None
    previous_delta: float | None = None
    for step in range(0, max(2, int(steps)) + 1):
        distance = max_width * float(step) / float(max(2, int(steps)))
        delta = _slope_face_delta(
            sampling_service=sampling_service,
            surface=surface,
            edge_x=edge_x,
            edge_y=edge_y,
            edge_z=edge_z,
            normal_x=normal_x,
            normal_y=normal_y,
            distance=distance,
            slope=slope,
        )
        if delta is None:
            continue
        if abs(delta) <= tolerance and distance > tolerance:
            return _slope_face_point(edge_x, edge_y, edge_z, normal_x, normal_y, distance, slope)
        if previous_delta is not None and previous_distance is not None and previous_delta * delta < 0.0:
            return _bisect_slope_face_intersection(
                sampling_service=sampling_service,
                surface=surface,
                edge_x=edge_x,
                edge_y=edge_y,
                edge_z=edge_z,
                normal_x=normal_x,
                normal_y=normal_y,
                slope=slope,
                low=previous_distance,
                high=distance,
                tolerance=tolerance,
            )
        previous_distance = distance
        previous_delta = delta
    return None


def _bisect_slope_face_intersection(
    *,
    sampling_service: TinSamplingService,
    surface: TINSurface,
    edge_x: float,
    edge_y: float,
    edge_z: float,
    normal_x: float,
    normal_y: float,
    slope: float,
    low: float,
    high: float,
    tolerance: float,
    iterations: int = 32,
) -> tuple[float, float, float] | None:
    low_delta = _slope_face_delta(
        sampling_service=sampling_service,
        surface=surface,
        edge_x=edge_x,
        edge_y=edge_y,
        edge_z=edge_z,
        normal_x=normal_x,
        normal_y=normal_y,
        distance=low,
        slope=slope,
    )
    if low_delta is None:
        return None
    for _index in range(max(1, int(iterations))):
        mid = (float(low) + float(high)) * 0.5
        mid_delta = _slope_face_delta(
            sampling_service=sampling_service,
            surface=surface,
            edge_x=edge_x,
            edge_y=edge_y,
            edge_z=edge_z,
            normal_x=normal_x,
            normal_y=normal_y,
            distance=mid,
            slope=slope,
        )
        if mid_delta is None:
            return None
        if abs(mid_delta) <= tolerance or abs(float(high) - float(low)) <= tolerance:
            return _slope_face_point(edge_x, edge_y, edge_z, normal_x, normal_y, mid, slope)
        if low_delta * mid_delta <= 0.0:
            high = mid
        else:
            low = mid
            low_delta = mid_delta
    return _slope_face_point(edge_x, edge_y, edge_z, normal_x, normal_y, (float(low) + float(high)) * 0.5, slope)


def _slope_face_delta(
    *,
    sampling_service: TinSamplingService,
    surface: TINSurface,
    edge_x: float,
    edge_y: float,
    edge_z: float,
    normal_x: float,
    normal_y: float,
    distance: float,
    slope: float,
) -> float | None:
    x, y, z = _slope_face_point(edge_x, edge_y, edge_z, normal_x, normal_y, distance, slope)
    sample = sampling_service.sample_xy(surface=surface, x=x, y=y)
    if not bool(getattr(sample, "found", False)) or getattr(sample, "z", None) is None:
        return None
    return float(z) - float(sample.z)


def _slope_face_point(
    edge_x: float,
    edge_y: float,
    edge_z: float,
    normal_x: float,
    normal_y: float,
    distance: float,
    slope: float,
) -> tuple[float, float, float]:
    distance = float(distance)
    return (
        float(edge_x) + float(normal_x) * distance,
        float(edge_y) + float(normal_y) * distance,
        float(edge_z) + float(slope) * distance,
    )


def _daylight_provenance_notes(surface: TINSurface | None, hit_count: int, miss_count: int, intersection_count: int) -> str:
    if surface is None:
        return "First-slice corridor slope-face surface built from applied-section side-slope policy without an existing-ground TIN tie-in."
    return (
        "First-slice corridor slope-face surface built from applied-section side-slope policy "
        "and sampled existing-ground TIN tie-in. "
        f"EG intersections: {int(intersection_count)}, hits: {int(hit_count)}, misses: {int(miss_count)}."
    )

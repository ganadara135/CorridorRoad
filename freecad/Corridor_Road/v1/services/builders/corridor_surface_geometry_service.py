"""Corridor surface geometry builder service for CorridorRoad v1."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ...models.result.applied_section import AppliedSection, AppliedSectionFrame, AppliedSectionPoint
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex
from ..evaluation.tin_sampling_service import TinSamplingService


SUPPLEMENTAL_SAMPLING_MAX_SPACING = 5.0
SUPPLEMENTAL_DAYLIGHT_WIDTH_DELTA_THRESHOLD = 1.5
SUPPLEMENTAL_SLOPE_DELTA_THRESHOLD = 0.05
SUPPLEMENTAL_FRAME_Z_DELTA_THRESHOLD = 0.5


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
    supplemental_sampling_enabled: bool = False
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING


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

        sections = _section_rows_for_request(request)
        frame_rows = [getattr(section, "frame", None) for section in sections if getattr(section, "frame", None) is not None]
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
        edge_rows = _daylight_inner_edge_rows_for_sections(sections, fallback_half_width=fallback_half_width)
        daylight_rows = _daylight_rows_for_sections(sections)
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
                _append_side_slope_strip_triangles(
                    triangles,
                    triangle_id_prefix=f"span:{index}:left",
                    side_label="left",
                    p00=li0,
                    p01=lo0,
                    p10=li1,
                    p11=lo1,
                    triangle_kind="corridor_daylight_strip",
                )
            if daylight_rows[index][1] > 0.0 and daylight_rows[index + 1][1] > 0.0:
                ri0 = f"v{index}:right:inner"
                ro0 = f"v{index}:right:outer"
                ri1 = f"v{index + 1}:right:inner"
                ro1 = f"v{index + 1}:right:outer"
                _append_side_slope_strip_triangles(
                    triangles,
                    triangle_id_prefix=f"span:{index}:right",
                    side_label="right",
                    p00=ri0,
                    p01=ro0,
                    p10=ri1,
                    p11=ro1,
                    triangle_kind="corridor_daylight_strip",
                )

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

        sections = _section_rows_for_request(request)
        frame_rows = [getattr(section, "frame", None) for section in sections if getattr(section, "frame", None) is not None]
        if len(frame_rows) < 2:
            raise ValueError("At least two applied-section frames are required to build a corridor surface.")

        fallback_half_width = max(float(request.fallback_half_width or 0.0), 0.1)
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
        width_rows = _surface_width_rows_for_sections(sections, fallback_half_width=fallback_half_width)
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
            mesh_rows = list(_harmonized_side_slope_pair_rows(grid[section_index], grid[section_index + 1]))
            if len(mesh_rows[0]) < 2 or len(mesh_rows[1]) < 2:
                continue
            for row_index, points in enumerate(mesh_rows):
                for point_index, point in enumerate(points):
                    vertices.append(
                        TINVertex(
                            vertex_id=f"v{section_index}:{side_label}:r{row_index}:p{point_index}",
                            x=float(point.x),
                            y=float(point.y),
                            z=float(point.z),
                            source_point_ref=_span_source_point_ref(sections, section_index, row_index, len(mesh_rows), point),
                            notes=str(getattr(point, "point_role", "") or ""),
                        )
                    )
            for row_index in range(len(mesh_rows) - 1):
                point_count = min(len(mesh_rows[row_index]), len(mesh_rows[row_index + 1]))
                for point_index in range(point_count - 1):
                    p00 = f"v{section_index}:{side_label}:r{row_index}:p{point_index}"
                    p01 = f"v{section_index}:{side_label}:r{row_index}:p{point_index + 1}"
                    p10 = f"v{section_index}:{side_label}:r{row_index + 1}:p{point_index}"
                    p11 = f"v{section_index}:{side_label}:r{row_index + 1}:p{point_index + 1}"
                    if _same_section_point_xy(mesh_rows[row_index][point_index], mesh_rows[row_index][point_index + 1]):
                        continue
                    if _same_section_point_xy(mesh_rows[row_index + 1][point_index], mesh_rows[row_index + 1][point_index + 1]):
                        continue
                    _append_side_slope_strip_triangles(
                        triangles,
                        triangle_id_prefix=f"span:{section_index}:{side_label}:r{row_index}:p{point_index}",
                        side_label=side_label,
                        p00=p00,
                        p01=p01,
                        p10=p10,
                        p11=p11,
                        triangle_kind="corridor_daylight_bench_strip",
                    )
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


def _append_side_slope_strip_triangles(
    triangles: list[TINTriangle],
    *,
    triangle_id_prefix: str,
    side_label: str,
    p00: str,
    p01: str,
    p10: str,
    p11: str,
    triangle_kind: str,
) -> None:
    if str(side_label or "").strip().lower() == "left":
        triangles.append(TINTriangle(f"{triangle_id_prefix}:a", p00, p11, p01, triangle_kind=triangle_kind))
        triangles.append(TINTriangle(f"{triangle_id_prefix}:b", p00, p10, p11, triangle_kind=triangle_kind))
        return
    triangles.append(TINTriangle(f"{triangle_id_prefix}:a", p00, p01, p11, triangle_kind=triangle_kind))
    triangles.append(TINTriangle(f"{triangle_id_prefix}:b", p00, p11, p10, triangle_kind=triangle_kind))


def _same_section_point_xy(first: _SectionPointLite, second: _SectionPointLite, tolerance: float = 1.0e-8) -> bool:
    return _distance_xy(first.x, first.y, second.x, second.y) <= tolerance


def _harmonized_side_slope_pair_rows(
    first: list[_SectionPointLite],
    second: list[_SectionPointLite],
) -> tuple[list[_SectionPointLite], list[_SectionPointLite]]:
    """Return pair rows with matching point counts while preserving both polylines."""

    first = list(first or [])
    second = list(second or [])
    if len(first) >= 2 and len(first) == len(second):
        return first, second
    params = _merged_side_slope_polyline_params(first, second)
    if len(params) < 2:
        return first, second
    first_row = [_interpolate_side_slope_point_at_param(first, param) for param in params]
    second_row = [_interpolate_side_slope_point_at_param(second, param) for param in params]
    if len(first_row) >= 2 and len(first_row) == len(second_row):
        return first_row, second_row
    return first, second


def _merged_side_slope_polyline_params(*rows: list[_SectionPointLite], tolerance: float = 1.0e-9) -> list[float]:
    params = [0.0, 1.0]
    for row in rows:
        params.extend(_side_slope_polyline_params(row))
    output: list[float] = []
    for value in sorted(max(0.0, min(1.0, float(param))) for param in params):
        if not output or abs(value - output[-1]) > tolerance:
            output.append(value)
    return output


def _side_slope_polyline_params(row: list[_SectionPointLite]) -> list[float]:
    points = list(row or [])
    if len(points) < 2:
        return []
    distances = [0.0]
    total = 0.0
    for index in range(1, len(points)):
        total += _distance_3d(points[index - 1], points[index])
        distances.append(total)
    if total <= 1.0e-12:
        denom = max(1, len(points) - 1)
        return [float(index) / float(denom) for index in range(len(points))]
    return [float(distance) / float(total) for distance in distances]


def _interpolate_side_slope_point_at_param(row: list[_SectionPointLite], param: float) -> _SectionPointLite:
    points = list(row or [])
    if not points:
        return _SectionPointLite("", 0.0, 0.0, 0.0, 0.0, "")
    if len(points) == 1:
        return points[0]
    params = _side_slope_polyline_params(points)
    if len(params) != len(points):
        return points[-1]
    target = max(0.0, min(1.0, float(param)))
    if target <= params[0] + 1.0e-9:
        return points[0]
    if target >= params[-1] - 1.0e-9:
        return points[-1]
    last_segment = max(0, len(points) - 2)
    segment = 0
    while segment < last_segment and target > params[segment + 1] + 1.0e-12:
        segment += 1
    start = points[segment]
    end = points[segment + 1]
    start_param = params[segment]
    end_param = params[segment + 1]
    span = max(float(end_param) - float(start_param), 1.0e-12)
    ratio = (target - float(start_param)) / span
    role = _interpolated_side_slope_role(start, end, ratio)
    return _SectionPointLite(
        point_id=f"{start.point_id}->{end.point_id}@{target:.6g}",
        x=_lerp(start.x, end.x, ratio),
        y=_lerp(start.y, end.y, ratio),
        z=_lerp(start.z, end.z, ratio),
        lateral_offset=_lerp(start.lateral_offset, end.lateral_offset, ratio),
        point_role=role,
    )


def _interpolated_side_slope_role(start: _SectionPointLite, end: _SectionPointLite, ratio: float) -> str:
    if float(ratio) >= 1.0 - 1.0e-9:
        return str(getattr(end, "point_role", "") or "")
    start_role = str(getattr(start, "point_role", "") or "")
    end_role = str(getattr(end, "point_role", "") or "")
    if start_role == "bench_surface" or end_role == "bench_surface":
        return "bench_surface"
    if start_role == "terminal_edge":
        return end_role if end_role != "daylight_marker" else "side_slope_surface"
    if end_role == "daylight_marker":
        return start_role if start_role else "side_slope_surface"
    return start_role or end_role


def _distance_3d(first: _SectionPointLite, second: _SectionPointLite) -> float:
    return math.sqrt(
        (float(second.x) - float(first.x)) ** 2
        + (float(second.y) - float(first.y)) ** 2
        + (float(second.z) - float(first.z)) ** 2
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
            # AppliedSection daylight markers are evaluated source-truth for Build Corridor.
            # Terrain tie-in here is only a fallback for rows that do not yet carry one.
            if not _row_has_daylight_marker(rows):
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


def _row_has_daylight_marker(row: list[_SectionPointLite]) -> bool:
    return any(str(getattr(point, "point_role", "") or "") == "daylight_marker" for point in list(row or []))


def _span_source_point_ref(
    sections: list[object],
    section_index: int,
    row_index: int,
    row_count: int,
    point: _SectionPointLite,
) -> str:
    if row_index <= 0:
        section = sections[section_index] if section_index < len(sections) else None
    elif row_index >= max(0, int(row_count) - 1):
        section = sections[section_index + 1] if section_index + 1 < len(sections) else None
    else:
        section = None
    section_id = str(getattr(section, "applied_section_id", "") or "") if section is not None else ""
    if section_id:
        return f"{section_id}:{point.point_id}"
    return str(getattr(point, "point_id", "") or "")


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
                and "daylight_marker"
                not in {
                    str(getattr(point, "point_role", "") or ""),
                    str(getattr(previous, "point_role", "") or ""),
                }
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
    has_bench_breakline = any(
        str(getattr(point, "point_role", "") or "") == "bench_surface"
        for point in list(rows[1:] or [])
    )
    sampling_service = TinSamplingService()
    if has_bench_breakline:
        piecewise_rows = _terrain_adjusted_piecewise_side_slope_points(
            rows,
            surface=existing_ground_surface,
            sampling_service=sampling_service,
        )
        if piecewise_rows is not None:
            return piecewise_rows
    normal_x, normal_y = _outward_normal_for_side(frame, side_label=side_label)
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


def _terrain_adjusted_piecewise_side_slope_points(
    rows: list[_SectionPointLite],
    *,
    surface: TINSurface,
    sampling_service: TinSamplingService,
) -> list[_SectionPointLite] | None:
    if len(rows) < 2:
        return None
    terminal = rows[0]
    slope_sign = _terrain_slope_sign_at_point(
        terminal,
        surface=surface,
        sampling_service=sampling_service,
    )
    if slope_sign == 0:
        return rows
    oriented = [terminal]
    for point in list(rows[1:] or []):
        oriented_point = _terrain_oriented_side_slope_point(
            point,
            terminal=terminal,
            slope_sign=slope_sign,
            preserve_wrong_direction=True,
        )
        if oriented_point is not None:
            oriented.append(oriented_point)
    oriented = _unique_side_slope_points(oriented)
    if len(oriented) < 2:
        return None
    intersection = _find_piecewise_side_slope_terrain_intersection(
        oriented,
        surface=surface,
        sampling_service=sampling_service,
    )
    if intersection is None:
        return oriented
    segment_index, point = intersection
    return oriented[: segment_index + 1] + [point]


def _terrain_slope_sign_at_point(
    point: _SectionPointLite,
    *,
    surface: TINSurface,
    sampling_service: TinSamplingService,
    tolerance: float = 1.0e-6,
) -> int:
    sample = sampling_service.sample_xy(surface=surface, x=float(point.x), y=float(point.y))
    if not bool(getattr(sample, "found", False)) or getattr(sample, "z", None) is None:
        return 0
    delta = float(sample.z) - float(point.z)
    if delta > tolerance:
        return 1
    if delta < -tolerance:
        return -1
    return 0


def _unique_side_slope_points(rows: list[_SectionPointLite]) -> list[_SectionPointLite]:
    output: list[_SectionPointLite] = []
    for point in list(rows or []):
        if output:
            previous = output[-1]
            if (
                abs(float(point.lateral_offset) - float(previous.lateral_offset)) <= 1.0e-9
                and abs(float(point.z) - float(previous.z)) <= 1.0e-9
                and "daylight_marker"
                not in {
                    str(getattr(point, "point_role", "") or ""),
                    str(getattr(previous, "point_role", "") or ""),
                }
            ):
                continue
        output.append(point)
    return output


def _find_piecewise_side_slope_terrain_intersection(
    rows: list[_SectionPointLite],
    *,
    surface: TINSurface,
    sampling_service: TinSamplingService,
    tolerance: float = 1.0e-6,
) -> tuple[int, _SectionPointLite] | None:
    if len(rows) < 2:
        return None
    previous_delta = _side_slope_point_terrain_delta(rows[0], surface=surface, sampling_service=sampling_service)
    for index in range(len(rows) - 1):
        start = rows[index]
        end = rows[index + 1]
        end_delta = _side_slope_point_terrain_delta(end, surface=surface, sampling_service=sampling_service)
        if previous_delta is None:
            previous_delta = end_delta
            continue
        if end_delta is None:
            continue
        if abs(end_delta) <= tolerance and index > 0:
            return index + 1, _as_daylight_marker(end)
        if previous_delta * end_delta < 0.0:
            intersection = _bisect_piecewise_side_slope_intersection(
                start,
                end,
                surface=surface,
                sampling_service=sampling_service,
                tolerance=tolerance,
            )
            if intersection is not None:
                return index, intersection
        previous_delta = end_delta
    return None


def _side_slope_point_terrain_delta(
    point: _SectionPointLite,
    *,
    surface: TINSurface,
    sampling_service: TinSamplingService,
) -> float | None:
    sample = sampling_service.sample_xy(surface=surface, x=float(point.x), y=float(point.y))
    if not bool(getattr(sample, "found", False)) or getattr(sample, "z", None) is None:
        return None
    return float(point.z) - float(sample.z)


def _bisect_piecewise_side_slope_intersection(
    start: _SectionPointLite,
    end: _SectionPointLite,
    *,
    surface: TINSurface,
    sampling_service: TinSamplingService,
    tolerance: float,
    iterations: int = 32,
) -> _SectionPointLite | None:
    low = 0.0
    high = 1.0
    low_point = _interpolate_between_side_slope_points(start, end, low, role=start.point_role)
    low_delta = _side_slope_point_terrain_delta(low_point, surface=surface, sampling_service=sampling_service)
    if low_delta is None:
        return None
    for _index in range(max(1, int(iterations))):
        mid = (low + high) * 0.5
        mid_point = _interpolate_between_side_slope_points(start, end, mid, role="daylight_marker")
        mid_delta = _side_slope_point_terrain_delta(mid_point, surface=surface, sampling_service=sampling_service)
        if mid_delta is None:
            return None
        if abs(mid_delta) <= tolerance or abs(high - low) <= tolerance:
            return _as_daylight_marker(mid_point)
        if low_delta * mid_delta <= 0.0:
            high = mid
        else:
            low = mid
            low_delta = mid_delta
    return _as_daylight_marker(
        _interpolate_between_side_slope_points(start, end, (low + high) * 0.5, role="daylight_marker")
    )


def _interpolate_between_side_slope_points(
    start: _SectionPointLite,
    end: _SectionPointLite,
    ratio: float,
    *,
    role: str,
) -> _SectionPointLite:
    t = min(max(float(ratio), 0.0), 1.0)
    return _SectionPointLite(
        point_id=f"{start.point_id}->{end.point_id}@{t:.6g}",
        x=float(start.x) + (float(end.x) - float(start.x)) * t,
        y=float(start.y) + (float(end.y) - float(start.y)) * t,
        z=float(start.z) + (float(end.z) - float(start.z)) * t,
        lateral_offset=float(start.lateral_offset) + (float(end.lateral_offset) - float(start.lateral_offset)) * t,
        point_role=role,
    )


def _as_daylight_marker(point: _SectionPointLite) -> _SectionPointLite:
    return _SectionPointLite(
        point_id=point.point_id if str(point.point_role or "") == "daylight_marker" else f"{point.point_id}:daylight",
        x=point.x,
        y=point.y,
        z=point.z,
        lateral_offset=point.lateral_offset,
        point_role="daylight_marker",
    )


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


def _section_rows_for_request(request: CorridorDesignSurfaceGeometryRequest) -> list[object]:
    sections = _section_rows(request.applied_section_set)
    if not bool(getattr(request, "supplemental_sampling_enabled", False)):
        return sections
    return _supplemental_sampled_sections(
        sections,
        max_spacing=float(getattr(request, "supplemental_sampling_max_spacing", SUPPLEMENTAL_SAMPLING_MAX_SPACING) or SUPPLEMENTAL_SAMPLING_MAX_SPACING),
    )


def _supplemental_sampled_sections(
    sections: list[object],
    *,
    max_spacing: float,
) -> list[object]:
    if len(sections) < 2:
        return sections
    spacing = max(float(max_spacing or 0.0), 0.1)
    output: list[object] = []
    for index in range(len(sections) - 1):
        first = sections[index]
        second = sections[index + 1]
        output.append(first)
        if not _span_needs_supplemental_sampling(first, second, max_spacing=spacing):
            continue
        step_count = max(2, int(math.ceil(_section_station_delta(first, second) / spacing)))
        for step in range(1, step_count):
            ratio = float(step) / float(step_count)
            output.append(_interpolate_applied_section(first, second, ratio, sequence_index=step))
    output.append(sections[-1])
    return output


def _span_needs_supplemental_sampling(first, second, *, max_spacing: float) -> bool:
    if _section_station_delta(first, second) > float(max_spacing) + 1.0e-6:
        return True
    if max(
        abs(float(getattr(second, "daylight_left_width", 0.0) or 0.0) - float(getattr(first, "daylight_left_width", 0.0) or 0.0)),
        abs(float(getattr(second, "daylight_right_width", 0.0) or 0.0) - float(getattr(first, "daylight_right_width", 0.0) or 0.0)),
    ) > SUPPLEMENTAL_DAYLIGHT_WIDTH_DELTA_THRESHOLD:
        return True
    if max(
        abs(float(getattr(second, "daylight_left_slope", 0.0) or 0.0) - float(getattr(first, "daylight_left_slope", 0.0) or 0.0)),
        abs(float(getattr(second, "daylight_right_slope", 0.0) or 0.0) - float(getattr(first, "daylight_right_slope", 0.0) or 0.0)),
    ) > SUPPLEMENTAL_SLOPE_DELTA_THRESHOLD:
        return True
    first_frame = getattr(first, "frame", None)
    second_frame = getattr(second, "frame", None)
    if abs(float(getattr(second_frame, "z", 0.0) or 0.0) - float(getattr(first_frame, "z", 0.0) or 0.0)) > SUPPLEMENTAL_FRAME_Z_DELTA_THRESHOLD:
        return True
    return False


def _section_station_delta(first, second) -> float:
    first_frame = getattr(first, "frame", None)
    second_frame = getattr(second, "frame", None)
    first_station = float(getattr(first_frame, "station", getattr(first, "station", 0.0)) or 0.0)
    second_station = float(getattr(second_frame, "station", getattr(second, "station", first_station)) or first_station)
    return abs(second_station - first_station)


def _interpolate_applied_section(first, second, ratio: float, *, sequence_index: int) -> AppliedSection:
    t = min(max(float(ratio), 0.0), 1.0)
    first_frame = getattr(first, "frame", None)
    second_frame = getattr(second, "frame", None)
    frame = _interpolate_applied_section_frame(first_frame, second_frame, t)
    first_id = str(getattr(first, "applied_section_id", "") or "section")
    second_id = str(getattr(second, "applied_section_id", "") or "section")
    return AppliedSection(
        schema_version=int(getattr(first, "schema_version", getattr(second, "schema_version", 1)) or 1),
        project_id=str(getattr(first, "project_id", getattr(second, "project_id", "")) or ""),
        applied_section_id=f"{first_id}->{second_id}:supplemental:{sequence_index}",
        corridor_id=str(getattr(first, "corridor_id", getattr(second, "corridor_id", "")) or ""),
        alignment_id=str(getattr(first, "alignment_id", getattr(second, "alignment_id", "")) or ""),
        profile_id=str(getattr(first, "profile_id", getattr(second, "profile_id", "")) or ""),
        assembly_id=str(getattr(first, "assembly_id", getattr(second, "assembly_id", "")) or ""),
        station=float(getattr(frame, "station", 0.0) or 0.0),
        template_id=str(getattr(first, "template_id", getattr(second, "template_id", "")) or ""),
        region_id=str(getattr(first, "region_id", getattr(second, "region_id", "")) or ""),
        frame=frame,
        surface_left_width=_lerp(getattr(first, "surface_left_width", 0.0), getattr(second, "surface_left_width", 0.0), t),
        surface_right_width=_lerp(getattr(first, "surface_right_width", 0.0), getattr(second, "surface_right_width", 0.0), t),
        subgrade_depth=_lerp(getattr(first, "subgrade_depth", 0.0), getattr(second, "subgrade_depth", 0.0), t),
        daylight_left_width=_lerp(getattr(first, "daylight_left_width", 0.0), getattr(second, "daylight_left_width", 0.0), t),
        daylight_right_width=_lerp(getattr(first, "daylight_right_width", 0.0), getattr(second, "daylight_right_width", 0.0), t),
        daylight_left_slope=_lerp(getattr(first, "daylight_left_slope", 0.0), getattr(second, "daylight_left_slope", 0.0), t),
        daylight_right_slope=_lerp(getattr(first, "daylight_right_slope", 0.0), getattr(second, "daylight_right_slope", 0.0), t),
        point_rows=_interpolate_applied_section_points(first, second, t),
        component_rows=list(getattr(first, "component_rows", []) or []),
        quantity_rows=[],
        active_structure_ids=list(getattr(first, "active_structure_ids", []) or []),
        active_structure_rule_ids=list(getattr(first, "active_structure_rule_ids", []) or []),
        active_structure_influence_zone_ids=list(getattr(first, "active_structure_influence_zone_ids", []) or []),
        structure_diagnostic_rows=list(getattr(first, "structure_diagnostic_rows", []) or []),
    )


def _interpolate_applied_section_frame(first, second, ratio: float) -> AppliedSectionFrame:
    t = min(max(float(ratio), 0.0), 1.0)
    return AppliedSectionFrame(
        station=_lerp(getattr(first, "station", 0.0), getattr(second, "station", 0.0), t),
        x=_lerp(getattr(first, "x", 0.0), getattr(second, "x", 0.0), t),
        y=_lerp(getattr(first, "y", 0.0), getattr(second, "y", 0.0), t),
        z=_lerp(getattr(first, "z", 0.0), getattr(second, "z", 0.0), t),
        tangent_direction_deg=_interpolate_angle_degrees(
            float(getattr(first, "tangent_direction_deg", 0.0) or 0.0),
            float(getattr(second, "tangent_direction_deg", 0.0) or 0.0),
            t,
        ),
        profile_grade=_lerp(getattr(first, "profile_grade", 0.0), getattr(second, "profile_grade", 0.0), t),
        alignment_status=str(getattr(first, "alignment_status", "") or getattr(second, "alignment_status", "") or ""),
        profile_status=str(getattr(first, "profile_status", "") or getattr(second, "profile_status", "") or ""),
        active_alignment_element_id=str(getattr(first, "active_alignment_element_id", "") or ""),
        active_profile_segment_start_id=str(getattr(first, "active_profile_segment_start_id", "") or ""),
        active_profile_segment_end_id=str(getattr(second, "active_profile_segment_end_id", "") or ""),
        active_vertical_curve_id=str(getattr(first, "active_vertical_curve_id", "") or getattr(second, "active_vertical_curve_id", "") or ""),
        notes="supplemental_sampling",
    )


def _interpolate_applied_section_points(first, second, ratio: float) -> list[AppliedSectionPoint]:
    first_points = list(getattr(first, "point_rows", []) or [])
    second_points = list(getattr(second, "point_rows", []) or [])
    t = min(max(float(ratio), 0.0), 1.0)
    if len(first_points) != len(second_points):
        return _interpolate_stable_applied_section_points(first, second, t)
    output: list[AppliedSectionPoint] = []
    for index, first_point in enumerate(first_points):
        second_point = second_points[index]
        first_role = str(getattr(first_point, "point_role", "") or "")
        second_role = str(getattr(second_point, "point_role", "") or "")
        if first_role != second_role:
            return _interpolate_stable_applied_section_points(first, second, t)
        output.append(
            AppliedSectionPoint(
                point_id=f"{getattr(first_point, 'point_id', '')}->{getattr(second_point, 'point_id', '')}@{t:.6g}",
                x=_lerp(getattr(first_point, "x", 0.0), getattr(second_point, "x", 0.0), t),
                y=_lerp(getattr(first_point, "y", 0.0), getattr(second_point, "y", 0.0), t),
                z=_lerp(getattr(first_point, "z", 0.0), getattr(second_point, "z", 0.0), t),
                point_role=first_role,
                lateral_offset=_lerp(getattr(first_point, "lateral_offset", 0.0), getattr(second_point, "lateral_offset", 0.0), t),
            )
        )
    return output


def _interpolate_stable_applied_section_points(first, second, ratio: float) -> list[AppliedSectionPoint]:
    output: list[AppliedSectionPoint] = []
    t = min(max(float(ratio), 0.0), 1.0)
    for role in ("fg_surface", "subgrade_surface", "ditch_surface"):
        output.extend(_interpolate_matching_role_points(first, second, role=role, ratio=t))
    output.extend(_interpolate_side_slope_applied_section_points(first, second, t))
    return output


def _interpolate_matching_role_points(first, second, *, role: str, ratio: float) -> list[AppliedSectionPoint]:
    first_rows = _role_points_for_interpolation(first, role=role)
    second_rows = _role_points_for_interpolation(second, role=role)
    if not first_rows or not second_rows or len(first_rows) != len(second_rows):
        return []
    t = min(max(float(ratio), 0.0), 1.0)
    output: list[AppliedSectionPoint] = []
    for index, first_point in enumerate(first_rows):
        second_point = second_rows[index]
        output.append(
            AppliedSectionPoint(
                point_id=f"supplemental:{role}:{index}:{getattr(first_point, 'point_id', '')}->{getattr(second_point, 'point_id', '')}@{t:.6g}",
                x=_lerp(getattr(first_point, "x", 0.0), getattr(second_point, "x", 0.0), t),
                y=_lerp(getattr(first_point, "y", 0.0), getattr(second_point, "y", 0.0), t),
                z=_lerp(getattr(first_point, "z", 0.0), getattr(second_point, "z", 0.0), t),
                point_role=role,
                lateral_offset=_lerp(getattr(first_point, "lateral_offset", 0.0), getattr(second_point, "lateral_offset", 0.0), t),
            )
        )
    return output


def _role_points_for_interpolation(section, *, role: str) -> list[object]:
    rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == role
    ]
    rows.sort(key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
    return rows


def _interpolate_side_slope_applied_section_points(first, second, ratio: float) -> list[AppliedSectionPoint]:
    output: list[AppliedSectionPoint] = []
    t = min(max(float(ratio), 0.0), 1.0)
    for side_label in ("left", "right"):
        first_row = _side_slope_source_row_for_interpolation(first, side_label=side_label)
        second_row = _side_slope_source_row_for_interpolation(second, side_label=side_label)
        if not first_row or not second_row:
            continue
        if len(first_row) == 1 and len(second_row) == 1:
            harmonized_first, harmonized_second = first_row, second_row
        else:
            harmonized_first, harmonized_second = _harmonized_side_slope_pair_rows(first_row, second_row)
        point_count = min(len(harmonized_first), len(harmonized_second))
        for index in range(point_count):
            first_point = harmonized_first[index]
            second_point = harmonized_second[index]
            role = _interpolated_applied_side_slope_role(first_point, second_point)
            output.append(
                AppliedSectionPoint(
                    point_id=f"supplemental:{side_label}:{index}:{first_point.point_id}->{second_point.point_id}@{t:.6g}",
                    x=_lerp(first_point.x, second_point.x, t),
                    y=_lerp(first_point.y, second_point.y, t),
                    z=_lerp(first_point.z, second_point.z, t),
                    point_role=role,
                    lateral_offset=_lerp(first_point.lateral_offset, second_point.lateral_offset, t),
                )
            )
    return output


def _side_slope_source_row_for_interpolation(section, *, side_label: str) -> list[_SectionPointLite]:
    rows: list[_SectionPointLite] = []
    side = str(side_label or "").strip().lower()
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"side_slope_surface", "bench_surface", "daylight_marker"}:
            continue
        point_id = str(getattr(point, "point_id", "") or "").lower()
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        id_matches_side = f":{side}" in point_id or point_id.startswith(f"{side}:") or point_id.endswith(f":{side}")
        offset_matches_side = (side == "left" and offset >= -1.0e-9) or (side == "right" and offset <= 1.0e-9)
        if not id_matches_side and not offset_matches_side:
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
    if side == "left":
        rows.sort(key=lambda point: float(point.lateral_offset))
    else:
        rows.sort(key=lambda point: -float(point.lateral_offset))
    return _unique_side_slope_points(rows)


def _interpolated_applied_side_slope_role(first: _SectionPointLite, second: _SectionPointLite) -> str:
    first_role = str(getattr(first, "point_role", "") or "")
    second_role = str(getattr(second, "point_role", "") or "")
    if first_role == second_role:
        return first_role
    if "daylight_marker" in {first_role, second_role}:
        return "daylight_marker"
    if "bench_surface" in {first_role, second_role}:
        return "bench_surface"
    return "side_slope_surface"


def _lerp(first, second, ratio: float) -> float:
    return float(first or 0.0) + (float(second or 0.0) - float(first or 0.0)) * float(ratio)


def _interpolate_angle_degrees(first: float, second: float, ratio: float) -> float:
    delta = (float(second) - float(first) + 180.0) % 360.0 - 180.0
    return float(first) + delta * float(ratio)


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
    return _surface_width_rows_for_sections(_section_rows(applied_section_set), fallback_half_width=fallback_half_width)


def _surface_width_rows_for_sections(sections: list[object], *, fallback_half_width: float) -> list[tuple[float, float]]:
    widths: list[tuple[float, float]] = []
    for section in list(sections or []):
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
    return _daylight_inner_edge_rows_for_sections(_section_rows(applied_section_set), fallback_half_width=fallback_half_width)


def _daylight_inner_edge_rows_for_sections(
    sections: list[object],
    *,
    fallback_half_width: float,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Return left/right slope-face start offsets and elevations.

    The slope face starts at the outermost built section edge. Ditch/drainage
    points are separate from FG, but they are still part of the Assembly
    terminal geometry and must move the slope-face start outward.
    """

    rows: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for section in list(sections or []):
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
    return _daylight_rows_for_sections(_section_rows(applied_section_set))


def _daylight_rows_for_sections(sections: list[object]) -> list[tuple[float, float, float, float]]:
    rows: list[tuple[float, float, float, float]] = []
    for section in list(sections or []):
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

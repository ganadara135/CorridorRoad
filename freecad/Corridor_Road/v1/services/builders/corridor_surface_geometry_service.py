"""Corridor surface geometry builder service for CorridorRoad v1."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex
from ..evaluation.tin_sampling_service import TinSamplingService


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
        width_rows = _surface_width_rows(request.applied_section_set, fallback_half_width=fallback_half_width)
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
            left_width, right_width = width_rows[index]
            left_daylight_width, right_daylight_width, left_slope, right_slope = daylight_rows[index]
            if left_daylight_width > 0.0:
                inner_x = x + nx * left_width
                inner_y = y + ny * left_width
                outer = _resolve_slope_face_outer_point(
                    sampling_service=sampling_service,
                    surface=request.existing_ground_surface,
                    edge_x=inner_x,
                    edge_y=inner_y,
                    edge_z=z,
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
                        TINVertex(f"v{index}:left:inner", inner_x, inner_y, z),
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
                inner_x = x - nx * right_width
                inner_y = y - ny * right_width
                outer = _resolve_slope_face_outer_point(
                    sampling_service=sampling_service,
                    surface=request.existing_ground_surface,
                    edge_x=inner_x,
                    edge_y=inner_y,
                    edge_z=z,
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
                        TINVertex(f"v{index}:right:inner", inner_x, inner_y, z),
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

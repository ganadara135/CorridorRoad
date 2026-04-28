"""Corridor surface geometry builder service for CorridorRoad v1."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex


@dataclass(frozen=True)
class CorridorDesignSurfaceGeometryRequest:
    """Input bundle for a minimal corridor surface ribbon."""

    project_id: str
    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    surface_id: str
    fallback_half_width: float = 6.0


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
        )

    def build_subgrade_surface(self, request: CorridorDesignSurfaceGeometryRequest) -> TINSurface:
        """Build a simple subgrade-surface ribbon below the design surface."""

        return self._build_surface_ribbon(
            request,
            surface_kind="subgrade_surface",
            label_prefix="Subgrade Surface",
            z_offset_resolver=lambda section: -max(float(getattr(section, "subgrade_depth", 0.0) or 0.0), 0.0),
            triangle_kind="corridor_subgrade_strip",
        )

    def _build_surface_ribbon(
        self,
        request: CorridorDesignSurfaceGeometryRequest,
        *,
        surface_kind: str,
        label_prefix: str,
        z_offset_resolver,
        triangle_kind: str,
    ) -> TINSurface:
        """Build a two-edge ribbon from applied-section frames."""

        frame_rows = _frame_rows(request.applied_section_set)
        if len(frame_rows) < 2:
            raise ValueError("At least two applied-section frames are required to build a corridor surface.")

        fallback_half_width = max(float(request.fallback_half_width or 0.0), 0.1)
        vertices: list[TINVertex] = []
        triangles: list[TINTriangle] = []
        sections = _section_rows(request.applied_section_set)
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

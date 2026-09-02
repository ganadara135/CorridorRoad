"""Evaluate final Intersection patch triangle and boundary-shape quality."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.intersection_patch_shape_quality import (
    IntersectionPatchShapeQualityResult,
)
from ..geometry import xy_triangle_quality_ratio


@dataclass(frozen=True)
class IntersectionPatchShapeQualityRequest:
    vertices: tuple[object, ...]
    triangles: tuple[object, ...]
    skinny_threshold: float = 0.08


class IntersectionPatchShapeQualityService:
    """Classify triangulation mode and calculate normalized quality metrics."""

    def evaluate(
        self,
        request: IntersectionPatchShapeQualityRequest,
    ) -> IntersectionPatchShapeQualityResult:
        vertices = tuple(request.vertices or ())
        triangles = tuple(request.triangles or ())
        vertex_map = {
            str(getattr(vertex, "vertex_id", "") or ""): vertex
            for vertex in vertices
            if str(getattr(vertex, "vertex_id", "") or "")
        }
        xs = [float(getattr(vertex, "x", 0.0) or 0.0) for vertex in vertices]
        ys = [float(getattr(vertex, "y", 0.0) or 0.0) for vertex in vertices]
        bbox_x = (max(xs) - min(xs)) if xs else 0.0
        bbox_y = (max(ys) - min(ys)) if ys else 0.0
        min_axis = min(abs(bbox_x), abs(bbox_y))
        max_axis = max(abs(bbox_x), abs(bbox_y))
        aspect_ratio = (
            max_axis / min_axis if min_axis > 1.0e-9 else 0.0
        )
        quality_values = []
        fan_fallback = False
        structured_strip = False
        curb_return_arc = False
        curb_return_blend = False
        missing_vertex_count = 0
        for triangle in triangles:
            quality_ref = str(getattr(triangle, "quality_ref", "") or "")
            if "fan" in quality_ref:
                fan_fallback = True
            if "structured_strip" in quality_ref:
                structured_strip = True
            if "curb_return" in quality_ref:
                curb_return_arc = True
            if "curb_return_blend" in quality_ref:
                curb_return_blend = True
            triangle_vertices = [
                vertex_map.get(str(getattr(triangle, attr, "") or ""))
                for attr in ("v1", "v2", "v3")
            ]
            if any(vertex is None for vertex in triangle_vertices):
                missing_vertex_count += 1
                continue
            quality_values.append(
                xy_triangle_quality_ratio(
                    triangle_vertices[0],
                    triangle_vertices[1],
                    triangle_vertices[2],
                )
            )
        minimum_quality = min(quality_values) if quality_values else 0.0
        threshold = float(request.skinny_threshold)
        skinny_count = len(
            [quality for quality in quality_values if quality < threshold]
        )
        if structured_strip and curb_return_blend:
            triangulation_mode = "structured_strip_curb_return_blend"
        elif structured_strip and curb_return_arc:
            triangulation_mode = "structured_strip_curb_return"
        elif structured_strip:
            triangulation_mode = "structured_strip"
        elif fan_fallback:
            triangulation_mode = "fan_fallback"
        else:
            triangulation_mode = "ear_clip"
        diagnostics = (
            (f"intersection_patch_quality_missing_vertices:{missing_vertex_count}",)
            if missing_vertex_count
            else ()
        )
        return IntersectionPatchShapeQualityResult(
            status="ready",
            triangulation_mode=triangulation_mode,
            bbox_x=bbox_x,
            bbox_y=bbox_y,
            bbox_aspect_ratio=aspect_ratio,
            triangle_min_quality=minimum_quality,
            skinny_triangle_count=skinny_count,
            evaluated_triangle_count=len(quality_values),
            missing_vertex_triangle_count=missing_vertex_count,
            skinny_threshold=threshold,
            diagnostic_rows=diagnostics,
        )

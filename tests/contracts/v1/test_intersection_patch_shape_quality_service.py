from __future__ import annotations

import pytest

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result import (
    IntersectionPatchShapeQualityResult,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import (
    TINTriangle,
    TINVertex,
)
from freecad.Corridor_Road.v1.services.evaluation import (
    IntersectionPatchShapeQualityRequest,
    IntersectionPatchShapeQualityService,
)


def _vertices():
    return (
        TINVertex("v1", 0.0, 0.0, 0.0),
        TINVertex("v2", 4.0, 0.0, 0.0),
        TINVertex("v3", 0.0, 2.0, 0.0),
    )


def _triangle(triangle_id: str, quality_ref: str):
    return TINTriangle(
        triangle_id,
        "v1",
        "v2",
        "v3",
        quality_ref=quality_ref,
    )


@pytest.mark.parametrize(
    ("quality_refs", "expected_mode"),
    [
        (("ordered_polygon",), "ear_clip"),
        (("ordered_fan_fallback",), "fan_fallback"),
        (("structured_strip",), "structured_strip"),
        (("structured_strip", "curb_return_core"), "structured_strip_curb_return"),
        (
            ("structured_strip", "curb_return_blend"),
            "structured_strip_curb_return_blend",
        ),
    ],
)
def test_quality_classifies_existing_triangulation_modes(
    quality_refs,
    expected_mode,
) -> None:
    triangles = tuple(
        _triangle(f"t{index}", quality_ref)
        for index, quality_ref in enumerate(quality_refs, start=1)
    )

    result = IntersectionPatchShapeQualityService().evaluate(
        IntersectionPatchShapeQualityRequest(
            vertices=_vertices(),
            triangles=triangles,
        )
    )

    assert isinstance(result, IntersectionPatchShapeQualityResult)
    assert result.status == "ready"
    assert result.triangulation_mode == expected_mode
    assert result.evaluated_triangle_count == len(triangles)


def test_quality_preserves_bbox_aspect_and_normalized_triangle_quality() -> None:
    result = IntersectionPatchShapeQualityService().evaluate(
        IntersectionPatchShapeQualityRequest(
            vertices=_vertices(),
            triangles=(_triangle("t1", "ordered_polygon"),),
        )
    )

    assert result.bbox_x == 4.0
    assert result.bbox_y == 2.0
    assert result.bbox_aspect_ratio == 2.0
    assert result.triangle_min_quality == pytest.approx(0.6928203230275509)
    assert result.skinny_triangle_count == 0
    assert result.skinny_threshold == 0.08


def test_quality_counts_skinny_triangles_with_strict_threshold() -> None:
    vertices = (
        TINVertex("v1", 0.0, 0.0, 0.0),
        TINVertex("v2", 100.0, 0.0, 0.0),
        TINVertex("v3", 50.0, 0.01, 0.0),
    )
    triangle = _triangle("t1", "ordered_polygon")
    default = IntersectionPatchShapeQualityService().evaluate(
        IntersectionPatchShapeQualityRequest(vertices=vertices, triangles=(triangle,))
    )
    zero_threshold = IntersectionPatchShapeQualityService().evaluate(
        IntersectionPatchShapeQualityRequest(
            vertices=vertices,
            triangles=(triangle,),
            skinny_threshold=0.0,
        )
    )

    assert 0.0 < default.triangle_min_quality < 0.08
    assert default.skinny_triangle_count == 1
    assert zero_threshold.skinny_triangle_count == 0


def test_quality_skips_missing_triangle_vertices_but_preserves_mode() -> None:
    result = IntersectionPatchShapeQualityService().evaluate(
        IntersectionPatchShapeQualityRequest(
            vertices=_vertices()[:2],
            triangles=(_triangle("t1", "ordered_fan_fallback"),),
        )
    )

    assert result.triangulation_mode == "fan_fallback"
    assert result.triangle_min_quality == 0.0
    assert result.evaluated_triangle_count == 0
    assert result.missing_vertex_triangle_count == 1
    assert result.diagnostic_rows == (
        "intersection_patch_quality_missing_vertices:1",
    )


def test_quality_empty_and_command_compatibility_mapping() -> None:
    result = IntersectionPatchShapeQualityService().evaluate(
        IntersectionPatchShapeQualityRequest(vertices=(), triangles=())
    )
    legacy = cmd_build_corridor._intersection_patch_shape_quality([], [])

    assert result.triangulation_mode == "ear_clip"
    assert result.bbox_x == 0.0
    assert result.bbox_y == 0.0
    assert result.bbox_aspect_ratio == 0.0
    assert result.triangle_min_quality == 0.0
    assert result.skinny_triangle_count == 0
    assert legacy == {
        "triangulation_mode": result.triangulation_mode,
        "bbox_x": result.bbox_x,
        "bbox_y": result.bbox_y,
        "bbox_aspect_ratio": result.bbox_aspect_ratio,
        "triangle_min_quality": result.triangle_min_quality,
        "skinny_triangle_count": result.skinny_triangle_count,
    }

from __future__ import annotations

from types import SimpleNamespace

import pytest

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result import (
    IntersectionSurfacePatchBuildResult,
)
from freecad.Corridor_Road.v1.services.builders import (
    IntersectionSurfacePatchBuildRequest,
    IntersectionSurfacePatchBuildService,
)


def _request() -> IntersectionSurfacePatchBuildRequest:
    return IntersectionSurfacePatchBuildRequest(
        project_id="project:test",
        corridor_model=SimpleNamespace(corridor_id="corridor:test"),
        applied_section_set=SimpleNamespace(applied_section_set_id="sections:test"),
        prerequisite=SimpleNamespace(intersection_id="intersection:test"),
        intersection_model=SimpleNamespace(intersection_model_id="intersections:test"),
        surface_id="surface:intersection",
    )


def _surface(boundary_source: str = "ordered_patch_boundary"):
    return SimpleNamespace(
        vertex_rows=[SimpleNamespace(vertex_id="v1"), SimpleNamespace(vertex_id="v2")],
        triangle_rows=[SimpleNamespace(triangle_id="t1")],
        quality_rows=[
            SimpleNamespace(kind="patch_boundary_source", value=boundary_source),
            SimpleNamespace(kind="patch_triangulation_mode", value="ear_clip"),
        ],
    )


def test_intersection_patch_service_forwards_typed_request_exactly() -> None:
    request = _request()
    calls: list[dict[str, object]] = []

    def builder(**kwargs):
        calls.append(kwargs)
        return _surface()

    result = IntersectionSurfacePatchBuildService(builder).build(request)

    assert isinstance(result, IntersectionSurfacePatchBuildResult)
    assert result.status == "ready"
    assert result.surface_id == "surface:intersection"
    assert result.intersection_id == "intersection:test"
    assert result.boundary_source == "ordered_patch_boundary"
    assert result.triangulation_mode == "ear_clip"
    assert result.vertex_count == 2
    assert result.triangle_count == 1
    assert result.quality_row_count == 2
    assert result.fallback_used is False
    assert result.diagnostic_rows == ()
    assert calls == [
        {
            "project_id": request.project_id,
            "corridor_model": request.corridor_model,
            "applied_section_set": request.applied_section_set,
            "prerequisite": request.prerequisite,
            "intersection_model": request.intersection_model,
            "surface_id": request.surface_id,
        }
    ]


def test_intersection_patch_service_reports_convex_hull_fallback() -> None:
    result = IntersectionSurfacePatchBuildService(
        lambda **_kwargs: _surface("convex_hull_fallback")
    ).build(_request())

    assert result.status == "ready"
    assert result.fallback_used is True
    assert result.diagnostic_rows == (
        "intersection_patch_boundary_fallback:convex_hull_fallback",
    )


def test_intersection_patch_service_returns_typed_failure() -> None:
    def builder(**_kwargs):
        raise ValueError("patch failed")

    result = IntersectionSurfacePatchBuildService(builder).build(_request())

    assert result.status == "error"
    assert result.tin_surface is None
    assert result.error_message == "patch failed"
    assert result.diagnostic_rows == (
        "intersection_surface_patch_build_failed:ValueError:patch failed",
    )


def test_intersection_patch_service_reports_missing_builder() -> None:
    result = IntersectionSurfacePatchBuildService().build(_request())

    assert result.status == "unsupported"
    assert result.error_message == (
        "Intersection surface patch TIN builder is not configured."
    )
    assert result.diagnostic_rows == (
        "intersection_surface_patch_builder_missing",
    )


def test_command_result_adapter_preserves_ready_surface_and_failure_message() -> None:
    surface = _surface()
    ready = IntersectionSurfacePatchBuildResult(
        status="ready",
        surface_id="surface:intersection",
        intersection_id="intersection:test",
        tin_surface=surface,
    )
    failed = IntersectionSurfacePatchBuildResult(
        status="error",
        surface_id="surface:intersection",
        intersection_id="intersection:test",
        error_message="original patch failure",
    )

    assert cmd_build_corridor._tin_surface_from_intersection_patch_build_result(
        ready
    ) is surface
    with pytest.raises(RuntimeError, match="^original patch failure$"):
        cmd_build_corridor._tin_surface_from_intersection_patch_build_result(failed)

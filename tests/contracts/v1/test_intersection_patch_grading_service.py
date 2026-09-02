from __future__ import annotations

from types import SimpleNamespace

import pytest

from freecad.Corridor_Road.v1.models.result import IntersectionPatchGradingResult
from freecad.Corridor_Road.v1.models.result.tin_surface import TINVertex
from freecad.Corridor_Road.v1.services.evaluation import (
    IntersectionPatchGradingRequest,
    IntersectionPatchGradingService,
)


def _vertex(vertex_id: str, x: float, y: float, z: float, alignment: str):
    return TINVertex(
        vertex_id=vertex_id,
        x=x,
        y=y,
        z=z,
        notes=f"alignment={alignment}",
    )


def test_grading_selects_first_active_matching_policy() -> None:
    disabled = SimpleNamespace(
        policy_id="grading:disabled",
        intersection_id="intersection:test",
        status="disabled",
        mode="flatten_intersection",
    )
    active = SimpleNamespace(
        policy_id="grading:active",
        intersection_id="intersection:test",
        status="active",
        mode="keep_primary_crown",
    )
    model = SimpleNamespace(grading_policy_rows=[disabled, active])

    selected = IntersectionPatchGradingService().select_policy(
        model,
        "intersection:test",
    )

    assert selected is active


def test_grading_defaults_unknown_mode_to_normal_superelevation() -> None:
    vertices = (_vertex("v1", 0, 0, 10, "primary"),)
    policy = SimpleNamespace(
        intersection_id="intersection:test",
        status="active",
        mode="unknown",
    )
    model = SimpleNamespace(grading_policy_rows=[policy])

    result = IntersectionPatchGradingService().evaluate(
        IntersectionPatchGradingRequest(
            vertices=vertices,
            intersection_model=model,
            intersection_id="intersection:test",
        )
    )

    assert isinstance(result, IntersectionPatchGradingResult)
    assert result.grading_mode == "use_normal_superelevation"
    assert result.vertex_rows == vertices
    assert result.max_z_delta == 0.0


def test_flatten_grading_uses_mean_z_and_records_max_delta() -> None:
    vertices = (
        _vertex("v1", 0, 0, 10, "primary"),
        _vertex("v2", 5, 0, 12, "primary"),
        _vertex("v3", 0, 5, 14, "side"),
    )
    policy = SimpleNamespace(
        intersection_id="intersection:test",
        status="active",
        mode="flatten_intersection",
    )

    result = IntersectionPatchGradingService().evaluate(
        IntersectionPatchGradingRequest(
            vertices=vertices,
            intersection_model=SimpleNamespace(grading_policy_rows=[policy]),
            intersection_id="intersection:test",
        )
    )

    assert [vertex.z for vertex in result.vertex_rows] == [12.0, 12.0, 12.0]
    assert result.max_z_delta == 2.0
    assert all(
        "intersection_grading=flatten_intersection" in vertex.notes
        for vertex in result.vertex_rows
    )


def test_blend_grading_fits_plane_and_preserves_plane_note() -> None:
    vertices = (
        _vertex("v1", 0, 0, 1, "primary"),
        _vertex("v2", 1, 0, 2, "primary"),
        _vertex("v3", 0, 1, 2, "side"),
        _vertex("v4", 1, 1, 3, "side"),
    )
    policy = SimpleNamespace(
        intersection_id="intersection:test",
        status="active",
        mode="blend_primary_side",
        primary_alignment_ref="primary",
    )

    result = IntersectionPatchGradingService().evaluate(
        IntersectionPatchGradingRequest(
            vertices=vertices,
            intersection_model=SimpleNamespace(grading_policy_rows=[policy]),
            intersection_id="intersection:test",
        )
    )

    assert result.grading_plane == pytest.approx((1.0, 1.0, 1.0))
    assert [vertex.z for vertex in result.vertex_rows] == pytest.approx(
        [1.0, 2.0, 2.0, 3.0]
    )
    assert all(
        "blend_basis=primary_side_plane" in vertex.notes
        for vertex in result.vertex_rows
    )


def test_blend_grading_falls_back_to_primary_mean_when_plane_is_singular() -> None:
    vertices = (
        _vertex("v1", 0, 0, 10, "primary"),
        _vertex("v2", 1, 0, 14, "primary"),
        _vertex("v3", 2, 0, 20, "side"),
    )
    policy = SimpleNamespace(
        intersection_id="intersection:test",
        status="active",
        mode="blend_primary_side",
        primary_alignment_ref="primary",
    )

    result = IntersectionPatchGradingService().evaluate(
        IntersectionPatchGradingRequest(
            vertices=vertices,
            intersection_model=SimpleNamespace(grading_policy_rows=[policy]),
            intersection_id="intersection:test",
        )
    )

    assert result.grading_plane is None
    assert [vertex.z for vertex in result.vertex_rows] == [10, 14, 16.0]
    assert result.max_z_delta == 4.0
    assert result.diagnostic_rows == (
        "intersection_grading_blend_primary_fallback",
    )
    assert "blend_basis=primary_preserved" in result.vertex_rows[0].notes
    assert "blend_basis=primary_side_half" in result.vertex_rows[2].notes

from __future__ import annotations

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result import (
    IntersectionPatchDrainageReviewResult,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import TINVertex
from freecad.Corridor_Road.v1.services.evaluation import (
    IntersectionPatchDrainageReviewRequest,
    IntersectionPatchDrainageReviewService,
)


def _vertex(vertex_id: str, x: float, y: float, z: float):
    return TINVertex(
        vertex_id,
        x,
        y,
        z,
        source_point_ref=f"source:{vertex_id}",
    )


def test_drainage_review_preserves_empty_contract_and_result_scope() -> None:
    result = IntersectionPatchDrainageReviewService().evaluate(
        IntersectionPatchDrainageReviewRequest(
            boundary_vertices=(),
            all_vertices=(),
        )
    )

    assert isinstance(result, IntersectionPatchDrainageReviewResult)
    assert result.status == "empty"
    assert result.source_scope == "result_only_review_hint"
    assert result.low_point_tolerance == 0.001
    assert result.low_point_candidate_count == 0
    assert result.low_point_x == 0.0
    assert result.low_point_y == 0.0
    assert result.low_point_z == 0.0
    assert result.low_point_source_ref == ""
    assert result.flow_hint_count == 0
    assert result.flow_hint_summary == "no intersection patch vertices"
    assert result.diagnostic_rows == (
        "intersection_patch_drainage_review_no_vertices",
    )


def test_drainage_review_selects_first_low_candidate_with_tolerance() -> None:
    first = _vertex("low:first", 1.0, 2.0, 10.0)
    second = _vertex("low:second", 3.0, 4.0, 10.0005)

    result = IntersectionPatchDrainageReviewService().evaluate(
        IntersectionPatchDrainageReviewRequest(
            boundary_vertices=(first, second),
            all_vertices=(first, second, _vertex("high", 5.0, 6.0, 12.0)),
        )
    )

    assert result.status == "ready"
    assert result.low_point_candidate_count == 2
    assert result.low_point_x == 1.0
    assert result.low_point_y == 2.0
    assert result.low_point_z == 10.0
    assert result.low_point_source_ref == "source:low:first"


def test_drainage_review_uses_strict_elevated_boundary_filter_and_average_vector() -> None:
    low = _vertex("low", 1.0, 1.0, 10.0)
    at_tolerance = _vertex("at:tolerance", 0.0, 0.0, 10.001)
    high_first = _vertex("high:1", 3.0, 5.0, 11.0)
    high_second = _vertex("high:2", 5.0, 1.0, 12.0)

    result = IntersectionPatchDrainageReviewService().evaluate(
        IntersectionPatchDrainageReviewRequest(
            boundary_vertices=(at_tolerance, high_first, high_second),
            all_vertices=(low, at_tolerance, high_first, high_second),
        )
    )

    assert result.flow_hint_count == 2
    assert result.average_flow_dx == -3.0
    assert result.average_flow_dy == -2.0
    assert result.flow_hint_summary == (
        "boundary_to_low count=2; avg_vector=(-3.000,-2.000)"
    )


def test_drainage_review_flat_summary_and_none_filtering() -> None:
    low = _vertex("low", 0.0, 0.0, 5.0)
    near_low = _vertex("near", 2.0, 2.0, 5.0009)

    result = IntersectionPatchDrainageReviewService().evaluate(
        IntersectionPatchDrainageReviewRequest(
            boundary_vertices=(None, low, near_low),
            all_vertices=(None, low, near_low),
        )
    )

    assert result.low_point_candidate_count == 2
    assert result.flow_hint_count == 0
    assert result.average_flow_dx == 0.0
    assert result.average_flow_dy == 0.0
    assert result.flow_hint_summary == (
        "boundary_to_low count=0; patch appears flat at low-point tolerance"
    )


def test_drainage_review_custom_tolerance_is_explicit_and_nonnegative() -> None:
    low = _vertex("low", 0.0, 0.0, 5.0)
    near = _vertex("near", 1.0, 0.0, 5.4)

    wide = IntersectionPatchDrainageReviewService().evaluate(
        IntersectionPatchDrainageReviewRequest(
            boundary_vertices=(near,),
            all_vertices=(low, near),
            low_point_tolerance=0.5,
        )
    )
    clamped = IntersectionPatchDrainageReviewService().evaluate(
        IntersectionPatchDrainageReviewRequest(
            boundary_vertices=(near,),
            all_vertices=(low, near),
            low_point_tolerance=-1.0,
        )
    )

    assert wide.low_point_tolerance == 0.5
    assert wide.low_point_candidate_count == 2
    assert wide.flow_hint_count == 0
    assert clamped.low_point_tolerance == 0.0
    assert clamped.low_point_candidate_count == 1
    assert clamped.flow_hint_count == 1


def test_drainage_review_command_compatibility_mapping() -> None:
    low = _vertex("low", 0.0, 0.0, 5.0)
    high = _vertex("high", 2.0, 0.0, 6.0)
    typed = IntersectionPatchDrainageReviewService().evaluate(
        IntersectionPatchDrainageReviewRequest(
            boundary_vertices=(high,),
            all_vertices=(low, high),
        )
    )
    legacy = cmd_build_corridor._intersection_patch_drainage_hint(
        [high],
        [low, high],
    )

    assert legacy == {
        "low_point_candidate_count": typed.low_point_candidate_count,
        "low_point_x": typed.low_point_x,
        "low_point_y": typed.low_point_y,
        "low_point_z": typed.low_point_z,
        "low_point_source_ref": typed.low_point_source_ref,
        "flow_hint_count": typed.flow_hint_count,
        "flow_hint_summary": typed.flow_hint_summary,
    }

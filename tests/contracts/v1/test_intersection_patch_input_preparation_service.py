from __future__ import annotations

from types import SimpleNamespace

from freecad.Corridor_Road.v1.models.result import (
    IntersectionPatchInputPreparationResult,
    IntersectionPatchSuperelevationContext,
)
from freecad.Corridor_Road.v1.services.builders import (
    IntersectionPatchInputPreparationRequest,
    IntersectionPatchInputPreparationService,
)


def _point(
    x: float,
    y: float,
    z: float,
    role: str = "fg_surface",
):
    return SimpleNamespace(x=x, y=y, z=z, point_role=role)


def _section(
    section_id: str,
    alignment_id: str,
    station: float,
    points: list[object],
    *,
    region_id: str = "region:intersection",
    intersection_id: str = "intersection:test",
    source_id: str = "superelevation:test",
    transition_id: str = "transition:test",
    left: float = -2.0,
    right: float = 2.0,
):
    return SimpleNamespace(
        applied_section_id=section_id,
        alignment_id=alignment_id,
        station=station,
        region_id=region_id,
        active_intersection_id=intersection_id,
        active_superelevation_id=source_id,
        active_superelevation_transition_id=transition_id,
        superelevation_left_crossfall=left,
        superelevation_right_crossfall=right,
        point_rows=points,
    )


def _request(sections: list[object], intersection_model=None):
    station_rows = [
        SimpleNamespace(
            applied_section_id=section.applied_section_id,
            station=section.station,
        )
        for section in reversed(sections)
    ]
    return IntersectionPatchInputPreparationRequest(
        applied_section_set=SimpleNamespace(
            sections=sections,
            station_rows=station_rows,
        ),
        prerequisite=SimpleNamespace(
            intersection_id="intersection:test",
            control_region_refs=("region:intersection",),
        ),
        intersection_model=intersection_model,
    )


def test_preparation_selects_nearest_center_section_per_alignment() -> None:
    sections = [
        _section("primary:90", "alignment:primary", 90.0, [_point(0, 0, 10)]),
        _section(
            "primary:100",
            "alignment:primary",
            100.0,
            [_point(0, 0, 0, "other"), _point(0, 1, 11), _point(0, -1, 11)],
            left=-3.0,
            right=3.0,
        ),
        _section("side:190", "alignment:side", 190.0, [_point(4, 0, 12)]),
        _section(
            "side:200",
            "alignment:side",
            200.0,
            [_point(5, 1, 13), _point(5, -1, 13)],
            left=-2.0,
            right=4.0,
        ),
    ]
    model = SimpleNamespace(
        intersection_rows=[
            SimpleNamespace(
                intersection_id="intersection:test",
                primary_alignment_ref="alignment:primary",
                primary_station=100.0,
                secondary_station_refs={"alignment:side": 200.0},
            )
        ],
        control_area_rows=[],
    )

    result = IntersectionPatchInputPreparationService().prepare(
        _request(sections, model)
    )

    assert isinstance(result, IntersectionPatchInputPreparationResult)
    assert result.status == "ready"
    assert [row.applied_section_id for row in result.section_rows] == [
        "primary:100",
        "side:200",
    ]
    assert len(result.vertex_rows) == 4
    assert result.vertex_rows[0].source_point_ref == "primary:100:fg:2"
    assert "alignment=alignment:primary; station=100.000" in result.vertex_rows[0].notes
    assert result.control_region_refs == ("region:intersection",)


def test_preparation_deduplicates_six_decimal_xy_and_keeps_first_source() -> None:
    section = _section(
        "section:1",
        "alignment:primary",
        100.0,
        [
            _point(0.0000001, 0.0, 10.0),
            _point(0.0000004, 0.0, 99.0),
            _point(5.0, 0.0, 11.0),
            _point(0.0, 5.0, 12.0),
        ],
    )

    result = IntersectionPatchInputPreparationService().prepare(_request([section]))

    assert result.status == "ready"
    assert result.duplicate_xy_count == 1
    assert len(result.vertex_rows) == 3
    assert result.vertex_rows[0].z == 10.0
    assert result.vertex_rows[0].source_point_ref == "section:1:fg:1"


def test_preparation_returns_typed_superelevation_context() -> None:
    sections = [
        _section(
            "section:1",
            "alignment:primary",
            100.0,
            [_point(0, 0, 10), _point(5, 0, 11), _point(0, 5, 12)],
            left=-3.0,
            right=4.0,
        )
    ]

    result = IntersectionPatchInputPreparationService().prepare(_request(sections))
    context = result.superelevation_context

    assert isinstance(context, IntersectionPatchSuperelevationContext)
    assert context.source_count == 1
    assert context.transition_count == 1
    assert context.left_min == -3.0
    assert context.left_max == -3.0
    assert context.right_min == 4.0
    assert context.right_max == 4.0
    assert context.summary == (
        "sources=1; transitions=1; L -3.000%..-3.000%; R 4.000%..4.000%"
    )


def test_preparation_preserves_too_few_fg_points_error_contract() -> None:
    section = _section(
        "section:1",
        "alignment:primary",
        100.0,
        [_point(0, 0, 10), _point(5, 0, 11)],
    )

    result = IntersectionPatchInputPreparationService().prepare(_request([section]))

    assert result.status == "error"
    assert len(result.vertex_rows) == 2
    assert result.error_message == (
        "intersection_patch_boundary_too_few_points: at least three unique "
        "fg_surface points are required."
    )
    assert result.diagnostic_rows == (
        "intersection_patch_boundary_too_few_points",
    )

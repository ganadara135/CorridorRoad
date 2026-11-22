"""A station on the Alignment but outside the Profile keeps its plan frame and says it is a fallback."""

import math

import pytest

from freecad.Corridor_Road.v1.models.result.centerline3d import Centerline3DPointRow, Centerline3DResult
from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentElement, AlignmentModel
from freecad.Corridor_Road.v1.models.source.profile_model import ProfileControlPoint, ProfileModel
from freecad.Corridor_Road.v1.services.builders.applied_section_service import AppliedSectionService
from freecad.Corridor_Road.v1.services.evaluation.centerline3d_frame_service import Centerline3DFrameService
from freecad.Corridor_Road.v1.services.evaluation.profile_evaluation_service import ProfileEvaluationService

# 100 m due east, then a 100 m quarter circle that ends heading due north.
RADIUS = 200.0 / math.pi
ARC = [(100.0 + RADIUS * math.sin(i * math.pi / 16), RADIUS - RADIUS * math.cos(i * math.pi / 16)) for i in range(9)]
ALIGNMENT = AlignmentModel(
    schema_version=1,
    project_id="project:test",
    alignment_id="alignment:test",
    geometry_sequence=[
        AlignmentElement(
            "tangent", "tangent", 0.0, 100.0, length=100.0,
            geometry_payload={"x_values": [0.0, 100.0], "y_values": [0.0, 0.0]},
        ),
        AlignmentElement(
            "curve", "circular_curve", 100.0, 200.0, length=100.0,
            geometry_payload={"x_values": [p[0] for p in ARC], "y_values": [p[1] for p in ARC]},
        ),
    ],
)
PROFILE = ProfileModel(
    schema_version=1,
    project_id="project:test",
    profile_id="profile:test",
    alignment_id="alignment:test",
    control_rows=[ProfileControlPoint("pvi:20", 20.0, 10.0), ProfileControlPoint("pvi:150", 150.0, 15.0)],
)
CENTERLINE = Centerline3DResult(
    status="ready",
    point_rows=(
        Centerline3DPointRow(20.0, 20.0, 0.0, 10.0, grade=5.0 / 130.0),
        Centerline3DPointRow(150.0, 145.016, 18.646, 15.0, grade=5.0 / 130.0),
    ),
)


def _plan_point(station: float) -> tuple[float, float, float]:
    if station <= 100.0:
        return station, 0.0, 0.0
    angle = (station - 100.0) / RADIUS
    return 100.0 + RADIUS * math.sin(angle), RADIUS - RADIUS * math.cos(angle), math.degrees(angle)


@pytest.mark.parametrize(
    ("station", "held_elevation"),
    [(0.0, 10.0), (10.0, 10.0), (160.0, 15.0), (180.0, 15.0), (200.0, 15.0)],
)
def test_station_outside_the_profile_keeps_true_plan_frame_and_holds_elevation(station, held_elevation) -> None:
    frame = Centerline3DFrameService().resolve_station(CENTERLINE, station, alignment=ALIGNMENT, profile=PROFILE)
    x, y, heading = _plan_point(station)

    assert frame.x == pytest.approx(x, abs=1.0e-6)
    assert frame.y == pytest.approx(y, abs=1.0e-6)
    assert frame.tangent_direction_deg == pytest.approx(heading, abs=1.0e-6)
    assert frame.z == held_elevation
    assert frame.grade == 0.0
    assert frame.status == "warning"
    assert frame.source_mode == "alignment_profile_fallback"
    assert any(row.startswith("warning|profile_station_out_of_range|") for row in frame.diagnostic_rows)
    assert not any(row.startswith("error|") for row in frame.diagnostic_rows)


def test_station_inside_the_profile_is_still_a_source_geometry_frame() -> None:
    frame = Centerline3DFrameService().resolve_station(CENTERLINE, 85.0, alignment=ALIGNMENT, profile=PROFILE)

    assert frame.status == "ok"
    assert frame.source_mode == "centerline3d_source_geometry"
    assert frame.z == pytest.approx(12.5)


def test_applied_section_frame_reports_the_held_elevation_as_a_fallback() -> None:
    frame = Centerline3DFrameService().resolve_station(CENTERLINE, 180.0, alignment=ALIGNMENT, profile=PROFILE)

    section_frame = AppliedSectionService._build_frame(
        station=180.0,
        alignment_id="alignment:test",
        alignment_result=None,
        profile_result=ProfileEvaluationService().evaluate_station(PROFILE, 180.0),
        centerline_frame=frame,
    )

    assert section_frame.source_mode == "alignment_profile_fallback"
    assert section_frame.profile_status == "out_of_range"
    assert "source=alignment_profile_fallback" in section_frame.notes
    assert "source=centerline3d_source_geometry" not in section_frame.notes
    assert any("profile_station_out_of_range" in row for row in section_frame.source_diagnostic_rows)


def test_station_past_the_alignment_is_not_given_a_source_frame() -> None:
    frame = Centerline3DFrameService().resolve_station(CENTERLINE, 210.0, alignment=ALIGNMENT, profile=PROFILE)

    assert frame.source_mode == "centerline3d_result"
    assert any("alignment_source_not_resolved" in row for row in frame.diagnostic_rows)

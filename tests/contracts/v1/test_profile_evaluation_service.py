from freecad.Corridor_Road.v1.models.source.profile_model import (
    ProfileControlPoint,
    ProfileModel,
    VerticalCurveRow,
)
from freecad.Corridor_Road.v1.services.evaluation import ProfileEvaluationService


def _profile_model() -> ProfileModel:
    return ProfileModel(
        schema_version=1,
        project_id="test-project",
        profile_id="profile:fg",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint(
                control_point_id="pvi-0",
                station=0.0,
                elevation=10.0,
                kind="grade_break",
            ),
            ProfileControlPoint(
                control_point_id="pvi-50",
                station=50.0,
                elevation=15.0,
                kind="pvi",
            ),
            ProfileControlPoint(
                control_point_id="pvi-100",
                station=100.0,
                elevation=12.5,
                kind="grade_break",
            ),
        ],
        vertical_curve_rows=[
            VerticalCurveRow(
                vertical_curve_id="curve-1",
                kind="parabolic_vertical_curve",
                station_start=40.0,
                station_end=60.0,
                curve_length=20.0,
            )
        ],
    )


def test_profile_evaluation_interpolates_elevation_and_grade_between_controls() -> None:
    result = ProfileEvaluationService().evaluate_station(_profile_model(), 25.0)

    assert result.status == "ok"
    assert abs(result.elevation - 12.5) < 1e-9
    assert abs(result.grade - 0.1) < 1e-9
    assert result.active_segment_start_id == "pvi-0"
    assert result.active_segment_end_id == "pvi-50"
    assert abs(result.offset_on_segment - 25.0) < 1e-9


def test_profile_evaluation_reports_descending_grade_after_pvi() -> None:
    result = ProfileEvaluationService().evaluate_station(_profile_model(), 75.0)

    assert result.status == "ok"
    assert abs(result.elevation - 13.75) < 1e-9
    assert abs(result.grade + 0.05) < 1e-9
    assert result.active_segment_start_id == "pvi-50"
    assert result.active_segment_end_id == "pvi-100"


def test_profile_evaluation_attaches_active_vertical_curve_metadata() -> None:
    result = ProfileEvaluationService().evaluate_station(_profile_model(), 45.0)

    assert result.status == "ok"
    assert result.active_vertical_curve_id == "curve-1"
    assert "vertical-curve" in result.notes


def test_profile_evaluation_uses_parabolic_vertical_curve_elevation_and_grade() -> None:
    result = ProfileEvaluationService().evaluate_station(_profile_model(), 45.0)

    assert result.status == "ok"
    assert result.active_vertical_curve_id == "curve-1"
    assert abs(result.elevation - 14.40625) < 1e-9
    assert abs(result.grade - 0.0625) < 1e-9
    assert "parabolic" in result.notes


def test_profile_evaluation_parabolic_curve_matches_tangent_at_evc() -> None:
    result = ProfileEvaluationService().evaluate_station(_profile_model(), 60.0)

    assert result.status == "ok"
    assert abs(result.elevation - 14.5) < 1e-9
    assert abs(result.grade + 0.05) < 1e-9


def test_profile_evaluation_reports_out_of_range_station() -> None:
    result = ProfileEvaluationService().evaluate_station(_profile_model(), 120.0)

    assert result.status == "out_of_range"
    assert result.elevation == 12.5
    assert result.active_control_point_id == "pvi-100"


def test_profile_evaluation_reports_no_controls() -> None:
    result = ProfileEvaluationService().evaluate_station(
        ProfileModel(
            schema_version=1,
            project_id="test-project",
            profile_id="profile:empty",
            alignment_id="alignment:test",
        ),
        10.0,
    )

    assert result.status == "no_controls"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 profile evaluation service contract tests completed.")

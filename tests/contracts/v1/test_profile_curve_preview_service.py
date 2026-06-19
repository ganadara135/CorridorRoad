from freecad.Corridor_Road.v1.models.source.profile_model import ProfileControlPoint, ProfileModel, VerticalCurveRow
from freecad.Corridor_Road.v1.services.evaluation import ProfileCurvePreviewRequest, ProfileCurvePreviewService


def _sag_profile() -> ProfileModel:
    return ProfileModel(
        schema_version=1,
        project_id="project:test",
        profile_id="profile:sag",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint("pvi:0", 0.0, 0.0),
            ProfileControlPoint("pvi:50", 50.0, -20.0, kind="pvi"),
            ProfileControlPoint("pvi:100", 100.0, 0.0),
        ],
        vertical_curve_rows=[
            VerticalCurveRow("curve:sag", "parabolic_vertical_curve", 0.0, 100.0, curve_length=100.0),
        ],
    )


def test_profile_curve_preview_returns_evaluated_and_source_tangent_points() -> None:
    result = ProfileCurvePreviewService().evaluate(ProfileCurvePreviewRequest(profile=_sag_profile(), sample_interval=10.0))

    evaluated = [row for row in result.point_rows if row.role == "evaluated_curve"]
    tangent = [row for row in result.point_rows if row.role == "source_tangent"]

    assert result.status == "ready"
    assert evaluated
    assert tangent
    assert any(abs(row.station - 50.0) <= 1.0e-9 and abs(row.elevation - (-10.0)) <= 1.0e-9 for row in evaluated)
    assert any(abs(row.station - 50.0) <= 1.0e-9 and abs(row.elevation - (-20.0)) <= 1.0e-9 for row in tangent)


def test_profile_curve_preview_labels_required_vertical_curve_annotations() -> None:
    result = ProfileCurvePreviewService().evaluate(ProfileCurvePreviewRequest(profile=_sag_profile(), sample_interval=10.0))
    kinds = {row.kind for row in result.annotation_rows}
    curve = result.curve_rows[0]

    assert {"BVC", "PVI", "EVC", "L", "g1", "g2", "A", "K", "LP", "Max deviation"}.issubset(kinds)
    assert curve.curve_id == "curve:sag"
    assert curve.high_low_kind == "LP"
    assert abs(curve.high_low_station - 50.0) <= 1.0e-9
    assert curve.max_chord_deviation > 0.0
    assert any(row.kind == "profile_vertical_curve_parabolic_evaluated" for row in result.diagnostic_rows)


def test_profile_curve_preview_reports_missing_pvi_and_linear_fallback() -> None:
    profile = ProfileModel(
        schema_version=1,
        project_id="project:test",
        profile_id="profile:missing-pvi",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint("pvi:0", 0.0, 0.0),
            ProfileControlPoint("pvi:100", 100.0, 0.0),
        ],
        vertical_curve_rows=[
            VerticalCurveRow("curve:no-pvi", "parabolic_vertical_curve", 0.0, 100.0, curve_length=100.0),
        ],
    )

    result = ProfileCurvePreviewService().evaluate(ProfileCurvePreviewRequest(profile=profile, sample_interval=10.0))
    diagnostic_kinds = {row.kind for row in result.diagnostic_rows}

    assert result.status == "ready"
    assert "profile_vertical_curve_missing_pvi" in diagnostic_kinds
    assert "profile_vertical_curve_linear_fallback" in diagnostic_kinds
    assert result.curve_rows[0].status == "warning"


if __name__ == "__main__":
    test_profile_curve_preview_returns_evaluated_and_source_tangent_points()
    test_profile_curve_preview_labels_required_vertical_curve_annotations()
    test_profile_curve_preview_reports_missing_pvi_and_linear_fallback()
    print("PASS Profile curve preview service contract validation")

"""Contract tests for Profile presets with vertical-curve sample data."""

from __future__ import annotations

from freecad.Corridor_Road.v1.commands.cmd_profile_editor import (
    profile_model_from_editor_rows,
    profile_preset_names,
    profile_preset_rows,
    profile_preset_rows_for_station_rows,
    profile_preset_vertical_curve_rows,
    profile_preset_vertical_curve_rows_for_station_rows,
)
from freecad.Corridor_Road.v1.services.evaluation import ProfileCurvePreviewRequest, ProfileCurvePreviewService


def test_vertical_curve_showcase_preset_provides_control_and_curve_rows() -> None:
    assert profile_preset_names()[0] == "Vertical Curve Showcase"
    assert "Starter Road" not in profile_preset_names()

    control_rows = profile_preset_rows("Vertical Curve Showcase")
    curve_rows = profile_preset_vertical_curve_rows("Vertical Curve Showcase")

    assert len(control_rows) == 5
    assert len(curve_rows) == 3
    elevations = [float(row["elevation"]) for row in control_rows]
    assert min(elevations) >= 30.0
    assert max(elevations) <= 130.0
    assert all(str(row["kind"]) == "parabolic_vertical_curve" for row in curve_rows)


def test_vertical_curve_showcase_scales_to_current_station_rows() -> None:
    station_rows = [
        {"station": 1000.0, "kind": "grade_break"},
        {"station": 1080.0, "kind": "pvi"},
        {"station": 1160.0, "kind": "pvi"},
        {"station": 1240.0, "kind": "pvi"},
        {"station": 1320.0, "kind": "grade_break"},
    ]

    control_rows = profile_preset_rows_for_station_rows("Vertical Curve Showcase", station_rows)
    curve_rows = profile_preset_vertical_curve_rows_for_station_rows("Vertical Curve Showcase", station_rows)

    assert control_rows[0]["station"] == 1000.0
    assert control_rows[-1]["station"] == 1320.0
    assert len(curve_rows) == 3
    assert curve_rows[0]["station_start"] == 1056.0
    assert curve_rows[0]["station_end"] == 1104.0
    assert 0.5 * (curve_rows[0]["station_start"] + curve_rows[0]["station_end"]) == 1080.0


def test_vertical_curve_showcase_preview_exposes_crest_and_sag_curves() -> None:
    control_rows = profile_preset_rows("Vertical Curve Showcase")
    curve_rows = profile_preset_vertical_curve_rows("Vertical Curve Showcase")
    profile = profile_model_from_editor_rows(control_rows, curve_rows, profile_id="profile:vertical-curve-showcase")

    result = ProfileCurvePreviewService().evaluate(
        ProfileCurvePreviewRequest(profile=profile, sample_interval=5.0)
    )

    kinds = {str(row.high_low_kind) for row in result.curve_rows}
    assert result.status == "ready"
    assert len(result.curve_rows) == 3
    assert result.curve_rows[0].pvi_station == 80.0
    assert 0.5 * (result.curve_rows[0].bvc_station + result.curve_rows[0].evc_station) == result.curve_rows[0].pvi_station
    pvi_1 = control_rows[1]
    pvi_2 = control_rows[2]
    expected_first_evc_elevation = float(pvi_1["elevation"]) + (
        (float(pvi_2["elevation"]) - float(pvi_1["elevation"]))
        / (float(pvi_2["station"]) - float(pvi_1["station"]))
    ) * (result.curve_rows[0].evc_station - float(pvi_1["station"]))
    assert abs(result.curve_rows[0].evc_elevation - expected_first_evc_elevation) <= 1.0e-9
    assert "HP" in kinds
    assert "LP" in kinds
    assert any(row.kind == "BVC" for row in result.annotation_rows)
    assert any(row.kind == "EVC" for row in result.annotation_rows)


if __name__ == "__main__":
    test_vertical_curve_showcase_preset_provides_control_and_curve_rows()
    test_vertical_curve_showcase_scales_to_current_station_rows()
    test_vertical_curve_showcase_preview_exposes_crest_and_sag_curves()
    print("PASS Profile vertical curve preset validation")

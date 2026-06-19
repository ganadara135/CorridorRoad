"""Contract tests for K-value based Profile vertical curve auto generation."""

from __future__ import annotations

from freecad.Corridor_Road.objects import design_standards as _ds
from freecad.Corridor_Road.v1.commands.cmd_profile_editor import (
    generate_profile_vertical_curve_rows_from_controls,
    profile_model_from_editor_rows,
    profile_vertical_curve_k_value,
)
from freecad.Corridor_Road.v1.services.evaluation import ProfileCurvePreviewRequest, ProfileCurvePreviewService


def _control_rows():
    return [
        {"station": 0.0, "elevation": 0.0, "kind": "grade_break"},
        {"station": 100.0, "elevation": 10.0, "kind": "pvi"},
        {"station": 200.0, "elevation": 0.0, "kind": "pvi"},
        {"station": 300.0, "elevation": 10.0, "kind": "grade_break"},
    ]


def _long_control_rows():
    return [
        {"station": 0.0, "elevation": 0.0, "kind": "grade_break"},
        {"station": 1000.0, "elevation": 100.0, "kind": "pvi"},
        {"station": 2000.0, "elevation": 0.0, "kind": "pvi"},
        {"station": 3000.0, "elevation": 100.0, "kind": "grade_break"},
    ]


def test_profile_vertical_curve_k_value_lookup_uses_nearest_speed_and_type() -> None:
    assert profile_vertical_curve_k_value(62.0, "crest") == 18.0
    assert profile_vertical_curve_k_value(82.0, "sag") == 32.0
    assert _ds.vertical_curve_k_value("KDS", 62.0, "crest") == 18.0
    assert _ds.vertical_curve_k_value("AASHTO", 62.0, "crest") == 19.0
    assert profile_vertical_curve_k_value(62.0, "crest", standard="AASHTO") == 19.0


def test_k_value_auto_generates_crest_and_sag_lengths() -> None:
    rows, summary = generate_profile_vertical_curve_rows_from_controls(
        _long_control_rows(),
        design_speed_kph=60.0,
        min_length=10.0,
        max_length=1000.0,
        tangent_clearance_ratio=0.49,
        return_diagnostics=True,
    )

    assert len(rows) == 2
    assert summary["crest"] == 1
    assert summary["sag"] == 1
    assert rows[0]["kind"] == "parabolic_vertical_curve"
    assert rows[1]["kind"] == "parabolic_vertical_curve"
    assert abs(float(rows[0]["length"]) - 360.0) <= 1.0e-9
    assert abs(float(rows[1]["length"]) - 360.0) <= 1.0e-9


def test_k_value_auto_clamps_by_spacing_and_reports_warning() -> None:
    rows, summary = generate_profile_vertical_curve_rows_from_controls(
        _control_rows(),
        design_speed_kph=100.0,
        min_length=10.0,
        max_length=1000.0,
        tangent_clearance_ratio=0.45,
        return_diagnostics=True,
    )

    assert len(rows) == 2
    assert summary["clamped"] >= 1
    assert abs(float(rows[0]["length"]) - 90.0) <= 1.0e-9
    assert any("clamped" in row for row in summary["diagnostics"])


def test_k_value_auto_uses_selected_design_standard() -> None:
    rows, _summary = generate_profile_vertical_curve_rows_from_controls(
        _long_control_rows(),
        design_standard="AASHTO",
        design_speed_kph=60.0,
        min_length=10.0,
        max_length=1000.0,
        tangent_clearance_ratio=0.49,
        return_diagnostics=True,
    )

    assert abs(float(rows[0]["length"]) - 380.0) <= 1.0e-9


def test_k_value_auto_preview_exposes_crest_and_sag() -> None:
    rows, _summary = generate_profile_vertical_curve_rows_from_controls(
        _control_rows(),
        design_speed_kph=60.0,
        min_length=10.0,
        max_length=300.0,
        tangent_clearance_ratio=0.49,
        return_diagnostics=True,
    )
    profile = profile_model_from_editor_rows(_control_rows(), rows, profile_id="profile:k-value-auto")

    result = ProfileCurvePreviewService().evaluate(
        ProfileCurvePreviewRequest(profile=profile, sample_interval=5.0)
    )
    kinds = {row.high_low_kind for row in result.curve_rows}

    assert result.status == "ready"
    assert "HP" in kinds
    assert "LP" in kinds


if __name__ == "__main__":
    test_profile_vertical_curve_k_value_lookup_uses_nearest_speed_and_type()
    test_k_value_auto_generates_crest_and_sag_lengths()
    test_k_value_auto_clamps_by_spacing_and_reports_warning()
    test_k_value_auto_uses_selected_design_standard()
    test_k_value_auto_preview_exposes_crest_and_sag()
    print("PASS Profile vertical curve K-value auto validation")

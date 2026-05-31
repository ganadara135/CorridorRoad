from freecad.Corridor_Road.v1.services.evaluation.superelevation_auto_calculation_service import (
    SuperelevationAutoCalculationRequest,
    SuperelevationAutoCalculationService,
    SuperelevationCurveCandidate,
)


def test_superelevation_auto_calculation_generates_paired_crossfall_rows() -> None:
    result = SuperelevationAutoCalculationService().calculate(
        SuperelevationAutoCalculationRequest(
            project_id="project:test",
            alignment_id="alignment:test",
            station_start=0.0,
            station_end=200.0,
            design_speed_kph=60.0,
            max_superelevation_percent=8.0,
            side_friction=0.15,
            min_transition_length=20.0,
            curve_candidates=[
                SuperelevationCurveCandidate(
                    curve_id="curve:1",
                    station_start=50.0,
                    station_end=150.0,
                    radius=120.0,
                    direction="right",
                    transition_length=25.0,
                )
            ],
        )
    )

    model = result.superelevation_model
    assert model.alignment_id == "alignment:test"
    assert len(model.control_rows) == 12
    assert len(model.transition_rows) == 2
    full_rows = [row for row in model.control_rows if row.kind == "full_super"]
    assert any(row.side == "left" and row.crossfall_value > 0.0 for row in full_rows)
    assert any(row.side == "right" and row.crossfall_value < 0.0 for row in full_rows)
    assert {row.kind for row in model.constraint_rows} >= {
        "design_speed",
        "max_superelevation_rate",
        "side_friction",
        "min_transition_length",
    }


def test_superelevation_auto_calculation_without_curves_keeps_normal_crossfall() -> None:
    result = SuperelevationAutoCalculationService().calculate(
        SuperelevationAutoCalculationRequest(
            project_id="project:test",
            alignment_id="alignment:test",
            station_start=0.0,
            station_end=100.0,
            curve_candidates=[],
        )
    )

    model = result.superelevation_model
    assert len(model.control_rows) == 4
    assert all(row.crossfall_value == -2.0 for row in model.control_rows)
    assert result.diagnostic_rows[0].kind == "no_alignment_curve_candidates"

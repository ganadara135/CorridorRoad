from freecad.Corridor_Road.v1.models.source.superelevation_model import (
    CrossfallControlRow,
    RunoffTransitionRow,
    SuperelevationConstraint,
    SuperelevationModel,
)
from freecad.Corridor_Road.v1.services.evaluation.superelevation_service import (
    SuperelevationService,
    SuperelevationValidationService,
)


def _model() -> SuperelevationModel:
    return SuperelevationModel(
        schema_version=1,
        project_id="project:test",
        superelevation_id="superelevation:main",
        alignment_id="alignment:main",
        control_rows=[
            CrossfallControlRow("control:normal", 0.0, "both", -2.0, kind="normal_crown"),
            CrossfallControlRow("control:right-full", 80.0, "right", 6.0, kind="full_super"),
            CrossfallControlRow("control:left-after", 120.0, "left", -2.0, kind="rotation_end"),
            CrossfallControlRow("control:right-after", 120.0, "right", -2.0, kind="rotation_end"),
        ],
        transition_rows=[
            RunoffTransitionRow("transition:runoff", 40.0, 80.0, "runoff"),
            RunoffTransitionRow("transition:runout", 80.0, 120.0, "runout"),
        ],
    )


def test_superelevation_service_interpolates_right_side_transition() -> None:
    result = SuperelevationService().evaluate_station(_model(), 60.0)

    assert result.status == "ok"
    assert result.active_transition_id == "transition:runoff"
    assert result.left_crossfall == -2.0
    assert result.right_crossfall == 2.0
    assert result.active_control_ids == ["control:normal", "control:right-full"]


def test_superelevation_service_uses_active_control_outside_transition() -> None:
    result = SuperelevationService().evaluate_station(_model(), 90.0)

    assert result.active_transition_id == "transition:runout"
    assert result.left_crossfall == -2.0
    assert result.right_crossfall == 4.0


def test_superelevation_service_falls_back_to_assembly_defaults_when_empty() -> None:
    model = SuperelevationModel(
        schema_version=1,
        project_id="project:test",
        superelevation_id="superelevation:empty",
        alignment_id="alignment:main",
    )

    result = SuperelevationService().evaluate_station(
        model,
        10.0,
        default_left_crossfall=-2.5,
        default_right_crossfall=-2.5,
    )

    assert result.status == "fallback"
    assert result.left_crossfall == -2.5
    assert result.right_crossfall == -2.5
    assert [row.kind for row in result.diagnostic_rows] == ["empty_superelevation_controls"]


def test_superelevation_validation_reports_bad_rows_and_station_range() -> None:
    model = SuperelevationModel(
        schema_version=1,
        project_id="project:test",
        superelevation_id="superelevation:bad",
        alignment_id="",
        control_rows=[
            CrossfallControlRow("", 0.0, "diagonal", -2.0),
            CrossfallControlRow("control:high", 150.0, "right", 14.0),
            CrossfallControlRow("control:dup-a", 20.0, "left", -2.0),
            CrossfallControlRow("control:dup-b", 20.0, "left", -3.0),
        ],
        transition_rows=[
            RunoffTransitionRow("transition:bad", 80.0, 40.0, "runoff"),
            RunoffTransitionRow("transition:outside", 90.0, 120.0, "runoff"),
        ],
        constraint_rows=[
            SuperelevationConstraint("constraint:max", "max_superelevation_rate", 8.0, "percent"),
            SuperelevationConstraint("constraint:min", "min_transition_length", 50.0, "m"),
        ],
    )

    result = SuperelevationValidationService().validate(model, station_range=(0.0, 100.0))
    kinds = [row.kind for row in result.diagnostic_rows]

    assert result.status == "error"
    assert "missing_alignment_id" in kinds
    assert "missing_control_row_id" in kinds
    assert "invalid_control_side" in kinds
    assert "control_station_outside_station_range" in kinds
    assert "high_crossfall_value" in kinds
    assert "duplicate_station_side_control" in kinds
    assert "invalid_transition_station_range" in kinds
    assert "transition_outside_station_range" in kinds
    assert "transition_shorter_than_minimum" in kinds


def test_superelevation_service_samples_stations_in_order() -> None:
    rows = SuperelevationService().sample_stations(_model(), [80.0, 0.0, 40.0])

    assert [row.station for row in rows] == [0.0, 40.0, 80.0]
    assert rows[-1].right_crossfall == 6.0


def test_superelevation_validation_allows_display_rounded_boundary_stations() -> None:
    model = SuperelevationModel(
        schema_version=1,
        project_id="project:test",
        superelevation_id="superelevation:boundary",
        alignment_id="alignment:main",
        control_rows=[
            CrossfallControlRow("control:end-left", 203.108, "left", -2.0),
            CrossfallControlRow("control:end-right", 203.108, "right", -2.0),
        ],
        transition_rows=[
            RunoffTransitionRow("transition:min", 10.0, 30.0, "runoff"),
        ],
        constraint_rows=[
            SuperelevationConstraint("constraint:min", "min_transition_length", 20.0000001, "m"),
        ],
    )

    result = SuperelevationValidationService().validate(model, station_range=(0.0, 203.1076))
    kinds = [row.kind for row in result.diagnostic_rows]

    assert "control_station_outside_station_range" not in kinds
    assert "transition_shorter_than_minimum" not in kinds


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 superelevation service contract tests completed.")

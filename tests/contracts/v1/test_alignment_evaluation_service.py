from freecad.Corridor_Road.v1.models.source.alignment_model import (
    AlignmentElement,
    AlignmentModel,
)
from freecad.Corridor_Road.v1.services.evaluation import AlignmentEvaluationService


def _east_tangent_alignment() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:east",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:east:tangent:1",
                kind="tangent",
                station_start=100.0,
                station_end=200.0,
                length=100.0,
                geometry_payload={
                    "x_values": [1000.0, 1100.0],
                    "y_values": [2000.0, 2000.0],
                },
            )
        ],
    )


def _north_tangent_alignment() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:north",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:north:tangent:1",
                kind="tangent",
                station_start=0.0,
                station_end=10.0,
                geometry_payload={
                    "x_values": [0.0, 0.0],
                    "y_values": [0.0, 10.0],
                },
            )
        ],
    )


def _sampled_polyline_alignment() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:sampled",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:sampled:curve-ish:1",
                kind="sampled_curve",
                station_start=0.0,
                station_end=20.0,
                length=20.0,
                geometry_payload={
                    "x_values": [0.0, 10.0, 10.0],
                    "y_values": [0.0, 0.0, 10.0],
                },
            )
        ],
    )


def test_evaluate_station_on_tangent_returns_xy_and_tangent() -> None:
    result = AlignmentEvaluationService().evaluate_station(
        _east_tangent_alignment(),
        125.0,
    )

    assert result.status == "ok"
    assert result.active_element_kind == "tangent"
    assert abs(result.x - 1025.0) < 1e-9
    assert abs(result.y - 2000.0) < 1e-9
    assert abs(result.tangent_direction_deg - 0.0) < 1e-9
    assert abs(result.offset_on_element - 25.0) < 1e-9


def test_evaluate_station_on_sampled_polyline_uses_active_segment_tangent() -> None:
    result = AlignmentEvaluationService().evaluate_station(
        _sampled_polyline_alignment(),
        15.0,
    )

    assert result.status == "ok"
    assert abs(result.x - 10.0) < 1e-9
    assert abs(result.y - 5.0) < 1e-9
    assert abs(result.tangent_direction_deg - 90.0) < 1e-9


def test_evaluate_station_outside_alignment_reports_status() -> None:
    result = AlignmentEvaluationService().evaluate_station(
        _east_tangent_alignment(),
        250.0,
    )

    assert result.status == "out_of_range"
    assert result.active_element_id == ""


def test_station_offset_to_xy_uses_left_positive_local_frame() -> None:
    x, y = AlignmentEvaluationService().station_offset_to_xy(
        _north_tangent_alignment(),
        5.0,
        2.0,
    )

    assert abs(x + 2.0) < 1e-9
    assert abs(y - 5.0) < 1e-9


def test_station_offset_adapter_can_drive_downstream_sampling() -> None:
    service = AlignmentEvaluationService()
    adapter = service.station_offset_adapter(_east_tangent_alignment())

    x, y = adapter(150.0, 5.0)

    assert abs(x - 1050.0) < 1e-9
    assert abs(y - 2005.0) < 1e-9


def test_station_offset_to_xy_rejects_invalid_station() -> None:
    try:
        AlignmentEvaluationService().station_offset_to_xy(
            _east_tangent_alignment(),
            250.0,
            0.0,
        )
    except ValueError as exc:
        assert "outside" in str(exc)
    else:
        raise AssertionError("Expected invalid station to be rejected.")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 alignment evaluation service contract tests completed.")

from freecad.Corridor_Road.v1.models.source.alignment_model import (
    AlignmentElement,
    AlignmentModel,
)
from freecad.Corridor_Road.v1.services.evaluation import AlignmentStationSamplingService


def _two_element_alignment() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:sample-range",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:sample-range:tangent:1",
                kind="tangent",
                station_start=0.0,
                station_end=40.0,
                length=40.0,
                geometry_payload={
                    "x_values": [1000.0, 1040.0],
                    "y_values": [2000.0, 2000.0],
                },
            ),
            AlignmentElement(
                element_id="alignment:sample-range:sampled:2",
                kind="sampled_curve",
                station_start=40.0,
                station_end=80.0,
                length=40.0,
                geometry_payload={
                    "x_values": [1040.0, 1070.0, 1080.0],
                    "y_values": [2000.0, 2010.0, 2040.0],
                },
            ),
        ],
    )


def test_sample_alignment_returns_regular_station_grid_with_end() -> None:
    result = AlignmentStationSamplingService().sample_alignment(
        alignment=_two_element_alignment(),
        interval=20.0,
    )

    assert result.status == "ok"
    assert [row.station for row in result.rows] == [0.0, 20.0, 40.0, 60.0, 80.0]
    assert result.rows[0].source_reason == "range_start"
    assert result.rows[-1].source_reason == "range_end"
    assert result.rows[0].x == 1000.0
    assert result.rows[2].active_element_id == "alignment:sample-range:tangent:1"
    assert result.rows[3].active_element_id == "alignment:sample-range:sampled:2"


def test_sample_range_merges_extra_stations_without_duplicates() -> None:
    result = AlignmentStationSamplingService().sample_range(
        alignment=_two_element_alignment(),
        station_start=0.0,
        station_end=80.0,
        interval=30.0,
        extra_stations=[40.0, 40.0, 55.0, 100.0],
    )

    assert [row.station for row in result.rows] == [0.0, 30.0, 40.0, 55.0, 60.0, 80.0]
    assert result.rows[2].source_reason == "extra_station"
    assert result.rows[3].source_reason == "extra_station"


def test_sample_range_invalid_interval_returns_error() -> None:
    result = AlignmentStationSamplingService().sample_range(
        alignment=_two_element_alignment(),
        station_start=0.0,
        station_end=80.0,
        interval=0.0,
    )

    assert result.status == "error"
    assert result.rows == []
    assert "greater than zero" in result.notes


def test_sample_alignment_without_geometry_returns_empty() -> None:
    result = AlignmentStationSamplingService().sample_alignment(
        alignment=AlignmentModel(
            schema_version=1,
            project_id="test-project",
            alignment_id="alignment:empty",
        ),
        interval=20.0,
    )

    assert result.status == "empty"
    assert result.rows == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 alignment station sampling service contract tests completed.")

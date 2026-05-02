from freecad.Corridor_Road.v1.models.result import TINSurface
from freecad.Corridor_Road.v1.models.result.tin_surface import TINTriangle, TINVertex
from freecad.Corridor_Road.v1.services.evaluation import (
    TinSamplingService,
    TinSectionSamplingService,
)


def _square_surface() -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:section-square",
        vertex_rows=[
            TINVertex("v0", 0.0, 0.0, 0.0),
            TINVertex("v1", 10.0, 0.0, 10.0),
            TINVertex("v2", 10.0, 10.0, 20.0),
            TINVertex("v3", 0.0, 10.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("t0", "v0", "v1", "v2"),
            TINTriangle("t1", "v0", "v2", "v3"),
        ],
    )


def test_sample_offsets_returns_profile_rows_for_all_hits() -> None:
    result = TinSectionSamplingService().sample_offsets(
        surface=_square_surface(),
        station=5.0,
        offsets=[0.0, 2.5, 5.0],
        station_offset_to_xy=lambda station, offset: (station, offset),
    )

    assert result.surface_ref == "tin:section-square"
    assert result.station == 5.0
    assert result.status == "ok"
    assert result.hit_count == 3
    assert [row.offset for row in result.rows] == [0.0, 2.5, 5.0]
    assert [round(float(row.z or 0.0), 6) for row in result.rows] == [5.0, 7.5, 10.0]
    assert all(row.face_id for row in result.rows)


def test_sample_offsets_keeps_no_hit_rows_without_zero_elevation() -> None:
    result = TinSectionSamplingService().sample_offsets(
        surface=_square_surface(),
        station=5.0,
        offsets=[5.0, 15.0],
        station_offset_to_xy=lambda station, offset: (station, offset),
    )

    assert result.status == "partial"
    assert result.hit_count == 1
    assert result.miss_count == 1
    assert result.rows[0].status == "ok"
    assert result.rows[1].status == "no_hit"
    assert result.rows[1].z is None
    assert result.rows[1].z != 0.0


def test_sample_offsets_without_adapter_returns_explicit_error_rows() -> None:
    result = TinSectionSamplingService().sample_offsets(
        surface=_square_surface(),
        station=5.0,
        offsets=[-2.0, 0.0, 2.0],
    )

    assert result.status == "error"
    assert result.hit_count == 0
    assert len(result.rows) == 3
    assert all(row.status == "error" for row in result.rows)
    assert "adapter is missing" in result.notes


def test_sample_offsets_adapter_exception_is_reported_per_row() -> None:
    def _adapter(station: float, offset: float) -> tuple[float, float]:
        if offset < 0.0:
            raise ValueError("negative offset blocked")
        return station, offset

    result = TinSectionSamplingService().sample_offsets(
        surface=_square_surface(),
        station=5.0,
        offsets=[-1.0, 1.0],
        station_offset_to_xy=_adapter,
    )

    assert result.status == "partial"
    assert result.rows[0].status == "error"
    assert result.rows[0].z is None
    assert "negative offset blocked" in result.rows[0].notes
    assert result.rows[1].status == "ok"


def test_sample_offsets_uses_station_rows_adapter_from_tin_sampling_service() -> None:
    adapter = TinSamplingService().station_offset_adapter_from_rows(
        [
            {"station": 0.0, "x": 0.0, "y": 0.0},
            {"station": 10.0, "x": 10.0, "y": 0.0},
        ]
    )

    result = TinSectionSamplingService().sample_offsets(
        surface=_square_surface(),
        station=5.0,
        offsets=[0.0, 5.0],
        station_offset_to_xy=adapter,
    )

    assert result.status == "ok"
    assert [row.x for row in result.rows] == [5.0, 5.0]
    assert [row.y for row in result.rows] == [0.0, 5.0]
    assert [round(float(row.z or 0.0), 6) for row in result.rows] == [5.0, 10.0]


def test_sample_offsets_empty_offsets_is_explicit_empty_result() -> None:
    result = TinSectionSamplingService().sample_offsets(
        surface=_square_surface(),
        station=5.0,
        offsets=[],
        station_offset_to_xy=lambda station, offset: (station, offset),
    )

    assert result.status == "empty"
    assert result.rows == []
    assert "At least one" in result.notes


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 TIN section sampling contract tests completed.")

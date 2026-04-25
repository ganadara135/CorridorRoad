from freecad.Corridor_Road.v1.models.result import TINSurface
from freecad.Corridor_Road.v1.models.result.tin_surface import TINTriangle, TINVertex
from freecad.Corridor_Road.v1.services.evaluation import TinSamplingService


def _single_triangle_surface() -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:single",
        vertex_rows=[
            TINVertex("v0", 0.0, 0.0, 10.0),
            TINVertex("v1", 10.0, 0.0, 20.0),
            TINVertex("v2", 0.0, 10.0, 30.0),
        ],
        triangle_rows=[
            TINTriangle("t0", "v0", "v1", "v2"),
        ],
    )


def _square_surface() -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:square",
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


def test_tin_surface_exports_from_result_models() -> None:
    surface = _single_triangle_surface()

    assert surface.surface_id == "tin:single"
    assert len(surface.vertex_map()) == 3


def test_sample_xy_inside_single_triangle_interpolates_z() -> None:
    result = TinSamplingService().sample_xy(
        surface=_single_triangle_surface(),
        x=2.5,
        y=2.5,
    )

    assert result.found is True
    assert result.status == "ok"
    assert result.face_id == "t0"
    assert abs(float(result.z or 0.0) - 17.5) < 1e-9
    assert result.confidence > 0.0


def test_sample_xy_two_triangle_square_interpolates_z() -> None:
    result = TinSamplingService().sample_xy(
        surface=_square_surface(),
        x=7.5,
        y=7.5,
    )

    assert result.found is True
    assert result.status == "ok"
    assert abs(float(result.z or 0.0) - 15.0) < 1e-9


def test_sample_xy_accepts_boundary_point() -> None:
    result = TinSamplingService().sample_xy(
        surface=_single_triangle_surface(),
        x=5.0,
        y=0.0,
    )

    assert result.found is True
    assert result.status == "ok"
    assert abs(float(result.z or 0.0) - 15.0) < 1e-9


def test_sample_xy_outside_returns_no_hit() -> None:
    result = TinSamplingService().sample_xy(
        surface=_single_triangle_surface(),
        x=20.0,
        y=20.0,
    )

    assert result.found is False
    assert result.status == "no_hit"
    assert result.z is None
    assert "No containing" in result.notes


def test_sample_xy_degenerate_triangle_does_not_crash() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:degenerate",
        vertex_rows=[
            TINVertex("v0", 0.0, 0.0, 0.0),
            TINVertex("v1", 1.0, 1.0, 1.0),
            TINVertex("v2", 2.0, 2.0, 2.0),
        ],
        triangle_rows=[
            TINTriangle("t0", "v0", "v1", "v2"),
        ],
    )

    result = TinSamplingService().sample_xy(surface=surface, x=1.0, y=1.0)

    assert result.found is False
    assert result.status == "no_hit"
    assert "degenerate" in result.notes


def test_sample_station_offset_uses_explicit_adapter() -> None:
    result = TinSamplingService().sample_station_offset(
        surface=_single_triangle_surface(),
        station=2.5,
        offset=2.5,
        station_offset_to_xy=lambda station, offset: (station, offset),
    )

    assert result.found is True
    assert result.query_kind == "station_offset"
    assert abs(float(result.z or 0.0) - 17.5) < 1e-9


def test_station_offset_adapter_from_rows_uses_evaluated_station_xy() -> None:
    service = TinSamplingService()
    adapter = service.station_offset_adapter_from_rows(
        [
            {"station": 0.0, "x": 0.0, "y": 0.0},
            {"station": 10.0, "x": 10.0, "y": 0.0},
        ]
    )

    result = service.sample_station_offset(
        surface=_single_triangle_surface(),
        station=2.5,
        offset=2.5,
        station_offset_to_xy=adapter,
    )

    assert result.found is True
    assert result.query_kind == "station_offset"
    assert abs(result.x - 2.5) < 1e-9
    assert abs(result.y - 2.5) < 1e-9
    assert abs(float(result.z or 0.0) - 17.5) < 1e-9


def test_sample_station_offset_without_adapter_is_explicit_error() -> None:
    result = TinSamplingService().sample_station_offset(
        surface=_single_triangle_surface(),
        station=2.5,
        offset=2.5,
    )

    assert result.found is False
    assert result.status == "error"
    assert result.query_kind == "station_offset"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 TIN sampling contract tests completed.")

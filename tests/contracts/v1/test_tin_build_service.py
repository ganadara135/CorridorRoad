from pathlib import Path

from freecad.Corridor_Road.v1.services.builders import (
    TINBuildRequest,
    TINBuildService,
    TINPointInput,
)
from freecad.Corridor_Road.v1.services.evaluation import TinSamplingService


SAMPLE_PATH = Path("tests/samples/pointcloud_utm_realistic_hilly.csv")
MOUNTAIN_VALLEY_PLAIN_SAMPLE_PATH = Path("tests/samples/pointcloud_tin_mountain_valley_plain.csv")


def _quality_value(surface, kind: str):
    for row in surface.quality_rows:
        if row.kind == kind:
            return row.value
    return None


def test_build_from_points_creates_two_triangles_per_grid_cell() -> None:
    surface = TINBuildService().build_from_points(
        TINBuildRequest(
            project_id="test-project",
            surface_id="tin:small-grid",
            point_rows=[
                TINPointInput("p0", 0.0, 0.0, 10.0),
                TINPointInput("p1", 10.0, 0.0, 12.0),
                TINPointInput("p2", 0.0, 10.0, 14.0),
                TINPointInput("p3", 10.0, 10.0, 16.0),
            ],
        )
    )

    assert surface.surface_id == "tin:small-grid"
    assert len(surface.vertex_rows) == 4
    assert len(surface.triangle_rows) == 2
    assert _quality_value(surface, "x_spacing") == 10.0
    assert _quality_value(surface, "y_spacing") == 10.0


def test_build_from_csv_uses_realistic_pointcloud_sample() -> None:
    surface = TINBuildService().build_from_csv(
        SAMPLE_PATH,
        project_id="test-project",
        surface_id="tin:sample-hilly",
    )

    assert len(surface.vertex_rows) == 14641
    assert len(surface.triangle_rows) == 28800
    assert _quality_value(surface, "unique_x_count") == 121
    assert _quality_value(surface, "unique_y_count") == 121
    assert _quality_value(surface, "x_spacing") == 5.0
    assert _quality_value(surface, "y_spacing") == 5.0
    assert abs(float(_quality_value(surface, "z_min")) - 96.868) < 1e-9
    assert abs(float(_quality_value(surface, "z_max")) - 126.459) < 1e-9


def test_csv_built_tin_can_be_sampled_at_known_vertex() -> None:
    surface = TINBuildService().build_from_csv(
        SAMPLE_PATH,
        project_id="test-project",
        surface_id="tin:sample-hilly",
    )

    result = TinSamplingService().sample_xy(
        surface=surface,
        x=352000.0,
        y=4169000.0,
    )

    assert result.found is True
    assert result.status == "ok"
    assert abs(float(result.z or 0.0) - 116.0) < 1e-9


def test_build_from_csv_uses_mountain_valley_plain_sample() -> None:
    surface = TINBuildService().build_from_csv(
        MOUNTAIN_VALLEY_PLAIN_SAMPLE_PATH,
        project_id="test-project",
        surface_id="tin:mountain-valley-plain",
    )

    assert len(surface.vertex_rows) == 25921
    assert len(surface.triangle_rows) == 51200
    assert _quality_value(surface, "unique_x_count") == 161
    assert _quality_value(surface, "unique_y_count") == 161
    assert _quality_value(surface, "x_spacing") == 5.0
    assert _quality_value(surface, "y_spacing") == 5.0
    assert abs(float(_quality_value(surface, "z_min")) - 49.9) < 1e-9
    assert abs(float(_quality_value(surface, "z_max")) - 192.66) < 1e-9


def test_mountain_valley_plain_sample_can_be_sampled_near_center() -> None:
    surface = TINBuildService().build_from_csv(
        MOUNTAIN_VALLEY_PLAIN_SAMPLE_PATH,
        project_id="test-project",
        surface_id="tin:mountain-valley-plain",
    )

    result = TinSamplingService().sample_xy(
        surface=surface,
        x=353400.0,
        y=4168400.0,
    )

    assert result.found is True
    assert result.status == "ok"
    assert abs(float(result.z or 0.0) - 97.527) < 1e-9


def test_incomplete_lattice_is_rejected_explicitly() -> None:
    try:
        TINBuildService().build_from_points(
            TINBuildRequest(
                project_id="test-project",
                surface_id="tin:bad-grid",
                point_rows=[
                    TINPointInput("p0", 0.0, 0.0, 10.0),
                    TINPointInput("p1", 10.0, 0.0, 12.0),
                    TINPointInput("p2", 0.0, 10.0, 14.0),
                ],
            )
        )
    except ValueError as exc:
        assert "complete regular point lattice" in str(exc)
    else:
        raise AssertionError("Expected incomplete lattice to be rejected.")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 TIN build service contract tests completed.")

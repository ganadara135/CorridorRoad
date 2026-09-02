import math

from freecad.Corridor_Road.v1.models.result.centerline3d_arc_fit import Centerline3DArcFitResult
from freecad.Corridor_Road.v1.services.evaluation import Centerline3DSourceGeometryService


def test_source_geometry_service_returns_typed_accepted_arc_fit() -> None:
    radius = 100.0
    points = [
        (radius, 0.0),
        (radius / math.sqrt(2.0), radius / math.sqrt(2.0)),
        (0.0, radius),
    ]

    result = Centerline3DSourceGeometryService.evaluate_plan_arc_fit(points)

    assert isinstance(result, Centerline3DArcFitResult)
    assert result.accepted is True
    assert result.arc is not None
    assert abs(result.arc[2] - radius) <= 1.0e-9
    assert result.radial_error <= result.tolerance


def test_source_geometry_service_rejects_arc_outside_tolerance() -> None:
    result = Centerline3DSourceGeometryService.evaluate_plan_arc_fit(
        [(100.0, 0.0), (70.710678, 120.0), (40.0, 20.0), (0.0, 100.0)]
    )

    assert result.arc is not None
    assert result.accepted is False
    assert result.radial_error > result.tolerance


def test_source_geometry_service_normalizes_plan_payload_pairs() -> None:
    points = Centerline3DSourceGeometryService.plan_points_from_geometry_payload(
        {
            "x_values": [0, "bad", 20, 30],
            "y_values": [10, 20, "bad"],
        }
    )

    assert points == [(0.0, 10.0), (20.0, 20.0)]
    assert Centerline3DSourceGeometryService.plan_points_from_geometry_payload(None) == []


def test_source_geometry_service_normalizes_arc_fit_tolerances() -> None:
    assert Centerline3DSourceGeometryService.normalize_arc_fit_tolerances(-1.0, -0.5) == (0.0, 0.0)

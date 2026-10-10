from dataclasses import dataclass

from freecad.Corridor_Road.v1.services.geometry import xy_point


@dataclass(frozen=True)
class _Point:
    x: float
    y: float


def test_xy_point_accepts_objects_and_sequences() -> None:
    assert xy_point(_Point(3.0, 4.0)) == (3.0, 4.0)
    assert xy_point((6.0, 8.0, 10.0)) == (6.0, 8.0)
    assert xy_point(None) == (0.0, 0.0)

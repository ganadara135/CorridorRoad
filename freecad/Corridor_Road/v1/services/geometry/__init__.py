"""Pure geometry services for CorridorRoad v1."""

from .xy_primitives import xy_point
from .segment_geometry import xy_point_on_segment
from .polygon_relations import (
    xy_closed_edges,
    xy_point_in_polygon,
    xy_point_in_polygon_strict,
)

__all__ = [
    "xy_point",
    "xy_point_on_segment",
    "xy_closed_edges",
    "xy_point_in_polygon",
    "xy_point_in_polygon_strict",
]

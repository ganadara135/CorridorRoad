"""Pure geometry services for CorridorRoad v1."""

from .xy_primitives import (
    xy_distance,
    xy_point,
    xy_point_in_triangle_strict,
    xy_polygon_signed_area,
    xy_triangle_signed_area,
)
from .polygon_triangulation import (
    ear_clip_triangulation_indices,
    triangulate_simple_polygon_points,
    xy_triangle_quality_ratio,
)
from .convex_polygon_clipping import (
    dedupe_xy_payload_points,
    intersect_payload_polygon_with_convex_polygon,
    subtract_convex_polygon_from_payload_polygon,
    xy_polygon_is_convex,
)
from .segment_geometry import (
    clip_polyline_points_to_anchor_window,
    clip_segment_to_anchor_box,
    xy_point_on_segment,
    xy_point_segment_distance_with_ratio,
    xy_segment_distance,
    xy_segment_parameter_clamped,
    xy_segment_projection_ratio,
    xy_segments_cross_strict,
    xy_segments_intersect,
    xyz_segment_intersection_point,
)
from .polygon_relations import (
    xy_closed_edges,
    xy_polygon_boundaries_intersect,
    xy_polygon_self_intersects,
    xy_point_in_polygon,
    xy_point_in_polygon_strict,
    xy_triangle_intersects_polygon,
    xy_triangle_polygon_intersection_kind,
)
from .polygon_boundary import (
    xyz_exterior_convex_hull,
    xyz_ordered_outer_boundary_from_segments,
    xyz_point,
    xyz_polygon_union_outer_boundary,
)

__all__ = [
    "clip_polyline_points_to_anchor_window",
    "clip_segment_to_anchor_box",
    "xy_distance",
    "xy_point",
    "xy_point_in_triangle_strict",
    "xy_polygon_signed_area",
    "xy_triangle_signed_area",
    "ear_clip_triangulation_indices",
    "triangulate_simple_polygon_points",
    "xy_triangle_quality_ratio",
    "dedupe_xy_payload_points",
    "intersect_payload_polygon_with_convex_polygon",
    "subtract_convex_polygon_from_payload_polygon",
    "xy_polygon_is_convex",
    "xy_point_segment_distance_with_ratio",
    "xy_point_on_segment",
    "xy_segment_distance",
    "xy_segment_parameter_clamped",
    "xy_segment_projection_ratio",
    "xy_segments_cross_strict",
    "xy_segments_intersect",
    "xyz_segment_intersection_point",
    "xy_closed_edges",
    "xy_polygon_boundaries_intersect",
    "xy_polygon_self_intersects",
    "xy_point_in_polygon",
    "xy_point_in_polygon_strict",
    "xy_triangle_intersects_polygon",
    "xy_triangle_polygon_intersection_kind",
    "xyz_exterior_convex_hull",
    "xyz_ordered_outer_boundary_from_segments",
    "xyz_point",
    "xyz_polygon_union_outer_boundary",
]

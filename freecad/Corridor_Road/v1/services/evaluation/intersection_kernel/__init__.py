"""Parametric intersection kernel (`V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md`).

Pure evaluation: no FreeCAD, Qt, objects, commands or ui imports.
"""

from .kernel import build_intersection_geometry, intersection_input_fingerprint
from .resolve import ResolvedIntersection, resolve_intersection
from .road_context import Crossing, PolylineRoad, PolylineRoadContext, RoadContext, SurfaceProfile

__all__ = [
    "Crossing",
    "PolylineRoad",
    "PolylineRoadContext",
    "ResolvedIntersection",
    "RoadContext",
    "SurfaceProfile",
    "build_intersection_geometry",
    "intersection_input_fingerprint",
    "resolve_intersection",
]

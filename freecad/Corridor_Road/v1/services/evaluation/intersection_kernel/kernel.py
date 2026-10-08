"""`build_intersection_geometry`: an `IntersectionSpec` and a `RoadContext` in, one result out."""

from __future__ import annotations

import hashlib

from ....models.result.intersection_geometry import IntersectionGeometryResult
from ....models.source.intersection_spec import IntersectionSpec
from .planar import build_planar_geometry
from .resolve import resolve_intersection
from .road_context import RoadContext
from .surface import build_surfaces
from .vertical import crown_lines


INTERSECTION_GEOMETRY_SCHEMA_VERSION = 1


def intersection_input_fingerprint(spec: IntersectionSpec, context: RoadContext) -> str:
    """Return a digest of everything the result depends on: the spec and the roads it names."""

    digest = hashlib.sha1()
    digest.update(repr(spec).encode("utf-8"))
    available = set(context.road_refs())
    for road_ref in spec.road_refs:
        if road_ref in available:
            for row in context.fingerprint_rows(road_ref):
                digest.update(b"\n")
                digest.update(row.encode("utf-8"))
    return digest.hexdigest()


def build_intersection_geometry(spec: IntersectionSpec, context: RoadContext) -> IntersectionGeometryResult:
    fingerprint = intersection_input_fingerprint(spec, context)
    resolved = resolve_intersection(spec, context)
    common = dict(
        schema_version=INTERSECTION_GEOMETRY_SCHEMA_VERSION,
        intersection_id=spec.intersection_id,
        kind=spec.kind,
        input_fingerprint=fingerprint,
        anchor_xy=resolved.anchor_xy,
        anchor_station_by_road=tuple(sorted(resolved.anchor_station_by_road.items())),
        resolved_values=tuple(resolved.resolved_values),
    )
    if resolved.blocked:
        return IntersectionGeometryResult(status="blocked", diagnostics=tuple(resolved.diagnostics), **common)
    if spec.kind == "roundabout":
        # plan phase R6; until then a roundabout resolves its legs but builds no geometry
        return IntersectionGeometryResult(status="not_implemented", diagnostics=tuple(resolved.diagnostics), **common)

    planar = build_planar_geometry(resolved, context)
    surface_diagnostics = []
    surfaces = None
    if planar.boundary_vertices:
        crowns = crown_lines(resolved, context, planar, surface_diagnostics)
        surfaces = build_surfaces(planar, crowns, context, spec.intersection_id)
        surface_diagnostics += surfaces.diagnostics
    diagnostics = tuple(resolved.diagnostics) + tuple(planar.diagnostics) + tuple(surface_diagnostics)
    if any(row.effect == "blocked" for row in diagnostics):
        status = "blocked"
    elif any(row.effect in {"partial", "fallback"} for row in diagnostics):
        status = "partial"
    else:
        status = "ready"
    return IntersectionGeometryResult(
        status=status,
        legs=tuple(planar.legs),
        corners=tuple(planar.corners),
        boundary_xyz=tuple(planar.boundary_xyz),
        boundary_area_m2=planar.boundary_area_m2,
        clip_spans=tuple(planar.clip_spans),
        supplemental_stations=tuple(planar.supplemental_stations),
        diagnostics=diagnostics,
        patch_vertices_xyz=tuple(surfaces.patch_vertices_xyz) if surfaces else (),
        patch_triangles=tuple(surfaces.patch_triangles) if surfaces else (),
        slope_vertices_xyz=tuple(surfaces.slope_vertices_xyz) if surfaces else (),
        slope_triangles=tuple(surfaces.slope_triangles) if surfaces else (),
        breaklines=tuple(surfaces.breaklines) if surfaces else (),
        quality_rows=tuple(surfaces.quality_rows) if surfaces else (),
        **common,
    )

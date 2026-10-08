"""Build Parametric's use of the parametric intersection kernel (plan phase R7a).

With the kernel engine selected the intersection is built in three steps, all from the kernel's one
result:

- Applied Sections gain a section at every leg mouth (`kernel_mouth_stations`), so the corridor
  surface ends exactly on the cut the kernel's boundary starts from;
- the corridor's design and slope surfaces lose the triangles of each road inside its clip span,
  between its two mouths (`clip_tin_surface_by_station_spans`); no polygon clip, no tolerance band;
- the kernel's patch and side slope become the intersection surfaces (`kernel_tin_surface`).

Units are metres throughout, as the Applied Sections and the corridor TINs carry them.
"""

from __future__ import annotations

from dataclasses import replace

from ...models.result.intersection_geometry import IntersectionGeometryResult
from ...models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex
from ..evaluation.intersection_kernel import build_intersection_geometry
from .intersection_kernel_context_service import road_context_from_models, spec_from_intersection_model


# two stations closer than this are the same station (the kernel's STATION_TOLERANCE_M)
_STATION_TOLERANCE_M = 1.0e-6


def intersection_geometry_from_models(intersection_model, alignment_models, applied_section_set, *, spec=None) -> IntersectionGeometryResult | None:
    """The kernel result for the document's intersection, or None when it has none.

    `spec` is the stored parametric spec (plan phase R7b); without one, the spec is read from the
    intersection rows.
    """

    spec = spec or spec_from_intersection_model(intersection_model)
    if spec is None:
        return None
    wanted = set(spec.road_refs)
    alignments = [model for model in list(alignment_models or []) if str(getattr(model, "alignment_id", "") or "") in wanted]
    return build_intersection_geometry(spec, road_context_from_models(alignments, applied_section_set))


def kernel_mouth_stations(result: IntersectionGeometryResult | None) -> dict[str, list[float]]:
    """The stations each road needs an Applied Section at: its leg mouths."""

    stations: dict[str, list[float]] = {}
    for road_ref, station in list(getattr(result, "supplemental_stations", ()) or ()):
        stations.setdefault(str(road_ref), []).append(float(station))
    return stations


def missing_mouth_stations(applied_section_set, stations_by_road: dict[str, list[float]]) -> dict[str, list[float]]:
    """The mouth stations the Applied Section set does not have a section at yet."""

    present: dict[str, list[float]] = {}
    for section in list(getattr(applied_section_set, "sections", []) or []):
        present.setdefault(str(getattr(section, "alignment_id", "") or ""), []).append(float(getattr(section, "station", 0.0) or 0.0))
    missing: dict[str, list[float]] = {}
    for road_ref, stations in stations_by_road.items():
        for station in stations:
            if not any(abs(station - value) <= _STATION_TOLERANCE_M for value in present.get(road_ref, [])):
                missing.setdefault(road_ref, []).append(station)
    return missing


def clip_tin_surface_by_station_spans(surface: TINSurface | None, applied_section_set, clip_spans) -> TINSurface | None:
    """Drop the corridor triangles of each road that lie wholly inside its clip span.

    A corridor vertex names the Applied Section it comes from (`source_point_ref` starts with the
    section id), so each triangle knows its road and stations. A triangle goes when all three
    vertices belong to one road and lie within that road's span; a triangle reaching beyond a
    mouth stays, and since the mouth is an Applied Section the corridor's edge is the mouth cut.
    """

    if surface is None or not clip_spans:
        return surface
    section_by_id = {
        str(getattr(section, "applied_section_id", "") or ""): (str(getattr(section, "alignment_id", "") or ""), float(getattr(section, "station", 0.0) or 0.0))
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    spans: dict[str, list[tuple[float, float]]] = {}
    for road_ref, start, end in clip_spans:
        spans.setdefault(str(road_ref), []).append((float(start), float(end)))
    vertex_place = {vertex.vertex_id: _section_of(vertex.source_point_ref, section_by_id) for vertex in surface.vertex_rows}
    kept: list[TINTriangle] = []
    removed = 0
    for triangle in surface.triangle_rows:
        places = [vertex_place.get(ref) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if _inside_span(places, spans):
            removed += 1
            continue
        kept.append(triangle)
    used = {ref for triangle in kept for ref in (triangle.v1, triangle.v2, triangle.v3)}
    quality = list(surface.quality_rows) + [
        TINQualityRow(f"{surface.surface_id}:intersection-kernel-clip", "intersection_kernel_clip_removed_triangle_count", float(removed), "count")
    ]
    return replace(
        surface,
        vertex_rows=[vertex for vertex in surface.vertex_rows if vertex.vertex_id in used],
        triangle_rows=kept,
        quality_rows=quality,
    )


def kernel_tin_surface(result: IntersectionGeometryResult, *, part: str, surface_id: str, project_id: str) -> TINSurface:
    """The kernel's patch (`part="patch"`) or side slope (`part="slope"`) as a TIN surface."""

    if part == "patch":
        points, triangles, kind = result.patch_vertices_xyz, result.patch_triangles, "intersection_surface"
    else:
        points, triangles, kind = result.slope_vertices_xyz, result.slope_triangles, "intersection_slope_face_surface"
    prefix = f"{result.intersection_id}:{part}"
    vertices = [TINVertex(f"{prefix}:v{index}", float(x), float(y), float(z), source_point_ref=prefix) for index, (x, y, z) in enumerate(points)]
    rows = [
        TINTriangle(f"{prefix}:t{index}", f"{prefix}:v{a}", f"{prefix}:v{b}", f"{prefix}:v{c}", triangle_kind=f"intersection_kernel_{part}")
        for index, (a, b, c) in enumerate(triangles)
    ]
    quality = [
        TINQualityRow(f"{prefix}:q:{name}", name, float(value), "count" if name.endswith("count") else "ratio")
        for name, value in result.quality_rows
        if name.startswith(part)
    ]
    return TINSurface(
        schema_version=1,
        project_id=project_id,
        label=f"Intersection {part}",
        source_refs=[result.intersection_id, f"intersection-kernel:{result.input_fingerprint}"],
        surface_id=surface_id,
        surface_kind=kind,
        vertex_rows=vertices,
        triangle_rows=rows,
        quality_rows=quality,
        provenance_rows=[TINProvenanceRow(f"{prefix}:provenance", "intersection_kernel", result.input_fingerprint, f"status={result.status}")],
    )


def _section_of(source_point_ref: str, section_by_id: dict[str, tuple[str, float]]):
    parts = str(source_point_ref or "").split(":")
    for size in range(len(parts), 0, -1):
        place = section_by_id.get(":".join(parts[:size]))
        if place is not None:
            return place
    return None


def _inside_span(places, spans) -> bool:
    if any(place is None for place in places):
        return False
    roads = {place[0] for place in places}
    if len(roads) != 1:
        return False
    (road,) = roads
    for start, end in spans.get(road, []):
        if all(start - _STATION_TOLERANCE_M <= place[1] <= end + _STATION_TOLERANCE_M for place in places):
            return True
    return False

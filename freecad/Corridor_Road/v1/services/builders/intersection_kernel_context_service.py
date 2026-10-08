"""Inputs of the parametric intersection kernel, built from evaluated models (plan phase R3).

`road_context_from_models` turns Alignment models and the Applied Section set into the kernel's
`RoadContext`. The pavement half width comes only from the Applied Sections (decision D1 of
`V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md`): `surface_left_width` and `surface_right_width`
of each section of that Alignment, by station. Stations and coordinates are metres, as the
Alignment's sampled geometry and the Applied Sections already carry them.

`spec_from_intersection_model` reads an `IntersectionSpec` out of the current row-based
`IntersectionModel`. It exists for shadow mode only and goes away with the switch (phase R7).
"""

from __future__ import annotations

import math

from ...models.source.intersection_spec import AnchorSpec, IntersectionSpec
from ..evaluation.intersection_evaluation_service import IntersectionEvaluationService
from ..evaluation.intersection_kernel import build_intersection_geometry
from ..evaluation.intersection_kernel.road_context import STATION_TOLERANCE_M, PolylineRoad, PolylineRoadContext
from ..evaluation.intersection_kernel_shadow_service import (
    IntersectionKernelShadowComparison,
    IntersectionKernelShadowService,
)


_KIND_BY_MODEL_KIND = {
    "t_intersection": "t",
    "cross_intersection": "cross",
    "roundabout": "roundabout",
}


def road_context_from_models(alignment_models, applied_section_set=None) -> PolylineRoadContext:
    sections_by_alignment: dict[str, list[object]] = {}
    for section in list(getattr(applied_section_set, "sections", []) or []):
        alignment_id = str(getattr(section, "alignment_id", "") or "")
        if alignment_id:
            sections_by_alignment.setdefault(alignment_id, []).append(section)
    roads: dict[str, PolylineRoad] = {}
    for model in list(alignment_models or []):
        alignment_id = str(getattr(model, "alignment_id", "") or "")
        if not alignment_id or alignment_id in roads:
            continue
        stations, xy = _alignment_polyline(model)
        if len(stations) < 2:
            continue
        sections = sorted(sections_by_alignment.get(alignment_id, []), key=_section_station)
        widths, grades = [], []
        for section in sections:
            station = _section_station(section)
            if widths and abs(station - widths[-1][0]) <= STATION_TOLERANCE_M:
                continue
            left = abs(float(getattr(section, "surface_left_width", 0.0) or 0.0))
            right = abs(float(getattr(section, "surface_right_width", 0.0) or 0.0))
            if left > 0.0 and right > 0.0:
                widths.append((station, left, right))
            frame = getattr(section, "frame", None)
            if frame is not None:
                grades.append((station, float(getattr(frame, "z", 0.0) or 0.0)))
        roads[alignment_id] = PolylineRoad(
            alignment_id,
            tuple(stations),
            tuple(xy),
            tuple(widths),
            tuple(grades),
            width_source=str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
        )
    return PolylineRoadContext(roads)


def spec_from_intersection_model(intersection_model, intersection_id: str = "") -> IntersectionSpec | None:
    rows = list(getattr(intersection_model, "intersection_rows", []) or [])
    row = next((r for r in rows if not intersection_id or str(getattr(r, "intersection_id", "") or "") == intersection_id), None)
    if row is None:
        return None
    row_id = str(getattr(row, "intersection_id", "") or "")
    kind = _KIND_BY_MODEL_KIND.get(str(getattr(row, "intersection_kind", "") or ""), str(getattr(row, "intersection_kind", "") or ""))
    primary = str(getattr(row, "primary_alignment_ref", "") or "")
    roads = tuple(ref for ref in (primary, *[str(r) for r in list(getattr(row, "secondary_alignment_refs", []) or [])]) if ref)
    anchor = next(
        (a for a in list(getattr(intersection_model, "anchor_rows", []) or []) if str(getattr(a, "intersection_id", "") or "") == row_id),
        None,
    )
    if anchor is not None and str(getattr(anchor, "primary_alignment_ref", "") or "") == primary:
        stations = [(primary, float(getattr(anchor, "primary_station", 0.0) or 0.0))]
        stations += [(str(ref), float(value)) for ref, value in dict(getattr(anchor, "secondary_station_refs", {}) or {}).items()]
        anchor_spec = AnchorSpec("manual", tuple(stations))
    else:
        anchor_spec = AnchorSpec()
    radius = next(
        (
            float(getattr(p, "radius", 0.0) or 0.0)
            for p in list(getattr(intersection_model, "curb_return_policy_rows", []) or [])
            if str(getattr(p, "intersection_id", "") or "") == row_id
            and str(getattr(p, "status", "") or "active") == "active"
            and float(getattr(p, "radius", 0.0) or 0.0) > 0.0
        ),
        None,
    )
    grading = next(
        (
            str(getattr(p, "mode", "") or "")
            for p in list(getattr(intersection_model, "grading_policy_rows", []) or [])
            if str(getattr(p, "intersection_id", "") or "") == row_id and str(getattr(p, "mode", "") or "")
        ),
        None,
    )
    return IntersectionSpec(row_id, kind, roads, anchor=anchor_spec, corner_radius_m=radius, grading_mode=grading)


def intersection_kernel_shadow_comparison(
    intersection_model,
    alignment_models,
    applied_section_set,
    boundary_segment_result=None,
) -> IntersectionKernelShadowComparison:
    """Run the kernel on the document's current inputs and compare it with the current pipeline.

    Shadow mode (plan section 6). The evaluation chain's outer boundary loop is evaluated here
    for the envelope comparison; nothing it produces is kept.
    """

    spec = spec_from_intersection_model(intersection_model)
    if spec is None:
        return IntersectionKernelShadowComparison("skipped", rows=("reason|the Intersection model has no intersection row",))
    context = road_context_from_models(alignment_models, applied_section_set)
    kernel_result = build_intersection_geometry(spec, context)
    boundary_loop_result = None
    if kernel_result.status not in {"blocked", "not_implemented"}:
        service = IntersectionEvaluationService()
        edge_network = service.evaluate_edge_network(intersection_model, intersection_id=spec.intersection_id)
        surface_zones = service.evaluate_surface_zones(intersection_model, edge_network, intersection_id=spec.intersection_id)
        boundary_loop_result = service.evaluate_boundary_loops(intersection_model, surface_zones, edge_network, intersection_id=spec.intersection_id)
    return IntersectionKernelShadowService().compare(
        kernel_result,
        boundary_segment_result=boundary_segment_result,
        boundary_loop_result=boundary_loop_result,
    )


def _alignment_polyline(model) -> tuple[list[float], list[tuple[float, float]]]:
    """The Alignment's sampled XY with the station of each point, element by element.

    Inside an element the station runs in proportion to the sampled length, as the Alignment
    detection service maps it. Repeated points at element joints are kept once.
    """

    stations: list[float] = []
    xy: list[tuple[float, float]] = []
    for element in list(getattr(model, "geometry_sequence", []) or []):
        payload = dict(getattr(element, "geometry_payload", {}) or {})
        points = list(zip(_floats(payload.get("x_values", [])), _floats(payload.get("y_values", []))))
        if len(points) < 2:
            continue
        lengths = [0.0]
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            lengths.append(lengths[-1] + math.hypot(x1 - x0, y1 - y0))
        start, end = float(element.station_start), float(element.station_end)
        total = lengths[-1]
        for index, point in enumerate(points):
            ratio = lengths[index] / total if total > 1.0e-12 else index / (len(points) - 1)
            station = start + (end - start) * ratio
            if stations and (station <= stations[-1] + STATION_TOLERANCE_M or math.hypot(point[0] - xy[-1][0], point[1] - xy[-1][1]) <= 1.0e-12):
                continue
            stations.append(station)
            xy.append(point)
    return stations, xy


def _floats(values) -> list[float]:
    rows: list[float] = []
    for value in list(values or []):
        try:
            rows.append(float(value))
        except (TypeError, ValueError):
            continue
    return rows


def _section_station(section) -> float:
    frame = getattr(section, "frame", None)
    value = getattr(frame, "station", None) if frame is not None else None
    if value is None:
        value = getattr(section, "station", 0.0)
    return float(value or 0.0)

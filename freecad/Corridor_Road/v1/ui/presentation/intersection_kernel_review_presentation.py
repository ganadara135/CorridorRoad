"""Build Parametric review rows of the parametric intersection kernel's result (plan phase R7c-2).

One table, the viewer's Intersections tab: the intersection, each leg with its mouth, each corner
with its radius and where the radius came from, the boundary, the two surfaces, the clip spans, the
drainage candidates, every resolved value with its origin, and the diagnostics. Each row also knows
the linework to highlight for it (`intersection_kernel_row_polylines`). Widget-free and FreeCAD-free.
"""

from __future__ import annotations

import math


_STATUS = {"ready": "ready", "partial": "warning", "blocked": "error", "not_implemented": "missing"}
_SEVERITY = {"error": "error", "warning": "warning", "info": "ready"}


def _row(family: str, row_id: str, status: str, *, role: str = "", source_refs: str = "", notes: str = "", focus_object: str = "", source_diagnostics: str = "") -> dict[str, object]:
    return {
        "contract_family": family,
        "status": status,
        "source_status": "spec",
        "output_path": "intersection_kernel",
        "row_id": row_id,
        "role": role,
        "source_refs": source_refs,
        "boundary_refs": "",
        "source_diagnostics": source_diagnostics,
        "focus_object": focus_object,
        "notes": notes,
    }


def intersection_kernel_review_rows(result) -> list[dict[str, object]]:
    """The review rows of one kernel result; one `missing` row when there is none."""

    if result is None:
        return [_row("intersection", "", "missing", notes="No Intersection source in this document, or no Applied Sections to build it on.")]
    status = _STATUS.get(result.status, "warning")
    quality = dict(result.quality_rows)
    origins = {(v.name, v.subject): v.origin for v in result.resolved_values}
    rows = [
        _row(
            "intersection", result.intersection_id, status, role=result.kind,
            notes=f"kernel status {result.status}; boundary area {result.boundary_area_m2:.3f} m2; fingerprint {result.input_fingerprint[:12]}",
            focus_object="V1CorridorIntersectionSurfacePreview",
        )
    ]
    for leg in result.legs:
        if not leg.enabled:
            rows.append(_row("leg", leg.leg_id, "ready", role=f"{leg.side}, closed", source_refs=leg.road_ref, notes="closed"))
            continue
        if leg.mouth_station is None:
            rows.append(_row("leg", leg.leg_id, "error", role=leg.side, source_refs=leg.road_ref, notes="no mouth: see the diagnostics"))
            continue
        width = math.dist(leg.mouth_left_xyz[:2], leg.mouth_right_xyz[:2]) if leg.mouth_left_xyz and leg.mouth_right_xyz else 0.0
        rows.append(
            _row(
                "leg", leg.leg_id, "ready", role=leg.side, source_refs=leg.road_ref,
                notes=f"mouth station {leg.mouth_station:.3f}; mouth width {width:.3f} m; bearing {math.degrees(leg.bearing_rad):.1f} deg",
            )
        )
    for corner in result.corners:
        solved = bool(corner.arc_xyz) or corner.treatment == "none"
        if corner.treatment == "ring":
            radii = [
                f"{side} flare {value.value:.3f} m ({value.origin})"
                for side in ("from", "to")
                for value in result.resolved_values
                if value.name == "flare_radius_m" and value.subject == f"{corner.corner_key}:{side}"
            ]
            notes = "; ".join(radii)
        elif corner.treatment == "fillet":
            notes = f"radius {corner.radius_m:.3f} m ({origins.get(('corner_radius_m', corner.corner_key), '-')})"
            if corner.from_tangent_station is not None:
                notes += f"; tangent stations {corner.from_tangent_station:.3f} / {corner.to_tangent_station:.3f}"
        else:
            notes = "the road edge runs straight through"
        rows.append(_row("corner", corner.corner_key, "ready" if solved else "error", role=corner.treatment, notes=notes))
    if result.boundary_xyz:
        rows.append(
            _row(
                "boundary", result.intersection_id, status, role="outer",
                notes=f"{len(result.boundary_xyz)} vertices; area {result.boundary_area_m2:.3f} m2; {len(result.boundary_holes_xyz)} island(s)",
            )
        )
    for part, name in (("patch", "V1CorridorIntersectionSurfacePreview"), ("slope", "V1CorridorIntersectionSlopeFaceSurfacePreview")):
        if f"{part}_triangle_count" not in quality:
            continue
        skinny = int(quality.get(f"{part}_triangle_skinny_count", 0))
        rows.append(
            _row(
                "surface", f"{result.intersection_id}:{part}", "ready" if skinny == 0 else "warning", role=part,
                notes=(
                    f"{int(quality[f'{part}_triangle_count'])} triangles; minimum quality "
                    f"{quality.get(f'{part}_triangle_min_quality', 0.0):.3f}; skinny {skinny}"
                ),
                focus_object=name,
            )
        )
    for road_ref, start, end in result.clip_spans:
        rows.append(_row("corridor_clip", road_ref, "ready", role="clip span", source_refs=road_ref, notes=f"stations {start:.3f} to {end:.3f}"))
    for index, candidate in enumerate(result.drainage_candidates, start=1):
        rows.append(
            _row(
                "drainage", f"{result.intersection_id}:low-point:{index}", "ready", role=candidate.kind, source_refs=candidate.road_ref,
                notes=f"z {candidate.z:.3f}; nearest station {candidate.station:.3f}; at ({candidate.x:.3f}, {candidate.y:.3f})",
            )
        )
    for value in result.resolved_values:
        shown = f"{value.value:.3f}" if isinstance(value.value, float) else str(value.value)
        rows.append(_row("value", f"{value.name}:{value.subject}", "ready", role=value.origin, notes=f"{value.name} = {shown}"))
    for diagnostic in result.diagnostics:
        rows.append(
            _row(
                "diagnostic", diagnostic.code, _SEVERITY.get(diagnostic.severity, "warning"), role=diagnostic.effect,
                source_refs=diagnostic.subject, notes=diagnostic.inspect, source_diagnostics=diagnostic.as_text(),
            )
        )
    return rows


def intersection_kernel_row_polylines(result, row: dict[str, object]) -> list[list[tuple[float, float, float]]]:
    """The linework that shows one review row in 3D, or nothing (the row then focuses its object)."""

    if result is None:
        return []
    family = str(row.get("contract_family", "") or "")
    row_id = str(row.get("row_id", "") or "")
    if family == "leg":
        for leg in result.legs:
            if leg.leg_id == row_id and leg.mouth_left_xyz and leg.mouth_right_xyz:
                return [[leg.mouth_right_xyz, leg.mouth_left_xyz]]
    if family == "corner":
        for corner in result.corners:
            if corner.corner_key == row_id and corner.arc_xyz:
                return [list(corner.arc_xyz)]
    if family == "boundary":
        lines = [list(result.boundary_xyz) + [result.boundary_xyz[0]]] if result.boundary_xyz else []
        lines += [list(hole) + [hole[0]] for hole in result.boundary_holes_xyz]
        return lines
    if family == "drainage":
        for index, candidate in enumerate(result.drainage_candidates, start=1):
            if row_id.endswith(f":low-point:{index}"):
                x, y, z = candidate.x, candidate.y, candidate.z
                # a 1 m cross on the low point
                return [[(x - 0.5, y, z), (x + 0.5, y, z)], [(x, y - 0.5, z), (x, y + 0.5, z)]]
    return []

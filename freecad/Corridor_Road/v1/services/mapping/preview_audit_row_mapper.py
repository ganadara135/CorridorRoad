"""Serialize result models into the audit row strings stored on preview objects.

These rows are a normalized contract: the builders and the Build Parametric
command write them onto preview object properties, and the presentation parsers
read them back. They lived in three modules as identical copies until this
module became their single owner.
"""

from __future__ import annotations

from ...models.result.intersection_shared_boundary_graph import IntersectionSharedBoundaryGraphResult
from ..evaluation.intersection_shared_boundary_graph_evaluation_service import (
    intersection_shared_boundary_graph_audit,
)


def audit_field(value: object) -> str:
    return str(value or "").replace("|", "/").replace(";;", ";").strip()


def shared_breakline_segment_rows(shared_result, refs: list[str] | None = None) -> list[str]:
    """Serialize breakline segment geometry for presentation-only 3D audit highlights."""

    if shared_result is None:
        return []
    wanted = {str(ref or "") for ref in list(refs or []) if str(ref or "")}
    point_by_ref: dict[str, list[object]] = {}
    for point in list(getattr(shared_result, "point_rows", []) or []):
        ref = str(getattr(point, "breakline_ref", "") or "")
        if not ref:
            continue
        point_by_ref.setdefault(ref, []).append(point)
    rows: list[str] = []
    for breakline in list(getattr(shared_result, "breakline_rows", []) or []):
        breakline_id = str(getattr(breakline, "breakline_id", "") or "")
        if not breakline_id or (wanted and breakline_id not in wanted):
            continue
        points = sorted(point_by_ref.get(breakline_id, []), key=lambda point: int(getattr(point, "sequence", 0) or 0))
        if len(points) < 2:
            continue
        role = str(getattr(breakline, "breakline_role", "") or "")
        material = str(getattr(breakline, "material_role", "") or "") or role
        status = str(getattr(breakline, "source_status", "") or "")
        consumer_refs = ",".join(str(value or "") for value in tuple(getattr(breakline, "consumer_refs", ()) or ()) if str(value or ""))
        for index, (start, end) in enumerate(zip(points[:-1], points[1:])):
            try:
                values = [
                    breakline_id,
                    role,
                    status,
                    str(index),
                    f"{float(getattr(start, 'x', 0.0) or 0.0):.9g}",
                    f"{float(getattr(start, 'y', 0.0) or 0.0):.9g}",
                    f"{float(getattr(start, 'z', 0.0) or 0.0):.9g}",
                    f"{float(getattr(end, 'x', 0.0) or 0.0):.9g}",
                    f"{float(getattr(end, 'y', 0.0) or 0.0):.9g}",
                    f"{float(getattr(end, 'z', 0.0) or 0.0):.9g}",
                    material,
                ]
                if consumer_refs:
                    values.append(consumer_refs)
                rows.append("|".join(value.replace("|", "_") for value in values))
            except Exception:
                continue
    return rows


def intersection_shared_boundary_graph_audit_rows(graph_result: IntersectionSharedBoundaryGraphResult | None) -> list[str]:
    if graph_result is None:
        return []
    rows: list[str] = []
    graph_audit = intersection_shared_boundary_graph_audit(graph_result)
    for edge in list(getattr(graph_result, "edge_rows", []) or []):
        diagnostics = ",".join(str(value or "") for value in tuple(getattr(edge, "diagnostics", ()) or ()) if str(value or ""))
        consumers = ",".join(str(value or "") for value in tuple(getattr(edge, "consumer_refs", ()) or ()) if str(value or ""))
        source_refs = ",".join(str(value or "") for value in tuple(getattr(edge, "source_refs", ()) or ()) if str(value or ""))
        rows.append(
            "|".join(
                [
                    "edge",
                    audit_field(str(getattr(edge, "edge_id", "") or "")),
                    audit_field(str(getattr(edge, "edge_role", "") or "")),
                    audit_field(str(getattr(edge, "from_node_ref", "") or "")),
                    audit_field(str(getattr(edge, "to_node_ref", "") or "")),
                    audit_field(consumers),
                    audit_field(diagnostics),
                    audit_field(source_refs),
                ]
            )
        )
    for cell in list(getattr(graph_result, "cell_rows", []) or []):
        diagnostics = ",".join(str(value or "") for value in tuple(getattr(cell, "diagnostics", ()) or ()) if str(value or ""))
        boundary_refs = ",".join(str(value or "") for value in tuple(getattr(cell, "boundary_edge_refs", ()) or ()) if str(value or ""))
        rows.append(
            "|".join(
                [
                    "cell",
                    audit_field(str(getattr(cell, "cell_id", "") or "")),
                    audit_field(str(getattr(cell, "cell_role", "") or "")),
                    "1" if bool(getattr(cell, "closed", False)) else "0",
                    audit_field(str(getattr(cell, "owner_surface_ref", "") or "")),
                    audit_field(boundary_refs),
                    audit_field(diagnostics),
                    "",
                ]
            )
        )
    for diagnostic in list(graph_audit.get("diagnostic_rows", []) or []):
        rows.append("|".join(["graph", audit_field(str(diagnostic or "")), "", "", "", "", ""]))
    return rows


def intersection_shared_boundary_graph_segment_rows(graph_result: IntersectionSharedBoundaryGraphResult | None) -> list[str]:
    if graph_result is None:
        return []
    node_by_id = {
        str(getattr(node, "node_id", "") or ""): node
        for node in list(getattr(graph_result, "node_rows", []) or [])
        if str(getattr(node, "node_id", "") or "")
    }
    rows: list[str] = []
    for edge in list(getattr(graph_result, "edge_rows", []) or []):
        from_ref = str(getattr(edge, "from_node_ref", "") or "")
        to_ref = str(getattr(edge, "to_node_ref", "") or "")
        from_node = node_by_id.get(from_ref)
        to_node = node_by_id.get(to_ref)
        if from_node is None or to_node is None:
            continue
        consumers = ",".join(str(value or "") for value in tuple(getattr(edge, "consumer_refs", ()) or ()) if str(value or ""))
        rows.append(
            "|".join(
                [
                    audit_field(str(getattr(edge, "edge_id", "") or "")),
                    audit_field(str(getattr(edge, "edge_role", "") or "")),
                    audit_field(from_ref),
                    audit_field(to_ref),
                    f"{float(getattr(from_node, 'x', 0.0) or 0.0):.9f}",
                    f"{float(getattr(from_node, 'y', 0.0) or 0.0):.9f}",
                    f"{float(getattr(from_node, 'z', 0.0) or 0.0):.9f}",
                    f"{float(getattr(to_node, 'x', 0.0) or 0.0):.9f}",
                    f"{float(getattr(to_node, 'y', 0.0) or 0.0):.9f}",
                    f"{float(getattr(to_node, 'z', 0.0) or 0.0):.9f}",
                    audit_field(consumers),
                ]
            )
        )
    return rows


__all__ = [
    "audit_field",
    "shared_breakline_segment_rows",
    "intersection_shared_boundary_graph_audit_rows",
    "intersection_shared_boundary_graph_segment_rows",
]

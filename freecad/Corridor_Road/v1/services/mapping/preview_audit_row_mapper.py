"""Serialize result models into the audit row strings stored on preview objects.

These rows are a normalized contract: the builders and the Build Parametric
command write them onto preview object properties, and the presentation parsers
read them back. They lived in three modules as identical copies until this
module became their single owner.
"""

from __future__ import annotations


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


__all__ = [
    "shared_breakline_segment_rows",
]

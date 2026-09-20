"""Pure readers and formatters over v1 model rows.

Applied Section fields, the reference-list formatters that describe them, and
the intersection row lookup. They hold no document access and no rules, so the
commands, the services, and the presentation layer may all read through them.
"""

from __future__ import annotations


def section_station(section) -> float:
    frame = getattr(section, "frame", None)
    try:
        return float(getattr(frame, "station", getattr(section, "station", 0.0)) or 0.0)
    except Exception:
        try:
            return float(getattr(section, "station", 0.0) or 0.0)
        except Exception:
            return 0.0


def section_region_id(section) -> str:
    return str(getattr(section, "region_id", "") or "(unassigned)")


def section_structure_values(sections: list[object]) -> list[str]:
    values: list[str] = []
    for section in list(sections or []):
        values.extend(
            str(value or "").strip()
            for value in list(getattr(section, "active_structure_ids", []) or [])
            if str(value or "").strip()
        )
    return values


def section_float_attr(obj, attr: str) -> float:
    try:
        return float(getattr(obj, attr, 0.0) or 0.0)
    except Exception:
        return 0.0


def surface_point_role_counts(section) -> dict[str, int]:
    roles = {"fg_surface", "subgrade_surface", "ditch_surface", "side_slope_surface", "bench_surface", "daylight_marker"}
    counts = {role: 0 for role in roles}
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role in counts:
            counts[role] += 1
    return {role: count for role, count in counts.items() if count}


def role_count_summary(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{role}:{count}" for role, count in sorted(counts.items()))


def unique_join(values: list[str], *, max_items: int = 3) -> str:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    if not output:
        return ""
    clipped = output[: max(1, int(max_items))]
    if len(output) > len(clipped):
        clipped.append(f"+{len(output) - len(clipped)}")
    return ", ".join(clipped)


def unique_refs(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def intersection_row_by_id(intersection_model, intersection_id: str):
    target = str(intersection_id or "").strip()
    if intersection_model is None or not target:
        return None
    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        if str(getattr(row, "intersection_id", "") or "").strip() == target:
            return row
    return None


__all__ = [
    "intersection_row_by_id",
    "role_count_summary",
    "section_float_attr",
    "section_region_id",
    "section_station",
    "section_structure_values",
    "surface_point_role_counts",
    "unique_join",
    "unique_refs",
]

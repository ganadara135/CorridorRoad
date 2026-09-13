"""Presentation rows for the guided review steps split by Subassembly kind."""

from __future__ import annotations

from .review_text import format_count_summary as _format_count_summary


SUBASSEMBLY_GUIDED_REVIEW_KIND_ORDER = (
    "lane",
    "shoulder",
    "ditch",
    "lined_ditch",
    "gutter",
    "curb",
    "side_slope",
    "median",
    "sidewalk",
    "bike_lane",
    "green_strip",
    "barrier",
    "pavement_layer",
    "subbase",
    "structure_interface",
    "intersection_transition",
    "curb_return_transition",
    "custom",
)


def subassembly_kind_guided_review_rows(sections) -> list[dict[str, object]]:
    """Return guided-review rows split by evaluated Subassembly kind."""

    summaries: dict[str, dict[str, object]] = {}
    for section in sections:
        rows = {
            str(getattr(row, "subassembly_id", "") or "").strip(): row
            for row in list(getattr(section, "subassembly_rows", []) or [])
            if str(getattr(row, "subassembly_id", "") or "").strip()
        }
        link_rows = list(getattr(section, "subassembly_link_rows", []) or [])
        shape_rows = list(getattr(section, "subassembly_shape_rows", []) or [])
        for subassembly_id, subassembly in rows.items():
            kind = str(getattr(subassembly, "kind", "") or "unknown").strip() or "unknown"
            summary = summaries.setdefault(
                kind,
                {
                    "kind": kind,
                    "section_count": 0,
                    "subassembly_count": 0,
                    "point_count": 0,
                    "link_count": 0,
                    "shape_count": 0,
                    "surface_roles": {},
                    "preset_statuses": {},
                    "preset_refs": [],
                    "diagnostic_count": 0,
                },
            )
            summary["section_count"] = int(summary.get("section_count", 0) or 0) + 1
            summary["subassembly_count"] = int(summary.get("subassembly_count", 0) or 0) + 1
            preset_ref = str(getattr(subassembly, "preset_ref", "") or "").strip()
            preset_status = str(getattr(subassembly, "preset_status", "") or "").strip()
            if not preset_status:
                preset_status = "linked" if preset_ref else "snapshot"
            preset_statuses = summary.setdefault("preset_statuses", {})
            preset_statuses[preset_status] = int(preset_statuses.get(preset_status, 0) or 0) + 1
            if preset_ref:
                preset_refs = summary.setdefault("preset_refs", [])
                if preset_ref not in preset_refs:
                    preset_refs.append(preset_ref)
            summary["diagnostic_count"] = int(summary.get("diagnostic_count", 0) or 0) + len(list(getattr(subassembly, "diagnostics", []) or []))
            point_count = 0
            for point in list(getattr(section, "subassembly_point_rows", []) or []):
                if str(getattr(point, "subassembly_ref", "") or "").strip() == subassembly_id:
                    point_count += 1
                    summary["diagnostic_count"] = int(summary.get("diagnostic_count", 0) or 0) + len(list(getattr(point, "diagnostics", []) or []))
            summary["point_count"] = int(summary.get("point_count", 0) or 0) + point_count
            for link in link_rows:
                if str(getattr(link, "subassembly_ref", "") or "").strip() != subassembly_id:
                    continue
                summary["link_count"] = int(summary.get("link_count", 0) or 0) + 1
                role = str(getattr(link, "surface_role", "") or "unassigned").strip() or "unassigned"
                role_counts = summary.setdefault("surface_roles", {})
                role_counts[role] = int(role_counts.get(role, 0) or 0) + 1
                summary["diagnostic_count"] = int(summary.get("diagnostic_count", 0) or 0) + len(list(getattr(link, "diagnostics", []) or []))
            for shape in shape_rows:
                if str(getattr(shape, "subassembly_ref", "") or "").strip() == subassembly_id:
                    summary["shape_count"] = int(summary.get("shape_count", 0) or 0) + 1

    rows: list[dict[str, object]] = []
    ordered_kinds = [
        kind
        for kind in SUBASSEMBLY_GUIDED_REVIEW_KIND_ORDER
        if kind in summaries
    ] + sorted(kind for kind in summaries if kind not in SUBASSEMBLY_GUIDED_REVIEW_KIND_ORDER)
    for kind in ordered_kinds:
        # Side Slope is reviewed through its accepted daylight/intersection result,
        # not through partial Applied Section point rows.
        if kind == "side_slope":
            continue
        summary = summaries[kind]
        roles = dict(summary.get("surface_roles", {}) or {})
        preset_statuses = dict(summary.get("preset_statuses", {}) or {})
        preset_refs = list(summary.get("preset_refs", []) or [])
        status = "ready"
        warnings: list[str] = []
        if int(summary.get("link_count", 0) or 0) <= 0:
            status = "warning"
            warnings.append("no evaluated links")
        if kind in {"ditch", "lined_ditch", "gutter"} and int(roles.get("drainage_surface", 0) or 0) <= 0:
            status = "warning"
            warnings.append("no drainage_surface links")
        if int(summary.get("diagnostic_count", 0) or 0) > 0:
            status = "warning"
            warnings.append(f"diagnostics={int(summary.get('diagnostic_count', 0) or 0)}")
        notes = (
            f"sections={int(summary.get('section_count', 0) or 0)}, "
            f"points={int(summary.get('point_count', 0) or 0)}, "
            f"links={int(summary.get('link_count', 0) or 0)}, "
            f"shapes={int(summary.get('shape_count', 0) or 0)}; "
            f"roles={_format_count_summary(roles)}; "
            f"presets={_format_count_summary(preset_statuses)}"
        )
        if preset_refs:
            notes = f"{notes}; preset_refs={_format_count_summary({ref: 1 for ref in preset_refs})}"
        if warnings:
            notes = f"{notes}; " + "; ".join(warnings)
        rows.append(
            {
                "step_id": f"subassembly_kind:{kind}",
                "title": f"3. {_subassembly_kind_display_name(kind)}",
                "roles": ["centerline", "design", "daylight", "drainage"],
                "status": status,
                "focus": f"{_subassembly_kind_display_name(kind)} Subassembly",
                "notes": notes,
                "preset_statuses": preset_statuses,
                "preset_refs": preset_refs,
            }
        )
    return rows


def _subassembly_kind_display_name(kind: str) -> str:
    text = str(kind or "unknown").strip() or "unknown"
    return " ".join(part.capitalize() for part in text.replace("-", "_").split("_") if part)

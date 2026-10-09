"""Presentation mapping for typed shared-breakline audit results."""

from __future__ import annotations


from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SharedBreaklineAuditPresentation:
    status: str
    missing_consumer_count: int
    mismatch_count: int
    geometry_match_count: int
    geometry_mismatch_count: int
    mesh_match_count: int
    mesh_mismatch_count: int
    reversed_edge_count: int
    solid_readiness_status: str
    solid_open_end_count: int
    solid_duplicate_edge_count: int
    solid_reversed_edge_count: int
    solid_non_manifold_node_count: int
    solid_readiness_notes: str
    notes: str
    summary: str
    note_rows: tuple[str, ...]


class SharedBreaklineAuditPresentationMapper:
    """Map typed or compatibility audit results into stable display fields."""

    def map(self, audit: object) -> SharedBreaklineAuditPresentation:
        status = str(_value(audit, "status", "") or "")
        geometry_match = int(_value(audit, "geometry_match_count", 0) or 0)
        geometry_mismatch = int(
            _value(audit, "geometry_mismatch_count", 0) or 0
        )
        mesh_match = int(_value(audit, "mesh_match_count", 0) or 0)
        mesh_mismatch = int(_value(audit, "mesh_mismatch_count", 0) or 0)
        missing = int(_value(audit, "missing_consumer_count", 0) or 0)
        mismatch = int(_value(audit, "mismatch_count", 0) or 0)
        reversed_count = int(_value(audit, "reversed_edge_count", 0) or 0)
        notes = str(_value(audit, "notes", "") or "")
        summary = (
            f"audit={status or 'unknown'} "
            f"geometry={geometry_match}/{geometry_match + geometry_mismatch} "
            f"mesh={mesh_match}/{mesh_match + mesh_mismatch} "
            f"missing={missing} mismatch={mismatch} reversed={reversed_count}"
        )
        return SharedBreaklineAuditPresentation(
            status=status,
            missing_consumer_count=missing,
            mismatch_count=mismatch,
            geometry_match_count=geometry_match,
            geometry_mismatch_count=geometry_mismatch,
            mesh_match_count=mesh_match,
            mesh_mismatch_count=mesh_mismatch,
            reversed_edge_count=reversed_count,
            solid_readiness_status=str(
                _value(audit, "solid_readiness_status", "") or ""
            ),
            solid_open_end_count=int(
                _value(audit, "solid_open_end_count", 0) or 0
            ),
            solid_duplicate_edge_count=int(
                _value(audit, "solid_duplicate_edge_count", 0) or 0
            ),
            solid_reversed_edge_count=int(
                _value(audit, "solid_reversed_edge_count", 0) or 0
            ),
            solid_non_manifold_node_count=int(
                _value(audit, "solid_non_manifold_node_count", 0) or 0
            ),
            solid_readiness_notes=str(
                _value(audit, "solid_readiness_notes", "") or ""
            ),
            notes=notes,
            summary=summary,
            note_rows=tuple(
                value.strip() for value in notes.split(";") if value.strip()
            ),
        )


def _value(source: object, name: str, default: object) -> object:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


# Moved from cmd_build_corridor by M5: panel display rows for the
# shared-breakline audit table. The command module keeps the document read
# and imports these back.

def shared_breakline_audit_display_rows(rows: list[dict[str, object]], *, include_internal: bool = False) -> list[dict[str, object]]:
    """Return panel-friendly shared breakline audit rows.

    The default panel view keeps one row per audited surface; ``include_internal`` adds one row per
    breakline role of that surface, for tests and developer diagnostics.
    """

    output: list[dict[str, object]] = []
    for row in list(rows or []):
        surface_row = dict(row)
        surface_row["row_kind"] = "surface"
        output.append(surface_row)
        if not include_internal:
            continue
        for role, count in _shared_breakline_summary_count_items(str(row.get("role_summary", "") or "")):
            detail = dict(row)
            detail["row_kind"] = "role"
            detail["surface"] = f"  Role: {role}"
            detail["consumed"] = count
            detail["total"] = count
            detail["material_summary"] = str(row.get("material_summary", "") or "")
            detail["role_summary"] = f"{role}={count}"
            detail["breakline_role_filter"] = role
            detail["recommended_action"] = _shared_breakline_recommended_action_from_notes(role) or str(row.get("recommended_action", "") or "")
            output.append(detail)
    return output


def _shared_breakline_recommended_action_from_notes(notes: str) -> str:
    text = str(notes or "")
    if not text:
        return ""
    if "patch-to-slope-face" in text or "patch_to_slope_face" in text:
        return "Rebuild Intersection and Slope Face constraints"
    if "curb_return_to_slope_face" in text or "curb-return-to-slope-face" in text:
        return "Rebuild Intersection and Slope Face constraints"
    if "patch-to-design" in text or "patch_to_design" in text:
        return "Rebuild Intersection and Design constraints"
    if "curb_return_to_pavement" in text or "curb-return-to-pavement" in text:
        return "Rebuild Intersection and Design constraints"
    if "curb_return_to_shoulder" in text or "curb-return-to-shoulder" in text:
        return "Rebuild Intersection and Design constraints"
    if "patch-to-shoulder" in text or "patch_to_shoulder" in text:
        return "Rebuild Intersection and Design constraints"
    if "shoulder-to-slope-face" in text or "shoulder_to_slope_face" in text:
        return "Rebuild Applied Sections, then constrained surfaces"
    if "curb_return_inner" in text or "curb-return-inner" in text or "curb_return_outer" in text or "curb-return-outer" in text:
        return "Rebuild Intersection curb-return constraints"
    if (
        "region-transition" in text
        or "region_start_boundary" in text
        or "region_end_boundary" in text
        or "assembly_change_boundary" in text
        or "surface_transition_boundary" in text
    ):
        return "Review Region spans, then Build Parametric"
    if (
        "control_area_entry" in text
        or "control-area-entry" in text
        or "control_area_exit" in text
        or "control-area-exit" in text
        or "region_to_intersection_control" in text
        or "region-to-intersection-control" in text
    ):
        return "Review Intersection control areas and Region spans, then Build Parametric"
    if (
        "lane_to_lane" in text
        or "lane_to_shoulder" in text
        or "shoulder_edge" in text
        or "shoulder_to_side_slope" in text
        or "side_slope_to_daylight" in text
    ):
        return "Rebuild Applied Sections, then constrained surfaces"
    if (
        "intersection_gutter_handoff" in text
        or "intersection-gutter-handoff" in text
        or "intersection_ditch_handoff" in text
        or "intersection-ditch-handoff" in text
        or "low_point_flow_split" in text
        or "low-point-flow-split" in text
        or "drainage_capture_edge" in text
        or "drainage-capture-edge" in text
    ):
        return "Review Intersection Drainage source, then rebuild Intersection"
    if (
        "corridor_gutter_handoff" in text
        or "corridor-ditch-handoff" in text
        or "corridor_ditch_handoff" in text
        or "corridor-gutter-handoff" in text
    ):
        return "Review Drainage source, then rebuild Applied Sections"
    return ""


def _shared_breakline_summary_count_items(summary: str) -> list[tuple[str, int]]:
    items: list[tuple[str, int]] = []
    for part in str(summary or "").split(","):
        text = str(part or "").strip()
        if not text or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        try:
            count = int(str(value or "0").strip() or 0)
        except Exception:
            count = 0
        if key:
            items.append((key, count))
    return items


CORRIDOR_BUILD_REVIEW_STATUS_VALUES = ("ready", "warning", "missing", "empty", "error")


def _normalize_corridor_build_review_status(status: str, *, default: str = "missing") -> str:
    value = str(status or "").strip().lower()
    if value == "warn":
        value = "warning"
    if value == "not_built":
        value = "missing"
    if value in CORRIDOR_BUILD_REVIEW_STATUS_VALUES:
        return value
    return str(default or "missing")


def _shared_breakline_recommended_action(
    *,
    geometry_mismatch_count: int,
    missing_consumer_count: int,
    mismatch_count: int,
    reversed_edge_count: int,
    mesh_mismatch_count: int = 0,
    notes: str = "",
) -> str:
    if int(mismatch_count or 0) > 0:
        return "Review the shared breakline sources"
    if int(missing_consumer_count or 0) > 0:
        return "Rebuild Build Parametric"
    role_action = _shared_breakline_recommended_action_from_notes(notes)
    if role_action:
        return role_action
    if int(mesh_mismatch_count or 0) > 0:
        return "Rebuild constrained surface mesh"
    if int(geometry_mismatch_count or 0) > 0:
        return "Rebuild Applied Sections, then Build Parametric"
    if int(reversed_edge_count or 0) > 0:
        return "Monitor; check Watertight normals if needed"
    return "No action needed"


def shared_breakline_audit_rows_from_preview_objects(preview_entries) -> list[dict[str, object]]:
    """Return panel-friendly shared breakline audit rows from built preview objects."""

    rows: list[dict[str, object]] = []
    for role, title, object_name, obj in preview_entries:
        result_id = str(getattr(obj, "SharedBreaklineResultId", "") or "")
        audit_status = str(getattr(obj, "SharedBreaklineAuditStatus", "") or "")
        if not result_id and not audit_status:
            continue
        geometry_match = int(getattr(obj, "SharedBreaklineGeometryMatchCount", 0) or 0)
        geometry_mismatch = int(getattr(obj, "SharedBreaklineGeometryMismatchCount", 0) or 0)
        mesh_match = int(getattr(obj, "SharedBreaklineMeshMatchCount", 0) or 0)
        mesh_mismatch = int(getattr(obj, "SharedBreaklineMeshMismatchCount", 0) or 0)
        missing = int(getattr(obj, "SharedBreaklineMissingConsumerCount", 0) or 0)
        mismatch = int(getattr(obj, "SharedBreaklineMismatchCount", 0) or 0)
        reversed_count = int(getattr(obj, "SharedBreaklineReversedEdgeCount", 0) or 0)
        notes = "; ".join(str(value or "") for value in list(getattr(obj, "SharedBreaklineAuditNotes", []) or []) if str(value or ""))
        if not notes:
            notes = str(getattr(obj, "SharedBreaklineAuditSummary", "") or "")
        status = _normalize_corridor_build_review_status(audit_status or str(getattr(obj, "SharedBreaklineStatus", "") or "missing"), default="missing")
        substantive_warning = bool(geometry_mismatch or mesh_mismatch or missing or mismatch or reversed_count)
        if substantive_warning:
            status = "warning"
        elif status == "warning":
            status = "ready"
        rows.append(
            {
                "role": role,
                "surface": title,
                "object_name": str(getattr(obj, "Name", "") or object_name),
                "object_label": str(getattr(obj, "Label", "") or object_name),
                "status": status,
                "result_id": result_id,
                "material_summary": str(getattr(obj, "SharedBreaklineMaterialSummary", "") or ""),
                "role_summary": str(getattr(obj, "SharedBreaklineRoleSummary", "") or ""),
                "consumed": int(getattr(obj, "SharedBreaklineConsumedCount", 0) or 0),
                "total": int(getattr(obj, "SharedBreaklineCount", 0) or 0),
                "geometry_match_count": geometry_match,
                "geometry_mismatch_count": geometry_mismatch,
                "mesh_match_count": mesh_match,
                "mesh_mismatch_count": mesh_mismatch,
                "missing_consumer_count": missing,
                "mismatch_count": mismatch,
                "reversed_edge_count": reversed_count,
                "solid_readiness_status": str(getattr(obj, "SharedBreaklineSolidReadinessStatus", "") or ""),
                "solid_open_end_count": int(getattr(obj, "SharedBreaklineSolidOpenEndCount", 0) or 0),
                "solid_duplicate_edge_count": int(getattr(obj, "SharedBreaklineSolidDuplicateEdgeCount", 0) or 0),
                "solid_non_manifold_node_count": int(getattr(obj, "SharedBreaklineSolidNonManifoldNodeCount", 0) or 0),
                "recommended_action": _shared_breakline_recommended_action(
                    geometry_mismatch_count=geometry_mismatch,
                    mesh_mismatch_count=mesh_mismatch,
                    missing_consumer_count=missing,
                    mismatch_count=mismatch,
                    reversed_edge_count=reversed_count,
                    notes=notes,
                ),
                "notes": notes,
            }
        )
    return rows

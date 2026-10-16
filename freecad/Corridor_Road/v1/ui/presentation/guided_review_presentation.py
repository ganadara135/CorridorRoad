"""Guided Review rows of the Build Parametric panel.

The command reads the document's review rows and summaries; these rules turn them into the ordered
Guided Review steps the panel lists. Moved from `commands/cmd_build_corridor.py` (GR-7).
"""

from __future__ import annotations


CORRIDOR_BUILD_GUIDED_REVIEW_STEPS = (
    ("centerline", "1. Centerline", ("centerline",), "Check 3D centerline continuity and station ordering."),
    ("design", "2. Design Surface", ("centerline", "design"), "Check finished-grade surface continuity."),
    ("intersections", "4. Intersections", ("intersection",), "Check intersection-controlled Region context and Applied Sections handoff."),
    ("slope_issues", "5. Side Slope", ("daylight", "intersection_slope"), "Review ordinary and intersection-owned Side Slope result surfaces and their diagnostics separately."),
    ("drainage", "6. Drainage Surface", ("centerline", "drainage"), "Check roadside ditch surfaces and intersection low-point drainage coverage."),
    ("drainage_flow", "7. Drainage Flow", ("centerline", "drainage"), "Check Flow Route connections and linked drainage structures."),
)


def guided_review_step_rows(
    *,
    review_by_role: dict[str, dict[str, object]],
    issue_count: int,
    drainage_summary: dict[str, object],
    drainage_flow_summary: dict[str, object],
    intersection_summary: dict[str, object],
    subassembly_kind_rows: list[dict[str, object]],
    general_road: bool,
) -> list[dict[str, object]]:
    """Ordered Guided Review rows from the review rows and summaries the command reads.

    A General Road document has no intersection, so it has no Intersections step.
    """

    rows: list[dict[str, object]] = []
    for step_id, title, roles, default_notes in CORRIDOR_BUILD_GUIDED_REVIEW_STEPS:
        if step_id == "intersections" and general_road:
            continue
        if step_id == "slope_issues":
            daylight = review_by_role.get("daylight", {})
            intersection_slope = review_by_role.get("intersection_slope", {})
            base_status = str(daylight.get("status", "missing") or "missing")
            intersection_status = str(intersection_slope.get("status", "missing") or "missing")
            if base_status == "error" or intersection_status == "error":
                status = "error"
            elif (base_status == "ready" or intersection_status == "ready") and issue_count:
                status = "warning"
            elif base_status == "ready" or intersection_status == "ready":
                status = "ready"
            else:
                status = intersection_status if intersection_status not in {"missing", "empty"} else base_status
            intersection_count = intersection_slope.get("triangle_or_point_count", "")
            intersection_note = f"; intersection slope triangles={intersection_count}" if intersection_count not in {"", None} else ""
            boundary_review_note = _slope_face_boundary_guided_review_suffix(daylight, intersection_slope)
            notes = f"{issue_count} Side Slope diagnostic(s) to review{intersection_note}." if issue_count else f"No Side Slope fallback diagnostics{intersection_note}."
            if boundary_review_note:
                notes = f"{notes} {boundary_review_note}"
            if intersection_status == "ready" and base_status == "ready":
                focus = "Intersection and Corridor Slope Face Surfaces"
            elif intersection_status == "ready":
                focus = "Intersection Slope Face Surface"
            elif base_status == "ready":
                focus = "Slope Face Surface"
            else:
                focus = "Side Slope Result Diagnostic"
        else:
            primary_role = str(list(roles)[-1] if roles else "")
            source = review_by_role.get(primary_role, {})
            status = str(source.get("status", "missing") or "missing")
            notes = default_notes if status == "ready" else str(source.get("notes", "") or "Not built yet.")
            focus = str(source.get("result", title) or title)
            output_path = str(source.get("output_path", "") or "")
            if step_id == "drainage":
                drainage = drainage_summary
                status = str(drainage.get("status", status) or status)
                notes = str(drainage.get("notes", notes) or notes)
                focus = "Drainage Surface" if source.get("status") == "ready" else "Drainage Diagnostics"
            elif step_id == "drainage_flow":
                status = str(drainage_flow_summary.get("status", status) or status)
                notes = str(drainage_flow_summary.get("notes", default_notes) or default_notes)
                focus = str(drainage_flow_summary.get("focus", "Drainage Flow") or "Drainage Flow")
            elif step_id == "intersections":
                intersection_source = review_by_role.get("intersection", source)
                status = str(intersection_summary.get("status", status) or status)
                notes = str(intersection_summary.get("notes", default_notes) or default_notes)
                focus = str(intersection_summary.get("focus", "Intersections") or "Intersections")
                output_path = str(intersection_source.get("output_path", output_path) or output_path)
        rows.append(
            {
                "step_id": step_id,
                "title": title,
                "roles": list(roles),
                "status": status,
                "focus": focus,
                "output_path": output_path if step_id != "slope_issues" else str(intersection_slope.get("output_path", "") or daylight.get("output_path", "") or ""),
                "notes": notes,
            }
        )
        if step_id == "design":
            rows.extend(subassembly_kind_rows)
    return rows


def _slope_face_boundary_guided_review_suffix(*review_rows: dict[str, object]) -> str:
    boundary_note = _slope_face_boundary_review_note_from_rows(*review_rows)
    if not boundary_note:
        return ""
    return f"boundary_review=intersection_slope_face_boundary_result; {boundary_note}"


def _slope_face_boundary_review_note_from_rows(*review_rows: dict[str, object]) -> str:
    for row in review_rows:
        notes = str((row or {}).get("notes", "") or "")
        marker = "slope_face_boundary="
        index = notes.find(marker)
        if index < 0:
            continue
        tail = notes[index:].strip()
        if " | " in tail:
            tail = tail.split(" | ", 1)[0].strip()
        return tail
    return ""


__all__ = ["CORRIDOR_BUILD_GUIDED_REVIEW_STEPS", "guided_review_step_rows"]

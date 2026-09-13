"""Presentation rows for the Roadside Drainage review table."""

from __future__ import annotations

from typing import Callable

from .review_text import unique_refs as _unique_refs

DRAINAGE_REVIEW_MISSING_APPLIED_SECTIONS_NOTE = "Applied Sections are required before drainage review."
DRAINAGE_REVIEW_NO_STATION_ROWS_NOTE = "No Applied Section station rows."


def drainage_review_placeholder_row(notes: str) -> dict[str, object]:
    """Return the single row shown when there is no Applied Section station to review."""

    return {
        "station": "",
        "section_id": "",
        "context": "roadside_drainage",
        "context_label": "Roadside Drainage",
        "status": "missing",
        "ditch_point_count": 0,
        "left_count": 0,
        "right_count": 0,
        "notes": notes,
    }


def drainage_review_station_rows(
    applied,
    *,
    active_ditch_rows_for: Callable[[float], list[object]],
) -> list[dict[str, object]]:
    """Return station-level drainage source diagnostics from Applied Sections."""

    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied, "sections", []) or [])
    }
    output: list[dict[str, object]] = []
    for row in sorted(list(getattr(applied, "station_rows", []) or []), key=lambda item: float(getattr(item, "station", 0.0) or 0.0)):
        section_id = str(getattr(row, "applied_section_id", "") or "")
        section = sections.get(section_id)
        station = float(getattr(row, "station", 0.0) or 0.0)
        active_ditch_rows = active_ditch_rows_for(station)
        if section is None:
            output.append(
                {
                    "station": station,
                    "section_id": section_id,
                    "context": "roadside_drainage",
                    "context_label": "Roadside Drainage",
                    "status": "missing",
                    "ditch_point_count": 0,
                    "left_count": 0,
                    "right_count": 0,
                    "marker_object": _drainage_review_marker_name(len(output)),
                    "x": "",
                    "y": "",
                    "z": "",
                    "notes": "Applied section row is missing.",
                }
            )
            continue
        ditch_points = [
            point
            for point in list(getattr(section, "point_rows", []) or [])
            if str(getattr(point, "point_role", "") or "") == "ditch_surface"
        ]
        left_count = sum(1 for point in ditch_points if _drainage_point_side(point) == "L")
        right_count = sum(1 for point in ditch_points if _drainage_point_side(point) == "R")
        mismatch_notes = _drainage_source_surface_mismatch_notes(active_ditch_rows, ditch_points)
        if active_ditch_rows and any(note.startswith("missing_side=") for note in mismatch_notes):
            status = "missing"
            notes = "Active Drainage ditch row has no matching ditch_surface side. " + " ".join(mismatch_notes)
        elif not ditch_points:
            status = "missing"
            notes = "No ditch_surface point rows from Assembly/Applied Sections."
            if active_ditch_rows:
                notes += " " + " ".join(mismatch_notes)
        elif mismatch_notes:
            status = "warn"
            notes = "Drainage source/result mismatch. " + " ".join(mismatch_notes)
        elif left_count and right_count:
            status = "ready"
            notes = "Left and right ditch surface points available."
        else:
            status = "warn"
            notes = "Only one side has ditch surface points."
        marker_point = _drainage_review_marker_point(section, ditch_points)
        output.append(
            {
                "station": station,
                "section_id": section_id,
                "context": "roadside_drainage",
                "context_label": "Roadside Drainage",
                "status": status,
                "ditch_point_count": len(ditch_points),
                "left_count": left_count,
                "right_count": right_count,
                "marker_object": _drainage_review_marker_name(len(output)),
                "x": f"{marker_point[0]:.6f}",
                "y": f"{marker_point[1]:.6f}",
                "z": f"{marker_point[2]:.6f}",
                "notes": notes,
            }
        )
    return output


def _drainage_source_surface_mismatch_notes(active_ditch_rows: list[object], ditch_points: list[object]) -> list[str]:
    if not active_ditch_rows:
        return []
    point_data = _ditch_point_context_by_side(ditch_points)
    notes: list[str] = []
    for row in active_ditch_rows:
        drainage_ref = str(getattr(row, "drainage_element_id", "") or "").strip()
        subassembly_ref = str(getattr(row, "subassembly_ref", "") or "").strip()
        for side in _drainage_row_sides(row):
            data = point_data.get(side, {})
            point_count = int(data.get("point_count", 0) or 0)
            drainage_refs = set(data.get("drainage_refs", []) or [])
            subassembly_refs = set(data.get("subassembly_refs", []) or [])
            if point_count <= 0:
                notes.append(f"missing_side={side};drainage_ref={drainage_ref or '-'}")
                continue
            if drainage_ref and drainage_ref not in drainage_refs:
                notes.append(f"missing_drainage_ref={drainage_ref};side={side}")
            if subassembly_ref and subassembly_ref not in subassembly_refs:
                notes.append(f"subassembly_mismatch={subassembly_ref};side={side}")
    return _unique_refs(notes)


def _ditch_point_context_by_side(ditch_points: list[object]) -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for point in list(ditch_points or []):
        side = _long_drainage_side(_drainage_point_side(point))
        if side not in {"left", "right"}:
            continue
        data = output.setdefault(side, {"point_count": 0, "drainage_refs": [], "subassembly_refs": []})
        data["point_count"] = int(data.get("point_count", 0) or 0) + 1
        drainage_ref = str(getattr(point, "drainage_ref", "") or "").strip()
        subassembly_ref = str(getattr(point, "subassembly_ref", "") or "").strip()
        if drainage_ref:
            data.setdefault("drainage_refs", []).append(drainage_ref)
        if subassembly_ref:
            data.setdefault("subassembly_refs", []).append(subassembly_ref)
    for data in output.values():
        data["drainage_refs"] = _unique_refs(list(data.get("drainage_refs", []) or []))
        data["subassembly_refs"] = _unique_refs(list(data.get("subassembly_refs", []) or []))
    return output


def _drainage_row_sides(row) -> list[str]:
    side = str(getattr(row, "side", "") or "").strip().lower()
    if side == "both":
        return ["left", "right"]
    if side in {"left", "right"}:
        return [side]
    ref_text = " ".join(
        [
            str(getattr(row, "drainage_element_id", "") or ""),
            str(getattr(row, "subassembly_ref", "") or ""),
        ]
    ).lower()
    if "left" in ref_text or ":l" in ref_text or "-l" in ref_text:
        return ["left"]
    if "right" in ref_text or ":r" in ref_text or "-r" in ref_text:
        return ["right"]
    return []


def _long_drainage_side(side: str) -> str:
    text = str(side or "").strip().lower()
    if text in {"l", "left"}:
        return "left"
    if text in {"r", "right"}:
        return "right"
    return text


def _drainage_point_side(point) -> str:
    point_id = str(getattr(point, "point_id", "") or "").lower()
    side = str(getattr(point, "side", "") or "").strip().lower()
    if side == "left":
        return "L"
    if side == "right":
        return "R"
    lateral = float(getattr(point, "lateral_offset", 0.0) or 0.0)
    if "left" in point_id:
        return "L"
    if "right" in point_id:
        return "R"
    if lateral > 0.0:
        return "L"
    if lateral < 0.0:
        return "R"
    return ""


def _drainage_review_marker_point(section, ditch_points: list[object]) -> tuple[float, float, float]:
    points = list(ditch_points or [])
    if points:
        return (
            sum(float(getattr(point, "x", 0.0) or 0.0) for point in points) / len(points),
            sum(float(getattr(point, "y", 0.0) or 0.0) for point in points) / len(points),
            sum(float(getattr(point, "z", 0.0) or 0.0) for point in points) / len(points),
        )
    frame = getattr(section, "frame", None)
    if frame is not None:
        return (
            float(getattr(frame, "x", 0.0) or 0.0),
            float(getattr(frame, "y", 0.0) or 0.0),
            float(getattr(frame, "z", 0.0) or 0.0),
        )
    return (0.0, 0.0, 0.0)


def _drainage_review_marker_name(row_index: int) -> str:
    return f"ReviewIssueDrainageStation{max(0, int(row_index)) + 1:03d}"

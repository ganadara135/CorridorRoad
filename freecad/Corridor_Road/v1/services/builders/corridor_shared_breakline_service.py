"""Shared breakline construction for the corridor surfaces of CorridorRoad v1.

Builds the `SharedBreaklineResult` the Design, Subgrade, Daylight and Region surfaces share, from
an AppliedSectionSet: the general section-link breaklines, the side slope boundary runs and the
Region assembly-change breaklines, and audits them. Pure functions of the result models: they
read no document and create no FreeCAD object. Moved from `commands/cmd_build_corridor.py` (GR-7).
"""

from __future__ import annotations

from ...models.result.shared_breakline import SharedBreaklinePointRow, SharedBreaklineResult, SharedBreaklineRow
from ..evaluation.shared_breakline_audit_service import SharedBreaklineAuditService


def unique_text_values(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def corridor_general_shared_breakline_result(applied_section_set) -> SharedBreaklineResult:
    """Build corridor-wide shared breakline rows from ordinary Applied Section link roles."""

    project_id = str(getattr(applied_section_set, "project_id", "") or "")
    corridor_id = str(getattr(applied_section_set, "corridor_id", "") or "corridor")
    result_id = f"shared-breakline:corridor:{corridor_id or 'main'}"
    point_rows: list[SharedBreaklinePointRow] = []
    breakline_rows: list[SharedBreaklineRow] = []
    diagnostics: list[str] = []
    groups: dict[tuple[str, str, str, str, str, str], list[dict[str, object]]] = {}
    for section_sequence, section in enumerate(_ordered_applied_sections_for_breaklines(applied_section_set)):
        if str(getattr(section, "active_intersection_id", "") or ""):
            continue
        station = float(getattr(section, "station", 0.0) or 0.0)
        alignment_ref = str(getattr(section, "alignment_id", "") or "")
        region_ref = str(getattr(section, "region_id", "") or "")
        _append_slope_face_applied_section_breakline_group_entries(
            groups,
            section=section,
            station=station,
            alignment_ref=alignment_ref,
            region_ref=region_ref,
            section_sequence=section_sequence,
        )
        point_lookup = _applied_section_subassembly_point_lookup(section)
        for link in list(getattr(section, "subassembly_link_rows", []) or []):
            surface_role = _normal_shared_breakline_surface_role(getattr(link, "surface_role", ""))
            if surface_role not in {"design_surface", "slope_face_surface", "drainage_surface"}:
                continue
            if surface_role == "slope_face_surface":
                continue
            for endpoint_kind, point_ref in (("start", getattr(link, "start_point_ref", "")), ("end", getattr(link, "end_point_ref", ""))):
                point = point_lookup.get(str(point_ref or ""))
                if point is None:
                    diagnostics.append(f"missing_link_point:{getattr(section, 'applied_section_id', '')}:{getattr(link, 'link_id', '')}:{point_ref}")
                    continue
                point_code = str(getattr(point, "point_code", "") or point_ref or endpoint_kind)
                side = str(getattr(point, "side", "") or _subassembly_side_for_ref(section, getattr(link, "subassembly_ref", "")) or "")
                breakline_role = _general_breakline_role_for_link(link, endpoint_kind=endpoint_kind)
                key = (
                    alignment_ref,
                    region_ref,
                    surface_role,
                    breakline_role,
                    side,
                    f"{str(getattr(link, 'subassembly_ref', '') or '')}:{point_code}:{endpoint_kind}",
                )
                groups.setdefault(key, []).append(
                    {
                        "section": section,
                        "link": link,
                        "point": point,
                        "station": station,
                        "alignment_ref": alignment_ref,
                        "region_ref": region_ref,
                        "side": side,
                    }
                )
    breakline_index = 1
    for _index, (key, entries) in enumerate(sorted(groups.items(), key=lambda item: item[0]), start=1):
        ordered = sorted(entries, key=lambda entry: float(entry.get("station", 0.0) or 0.0))
        alignment_ref, region_ref, surface_role, breakline_role, side, endpoint_key = key
        safe_role = _safe_breakline_id_part(breakline_role)
        safe_endpoint = _safe_breakline_id_part(endpoint_key)
        for run_entries in _contiguous_shared_breakline_entry_runs(ordered):
            if len(run_entries) < 2:
                continue
            breakline_id = f"{result_id}:{safe_role}:{breakline_index}:{safe_endpoint}"
            breakline_index += 1
            refs: list[str] = []
            for point_index, entry in enumerate(run_entries):
                point = entry["point"]
                section = entry["section"]
                point_id = f"{breakline_id}:p{point_index + 1}"
                refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id=point_id,
                        breakline_ref=breakline_id,
                        sequence=point_index,
                        x=float(getattr(point, "x", 0.0) or 0.0),
                        y=float(getattr(point, "y", 0.0) or 0.0),
                        z=float(getattr(point, "z", 0.0) or 0.0),
                        station=float(entry.get("station", 0.0) or 0.0),
                        offset=float(getattr(point, "lateral_offset", 0.0) or 0.0),
                        source_point_ref=f"{getattr(section, 'applied_section_id', '')}:{getattr(point, 'point_id', '')}",
                        notes=str(entry.get("source_note", "") or "corridor-wide shared breakline from Applied Section subassembly link endpoint"),
                    )
                )
            consumer = _general_breakline_consumer_for_surface_role(surface_role)
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=breakline_id,
                    domain_kind="corridor",
                    domain_ref=corridor_id,
                    breakline_role=breakline_role,
                    source_contract_refs=tuple(
                        unique_text_values(
                            [
                                *[
                                    _shared_breakline_entry_source_ref(entry)
                                    for entry in run_entries
                                ],
                                *[
                                    ref
                                    for entry in run_entries
                                    for ref in _applied_section_profile_source_refs(entry["section"])
                                ],
                            ]
                        )
                    ),
                    consumer_refs=(consumer,),
                    from_output_role=consumer,
                    to_output_role=consumer,
                    point_refs=tuple(refs),
                    station_start=float(run_entries[0].get("station", 0.0) or 0.0),
                    station_end=float(run_entries[-1].get("station", 0.0) or 0.0),
                    alignment_ref=alignment_ref,
                    side=side,
                    material_role=surface_role,
                    source_status="ready",
                    handoff_target="applied_sections",
                    notes=f"Ordinary corridor breakline for {surface_role}; region={region_ref}; endpoint={endpoint_key}; source={_shared_breakline_entry_source_mode(run_entries)}",
                )
            )
    status = "ready" if breakline_rows else "missing"
    if not breakline_rows and not diagnostics:
        diagnostics.append("corridor_shared_breakline_rows_missing")
    return SharedBreaklineResult(
        schema_version=1,
        project_id=project_id,
        breakline_result_id=result_id,
        domain_kind="corridor",
        domain_ref=corridor_id,
        status=status,
        breakline_count=len(breakline_rows),
        ready_count=len(breakline_rows),
        warning_count=0,
        error_count=0,
        diagnostic_rows=diagnostics,
        breakline_rows=breakline_rows,
        point_rows=point_rows,
    )


def _applied_section_profile_source_refs(section) -> list[str]:
    refs: list[str] = []
    for attr in ("profile_id", "active_profile_id", "profile_ref"):
        ref = str(getattr(section, attr, "") or "").strip()
        if ref:
            refs.append(ref)
    frame = getattr(section, "frame", None)
    if frame is not None:
        for attr in ("active_profile_segment_start_id", "active_profile_segment_end_id", "active_vertical_curve_id"):
            ref = str(getattr(frame, attr, "") or "").strip()
            if ref:
                refs.append(ref)
    return unique_text_values(refs)


def _append_slope_face_applied_section_breakline_group_entries(
    groups: dict[tuple[str, str, str, str, str, str], list[dict[str, object]]],
    *,
    section,
    station: float,
    alignment_ref: str,
    region_ref: str,
    section_sequence: int,
) -> None:
    for side in ("left", "right"):
        rows = _applied_section_slope_face_boundary_points(section, side_label=side)
        if len(rows) < 2:
            continue
        for slot in _applied_section_slope_face_breakline_slots(rows, side_label=side):
            point = slot["point"]
            breakline_role = str(slot["breakline_role"])
            endpoint_key = str(slot["endpoint_key"])
            key = (
                alignment_ref,
                region_ref,
                "slope_face_surface",
                breakline_role,
                side,
                endpoint_key,
            )
            groups.setdefault(key, []).append(
                {
                    "section": section,
                    "link": None,
                    "point": point,
                    "station": station,
                    "alignment_ref": alignment_ref,
                    "region_ref": region_ref,
                    "side": side,
                    "source_mode": "applied_section_side_slope_point_rows",
                    "source_note": "corridor-wide shared breakline from Applied Section side slope boundary point",
                    "source_section_sequence": int(section_sequence),
                }
            )


def _contiguous_shared_breakline_entry_runs(entries: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    ordered = list(entries or [])
    if len(ordered) < 2:
        return [ordered] if ordered else []
    if not any("source_section_sequence" in entry for entry in ordered):
        return [ordered]
    runs: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    previous_sequence: int | None = None
    for entry in ordered:
        sequence_value = entry.get("source_section_sequence")
        try:
            sequence = int(sequence_value)
        except Exception:
            sequence = None
        if (
            current
            and sequence is not None
            and previous_sequence is not None
            and sequence != previous_sequence + 1
        ):
            runs.append(current)
            current = []
        current.append(entry)
        previous_sequence = sequence
    if current:
        runs.append(current)
    return runs


def _applied_section_slope_face_breakline_slots(rows: list[object], *, side_label: str) -> list[dict[str, object]]:
    """Return stable shared-breakline slots for an AppliedSection side slope.

    Internal side-slope points can appear/disappear as supplemental sampling,
    terrain daylight, or intersection clipping changes.  Shared breaklines must
    therefore follow stable boundary semantics instead of raw point indices.
    """

    points = list(rows or [])
    if len(points) < 2:
        return []
    side = str(side_label or "").strip().lower() or "side"
    slots: list[dict[str, object]] = []
    inner = points[0]
    outer = points[-1]
    slots.append(
        {
            "point": inner,
            "breakline_role": "shoulder_to_side_slope",
            "endpoint_key": f"applied-section-side-slope:{side}:inner:{_applied_section_slope_face_slot_role(inner)}",
        }
    )
    slots.append(
        {
            "point": outer,
            "breakline_role": "side_slope_to_daylight",
            "endpoint_key": f"applied-section-side-slope:{side}:outer:{_applied_section_slope_face_slot_role(outer)}",
        }
    )
    return slots


def _applied_section_slope_face_slot_role(point) -> str:
    role = str(getattr(point, "point_role", "") or "").strip()
    if role in {"side_slope_surface", "bench_surface", "daylight_marker"}:
        return role
    return "slope_face_point"


def _applied_section_slope_face_boundary_points(section, *, side_label: str) -> list[object]:
    side = str(side_label or "").strip().lower()
    rows = []
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"side_slope_surface", "bench_surface", "daylight_marker"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        point_side = str(getattr(point, "side", "") or "").strip().lower()
        point_id = str(getattr(point, "point_id", "") or "").strip().lower()
        id_matches_side = f":{side}" in point_id or point_id.startswith(f"{side}:") or point_id.endswith(f":{side}")
        offset_matches_side = (side == "left" and offset >= -1.0e-9) or (side == "right" and offset <= 1.0e-9)
        if point_side and point_side != side:
            continue
        if not point_side and not id_matches_side and not offset_matches_side:
            continue
        rows.append(point)
    if side == "left":
        rows.sort(key=lambda point: (float(getattr(point, "lateral_offset", 0.0) or 0.0), str(getattr(point, "point_id", "") or "")))
    else:
        rows.sort(key=lambda point: (-float(getattr(point, "lateral_offset", 0.0) or 0.0), str(getattr(point, "point_id", "") or "")))
    return rows


def _shared_breakline_entry_source_ref(entry: dict[str, object]) -> str:
    section = entry.get("section")
    link = entry.get("link")
    point = entry.get("point")
    if link is not None:
        return f"{getattr(section, 'applied_section_id', '')}:{getattr(link, 'link_id', '')}"
    return f"{getattr(section, 'applied_section_id', '')}:{getattr(point, 'point_id', '')}"


def _shared_breakline_entry_source_mode(entries: list[dict[str, object]]) -> str:
    modes = unique_text_values(str(entry.get("source_mode", "") or "subassembly_link_rows") for entry in list(entries or []))
    return ",".join(modes) if modes else "subassembly_link_rows"


def combined_shared_breakline_result(*results) -> SharedBreaklineResult | None:
    """Combine multiple SharedBreaklineResult values for one preview/audit surface."""

    clean = [result for result in list(results or []) if result is not None]
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    first = clean[0]
    breakline_rows: list[SharedBreaklineRow] = []
    point_rows: list[SharedBreaklinePointRow] = []
    diagnostics: list[str] = []
    for result in clean:
        breakline_rows.extend(list(getattr(result, "breakline_rows", []) or []))
        point_rows.extend(list(getattr(result, "point_rows", []) or []))
        diagnostics.extend(str(row) for row in list(getattr(result, "diagnostic_rows", []) or []) if str(row))
    error_count = sum(int(getattr(result, "error_count", 0) or 0) for result in clean)
    warning_count = sum(int(getattr(result, "warning_count", 0) or 0) for result in clean)
    ready_count = sum(int(getattr(result, "ready_count", 0) or 0) for result in clean)
    status = "ready" if breakline_rows and error_count == 0 else "missing" if not breakline_rows else "warning"
    return SharedBreaklineResult(
        schema_version=1,
        project_id=str(getattr(first, "project_id", "") or ""),
        breakline_result_id="shared-breakline:combined:" + ",".join(str(getattr(result, "breakline_result_id", "") or "") for result in clean),
        domain_kind="combined",
        domain_ref=",".join(str(getattr(result, "domain_ref", "") or "") for result in clean if str(getattr(result, "domain_ref", "") or "")),
        status=status,
        breakline_count=len(breakline_rows),
        ready_count=ready_count,
        warning_count=warning_count,
        error_count=error_count,
        diagnostic_rows=diagnostics,
        breakline_rows=breakline_rows,
        point_rows=point_rows,
    )


def corridor_region_transition_shared_breakline_result(applied_section_set) -> SharedBreaklineResult:
    """Build shared breaklines for ordinary corridor Region start/end boundaries."""

    project_id = str(getattr(applied_section_set, "project_id", "") or "")
    corridor_id = str(getattr(applied_section_set, "corridor_id", "") or "corridor")
    result_id = f"shared-breakline:region-transition:{corridor_id or 'main'}"
    point_rows: list[SharedBreaklinePointRow] = []
    breakline_rows: list[SharedBreaklineRow] = []
    grouped: dict[tuple[str, str], list[object]] = {}
    for section in _ordered_applied_sections_for_breaklines(applied_section_set):
        if str(getattr(section, "active_intersection_id", "") or ""):
            continue
        key = (str(getattr(section, "alignment_id", "") or ""), str(getattr(section, "region_id", "") or ""))
        grouped.setdefault(key, []).append(section)
    for group_index, ((alignment_ref, region_ref), sections) in enumerate(sorted(grouped.items(), key=lambda item: item[0]), start=1):
        ordered_sections = sorted(sections, key=lambda section: float(getattr(section, "station", 0.0) or 0.0))
        for boundary_kind, section in (("region_start_boundary", ordered_sections[0]), ("region_end_boundary", ordered_sections[-1])):
            role_points = _section_surface_role_boundary_points(section)
            for surface_role, points in sorted(role_points.items()):
                if len(points) < 2:
                    continue
                consumer = _general_breakline_consumer_for_surface_role(surface_role)
                safe_role = _safe_breakline_id_part(boundary_kind)
                safe_surface = _safe_breakline_id_part(surface_role)
                breakline_id = f"{result_id}:{safe_role}:{group_index}:{safe_surface}"
                refs: list[str] = []
                for point_index, point in enumerate(points):
                    point_id = f"{breakline_id}:p{point_index + 1}"
                    refs.append(point_id)
                    point_rows.append(
                        SharedBreaklinePointRow(
                            point_id=point_id,
                            breakline_ref=breakline_id,
                            sequence=point_index,
                            x=float(getattr(point, "x", 0.0) or 0.0),
                            y=float(getattr(point, "y", 0.0) or 0.0),
                            z=float(getattr(point, "z", 0.0) or 0.0),
                            station=float(getattr(section, "station", 0.0) or 0.0),
                            offset=float(getattr(point, "lateral_offset", 0.0) or 0.0),
                            source_point_ref=f"{getattr(section, 'applied_section_id', '')}:{getattr(point, 'point_id', '')}",
                            notes="corridor Region boundary shared breakline from Applied Section surface-role endpoints",
                        )
                    )
                breakline_rows.append(
                    SharedBreaklineRow(
                        breakline_id=breakline_id,
                        domain_kind="region_transition",
                        domain_ref=region_ref,
                        breakline_role=boundary_kind,
                        source_contract_refs=(str(getattr(section, "applied_section_id", "") or ""),),
                        consumer_refs=(consumer,),
                        from_output_role=consumer,
                        to_output_role=consumer,
                        point_refs=tuple(refs),
                        station_start=float(getattr(section, "station", 0.0) or 0.0),
                        station_end=float(getattr(section, "station", 0.0) or 0.0),
                        alignment_ref=alignment_ref,
                        side="cross_section",
                        material_role=surface_role,
                        source_status="ready",
                        handoff_target="region_model",
                        notes=f"Region {boundary_kind}; region={region_ref}; surface={surface_role}",
                    )
                )
    _append_region_assembly_change_breaklines(
        applied_section_set=applied_section_set,
        result_id=result_id,
        breakline_rows=breakline_rows,
        point_rows=point_rows,
    )
    status = "ready" if breakline_rows else "missing"
    diagnostics = [] if breakline_rows else ["region_transition_shared_breakline_rows_missing"]
    return SharedBreaklineResult(
        schema_version=1,
        project_id=project_id,
        breakline_result_id=result_id,
        domain_kind="region_transition",
        domain_ref=corridor_id,
        status=status,
        breakline_count=len(breakline_rows),
        ready_count=len(breakline_rows),
        warning_count=0,
        error_count=0,
        diagnostic_rows=diagnostics,
        breakline_rows=breakline_rows,
        point_rows=point_rows,
    )


def _append_region_assembly_change_breaklines(
    *,
    applied_section_set,
    result_id: str,
    breakline_rows: list[SharedBreaklineRow],
    point_rows: list[SharedBreaklinePointRow],
) -> None:
    sections_by_alignment: dict[str, list[object]] = {}
    for section in _ordered_applied_sections_for_breaklines(applied_section_set):
        if str(getattr(section, "active_intersection_id", "") or ""):
            continue
        alignment_ref = str(getattr(section, "alignment_id", "") or "")
        sections_by_alignment.setdefault(alignment_ref, []).append(section)
    next_index = len(breakline_rows) + 1
    for alignment_ref, sections in sorted(sections_by_alignment.items()):
        ordered = sorted(
            sections,
            key=lambda section: (
                float(getattr(section, "station", 0.0) or 0.0),
                str(getattr(section, "region_id", "") or ""),
                str(getattr(section, "applied_section_id", "") or ""),
            ),
        )
        for previous, current in zip(ordered[:-1], ordered[1:]):
            previous_region = str(getattr(previous, "region_id", "") or "")
            current_region = str(getattr(current, "region_id", "") or "")
            if not previous_region or previous_region == current_region:
                continue
            previous_assembly = str(getattr(previous, "assembly_id", "") or "")
            current_assembly = str(getattr(current, "assembly_id", "") or "")
            if not previous_assembly or not current_assembly or previous_assembly == current_assembly:
                continue
            boundary_section = current
            role_points = _section_surface_role_boundary_points(boundary_section)
            for surface_role, points in sorted(role_points.items()):
                if len(points) < 2:
                    continue
                consumer = _general_breakline_consumer_for_surface_role(surface_role)
                safe_surface = _safe_breakline_id_part(surface_role)
                breakline_id = f"{result_id}:assembly_change_boundary:{next_index}:{safe_surface}"
                next_index += 1
                refs: list[str] = []
                for point_index, point in enumerate(points):
                    point_id = f"{breakline_id}:p{point_index + 1}"
                    refs.append(point_id)
                    point_rows.append(
                        SharedBreaklinePointRow(
                            point_id=point_id,
                            breakline_ref=breakline_id,
                            sequence=point_index,
                            x=float(getattr(point, "x", 0.0) or 0.0),
                            y=float(getattr(point, "y", 0.0) or 0.0),
                            z=float(getattr(point, "z", 0.0) or 0.0),
                            station=float(getattr(boundary_section, "station", 0.0) or 0.0),
                            offset=float(getattr(point, "lateral_offset", 0.0) or 0.0),
                            source_point_ref=f"{getattr(boundary_section, 'applied_section_id', '')}:{getattr(point, 'point_id', '')}",
                            notes="corridor Region assembly-change shared breakline from Applied Section surface-role endpoints",
                        )
                    )
                breakline_rows.append(
                    SharedBreaklineRow(
                        breakline_id=breakline_id,
                        domain_kind="region_transition",
                        domain_ref=f"{previous_region}->{current_region}",
                        breakline_role="assembly_change_boundary",
                        source_contract_refs=(
                            str(getattr(previous, "applied_section_id", "") or ""),
                            str(getattr(current, "applied_section_id", "") or ""),
                            previous_assembly,
                            current_assembly,
                        ),
                        consumer_refs=(consumer,),
                        from_output_role=consumer,
                        to_output_role=consumer,
                        point_refs=tuple(refs),
                        station_start=float(getattr(boundary_section, "station", 0.0) or 0.0),
                        station_end=float(getattr(boundary_section, "station", 0.0) or 0.0),
                        alignment_ref=alignment_ref,
                        side="cross_section",
                        material_role=surface_role,
                        source_status="ready",
                        handoff_target="region_assembly_change",
                        notes=(
                            "Region assembly_change_boundary; "
                            f"from_region={previous_region}; to_region={current_region}; "
                            f"from_assembly={previous_assembly}; to_assembly={current_assembly}; surface={surface_role}"
                        ),
                    )
                )


def _section_surface_role_boundary_points(section) -> dict[str, list[object]]:
    point_lookup = _applied_section_subassembly_point_lookup(section)
    grouped: dict[str, dict[str, object]] = {}
    for link in list(getattr(section, "subassembly_link_rows", []) or []):
        surface_role = _normal_shared_breakline_surface_role(getattr(link, "surface_role", ""))
        if surface_role not in {"design_surface", "slope_face_surface", "drainage_surface"}:
            continue
        role_points = grouped.setdefault(surface_role, {})
        for point_ref in (getattr(link, "start_point_ref", ""), getattr(link, "end_point_ref", "")):
            point = point_lookup.get(str(point_ref or ""))
            if point is None:
                continue
            key = f"{round(float(getattr(point, 'x', 0.0) or 0.0), 6)}:{round(float(getattr(point, 'y', 0.0) or 0.0), 6)}:{round(float(getattr(point, 'z', 0.0) or 0.0), 6)}"
            role_points[key] = point
    output: dict[str, list[object]] = {}
    for surface_role, points in grouped.items():
        output[surface_role] = sorted(
            points.values(),
            key=lambda point: (
                float(getattr(point, "lateral_offset", 0.0) or 0.0),
                str(getattr(point, "point_id", "") or ""),
            ),
        )
    return output


def _ordered_applied_sections_for_breaklines(applied_section_set) -> list[object]:
    return sorted(
        list(getattr(applied_section_set, "sections", []) or []),
        key=lambda section: (
            str(getattr(section, "alignment_id", "") or ""),
            str(getattr(section, "region_id", "") or ""),
            float(getattr(section, "station", 0.0) or 0.0),
            str(getattr(section, "applied_section_id", "") or ""),
        ),
    )


def _applied_section_subassembly_point_lookup(section) -> dict[str, object]:
    return {
        str(getattr(point, "point_id", "") or ""): point
        for point in list(getattr(section, "subassembly_point_rows", []) or [])
        if str(getattr(point, "point_id", "") or "")
    }


def _subassembly_side_for_ref(section, subassembly_ref: object) -> str:
    target = str(subassembly_ref or "")
    for row in list(getattr(section, "subassembly_rows", []) or []):
        if str(getattr(row, "subassembly_id", "") or "") == target:
            return str(getattr(row, "side", "") or "")
    return ""


def _normal_shared_breakline_surface_role(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in {"design", "fg", "fg_surface", "finished_grade", "finished-grade"}:
        return "design_surface"
    if text in {"slope_face", "side_slope", "side-slope", "daylight", "daylight_surface"}:
        return "slope_face_surface"
    if text in {"drainage", "ditch", "gutter"}:
        return "drainage_surface"
    return text


def _general_breakline_consumer_for_surface_role(surface_role: str) -> str:
    if surface_role == "design_surface":
        return "design_surface"
    if surface_role == "slope_face_surface":
        return "slope_face_surface"
    if surface_role == "drainage_surface":
        return "drainage_surface"
    return str(surface_role or "")


def _general_breakline_role_for_link(link, *, endpoint_kind: str) -> str:
    surface_role = _normal_shared_breakline_surface_role(getattr(link, "surface_role", ""))
    text = " ".join(
        [
            str(getattr(link, "link_code", "") or ""),
            str(getattr(link, "link_id", "") or ""),
            str(getattr(link, "subassembly_ref", "") or ""),
        ]
    ).lower()
    endpoint = str(endpoint_kind or "")
    if surface_role == "design_surface":
        if "shoulder" in text:
            return "lane_to_shoulder" if endpoint == "start" else "shoulder_edge"
        return "lane_to_lane" if endpoint == "start" else "lane_to_shoulder"
    if surface_role == "slope_face_surface":
        if endpoint == "start":
            return "shoulder_to_side_slope"
        return "side_slope_to_daylight"
    if surface_role == "drainage_surface":
        if "gutter" in text:
            return "corridor_gutter_handoff"
        return "corridor_ditch_handoff"
    return f"{surface_role}_boundary"


def _safe_breakline_id_part(value: object) -> str:
    text = str(value or "").strip()
    output = []
    for char in text:
        output.append(char if char.isalnum() or char in {"_", "-"} else "-")
    return "".join(output).strip("-") or "boundary"


def shared_breakline_adjacency_graph(
    shared_result,
    *,
    tolerance: float = 1.0e-6,
) -> dict[str, object]:
    """Return the legacy mapping for the typed shared-breakline adjacency result."""

    return SharedBreaklineAuditService().adjacency(
        shared_result,
        tolerance=tolerance,
    ).to_legacy_dict()


def shared_breakline_audit(
    shared_result,
    consumer_surfaces: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return the legacy mapping for the typed shared-breakline audit result."""

    return SharedBreaklineAuditService().audit(
        shared_result,
        consumer_surfaces,
    ).to_legacy_dict()


__all__ = [
    "unique_text_values",
    "combined_shared_breakline_result",
    "corridor_general_shared_breakline_result",
    "corridor_region_transition_shared_breakline_result",
    "shared_breakline_adjacency_graph",
    "shared_breakline_audit",
]

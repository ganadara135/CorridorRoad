"""Region boundary continuity: what changes where two Regions meet.

The rule compares adjacent Applied Sections against the jump thresholds below
and reports the differences as diagnostic rows, together with the source range
and sample coverage of a Region and the intersection context around it. It
reads models only, so the document work that feeds it stays in the command.
"""

from __future__ import annotations

from ...common.model_fields import (
    intersection_row_by_id,
    role_count_summary,
    section_float_attr,
    section_region_id,
    section_station,
    section_structure_values,
    surface_point_role_counts,
    unique_join,
    unique_refs,
)


REGION_BOUNDARY_WIDTH_JUMP_THRESHOLD = 1.0
REGION_BOUNDARY_SUBGRADE_JUMP_THRESHOLD = 0.15
REGION_BOUNDARY_DAYLIGHT_WIDTH_JUMP_THRESHOLD = 1.0
REGION_BOUNDARY_DAYLIGHT_SLOPE_JUMP_THRESHOLD = 0.05


def region_boundary_diagnostic(severity: str, kind: str, message: str, boundary_side: str) -> dict[str, str]:
    return {
        "severity": str(severity or ""),
        "kind": str(kind or ""),
        "message": str(message or ""),
        "boundary_side": str(boundary_side or ""),
    }


def region_source_range_diagnostics(source_rows: list[object], row_index: int) -> list[dict[str, str]]:
    rows = list(source_rows or [])
    if row_index < 0 or row_index >= len(rows):
        return []
    diagnostics: list[dict[str, str]] = []
    current = rows[row_index]
    start = float(getattr(current, "station_start", 0.0) or 0.0)
    end = float(getattr(current, "station_end", 0.0) or 0.0)
    tolerance = 1.0e-6
    if row_index > 0:
        previous = rows[row_index - 1]
        previous_end = float(getattr(previous, "station_end", 0.0) or 0.0)
        if previous_end < start - tolerance:
            diagnostics.append(
                region_boundary_diagnostic(
                    "warning",
                    "region_source_gap_before",
                    f"STA {previous_end:.3f}->{start:.3f}: source Region gap before this row.",
                    "start",
                )
            )
        elif previous_end > start + tolerance:
            diagnostics.append(
                region_boundary_diagnostic(
                    "warning",
                    "region_source_overlap_before",
                    f"STA {start:.3f}->{previous_end:.3f}: source Region rows overlap before this row.",
                    "start",
                )
            )
    if row_index < len(rows) - 1:
        next_row = rows[row_index + 1]
        next_start = float(getattr(next_row, "station_start", 0.0) or 0.0)
        if end < next_start - tolerance:
            diagnostics.append(
                region_boundary_diagnostic(
                    "warning",
                    "region_source_gap_after",
                    f"STA {end:.3f}->{next_start:.3f}: source Region gap after this row.",
                    "end",
                )
            )
        elif end > next_start + tolerance:
            diagnostics.append(
                region_boundary_diagnostic(
                    "warning",
                    "region_source_overlap_after",
                    f"STA {next_start:.3f}->{end:.3f}: source Region rows overlap after this row.",
                    "end",
                )
            )
    return diagnostics


def region_sample_coverage_diagnostics(source_row, sections: list[object]) -> list[dict[str, str]]:
    start = float(getattr(source_row, "station_start", 0.0) or 0.0)
    end = float(getattr(source_row, "station_end", 0.0) or 0.0)
    low = min(start, end)
    high = max(start, end)
    ordered = sorted(list(sections or []), key=lambda section: section_station(section))
    if not ordered:
        return [
            region_boundary_diagnostic(
                "warning",
                "region_sample_missing",
                f"STA {low:.3f}->{high:.3f}: no Applied Section samples exist inside this Region.",
                "range",
            )
        ]
    diagnostics: list[dict[str, str]] = []
    first_station = section_station(ordered[0])
    last_station = section_station(ordered[-1])
    tolerance = 1.0e-6
    if first_station > low + tolerance:
        diagnostics.append(
            region_boundary_diagnostic(
                "warning",
                "region_sample_start_gap",
                f"STA {low:.3f}->{first_station:.3f}: Applied Section samples are missing at the Region start.",
                "start",
            )
        )
    if last_station < high - tolerance:
        diagnostics.append(
            region_boundary_diagnostic(
                "warning",
                "region_sample_end_gap",
                f"STA {last_station:.3f}->{high:.3f}: Applied Section samples are missing at the Region end.",
                "end",
            )
        )
    return diagnostics


def _intersection_model_mentions_region(intersection_model, intersection_id: str, region_id: str) -> bool:
    target_region = str(region_id or "").strip()
    if not target_region:
        return True
    refs: list[str] = []
    row = intersection_row_by_id(intersection_model, intersection_id)
    if row is not None:
        refs.extend(str(value or "") for value in list(getattr(row, "control_region_refs", []) or []))
        refs.extend(str(getattr(leg, "region_ref", "") or "") for leg in list(getattr(row, "leg_rows", []) or []))
    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if str(getattr(area, "intersection_id", "") or "").strip() == str(intersection_id or "").strip():
            refs.extend(str(value or "") for value in list(getattr(area, "control_region_refs", []) or []))
    return any(ref == target_region or ref.endswith(f"/{target_region}") for ref in refs if ref)


def region_intersection_context_diagnostics(source_row, sections: list[object], *, intersection_model=None) -> list[dict[str, str]]:
    source_ref = str(getattr(source_row, "intersection_ref", "") or "").strip()
    region_id = str(getattr(source_row, "region_id", "") or "").strip()
    active_refs = unique_refs(
        [
            str(getattr(section, "active_intersection_id", "") or "")
            for section in list(sections or [])
            if str(getattr(section, "active_intersection_id", "") or "").strip()
        ]
    )
    diagnostics: list[dict[str, str]] = []
    if source_ref:
        if intersection_model is None:
            diagnostics.append(
                region_boundary_diagnostic(
                    "warning",
                    "intersection_model_missing",
                    f"{source_ref}: Region is tagged as intersection-controlled but no IntersectionModel is available.",
                    "range",
                )
            )
        elif intersection_row_by_id(intersection_model, source_ref) is None:
            diagnostics.append(
                region_boundary_diagnostic(
                    "warning",
                    "intersection_ref_missing_in_model",
                    f"{source_ref}: Region intersection_ref is not present in IntersectionModel.",
                    "range",
                )
            )
        if sections and source_ref not in active_refs:
            diagnostics.append(
                region_boundary_diagnostic(
                    "warning",
                    "intersection_context_not_reflected_in_applied_sections",
                    f"{source_ref}: Applied Sections inside this Region do not carry the expected active intersection.",
                    "range",
                )
            )
        if intersection_model is not None and not _intersection_model_mentions_region(intersection_model, source_ref, region_id):
            diagnostics.append(
                region_boundary_diagnostic(
                    "warning",
                    "intersection_control_region_missing",
                    f"{source_ref}: IntersectionModel does not list this Region as a control Region.",
                    "range",
                )
            )
    elif active_refs:
        diagnostics.append(
            region_boundary_diagnostic(
                "warning",
                "intersection_context_without_region_source_ref",
                f"{', '.join(active_refs)}: Applied Sections carry intersection context, but Region source has no intersection_ref.",
                "range",
            )
        )
    if len(active_refs) > 1:
        diagnostics.append(
            region_boundary_diagnostic(
                "warning",
                "intersection_context_overlap",
                f"Multiple active intersections are present in this Region: {', '.join(active_refs)}.",
                "range",
            )
        )
    return diagnostics


def region_boundary_diagnostics(left, right, *, boundary_side: str) -> list[dict[str, str]]:
    if left is None or right is None:
        return []
    diagnostics: list[dict[str, str]] = []
    left_station = section_station(left)
    right_station = section_station(right)
    station_text = f"STA {left_station:.3f}->{right_station:.3f}"
    left_region = section_region_id(left)
    right_region = section_region_id(right)
    if left_region != right_region:
        diagnostics.append(
            region_boundary_diagnostic(
                "info",
                "region_context_change",
                f"{station_text}: {left_region} -> {right_region}.",
                boundary_side,
            )
        )
    for attr, label, threshold, kind in (
        ("surface_left_width", "left design width", REGION_BOUNDARY_WIDTH_JUMP_THRESHOLD, "region_boundary_width_jump"),
        ("surface_right_width", "right design width", REGION_BOUNDARY_WIDTH_JUMP_THRESHOLD, "region_boundary_width_jump"),
        ("subgrade_depth", "subgrade depth", REGION_BOUNDARY_SUBGRADE_JUMP_THRESHOLD, "region_boundary_subgrade_jump"),
        ("daylight_left_width", "left daylight width", REGION_BOUNDARY_DAYLIGHT_WIDTH_JUMP_THRESHOLD, "region_boundary_daylight_width_jump"),
        ("daylight_right_width", "right daylight width", REGION_BOUNDARY_DAYLIGHT_WIDTH_JUMP_THRESHOLD, "region_boundary_daylight_width_jump"),
        ("daylight_left_slope", "left daylight slope", REGION_BOUNDARY_DAYLIGHT_SLOPE_JUMP_THRESHOLD, "region_boundary_daylight_slope_jump"),
        ("daylight_right_slope", "right daylight slope", REGION_BOUNDARY_DAYLIGHT_SLOPE_JUMP_THRESHOLD, "region_boundary_daylight_slope_jump"),
    ):
        delta = abs(section_float_attr(right, attr) - section_float_attr(left, attr))
        if delta > threshold + 1.0e-9:
            diagnostics.append(
                region_boundary_diagnostic(
                    "warning",
                    kind,
                    f"{station_text}: {label} changes by {delta:.3f}.",
                    boundary_side,
                )
            )
    left_roles = surface_point_role_counts(left)
    right_roles = surface_point_role_counts(right)
    if left_roles != right_roles:
        diagnostics.append(
            region_boundary_diagnostic(
                "warning",
                "region_boundary_point_role_mismatch",
                f"{station_text}: surface point roles differ ({role_count_summary(left_roles)} -> {role_count_summary(right_roles)}).",
                boundary_side,
            )
        )
    for role, kind, label in (
        ("ditch_surface", "region_boundary_ditch_mismatch", "ditch"),
        ("bench_surface", "region_boundary_bench_mismatch", "bench"),
    ):
        left_count = left_roles.get(role, 0)
        right_count = right_roles.get(role, 0)
        if bool(left_count) != bool(right_count):
            diagnostics.append(
                region_boundary_diagnostic(
                    "warning",
                    kind,
                    f"{station_text}: {label} rows exist on one side only ({left_count} -> {right_count}).",
                    boundary_side,
                )
            )
    left_structures = set(section_structure_values([left]))
    right_structures = set(section_structure_values([right]))
    if left_structures != right_structures:
        diagnostics.append(
            region_boundary_diagnostic(
                "info",
                "region_boundary_structure_context_change",
                f"{station_text}: structure context changes ({unique_join(sorted(left_structures)) or '-'} -> {unique_join(sorted(right_structures)) or '-'}).",
                boundary_side,
            )
        )
    return diagnostics


def region_boundary_status(diagnostics: list[dict[str, str]]) -> str:
    severities = {str(row.get("severity", "") or "") for row in list(diagnostics or [])}
    if "error" in severities:
        return "error"
    if "warning" in severities:
        return "warn"
    return "ready"


def region_boundary_diagnostic_summary(diagnostics: list[dict[str, str]], *, max_items: int = 2) -> str:
    if not diagnostics:
        return "ok"
    warning_count = sum(1 for row in diagnostics if str(row.get("severity", "") or "") == "warning")
    info_count = sum(1 for row in diagnostics if str(row.get("severity", "") or "") == "info")
    messages = [str(row.get("message", "") or "") for row in diagnostics if str(row.get("severity", "") or "") != "info"]
    if not messages:
        messages = [str(row.get("message", "") or "") for row in diagnostics]
    clipped = [message for message in messages if message][: max(1, int(max_items))]
    suffix = ""
    if len(messages) > len(clipped):
        suffix = f"; +{len(messages) - len(clipped)} more"
    prefix = f"{warning_count} warning(s), {info_count} info"
    return f"{prefix}: {'; '.join(clipped)}{suffix}"


__all__ = [
    "REGION_BOUNDARY_WIDTH_JUMP_THRESHOLD",
    "REGION_BOUNDARY_SUBGRADE_JUMP_THRESHOLD",
    "REGION_BOUNDARY_DAYLIGHT_WIDTH_JUMP_THRESHOLD",
    "REGION_BOUNDARY_DAYLIGHT_SLOPE_JUMP_THRESHOLD",
    "region_boundary_diagnostic",
    "region_source_range_diagnostics",
    "region_sample_coverage_diagnostics",
    "region_intersection_context_diagnostics",
    "region_boundary_diagnostics",
    "region_boundary_status",
    "region_boundary_diagnostic_summary",
]

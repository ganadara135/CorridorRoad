"""Region review rows of the Build Parametric panel.

Turns the Applied Sections and the Region, Structure, Drainage and Intersection sources the
command reads into one review row per Region: its station range, assembly, context summaries and
boundary continuity diagnostics. The rows' generated-object check reads the document, so the
command passes it in. Moved from `commands/cmd_build_corridor.py` (GR-7).
"""

from __future__ import annotations

from typing import Callable

from ...common.model_fields import (
    intersection_row_by_id,
    section_region_id,
    section_station,
    section_structure_values,
    unique_join,
    unique_refs,
)
from ...services.evaluation.region_boundary_continuity_evaluation_service import (
    region_boundary_diagnostic_summary,
    region_boundary_diagnostics,
    region_boundary_status,
    region_intersection_context_diagnostics,
    region_sample_coverage_diagnostics,
    region_source_range_diagnostics,
)
from ...services.evaluation.station_context_resolver import StationContextResolver


def _display_source_id(value: object, prefix: str) -> str:
    text = str(value or "")
    if prefix and text.startswith(prefix):
        return text[len(prefix) :]
    return text


def _station_ordered_applied_sections(applied_section_set) -> list[object]:
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    output: list[object] = []
    for row in sorted(
        list(getattr(applied_section_set, "station_rows", []) or []),
        key=lambda item: float(getattr(item, "station", 0.0) or 0.0),
    ):
        section = sections.get(str(getattr(row, "applied_section_id", "") or ""))
        if section is not None:
            output.append(section)
    if output:
        return output
    return sorted(list(getattr(applied_section_set, "sections", []) or []), key=lambda section: section_station(section))


def _contiguous_region_groups(sections: list[object]) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    for section in list(sections or []):
        region_id = section_region_id(section)
        if not groups or str(groups[-1].get("region_id", "") or "") != region_id:
            groups.append({"region_id": region_id, "sections": [section]})
        else:
            groups[-1]["sections"].append(section)
    for group in groups:
        group_sections = list(group.get("sections", []) or [])
        stations = [section_station(section) for section in group_sections]
        group["station_start"] = min(stations) if stations else 0.0
        group["station_end"] = max(stations) if stations else 0.0
    return groups


def _region_source_rows(region_model) -> list[object]:
    if region_model is None:
        return []
    rows = [
        row
        for row in list(getattr(region_model, "region_rows", []) or [])
        if str(getattr(row, "region_id", "") or "").strip()
    ]
    return sorted(
        rows,
        key=lambda row: (
            float(getattr(row, "station_start", 0.0) or 0.0),
            float(getattr(row, "station_end", 0.0) or 0.0),
            int(getattr(row, "region_index", 0) or 0),
            str(getattr(row, "region_id", "") or ""),
        ),
    )


def _sections_for_region_model(sections: list[object], region_model) -> list[object]:
    alignment_id = str(getattr(region_model, "alignment_id", "") or "").strip()
    if not alignment_id:
        return list(sections or [])
    return [
        section
        for section in list(sections or [])
        if str(getattr(section, "alignment_id", "") or "").strip() == alignment_id
    ]


def _region_boundary_rows_from_source_regions(
    source_rows: list[object],
    sections: list[object],
    *,
    generated_object_summary: Callable[[dict[str, object]], dict[str, object]],
    region_model=None,
    structure_model=None,
    drainage_model=None,
    intersection_model=None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    section_groups = [
        _sections_for_source_region_row(sections, row)
        for row in list(source_rows or [])
    ]
    for index, source_row in enumerate(list(source_rows or [])):
        group_sections = section_groups[index]
        first = group_sections[0] if group_sections else None
        last = group_sections[-1] if group_sections else None
        diagnostics: list[dict[str, str]] = []
        diagnostics.extend(region_source_range_diagnostics(source_rows, index))
        diagnostics.extend(region_sample_coverage_diagnostics(source_row, group_sections))
        intersection_diagnostics = region_intersection_context_diagnostics(
            source_row,
            group_sections,
            intersection_model=intersection_model,
        )
        diagnostics.extend(intersection_diagnostics)
        if index > 0:
            previous_last = section_groups[index - 1][-1] if section_groups[index - 1] else None
            diagnostics.extend(region_boundary_diagnostics(previous_last, first, boundary_side="start"))
        if index < len(source_rows) - 1:
            next_first = section_groups[index + 1][0] if section_groups[index + 1] else None
            diagnostics.extend(region_boundary_diagnostics(last, next_first, boundary_side="end"))
        boundary_status = region_boundary_status(diagnostics)
        row = {
            "alignment_id": str(getattr(region_model, "alignment_id", "") or ""),
            "region_id": str(getattr(source_row, "region_id", "") or ""),
            "station_start": float(getattr(source_row, "station_start", 0.0) or 0.0),
            "station_end": float(getattr(source_row, "station_end", 0.0) or 0.0),
            "assembly": str(getattr(source_row, "assembly_ref", "") or "") or unique_join(_section_text_values(group_sections, "assembly_id")),
            "structure": _region_group_structure_summary(
                group_sections,
                region_model=region_model,
                structure_model=structure_model,
            ),
            "drainage": _region_group_drainage_summary(
                group_sections,
                region_model=region_model,
                drainage_model=drainage_model,
            ),
            "intersection": _region_group_intersection_summary(
                source_row,
                group_sections,
                intersection_model=intersection_model,
            ),
            "surface_status": _region_group_surface_status(group_sections),
            "boundary_status": boundary_status,
            "diagnostics": region_boundary_diagnostic_summary(diagnostics),
            "diagnostic_count": len(diagnostics),
            "intersection_diagnostic_count": len(intersection_diagnostics),
        }
        row.update(generated_object_summary(row))
        rows.append(row)
    return rows


def _sections_for_source_region_row(sections: list[object], source_row) -> list[object]:
    region_id = str(getattr(source_row, "region_id", "") or "")
    try:
        start = float(getattr(source_row, "station_start", 0.0) or 0.0)
        end = float(getattr(source_row, "station_end", start) or start)
    except Exception:
        start = 0.0
        end = 0.0
    low = min(start, end)
    high = max(start, end)
    tolerance = 1.0e-6
    rows = [
        section
        for section in list(sections or [])
        if section_region_id(section) == region_id
        and low - tolerance <= section_station(section) <= high + tolerance
    ]
    return sorted(rows, key=lambda section: section_station(section))


def _section_text_values(sections: list[object], attr: str) -> list[str]:
    values: list[str] = []
    for section in list(sections or []):
        text = str(getattr(section, attr, "") or "").strip()
        if text:
            values.append(text)
    return values


def _region_group_structure_summary(sections: list[object], *, region_model=None, structure_model=None) -> str:
    values = list(section_structure_values(sections))
    if region_model is not None and structure_model is not None:
        for context in _region_group_station_contexts(
            sections,
            region_model=region_model,
            structure_model=structure_model,
        ):
            result = getattr(context, "structure_result", None)
            values.extend(
                str(value or "").strip()
                for value in list(getattr(result, "active_structure_ids", []) or [])
                if str(value or "").strip()
            )
    return unique_join(values) or "-"


def _region_group_station_contexts(
    sections: list[object],
    *,
    region_model=None,
    structure_model=None,
    drainage_model=None,
) -> list[object]:
    if region_model is None or not sections:
        return []
    resolver = StationContextResolver()
    contexts: list[object] = []
    for section in list(sections or []):
        try:
            context = resolver.resolve(
                region_model=region_model,
                structure_model=structure_model,
                drainage_model=drainage_model,
                station=section_station(section),
            )
        except Exception:
            continue
        section_region = section_region_id(section)
        context_region = str(getattr(getattr(context, "region_context", None), "region_id", "") or "")
        if section_region and context_region and section_region != context_region:
            continue
        contexts.append(context)
    return contexts


def _region_group_drainage_summary(sections: list[object], *, region_model=None, drainage_model=None) -> str:
    drainage_refs: list[str] = []
    if region_model is not None and drainage_model is not None:
        for context in _region_group_station_contexts(
            sections,
            region_model=region_model,
            drainage_model=drainage_model,
        ):
            drainage_refs.extend(
                str(value or "").strip()
                for value in list(getattr(context, "active_drainage_refs", []) or [])
                if str(value or "").strip()
            )
    ditch_count = sum(
        1
        for section in list(sections or [])
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "ditch_surface"
    )
    summary_parts: list[str] = []
    drainage_summary = unique_join(drainage_refs)
    if drainage_summary:
        summary_parts.append(drainage_summary)
    if ditch_count:
        summary_parts.append(f"ditch points: {ditch_count}")
    return "; ".join(summary_parts) if summary_parts else "-"


def _region_group_intersection_summary(source_row, sections: list[object], *, intersection_model=None) -> str:
    source_ref = str(getattr(source_row, "intersection_ref", "") or "").strip() if source_row is not None else ""
    active_refs = unique_refs(
        [
            str(getattr(section, "active_intersection_id", "") or "")
            for section in list(sections or [])
            if str(getattr(section, "active_intersection_id", "") or "").strip()
        ]
    )
    leg_roles = unique_refs(
        [
            str(getattr(section, "active_intersection_leg_role", "") or "")
            for section in list(sections or [])
            if str(getattr(section, "active_intersection_leg_role", "") or "").strip()
        ]
    )
    parts: list[str] = []
    if source_ref:
        parts.append(_display_source_id(source_ref, "intersection:"))
    elif active_refs:
        parts.extend(_display_source_id(ref, "intersection:") for ref in active_refs)
    if leg_roles:
        parts.append("/".join(leg_roles))
    if source_ref and intersection_model is not None and intersection_row_by_id(intersection_model, source_ref) is None:
        parts.append("unlinked")
    return " | ".join(part for part in parts if part) or "-"


def _region_group_surface_status(sections: list[object]) -> str:
    if not sections:
        return "missing"
    return "ready" if all(getattr(section, "frame", None) is not None for section in sections) else "warn"


def region_boundary_review_rows(
    applied,
    *,
    region_models: list[object],
    structure_model=None,
    drainage_model=None,
    intersection_model=None,
    generated_object_summary: Callable[[dict[str, object]], dict[str, object]],
) -> list[dict[str, object]]:
    """One review row per Region, from the Region sources when they have rows, else from the
    Region ids the Applied Sections carry. `generated_object_summary` adds a row's
    generated-object fields."""

    if applied is None:
        return [
            {
                "alignment_id": "",
                "region_id": "",
                "station_start": "",
                "station_end": "",
                "assembly": "",
                "structure": "",
                "drainage": "",
                "surface_status": "missing",
                "boundary_status": "missing",
                "diagnostics": "Applied Sections are required before Region boundary review.",
            }
        ]
    sections = _station_ordered_applied_sections(applied)
    if not sections:
        return [
            {
                "alignment_id": "",
                "region_id": "",
                "station_start": "",
                "station_end": "",
                "assembly": "",
                "structure": "",
                "drainage": "",
                "surface_status": "missing",
                "boundary_status": "missing",
                "diagnostics": "No Applied Section station rows are available.",
            }
        ]
    region_model = region_models[0] if region_models else None
    source_region_groups = [
        (model, _region_source_rows(model))
        for model in region_models
        if _region_source_rows(model)
    ]
    if source_region_groups:
        rows: list[dict[str, object]] = []
        for model, source_rows in source_region_groups:
            alignment_sections = _sections_for_region_model(sections, model)
            rows.extend(
                _region_boundary_rows_from_source_regions(
                    source_rows,
                    alignment_sections,
                    generated_object_summary=generated_object_summary,
                    region_model=model,
                    structure_model=structure_model,
                    drainage_model=drainage_model,
                    intersection_model=intersection_model,
                )
            )
        return rows
    groups = _contiguous_region_groups(sections)
    rows: list[dict[str, object]] = []
    for index, group in enumerate(groups):
        group_sections = list(group.get("sections", []) or [])
        first = group_sections[0]
        last = group_sections[-1]
        diagnostics: list[dict[str, str]] = []
        if index > 0:
            diagnostics.extend(region_boundary_diagnostics(groups[index - 1]["sections"][-1], first, boundary_side="start"))
        if index < len(groups) - 1:
            diagnostics.extend(region_boundary_diagnostics(last, groups[index + 1]["sections"][0], boundary_side="end"))
        boundary_status = region_boundary_status(diagnostics)
        row = {
            "alignment_id": unique_join(_section_text_values(group_sections, "alignment_id")),
            "region_id": str(group.get("region_id", "") or ""),
            "station_start": float(group.get("station_start", 0.0) or 0.0),
            "station_end": float(group.get("station_end", 0.0) or 0.0),
            "assembly": unique_join(_section_text_values(group_sections, "assembly_id")),
            "structure": _region_group_structure_summary(
                group_sections,
                region_model=region_model,
                structure_model=structure_model,
            ),
            "drainage": _region_group_drainage_summary(
                group_sections,
                region_model=region_model,
                drainage_model=drainage_model,
            ),
            "intersection": _region_group_intersection_summary(None, group_sections, intersection_model=intersection_model),
            "surface_status": _region_group_surface_status(group_sections),
            "boundary_status": boundary_status,
            "diagnostics": region_boundary_diagnostic_summary(diagnostics),
            "diagnostic_count": len(diagnostics),
        }
        row.update(generated_object_summary(row))
        rows.append(row)
    return rows


__all__ = [
    "region_boundary_review_rows",
]

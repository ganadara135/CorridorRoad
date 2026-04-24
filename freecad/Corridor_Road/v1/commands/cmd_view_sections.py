"""Section viewer command bridge for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from ..services.evaluation import LegacyDocumentAdapter
from ..services.mapping import SectionOutputMapper
from ..ui.common import clear_ui_context, get_ui_context
from ..ui.viewers import CrossSectionViewerTaskPanel
from .selection_context import selected_section_target
from .cmd_earthwork_balance import build_demo_earthwork_report


def _safe_bool(value) -> bool:
    """Return True only for explicit truthy values without raising."""

    try:
        return bool(value)
    except Exception:
        return False


def _build_result_state(
    *,
    state: str,
    reason: str = "",
) -> dict[str, str]:
    """Build a normalized viewer result-state payload."""

    return {
        "state": str(state or "unknown"),
        "reason": str(reason or "").strip(),
    }


def _status_text(obj) -> str:
    """Return a normalized legacy status text for one object."""

    return str(getattr(obj, "Status", "") or "").strip()


def _needs_recompute(obj) -> bool:
    """Return whether one legacy object exposes a recompute-needed signal."""

    return _safe_bool(getattr(obj, "NeedsRecompute", False))


def _state_from_status_text(status_text: str) -> tuple[str | None, str]:
    """Map one legacy status string into a normalized viewer state."""

    text = str(status_text or "").strip()
    upper_text = text.upper()
    if not text:
        return None, ""
    if upper_text.startswith("ERROR") or upper_text.startswith("CANCELED"):
        return "blocked", text
    if upper_text.startswith("MISSING ") or upper_text in (
        "NO STATIONS",
        "NO SECTION WIRES",
        "ALIGNMENT LENGTH IS ZERO",
        "INSUFFICIENT STATIONS",
        "INSUFFICIENT SAMPLED POINTS",
        "MISSING ALIGNMENT",
    ):
        return "blocked", text
    if "NEEDS_RECOMPUTE" in upper_text:
        return "rebuild_needed", text
    if upper_text.startswith("WARN") or "WARN" in upper_text:
        return "stale", text
    return None, text


def _diagnostic_state(
    diagnostic_rows: list[dict[str, object]] | None,
) -> tuple[str | None, str]:
    """Map normalized diagnostic rows into one viewer state when relevant."""

    rows = list(diagnostic_rows or [])
    severities = {str((row or {}).get("severity", "") or "").strip().lower() for row in rows}
    if "error" in severities:
        return "blocked", "Diagnostic rows contain error severity."
    if "warning" in severities or "warn" in severities:
        return "stale", "Diagnostic rows contain warning severity."
    return None, ""


def _resolve_result_state(
    *,
    explicit_result_state: dict[str, object] | None = None,
    diagnostic_rows: list[dict[str, object]] | None = None,
    legacy_objects: dict[str, object] | None = None,
) -> dict[str, str]:
    """Resolve the normalized section-viewer result state."""

    explicit = dict(explicit_result_state or {})
    explicit_state = str(explicit.get("state", "") or "").strip()
    explicit_reason = str(explicit.get("reason", "") or "").strip()
    if explicit_state:
        return _build_result_state(state=explicit_state, reason=explicit_reason)

    objects = dict(legacy_objects or {})
    for key in (
        "section_set",
        "corridor",
        "cut_fill_calc",
        "typical_section",
        "region_plan",
        "structure_set",
    ):
        obj = objects.get(key)
        if obj is None:
            continue
        if _needs_recompute(obj):
            label = str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or key).strip()
            return _build_result_state(
                state="rebuild_needed",
                reason=f"{label} is marked as needing recompute.",
            )
        state_value, state_reason = _state_from_status_text(_status_text(obj))
        if state_value:
            return _build_result_state(state=state_value, reason=state_reason)

    diagnostic_state, diagnostic_reason = _diagnostic_state(diagnostic_rows)
    if diagnostic_state:
        return _build_result_state(state=diagnostic_state, reason=diagnostic_reason)

    return _build_result_state(
        state="current",
        reason=explicit_reason or "Built from current section viewer payload.",
    )


def _build_source_inspector(
    *,
    applied_section,
    section_output,
    station_row: dict[str, object] | None,
    section_set=None,
    typical_section=None,
    region_plan=None,
    structure_set=None,
    viewer_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a compact source-inspector payload for the v1 section viewer."""

    viewer_context = dict(viewer_context or {})
    focused = dict(viewer_context.get("focused_component", {}) or {})
    focused_id = str(focused.get("id", "") or "").strip()
    focused_kind = str(focused.get("type", "") or "").strip()
    focused_side = str(focused.get("side", "") or "").strip()

    selected_component = None
    for row in list(getattr(section_output, "component_rows", []) or []):
        row_id = str(getattr(row, "component_id", "") or "").strip()
        if focused_id and row_id == focused_id:
            selected_component = row
            break
    if selected_component is None:
        component_rows = list(getattr(section_output, "component_rows", []) or [])
        if component_rows:
            selected_component = component_rows[0]

    component_id = focused_id or str(getattr(selected_component, "component_id", "") or "").strip()
    component_kind = focused_kind or str(getattr(selected_component, "kind", "") or "").strip()
    component_side = focused_side or str(focused.get("scope", "") or "").strip()
    owner_template = str(getattr(applied_section, "template_id", "") or "").strip()
    owner_region = str(getattr(applied_section, "region_id", "") or "").strip()
    section_set_label = str(getattr(section_set, "Label", "") or getattr(section_set, "Name", "") or "").strip()
    template_label = str(getattr(typical_section, "Label", "") or getattr(typical_section, "Name", "") or owner_template).strip()
    region_label = str(getattr(region_plan, "Label", "") or getattr(region_plan, "Name", "") or owner_region).strip()
    structure_label = str(getattr(structure_set, "Label", "") or getattr(structure_set, "Name", "") or "").strip()
    owner_structure = structure_label or str(viewer_context.get("structure_summary", "") or "").strip()

    unresolved_fields = []
    if not section_set_label:
        unresolved_fields.append("section_set")
    if not template_label and not owner_template:
        unresolved_fields.append("template")
    if not region_label and not owner_region:
        unresolved_fields.append("region")
    if not owner_structure:
        unresolved_fields.append("structure")

    if len(unresolved_fields) == 0:
        ownership_status = "resolved"
    elif len(unresolved_fields) == 4:
        ownership_status = "unresolved"
    else:
        ownership_status = "partial"

    return {
        "station_label": str((station_row or {}).get("label", "") or "").strip(),
        "section_set_label": section_set_label,
        "template_label": template_label,
        "region_label": region_label,
        "structure_label": structure_label,
        "component_id": component_id,
        "component_kind": component_kind,
        "component_side": component_side,
        "owner_template": owner_template,
        "owner_region": owner_region,
        "owner_structure": owner_structure,
        "ownership_status": ownership_status,
        "unresolved_fields": list(unresolved_fields),
        "component_count": int(len(list(getattr(section_output, "component_rows", []) or []))),
        "quantity_count": int(len(list(getattr(section_output, "quantity_rows", []) or []))),
    }


def _build_terrain_review_rows(
    *,
    applied_section,
    station_row: dict[str, object] | None,
) -> list[dict[str, str]]:
    """Build minimal terrain review rows for the v1 section viewer."""

    station_label = str((station_row or {}).get("label", "") or "").strip()
    rows = [
        {
            "kind": "terrain_context",
            "label": "Terrain Source",
            "value": "TIN-first section review",
            "notes": "Section review is driven by TIN-based terrain handling.",
        }
    ]
    if station_label:
        rows.append(
            {
                "kind": "station_context",
                "label": "Focused Station",
                "value": station_label,
                "notes": "",
            }
        )
    region_id = str(getattr(applied_section, "region_id", "") or "").strip()
    if region_id:
        rows.append(
            {
                "kind": "region_context",
                "label": "Region Context",
                "value": region_id,
                "notes": "Terrain behavior should be reviewed together with region policy.",
            }
        )
    return rows


def _build_structure_review_rows(
    *,
    viewer_context: dict[str, object] | None,
    region_plan=None,
) -> list[dict[str, str]]:
    """Build minimal structure review rows for the v1 section viewer."""

    viewer_context = dict(viewer_context or {})
    rows = []
    for value in list(viewer_context.get("structure_rows", []) or [])[:6]:
        text = str(value or "").strip()
        if text:
            rows.append(
                {
                    "kind": "structure_context",
                    "label": "Structure Context",
                    "value": text,
                    "notes": "",
                }
            )
    structure_summary = str(viewer_context.get("structure_summary", "") or "").strip()
    if structure_summary:
        rows.insert(
            0,
            {
                "kind": "structure_summary",
                "label": "Structure Summary",
                "value": structure_summary,
                "notes": "",
            },
        )
    if not rows and region_plan is not None:
        rows.append(
            {
                "kind": "structure_fallback",
                "label": "Structure Context",
                "value": str(getattr(region_plan, "Label", "") or getattr(region_plan, "Name", "") or "").strip(),
                "notes": "No explicit structure rows were provided in the current preview payload.",
            }
        )
    return rows


def _nearest_earthwork_balance_row(balance_rows: list[object] | None, station: float | None):
    """Resolve the nearest earthwork balance row for one station."""

    rows = list(balance_rows or [])
    if not rows:
        return None
    if station is None:
        return rows[0]
    return min(rows, key=lambda row: _earthwork_station_distance(row, station))


def _earthwork_station_distance(row, station: float) -> float:
    """Measure distance from one station to an earthwork window row."""

    station_start = getattr(row, "station_start", None)
    station_end = getattr(row, "station_end", None)
    if station_start is None and station_end is None:
        return abs(float(station))
    if station_start is None:
        station_start = station_end
    if station_end is None:
        station_end = station_start
    lo = float(station_start)
    hi = float(station_end)
    if lo > hi:
        lo, hi = hi, lo
    if lo <= float(station) <= hi:
        return 0.0
    return min(abs(float(station) - lo), abs(float(station) - hi))


def _earthwork_zone_kind(cut_value: float, fill_value: float) -> str:
    """Classify one earthwork hint row from cut/fill values."""

    delta = float(cut_value) - float(fill_value)
    if delta > 0.0:
        return "surplus_zone"
    if delta < 0.0:
        return "deficit_zone"
    return "balanced_zone"


def _build_earthwork_hint_rows(
    *,
    earthwork_model=None,
    station_row: dict[str, object] | None,
    cut_fill_calc=None,
) -> list[dict[str, str]]:
    """Build minimal earthwork hint rows for the section viewer."""

    station_value = None
    if station_row:
        try:
            station_value = float(station_row.get("station", 0.0) or 0.0)
        except Exception:
            station_value = None
    focused_row = _nearest_earthwork_balance_row(
        getattr(earthwork_model, "balance_rows", []) or [],
        station_value,
    )
    if focused_row is None:
        return []

    station_start = float(getattr(focused_row, "station_start", 0.0) or 0.0)
    station_end = float(getattr(focused_row, "station_end", 0.0) or 0.0)
    cut_value = float(getattr(focused_row, "cut_value", 0.0) or 0.0)
    fill_value = float(getattr(focused_row, "fill_value", 0.0) or 0.0)
    balance_ratio = float(getattr(focused_row, "balance_ratio", 0.0) or 0.0)
    zone_kind = _earthwork_zone_kind(cut_value, fill_value)
    calc_label = str(getattr(cut_fill_calc, "Label", "") or getattr(cut_fill_calc, "Name", "") or "").strip()

    return [
        {
            "kind": "earthwork_window",
            "label": "Earthwork Window",
            "value": f"{station_start:.3f} -> {station_end:.3f}",
            "notes": "Nearest earthwork window for the current section station.",
        },
        {
            "kind": "earthwork_cut_fill",
            "label": "Cut / Fill",
            "value": f"{cut_value:.3f} / {fill_value:.3f} m3",
            "notes": f"Balance ratio {balance_ratio:.3f}",
        },
        {
            "kind": "earthwork_state",
            "label": "Earthwork State",
            "value": zone_kind,
            "notes": f"Source={calc_label}" if calc_label else "",
        },
    ]


def _build_review_marker_rows(
    *,
    station_row: dict[str, object] | None,
    viewer_context: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    """Build placeholder review-marker rows for the section viewer."""

    viewer_context = dict(viewer_context or {})
    station_label = str((station_row or {}).get("label", "") or "").strip() or "Current station"
    focused = dict(viewer_context.get("focused_component", {}) or {})
    focused_label = str(focused.get("label", "") or "").strip()
    notes = "Placeholder only; persistent bookmark storage is not implemented yet."
    if focused_label:
        notes = f"{notes} Focus={focused_label}"
    return [
        {
            "kind": "review_bookmark_placeholder",
            "label": "Bookmark Slot",
            "value": station_label,
            "notes": notes,
        },
        {
            "kind": "review_issue_placeholder",
            "label": "Issue Marker Slot",
            "value": focused_label or "(no focused component)",
            "notes": "Use this slot for future section review issue markers.",
        },
    ]


def _build_diagnostic_review_rows(
    *,
    section_output,
    viewer_context: dict[str, object] | None,
) -> list[dict[str, str]]:
    """Normalize diagnostic rows for the v1 section viewer."""

    viewer_context = dict(viewer_context or {})
    rows = [
        {
            "severity": str(getattr(row, "severity", "") or "").strip(),
            "kind": str(getattr(row, "kind", "") or "").strip(),
            "message": str(getattr(row, "message", "") or "").strip(),
            "notes": str(getattr(row, "notes", "") or "").strip(),
        }
        for row in list(getattr(section_output, "diagnostic_rows", []) or [])
    ]
    if not rows:
        for token in list(viewer_context.get("diagnostic_tokens", []) or [])[:6]:
            text = str(token or "").strip()
            if text:
                rows.append(
                    {
                        "severity": "info",
                        "kind": "viewer_context",
                        "message": text,
                        "notes": "",
                    }
                )
    return rows


def _build_key_station_rows(
    station_rows: list[dict[str, object]] | None,
    *,
    current_station: float | None,
) -> list[dict[str, object]]:
    """Build a compact key-station navigation payload around one current station."""

    rows = [dict(row or {}) for row in list(station_rows or [])]
    if not rows:
        return []

    if current_station is None:
        current_index = 0
    else:
        current_index = min(
            range(len(rows)),
            key=lambda idx: abs(float(rows[idx].get("station", 0.0) or 0.0) - float(current_station)),
        )

    candidate_indexes = {
        0,
        max(0, current_index - 2),
        max(0, current_index - 1),
        current_index,
        min(len(rows) - 1, current_index + 1),
        min(len(rows) - 1, current_index + 2),
        len(rows) - 1,
    }

    result = []
    for output_index, row_index in enumerate(sorted(candidate_indexes)):
        row = dict(rows[row_index])
        row["index"] = row_index
        row["is_current"] = bool(row_index == current_index)
        if row_index == 0:
            row["navigation_kind"] = "first"
        elif row_index == len(rows) - 1:
            row["navigation_kind"] = "last"
        elif row_index == current_index:
            row["navigation_kind"] = "current"
        elif row_index < current_index:
            row["navigation_kind"] = "previous"
        else:
            row["navigation_kind"] = "next"
        row["navigation_order"] = output_index
        result.append(row)
    return result


def build_document_section_preview(
    document,
    *,
    preferred_section_set=None,
    preferred_station: float | None = None,
) -> dict[str, object] | None:
    """Build a v1 section viewer payload from a FreeCAD document when possible."""

    adapter = LegacyDocumentAdapter()
    project = adapter._find_project(document)
    bundle = adapter.build_preview_bundle(
        document,
        preferred_section_set=preferred_section_set,
    )
    if bundle is None or not bundle.applied_section_set.sections:
        return None

    section_set = preferred_section_set or adapter._resolve_section_set(
        project,
        document,
        preferred_section_set=preferred_section_set,
    )
    typical_section = adapter._resolve_typical_section(project, section_set, document)
    region_plan = adapter._resolve_region_plan(project, section_set, document)
    viewer_station_rows = adapter.viewer_station_rows(section_set) if section_set is not None else []
    station_row = adapter.nearest_station_row(section_set, preferred_station=preferred_station)
    target_station = (
        adapter._safe_float(station_row.get("station", 0.0), 0.0)
        if station_row is not None
        else bundle.applied_section_set.sections[0].station
    )
    applied_section = min(
        list(bundle.applied_section_set.sections),
        key=lambda row: abs(float(row.station) - float(target_station)),
    )
    section_output = SectionOutputMapper().map_applied_section(applied_section)
    station_payload = station_row or {"station": applied_section.station, "label": f"STA {applied_section.station:.3f}"}
    viewer_context = {}
    legacy_objects = {
        "project": project,
        "section_set": section_set,
        "typical_section": typical_section,
        "region_plan": region_plan,
        "corridor": getattr(project, "Corridor", None) if project is not None else None,
        "cut_fill_calc": getattr(project, "CutFillCalc", None) if project is not None else None,
        "structure_set": getattr(project, "StructureSet", None) if project is not None else None,
    }
    diagnostic_rows = _build_diagnostic_review_rows(
        section_output=section_output,
        viewer_context=viewer_context,
    )
    earthwork_hint_rows = _build_earthwork_hint_rows(
        earthwork_model=bundle.earthwork_model,
        station_row=station_payload,
        cut_fill_calc=legacy_objects.get("cut_fill_calc"),
    )
    review_marker_rows = _build_review_marker_rows(
        station_row=station_payload,
        viewer_context=viewer_context,
    )
    return {
        "applied_section": applied_section,
        "section_output": section_output,
        "station_row": station_payload,
        "result_state": _resolve_result_state(
            diagnostic_rows=diagnostic_rows,
            legacy_objects=legacy_objects,
        ),
        "source_inspector": _build_source_inspector(
            applied_section=applied_section,
            section_output=section_output,
            station_row=station_payload,
            section_set=section_set,
            typical_section=typical_section,
            region_plan=region_plan,
            structure_set=legacy_objects.get("structure_set"),
        ),
        "terrain_rows": _build_terrain_review_rows(
            applied_section=applied_section,
            station_row=station_payload,
        ),
        "structure_rows": _build_structure_review_rows(
            viewer_context=viewer_context,
            region_plan=region_plan,
        ),
        "earthwork_hint_rows": earthwork_hint_rows,
        "review_marker_rows": review_marker_rows,
        "diagnostic_rows": diagnostic_rows,
        "key_station_rows": _build_key_station_rows(
            viewer_station_rows,
            current_station=target_station,
        ),
        "legacy_objects": legacy_objects,
    }


def build_demo_section_preview(document_label: str = "") -> dict[str, object]:
    """Build a minimal section viewer payload for the v1 bridge."""

    report = build_demo_earthwork_report(document_label=document_label)
    applied_section = report["applied_section_set"].sections[0]
    section_output = SectionOutputMapper().map_applied_section(applied_section)

    return {
        "applied_section": applied_section,
        "section_output": section_output,
        "station_row": {"station": applied_section.station, "label": f"STA {applied_section.station:.3f}"},
        "result_state": _build_result_state(
            state="current",
            reason="Built from demo section viewer payload.",
        ),
        "source_inspector": _build_source_inspector(
            applied_section=applied_section,
            section_output=section_output,
            station_row={"station": applied_section.station, "label": f"STA {applied_section.station:.3f}"},
        ),
        "terrain_rows": [
            {
                "kind": "terrain_context",
                "label": "Terrain Source",
                "value": "Demo TIN terrain",
                "notes": "Demo review payload.",
            }
        ],
        "structure_rows": [
            {
                "kind": "structure_summary",
                "label": "Structure Summary",
                "value": "No structure interaction in demo payload",
                "notes": "",
            }
        ],
        "earthwork_hint_rows": _build_earthwork_hint_rows(
            earthwork_model=report.get("earthwork_model"),
            station_row={"station": applied_section.station, "label": f"STA {applied_section.station:.3f}"},
        ),
        "review_marker_rows": _build_review_marker_rows(
            station_row={"station": applied_section.station, "label": f"STA {applied_section.station:.3f}"},
        ),
        "diagnostic_rows": [
            {
                "severity": "info",
                "kind": "demo_payload",
                "message": "Demo viewer payload is active.",
                "notes": "",
            }
        ],
        "key_station_rows": [
            {"index": 0, "station": 0.0, "label": "STA 0.000", "navigation_kind": "current", "is_current": True},
            {"index": 1, "station": 20.0, "label": "STA 20.000", "navigation_kind": "next", "is_current": False},
            {"index": 2, "station": 40.0, "label": "STA 40.000", "navigation_kind": "last", "is_current": False},
        ],
        "legacy_objects": {},
    }


def format_section_preview(preview: dict[str, object]) -> str:
    """Format a concise human-readable section viewer summary."""

    applied_section = preview["applied_section"]
    section_output = preview["section_output"]
    station_row = dict(preview.get("station_row", {}) or {})
    station_label = str(station_row.get("label", f"STA {section_output.station:.3f}") or f"STA {section_output.station:.3f}")
    viewer_context = dict(preview.get("viewer_context", {}) or {})
    focused = dict(viewer_context.get("focused_component", {}) or {})
    focused_label = str(focused.get("label", "") or "").strip()
    result_state = dict(preview.get("result_state", {}) or {})
    state_text = str(result_state.get("state", "unknown") or "unknown").strip()

    lines = [
        "CorridorRoad v1 Cross Section Viewer",
        f"Result State: {state_text}",
        f"Station: {section_output.station}",
        f"Station Label: {station_label}",
        f"Components: {len(section_output.component_rows)}",
        f"Quantities: {len(section_output.quantity_rows)}",
        f"Region: {applied_section.region_id or '(none)'}",
        f"Template: {applied_section.template_id or '(unresolved)'}",
    ]
    state_reason = str(result_state.get("reason", "") or "").strip()
    if state_reason:
        lines.append(f"State Reason: {state_reason}")
    if focused_label:
        lines.append(f"Focus Component: {focused_label}")
    return "\n".join(lines)


def show_v1_section_preview(
    *,
    document=None,
    preferred_section_set=None,
    preferred_station: float | None = None,
    extra_context: dict[str, object] | None = None,
    app_module=None,
    gui_module=None,
) -> dict[str, object]:
    """Build and show one v1 section viewer for a given document context."""

    app = App if app_module is None else app_module
    gui = Gui if gui_module is None else gui_module
    active_document = document
    if active_document is None and app is not None:
        active_document = getattr(app, "ActiveDocument", None)

    document_label = ""
    if active_document is not None:
        document_label = str(getattr(active_document, "Label", "") or "")
    preview = None
    if active_document is not None:
        preview = build_document_section_preview(
            active_document,
            preferred_section_set=preferred_section_set,
            preferred_station=preferred_station,
        )
    if preview is None:
        preview = build_demo_section_preview(document_label=document_label)
    explicit_review_marker_rows = None
    if extra_context:
        preview.update(dict(extra_context))
        explicit_review_marker_rows = dict(extra_context).get("review_marker_rows", None)
    viewer_context = dict(preview.get("viewer_context", {}) or {})
    legacy_objects = dict(preview.get("legacy_objects", {}) or {})
    preview["source_inspector"] = _build_source_inspector(
        applied_section=preview["applied_section"],
        section_output=preview["section_output"],
        station_row=dict(preview.get("station_row", {}) or {}),
        section_set=legacy_objects.get("section_set"),
        typical_section=legacy_objects.get("typical_section"),
        region_plan=legacy_objects.get("region_plan"),
        structure_set=legacy_objects.get("structure_set"),
        viewer_context=viewer_context,
    )
    preview["terrain_rows"] = list(preview.get("terrain_rows", []) or []) or _build_terrain_review_rows(
        applied_section=preview["applied_section"],
        station_row=dict(preview.get("station_row", {}) or {}),
    )
    preview["structure_rows"] = list(preview.get("structure_rows", []) or []) or _build_structure_review_rows(
        viewer_context=viewer_context,
        region_plan=legacy_objects.get("region_plan"),
    )
    preview["earthwork_hint_rows"] = list(preview.get("earthwork_hint_rows", []) or []) or _build_earthwork_hint_rows(
        earthwork_model=None,
        station_row=dict(preview.get("station_row", {}) or {}),
        cut_fill_calc=legacy_objects.get("cut_fill_calc"),
    )
    if explicit_review_marker_rows is not None:
        preview["review_marker_rows"] = list(preview.get("review_marker_rows", []) or [])
    else:
        preview["review_marker_rows"] = _build_review_marker_rows(
            station_row=dict(preview.get("station_row", {}) or {}),
            viewer_context=viewer_context,
        )
    preview["diagnostic_rows"] = list(preview.get("diagnostic_rows", []) or []) or _build_diagnostic_review_rows(
        section_output=preview["section_output"],
        viewer_context=viewer_context,
    )
    preview["key_station_rows"] = list(preview.get("key_station_rows", []) or [])
    preview["result_state"] = _resolve_result_state(
        explicit_result_state=dict(preview.get("result_state", {}) or {}),
        diagnostic_rows=list(preview.get("diagnostic_rows", []) or []),
        legacy_objects=legacy_objects,
    )
    summary_text = format_section_preview(preview)

    if app is not None:
        app.Console.PrintMessage(summary_text + "\n")

    if gui is not None and hasattr(gui, "Control"):  # pragma: no branch - GUI path only in FreeCAD.
        try:
            gui.Control.showDialog(CrossSectionViewerTaskPanel(preview))
        except Exception:
            try:  # pragma: no cover - GUI fallback not available in tests.
                from PySide import QtGui

                QtGui.QMessageBox.information(
                    None,
                    "CorridorRoad v1 Cross Section Viewer",
                    summary_text,
                )
            except Exception:
                pass

    return preview


def run_v1_section_view_command() -> dict[str, object]:
    """Execute the minimal v1 section viewer bridge and show a summary."""

    preferred_section_set = None
    preferred_station = None
    extra_context = None
    ui_context = get_ui_context()
    clear_ui_context()
    if App is not None and getattr(App, "ActiveDocument", None) is not None:
        preferred_section_set, preferred_station = selected_section_target(Gui, App.ActiveDocument)
        if preferred_section_set is None:
            object_name = str(ui_context.get("preferred_section_set_name", "") or "").strip()
            if object_name:
                try:
                    preferred_section_set = App.ActiveDocument.getObject(object_name)
                except Exception:
                    preferred_section_set = None
        if preferred_station is None and ui_context.get("preferred_station", None) is not None:
            try:
                preferred_station = float(ui_context.get("preferred_station"))
            except Exception:
                preferred_station = None
        extra_context = {}
        for key in (
            "viewer_context",
            "result_state",
            "station_row",
            "source",
        ):
            if key in ui_context:
                extra_context[key] = ui_context[key]
        if not extra_context:
            extra_context = None

    return show_v1_section_preview(
        document=getattr(App, "ActiveDocument", None) if App is not None else None,
        preferred_section_set=preferred_section_set,
        preferred_station=preferred_station,
        extra_context=extra_context,
        app_module=App,
        gui_module=Gui,
    )


class CmdV1ViewSections:
    """Standalone v1 cross-section viewer command."""

    def GetResources(self):
        from freecad.Corridor_Road.misc.resources import icon_path

        return {
            "Pixmap": icon_path("view_cross_section.svg"),
            "MenuText": "Cross Section Viewer (v1)",
            "ToolTip": "Run the v1 cross-section viewer pipeline",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_section_view_command()


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1ViewSections", CmdV1ViewSections())

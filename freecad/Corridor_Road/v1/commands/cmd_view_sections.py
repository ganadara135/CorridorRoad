"""Section viewer command bridge for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from ..models.output.section_output import SectionGeometryRow
from ..models.result.applied_section import AppliedSection
from ..models.result.applied_section_set import AppliedSectionSet
from ..models.result.tin_surface import TINSurface
from ..services.evaluation import (
    AlignmentEvaluationService,
    LegacyDocumentAdapter,
    SectionEarthworkAreaService,
    TinSamplingService,
    TinSectionSamplingService,
)
from ..services.mapping import SectionOutputMapper
from ..services.mapping.cross_section_drawing_mapper import CrossSectionDrawingMapper
from ..ui.common import clear_ui_context, get_ui_context
from ..ui.viewers import CrossSectionViewerTaskPanel
from ..ui.viewers.cross_section_viewer import build_corridor_result_status
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
    """Return a normalized status text for one source/result object."""

    return str(getattr(obj, "Status", "") or "").strip()


def _needs_recompute(obj) -> bool:
    """Return whether one source/result object exposes a recompute-needed signal."""

    return _safe_bool(getattr(obj, "NeedsRecompute", False))


def _state_from_status_text(status_text: str) -> tuple[str | None, str]:
    """Map one source/result status string into a normalized viewer state."""

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
    source_objects: dict[str, object] | None = None,
) -> dict[str, str]:
    """Resolve the normalized section-viewer result state."""

    explicit = dict(explicit_result_state or {})
    explicit_state = str(explicit.get("state", "") or "").strip()
    explicit_reason = str(explicit.get("reason", "") or "").strip()
    if explicit_state:
        return _build_result_state(state=explicit_state, reason=explicit_reason)

    objects = dict(source_objects or {})
    for key in (
        "applied_section_set",
        "corridor",
        "cut_fill_calc",
        "assembly_model",
        "region_model",
        "structure_model",
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
    applied_section_set=None,
    section_set=None,
    assembly_model=None,
    region_model=None,
    structure_model=None,
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
    applied_section_set_label = str(
        getattr(applied_section_set, "label", "")
        or getattr(applied_section_set, "applied_section_set_id", "")
        or ""
    ).strip()
    applied_section_set_ref = str(getattr(applied_section_set, "applied_section_set_id", "") or "").strip()
    section_set_label = str(
        getattr(section_set, "Label", "")
        or getattr(section_set, "Name", "")
        or applied_section_set_label
        or ""
    ).strip()
    owner_template = str(getattr(applied_section, "template_id", "") or "").strip()
    owner_region = str(getattr(applied_section, "region_id", "") or "").strip()
    if not owner_template:
        owner_template = _first_component_ref(section_output, "template_ref")
    if not owner_region:
        owner_region = _first_component_ref(section_output, "region_ref")
    template_object_label = str(getattr(assembly_model, "Label", "") or getattr(assembly_model, "Name", "") or "").strip()
    region_object_label = str(getattr(region_model, "Label", "") or getattr(region_model, "Name", "") or "").strip()
    structure_label = str(getattr(structure_model, "Label", "") or getattr(structure_model, "Name", "") or "").strip()
    template_label = template_object_label or owner_template
    region_label = region_object_label or owner_region
    owner_structure = structure_label or str(viewer_context.get("structure_summary", "") or "").strip()
    section_set_status = _source_owner_status(object_label=section_set_label, source_ref=applied_section_set_ref)
    template_status = _source_owner_status(object_label=template_object_label, source_ref=owner_template)
    region_status = _source_owner_status(object_label=region_object_label, source_ref=owner_region)
    structure_status = _source_owner_status(object_label=structure_label, source_ref=owner_structure)

    unresolved_fields = []
    if section_set_status == "unresolved":
        unresolved_fields.append("section_set")
    if template_status == "unresolved":
        unresolved_fields.append("template")
    if region_status == "unresolved":
        unresolved_fields.append("region")
    if structure_status == "unresolved":
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
        "section_set_source_ref": applied_section_set_ref,
        "section_set_status": section_set_status,
        "template_label": template_label,
        "template_object_label": template_object_label,
        "template_source_ref": owner_template,
        "template_status": template_status,
        "region_label": region_label,
        "region_object_label": region_object_label,
        "region_source_ref": owner_region,
        "region_status": region_status,
        "structure_label": structure_label,
        "structure_status": structure_status,
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


def _first_component_ref(section_output, attr_name: str) -> str:
    """Return the first non-empty component source reference from section output."""

    for row in list(getattr(section_output, "component_rows", []) or []):
        value = str(getattr(row, attr_name, "") or "").strip()
        if value:
            return value
    return ""


def _source_owner_status(*, object_label: str, source_ref: str) -> str:
    """Classify how strongly one source owner is resolved."""

    if str(object_label or "").strip():
        return "resolved"
    if str(source_ref or "").strip():
        return "source_ref"
    return "unresolved"


def _viewer_station_rows_from_applied_section_set(applied_section_set) -> list[dict[str, object]]:
    """Build viewer station rows from a v1 AppliedSectionSet result contract."""

    rows = []
    for index, row in enumerate(list(getattr(applied_section_set, "station_rows", []) or [])):
        try:
            station = float(getattr(row, "station", 0.0) or 0.0)
        except Exception:
            continue
        rows.append(
            {
                "index": index,
                "station": station,
                "label": f"STA {station:.3f}",
                "applied_section_id": str(getattr(row, "applied_section_id", "") or ""),
                "kind": str(getattr(row, "kind", "") or ""),
            }
        )
    if rows:
        return rows
    for index, section in enumerate(list(getattr(applied_section_set, "sections", []) or [])):
        try:
            station = float(getattr(section, "station", 0.0) or 0.0)
        except Exception:
            continue
        rows.append(
            {
                "index": index,
                "station": station,
                "label": f"STA {station:.3f}",
                "applied_section_id": str(getattr(section, "applied_section_id", "") or ""),
                "kind": "applied_section",
            }
        )
    return rows


def _merge_viewer_station_rows(*row_groups: list[dict[str, object]] | None) -> list[dict[str, object]]:
    """Merge station navigation rows without dropping v1 result stations."""

    by_station: dict[float, dict[str, object]] = {}
    for rows in row_groups:
        for row in list(rows or []):
            item = dict(row or {})
            try:
                station = round(float(item.get("station", 0.0) or 0.0), 6)
            except Exception:
                continue
            existing = by_station.get(station, {})
            merged = dict(existing)
            merged.update({key: value for key, value in item.items() if value not in (None, "")})
            by_station[station] = merged
    merged_rows = [by_station[key] for key in sorted(by_station)]
    for index, row in enumerate(merged_rows):
        row["index"] = index
        row["station"] = float(row.get("station", 0.0) or 0.0)
        row["label"] = str(row.get("label", "") or f"STA {row['station']:.3f}")
    return merged_rows


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


def _build_tin_section_terrain_rows(
    *,
    surface: TINSurface | None,
    station_row: dict[str, object] | None,
    station_rows: list[dict[str, object]] | None = None,
    offsets: list[float] | None = None,
    station_offset_to_xy=None,
    sample_result=None,
) -> list[dict[str, str]]:
    """Build section terrain review rows from a TIN surface."""

    if surface is None:
        return []

    station = _station_value_from_row(station_row)
    offset_values = _terrain_offsets(offsets)
    adapter = station_offset_to_xy or _station_offset_adapter_from_rows(station_rows)
    if adapter is None and sample_result is None:
        return [
            {
                "kind": "tin_section_adapter",
                "label": "TIN Section Adapter",
                "value": "missing",
                "notes": "TIN terrain sampling requires station rows with x/y or an explicit station_offset_to_xy adapter.",
            }
        ]

    result = sample_result or TinSectionSamplingService().sample_offsets(
        surface=surface,
        station=station,
        offsets=offset_values,
        station_offset_to_xy=adapter,
    )
    surface_id = str(getattr(surface, "surface_id", "") or "").strip()
    rows: list[dict[str, str]] = [
        {
            "kind": "tin_section_summary",
            "label": "TIN Section Samples",
            "value": f"{result.hit_count}/{len(result.rows)} hit",
            "notes": f"surface={surface_id}; status={result.status}",
        }
    ]
    rows.extend(_tin_section_sample_row(row) for row in result.rows)
    return rows


def _resolve_terrain_review_rows(preview: dict[str, object]) -> list[dict[str, str]]:
    """Resolve terrain rows, adding TIN section samples when available."""

    base_rows = list(preview.get("terrain_rows", []) or []) or _build_terrain_review_rows(
        applied_section=preview["applied_section"],
        station_row=dict(preview.get("station_row", {}) or {}),
    )
    sample_result = preview.get("tin_section_sample_result", None)
    tin_rows = _build_tin_section_terrain_rows(
        surface=preview.get("tin_surface"),
        station_row=dict(preview.get("station_row", {}) or {}),
        station_rows=list(preview.get("station_rows", []) or []),
        offsets=_terrain_offsets_from_preview(preview),
        station_offset_to_xy=preview.get("station_offset_to_xy", None),
        sample_result=sample_result,
    )
    if not tin_rows:
        return base_rows
    return base_rows + tin_rows


def _resolve_tin_section_sample_result(preview: dict[str, object]):
    """Resolve and cache the TIN section sample result for one preview."""

    existing = preview.get("tin_section_sample_result", None)
    if existing is not None:
        return existing
    surface = preview.get("tin_surface", None)
    if surface is None:
        return None
    adapter = (
        preview.get("station_offset_to_xy", None)
        or _station_offset_adapter_from_alignment(preview.get("alignment_model", None))
        or _station_offset_adapter_from_rows(
            list(preview.get("station_rows", []) or [])
        )
    )
    if adapter is None:
        return None
    result = TinSectionSamplingService().sample_offsets(
        surface=surface,
        station=_station_value_from_row(dict(preview.get("station_row", {}) or {})),
        offsets=_terrain_offsets_from_preview(preview),
        station_offset_to_xy=adapter,
    )
    preview["tin_section_sample_result"] = result
    return result


def _apply_tin_section_geometry(preview: dict[str, object]) -> None:
    """Append a drawable existing-ground TIN polyline to section output."""

    section_output = preview.get("section_output", None)
    if section_output is None:
        return
    result = _resolve_tin_section_sample_result(preview)
    geometry_rows = _tin_section_geometry_rows(result) if result is not None else []
    if not geometry_rows:
        return

    existing_rows = [
        row
        for row in list(getattr(section_output, "geometry_rows", []) or [])
        if str(getattr(row, "kind", "") or "") != "existing_ground_tin"
    ]
    section_output.geometry_rows = existing_rows + geometry_rows


def _apply_section_earthwork_area(preview: dict[str, object]) -> None:
    """Attach section-level cut/fill area quantities when section geometry is available."""

    section_output = preview.get("section_output", None)
    if section_output is None:
        return
    service = SectionEarthworkAreaService()
    result = service.build(section_output)
    preview["section_earthwork_area_result"] = result
    if result.status != "ok":
        return

    quantity_kinds = service.quantity_kinds()
    existing_rows = [
        row
        for row in list(getattr(section_output, "quantity_rows", []) or [])
        if not (
            str(getattr(row, "quantity_kind", "") or "") in quantity_kinds
            and str(getattr(row, "component_ref", "") or "") == "section_earthwork_area"
        )
    ]
    row_id_prefix = str(getattr(section_output, "section_output_id", "") or "section")
    section_output.quantity_rows = existing_rows + service.to_section_quantity_rows(
        result,
        row_id_prefix=row_id_prefix,
    )


def _tin_section_geometry_rows(result) -> list[SectionGeometryRow]:
    segments: list[list[object]] = []
    current: list[object] = []
    for row in list(getattr(result, "rows", []) or []):
        if bool(getattr(row, "found", False)) and getattr(row, "z", None) is not None:
            current.append(row)
            continue
        if current:
            segments.append(current)
            current = []
    if current:
        segments.append(current)

    station = float(getattr(result, "station", 0.0) or 0.0)
    rows = []
    for index, segment in enumerate(segments, start=1):
        if len(segment) < 2:
            continue
        rows.append(
            SectionGeometryRow(
                row_id=f"tin-section-terrain:{station:g}:{index}",
                kind="existing_ground_tin",
                x_values=[float(row.offset) for row in segment],
                y_values=[float(row.z) for row in segment],
                z_values=[float(row.z) for row in segment],
                closed=False,
                style_role="existing_ground",
                source_ref=str(getattr(result, "surface_ref", "") or ""),
            )
        )
    return rows


def _tin_section_sample_row(row) -> dict[str, str]:
    z_text = f"z={float(row.z):.3f}" if row.z is not None else str(row.status or "no_hit")
    face_text = f"face={row.face_id}" if row.face_id else "face=(none)"
    return {
        "kind": "tin_section_sample",
        "label": f"Offset {float(row.offset):g}",
        "value": z_text,
        "notes": (
            f"x={float(row.x):.3f}, y={float(row.y):.3f}, "
            f"{face_text}, confidence={float(row.confidence):.3f}; {row.notes}"
        ).strip(),
    }


def _terrain_offsets_from_preview(preview: dict[str, object]) -> list[float] | None:
    viewer_context = dict(preview.get("viewer_context", {}) or {})
    for value in (
        preview.get("terrain_offsets", None),
        viewer_context.get("terrain_offsets", None),
    ):
        if value is not None:
            return _terrain_offsets(value)
    return None


def _terrain_offsets(offsets) -> list[float]:
    values = []
    for value in list(offsets or [-20.0, -10.0, 0.0, 10.0, 20.0]):
        try:
            values.append(float(value))
        except Exception:
            continue
    return values or [-20.0, -10.0, 0.0, 10.0, 20.0]


def _station_value_from_row(station_row: dict[str, object] | None) -> float:
    try:
        return float((station_row or {}).get("station", 0.0) or 0.0)
    except Exception:
        return 0.0


def _station_offset_adapter_from_rows(station_rows: list[dict[str, object]] | None):
    rows = [
        dict(row or {})
        for row in list(station_rows or [])
        if _has_station_xy(row)
    ]
    if not rows:
        return None
    try:
        return TinSamplingService().station_offset_adapter_from_rows(rows)
    except Exception:
        return None


def _station_offset_adapter_from_alignment(alignment_model):
    if alignment_model is None:
        return None
    try:
        return AlignmentEvaluationService().station_offset_adapter(alignment_model)
    except Exception:
        return None


def _has_station_xy(row: dict[str, object]) -> bool:
    return row.get("station", None) is not None and row.get("x", None) is not None and row.get("y", None) is not None


def _resolve_document_tin_surface(document, *, gui_module=Gui) -> TINSurface | None:
    """Resolve a document TIN surface for section terrain sampling when available."""

    if document is None:
        return None
    try:
        from .cmd_review_tin import build_document_tin_review

        preview = build_document_tin_review(document, gui_module=gui_module)
        surface = (preview or {}).get("tin_surface", None)
        return surface if isinstance(surface, TINSurface) else None
    except Exception:
        return None


def _build_structure_review_rows(
    *,
    viewer_context: dict[str, object] | None,
    region_model=None,
    structure_model=None,
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
    if structure_model is not None:
        label = str(getattr(structure_model, "Label", "") or getattr(structure_model, "Name", "") or "").strip()
        count = getattr(structure_model, "StructureCount", None)
        if count is None:
            count = len(list(getattr(structure_model, "StructureIds", []) or []))
        rows.append(
            {
                "kind": "structure_model",
                "label": "Structure Model",
                "value": label or "Structures",
                "notes": f"Rows: {int(count or 0)}",
            }
        )
    if not rows and region_model is not None:
        rows.append(
            {
                "kind": "structure_fallback",
                "label": "Structure Context",
                "value": str(getattr(region_model, "Label", "") or getattr(region_model, "Name", "") or "").strip(),
                "notes": "No explicit v1 structure rows were provided in the current preview payload.",
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


def _build_corridor_review_rows(document) -> list[dict[str, object]]:
    """Resolve Build Corridor preview-object rows for the section viewer."""

    if document is None:
        return []
    try:
        from .cmd_build_corridor import corridor_build_review_rows

        return list(corridor_build_review_rows(document) or [])
    except Exception:
        return []


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


def build_document_section_preview(
    document,
    *,
    preferred_section_set=None,
    preferred_station: float | None = None,
) -> dict[str, object] | None:
    """Build a v1 section viewer payload from a FreeCAD document when possible."""

    adapter = LegacyDocumentAdapter()
    project = adapter._find_project(document)
    return _build_v1_applied_section_set_preview(
        document,
        project=project,
        preferred_applied_section_set=preferred_section_set,
        preferred_station=preferred_station,
    )


def _build_v1_applied_section_set_preview(
    document,
    *,
    project=None,
    preferred_applied_section_set=None,
    preferred_station: float | None = None,
) -> dict[str, object] | None:
    """Build a section viewer payload directly from a persisted v1 AppliedSectionSet."""

    try:
        from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
    except Exception:
        return None
    try:
        from ..objects.obj_assembly import find_v1_assembly_model
    except Exception:
        find_v1_assembly_model = None
    try:
        from ..objects.obj_region import find_v1_region_model
    except Exception:
        find_v1_region_model = None
    try:
        from ..objects.obj_structure import find_v1_structure_model
    except Exception:
        find_v1_structure_model = None

    applied_obj = find_v1_applied_section_set(document, preferred_applied_section_set)
    applied_section_set = to_applied_section_set(applied_obj)
    sections = list(getattr(applied_section_set, "sections", []) or []) if applied_section_set is not None else []
    if applied_obj is None or applied_section_set is None or not sections:
        return None

    station_rows = _viewer_station_rows_from_applied_section_set(applied_section_set)
    if preferred_station is None and station_rows:
        target_station = float(station_rows[0].get("station", 0.0) or 0.0)
    elif preferred_station is None:
        target_station = float(getattr(sections[0], "station", 0.0) or 0.0)
    else:
        target_station = float(preferred_station)

    applied_section = min(
        sections,
        key=lambda row: abs(float(getattr(row, "station", 0.0) or 0.0) - target_station),
    )
    target_station = float(getattr(applied_section, "station", target_station) or target_station)
    station_payload = _nearest_station_payload(station_rows, target_station) or {
        "station": target_station,
        "label": f"STA {target_station:.3f}",
    }
    section_output = SectionOutputMapper().map_applied_section(applied_section)
    drawing_payload = CrossSectionDrawingMapper().map_applied_section_set(
        applied_section_set,
        station=target_station,
    )

    assembly_model = find_v1_assembly_model(document) if find_v1_assembly_model is not None else None
    region_model = find_v1_region_model(document) if find_v1_region_model is not None else None
    structure_model = find_v1_structure_model(document) if find_v1_structure_model is not None else None
    source_objects = {
        "project": project,
        "applied_section_set": applied_obj,
        "alignment": None,
        "assembly_model": assembly_model,
        "region_model": region_model,
        "corridor": getattr(project, "Corridor", None) if project is not None else None,
        "cut_fill_calc": getattr(project, "CutFillCalc", None) if project is not None else None,
        "structure_model": structure_model,
    }
    viewer_context: dict[str, object] = {}
    diagnostic_rows = _build_diagnostic_review_rows(
        section_output=section_output,
        viewer_context=viewer_context,
    )
    earthwork_hint_rows = _build_earthwork_hint_rows(
        earthwork_model=None,
        station_row=station_payload,
        cut_fill_calc=source_objects.get("cut_fill_calc"),
    )
    review_marker_rows = _build_review_marker_rows(
        station_row=station_payload,
        viewer_context=viewer_context,
    )

    return {
        "source": "v1_applied_section_set",
        "applied_section_set": applied_section_set,
        "applied_section": applied_section,
        "section_output": section_output,
        "drawing_payload": drawing_payload,
        "station_row": station_payload,
        "result_state": _resolve_result_state(
            diagnostic_rows=diagnostic_rows,
            source_objects=source_objects,
        ),
        "source_inspector": _build_source_inspector(
            applied_section=applied_section,
            section_output=section_output,
            station_row=station_payload,
            applied_section_set=applied_section_set,
            section_set=applied_obj,
            assembly_model=None,
            region_model=region_model,
            structure_model=structure_model,
            viewer_context=viewer_context,
        ),
        "terrain_rows": _build_terrain_review_rows(
            applied_section=applied_section,
            station_row=station_payload,
        ),
        "tin_surface": _resolve_document_tin_surface(document),
        "station_rows": station_rows,
        "structure_rows": _build_structure_review_rows(
            viewer_context=viewer_context,
            region_model=region_model,
            structure_model=structure_model,
        ),
        "earthwork_hint_rows": earthwork_hint_rows,
        "review_marker_rows": review_marker_rows,
        "corridor_review_rows": _build_corridor_review_rows(document),
        "diagnostic_rows": diagnostic_rows,
        "source_objects": source_objects,
    }


def _nearest_station_payload(rows: list[dict[str, object]], station: float) -> dict[str, object] | None:
    """Return the station navigation row nearest to a target station."""

    if not rows:
        return None
    best = min(
        [dict(row or {}) for row in rows],
        key=lambda row: abs(float(row.get("station", 0.0) or 0.0) - float(station)),
    )
    best["is_current"] = True
    return best


def build_demo_section_preview(document_label: str = "") -> dict[str, object]:
    """Build a minimal section viewer payload for the v1 bridge."""

    report = build_demo_earthwork_report(document_label=document_label)
    applied_section = report["applied_section_set"].sections[0]
    section_output = SectionOutputMapper().map_applied_section(applied_section)
    drawing_payload = CrossSectionDrawingMapper().map_applied_section_set(report["applied_section_set"], station=applied_section.station)

    return {
        "applied_section_set": report["applied_section_set"],
        "applied_section": applied_section,
        "section_output": section_output,
        "drawing_payload": drawing_payload,
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
        "corridor_review_rows": [],
        "diagnostic_rows": [
            {
                "severity": "info",
                "kind": "demo_payload",
                "message": "Demo viewer payload is active.",
                "notes": "",
            }
        ],
        "station_rows": [
            {"index": 0, "station": 0.0, "label": "STA 0.000", "is_current": True},
            {"index": 1, "station": 20.0, "label": "STA 20.000", "is_current": False},
            {"index": 2, "station": 40.0, "label": "STA 40.000", "is_current": False},
        ],
    }


def _build_missing_v1_applied_section_set_preview(document_label: str = "") -> dict[str, object]:
    """Build a blocked v1-only payload when no AppliedSectionSet result exists."""

    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="corridorroad-v1",
        applied_section_set_id="",
        label=str(document_label or "No v1 AppliedSectionSet"),
    )
    applied_section = AppliedSection(
        schema_version=1,
        project_id="corridorroad-v1",
        applied_section_id="missing:v1-applied-section",
        label=str(document_label or "No v1 AppliedSectionSet"),
        station=0.0,
    )
    section_output = SectionOutputMapper().map_applied_section(applied_section)
    diagnostic_rows = [
        {
            "severity": "error",
            "kind": "missing_v1_applied_section_set",
            "message": "No v1 AppliedSectionSet result was found in the active document.",
            "notes": "Run v1 Applied Sections before opening the Cross Section Viewer.",
        }
    ]
    return {
        "source": "missing_v1_applied_section_set",
        "applied_section_set": applied_section_set,
        "applied_section": applied_section,
        "section_output": section_output,
        "station_row": {"station": 0.0, "label": "STA 0.000"},
        "station_rows": [],
        "result_state": _build_result_state(
            state="blocked",
            reason="No v1 AppliedSectionSet result was found in the active document.",
        ),
        "source_inspector": _build_source_inspector(
            applied_section=applied_section,
            section_output=section_output,
            station_row={"station": 0.0, "label": "STA 0.000"},
            applied_section_set=None,
        ),
        "terrain_rows": [],
        "structure_rows": [],
        "earthwork_hint_rows": [],
        "review_marker_rows": [],
        "corridor_review_rows": [],
        "diagnostic_rows": diagnostic_rows,
        "source_objects": {},
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
    drawing_payload = preview.get("drawing_payload")
    source_inspector = dict(preview.get("source_inspector", {}) or {})
    ownership_status = str(source_inspector.get("ownership_status", "unknown") or "unknown").strip()
    template_label = str(
        applied_section.template_id
        or source_inspector.get("template_label", "")
        or source_inspector.get("template_source_ref", "")
        or "(unresolved)"
    )

    lines = [
        "CorridorRoad v1 Cross Section Viewer",
        f"Result State: {state_text}",
        f"Station: {section_output.station}",
        f"Station Label: {station_label}",
        f"Components: {len(section_output.component_rows)}",
        f"Quantities: {len(section_output.quantity_rows)}",
        f"Drawing Geometry: {len(list(getattr(drawing_payload, 'geometry_rows', []) or []))}",
        f"Drawing Labels: {len(list(getattr(drawing_payload, 'label_rows', []) or []))}",
        f"Drawing Dimensions: {len(list(getattr(drawing_payload, 'dimension_rows', []) or []))}",
        f"Source Ownership: {ownership_status}",
        f"Region: {applied_section.region_id or '(none)'}",
        f"Assembly Template: {template_label}",
    ]
    unresolved_fields = [
        str(value)
        for value in list(source_inspector.get("unresolved_fields", []) or [])
        if str(value or "").strip()
    ]
    if unresolved_fields:
        lines.append(f"Unresolved Source Owners: {', '.join(unresolved_fields)}")
    frame = getattr(applied_section, "frame", None)
    if frame is not None:
        lines.append(
            "Frame: "
            f"x={float(getattr(frame, 'x', 0.0) or 0.0):.3f}, "
            f"y={float(getattr(frame, 'y', 0.0) or 0.0):.3f}, "
            f"z={float(getattr(frame, 'z', 0.0) or 0.0):.3f}"
        )
        lines.append(
            "Frame Profile: "
            f"grade={float(getattr(frame, 'profile_grade', 0.0) or 0.0):.6f}, "
            f"alignment={getattr(frame, 'alignment_status', '')}, "
            f"profile={getattr(frame, 'profile_status', '')}"
        )
    state_reason = str(result_state.get("reason", "") or "").strip()
    if state_reason:
        lines.append(f"State Reason: {state_reason}")
    corridor_status = build_corridor_result_status(preview)
    corridor_text = str(corridor_status.get("text", "") or "").strip()
    if corridor_text:
        lines.append(corridor_text)
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
    if preview is None and active_document is not None:
        preview = _build_missing_v1_applied_section_set_preview(document_label=document_label)
    if preview is None:
        preview = build_demo_section_preview(document_label=document_label)
    explicit_review_marker_rows = None
    if extra_context:
        preview.update(dict(extra_context))
        explicit_review_marker_rows = dict(extra_context).get("review_marker_rows", None)
        _retarget_preview_to_station(preview)
    viewer_context = dict(preview.get("viewer_context", {}) or {})
    source_objects = dict(preview.get("source_objects", {}) or {})
    _apply_tin_section_geometry(preview)
    _apply_section_earthwork_area(preview)
    preview["source_inspector"] = _build_source_inspector(
        applied_section=preview["applied_section"],
        section_output=preview["section_output"],
        station_row=dict(preview.get("station_row", {}) or {}),
        applied_section_set=preview.get("applied_section_set", None),
        section_set=source_objects.get("applied_section_set"),
        assembly_model=source_objects.get("assembly_model"),
        region_model=source_objects.get("region_model"),
        structure_model=source_objects.get("structure_model"),
        viewer_context=viewer_context,
    )
    preview["terrain_rows"] = _resolve_terrain_review_rows(preview)
    preview["structure_rows"] = list(preview.get("structure_rows", []) or []) or _build_structure_review_rows(
        viewer_context=viewer_context,
        region_model=source_objects.get("region_model"),
        structure_model=source_objects.get("structure_model"),
    )
    preview["earthwork_hint_rows"] = list(preview.get("earthwork_hint_rows", []) or []) or _build_earthwork_hint_rows(
        earthwork_model=None,
        station_row=dict(preview.get("station_row", {}) or {}),
        cut_fill_calc=source_objects.get("cut_fill_calc"),
    )
    if explicit_review_marker_rows is not None:
        preview["review_marker_rows"] = list(preview.get("review_marker_rows", []) or [])
    else:
        preview["review_marker_rows"] = _build_review_marker_rows(
            station_row=dict(preview.get("station_row", {}) or {}),
            viewer_context=viewer_context,
        )
    if "corridor_review_rows" not in preview:
        preview["corridor_review_rows"] = _build_corridor_review_rows(active_document)
    preview["diagnostic_rows"] = list(preview.get("diagnostic_rows", []) or []) or _build_diagnostic_review_rows(
        section_output=preview["section_output"],
        viewer_context=viewer_context,
    )
    preview["station_rows"] = _merge_viewer_station_rows(
        list(preview.get("station_rows", []) or []),
        _viewer_station_rows_from_applied_section_set(preview.get("applied_section_set", None)),
    )
    preview["result_state"] = _resolve_result_state(
        explicit_result_state=dict(preview.get("result_state", {}) or {}),
        diagnostic_rows=list(preview.get("diagnostic_rows", []) or []),
        source_objects=source_objects,
    )
    if "drawing_payload" not in preview:
        try:
            preview["drawing_payload"] = CrossSectionDrawingMapper().map_applied_section(preview["applied_section"])
        except Exception:
            pass
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


def _retarget_preview_to_station(preview: dict[str, object]) -> None:
    """Rebuild station-owned payload fields after navigation changes station_row."""

    section_set = preview.get("applied_section_set", None)
    sections = list(getattr(section_set, "sections", []) or [])
    if not sections:
        return
    station_row = dict(preview.get("station_row", {}) or {})
    try:
        target_station = float(station_row.get("station", getattr(preview.get("applied_section"), "station", 0.0)) or 0.0)
    except Exception:
        target_station = float(getattr(preview.get("applied_section"), "station", 0.0) or 0.0)
    section = min(sections, key=lambda row: abs(float(getattr(row, "station", 0.0) or 0.0) - target_station))
    preview["applied_section"] = section
    preview["section_output"] = SectionOutputMapper().map_applied_section(section)
    preview["drawing_payload"] = CrossSectionDrawingMapper().map_applied_section_set(section_set, station=target_station)


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
            object_name = str(
                ui_context.get("preferred_applied_section_set_name", "")
                or ui_context.get("preferred_section_set_name", "")
                or ""
            ).strip()
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
            "earthwork_hint_rows",
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

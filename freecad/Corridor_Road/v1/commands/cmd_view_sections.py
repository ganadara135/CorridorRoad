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
    StationContextResolver,
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
        "intersection_model",
        "structure_model",
        "drainage_model",
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
    drainage_model=None,
    superelevation_model=None,
    intersection_model=None,
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
    drainage_label = str(getattr(drainage_model, "Label", "") or getattr(drainage_model, "Name", "") or "").strip()
    superelevation_label = str(getattr(superelevation_model, "Label", "") or getattr(superelevation_model, "Name", "") or "").strip()
    intersection_label = str(getattr(intersection_model, "Label", "") or getattr(intersection_model, "Name", "") or "").strip()
    template_label = template_object_label or owner_template
    region_label = region_object_label or owner_region
    owner_superelevation = str(getattr(applied_section, "active_superelevation_id", "") or "").strip()
    owner_intersection = str(getattr(applied_section, "active_intersection_id", "") or "").strip()
    owner_intersection_control_area = str(getattr(applied_section, "active_intersection_control_area_id", "") or "").strip()
    owner_intersection_leg = str(getattr(applied_section, "active_intersection_leg_id", "") or "").strip()
    owner_intersection_leg_role = str(getattr(applied_section, "active_intersection_leg_role", "") or "").strip()
    active_structure_ref = str(viewer_context.get("active_structure_ref", "") or "").strip()
    if not active_structure_ref:
        active_structure_ref = _applied_section_structure_ref(applied_section)
    owner_structure = active_structure_ref or structure_label or str(viewer_context.get("structure_summary", "") or "").strip()
    active_drainage_ref = str(viewer_context.get("active_drainage_ref", "") or "").strip()
    if not active_drainage_ref:
        active_drainage_ref = _applied_section_drainage_ref(applied_section)
    owner_drainage = active_drainage_ref or drainage_label or str(viewer_context.get("drainage_summary", "") or "").strip()
    section_set_status = _source_owner_status(object_label=section_set_label, source_ref=applied_section_set_ref)
    template_status = _source_owner_status(object_label=template_object_label, source_ref=owner_template)
    region_status = _source_owner_status(object_label=region_object_label, source_ref=owner_region)
    structure_status = _source_owner_status(object_label=structure_label, source_ref=owner_structure)
    drainage_status = (
        _source_owner_status(object_label=drainage_label, source_ref=owner_drainage)
        if (drainage_label or owner_drainage)
        else "not_applicable"
    )
    superelevation_status = (
        _source_owner_status(object_label=superelevation_label, source_ref=owner_superelevation)
        if owner_superelevation
        else "not_applicable"
    )
    intersection_status = (
        _source_owner_status(object_label=intersection_label, source_ref=owner_intersection)
        if owner_intersection
        else "not_applicable"
    )

    unresolved_fields = []
    if section_set_status == "unresolved":
        unresolved_fields.append("section_set")
    if template_status == "unresolved":
        unresolved_fields.append("template")
    if region_status == "unresolved":
        unresolved_fields.append("region")
    if structure_status == "unresolved":
        unresolved_fields.append("structure")
    if drainage_status == "unresolved":
        unresolved_fields.append("drainage")
    if superelevation_status == "unresolved":
        unresolved_fields.append("superelevation")
    if intersection_status == "unresolved":
        unresolved_fields.append("intersection")

    required_owner_count = 7
    if len(unresolved_fields) == 0:
        ownership_status = "resolved"
    elif len(unresolved_fields) >= required_owner_count:
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
        "structure_source_ref": active_structure_ref,
        "structure_status": structure_status,
        "drainage_label": drainage_label,
        "drainage_source_ref": active_drainage_ref,
        "drainage_status": drainage_status,
        "superelevation_label": superelevation_label or owner_superelevation,
        "superelevation_source_ref": owner_superelevation,
        "superelevation_status": superelevation_status,
        "intersection_label": intersection_label or owner_intersection,
        "intersection_source_ref": owner_intersection,
        "intersection_status": intersection_status,
        "intersection_control_area_ref": owner_intersection_control_area,
        "intersection_leg_ref": owner_intersection_leg,
        "intersection_leg_role": owner_intersection_leg_role,
        "component_id": component_id,
        "component_kind": component_kind,
        "component_side": component_side,
        "owner_template": owner_template,
        "owner_region": owner_region,
        "owner_structure": owner_structure,
        "owner_drainage": owner_drainage,
        "owner_superelevation": owner_superelevation,
        "owner_intersection": owner_intersection,
        "ownership_status": ownership_status,
        "unresolved_fields": list(unresolved_fields),
        "component_count": int(len(list(getattr(section_output, "component_rows", []) or []))),
        "quantity_count": int(len(list(getattr(section_output, "quantity_rows", []) or []))),
    }

def _build_intersection_context_rows(
    document,
    *,
    intersection_model_obj=None,
    applied_section=None,
) -> list[dict[str, object]]:
    """Build intersection contract rows for the focused cross-section station."""

    active_intersection = str(getattr(applied_section, "active_intersection_id", "") or "").strip()
    if not active_intersection:
        return []

    try:
        from ..objects.obj_intersection import find_v1_intersection_model, to_intersection_model
    except Exception:
        find_v1_intersection_model = None
        to_intersection_model = None
    try:
        from ..services.evaluation.intersection_evaluation_service import IntersectionEvaluationService
    except Exception:
        IntersectionEvaluationService = None

    model_obj = intersection_model_obj
    if model_obj is None and document is not None and find_v1_intersection_model is not None:
        model_obj = find_v1_intersection_model(document)
    if model_obj is None:
        return [
            _intersection_context_row(
                "source",
                "missing",
                active_intersection,
                "intersection_model",
                notes="Intersection source model was not found.",
            )
        ]

    model = to_intersection_model(model_obj) if to_intersection_model is not None else None
    if model is None and hasattr(model_obj, "intersection_rows"):
        model = model_obj
    if model is None:
        return [
            _intersection_context_row(
                "source",
                "error",
                active_intersection,
                "intersection_model",
                notes="Intersection source model could not be decoded.",
            )
        ]
    if IntersectionEvaluationService is None:
        return [
            _intersection_context_row(
                "source",
                "error",
                active_intersection,
                "intersection_model",
                notes="Intersection evaluation service is unavailable.",
            )
        ]

    active_leg = str(getattr(applied_section, "active_intersection_leg_id", "") or "").strip()
    active_leg_role = str(getattr(applied_section, "active_intersection_leg_role", "") or "").strip()
    active_control_area = str(getattr(applied_section, "active_intersection_control_area_id", "") or "").strip()
    active_alignment = str(getattr(applied_section, "alignment_id", "") or "").strip()
    active_grading_policy = str(getattr(applied_section, "active_intersection_grading_policy_ref", "") or "").strip()

    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(model)
    edge_network = service.evaluate_edge_network(model, topology_result=topology)
    surface_zones = service.evaluate_surface_zones(model, edge_network_result=edge_network)
    corridor_clips = service.evaluate_corridor_clipping(
        model,
        topology_result=topology,
        surface_zone_result=surface_zones,
    )
    drainage_hints = service.evaluate_drainage_hints(model, surface_zone_result=surface_zones)

    rows: list[dict[str, object]] = [
        _intersection_context_row(
            "topology",
            topology.status,
            getattr(topology, "topology_result_id", "") or active_intersection,
            "intersection",
            source_refs=[active_intersection],
            notes=(
                f"legs={int(getattr(topology, 'leg_span_count', 0) or 0)}; "
                f"control areas={int(getattr(topology, 'control_area_count', 0) or 0)}"
            ),
        )
    ]

    for leg_row in list(getattr(topology, "leg_span_rows", []) or []):
        if active_leg and str(getattr(leg_row, "leg_ref", "") or "") != active_leg:
            continue
        rows.append(
            _intersection_context_row(
                "topology",
                getattr(leg_row, "status", "") or topology.status,
                getattr(leg_row, "leg_span_id", "") or active_leg,
                getattr(leg_row, "leg_role", "") or active_leg_role or "leg",
                source_refs=[
                    getattr(leg_row, "alignment_ref", ""),
                    getattr(leg_row, "region_ref", ""),
                    getattr(leg_row, "arm_policy_ref", ""),
                    getattr(leg_row, "grading_policy_ref", ""),
                ],
                boundary_refs=[getattr(leg_row, "control_area_ref", "")],
                notes=f"STA {float(getattr(leg_row, 'station_start', 0.0) or 0.0):.3f}-{float(getattr(leg_row, 'station_end', 0.0) or 0.0):.3f}",
            )
        )

    for control_row in list(getattr(topology, "control_area_rows", []) or []):
        if active_control_area and str(getattr(control_row, "control_area_id", "") or "") != active_control_area:
            continue
        rows.append(
            _intersection_context_row(
                "control_area",
                getattr(control_row, "status", "") or topology.status,
                getattr(control_row, "control_area_id", "") or active_control_area,
                "active_control_area",
                source_refs=[
                    getattr(control_row, "alignment_ref", ""),
                    getattr(control_row, "curb_return_policy_ref", ""),
                    getattr(control_row, "grading_policy_ref", ""),
                    getattr(control_row, "drainage_policy_ref", ""),
                ],
                boundary_refs=list(getattr(control_row, "control_region_refs", []) or []),
                notes=_station_range_note(getattr(control_row, "station_ranges", ()) or ()),
            )
        )

    for edge_row in list(getattr(edge_network, "edge_rows", []) or []):
        edge_leg = str(getattr(edge_row, "leg_ref", "") or "").strip()
        edge_control = str(getattr(edge_row, "control_area_ref", "") or "").strip()
        if active_leg and edge_leg and edge_leg != active_leg:
            continue
        if active_control_area and edge_control and edge_control != active_control_area:
            continue
        rows.append(
            _intersection_context_row(
                "edge_network",
                getattr(edge_row, "status", "") or edge_network.status,
                getattr(edge_row, "edge_id", ""),
                getattr(edge_row, "edge_role", "") or "edge",
                source_refs=[
                    getattr(edge_row, "source_policy_ref", ""),
                    getattr(edge_row, "alignment_ref", ""),
                    getattr(edge_row, "leg_ref", ""),
                ],
                boundary_refs=[edge_control],
                notes=(
                    f"family={getattr(edge_row, 'edge_family', '')}; side={getattr(edge_row, 'side', '')}; "
                    f"STA {float(getattr(edge_row, 'station_start', 0.0) or 0.0):.3f}-{float(getattr(edge_row, 'station_end', 0.0) or 0.0):.3f}"
                ),
            )
        )

    for zone_row in list(getattr(surface_zones, "zone_rows", []) or []):
        leg_refs = [str(value or "").strip() for value in list(getattr(zone_row, "leg_refs", ()) or ()) if str(value or "").strip()]
        control_refs = [
            str(value or "").strip()
            for value in list(getattr(zone_row, "control_area_refs", ()) or ())
            if str(value or "").strip()
        ]
        if active_leg and leg_refs and active_leg not in leg_refs:
            continue
        if active_control_area and control_refs and active_control_area not in control_refs:
            continue
        rows.append(
            _intersection_context_row(
                "surface_zone",
                getattr(zone_row, "status", "") or surface_zones.status,
                getattr(zone_row, "zone_id", ""),
                getattr(zone_row, "design_zone_role", "") or getattr(zone_row, "zone_role", "") or "zone",
                source_refs=[
                    getattr(zone_row, "vertical_policy_ref", ""),
                    *list(getattr(zone_row, "source_edge_refs", ()) or ()),
                ],
                boundary_refs=list(getattr(zone_row, "boundary_edge_refs", ()) or ()),
                notes=(
                    f"surface={getattr(zone_row, 'surface_role', '')}; "
                    f"triangulation={getattr(zone_row, 'triangulation_method', '')}"
                ),
            )
        )

    for clip_row in list(getattr(corridor_clips, "clip_rows", []) or []):
        clip_control = str(getattr(clip_row, "control_area_ref", "") or "").strip()
        clip_alignment = str(getattr(clip_row, "alignment_ref", "") or "").strip()
        if active_control_area and clip_control and clip_control != active_control_area:
            continue
        if active_alignment and clip_alignment and clip_alignment != active_alignment:
            continue
        rows.append(
            _intersection_context_row(
                "corridor_clip",
                getattr(clip_row, "status", "") or corridor_clips.status,
                getattr(clip_row, "clip_id", ""),
                getattr(clip_row, "surface_role", "") or "clip",
                source_refs=[clip_alignment, *list(getattr(clip_row, "control_region_refs", ()) or ())],
                boundary_refs=list(getattr(clip_row, "protected_zone_refs", ()) or ()),
                notes=(
                    f"{getattr(clip_row, 'clip_timing', '')}; "
                    f"{getattr(clip_row, 'clip_method', '')}"
                ),
            )
        )

    for hint_row in list(getattr(drainage_hints, "hint_rows", []) or []):
        control_refs = [
            str(value or "").strip()
            for value in list(getattr(hint_row, "control_area_refs", ()) or ())
            if str(value or "").strip()
        ]
        if active_control_area and control_refs and active_control_area not in control_refs:
            continue
        rows.append(
            _intersection_context_row(
                "drainage_hint",
                getattr(hint_row, "status", "") or drainage_hints.status,
                getattr(hint_row, "hint_id", ""),
                getattr(hint_row, "hint_kind", "") or "hint",
                source_refs=[
                    getattr(hint_row, "drainage_policy_ref", ""),
                    *list(getattr(hint_row, "source_edge_refs", ()) or ()),
                ],
                boundary_refs=[
                    getattr(hint_row, "zone_ref", ""),
                    *control_refs,
                ],
                notes=(
                    f"recommend={getattr(hint_row, 'recommended_element_kind', '')}; "
                    f"zone={getattr(hint_row, 'zone_role', '')}; "
                    f"{getattr(hint_row, 'notes', '')}"
                ),
            )
        )

    for policy in list(getattr(model, "grading_policy_rows", []) or []):
        policy_id = str(getattr(policy, "policy_id", "") or "").strip()
        if active_grading_policy and policy_id != active_grading_policy:
            continue
        if str(getattr(policy, "intersection_id", "") or "").strip() != active_intersection:
            continue
        rows.append(
            _intersection_context_row(
                "grading",
                getattr(policy, "status", "") or "active",
                policy_id,
                getattr(policy, "mode", "") or "grading_policy",
                source_refs=[
                    getattr(policy, "primary_alignment_ref", ""),
                    *list(getattr(policy, "secondary_alignment_refs", []) or []),
                ],
                notes=f"target crossfall={float(getattr(policy, 'target_crossfall_percent', 0.0) or 0.0):.3f}%",
            )
        )

    for policy in list(getattr(model, "drainage_policy_rows", []) or []):
        if str(getattr(policy, "intersection_id", "") or "").strip() != active_intersection:
            continue
        rows.append(
            _intersection_context_row(
                "drainage",
                getattr(policy, "status", "") or "active",
                getattr(policy, "policy_id", "") or "",
                getattr(policy, "capture_mode", "") or "drainage_policy",
                source_refs=list(getattr(policy, "drainage_element_refs", []) or []),
                boundary_refs=list(getattr(policy, "gutter_edge_refs", []) or []),
                notes=f"inlet spacing={float(getattr(policy, 'inlet_spacing', 0.0) or 0.0):.3f}; low point tolerance={float(getattr(policy, 'low_point_tolerance', 0.0) or 0.0):.3f}",
            )
        )

    return rows


def _intersection_context_row(
    family: str,
    status: str,
    row_id: str,
    role: str,
    *,
    source_refs: list[str] | tuple[str, ...] | None = None,
    boundary_refs: list[str] | tuple[str, ...] | None = None,
    notes: str = "",
) -> dict[str, object]:
    return {
        "family": str(family or "").strip(),
        "status": _normalized_intersection_review_status(status),
        "row_id": str(row_id or "").strip(),
        "role": str(role or "").strip(),
        "source_refs": [str(value).strip() for value in list(source_refs or []) if str(value or "").strip()],
        "boundary_refs": [str(value).strip() for value in list(boundary_refs or []) if str(value or "").strip()],
        "notes": str(notes or "").strip(),
    }


def _normalized_intersection_review_status(status: str) -> str:
    value = str(status or "").strip().lower()
    if value == "candidate":
        return "ready"
    if value == "warn":
        return "warning"
    return value or "unknown"


def _station_range_note(ranges: tuple[tuple[float, float], ...] | list[tuple[float, float]]) -> str:
    pieces = []
    for start, end in list(ranges or []):
        pieces.append(f"STA {float(start or 0.0):.3f}-{float(end or 0.0):.3f}")
    return ", ".join(pieces)


def _intersection_context_summary(rows: list[dict[str, object]]) -> str:
    if not rows:
        return ""
    counts: dict[str, int] = {}
    for row in rows:
        family = str(row.get("family", "") or "unknown").strip()
        counts[family] = counts.get(family, 0) + 1
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _first_component_ref(section_output, attr_name: str) -> str:
    """Return the first non-empty component source reference from section output."""

    for row in list(getattr(section_output, "component_rows", []) or []):
        value = str(getattr(row, attr_name, "") or "").strip()
        if value:
            return value
    return ""


def _applied_section_structure_ref(applied_section) -> str:
    """Return the singular active Structure ref carried by an AppliedSection."""

    for value in list(getattr(applied_section, "active_structure_ids", []) or []):
        text = str(value or "").strip()
        if text:
            return text
    for component in list(getattr(applied_section, "component_rows", []) or []):
        for value in list(getattr(component, "structure_ids", []) or []):
            text = str(value or "").strip()
            if text:
                return text
    return ""


def _applied_section_drainage_ref(applied_section) -> str:
    """Return the first active Drainage Element ref carried by an AppliedSection."""

    for point in list(getattr(applied_section, "point_rows", []) or []):
        text = str(getattr(point, "drainage_ref", "") or "").strip()
        if text:
            return text
    for component in list(getattr(applied_section, "component_rows", []) or []):
        for value in list(getattr(component, "drainage_refs", []) or []):
            text = str(value or "").strip()
            if text:
                return text
    return ""


def _source_owner_status(*, object_label: str, source_ref: str) -> str:
    """Classify how strongly one source owner is resolved."""

    if str(object_label or "").strip():
        return "resolved"
    if str(source_ref or "").strip():
        return "source_ref"
    return "unresolved"


def _display_source_id(value: object, prefix: str = "") -> str:
    """Return a compact source id for table labels without changing stored refs."""

    text = str(value or "").strip()
    prefix_text = str(prefix or "").strip()
    if prefix_text and text.startswith(prefix_text):
        return text[len(prefix_text) :]
    return text


def _viewer_station_rows_from_applied_section_set(applied_section_set) -> list[dict[str, object]]:
    """Build viewer station rows from a v1 AppliedSectionSet result contract."""

    rows = []
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    for index, row in enumerate(list(getattr(applied_section_set, "station_rows", []) or [])):
        try:
            station = float(getattr(row, "station", 0.0) or 0.0)
        except Exception:
            continue
        section_id = str(getattr(row, "applied_section_id", "") or "")
        section = sections.get(section_id)
        alignment_id = str(getattr(section, "alignment_id", "") or getattr(applied_section_set, "alignment_id", "") or "").strip()
        alignment_label = _display_source_id(alignment_id, "alignment:") if alignment_id else ""
        label = f"{alignment_label} | STA {station:.3f}" if alignment_label else f"STA {station:.3f}"
        rows.append(
            {
                "index": index,
                "station": station,
                "label": label,
                "applied_section_id": section_id,
                "alignment_id": alignment_id,
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
                "label": (
                    f"{_display_source_id(str(getattr(section, 'alignment_id', '') or ''), 'alignment:')} | STA {station:.3f}"
                    if str(getattr(section, "alignment_id", "") or "").strip()
                    else f"STA {station:.3f}"
                ),
                "applied_section_id": str(getattr(section, "applied_section_id", "") or ""),
                "alignment_id": str(getattr(section, "alignment_id", "") or ""),
                "kind": "applied_section",
            }
        )
    return rows


def _merge_viewer_station_rows(*row_groups: list[dict[str, object]] | None) -> list[dict[str, object]]:
    """Merge station navigation rows without dropping v1 result stations."""

    by_key: dict[tuple[str, float], dict[str, object]] = {}
    for rows in row_groups:
        for row in list(rows or []):
            item = dict(row or {})
            try:
                station = round(float(item.get("station", 0.0) or 0.0), 6)
            except Exception:
                continue
            section_id = str(item.get("applied_section_id", "") or "").strip()
            alignment_id = str(item.get("alignment_id", "") or "").strip()
            base_key = (f"station:{station}", station)
            key = (section_id or alignment_id or f"station:{station}", station)
            if (section_id or alignment_id) and base_key in by_key:
                key = base_key
            existing = by_key.get(key, {})
            merged = dict(existing)
            merged.update({key: value for key, value in item.items() if value not in (None, "")})
            by_key[key] = merged
    merged_rows = [
        by_key[key]
        for key in sorted(
            by_key,
            key=lambda value: (value[1], str(by_key[value].get("alignment_id", "") or ""), str(value[0])),
        )
    ]
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
    active_structure_ref = str(viewer_context.get("active_structure_ref", "") or "").strip()
    if active_structure_ref:
        rows.append(
            {
                "kind": "active_structure",
                "label": "Active Structure",
                "value": active_structure_ref,
                "notes": "Resolved from Station Context for the current station.",
            }
        )
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


def _apply_station_context_to_viewer_context(
    viewer_context: dict[str, object] | None,
    *,
    station: float,
    region_model=None,
    structure_model=None,
    drainage_model=None,
) -> dict[str, object]:
    """Populate viewer context from the shared station-context resolver when possible."""

    output = dict(viewer_context or {})
    source_region_model = _as_region_source_model(region_model)
    if source_region_model is None:
        return output
    try:
        context = StationContextResolver().resolve(
            region_model=source_region_model,
            structure_model=_as_structure_source_model(structure_model),
            drainage_model=_as_drainage_source_model(drainage_model),
            station=float(station),
        )
    except Exception:
        return output
    region_id = str(getattr(getattr(context, "region_context", None), "region_id", "") or "").strip()
    if region_id:
        output["station_context_region_ref"] = region_id
    structure_refs = _unique_text_values(
        list(getattr(getattr(context, "structure_result", None), "active_structure_ids", []) or [])
    )
    if structure_refs:
        output["active_structure_ref"] = structure_refs[0]
        output["structure_summary"] = ", ".join(structure_refs)
        output["structure_rows"] = structure_refs
    drainage_refs = _unique_text_values(list(getattr(context, "active_drainage_refs", []) or []))
    if drainage_refs:
        output["active_drainage_ref"] = drainage_refs[0]
        output["drainage_summary"] = ", ".join(drainage_refs)
        output["active_drainage_refs"] = drainage_refs
    drainage_refs_by_side = dict(getattr(context, "active_drainage_refs_by_side", {}) or {})
    if drainage_refs_by_side:
        output["active_drainage_refs_by_side"] = {
            str(side or "").strip(): _unique_text_values(list(refs or []))
            for side, refs in drainage_refs_by_side.items()
            if str(side or "").strip()
        }
    flow_route_refs = _unique_text_values(list(getattr(context, "active_flow_route_refs", []) or []))
    if flow_route_refs:
        output["active_flow_route_ref"] = flow_route_refs[0]
        output["flow_route_summary"] = ", ".join(flow_route_refs)
        output["active_flow_route_refs"] = flow_route_refs
    return output


def _as_region_source_model(value):
    if value is None:
        return None
    if hasattr(value, "region_rows"):
        return value
    try:
        from ..objects.obj_region import to_region_model

        return to_region_model(value)
    except Exception:
        return None


def _as_structure_source_model(value):
    if value is None:
        return None
    if hasattr(value, "structure_rows"):
        return value
    try:
        from ..objects.obj_structure import to_structure_model

        return to_structure_model(value)
    except Exception:
        return None


def _as_drainage_source_model(value):
    if value is None:
        return None
    if hasattr(value, "element_rows"):
        return value
    try:
        from ..objects.obj_drainage import to_drainage_model

        return to_drainage_model(value)
    except Exception:
        return None


def _unique_text_values(values: list[object]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


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
    preferred_applied_section_id: str = "",
) -> dict[str, object] | None:
    """Build a v1 section viewer payload from a FreeCAD document when possible."""

    adapter = LegacyDocumentAdapter()
    project = adapter._find_project(document)
    return _build_v1_applied_section_set_preview(
        document,
        project=project,
        preferred_applied_section_set=preferred_section_set,
        preferred_station=preferred_station,
        preferred_applied_section_id=preferred_applied_section_id,
    )


def _build_v1_applied_section_set_preview(
    document,
    *,
    project=None,
    preferred_applied_section_set=None,
    preferred_station: float | None = None,
    preferred_applied_section_id: str = "",
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
    try:
        from ..objects.obj_drainage import find_v1_drainage_model
    except Exception:
        find_v1_drainage_model = None
    try:
        from ..objects.obj_superelevation import find_v1_superelevation_source
    except Exception:
        find_v1_superelevation_source = None
    try:
        from ..objects.obj_intersection import find_v1_intersection_model
    except Exception:
        find_v1_intersection_model = None

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

    preferred_section_id = str(preferred_applied_section_id or "").strip()
    applied_section = None
    if preferred_section_id:
        for section in sections:
            if str(getattr(section, "applied_section_id", "") or "").strip() == preferred_section_id:
                applied_section = section
                break
    if applied_section is None:
        applied_section = min(
            sections,
            key=lambda row: abs(float(getattr(row, "station", 0.0) or 0.0) - target_station),
        )
    target_station = float(getattr(applied_section, "station", target_station) or target_station)
    station_payload = _nearest_station_payload(
        station_rows,
        target_station,
        applied_section_id=str(getattr(applied_section, "applied_section_id", "") or ""),
    ) or {
        "station": target_station,
        "label": f"STA {target_station:.3f}",
        "applied_section_id": str(getattr(applied_section, "applied_section_id", "") or ""),
        "alignment_id": str(getattr(applied_section, "alignment_id", "") or ""),
    }
    section_output = SectionOutputMapper().map_applied_section(applied_section)
    drawing_payload = CrossSectionDrawingMapper().map_applied_section_set(
        applied_section_set,
        station=target_station,
    )

    assembly_model = find_v1_assembly_model(document) if find_v1_assembly_model is not None else None
    region_model = find_v1_region_model(document) if find_v1_region_model is not None else None
    structure_model = find_v1_structure_model(document) if find_v1_structure_model is not None else None
    drainage_model = find_v1_drainage_model(document) if find_v1_drainage_model is not None else None
    superelevation_model = find_v1_superelevation_source(document) if find_v1_superelevation_source is not None else None
    intersection_model = find_v1_intersection_model(document) if find_v1_intersection_model is not None else None
    source_objects = {
        "project": project,
        "applied_section_set": applied_obj,
        "alignment": None,
        "assembly_model": assembly_model,
        "region_model": region_model,
        "corridor": getattr(project, "Corridor", None) if project is not None else None,
        "cut_fill_calc": getattr(project, "CutFillCalc", None) if project is not None else None,
        "structure_model": structure_model,
        "drainage_model": drainage_model,
        "superelevation_model": superelevation_model,
        "intersection_model": intersection_model,
    }
    viewer_context: dict[str, object] = {
        "active_structure_ref": _applied_section_structure_ref(applied_section),
        "active_drainage_ref": _applied_section_drainage_ref(applied_section),
    }
    viewer_context = _apply_station_context_to_viewer_context(
        viewer_context,
        station=target_station,
        region_model=region_model,
        structure_model=structure_model,
        drainage_model=drainage_model,
    )
    intersection_context_rows = _build_intersection_context_rows(
        document,
        intersection_model_obj=intersection_model,
        applied_section=applied_section,
    )
    intersection_context_summary = _intersection_context_summary(intersection_context_rows)
    if intersection_context_summary:
        viewer_context["intersection_contract_summary"] = intersection_context_summary
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
            drainage_model=drainage_model,
            superelevation_model=superelevation_model,
            intersection_model=intersection_model,
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
        "intersection_context_rows": intersection_context_rows,
        "earthwork_hint_rows": earthwork_hint_rows,
        "review_marker_rows": review_marker_rows,
        "corridor_review_rows": _build_corridor_review_rows(document),
        "diagnostic_rows": diagnostic_rows,
        "source_objects": source_objects,
    }


def _nearest_station_payload(
    rows: list[dict[str, object]],
    station: float,
    *,
    applied_section_id: str = "",
) -> dict[str, object] | None:
    """Return the station navigation row nearest to a target station."""

    if not rows:
        return None
    section_id = str(applied_section_id or "").strip()
    if section_id:
        for row in [dict(item or {}) for item in rows]:
            if str(row.get("applied_section_id", "") or "").strip() == section_id:
                row["is_current"] = True
                return row
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
    superelevation_line = _section_output_superelevation_summary(section_output)
    if superelevation_line:
        lines.append(superelevation_line)
    intersection_line = _section_output_intersection_summary(section_output)
    if intersection_line:
        lines.append(intersection_line)
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


def _section_output_superelevation_summary(section_output) -> str:
    rows = {
        str(getattr(row, "kind", "") or ""): row
        for row in list(getattr(section_output, "summary_rows", []) or [])
    }
    superelevation_id = str(getattr(rows.get("superelevation_id"), "value", "") or "").strip()
    if not superelevation_id:
        return ""
    left = float(getattr(rows.get("superelevation_left_crossfall"), "value", 0.0) or 0.0)
    right = float(getattr(rows.get("superelevation_right_crossfall"), "value", 0.0) or 0.0)
    transition = str(getattr(rows.get("superelevation_transition"), "value", "") or "").strip()
    pieces = [f"Superelevation: {superelevation_id}", f"L {left:.3f}%", f"R {right:.3f}%"]
    if transition:
        pieces.append(f"Transition {transition}")
    return " | ".join(pieces)


def _section_output_intersection_summary(section_output) -> str:
    rows = {
        str(getattr(row, "kind", "") or ""): row
        for row in list(getattr(section_output, "summary_rows", []) or [])
    }
    intersection_id = str(getattr(rows.get("intersection_id"), "value", "") or "").strip()
    if not intersection_id:
        return ""
    control_area = str(getattr(rows.get("intersection_control_area"), "value", "") or "").strip()
    leg = str(getattr(rows.get("intersection_leg"), "value", "") or "").strip()
    control_regions = str(getattr(rows.get("intersection_control_regions"), "value", "") or "").strip()
    grading_policy = str(getattr(rows.get("intersection_grading_policy"), "value", "") or "").strip()
    pieces = [f"Intersection: {intersection_id}"]
    if control_area:
        pieces.append(f"Control Area {control_area}")
    if leg:
        pieces.append(f"Leg {leg}")
    if control_regions:
        pieces.append(f"Regions {control_regions}")
    if grading_policy:
        pieces.append(f"Grading {grading_policy}")
    return " | ".join(pieces)


def show_v1_section_preview(
    *,
    document=None,
    preferred_section_set=None,
    preferred_station: float | None = None,
    preferred_applied_section_id: str = "",
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
            preferred_applied_section_id=preferred_applied_section_id,
        )
    if preview is None and active_document is not None:
        preview = _build_missing_v1_applied_section_set_preview(document_label=document_label)
    if preview is None:
        preview = build_demo_section_preview(document_label=document_label)
    explicit_review_marker_rows = None
    if extra_context:
        context = dict(extra_context)
        preview.update(context)
        explicit_review_marker_rows = context.get("review_marker_rows", None)
        if "station_row" in context or context.get("preferred_applied_section_id"):
            _retarget_preview_to_station(preview)
    viewer_context = dict(preview.get("viewer_context", {}) or {})
    active_structure_ref = _applied_section_structure_ref(preview.get("applied_section", None))
    if active_structure_ref and not str(viewer_context.get("active_structure_ref", "") or "").strip():
        viewer_context["active_structure_ref"] = active_structure_ref
        preview["viewer_context"] = viewer_context
    active_drainage_ref = _applied_section_drainage_ref(preview.get("applied_section", None))
    if active_drainage_ref and not str(viewer_context.get("active_drainage_ref", "") or "").strip():
        viewer_context["active_drainage_ref"] = active_drainage_ref
        preview["viewer_context"] = viewer_context
    source_objects = dict(preview.get("source_objects", {}) or {})
    station_payload = dict(preview.get("station_row", {}) or {})
    station_value = station_payload.get("station", None)
    if station_value is None:
        station_value = getattr(preview.get("applied_section", None), "station", 0.0)
    viewer_context = _apply_station_context_to_viewer_context(
        viewer_context,
        station=float(station_value or 0.0),
        region_model=source_objects.get("region_model"),
        structure_model=source_objects.get("structure_model"),
        drainage_model=source_objects.get("drainage_model"),
    )
    if "intersection_context_rows" not in preview:
        preview["intersection_context_rows"] = _build_intersection_context_rows(
            active_document,
            intersection_model_obj=source_objects.get("intersection_model"),
            applied_section=preview.get("applied_section", None),
        )
    intersection_context_summary = _intersection_context_summary(
        [dict(row or {}) for row in list(preview.get("intersection_context_rows", []) or [])]
    )
    if intersection_context_summary:
        viewer_context["intersection_contract_summary"] = intersection_context_summary
    preview["viewer_context"] = viewer_context
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
        drainage_model=source_objects.get("drainage_model"),
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
    target_section_id = str(station_row.get("applied_section_id", "") or "").strip()
    if target_section_id:
        for section in sections:
            if str(getattr(section, "applied_section_id", "") or "").strip() == target_section_id:
                preview["applied_section"] = section
                preview["section_output"] = SectionOutputMapper().map_applied_section(section)
                preview["drawing_payload"] = CrossSectionDrawingMapper().map_applied_section_set(
                    section_set,
                    station=float(getattr(section, "station", 0.0) or 0.0),
                )
                return
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
    preferred_applied_section_id = ""
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
        preferred_applied_section_id = str(ui_context.get("preferred_applied_section_id", "") or "").strip()
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
        preferred_applied_section_id=preferred_applied_section_id,
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

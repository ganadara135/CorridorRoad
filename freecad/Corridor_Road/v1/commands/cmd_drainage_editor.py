"""Drainage editor command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets  # noqa: F401 - runtime-injected UI collaborator

from ..ui.editors.drainage_editor import (
    V1DrainageEditorTaskPanel,
    configure_drainage_editor_task_panel_runtime,
)
from ..services.editing import prepare_drainage_edit

from ..models.source.drainage_model import (
    DrainageElementRow,
    DrainageFlowRoute,
    DrainageModel,
    DrainagePolicySet,
)
from ..objects.obj_drainage import (  # noqa: F401 - runtime-injected UI collaborator
    create_or_update_v1_drainage_model_object,
    find_v1_drainage_model,
    to_drainage_model,
)
from ..objects.obj_region import find_v1_region_model, to_region_model  # noqa: F401 - runtime-injected UI collaborator
from ..objects.obj_stationing import find_v1_stationing
from ..objects.obj_structure import find_v1_structure_model, to_structure_model  # noqa: F401 - runtime-injected UI collaborator
from ..services.evaluation.drainage_resolution_service import (  # noqa: F401 - runtime-injected UI collaborator
    DrainageValidationService,
    build_drainage_pipeline_segment_candidates,
)
from ..ui.common.styles import apply_clickable_tab_style  # noqa: F401 - runtime-injected UI collaborator
from .cmd_drainage_review import (  # noqa: F401 - runtime-injected UI collaborator
    build_drainage_review_output,
    show_drainage_pipeline_networks_preview_object,
    show_drainage_pipeline_segment_preview_object,
)


ELEMENT_KIND_CHOICES = ["ditch", "gutter", "swale", "channel", "culvert_reference", "inlet_reference", "outfall_reference"]
SIDE_CHOICES = ["", "left", "right", "both", "center"]
FLOW_INTENT_CHOICES = ["collect_and_convey", "edge_runoff_capture", "ditch_outfall", "cross_drainage_transfer"]
ELEMENT_KIND_COLUMN = 1
ELEMENT_ASSEMBLY_COLUMN = 5
ELEMENT_POLICY_COLUMN = 6
ELEMENT_STRUCTURE_COLUMN = 7
FLOW_ROUTE_FROM_COLUMN = 1
FLOW_ROUTE_TO_COLUMN = 2
FLOW_ROUTE_OUTLET_COLUMN = 3
INVALID_COMBO_STYLE = "QComboBox { background-color: rgb(96, 40, 40); color: rgb(255, 255, 255); }"
DISABLED_COMBO_STYLE = "QComboBox { background-color: rgb(48, 48, 48); color: rgb(140, 140, 140); }"
DRAINAGE_PRESETS = {
    "Roadside Ditch": {
        "note": "One right-side roadside ditch across the available station range.",
        "elements": [
            {
                "id": "drainage:side-ditch-right",
                "kind": "ditch",
                "side": "right",
                "start": 0.0,
                "end": 1.0,
                "subassembly": "ditch:right",
                "policy": "drainage-policy:lined-concrete",
            },
            {
                "id": "drainage:outfall-main",
                "kind": "outfall_reference",
                "side": "right",
                "start": 0.98,
                "end": 1.0,
                "policy": "drainage-policy:lined-concrete",
            }
        ],
        "policies": [
            {
                "id": "drainage-policy:lined-concrete",
                "flow_intent": "collect_and_convey",
                "min_grade": "0.005",
                "low_point": "review_sag",
                "collection": "roadside",
                "discharge": "outfall",
                "earthwork": "preserve_conveyance",
            }
        ],
        "flow_routes": [
            {
                "id": "flow-route:flowId-01",
                "kind": "roadside_flow",
                "from": "drainage:side-ditch-right",
                "to": "drainage:outfall-main",
                "start": 0.0,
                "end": 1.0,
                "outlet": "drainage:outfall-main",
                "risk": "medium",
            }
        ],
    },
    "Dual Side Ditches": {
        "note": "Left and right roadside ditches with one shared flow policy.",
        "elements": [
            {
                "id": "drainage:side-ditch-left",
                "kind": "ditch",
                "side": "left",
                "start": 0.0,
                "end": 1.0,
                "subassembly": "ditch:left",
                "policy": "drainage-policy:lined-concrete",
            },
            {
                "id": "drainage:side-ditch-right",
                "kind": "ditch",
                "side": "right",
                "start": 0.0,
                "end": 1.0,
                "subassembly": "ditch:right",
                "policy": "drainage-policy:lined-concrete",
            },
            {
                "id": "drainage:outfall-left",
                "kind": "outfall_reference",
                "side": "left",
                "start": 0.98,
                "end": 1.0,
                "policy": "drainage-policy:lined-concrete",
            },
            {
                "id": "drainage:outfall-right",
                "kind": "outfall_reference",
                "side": "right",
                "start": 0.98,
                "end": 1.0,
                "policy": "drainage-policy:lined-concrete",
            },
        ],
        "policies": [
            {
                "id": "drainage-policy:lined-concrete",
                "flow_intent": "collect_and_convey",
                "min_grade": "0.005",
                "low_point": "review_sag",
                "collection": "both_sides",
                "discharge": "outfall",
                "earthwork": "preserve_conveyance",
            }
        ],
        "flow_routes": [
            {
                "id": "flow-route:flowId-01",
                "kind": "roadside_flow",
                "from": "drainage:side-ditch-left",
                "to": "drainage:outfall-left",
                "start": 0.0,
                "end": 1.0,
                "outlet": "drainage:outfall-left",
                "risk": "medium",
            },
            {
                "id": "flow-route:flowId-02",
                "kind": "roadside_flow",
                "from": "drainage:side-ditch-right",
                "to": "drainage:outfall-right",
                "start": 0.0,
                "end": 1.0,
                "outlet": "drainage:outfall-right",
                "risk": "medium",
            },
        ],
    },
    "Culvert Crossing": {
        "note": "Roadside ditch continuity with one culvert/cross-drain reference at the middle of the station range.",
        "elements": [
            {
                "id": "drainage:side-ditch-left",
                "kind": "ditch",
                "side": "left",
                "start": 0.0,
                "end": 1.0,
                "subassembly": "ditch:left",
                "policy": "drainage-policy:roadside-ditch",
            },
            {
                "id": "drainage:side-ditch-right",
                "kind": "ditch",
                "side": "right",
                "start": 0.0,
                "end": 1.0,
                "subassembly": "ditch:right",
                "policy": "drainage-policy:roadside-ditch",
            },
            {
                "id": "drainage:culvert-01",
                "kind": "culvert_reference",
                "side": "center",
                "start": 0.48,
                "end": 0.52,
                "subassembly": "",
                "policy": "drainage-policy:cross-drain",
            },
        ],
        "policies": [
            {
                "id": "drainage-policy:roadside-ditch",
                "flow_intent": "collect_and_convey",
                "min_grade": "0.005",
                "low_point": "review_sag",
                "collection": "roadside",
                "discharge": "culvert",
                "earthwork": "preserve_conveyance",
            },
            {
                "id": "drainage-policy:cross-drain",
                "flow_intent": "cross_drainage_transfer",
                "min_grade": "",
                "low_point": "must_connect_to_outfall",
                "collection": "upstream_ditch",
                "discharge": "downstream_ditch",
                "earthwork": "structure_control",
            },
        ],
        "flow_routes": [
            {
                "id": "flow-route:flowId-01",
                "kind": "ditch_to_structure",
                "from": "drainage:side-ditch-left",
                "to": "drainage:culvert-01",
                "start": 0.45,
                "end": 0.55,
                "outlet": "",
                "risk": "high",
            }
        ],
    },
    "Drainage Structures Flow": {
        "note": "Structure-backed station-band flow example matching the Structures preset: ditch sections drain to local inlets, inlet pipes connect to one culvert, then culvert discharges to outlet headwall/outfall.",
        "elements": [
            {
                "id": "drainage:side-ditch-right-01",
                "kind": "ditch",
                "side": "right",
                "start": 0.0,
                "end": 0.24,
                "subassembly": "ditch:right",
                "policy": "drainage-policy:roadside-ditch",
            },
            {
                "id": "drainage:side-ditch-right-02",
                "kind": "ditch",
                "side": "right",
                "start": 0.24,
                "end": 0.38,
                "subassembly": "ditch:right",
                "policy": "drainage-policy:roadside-ditch",
            },
            {
                "id": "drainage:side-ditch-right-03",
                "kind": "ditch",
                "side": "right",
                "start": 0.38,
                "end": 0.52,
                "subassembly": "ditch:right",
                "policy": "drainage-policy:roadside-ditch",
            },
            {
                "id": "drainage:inlet-01",
                "kind": "inlet_reference",
                "side": "right",
                "start": 0.23,
                "end": 0.25,
                "policy": "drainage-policy:structure-node",
                "structure": "structure:inlet-01",
            },
            {
                "id": "drainage:inlet-02",
                "kind": "inlet_reference",
                "side": "right",
                "start": 0.37,
                "end": 0.39,
                "policy": "drainage-policy:structure-node",
                "structure": "structure:inlet-02",
            },
            {
                "id": "drainage:inlet-03",
                "kind": "inlet_reference",
                "side": "right",
                "start": 0.51,
                "end": 0.53,
                "policy": "drainage-policy:structure-node",
                "structure": "structure:inlet-03",
            },
            {
                "id": "drainage:culvert-01",
                "kind": "culvert_reference",
                "side": "center",
                "start": 0.62,
                "end": 0.72,
                "policy": "drainage-policy:cross-drain",
                "structure": "structure:culvert-01",
            },
            {
                "id": "drainage:outlet-01",
                "kind": "outfall_reference",
                "side": "left",
                "start": 0.78,
                "end": 0.82,
                "policy": "drainage-policy:outfall",
                "structure": "structure:outlet-01",
            },
        ],
        "policies": [
            {
                "id": "drainage-policy:roadside-ditch",
                "flow_intent": "collect_and_convey",
                "min_grade": "0.005",
                "low_point": "collect_at_inlet",
                "collection": "right_side_ditch",
                "discharge": "inlet",
                "earthwork": "preserve_conveyance",
            },
            {
                "id": "drainage-policy:structure-node",
                "flow_intent": "edge_runoff_capture",
                "min_grade": "",
                "low_point": "catch_basin",
                "collection": "ditch_inlet",
                "discharge": "pipe_culvert",
                "earthwork": "structure_control",
            },
            {
                "id": "drainage-policy:cross-drain",
                "flow_intent": "cross_drainage_transfer",
                "min_grade": "",
                "low_point": "must_connect_to_outfall",
                "collection": "inlet_pipe",
                "discharge": "outlet_headwall",
                "earthwork": "structure_control",
            },
            {
                "id": "drainage-policy:outfall",
                "flow_intent": "ditch_outfall",
                "min_grade": "",
                "low_point": "free_discharge",
                "collection": "culvert_outlet",
                "discharge": "outfall",
                "earthwork": "protect_outlet",
            },
        ],
        "flow_routes": [
            {
                "id": "flow-route:flowId-01",
                "kind": "ditch_to_inlet",
                "from": "drainage:side-ditch-right-01",
                "to": "drainage:inlet-01",
                "outlet": "",
                "risk": "medium",
            },
            {
                "id": "flow-route:flowId-02",
                "kind": "ditch_to_inlet",
                "from": "drainage:side-ditch-right-02",
                "to": "drainage:inlet-02",
                "outlet": "",
                "risk": "medium",
            },
            {
                "id": "flow-route:flowId-03",
                "kind": "ditch_to_inlet",
                "from": "drainage:side-ditch-right-03",
                "to": "drainage:inlet-03",
                "outlet": "",
                "risk": "medium",
            },
            {
                "id": "flow-route:flowId-04",
                "kind": "collector_pipe",
                "from": "drainage:inlet-01",
                "to": "drainage:inlet-02",
                "outlet": "",
                "risk": "high",
            },
            {
                "id": "flow-route:flowId-05",
                "kind": "collector_pipe",
                "from": "drainage:inlet-02",
                "to": "drainage:inlet-03",
                "outlet": "",
                "risk": "high",
            },
            {
                "id": "flow-route:flowId-06",
                "kind": "inlet_to_culvert",
                "from": "drainage:inlet-03",
                "to": "drainage:culvert-01",
                "outlet": "",
                "risk": "high",
            },
            {
                "id": "flow-route:flowId-07",
                "kind": "culvert_to_outfall",
                "from": "drainage:culvert-01",
                "to": "drainage:outlet-01",
                "outlet": "drainage:outlet-01",
                "risk": "medium",
            },
        ],
    },
}


def drainage_preset_names() -> list[str]:
    """Return available v1 Drainage preset names."""

    return list(DRAINAGE_PRESETS.keys())


def _preset_load_summary(model: DrainageModel) -> str:
    element_rows = list(getattr(model, "element_rows", []) or [])
    flow_route_rows = list(getattr(model, "flow_route_rows", []) or [])
    structure_refs = {
        str(getattr(row, "structure_ref", "") or "").strip()
        for row in element_rows
        if str(getattr(row, "structure_ref", "") or "").strip()
    }
    capture_count = 0
    pipe_count = 0
    element_by_id = {
        str(getattr(row, "drainage_element_id", "") or "").strip(): row
        for row in element_rows
        if str(getattr(row, "drainage_element_id", "") or "").strip()
    }
    for route in flow_route_rows:
        from_element = element_by_id.get(str(getattr(route, "from_element_ref", "") or "").strip())
        to_element = element_by_id.get(str(getattr(route, "to_element_ref", "") or "").strip())
        from_structure = str(getattr(from_element, "structure_ref", "") or "").strip()
        to_structure = str(getattr(to_element, "structure_ref", "") or "").strip()
        if from_structure and to_structure:
            pipe_count += 1
        else:
            capture_count += 1
    return (
        "Preset Summary: "
        f"elements={len(element_rows)}; "
        f"flow-routes={len(flow_route_rows)}; "
        f"structure-backed={len(structure_refs)}; "
        f"capture-only={capture_count}; "
        f"pipe-producing={pipe_count}"
    )


def _preset_structure_self_check_text(preset_name: str, *, structure_refs: list[str]) -> str:
    preset = DRAINAGE_PRESETS.get(str(preset_name or "").strip(), {})
    required_refs = _preset_required_structure_refs(preset)
    if not required_refs:
        return "Structure Preset Check: no Structure refs required."
    available = {str(value or "").strip() for value in list(structure_refs or []) if str(value or "").strip()}
    missing = [ref for ref in required_refs if ref not in available]
    matched = len(required_refs) - len(missing)
    if missing:
        return (
            "Structure Preset Check: "
            f"matched={matched}/{len(required_refs)}; "
            "missing=" + ", ".join(_display_source_ref(ref) for ref in missing)
        )
    return f"Structure Preset Check: matched={matched}/{len(required_refs)}."


def _preset_pair_self_check_text(model: DrainageModel, structure_model) -> str:
    structure_refs = {
        str(getattr(row, "structure_ref", "") or "").strip()
        for row in list(getattr(model, "element_rows", []) or [])
        if str(getattr(row, "structure_ref", "") or "").strip()
    }
    if not structure_refs:
        return "Preset Pair Check: no Structure-backed Drainage Elements."
    if structure_model is None:
        return "Preset Pair Check: no active Structures model; pipe endpoint compatibility was not checked."
    candidates = list(build_drainage_pipeline_segment_candidates(model, structure_model))
    capture_count = sum(1 for row in candidates if str(getattr(row, "status", "") or "") == "capture_only")
    ready_count = sum(1 for row in candidates if str(getattr(row, "status", "") or "") == "ready")
    unresolved = [
        row
        for row in candidates
        if str(getattr(row, "status", "") or "") not in {"capture_only", "ready"}
    ]
    text = (
        "Preset Pair Check: "
        f"capture-only={capture_count}; "
        f"ready-pipes={ready_count}; "
        f"unresolved={len(unresolved)}"
    )
    if unresolved:
        examples = [
            f"{_display_source_ref(getattr(row, 'flow_route_ref', ''))}:{getattr(row, 'status', '')}"
            for row in unresolved[:3]
        ]
        text += "; " + " | ".join(examples)
    return text


def _preset_station_range_self_check_text(
    model: DrainageModel,
    *,
    station_start: float,
    station_end: float,
    station_source: str = "fallback",
) -> str:
    lower = min(float(station_start), float(station_end))
    upper = max(float(station_start), float(station_end))
    element_rows = list(getattr(model, "element_rows", []) or [])
    if not element_rows:
        return (
            "Station Range Check: "
            f"source={station_source}; "
            f"document={_format_float(lower)}-{_format_float(upper)}; "
            "elements=none; invalid=0; outside=0"
        )
    element_ranges: list[tuple[float, float]] = []
    invalid_count = 0
    outside_count = 0
    tolerance = 1.0e-6
    for row in element_rows:
        start = _float_value(getattr(row, "station_start", 0.0))
        end = _float_value(getattr(row, "station_end", 0.0))
        element_ranges.append((start, end))
        if start >= end:
            invalid_count += 1
        if start < lower - tolerance or end > upper + tolerance:
            outside_count += 1
    element_lower = min(min(start, end) for start, end in element_ranges)
    element_upper = max(max(start, end) for start, end in element_ranges)
    return (
        "Station Range Check: "
        f"source={station_source}; "
        f"document={_format_float(lower)}-{_format_float(upper)}; "
        f"elements={_format_float(element_lower)}-{_format_float(element_upper)}; "
        f"invalid={invalid_count}; "
        f"outside={outside_count}"
    )


def _preset_required_structure_refs(preset: dict) -> list[str]:
    refs = [
        str(spec.get("structure", "") or "").strip()
        for spec in list((preset or {}).get("elements", []) or [])
        if str(spec.get("structure", "") or "").strip()
    ]
    return _unique_texts(refs)


class CmdV1DrainageEditor:
    def GetResources(self):
        return {
            "Pixmap": icon_path("drainage.svg"),
            "MenuText": "Drainage",
            "ToolTip": "Create and edit v1 drainage design intent",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_drainage_editor_command()


def run_v1_drainage_editor_command(document=None):
    """Open the v1 Drainage editor panel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    panel = V1DrainageEditorTaskPanel(document=doc)
    if _gui_available() and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


def starter_drainage_model_from_document(document=None, *, project=None) -> DrainageModel:
    """Build a non-destructive starter DrainageModel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    prj = project or find_project(doc)
    return DrainageModel(
        schema_version=1,
        project_id=_project_id(prj),
        drainage_model_id="drainage:main",
        label="Drainage",
        element_rows=[],
        policy_rows=[],
        flow_route_rows=[],
    )


def drainage_preset_model_from_document(
    preset_name: str,
    document=None,
    *,
    project=None,
) -> DrainageModel:
    """Build a non-destructive DrainageModel from a named preset."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    preset = DRAINAGE_PRESETS.get(str(preset_name or "").strip())
    if preset is None:
        raise ValueError(f"Unknown Drainage preset: {preset_name}")
    prj = project or find_project(doc)
    station_start, station_end = _document_station_range(doc)
    return DrainageModel(
        schema_version=1,
        project_id=_project_id(prj),
        drainage_model_id="drainage:main",
        label=str(preset_name or "Drainage"),
        element_rows=_preset_element_rows(preset, station_start=station_start, station_end=station_end),
        policy_rows=_preset_policy_rows(preset),
        flow_route_rows=_preset_flow_route_rows(preset),
    )


def apply_v1_drainage_model(*, document=None, drainage_model: DrainageModel):
    """Persist a DrainageModel into the active document."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prepared = prepare_drainage_edit(drainage_model)
    return create_or_update_v1_drainage_model_object(
        doc,
        drainage_model=prepared.model,
        project=find_project(doc),
    )


def _item_text(table, row: int, column: int) -> str:
    widget = table.cellWidget(row, column)
    if widget is not None:
        if hasattr(widget, "currentText"):
            return str(widget.currentText() or "").strip()
        if hasattr(widget, "text"):
            return str(widget.text() or "").strip()
    item = table.item(row, column)
    return "" if item is None else str(item.text() or "").strip()


def _combo_source_text(table, row: int, column: int) -> str:
    widget = table.cellWidget(row, column)
    if widget is not None and hasattr(widget, "currentData"):
        current_text = str(widget.currentText() or "").strip() if hasattr(widget, "currentText") else ""
        data = widget.currentData()
        data_text = str(data or "").strip() if data is not None else ""
        if data_text and (
            _display_source_ref(data_text) == current_text
            or _display_connection_point_ref(data_text) == current_text
        ):
            return data_text
    return _item_text(table, row, column)


def _display_prefixed_id(value: object, prefix: str) -> str:
    text = str(value or "").strip()
    if prefix and text.startswith(prefix):
        return text[len(prefix) :]
    return text


def _display_source_ref(value: object) -> str:
    text = str(value or "").strip()
    if ":" not in text:
        return text
    return text.split(":", 1)[1]


def _display_connection_point_ref(value: object) -> str:
    text = _display_prefixed_id(value, "connection:")
    if ":" in text:
        return text.rsplit(":", 1)[1]
    return text


def _structure_connection_point_by_ref(structure_model, connection_point_ref: str):
    expected = str(connection_point_ref or "").strip()
    if not expected:
        return None
    for row in list(getattr(structure_model, "connection_point_rows", []) or []):
        if str(getattr(row, "connection_point_id", "") or "").strip() == expected:
            return row
    return None


def _role_suffix(role: object) -> str:
    text = str(role or "").strip()
    return f" ({text})" if text else ""


def _source_prefixed_id(value: object, prefix: str, default_suffix: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        text = str(default_suffix or "").strip()
    if not text:
        return ""
    if prefix and not text.startswith(prefix):
        return f"{prefix}{text}"
    return text


def _source_ref_from_display(value: object, choices: list[str], *, default_prefix: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for choice in list(choices or []):
        if str(choice or "").strip() == text:
            return str(choice or "").strip()
        if _display_source_ref(choice) == text:
            return str(choice or "").strip()
        if _display_connection_point_ref(choice) == text:
            return str(choice or "").strip()
    if ":" in text:
        return text
    if default_prefix:
        return f"{default_prefix}{text}"
    return text


def _source_structure_ref(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if ":" in text:
        return text
    return f"structure:{text}"


def _unique_texts(values: list[object]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _structure_disabled_for_kind(kind: object) -> bool:
    return str(kind or "").strip().lower() == "ditch"


def _drainage_element_is_outlet_kind(kind: object) -> bool:
    text = str(kind or "").strip().lower()
    return text in {"outfall_reference", "outlet_reference"} or "outfall" in text or "outlet" in text


def _assembly_disabled_for_kind(kind: object) -> bool:
    return str(kind or "").strip().lower() != "ditch"


def _element_subassembly_ref(row) -> str:
    return str(getattr(row, "subassembly_ref", "") or "")


def _document_station_range(document) -> tuple[float, float]:
    values = _document_station_values(document)
    if values:
        return min(values), max(values)
    return 0.0, 100.0


def _document_station_values(document) -> list[float]:
    stationing = find_v1_stationing(document)
    stations = list(getattr(stationing, "StationValues", []) or []) if stationing is not None else []
    values: dict[float, float] = {}
    for station in stations:
        try:
            value = float(station)
        except Exception:
            continue
        values[round(value, 6)] = value
    return [values[key] for key in sorted(values)]


def _preset_element_rows(preset: dict, *, station_start: float, station_end: float) -> list[DrainageElementRow]:
    rows: list[DrainageElementRow] = []
    for index, spec in enumerate(list(preset.get("elements", []) or []), start=1):
        rows.append(
            DrainageElementRow(
                drainage_element_id=str(spec.get("id", "") or f"drainage:element:{index}"),
                element_kind=str(spec.get("kind", "") or "ditch"),
                side=str(spec.get("side", "") or ""),
                structure_ref=str(spec.get("structure", "") or ""),
                connection_point_ref="",
                region_ref="",
                subassembly_ref=str(spec.get("subassembly", "") or ""),
                station_start=_preset_station_value(spec.get("start", 0.0), station_start=station_start, station_end=station_end),
                station_end=_preset_station_value(spec.get("end", 1.0), station_start=station_start, station_end=station_end),
                policy_set_ref=str(spec.get("policy", "") or ""),
            )
        )
    return rows


def _preset_policy_rows(preset: dict) -> list[DrainagePolicySet]:
    rows: list[DrainagePolicySet] = []
    for index, spec in enumerate(list(preset.get("policies", []) or []), start=1):
        rows.append(
            DrainagePolicySet(
                policy_set_id=str(spec.get("id", "") or f"drainage-policy:{index}"),
                flow_intent=str(spec.get("flow_intent", "") or "collect_and_convey"),
                min_grade_rule=spec.get("min_grade", ""),
                low_point_rule=str(spec.get("low_point", "") or ""),
                collection_rule=str(spec.get("collection", "") or ""),
                discharge_rule=str(spec.get("discharge", "") or ""),
                earthwork_priority=str(spec.get("earthwork", "") or ""),
            )
        )
    return rows


def _preset_flow_route_rows(preset: dict) -> list[DrainageFlowRoute]:
    rows: list[DrainageFlowRoute] = []
    for index, spec in enumerate(list(preset.get("flow_routes", []) or []), start=1):
        rows.append(
            DrainageFlowRoute(
                flow_route_id=str(spec.get("id", "") or f"flow-route:{index}"),
                from_element_ref=str(spec.get("from", "") or ""),
                to_element_ref=str(spec.get("to", "") or ""),
                outlet_ref=str(spec.get("outlet", "") or ""),
                direction=str(spec.get("kind", "") or "roadside_flow"),
                risk_level=str(spec.get("risk", "") or ""),
            )
        )
    return rows


def _preset_station_value(value: object, *, station_start: float, station_end: float) -> float:
    lower = min(float(station_start), float(station_end))
    upper = max(float(station_start), float(station_end))
    span = max(upper - lower, 0.0)
    try:
        numeric = float(value)
    except Exception:
        numeric = 0.0
    if 0.0 <= numeric <= 1.0:
        return lower + span * numeric
    return min(max(numeric, lower), upper)


def _float_value(value: object) -> float:
    try:
        return float(str(value or "0").strip())
    except Exception:
        return 0.0


def _format_float(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"


def _format_validation_result(result, model: DrainageModel) -> str:
    summary = _flow_route_validation_summary_text(result)
    region_summary = _region_validation_summary_text(result)
    lines = [
        f"Validation: {result.status}",
        f"Elements: {len(model.element_rows)}",
        f"Policies: {len(model.policy_rows)}",
        f"Flow Routes: {len(model.flow_route_rows)}",
        f"Diagnostics: {len(result.diagnostic_rows)}",
    ]
    if summary:
        lines.append(summary)
    if region_summary:
        lines.append(region_summary)
    visible_diagnostics = [
        row for row in list(result.diagnostic_rows or [])
        if str(getattr(row, "kind", "") or "") != "flow_route_capture_pipe_summary"
    ]
    for row in visible_diagnostics[:6]:
        lines.append(f"{row.severity}:{row.kind}: {row.message}")
    remaining = len(visible_diagnostics) - 6
    if remaining > 0:
        lines.append(f"+{remaining} more diagnostics")
    return "\n".join(lines)


def _region_validation_summary_text(result) -> str:
    missing = 0
    outside = 0
    examples: list[str] = []
    for row in list(getattr(result, "diagnostic_rows", []) or []):
        kind = str(getattr(row, "kind", "") or "")
        if kind not in {"missing_drainage_element_region_ref", "drainage_element_outside_region_station_range"}:
            continue
        if kind == "missing_drainage_element_region_ref":
            missing += 1
        if kind == "drainage_element_outside_region_station_range":
            outside += 1
        if len(examples) < 2:
            notes = _note_pairs(str(getattr(row, "notes", "") or ""))
            source = _display_source_ref(notes.get("source_ref", ""))
            region = _display_source_ref(notes.get("region_ref", ""))
            element_start = notes.get("element_start", "")
            element_end = notes.get("element_end", "")
            region_start = notes.get("region_start", "")
            region_end = notes.get("region_end", "")
            if element_start and element_end and region_start and region_end:
                examples.append(f"{source or '-'} STA {element_start}-{element_end} vs {region or '-'} {region_start}-{region_end}")
            else:
                examples.append(f"{source or '-'} -> {region or '-'}")
    if not missing and not outside:
        return ""
    text = f"Region Summary: missing-region={missing}; outside-boundary={outside}"
    if examples:
        text += "; " + " | ".join(examples)
    return text


def _flow_route_validation_summary_text(result) -> str:
    for row in list(getattr(result, "diagnostic_rows", []) or []):
        if str(getattr(row, "kind", "") or "") != "flow_route_capture_pipe_summary":
            continue
        notes = _note_pairs(str(getattr(row, "notes", "") or ""))
        return (
            "Flow Route Summary: "
            f"capture-only={notes.get('capture_only_count', '0')}; "
            f"pipe-producing={notes.get('pipe_producing_count', '0')}; "
            f"fallback={notes.get('station_span_fallback_count', '0')}; "
            f"missing-elements={notes.get('missing_element_count', '0')}"
        )
    return ""


def _note_pairs(notes: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for part in str(notes or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip()
    return values


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _show_message(parent, title: str, message: str) -> None:
    if not _gui_available():
        return
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


def _gui_available() -> bool:
    return bool(Gui is not None and getattr(App, "GuiUp", False))


configure_drainage_editor_task_panel_runtime(globals())


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditDrainage", CmdV1DrainageEditor())

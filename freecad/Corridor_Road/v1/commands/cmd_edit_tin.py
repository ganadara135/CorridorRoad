"""TIN editor command for CorridorRoad v1."""

from __future__ import annotations

from pathlib import Path
import re

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from ..ui.editors.tin_editor import (  # noqa: F401 - runtime-injected UI collaborator
    V1TINEditorTaskPanel,
    _TINFacePickObserver,
    configure_tineditor_task_panel_runtime,
)

from ..models.source import TINEditOperation
from ..services.editing import TINEditService
from ..services.evaluation import TinSamplingService
from ..services.mapping import TINMeshPreviewMapper
from ..ui.common.styles import apply_clickable_tab_style  # noqa: F401 - runtime-injected UI collaborator
from .cmd_review_tin import (
    _focus_tin_preview_object,
    _selected_surface_object,
    _tin_surface_from_object,
    resolve_document_tin_max_triangles,
)


def apply_tin_editor_operations(
    *,
    document,
    base_surface,
    operations: list[TINEditOperation | dict[str, object]],
    object_name: str = "",
    mesh_module=None,
    app_module=None,
) -> dict[str, object]:
    """Apply TIN editor operations and update the edited mesh preview."""

    if document is None:
        raise RuntimeError("No active document.")
    if base_surface is None:
        raise ValueError("A TIN surface is required before applying TIN edits.")
    edit_result = TINEditService().apply_operations(
        base_surface,
        operations,
        edited_surface_id=_edited_surface_id(base_surface),
        edited_label=f"{getattr(base_surface, 'label', '') or getattr(base_surface, 'surface_id', '') or 'TIN'} (edited)",
    )
    preview = TINMeshPreviewMapper().create_or_update_preview_object(
        document,
        edit_result.surface,
        object_name=object_name or _edited_preview_object_name(edit_result.surface),
        label_prefix="TIN Edited Preview",
        surface_role="edited",
        mesh_module=mesh_module,
        app_module=app_module,
    )
    _route_preview_to_tree(document, preview)
    tree_records = _route_edit_records_to_tree(document, edit_result)
    return {
        "edit_result": edit_result,
        "edited_surface": edit_result.surface,
        "mesh_preview": preview,
        "operations": operations,
        "tree_records": tree_records,
    }


def run_v1_tin_editor_command(*, document=None, gui_module=Gui):
    """Open the v1 TIN editor for the selected or first document TIN-capable object."""

    if App is None and document is None:
        raise RuntimeError("FreeCAD is required.")
    document = document or getattr(App, "ActiveDocument", None)
    if document is None:
        raise RuntimeError("No active document.")
    source_obj = _selected_surface_object(gui_module, document)
    max_triangles = resolve_document_tin_max_triangles(document, surface_obj=source_obj)
    base_surface = _tin_surface_from_object(source_obj, max_triangles=max_triangles) if source_obj is not None else None
    if gui_module is not None and hasattr(gui_module, "Control"):
        gui_module.Control.showDialog(
            V1TINEditorTaskPanel(
                document=document,
                source_obj=source_obj,
                base_surface=base_surface,
                gui_module=gui_module,
            )
        )
    return base_surface


def build_tin_source_from_csv(
    *,
    document,
    csv_path: str,
    app_module=App,
) -> dict[str, object]:
    """Build a base TIN from CSV and make it available as the editable source preview."""

    if document is None:
        raise RuntimeError("No active document.")
    csv_path = str(csv_path or "").strip()
    if not csv_path:
        raise ValueError("CSV path is required.")
    from .cmd_review_tin import show_v1_tin_review

    preview = show_v1_tin_review(
        document=document,
        extra_context={
            "csv_path": csv_path,
            "surface_id": _surface_id_from_csv(csv_path),
            "create_mesh_preview": True,
            "doc_or_project": document,
            "input_coords": "auto",
        },
        app_module=app_module,
        gui_module=None,
    )
    mesh_preview = preview.get("mesh_preview", None)
    object_name = str(getattr(mesh_preview, "object_name", "") or "")
    source_obj = document.getObject(object_name) if object_name else None
    return {
        "tin_surface": preview["tin_surface"],
        "mesh_preview": mesh_preview,
        "source_obj": source_obj,
        "preview": preview,
    }


class CmdV1TINEditor:
    """Open the v1 TIN editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("pointcloud_tin.svg"),
            "MenuText": "TIN",
            "ToolTip": "Build, edit, preview, and review a v1 TIN from point-cloud data",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_tin_editor_command()


def _edited_surface_id(surface) -> str:
    base_id = str(getattr(surface, "surface_id", "") or "tin")
    return base_id if base_id.endswith(":edited") else f"{base_id}:edited"


def _edited_preview_object_name(surface) -> str:
    raw = str(getattr(surface, "surface_id", "") or "tin:edited")
    token = "".join(ch if ch.isalnum() else "_" for ch in raw).strip("_") or "tin_edited"
    return f"TINPreview_Edited_{token}"[:80]


def _rect_parameters(min_x, max_x, min_y, max_y) -> dict[str, float]:
    return {
        "min_x": float(min_x.value()),
        "max_x": float(max_x.value()),
        "min_y": float(min_y.value()),
        "max_y": float(max_y.value()),
    }


def _rect_from_xy_points(first: tuple[float, float], second: tuple[float, float]) -> dict[str, float]:
    x1, y1 = float(first[0]), float(first[1])
    x2, y2 = float(second[0]), float(second[1])
    return {
        "min_x": min(x1, x2),
        "max_x": max(x1, x2),
        "min_y": min(y1, y2),
        "max_y": max(y1, y2),
    }


def _boundary_rect_preview_name() -> str:
    return "CRV1_TIN_Boundary_Rectangle_Preview"


def _void_rect_preview_name() -> str:
    return "CRV1_TIN_Void_Rectangle_Preview"


def _default_sample_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "tests" / "samples"


def _select_tin_csv_path(gui_module) -> str:
    if gui_module is None:
        return ""
    start_dir = _default_sample_dir()
    if not start_dir.exists():
        start_dir = Path.home()
    try:
        selected, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select Point Cloud CSV for TIN",
            str(start_dir),
            "CSV Files (*.csv);;All Files (*.*)",
        )
        return str(selected or "")
    except Exception:
        return ""


def _surface_id_from_csv(csv_path: str) -> str:
    stem = Path(str(csv_path)).stem.strip() or "csv"
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in stem)
    return f"tin:{safe}"


def _update_rect_preview(
    document,
    name: str,
    rect: dict[str, float],
    *,
    surface=None,
    role: str = "boundary",
    final: bool = False,
):
    if document is None:
        return None
    try:
        import FreeCAD as app_module  # type: ignore
        import Part  # type: ignore
    except Exception:
        return None
    try:
        min_x = float(rect["min_x"])
        max_x = float(rect["max_x"])
        min_y = float(rect["min_y"])
        max_y = float(rect["max_y"])
    except Exception:
        return None
    if abs(max_x - min_x) <= 1.0e-9 or abs(max_y - min_y) <= 1.0e-9:
        return None
    z_value = _rect_preview_z(surface, rect)
    points = [
        app_module.Vector(min_x, min_y, z_value),
        app_module.Vector(max_x, min_y, z_value),
        app_module.Vector(max_x, max_y, z_value),
        app_module.Vector(min_x, max_y, z_value),
        app_module.Vector(min_x, min_y, z_value),
    ]
    try:
        obj = document.getObject(name)
        if obj is None:
            obj = document.addObject("Part::Feature", name)
        obj.Shape = Part.makePolygon(points)
        role_label = "Boundary" if str(role).lower() == "boundary" else "Void"
        obj.Label = f"TIN {role_label} Rectangle Preview"
        _set_string_property(obj, "CRRecordKind", "tin_edit_rectangle_preview")
        _set_string_property(obj, "PreviewRole", str(role or "boundary"))
        _set_string_property(obj, "PreviewState", "final" if final else "picking")
        _style_rect_preview(obj, role=role, final=final)
        try:
            document.recompute()
        except Exception:
            pass
        return obj
    except Exception:
        return None


def _remove_rect_preview(document, name: str) -> None:
    if document is None:
        return
    try:
        obj = document.getObject(name)
        if obj is not None:
            document.removeObject(str(getattr(obj, "Name", "") or name))
            try:
                document.recompute()
            except Exception:
                pass
    except Exception:
        pass


def _remove_rect_previews(document, *, role: str = "") -> None:
    if document is None:
        return
    role = str(role or "").lower()
    remove_names = []
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        label = str(getattr(obj, "Label", "") or "")
        record_kind = str(getattr(obj, "CRRecordKind", "") or "")
        preview_role = str(getattr(obj, "PreviewRole", "") or "").lower()
        is_preview = (
            record_kind == "tin_edit_rectangle_preview"
            or name.startswith("CRV1_TIN_Boundary_Rectangle_Preview")
            or name.startswith("CRV1_TIN_Void_Rectangle_Preview")
            or label.startswith("TIN Boundary Rectangle Preview")
            or label.startswith("TIN Void Rectangle Preview")
        )
        if not is_preview:
            continue
        if role and preview_role and preview_role != role:
            continue
        if role == "boundary" and "Void_Rectangle_Preview" in name:
            continue
        if role == "void" and "Boundary_Rectangle_Preview" in name:
            continue
        if name:
            remove_names.append(name)
    for name in _unique_strings(remove_names):
        try:
            document.removeObject(name)
        except Exception:
            pass
    if remove_names:
        try:
            document.recompute()
        except Exception:
            pass


def _rect_preview_z(surface, rect: dict[str, float]) -> float:
    rows = list(getattr(surface, "vertex_rows", []) or []) if surface is not None else []
    z_values = []
    for row in rows:
        try:
            z_values.append(float(row.z))
        except Exception:
            pass
    z_base = max(z_values) if z_values else 0.0
    try:
        span = max(
            abs(float(rect.get("max_x", 0.0)) - float(rect.get("min_x", 0.0))),
            abs(float(rect.get("max_y", 0.0)) - float(rect.get("min_y", 0.0))),
        )
    except Exception:
        span = 0.0
    return z_base + max(1.0, span * 0.01)


def _style_rect_preview(obj, *, role: str, final: bool) -> None:
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return
    is_void = str(role or "").lower() == "void"
    try:
        vobj.Visibility = True
        if hasattr(vobj, "Selectable"):
            vobj.Selectable = False
        vobj.LineColor = (1.0, 0.28, 0.18) if is_void else (0.10, 0.75, 1.0)
        vobj.ShapeColor = (1.0, 0.36, 0.18) if is_void else (0.15, 0.65, 1.0)
        if hasattr(vobj, "LineWidth"):
            vobj.LineWidth = 4.0 if final else 2.0
        if hasattr(vobj, "Transparency"):
            vobj.Transparency = 0
    except Exception:
        pass


def _spin_box():
    spin = QtWidgets.QDoubleSpinBox()
    spin.setRange(-1.0e12, 1.0e12)
    spin.setDecimals(3)
    spin.setSingleStep(1.0)
    return spin


def _table_item_text(table, row: int, col: int) -> str:
    item = table.item(row, col)
    return str(item.text() if item is not None else "").strip()


def triangle_ids_from_selected_faces(gui_module=Gui, *, source_obj=None) -> list[str]:
    """Return TIN triangle ids inferred from selected FreeCAD mesh face subelements."""

    if gui_module is None or not hasattr(gui_module, "Selection"):
        return []
    selections = _selection_ex_rows(gui_module.Selection)
    matching_ids: list[str] = []
    fallback_ids: list[str] = []
    for selection in selections:
        selected_obj = getattr(selection, "Object", None)
        target = matching_ids if _selection_matches_source(selected_obj, source_obj) else fallback_ids
        for name in _selection_subelement_names(selection):
            triangle_id = _triangle_id_from_subelement_name(str(name or ""))
            if triangle_id:
                target.append(triangle_id)
    if matching_ids:
        return _unique_strings(matching_ids)
    return _unique_strings(fallback_ids)


def triangle_ids_from_view_event(gui_module, event, *, source_obj=None, surface=None) -> list[str]:
    """Return triangle ids from the 3D view object info at a mouse event position."""

    view = _active_view(gui_module)
    position = _event_position(event)
    if view is None or position is None:
        return []
    info = _object_info_at_position(view, position)
    ids = triangle_ids_from_object_info(info, source_obj=source_obj)
    if ids:
        return ids
    return triangle_ids_from_view_xy(gui_module, event, surface=surface)


def triangle_ids_from_view_xy(gui_module, event, *, surface=None) -> list[str]:
    """Return triangle ids by projecting the click to XY and sampling the TIN surface."""

    if surface is None:
        return []
    view = _active_view(gui_module)
    point = _world_point_from_view_event(view, event)
    if point is None:
        return []
    try:
        result = TinSamplingService().sample_xy(surface=surface, x=float(point.x), y=float(point.y))
    except Exception:
        return []
    face_id = str(getattr(result, "face_id", "") or "").strip()
    return [face_id] if bool(getattr(result, "found", False)) and face_id else []


def nearest_tin_vertex(surface, x: float, y: float) -> dict[str, object]:
    """Return the nearest TIN vertex to an XY pick point."""

    rows = list(getattr(surface, "vertex_rows", []) or []) if surface is not None else []
    if not rows:
        return {}
    x_value = float(x)
    y_value = float(y)
    best = None
    best_distance_sq = None
    for row in rows:
        try:
            dx = float(row.x) - x_value
            dy = float(row.y) - y_value
        except Exception:
            continue
        distance_sq = dx * dx + dy * dy
        if best is None or distance_sq < best_distance_sq:
            best = row
            best_distance_sq = distance_sq
    if best is None or best_distance_sq is None:
        return {}
    return {
        "vertex_id": str(getattr(best, "vertex_id", "") or ""),
        "x": float(getattr(best, "x", 0.0) or 0.0),
        "y": float(getattr(best, "y", 0.0) or 0.0),
        "z": float(getattr(best, "z", 0.0) or 0.0),
        "distance": best_distance_sq ** 0.5,
    }


def triangle_ids_from_object_info(info, *, source_obj=None) -> list[str]:
    """Return triangle ids from FreeCAD ActiveView.getObjectInfo output."""

    if not isinstance(info, dict):
        return []
    selected_obj = info.get("Object", None)
    if selected_obj is not None and not _selection_matches_source(selected_obj, source_obj):
        return []
    names = []
    for key in (
        "Component",
        "ComponentName",
        "SubName",
        "SubElement",
        "SubElementName",
        "Element",
        "Name",
    ):
        value = str(info.get(key, "") or "").strip()
        if value:
            names.append(value)
    for name in names:
        triangle_id = _triangle_id_from_subelement_name(name)
        if triangle_id:
            return [triangle_id]
    return []


def _active_view(gui_module):
    try:
        return gui_module.ActiveDocument.ActiveView
    except Exception:
        return None


def _is_left_mouse_down(event) -> bool:
    if not isinstance(event, dict):
        return True
    state = str(event.get("State", "") or "").upper()
    button = str(event.get("Button", "") or "").upper()
    if state and state not in {"DOWN", "PRESS", "PRESSED"}:
        return False
    if button and button not in {"BUTTON1", "BUTTON_1", "LEFT", "LEFTBUTTON"}:
        return False
    return True


def _event_position(event):
    if not isinstance(event, dict):
        return None
    position = event.get("Position", event.get("position", None))
    if position is None:
        return None
    try:
        if isinstance(position, (tuple, list)) and len(position) >= 2:
            return int(position[0]), int(position[1])
        if hasattr(position, "getValue"):
            values = position.getValue()
            return int(values[0]), int(values[1])
        if hasattr(position, "x") and hasattr(position, "y"):
            x_value = position.x() if callable(position.x) else position.x
            y_value = position.y() if callable(position.y) else position.y
            return int(x_value), int(y_value)
    except Exception:
        return None
    return None


def _object_info_at_position(view, position):
    if view is None or position is None or not hasattr(view, "getObjectInfo"):
        return {}
    x_value, y_value = position
    for arg in ((int(x_value), int(y_value)), [int(x_value), int(y_value)]):
        try:
            info = view.getObjectInfo(arg)
            if isinstance(info, dict):
                return info
        except Exception:
            pass
    try:
        info = view.getObjectInfo(int(x_value), int(y_value))
        if isinstance(info, dict):
            return info
    except Exception:
        pass
    return {}


def _world_point_from_view_event(view, event):
    position = _event_position(event)
    if view is None or position is None or not hasattr(view, "getPoint"):
        return None
    x_value, y_value = position
    for args in (((int(x_value), int(y_value)),), ([int(x_value), int(y_value)],), (int(x_value), int(y_value))):
        try:
            point = view.getPoint(*args)
            if point is not None and hasattr(point, "x") and hasattr(point, "y"):
                return point
        except Exception:
            pass
    return None


def _format_xy_point(point) -> str:
    if point is None or not hasattr(point, "x") or not hasattr(point, "y"):
        return ""
    try:
        return _format_xy_tuple((float(point.x), float(point.y)))
    except Exception:
        return ""


def _format_xy_tuple(value: tuple[float, float]) -> str:
    return f"({float(value[0]):.3f}, {float(value[1]):.3f})"


def _as_float(value) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _view_event_component_text(gui_module, event) -> str:
    view = _active_view(gui_module)
    position = _event_position(event)
    info = _object_info_at_position(view, position)
    if not isinstance(info, dict):
        return ""
    return str(info.get("Component", "") or info.get("SubName", "") or info.get("Name", "") or "")


def _selection_ex_rows(selection_api) -> list[object]:
    for args in (("", 0), ()):
        try:
            return list(selection_api.getSelectionEx(*args) or [])
        except TypeError:
            continue
        except Exception:
            return []
    return []


def _selection_matches_source(selected_obj, source_obj) -> bool:
    if source_obj is None or selected_obj is None:
        return True
    if selected_obj == source_obj:
        return True
    for attr in ("Name", "Label", "SurfaceId"):
        left = str(getattr(selected_obj, attr, "") or "").strip()
        right = str(getattr(source_obj, attr, "") or "").strip()
        if left and right and left == right:
            return True
    return False


def _selection_subelement_names(selection) -> list[str]:
    names: list[str] = []
    for attr in ("SubElementNames", "SubElements"):
        value = getattr(selection, attr, None)
        if isinstance(value, str):
            names.append(value)
            continue
        try:
            names.extend(str(item or "") for item in list(value or []))
        except Exception:
            pass
    for sub_object in list(getattr(selection, "SubObjects", []) or []):
        for attr in ("Name", "ElementName", "TypeId"):
            value = str(getattr(sub_object, attr, "") or "").strip()
            if value:
                names.append(value)
    return _unique_strings(names)


def _triangle_id_from_subelement_name(name: str) -> str:
    match = re.search(r"(Face|Facet)[_\s]*(\d+)", str(name or "").strip(), flags=re.IGNORECASE)
    if match is None:
        return ""
    prefix = match.group(1).lower()
    face_index = int(match.group(2))
    if face_index <= 0 and prefix != "facet":
        return ""
    if face_index == 0:
        return "t0"
    return f"t{face_index - 1}"


def _split_id_text(text: str) -> list[str]:
    return [token.strip() for token in str(text or "").replace(";", ",").split(",") if token.strip()]


def _unique_strings(values: list[object]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _surface_extent(surface) -> dict[str, float]:
    rows = list(getattr(surface, "vertex_rows", []) or []) if surface is not None else []
    if not rows:
        return {}
    x_values = [float(row.x) for row in rows]
    y_values = [float(row.y) for row in rows]
    return {
        "min_x": min(x_values),
        "max_x": max(x_values),
        "min_y": min(y_values),
        "max_y": max(y_values),
    }


def _route_preview_to_tree(document, mesh_preview) -> None:
    if document is None or mesh_preview is None:
        return
    object_name = str(getattr(mesh_preview, "object_name", "") or "").strip()
    if not object_name:
        return
    try:
        from freecad.Corridor_Road.objects.obj_project import find_project, route_to_v1_tree

        project = find_project(document)
        obj = document.getObject(object_name)
        if project is not None and obj is not None:
            route_to_v1_tree(project, obj)
    except Exception:
        pass


def _route_edit_records_to_tree(document, edit_result) -> dict[str, str]:
    if document is None or edit_result is None:
        return {}
    try:
        from freecad.Corridor_Road.objects.obj_project import find_project, route_to_v1_tree

        project = find_project(document)
        if project is None:
            return {}
        result_record = _ensure_edited_result_record(document, edit_result)
        diagnostics_record = _ensure_edit_diagnostics_record(document, edit_result)
        route_to_v1_tree(project, result_record)
        route_to_v1_tree(project, diagnostics_record)
        return {
            "edited_result": str(getattr(result_record, "Name", "") or ""),
            "edit_diagnostics": str(getattr(diagnostics_record, "Name", "") or ""),
        }
    except Exception:
        return {}


def _ensure_edited_result_record(document, edit_result):
    surface = edit_result.surface
    surface_id = str(getattr(surface, "surface_id", "") or "tin:edited")
    name = f"CRV1_TIN_Edited_Result_{_safe_name_token(surface_id)}"
    obj = _get_or_create_metadata_object(document, name, f"TIN Edited Result - {surface_id}")
    _set_string_property(obj, "CRRecordKind", "tin_surface_result")
    _set_string_property(obj, "SurfaceRole", "edited")
    _set_string_property(obj, "SurfaceId", surface_id)
    _set_string_property(obj, "SurfaceKind", str(getattr(surface, "surface_kind", "") or ""))
    _set_string_property(obj, "SourceSurfaceId", _source_surface_id(surface))
    _set_integer_property(obj, "VertexCount", len(list(getattr(surface, "vertex_rows", []) or [])))
    _set_integer_property(obj, "TriangleCount", len(list(getattr(surface, "triangle_rows", []) or [])))
    _set_integer_property(obj, "RemovedTriangleCount", int(getattr(edit_result, "removed_triangle_count", 0) or 0))
    _set_integer_property(obj, "ChangedVertexCount", int(getattr(edit_result, "changed_vertex_count", 0) or 0))
    _set_integer_property(obj, "OperationCount", len(list(getattr(edit_result, "operation_reports", []) or [])))
    _set_string_property(obj, "EditStatus", str(getattr(edit_result, "status", "") or ""))
    return obj


def _ensure_edit_diagnostics_record(document, edit_result):
    surface = edit_result.surface
    surface_id = str(getattr(surface, "surface_id", "") or "tin:edited")
    name = f"CRV1_TIN_Edit_Diagnostics_{_safe_name_token(surface_id)}"
    obj = _get_or_create_metadata_object(document, name, f"TIN Edit Diagnostics - {surface_id}")
    _set_string_property(obj, "CRRecordKind", "tin_diagnostics")
    _set_string_property(obj, "SurfaceRole", "edited")
    _set_string_property(obj, "SurfaceId", surface_id)
    _set_string_property(obj, "EditStatus", str(getattr(edit_result, "status", "") or ""))
    _set_integer_property(obj, "RemovedTriangleCount", int(getattr(edit_result, "removed_triangle_count", 0) or 0))
    _set_integer_property(obj, "ChangedVertexCount", int(getattr(edit_result, "changed_vertex_count", 0) or 0))
    _set_string_property(obj, "OperationSummary", _operation_summary(edit_result))
    return obj


def _get_or_create_metadata_object(document, name: str, label: str):
    obj = document.getObject(name)
    if obj is None:
        obj = document.addObject("App::FeaturePython", name)
    try:
        obj.Label = label
    except Exception:
        pass
    return obj


def _set_string_property(obj, name: str, value: str) -> None:
    if obj is None:
        return
    if not hasattr(obj, name):
        obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
    setattr(obj, name, str(value or ""))


def _set_integer_property(obj, name: str, value: int) -> None:
    if obj is None:
        return
    if not hasattr(obj, name):
        obj.addProperty("App::PropertyInteger", name, "CorridorRoad", name)
    setattr(obj, name, int(value or 0))


def _safe_name_token(value: str) -> str:
    raw = str(value or "tin").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw)
    return (safe.strip("_") or "tin")[:80]


def _source_surface_id(surface) -> str:
    for source_ref in list(getattr(surface, "source_refs", []) or []):
        text = str(source_ref or "").strip()
        if text.startswith("tin:") and not text.endswith(":edited"):
            return text
    surface_id = str(getattr(surface, "surface_id", "") or "")
    return surface_id.removesuffix(":edited")


def _operation_summary(edit_result) -> str:
    rows = []
    for report in list(getattr(edit_result, "operation_reports", []) or []):
        rows.append(
            f"{report.operation_id}:{report.operation_kind}:"
            f"status={report.status}:removed={report.removed_triangle_count}:changed={report.changed_vertex_count}"
        )
    return " | ".join(rows)


def _focus_preview(document, mesh_preview, *, gui_module=Gui) -> bool:
    preview = {"mesh_preview": mesh_preview}
    return bool(_focus_tin_preview_object(document, preview, gui_module=gui_module))


def _focus_preview_deferred(document, mesh_preview, *, gui_module=Gui) -> None:
    """Run one more fit pass after modal messages and GUI paint events settle."""

    if gui_module is None:
        return
    try:
        QtCore.QTimer.singleShot(150, lambda: _focus_preview(document, mesh_preview, gui_module=gui_module))
    except Exception:
        pass


def _format_editor_result(result: dict[str, object]) -> str:
    edit_result = result["edit_result"]
    lines = [
        "TIN edit result",
        f"Status: {edit_result.status}",
        f"Edited surface: {edit_result.surface.surface_id}",
        f"Vertices: {len(list(edit_result.surface.vertex_rows or []))}",
        f"Triangles: {len(list(edit_result.surface.triangle_rows or []))}",
        f"Removed triangles: {edit_result.removed_triangle_count}",
        f"Changed vertices: {edit_result.changed_vertex_count}",
        "",
        "Operations:",
    ]
    for report in list(edit_result.operation_reports or []):
        lines.append(
            f"- {report.operation_id}: {report.operation_kind}, status={report.status}, "
            f"removed={report.removed_triangle_count}, changed={report.changed_vertex_count}"
        )
    return "\n".join(lines)


def _process_panel_events() -> None:
    try:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.processEvents()
    except Exception:
        pass
    try:
        if Gui is not None and hasattr(Gui, "updateGui"):
            Gui.updateGui()
    except Exception:
        pass


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


configure_tineditor_task_panel_runtime(globals())


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditTIN", CmdV1TINEditor())

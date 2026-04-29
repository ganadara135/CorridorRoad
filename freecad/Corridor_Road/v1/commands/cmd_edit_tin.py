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

from ..models.source import TINEditOperation
from ..services.editing import TINEditService
from ..services.evaluation import TinSamplingService
from ..services.mapping import TINMeshPreviewMapper
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


class V1TINEditorTaskPanel:
    """First v1 TIN editor panel using replayable edit operations."""

    def __init__(self, *, document=None, source_obj=None, base_surface=None, gui_module=Gui):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.gui_module = gui_module
        self.source_obj = source_obj
        self.base_surface = base_surface
        self._source_csv_path = ""
        self._triangle_pick_observer = None
        self._triangle_pick_active = False
        self._triangle_pick_timer = None
        self._triangle_pick_view = None
        self._triangle_pick_event_callback_id = None
        self._vertex_pick_active = False
        self._vertex_pick_view = None
        self._vertex_pick_event_callback_id = None
        self._boundary_pick_active = False
        self._boundary_pick_points: list[tuple[float, float]] = []
        self._boundary_pick_view = None
        self._boundary_pick_event_callback_id = None
        self._boundary_pick_location_callback_id = None
        self._void_rect_active = False
        self._void_suppress_activation = False
        self._void_pick_active = False
        self._void_pick_points: list[tuple[float, float]] = []
        self._void_pick_view = None
        self._void_pick_event_callback_id = None
        self._void_pick_location_callback_id = None
        self.form = self._build_ui()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._build_tin(close_after=True)

    def reject(self):
        self._stop_triangle_pick_mode(silent=True)
        self._stop_vertex_pick_mode(silent=True)
        self._stop_boundary_pick_mode(silent=True)
        self._stop_void_pick_mode(silent=True)
        if self.gui_module is not None:
            self.gui_module.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - TIN")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("TIN")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        self._summary = QtWidgets.QLabel(self._summary_text())
        self._summary.setWordWrap(True)
        self._summary.setStyleSheet("color: #dfe8ff; background: #263142; padding: 6px;")
        layout.addWidget(self._summary)

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.addTab(self._build_source_tab(), "Source")
        self._tabs.addTab(self._build_boundary_tab(), "Boundary")
        self._tabs.addTab(self._build_void_tab(), "Voids")
        self._tabs.addTab(self._build_triangles_tab(), "Triangles")
        self._tabs.addTab(self._build_vertices_tab(), "Vertices")
        self._tabs.addTab(self._build_diagnostics_tab(), "Diagnostics")
        layout.addWidget(self._tabs, 1)

        button_row = QtWidgets.QHBoxLayout()
        build_button = QtWidgets.QPushButton("Apply")
        build_button.clicked.connect(lambda: self._build_tin(close_after=False))
        button_row.addWidget(build_button)
        show_button = QtWidgets.QPushButton("Show Preview")
        show_button.clicked.connect(self._show_preview)
        button_row.addWidget(show_button)
        review_button = QtWidgets.QPushButton("Review Result")
        review_button.clicked.connect(self._review_tin)
        button_row.addWidget(review_button)
        button_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)
        return widget

    def _build_source_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)
        note = QtWidgets.QLabel(
            "Build or replace the editable base TIN from a point-cloud CSV, then continue with Boundary, Voids, and edits."
        )
        note.setWordWrap(True)
        layout.addRow(note)

        path_row = QtWidgets.QHBoxLayout()
        self._source_csv_text = QtWidgets.QLineEdit()
        self._source_csv_text.setPlaceholderText("Path to point-cloud CSV file")
        path_row.addWidget(self._source_csv_text, 1)
        browse_button = QtWidgets.QPushButton("Browse CSV")
        browse_button.clicked.connect(self._browse_source_csv)
        path_row.addWidget(browse_button)
        path_widget = QtWidgets.QWidget()
        path_widget.setLayout(path_row)
        layout.addRow("CSV:", path_widget)

        sample_row = QtWidgets.QHBoxLayout()
        self._sample_csv_combo = QtWidgets.QComboBox()
        self._populate_sample_csv_combo()
        sample_row.addWidget(self._sample_csv_combo, 1)
        use_sample_button = QtWidgets.QPushButton("Use Sample")
        use_sample_button.clicked.connect(self._use_selected_sample_csv)
        sample_row.addWidget(use_sample_button)
        sample_widget = QtWidgets.QWidget()
        sample_widget.setLayout(sample_row)
        layout.addRow("Sample:", sample_widget)

        return tab

    def _build_boundary_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)
        note = QtWidgets.QLabel(
            "Clip the outer TIN boundary. Use the full extent, type values, or pick two opposite rectangle corners in 3D."
        )
        note.setWordWrap(True)
        layout.addRow(note)
        self._boundary_min_x = _spin_box()
        self._boundary_max_x = _spin_box()
        self._boundary_min_y = _spin_box()
        self._boundary_max_y = _spin_box()
        self._fill_surface_extents(
            self._boundary_min_x,
            self._boundary_max_x,
            self._boundary_min_y,
            self._boundary_max_y,
        )
        layout.addRow("Min X:", self._boundary_min_x)
        layout.addRow("Max X:", self._boundary_max_x)
        layout.addRow("Min Y:", self._boundary_min_y)
        layout.addRow("Max Y:", self._boundary_max_y)
        action_row = QtWidgets.QHBoxLayout()
        use_extent_button = QtWidgets.QPushButton("Use Full Extent")
        use_extent_button.clicked.connect(self._use_boundary_full_extent)
        action_row.addWidget(use_extent_button)
        self._boundary_pick_button = QtWidgets.QPushButton("Pick Rectangle")
        self._boundary_pick_button.clicked.connect(self._toggle_boundary_pick_mode)
        action_row.addWidget(self._boundary_pick_button)
        reset_button = QtWidgets.QPushButton("Reset Boundary")
        reset_button.clicked.connect(self._reset_boundary_rect)
        action_row.addWidget(reset_button)
        action_row.addStretch(1)
        action_widget = QtWidgets.QWidget()
        action_widget.setLayout(action_row)
        layout.addRow(action_widget)
        return tab

    def _build_void_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)
        note = QtWidgets.QLabel(
            "Cut an internal hole from the TIN. Pick two opposite rectangle corners, type values, or clear to disable."
        )
        note.setWordWrap(True)
        layout.addRow(note)
        self._void_min_x = _spin_box()
        self._void_max_x = _spin_box()
        self._void_min_y = _spin_box()
        self._void_max_y = _spin_box()
        for spin in (self._void_min_x, self._void_max_x, self._void_min_y, self._void_max_y):
            spin.valueChanged.connect(self._mark_void_rect_active)
        layout.addRow("Min X:", self._void_min_x)
        layout.addRow("Max X:", self._void_max_x)
        layout.addRow("Min Y:", self._void_min_y)
        layout.addRow("Max Y:", self._void_max_y)
        action_row = QtWidgets.QHBoxLayout()
        self._void_pick_button = QtWidgets.QPushButton("Pick Rectangle")
        self._void_pick_button.clicked.connect(self._toggle_void_pick_mode)
        action_row.addWidget(self._void_pick_button)
        clear_button = QtWidgets.QPushButton("Reset Void")
        clear_button.clicked.connect(self._reset_void_rect)
        action_row.addWidget(clear_button)
        action_row.addStretch(1)
        action_widget = QtWidgets.QWidget()
        action_widget.setLayout(action_row)
        layout.addRow(action_widget)
        return tab

    def _build_triangles_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        note = QtWidgets.QLabel(
            "Delete triangle ids, comma lists, ranges, or selected 3D mesh faces. "
            "Examples: t1,t2,t8 or t10-t15."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self._triangle_delete_text = QtWidgets.QLineEdit()
        self._triangle_delete_text.setPlaceholderText("Triangle ids to delete")
        layout.addWidget(self._triangle_delete_text)

        button_row = QtWidgets.QHBoxLayout()
        self._triangle_pick_button = QtWidgets.QPushButton("Start Pick Mode")
        self._triangle_pick_button.clicked.connect(self._toggle_triangle_pick_mode)
        button_row.addWidget(self._triangle_pick_button)
        clear_button = QtWidgets.QPushButton("Clear")
        clear_button.clicked.connect(lambda: self._triangle_delete_text.setText(""))
        button_row.addWidget(clear_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        layout.addStretch(1)
        return tab

    def _build_vertices_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        note = QtWidgets.QLabel("Override vertex elevations without changing the source TIN. Leave empty rows blank.")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._vertex_table = QtWidgets.QTableWidget(0, 3)
        self._vertex_table.setHorizontalHeaderLabels(["Vertex ID", "New Z", "Notes"])
        self._vertex_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._vertex_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._vertex_table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        layout.addWidget(self._vertex_table, 1)

        button_row = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Vertex Override")
        add_button.clicked.connect(self._add_vertex_override_row)
        button_row.addWidget(add_button)
        self._vertex_pick_button = QtWidgets.QPushButton("Start Vertex Pick Mode")
        self._vertex_pick_button.clicked.connect(self._toggle_vertex_pick_mode)
        button_row.addWidget(self._vertex_pick_button)
        delete_button = QtWidgets.QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_selected_vertex_override_rows)
        button_row.addWidget(delete_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self._add_vertex_override_row()
        layout.addStretch(1)
        return tab

    def _build_diagnostics_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self._diagnostics = QtWidgets.QPlainTextEdit()
        self._diagnostics.setReadOnly(True)
        self._diagnostics.setPlainText(self._summary_text())
        layout.addWidget(self._diagnostics)
        return tab

    def _build_tin(self, *, close_after: bool = False) -> bool:
        try:
            source_result = None
            csv_path = str(self._source_csv_text.text() or "").strip()
            if csv_path and (self.base_surface is None or csv_path != self._source_csv_path):
                source_result = self._build_source_tin(show_completion=False, focus_preview=False)
            result = self._apply_current_editor_state(focus_preview=True)
            edit_result = result["edit_result"]
            mesh_preview = result.get("mesh_preview")
            source_text = ""
            if source_result is not None:
                source_surface = source_result.get("tin_surface")
                source_text = (
                    f"Base surface: {getattr(source_surface, 'surface_id', '')}\n"
                    f"Base vertices: {len(list(getattr(source_surface, 'vertex_rows', []) or []))}\n"
                    f"Base triangles: {len(list(getattr(source_surface, 'triangle_rows', []) or []))}\n"
                )
            _show_message(
                self.form,
                "TIN",
                (
                    "TIN settings have been applied.\n"
                    f"{source_text}"
                    f"Preview: {getattr(mesh_preview, 'object_name', '')}\n"
                    f"Result triangles: {len(list(result['edited_surface'].triangle_rows or []))}\n"
                    f"Removed triangles: {edit_result.removed_triangle_count}\n"
                    f"Changed vertices: {edit_result.changed_vertex_count}"
                ),
            )
            if close_after and self.gui_module is not None:
                self.gui_module.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_diagnostics(f"TIN build failed:\n{exc}")
            _show_message(self.form, "TIN", f"TIN was not built.\n{exc}")
            return False

    def _apply(self, *, close_after: bool = False, show_completion: bool = True) -> bool:
        try:
            result = self._apply_current_editor_state(focus_preview=True)
            if show_completion:
                _show_message(
                    self.form,
                    "TIN",
                    (
                        "TIN edits have been applied.\n"
                        f"Preview: {getattr(result.get('mesh_preview'), 'object_name', '')}\n"
                        f"Removed triangles: {result['edit_result'].removed_triangle_count}\n"
                        f"Changed vertices: {result['edit_result'].changed_vertex_count}"
                    ),
                )
            if close_after and self.gui_module is not None:
                self.gui_module.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_diagnostics(f"TIN edit failed:\n{exc}")
            _show_message(self.form, "TIN", f"TIN edits were not applied.\n{exc}")
            return False

    def _show_preview(self) -> None:
        try:
            self._apply_current_editor_state(focus_preview=True)
        except Exception as exc:
            self._set_diagnostics(f"TIN preview failed:\n{exc}")
            _show_message(self.form, "TIN", f"TIN preview could not be shown.\n{exc}")

    def _review_tin(self) -> None:
        try:
            from .cmd_review_tin import show_v1_tin_review

            result = self._apply_current_editor_state(focus_preview=False)
            _remove_rect_previews(self.document)
            show_v1_tin_review(
                document=self.document,
                extra_context={
                    "tin_surface": result["edited_surface"],
                    "create_mesh_preview": False,
                },
                app_module=App,
                gui_module=self.gui_module,
            )
        except Exception as exc:
            _show_message(self.form, "TIN", f"TIN Review could not be opened.\n{exc}")

    def _browse_source_csv(self) -> None:
        path = _select_tin_csv_path(self.gui_module)
        if path:
            self._source_csv_text.setText(path)

    def _populate_sample_csv_combo(self) -> None:
        if not hasattr(self, "_sample_csv_combo"):
            return
        self._sample_csv_combo.clear()
        samples_dir = _default_sample_dir()
        rows = []
        if samples_dir.exists():
            rows = sorted(samples_dir.glob("pointcloud*.csv"))
        self._sample_csv_combo.addItem("(select sample)", "")
        for path in rows:
            self._sample_csv_combo.addItem(path.name, str(path))

    def _use_selected_sample_csv(self) -> None:
        if not hasattr(self, "_sample_csv_combo"):
            return
        path = str(self._sample_csv_combo.currentData() or "")
        if path:
            self._source_csv_text.setText(path)

    def _build_source_tin(self, *, show_completion: bool = True, focus_preview: bool = True) -> dict[str, object]:
        try:
            csv_path = str(self._source_csv_text.text() or "").strip()
            if not csv_path:
                raise ValueError("Select a point-cloud CSV file first.")
            result = build_tin_source_from_csv(
                document=self.document,
                csv_path=csv_path,
                app_module=App,
            )
            self.base_surface = result["tin_surface"]
            self._source_csv_path = csv_path
            self.source_obj = result.get("source_obj", None)
            self._last_result = None
            self._summary.setText(self._summary_text())
            self._reset_boundary_rect()
            self._reset_void_rect()
            mesh_preview = result.get("mesh_preview")
            if focus_preview:
                _focus_preview(self.document, mesh_preview, gui_module=self.gui_module)
            if show_completion:
                _show_message(
                    self.form,
                    "TIN",
                    (
                        "TIN source has been built.\n"
                        f"Surface: {self.base_surface.surface_id}\n"
                        f"Vertices: {len(list(self.base_surface.vertex_rows or []))}\n"
                        f"Triangles: {len(list(self.base_surface.triangle_rows or []))}"
                    ),
                )
            if focus_preview:
                _focus_preview(self.document, mesh_preview, gui_module=self.gui_module)
                _focus_preview_deferred(self.document, mesh_preview, gui_module=self.gui_module)
            return result
        except Exception as exc:
            self._set_diagnostics(f"TIN source build failed:\n{exc}")
            if show_completion:
                _show_message(self.form, "TIN", f"TIN source could not be built.\n{exc}")
            raise

    def _apply_current_editor_state(self, *, focus_preview: bool) -> dict[str, object]:
        if self.base_surface is None:
            raise ValueError("No selected TIN-capable Mesh/Shape object was found.")
        operations = self._operations_from_ui()
        result = apply_tin_editor_operations(
            document=self.document,
            base_surface=self.base_surface,
            operations=operations,
        )
        self._stop_triangle_pick_mode(silent=True)
        self._stop_vertex_pick_mode(silent=True)
        self._stop_boundary_pick_mode(silent=True)
        self._stop_void_pick_mode(silent=True)
        self._last_result = result
        self._set_diagnostics(_format_editor_result(result))
        if focus_preview:
            _focus_preview(self.document, result.get("mesh_preview"), gui_module=self.gui_module)
        return result

    def _use_boundary_full_extent(self) -> None:
        self._reset_boundary_rect()

    def _reset_boundary_rect(self) -> None:
        self._fill_surface_extents(
            self._boundary_min_x,
            self._boundary_max_x,
            self._boundary_min_y,
            self._boundary_max_y,
        )
        self._stop_boundary_pick_mode(silent=True)
        _remove_rect_previews(self.document, role="boundary")
        self._set_diagnostics("Boundary reset to the full TIN extent.")

    def _toggle_boundary_pick_mode(self) -> None:
        if self._boundary_pick_active:
            self._stop_boundary_pick_mode()
            return
        self._start_boundary_pick_mode()

    def _start_boundary_pick_mode(self) -> None:
        self._stop_triangle_pick_mode(silent=True)
        self._stop_vertex_pick_mode(silent=True)
        self._stop_void_pick_mode(silent=True)
        view = _active_view(self.gui_module)
        if view is None or not hasattr(view, "addEventCallback"):
            _show_message(self.form, "TIN", "Boundary picking is not available in this FreeCAD session.")
            return
        try:
            self._boundary_pick_view = view
            self._boundary_pick_event_callback_id = view.addEventCallback(
                "SoMouseButtonEvent",
                self._handle_boundary_mouse_event,
            )
            try:
                self._boundary_pick_location_callback_id = view.addEventCallback(
                    "SoLocation2Event",
                    self._handle_boundary_location_event,
                )
            except Exception:
                self._boundary_pick_location_callback_id = None
            self._boundary_pick_active = True
            self._boundary_pick_points = []
            _remove_rect_previews(self.document, role="boundary")
            self._set_boundary_pick_ui(True)
            self._set_diagnostics("Boundary pick is active. Click two opposite rectangle corners.")
        except Exception as exc:
            self._boundary_pick_view = None
            self._boundary_pick_event_callback_id = None
            self._boundary_pick_active = False
            self._set_boundary_pick_ui(False)
            _show_message(self.form, "TIN", f"Boundary pick could not be started.\n{exc}")

    def _stop_boundary_pick_mode(self, *, silent: bool = False) -> None:
        view = self._boundary_pick_view
        callback_id = self._boundary_pick_event_callback_id
        location_callback_id = self._boundary_pick_location_callback_id
        self._boundary_pick_view = None
        self._boundary_pick_event_callback_id = None
        self._boundary_pick_location_callback_id = None
        was_active = self._boundary_pick_active
        self._boundary_pick_active = False
        self._set_boundary_pick_ui(False)
        if view is not None and callback_id is not None and hasattr(view, "removeEventCallback"):
            try:
                view.removeEventCallback("SoMouseButtonEvent", callback_id)
            except Exception:
                pass
        if view is not None and location_callback_id is not None and hasattr(view, "removeEventCallback"):
            try:
                view.removeEventCallback("SoLocation2Event", location_callback_id)
            except Exception:
                pass
        if was_active and len(self._boundary_pick_points) < 2:
            _remove_rect_previews(self.document, role="boundary")
        if was_active and not silent:
            self._set_diagnostics("Boundary pick stopped.")

    def _set_boundary_pick_ui(self, active: bool) -> None:
        if hasattr(self, "_boundary_pick_button"):
            self._boundary_pick_button.setText("Stop Picking" if active else "Pick Rectangle")

    def _handle_boundary_mouse_event(self, event) -> None:
        if not self._boundary_pick_active or not _is_left_mouse_down(event):
            return
        point = _world_point_from_view_event(_active_view(self.gui_module), event)
        if point is None:
            self._set_diagnostics("Boundary pick did not resolve an XY point. Try clicking directly on the TIN surface.")
            return
        xy = (float(point.x), float(point.y))
        self._boundary_pick_points.append(xy)
        if len(self._boundary_pick_points) == 1:
            self._set_diagnostics(f"Boundary first corner: {_format_xy_tuple(xy)}. Click the opposite corner.")
            return
        rect = _rect_from_xy_points(self._boundary_pick_points[0], self._boundary_pick_points[-1])
        self._set_boundary_rect(rect)
        _update_rect_preview(
            self.document,
            _boundary_rect_preview_name(),
            rect,
            surface=self.base_surface,
            role="boundary",
            final=True,
        )
        self._stop_boundary_pick_mode(silent=True)
        self._set_diagnostics("Boundary values updated from two 3D View corners.")

    def _handle_boundary_location_event(self, event) -> None:
        if not self._boundary_pick_active or len(self._boundary_pick_points) != 1:
            return
        point = _world_point_from_view_event(_active_view(self.gui_module), event)
        if point is None:
            return
        rect = _rect_from_xy_points(self._boundary_pick_points[0], (float(point.x), float(point.y)))
        _update_rect_preview(
            self.document,
            _boundary_rect_preview_name(),
            rect,
            surface=self.base_surface,
            role="boundary",
            final=False,
        )

    def _set_boundary_rect(self, rect: dict[str, float]) -> None:
        self._boundary_min_x.setValue(float(rect["min_x"]))
        self._boundary_max_x.setValue(float(rect["max_x"]))
        self._boundary_min_y.setValue(float(rect["min_y"]))
        self._boundary_max_y.setValue(float(rect["max_y"]))

    def _append_selected_triangle_faces(self) -> None:
        ids = triangle_ids_from_selected_faces(self.gui_module, source_obj=self.source_obj)
        if not ids:
            _show_message(
                self.form,
                "TIN",
                "No selected mesh faces were found. Select one or more TIN mesh faces in the 3D View first.",
            )
            return
        self._append_triangle_ids(ids)

    def _mark_void_rect_active(self, *args) -> None:
        if self._void_suppress_activation:
            return
        self._void_rect_active = True

    def _reset_void_rect(self) -> None:
        self._void_suppress_activation = True
        try:
            self._void_min_x.setValue(0.0)
            self._void_max_x.setValue(0.0)
            self._void_min_y.setValue(0.0)
            self._void_max_y.setValue(0.0)
        finally:
            self._void_suppress_activation = False
        self._void_rect_active = False
        self._stop_void_pick_mode(silent=True)
        _remove_rect_previews(self.document, role="void")
        self._set_diagnostics("Void reset to the default disabled state.")

    def _toggle_void_pick_mode(self) -> None:
        if self._void_pick_active:
            self._stop_void_pick_mode()
            return
        self._start_void_pick_mode()

    def _start_void_pick_mode(self) -> None:
        self._stop_triangle_pick_mode(silent=True)
        self._stop_vertex_pick_mode(silent=True)
        self._stop_boundary_pick_mode(silent=True)
        view = _active_view(self.gui_module)
        if view is None or not hasattr(view, "addEventCallback"):
            _show_message(self.form, "TIN", "Void picking is not available in this FreeCAD session.")
            return
        try:
            self._void_pick_view = view
            self._void_pick_event_callback_id = view.addEventCallback(
                "SoMouseButtonEvent",
                self._handle_void_mouse_event,
            )
            try:
                self._void_pick_location_callback_id = view.addEventCallback(
                    "SoLocation2Event",
                    self._handle_void_location_event,
                )
            except Exception:
                self._void_pick_location_callback_id = None
            self._void_pick_active = True
            self._void_pick_points = []
            _remove_rect_previews(self.document, role="void")
            self._set_void_pick_ui(True)
            self._set_diagnostics("Void pick is active. Click two opposite rectangle corners.")
        except Exception as exc:
            self._void_pick_view = None
            self._void_pick_event_callback_id = None
            self._void_pick_active = False
            self._set_void_pick_ui(False)
            _show_message(self.form, "TIN", f"Void pick could not be started.\n{exc}")

    def _stop_void_pick_mode(self, *, silent: bool = False) -> None:
        view = self._void_pick_view
        callback_id = self._void_pick_event_callback_id
        location_callback_id = self._void_pick_location_callback_id
        self._void_pick_view = None
        self._void_pick_event_callback_id = None
        self._void_pick_location_callback_id = None
        was_active = self._void_pick_active
        self._void_pick_active = False
        self._set_void_pick_ui(False)
        if view is not None and callback_id is not None and hasattr(view, "removeEventCallback"):
            try:
                view.removeEventCallback("SoMouseButtonEvent", callback_id)
            except Exception:
                pass
        if view is not None and location_callback_id is not None and hasattr(view, "removeEventCallback"):
            try:
                view.removeEventCallback("SoLocation2Event", location_callback_id)
            except Exception:
                pass
        if was_active and len(self._void_pick_points) < 2:
            _remove_rect_previews(self.document, role="void")
        if was_active and not silent:
            self._set_diagnostics("Void pick stopped.")

    def _set_void_pick_ui(self, active: bool) -> None:
        if hasattr(self, "_void_pick_button"):
            self._void_pick_button.setText("Stop Picking" if active else "Pick Rectangle")

    def _handle_void_mouse_event(self, event) -> None:
        if not self._void_pick_active or not _is_left_mouse_down(event):
            return
        point = _world_point_from_view_event(_active_view(self.gui_module), event)
        if point is None:
            self._set_diagnostics("Void pick did not resolve an XY point. Try clicking directly on the TIN surface.")
            return
        xy = (float(point.x), float(point.y))
        self._void_pick_points.append(xy)
        if len(self._void_pick_points) == 1:
            self._set_diagnostics(f"Void first corner: {_format_xy_tuple(xy)}. Click the opposite corner.")
            return
        rect = _rect_from_xy_points(self._void_pick_points[0], self._void_pick_points[-1])
        self._set_void_rect(rect)
        _update_rect_preview(
            self.document,
            _void_rect_preview_name(),
            rect,
            surface=self.base_surface,
            role="void",
            final=True,
        )
        self._stop_void_pick_mode(silent=True)
        self._set_diagnostics("Void values updated from two 3D View corners.")

    def _handle_void_location_event(self, event) -> None:
        if not self._void_pick_active or len(self._void_pick_points) != 1:
            return
        point = _world_point_from_view_event(_active_view(self.gui_module), event)
        if point is None:
            return
        rect = _rect_from_xy_points(self._void_pick_points[0], (float(point.x), float(point.y)))
        _update_rect_preview(
            self.document,
            _void_rect_preview_name(),
            rect,
            surface=self.base_surface,
            role="void",
            final=False,
        )

    def _set_void_rect(self, rect: dict[str, float]) -> None:
        self._void_suppress_activation = True
        try:
            self._void_min_x.setValue(float(rect["min_x"]))
            self._void_max_x.setValue(float(rect["max_x"]))
            self._void_min_y.setValue(float(rect["min_y"]))
            self._void_max_y.setValue(float(rect["max_y"]))
        finally:
            self._void_suppress_activation = False
        self._void_rect_active = True

    def _toggle_triangle_pick_mode(self) -> None:
        if self._triangle_pick_active:
            self._stop_triangle_pick_mode()
            return
        self._start_triangle_pick_mode()

    def _start_triangle_pick_mode(self) -> None:
        self._stop_boundary_pick_mode(silent=True)
        self._stop_void_pick_mode(silent=True)
        self._stop_vertex_pick_mode(silent=True)
        selection = getattr(self.gui_module, "Selection", None) if self.gui_module is not None else None
        if self._triangle_pick_observer is None:
            self._triangle_pick_observer = _TINFacePickObserver(self)
        try:
            if selection is not None and hasattr(selection, "addObserver"):
                selection.addObserver(self._triangle_pick_observer)
            view_callback_started = self._start_triangle_pick_view_callback()
            if not view_callback_started and (selection is None or not hasattr(selection, "addObserver")):
                _show_message(self.form, "TIN", "Pick Mode is not available in this FreeCAD session.")
                return
            self._triangle_pick_active = True
            self._set_triangle_pick_ui(True)
            self._start_triangle_pick_polling()
            self._set_diagnostics(
                "Pick Mode is active. Click TIN mesh faces in the 3D View; picked faces will be added below. "
                "If the whole TIN object is selected, click directly on the target triangle."
            )
            self._poll_triangle_pick_selection()
        except Exception as exc:
            self._triangle_pick_observer = None
            self._triangle_pick_active = False
            self._stop_triangle_pick_view_callback()
            self._stop_triangle_pick_polling()
            self._set_triangle_pick_ui(False)
            _show_message(self.form, "TIN", f"Pick Mode could not be started.\n{exc}")

    def _stop_triangle_pick_mode(self, *, silent: bool = False) -> None:
        selection = getattr(self.gui_module, "Selection", None) if self.gui_module is not None else None
        if self._triangle_pick_observer is not None and selection is not None:
            try:
                selection.removeObserver(self._triangle_pick_observer)
            except Exception:
                pass
        self._triangle_pick_observer = None
        was_active = self._triangle_pick_active
        self._triangle_pick_active = False
        self._stop_triangle_pick_view_callback()
        self._stop_triangle_pick_polling()
        self._set_triangle_pick_ui(False)
        if was_active and not silent:
            self._set_diagnostics("Pick Mode stopped.")

    def _set_triangle_pick_ui(self, active: bool) -> None:
        if hasattr(self, "_triangle_pick_button"):
            self._triangle_pick_button.setText("Stop Pick Mode" if active else "Start Pick Mode")

    def _start_triangle_pick_polling(self) -> None:
        if self._triangle_pick_timer is None:
            self._triangle_pick_timer = QtCore.QTimer(self.form)
            self._triangle_pick_timer.setInterval(250)
            self._triangle_pick_timer.timeout.connect(self._poll_triangle_pick_selection)
        self._triangle_pick_timer.start()

    def _stop_triangle_pick_polling(self) -> None:
        if self._triangle_pick_timer is None:
            return
        try:
            self._triangle_pick_timer.stop()
        except Exception:
            pass

    def _start_triangle_pick_view_callback(self) -> bool:
        view = _active_view(self.gui_module)
        if view is None or not hasattr(view, "addEventCallback"):
            return False
        if self._triangle_pick_event_callback_id is not None:
            return True
        try:
            self._triangle_pick_view = view
            self._triangle_pick_event_callback_id = view.addEventCallback(
                "SoMouseButtonEvent",
                self._handle_triangle_mouse_event,
            )
            return True
        except Exception:
            self._triangle_pick_view = None
            self._triangle_pick_event_callback_id = None
            return False

    def _stop_triangle_pick_view_callback(self) -> None:
        view = self._triangle_pick_view
        callback_id = self._triangle_pick_event_callback_id
        self._triangle_pick_view = None
        self._triangle_pick_event_callback_id = None
        if view is None or callback_id is None or not hasattr(view, "removeEventCallback"):
            return
        try:
            view.removeEventCallback("SoMouseButtonEvent", callback_id)
        except Exception:
            pass

    def _poll_triangle_pick_selection(self) -> None:
        if not self._triangle_pick_active:
            return
        ids = triangle_ids_from_selected_faces(self.gui_module, source_obj=self.source_obj)
        if ids:
            self._append_triangle_ids(ids)

    def _handle_triangle_mouse_event(self, event) -> None:
        if not self._triangle_pick_active or not _is_left_mouse_down(event):
            return
        ids = triangle_ids_from_view_event(self.gui_module, event, source_obj=self.source_obj, surface=self.base_surface)
        if ids:
            self._append_triangle_ids(ids)
            return
        component = _view_event_component_text(self.gui_module, event)
        point = _world_point_from_view_event(_active_view(self.gui_module), event)
        point_text = _format_xy_point(point)
        self._set_diagnostics(
            "Pick Mode click did not resolve a mesh face"
            + (f" (component: {component})." if component else ".")
            + (f" XY={point_text}" if point_text else "")
        )

    def _handle_triangle_pick_event(self, *args) -> None:
        if not self._triangle_pick_active:
            return
        doc_name = str(args[0] if len(args) > 0 else "")
        obj_name = str(args[1] if len(args) > 1 else "")
        sub_name = str(args[2] if len(args) > 2 else "")
        triangle_id = _triangle_id_from_subelement_name(sub_name)
        if triangle_id:
            self._append_triangle_ids([triangle_id])
            return
        ids = triangle_ids_from_selected_faces(self.gui_module, source_obj=None)
        if ids:
            self._append_triangle_ids(ids)
            return
        label = f"{obj_name}.{sub_name}" if obj_name or sub_name else "(no face)"
        self._set_diagnostics(f"Pick Mode ignored selection {label}. Select a mesh Face/Facet.")

    def _append_triangle_ids(self, ids: list[str]) -> None:
        existing = _split_id_text(str(self._triangle_delete_text.text() or ""))
        merged = _unique_strings(existing + list(ids or []))
        if merged == existing:
            return
        self._triangle_delete_text.setText(",".join(merged))
        added = [triangle_id for triangle_id in _unique_strings(list(ids or [])) if triangle_id not in existing]
        self._set_diagnostics(f"Triangle ids added: {', '.join(added)}")

    def _toggle_vertex_pick_mode(self) -> None:
        if self._vertex_pick_active:
            self._stop_vertex_pick_mode()
            return
        self._start_vertex_pick_mode()

    def _start_vertex_pick_mode(self) -> None:
        self._stop_triangle_pick_mode(silent=True)
        self._stop_boundary_pick_mode(silent=True)
        self._stop_void_pick_mode(silent=True)
        view = _active_view(self.gui_module)
        if view is None or not hasattr(view, "addEventCallback"):
            _show_message(self.form, "TIN", "Vertex Pick Mode is not available in this FreeCAD session.")
            return
        if self.base_surface is None:
            _show_message(self.form, "TIN", "Build or select a TIN surface before picking vertices.")
            return
        try:
            self._vertex_pick_view = view
            self._vertex_pick_event_callback_id = view.addEventCallback(
                "SoMouseButtonEvent",
                self._handle_vertex_mouse_event,
            )
            self._vertex_pick_active = True
            self._set_vertex_pick_ui(True)
            self._set_diagnostics(
                "Vertex Pick Mode is active. Click near a bad terrain point; the nearest TIN vertex id "
                "and current Z will be added to the Vertices table."
            )
        except Exception as exc:
            self._vertex_pick_view = None
            self._vertex_pick_event_callback_id = None
            self._vertex_pick_active = False
            self._set_vertex_pick_ui(False)
            _show_message(self.form, "TIN", f"Vertex Pick Mode could not be started.\n{exc}")

    def _stop_vertex_pick_mode(self, *, silent: bool = False) -> None:
        view = self._vertex_pick_view
        callback_id = self._vertex_pick_event_callback_id
        self._vertex_pick_view = None
        self._vertex_pick_event_callback_id = None
        was_active = self._vertex_pick_active
        self._vertex_pick_active = False
        self._set_vertex_pick_ui(False)
        if view is not None and callback_id is not None and hasattr(view, "removeEventCallback"):
            try:
                view.removeEventCallback("SoMouseButtonEvent", callback_id)
            except Exception:
                pass
        if was_active and not silent:
            self._set_diagnostics("Vertex Pick Mode stopped.")

    def _set_vertex_pick_ui(self, active: bool) -> None:
        if hasattr(self, "_vertex_pick_button"):
            self._vertex_pick_button.setText("Stop Vertex Pick Mode" if active else "Start Vertex Pick Mode")

    def _handle_vertex_mouse_event(self, event) -> None:
        if not self._vertex_pick_active or not _is_left_mouse_down(event):
            return
        point = _world_point_from_view_event(_active_view(self.gui_module), event)
        if point is None:
            self._set_diagnostics("Vertex pick did not resolve an XY point. Click directly on the TIN surface.")
            return
        picked = nearest_tin_vertex(self.base_surface, float(point.x), float(point.y))
        if not picked:
            self._set_diagnostics("Vertex pick did not find a nearby TIN vertex.")
            return
        self._append_vertex_override_from_pick(picked)

    def _append_vertex_override_from_pick(self, picked: dict[str, object]) -> None:
        vertex_id = str(picked.get("vertex_id", "") or "").strip()
        if not vertex_id:
            return
        current_z = float(picked.get("z", 0.0) or 0.0)
        existing_row = self._find_vertex_override_row(vertex_id)
        row = existing_row if existing_row >= 0 else self._first_empty_vertex_override_row()
        if row < 0:
            self._add_vertex_override_row()
            row = self._vertex_table.rowCount() - 1
        self._vertex_table.setItem(row, 0, QtWidgets.QTableWidgetItem(vertex_id))
        if not _table_item_text(self._vertex_table, row, 1):
            self._vertex_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{current_z:.3f}"))
        if not _table_item_text(self._vertex_table, row, 2):
            distance = float(picked.get("distance", 0.0) or 0.0)
            self._vertex_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"picked; current_z={current_z:.3f}; d={distance:.3f}"))
        self._vertex_table.selectRow(row)
        self._set_diagnostics(
            f"Picked vertex {vertex_id}: current Z={current_z:.3f}, "
            f"XY=({_as_float(picked.get('x')):.3f}, {_as_float(picked.get('y')):.3f}). "
            "Edit New Z, then click Apply."
        )

    def _find_vertex_override_row(self, vertex_id: str) -> int:
        target = str(vertex_id or "").strip()
        for row in range(self._vertex_table.rowCount()):
            if _table_item_text(self._vertex_table, row, 0) == target:
                return row
        return -1

    def _first_empty_vertex_override_row(self) -> int:
        for row in range(self._vertex_table.rowCount()):
            if (
                not _table_item_text(self._vertex_table, row, 0)
                and not _table_item_text(self._vertex_table, row, 1)
                and not _table_item_text(self._vertex_table, row, 2)
            ):
                return row
        return -1

    def _operations_from_ui(self) -> list[TINEditOperation]:
        operations: list[TINEditOperation] = []
        target_surface_id = str(getattr(self.base_surface, "surface_id", "") or "")
        operations.append(
            TINEditOperation(
                "tin-edit:boundary-rect",
                "boundary_clip_rect",
                target_surface_id=target_surface_id,
                parameters=_rect_parameters(
                    self._boundary_min_x,
                    self._boundary_max_x,
                    self._boundary_min_y,
                    self._boundary_max_y,
                ),
            )
        )
        if self._void_rect_active:
            operations.append(
                TINEditOperation(
                    "tin-edit:void-rect",
                    "void_clip_rect",
                    target_surface_id=target_surface_id,
                    parameters=_rect_parameters(
                        self._void_min_x,
                        self._void_max_x,
                        self._void_min_y,
                        self._void_max_y,
                    ),
                )
            )
        triangle_ids = str(self._triangle_delete_text.text() or "").strip()
        if triangle_ids:
            operations.append(
                TINEditOperation(
                    "tin-edit:delete-triangles",
                    "delete_triangles",
                    target_surface_id=target_surface_id,
                    parameters={"triangle_ids": triangle_ids},
                )
            )
        vertex_rows = self._vertex_override_rows()
        if vertex_rows:
            operations.append(
                TINEditOperation(
                    "tin-edit:override-vertex-z",
                    "override_vertex_elevation",
                    target_surface_id=target_surface_id,
                    parameters={"vertices": vertex_rows},
                )
            )
        return operations

    def _add_vertex_override_row(self) -> None:
        row = self._vertex_table.rowCount()
        self._vertex_table.insertRow(row)
        for col in range(3):
            self._vertex_table.setItem(row, col, QtWidgets.QTableWidgetItem(""))
        try:
            self._vertex_table.resizeColumnsToContents()
        except Exception:
            pass

    def _delete_selected_vertex_override_rows(self) -> None:
        rows = sorted({index.row() for index in self._vertex_table.selectedIndexes()}, reverse=True)
        if not rows and self._vertex_table.rowCount() > 0:
            rows = [self._vertex_table.rowCount() - 1]
        for row in rows:
            self._vertex_table.removeRow(row)
        if self._vertex_table.rowCount() == 0:
            self._add_vertex_override_row()

    def _vertex_override_rows(self) -> list[dict[str, object]]:
        rows = []
        for row in range(self._vertex_table.rowCount()):
            vertex_id = _table_item_text(self._vertex_table, row, 0)
            new_z_text = _table_item_text(self._vertex_table, row, 1)
            notes = _table_item_text(self._vertex_table, row, 2)
            if not vertex_id and not new_z_text and not notes:
                continue
            if not vertex_id:
                raise ValueError(f"Vertex override row {row + 1} needs a vertex id.")
            if not new_z_text:
                raise ValueError(f"Vertex override row {row + 1} needs a new Z value.")
            try:
                new_z = float(new_z_text)
            except ValueError:
                raise ValueError(f"Vertex override row {row + 1} new Z must be a number.") from None
            rows.append({"vertex_id": vertex_id, "new_z": new_z, "notes": notes})
        return rows

    def _summary_text(self) -> str:
        if self.base_surface is None:
            return "No TIN surface is selected. Use the Source tab to build a TIN from CSV or select an existing TIN preview."
        return (
            f"Surface: {getattr(self.base_surface, 'label', '') or getattr(self.base_surface, 'surface_id', '')}\n"
            f"Surface ID: {getattr(self.base_surface, 'surface_id', '')}\n"
            f"Vertices: {len(list(getattr(self.base_surface, 'vertex_rows', []) or []))}\n"
            f"Triangles: {len(list(getattr(self.base_surface, 'triangle_rows', []) or []))}"
        )

    def _fill_surface_extents(self, min_x, max_x, min_y, max_y) -> None:
        extent = _surface_extent(self.base_surface)
        if not extent:
            return
        min_x.setValue(extent["min_x"])
        max_x.setValue(extent["max_x"])
        min_y.setValue(extent["min_y"])
        max_y.setValue(extent["max_y"])

    def _set_diagnostics(self, text: str) -> None:
        if hasattr(self, "_diagnostics"):
            self._diagnostics.setPlainText(str(text or ""))


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


class _TINFacePickObserver:
    """FreeCAD selection observer used by the TIN triangle pick mode."""

    def __init__(self, panel):
        self.panel = panel

    def addSelection(self, *args):
        self.panel._handle_triangle_pick_event(*args)

    def setSelection(self, *args):
        self.panel._handle_triangle_pick_event(*args)

    def removeSelection(self, *args):
        return

    def clearSelection(self, *args):
        return


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


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditTIN", CmdV1TINEditor())

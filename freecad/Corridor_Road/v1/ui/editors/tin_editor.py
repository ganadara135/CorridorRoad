"""TIN editor presentation for CorridorRoad v1."""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - plain Python contract tests.
    Gui = None


def configure_tineditor_task_panel_runtime(bindings) -> None:
    """Bind command/controller collaborators without importing the command module."""

    protected = {
        "V1TINEditorTaskPanel",
        "_TINFacePickObserver",
        "configure_tineditor_task_panel_runtime",
    }
    for name, value in dict(bindings or {}).items():
        if name.startswith("__") or name in protected:
            continue
        globals()[name] = value


# Explicit runtime collaborators are replaced by the command callback map.
App = None
TINEditOperation = None
_active_view = None
_as_float = None
_boundary_rect_preview_name = None
_default_sample_dir = None
_focus_preview = None
_focus_preview_deferred = None
_format_editor_result = None
_format_xy_point = None
_format_xy_tuple = None
_is_left_mouse_down = None
_process_panel_events = None
_rect_from_xy_points = None
_rect_parameters = None
_remove_rect_previews = None
_select_tin_csv_path = None
_show_message = None
_spin_box = None
_split_id_text = None
_surface_extent = None
_table_item_text = None
_triangle_id_from_subelement_name = None
_unique_strings = None
_update_rect_preview = None
_view_event_component_text = None
_void_rect_preview_name = None
_world_point_from_view_event = None
apply_clickable_tab_style = None
apply_tin_editor_operations = None
build_tin_source_from_csv = None
nearest_tin_vertex = None
triangle_ids_from_selected_faces = None
triangle_ids_from_view_event = None


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
        widget.setWindowTitle("ParametricRoad v1 - TIN")
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

        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Ready")
        layout.addWidget(self._progress)

        self._tabs = QtWidgets.QTabWidget()
        apply_clickable_tab_style(self._tabs, "TINEditorTabs")
        self._tabs.addTab(self._build_source_tab(), "Source")
        self._tabs.addTab(self._build_boundary_tab(), "Boundary")
        self._tabs.addTab(self._build_void_tab(), "Voids")
        self._tabs.addTab(self._build_triangles_tab(), "Triangles")
        self._tabs.addTab(self._build_vertices_tab(), "Vertices")
        self._tabs.addTab(self._build_diagnostics_tab(), "Diagnostics")
        layout.addWidget(self._tabs, 1)

        button_row = QtWidgets.QHBoxLayout()
        show_button = QtWidgets.QPushButton("Show Preview")
        show_button.clicked.connect(self._show_preview)
        button_row.addWidget(show_button)
        review_button = QtWidgets.QPushButton("Review Result")
        review_button.clicked.connect(self._review_tin)
        button_row.addWidget(review_button)
        build_button = QtWidgets.QPushButton("Apply")
        build_button.clicked.connect(lambda: self._build_tin(close_after=False))
        button_row.addWidget(build_button)
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
            self._set_progress(0, "Preparing TIN apply...")
            source_result = None
            csv_path = str(self._source_csv_text.text() or "").strip()
            if csv_path and (self.base_surface is None or csv_path != self._source_csv_path):
                self._set_progress(15, "Building source TIN...")
                source_result = self._build_source_tin(show_completion=False, focus_preview=False)
                self._set_progress(45, "Source TIN ready...")
            else:
                self._set_progress(25, "Reading TIN edit rows...")
            result = self._apply_current_editor_state(focus_preview=True)
            self._set_progress(85, "Updating TIN preview...")
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
            self._set_progress(100, "TIN apply complete")
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
            self._set_progress(0, "TIN apply failed")
            self._set_diagnostics(f"TIN build failed:\n{exc}")
            _show_message(self.form, "TIN", f"TIN was not built.\n{exc}")
            return False

    def _apply(self, *, close_after: bool = False, show_completion: bool = True) -> bool:
        try:
            self._set_progress(0, "Preparing TIN apply...")
            self._set_progress(30, "Reading TIN edit rows...")
            result = self._apply_current_editor_state(focus_preview=True)
            self._set_progress(85, "Updating TIN preview...")
            if show_completion:
                self._set_progress(100, "TIN apply complete")
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
            if not show_completion:
                self._set_progress(100, "TIN apply complete")
            return True
        except Exception as exc:
            self._set_progress(0, "TIN apply failed")
            self._set_diagnostics(f"TIN edit failed:\n{exc}")
            _show_message(self.form, "TIN", f"TIN edits were not applied.\n{exc}")
            return False

    def _show_preview(self) -> None:
        try:
            self._set_progress(0, "Preparing TIN preview...")
            self._set_progress(30, "Reading TIN edit rows...")
            self._apply_current_editor_state(focus_preview=True)
            self._set_progress(100, "TIN preview ready")
        except Exception as exc:
            self._set_progress(0, "TIN preview failed")
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
        self._set_progress(55, "Applying TIN operations...")
        result = apply_tin_editor_operations(
            document=self.document,
            base_surface=self.base_surface,
            operations=operations,
        )
        self._set_progress(75, "Writing TIN result...")
        self._stop_triangle_pick_mode(silent=True)
        self._stop_vertex_pick_mode(silent=True)
        self._stop_boundary_pick_mode(silent=True)
        self._stop_void_pick_mode(silent=True)
        self._last_result = result
        self._set_diagnostics(_format_editor_result(result))
        if focus_preview:
            self._set_progress(90, "Focusing TIN preview...")
            _focus_preview(self.document, result.get("mesh_preview"), gui_module=self.gui_module)
        return result

    def _set_progress(self, value: int, text: str = "") -> None:
        progress = getattr(self, "_progress", None)
        if progress is None:
            return
        try:
            progress.setValue(max(0, min(100, int(value))))
            if text:
                progress.setFormat(text)
        except Exception:
            return
        _process_panel_events()

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


__all__ = [
    "V1TINEditorTaskPanel",
    "_TINFacePickObserver",
    "configure_tineditor_task_panel_runtime",
]

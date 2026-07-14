"""Structure editor task-panel presentation boundary for CorridorRoad v1."""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtWidgets


# Explicit runtime collaborators are replaced by the command callback map.
App = None
CulvertGeometrySpec = None
GEOMETRY_SOURCE_CHOICES = None
Gui = None
LENGTH_MODE_CHOICES = None
NATIVE_TYPE_CHOICES = None
STRUCTURE_GEOMETRY_REF_ROLE = None
STRUCTURE_GEOMETRY_SOURCE_ROLE = None
STRUCTURE_GEOMETRY_SPEC_REF_ROLE = None
STRUCTURE_KIND_CHOICES = None
STRUCTURE_NATIVE_TYPE_ROLE = None
STRUCTURE_PRESETS = None
STRUCTURE_ROLE_CHOICES = None
StructureConnectionPoint = None
StructureGeometrySpec = None
StructureModel = None
StructurePlacement = None
StructureRow = None
VERTICAL_POSITION_MODE_CHOICES = None
_alignment_id = None
_bridge_spec_from_detail = None
_culvert_spec_from_detail = None
_default_geometry_height = None
_default_geometry_height_for_native = None
_default_geometry_width = None
_default_geometry_width_for_native = None
_default_shape_kind = None
_default_shape_kind_for_native = None
_default_structure_kind_for_native = None
_default_structure_role_for_native = None
_derive_default_connection_points_for_row = None
_detail_spec_family = None
_detail_values_with_native_defaults = None
_display_structure_ref = None
_filter_kind_specs = None
_format_float = None
_format_optional_float = None
_format_validation_result = None
_geometry_source_mode = None
_item_text = None
_item_user_data = None
_kind_detail_values = None
_mark_auto_native_connection_points = None
_native_detail_field_specs = None
_normalized_connection_point_rows_for_structures = None
_optional_float_text = None
_project_id = None
_replace_kind_spec = None
_required_float = None
_retaining_wall_spec_from_detail = None
_selected_3d_object = None
_selected_3d_point = None
_selected_structure_diagnostics = None
_show_message = None
_source_structure_ref = None
_station_offset_from_point = None
_structure_editor_diagnostics = None
apply_v1_structure_model = None
find_project = None
find_v1_alignment = None
find_v1_structure_model = None
show_v1_structure_connection_points_preview_object = None
show_v1_structure_preview_object = None
structure_preset_model_from_document = None
structure_preset_names = None
to_structure_model = None


class StructureEditorTaskPanelPresentation:
    """Own common task-panel lifecycle and presentation state.

    The concrete command-side controller supplies the existing UI construction and
    source-edit callbacks while those responsibilities are migrated incrementally.
    """

    def __init__(
        self,
        *,
        document=None,
        app_module=None,
        gui_module=None,
        structure_finder=None,
    ) -> None:
        self._app_module = app_module
        self._gui_module = gui_module
        self.document = document or (
            getattr(app_module, "ActiveDocument", None) if app_module is not None else None
        )
        self.structure_obj = structure_finder(self.document) if callable(structure_finder) else None
        self._geometry_spec_rows = []
        self._bridge_geometry_spec_rows = []
        self._culvert_geometry_spec_rows = []
        self._retaining_wall_geometry_spec_rows = []
        self._connection_point_rows = []
        self._active_detail_structure_id = ""
        self._active_detail_spec_ref = ""
        self._loading_selected_detail = False
        self.form = self._build_ui()
        self._load_existing_rows()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._apply(close_after=True)

    def reject(self):
        gui = self._gui_module
        if gui is not None and hasattr(gui, "Control"):
            gui.Control.closeDialog()
        return True

    def _set_status(self, text: str) -> None:
        self._status.setPlainText(str(text or ""))

    def _set_detail_validation(self, text: str, *, status: str) -> None:
        if not hasattr(self, "_detail_validation"):
            return
        self._detail_validation.setText(str(text or ""))
        color = {
            "ok": "#2f8f46",
            "warning": "#a06a00",
            "error": "#b00020",
            "none": "#666666",
        }.get(str(status or ""), "#666666")
        try:
            self._detail_validation.setStyleSheet(f"color: {color};")
        except Exception:
            pass


def configure_structure_editor_task_panel_runtime(bindings) -> None:
    """Bind command/controller collaborators without importing the command module."""

    protected = {
        "StructureEditorTaskPanelPresentation",
        "V1StructureEditorTaskPanel",
        "configure_structure_editor_task_panel_runtime",
    }
    for name, value in dict(bindings or {}).items():
        if name.startswith("__") or name in protected:
            continue
        globals()[name] = value


class V1StructureEditorTaskPanel(StructureEditorTaskPanelPresentation):
    """Table-based v1 Structure source editor."""

    # Task-panel methods are owned here. Runtime collaborators are injected by
    # the thin command adapter after its controllers and helpers are defined.
    def __init__(self, *, document=None):
        super().__init__(
            document=document,
            app_module=App,
            gui_module=Gui,
            structure_finder=find_v1_structure_model,
        )

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("ParametricRoad v1 - Structures")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Structures")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel(
            "Define station-bounded v1 structure source rows. Apply stores source intent only; "
            "rebuild Applied Sections to reflect structure context in section results."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        self._preset_combo = QtWidgets.QComboBox()
        self._preset_combo.addItems(structure_preset_names())
        preset_row.addWidget(self._preset_combo)
        load_preset_button = QtWidgets.QPushButton("Load Preset")
        load_preset_button.clicked.connect(self._load_selected_preset)
        preset_row.addWidget(load_preset_button)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        self._preset_note = QtWidgets.QLabel("")
        self._preset_note.setWordWrap(True)
        layout.addWidget(self._preset_note)
        self._preset_combo.currentIndexChanged.connect(self._update_preset_note)

        self._table = QtWidgets.QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["Structure Id", "Kind", "Role", "Start STA", "End STA", "Offset", "Notes"]
        )
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        self._table.itemSelectionChanged.connect(self._load_selected_detail)
        self._table.cellClicked.connect(self._activate_structure_detail_row)
        self._table.currentCellChanged.connect(self._handle_structure_current_cell_changed)
        self._table.cellDoubleClicked.connect(self._activate_structure_detail_row)
        try:
            self._table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._table, 1)

        edit_row = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Structure")
        add_button.clicked.connect(self._add_structure_row)
        edit_row.addWidget(add_button)
        delete_button = QtWidgets.QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_selected_rows)
        edit_row.addWidget(delete_button)
        sort_button = QtWidgets.QPushButton("Sort by Station")
        sort_button.clicked.connect(self._sort_rows)
        edit_row.addWidget(sort_button)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)

        self._geometry_table = QtWidgets.QTableWidget(0, 12)
        self._geometry_table.setObjectName("InternalGeometrySpecStore")
        self._geometry_table.setToolTip("Internal source-contract store. Edit geometry through Selected Structure Detail.")
        self._geometry_table.setHorizontalHeaderLabels(
            [
                "Spec Id",
                "Structure Ref",
                "Shape",
                "Width",
                "Height",
                "Length Mode",
                "Skew",
                "Vertical Mode",
                "Base Elev",
                "Top Elev",
                "Material",
                "Notes",
            ]
        )
        self._geometry_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._geometry_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self._geometry_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        try:
            self._geometry_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._geometry_table.setVisible(False)

        detail_group = QtWidgets.QGroupBox("Selected Structure Detail")
        detail_layout = QtWidgets.QVBoxLayout(detail_group)
        self._detail_summary = QtWidgets.QLabel("No structure row is selected.")
        detail_layout.addWidget(self._detail_summary)
        self._detail_validation = QtWidgets.QLabel("Selected validation: not available")
        self._detail_validation.setWordWrap(True)
        detail_layout.addWidget(self._detail_validation)
        detail_form = QtWidgets.QFormLayout()
        self._geometry_source_combo = QtWidgets.QComboBox()
        self._geometry_source_combo.addItems(GEOMETRY_SOURCE_CHOICES)
        self._geometry_source_combo.setToolTip("Native creates a simple Parametric Road body. External Ref uses a referenced body plus explicit connection-point mapping.")
        self._geometry_source_combo.currentIndexChanged.connect(self._handle_geometry_source_changed)
        detail_form.addRow("Geometry Source", self._geometry_source_combo)
        self._native_type_combo = QtWidgets.QComboBox()
        self._native_type_combo.addItems(NATIVE_TYPE_CHOICES)
        self._native_type_combo.setToolTip("Simple native structure type used to drive practical dimensions and default connection points.")
        self._native_type_combo.currentIndexChanged.connect(self._handle_native_type_changed)
        detail_form.addRow("Native Type", self._native_type_combo)
        external_ref_row = QtWidgets.QHBoxLayout()
        self._geometry_ref_field = QtWidgets.QLineEdit()
        self._geometry_ref_field.setPlaceholderText("Select an existing FreeCAD/imported object")
        self._geometry_ref_field.setToolTip(
            "External Ref stores the referenced body object name only. "
            "Drainage connection points remain editable source rows below."
        )
        self._geometry_ref_field.textEdited.connect(lambda _text: self._sync_selected_detail_to_row())
        external_ref_row.addWidget(self._geometry_ref_field, 1)
        self._pick_external_ref_button = QtWidgets.QPushButton("Pick External")
        self._pick_external_ref_button.setToolTip("Use the currently selected 3D object as the external Structure body reference.")
        self._pick_external_ref_button.clicked.connect(self._pick_external_geometry_ref_from_3d)
        external_ref_row.addWidget(self._pick_external_ref_button)
        detail_form.addRow("External Geometry Ref", external_ref_row)
        self._common_shape_label = QtWidgets.QLabel("Shape (auto)")
        self._common_shape_label.setToolTip("Auto-filled from Native Type. Edit only when a custom native shape key is needed.")
        self._common_shape_field = QtWidgets.QLineEdit()
        self._common_shape_field.setPlaceholderText("Auto from Native Type")
        self._common_shape_field.setToolTip(
            "Auto-filled from Native Type and used by generated structure geometry. "
            "Leave the default unless this structure needs a custom native shape key."
        )
        detail_form.addRow(self._common_shape_label, self._common_shape_field)
        self._common_width_field = QtWidgets.QLineEdit()
        detail_form.addRow("Width", self._common_width_field)
        self._common_height_field = QtWidgets.QLineEdit()
        detail_form.addRow("Height", self._common_height_field)
        self._common_vertical_mode_combo = QtWidgets.QComboBox()
        self._common_vertical_mode_combo.setEditable(True)
        self._common_vertical_mode_combo.addItems(VERTICAL_POSITION_MODE_CHOICES)
        detail_form.addRow("Vertical Mode", self._common_vertical_mode_combo)
        self._common_base_elev_field = QtWidgets.QLineEdit()
        detail_form.addRow("Base Elev", self._common_base_elev_field)
        self._common_top_elev_field = QtWidgets.QLineEdit()
        detail_form.addRow("Top Elev", self._common_top_elev_field)
        self._common_skew_field = QtWidgets.QLineEdit()
        detail_form.addRow("Skew", self._common_skew_field)
        self._common_material_field = QtWidgets.QLineEdit()
        detail_form.addRow("Material", self._common_material_field)
        self._common_notes_field = QtWidgets.QLineEdit()
        detail_form.addRow("Geometry Notes", self._common_notes_field)
        self._detail_labels = []
        self._detail_fields = []
        for _index in range(10):
            label = QtWidgets.QLabel("")
            field = QtWidgets.QLineEdit()
            detail_form.addRow(label, field)
            self._detail_labels.append(label)
            self._detail_fields.append(field)
        detail_layout.addLayout(detail_form)

        self._connection_label = QtWidgets.QLabel("Drainage Connection Points")
        self._connection_label.setToolTip("Stable source endpoints for Drainage pipe/channel connectivity.")
        detail_layout.addWidget(self._connection_label)
        self._connection_table = QtWidgets.QTableWidget(0, 12)
        self._connection_table.setHorizontalHeaderLabels(
            [
                "Point ID",
                "Role",
                "STA",
                "Offset",
                "Elev",
                "Invert",
                "Shape",
                "Width",
                "Height",
                "Diameter",
                "Direction",
                "Notes",
            ]
        )
        self._connection_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._connection_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._connection_table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        self._connection_table.cellDoubleClicked.connect(lambda row_index, _col: self._preview_connection_point_row(row_index))
        try:
            self._connection_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        detail_layout.addWidget(self._connection_table, 1)

        connection_action_row = QtWidgets.QHBoxLayout()
        add_point_button = QtWidgets.QPushButton("Add Point")
        add_point_button.clicked.connect(self._add_connection_point)
        connection_action_row.addWidget(add_point_button)
        delete_point_button = QtWidgets.QPushButton("Delete Point")
        delete_point_button.clicked.connect(self._delete_connection_points)
        connection_action_row.addWidget(delete_point_button)
        pick_point_button = QtWidgets.QPushButton("Pick From 3D")
        pick_point_button.clicked.connect(self._pick_connection_point_from_3d)
        connection_action_row.addWidget(pick_point_button)
        derive_points_button = QtWidgets.QPushButton("Derive Defaults")
        derive_points_button.clicked.connect(self._derive_default_connection_points)
        connection_action_row.addWidget(derive_points_button)
        preview_points_button = QtWidgets.QPushButton("Preview Points")
        preview_points_button.clicked.connect(self._preview_connection_points)
        connection_action_row.addWidget(preview_points_button)
        connection_action_row.addStretch(1)
        detail_layout.addLayout(connection_action_row)

        detail_action_row = QtWidgets.QHBoxLayout()
        self._apply_detail_button = QtWidgets.QPushButton("Apply Selected Detail")
        self._apply_detail_button.setToolTip("Apply geometry detail and Drainage Connection Points for the selected Structure row.")
        self._apply_detail_button.clicked.connect(self._apply_selected_detail)
        detail_action_row.addWidget(self._apply_detail_button)
        detail_action_row.addStretch(1)
        detail_layout.addLayout(detail_action_row)
        layout.addWidget(detail_group)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setFixedHeight(100)
        self._status.setPlainText("No structure source object is selected.")
        layout.addWidget(self._status)

        action_row = QtWidgets.QHBoxLayout()
        validate_button = QtWidgets.QPushButton("Validate")
        validate_button.clicked.connect(self._validate)
        action_row.addWidget(validate_button)
        self._save_button = QtWidgets.QPushButton("Apply")
        self._save_button.setToolTip("Apply the current Structure source rows without creating a 3D preview.")
        self._save_button.clicked.connect(lambda: self._apply(close_after=False, show_preview=False))
        action_row.addWidget(self._save_button)
        self._preview_button = QtWidgets.QPushButton("Preview 3D")
        self._preview_button.setToolTip("Create a temporary 3D preview from the current panel values without applying.")
        self._preview_button.clicked.connect(self._show_preview)
        action_row.addWidget(self._preview_button)
        self._save_preview_button = QtWidgets.QPushButton("Apply + Preview")
        self._save_preview_button.setToolTip("Apply the current Structure source rows, then create a 3D preview.")
        self._save_preview_button.clicked.connect(lambda: self._apply(close_after=False, show_preview=True))
        action_row.addWidget(self._save_preview_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        self._update_preset_note()
        return widget

    def _load_existing_rows(self) -> None:
        self.structure_obj = find_v1_structure_model(self.document, preferred_structure_model=self.structure_obj)
        model = to_structure_model(self.structure_obj)
        if model is None:
            return
        self._geometry_spec_rows = list(getattr(model, "geometry_spec_rows", []) or [])
        self._bridge_geometry_spec_rows = list(getattr(model, "bridge_geometry_spec_rows", []) or [])
        self._culvert_geometry_spec_rows = list(getattr(model, "culvert_geometry_spec_rows", []) or [])
        self._retaining_wall_geometry_spec_rows = list(getattr(model, "retaining_wall_geometry_spec_rows", []) or [])
        self._connection_point_rows = list(getattr(model, "connection_point_rows", []) or [])
        self._active_detail_structure_id = ""
        self._active_detail_spec_ref = ""
        self._replace_rows(model.structure_rows)
        self._replace_geometry_specs(self._geometry_spec_rows)
        self._select_first_structure_row()
        self._set_status(f"Loaded {len(model.structure_rows)} Structure row(s) from {self.structure_obj.Label}.")

    def _reload_existing_rows(self, *, selected_structure_id: str = "") -> None:
        self.structure_obj = find_v1_structure_model(self.document, preferred_structure_model=self.structure_obj)
        model = to_structure_model(self.structure_obj)
        if model is None:
            return
        self._geometry_spec_rows = list(getattr(model, "geometry_spec_rows", []) or [])
        self._bridge_geometry_spec_rows = list(getattr(model, "bridge_geometry_spec_rows", []) or [])
        self._culvert_geometry_spec_rows = list(getattr(model, "culvert_geometry_spec_rows", []) or [])
        self._retaining_wall_geometry_spec_rows = list(getattr(model, "retaining_wall_geometry_spec_rows", []) or [])
        self._connection_point_rows = list(getattr(model, "connection_point_rows", []) or [])
        self._active_detail_structure_id = ""
        self._active_detail_spec_ref = ""
        self._replace_rows(model.structure_rows)
        self._replace_geometry_specs(self._geometry_spec_rows)
        if selected_structure_id:
            self._select_structure_id(selected_structure_id)
        else:
            self._select_first_structure_row()

    def _load_selected_preset(self) -> None:
        try:
            preset_name = str(self._preset_combo.currentText() or "Bridge Segment")
            model = structure_preset_model_from_document(preset_name, document=self.document)
            self._geometry_spec_rows = list(getattr(model, "geometry_spec_rows", []) or [])
            self._bridge_geometry_spec_rows = list(getattr(model, "bridge_geometry_spec_rows", []) or [])
            self._culvert_geometry_spec_rows = list(getattr(model, "culvert_geometry_spec_rows", []) or [])
            self._retaining_wall_geometry_spec_rows = list(getattr(model, "retaining_wall_geometry_spec_rows", []) or [])
            self._connection_point_rows = list(getattr(model, "connection_point_rows", []) or [])
            self._replace_rows(model.structure_rows)
            self._replace_geometry_specs(self._geometry_spec_rows)
            self._select_first_structure_row()
            self._set_status(f"Structure preset loaded: {preset_name}. Apply when ready.")
        except Exception as exc:
            self._set_status(f"Structure preset was not loaded:\n{exc}")

    def _update_preset_note(self) -> None:
        if not hasattr(self, "_preset_note"):
            return
        preset = STRUCTURE_PRESETS.get(str(self._preset_combo.currentText() or ""), {})
        self._preset_note.setText(str(preset.get("note", "") or ""))

    def _replace_rows(self, rows: list[StructureRow]) -> None:
        self._table.setRowCount(0)
        for row in rows:
            self._append_row(row)

    def _replace_geometry_specs(self, rows: list[StructureGeometrySpec]) -> None:
        self._geometry_table.setRowCount(0)
        for row in rows:
            self._append_geometry_spec(row)

    def _append_row(self, row: StructureRow | None = None) -> None:
        row = row or StructureRow(
            structure_id=f"structure:{self._table.rowCount() + 1}",
            structure_kind="bridge",
            structure_role="interface",
            placement=StructurePlacement(
                placement_id=f"placement:{self._table.rowCount() + 1}",
                alignment_id=_alignment_id(self.document),
                station_start=0.0,
                station_end=100.0,
            ),
            geometry_spec_ref=f"geometry-spec:{self._table.rowCount() + 1}",
        )
        index = self._table.rowCount()
        self._table.insertRow(index)
        values = [
            _display_structure_ref(row.structure_id),
            row.structure_kind,
            row.structure_role,
            _format_float(row.placement.station_start),
            _format_float(row.placement.station_end),
            _format_float(row.placement.offset),
            "",
        ]
        for col, value in enumerate(values):
            if col == 1:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(STRUCTURE_KIND_CHOICES)
                combo.setCurrentText(str(value or "bridge"))
                self._bind_structure_row_widget(combo)
                self._table.setCellWidget(index, col, combo)
            elif col == 2:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(STRUCTURE_ROLE_CHOICES)
                combo.setCurrentText(str(value or "interface"))
                self._bind_structure_row_widget(combo)
                self._table.setCellWidget(index, col, combo)
            else:
                item = QtWidgets.QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(STRUCTURE_GEOMETRY_SPEC_REF_ROLE, str(getattr(row, "geometry_spec_ref", "") or ""))
                    item.setData(STRUCTURE_GEOMETRY_REF_ROLE, str(getattr(row, "geometry_ref", "") or ""))
                    item.setData(STRUCTURE_GEOMETRY_SOURCE_ROLE, _geometry_source_mode(row))
                    item.setData(STRUCTURE_NATIVE_TYPE_ROLE, str(getattr(row, "native_type", "") or ""))
                self._table.setItem(index, col, item)

    def _append_geometry_spec(self, row: StructureGeometrySpec | None = None) -> None:
        row = row or StructureGeometrySpec(
            geometry_spec_id=f"geometry-spec:{self._geometry_table.rowCount() + 1}",
            structure_ref=f"structure:{self._geometry_table.rowCount() + 1}",
            shape_kind="deck_slab",
            width=10.0,
            height=1.2,
        )
        index = self._geometry_table.rowCount()
        self._geometry_table.insertRow(index)
        values = [
            row.geometry_spec_id,
            row.structure_ref,
            row.shape_kind,
            _format_float(row.width),
            _format_float(row.height),
            row.length_mode,
            _format_float(row.skew_angle_deg),
            row.vertical_position_mode,
            _format_optional_float(row.base_elevation),
            _format_optional_float(row.top_elevation),
            row.material,
            row.notes,
        ]
        for col, value in enumerate(values):
            if col == 5:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(LENGTH_MODE_CHOICES)
                combo.setCurrentText(str(value or "station_range"))
                self._geometry_table.setCellWidget(index, col, combo)
            elif col == 7:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(VERTICAL_POSITION_MODE_CHOICES)
                combo.setCurrentText(str(value or "profile_frame"))
                self._geometry_table.setCellWidget(index, col, combo)
            else:
                self._geometry_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))

    def _add_structure_row(self) -> None:
        self._append_row()
        self._add_missing_geometry_specs()
        self._table.selectRow(max(0, self._table.rowCount() - 1))
        self._set_status("Added a Structure row. Edit values, then Validate or Apply.")

    def _delete_selected_rows(self) -> None:
        rows = sorted({item.row() for item in list(self._table.selectedItems() or [])}, reverse=True)
        if not rows and self._table.currentRow() >= 0:
            rows = [self._table.currentRow()]
        for row_index in rows:
            self._table.removeRow(row_index)
        self._load_selected_detail()
        self._set_status(f"Deleted {len(rows)} Structure row(s).")

    def _add_missing_geometry_specs(self) -> None:
        existing_spec_ids = {str(row.geometry_spec_id) for row in self._geometry_spec_table_rows(allow_blank=True)}
        existing_structure_refs = {str(row.structure_ref) for row in self._geometry_spec_table_rows(allow_blank=True)}
        added = 0
        for row in self._table_rows():
            structure_ref = str(row.structure_id)
            spec_ref = str(row.geometry_spec_ref or f"geometry-spec:{structure_ref.split(':')[-1]}")
            if spec_ref in existing_spec_ids or structure_ref in existing_structure_refs:
                continue
            self._append_geometry_spec(
                StructureGeometrySpec(
                    geometry_spec_id=spec_ref,
                    structure_ref=structure_ref,
                    shape_kind=_default_shape_kind(row.structure_kind),
                    width=_default_geometry_width(row.structure_kind),
                    height=_default_geometry_height(row.structure_kind),
                    length_mode="station_range",
                    vertical_position_mode="profile_frame",
                    style_role=str(row.structure_kind),
                )
            )
            added += 1
        self._set_status(f"Added {added} missing Geometry Spec row(s).")

    def _add_connection_point(self) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before adding a connection point.")
            return
        self._append_connection_point(
            StructureConnectionPoint(
                connection_point_id=f"connection:{str(row.structure_id).split(':')[-1]}:{self._connection_table.rowCount() + 1}",
                structure_ref=str(row.structure_id),
                point_role="inlet",
                station=float(getattr(row.placement, "station_start", 0.0) or 0.0),
                offset=float(getattr(row.placement, "offset", 0.0) or 0.0),
                region_ref="",
            )
        )
        self._set_status(f"Added a connection point for {row.structure_id}.")

    def _delete_connection_points(self) -> None:
        rows = sorted({item.row() for item in list(self._connection_table.selectedItems() or [])}, reverse=True)
        if not rows and self._connection_table.currentRow() >= 0:
            rows = [self._connection_table.currentRow()]
        for row_index in rows:
            self._connection_table.removeRow(row_index)
        if self._active_detail_structure_id:
            self._sync_connection_points_from_table(self._active_detail_structure_id)
        self._set_status(f"Deleted {len(rows)} connection point row(s).")

    def _derive_default_connection_points(self) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before deriving connection points.")
            return
        points = _derive_default_connection_points_for_row(row, self._geometry_spec_for_structure(row), self._culvert_spec_for_structure(row))
        if not points:
            self._set_status(f"No default connection point rule is defined for {row.structure_kind}.")
            return
        self._replace_connection_points(points)
        self._sync_connection_points_from_table(str(row.structure_id))
        self._set_status(f"Derived {len(points)} connection point row(s) for {row.structure_id}.")

    def _pick_connection_point_from_3d(self) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before picking a connection point.")
            return
        try:
            point = _selected_3d_point()
            station, offset = _station_offset_from_point(self.document, point)
            target_row = self._connection_table.currentRow()
            if target_row < 0:
                self._add_connection_point()
                target_row = self._connection_table.rowCount() - 1
            self._set_connection_cell(target_row, 2, _format_float(station))
            self._set_connection_cell(target_row, 3, _format_float(offset))
            self._set_connection_cell(target_row, 4, _format_float(float(getattr(point, "z", 0.0) or 0.0)))
            self._set_connection_cell(target_row, 5, _format_float(float(getattr(point, "z", 0.0) or 0.0)))
            notes = _item_text(self._connection_table, target_row, 11)
            if "picked_from_3d" not in notes:
                self._set_connection_cell(target_row, 11, (notes + "; " if notes else "") + "picked_from_3d")
            self._sync_connection_points_from_table(str(row.structure_id))
            self._set_status(
                "Picked 3D point into connection point row: "
                f"STA {station:.3f}, Offset {offset:.3f}, Elev {float(getattr(point, 'z', 0.0) or 0.0):.3f}."
            )
        except Exception as exc:
            self._set_status(f"3D point was not picked:\n{exc}")

    def _pick_external_geometry_ref_from_3d(self) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before picking an external geometry reference.")
            return
        try:
            obj = _selected_3d_object()
            ref = str(getattr(obj, "Name", "") or getattr(obj, "Label", "") or "").strip()
            if not ref:
                raise RuntimeError("Selected object has no usable object name.")
            row_index = self._table.currentRow()
            self._geometry_source_combo.setCurrentText("external_ref")
            self._geometry_ref_field.setText(ref)
            self._set_row_geometry_source_mode(row_index, "external_ref")
            self._set_row_geometry_ref(row_index, ref)
            self._refresh_selected_detail_validation(str(row.structure_id), str(getattr(row, "geometry_spec_ref", "") or ""))
            self._set_status(
                f"External geometry reference set for {row.structure_id}: {ref}. "
                "Map connection points with Pick From 3D or explicit station/offset rows."
            )
        except Exception as exc:
            self._set_status(f"External geometry reference was not picked:\n{exc}")

    def _preview_connection_points(self) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before previewing connection points.")
            return
        try:
            model = self._model_from_table()
            preview = show_v1_structure_connection_points_preview_object(
                self.document,
                model,
                structure_ref=str(row.structure_id),
            )
            self._focus_preview_object(preview)
            self._set_status(f"Connection point preview shown for {row.structure_id}.")
        except Exception as exc:
            self._set_status(f"Connection point preview was not shown:\n{exc}")

    def _preview_connection_point_row(self, row_index: int) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before previewing a connection point.")
            return
        try:
            model = self._model_from_table()
            connection_ref = _item_text(self._connection_table, row_index, 0)
            preview = show_v1_structure_connection_points_preview_object(
                self.document,
                model,
                structure_ref=str(row.structure_id),
                connection_point_ref=connection_ref,
            )
            self._focus_preview_object(preview)
            self._set_status(f"Connection point preview shown: {connection_ref}.")
        except Exception as exc:
            self._set_status(f"Connection point preview was not shown:\n{exc}")

    def _connection_points_for_structure(self, structure_ref: str) -> list[StructureConnectionPoint]:
        expected = str(structure_ref or "")
        return [
            row
            for row in list(self._connection_point_rows or [])
            if str(getattr(row, "structure_ref", "") or "") == expected
        ]

    def _replace_connection_points(self, rows: list[StructureConnectionPoint]) -> None:
        self._connection_table.setRowCount(0)
        for row in rows:
            self._append_connection_point(row)

    def _append_connection_point(self, row: StructureConnectionPoint) -> None:
        index = self._connection_table.rowCount()
        self._connection_table.insertRow(index)
        values = [
            row.connection_point_id,
            row.point_role,
            _format_float(row.station),
            _format_float(row.offset),
            _format_optional_float(row.elevation),
            _format_optional_float(row.invert_elevation),
            row.shape_kind,
            _format_float(row.width),
            _format_float(row.height),
            _format_float(row.diameter),
            row.direction,
            row.notes,
        ]
        for col, value in enumerate(values):
            self._connection_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))

    def _set_connection_cell(self, row_index: int, col: int, value: str) -> None:
        item = self._connection_table.item(row_index, col)
        if item is None:
            item = QtWidgets.QTableWidgetItem("")
            self._connection_table.setItem(row_index, col, item)
        item.setText(str(value or ""))

    def _sync_connection_points_from_table(self, structure_ref: str) -> None:
        structure_ref = str(structure_ref or "")
        if not structure_ref:
            return
        retained = [
            row
            for row in list(self._connection_point_rows or [])
            if str(getattr(row, "structure_ref", "") or "") != structure_ref
        ]
        retained.extend(self._connection_point_table_rows(structure_ref))
        self._connection_point_rows = retained

    def _connection_point_table_rows(self, structure_ref: str) -> list[StructureConnectionPoint]:
        rows: list[StructureConnectionPoint] = []
        for row_index in range(self._connection_table.rowCount()):
            point_id = _item_text(self._connection_table, row_index, 0) or f"connection:{structure_ref.split(':')[-1]}:{row_index + 1}"
            rows.append(
                StructureConnectionPoint(
                    connection_point_id=point_id,
                    structure_ref=structure_ref,
                    point_role=_item_text(self._connection_table, row_index, 1) or "inlet",
                    station=_required_float(_item_text(self._connection_table, row_index, 2), f"Connection point row {row_index + 1} STA"),
                    offset=_required_float(_item_text(self._connection_table, row_index, 3) or "0", f"Connection point row {row_index + 1} offset"),
                    elevation=_optional_float_text(_item_text(self._connection_table, row_index, 4)),
                    invert_elevation=_optional_float_text(_item_text(self._connection_table, row_index, 5)),
                    shape_kind=_item_text(self._connection_table, row_index, 6),
                    width=_required_float(_item_text(self._connection_table, row_index, 7) or "0", f"Connection point row {row_index + 1} width"),
                    height=_required_float(_item_text(self._connection_table, row_index, 8) or "0", f"Connection point row {row_index + 1} height"),
                    diameter=_required_float(_item_text(self._connection_table, row_index, 9) or "0", f"Connection point row {row_index + 1} diameter"),
                    direction=_item_text(self._connection_table, row_index, 10),
                    connection_order=row_index + 1,
                    region_ref="",
                    notes=_item_text(self._connection_table, row_index, 11),
                )
            )
        return rows

    def _structure_row_by_id(self, structure_ref: str) -> StructureRow | None:
        expected = str(structure_ref or "")
        for row_index in range(self._table.rowCount()):
            if _source_structure_ref(_item_text(self._table, row_index, 0)) == expected:
                return self._structure_row_from_table_index(row_index)
        return None

    def _geometry_spec_for_structure(self, row: StructureRow) -> StructureGeometrySpec | None:
        spec_ref = str(getattr(row, "geometry_spec_ref", "") or "")
        for spec in self._geometry_spec_table_rows(allow_blank=True):
            if str(getattr(spec, "geometry_spec_id", "") or "") == spec_ref:
                return spec
        return None

    def _culvert_spec_for_structure(self, row: StructureRow) -> CulvertGeometrySpec | None:
        spec_ref = str(getattr(row, "geometry_spec_ref", "") or "")
        for spec in list(self._culvert_geometry_spec_rows or []):
            if str(getattr(spec, "geometry_spec_ref", "") or "") == spec_ref:
                return spec
        return None

    def _sort_rows(self) -> None:
        try:
            current_id = self._current_structure_id()
            rows = sorted(self._table_rows(), key=lambda row: (row.placement.station_start, row.placement.station_end, row.structure_id))
            self._replace_rows(rows)
            self._select_structure_id(current_id)
            self._set_status("Structure rows sorted by station.")
        except Exception as exc:
            self._set_status(f"Structure rows were not sorted:\n{exc}")

    def _activate_structure_detail_row(self, row_index: int, _column: int = 0) -> None:
        if row_index < 0 or row_index >= self._table.rowCount():
            return
        try:
            self._table.blockSignals(True)
            self._table.setCurrentCell(row_index, 0)
            self._table.selectRow(row_index)
        finally:
            self._table.blockSignals(False)
        self._load_selected_detail()

    def _handle_structure_current_cell_changed(self, row_index: int, _column: int, previous_row: int, _previous_column: int) -> None:
        if row_index < 0 or row_index == previous_row:
            return
        self._activate_structure_detail_row(row_index, _column)

    def _bind_structure_row_widget(self, widget) -> None:
        try:
            original_mouse_press = widget.mousePressEvent

            def mouse_press_event(event, row_widget=widget, original=original_mouse_press):
                self._activate_structure_detail_widget(row_widget)
                original(event)

            widget.mousePressEvent = mouse_press_event
        except Exception:
            pass
        try:
            widget.currentIndexChanged.connect(lambda _index, row_widget=widget: self._activate_structure_detail_widget(row_widget))
        except Exception:
            pass

    def _activate_structure_detail_widget(self, widget) -> None:
        row_index = self._structure_table_widget_row(widget)
        if row_index >= 0:
            self._activate_structure_detail_row(row_index, 0)

    def _structure_table_widget_row(self, widget) -> int:
        for row_index in range(self._table.rowCount()):
            for col_index in range(self._table.columnCount()):
                if self._table.cellWidget(row_index, col_index) is widget:
                    return row_index
        return -1

    def _load_selected_detail(self) -> None:
        if not self._loading_selected_detail and self._active_detail_structure_id:
            self._sync_common_geometry_detail_to_specs(self._active_detail_structure_id, self._active_detail_spec_ref)
            self._sync_connection_points_from_table(self._active_detail_structure_id)
        self._loading_selected_detail = True
        try:
            row = self._current_structure_row()
            if row is None:
                self._active_detail_structure_id = ""
                self._active_detail_spec_ref = ""
                self._detail_summary.setText("No structure row is selected.")
                self._set_detail_validation("Selected validation: not available", status="none")
                self._geometry_source_combo.setEnabled(False)
                self._native_type_combo.setEnabled(False)
                self._geometry_source_combo.setCurrentText("native")
                self._native_type_combo.setCurrentText("")
                self._geometry_ref_field.setText("")
                self._geometry_ref_field.setEnabled(False)
                self._pick_external_ref_button.setEnabled(False)
                self._load_common_geometry_detail(None, "")
                self._connection_table.setRowCount(0)
                for label, field in zip(self._detail_labels, self._detail_fields):
                    label.setText("")
                    label.hide()
                    field.setText("")
                    field.hide()
                return
            source_mode = _geometry_source_mode(row)
            native_type = str(getattr(row, "native_type", "") or "")
            self._geometry_source_combo.setEnabled(True)
            self._geometry_source_combo.setCurrentText(source_mode)
            self._native_type_combo.setEnabled(source_mode == "native")
            self._native_type_combo.setCurrentText(native_type if native_type in NATIVE_TYPE_CHOICES else "")
            self._geometry_ref_field.setEnabled(source_mode != "native")
            self._pick_external_ref_button.setEnabled(source_mode != "native")
            self._geometry_ref_field.setText(str(getattr(row, "geometry_ref", "") or ""))
            spec_ref = self._ensure_row_geometry_spec_ref(self._table.currentRow(), row)
            self._active_detail_structure_id = str(row.structure_id)
            self._active_detail_spec_ref = spec_ref
            self._load_common_geometry_detail(row, spec_ref)
            self._replace_connection_points(self._connection_points_for_structure(row.structure_id))
            kind = str(row.structure_kind or "").strip().lower()
            self._detail_summary.setText(f"{_display_structure_ref(row.structure_id)} | {kind or 'custom'} | {spec_ref}")
            self._load_type_specific_detail(row, spec_ref)
        finally:
            self._loading_selected_detail = False
        if self._active_detail_structure_id:
            self._refresh_selected_detail_validation(self._active_detail_structure_id, self._active_detail_spec_ref)

    def _apply_selected_detail(self) -> None:
        try:
            row_index = self._table.currentRow()
            row = self._current_structure_row()
            if row is None or row_index < 0:
                self._set_status("Select a Structure row before applying detail fields.")
                return
            self._set_row_geometry_source_mode(row_index, str(self._geometry_source_combo.currentText() or "native"))
            self._set_row_native_type(row_index, str(self._native_type_combo.currentText() or ""))
            self._set_row_geometry_ref(row_index, str(self._geometry_ref_field.text() or "").strip())
            native_type = str(self._native_type_combo.currentText() or "").strip().lower()
            self._apply_native_type_row_defaults(row_index, native_type=native_type)
            row = self._current_structure_row()
            if row is None:
                self._set_status("Select a Structure row before applying detail fields.")
                return
            spec_ref = self._ensure_row_geometry_spec_ref(row_index, row)
            self._add_or_update_common_spec_for_row(row, spec_ref)
            kind = str(row.structure_kind or "").strip().lower()
            detail_family = _detail_spec_family(native_type, kind)
            fields = _native_detail_field_specs(native_type, kind)
            values = {
                key: str(self._detail_fields[index].text() or "").strip()
                for index, (key, _label) in enumerate(fields)
            }
            values = _detail_values_with_native_defaults(native_type, values)
            if not fields:
                self._sync_connection_points_from_table(str(row.structure_id))
                self._load_selected_detail()
                self._refresh_selected_detail_validation(str(row.structure_id), spec_ref)
                self._set_status(
                    f"Selected detail applied for {row.structure_id}. Apply the model to persist changes."
                )
                return
            if detail_family == "bridge":
                self._bridge_geometry_spec_rows = _replace_kind_spec(
                    self._bridge_geometry_spec_rows,
                    _bridge_spec_from_detail(spec_ref, values),
                )
            elif detail_family == "culvert":
                self._culvert_geometry_spec_rows = _replace_kind_spec(
                    self._culvert_geometry_spec_rows,
                    _culvert_spec_from_detail(spec_ref, values),
                )
            elif detail_family == "retaining_wall":
                self._retaining_wall_geometry_spec_rows = _replace_kind_spec(
                    self._retaining_wall_geometry_spec_rows,
                    _retaining_wall_spec_from_detail(spec_ref, values),
                )
            else:
                self._set_status(f"No kind-specific detail fields are defined for {kind or 'custom'}.")
                return
            self._derive_default_connection_points_if_empty_or_auto(row)
            self._sync_connection_points_from_table(str(row.structure_id))
            self._load_selected_detail()
            self._refresh_selected_detail_validation(str(row.structure_id), spec_ref)
            self._set_status(
                f"Selected detail applied for {row.structure_id}. Apply the model to persist changes."
            )
        except Exception as exc:
            self._set_status(f"Structure detail was not applied:\n{exc}")

    def _handle_native_type_changed(self, _index: int) -> None:
        if getattr(self, "_loading_selected_detail", False):
            return
        self._sync_selected_detail_to_row()
        row = self._current_structure_row()
        if row is None:
            return
        spec_ref = self._ensure_row_geometry_spec_ref(self._table.currentRow(), row)
        self._apply_native_type_row_defaults(self._table.currentRow(), native_type=str(self._native_type_combo.currentText() or ""))
        self._apply_native_type_common_defaults(row)
        self._load_type_specific_detail(row, spec_ref)

    def _handle_geometry_source_changed(self, _index: int) -> None:
        source_mode = str(self._geometry_source_combo.currentText() or "native")
        self._geometry_ref_field.setEnabled(source_mode != "native")
        self._pick_external_ref_button.setEnabled(source_mode != "native")
        self._native_type_combo.setEnabled(source_mode == "native")
        self._set_common_geometry_detail_enabled(source_mode == "native")
        self._sync_selected_detail_to_row()

    def _load_type_specific_detail(self, row: StructureRow, spec_ref: str) -> None:
        kind = str(row.structure_kind or "").strip().lower()
        native_type = str(getattr(row, "native_type", "") or "").strip().lower()
        detail_family = _detail_spec_family(native_type, kind)
        values = _kind_detail_values(
            detail_family,
            spec_ref,
            self._bridge_geometry_spec_rows,
            self._culvert_geometry_spec_rows,
            self._retaining_wall_geometry_spec_rows,
        )
        values = _detail_values_with_native_defaults(native_type, values)
        fields = _native_detail_field_specs(native_type, kind)
        for index, (key, label_text) in enumerate(fields):
            self._detail_labels[index].setText(label_text)
            self._detail_labels[index].show()
            self._detail_fields[index].setText(str(values.get(key, "")))
            self._detail_fields[index].show()
        for index in range(len(fields), len(self._detail_fields)):
            self._detail_labels[index].setText("")
            self._detail_labels[index].hide()
            self._detail_fields[index].setText("")
            self._detail_fields[index].hide()

    def _common_geometry_fields(self):
        return [
            self._common_shape_field,
            self._common_width_field,
            self._common_height_field,
            self._common_vertical_mode_combo,
            self._common_base_elev_field,
            self._common_top_elev_field,
            self._common_skew_field,
            self._common_material_field,
            self._common_notes_field,
        ]

    def _set_common_geometry_detail_enabled(self, enabled: bool) -> None:
        for field in self._common_geometry_fields():
            try:
                field.setEnabled(enabled)
            except Exception:
                pass

    def _load_common_geometry_detail(self, row: StructureRow | None, spec_ref: str) -> None:
        if row is None:
            self._common_shape_field.setText("")
            self._common_width_field.setText("")
            self._common_height_field.setText("")
            self._common_vertical_mode_combo.setCurrentText("profile_frame")
            self._common_base_elev_field.setText("")
            self._common_top_elev_field.setText("")
            self._common_skew_field.setText("")
            self._common_material_field.setText("")
            self._common_notes_field.setText("")
            self._set_common_geometry_detail_enabled(False)
            return
        spec = self._common_geometry_spec_for_ref(spec_ref)
        native_type = str(getattr(row, "native_type", "") or "").strip().lower()
        self._set_common_geometry_detail_enabled(_geometry_source_mode(row) == "native")
        self._common_shape_field.setText(str(getattr(spec, "shape_kind", "") or _default_shape_kind_for_native(native_type, row.structure_kind)))
        self._common_width_field.setText(_format_float(getattr(spec, "width", 0.0) or _default_geometry_width_for_native(native_type, row.structure_kind)))
        self._common_height_field.setText(_format_float(getattr(spec, "height", 0.0) or _default_geometry_height_for_native(native_type, row.structure_kind)))
        self._common_vertical_mode_combo.setCurrentText(str(getattr(spec, "vertical_position_mode", "") or "profile_frame"))
        self._common_base_elev_field.setText(_format_optional_float(getattr(spec, "base_elevation", None)))
        self._common_top_elev_field.setText(_format_optional_float(getattr(spec, "top_elevation", None)))
        self._common_skew_field.setText(_format_float(getattr(spec, "skew_angle_deg", 0.0) or 0.0))
        self._common_material_field.setText(str(getattr(spec, "material", "") or ""))
        self._common_notes_field.setText(str(getattr(spec, "notes", "") or ""))

    def _common_geometry_spec_for_ref(self, spec_ref: str) -> StructureGeometrySpec | None:
        for spec in self._geometry_spec_table_rows(allow_blank=True):
            if str(getattr(spec, "geometry_spec_id", "") or "") == str(spec_ref or ""):
                return spec
        return None

    def _sync_common_geometry_detail_to_specs(self, structure_ref: str, spec_ref: str) -> None:
        if getattr(self, "_loading_selected_detail", False):
            return
        if not structure_ref or not spec_ref or not hasattr(self, "_common_shape_field"):
            return
        row = self._current_structure_row()
        if row is None or str(getattr(row, "structure_id", "") or "") != str(structure_ref):
            row = None
            for candidate in self._table_rows():
                if str(candidate.structure_id) == str(structure_ref):
                    row = candidate
                    break
        if row is None:
            return
        existing = self._common_geometry_spec_for_ref(spec_ref)
        spec = StructureGeometrySpec(
            geometry_spec_id=spec_ref,
            structure_ref=structure_ref,
            shape_kind=str(self._common_shape_field.text() or "").strip() or _default_shape_kind_for_native(getattr(row, "native_type", ""), row.structure_kind),
            width=_required_float(str(self._common_width_field.text() or ""), "Selected Structure Detail Width"),
            height=_required_float(str(self._common_height_field.text() or ""), "Selected Structure Detail Height"),
            length_mode=str(getattr(existing, "length_mode", "") or "station_range"),
            skew_angle_deg=_required_float(str(self._common_skew_field.text() or "0"), "Selected Structure Detail Skew"),
            vertical_position_mode=str(self._common_vertical_mode_combo.currentText() or "profile_frame"),
            base_elevation=_optional_float_text(str(self._common_base_elev_field.text() or "")),
            top_elevation=_optional_float_text(str(self._common_top_elev_field.text() or "")),
            material=str(self._common_material_field.text() or "").strip(),
            style_role=str(getattr(existing, "style_role", "") or row.structure_kind),
            notes=str(self._common_notes_field.text() or "").strip(),
        )
        specs = self._geometry_spec_table_rows(allow_blank=True)
        for index, candidate in enumerate(specs):
            if str(candidate.geometry_spec_id) == str(spec_ref):
                specs[index] = spec
                self._replace_geometry_specs(specs)
                return
        specs.append(spec)
        self._replace_geometry_specs(specs)

    def _apply_native_type_common_defaults(self, row: StructureRow) -> None:
        native_type = str(self._native_type_combo.currentText() or "").strip().lower()
        if not native_type:
            return
        self._common_shape_field.setText(_default_shape_kind_for_native(native_type, row.structure_kind))
        self._common_width_field.setText(_format_float(_default_geometry_width_for_native(native_type, row.structure_kind)))
        self._common_height_field.setText(_format_float(_default_geometry_height_for_native(native_type, row.structure_kind)))

    def _apply_native_type_row_defaults(self, row_index: int, *, native_type: str) -> None:
        if row_index < 0 or row_index >= self._table.rowCount():
            return
        native = str(native_type or "").strip().lower()
        kind = _default_structure_kind_for_native(native)
        role = _default_structure_role_for_native(native)
        if kind:
            self._set_row_structure_kind(row_index, kind)
        if role:
            self._set_row_structure_role(row_index, role)

    def _set_row_structure_kind(self, row_index: int, value: str) -> None:
        self._set_row_combo_or_item_text(row_index, 1, value)

    def _set_row_structure_role(self, row_index: int, value: str) -> None:
        self._set_row_combo_or_item_text(row_index, 2, value)

    def _set_row_combo_or_item_text(self, row_index: int, col_index: int, value: str) -> None:
        widget = self._table.cellWidget(row_index, col_index)
        if widget is not None and hasattr(widget, "setCurrentText"):
            widget.setCurrentText(str(value or ""))
            return
        item = self._table.item(row_index, col_index)
        if item is None:
            item = QtWidgets.QTableWidgetItem("")
            self._table.setItem(row_index, col_index, item)
        item.setText(str(value or ""))

    def _derive_default_connection_points_if_empty_or_auto(self, row: StructureRow | None) -> None:
        if row is None or not self._connection_table_is_empty_or_auto_native():
            return
        points = _derive_default_connection_points_for_row(
            row,
            self._geometry_spec_for_structure(row),
            self._culvert_spec_for_structure(row),
        )
        if not points:
            return
        self._replace_connection_points(_mark_auto_native_connection_points(points))

    def _connection_table_is_empty_or_auto_native(self) -> bool:
        if self._connection_table.rowCount() <= 0:
            return True
        for row_index in range(self._connection_table.rowCount()):
            if "auto_native_default" not in _item_text(self._connection_table, row_index, 11):
                return False
        return True

    def _validate(self) -> None:
        try:
            model = self._model_from_table()
            self._refresh_selected_detail_validation(self._active_detail_structure_id, self._active_detail_spec_ref, model=model)
            self._set_status(_format_validation_result(model, document=self.document))
        except Exception as exc:
            self._set_status(f"Structure validation failed:\n{exc}")

    def _apply(self, *, close_after: bool = False, show_preview: bool = False) -> bool:
        try:
            model = self._model_from_table()
            diagnostics = _structure_editor_diagnostics(model, document=self.document)
            if any(str(row).startswith("error|") for row in diagnostics):
                self._set_status(_format_validation_result(model, document=self.document))
                _show_message(self.form, "Structures", "Structures were not applied because validation has errors.")
                return False
            selected_structure_id = self._current_structure_id()
            self.structure_obj = apply_v1_structure_model(document=self.document, structure_model=model)
            self._reload_existing_rows(selected_structure_id=selected_structure_id)
            preview_text = ""
            if show_preview and list(model.structure_rows or []):
                preview = show_v1_structure_preview_object(self.document, model)
                self._focus_preview_object(preview)
                preview_text = f"\n3D Preview: {preview.Label}"
            self._set_status(_format_validation_result(model, document=self.document) + f"\n\nApplied to: {self.structure_obj.Label}{preview_text}")
            _show_message(self.form, "Structures", f"Structures have been applied.\nRows: {len(model.structure_rows)}")
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(f"Structures were not applied:\n{exc}")
            _show_message(self.form, "Structures", f"Structures were not applied.\n{exc}")
            return False

    def _show_preview(self) -> None:
        try:
            model = self._model_from_table()
            diagnostics = _structure_editor_diagnostics(model, document=self.document)
            if any(str(row).startswith("error|") for row in diagnostics):
                self._set_status(_format_validation_result(model, document=self.document))
                return
            preview = show_v1_structure_preview_object(self.document, model)
            self._focus_preview_object(preview)
            self._set_status(_format_validation_result(model, document=self.document) + f"\n\n3D Preview shown: {preview.Label}")
        except Exception as exc:
            self._set_status(f"Structure preview was not shown:\n{exc}")

    def _focus_preview_object(self, preview) -> None:
        if Gui is None or preview is None:
            return
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(preview)
        except Exception:
            pass
        try:
            view = getattr(getattr(Gui, "ActiveDocument", None), "ActiveView", None)
            if view is not None and hasattr(view, "fitSelection"):
                view.fitSelection()
        except Exception:
            pass

    def _model_from_table(self) -> StructureModel:
        self._sync_selected_detail_to_row()
        if self._active_detail_structure_id:
            self._sync_common_geometry_detail_to_specs(self._active_detail_structure_id, self._active_detail_spec_ref)
            self._sync_connection_points_from_table(self._active_detail_structure_id)
        existing = to_structure_model(self.structure_obj)
        alignment = find_v1_alignment(self.document)
        structure_rows = self._table_rows()
        structure_ids = {str(row.structure_id) for row in structure_rows}
        geometry_spec_rows = [
            row
            for row in self._geometry_spec_table_rows()
            if str(getattr(row, "structure_ref", "") or "") in structure_ids
        ]
        connection_point_rows = _normalized_connection_point_rows_for_structures(
            [
                row
                for row in self._connection_point_rows
                if str(getattr(row, "structure_ref", "") or "") in structure_ids
            ],
            structure_rows,
        )
        return StructureModel(
            schema_version=1,
            project_id=_project_id(find_project(self.document)),
            structure_model_id=str(getattr(existing, "structure_model_id", "") or "structures:main"),
            alignment_id=str(getattr(existing, "alignment_id", "") or getattr(alignment, "AlignmentId", "") or ""),
            label="Structures",
            structure_rows=structure_rows,
            geometry_spec_rows=geometry_spec_rows,
            bridge_geometry_spec_rows=_filter_kind_specs(
                self._bridge_geometry_spec_rows or getattr(existing, "bridge_geometry_spec_rows", []),
                geometry_spec_rows,
            ),
            culvert_geometry_spec_rows=_filter_kind_specs(
                self._culvert_geometry_spec_rows or getattr(existing, "culvert_geometry_spec_rows", []),
                geometry_spec_rows,
            ),
            retaining_wall_geometry_spec_rows=_filter_kind_specs(
                self._retaining_wall_geometry_spec_rows or getattr(existing, "retaining_wall_geometry_spec_rows", []),
                geometry_spec_rows,
            ),
            connection_point_rows=connection_point_rows,
            interaction_rule_rows=[],
            influence_zone_rows=[],
        )

    def _table_rows(self) -> list[StructureRow]:
        rows: list[StructureRow] = []
        alignment_id = _alignment_id(self.document)
        for row_index in range(self._table.rowCount()):
            structure_id = _source_structure_ref(_item_text(self._table, row_index, 0) or f"{row_index + 1}")
            kind = _item_text(self._table, row_index, 1) or "bridge"
            role = _item_text(self._table, row_index, 2) or "interface"
            station_start = _required_float(_item_text(self._table, row_index, 3), f"Row {row_index + 1} start STA")
            station_end = _required_float(_item_text(self._table, row_index, 4), f"Row {row_index + 1} end STA")
            offset = _required_float(_item_text(self._table, row_index, 5) or "0", f"Row {row_index + 1} offset")
            geometry_ref = self._row_geometry_ref(row_index)
            geometry_source_mode = self._row_geometry_source_mode(row_index)
            rows.append(
                StructureRow(
                    structure_id=structure_id,
                    structure_kind=kind,
                    structure_role=role,
                    placement=StructurePlacement(
                        placement_id=f"placement:{row_index + 1}",
                        alignment_id=alignment_id,
                        station_start=station_start,
                        station_end=station_end,
                        offset=offset,
                        region_ref="",
                    ),
                    geometry_spec_ref=_item_user_data(self._table, row_index, 0, STRUCTURE_GEOMETRY_SPEC_REF_ROLE),
                    geometry_ref=geometry_ref,
                    reference_mode="native" if geometry_source_mode == "native" else "source_ref",
                    geometry_source_mode=geometry_source_mode,
                    native_type=self._row_native_type(row_index),
                )
            )
        return rows

    def _current_structure_id(self) -> str:
        row = self._current_structure_row()
        return str(getattr(row, "structure_id", "") or "") if row is not None else ""

    def _current_structure_row(self) -> StructureRow | None:
        row_index = self._table.currentRow()
        if row_index < 0 and self._table.selectedItems():
            row_index = self._table.selectedItems()[0].row()
        if row_index < 0 or row_index >= self._table.rowCount():
            return None
        return self._structure_row_from_table_index(row_index)

    def _structure_row_from_table_index(self, row_index: int) -> StructureRow:
        alignment_id = _alignment_id(self.document)
        structure_id = _source_structure_ref(_item_text(self._table, row_index, 0) or f"{row_index + 1}")
        kind = _item_text(self._table, row_index, 1) or "bridge"
        role = _item_text(self._table, row_index, 2) or "interface"
        station_start = _required_float(_item_text(self._table, row_index, 3), f"Row {row_index + 1} start STA")
        station_end = _required_float(_item_text(self._table, row_index, 4), f"Row {row_index + 1} end STA")
        offset = _required_float(_item_text(self._table, row_index, 5) or "0", f"Row {row_index + 1} offset")
        geometry_ref = self._row_geometry_ref(row_index)
        geometry_source_mode = self._row_geometry_source_mode(row_index)
        return StructureRow(
            structure_id=structure_id,
            structure_kind=kind,
            structure_role=role,
            placement=StructurePlacement(
                placement_id=f"placement:{row_index + 1}",
                alignment_id=alignment_id,
                station_start=station_start,
                station_end=station_end,
                offset=offset,
                region_ref="",
            ),
            geometry_spec_ref=_item_user_data(self._table, row_index, 0, STRUCTURE_GEOMETRY_SPEC_REF_ROLE),
            geometry_ref=geometry_ref,
            reference_mode="native" if geometry_source_mode == "native" else "source_ref",
            geometry_source_mode=geometry_source_mode,
            native_type=self._row_native_type(row_index),
        )

    def _select_first_structure_row(self) -> None:
        if self._table.rowCount() > 0:
            self._table.selectRow(0)
        self._load_selected_detail()

    def _select_structure_id(self, structure_id: str) -> None:
        expected = _source_structure_ref(structure_id)
        for row_index in range(self._table.rowCount()):
            if _source_structure_ref(_item_text(self._table, row_index, 0)) == expected:
                self._table.selectRow(row_index)
                return
        self._select_first_structure_row()

    def _ensure_row_geometry_spec_ref(self, row_index: int, row: StructureRow) -> str:
        spec_ref = str(getattr(row, "geometry_spec_ref", "") or "")
        if not spec_ref:
            spec_ref = f"geometry-spec:{str(row.structure_id).split(':')[-1]}"
            item = self._table.item(row_index, 0)
            if item is not None:
                item.setData(STRUCTURE_GEOMETRY_SPEC_REF_ROLE, spec_ref)
        return spec_ref

    def _row_geometry_ref(self, row_index: int) -> str:
        return _item_user_data(self._table, row_index, 0, STRUCTURE_GEOMETRY_REF_ROLE)

    def _set_row_geometry_ref(self, row_index: int, geometry_ref: str) -> None:
        item = self._table.item(row_index, 0)
        if item is not None:
            item.setData(STRUCTURE_GEOMETRY_REF_ROLE, str(geometry_ref or "").strip())

    def _row_geometry_source_mode(self, row_index: int) -> str:
        mode = _item_user_data(self._table, row_index, 0, STRUCTURE_GEOMETRY_SOURCE_ROLE)
        return mode if mode in GEOMETRY_SOURCE_CHOICES else "native"

    def _set_row_geometry_source_mode(self, row_index: int, mode: str) -> None:
        item = self._table.item(row_index, 0)
        if item is not None:
            item.setData(STRUCTURE_GEOMETRY_SOURCE_ROLE, mode if mode in GEOMETRY_SOURCE_CHOICES else "native")

    def _row_native_type(self, row_index: int) -> str:
        return _item_user_data(self._table, row_index, 0, STRUCTURE_NATIVE_TYPE_ROLE)

    def _set_row_native_type(self, row_index: int, native_type: str) -> None:
        item = self._table.item(row_index, 0)
        if item is not None:
            item.setData(STRUCTURE_NATIVE_TYPE_ROLE, str(native_type or "").strip())

    def _sync_selected_detail_to_row(self) -> None:
        row_index = self._table.currentRow()
        if row_index < 0 or row_index >= self._table.rowCount():
            return
        if getattr(self, "_loading_selected_detail", False):
            return
        if not hasattr(self, "_geometry_ref_field"):
            return
        self._set_row_geometry_source_mode(row_index, str(self._geometry_source_combo.currentText() or "native"))
        self._set_row_native_type(row_index, str(self._native_type_combo.currentText() or ""))
        self._set_row_geometry_ref(row_index, str(self._geometry_ref_field.text() or "").strip())

    def _add_or_update_common_spec_for_row(self, row: StructureRow, spec_ref: str) -> None:
        if str(row.structure_id) == str(self._active_detail_structure_id or ""):
            self._sync_common_geometry_detail_to_specs(str(row.structure_id), spec_ref)
            return
        specs = self._geometry_spec_table_rows(allow_blank=True)
        for index, spec in enumerate(specs):
            if spec.geometry_spec_id == spec_ref:
                specs[index] = StructureGeometrySpec(
                    geometry_spec_id=spec.geometry_spec_id,
                    structure_ref=row.structure_id,
                    shape_kind=spec.shape_kind or _default_shape_kind(row.structure_kind),
                    width=spec.width if spec.width > 0.0 else _default_geometry_width(row.structure_kind),
                    height=spec.height if spec.height > 0.0 else _default_geometry_height(row.structure_kind),
                    length_mode=spec.length_mode,
                    skew_angle_deg=spec.skew_angle_deg,
                    vertical_position_mode=spec.vertical_position_mode,
                    base_elevation=spec.base_elevation,
                    top_elevation=spec.top_elevation,
                    material=spec.material,
                    style_role=spec.style_role or row.structure_kind,
                    notes=spec.notes,
                )
                self._replace_geometry_specs(specs)
                return
        specs.append(
            StructureGeometrySpec(
                geometry_spec_id=spec_ref,
                structure_ref=row.structure_id,
                shape_kind=_default_shape_kind(row.structure_kind),
                width=_default_geometry_width(row.structure_kind),
                height=_default_geometry_height(row.structure_kind),
                length_mode="station_range",
                vertical_position_mode="profile_frame",
                style_role=row.structure_kind,
            )
        )
        self._replace_geometry_specs(specs)

    def _geometry_spec_table_rows(self, *, allow_blank: bool = False) -> list[StructureGeometrySpec]:
        rows: list[StructureGeometrySpec] = []
        for row_index in range(self._geometry_table.rowCount()):
            geometry_spec_id = _item_text(self._geometry_table, row_index, 0) or f"geometry-spec:{row_index + 1}"
            structure_ref = _item_text(self._geometry_table, row_index, 1)
            if not allow_blank and not structure_ref:
                raise ValueError(f"Geometry Spec row {row_index + 1} Structure Ref is required.")
            rows.append(
                StructureGeometrySpec(
                    geometry_spec_id=geometry_spec_id,
                    structure_ref=structure_ref,
                    shape_kind=_item_text(self._geometry_table, row_index, 2),
                    width=_required_float(_item_text(self._geometry_table, row_index, 3) or "0", f"Geometry Spec row {row_index + 1} width"),
                    height=_required_float(_item_text(self._geometry_table, row_index, 4) or "0", f"Geometry Spec row {row_index + 1} height"),
                    length_mode=_item_text(self._geometry_table, row_index, 5) or "station_range",
                    skew_angle_deg=_required_float(_item_text(self._geometry_table, row_index, 6) or "0", f"Geometry Spec row {row_index + 1} skew"),
                    vertical_position_mode=_item_text(self._geometry_table, row_index, 7) or "profile_frame",
                    base_elevation=_optional_float_text(_item_text(self._geometry_table, row_index, 8)),
                    top_elevation=_optional_float_text(_item_text(self._geometry_table, row_index, 9)),
                    material=_item_text(self._geometry_table, row_index, 10),
                    notes=_item_text(self._geometry_table, row_index, 11),
                )
            )
        return rows

    def _refresh_selected_detail_validation(
        self,
        structure_ref: str,
        spec_ref: str = "",
        *,
        model: StructureModel | None = None,
    ) -> None:
        structure_ref = str(structure_ref or "").strip()
        if not structure_ref:
            self._set_detail_validation("Selected validation: not available", status="none")
            return
        try:
            model = model or self._model_from_table()
            diagnostics = _selected_structure_diagnostics(model, structure_ref, spec_ref, document=self.document)
            if not diagnostics:
                self._set_detail_validation("Selected validation: ok", status="ok")
                return
            status = "error" if any(str(row).startswith("error|") for row in diagnostics) else "warning"
            shown = diagnostics[:4]
            suffix = "" if len(diagnostics) <= len(shown) else f"; +{len(diagnostics) - len(shown)} more"
            self._set_detail_validation(
                "Selected validation: "
                + status
                + "\n"
                + "\n".join(str(row) for row in shown)
                + suffix,
                status=status,
            )
        except Exception as exc:
            self._set_detail_validation(f"Selected validation: error\n{exc}", status="error")


__all__ = [
    "StructureEditorTaskPanelPresentation",
    "V1StructureEditorTaskPanel",
    "configure_structure_editor_task_panel_runtime",
]

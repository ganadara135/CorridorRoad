"""SubAssembly Designer presentation for CorridorRoad v1."""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets


def configure_sub_assembly_designer_task_panel_runtime(bindings) -> None:
    """Bind command/controller collaborators without importing the command module."""

    protected = {
        "V1SubAssemblyDesignerTaskPanel",
        "_DefinitionTableComboBox",
        "_ZoomablePreviewView",
        "configure_sub_assembly_designer_task_panel_runtime",
    }
    for name, value in dict(bindings or {}).items():
        if name.startswith("__") or name in protected:
            continue
        globals()[name] = value


# Explicit runtime collaborators are replaced by the command callback map.
App = None
DEFINITION_COLUMNS = None
Gui = None
LINK_COLUMNS = None
PARAMETER_COLUMNS = None
POINT_COLUMNS = None
SHAPE_COLUMNS = None
SUBASSEMBLY_DESIGNER_CATEGORY_VALUES = None
SUBASSEMBLY_DESIGNER_ENABLED_VALUES = None
SUBASSEMBLY_DESIGNER_KIND_VALUES = None
SUBASSEMBLY_DESIGNER_MATERIAL_VALUES = None
SUBASSEMBLY_DESIGNER_SIDE_VALUES = None
SubassemblyDefinition = None
SubassemblyDefinitionValidationService = None
SubassemblyExpressionService = None
SubassemblyLibrary = None
TARGET_COLUMNS = None
_append_table_row = None
_assembly_subassembly_row_labels = None
_bench_rows_preview_hint = None
_confirm_action = None
_decorate_parameter_row = None
_definition_count_columns = None
_definition_from_subassembly_preset = None
_designer_assembly_rows_referencing_preset = None
_designer_has_assembly_object = None
_designer_preset_by_id = None
_designer_preset_difference_keys = None
_designer_preset_history_text = None
_designer_preset_library_rows = None
_designer_preset_library_summary_text = None
_diagnostic_summary = None
_first_preset_name = None
_link_rows_from_table = None
_new_table = None
_parameter_rows_from_table = None
_point_rows_from_table = None
_preset_id_from_definition = None
_preview_pen_for_link = None
_project_id = None
_read_only_flags = None
_selected_assembly_subassembly_id = None
_shape_rows_from_table = None
_shared_template_update_choice = None
_show_message = None
_style_definition_count_item = None
_surface_role_preview_hint = None
_table_text = None
_target_rows_from_table = None
_truthy = None
apply_clickable_tab_style = None
apply_v1_subassembly_definition_to_active_assembly = None
apply_v1_subassembly_library = None
delete_v1_subassembly_preset = None
detach_v1_active_assembly_subassembly_as_custom = None
duplicate_v1_subassembly_preset = None
find_project = None
find_v1_subassembly_library = None
load_v1_subassembly_definition_from_active_assembly = None
rename_v1_subassembly_preset = None
save_v1_subassembly_definition_as_new_preset = None
subassembly_definition_library_from_preset = None
subassembly_definition_preset_names = None
to_subassembly_library = None
update_v1_subassembly_preset_from_definition = None


class V1SubAssemblyDesignerTaskPanel:
    """First-slice SubAssembly Designer source panel."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.library_obj = find_v1_subassembly_library(self.document)
        self.library_model = to_subassembly_library(self.library_obj) if self.library_obj is not None else None
        if self.library_model is None:
            self.library_model = subassembly_definition_library_from_preset(
                _first_preset_name(),
                project_id=_project_id(find_project(self.document)),
            )
        self._active_definition_index: int | None = None
        self._locked_definition_index: int | None = None
        self._allow_definition_selection_change = False
        self._loading = False
        self.form = self._build_form()
        self._load_model(self.library_model)

    def getStandardButtons(self):  # noqa: N802 - Qt API name
        return 0

    def accept(self):  # noqa: D401 - FreeCAD task panel API
        """Accept the panel."""

        return True

    def reject(self):  # noqa: D401 - FreeCAD task panel API
        """Close the panel."""

        return True

    def _build_form(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        title = QtWidgets.QLabel("SubAssembly Designer")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        description = QtWidgets.QLabel(
            "Define reusable Subassembly source definitions. Assembly places these definitions in station-based templates."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Starter:"))
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItems(subassembly_definition_preset_names())
        preset_row.addWidget(self.preset_combo, 1)
        self.load_preset_button = QtWidgets.QPushButton("Load Preset")
        self.load_preset_button.clicked.connect(self._load_selected_preset)
        preset_row.addWidget(self.load_preset_button)
        self.load_existing_button = QtWidgets.QPushButton("Load Existing")
        self.load_existing_button.clicked.connect(self._load_existing)
        preset_row.addWidget(self.load_existing_button)
        layout.addLayout(preset_row)

        self.assembly_row_widget = QtWidgets.QWidget()
        assembly_row_layout = QtWidgets.QVBoxLayout(self.assembly_row_widget)
        assembly_row_layout.setContentsMargins(0, 0, 0, 0)
        assembly_row_layout.setSpacing(6)
        assembly_row = QtWidgets.QHBoxLayout()
        assembly_row.addWidget(QtWidgets.QLabel("Assembly Row:"))
        self.assembly_row_combo = QtWidgets.QComboBox()
        self.assembly_row_combo.addItems(_assembly_subassembly_row_labels(self.document))
        self.assembly_row_combo.currentIndexChanged.connect(lambda _index: self._refresh_save_target_label())
        assembly_row.addWidget(self.assembly_row_combo, 1)
        assembly_row.addStretch(1)
        assembly_row_layout.addLayout(assembly_row)

        assembly_load_row = QtWidgets.QHBoxLayout()
        assembly_load_row.addSpacing(110)
        self.refresh_assembly_rows_button = QtWidgets.QPushButton("Refresh Rows")
        self.refresh_assembly_rows_button.clicked.connect(self._refresh_assembly_rows)
        assembly_load_row.addWidget(self.refresh_assembly_rows_button)
        self.load_from_assembly_button = QtWidgets.QPushButton("Load Row")
        self.load_from_assembly_button.clicked.connect(self._load_from_assembly)
        assembly_load_row.addWidget(self.load_from_assembly_button)
        self.apply_to_assembly_button = QtWidgets.QPushButton("Save Changes")
        self.apply_to_assembly_button.setToolTip("Save current edits to the selected Assembly row when available; otherwise save the SubAssembly library source.")
        self.apply_to_assembly_button.clicked.connect(self._save_changes)
        assembly_load_row.addWidget(self.apply_to_assembly_button)
        self.save_as_preset_button = QtWidgets.QPushButton("Save as Reusable Subassembly Template")
        self.save_as_preset_button.setToolTip("Create a reusable template from the selected Subassembly definition.")
        self.save_as_preset_button.clicked.connect(self._save_as_new_preset)
        assembly_load_row.addWidget(self.save_as_preset_button)
        assembly_load_row.addStretch(1)
        assembly_row_layout.addLayout(assembly_load_row)
        self.assembly_row_widget.setVisible(_designer_has_assembly_object(self.document))
        layout.addWidget(self.assembly_row_widget)

        self.preset_state_label = QtWidgets.QLabel("Editing Source: Snapshot")
        self.preset_state_label.setWordWrap(True)
        self._set_preset_state("Editing Source: Snapshot. Load an Assembly row or save changes to persist edits.", "snapshot")
        layout.addWidget(self.preset_state_label)
        self.save_target_label = QtWidgets.QLabel("Save target: SubAssembly library source")
        self.save_target_label.setWordWrap(True)
        self.save_target_label.setToolTip("Shows where Save Changes will write the current edits.")
        self.save_target_label.setStyleSheet(
            "QLabel {"
            "background: #202936;"
            "color: #d8e0ea;"
            "border: 1px solid #435066;"
            "border-left: 4px solid #6f7f95;"
            "border-radius: 4px;"
            "padding: 4px 6px;"
            "}"
        )
        layout.addWidget(self.save_target_label)
        self._refresh_save_target_label()
        self.changed_fields_label = QtWidgets.QLabel("Changed fields: 0")
        self.changed_fields_label.setWordWrap(True)
        self.changed_fields_label.setToolTip("Counts cells locally edited in this Designer session.")
        self.changed_fields_label.setStyleSheet(
            "QLabel {"
            "background: #202936;"
            "color: #f3d36b;"
            "border: 1px solid #435066;"
            "border-left: 4px solid #c79a2a;"
            "border-radius: 4px;"
            "padding: 4px 6px;"
            "}"
        )
        layout.addWidget(self.changed_fields_label)
        self.preset_differences_label = QtWidgets.QLabel("Subassembly Template differences: n/a")
        self.preset_differences_label.setWordWrap(True)
        self.preset_differences_label.setToolTip("Counts current values that differ from the matching reusable Subassembly template defaults.")
        self.preset_differences_label.setStyleSheet(
            "QLabel {"
            "background: #202936;"
            "color: #9cc8f2;"
            "border: 1px solid #435066;"
            "border-left: 4px solid #4d8ed8;"
            "border-radius: 4px;"
            "padding: 4px 6px;"
            "}"
        )
        layout.addWidget(self.preset_differences_label)

        self.advanced_template_toggle = QtWidgets.QPushButton("Show Advanced Subassembly Template Library")
        self.advanced_template_toggle.setCheckable(True)
        self.advanced_template_toggle.setToolTip("Show optional shared template library management actions.")
        self.advanced_template_toggle.toggled.connect(self._toggle_advanced_template_library)
        layout.addWidget(self.advanced_template_toggle)

        self.advanced_template_widget = QtWidgets.QWidget()
        advanced_template_layout = QtWidgets.QVBoxLayout(self.advanced_template_widget)
        advanced_template_layout.setContentsMargins(0, 0, 0, 0)
        self.preset_library_summary_label = QtWidgets.QLabel(_designer_preset_library_summary_text(self.document))
        self.preset_library_summary_label.setWordWrap(True)
        self.preset_library_summary_label.setToolTip(
            "Advanced reusable Subassembly template library summary."
        )
        self.preset_library_summary_label.setStyleSheet(
            "QLabel {"
            "background: #202936;"
            "color: #d8e0ea;"
            "border: 1px solid #435066;"
            "border-left: 4px solid #6f7f95;"
            "border-radius: 4px;"
            "padding: 4px 6px;"
            "}"
        )
        advanced_template_layout.addWidget(self.preset_library_summary_label)
        self.advanced_template_warning_label = QtWidgets.QLabel(
            "Shared Reusable Subassembly Template changes may affect Assembly rows that reference the template after refresh/rebuild."
        )
        self.advanced_template_warning_label.setWordWrap(True)
        self.advanced_template_warning_label.setStyleSheet(
            "QLabel {"
            "background: #302b1c;"
            "color: #f2d38a;"
            "border: 1px solid #7f6427;"
            "border-left: 4px solid #d9a441;"
            "border-radius: 4px;"
            "padding: 4px 6px;"
            "}"
        )
        advanced_template_layout.addWidget(self.advanced_template_warning_label)
        self.preset_library_table = QtWidgets.QTableWidget(0, 6)
        self.preset_library_table.setHorizontalHeaderLabels(("Preset ID", "Version", "Kind", "Definition Ref", "Name", "History"))
        self.preset_library_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.preset_library_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.preset_library_table.setMaximumHeight(124)
        self.preset_library_table.horizontalHeader().setStretchLastSection(True)
        self.preset_library_table.setToolTip("Advanced read-only reusable Subassembly template list. Use Edit Selected Subassembly Template to load one into the editable tables above.")
        advanced_template_layout.addWidget(self.preset_library_table)
        preset_library_button_row = QtWidgets.QHBoxLayout()
        self.edit_preset_button = QtWidgets.QPushButton("Edit Selected Subassembly Template")
        self.edit_preset_button.setToolTip("Load the selected reusable Subassembly template into the editable Definition tables above. Use Update Shared Subassembly Template to persist changes.")
        self.edit_preset_button.clicked.connect(self._edit_selected_preset)
        preset_library_button_row.addWidget(self.edit_preset_button)
        self.update_preset_button = QtWidgets.QPushButton("Update Shared Subassembly Template")
        self.update_preset_button.setToolTip("Update the selected shared template from the current definition after confirmation.")
        self.update_preset_button.clicked.connect(self._update_preset)
        preset_library_button_row.addWidget(self.update_preset_button)
        self.duplicate_preset_button = QtWidgets.QPushButton("Duplicate Selected Preset")
        self.duplicate_preset_button.setToolTip("Create a new reusable Subassembly template by copying the selected template row.")
        self.duplicate_preset_button.clicked.connect(self._duplicate_selected_preset)
        preset_library_button_row.addWidget(self.duplicate_preset_button)
        self.rename_preset_button = QtWidgets.QPushButton("Rename Selected Preset")
        self.rename_preset_button.setToolTip("Rename the selected preset id and update Assembly rows that reference it.")
        self.rename_preset_button.clicked.connect(self._rename_selected_preset)
        preset_library_button_row.addWidget(self.rename_preset_button)
        self.delete_preset_button = QtWidgets.QPushButton("Delete Selected Preset")
        self.delete_preset_button.setToolTip(
            "Delete the selected preset from the project library. Assembly rows that reference it will report missing_preset."
        )
        self.delete_preset_button.clicked.connect(self._delete_selected_preset)
        preset_library_button_row.addWidget(self.delete_preset_button)
        self.detach_custom_button = QtWidgets.QPushButton("Detach as Custom")
        self.detach_custom_button.setToolTip("Keep the active Assembly row independent from reusable template updates.")
        self.detach_custom_button.clicked.connect(self._detach_as_custom)
        preset_library_button_row.addWidget(self.detach_custom_button)
        preset_library_button_row.addStretch(1)
        advanced_template_layout.addLayout(preset_library_button_row)
        self.advanced_template_widget.setVisible(False)
        layout.addWidget(self.advanced_template_widget)
        self._refresh_preset_library_summary()

        ids_row = QtWidgets.QHBoxLayout()
        ids_row.addWidget(QtWidgets.QLabel("Library ID:"))
        self.library_id_edit = QtWidgets.QLineEdit()
        self.library_id_edit.setReadOnly(True)
        ids_row.addWidget(self.library_id_edit, 1)
        ids_row.addWidget(QtWidgets.QLabel("Definitions:"))
        self.definition_count_label = QtWidgets.QLabel("0")
        ids_row.addWidget(self.definition_count_label)
        layout.addLayout(ids_row)

        self.table = QtWidgets.QTableWidget(0, len(DEFINITION_COLUMNS))
        self.table.setHorizontalHeaderLabels(DEFINITION_COLUMNS)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget {"
            "background-color: #1b2230;"
            "alternate-background-color: #202938;"
            "color: #f0f4fa;"
            "gridline-color: #3f4b60;"
            "selection-background-color: #4aa0ec;"
            "selection-color: #ffffff;"
            "}"
            "QTableWidget::item {"
            "background-color: transparent;"
            "color: #f0f4fa;"
            "}"
            "QTableWidget::item:selected {"
            "background-color: #4aa0ec;"
            "color: #ffffff;"
            "}"
        )
        try:
            self.table.setMouseTracking(False)
            self.table.viewport().setMouseTracking(False)
            self.table.viewport().setAttribute(QtCore.Qt.WA_Hover, False)
        except Exception:
            pass
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellPressed.connect(self._definition_row_pressed)
        self.table.currentCellChanged.connect(self._definition_current_cell_changed)
        self.table.itemSelectionChanged.connect(self._definition_selection_changed)
        self.table.itemChanged.connect(self._definition_table_changed)
        layout.addWidget(self.table, 1)

        self.detail_group = QtWidgets.QGroupBox("Selected Definition Detail")
        detail_layout = QtWidgets.QVBoxLayout(self.detail_group)
        self.detail_summary = QtWidgets.QLabel("Select a Subassembly definition row.")
        self.detail_summary.setWordWrap(True)
        detail_layout.addWidget(self.detail_summary)

        detail_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        detail_table_panel = QtWidgets.QWidget()
        detail_table_layout = QtWidgets.QVBoxLayout(detail_table_panel)
        detail_table_layout.setContentsMargins(0, 0, 0, 0)

        self.detail_tabs = QtWidgets.QTabWidget()
        apply_clickable_tab_style(self.detail_tabs, "SubassemblyDesignerDetailTabs")
        self.parameter_table = _new_table(PARAMETER_COLUMNS)
        self.point_table = _new_table(POINT_COLUMNS)
        self.link_table = _new_table(LINK_COLUMNS)
        self.shape_table = _new_table(SHAPE_COLUMNS)
        self.target_table = _new_table(TARGET_COLUMNS)
        for detail_table in (
            self.parameter_table,
            self.point_table,
            self.link_table,
            self.shape_table,
            self.target_table,
        ):
            detail_table.itemChanged.connect(self._detail_table_changed)
        self.preview_widget = self._build_preview_widget()
        self.diagnostics_widget = self._build_diagnostics_widget()
        self.detail_tabs.addTab(self.parameter_table, "Parameters")
        self.detail_tabs.addTab(self.point_table, "Points")
        self.detail_tabs.addTab(self.link_table, "Links")
        self.detail_tabs.addTab(self.shape_table, "Shapes")
        self.detail_tabs.addTab(self.target_table, "Targets")
        self.detail_tabs.addTab(self.diagnostics_widget, "Diagnostics")
        detail_table_layout.addWidget(self.detail_tabs, 1)

        detail_buttons = QtWidgets.QHBoxLayout()
        self.add_detail_row_button = QtWidgets.QPushButton("Add Row")
        self.add_detail_row_button.clicked.connect(self._add_detail_row)
        detail_buttons.addWidget(self.add_detail_row_button)
        self.delete_detail_row_button = QtWidgets.QPushButton("Delete Selected")
        self.delete_detail_row_button.clicked.connect(self._delete_detail_row)
        detail_buttons.addWidget(self.delete_detail_row_button)
        detail_buttons.addStretch(1)
        detail_table_layout.addLayout(detail_buttons)

        detail_splitter.addWidget(detail_table_panel)
        detail_splitter.addWidget(self.preview_widget)
        try:
            detail_splitter.setStretchFactor(0, 3)
            detail_splitter.setStretchFactor(1, 2)
            detail_splitter.setSizes([620, 420])
        except Exception:
            pass
        detail_layout.addWidget(detail_splitter, 1)
        layout.addWidget(self.detail_group, 2)

        self.status_text = QtWidgets.QPlainTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(86)
        layout.addWidget(self.status_text)

        button_row = QtWidgets.QHBoxLayout()
        self.add_definition_button = QtWidgets.QPushButton("Add Definition")
        self.add_definition_button.clicked.connect(self._add_definition)
        button_row.addWidget(self.add_definition_button)
        self.duplicate_definition_button = QtWidgets.QPushButton("Duplicate")
        self.duplicate_definition_button.clicked.connect(self._duplicate_definition)
        button_row.addWidget(self.duplicate_definition_button)
        self.delete_definition_button = QtWidgets.QPushButton("Delete Selected")
        self.delete_definition_button.clicked.connect(self._delete_definition)
        button_row.addWidget(self.delete_definition_button)
        self.validate_button = QtWidgets.QPushButton("Validate")
        self.validate_button.clicked.connect(self._validate_current_library)
        button_row.addWidget(self.validate_button)
        button_row.addStretch(1)
        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.clicked.connect(self._apply)
        button_row.addWidget(self.apply_button)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self._close)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)
        return widget

    def _build_preview_widget(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        title_row = QtWidgets.QHBoxLayout()
        preview_title = QtWidgets.QLabel("Live Preview")
        preview_title.setStyleSheet("font-weight: 600;")
        title_row.addWidget(preview_title)
        title_row.addStretch(1)
        self.auto_preview_checkbox = QtWidgets.QCheckBox("Auto Preview")
        self.auto_preview_checkbox.setChecked(True)
        self.auto_preview_checkbox.toggled.connect(self._auto_preview_toggled)
        title_row.addWidget(self.auto_preview_checkbox)
        layout.addLayout(title_row)
        self.preview_scene = QtWidgets.QGraphicsScene()
        self.preview_view = _ZoomablePreviewView(self.preview_scene)
        try:
            self.preview_view.setRenderHint(QtGui.QPainter.Antialiasing, True)
        except Exception:
            pass
        self.preview_view.setMinimumHeight(360)
        layout.addWidget(self.preview_view, 1)
        preview_buttons = QtWidgets.QHBoxLayout()
        self.refresh_preview_button = QtWidgets.QPushButton("Refresh Preview")
        self.refresh_preview_button.clicked.connect(self._refresh_preview)
        preview_buttons.addWidget(self.refresh_preview_button)
        self.preview_status = QtWidgets.QLabel("Select a definition and refresh preview.")
        self.preview_status.setWordWrap(True)
        preview_buttons.addWidget(self.preview_status, 1)
        layout.addLayout(preview_buttons)
        return widget

    def _build_diagnostics_widget(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.diagnostics_table = QtWidgets.QTableWidget(0, 4)
        self.diagnostics_table.setHorizontalHeaderLabels(("Severity", "Kind", "Message", "Notes"))
        self.diagnostics_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.diagnostics_table.setAlternatingRowColors(True)
        self.diagnostics_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.diagnostics_table, 1)
        self.diagnostics_status = QtWidgets.QLabel("Run Validate to review Subassembly definition diagnostics.")
        self.diagnostics_status.setWordWrap(True)
        layout.addWidget(self.diagnostics_status)
        return widget

    def _load_model(self, library_model: SubassemblyLibrary) -> None:
        self._loading = True
        self._active_definition_index = None
        self.library_model = library_model
        self.library_id_edit.setText(str(getattr(library_model, "library_id", "") or ""))
        rows = list(getattr(library_model, "definition_rows", []) or [])
        self.definition_count_label.setText(str(len(rows)))
        self.table.setRowCount(0)
        for definition in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (
                definition.definition_id,
                definition.name,
                definition.kind,
                definition.category,
                definition.side_behavior,
                len(definition.parameter_rows),
                len(definition.point_rows),
                len(definition.link_rows),
                len(definition.shape_rows),
                len(definition.target_rows),
                "Yes" if definition.enabled else "No",
                definition.notes,
            )
            for column, value in enumerate(values):
                if column == 2:
                    self._set_definition_combo(row, column, SUBASSEMBLY_DESIGNER_KIND_VALUES, str(value))
                elif column == 3:
                    self._set_definition_combo(row, column, SUBASSEMBLY_DESIGNER_CATEGORY_VALUES, str(value))
                elif column == 4:
                    self._set_definition_combo(row, column, SUBASSEMBLY_DESIGNER_SIDE_VALUES, str(value))
                elif column == 10:
                    self._set_definition_combo(row, column, SUBASSEMBLY_DESIGNER_ENABLED_VALUES, str(value or "Yes"))
                else:
                    item = QtWidgets.QTableWidgetItem(str(value))
                    if column in _definition_count_columns():
                        item.setFlags(_read_only_flags(item))
                        _style_definition_count_item(item)
                    self.table.setItem(row, column, item)
        self._loading = False
        if rows:
            self.table.selectRow(0)
        else:
            self._load_detail(None)
        self._set_status(
            f"Loaded Subassembly library: {library_model.library_id}\n"
            f"Starter: {library_model.preset_name or '-'}\n"
            "Definition editing is enabled. Apply persists the source library object."
        )

    def _load_selected_preset(self) -> None:
        preset_name = str(self.preset_combo.currentText() or "").strip() or _first_preset_name()
        self._load_model(
            subassembly_definition_library_from_preset(
                preset_name,
                project_id=_project_id(find_project(self.document)),
            )
        )
        self._set_preset_state(f"Editing Source: Snapshot. Loaded definition starter template '{preset_name}'.", "snapshot")
        self._clear_changed_field_markers()

    def _set_definition_combo(self, row: int, column: int, values: tuple[str, ...], current: str) -> None:
        combo = _DefinitionTableComboBox(self.table, row)
        combo.addItems(list(values))
        current_text = str(current or "").strip()
        index = combo.findText(current_text)
        if index < 0 and current_text:
            combo.addItem(current_text)
            index = combo.findText(current_text)
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.currentTextChanged.connect(lambda _value: self._definition_table_changed())
        self.table.setCellWidget(row, column, combo)

    def _set_detail_combo(self, table, row: int, column: int, values: tuple[str, ...], current: str) -> None:
        combo = _DefinitionTableComboBox(table, row)
        combo.addItems(list(values))
        current_text = str(current or "").strip()
        index = combo.findText(current_text)
        if index < 0 and current_text:
            combo.addItem(current_text)
            index = combo.findText(current_text)
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.currentTextChanged.connect(lambda _value: self._detail_table_changed())
        table.setCellWidget(row, column, combo)

    def _load_existing(self) -> None:
        obj = find_v1_subassembly_library(self.document)
        model = to_subassembly_library(obj) if obj is not None else None
        if model is None:
            self._set_status("No existing Subassembly library object was found in the active document.")
            return
        self.library_obj = obj
        self._load_model(model)

    def _load_from_assembly(self) -> None:
        self._save_active_definition_detail()
        definition = load_v1_subassembly_definition_from_active_assembly(
            document=self.document,
            subassembly_id=_selected_assembly_subassembly_id(self.assembly_row_combo),
        )
        if definition is None:
            message = "No Assembly/Subassembly row with a reusable definition was found."
            self._set_preset_state("Editing Source: Missing. No reusable Assembly/Subassembly row was found.", "missing")
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        rows = list(getattr(self.library_model, "definition_rows", []) or [])
        replace_index = None
        for index, row in enumerate(rows):
            if str(getattr(row, "definition_id", "") or "") == str(definition.definition_id):
                replace_index = index
                break
        if replace_index is None:
            rows.append(definition)
            replace_index = len(rows) - 1
        else:
            rows[replace_index] = definition
        self.library_model.definition_rows = rows
        self._load_model(self.library_model)
        self._restore_definition_selection(replace_index)
        self._active_definition_index = replace_index
        self._load_detail(definition)
        self._set_status(
            f"Loaded Assembly Subassembly into Designer.\n"
            f"Definition: {definition.definition_id}\n"
            "Status: Modified from Assembly instance until Save Changes persists it."
        )
        self._set_preset_state(
            f"Editing Source: Modified. Loaded {definition.definition_id} from Assembly; use Save Changes to persist edits.",
            "modified",
        )

    def _apply_to_assembly(self) -> None:
        self._save_active_definition_detail()
        definition = self._selected_definition()
        if definition is None:
            message = "Select a Subassembly definition before applying it to Assembly."
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        obj = apply_v1_subassembly_definition_to_active_assembly(
            document=self.document,
            project=find_project(self.document),
            definition=definition,
            subassembly_id=_selected_assembly_subassembly_id(self.assembly_row_combo),
        )
        message = (
            "SubAssembly definition applied to Assembly.\n"
            f"Definition: {definition.definition_id}\n"
            f"Assembly object: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')}"
        )
        self._set_status(message)
        self._set_preset_state(
            f"Editing Source: Saved. Applied {definition.definition_id} back to the selected Assembly row.",
            "linked",
        )
        _show_message(self.form, "SubAssembly Designer", message)

    def _save_changes(self) -> None:
        if _designer_has_assembly_object(self.document):
            self._apply_to_assembly()
            return
        self._apply()

    def _toggle_advanced_template_library(self, checked: bool) -> None:
        widget = getattr(self, "advanced_template_widget", None)
        if widget is not None:
            widget.setVisible(bool(checked))
        button = getattr(self, "advanced_template_toggle", None)
        if button is not None:
            button.setText(
                "Hide Advanced Subassembly Template Library"
                if checked
                else "Show Advanced Subassembly Template Library"
            )

    def _refresh_assembly_rows(self) -> None:
        row_widget = getattr(self, "assembly_row_widget", None)
        if row_widget is not None:
            row_widget.setVisible(_designer_has_assembly_object(self.document))
        current = _selected_assembly_subassembly_id(self.assembly_row_combo)
        self.assembly_row_combo.clear()
        self.assembly_row_combo.addItems(_assembly_subassembly_row_labels(self.document))
        if current:
            for index in range(self.assembly_row_combo.count()):
                if str(self.assembly_row_combo.itemText(index) or "").split("|", 1)[0].strip() == current:
                    self.assembly_row_combo.setCurrentIndex(index)
                    break
        self._refresh_save_target_label()
        self._set_status("Assembly row list refreshed.")

    def _save_as_new_preset(self) -> None:
        self._save_active_definition_detail()
        definition = self._selected_definition()
        if definition is None:
            message = "Select a Subassembly definition before saving it as a preset."
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        obj = save_v1_subassembly_definition_as_new_preset(
            document=self.document,
            project=find_project(self.document),
            definition=definition,
        )
        count = int(getattr(obj, "SubassemblyPresetCount", 0) or 0)
        message = (
            "SubAssembly definition saved as a new Reusable Subassembly Template.\n"
            f"Definition: {definition.definition_id}\n"
            f"Project presets: {count}"
        )
        self._set_status(message)
        self._set_preset_state(
            f"Editing Source: Reusable Subassembly Template. Saved {definition.definition_id} as a reusable project template.",
            "linked",
        )
        self._refresh_preset_library_summary()
        self._clear_changed_field_markers()
        _show_message(self.form, "SubAssembly Designer", message)

    def _update_preset(self) -> None:
        self._save_active_definition_detail()
        definition = self._selected_definition()
        if definition is None:
            message = "Select a Subassembly definition before updating a preset."
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        preset_id = _preset_id_from_definition(definition)
        affected = _designer_assembly_rows_referencing_preset(self.document, preset_id)
        affected_text = ", ".join(affected[:8]) + (f", +{len(affected) - 8} more" if len(affected) > 8 else "")
        choice = _shared_template_update_choice(
            self.form,
            "Update Shared Subassembly Template",
            "This Reusable Subassembly Template may be used by other Assembly rows.\n\n"
            f"Template: {preset_id}\n"
            f"Affected Assembly rows: {len(affected)}"
            + (f"\n{affected_text}" if affected_text else "")
            + "\n\nUpdate the shared Subassembly Template, or save these edits as a custom copy?",
        )
        if choice == "cancel":
            return
        if choice == "copy":
            self._save_as_new_preset()
            return
        try:
            obj = update_v1_subassembly_preset_from_definition(
                document=self.document,
                project=find_project(self.document),
                definition=definition,
            )
        except Exception as exc:
            message = str(exc)
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        message = (
            "SubAssembly preset updated.\n"
            f"Definition: {definition.definition_id}\n"
            f"Preset library: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')}"
        )
        self._set_status(message)
        self._set_preset_state(
            f"Editing Source: Shared Template Updated. Updated shared Subassembly template for {definition.definition_id}; dependent Assemblies may become outdated.",
            "linked",
        )
        self._refresh_preset_library_summary()
        self._clear_changed_field_markers()
        _show_message(self.form, "SubAssembly Designer", message)

    def _detach_as_custom(self) -> None:
        try:
            obj = detach_v1_active_assembly_subassembly_as_custom(
                document=self.document,
                project=find_project(self.document),
            )
        except Exception as exc:
            message = str(exc)
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        message = (
            "Active Assembly Subassembly detached as custom snapshot.\n"
            f"Assembly object: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')}"
        )
        self._set_status(message)
        self._set_preset_state("Editing Source: Custom Snapshot. Active Assembly Subassembly is independent from reusable template updates.", "snapshot")
        _show_message(self.form, "SubAssembly Designer", message)

    def _edit_selected_preset(self) -> None:
        preset_id = self._selected_preset_library_id()
        if not preset_id:
            message = "Select a Reusable Subassembly Template row before editing it."
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        preset = _designer_preset_by_id(self.document, preset_id)
        if preset is None:
            message = f"Preset was not found: {preset_id}"
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        self._save_active_definition_detail()
        definition = _definition_from_subassembly_preset(preset)
        rows = list(getattr(self.library_model, "definition_rows", []) or [])
        replace_index = None
        for index, row in enumerate(rows):
            if str(getattr(row, "definition_id", "") or "") == str(definition.definition_id):
                replace_index = index
                break
        if replace_index is None:
            rows.append(definition)
            replace_index = len(rows) - 1
        else:
            rows[replace_index] = definition
        self.library_model.definition_rows = rows
        self._load_model(self.library_model)
        self._restore_definition_selection(replace_index)
        self._active_definition_index = replace_index
        self._load_detail(definition)
        self._set_status(
            "Loaded selected Reusable Subassembly Template into the editable Definition tables.\n"
            f"Template: {preset_id}\n"
            "Edit the Definition/Detail tables above, then use Update Shared Subassembly Template to persist changes."
        )
        self._set_preset_state(
            f"Editing Source: Shared Template. Editing project template {preset_id}; use Update Shared Subassembly Template to persist edits.",
            "linked",
        )
        self._clear_changed_field_markers()

    def _duplicate_selected_preset(self) -> None:
        preset_id = self._selected_preset_library_id()
        if not preset_id:
            message = "Select a Reusable Subassembly Template row before duplicating it."
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        try:
            obj = duplicate_v1_subassembly_preset(
                document=self.document,
                project=find_project(self.document),
                preset_id=preset_id,
            )
        except Exception as exc:
            message = str(exc)
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        self._refresh_preset_library_summary()
        message = (
            "SubAssembly preset duplicated.\n"
            f"Source preset: {preset_id}\n"
            f"Preset library: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')}"
        )
        self._set_status(message)
        _show_message(self.form, "SubAssembly Designer", message)

    def _rename_selected_preset(self) -> None:
        preset_id = self._selected_preset_library_id()
        if not preset_id:
            message = "Select a Reusable Subassembly Template row before renaming it."
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        try:
            new_id, accepted = QtWidgets.QInputDialog.getText(
                self.form,
                "Rename SubAssembly Preset",
                "New preset id:",
                QtWidgets.QLineEdit.Normal,
                preset_id,
            )
        except Exception:
            new_id, accepted = "", False
        if not accepted:
            return
        new_id = str(new_id or "").strip()
        affected = _designer_assembly_rows_referencing_preset(self.document, preset_id)
        affected_text = ", ".join(affected[:8]) + (f", +{len(affected) - 8} more" if len(affected) > 8 else "")
        message = (
            f"Rename preset {preset_id} to {new_id}?\n\n"
            f"Affected Assembly rows: {len(affected)}"
            + (f"\n{affected_text}" if affected_text else "")
        )
        if not _confirm_action(self.form, "Rename Preset", message):
            return
        try:
            obj = rename_v1_subassembly_preset(
                document=self.document,
                project=find_project(self.document),
                preset_id=preset_id,
                new_preset_id=new_id,
            )
        except Exception as exc:
            message = str(exc)
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        self._refresh_preset_library_summary()
        self._refresh_assembly_rows()
        message = (
            "SubAssembly preset renamed.\n"
            f"Old preset: {preset_id}\n"
            f"New preset: {new_id}\n"
            f"Affected Assembly rows: {len(affected)}\n"
            f"Preset library: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')}"
        )
        self._set_status(message)
        _show_message(self.form, "SubAssembly Designer", message)

    def _delete_selected_preset(self) -> None:
        preset_id = self._selected_preset_library_id()
        if not preset_id:
            message = "Select a Reusable Subassembly Template row before deleting it."
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        affected = _designer_assembly_rows_referencing_preset(self.document, preset_id)
        affected_text = ", ".join(affected[:8]) + (f", +{len(affected) - 8} more" if len(affected) > 8 else "")
        message = (
            f"Delete preset {preset_id} from the project library?\n\n"
            f"Affected Assembly rows: {len(affected)}\n"
            "Affected rows are not silently detached; they will report missing_preset until reassigned."
            + (f"\n{affected_text}" if affected_text else "")
        )
        if not _confirm_action(self.form, "Delete Preset", message):
            return
        try:
            obj = delete_v1_subassembly_preset(
                document=self.document,
                project=find_project(self.document),
                preset_id=preset_id,
            )
        except Exception as exc:
            message = str(exc)
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        self._refresh_preset_library_summary()
        self._refresh_assembly_rows()
        message = (
            "SubAssembly preset deleted.\n"
            f"Template: {preset_id}\n"
            f"Affected Assembly rows now reference a missing preset: {len(affected)}\n"
            f"Preset library: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')}"
        )
        self._set_status(message)
        _show_message(self.form, "SubAssembly Designer", message)

    def _apply(self) -> None:
        self._save_active_definition_detail()
        self.library_model = self._library_model_from_ui()
        validation = self._validate_library_model(self.library_model)
        if validation.status == "error":
            self.detail_tabs.setCurrentWidget(self.diagnostics_widget)
            message = "SubAssembly Library was not applied because validation has errors."
            self._set_status(message)
            _show_message(self.form, "SubAssembly Designer", message)
            return
        obj = apply_v1_subassembly_library(
            document=self.document,
            project=find_project(self.document),
            library_model=self.library_model,
            object_name=str(getattr(self.library_obj, "Name", "") or "V1SubassemblyLibrary"),
        )
        self.library_obj = obj
        count = int(getattr(obj, "DefinitionCount", 0) or 0)
        message = f"SubAssembly Library applied.\nDefinitions: {count}"
        self._set_status(message)
        self._clear_changed_field_markers()
        _show_message(self.form, "SubAssembly Designer", message)

    def _close(self) -> None:
        if Gui is not None and hasattr(Gui, "Control"):
            try:
                Gui.Control.closeDialog()
            except Exception:
                pass

    def _definition_selection_changed(self) -> None:
        if self._loading:
            return
        current_index = self._selected_definition_index()
        locked_index = self._locked_definition_index
        allow_change = bool(self._allow_definition_selection_change)
        self._allow_definition_selection_change = False
        if (
            locked_index is not None
            and current_index is not None
            and current_index != locked_index
            and not allow_change
        ):
            self._restore_definition_selection(locked_index)
            return
        previous_index = self._active_definition_index
        if previous_index is not None:
            self._save_definition_detail(previous_index)
        definition = self._selected_definition()
        self._active_definition_index = current_index
        self._lock_definition_selection(current_index)
        self._load_detail(definition)

    def _definition_row_pressed(self, row: int, _column: int) -> None:
        self._allow_definition_selection_change = True
        self._locked_definition_index = int(row)
        try:
            self.table.setProperty("lockedDefinitionRow", int(row))
            self.table.setProperty("allowDefinitionSelectionChange", True)
        except Exception:
            pass

    def _definition_current_cell_changed(self, row: int, _column: int, _previous_row: int, _previous_column: int) -> None:
        if self._loading:
            return
        if row is None or row < 0:
            return
        locked_index = self._locked_definition_index
        if locked_index is None:
            return
        allow_change = bool(self._allow_definition_selection_change)
        self._allow_definition_selection_change = False
        if int(row) != int(locked_index) and not allow_change:
            self._restore_definition_selection(locked_index)

    def _lock_definition_selection(self, row: int | None) -> None:
        self._locked_definition_index = None if row is None else int(row)
        try:
            self.table.setProperty("lockedDefinitionRow", -1 if row is None else int(row))
            self.table.setProperty("allowDefinitionSelectionChange", False)
        except Exception:
            pass

    def _restore_definition_selection(self, row: int | None) -> None:
        if row is None or not (0 <= int(row) < self.table.rowCount()):
            return
        was_loading = self._loading
        self._loading = True
        try:
            self.table.clearSelection()
            self.table.selectRow(int(row))
            self.table.setCurrentCell(int(row), 0)
        except Exception:
            pass
        finally:
            self._loading = was_loading
        self._lock_definition_selection(int(row))

    def _load_detail(self, definition: SubassemblyDefinition | None) -> None:
        was_loading = self._loading
        self._loading = True
        self._clear_detail_tables()
        if definition is None:
            self.detail_summary.setText("Select a Subassembly definition row.")
            self._clear_preview("Select a Subassembly definition row.")
            self._loading = was_loading
            return
        self.detail_summary.setText(
            f"{definition.name} | {definition.kind} | side={definition.side_behavior} | "
            f"category={definition.category or '-'}"
        )
        for parameter in definition.parameter_rows:
            row = self.parameter_table.rowCount()
            _append_table_row(
                self.parameter_table,
                (
                    parameter.parameter_id,
                    parameter.label,
                    parameter.value,
                    parameter.unit,
                    "Yes" if parameter.required else "No",
                    parameter.min_value,
                    parameter.max_value,
                    parameter.notes,
                ),
            )
            _decorate_parameter_row(self.parameter_table, row, parameter.parameter_id)
        for point in definition.point_rows:
            _append_table_row(
                self.point_table,
                (
                    point.point_id,
                    point.x_expr,
                    point.z_expr,
                    point.code,
                    point.role,
                    "Yes" if point.connectable else "No",
                    point.notes,
                ),
            )
        for link in definition.link_rows:
            row = self.link_table.rowCount()
            _append_table_row(
                self.link_table,
                (
                    link.link_id,
                    link.start_point_ref,
                    link.end_point_ref,
                    link.surface_role,
                    link.code,
                    link.material,
                    link.quantity_role,
                    link.notes,
                ),
            )
            self._set_detail_combo(self.link_table, row, 5, SUBASSEMBLY_DESIGNER_MATERIAL_VALUES, link.material)
        for shape in definition.shape_rows:
            row = self.shape_table.rowCount()
            _append_table_row(
                self.shape_table,
                (
                    shape.shape_id,
                    ",".join(shape.point_refs),
                    shape.shape_code,
                    shape.material,
                    shape.quantity_role,
                    shape.solid_role,
                    "Yes" if shape.closed else "No",
                    shape.notes,
                ),
            )
            self._set_detail_combo(self.shape_table, row, 3, SUBASSEMBLY_DESIGNER_MATERIAL_VALUES, shape.material)
        for target in definition.target_rows:
            _append_table_row(
                self.target_table,
                (
                    target.target_id,
                    target.target_kind,
                    "Yes" if target.required else "No",
                    target.fallback_policy,
                    target.notes,
                ),
            )
        self._loading = was_loading
        self._refresh_preview()

    def _clear_detail_tables(self) -> None:
        for table in (
            self.parameter_table,
            self.point_table,
            self.link_table,
            self.shape_table,
            self.target_table,
        ):
            table.setRowCount(0)

    def _selected_definition(self) -> SubassemblyDefinition | None:
        index = self._selected_definition_index()
        rows = list(getattr(self.library_model, "definition_rows", []) or [])
        if index is not None and 0 <= index < len(rows):
            return rows[index]
        return None

    def _selected_definition_index(self) -> int | None:
        selected = list(self.table.selectionModel().selectedRows()) if self.table.selectionModel() is not None else []
        if not selected:
            return None
        return int(selected[0].row())

    def _save_active_definition_detail(self) -> None:
        if self._active_definition_index is None:
            self._active_definition_index = self._selected_definition_index()
        if self._active_definition_index is not None:
            self._save_definition_detail(self._active_definition_index)

    def _save_definition_detail(self, index: int) -> None:
        rows = list(getattr(self.library_model, "definition_rows", []) or [])
        if not (0 <= int(index) < len(rows)):
            return
        rows[int(index)] = self._definition_from_detail(index, rows[int(index)])
        self.library_model.definition_rows = rows
        self._refresh_definition_count_cells(index, rows[int(index)])

    def _definition_from_detail(self, index: int, base: SubassemblyDefinition) -> SubassemblyDefinition:
        return SubassemblyDefinition(
            definition_id=_table_text(self.table, index, 0) or base.definition_id,
            name=_table_text(self.table, index, 1) or base.name,
            kind=_table_text(self.table, index, 2) or base.kind,
            category=_table_text(self.table, index, 3),
            side_behavior=_table_text(self.table, index, 4) or base.side_behavior,
            parameter_rows=tuple(_parameter_rows_from_table(self.parameter_table)),
            point_rows=tuple(_point_rows_from_table(self.point_table)),
            link_rows=tuple(_link_rows_from_table(self.link_table)),
            shape_rows=tuple(_shape_rows_from_table(self.shape_table)),
            target_rows=tuple(_target_rows_from_table(self.target_table)),
            enabled=_truthy(_table_text(self.table, index, 10), default=True),
            notes=_table_text(self.table, index, 11),
        )

    def _library_model_from_ui(self) -> SubassemblyLibrary:
        definitions = []
        source_rows = list(getattr(self.library_model, "definition_rows", []) or [])
        for row in range(self.table.rowCount()):
            base = source_rows[row] if row < len(source_rows) else SubassemblyDefinition(
                definition_id=f"subassembly-definition:{row + 1}",
            )
            definitions.append(
                SubassemblyDefinition(
                    definition_id=_table_text(self.table, row, 0) or base.definition_id,
                    name=_table_text(self.table, row, 1) or base.name,
                    kind=_table_text(self.table, row, 2) or base.kind,
                    category=_table_text(self.table, row, 3),
                    side_behavior=_table_text(self.table, row, 4) or base.side_behavior,
                    parameter_rows=base.parameter_rows,
                    point_rows=base.point_rows,
                    link_rows=base.link_rows,
                    shape_rows=base.shape_rows,
                    target_rows=base.target_rows,
                    enabled=_truthy(_table_text(self.table, row, 10), default=True),
                    notes=_table_text(self.table, row, 11),
                )
            )
        return SubassemblyLibrary(
            schema_version=int(getattr(self.library_model, "schema_version", 1) or 1),
            project_id=_project_id(find_project(self.document)),
            label=str(getattr(self.library_model, "label", "") or "SubAssembly Library"),
            library_id=str(self.library_id_edit.text() or getattr(self.library_model, "library_id", "") or "subassembly-library:main"),
            preset_name=str(getattr(self.library_model, "preset_name", "") or ""),
            definition_rows=definitions,
        )

    def _refresh_definition_count_cells(self, row: int, definition: SubassemblyDefinition) -> None:
        counts = {
            5: len(definition.parameter_rows),
            6: len(definition.point_rows),
            7: len(definition.link_rows),
            8: len(definition.shape_rows),
            9: len(definition.target_rows),
        }
        for column, value in counts.items():
            item = QtWidgets.QTableWidgetItem(str(value))
            item.setFlags(_read_only_flags(item))
            _style_definition_count_item(item)
            self.table.setItem(row, column, item)
        self.definition_count_label.setText(str(self.table.rowCount()))

    def _add_definition(self) -> None:
        self._save_active_definition_detail()
        row = self.table.rowCount()
        definition = SubassemblyDefinition(
            definition_id=f"subassembly-definition:new-{row + 1}",
            name=f"New Subassembly {row + 1}",
            kind="lane",
            side_behavior="both",
        )
        self.library_model.definition_rows.append(definition)
        self.table.insertRow(row)
        values = (
            definition.definition_id,
            definition.name,
            definition.kind,
            definition.category,
            definition.side_behavior,
            0,
            0,
            0,
            0,
            0,
            "Yes",
            definition.notes,
        )
        for column, value in enumerate(values):
            if column == 2:
                self._set_definition_combo(row, column, SUBASSEMBLY_DESIGNER_KIND_VALUES, str(value))
            elif column == 3:
                self._set_definition_combo(row, column, SUBASSEMBLY_DESIGNER_CATEGORY_VALUES, str(value))
            elif column == 4:
                self._set_definition_combo(row, column, SUBASSEMBLY_DESIGNER_SIDE_VALUES, str(value))
            elif column == 10:
                self._set_definition_combo(row, column, SUBASSEMBLY_DESIGNER_ENABLED_VALUES, str(value or "Yes"))
            else:
                item = QtWidgets.QTableWidgetItem(str(value))
                if column in _definition_count_columns():
                    item.setFlags(_read_only_flags(item))
                    _style_definition_count_item(item)
                self.table.setItem(row, column, item)
        self.definition_count_label.setText(str(self.table.rowCount()))
        self.table.selectRow(row)

    def _duplicate_definition(self) -> None:
        self._save_active_definition_detail()
        source = self._selected_definition()
        if source is None:
            return
        row = self.table.rowCount()
        duplicate = SubassemblyDefinition(
            definition_id=f"{source.definition_id}-copy",
            name=f"{source.name} Copy",
            kind=source.kind,
            category=source.category,
            side_behavior=source.side_behavior,
            parameter_rows=source.parameter_rows,
            point_rows=source.point_rows,
            link_rows=source.link_rows,
            shape_rows=source.shape_rows,
            target_rows=source.target_rows,
            enabled=source.enabled,
            notes=source.notes,
        )
        self.library_model.definition_rows.append(duplicate)
        self._load_model(self.library_model)
        self.table.selectRow(row)

    def _delete_definition(self) -> None:
        index = self._selected_definition_index()
        if index is None:
            return
        rows = list(getattr(self.library_model, "definition_rows", []) or [])
        if 0 <= index < len(rows):
            del rows[index]
            self.library_model.definition_rows = rows
        self._load_model(self.library_model)

    def _add_detail_row(self) -> None:
        table = self.detail_tabs.currentWidget()
        if table is self.preview_widget or table is self.diagnostics_widget:
            self._refresh_preview()
            return
        if table is self.parameter_table:
            _append_table_row(table, (f"param-{table.rowCount() + 1}", "", "", "", "No", "", "", ""))
        elif table is self.point_table:
            _append_table_row(table, (f"point-{table.rowCount() + 1}", "0.0", "0.0", "", "", "No", ""))
        elif table is self.link_table:
            row = table.rowCount()
            _append_table_row(table, (f"link-{row + 1}", "", "", "design", "", "", "", ""))
            self._set_detail_combo(table, row, 5, SUBASSEMBLY_DESIGNER_MATERIAL_VALUES, "")
        elif table is self.shape_table:
            row = table.rowCount()
            _append_table_row(table, (f"shape-{row + 1}", "", "", "", "", "", "Yes", ""))
            self._set_detail_combo(table, row, 3, SUBASSEMBLY_DESIGNER_MATERIAL_VALUES, "")
        elif table is self.target_table:
            _append_table_row(table, (f"target-{table.rowCount() + 1}", "terrain_daylight", "No", "", ""))
        self._refresh_preview_if_auto()

    def _delete_detail_row(self) -> None:
        table = self.detail_tabs.currentWidget()
        if table is self.preview_widget or table is self.diagnostics_widget:
            self._refresh_preview()
            return
        selected = list(table.selectionModel().selectedRows()) if table.selectionModel() is not None else []
        for index in sorted((int(row.row()) for row in selected), reverse=True):
            table.removeRow(index)
        self._refresh_preview_if_auto()

    def _definition_table_changed(self, _item=None) -> None:
        if self._loading:
            return
        self._mark_changed_item(_item, "Local edit in definition table. Apply or save to persist this change.")
        self._set_preset_state("Editing Source: Modified. Definition table has local edits not yet saved.", "modified")
        self._refresh_preview_if_auto()

    def _detail_table_changed(self, _item=None) -> None:
        if self._loading:
            return
        self._mark_changed_item(_item, "Local edit in detail table. Apply or save to persist this change.")
        self._set_preset_state("Editing Source: Modified. Detail table has local edits not yet saved.", "modified")
        self._refresh_preview_if_auto()

    def _auto_preview_toggled(self, checked: bool) -> None:
        if checked:
            self._refresh_preview()

    def _refresh_preview_if_auto(self) -> None:
        try:
            enabled = bool(self.auto_preview_checkbox.isChecked())
        except Exception:
            enabled = True
        if enabled:
            self._refresh_preview()

    def _refresh_preview(self) -> None:
        index = self._selected_definition_index()
        if index is None:
            self._clear_preview("Select a Subassembly definition row.")
            return
        source_rows = list(getattr(self.library_model, "definition_rows", []) or [])
        if not (0 <= index < len(source_rows)):
            self._clear_preview("Selected definition is not available.")
            return
        definition = self._definition_from_detail(index, source_rows[index])
        result = SubassemblyExpressionService().evaluate_definition(definition)
        if result.status != "ok":
            self._draw_preview(definition, [], result.diagnostic_rows)
            self.preview_status.setText(_diagnostic_summary(result.diagnostic_rows))
            return
        self._draw_preview(definition, result.point_rows, result.diagnostic_rows)
        status_lines = [
            f"Preview: {definition.definition_id} | points={len(result.point_rows)} | links={len(definition.link_rows)}"
        ]
        surface_hint = _surface_role_preview_hint(definition)
        if surface_hint:
            status_lines.append(surface_hint)
        bench_hint = _bench_rows_preview_hint(definition)
        if bench_hint:
            status_lines.append(bench_hint)
        self.preview_status.setText("\n".join(status_lines))

    def _clear_preview(self, message: str) -> None:
        try:
            self.preview_scene.clear()
        except Exception:
            pass
        self.preview_status.setText(str(message or ""))

    def _add_preview_label(self, scene, text: str, anchor_x: float, anchor_y: float, used_rects, color) -> None:
        label = scene.addText(str(text or ""))
        label_color = color if isinstance(color, QtGui.QColor) else QtGui.QColor(str(color or "#f8fafc"))
        label.setDefaultTextColor(label_color)
        font = label.font()
        font.setPointSize(8)
        label.setFont(font)
        label.setZValue(30.0)

        offsets = (
            (6.0, -18.0),
            (8.0, 6.0),
            (-34.0, -18.0),
            (-34.0, 6.0),
            (14.0, -34.0),
            (14.0, 22.0),
            (-58.0, -34.0),
            (-58.0, 22.0),
        )
        final_rect = None
        for index, (dx, dy) in enumerate(offsets):
            if index >= len(offsets) - 1:
                dy += 14.0 * max(0, len(used_rects) - len(offsets) + 1)
            label.setPos(float(anchor_x) + dx, float(anchor_y) + dy)
            rect = label.mapRectToScene(label.boundingRect()).adjusted(-4.0, -2.0, 4.0, 2.0)
            if not any(rect.intersects(existing) for existing in used_rects):
                final_rect = rect
                break
            final_rect = rect

        if final_rect is None:
            final_rect = label.mapRectToScene(label.boundingRect()).adjusted(-4.0, -2.0, 4.0, 2.0)
        used_rects.append(final_rect)
        background = scene.addRect(
            final_rect,
            QtGui.QPen(QtGui.QColor(74, 91, 116, 180)),
            QtGui.QBrush(QtGui.QColor(15, 23, 42, 220)),
        )
        background.setZValue(29.0)

    def _draw_preview(self, definition: SubassemblyDefinition, point_rows, diagnostic_rows) -> None:
        scene = self.preview_scene
        scene.clear()
        if diagnostic_rows:
            text = scene.addText(_diagnostic_summary(diagnostic_rows))
            text.setDefaultTextColor(QtGui.QColor("#d35400"))
            scene.setSceneRect(scene.itemsBoundingRect().adjusted(-20, -20, 20, 20))
            return
        points = {row.point_id: row for row in list(point_rows or [])}
        if not points:
            text = scene.addText("No evaluated points are available.")
            text.setDefaultTextColor(QtGui.QColor("#666666"))
            return
        scale = 42.0
        pen_link = QtGui.QPen(QtGui.QColor("#0b74de"))
        pen_link.setWidthF(2.0)
        pen_slope = QtGui.QPen(QtGui.QColor("#2ca25f"))
        pen_slope.setWidthF(2.6)
        pen_bench = QtGui.QPen(QtGui.QColor("#f39c12"))
        pen_bench.setWidthF(3.2)
        pen_axis = QtGui.QPen(QtGui.QColor("#888888"))
        pen_axis.setStyle(QtCore.Qt.DashLine)
        pen_shape = QtGui.QPen(QtGui.QColor("#2e7d32"))
        pen_shape.setWidthF(1.4)
        brush_shape = QtGui.QBrush(QtGui.QColor(80, 180, 100, 70))
        pen_point = QtGui.QPen(QtGui.QColor("#111111"))
        brush_point = QtGui.QBrush(QtGui.QColor("#ffd200"))

        scene.addLine(-260, 0, 260, 0, pen_axis)
        scene.addLine(0, -120, 0, 80, pen_axis)
        side_behavior = str(getattr(definition, "side_behavior", "") or "").strip().lower().replace("-", "_")
        preview_sides = (("left", 1.0), ("right", -1.0)) if side_behavior == "both" else (("", 1.0),)
        used_label_rects = []

        for side_label, x_sign in preview_sides:
            side_suffix = f"{side_label}:" if side_label else ""
            for shape in list(getattr(definition, "shape_rows", []) or []):
                polygon_points = []
                for point_ref in list(getattr(shape, "point_refs", []) or []):
                    point = points.get(str(point_ref))
                    if point is None:
                        continue
                    polygon_points.append(QtCore.QPointF(float(x_sign) * point.x * scale, -point.z * scale))
                if len(polygon_points) >= 3:
                    polygon = QtGui.QPolygonF(polygon_points)
                    scene.addPolygon(polygon, pen_shape, brush_shape)

            for link in list(getattr(definition, "link_rows", []) or []):
                p1 = points.get(str(getattr(link, "start_point_ref", "") or ""))
                p2 = points.get(str(getattr(link, "end_point_ref", "") or ""))
                if p1 is None or p2 is None:
                    continue
                link_pen = _preview_pen_for_link(link, pen_link, pen_slope, pen_bench)
                scene.addLine(float(x_sign) * p1.x * scale, -p1.z * scale, float(x_sign) * p2.x * scale, -p2.z * scale, link_pen)

                mid_x = float(x_sign) * ((p1.x + p2.x) * 0.5) * scale
                mid_y = -((p1.z + p2.z) * 0.5) * scale
                code = str(getattr(link, "code", "") or getattr(link, "link_id", "") or "")
                if code:
                    self._add_preview_label(
                        scene,
                        f"{side_suffix}{code}" if side_suffix else code,
                        mid_x,
                        mid_y,
                        used_label_rects,
                        link_pen.color(),
                    )

            for point in points.values():
                x = float(x_sign) * point.x * scale
                y = -point.z * scale
                scene.addEllipse(x - 3.5, y - 3.5, 7.0, 7.0, pen_point, brush_point)
                self._add_preview_label(
                    scene,
                    f"{side_suffix}{point.point_id}" if side_suffix else str(point.point_id),
                    x,
                    y,
                    used_label_rects,
                    "#f8fafc",
                )

        bounds = scene.itemsBoundingRect().adjusted(-30, -30, 30, 30)
        scene.setSceneRect(bounds)
        try:
            self.preview_view.reset_zoom_for_bounds(bounds)
        except Exception:
            pass

    def _validate_current_library(self) -> None:
        self._save_active_definition_detail()
        self.library_model = self._library_model_from_ui()
        validation = self._validate_library_model(self.library_model)
        self.detail_tabs.setCurrentWidget(self.diagnostics_widget)
        self._set_status(f"Validation: {validation.status}; diagnostics={len(validation.diagnostic_rows)}")

    def _validate_library_model(self, library_model: SubassemblyLibrary):
        validation = SubassemblyDefinitionValidationService().validate_library(library_model)
        self._load_diagnostics(validation.diagnostic_rows)
        self.diagnostics_status.setText(f"Validation: {validation.status}; diagnostics={len(validation.diagnostic_rows)}")
        return validation

    def _load_diagnostics(self, rows) -> None:
        self.diagnostics_table.setRowCount(0)
        for diagnostic in list(rows or []):
            row = self.diagnostics_table.rowCount()
            self.diagnostics_table.insertRow(row)
            values = (
                str(getattr(diagnostic, "severity", "") or ""),
                str(getattr(diagnostic, "kind", "") or ""),
                str(getattr(diagnostic, "message", "") or ""),
                str(getattr(diagnostic, "notes", "") or ""),
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(_read_only_flags(item))
                self.diagnostics_table.setItem(row, column, item)

    def _set_status(self, message: str) -> None:
        self.status_text.setPlainText(str(message or ""))

    def _set_preset_state(self, message: str, state: str = "snapshot") -> None:
        label = getattr(self, "preset_state_label", None)
        if label is None:
            return
        colors = {
            "linked": ("#202936", "#8fd18f", "#3d8f4a"),
            "modified": ("#202936", "#f3d36b", "#c79a2a"),
            "snapshot": ("#202936", "#d8e0ea", "#6f7f95"),
            "missing": ("#202936", "#ff9b9b", "#c85d5d"),
            "outdated": ("#202936", "#ffbe70", "#d4832f"),
        }
        background, foreground, accent = colors.get(str(state or "snapshot"), colors["snapshot"])
        label.setText(str(message or "Editing Source: Snapshot"))
        label.setStyleSheet(
            "QLabel {"
            f"background: {background};"
            f"color: {foreground};"
            "border: 1px solid #435066;"
            f"border-left: 4px solid {accent};"
            "border-radius: 4px;"
            "padding: 4px 6px;"
            "}"
        )
        self._refresh_save_target_label()

    def _refresh_save_target_label(self) -> None:
        label = getattr(self, "save_target_label", None)
        if label is None:
            return
        combo = getattr(self, "assembly_row_combo", None)
        if _designer_has_assembly_object(self.document):
            row_label = str(combo.currentText() if combo is not None else "").strip()
            subassembly_id = row_label.split("|", 1)[0].strip() if row_label else ""
            if not subassembly_id or subassembly_id.startswith("Auto:"):
                label.setText("Save target: first enabled Assembly row")
            else:
                label.setText(f"Save target: Assembly row {subassembly_id}")
            return
        label.setText("Save target: SubAssembly library source")

    def _refresh_preset_library_summary(self) -> None:
        label = getattr(self, "preset_library_summary_label", None)
        if label is not None:
            label.setText(_designer_preset_library_summary_text(self.document))
        table = getattr(self, "preset_library_table", None)
        if table is None:
            return
        rows = _designer_preset_library_rows(self.document) or []
        table.setRowCount(0)
        for preset in rows:
            row = table.rowCount()
            table.insertRow(row)
            values = (
                str(getattr(preset, "preset_id", "") or ""),
                str(getattr(preset, "version", "") or ""),
                str(getattr(preset, "kind", "") or ""),
                str(getattr(preset, "definition_ref", "") or ""),
                str(getattr(preset, "name", "") or ""),
                _designer_preset_history_text(preset),
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(_read_only_flags(item))
                item.setToolTip("Project Subassembly preset source row.")
                table.setItem(row, column, item)

    def _selected_preset_library_id(self) -> str:
        table = getattr(self, "preset_library_table", None)
        if table is None:
            return ""
        rows = sorted({index.row() for index in table.selectedIndexes()})
        if not rows:
            current = table.currentRow()
            rows = [current] if current >= 0 else []
        if not rows:
            return ""
        item = table.item(rows[0], 0)
        return str(item.text() if item is not None else "").strip()

    def _mark_changed_item(self, item, message: str) -> None:
        if item is None:
            return
        try:
            item.setData(QtCore.Qt.UserRole, "local_edit")
            item.setBackground(QtGui.QBrush(QtGui.QColor(255, 245, 196)))
            item.setForeground(QtGui.QBrush(QtGui.QColor(24, 24, 24)))
            item.setToolTip(str(message or "Local edit."))
            self._refresh_changed_field_summary()
        except Exception:
            return

    def _refresh_changed_field_summary(self) -> None:
        label = getattr(self, "changed_fields_label", None)
        if label is None:
            return
        count = 0
        for table in (
            getattr(self, "table", None),
            getattr(self, "parameter_table", None),
            getattr(self, "point_table", None),
            getattr(self, "link_table", None),
            getattr(self, "shape_table", None),
            getattr(self, "target_table", None),
        ):
            if table is None:
                continue
            for row in range(table.rowCount()):
                for column in range(table.columnCount()):
                    item = table.item(row, column)
                    try:
                        if item is not None and item.data(QtCore.Qt.UserRole) == "local_edit":
                            count += 1
                    except Exception:
                        continue
        label.setText(f"Changed fields: {count}")
        self._refresh_preset_difference_summary()

    def _refresh_preset_difference_summary(self) -> None:
        label = getattr(self, "preset_differences_label", None)
        if label is None:
            return
        try:
            definition = self._selected_definition()
        except Exception:
            definition = None
        if definition is None:
            label.setText("Subassembly Template differences: n/a")
            return
        preset_id = _preset_id_from_definition(definition)
        preset = _designer_preset_by_id(self.document, preset_id)
        if preset is None:
            label.setText(f"Subassembly Template differences: n/a ({preset_id} not found)")
            return
        changed = _designer_preset_difference_keys(definition, preset)
        label.setText(f"Subassembly Template differences: {len(changed)}")
        if changed:
            label.setToolTip("Different preset fields: " + ", ".join(changed[:12]))
        else:
            label.setToolTip("Current definition values match the matching Reusable Subassembly Template contract.")

    def _clear_changed_field_markers(self) -> None:
        for table in (
            getattr(self, "table", None),
            getattr(self, "parameter_table", None),
            getattr(self, "point_table", None),
            getattr(self, "link_table", None),
            getattr(self, "shape_table", None),
            getattr(self, "target_table", None),
        ):
            if table is None:
                continue
            for row in range(table.rowCount()):
                for column in range(table.columnCount()):
                    item = table.item(row, column)
                    if item is None:
                        continue
                    try:
                        if item.data(QtCore.Qt.UserRole) != "local_edit":
                            continue
                        item.setData(QtCore.Qt.UserRole, None)
                        item.setBackground(QtGui.QBrush())
                        item.setForeground(QtGui.QBrush())
                        item.setToolTip("")
                    except Exception:
                        continue
        self._refresh_changed_field_summary()


class _DefinitionTableComboBox(QtWidgets.QComboBox):
    """Combo box that does not move the definition-table selection on hover."""

    def __init__(self, table=None, row: int | None = None):
        super().__init__()
        self._table = table
        self._row = row
        try:
            self.setFocusPolicy(QtCore.Qt.ClickFocus)
            self.setMouseTracking(False)
            self.setAttribute(QtCore.Qt.WA_Hover, False)
            self.view().setMouseTracking(False)
            self.view().setAttribute(QtCore.Qt.WA_Hover, False)
        except Exception:
            pass

    def event(self, event):  # noqa: D401 - Qt event API
        """Ignore hover-only events inside QTableWidget cell widgets."""

        try:
            event_type = event.type()
            hover_types = {
                QtCore.QEvent.Enter,
                QtCore.QEvent.MouseMove,
                QtCore.QEvent.HoverEnter,
                QtCore.QEvent.HoverMove,
                QtCore.QEvent.HoverLeave,
            }
            if event_type in hover_types:
                self._restore_table_selection()
                return True
        except Exception:
            pass
        return super().event(event)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt API name
        self._restore_table_selection()
        try:
            event.accept()
        except Exception:
            pass

    def mousePressEvent(self, event):  # noqa: N802 - Qt API name
        self._restore_table_selection()
        try:
            super().mousePressEvent(event)
        except Exception:
            pass

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt API name
        self._restore_table_selection()
        try:
            super().mouseReleaseEvent(event)
        except Exception:
            pass

    def showPopup(self):  # noqa: N802 - Qt API name
        self._restore_table_selection()
        return super().showPopup()

    def enterEvent(self, event):  # noqa: N802 - Qt API name
        self._restore_table_selection()
        try:
            event.accept()
        except Exception:
            pass

    def leaveEvent(self, event):  # noqa: N802 - Qt API name
        self._restore_table_selection()
        try:
            event.accept()
        except Exception:
            pass

    def _restore_table_selection(self) -> None:
        table = self._table
        if table is None:
            return
        try:
            locked = table.property("lockedDefinitionRow")
            locked_row = int(locked) if locked is not None else -1
        except Exception:
            locked_row = -1
        if locked_row < 0:
            try:
                selected_rows = [index.row() for index in table.selectionModel().selectedRows()]
                locked_row = int(selected_rows[0]) if selected_rows else -1
            except Exception:
                locked_row = -1
        if locked_row < 0:
            return
        try:
            selected_rows = {index.row() for index in table.selectionModel().selectedRows()}
            current_row = int(table.currentRow())
            if selected_rows == {locked_row} and current_row == locked_row:
                return
            previous_state = bool(table.blockSignals(True))
            try:
                table.clearSelection()
                table.selectRow(locked_row)
                table.setCurrentCell(locked_row, 0)
            finally:
                table.blockSignals(previous_state)
            table.setProperty("lockedDefinitionRow", locked_row)
            table.setProperty("allowDefinitionSelectionChange", False)
        except Exception:
            pass

    def _allow_table_selection_change(self) -> None:
        table = self._table
        row = self._row
        if table is None or row is None:
            return
        try:
            table.setProperty("allowDefinitionSelectionChange", True)
            table.setProperty("lockedDefinitionRow", int(row))
            table.selectRow(int(row))
            table.setCurrentCell(int(row), 0)
        except Exception:
            pass


class _ZoomablePreviewView(QtWidgets.QGraphicsView):
    """Graphics view with mouse-wheel zoom for the Designer live preview."""

    def __init__(self, scene=None):
        super().__init__(scene)
        self._zoom_factor = 1.0
        try:
            self.setFocusPolicy(QtCore.Qt.StrongFocus)
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
            self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        except Exception:
            pass

    def wheelEvent(self, event):  # noqa: N802 - Qt API name
        try:
            delta = event.angleDelta().y()
        except Exception:
            delta = 0
        if not delta:
            try:
                super().wheelEvent(event)
            except Exception:
                pass
            return
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        next_zoom = self._zoom_factor * factor
        if next_zoom < 0.15 or next_zoom > 12.0:
            try:
                event.accept()
            except Exception:
                pass
            return
        self._zoom_factor = next_zoom
        self.scale(factor, factor)
        try:
            event.accept()
        except Exception:
            pass

    def mousePressEvent(self, event):  # noqa: N802 - Qt API name
        try:
            self.setFocus(QtCore.Qt.MouseFocusReason)
        except Exception:
            pass
        try:
            super().mousePressEvent(event)
        except Exception:
            pass

    def reset_zoom_for_bounds(self, bounds) -> None:
        self._zoom_factor = 1.0
        try:
            self.resetTransform()
            self.fitInView(bounds, QtCore.Qt.KeepAspectRatio)
        except Exception:
            pass


__all__ = [
    "V1SubAssemblyDesignerTaskPanel",
    "_DefinitionTableComboBox",
    "_ZoomablePreviewView",
    "configure_sub_assembly_designer_task_panel_runtime",
]

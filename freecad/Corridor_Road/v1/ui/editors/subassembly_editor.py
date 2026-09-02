"""Assembly/Subassembly editor presentation for CorridorRoad v1."""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets


def configure_assembly_subassembly_editor_task_panel_runtime(bindings) -> None:
    """Bind command/controller collaborators without importing the command module."""

    protected = {
        "_AssemblyTableComboBox",
        "V1AssemblySubassemblyEditorTaskPanel",
        "_AssemblySectionPreviewView",
        "configure_assembly_subassembly_editor_task_panel_runtime",
    }
    for name, value in dict(bindings or {}).items():
        if name.startswith("__") or name in protected:
            continue
        globals()[name] = value


# Explicit runtime collaborators are replaced by the command callback map.
ASSEMBLY_SUBASSEMBLY_SIDES = None
App = None
AssemblySubassemblyModel = None
COL_DEFINITION_REF = None
COL_ENABLED = None
COL_ID = None
COL_INDEX = None
COL_KIND = None
COL_MATERIAL = None
COL_NOTES = None
COL_OVERRIDES = None
COL_PARAMETERS = None
COL_PRESET_REF = None
COL_PRESET_STATUS = None
COL_PRESET_VERSION = None
COL_SIDE = None
COL_SLOPE = None
COL_SOURCE_INSTANCE_REF = None
COL_TARGET_REF = None
COL_THICKNESS = None
COL_WIDTH = None
DITCH_SHAPES = None
DITCH_SHAPE_DEFAULTS = None
Gui = None
HIDDEN_SOURCE_COLUMNS = None
SUBASSEMBLY_COLUMNS = None
SUBASSEMBLY_PRESET_STATUSES = None
SubassemblySectionTemplate = None
TemplateSubassembly = None
_active_template = None
_apply_preset_defaults_to_row = None
_assembly_section_preview_segments = None
_bench_detail_note = None
_compact_bench_rows = None
_definition_override_rows = None
_definition_parameter_defaults = None
_definition_preview_text = None
_detail_parameter_rows = None
_detail_parameters = None
_detail_value = None
_ditch_detail_note = None
_float = None
_format_float = None
_guess_missing_subassembly_refs_for_panel = None
_item_text = None
_merge_detail_parameters = None
_override_value_changed = None
_physical_body_contract_summary = None
_preset_status_display = None
_preset_status_legend_text = None
_project_id = None
_replace_detail_rows = None
_set_combo_text = None
_set_detail_value = None
_set_table_item_text = None
_show_message = None
_subassembly_definition_for_ref = None
_subassembly_definition_ref_set = None
_subassembly_definition_ref_values = None
_subassembly_library_model = None
_subassembly_preset_for_ref = None
_subassembly_preset_ref_set = None
_subassembly_preset_ref_values = None
_subassembly_preset_version_map = None
_subassembly_preview_text = None
_truthy = None
_validate_subassembly_model = None
apply_v1_assembly_subassembly_model = None
assembly_preset_names = None
assembly_subassembly_preset_model_from_document = None
find_project = None
find_v1_assembly_subassembly_model = None
normalize_bench_rows = None
parse_subassembly_parameters = None
serialize_subassembly_parameters = None
to_assembly_subassembly_model = None


class _AssemblyTableComboBox(QtWidgets.QComboBox):
    """Combo box that does not move the Assembly table selection on hover."""

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
        self._allow_table_selection_change()
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
        self._allow_table_selection_change()
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
            locked = table.property("lockedAssemblyRow")
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
            table.setProperty("lockedAssemblyRow", locked_row)
            table.setProperty("allowAssemblySelectionChange", False)
        except Exception:
            pass

    def _allow_table_selection_change(self) -> None:
        table = self._table
        row = self._row
        if table is None or row is None:
            return
        try:
            table.setProperty("allowAssemblySelectionChange", True)
            table.setProperty("lockedAssemblyRow", int(row))
            table.selectRow(int(row))
            table.setCurrentCell(int(row), 0)
        except Exception:
            pass


class V1AssemblySubassemblyEditorTaskPanel:
    """Table-based v1 Assembly/Subassembly source editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self._locked_assembly_row_index: int | None = None
        self._allow_assembly_selection_change = False
        self._loading = False
        self.assembly_obj = find_v1_assembly_subassembly_model(self.document)
        self.model = to_assembly_subassembly_model(self.assembly_obj) if self.assembly_obj is not None else None
        if self.model is None:
            self.model = assembly_subassembly_preset_model_from_document("Full Set Road", document=self.document)
        self.form = self._build_form()
        self._load_model(self.model)

    def getStandardButtons(self):  # noqa: N802 - Qt API name
        return 0

    def _build_form(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        title = QtWidgets.QLabel("Assembly / Subassembly")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        description = QtWidgets.QLabel(
            "Define assembly intent with explicit Subassembly rows. The existing Assembly panel remains available during transition."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Assembly Template:"))
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItems(assembly_preset_names())
        self.preset_combo.setCurrentText("Full Set Road")
        preset_row.addWidget(self.preset_combo, 1)
        self.load_preset_button = QtWidgets.QPushButton("Load Assembly Template")
        self.load_preset_button.clicked.connect(self._load_selected_preset)
        preset_row.addWidget(self.load_preset_button)
        layout.addLayout(preset_row)

        ids_row = QtWidgets.QHBoxLayout()
        ids_row.addWidget(QtWidgets.QLabel("Assembly ID:"))
        self.assembly_id_edit = QtWidgets.QLineEdit()
        ids_row.addWidget(self.assembly_id_edit, 1)
        ids_row.addWidget(QtWidgets.QLabel("Template ID:"))
        self.template_id_edit = QtWidgets.QLineEdit()
        ids_row.addWidget(self.template_id_edit, 1)
        layout.addLayout(ids_row)

        guess_ref_row = QtWidgets.QHBoxLayout()
        self.guess_subassembly_refs_button = QtWidgets.QPushButton("Guess Subassembly Refs")
        self.guess_subassembly_refs_button.setObjectName("GuessSubassemblyRefsButton")
        self.guess_subassembly_refs_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.guess_subassembly_refs_button.setMinimumHeight(32)
        self.guess_subassembly_refs_button.setStyleSheet(
            "QPushButton#GuessSubassemblyRefsButton {"
            "background: #1f4f83;"
            "color: #ffffff;"
            "border: 1px solid #6fb6ff;"
            "border-radius: 4px;"
            "padding: 6px 12px;"
            "font-weight: 600;"
            "}"
            "QPushButton#GuessSubassemblyRefsButton:hover {"
            "background: #2b6faa;"
            "border-color: #93c5fd;"
            "}"
            "QPushButton#GuessSubassemblyRefsButton:pressed {"
            "background: #163d66;"
            "}"
        )
        self.guess_subassembly_refs_button.setToolTip(
            "Fill empty Subassembly Ref cells by guessing from each Subassembly ID. Existing refs are not overwritten."
        )
        self.guess_subassembly_refs_button.clicked.connect(lambda _checked=False: _guess_missing_subassembly_refs_for_panel(self))
        guess_ref_row.addWidget(self.guess_subassembly_refs_button)
        self.guess_subassembly_refs_note = QtWidgets.QLabel(
            "Subassembly Ref guesses are based on Subassembly ID text and may be inaccurate. Review the assigned refs before Apply."
        )
        self.guess_subassembly_refs_note.setWordWrap(True)
        self.guess_subassembly_refs_note.setStyleSheet(
            "QLabel {"
            "background: #302b1c;"
            "color: #f2d38a;"
            "border: 1px solid #7f6427;"
            "border-left: 4px solid #d9a441;"
            "border-radius: 4px;"
            "padding: 4px 6px;"
            "}"
        )
        guess_ref_row.addWidget(self.guess_subassembly_refs_note, 1)
        layout.addLayout(guess_ref_row)

        self.table = QtWidgets.QTableWidget(0, len(SUBASSEMBLY_COLUMNS))
        self.table.setHorizontalHeaderLabels(SUBASSEMBLY_COLUMNS)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        try:
            self.table.setMouseTracking(False)
            self.table.viewport().setMouseTracking(False)
            self.table.viewport().setAttribute(QtCore.Qt.WA_Hover, False)
        except Exception:
            pass
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellPressed.connect(self._assembly_row_pressed)
        self.table.cellClicked.connect(self._assembly_row_clicked)
        self.table.currentCellChanged.connect(self._assembly_current_cell_changed)
        for column in HIDDEN_SOURCE_COLUMNS:
            self.table.setColumnHidden(column, True)
        layout.addWidget(self.table, 1)
        self.preset_status_legend = QtWidgets.QLabel(_preset_status_legend_text())
        self.preset_status_legend.setWordWrap(True)
        self.preset_status_legend.setToolTip(
            "Template status colors are visual review aids only; Apply writes the Assembly source object."
        )
        self.preset_status_legend.setStyleSheet(
            "QLabel {"
            "background: #202936;"
            "color: #d8e0ea;"
            "border: 1px solid #435066;"
            "border-left: 4px solid #6f7f95;"
            "border-radius: 4px;"
            "padding: 4px 6px;"
            "}"
        )
        layout.addWidget(self.preset_status_legend)

        self.detail_group = QtWidgets.QGroupBox("Selected Subassembly Detail")
        detail_layout = QtWidgets.QVBoxLayout(self.detail_group)
        self.detail_summary = QtWidgets.QLabel("Select a Subassembly row.")
        self.detail_summary.setWordWrap(True)
        detail_layout.addWidget(self.detail_summary)
        self.detail_table = QtWidgets.QTableWidget(0, 2)
        self.detail_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.detail_table.horizontalHeader().setStretchLastSection(True)
        detail_layout.addWidget(self.detail_table)
        preview_label = QtWidgets.QLabel("Point / Link / Shape Preview")
        preview_label.setStyleSheet("font-weight: 600;")
        detail_layout.addWidget(preview_label)
        self.detail_preview = QtWidgets.QPlainTextEdit()
        self.detail_preview.setReadOnly(True)
        self.detail_preview.setMinimumHeight(110)
        detail_layout.addWidget(self.detail_preview)
        detail_button_row = QtWidgets.QHBoxLayout()
        self.load_detail_defaults_button = QtWidgets.QPushButton("Load Detail Defaults")
        self.load_detail_defaults_button.setToolTip("Load kind-specific detail defaults into the selected row editor.")
        self.load_detail_defaults_button.clicked.connect(self._load_selected_detail_defaults)
        detail_button_row.addWidget(self.load_detail_defaults_button)
        self.refresh_from_preset_button = QtWidgets.QPushButton("Refresh from Template")
        self.refresh_from_preset_button.setToolTip("Replace the selected linked row with current reusable Subassembly template defaults and clear local overrides.")
        self.refresh_from_preset_button.clicked.connect(self._refresh_selected_from_preset)
        detail_button_row.addWidget(self.refresh_from_preset_button)
        self.detach_as_custom_button = QtWidgets.QPushButton("Detach as Custom")
        self.detach_as_custom_button.setToolTip("Convert the selected template-linked row into a local snapshot that no longer follows template updates.")
        self.detach_as_custom_button.clicked.connect(self._detach_selected_as_custom)
        detail_button_row.addWidget(self.detach_as_custom_button)
        self.add_bench_row_button = QtWidgets.QPushButton("Add Bench Row")
        self.add_bench_row_button.setToolTip("Append a side-slope bench row to the selected detail parameters.")
        self.add_bench_row_button.clicked.connect(self._add_detail_bench_row)
        detail_button_row.addWidget(self.add_bench_row_button)
        self.reset_overrides_button = QtWidgets.QPushButton("Reset Overrides")
        self.reset_overrides_button.setToolTip("Clear local overrides on the selected row and return it to linked template defaults where possible.")
        self.reset_overrides_button.clicked.connect(self._reset_selected_overrides)
        detail_button_row.addWidget(self.reset_overrides_button)
        self.apply_detail_button = QtWidgets.QPushButton("Apply Detail")
        self.apply_detail_button.setToolTip("Apply detail-table edits to the selected Assembly row without writing the FreeCAD source object yet.")
        self.apply_detail_button.clicked.connect(self._apply_selected_detail)
        detail_button_row.addWidget(self.apply_detail_button)
        detail_button_row.addStretch(1)
        detail_layout.addLayout(detail_button_row)
        layout.addWidget(self.detail_group)

        button_row = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add Subassembly")
        self.add_button.clicked.connect(self._add_row)
        button_row.addWidget(self.add_button)
        self.delete_button = QtWidgets.QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_selected)
        button_row.addWidget(self.delete_button)
        self.validate_button = QtWidgets.QPushButton("Validate")
        self.validate_button.clicked.connect(self._validate)
        button_row.addWidget(self.validate_button)
        self.refresh_outdated_presets_button = QtWidgets.QPushButton("Refresh Outdated Templates")
        self.refresh_outdated_presets_button.setToolTip(
            "Refresh rows whose reusable Subassembly template version is outdated; modified, missing, and snapshot rows are skipped."
        )
        self.refresh_outdated_presets_button.clicked.connect(self._refresh_outdated_presets)
        button_row.addWidget(self.refresh_outdated_presets_button)
        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.setToolTip("Validate and write the Assembly/Subassembly source object.")
        self.apply_button.clicked.connect(self._apply)
        button_row.addWidget(self.apply_button)
        button_row.addStretch(1)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self._close)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

        self.summary = QtWidgets.QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMinimumHeight(90)
        layout.addWidget(self.summary)

        preview_button_row = QtWidgets.QHBoxLayout()
        preview_button_row.addStretch(1)
        self.show_section_preview_button = QtWidgets.QPushButton("Show Section Preview")
        self.show_section_preview_button.setToolTip("Refresh the in-panel preview of the current Assembly/Subassembly cross-section source.")
        self.show_section_preview_button.clicked.connect(self._show_section_preview)
        preview_button_row.addWidget(self.show_section_preview_button)
        layout.addLayout(preview_button_row)

        self.section_preview_group = QtWidgets.QGroupBox("Section Preview")
        section_preview_layout = QtWidgets.QVBoxLayout(self.section_preview_group)
        self.section_preview_scene = QtWidgets.QGraphicsScene()
        self.section_preview_view = _AssemblySectionPreviewView(self.section_preview_scene)
        try:
            self.section_preview_view.setRenderHint(QtGui.QPainter.Antialiasing, True)
        except Exception:
            pass
        self.section_preview_view.setMinimumHeight(240)
        section_preview_layout.addWidget(self.section_preview_view, 1)
        self.section_preview_status = QtWidgets.QLabel("Click Show Section Preview to review the current Assembly/Subassembly section.")
        self.section_preview_status.setWordWrap(True)
        section_preview_layout.addWidget(self.section_preview_status)
        layout.addWidget(self.section_preview_group)
        return widget

    def _load_model(self, model: AssemblySubassemblyModel) -> None:
        self.model = model
        self.assembly_id_edit.setText(str(model.assembly_id or ""))
        template = _active_template(model)
        self.template_id_edit.setText(str(getattr(template, "template_id", "") or ""))
        rows = list(getattr(template, "subassembly_rows", []) or [])
        self.table.setRowCount(0)
        for row in rows:
            self._append_subassembly(row)
        self._refresh_preset_status_indicators()
        if rows:
            self.table.selectRow(0)
            self._lock_assembly_selection(0)
        else:
            self._lock_assembly_selection(None)
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Loaded {len(rows)} subassembly rows. Apply writes a V1AssemblySubassemblyModel source object.")

    def _load_selected_preset(self) -> None:
        try:
            model = assembly_subassembly_preset_model_from_document(self.preset_combo.currentText(), document=self.document)
            self._load_model(model)
        except Exception as exc:
            _show_message(self.form, "Assembly / Subassembly", f"Assembly Template load failed: {exc}")

    def _append_subassembly(self, subassembly: TemplateSubassembly) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._set_combo(row, COL_ENABLED, ("Yes", "No"), "Yes" if subassembly.enabled else "No")
        self.table.setItem(row, COL_ID, QtWidgets.QTableWidgetItem(str(subassembly.subassembly_id)))
        self._set_definition_combo(row, COL_DEFINITION_REF, subassembly.definition_ref)
        self._set_preset_combo(row, COL_PRESET_REF, getattr(subassembly, "preset_ref", ""))
        self.table.setItem(row, COL_PRESET_VERSION, QtWidgets.QTableWidgetItem(str(getattr(subassembly, "preset_version", "") or "")))
        self._set_combo(
            row,
            COL_PRESET_STATUS,
            ("",) + tuple(SUBASSEMBLY_PRESET_STATUSES),
            _preset_status_display(subassembly),
        )
        self._set_combo(row, COL_SIDE, ASSEMBLY_SUBASSEMBLY_SIDES, subassembly.side)
        self.table.setItem(row, COL_INDEX, QtWidgets.QTableWidgetItem(str(int(subassembly.subassembly_index or row + 1))))
        self.table.setItem(row, COL_TARGET_REF, QtWidgets.QTableWidgetItem(str(subassembly.target_ref)))
        self.table.setItem(row, COL_NOTES, QtWidgets.QTableWidgetItem(str(subassembly.notes)))
        self.table.setItem(row, COL_KIND, QtWidgets.QTableWidgetItem(str(subassembly.kind)))
        self.table.setItem(row, COL_WIDTH, QtWidgets.QTableWidgetItem(_format_float(subassembly.width)))
        self.table.setItem(row, COL_SLOPE, QtWidgets.QTableWidgetItem(_format_float(subassembly.slope)))
        self.table.setItem(row, COL_THICKNESS, QtWidgets.QTableWidgetItem(_format_float(subassembly.thickness)))
        self.table.setItem(row, COL_MATERIAL, QtWidgets.QTableWidgetItem(str(subassembly.material)))
        self.table.setItem(row, COL_OVERRIDES, QtWidgets.QTableWidgetItem(serialize_subassembly_parameters(subassembly.parameter_overrides)))
        self.table.setItem(row, COL_PARAMETERS, QtWidgets.QTableWidgetItem(serialize_subassembly_parameters(subassembly.parameters)))
        self.table.setItem(row, COL_SOURCE_INSTANCE_REF, QtWidgets.QTableWidgetItem(str(getattr(subassembly, "source_instance_ref", "") or "")))
        self._style_subassembly_row(row)
        if self.table.rowCount() == 1:
            self.table.selectRow(0)

    def _set_combo(self, row: int, column: int, values: tuple[str, ...], current: str) -> None:
        combo = _AssemblyTableComboBox(self.table, row)
        combo.addItems(list(values))
        index = combo.findText(str(current or ""))
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.currentTextChanged.connect(lambda _value, table_row=row: self._preset_ref_changed(table_row))
        self.table.setCellWidget(row, column, combo)

    def _preset_ref_changed(self, row: int) -> None:
        if row < 0 or row >= self.table.rowCount():
            return
        preset_ref = _item_text(self.table, row, COL_PRESET_REF)
        if not preset_ref:
            _set_table_item_text(self.table, row, COL_PRESET_VERSION, "")
            _set_combo_text(self.table, row, COL_PRESET_STATUS, "snapshot")
            self._style_subassembly_row(row)
            return
        preset = _subassembly_preset_for_ref(self.document, preset_ref)
        if preset is None:
            versions = _subassembly_preset_version_map(self.document)
            _set_table_item_text(self.table, row, COL_PRESET_VERSION, versions.get(preset_ref, ""))
            _set_combo_text(self.table, row, COL_PRESET_STATUS, "missing_preset")
            self._style_subassembly_row(row)
            self._refresh_selected_detail()
            return
        _apply_preset_defaults_to_row(self.table, row, preset, clear_overrides=False)
        self._style_subassembly_row(row)
        self._refresh_selected_detail()

    def _assembly_row_pressed(self, row: int, _column: int) -> None:
        self._allow_assembly_selection_change = True
        self._locked_assembly_row_index = int(row)
        try:
            self.table.setProperty("lockedAssemblyRow", int(row))
            self.table.setProperty("allowAssemblySelectionChange", True)
        except Exception:
            pass

    def _assembly_row_clicked(self, row: int, _column: int) -> None:
        if self._loading or row is None or row < 0:
            return
        self._lock_assembly_selection(int(row))
        self._refresh_selected_detail()

    def _assembly_current_cell_changed(self, row: int, _column: int, _previous_row: int, _previous_column: int) -> None:
        if self._loading:
            return
        if row is None or row < 0:
            return
        locked_index = self._locked_assembly_row_index
        if locked_index is None:
            self._lock_assembly_selection(int(row))
            return
        allow_change = bool(self._allow_assembly_selection_change)
        self._allow_assembly_selection_change = False
        if int(row) != int(locked_index) and not allow_change:
            self._restore_assembly_selection(locked_index)
        else:
            self._lock_assembly_selection(int(row))

    def _lock_assembly_selection(self, row: int | None) -> None:
        self._locked_assembly_row_index = None if row is None else int(row)
        try:
            self.table.setProperty("lockedAssemblyRow", -1 if row is None else int(row))
            self.table.setProperty("allowAssemblySelectionChange", False)
        except Exception:
            pass

    def _restore_assembly_selection(self, row: int | None) -> None:
        if row is None or not (0 <= int(row) < self.table.rowCount()):
            return
        was_loading = self._loading
        self._loading = True
        try:
            previous_state = bool(self.table.blockSignals(True))
            try:
                self.table.clearSelection()
                self.table.selectRow(int(row))
                self.table.setCurrentCell(int(row), 0)
            finally:
                self.table.blockSignals(previous_state)
        finally:
            self._loading = was_loading
        self._lock_assembly_selection(int(row))

    def _style_subassembly_row(self, row: int) -> None:
        if row < 0 or row >= self.table.rowCount():
            return
        status = _item_text(self.table, row, COL_PRESET_STATUS)
        preset_ref = _item_text(self.table, row, COL_PRESET_REF)
        if not status:
            status = "linked" if preset_ref else "snapshot"
        colors = {
            "linked": (31, 54, 40),
            "modified": (62, 51, 28),
            "snapshot": (37, 44, 56),
            "missing_preset": (62, 36, 40),
            "preset_outdated": (65, 47, 30),
            "outdated": (65, 47, 30),
        }
        rgb = colors.get(status, (37, 44, 56))
        try:
            background_color = QtGui.QColor(*rgb)
            foreground_color = QtGui.QColor(232, 238, 246)
            background = QtGui.QBrush(background_color)
            foreground = QtGui.QBrush(foreground_color)
            selected_background = QtGui.QBrush(QtGui.QColor(74, 160, 236))
            selected_foreground = QtGui.QBrush(QtGui.QColor(255, 255, 255))
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item is not None:
                    item.setBackground(background)
                    item.setForeground(foreground)
                    item.setData(QtCore.Qt.BackgroundRole, background)
                    item.setData(QtCore.Qt.ForegroundRole, foreground)
                    item.setData(QtCore.Qt.UserRole + 51, selected_background)
                    item.setData(QtCore.Qt.UserRole + 52, selected_foreground)
                widget = self.table.cellWidget(row, column)
                if widget is not None:
                    widget.setStyleSheet(
                        "QComboBox {"
                        f"background-color: rgb({rgb[0]}, {rgb[1]}, {rgb[2]});"
                        "color: rgb(232, 238, 246);"
                        "selection-background-color: rgb(74, 160, 236);"
                        "selection-color: rgb(255, 255, 255);"
                        "border: 1px solid rgb(67, 80, 102);"
                        "}"
                        "QComboBox QAbstractItemView {"
                        "background-color: rgb(31, 38, 50);"
                        "color: rgb(232, 238, 246);"
                        "selection-background-color: rgb(74, 160, 236);"
                        "selection-color: rgb(255, 255, 255);"
                        "}"
                    )
        except Exception:
            return

    def _refresh_preset_status_indicators(self) -> None:
        versions = _subassembly_preset_version_map(self.document)
        for row in range(self.table.rowCount()):
            preset_ref = _item_text(self.table, row, COL_PRESET_REF)
            status = _item_text(self.table, row, COL_PRESET_STATUS)
            if not preset_ref:
                if not status:
                    _set_combo_text(self.table, row, COL_PRESET_STATUS, "snapshot")
                self._style_subassembly_row(row)
                continue
            library_version = str(versions.get(preset_ref, "") or "")
            row_version = _item_text(self.table, row, COL_PRESET_VERSION)
            if not library_version:
                _set_combo_text(self.table, row, COL_PRESET_STATUS, "missing_preset")
            elif status != "modified" and row_version and row_version != library_version:
                _set_combo_text(self.table, row, COL_PRESET_STATUS, "preset_outdated")
            elif status in {"", "missing_preset", "preset_outdated", "outdated"}:
                _set_combo_text(self.table, row, COL_PRESET_STATUS, "linked")
            self._style_subassembly_row(row)

    def _set_definition_combo(self, row: int, column: int, current: str) -> None:
        combo = _AssemblyTableComboBox(self.table, row)
        combo.addItems(_subassembly_definition_ref_values(self.document))
        index = combo.findText(str(current or ""))
        if index >= 0:
            combo.setCurrentIndex(index)
        self.table.setCellWidget(row, column, combo)

    def _set_preset_combo(self, row: int, column: int, current: str) -> None:
        combo = _AssemblyTableComboBox(self.table, row)
        combo.addItems(_subassembly_preset_ref_values(self.document))
        current_text = str(current or "").strip()
        index = combo.findText(current_text)
        if index < 0 and current_text:
            combo.addItem(current_text)
            index = combo.findText(current_text)
        if index >= 0:
            combo.setCurrentIndex(index)
        self.table.setCellWidget(row, column, combo)

    def _add_row(self) -> None:
        index = self.table.rowCount() + 1
        self._append_subassembly(
            TemplateSubassembly(
                subassembly_id=f"subassembly:{index}",
                kind="lane",
                subassembly_index=index,
                side="center",
                width=3.5,
                slope=-0.02,
                material="asphalt",
            )
        )

    def _delete_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self._refresh_selected_detail()

    def _selected_row(self) -> int:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if rows:
            return rows[0]
        return int(self.table.currentRow())

    def _refresh_selected_detail(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            self.detail_summary.setText("Select a Subassembly row.")
            self.detail_table.setRowCount(0)
            self.detail_preview.setPlainText("")
            self.load_detail_defaults_button.setEnabled(False)
            self.refresh_from_preset_button.setEnabled(False)
            self.detach_as_custom_button.setEnabled(False)
            self.add_bench_row_button.setEnabled(False)
            self.reset_overrides_button.setEnabled(False)
            self.apply_detail_button.setEnabled(False)
            return
        subassembly_id = _item_text(self.table, row, COL_ID)
        definition_ref = _item_text(self.table, row, COL_DEFINITION_REF)
        preset_ref = _item_text(self.table, row, COL_PRESET_REF)
        definition = _subassembly_definition_for_ref(self.document, definition_ref)
        kind = _item_text(self.table, row, COL_KIND)
        side = _item_text(self.table, row, COL_SIDE)
        params = parse_subassembly_parameters(_item_text(self.table, row, COL_PARAMETERS))
        overrides = parse_subassembly_parameters(_item_text(self.table, row, COL_OVERRIDES))
        contract_summary = _physical_body_contract_summary(
            subassembly_id=subassembly_id,
            kind=kind,
            thickness=_float(_item_text(self.table, row, COL_THICKNESS)),
            material=_item_text(self.table, row, COL_MATERIAL),
            parameters=params,
        )
        self.detail_summary.setText(
            f"{subassembly_id} | {kind} | {side} | index={_item_text(self.table, row, COL_INDEX) or row + 1} | "
            f"subassembly_ref={definition_ref or '-'}\n"
            "Assembly places Subassemblies. Edit values here only when this placement needs parameter overrides.\n"
            f"{contract_summary}"
        )
        rows = _definition_override_rows(definition, overrides) if definition is not None else _detail_parameter_rows(kind, params)
        self.detail_table.setRowCount(0)
        for key, value in rows:
            detail_row = self.detail_table.rowCount()
            self.detail_table.insertRow(detail_row)
            key_item = QtWidgets.QTableWidgetItem(str(key))
            key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.detail_table.setItem(detail_row, 0, key_item)
            self.detail_table.setItem(detail_row, 1, QtWidgets.QTableWidgetItem(str(value)))
        self.detail_preview.setPlainText(
            _definition_preview_text(definition, overrides)
            if definition is not None
            else _subassembly_preview_text(
                subassembly_id=subassembly_id,
                kind=kind,
                side=side,
                width=_float(_item_text(self.table, row, COL_WIDTH)),
                slope=_float(_item_text(self.table, row, COL_SLOPE)),
                thickness=_float(_item_text(self.table, row, COL_THICKNESS)),
                material=_item_text(self.table, row, COL_MATERIAL),
                parameters=params,
            )
        )
        self.load_detail_defaults_button.setEnabled(definition is None and kind == "ditch")
        self.refresh_from_preset_button.setEnabled(bool(preset_ref))
        self.detach_as_custom_button.setEnabled(bool(preset_ref))
        self.add_bench_row_button.setEnabled(definition is None and kind == "side_slope")
        self.reset_overrides_button.setEnabled(definition is not None and bool(overrides))
        self.apply_detail_button.setEnabled(
            definition is not None or kind in {"ditch", "side_slope", "lane", "shoulder", "pavement_layer", "subbase"}
        )

    def _load_selected_detail_defaults(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount() or _item_text(self.table, row, COL_KIND) != "ditch":
            return
        shape = _detail_value(self.detail_table, "shape") or "trapezoid"
        defaults = dict(DITCH_SHAPE_DEFAULTS.get(shape, DITCH_SHAPE_DEFAULTS["trapezoid"]))
        defaults["shape"] = shape if shape in DITCH_SHAPES else "trapezoid"
        _replace_detail_rows(self.detail_table, _detail_parameter_rows("ditch", defaults))

    def _refresh_selected_from_preset(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            return
        preset_ref = _item_text(self.table, row, COL_PRESET_REF)
        if not preset_ref:
            self.summary.setPlainText("Select a Subassembly row with a template ref before refreshing.")
            return
        preset = _subassembly_preset_for_ref(self.document, preset_ref)
        if preset is None:
            _set_combo_text(self.table, row, COL_PRESET_STATUS, "missing_preset")
            self._style_subassembly_row(row)
            self.summary.setPlainText(f"Reusable Subassembly Template was not found: {preset_ref}")
            self._refresh_selected_detail()
            return
        _apply_preset_defaults_to_row(self.table, row, preset, clear_overrides=True)
        self._style_subassembly_row(row)
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Refreshed {_item_text(self.table, row, COL_ID)} from template {preset_ref}.")

    def _detach_selected_as_custom(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            return
        subassembly_id = _item_text(self.table, row, COL_ID)
        preset_ref = _item_text(self.table, row, COL_PRESET_REF)
        if not preset_ref:
            self.summary.setPlainText(f"{subassembly_id} is already a custom snapshot.")
            return
        current_parameters = parse_subassembly_parameters(_item_text(self.table, row, COL_PARAMETERS))
        current_overrides = parse_subassembly_parameters(_item_text(self.table, row, COL_OVERRIDES))
        snapshot_parameters = dict(current_parameters)
        snapshot_parameters.update(current_overrides)
        _set_table_item_text(self.table, row, COL_PARAMETERS, serialize_subassembly_parameters(snapshot_parameters))
        _set_table_item_text(self.table, row, COL_OVERRIDES, "")
        _set_combo_text(self.table, row, COL_PRESET_REF, "")
        _set_table_item_text(self.table, row, COL_PRESET_VERSION, "")
        _set_combo_text(self.table, row, COL_PRESET_STATUS, "snapshot")
        if not _item_text(self.table, row, COL_SOURCE_INSTANCE_REF):
            _set_table_item_text(self.table, row, COL_SOURCE_INSTANCE_REF, subassembly_id)
        self._style_subassembly_row(row)
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Detached {subassembly_id} from template {preset_ref}; row is now a custom snapshot.")

    def _add_detail_bench_row(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount() or _item_text(self.table, row, COL_KIND) != "side_slope":
            return
        bench_rows = normalize_bench_rows(_detail_value(self.detail_table, "bench_rows"))
        bench_rows.append({"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": _float(_item_text(self.table, row, COL_SLOPE), -0.5)})
        _set_detail_value(self.detail_table, "bench_mode", "rows")
        _set_detail_value(self.detail_table, "bench_rows", _compact_bench_rows(bench_rows))

    def _apply_selected_detail(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            return
        kind = _item_text(self.table, row, COL_KIND)
        definition_ref = _item_text(self.table, row, COL_DEFINITION_REF)
        edited = _detail_parameters(self.detail_table)
        if definition_ref:
            definition = _subassembly_definition_for_ref(self.document, definition_ref)
            defaults = _definition_parameter_defaults(definition)
            overrides = {
                key: value
                for key, value in edited.items()
                if _override_value_changed(key, value, defaults.get(key, ""))
            }
            _set_table_item_text(self.table, row, COL_OVERRIDES, serialize_subassembly_parameters(overrides))
            if _item_text(self.table, row, COL_PRESET_REF):
                _set_combo_text(self.table, row, COL_PRESET_STATUS, "modified" if overrides else "linked")
                self._style_subassembly_row(row)
        else:
            existing = parse_subassembly_parameters(_item_text(self.table, row, COL_PARAMETERS))
            params = _merge_detail_parameters(kind, existing, edited)
            _set_table_item_text(self.table, row, COL_PARAMETERS, serialize_subassembly_parameters(params))
            if kind == "ditch":
                _set_table_item_text(self.table, row, COL_NOTES, _ditch_detail_note(params))
            elif kind == "side_slope":
                _set_table_item_text(self.table, row, COL_NOTES, _bench_detail_note(params))
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Detail applied to {_item_text(self.table, row, COL_ID)}.")

    def _reset_selected_overrides(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            return
        _set_table_item_text(self.table, row, COL_OVERRIDES, "")
        if _item_text(self.table, row, COL_PRESET_REF):
            _set_combo_text(self.table, row, COL_PRESET_STATUS, "linked")
            self._style_subassembly_row(row)
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Overrides reset for {_item_text(self.table, row, COL_ID)}.")

    def _refresh_outdated_presets(self) -> None:
        preset_versions = _subassembly_preset_version_map(self.document)
        refreshed: list[str] = []
        skipped: list[str] = []
        for row in range(self.table.rowCount()):
            subassembly_id = _item_text(self.table, row, COL_ID) or f"row:{row + 1}"
            preset_ref = _item_text(self.table, row, COL_PRESET_REF)
            if not preset_ref:
                continue
            preset = _subassembly_preset_for_ref(self.document, preset_ref)
            if preset is None:
                _set_combo_text(self.table, row, COL_PRESET_STATUS, "missing_preset")
                self._style_subassembly_row(row)
                skipped.append(f"{subassembly_id}:missing")
                continue
            status = _item_text(self.table, row, COL_PRESET_STATUS)
            row_version = _item_text(self.table, row, COL_PRESET_VERSION)
            library_version = str(preset_versions.get(preset_ref, "") or "")
            if status == "modified":
                skipped.append(f"{subassembly_id}:modified")
                continue
            if row_version == library_version and status not in {"preset_outdated", "outdated"}:
                continue
            _apply_preset_defaults_to_row(self.table, row, preset, clear_overrides=True)
            self._style_subassembly_row(row)
            refreshed.append(subassembly_id)
        self._refresh_selected_detail()
        parts = [f"Refreshed outdated template rows: {len(refreshed)}"]
        if refreshed:
            parts.append("rows=" + ", ".join(refreshed[:5]) + (f", +{len(refreshed) - 5} more" if len(refreshed) > 5 else ""))
        if skipped:
            parts.append("skipped=" + ", ".join(skipped[:5]) + (f", +{len(skipped) - 5} more" if len(skipped) > 5 else ""))
        self.summary.setPlainText("\n".join(parts))

    def _guess_missing_subassembly_refs(self) -> None:
        _guess_missing_subassembly_refs_for_panel(self)

    def _build_model_from_ui(self) -> AssemblySubassemblyModel:
        template_id = str(self.template_id_edit.text() or "template:subassembly").strip()
        subassemblies: list[TemplateSubassembly] = []
        for row in range(self.table.rowCount()):
            subassemblies.append(
                TemplateSubassembly(
                    subassembly_id=_item_text(self.table, row, COL_ID) or f"subassembly:{row + 1}",
                    definition_ref=_item_text(self.table, row, COL_DEFINITION_REF),
                    preset_ref=_item_text(self.table, row, COL_PRESET_REF),
                    preset_version=_item_text(self.table, row, COL_PRESET_VERSION),
                    preset_status=_item_text(self.table, row, COL_PRESET_STATUS),
                    source_instance_ref=_item_text(self.table, row, COL_SOURCE_INSTANCE_REF),
                    kind=_item_text(self.table, row, COL_KIND) or "lane",
                    subassembly_index=int(_float(_item_text(self.table, row, COL_INDEX), row + 1)),
                    side=_item_text(self.table, row, COL_SIDE) or "center",
                    width=_float(_item_text(self.table, row, COL_WIDTH)),
                    slope=_float(_item_text(self.table, row, COL_SLOPE)),
                    thickness=_float(_item_text(self.table, row, COL_THICKNESS)),
                    material=_item_text(self.table, row, COL_MATERIAL),
                    target_ref=_item_text(self.table, row, COL_TARGET_REF),
                    parameter_overrides=parse_subassembly_parameters(_item_text(self.table, row, COL_OVERRIDES)),
                    parameters=parse_subassembly_parameters(_item_text(self.table, row, COL_PARAMETERS)),
                    notes=_item_text(self.table, row, COL_NOTES),
                    enabled=_truthy(_item_text(self.table, row, COL_ENABLED)),
                )
            )
        return AssemblySubassemblyModel(
            schema_version=1,
            project_id=_project_id(find_project(self.document)),
            assembly_id=str(self.assembly_id_edit.text() or "assembly:subassembly-main").strip(),
            active_template_id=template_id,
            template_rows=[
                SubassemblySectionTemplate(
                    template_id=template_id,
                    template_kind="roadway",
                    template_index=1,
                    label=template_id,
                    subassembly_rows=subassemblies,
                    notes="Subassembly-based assembly source.",
                )
            ],
        )

    def _validate(self) -> list[str]:
        model = self._build_model_from_ui()
        messages = _validate_subassembly_model(
            model,
            available_definition_ids=_subassembly_definition_ref_set(self.document),
            available_preset_ids=_subassembly_preset_ref_set(self.document),
            preset_versions=_subassembly_preset_version_map(self.document),
        )
        status = "ok" if not any(message.startswith("ERROR") for message in messages) else "error"
        self.summary.setPlainText("Validation: " + status + "\n" + ("\n".join(messages) if messages else "No diagnostics."))
        return messages

    def _apply(self) -> None:
        messages = self._validate()
        if any(message.startswith("ERROR") for message in messages):
            _show_message(self.form, "Assembly / Subassembly", "Validation failed. Fix errors before Apply.")
            return
        model = self._build_model_from_ui()
        try:
            self.assembly_obj = apply_v1_assembly_subassembly_model(
                document=self.document,
                assembly_model=model,
                assembly_obj=self.assembly_obj,
            )
            self.summary.setPlainText(
                f"Apply complete.\nAssembly/Subassembly object: {getattr(self.assembly_obj, 'Label', '')}\nSubassemblies: {self.table.rowCount()}"
            )
            _show_message(self.form, "Assembly / Subassembly", "Assembly / Subassembly source applied.")
        except Exception as exc:
            self.summary.setPlainText(f"Apply failed: {exc}")
            _show_message(self.form, "Assembly / Subassembly", f"Apply failed: {exc}")

    def _show_section_preview(self) -> None:
        try:
            self._draw_section_preview(
                self._build_model_from_ui(),
                definition_library=_subassembly_library_model(self.document),
            )
        except Exception as exc:
            self.summary.setPlainText(f"Section preview failed: {exc}")
            _show_message(self.form, "Assembly / Subassembly", f"Section preview failed:\n{exc}")
            return
        self.summary.setPlainText("Section preview updated in the panel.")

    def _add_section_preview_label(self, scene, text: str, anchor_x: float, anchor_y: float, used_rects) -> None:
        label = scene.addText(str(text or ""))
        label.setDefaultTextColor(QtGui.QColor("#f8fafc"))
        font = label.font()
        font.setPointSize(8)
        label.setFont(font)
        label.setZValue(30.0)

        offsets = (
            (6.0, -18.0),
            (8.0, 6.0),
            (-42.0, -18.0),
            (-42.0, 6.0),
            (14.0, -34.0),
            (14.0, 22.0),
            (-66.0, -34.0),
            (-66.0, 22.0),
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

    def _draw_section_preview(self, assembly_model: AssemblySubassemblyModel, *, definition_library=None) -> None:
        scene = self.section_preview_scene
        scene.clear()
        template = _active_template(assembly_model)
        rows = [
            row
            for row in list(getattr(template, "subassembly_rows", []) or [])
            if bool(getattr(row, "enabled", True))
        ]
        segments = _assembly_section_preview_segments(rows, definition_library=definition_library)
        if not segments:
            text = scene.addText("No enabled Assembly/Subassembly rows are available for preview.")
            text.setDefaultTextColor(QtGui.QColor("#d8e0ea"))
            self.section_preview_status.setText("Preview: no enabled rows.")
            return
        scale = 42.0
        pen_axis = QtGui.QPen(QtGui.QColor("#6f7f95"))
        pen_axis.setStyle(QtCore.Qt.DashLine)
        pen_top = QtGui.QPen(QtGui.QColor("#ffd45a"))
        pen_top.setWidthF(2.4)
        pen_shape = QtGui.QPen(QtGui.QColor("#35c878"))
        pen_shape.setWidthF(1.2)
        brush_shape = QtGui.QBrush(QtGui.QColor(53, 200, 120, 55))
        pen_point = QtGui.QPen(QtGui.QColor("#111111"))
        brush_point = QtGui.QBrush(QtGui.QColor("#ffd45a"))
        scene.addLine(-320, 0, 320, 0, pen_axis)
        scene.addLine(0, -160, 0, 120, pen_axis)
        used_label_rects = []
        for segment in segments:
            row = segment["row"]
            side_label = str(segment["side"])
            points = list(segment["points"])
            topline = list(segment.get("topline", []) or points[:2])
            polygon = QtGui.QPolygonF([QtCore.QPointF(float(x) * scale, -float(z) * scale) for x, z in points])
            if len(points) >= 3:
                scene.addPolygon(polygon, pen_shape, brush_shape)
            for start, end in zip(topline, topline[1:]):
                scene.addLine(start[0] * scale, -start[1] * scale, end[0] * scale, -end[1] * scale, pen_top)
            for x, z in topline:
                scene.addEllipse(x * scale - 3.0, -z * scale - 3.0, 6.0, 6.0, pen_point, brush_point)
            top_end = topline[-1]
            self._add_section_preview_label(
                scene,
                f"{str(getattr(row, 'subassembly_id', '') or '')} ({side_label})",
                top_end[0] * scale,
                -top_end[1] * scale,
                used_label_rects,
            )
        bounds = scene.itemsBoundingRect().adjusted(-28, -28, 28, 28)
        scene.setSceneRect(bounds)
        try:
            self.section_preview_view.reset_zoom_for_bounds(bounds)
        except Exception:
            pass
        self.section_preview_status.setText(f"Preview: {len(rows)} row(s), {len(segments)} segment(s).")

    def _close(self) -> None:
        if Gui is not None and hasattr(Gui, "Control"):
            Gui.Control.closeDialog()


class _AssemblySectionPreviewView(QtWidgets.QGraphicsView):
    """Graphics view with mouse-wheel zoom for the Assembly/Subassembly section preview."""

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

    def reset_zoom_for_bounds(self, bounds) -> None:
        try:
            self.resetTransform()
            self._zoom_factor = 1.0
            self.fitInView(bounds, QtCore.Qt.KeepAspectRatio)
        except Exception:
            pass


__all__ = [
    "_AssemblyTableComboBox",
    "V1AssemblySubassemblyEditorTaskPanel",
    "_AssemblySectionPreviewView",
    "configure_assembly_subassembly_editor_task_panel_runtime",
]

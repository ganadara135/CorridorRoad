"""Drainage editor presentation for CorridorRoad v1."""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets


def configure_drainage_editor_task_panel_runtime(bindings) -> None:
    """Bind command/controller collaborators without importing the command module."""

    protected = {
        "V1DrainageEditorTaskPanel",
        "configure_drainage_editor_task_panel_runtime",
    }
    for name, value in dict(bindings or {}).items():
        if name.startswith("__") or name in protected:
            continue
        globals()[name] = value


# Explicit runtime collaborators are replaced by the command callback map.
App = None
DISABLED_COMBO_STYLE = None
DRAINAGE_PRESETS = None
DrainageElementRow = None
DrainageFlowRoute = None
DrainageModel = None
DrainagePolicySet = None
DrainageValidationService = None
ELEMENT_ASSEMBLY_COLUMN = None
ELEMENT_KIND_CHOICES = None
ELEMENT_KIND_COLUMN = None
ELEMENT_POLICY_COLUMN = None
ELEMENT_STRUCTURE_COLUMN = None
FLOW_INTENT_CHOICES = None
FLOW_ROUTE_FROM_COLUMN = None
FLOW_ROUTE_OUTLET_COLUMN = None
FLOW_ROUTE_TO_COLUMN = None
Gui = None
INVALID_COMBO_STYLE = None
SIDE_CHOICES = None
_assembly_disabled_for_kind = None
_combo_source_text = None
_display_connection_point_ref = None
_display_prefixed_id = None
_display_source_ref = None
_document_station_range = None
_document_station_values = None
_drainage_element_is_outlet_kind = None
_element_subassembly_ref = None
_float_value = None
_format_float = None
_format_validation_result = None
_gui_available = None
_item_text = None
_preset_load_summary = None
_preset_pair_self_check_text = None
_preset_station_range_self_check_text = None
_preset_structure_self_check_text = None
_project_id = None
_role_suffix = None
_show_message = None
_source_prefixed_id = None
_source_ref_from_display = None
_source_structure_ref = None
_structure_connection_point_by_ref = None
_structure_disabled_for_kind = None
_unique_texts = None
apply_clickable_tab_style = None
apply_v1_drainage_model = None
build_drainage_pipeline_segment_candidates = None
build_drainage_review_output = None
drainage_preset_model_from_document = None
drainage_preset_names = None
find_project = None
find_v1_drainage_model = None
find_v1_region_model = None
find_v1_structure_model = None
show_drainage_pipeline_networks_preview_object = None
show_drainage_pipeline_segment_preview_object = None
starter_drainage_model_from_document = None
to_drainage_model = None
to_region_model = None
to_structure_model = None


class V1DrainageEditorTaskPanel:
    """Table-based v1 Drainage source editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.drainage_obj = find_v1_drainage_model(self.document)
        self.form = self._build_ui()
        self._load_existing_or_starter()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._apply(close_after=True)

    def reject(self):
        if _gui_available():
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("ParametricRoad v1 - Drainage")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Drainage")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        self._preset_combo = QtWidgets.QComboBox()
        self._preset_combo.addItem("")
        self._preset_combo.addItems(drainage_preset_names())
        self._preset_combo.setCurrentIndex(0)
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

        source_row = QtWidgets.QHBoxLayout()
        source_row.addWidget(QtWidgets.QLabel("Model ID"))
        self._model_id = QtWidgets.QLineEdit("drainage:main")
        source_row.addWidget(self._model_id, 1)
        layout.addLayout(source_row)

        self._tabs = QtWidgets.QTabWidget()
        apply_clickable_tab_style(self._tabs, "DrainageEditorTabs")
        self._element_table = self._table(
            [
                "Element ID",
                "Kind",
                "Side",
                "Start STA",
                "End STA",
                "Subassembly",
                "Policy",
                "Structure Ref",
            ]
        )
        self._policy_table = self._table(
            ["Policy ID", "Flow Intent", "Min Grade", "Low Point", "Collection", "Discharge", "Earthwork Priority"]
        )
        self._flow_route_table = self._table(
            ["Flow Route ID", "From Element", "To Element", "Outlet", "Direction", "Risk", "Notes"]
        )
        self._configure_flow_route_table()
        self._element_table.cellChanged.connect(lambda row, column: self._on_element_table_changed(row, column))
        self._policy_table.cellChanged.connect(lambda _row, _column: self._refresh_element_policy_combos())
        self._flow_route_table.cellChanged.connect(lambda _row, _column: self._update_flow_route_preview())
        self._flow_route_table.itemSelectionChanged.connect(self._update_flow_route_preview)
        self._flow_route_table.cellDoubleClicked.connect(lambda row, _column: self._show_flow_route_segment(row))
        self._tabs.addTab(self._element_table, "Elements")
        self._tabs.addTab(self._policy_table, "Policies")
        self._tabs.addTab(self._flow_route_table, "Flow Routes")
        self._tabs.currentChanged.connect(lambda _index: self._update_tab_action_visibility())
        layout.addWidget(self._tabs, 1)

        self._flow_route_preview = QtWidgets.QLabel("")
        self._flow_route_preview.setWordWrap(True)
        layout.addWidget(self._flow_route_preview)

        edit_rows = QtWidgets.QVBoxLayout()
        edit_rows.setSpacing(4)
        edit_row_top = QtWidgets.QHBoxLayout()
        edit_row_bottom = QtWidgets.QHBoxLayout()
        self._add_element_button = QtWidgets.QPushButton("Add Element")
        self._add_element_button.clicked.connect(self._add_element_row)
        edit_row_top.addWidget(self._add_element_button)
        self._add_left_ditch_button = QtWidgets.QPushButton("Add Left Ditch")
        self._add_left_ditch_button.clicked.connect(lambda: self._add_ditch_row("left"))
        edit_row_top.addWidget(self._add_left_ditch_button)
        self._add_right_ditch_button = QtWidgets.QPushButton("Add Right Ditch")
        self._add_right_ditch_button.clicked.connect(lambda: self._add_ditch_row("right"))
        edit_row_top.addWidget(self._add_right_ditch_button)
        edit_row_top.addStretch(1)
        self._add_inlet_button = QtWidgets.QPushButton("Add Inlet")
        self._add_inlet_button.clicked.connect(self._add_inlet_row)
        edit_row_bottom.addWidget(self._add_inlet_button)
        self._add_outlet_button = QtWidgets.QPushButton("Add Outlet")
        self._add_outlet_button.clicked.connect(self._add_outlet_row)
        edit_row_bottom.addWidget(self._add_outlet_button)
        self._add_cross_drain_button = QtWidgets.QPushButton("Add Cross Drain")
        self._add_cross_drain_button.clicked.connect(self._add_cross_drain_row)
        edit_row_bottom.addWidget(self._add_cross_drain_button)
        self._add_policy_button = QtWidgets.QPushButton("Add Policy")
        self._add_policy_button.clicked.connect(self._add_policy_row)
        edit_row_bottom.addWidget(self._add_policy_button)
        self._add_flow_route_button = QtWidgets.QPushButton("Add Flow Route")
        self._add_flow_route_button.clicked.connect(self._add_flow_route_row)
        edit_row_bottom.addWidget(self._add_flow_route_button)
        self._delete_button = QtWidgets.QPushButton("Delete Selected")
        self._delete_button.clicked.connect(self._delete_selected_rows)
        edit_row_bottom.addWidget(self._delete_button)
        edit_row_bottom.addStretch(1)
        edit_rows.addLayout(edit_row_top)
        edit_rows.addLayout(edit_row_bottom)
        layout.addLayout(edit_rows)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setFixedHeight(90)
        layout.addWidget(self._status)

        action_row = QtWidgets.QHBoxLayout()
        validate_button = QtWidgets.QPushButton("Validate")
        validate_button.clicked.connect(self._validate)
        action_row.addWidget(validate_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        action_row.addWidget(apply_button)
        show_flow_network_button = QtWidgets.QPushButton("Show Flow Network")
        show_flow_network_button.clicked.connect(self._show_flow_network)
        action_row.addWidget(show_flow_network_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        self._update_preset_note()
        self._update_tab_action_visibility()
        return widget

    def _table(self, headers: list[str]):
        table = QtWidgets.QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        try:
            table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        return table

    def _configure_flow_route_table(self) -> None:
        widths = {
            0: 120,
            FLOW_ROUTE_FROM_COLUMN: 180,
            FLOW_ROUTE_TO_COLUMN: 180,
            FLOW_ROUTE_OUTLET_COLUMN: 180,
            4: 120,
            5: 90,
            6: 220,
        }
        try:
            self._flow_route_table.horizontalHeader().setMinimumSectionSize(90)
        except Exception:
            pass
        for column, width in widths.items():
            try:
                self._flow_route_table.setColumnWidth(column, width)
            except Exception:
                pass

    def _load_existing_or_starter(self) -> None:
        model = to_drainage_model(self.drainage_obj)
        if model is None:
            model = starter_drainage_model_from_document(self.document)
            self._replace_model(model)
            self._set_status("No DrainageModel source object is available. Tables are empty; add rows or load a preset, then Apply.")
            return
        self._replace_model(model)
        self._set_status(f"Loaded DrainageModel from {self.drainage_obj.Label}.")

    def _load_selected_preset(self) -> None:
        try:
            preset_name = str(self._preset_combo.currentText() or "").strip()
            if not preset_name:
                self._set_status("Select a Drainage preset before loading preset data.")
                return
            model = drainage_preset_model_from_document(preset_name, document=self.document)
            self._replace_model(model)
            self._set_status(
                "\n".join(
                    value
                    for value in [
                        f"Drainage preset loaded: {preset_name}. Apply when ready.",
                        _preset_load_summary(model),
                        self._preset_station_range_self_check_text(model),
                        self._preset_structure_self_check_text(preset_name),
                        _preset_pair_self_check_text(model, self._structure_model()),
                    ]
                    if value
                )
            )
        except Exception as exc:
            self._set_status(f"Drainage preset was not loaded:\n{exc}")

    def _update_preset_note(self) -> None:
        if not hasattr(self, "_preset_note"):
            return
        preset = DRAINAGE_PRESETS.get(str(self._preset_combo.currentText() or ""), {})
        self._preset_note.setText(str(preset.get("note", "") or ""))

    def _replace_model(self, model: DrainageModel) -> None:
        self._model_id.setText(str(getattr(model, "drainage_model_id", "") or "drainage:main"))
        self._element_table.setRowCount(0)
        for row in list(getattr(model, "element_rows", []) or []):
            self._append_element_row(row)
        self._policy_table.setRowCount(0)
        for row in list(getattr(model, "policy_rows", []) or []):
            self._append_policy_row(row)
        self._flow_route_table.setRowCount(0)
        for row in list(getattr(model, "flow_route_rows", []) or []):
            self._append_flow_route_row(row)
        self._refresh_validation_cell_styles()

    def _append_element_row(self, row: DrainageElementRow | None = None) -> None:
        row = row or self._default_ditch_row("right")
        index = self._element_table.rowCount()
        self._element_table.insertRow(index)
        values = [
            _display_prefixed_id(row.drainage_element_id, "drainage:"),
            row.element_kind,
            getattr(row, "side", "") or "",
            _format_float(row.station_start),
            _format_float(row.station_end),
            _element_subassembly_ref(row),
            _display_prefixed_id(row.policy_set_ref, "drainage-policy:"),
            _display_prefixed_id(row.structure_ref, "structure:"),
        ]
        for col, value in enumerate(values):
            if col == 1:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(ELEMENT_KIND_CHOICES)
                combo.setCurrentText(str(value or "ditch"))
                try:
                    combo.currentTextChanged.connect(
                        lambda _text, row_index=index: self._on_element_kind_changed(row_index)
                    )
                except Exception:
                    pass
                self._element_table.setCellWidget(index, col, combo)
            elif col == 2:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(SIDE_CHOICES)
                combo.setCurrentText(str(value or ""))
                self._element_table.setCellWidget(index, col, combo)
            elif col == ELEMENT_POLICY_COLUMN:
                self._set_combo_cell(
                    self._element_table,
                    index,
                    col,
                    _source_prefixed_id(value, "drainage-policy:"),
                    self._policy_ref_choices(),
                    display_refs=True,
                )
            elif col == ELEMENT_STRUCTURE_COLUMN:
                self._set_combo_cell(
                    self._element_table,
                    index,
                    col,
                    _source_structure_ref(value),
                    self._structure_ref_choices(),
                    display_refs=True,
                )
            else:
                self._element_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))
        self._update_element_cell_states(index)
        self._refresh_flow_route_element_combos()
        self._refresh_validation_cell_styles()

    def _default_ditch_row(self, side: str) -> DrainageElementRow:
        normalized_side = str(side or "right").strip().lower() or "right"
        if normalized_side not in {"left", "right"}:
            normalized_side = "right"
        base_id = f"drainage:side-ditch-{normalized_side}"
        return DrainageElementRow(
            drainage_element_id=self._unique_element_id(base_id),
            element_kind="ditch",
            side=normalized_side,
            subassembly_ref=f"ditch:{normalized_side}",
            station_start=0.0,
            station_end=100.0,
            policy_set_ref=self._first_policy_ref(),
        )

    def _default_structure_element_row(
        self,
        *,
        base_id: str,
        element_kind: str,
        structure_keyword: str,
        policy_keyword: str,
        side: str = "right",
    ) -> DrainageElementRow:
        structure_ref = self._first_structure_ref_matching(structure_keyword)
        station_start, station_end = self._structure_station_span(structure_ref)
        return DrainageElementRow(
            drainage_element_id=self._unique_numbered_element_id(base_id),
            element_kind=element_kind,
            side=side,
            station_start=station_start,
            station_end=station_end,
            structure_ref=structure_ref,
            policy_set_ref=self._first_policy_ref_matching(policy_keyword) or self._first_policy_ref(),
        )

    def _unique_element_id(self, base_id: str) -> str:
        existing = {
            _source_prefixed_id(_item_text(self._element_table, index, 0), "drainage:")
            for index in range(self._element_table.rowCount())
            if _item_text(self._element_table, index, 0)
        }
        if base_id not in existing:
            return base_id
        suffix = 2
        while f"{base_id}:{suffix}" in existing:
            suffix += 1
        return f"{base_id}:{suffix}"

    def _unique_numbered_element_id(self, base_id: str) -> str:
        normalized = _source_prefixed_id(base_id, "drainage:")
        existing = {
            _source_prefixed_id(_item_text(self._element_table, index, 0), "drainage:")
            for index in range(self._element_table.rowCount())
            if _item_text(self._element_table, index, 0)
        }
        if normalized not in existing:
            return normalized
        root = normalized.rsplit("-", 1)[0] if "-" in normalized.rsplit(":", 1)[-1] else normalized
        suffix = 2
        while f"{root}-{suffix:02d}" in existing:
            suffix += 1
        return f"{root}-{suffix:02d}"

    def _append_policy_row(self, row: DrainagePolicySet | None = None) -> None:
        row = row or DrainagePolicySet(
            policy_set_id=f"drainage-policy:{self._policy_table.rowCount() + 1}",
            flow_intent="collect_and_convey",
        )
        index = self._policy_table.rowCount()
        self._policy_table.insertRow(index)
        values = [
            _display_prefixed_id(row.policy_set_id, "drainage-policy:"),
            row.flow_intent,
            row.min_grade_rule,
            row.low_point_rule,
            row.collection_rule,
            row.discharge_rule,
            row.earthwork_priority,
        ]
        for col, value in enumerate(values):
            if col == 1:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(FLOW_INTENT_CHOICES)
                combo.setCurrentText(str(value or "collect_and_convey"))
                self._policy_table.setCellWidget(index, col, combo)
            else:
                self._policy_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))
        self._refresh_element_policy_combos()

    def _append_flow_route_row(self, row: DrainageFlowRoute | None = None) -> None:
        row = row or DrainageFlowRoute(
            flow_route_id=f"flow-route:{self._flow_route_table.rowCount() + 1}",
        )
        index = self._flow_route_table.rowCount()
        self._flow_route_table.insertRow(index)
        values = [
            _display_prefixed_id(row.flow_route_id, "flow-route:"),
            row.from_element_ref,
            row.to_element_ref,
            row.outlet_ref,
            row.direction,
            row.risk_level,
            row.notes,
        ]
        for col, value in enumerate(values):
            if col == FLOW_ROUTE_FROM_COLUMN or col == FLOW_ROUTE_TO_COLUMN:
                self._set_combo_cell(self._flow_route_table, index, col, str(value), self._element_ref_choices(), display_refs=True)
            elif col == FLOW_ROUTE_OUTLET_COLUMN:
                self._set_combo_cell(self._flow_route_table, index, col, str(value), self._outlet_ref_choices(), display_refs=True)
            else:
                self._flow_route_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))
        self._update_flow_route_outlet_cell_state(index)
        self._update_flow_route_preview()

    def _add_element_row(self) -> None:
        self._append_element_row()
        self._set_status("Added Drainage element row.")

    def _add_ditch_row(self, side: str) -> None:
        row = self._default_ditch_row(side)
        self._append_element_row(row)
        self._set_status(f"Added {row.side} side ditch row.")

    def _add_inlet_row(self) -> None:
        row = self._default_structure_element_row(
            base_id="drainage:inlet-01",
            element_kind="inlet_reference",
            structure_keyword="inlet",
            policy_keyword="inlet",
        )
        self._append_element_row(row)
        self._set_status("Added inlet reference row.")

    def _add_outlet_row(self) -> None:
        row = self._default_structure_element_row(
            base_id="drainage:outlet-01",
            element_kind="outfall_reference",
            structure_keyword="outlet",
            policy_keyword="outfall",
        )
        self._append_element_row(row)
        self._set_status("Added outlet reference row.")

    def _add_cross_drain_row(self) -> None:
        row = self._default_structure_element_row(
            base_id="drainage:culvert-01",
            element_kind="culvert_reference",
            structure_keyword="culvert",
            policy_keyword="cross",
            side="center",
        )
        self._append_element_row(row)
        self._set_status("Added cross-drain culvert reference row.")

    def _add_policy_row(self) -> None:
        self._append_policy_row()
        self._set_status("Added Drainage policy row.")

    def _add_flow_route_row(self) -> None:
        self._append_flow_route_row()
        self._set_status("Added Drainage flow route row.")

    def _delete_selected_rows(self) -> None:
        table = self._tabs.currentWidget()
        if table is None:
            return
        rows = sorted({item.row() for item in list(table.selectedItems() or [])}, reverse=True)
        if not rows and table.currentRow() >= 0:
            rows = [table.currentRow()]
        for row_index in rows:
            table.removeRow(row_index)
        if table is self._element_table:
            self._refresh_flow_route_element_combos()
        if table is self._policy_table:
            self._refresh_element_policy_combos()
        if table is self._flow_route_table:
            self._update_flow_route_preview()
        self._refresh_validation_cell_styles()
        self._set_status(f"Deleted {len(rows)} row(s).")

    def _update_tab_action_visibility(self) -> None:
        current = self._tabs.currentWidget() if hasattr(self, "_tabs") else None
        is_elements = current is getattr(self, "_element_table", None)
        is_policies = current is getattr(self, "_policy_table", None)
        is_flow_routes = current is getattr(self, "_flow_route_table", None)
        for button in (
            getattr(self, "_add_element_button", None),
            getattr(self, "_add_left_ditch_button", None),
            getattr(self, "_add_right_ditch_button", None),
            getattr(self, "_add_inlet_button", None),
            getattr(self, "_add_outlet_button", None),
            getattr(self, "_add_cross_drain_button", None),
        ):
            if button is not None:
                button.setVisible(is_elements)
        if getattr(self, "_add_policy_button", None) is not None:
            self._add_policy_button.setVisible(is_policies)
        if getattr(self, "_add_flow_route_button", None) is not None:
            self._add_flow_route_button.setVisible(is_flow_routes)

    def _validate(self) -> None:
        try:
            model = self._model_from_tables()
            result = DrainageValidationService().validate(
                model,
                region_model=self._region_model(),
                structure_model=self._structure_model(),
            )
            self._refresh_validation_cell_styles()
            self._set_status(_format_validation_result(result, model))
        except Exception as exc:
            self._set_status(f"Drainage validation failed:\n{exc}")

    def _show_flow_network(self) -> None:
        try:
            model = self._model_from_tables()
            result = DrainageValidationService().validate(
                model,
                region_model=self._region_model(),
                structure_model=self._structure_model(),
            )
            if result.status == "error":
                self._set_status(_format_validation_result(result, model))
                _show_message(self.form, "Drainage", "Drainage Flow Network was not shown because validation has errors.")
                return
            self.drainage_obj = apply_v1_drainage_model(document=self.document, drainage_model=model)
            output = build_drainage_review_output(self.document)
            preview = show_drainage_pipeline_networks_preview_object(self.document, output=output)
            network_count = len(list(getattr(output, "pipeline_network_rows", []) or []))
            segment_count = len(list(getattr(output, "pipeline_segment_rows", []) or []))
            self._set_status(
                _format_validation_result(result, model)
                + "\n\n"
                + "\n".join(
                    [
                        "Drainage Flow Network preview shown.",
                        f"Applied to: {self.drainage_obj.Label}",
                        f"Preview object: {getattr(preview, 'Label', getattr(preview, 'Name', ''))}",
                        f"Networks: {network_count}",
                        f"Pipeline segments: {segment_count}",
                    ]
                )
            )
        except Exception as exc:
            self._set_status(f"Drainage Flow Network preview failed:\n{exc}")
            _show_message(self.form, "Drainage", f"Drainage Flow Network preview failed.\n{exc}")

    def _show_flow_route_segment(self, row_index: int) -> None:
        try:
            if row_index < 0 or row_index >= self._flow_route_table.rowCount():
                return
            route_ref = _source_prefixed_id(_item_text(self._flow_route_table, row_index, 0), "flow-route:")
            model = self._model_from_tables()
            result = DrainageValidationService().validate(
                model,
                region_model=self._region_model(),
                structure_model=self._structure_model(),
            )
            if result.status == "error":
                self._set_status(_format_validation_result(result, model))
                _show_message(self.form, "Drainage", "Flow Route was not shown because validation has errors.")
                return
            self.drainage_obj = apply_v1_drainage_model(document=self.document, drainage_model=model)
            output = build_drainage_review_output(self.document)
            segment_rows = list(getattr(output, "pipeline_segment_rows", []) or [])
            segment_index = next(
                (
                    index
                    for index, segment in enumerate(segment_rows)
                    if str(getattr(segment, "flow_route_ref", "") or "") == route_ref
                ),
                -1,
            )
            if segment_index < 0:
                self._set_status(
                    _format_validation_result(result, model)
                    + f"\n\nFlow Route preview not available for {route_ref}.\n"
                    + "This row does not resolve to a Structure-backed pipe segment."
                )
                return
            preview = show_drainage_pipeline_segment_preview_object(
                self.document,
                row_index=segment_index,
                output=output,
            )
            self._set_status(
                _format_validation_result(result, model)
                + "\n\n"
                + "\n".join(
                    [
                        "Flow Route pipe segment preview shown.",
                        f"Flow Route: {route_ref}",
                        f"Preview object: {getattr(preview, 'Label', getattr(preview, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            self._set_status(f"Flow Route preview failed:\n{exc}")
            _show_message(self.form, "Drainage", f"Flow Route preview failed.\n{exc}")

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            model = self._model_from_tables()
            result = DrainageValidationService().validate(
                model,
                region_model=self._region_model(),
                structure_model=self._structure_model(),
            )
            if result.status == "error":
                self._set_status(_format_validation_result(result, model))
                _show_message(self.form, "Drainage", "Drainage was not applied because validation has errors.")
                return False
            self.drainage_obj = apply_v1_drainage_model(document=self.document, drainage_model=model)
            self._set_status(_format_validation_result(result, model) + f"\n\nApplied to: {self.drainage_obj.Label}")
            _show_message(self.form, "Drainage", f"Drainage has been applied.\nElements: {len(model.element_rows)}")
            if close_after and _gui_available():
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(f"Drainage was not applied:\n{exc}")
            _show_message(self.form, "Drainage", f"Drainage was not applied.\n{exc}")
            return False

    def _model_from_tables(self) -> DrainageModel:
        return DrainageModel(
            schema_version=1,
            project_id=_project_id(find_project(self.document)),
            drainage_model_id=str(self._model_id.text() or "drainage:main"),
            label="Drainage",
            element_rows=self._element_rows(),
            policy_rows=self._policy_rows(),
            flow_route_rows=self._flow_route_rows(),
        )

    def _element_rows(self) -> list[DrainageElementRow]:
        rows: list[DrainageElementRow] = []
        for index in range(self._element_table.rowCount()):
            element_kind = _item_text(self._element_table, index, ELEMENT_KIND_COLUMN) or "ditch"
            rows.append(
                DrainageElementRow(
                    drainage_element_id=_source_prefixed_id(
                        _item_text(self._element_table, index, 0),
                        "drainage:",
                        f"element:{index + 1}",
                    ),
                    element_kind=element_kind,
                    region_ref="",
                    side=_item_text(self._element_table, index, 2),
                    station_start=_float_value(_item_text(self._element_table, index, 3)),
                    station_end=_float_value(_item_text(self._element_table, index, 4)),
                    subassembly_ref="" if _assembly_disabled_for_kind(element_kind) else _item_text(
                        self._element_table,
                        index,
                        ELEMENT_ASSEMBLY_COLUMN,
                    ),
                    policy_set_ref=_source_ref_from_display(
                        _combo_source_text(self._element_table, index, ELEMENT_POLICY_COLUMN),
                        self._policy_ref_choices(),
                        default_prefix="drainage-policy:",
                    ),
                    structure_ref="" if _structure_disabled_for_kind(element_kind) else _source_ref_from_display(
                        _combo_source_text(self._element_table, index, ELEMENT_STRUCTURE_COLUMN),
                        self._structure_ref_choices(),
                        default_prefix="structure:",
                    ),
                    connection_point_ref="",
                )
            )
        return rows

    def _policy_rows(self) -> list[DrainagePolicySet]:
        rows: list[DrainagePolicySet] = []
        for index in range(self._policy_table.rowCount()):
            rows.append(
                DrainagePolicySet(
                    policy_set_id=_source_prefixed_id(
                        _item_text(self._policy_table, index, 0),
                        "drainage-policy:",
                        str(index + 1),
                    ),
                    flow_intent=_item_text(self._policy_table, index, 1),
                    min_grade_rule=_item_text(self._policy_table, index, 2),
                    low_point_rule=_item_text(self._policy_table, index, 3),
                    collection_rule=_item_text(self._policy_table, index, 4),
                    discharge_rule=_item_text(self._policy_table, index, 5),
                    earthwork_priority=_item_text(self._policy_table, index, 6),
                )
            )
        return rows

    def _flow_route_rows(self) -> list[DrainageFlowRoute]:
        rows: list[DrainageFlowRoute] = []
        for index in range(self._flow_route_table.rowCount()):
            rows.append(
                DrainageFlowRoute(
                    flow_route_id=_source_prefixed_id(
                        _item_text(self._flow_route_table, index, 0),
                        "flow-route:",
                        str(index + 1),
                    ),
                    from_element_ref=_source_ref_from_display(
                        _combo_source_text(self._flow_route_table, index, FLOW_ROUTE_FROM_COLUMN),
                        self._element_ref_choices(),
                        default_prefix="drainage:",
                    ),
                    to_element_ref=_source_ref_from_display(
                        _combo_source_text(self._flow_route_table, index, FLOW_ROUTE_TO_COLUMN),
                        self._element_ref_choices(),
                        default_prefix="drainage:",
                    ),
                    outlet_ref="" if not self._flow_route_outlet_enabled(index) else _source_ref_from_display(
                        _combo_source_text(self._flow_route_table, index, FLOW_ROUTE_OUTLET_COLUMN),
                        self._outlet_ref_choices(),
                    ),
                    direction=_item_text(self._flow_route_table, index, 4),
                    risk_level=_item_text(self._flow_route_table, index, 5),
                    notes=_item_text(self._flow_route_table, index, 6),
                )
            )
        return rows

    def _first_policy_ref(self) -> str:
        return _source_prefixed_id(_item_text(self._policy_table, 0, 0), "drainage-policy:") if self._policy_table.rowCount() else ""

    def _first_policy_ref_matching(self, keyword: str) -> str:
        needle = str(keyword or "").strip().lower()
        if not needle:
            return ""
        for row in range(self._policy_table.rowCount()):
            values = [
                _item_text(self._policy_table, row, column)
                for column in range(self._policy_table.columnCount())
            ]
            if needle in " ".join(values).lower():
                return _source_prefixed_id(_item_text(self._policy_table, row, 0), "drainage-policy:")
        return ""

    def _first_structure_ref_matching(self, keyword: str) -> str:
        needle = str(keyword or "").strip().lower()
        model = self._structure_model()
        for row in list(getattr(model, "structure_rows", []) or []):
            values = [
                getattr(row, "structure_id", ""),
                getattr(row, "structure_kind", ""),
                getattr(row, "structure_role", ""),
                getattr(row, "native_type", ""),
                getattr(row, "geometry_source", ""),
            ]
            if needle and needle in " ".join(str(value or "") for value in values).lower():
                return str(getattr(row, "structure_id", "") or "").strip()
        return ""

    def _structure_station_span(self, structure_ref: str) -> tuple[float, float]:
        model = self._structure_model()
        for row in list(getattr(model, "structure_rows", []) or []):
            if str(getattr(row, "structure_id", "") or "").strip() != str(structure_ref or "").strip():
                continue
            placement = getattr(row, "placement", None)
            start = _float_value(getattr(placement, "station_start", 0.0))
            end = _float_value(getattr(placement, "station_end", start))
            return min(start, end), max(start, end)
        start, end = _document_station_range(self.document)
        if end <= start:
            return start, end
        mid = start + (end - start) * 0.5
        half_width = min(1.0, max((end - start) * 0.01, 0.25))
        return max(start, mid - half_width), min(end, mid + half_width)

    def _set_status(self, text: str) -> None:
        self._status.setPlainText(str(text or ""))

    def _structure_model(self):
        return to_structure_model(find_v1_structure_model(self.document))

    def _region_model(self):
        return to_region_model(find_v1_region_model(self.document))

    def _preset_structure_self_check_text(self, preset_name: str) -> str:
        return _preset_structure_self_check_text(
            preset_name,
            structure_refs=self._structure_ref_choices(),
        )

    def _preset_station_range_self_check_text(self, model: DrainageModel) -> str:
        values = _document_station_values(self.document)
        station_start, station_end = (min(values), max(values)) if values else _document_station_range(self.document)
        return _preset_station_range_self_check_text(
            model,
            station_start=station_start,
            station_end=station_end,
            station_source="stationing" if values else "fallback",
        )

    def _on_element_table_changed(self, row_index: int, column_index: int) -> None:
        if column_index in {0, ELEMENT_KIND_COLUMN, ELEMENT_STRUCTURE_COLUMN}:
            self._refresh_flow_route_element_combos()
            self._update_flow_route_preview()

    def _on_element_kind_changed(self, row_index: int) -> None:
        self._update_element_cell_states(row_index)
        self._refresh_flow_route_element_combos()
        self._update_flow_route_preview()

    def _set_combo_cell(
        self,
        table,
        row: int,
        column: int,
        value: str,
        choices: list[str],
        *,
        display_refs: bool = False,
        include_current: bool = True,
    ) -> None:
        combo = QtWidgets.QComboBox()
        combo.setEditable(True)
        combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(14)
        if display_refs:
            source_value = str(value or "").strip()
            combo_choices = ["", *choices]
            if include_current:
                combo_choices.append(source_value)
            for choice in _unique_texts(combo_choices):
                combo.addItem(self._display_combo_source(choice, table=table, column=column), choice)
            selected_index = -1
            for item_index in range(combo.count()):
                if str(combo.itemData(item_index) or "").strip() == source_value:
                    selected_index = item_index
                    break
            if selected_index >= 0:
                combo.setCurrentIndex(selected_index)
            else:
                combo.setCurrentText(self._display_combo_source(source_value, table=table, column=column) if include_current else "")
        else:
            for choice in _unique_texts(["", *choices, value]):
                combo.addItem(choice)
            combo.setCurrentText(str(value or ""))
        combo.setToolTip(str(combo.currentText() or ""))
        if table is self._flow_route_table and column in (
            FLOW_ROUTE_FROM_COLUMN,
            FLOW_ROUTE_TO_COLUMN,
            FLOW_ROUTE_OUTLET_COLUMN,
        ):
            combo.setMinimumWidth(150)
        try:
            combo.currentTextChanged.connect(lambda _text: self._update_flow_route_preview())
            combo.currentTextChanged.connect(lambda text, widget=combo: widget.setToolTip(str(text or "")))
            if table is self._flow_route_table and column in (FLOW_ROUTE_FROM_COLUMN, FLOW_ROUTE_TO_COLUMN):
                combo.currentTextChanged.connect(
                    lambda _text, row_index=row, column_index=column: self._normalize_flow_route_link_cells(
                        row_index,
                        column_index,
                    )
                )
            if table is self._flow_route_table and column == FLOW_ROUTE_TO_COLUMN:
                combo.currentTextChanged.connect(
                    lambda _text, row_index=row: self._update_flow_route_outlet_cell_state(row_index)
                )
            combo.currentTextChanged.connect(lambda _text: self._refresh_validation_cell_styles())
        except Exception:
            pass
        table.setCellWidget(row, column, combo)

    def _display_combo_source(self, value: object, *, table, column: int) -> str:
        return _display_source_ref(value)

    def _normalize_flow_route_link_cells(self, row_index: int, _changed_column: int) -> None:
        if getattr(self, "_normalizing_flow_route_links", False):
            return
        if row_index < 0 or row_index >= self._flow_route_table.rowCount():
            return
        choices = self._element_ref_choices()
        from_ref = _source_ref_from_display(
            _combo_source_text(self._flow_route_table, row_index, FLOW_ROUTE_FROM_COLUMN),
            choices,
        )
        to_ref = _source_ref_from_display(
            _combo_source_text(self._flow_route_table, row_index, FLOW_ROUTE_TO_COLUMN),
            choices,
        )
        if not from_ref or not to_ref or from_ref != to_ref:
            return
        replacement = next((choice for choice in choices if choice and choice != from_ref), "")
        self._normalizing_flow_route_links = True
        try:
            self._set_combo_current_source(self._flow_route_table, row_index, FLOW_ROUTE_TO_COLUMN, replacement)
        finally:
            self._normalizing_flow_route_links = False
        self._update_flow_route_outlet_cell_state(row_index)
        self._update_flow_route_preview()

    def _set_combo_current_source(self, table, row: int, column: int, source_ref: str) -> None:
        combo = table.cellWidget(row, column)
        if combo is None or not hasattr(combo, "setCurrentText"):
            return
        text = _display_source_ref(source_ref)
        try:
            combo.blockSignals(True)
            target_index = -1
            if hasattr(combo, "itemData"):
                for item_index in range(combo.count()):
                    if str(combo.itemData(item_index) or "").strip() == str(source_ref or "").strip():
                        target_index = item_index
                        break
            if target_index >= 0:
                combo.setCurrentIndex(target_index)
            else:
                combo.setCurrentText(text)
            combo.setToolTip(text)
        finally:
            combo.blockSignals(False)

    def _refresh_flow_route_element_combos(self) -> None:
        if not hasattr(self, "_flow_route_table"):
            return
        element_choices = self._element_ref_choices()
        outlet_choices = self._outlet_ref_choices()
        for index in range(self._flow_route_table.rowCount()):
            self._set_combo_cell(
                self._flow_route_table,
                index,
                FLOW_ROUTE_FROM_COLUMN,
                _combo_source_text(self._flow_route_table, index, FLOW_ROUTE_FROM_COLUMN),
                element_choices,
                display_refs=True,
            )
            self._set_combo_cell(
                self._flow_route_table,
                index,
                FLOW_ROUTE_TO_COLUMN,
                _combo_source_text(self._flow_route_table, index, FLOW_ROUTE_TO_COLUMN),
                element_choices,
                display_refs=True,
            )
            self._set_combo_cell(
                self._flow_route_table,
                index,
                FLOW_ROUTE_OUTLET_COLUMN,
                _combo_source_text(self._flow_route_table, index, FLOW_ROUTE_OUTLET_COLUMN)
                if self._flow_route_outlet_enabled(index)
                else "",
                outlet_choices,
                display_refs=True,
            )
            self._normalize_flow_route_link_cells(index, FLOW_ROUTE_TO_COLUMN)
            self._update_flow_route_outlet_cell_state(index)

    def _refresh_element_policy_combos(self) -> None:
        if not hasattr(self, "_element_table"):
            return
        choices = self._policy_ref_choices()
        for index in range(self._element_table.rowCount()):
            self._set_combo_cell(
                self._element_table,
                index,
                ELEMENT_POLICY_COLUMN,
                _combo_source_text(self._element_table, index, ELEMENT_POLICY_COLUMN),
                choices,
                display_refs=True,
            )
        self._refresh_validation_cell_styles()

    def _element_ref_choices(self) -> list[str]:
        choices: list[str] = []
        for index in range(self._element_table.rowCount()):
            element_id = _source_prefixed_id(_item_text(self._element_table, index, 0), "drainage:", f"element:{index + 1}")
            if element_id:
                choices.append(element_id)
        return _unique_texts(choices)

    def _policy_ref_choices(self) -> list[str]:
        choices: list[str] = []
        for index in range(self._policy_table.rowCount()):
            policy_id = _source_prefixed_id(_item_text(self._policy_table, index, 0), "drainage-policy:", f"{index + 1}")
            if policy_id:
                choices.append(policy_id)
        return _unique_texts(choices)

    def _structure_ref_choices(self) -> list[str]:
        model = self._structure_model()
        choices = [
            str(getattr(row, "structure_id", "") or "").strip()
            for row in list(getattr(model, "structure_rows", []) or [])
            if str(getattr(row, "structure_id", "") or "").strip()
        ]
        return _unique_texts(choices)

    def _outlet_ref_choices(self) -> list[str]:
        choices: list[str] = []
        for index in range(self._element_table.rowCount()):
            element_id = _source_prefixed_id(_item_text(self._element_table, index, 0), "drainage:", f"element:{index + 1}")
            element_kind = str(_item_text(self._element_table, index, ELEMENT_KIND_COLUMN) or "").strip().lower()
            structure_ref = _source_ref_from_display(
                _combo_source_text(self._element_table, index, ELEMENT_STRUCTURE_COLUMN),
                self._structure_ref_choices(),
                default_prefix="structure:",
            )
            if element_id and (element_kind == "outfall_reference" or element_kind.endswith("_reference")):
                choices.append(element_id)
            if structure_ref and element_kind != "ditch":
                choices.append(structure_ref)
        return _unique_texts(choices)

    def _flow_route_outlet_enabled(self, row_index: int) -> bool:
        to_ref = _source_ref_from_display(
            _combo_source_text(self._flow_route_table, row_index, FLOW_ROUTE_TO_COLUMN),
            self._element_ref_choices(),
            default_prefix="drainage:",
        )
        return _drainage_element_is_outlet_kind(self._element_kind_for_ref(to_ref))

    def _element_kind_for_ref(self, element_ref: str) -> str:
        expected = str(element_ref or "").strip()
        if not expected:
            return ""
        for index in range(self._element_table.rowCount()):
            element_id = _source_prefixed_id(_item_text(self._element_table, index, 0), "drainage:", f"element:{index + 1}")
            if element_id == expected:
                return str(_item_text(self._element_table, index, ELEMENT_KIND_COLUMN) or "").strip().lower()
        return ""

    def _update_flow_route_outlet_cell_state(self, row_index: int) -> None:
        if row_index < 0 or row_index >= self._flow_route_table.rowCount():
            return
        widget = self._flow_route_table.cellWidget(row_index, FLOW_ROUTE_OUTLET_COLUMN)
        enabled = self._flow_route_outlet_enabled(row_index)
        if widget is None:
            return
        try:
            if not enabled:
                widget.blockSignals(True)
                widget.setCurrentText("")
                widget.setEnabled(False)
                widget.setToolTip("Outlet is only edited when To Element is an outlet/outfall element.")
                widget.setStyleSheet(DISABLED_COMBO_STYLE)
                widget.blockSignals(False)
            else:
                widget.setEnabled(True)
                widget.setStyleSheet("")
                if not str(widget.currentText() or "").strip():
                    to_ref = _source_ref_from_display(
                        _combo_source_text(self._flow_route_table, row_index, FLOW_ROUTE_TO_COLUMN),
                        self._element_ref_choices(),
                        default_prefix="drainage:",
                    )
                    self._set_combo_current_source(self._flow_route_table, row_index, FLOW_ROUTE_OUTLET_COLUMN, to_ref)
                widget.setToolTip(str(widget.currentText() or "Select the final outlet element."))
        except Exception:
            return
        self._refresh_validation_cell_styles()

    def _update_flow_route_preview(self) -> None:
        if not hasattr(self, "_flow_route_preview"):
            return
        if self._flow_route_table.rowCount() <= 0:
            self._flow_route_preview.setText("")
            return
        row = self._flow_route_table.currentRow()
        if row < 0:
            row = 0
        route_id = _item_text(self._flow_route_table, row, 0) or f"flow-route:{row + 1}"
        from_ref = _item_text(self._flow_route_table, row, FLOW_ROUTE_FROM_COLUMN) or "(from)"
        to_ref = _item_text(self._flow_route_table, row, FLOW_ROUTE_TO_COLUMN)
        outlet_ref = _item_text(self._flow_route_table, row, FLOW_ROUTE_OUTLET_COLUMN)
        chain = [from_ref]
        if to_ref:
            chain.append(to_ref)
        if outlet_ref and outlet_ref != to_ref:
            chain.append(outlet_ref)
        route_ref = _source_prefixed_id(route_id, "flow-route:")
        route_type_summary = self._flow_route_type_summary(route_ref)
        endpoint_summary = self._flow_route_endpoint_summary(route_ref)
        preview_lines = [f"Route Chain: {route_id}: {' -> '.join(chain)}"]
        if outlet_ref:
            preview_lines.append(f"Terminal Outlet: {outlet_ref}")
        if route_type_summary:
            preview_lines.append(route_type_summary)
        if endpoint_summary:
            preview_lines.append(endpoint_summary)
        self._flow_route_preview.setText("\n".join(preview_lines))

    def _flow_route_candidate_for_ref(self, route_ref: str):
        route_ref = str(route_ref or "").strip()
        if not route_ref:
            return None, None
        structure_model = self._structure_model()
        if structure_model is None:
            return None, structure_model
        try:
            model = self._model_from_tables()
            candidates = build_drainage_pipeline_segment_candidates(model, structure_model)
        except Exception as exc:
            return exc, structure_model
        candidate = next(
            (
                row
                for row in candidates
                if str(getattr(row, "flow_route_ref", "") or "").strip() == route_ref
            ),
            None,
        )
        return candidate, structure_model

    def _flow_route_type_summary(self, route_ref: str) -> str:
        candidate, _structure_model = self._flow_route_candidate_for_ref(route_ref)
        if isinstance(candidate, Exception):
            return f"Route Type: unresolved ({candidate})"
        if candidate is None:
            return "Route Type: not resolved"
        status = str(getattr(candidate, "status", "") or "").strip()
        if status == "capture_only":
            return "Route Type: capture-only open-channel handoff; no pipe solid is generated."
        if status == "ready":
            return "Route Type: pipe-producing Structure-to-Structure segment."
        if status == "missing_element":
            return "Route Type: broken route; From or To Element is missing."
        return f"Route Type: unresolved pipe route; station-span fallback only ({status})."

    def _flow_route_endpoint_summary(self, route_ref: str) -> str:
        route_ref = str(route_ref or "").strip()
        if not route_ref:
            return ""
        candidate, structure_model = self._flow_route_candidate_for_ref(route_ref)
        if structure_model is None:
            return "Endpoint: no Structures model is available."
        if isinstance(candidate, Exception):
            return f"Endpoint: unresolved ({candidate})"
        if candidate is None:
            return "Endpoint: route is not resolved yet."
        status = str(getattr(candidate, "status", "") or "").strip()
        if status == "capture_only":
            return "Endpoint: capture only; no pipe body is generated for this route."
        from_point_ref = str(getattr(candidate, "from_connection_point_ref", "") or "").strip()
        to_point_ref = str(getattr(candidate, "to_connection_point_ref", "") or "").strip()
        from_point = _structure_connection_point_by_ref(structure_model, from_point_ref)
        to_point = _structure_connection_point_by_ref(structure_model, to_point_ref)
        if status != "ready":
            return (
                "Endpoint: unresolved pipe ports; "
                f"status={status}; "
                f"from_port={_display_connection_point_ref(from_point_ref) or '-'}; "
                f"to_port={_display_connection_point_ref(to_point_ref) or '-'}"
            )
        from_structure = str(getattr(from_point, "structure_ref", "") or "").strip()
        to_structure = str(getattr(to_point, "structure_ref", "") or "").strip()
        from_role = str(getattr(from_point, "point_role", "") or "").strip()
        to_role = str(getattr(to_point, "point_role", "") or "").strip()
        return (
            "Endpoint: "
            f"From Structure {_display_source_ref(from_structure) or '-'} / "
            f"Port {_display_connection_point_ref(from_point_ref) or '-'}"
            f"{_role_suffix(from_role)} -> "
            f"To Structure {_display_source_ref(to_structure) or '-'} / "
            f"Port {_display_connection_point_ref(to_point_ref) or '-'}"
            f"{_role_suffix(to_role)}"
        )

    def _update_element_cell_states(self, row_index: int) -> None:
        self._update_element_assembly_cell_state(row_index)
        self._update_element_structure_cell_state(row_index)

    def _update_element_assembly_cell_state(self, row_index: int) -> None:
        if row_index < 0 or row_index >= self._element_table.rowCount():
            return
        item = self._element_table.item(row_index, ELEMENT_ASSEMBLY_COLUMN)
        if item is None:
            item = QtWidgets.QTableWidgetItem("")
            self._element_table.setItem(row_index, ELEMENT_ASSEMBLY_COLUMN, item)
        disabled = _assembly_disabled_for_kind(_item_text(self._element_table, row_index, ELEMENT_KIND_COLUMN))
        try:
            flags = item.flags()
            if disabled:
                item.setText("")
                item.setFlags((flags & ~QtCore.Qt.ItemIsEditable) & ~QtCore.Qt.ItemIsEnabled)
                item.setToolTip("Subassembly is only used for ditch elements.")
                item.setBackground(QtGui.QColor(48, 48, 48))
                item.setForeground(QtGui.QColor(140, 140, 140))
            else:
                item.setFlags(flags | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)
                item.setToolTip("")
                item.setBackground(QtGui.QBrush())
                item.setForeground(QtGui.QBrush())
        except Exception:
            return

    def _update_element_structure_cell_state(self, row_index: int) -> None:
        if row_index < 0 or row_index >= self._element_table.rowCount():
            return
        widget = self._element_table.cellWidget(row_index, ELEMENT_STRUCTURE_COLUMN)
        if widget is None:
            item = self._element_table.item(row_index, ELEMENT_STRUCTURE_COLUMN)
            current = _source_structure_ref(str(item.text() if item is not None else "") if item is not None else "")
            self._set_combo_cell(
                self._element_table,
                row_index,
                ELEMENT_STRUCTURE_COLUMN,
                current,
                self._structure_ref_choices(),
                display_refs=True,
                include_current=False,
            )
            if item is not None:
                self._element_table.takeItem(row_index, ELEMENT_STRUCTURE_COLUMN)
            widget = self._element_table.cellWidget(row_index, ELEMENT_STRUCTURE_COLUMN)
        disabled = _structure_disabled_for_kind(_item_text(self._element_table, row_index, ELEMENT_KIND_COLUMN))
        try:
            if disabled:
                if hasattr(widget, "setCurrentText"):
                    widget.setCurrentText("")
                widget.setEnabled(False)
                widget.setToolTip("Structure is not used for ditch elements.")
                widget.setStyleSheet(DISABLED_COMBO_STYLE)
            else:
                widget.setEnabled(True)
                widget.setToolTip("Select a Structure ID from the active Structures model.")
                widget.setStyleSheet("")
        except Exception:
            return

    def _refresh_validation_cell_styles(self) -> None:
        if getattr(self, "_refreshing_validation_cell_styles", False):
            return
        if not hasattr(self, "_element_table") or not hasattr(self, "_flow_route_table"):
            return
        self._refreshing_validation_cell_styles = True
        try:
            policy_choices = self._policy_ref_choices()
            policy_set = set(policy_choices)
            structure_choices = self._structure_ref_choices()
            structure_set = set(structure_choices)
            element_choices = self._element_ref_choices()
            element_set = set(element_choices)
            outlet_choices = self._outlet_ref_choices()
            outlet_set = set(outlet_choices)

            for row in range(self._element_table.rowCount()):
                policy_ref = _source_ref_from_display(
                    _combo_source_text(self._element_table, row, ELEMENT_POLICY_COLUMN),
                    policy_choices,
                    default_prefix="drainage-policy:",
                )
                self._set_combo_warning_state(
                    self._element_table,
                    row,
                    ELEMENT_POLICY_COLUMN,
                    invalid=not policy_ref or policy_ref not in policy_set,
                    message="Select a Policy from the Policies tab.",
                )

                kind = str(_item_text(self._element_table, row, ELEMENT_KIND_COLUMN) or "").strip().lower()
                structure_disabled = _structure_disabled_for_kind(kind)
                structure_ref = _source_ref_from_display(
                    _combo_source_text(self._element_table, row, ELEMENT_STRUCTURE_COLUMN),
                    structure_choices,
                    default_prefix="structure:",
                )
                self._set_combo_warning_state(
                    self._element_table,
                    row,
                    ELEMENT_STRUCTURE_COLUMN,
                    invalid=not structure_disabled and (not structure_ref or structure_ref not in structure_set),
                    message="Select a Structure Ref for Structure-backed drainage elements.",
                    disabled=structure_disabled,
                )

            for row in range(self._flow_route_table.rowCount()):
                from_ref = _source_ref_from_display(
                    _combo_source_text(self._flow_route_table, row, FLOW_ROUTE_FROM_COLUMN),
                    element_choices,
                    default_prefix="drainage:",
                )
                to_ref = _source_ref_from_display(
                    _combo_source_text(self._flow_route_table, row, FLOW_ROUTE_TO_COLUMN),
                    element_choices,
                    default_prefix="drainage:",
                )
                self._set_combo_warning_state(
                    self._flow_route_table,
                    row,
                    FLOW_ROUTE_FROM_COLUMN,
                    invalid=not from_ref or from_ref not in element_set,
                    message="Select an existing From Element.",
                )
                self._set_combo_warning_state(
                    self._flow_route_table,
                    row,
                    FLOW_ROUTE_TO_COLUMN,
                    invalid=not to_ref or to_ref not in element_set,
                    message="Select an existing To Element.",
                )
                outlet_enabled = self._flow_route_outlet_enabled(row)
                outlet_ref = _source_ref_from_display(
                    _combo_source_text(self._flow_route_table, row, FLOW_ROUTE_OUTLET_COLUMN),
                    outlet_choices,
                    default_prefix="drainage:",
                )
                self._set_combo_warning_state(
                    self._flow_route_table,
                    row,
                    FLOW_ROUTE_OUTLET_COLUMN,
                    invalid=outlet_enabled and bool(outlet_ref) and outlet_ref not in outlet_set,
                    message="Select an existing terminal Outlet, or leave it blank when the To Element is the outlet.",
                    disabled=not outlet_enabled,
                )
        finally:
            self._refreshing_validation_cell_styles = False

    def _set_combo_warning_state(
        self,
        table,
        row: int,
        column: int,
        *,
        invalid: bool,
        message: str,
        disabled: bool = False,
    ) -> None:
        widget = table.cellWidget(row, column)
        if widget is None or not hasattr(widget, "setStyleSheet"):
            return
        if disabled:
            try:
                widget.setStyleSheet(DISABLED_COMBO_STYLE)
            except Exception:
                pass
            return
        try:
            widget.setStyleSheet(INVALID_COMBO_STYLE if invalid else "")
            if invalid:
                widget.setToolTip(message)
            else:
                widget.setToolTip(str(widget.currentText() or ""))
        except Exception:
            return


__all__ = [
    "V1DrainageEditorTaskPanel",
    "configure_drainage_editor_task_panel_runtime",
]

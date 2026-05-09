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
from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets

from ..models.source.drainage_model import (
    DrainageCollectionRegion,
    DrainageElementRow,
    DrainageModel,
    DrainagePolicySet,
)
from ..objects.obj_drainage import (
    create_or_update_v1_drainage_model_object,
    find_v1_drainage_model,
    to_drainage_model,
)
from ..objects.obj_region import find_v1_region_model, to_region_model
from ..objects.obj_stationing import find_v1_stationing
from ..services.evaluation.drainage_resolution_service import DrainageValidationService


ELEMENT_KIND_CHOICES = ["ditch", "gutter", "swale", "channel", "culvert_reference", "inlet_reference", "outfall_reference"]
SIDE_CHOICES = ["", "left", "right", "both", "center"]
FLOW_INTENT_CHOICES = ["collect_and_convey", "edge_runoff_capture", "ditch_outfall", "cross_drainage_transfer"]
ELEMENT_KIND_COLUMN = 1
ELEMENT_STRUCTURE_COLUMN = 8
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
                "component": "ditch:right",
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
        "collections": [
            {
                "id": "drainage-collection:main",
                "kind": "roadside_collection",
                "start": 0.0,
                "end": 1.0,
                "receiver": "outfall:main",
                "risk": "medium",
            }
        ],
    },
    "Dual Side Ditches": {
        "note": "Left and right roadside ditches with one shared collection policy.",
        "elements": [
            {
                "id": "drainage:side-ditch-left",
                "kind": "ditch",
                "side": "left",
                "start": 0.0,
                "end": 1.0,
                "component": "ditch:left",
                "policy": "drainage-policy:lined-concrete",
            },
            {
                "id": "drainage:side-ditch-right",
                "kind": "ditch",
                "side": "right",
                "start": 0.0,
                "end": 1.0,
                "component": "ditch:right",
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
        "collections": [
            {
                "id": "drainage-collection:left",
                "kind": "roadside_collection",
                "start": 0.0,
                "end": 1.0,
                "receiver": "outfall:left",
                "risk": "medium",
            },
            {
                "id": "drainage-collection:right",
                "kind": "roadside_collection",
                "start": 0.0,
                "end": 1.0,
                "receiver": "outfall:right",
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
                "component": "ditch:left",
                "policy": "drainage-policy:roadside-ditch",
            },
            {
                "id": "drainage:side-ditch-right",
                "kind": "ditch",
                "side": "right",
                "start": 0.0,
                "end": 1.0,
                "component": "ditch:right",
                "policy": "drainage-policy:roadside-ditch",
            },
            {
                "id": "drainage:culvert-01",
                "kind": "culvert_reference",
                "side": "center",
                "start": 0.48,
                "end": 0.52,
                "component": "",
                "policy": "drainage-policy:cross-drain",
                "structure": "structure:culvert-01",
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
        "collections": [
            {
                "id": "drainage-collection:culvert-01",
                "kind": "ditch_collection_region",
                "start": 0.45,
                "end": 0.55,
                "receiver": "structure:culvert-01",
                "risk": "high",
            }
        ],
    },
}


def drainage_preset_names() -> list[str]:
    """Return available v1 Drainage preset names."""

    return list(DRAINAGE_PRESETS.keys())


def region_model_ids(document) -> list[str]:
    """Return v1 Region ids available for Drainage element region_ref selection."""

    region_obj = find_v1_region_model(document)
    model = to_region_model(region_obj)
    if model is None:
        return []
    output: list[str] = []
    seen: set[str] = set()
    for row in list(getattr(model, "region_rows", []) or []):
        region_id = str(getattr(row, "region_id", "") or "").strip()
        if not region_id or region_id in seen:
            continue
        seen.add(region_id)
        output.append(region_id)
    return output


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

    return drainage_preset_model_from_document("Roadside Ditch", document=document, project=project)


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
        collection_region_rows=_preset_collection_rows(preset, station_start=station_start, station_end=station_end),
    )


def apply_v1_drainage_model(*, document=None, drainage_model: DrainageModel):
    """Persist a DrainageModel into the active document."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    return create_or_update_v1_drainage_model_object(
        doc,
        drainage_model=drainage_model,
        project=find_project(doc),
    )


class V1DrainageEditorTaskPanel:
    """Table-based v1 Drainage source editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.drainage_obj = find_v1_drainage_model(self.document)
        self._region_refs = region_model_ids(self.document)
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
        widget.setWindowTitle("CorridorRoad v1 - Drainage")
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
        self._preset_combo.addItems(drainage_preset_names())
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
        self._element_table = self._table(
            [
                "Element ID",
                "Kind",
                "Region",
                "Side",
                "Start STA",
                "End STA",
                "Assembly",
                "Policy",
                "Structure",
            ]
        )
        self._policy_table = self._table(
            ["Policy ID", "Flow Intent", "Min Grade", "Low Point", "Collection", "Discharge", "Earthwork Priority"]
        )
        self._collection_table = self._table(
            ["Collection ID", "Kind", "Start STA", "End STA", "Receiver", "Risk", "Alignment"]
        )
        self._tabs.addTab(self._element_table, "Elements")
        self._tabs.addTab(self._policy_table, "Policies")
        self._tabs.addTab(self._collection_table, "Collections")
        self._tabs.currentChanged.connect(lambda _index: self._update_tab_action_visibility())
        layout.addWidget(self._tabs, 1)

        edit_row = QtWidgets.QHBoxLayout()
        self._add_element_button = QtWidgets.QPushButton("Add Element")
        self._add_element_button.clicked.connect(self._add_element_row)
        edit_row.addWidget(self._add_element_button)
        self._add_left_ditch_button = QtWidgets.QPushButton("Add Left Ditch")
        self._add_left_ditch_button.clicked.connect(lambda: self._add_ditch_row("left"))
        edit_row.addWidget(self._add_left_ditch_button)
        self._add_right_ditch_button = QtWidgets.QPushButton("Add Right Ditch")
        self._add_right_ditch_button.clicked.connect(lambda: self._add_ditch_row("right"))
        edit_row.addWidget(self._add_right_ditch_button)
        self._add_policy_button = QtWidgets.QPushButton("Add Policy")
        self._add_policy_button.clicked.connect(self._add_policy_row)
        edit_row.addWidget(self._add_policy_button)
        self._add_collection_button = QtWidgets.QPushButton("Add Collection")
        self._add_collection_button.clicked.connect(self._add_collection_row)
        edit_row.addWidget(self._add_collection_button)
        delete_row = QtWidgets.QPushButton("Delete Selected")
        delete_row.clicked.connect(self._delete_selected_rows)
        edit_row.addWidget(delete_row)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)

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

    def _load_existing_or_starter(self) -> None:
        model = to_drainage_model(self.drainage_obj)
        if model is None:
            model = starter_drainage_model_from_document(self.document)
            self._replace_model(model)
            self._set_status("Starter DrainageModel loaded. Apply when ready.")
            return
        self._replace_model(model)
        self._set_status(f"Loaded DrainageModel from {self.drainage_obj.Label}.")

    def _load_selected_preset(self) -> None:
        try:
            preset_name = str(self._preset_combo.currentText() or "Roadside Ditch")
            model = drainage_preset_model_from_document(preset_name, document=self.document)
            self._replace_model(model)
            self._set_status(f"Drainage preset loaded: {preset_name}. Apply when ready.")
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
        self._collection_table.setRowCount(0)
        for row in list(getattr(model, "collection_region_rows", []) or []):
            self._append_collection_row(row)

    def _append_element_row(self, row: DrainageElementRow | None = None) -> None:
        row = row or self._default_ditch_row("right")
        index = self._element_table.rowCount()
        self._element_table.insertRow(index)
        values = [
            _display_prefixed_id(row.drainage_element_id, "drainage:"),
            row.element_kind,
            getattr(row, "region_ref", "") or "",
            getattr(row, "side", "") or "",
            _format_float(row.station_start),
            _format_float(row.station_end),
            getattr(row, "assembly_component_ref", "") or "",
            _display_prefixed_id(row.policy_set_ref, "drainage-policy:"),
            row.structure_ref,
        ]
        for col, value in enumerate(values):
            if col == 1:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(ELEMENT_KIND_CHOICES)
                combo.setCurrentText(str(value or "ditch"))
                try:
                    combo.currentTextChanged.connect(
                        lambda _text, row_index=index: self._update_element_structure_cell_state(row_index)
                    )
                except Exception:
                    pass
                self._element_table.setCellWidget(index, col, combo)
            elif col == 2:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItem("")
                combo.addItems(self._region_refs)
                combo.setCurrentText(str(value or ""))
                self._element_table.setCellWidget(index, col, combo)
            elif col == 3:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(SIDE_CHOICES)
                combo.setCurrentText(str(value or ""))
                self._element_table.setCellWidget(index, col, combo)
            else:
                self._element_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))
        self._update_element_structure_cell_state(index)

    def _default_ditch_row(self, side: str) -> DrainageElementRow:
        normalized_side = str(side or "right").strip().lower() or "right"
        if normalized_side not in {"left", "right"}:
            normalized_side = "right"
        base_id = f"drainage:side-ditch-{normalized_side}"
        return DrainageElementRow(
            drainage_element_id=self._unique_element_id(base_id),
            element_kind="ditch",
            side=normalized_side,
            assembly_component_ref=f"ditch:{normalized_side}",
            station_start=0.0,
            station_end=100.0,
            policy_set_ref=self._first_policy_ref(),
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

    def _append_collection_row(self, row: DrainageCollectionRegion | None = None) -> None:
        row = row or DrainageCollectionRegion(
            collection_region_id=f"drainage-collection:{self._collection_table.rowCount() + 1}",
            region_kind="roadside_collection",
            station_start=0.0,
            station_end=100.0,
        )
        index = self._collection_table.rowCount()
        self._collection_table.insertRow(index)
        values = [
            row.collection_region_id,
            row.region_kind,
            _format_float(row.station_start),
            _format_float(row.station_end),
            row.expected_receiver_ref,
            row.risk_level,
            row.alignment_ref,
        ]
        for col, value in enumerate(values):
            self._collection_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))

    def _add_element_row(self) -> None:
        self._append_element_row()
        self._set_status("Added Drainage element row.")

    def _add_ditch_row(self, side: str) -> None:
        row = self._default_ditch_row(side)
        self._append_element_row(row)
        self._set_status(f"Added {row.side} side ditch row.")

    def _add_policy_row(self) -> None:
        self._append_policy_row()
        self._set_status("Added Drainage policy row.")

    def _add_collection_row(self) -> None:
        self._append_collection_row()
        self._set_status("Added Drainage collection row.")

    def _delete_selected_rows(self) -> None:
        table = self._tabs.currentWidget()
        if table is None:
            return
        rows = sorted({item.row() for item in list(table.selectedItems() or [])}, reverse=True)
        if not rows and table.currentRow() >= 0:
            rows = [table.currentRow()]
        for row_index in rows:
            table.removeRow(row_index)
        self._set_status(f"Deleted {len(rows)} row(s).")

    def _update_tab_action_visibility(self) -> None:
        current = self._tabs.currentWidget() if hasattr(self, "_tabs") else None
        is_elements = current is getattr(self, "_element_table", None)
        is_policies = current is getattr(self, "_policy_table", None)
        is_collections = current is getattr(self, "_collection_table", None)
        for button in (
            getattr(self, "_add_element_button", None),
            getattr(self, "_add_left_ditch_button", None),
            getattr(self, "_add_right_ditch_button", None),
        ):
            if button is not None:
                button.setVisible(is_elements)
        if getattr(self, "_add_policy_button", None) is not None:
            self._add_policy_button.setVisible(is_policies)
        if getattr(self, "_add_collection_button", None) is not None:
            self._add_collection_button.setVisible(is_collections)

    def _validate(self) -> None:
        try:
            model = self._model_from_tables()
            result = DrainageValidationService().validate(model, region_model=self._region_model())
            self._set_status(_format_validation_result(result, model))
        except Exception as exc:
            self._set_status(f"Drainage validation failed:\n{exc}")

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            model = self._model_from_tables()
            result = DrainageValidationService().validate(model, region_model=self._region_model())
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
            collection_region_rows=self._collection_rows(),
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
                    region_ref=_item_text(self._element_table, index, 2),
                    side=_item_text(self._element_table, index, 3),
                    station_start=_float_value(_item_text(self._element_table, index, 4)),
                    station_end=_float_value(_item_text(self._element_table, index, 5)),
                    assembly_component_ref=_item_text(self._element_table, index, 6),
                    policy_set_ref=_source_prefixed_id(_item_text(self._element_table, index, 7), "drainage-policy:"),
                    structure_ref="" if _structure_disabled_for_kind(element_kind) else _item_text(self._element_table, index, 8),
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

    def _collection_rows(self) -> list[DrainageCollectionRegion]:
        rows: list[DrainageCollectionRegion] = []
        for index in range(self._collection_table.rowCount()):
            rows.append(
                DrainageCollectionRegion(
                    collection_region_id=_item_text(self._collection_table, index, 0) or f"drainage-collection:{index + 1}",
                    region_kind=_item_text(self._collection_table, index, 1),
                    station_start=_float_value(_item_text(self._collection_table, index, 2)),
                    station_end=_float_value(_item_text(self._collection_table, index, 3)),
                    expected_receiver_ref=_item_text(self._collection_table, index, 4),
                    risk_level=_item_text(self._collection_table, index, 5),
                    alignment_ref=_item_text(self._collection_table, index, 6),
                )
            )
        return rows

    def _first_policy_ref(self) -> str:
        return _source_prefixed_id(_item_text(self._policy_table, 0, 0), "drainage-policy:") if self._policy_table.rowCount() else ""

    def _set_status(self, text: str) -> None:
        self._status.setPlainText(str(text or ""))

    def _region_model(self):
        return to_region_model(find_v1_region_model(self.document))

    def _update_element_structure_cell_state(self, row_index: int) -> None:
        if row_index < 0 or row_index >= self._element_table.rowCount():
            return
        item = self._element_table.item(row_index, ELEMENT_STRUCTURE_COLUMN)
        if item is None:
            item = QtWidgets.QTableWidgetItem("")
            self._element_table.setItem(row_index, ELEMENT_STRUCTURE_COLUMN, item)
        disabled = _structure_disabled_for_kind(_item_text(self._element_table, row_index, ELEMENT_KIND_COLUMN))
        try:
            flags = item.flags()
            if disabled:
                item.setText("")
                item.setFlags((flags & ~QtCore.Qt.ItemIsEditable) & ~QtCore.Qt.ItemIsEnabled)
                item.setToolTip("Structure is not used for ditch elements.")
                item.setBackground(QtGui.QColor(48, 48, 48))
                item.setForeground(QtGui.QColor(140, 140, 140))
            else:
                item.setFlags(flags | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)
                item.setToolTip("")
                item.setBackground(QtGui.QBrush())
                item.setForeground(QtGui.QBrush())
        except Exception:
            return


def _item_text(table, row: int, column: int) -> str:
    widget = table.cellWidget(row, column)
    if widget is not None:
        if hasattr(widget, "currentText"):
            return str(widget.currentText() or "").strip()
        if hasattr(widget, "text"):
            return str(widget.text() or "").strip()
    item = table.item(row, column)
    return "" if item is None else str(item.text() or "").strip()


def _display_prefixed_id(value: object, prefix: str) -> str:
    text = str(value or "").strip()
    if prefix and text.startswith(prefix):
        return text[len(prefix) :]
    return text


def _source_prefixed_id(value: object, prefix: str, default_suffix: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        text = str(default_suffix or "").strip()
    if not text:
        return ""
    if prefix and not text.startswith(prefix):
        return f"{prefix}{text}"
    return text


def _structure_disabled_for_kind(kind: object) -> bool:
    return str(kind or "").strip().lower() == "ditch"


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
                region_ref=str(spec.get("region", "") or ""),
                assembly_component_ref=str(spec.get("component", "") or ""),
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


def _preset_collection_rows(preset: dict, *, station_start: float, station_end: float) -> list[DrainageCollectionRegion]:
    rows: list[DrainageCollectionRegion] = []
    for index, spec in enumerate(list(preset.get("collections", []) or []), start=1):
        rows.append(
            DrainageCollectionRegion(
                collection_region_id=str(spec.get("id", "") or f"drainage-collection:{index}"),
                region_kind=str(spec.get("kind", "") or "roadside_collection"),
                station_start=_preset_station_value(spec.get("start", 0.0), station_start=station_start, station_end=station_end),
                station_end=_preset_station_value(spec.get("end", 1.0), station_start=station_start, station_end=station_end),
                alignment_ref=str(spec.get("alignment", "") or ""),
                expected_receiver_ref=str(spec.get("receiver", "") or ""),
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
    lines = [
        f"Validation: {result.status}",
        f"Elements: {len(model.element_rows)}",
        f"Policies: {len(model.policy_rows)}",
        f"Collections: {len(model.collection_region_rows)}",
        f"Diagnostics: {len(result.diagnostic_rows)}",
    ]
    for row in list(result.diagnostic_rows or [])[:6]:
        lines.append(f"{row.severity}:{row.kind}: {row.message}")
    remaining = len(list(result.diagnostic_rows or [])) - 6
    if remaining > 0:
        lines.append(f"+{remaining} more diagnostics")
    return "\n".join(lines)


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


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditDrainage", CmdV1DrainageEditor())

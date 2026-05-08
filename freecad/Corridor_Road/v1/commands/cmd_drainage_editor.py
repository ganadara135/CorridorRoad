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
from freecad.Corridor_Road.qt_compat import QtWidgets

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
from ..services.evaluation.drainage_resolution_service import DrainageValidationService


ELEMENT_KIND_CHOICES = ["ditch", "gutter", "swale", "channel", "culvert_reference", "inlet_reference", "outfall_reference"]
SIDE_CHOICES = ["", "left", "right", "both", "center"]
FLOW_INTENT_CHOICES = ["collect_and_convey", "edge_runoff_capture", "ditch_outfall", "cross_drainage_transfer"]


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

    prj = project or find_project(document)
    return DrainageModel(
        schema_version=1,
        project_id=_project_id(prj),
        drainage_model_id="drainage:main",
        label="Drainage",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:side-ditch-right",
                element_kind="ditch",
                side="right",
                assembly_component_ref="ditch:right",
                station_start=0.0,
                station_end=100.0,
                offset_rule="right shoulder ditch",
                policy_set_ref="drainage-policy:lined-concrete",
            )
        ],
        policy_rows=[
            DrainagePolicySet(
                policy_set_id="drainage-policy:lined-concrete",
                flow_intent="collect_and_convey",
                collection_rule="roadside",
                discharge_rule="outfall",
            )
        ],
        collection_region_rows=[
            DrainageCollectionRegion(
                collection_region_id="drainage-collection:main",
                region_kind="roadside_collection",
                station_start=0.0,
                station_end=100.0,
                expected_receiver_ref="outfall:main",
                risk_level="medium",
            )
        ],
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
                "Side",
                "Start STA",
                "End STA",
                "Region",
                "Assembly Component",
                "Offset Rule",
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
        layout.addWidget(self._tabs, 1)

        edit_row = QtWidgets.QHBoxLayout()
        add_element = QtWidgets.QPushButton("Add Element")
        add_element.clicked.connect(self._add_element_row)
        edit_row.addWidget(add_element)
        add_left_ditch = QtWidgets.QPushButton("Add Left Ditch")
        add_left_ditch.clicked.connect(lambda: self._add_ditch_row("left"))
        edit_row.addWidget(add_left_ditch)
        add_right_ditch = QtWidgets.QPushButton("Add Right Ditch")
        add_right_ditch.clicked.connect(lambda: self._add_ditch_row("right"))
        edit_row.addWidget(add_right_ditch)
        add_policy = QtWidgets.QPushButton("Add Policy")
        add_policy.clicked.connect(self._add_policy_row)
        edit_row.addWidget(add_policy)
        add_collection = QtWidgets.QPushButton("Add Collection")
        add_collection.clicked.connect(self._add_collection_row)
        edit_row.addWidget(add_collection)
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
            row.drainage_element_id,
            row.element_kind,
            getattr(row, "side", "") or "",
            _format_float(row.station_start),
            _format_float(row.station_end),
            getattr(row, "region_ref", "") or "",
            getattr(row, "assembly_component_ref", "") or "",
            row.offset_rule,
            row.policy_set_ref,
            row.structure_ref,
        ]
        for col, value in enumerate(values):
            if col == 1:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(ELEMENT_KIND_CHOICES)
                combo.setCurrentText(str(value or "ditch"))
                self._element_table.setCellWidget(index, col, combo)
            elif col == 2:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(SIDE_CHOICES)
                combo.setCurrentText(str(value or ""))
                self._element_table.setCellWidget(index, col, combo)
            else:
                self._element_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))

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
            offset_rule=f"{normalized_side} shoulder ditch",
            policy_set_ref=self._first_policy_ref(),
        )

    def _unique_element_id(self, base_id: str) -> str:
        existing = {
            _item_text(self._element_table, index, 0)
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
            row.policy_set_id,
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

    def _validate(self) -> None:
        try:
            model = self._model_from_tables()
            result = DrainageValidationService().validate(model)
            self._set_status(_format_validation_result(result, model))
        except Exception as exc:
            self._set_status(f"Drainage validation failed:\n{exc}")

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            model = self._model_from_tables()
            result = DrainageValidationService().validate(model)
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
            rows.append(
                DrainageElementRow(
                    drainage_element_id=_item_text(self._element_table, index, 0) or f"drainage:element:{index + 1}",
                    element_kind=_item_text(self._element_table, index, 1) or "ditch",
                    side=_item_text(self._element_table, index, 2),
                    station_start=_float_value(_item_text(self._element_table, index, 3)),
                    station_end=_float_value(_item_text(self._element_table, index, 4)),
                    region_ref=_item_text(self._element_table, index, 5),
                    assembly_component_ref=_item_text(self._element_table, index, 6),
                    offset_rule=_item_text(self._element_table, index, 7),
                    policy_set_ref=_item_text(self._element_table, index, 8),
                    structure_ref=_item_text(self._element_table, index, 9),
                )
            )
        return rows

    def _policy_rows(self) -> list[DrainagePolicySet]:
        rows: list[DrainagePolicySet] = []
        for index in range(self._policy_table.rowCount()):
            rows.append(
                DrainagePolicySet(
                    policy_set_id=_item_text(self._policy_table, index, 0) or f"drainage-policy:{index + 1}",
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
        return _item_text(self._policy_table, 0, 0) if self._policy_table.rowCount() else ""

    def _set_status(self, text: str) -> None:
        self._status.setPlainText(str(text or ""))


def _item_text(table, row: int, column: int) -> str:
    widget = table.cellWidget(row, column)
    if widget is not None:
        if hasattr(widget, "currentText"):
            return str(widget.currentText() or "").strip()
        if hasattr(widget, "text"):
            return str(widget.text() or "").strip()
    item = table.item(row, column)
    return "" if item is None else str(item.text() or "").strip()


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

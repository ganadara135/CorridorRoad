"""Drainage editor panel for CorridorRoad v1.

The panel edits the Drainage Policy and the Ditch Runs: which Assembly ditch drains which side of
which road over which stations. Nothing is written until Apply; opening the panel prefills the
runs from the Regions and the Assembly when the stored Drainage has none, without writing them.
"""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets
from freecad.Corridor_Road.v1.models.source.drainage_model import (
    DITCH_RUN_SIDES,
    LOW_POINT_RULES,
    DitchRun,
    DrainageModel,
    DrainagePolicy,
)
from freecad.Corridor_Road.v1.services.editing.drainage_editing_service import ditch_run_id
from freecad.Corridor_Road.v1.ui.common.panel_width import fit_task_panel_width


def configure_drainage_editor_task_panel_runtime(bindings) -> None:
    """Bind command collaborators without importing the command module."""

    for name, value in dict(bindings or {}).items():
        globals()[name] = value


# Runtime collaborators, bound by the command module.
App = None
Gui = None
apply_v1_drainage_model = None
drainage_editor_inputs = None

COLUMNS = ("ID", "Road", "Side", "Ditch", "Start STA", "End STA", "On")
ID_COLUMN, ROAD_COLUMN, SIDE_COLUMN, DITCH_COLUMN, START_COLUMN, END_COLUMN, ON_COLUMN = range(len(COLUMNS))
LOW_POINT_LABELS = {"require_inlet": "Needs an inlet or outfall", "allow_ponding": "May pond"}


class V1DrainageEditorTaskPanel:
    """Drainage Policy and Ditch Runs editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        inputs = drainage_editor_inputs(self.document)
        self._model: DrainageModel = inputs["model"]
        self._choices = list(inputs["choices"])
        self._alignment_ids = [value for value in inputs["alignment_ids"]] or [""]
        self._prefill: list[DitchRun] = list(inputs["prefill"])
        self.form = fit_task_panel_width(self._build_ui())
        self._load(self._model)
        if inputs["prefilled"]:
            self._set_status(
                f"{len(self._model.ditch_run_rows)} Ditch Run(s) filled from the Regions and the Assembly. "
                "Apply to keep them."
            )
        elif not self._choices:
            self._set_status("The Assembly has no ditch. Add a ditch Subassembly to the Assembly first.")

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

        policy_box = QtWidgets.QGroupBox("Policy")
        policy_form = QtWidgets.QFormLayout(policy_box)
        self._min_grade = QtWidgets.QDoubleSpinBox()
        self._min_grade.setRange(0.0, 20.0)
        self._min_grade.setDecimals(2)
        self._min_grade.setSingleStep(0.1)
        self._min_grade.setSuffix(" %")
        policy_form.addRow("Minimum flowline grade:", self._min_grade)
        self._max_spacing = QtWidgets.QDoubleSpinBox()
        self._max_spacing.setRange(0.0, 1000.0)
        self._max_spacing.setDecimals(1)
        self._max_spacing.setSingleStep(5.0)
        self._max_spacing.setSuffix(" m")
        policy_form.addRow("Maximum inlet spacing:", self._max_spacing)
        self._low_point_rule = QtWidgets.QComboBox()
        for rule in LOW_POINT_RULES:
            self._low_point_rule.addItem(LOW_POINT_LABELS.get(rule, rule), rule)
        policy_form.addRow("Low point:", self._low_point_rule)
        layout.addWidget(policy_box)

        layout.addWidget(QtWidgets.QLabel("Ditch Runs: the Assembly ditches that drain the road"))
        self._table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(list(COLUMNS))
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        try:
            self._table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._table.setColumnHidden(ROAD_COLUMN, len(self._alignment_ids) <= 1)
        layout.addWidget(self._table, 1)

        edit_row = QtWidgets.QHBoxLayout()
        fill_button = QtWidgets.QPushButton("Fill from Assembly")
        fill_button.setToolTip("Replace the Ditch Runs with one run per Assembly ditch and side over the Region spans.")
        fill_button.clicked.connect(self._fill_from_assembly)
        edit_row.addWidget(fill_button)
        add_button = QtWidgets.QPushButton("Add Run")
        add_button.clicked.connect(lambda: self._append_row(None))
        edit_row.addWidget(add_button)
        delete_button = QtWidgets.QPushButton("Delete Run")
        delete_button.clicked.connect(self._delete_selected_row)
        edit_row.addWidget(delete_button)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setFixedHeight(80)
        layout.addWidget(self._status)

        action_row = QtWidgets.QHBoxLayout()
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        action_row.addWidget(apply_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        return widget

    def _load(self, model: DrainageModel) -> None:
        policy = model.policy
        self._min_grade.setValue(float(policy.min_grade_percent))
        self._max_spacing.setValue(float(policy.max_inlet_spacing_m))
        index = self._low_point_rule.findData(policy.low_point_rule)
        self._low_point_rule.setCurrentIndex(max(index, 0))
        self._set_runs(model.ditch_run_rows)

    def _set_runs(self, runs: list[DitchRun]) -> None:
        self._table.setRowCount(0)
        for run in list(runs or []):
            self._append_row(run)

    def _append_row(self, run: DitchRun | None) -> None:
        if run is None:
            run = self._new_run()
        row = self._table.rowCount()
        self._table.insertRow(row)
        id_item = QtWidgets.QTableWidgetItem(run.ditch_run_id)
        id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self._table.setItem(row, ID_COLUMN, id_item)
        self._table.setCellWidget(row, ROAD_COLUMN, _combo(self._alignment_ids, run.alignment_ref))
        self._table.setCellWidget(row, SIDE_COLUMN, _combo(list(DITCH_RUN_SIDES), run.side))
        self._table.setCellWidget(row, DITCH_COLUMN, _combo([choice.subassembly_ref for choice in self._choices], run.subassembly_ref))
        self._table.setItem(row, START_COLUMN, QtWidgets.QTableWidgetItem(f"{float(run.station_start):.3f}"))
        self._table.setItem(row, END_COLUMN, QtWidgets.QTableWidgetItem(f"{float(run.station_end):.3f}"))
        on_item = QtWidgets.QTableWidgetItem("")
        on_item.setFlags((on_item.flags() | QtCore.Qt.ItemIsUserCheckable) & ~QtCore.Qt.ItemIsEditable)
        on_item.setCheckState(QtCore.Qt.Checked if run.enabled else QtCore.Qt.Unchecked)
        self._table.setItem(row, ON_COLUMN, on_item)

    def _new_run(self) -> DitchRun:
        """A run on the first ditch and side, over the span the prefill gives that road."""

        choice = self._choices[0] if self._choices else None
        subassembly_ref = choice.subassembly_ref if choice is not None else ""
        side = choice.sides[0] if choice is not None and choice.sides else DITCH_RUN_SIDES[0]
        alignment_id = self._alignment_ids[0]
        spans = [run for run in self._prefill if run.alignment_ref == alignment_id] or self._prefill
        start = min((run.station_start for run in spans), default=0.0)
        end = max((run.station_end for run in spans), default=0.0)
        used = {self._text(row, ID_COLUMN) for row in range(self._table.rowCount())}
        index = 1
        while ditch_run_id(alignment_id, side, subassembly_ref, index) in used:
            index += 1
        return DitchRun(ditch_run_id(alignment_id, side, subassembly_ref, index), side, subassembly_ref, start, end, alignment_ref=alignment_id)

    def _fill_from_assembly(self) -> None:
        if not self._prefill:
            self._set_status("The Assembly has no ditch on any Region, so there is nothing to fill.")
            return
        self._set_runs(self._prefill)
        self._set_status(f"{len(self._prefill)} Ditch Run(s) filled from the Regions and the Assembly. Apply to keep them.")

    def _delete_selected_row(self) -> None:
        rows = sorted({index.row() for index in self._table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self._table.removeRow(row)

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            model = self._model_from_panel()
            obj = apply_v1_drainage_model(document=self.document, drainage_model=model)
        except (ValueError, RuntimeError) as exc:
            self._set_status(str(exc))
            return False
        self._model = model
        self._set_status(
            f"Applied to {obj.Label}: {len(model.ditch_run_rows)} Ditch Run(s). "
            "Rebuild Applied Sections to tag the ditch points."
        )
        if close_after and _gui_available():
            Gui.Control.closeDialog()
        return True

    def _model_from_panel(self) -> DrainageModel:
        policy = DrainagePolicy(
            min_grade_percent=float(self._min_grade.value()),
            max_inlet_spacing_m=float(self._max_spacing.value()),
            low_point_rule=str(self._low_point_rule.currentData() or LOW_POINT_RULES[0]),
        )
        return DrainageModel(
            schema_version=self._model.schema_version,
            project_id=self._model.project_id,
            label=self._model.label or "Drainage",
            drainage_model_id=self._model.drainage_model_id,
            policy=policy,
            ditch_run_rows=[self._run(row) for row in range(self._table.rowCount())],
            point_rows=list(self._model.point_rows),
            link_rows=list(self._model.link_rows),
        )

    def _run(self, row: int) -> DitchRun:
        on_item = self._table.item(row, ON_COLUMN)
        return DitchRun(
            ditch_run_id=self._text(row, ID_COLUMN),
            side=self._combo_text(row, SIDE_COLUMN),
            subassembly_ref=self._combo_text(row, DITCH_COLUMN),
            station_start=_station(self._text(row, START_COLUMN), row, "Start STA"),
            station_end=_station(self._text(row, END_COLUMN), row, "End STA"),
            alignment_ref=self._combo_text(row, ROAD_COLUMN),
            enabled=on_item is None or on_item.checkState() == QtCore.Qt.Checked,
        )

    def _text(self, row: int, column: int) -> str:
        item = self._table.item(row, column)
        return str(item.text() if item is not None else "").strip()

    def _combo_text(self, row: int, column: int) -> str:
        combo = self._table.cellWidget(row, column)
        return str(combo.currentText() if combo is not None else "").strip()

    def _set_status(self, text: str) -> None:
        self._status.setPlainText(str(text or ""))


def _combo(values: list[str], current: str):
    combo = QtWidgets.QComboBox()
    items = list(values)
    if current and current not in items:
        # keep a value the Assembly no longer has visible, so Apply reports it instead of hiding it
        items.append(current)
    combo.addItems(items)
    if current:
        combo.setCurrentText(current)
    return combo


def _station(text: str, row: int, column_name: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"Ditch Run row {row + 1}: {column_name} '{text}' is not a number.") from None


def _gui_available() -> bool:
    return bool(Gui is not None and getattr(App, "GuiUp", False))

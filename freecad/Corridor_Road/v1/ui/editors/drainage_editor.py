"""Drainage editor panel for CorridorRoad v1.

The panel edits the Drainage Policy, the Ditch Runs (which Assembly ditch drains which side of
which road over which stations) and the Points (inlets and outfalls on a run, culverts crossing the
road). Nothing is written until Apply; opening the panel prefills the runs from the Regions and the
Assembly when the stored Drainage has none, and adding a suggestion only adds a table row.
"""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets
from freecad.Corridor_Road.v1.models.source.drainage_model import (
    DITCH_RUN_SIDES,
    DRAINAGE_POINT_KINDS,
    LOW_POINT_RULES,
    DitchRun,
    DrainageModel,
    DrainagePoint,
    DrainagePolicy,
)
from freecad.Corridor_Road.v1.services.editing.drainage_editing_service import ditch_run_id, next_point_id
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
drainage_status_text = None
drainage_suggestions = None
refresh_drainage_result = None

COLUMNS = ("ID", "Road", "Side", "Ditch", "Start STA", "End STA", "On")
ID_COLUMN, ROAD_COLUMN, SIDE_COLUMN, DITCH_COLUMN, START_COLUMN, END_COLUMN, ON_COLUMN = range(len(COLUMNS))
LOW_POINT_LABELS = {"require_inlet": "Needs an inlet or outfall", "allow_ponding": "May pond"}
POINT_COLUMNS = ("ID", "Kind", "Ditch Run", "STA")
POINT_ID_COLUMN, POINT_KIND_COLUMN, POINT_RUN_COLUMN, POINT_STATION_COLUMN = range(len(POINT_COLUMNS))
# A culvert crosses the road and collects from every run it meets, so it may name no run.
CROSSES_ROAD = ""


class V1DrainageEditorTaskPanel:
    """Drainage Policy, Ditch Runs and Points editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        inputs = drainage_editor_inputs(self.document)
        self._model: DrainageModel = inputs["model"]
        self._choices = list(inputs["choices"])
        self._alignment_ids = [value for value in inputs["alignment_ids"]] or [""]
        self._prefill: list[DitchRun] = list(inputs["prefill"])
        self._suggestions: list = []
        self.form = fit_task_panel_width(self._build_ui())
        self._load(self._model)
        self._refresh_suggestions()
        if inputs["prefilled"]:
            self._set_status(
                f"{len(self._model.ditch_run_rows)} Ditch Run(s) filled from the Regions and the Assembly. "
                "Apply to keep them."
            )
        elif not self._choices:
            self._set_status("The Assembly has no ditch. Add a ditch Subassembly to the Assembly first.")
        else:
            self._set_status(drainage_status_text(self.document))

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

        self._tabs = QtWidgets.QTabWidget()
        runs_tab = QtWidgets.QWidget()
        runs_layout = QtWidgets.QVBoxLayout(runs_tab)
        runs_layout.addWidget(QtWidgets.QLabel("The Assembly ditches that drain the road"))
        self._table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(list(COLUMNS))
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        try:
            self._table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._table.setColumnHidden(ROAD_COLUMN, len(self._alignment_ids) <= 1)
        runs_layout.addWidget(self._table, 1)

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
        runs_layout.addLayout(edit_row)
        self._tabs.addTab(runs_tab, "Ditch Runs")
        self._tabs.addTab(self._build_points_tab(), "Points")
        # the Points tab names runs, so its run lists follow the Ditch Runs tab
        self._tabs.currentChanged.connect(lambda _index: self._refresh_point_run_choices())
        layout.addWidget(self._tabs, 1)

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

    def _build_points_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.addWidget(QtWidgets.QLabel("Inlets and outfalls on a Ditch Run; culverts crossing the road"))
        self._point_table = QtWidgets.QTableWidget(0, len(POINT_COLUMNS))
        self._point_table.setHorizontalHeaderLabels(list(POINT_COLUMNS))
        self._point_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        try:
            self._point_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._point_table, 1)
        point_row = QtWidgets.QHBoxLayout()
        for label, kind in (("Add Inlet", "inlet"), ("Add Outfall", "outfall"), ("Add Culvert", "culvert")):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda _checked=False, kind=kind: self._append_point(None, kind=kind))
            point_row.addWidget(button)
        delete_button = QtWidgets.QPushButton("Delete Point")
        delete_button.clicked.connect(self._delete_selected_points)
        point_row.addWidget(delete_button)
        point_row.addStretch(1)
        layout.addLayout(point_row)

        layout.addWidget(QtWidgets.QLabel("Suggestions from the Drainage checks"))
        self._suggestion_list = QtWidgets.QListWidget()
        self._suggestion_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self._suggestion_list, 1)
        self._suggestion_note = QtWidgets.QLabel("")
        self._suggestion_note.setWordWrap(True)
        layout.addWidget(self._suggestion_note)
        suggestion_row = QtWidgets.QHBoxLayout()
        add_selected = QtWidgets.QPushButton("Add Selected")
        add_selected.setToolTip("Add the selected suggestions as points; Apply keeps them.")
        add_selected.clicked.connect(lambda: self._add_suggestions(selected_only=True))
        suggestion_row.addWidget(add_selected)
        add_all = QtWidgets.QPushButton("Add All")
        add_all.clicked.connect(lambda: self._add_suggestions(selected_only=False))
        suggestion_row.addWidget(add_all)
        suggestion_row.addStretch(1)
        layout.addLayout(suggestion_row)
        return tab

    def _append_point(self, point: DrainagePoint | None, *, kind: str = "inlet") -> None:
        if point is None:
            runs = self._run_ids()
            run_ref = CROSSES_ROAD if kind == "culvert" or not runs else runs[0]
            point = DrainagePoint(next_point_id(kind, self._point_ids()), kind, 0.0, ditch_run_ref=run_ref)
        row = self._point_table.rowCount()
        self._point_table.insertRow(row)
        id_item = QtWidgets.QTableWidgetItem(point.point_id)
        id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self._point_table.setItem(row, POINT_ID_COLUMN, id_item)
        self._point_table.setCellWidget(row, POINT_KIND_COLUMN, _combo(list(DRAINAGE_POINT_KINDS), point.kind))
        self._point_table.setCellWidget(row, POINT_RUN_COLUMN, _combo([CROSSES_ROAD, *self._run_ids()], point.ditch_run_ref))
        self._point_table.setItem(row, POINT_STATION_COLUMN, QtWidgets.QTableWidgetItem(f"{float(point.station):.3f}"))

    def _delete_selected_points(self) -> None:
        for row in sorted({index.row() for index in self._point_table.selectionModel().selectedRows()}, reverse=True):
            self._point_table.removeRow(row)

    def _refresh_point_run_choices(self) -> None:
        runs = [CROSSES_ROAD, *self._run_ids()]
        for row in range(self._point_table.rowCount()):
            current = self._point_text(row, POINT_RUN_COLUMN, combo=True)
            self._point_table.setCellWidget(row, POINT_RUN_COLUMN, _combo(runs, current))

    def _refresh_suggestions(self) -> None:
        self._suggestions, note = drainage_suggestions(self.document)
        self._suggestion_list.clear()
        for row in self._suggestions:
            self._suggestion_list.addItem(f"{row.kind} | {row.ditch_run_ref} | STA {row.station:.3f} | {row.message}")
        self._suggestion_note.setText(note)

    def _add_suggestions(self, *, selected_only: bool) -> None:
        indexes = (
            sorted(self._suggestion_list.row(item) for item in self._suggestion_list.selectedItems())
            if selected_only
            else range(len(self._suggestions))
        )
        present = {(point.kind, point.ditch_run_ref, round(point.station, 3)) for point in self._points()}
        added = 0
        for index in indexes:
            row = self._suggestions[index]
            if (row.kind, row.ditch_run_ref, round(row.station, 3)) in present:
                continue
            self._append_point(DrainagePoint(next_point_id(row.kind, self._point_ids()), row.kind, row.station, ditch_run_ref=row.ditch_run_ref))
            added += 1
        self._set_status(f"{added} suggested point(s) added to the Points table. Apply to keep them.")

    def _run_ids(self) -> list[str]:
        return [self._text(row, ID_COLUMN) for row in range(self._table.rowCount())]

    def _point_ids(self) -> set[str]:
        return {self._point_text(row, POINT_ID_COLUMN) for row in range(self._point_table.rowCount())}

    def _points(self) -> list[DrainagePoint]:
        runs = {run.ditch_run_id: run for run in (self._run(row) for row in range(self._table.rowCount()))}
        points = []
        for row in range(self._point_table.rowCount()):
            run_ref = self._point_text(row, POINT_RUN_COLUMN, combo=True)
            run = runs.get(run_ref)
            text = self._point_text(row, POINT_STATION_COLUMN)
            try:
                station = float(text)
            except ValueError:
                raise ValueError(f"Point row {row + 1}: STA '{text}' is not a number.") from None
            points.append(
                DrainagePoint(
                    point_id=self._point_text(row, POINT_ID_COLUMN),
                    kind=self._point_text(row, POINT_KIND_COLUMN, combo=True),
                    station=station,
                    side=run.side if run is not None else "",
                    ditch_run_ref=run_ref,
                    # a point takes its run's road; a crossing culvert the first road
                    alignment_ref=run.alignment_ref if run is not None else self._alignment_ids[0],
                )
            )
        return points

    def _point_text(self, row: int, column: int, *, combo: bool = False) -> str:
        if combo:
            widget = self._point_table.cellWidget(row, column)
            return str(widget.currentText() if widget is not None else "").strip()
        item = self._point_table.item(row, column)
        return str(item.text() if item is not None else "").strip()

    def _load(self, model: DrainageModel) -> None:
        policy = model.policy
        self._min_grade.setValue(float(policy.min_grade_percent))
        self._max_spacing.setValue(float(policy.max_inlet_spacing_m))
        index = self._low_point_rule.findData(policy.low_point_rule)
        self._low_point_rule.setCurrentIndex(max(index, 0))
        self._set_runs(model.ditch_run_rows)
        self._point_table.setRowCount(0)
        for point in model.point_rows:
            self._append_point(point)

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
        road = alignment_id if len(self._alignment_ids) > 1 else ""
        while ditch_run_id(subassembly_ref, side, index, road=road) in used:
            index += 1
        run_id = ditch_run_id(subassembly_ref, side, index, road=road)
        return DitchRun(run_id, side, subassembly_ref, start, end, alignment_ref=alignment_id)

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
        try:
            evaluation = refresh_drainage_result(self.document)
        except RuntimeError as exc:
            evaluation = f"The Drainage was not evaluated: {exc}"
        self._set_status(
            f"Applied to {obj.Label}: {len(model.ditch_run_rows)} Ditch Run(s), {len(model.point_rows)} point(s).\n{evaluation}"
        )
        self._refresh_suggestions()
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
            point_rows=self._points(),
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

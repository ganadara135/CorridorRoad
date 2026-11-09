"""Drainage Review panel for CorridorRoad v1.

A read-only review of the Drainage output: each Ditch Run's flowline profile with its inlets,
outfalls, culverts, low and high points and the stretches a check flags, and the checks table. A
double-clicked check is highlighted on the flowline in the 3D view. Nothing here edits a source.
"""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtGui, QtWidgets
from freecad.Corridor_Road.v1.ui.common.flowline_profile_widget import LEGEND_TEXT, SEVERITY_COLORS, FlowlineProfileWidget
from freecad.Corridor_Road.v1.ui.common.panel_width import fit_task_panel_width
from freecad.Corridor_Road.v1.ui.presentation.drainage_review_presentation import (
    drainage_check_table_rows,
    drainage_flowline_profile,
    drainage_pipe_table_rows,
    drainage_review_run_rows,
    drainage_review_summary,
)


def configure_drainage_review_task_panel_runtime(bindings) -> None:
    """Bind command collaborators without importing the command module."""

    for name, value in dict(bindings or {}).items():
        globals()[name] = value


# Runtime collaborators, bound by the command module.
App = None
Gui = None
drainage_review_state = None
focus_drainage_check = None
focus_drainage_pipe = None
open_drainage_editor = None

CHECK_COLUMNS = ("Severity", "Check", "Ditch Run", "STA", "Message")
PIPE_COLUMNS = ("Link", "Route", "Dia (m)", "Length (m)", "Inverts (m)", "Grade (%)", "Volume (m3)")


class V1DrainageReviewTaskPanel:
    """Read-only Drainage Review panel."""

    def __init__(self, *, document=None):
        self.document = document
        self._output = None
        self._pipe_refs: list = []
        self.form = fit_task_panel_width(self._build_ui())
        self._refresh()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self.reject()

    def reject(self):
        if Gui is not None and bool(getattr(App, "GuiUp", False)) and hasattr(Gui, "Control"):
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("ParametricRoad v1 - Drainage Review")
        layout = QtWidgets.QVBoxLayout(widget)
        self._summary = QtWidgets.QLabel("")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)
        self._freshness = QtWidgets.QLabel("")
        self._freshness.setWordWrap(True)
        layout.addWidget(self._freshness)

        self._run_combo = QtWidgets.QComboBox()
        self._run_combo.currentIndexChanged.connect(lambda _index: self._show_run())
        layout.addWidget(self._run_combo)
        self._profile = FlowlineProfileWidget()
        layout.addWidget(self._profile)
        legend = QtWidgets.QLabel(LEGEND_TEXT)
        legend.setWordWrap(True)
        layout.addWidget(legend)

        self._checks = QtWidgets.QTableWidget(0, len(CHECK_COLUMNS))
        self._checks.setHorizontalHeaderLabels(list(CHECK_COLUMNS))
        self._checks.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._checks.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        try:
            self._checks.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._checks.cellDoubleClicked.connect(lambda row, _column: self._focus_check(row))
        layout.addWidget(self._checks, 1)
        layout.addWidget(QtWidgets.QLabel("Pipes on the links (double-click to draw one in the 3D view)"))
        self._pipes = QtWidgets.QTableWidget(0, len(PIPE_COLUMNS))
        self._pipes.setHorizontalHeaderLabels(list(PIPE_COLUMNS))
        self._pipes.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._pipes.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._pipes.setMaximumHeight(130)
        try:
            self._pipes.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._pipes.cellDoubleClicked.connect(lambda row, _column: self._focus_pipe(row))
        layout.addWidget(self._pipes)
        self._status = QtWidgets.QLabel("Double-click a check to highlight it on the flowline.")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        buttons = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh)
        buttons.addWidget(refresh_button)
        self._all_pipes_button = QtWidgets.QPushButton("Show All Pipes")
        self._all_pipes_button.setToolTip("Draw every pipe as a tube in the 3D view.")
        self._all_pipes_button.clicked.connect(lambda: self._focus_pipe(-1))
        buttons.addWidget(self._all_pipes_button)
        editor_button = QtWidgets.QPushButton("Drainage")
        editor_button.setToolTip("Close the review and open the Drainage panel.")
        editor_button.clicked.connect(lambda: open_drainage_editor(self.document))
        buttons.addWidget(editor_button)
        buttons.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        return widget

    def _refresh(self) -> None:
        self._output, freshness = drainage_review_state(self.document)
        self._summary.setText(drainage_review_summary(self._output))
        self._freshness.setText(freshness)
        self._run_combo.blockSignals(True)
        self._run_combo.clear()
        for row in drainage_review_run_rows(self._output) if self._output is not None else []:
            counts = f" [{row['errors']} error(s), {row['warnings']} warning(s)]" if row["errors"] or row["warnings"] else ""
            self._run_combo.addItem(str(row["label"]) + counts, row["ditch_run_ref"])
        self._run_combo.blockSignals(False)
        self._show_run()
        self._show_pipes()

    def _show_run(self) -> None:
        run_ref = str(self._run_combo.currentData() or "")
        self._profile.set_profile(drainage_flowline_profile(self._output, run_ref) if self._output is not None and run_ref else None)
        rows = drainage_check_table_rows(self._output, run_ref) if self._output is not None else []
        self._check_refs = [row["check_ref"] for row in rows]
        self._checks.setRowCount(0)
        for row in rows:
            index = self._checks.rowCount()
            self._checks.insertRow(index)
            for column, key in enumerate(("severity", "kind", "ditch_run_ref", "stations", "message")):
                item = QtWidgets.QTableWidgetItem(str(row[key]))
                if key == "severity":
                    item.setForeground(QtGui.QBrush(QtGui.QColor(*SEVERITY_COLORS.get(row["severity"], (0, 0, 0)))))
                self._checks.setItem(index, column, item)

    def _show_pipes(self) -> None:
        rows = drainage_pipe_table_rows(self._output) if self._output is not None else []
        self._pipe_refs = [row["link_ref"] for row in rows]
        self._pipes.setRowCount(0)
        for row in rows:
            index = self._pipes.rowCount()
            self._pipes.insertRow(index)
            for column, key in enumerate(("link_ref", "route", "diameter", "length", "inverts", "grade", "volume")):
                self._pipes.setItem(index, column, QtWidgets.QTableWidgetItem(str(row[key])))
        self._all_pipes_button.setEnabled(bool(rows))

    def _focus_pipe(self, row: int) -> None:
        """Draw the pipe of a table row, or all of them for row -1."""

        if row >= len(self._pipe_refs):
            return
        try:
            obj = focus_drainage_pipe(self.document, self._pipe_refs[row] if row >= 0 else "")
        except (RuntimeError, ValueError) as exc:
            self._status.setText(f"The pipe was not drawn: {exc}")
            return
        self._status.setText(f"Drawn in the 3D view: {getattr(obj, 'Label', '')}.")

    def _focus_check(self, row: int) -> None:
        if row < 0 or row >= len(self._check_refs):
            return
        try:
            obj = focus_drainage_check(self.document, self._check_refs[row])
        except (RuntimeError, ValueError) as exc:
            self._status.setText(f"The check was not highlighted: {exc}")
            return
        self._status.setText(f"Highlighted on the flowline: {getattr(obj, 'Label', '')}.")

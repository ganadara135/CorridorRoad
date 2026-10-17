"""Drainage Review panel for CorridorRoad v1.

A read-only review of the Drainage output: each Ditch Run's flowline profile with its inlets,
outfalls, culverts, low and high points and the stretches a check flags, and the checks table. A
double-clicked check is highlighted on the flowline in the 3D view. Nothing here edits a source.
"""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets
from freecad.Corridor_Road.v1.ui.common.panel_width import fit_task_panel_width
from freecad.Corridor_Road.v1.ui.presentation.drainage_review_presentation import (
    drainage_check_table_rows,
    drainage_flowline_profile,
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
open_drainage_editor = None

CHECK_COLUMNS = ("Severity", "Check", "Ditch Run", "STA", "Message")
SEVERITY_COLORS = {"error": (200, 40, 40), "warning": (220, 140, 20), "info": (90, 90, 90)}
MARKER_COLORS = {"inlet": (30, 140, 60), "outfall": (20, 60, 170), "culvert": (130, 60, 160)}


class _FlowlineProfileWidget(QtWidgets.QWidget):
    """The flowline elevation along station, with its points and flagged stretches."""

    def __init__(self):
        super().__init__()
        self._profile = None
        self.setMinimumHeight(220)

    def set_profile(self, profile) -> None:
        self._profile = profile
        self.update()

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.fillRect(self.rect(), QtGui.QColor(250, 250, 250))
            profile = self._profile
            if profile is None or len(profile.points) < 2:
                painter.drawText(self.rect(), QtCore.Qt.AlignCenter, "No flowline to draw.")
                return
            stations = [station for station, _z in profile.points]
            elevations = [z for _station, z in profile.points] + [marker.z for marker in profile.markers]
            s0, s1 = min(stations), max(stations)
            z0, z1 = min(elevations), max(elevations)
            if z1 - z0 < 0.1:
                # keep a near-flat flowline readable: at least 0.1 m of height
                middle = (z0 + z1) / 2.0
                z0, z1 = middle - 0.05, middle + 0.05
            left, right, top, bottom = 56, 12, 14, 30
            width = max(self.width() - left - right, 1)
            height = max(self.height() - top - bottom, 1)

            def at(station: float, z: float) -> QtCore.QPointF:
                x = left + (station - s0) / max(s1 - s0, 1.0e-9) * width
                y = top + (z1 - z) / max(z1 - z0, 1.0e-9) * height
                return QtCore.QPointF(x, y)

            painter.setPen(QtGui.QPen(QtGui.QColor(120, 120, 120), 1))
            painter.drawText(4, top + 10, f"{z1:.2f}")
            painter.drawText(4, top + height, f"{z0:.2f}")
            painter.drawText(left, self.height() - 8, f"STA {s0:.1f}")
            painter.drawText(left + width - 80, self.height() - 8, f"STA {s1:.1f}")

            painter.setPen(QtGui.QPen(QtGui.QColor(40, 110, 200), 2))
            painter.drawPolyline(QtGui.QPolygonF([at(station, z) for station, z in profile.points]))
            for start, end, severity in profile.flagged:
                stretch = [at(station, z) for station, z in profile.points if start - 1.0e-6 <= station <= end + 1.0e-6]
                if len(stretch) >= 2:
                    painter.setPen(QtGui.QPen(QtGui.QColor(*SEVERITY_COLORS.get(severity, (90, 90, 90))), 5))
                    painter.drawPolyline(QtGui.QPolygonF(stretch))

            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(40, 110, 200))
            for station, z in profile.low_points:
                painter.drawEllipse(at(station, z), 4.0, 4.0)
            painter.setBrush(QtGui.QColor(150, 150, 150))
            for station, z in profile.high_points:
                painter.drawEllipse(at(station, z), 3.0, 3.0)
            for marker in profile.markers:
                point = at(marker.station, marker.z)
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(QtGui.QColor(*MARKER_COLORS.get(marker.kind, (0, 0, 0))))
                painter.drawRect(QtCore.QRectF(point.x() - 5.0, point.y() - 5.0, 10.0, 10.0))
                painter.setPen(QtGui.QPen(QtGui.QColor(30, 30, 30), 1))
                painter.drawText(point + QtCore.QPointF(6.0, -6.0), marker.label)
        finally:
            painter.end()


class V1DrainageReviewTaskPanel:
    """Read-only Drainage Review panel."""

    def __init__(self, *, document=None):
        self.document = document
        self._output = None
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
        self._profile = _FlowlineProfileWidget()
        layout.addWidget(self._profile)
        legend = QtWidgets.QLabel(
            "Blue line: flowline. Thick orange or red: a flagged stretch. Blue dots: low points; grey: high points. "
            "Squares: inlets (green), outfalls (blue), culverts (purple)."
        )
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
        self._status = QtWidgets.QLabel("Double-click a check to highlight it on the flowline.")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        buttons = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh)
        buttons.addWidget(refresh_button)
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

    def _focus_check(self, row: int) -> None:
        if row < 0 or row >= len(self._check_refs):
            return
        try:
            obj = focus_drainage_check(self.document, self._check_refs[row])
        except (RuntimeError, ValueError) as exc:
            self._status.setText(f"The check was not highlighted: {exc}")
            return
        self._status.setText(f"Highlighted on the flowline: {getattr(obj, 'Label', '')}.")

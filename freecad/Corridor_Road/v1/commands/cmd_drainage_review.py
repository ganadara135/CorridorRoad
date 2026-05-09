"""Drainage review command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtWidgets

from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..objects.obj_drainage import find_v1_drainage_model, to_drainage_model
from ..objects.obj_region import find_v1_region_model, to_region_model
from ..services.mapping.drainage_review_mapper import DrainageReviewMapper


class CmdV1DrainageReview:
    """Open a read-only Drainage Review panel."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("drainage_review.svg"),
            "MenuText": "Drainage Review",
            "ToolTip": "Review v1 drainage source handoff, Region refs, and Applied Section ditch context",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_drainage_review_command()


def run_v1_drainage_review_command(document=None):
    """Open the v1 Drainage Review task panel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    panel = V1DrainageReviewTaskPanel(document=doc)
    if _gui_available() and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


def build_drainage_review_output(document=None):
    """Build the read-only DrainageOutput payload from active document objects."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    drainage_model = to_drainage_model(find_v1_drainage_model(doc))
    region_model = to_region_model(find_v1_region_model(doc))
    applied_section_set = to_applied_section_set(find_v1_applied_section_set(doc))
    project_id = (
        str(getattr(drainage_model, "project_id", "") or "")
        or str(getattr(region_model, "project_id", "") or "")
        or str(getattr(applied_section_set, "project_id", "") or "")
        or "corridorroad-v1"
    )
    return DrainageReviewMapper().map(
        drainage_model=drainage_model,
        region_model=region_model,
        applied_section_set=applied_section_set,
        project_id=project_id,
    )


class V1DrainageReviewTaskPanel:
    """Read-only review panel for Drainage handoff context."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.output = None
        self.form = self._build_ui()
        self.refresh()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self.reject()

    def reject(self):
        if _gui_available():
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - Drainage Review")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Drainage Review")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        self._summary_table = _table(["Metric", "Value", "Unit"])
        self._summary_table.setMaximumHeight(150)
        layout.addWidget(self._summary_table)

        self._tabs = QtWidgets.QTabWidget()
        self._element_table = _table(["Kind", "Label", "Start STA", "End STA", "Source", "Notes"])
        self._region_table = _table(["Region", "Start STA", "End STA", "Drainage Status", "Notes"])
        self._applied_table = _table(["Station", "Section", "Ditch Points", "Drainage Refs", "Notes"])
        self._tabs.addTab(self._element_table, "Elements")
        self._tabs.addTab(self._region_table, "Region Handoff")
        self._tabs.addTab(self._applied_table, "Applied Sections")
        layout.addWidget(self._tabs, 1)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setFixedHeight(80)
        layout.addWidget(self._status)

        action_row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        action_row.addWidget(refresh_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        return widget

    def refresh(self) -> None:
        self.output = build_drainage_review_output(self.document)
        _populate_summary_table(self._summary_table, self.output.summary_rows)
        _populate_element_table(self._element_table, [row for row in self.output.element_rows if row.kind == "drainage_element"])
        _populate_region_table(self._region_table, [row for row in self.output.element_rows if row.kind == "region_handoff"])
        _populate_applied_table(
            self._applied_table,
            [row for row in self.output.element_rows if row.kind == "applied_section_ditch_context"],
        )
        self._status.setPlainText(_status_text(self.output))


def _table(headers: list[str]):
    table = QtWidgets.QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    try:
        table.horizontalHeader().setStretchLastSection(True)
    except Exception:
        pass
    return table


def _populate_summary_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(table, [row.label, str(row.value), row.unit])


def _populate_element_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(table, [row.kind, row.label, _format_float(row.station_start), _format_float(row.station_end), row.source_ref, row.notes])


def _populate_region_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        status = _note_value(row.notes, "status")
        _append_items(table, [row.label, _format_float(row.station_start), _format_float(row.station_end), status, row.notes])


def _populate_applied_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(
            table,
            [
                _format_float(row.station_start),
                row.source_ref,
                _note_value(row.notes, "ditch_points"),
                _note_value(row.notes, "drainage_refs"),
                row.notes,
            ],
        )


def _append_items(table, values: list[object]) -> None:
    index = table.rowCount()
    table.insertRow(index)
    for column, value in enumerate(values):
        table.setItem(index, column, QtWidgets.QTableWidgetItem(str(value or "")))


def _status_text(output) -> str:
    summary = {row.summary_id: row.value for row in list(getattr(output, "summary_rows", []) or [])}
    missing = int(summary.get("summary:missing-region-refs", 0) or 0)
    ditch_points = int(summary.get("summary:ditch-surface-points", 0) or 0)
    ditch_with_refs = int(summary.get("summary:ditch-surface-points-with-drainage", 0) or 0)
    lines = [
        f"Drainage Review rows: {len(list(getattr(output, 'element_rows', []) or []))}",
        f"Source refs: {', '.join(list(getattr(output, 'source_refs', []) or []))}",
    ]
    if missing:
        lines.append(f"Warnings: {missing} Region drainage ref(s) are missing from the active DrainageModel.")
    if ditch_points and ditch_with_refs < ditch_points:
        lines.append(f"Warnings: {ditch_points - ditch_with_refs} ditch_surface point(s) have no drainage_ref.")
    if len(lines) == 2:
        lines.append("No blocking Drainage Review diagnostics in the first-slice checks.")
    return "\n".join(lines)


def _note_value(notes: str, key: str) -> str:
    prefix = str(key or "") + "="
    for token in str(notes or "").split(";"):
        if token.startswith(prefix):
            return token[len(prefix) :]
    return ""


def _format_float(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"


def _gui_available() -> bool:
    return bool(Gui is not None and getattr(App, "GuiUp", False))


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1DrainageReview", CmdV1DrainageReview())

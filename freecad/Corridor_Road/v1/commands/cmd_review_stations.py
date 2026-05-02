"""v1 stationing generation, review, and settings panel."""

from __future__ import annotations

import math

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None
try:
    import Part
except Exception:  # pragma: no cover - Part is not available in plain Python.
    Part = None

from freecad.Corridor_Road.qt_compat import QtWidgets

from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_stationing import (
    ensure_v1_stationing_properties,
    find_v1_stationing,
    update_v1_stationing_from_alignment,
)
from .cmd_generate_stations import generate_v1_stations
from .selection_context import selected_alignment_profile_target


def stationing_review_summary_lines(stationing) -> list[str]:
    """Return compact summary lines for one V1Stationing object."""

    if stationing is None:
        return ["No V1Stationing object is available.", "Click Apply to generate stations from the current alignment."]
    ensure_v1_stationing_properties(stationing)
    station_count = len(list(getattr(stationing, "StationValues", []) or []))
    return [
        "CorridorRoad v1 Stationing Review",
        f"Stationing: {str(getattr(stationing, 'Label', '') or getattr(stationing, 'Name', '') or '')}",
        f"AlignmentId: {str(getattr(stationing, 'AlignmentId', '') or '')}",
        f"Source alignment: {str(getattr(stationing, 'SourceAlignmentLabel', '') or '')}",
        f"Stations: {station_count}",
        f"Interval: {float(getattr(stationing, 'Interval', 0.0) or 0.0):.3f} m",
        f"Major interval: {float(getattr(stationing, 'MajorInterval', 0.0) or 0.0):.3f} m",
        f"Station offset: {float(getattr(stationing, 'StationStartOffset', 0.0) or 0.0):.3f} m",
        f"Label format: {str(getattr(stationing, 'StationLabelFormat', '') or '')}",
        f"Kind summary: {str(getattr(stationing, 'ActiveElementKindSummary', '') or '')}",
        f"Station kind counts: key={int(getattr(stationing, 'KeyStationCount', 0) or 0)}, major={int(getattr(stationing, 'MajorStationCount', 0) or 0)}, minor={int(getattr(stationing, 'MinorStationCount', 0) or 0)}",
        f"Element station counts: tangent={int(getattr(stationing, 'TangentStationCount', 0) or 0)}, curve={int(getattr(stationing, 'CurveStationCount', 0) or 0)}, transition={int(getattr(stationing, 'TransitionStationCount', 0) or 0)}",
        f"Display ticks: {int(getattr(stationing, 'DisplayTickCount', 0) or 0)}",
        f"Display status: {str(getattr(stationing, 'DisplayStatus', '') or '')}",
        f"Status: {str(getattr(stationing, 'Status', '') or '')}",
        f"Notes: {str(getattr(stationing, 'Notes', '') or '')}",
    ]


def stationing_table_rows(stationing) -> list[dict[str, object]]:
    """Return table-friendly stationing rows."""

    if stationing is None:
        return []
    ensure_v1_stationing_properties(stationing)
    stations = _float_list(getattr(stationing, "StationValues", []) or [])
    labels = list(getattr(stationing, "StationLabels", []) or [])
    station_kinds = list(getattr(stationing, "StationKinds", []) or [])
    xs = _float_list(getattr(stationing, "XValues", []) or [])
    ys = _float_list(getattr(stationing, "YValues", []) or [])
    tangents = _float_list(getattr(stationing, "TangentDirections", []) or [])
    element_kinds = list(getattr(stationing, "ActiveElementKinds", []) or [])
    reasons = list(getattr(stationing, "SourceReasons", []) or [])
    rows = []
    for index, station in enumerate(stations):
        rows.append(
            {
                "station": float(station),
                "label": str(labels[index]) if index < len(labels) and labels[index] else f"STA {station:.3f}",
                "station_kind": str(station_kinds[index]) if index < len(station_kinds) and station_kinds[index] else "-",
                "x": xs[index] if index < len(xs) else 0.0,
                "y": ys[index] if index < len(ys) else 0.0,
                "tangent": tangents[index] if index < len(tangents) else 0.0,
                "element_kind": str(element_kinds[index]) if index < len(element_kinds) and element_kinds[index] else "-",
                "reason": str(reasons[index]) if index < len(reasons) and reasons[index] else "-",
            }
        )
    return rows


def station_highlight_shape(row: dict[str, object], *, radius: float = 5.0):
    """Build a 3D marker shape for one station table row."""

    if App is None or Part is None:
        return None
    x = _safe_float(row.get("x", 0.0), 0.0)
    y = _safe_float(row.get("y", 0.0), 0.0)
    tangent = _safe_float(row.get("tangent", 0.0), 0.0)
    marker_radius = max(float(radius), 0.5)
    center = App.Vector(x, y, 0.0)
    tangent_rad = math.radians(tangent)
    tx = math.cos(tangent_rad)
    ty = math.sin(tangent_rad)
    nx = -ty
    ny = tx
    edges = [
        Part.makeCircle(marker_radius, center, App.Vector(0.0, 0.0, 1.0)),
        Part.makeLine(
            App.Vector(x - tx * marker_radius, y - ty * marker_radius, 0.0),
            App.Vector(x + tx * marker_radius, y + ty * marker_radius, 0.0),
        ),
        Part.makeLine(
            App.Vector(x - nx * marker_radius, y - ny * marker_radius, 0.0),
            App.Vector(x + nx * marker_radius, y + ny * marker_radius, 0.0),
        ),
    ]
    return Part.Compound(edges)


def show_station_highlight(document, row: dict[str, object], *, radius: float = 5.0):
    """Create or update the visible 3D marker for a selected station row."""

    if document is None:
        raise RuntimeError("No active document is available for station highlight.")
    shape = station_highlight_shape(row, radius=radius)
    if shape is None:
        return None
    obj = _find_station_highlight(document)
    if obj is None:
        try:
            obj = document.addObject("Part::Feature", "V1StationHighlight")
        except Exception:
            obj = document.addObject("App::FeaturePython", "V1StationHighlight")
        try:
            obj.addProperty("App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
            obj.V1ObjectType = "V1StationHighlight"
        except Exception:
            pass
    label = str(row.get("label", "") or "Station")
    station = _safe_float(row.get("station", 0.0), 0.0)
    obj.Label = f"Station Highlight - {label}"
    try:
        obj.Shape = shape
    except Exception:
        pass
    try:
        obj.addProperty("App::PropertyFloat", "Station", "Stations", "highlighted station")
    except Exception:
        pass
    try:
        obj.Station = float(station)
    except Exception:
        pass
    _route_station_highlight_to_tree(document, obj)
    _style_station_highlight(obj)
    try:
        document.recompute()
    except Exception:
        pass
    return obj


class V1StationingReviewTaskPanel:
    """Generate, review, and adjust v1 stationing settings."""

    def __init__(self, *, stationing=None, document=None, preferred_alignment=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.stationing = stationing or find_v1_stationing(self.document)
        self.preferred_alignment = preferred_alignment
        self.form = self._build_ui()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._apply_settings(close_after=True)

    def reject(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - Stations")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Stations")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        self._summary = QtWidgets.QPlainTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setMinimumHeight(140)
        layout.addWidget(self._summary)

        settings_group = QtWidgets.QGroupBox("Station Generation / Display Settings")
        form = QtWidgets.QFormLayout(settings_group)
        self._interval = _double_spin(0.001, 100000.0, _stationing_float(self.stationing, "Interval", 20.0), 3, " m")
        self._major_interval = _double_spin(0.0, 100000.0, _stationing_float(self.stationing, "MajorInterval", 100.0), 3, " m")
        self._offset = _double_spin(-1000000.0, 1000000.0, _stationing_float(self.stationing, "StationStartOffset", 0.0), 3, " m")
        self._minor_tick = _double_spin(0.0, 100000.0, _stationing_float(self.stationing, "MinorTickLength", 2.0), 3, " m")
        self._major_tick = _double_spin(0.0, 100000.0, _stationing_float(self.stationing, "MajorTickLength", 4.0), 3, " m")
        self._label_format = QtWidgets.QComboBox()
        self._label_format.addItems(["STA_DECIMAL", "STA_PLUS", "PLAIN"])
        _set_combo_text(self._label_format, _stationing_text(self.stationing, "StationLabelFormat", "STA_DECIMAL"))
        self._show_ticks = QtWidgets.QCheckBox("Show station ticks")
        self._show_ticks.setChecked(_stationing_bool(self.stationing, "ShowTicks", True))
        form.addRow("Station interval:", self._interval)
        form.addRow("Major interval:", self._major_interval)
        form.addRow("Station offset:", self._offset)
        form.addRow("Label format:", self._label_format)
        form.addRow("Minor tick length:", self._minor_tick)
        form.addRow("Major tick length:", self._major_tick)
        form.addRow(self._show_ticks)
        layout.addWidget(settings_group)

        self._table = QtWidgets.QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(["Label", "Kind", "Station", "X", "Y", "Tangent", "Element", "Reason"])
        self._table.setMinimumHeight(260)
        try:
            self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        except Exception:
            pass
        self._table.cellDoubleClicked.connect(lambda row, _col: self._locate_station_row(row))
        try:
            self._table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._table, 1)

        button_row = QtWidgets.QHBoxLayout()
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply_settings(close_after=False))
        button_row.addWidget(apply_button)
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh)
        button_row.addWidget(refresh_button)
        button_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        self._refresh()
        return widget

    def _refresh(self) -> None:
        self._summary.setPlainText("\n".join(stationing_review_summary_lines(self.stationing)))
        self._table.setRowCount(0)
        for row in stationing_table_rows(self.stationing):
            self._append_row(row)

    def _append_row(self, row: dict[str, object]) -> None:
        row_index = self._table.rowCount()
        self._table.insertRow(row_index)
        values = [
            str(row.get("label", "")),
            str(row.get("station_kind", "")),
            f"{float(row.get('station', 0.0) or 0.0):.3f}",
            f"{float(row.get('x', 0.0) or 0.0):.3f}",
            f"{float(row.get('y', 0.0) or 0.0):.3f}",
            f"{float(row.get('tangent', 0.0) or 0.0):.3f}",
            str(row.get("element_kind", "")),
            str(row.get("reason", "")),
        ]
        for col, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem(value)
            try:
                item.setFlags(item.flags() & ~2)
            except Exception:
                pass
            self._table.setItem(row_index, col, item)

    def _apply_settings(self, *, close_after: bool = False) -> bool:
        if self.stationing is None:
            self.stationing = generate_v1_stations(
                document=self.document,
                alignment=self.preferred_alignment or find_v1_alignment(self.document),
                interval=float(self._interval.value()),
            )
        ensure_v1_stationing_properties(self.stationing)
        self.stationing.Interval = float(self._interval.value())
        self.stationing.MajorInterval = float(self._major_interval.value())
        self.stationing.StationStartOffset = float(self._offset.value())
        self.stationing.StationLabelFormat = str(self._label_format.currentText() or "STA_DECIMAL")
        self.stationing.MinorTickLength = float(self._minor_tick.value())
        self.stationing.MajorTickLength = float(self._major_tick.value())
        self.stationing.ShowTicks = bool(self._show_ticks.isChecked())

        alignment = self.preferred_alignment or find_v1_alignment(self.document)
        alignment_model = to_alignment_model(alignment) if alignment is not None else None
        if alignment_model is not None:
            update_v1_stationing_from_alignment(
                self.stationing,
                alignment_model,
                interval=float(self._interval.value()),
            )
        try:
            self.stationing.touch()
        except Exception:
            pass
        if self.document is not None:
            try:
                self.document.recompute()
            except Exception:
                pass
        self._refresh()
        self._show_apply_complete_message()
        if close_after and Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _locate_selected_station(self) -> None:
        row = self._selected_station_row()
        self._locate_row(row)

    def _locate_station_row(self, row_index: int) -> None:
        rows = stationing_table_rows(self.stationing)
        row = rows[int(row_index)] if 0 <= int(row_index) < len(rows) else None
        self._locate_row(row)

    def _locate_row(self, row: dict[str, object] | None) -> None:
        if row is None:
            _show_message(self.form, "Stations", "위치확인할 측점 행을 먼저 선택해 주세요.")
            return
        try:
            highlight = show_station_highlight(self.document, row)
            if Gui is not None and highlight is not None:
                try:
                    Gui.Selection.clearSelection()
                    Gui.Selection.addSelection(highlight)
                except Exception:
                    pass
                try:
                    view = Gui.ActiveDocument.ActiveView
                    view.fitAll()
                except Exception:
                    pass
        except Exception as exc:
            _show_message(self.form, "Stations", f"측점 위치를 표시하지 못했습니다.\n{exc}")

    def _selected_station_row(self) -> dict[str, object] | None:
        row_index = int(self._table.currentRow())
        if row_index < 0:
            try:
                selected = list(self._table.selectionModel().selectedRows() or [])
                if selected:
                    row_index = int(selected[0].row())
            except Exception:
                row_index = -1
        rows = stationing_table_rows(self.stationing)
        if row_index < 0 or row_index >= len(rows):
            return None
        return rows[row_index]

    def _show_apply_complete_message(self) -> None:
        try:
            station_count = len(list(getattr(self.stationing, "StationValues", []) or []))
            _show_message(self.form, "Stations", f"Stations have been applied successfully.\nStation count: {station_count}")
        except Exception:
            pass


def run_v1_stationing_review_command():
    """Open the v1 stationing panel without applying generation changes."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    stationing = _selected_stationing(Gui, document) or find_v1_stationing(document)
    preferred_alignment, _preferred_profile = selected_alignment_profile_target(Gui, document)
    if Gui is not None:
        if stationing is not None:
            try:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(stationing)
            except Exception:
                pass
        Gui.Control.showDialog(
            V1StationingReviewTaskPanel(
                stationing=stationing,
                document=document,
                preferred_alignment=preferred_alignment,
            )
        )
    return stationing


def _selected_stationing(gui, document):
    if gui is None:
        return None
    try:
        selection = list(gui.Selection.getSelection() or [])
    except Exception:
        selection = []
    for obj in selection:
        candidate = find_v1_stationing(document, preferred_stationing=obj)
        if candidate is not None:
            return candidate
    return None


def _double_spin(minimum: float, maximum: float, value: float, decimals: int, suffix: str):
    spin = QtWidgets.QDoubleSpinBox()
    spin.setRange(float(minimum), float(maximum))
    spin.setDecimals(int(decimals))
    spin.setValue(float(value))
    if suffix:
        spin.setSuffix(str(suffix))
    return spin


def _set_combo_text(combo, text: str) -> None:
    index = combo.findText(str(text or ""))
    if index >= 0:
        combo.setCurrentIndex(index)


def _safe_float(value, fallback: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(fallback)


def _find_station_highlight(document):
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if str(getattr(obj, "V1ObjectType", "") or "") == "V1StationHighlight":
            return obj
        if str(getattr(obj, "Name", "") or "").startswith("V1StationHighlight"):
            return obj
    return None


def _style_station_highlight(obj) -> None:
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return
    try:
        vobj.Visibility = True
        vobj.DisplayMode = "Wireframe"
        vobj.LineColor = (1.0, 0.05, 0.02)
        vobj.LineWidth = 6.0
        vobj.PointColor = (1.0, 0.05, 0.02)
        vobj.PointSize = 10.0
    except Exception:
        pass


def _route_station_highlight_to_tree(document, obj) -> None:
    try:
        from freecad.Corridor_Road.objects.obj_project import find_project, route_to_v1_tree

        project = find_project(document)
        if project is not None:
            route_to_v1_tree(project, obj)
    except Exception:
        pass


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


def _stationing_float(stationing, prop: str, fallback: float) -> float:
    if stationing is None:
        return float(fallback)
    return _safe_float(getattr(stationing, prop, fallback), fallback)


def _stationing_text(stationing, prop: str, fallback: str) -> str:
    if stationing is None:
        return str(fallback)
    return str(getattr(stationing, prop, fallback) or fallback)


def _stationing_bool(stationing, prop: str, fallback: bool) -> bool:
    if stationing is None:
        return bool(fallback)
    return bool(getattr(stationing, prop, fallback))


def _float_list(values) -> list[float]:
    rows = []
    for value in list(values or []):
        try:
            rows.append(float(value))
        except Exception:
            rows.append(0.0)
    return rows

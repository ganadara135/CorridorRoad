"""Earthwork viewer for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD GUI is not available in tests.
    Gui = None

from freecad.Corridor_Road.qt_compat import QtWidgets
from ..common import run_legacy_command, set_ui_context


class EarthworkViewerTaskPanel:
    """Minimal read-only v1 earthwork viewer task panel."""

    def __init__(self, report: dict[str, object]):
        self.report = dict(report or {})
        self.form = self._build_ui()

    def getStandardButtons(self):
        return 0

    def accept(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def reject(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - Earthwork Viewer")

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Earthwork Balance Viewer")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self._focus_label = QtWidgets.QLabel(self._focus_badge_text())
        self._focus_label.setStyleSheet(self._focus_badge_style())
        layout.addWidget(self._focus_label)

        summary = QtWidgets.QPlainTextEdit()
        summary.setReadOnly(True)
        summary.setMinimumHeight(150)
        summary.setPlainText(self._summary_text())
        layout.addWidget(summary)

        layout.addWidget(QtWidgets.QLabel("Key Stations"))
        self._key_station_combo = QtWidgets.QComboBox()
        for row in self._key_station_rows():
            label = str(row.get("label", "") or f"STA {float(row.get('station', 0.0) or 0.0):.3f}")
            navigation_kind = str(row.get("navigation_kind", "") or "").strip()
            if bool(row.get("is_current", False)):
                label = f"{label} [current]"
            elif navigation_kind:
                label = f"{label} [{navigation_kind}]"
            self._key_station_combo.addItem(label, row)
        if self._key_station_combo.count() > 0:
            self._key_station_combo.setCurrentIndex(self._current_key_station_index())
        layout.addWidget(self._key_station_combo)

        station_button_row = QtWidgets.QHBoxLayout()
        prev_button = QtWidgets.QPushButton("Prev")
        prev_button.clicked.connect(lambda: self._open_adjacent_station(-1))
        station_button_row.addWidget(prev_button)
        open_station_button = QtWidgets.QPushButton("Open Selected Station")
        open_station_button.clicked.connect(self._open_selected_station)
        station_button_row.addWidget(open_station_button)
        next_button = QtWidgets.QPushButton("Next")
        next_button.clicked.connect(lambda: self._open_adjacent_station(1))
        station_button_row.addWidget(next_button)
        station_button_row.addStretch(1)
        layout.addLayout(station_button_row)

        layout.addWidget(QtWidgets.QLabel("Earthwork Windows"))
        layout.addWidget(
            self._table_widget(
                headers=["From", "To", "Cut", "Fill", "Ratio"],
                rows=[
                    [
                        str(getattr(row, "station_start", "") or ""),
                        str(getattr(row, "station_end", "") or ""),
                        str(getattr(row, "cut_value", "") or ""),
                        str(getattr(row, "fill_value", "") or ""),
                        str(getattr(row, "balance_ratio", "") or ""),
                    ]
                    for row in list(getattr(self.report.get("earthwork_model"), "balance_rows", []) or [])
                ],
                empty_text="No earthwork balance rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Haul Zones"))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "From", "To", "Value"],
                rows=[
                    [
                        str(getattr(row, "kind", "") or ""),
                        str(getattr(row, "station_start", "") or ""),
                        str(getattr(row, "station_end", "") or ""),
                        str(getattr(row, "value", "") or ""),
                    ]
                    for row in list(getattr(self.report.get("mass_haul_model"), "haul_zone_rows", []) or [])
                ],
                empty_text="No haul zones.",
            )
        )

        self._status_label = QtWidgets.QLabel("")
        self._status_label.setStyleSheet("color: #666;")
        layout.addWidget(self._status_label)

        button_row = QtWidgets.QHBoxLayout()
        for label, command_name in (
            ("Open Alignment", "CorridorRoad_EditAlignment"),
            ("Open Profiles", "CorridorRoad_EditProfiles"),
            ("Open PVI", "CorridorRoad_EditPVI"),
        ):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(
                lambda _checked=False, name=command_name: self._open_legacy_command(name)
            )
            button_row.addWidget(button)
        button_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        return widget

    def _summary_text(self) -> str:
        earthwork_output = self.report.get("earthwork_output")
        mass_haul_output = self.report.get("mass_haul_output")
        station_row = dict(self.report.get("station_row", {}) or {})
        focused_balance_row = self.report.get("focused_balance_row")
        focused_haul_zone = self.report.get("focused_haul_zone")

        total_cut = self._summary_value(getattr(earthwork_output, "summary_rows", []) or [], "total_cut")
        total_fill = self._summary_value(getattr(earthwork_output, "summary_rows", []) or [], "total_fill")
        curve_count = self._summary_value(getattr(mass_haul_output, "summary_rows", []) or [], "mass_haul_summary")
        balance_point_count = self._summary_value(
            getattr(mass_haul_output, "summary_rows", []) or [],
            "balance_point_count",
        )

        lines = [
            f"Total cut: {total_cut} m3",
            f"Total fill: {total_fill} m3",
            f"Mass-haul curves: {curve_count}",
            f"Balance points: {balance_point_count}",
            f"Key stations: {len(self._key_station_rows())}",
        ]
        if station_row:
            lines.append(f"Focus Station: {station_row.get('label', '')}")
        if focused_balance_row is not None:
            lines.append(
                "Focused Window: "
                f"{float(getattr(focused_balance_row, 'station_start', 0.0) or 0.0):.3f}"
                " -> "
                f"{float(getattr(focused_balance_row, 'station_end', 0.0) or 0.0):.3f}"
            )
            lines.append(
                "Focused Cut/Fill: "
                f"{float(getattr(focused_balance_row, 'cut_value', 0.0) or 0.0):.3f}"
                " / "
                f"{float(getattr(focused_balance_row, 'fill_value', 0.0) or 0.0):.3f} m3"
            )
        if focused_haul_zone is not None:
            lines.append(f"Focused Haul Zone: {getattr(focused_haul_zone, 'kind', '') or '(none)'}")
        return "\n".join(lines)

    def _focus_badge_text(self) -> str:
        station_row = dict(self.report.get("station_row", {}) or {})
        focused_balance_row = self.report.get("focused_balance_row")
        station_label = str(station_row.get("label", "") or "").strip()
        pieces = []
        if station_label:
            pieces.append(station_label)
        if focused_balance_row is not None:
            station_start = float(getattr(focused_balance_row, "station_start", 0.0) or 0.0)
            station_end = float(getattr(focused_balance_row, "station_end", 0.0) or 0.0)
            pieces.append(f"window {station_start:.3f} -> {station_end:.3f}")
        if not pieces:
            return "Current Focus: not specified"
        return "Current Focus: " + " | ".join(pieces)

    def _focus_badge_style(self) -> str:
        return (
            "color: #7a4200; "
            "background: #fff2df; "
            "border: 1px solid #efc389; "
            "border-radius: 4px; "
            "padding: 4px 6px; "
            "font-weight: bold;"
        )

    def _key_station_rows(self) -> list[dict[str, object]]:
        return [dict(row or {}) for row in list(self.report.get("key_station_rows", []) or [])]

    def _current_key_station_index(self) -> int:
        rows = self._key_station_rows()
        for index, row in enumerate(rows):
            if bool(row.get("is_current", False)):
                return index
        return 0

    def _selected_key_station_row(self) -> dict[str, object] | None:
        combo = getattr(self, "_key_station_combo", None)
        if combo is None or combo.count() <= 0:
            rows = self._key_station_rows()
            return dict(rows[self._current_key_station_index()]) if rows else None
        data = combo.currentData()
        if isinstance(data, dict):
            return dict(data)
        rows = self._key_station_rows()
        index = max(0, min(combo.currentIndex(), len(rows) - 1))
        return dict(rows[index]) if rows else None

    def _open_selected_station(self) -> None:
        self._open_station_row(self._selected_key_station_row())

    def _open_adjacent_station(self, delta: int) -> None:
        rows = self._key_station_rows()
        if not rows:
            self._status_label.setText("No key station rows are available.")
            self._status_label.setStyleSheet("color: #b36b00;")
            return
        current_index = self._current_key_station_index()
        target_index = max(0, min(current_index + int(delta), len(rows) - 1))
        self._open_station_row(rows[target_index])

    def _open_station_row(self, row: dict[str, object] | None) -> None:
        if row is None:
            self._status_label.setText("No station row is available.")
            self._status_label.setStyleSheet("color: #b36b00;")
            return
        if Gui is None:
            self._status_label.setText("FreeCAD GUI is not available for station navigation.")
            self._status_label.setStyleSheet("color: #b33;")
            return

        legacy_objects = dict(self.report.get("legacy_objects", {}) or {})
        section_set = legacy_objects.get("section_set")
        station_value = float(row.get("station", 0.0) or 0.0)
        station_label = str(row.get("label", "") or f"STA {station_value:.3f}")
        context_payload = {
            "source": "v1_earthwork_navigation",
            "preferred_section_set_name": str(getattr(section_set, "Name", "") or "").strip(),
            "preferred_station": station_value,
            "station_row": dict(row),
        }
        set_ui_context(**context_payload)
        try:
            Gui.Control.closeDialog()
        except Exception:
            pass
        Gui.runCommand("CorridorRoad_V1EarthworkBalance", 0)
        self._status_label.setText(f"Opened {station_label} in v1 viewer.")
        self._status_label.setStyleSheet("color: #666;")

    def _open_legacy_command(self, command_name: str) -> None:
        legacy_objects = dict(self.report.get("legacy_objects", {}) or {})
        objects_to_select = []
        if command_name == "CorridorRoad_EditAlignment":
            objects_to_select = [legacy_objects.get("alignment")]
        elif command_name in ("CorridorRoad_EditProfiles", "CorridorRoad_EditPVI"):
            objects_to_select = [legacy_objects.get("profile"), legacy_objects.get("alignment")]
        success, message = run_legacy_command(
            command_name,
            gui_module=Gui,
            objects_to_select=[obj for obj in objects_to_select if obj is not None],
            context_payload={
                "source": "v1_earthwork_viewer",
                "station_row": dict(self.report.get("station_row", {}) or {}),
                "legacy_object_names": {
                    key: str(getattr(obj, "Name", "") or "")
                    for key, obj in legacy_objects.items()
                    if obj is not None
                },
            },
        )
        self._status_label.setText(message)
        if not success:
            self._status_label.setStyleSheet("color: #b33;")
        else:
            self._status_label.setStyleSheet("color: #666;")

    def _summary_value(self, summary_rows: list[object], kind: str) -> object:
        for row in summary_rows:
            if getattr(row, "kind", "") == kind:
                return getattr(row, "value", "")
        return ""

    def _table_widget(
        self,
        *,
        headers: list[str],
        rows: list[list[str]],
        empty_text: str,
    ):
        if not rows:
            empty = QtWidgets.QLabel(empty_text)
            empty.setStyleSheet("color: #666;")
            return empty

        table = QtWidgets.QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)

        for row_index, row_values in enumerate(rows):
            for col_index, value in enumerate(row_values):
                table.setItem(row_index, col_index, QtWidgets.QTableWidgetItem(str(value)))

        header = table.horizontalHeader()
        try:
            header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        except Exception:
            pass
        table.setMinimumHeight(150)
        return table


EarthworkPreviewTaskPanel = EarthworkViewerTaskPanel

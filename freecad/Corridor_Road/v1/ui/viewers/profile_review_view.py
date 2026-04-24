"""Plan/profile viewer for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD GUI is not available in tests.
    Gui = None

from freecad.Corridor_Road.qt_compat import QtWidgets
from ..common import run_legacy_command, set_ui_context


class PlanProfileViewerTaskPanel:
    """Minimal read-only v1 plan/profile viewer task panel."""

    def __init__(self, preview: dict[str, object]):
        self.preview = dict(preview or {})
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
        widget.setWindowTitle("CorridorRoad v1 - Plan/Profile Viewer")

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Plan/Profile Viewer")
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
        summary.setMinimumHeight(140)
        summary.setPlainText(self._summary_text())
        layout.addWidget(summary)

        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        layout.addWidget(QtWidgets.QLabel("Viewer Context"))
        layout.addWidget(
            self._table_widget(
                headers=["Field", "Value"],
                rows=self._viewer_context_rows(viewer_context),
                empty_text="No viewer context rows.",
            )
        )

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

        layout.addWidget(QtWidgets.QLabel("Plan Geometry"))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Start", "End", "Points"],
                rows=[
                    [
                        str(getattr(row, "kind", "") or ""),
                        str(self._station_start(row)),
                        str(self._station_end(row)),
                        str(len(list(getattr(row, "x_values", []) or []))),
                    ]
                    for row in list(getattr(self.preview.get("plan_output"), "geometry_rows", []) or [])
                ],
                empty_text="No plan geometry rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Profile Controls"))
        self._profile_table = self._table_widget(
            headers=["Station", "Elevation", "Label"],
            rows=[
                [
                    str(getattr(row, "station", "") or ""),
                    str(getattr(row, "elevation", "") or ""),
                    str(getattr(row, "label", "") or ""),
                ]
                for row in list(getattr(self.preview.get("profile_output"), "pvi_rows", []) or [])
            ],
            empty_text="No profile control rows.",
        )
        layout.addWidget(self._profile_table)
        self._select_focus_station_row(self._profile_table)

        layout.addWidget(QtWidgets.QLabel("Earthwork Attachments"))
        layout.addWidget(
            self._table_widget(
                headers=["From", "To", "Value", "Unit"],
                rows=[
                    [
                        str(getattr(row, "station_start", "") or ""),
                        str(getattr(row, "station_end", "") or ""),
                        str(getattr(row, "value", "") or ""),
                        str(getattr(row, "unit", "") or ""),
                    ]
                    for row in list(getattr(self.preview.get("profile_output"), "earthwork_rows", []) or [])
                ],
                empty_text="No attached earthwork rows.",
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
        alignment_model = self.preview.get("alignment_model")
        profile_model = self.preview.get("profile_model")
        plan_output = self.preview.get("plan_output")
        profile_output = self.preview.get("profile_output")
        viewer_context = dict(self.preview.get("viewer_context", {}) or {})

        lines = [
            f"Alignment: {getattr(alignment_model, 'label', '') or '(missing)'}",
            f"Alignment elements: {len(list(getattr(plan_output, 'geometry_rows', []) or []))}",
            f"Plan stations: {len(list(getattr(plan_output, 'station_rows', []) or []))}",
            f"Profile: {getattr(profile_model, 'label', '') or '(missing)'}",
            f"Profile controls: {len(list(getattr(profile_output, 'pvi_rows', []) or []))}",
            f"Earthwork attachments: {len(list(getattr(profile_output, 'earthwork_rows', []) or []))}",
            f"Key stations: {len(self._key_station_rows())}",
        ]
        focus_station_label = str(viewer_context.get("focus_station_label", "") or "").strip()
        source_panel = str(viewer_context.get("source_panel", "") or "").strip()
        selected_row = str(viewer_context.get("selected_row_label", "") or "").strip()
        if source_panel:
            lines.append(f"Context Source: {source_panel}")
        if focus_station_label:
            lines.append(f"Focus Station: {focus_station_label}")
        if selected_row:
            lines.append(f"Selected Row: {selected_row}")
        return "\n".join(lines)

    def _focus_badge_text(self) -> str:
        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        focus_station_label = str(viewer_context.get("focus_station_label", "") or "").strip()
        selected_row = str(viewer_context.get("selected_row_label", "") or "").strip()
        if focus_station_label and selected_row:
            return f"Current Focus: {focus_station_label} | {selected_row}"
        if focus_station_label:
            return f"Current Focus: {focus_station_label}"
        if selected_row:
            return f"Current Focus: {selected_row}"
        return "Current Focus: not specified"

    def _focus_badge_style(self) -> str:
        return (
            "color: #0b4f8a; "
            "background: #eaf3ff; "
            "border: 1px solid #bdd5f3; "
            "border-radius: 4px; "
            "padding: 4px 6px; "
            "font-weight: bold;"
        )

    def _viewer_context_rows(self, viewer_context: dict[str, object]) -> list[list[str]]:
        rows = []
        mapping = [
            ("Source", "source_panel"),
            ("Focus Station", "focus_station_label"),
            ("Selected Row", "selected_row_label"),
            ("Mode", "mode_summary"),
            ("Table Summary", "table_summary"),
            ("Status", "status_summary"),
        ]
        for label, key in mapping:
            value = str(viewer_context.get(key, "") or "").strip()
            if value:
                rows.append([label, value])
        for index, value in enumerate(list(viewer_context.get("summary_lines", []) or [])[:6], start=1):
            text = str(value or "").strip()
            if text:
                rows.append([f"Summary {index}", text])
        return rows

    def _focus_station_value(self) -> float | None:
        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        try:
            value = viewer_context.get("focus_station", None)
            if value is None or value == "":
                return None
            return float(value)
        except Exception:
            return None

    def _key_station_rows(self) -> list[dict[str, object]]:
        return [dict(row or {}) for row in list(self.preview.get("key_station_rows", []) or [])]

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

        legacy_objects = dict(self.preview.get("legacy_objects", {}) or {})
        alignment = legacy_objects.get("alignment")
        profile = legacy_objects.get("profile")
        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        station_value = float(row.get("station", 0.0) or 0.0)
        station_label = str(row.get("label", "") or f"STA {station_value:.3f}")
        viewer_context["focus_station"] = station_value
        viewer_context["focus_station_label"] = station_label
        context_payload = {
            "source": "v1_plan_profile_navigation",
            "preferred_alignment_name": str(getattr(alignment, "Name", "") or "").strip(),
            "preferred_profile_name": str(getattr(profile, "Name", "") or "").strip(),
            "preferred_station": station_value,
            "station_row": dict(row),
            "viewer_context": viewer_context,
        }
        set_ui_context(**context_payload)
        try:
            Gui.Control.closeDialog()
        except Exception:
            pass
        Gui.runCommand("CorridorRoad_V1ReviewPlanProfile", 0)
        self._status_label.setText(f"Opened {station_label} in v1 viewer.")
        self._status_label.setStyleSheet("color: #666;")

    def _select_focus_station_row(self, table) -> None:
        if not hasattr(table, "rowCount"):
            return
        focus_station = self._focus_station_value()
        if focus_station is None:
            return
        best_row = -1
        best_delta = None
        for row_index in range(int(table.rowCount())):
            item = table.item(row_index, 0)
            if item is None:
                continue
            try:
                station_value = float(str(item.text() or "").strip())
            except Exception:
                continue
            delta = abs(station_value - focus_station)
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_row = row_index
        if best_row < 0:
            return
        table.selectRow(best_row)
        item = table.item(best_row, 0)
        if item is not None:
            table.scrollToItem(item)

    def _open_legacy_command(self, command_name: str) -> None:
        legacy_objects = dict(self.preview.get("legacy_objects", {}) or {})
        objects_to_select = []
        if command_name == "CorridorRoad_EditAlignment":
            objects_to_select = [legacy_objects.get("alignment")]
        elif command_name in ("CorridorRoad_EditProfiles", "CorridorRoad_EditPVI"):
            objects_to_select = [legacy_objects.get("profile"), legacy_objects.get("alignment")]
        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        focus_station = viewer_context.get("focus_station", None)
        focus_station_label = str(viewer_context.get("focus_station_label", "") or "").strip()
        station_row = {}
        try:
            if focus_station is not None and focus_station != "":
                station_row["station"] = float(focus_station)
        except Exception:
            pass
        if focus_station_label:
            station_row["label"] = focus_station_label
        success, message = run_legacy_command(
            command_name,
            gui_module=Gui,
            objects_to_select=[obj for obj in objects_to_select if obj is not None],
            context_payload={
                "source": "v1_plan_profile_viewer",
                "station_row": station_row,
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

    def _station_start(self, row) -> object:
        x_values = list(getattr(row, "x_values", []) or [])
        if not x_values:
            return ""
        return x_values[0]

    def _station_end(self, row) -> object:
        x_values = list(getattr(row, "x_values", []) or [])
        if not x_values:
            return ""
        return x_values[-1]

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
        table.setMinimumHeight(120)
        return table


PlanProfilePreviewTaskPanel = PlanProfileViewerTaskPanel

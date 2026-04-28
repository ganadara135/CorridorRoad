"""Earthwork viewer for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD GUI is not available in tests.
    Gui = None

from freecad.Corridor_Road.qt_compat import QtWidgets
from ..common import run_legacy_command, set_ui_context


def build_section_handoff_context(
    report: dict[str, object],
    *,
    station_row: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the v1 Cross Section Viewer context for one earthwork focus."""

    payload_row = _station_payload(report, station_row=station_row)
    station_value = float(payload_row.get("station", 0.0) or 0.0)
    station_label = str(payload_row.get("label", "") or f"STA {station_value:.3f}")
    legacy_objects = dict(report.get("legacy_objects", {}) or {})
    section_set = legacy_objects.get("section_set")
    earthwork_model = report.get("earthwork_model", None)
    mass_haul_model = report.get("mass_haul_model", None)
    focused_balance_row = (
        _nearest_interval_row(getattr(earthwork_model, "balance_rows", []) or [], station_value)
        or report.get("focused_balance_row", None)
    )
    focused_haul_zone = (
        _nearest_interval_row(getattr(mass_haul_model, "haul_zone_rows", []) or [], station_value)
        or report.get("focused_haul_zone", None)
    )
    earthwork_hint_rows = _earthwork_handoff_rows(
        focused_balance_row=focused_balance_row,
        focused_haul_zone=focused_haul_zone,
    )

    viewer_context = {
        "source_panel": "Earthwork Review",
        "station_label": station_label,
        "tag_summary": "Earthwork focus",
        "earthwork_window_summary": _earthwork_window_summary(focused_balance_row),
        "earthwork_cut_fill_summary": _earthwork_cut_fill_summary(focused_balance_row),
        "haul_zone_summary": _haul_zone_summary(focused_haul_zone),
    }
    return {
        "source": "v1_earthwork_to_section",
        "preferred_section_set_name": str(getattr(section_set, "Name", "") or "").strip(),
        "preferred_station": station_value,
        "station_row": payload_row,
        "viewer_context": viewer_context,
        "earthwork_hint_rows": earthwork_hint_rows,
    }


def build_plan_profile_handoff_context(
    report: dict[str, object],
    *,
    station_row: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the v1 Plan/Profile Viewer context for one earthwork focus."""

    payload_row = _station_payload(report, station_row=station_row)
    station_value = float(payload_row.get("station", 0.0) or 0.0)
    station_label = str(payload_row.get("label", "") or f"STA {station_value:.3f}")
    legacy_objects = dict(report.get("legacy_objects", {}) or {})
    alignment = legacy_objects.get("alignment")
    profile = legacy_objects.get("profile")
    earthwork_model = report.get("earthwork_model", None)
    mass_haul_model = report.get("mass_haul_model", None)
    focused_balance_row = (
        _nearest_interval_row(getattr(earthwork_model, "balance_rows", []) or [], station_value)
        or report.get("focused_balance_row", None)
    )
    focused_haul_zone = (
        _nearest_interval_row(getattr(mass_haul_model, "haul_zone_rows", []) or [], station_value)
        or report.get("focused_haul_zone", None)
    )
    viewer_context = {
        "source_panel": "Earthwork Review",
        "focus_station": station_value,
        "focus_station_label": station_label,
        "selected_row_label": f"Earthwork window { _earthwork_window_summary(focused_balance_row) }".strip(),
        "earthwork_window_summary": _earthwork_window_summary(focused_balance_row),
        "earthwork_cut_fill_summary": _earthwork_cut_fill_summary(focused_balance_row),
        "haul_zone_summary": _haul_zone_summary(focused_haul_zone),
        "mode_summary": "Linear cause review from Earthwork Review",
    }
    return {
        "source": "v1_earthwork_to_plan_profile",
        "preferred_alignment_name": str(getattr(alignment, "Name", "") or "").strip(),
        "preferred_profile_name": str(getattr(profile, "Name", "") or "").strip(),
        "preferred_station": station_value,
        "station_row": payload_row,
        "viewer_context": viewer_context,
    }


def _station_payload(
    report: dict[str, object],
    *,
    station_row: dict[str, object] | None,
) -> dict[str, object]:
    row = dict(station_row or report.get("station_row", {}) or {})
    if row.get("station", None) is None:
        focused_balance_row = report.get("focused_balance_row", None)
        row["station"] = float(getattr(focused_balance_row, "station_start", 0.0) or 0.0)
    station_value = float(row.get("station", 0.0) or 0.0)
    row["station"] = station_value
    row["label"] = str(row.get("label", "") or f"STA {station_value:.3f}")
    return row


def _earthwork_handoff_rows(
    *,
    focused_balance_row,
    focused_haul_zone,
) -> list[dict[str, str]]:
    rows = []
    window_summary = _earthwork_window_summary(focused_balance_row)
    if window_summary:
        rows.append(
            {
                "kind": "earthwork_window",
                "label": "Earthwork Window",
                "value": window_summary,
                "notes": "Focused window from Earthwork Review.",
            }
        )
    cut_fill_summary = _earthwork_cut_fill_summary(focused_balance_row)
    if cut_fill_summary:
        rows.append(
            {
                "kind": "earthwork_cut_fill",
                "label": "Cut / Fill",
                "value": cut_fill_summary,
                "notes": "Volume values are from the active earthwork balance row.",
            }
        )
    haul_summary = _haul_zone_summary(focused_haul_zone)
    if haul_summary:
        rows.append(
            {
                "kind": "earthwork_haul_zone",
                "label": "Haul Zone",
                "value": haul_summary,
                "notes": "Nearest haul zone for the focused station.",
            }
        )
    return rows


def _earthwork_window_summary(row) -> str:
    if row is None:
        return ""
    station_start = float(getattr(row, "station_start", 0.0) or 0.0)
    station_end = float(getattr(row, "station_end", 0.0) or 0.0)
    return f"{station_start:.3f} -> {station_end:.3f}"


def _earthwork_cut_fill_summary(row) -> str:
    if row is None:
        return ""
    cut_value = float(getattr(row, "cut_value", 0.0) or 0.0)
    fill_value = float(getattr(row, "fill_value", 0.0) or 0.0)
    ratio = float(getattr(row, "balance_ratio", 0.0) or 0.0)
    return f"{cut_value:.3f} / {fill_value:.3f} m3; ratio={ratio:.3f}"


def _haul_zone_summary(row) -> str:
    if row is None:
        return ""
    kind = str(getattr(row, "kind", "") or "").strip()
    value = float(getattr(row, "value", 0.0) or 0.0)
    return f"{kind or '(none)'}; value={value:.3f} m3"


def _nearest_interval_row(rows: list[object], station: float):
    if not rows:
        return None
    return min(rows, key=lambda row: _station_interval_distance(row, station))


def _station_interval_distance(row, station: float) -> float:
    station_start = getattr(row, "station_start", None)
    station_end = getattr(row, "station_end", None)
    if station_start is None and station_end is None:
        return 0.0
    if station_start is None:
        return abs(float(station_end) - float(station))
    if station_end is None:
        return abs(float(station_start) - float(station))
    start = float(station_start)
    end = float(station_end)
    if start <= station <= end:
        return 0.0
    return min(abs(station - start), abs(station - end))


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
        open_section_button = QtWidgets.QPushButton("Open Cross Section")
        open_section_button.clicked.connect(self._open_selected_cross_section)
        station_button_row.addWidget(open_section_button)
        open_plan_profile_button = QtWidgets.QPushButton("Open Plan/Profile")
        open_plan_profile_button.clicked.connect(self._open_selected_plan_profile)
        station_button_row.addWidget(open_plan_profile_button)
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

        layout.addWidget(QtWidgets.QLabel("Mass Curve"))
        layout.addWidget(
            self._table_widget(
                headers=["Station", "Cumulative Mass"],
                rows=self._mass_curve_rows(),
                empty_text="No mass curve rows.",
            )
        )

        self._status_label = QtWidgets.QLabel("")
        self._status_label.setStyleSheet("color: #666;")
        layout.addWidget(self._status_label)

        button_row = QtWidgets.QHBoxLayout()
        for label, command_name in (
            ("Open Alignment Editor", "CorridorRoad_V1EditAlignment"),
            ("Open Profile Editor", "CorridorRoad_V1EditProfile"),
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
        final_cumulative_mass = self._summary_value(
            getattr(mass_haul_output, "summary_rows", []) or [],
            "final_cumulative_mass",
        )
        max_surplus_mass = self._summary_value(
            getattr(mass_haul_output, "summary_rows", []) or [],
            "max_surplus_cumulative_mass",
        )
        max_deficit_mass = self._summary_value(
            getattr(mass_haul_output, "summary_rows", []) or [],
            "max_deficit_cumulative_mass",
        )

        lines = [
            f"Total cut: {total_cut} m3",
            f"Total fill: {total_fill} m3",
            f"Mass-haul curves: {curve_count}",
            f"Balance points: {balance_point_count}",
            f"Final cumulative mass: {final_cumulative_mass} m3",
            f"Max surplus/deficit: {max_surplus_mass} / {max_deficit_mass} m3",
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

    def _mass_curve_rows(self) -> list[list[str]]:
        rows = []
        mass_haul_output = self.report.get("mass_haul_output", None)
        for curve in list(getattr(mass_haul_output, "curve_rows", []) or []):
            station_values = list(getattr(curve, "station_values", []) or [])
            mass_values = list(getattr(curve, "cumulative_mass_values", []) or [])
            for station, value in list(zip(station_values, mass_values))[:20]:
                rows.append(
                    [
                        f"{float(station):.3f}",
                        f"{float(value):.3f}",
                    ]
                )
        return rows

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

    def _open_selected_cross_section(self) -> None:
        self._open_cross_section_row(self._selected_key_station_row())

    def _open_selected_plan_profile(self) -> None:
        self._open_plan_profile_row(self._selected_key_station_row())

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

    def _open_cross_section_row(self, row: dict[str, object] | None) -> None:
        if row is None:
            self._status_label.setText("No station row is available for cross-section handoff.")
            self._status_label.setStyleSheet("color: #b36b00;")
            return
        if Gui is None:
            self._status_label.setText("FreeCAD GUI is not available for cross-section handoff.")
            self._status_label.setStyleSheet("color: #b33;")
            return

        context_payload = build_section_handoff_context(self.report, station_row=row)
        set_ui_context(**context_payload)
        station_label = str(dict(context_payload.get("station_row", {}) or {}).get("label", "") or "")
        self._set_status_safely(f"Opening Cross Section Viewer for {station_label}.", ok=True)
        try:
            Gui.Control.closeDialog()
        except Exception:
            pass
        Gui.runCommand("CorridorRoad_V1ViewSections", 0)

    def _open_plan_profile_row(self, row: dict[str, object] | None) -> None:
        if row is None:
            self._status_label.setText("No station row is available for plan/profile handoff.")
            self._status_label.setStyleSheet("color: #b36b00;")
            return
        if Gui is None:
            self._status_label.setText("FreeCAD GUI is not available for plan/profile handoff.")
            self._status_label.setStyleSheet("color: #b33;")
            return

        context_payload = build_plan_profile_handoff_context(self.report, station_row=row)
        set_ui_context(**context_payload)
        station_label = str(dict(context_payload.get("station_row", {}) or {}).get("label", "") or "")
        self._set_status_safely(f"Opening Plan/Profile Viewer for {station_label}.", ok=True)
        try:
            Gui.Control.closeDialog()
        except Exception:
            pass
        Gui.runCommand("CorridorRoad_V1ReviewPlanProfile", 0)

    def _open_legacy_command(self, command_name: str) -> None:
        legacy_objects = dict(self.report.get("legacy_objects", {}) or {})
        objects_to_select = []
        if command_name in ("CorridorRoad_V1EditAlignment", "CorridorRoad_EditAlignment"):
            objects_to_select = [legacy_objects.get("alignment")]
        elif command_name in ("CorridorRoad_V1EditProfile", "CorridorRoad_EditProfiles", "CorridorRoad_EditPVI"):
            objects_to_select = [legacy_objects.get("profile"), legacy_objects.get("alignment")]
        self._set_status_safely(f"Opening `{command_name}`.", ok=True)
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
        if not success:
            self._set_status_safely(message, ok=False)

    def _set_status_safely(self, text: str, *, ok: bool = True) -> None:
        label = getattr(self, "_status_label", None)
        if label is None:
            return
        try:
            label.setText(str(text or ""))
            label.setStyleSheet("color: #666;" if ok else "color: #b33;")
        except RuntimeError:
            pass

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

"""Plan/profile viewer for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD GUI is not available in tests.
    App = None
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
        widget.setWindowTitle("CorridorRoad v1 - Plan/Profile Connection Review")

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Plan/Profile Connection Review")
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

        readiness_rows = self._review_readiness_rows()
        if readiness_rows:
            layout.addWidget(QtWidgets.QLabel("Review Readiness"))
            layout.addWidget(
                self._table_widget(
                    headers=["Stage", "Status", "Next Action"],
                    rows=readiness_rows,
                    empty_text="Review context is ready.",
                )
            )

        layout.addWidget(QtWidgets.QLabel("Source Link Summary"))
        layout.addWidget(
            self._table_widget(
                headers=["Source", "Object", "ID / Ref", "Range / Count", "Status"],
                rows=self._source_link_rows(),
                empty_text="No source link rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Connection Diagnostics"))
        diagnostics_hint = QtWidgets.QLabel(
            "Double-click a diagnostic row to open the source panel most likely to fix that area."
        )
        diagnostics_hint.setWordWrap(True)
        diagnostics_hint.setStyleSheet("color: #666;")
        layout.addWidget(diagnostics_hint)
        self._connection_diagnostics_table = self._table_widget(
            headers=["Area", "Status", "Finding", "Next Action"],
            rows=self._connection_diagnostic_rows(),
            empty_text="No connection diagnostic rows.",
        )
        layout.addWidget(self._connection_diagnostics_table)
        self._connect_connection_diagnostics_table(self._connection_diagnostics_table)

        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        viewer_context_rows = self._viewer_context_rows(viewer_context)
        if viewer_context_rows:
            layout.addWidget(QtWidgets.QLabel("Viewer Context"))
            layout.addWidget(
                self._table_widget(
                    headers=["Field", "Value"],
                    rows=viewer_context_rows,
                    empty_text="No viewer context rows.",
                )
            )

        layout.addWidget(QtWidgets.QLabel("Station Connection"))
        connection_hint = QtWidgets.QLabel(
            "Primary connection review table: checks every station row against Alignment XY, "
            "Profile FG, and TIN EG on the same station domain."
        )
        connection_hint.setWordWrap(True)
        connection_hint.setStyleSheet("color: #666;")
        layout.addWidget(connection_hint)
        self._connection_issues_only = QtWidgets.QCheckBox("Show issue rows only")
        self._connection_issues_only.stateChanged.connect(lambda _state: self._refresh_connection_table())
        layout.addWidget(self._connection_issues_only)
        self._connection_table_slot = QtWidgets.QVBoxLayout()
        layout.addLayout(self._connection_table_slot)
        self._refresh_connection_table()

        layout.addWidget(QtWidgets.QLabel("Quick Navigation Stations"))
        navigation_hint = QtWidgets.QLabel(
            "Full station list for moving the review focus. Selecting a station reopens this review centered on that station."
        )
        navigation_hint.setWordWrap(True)
        navigation_hint.setStyleSheet("color: #666;")
        layout.addWidget(navigation_hint)
        self._key_station_combo = QtWidgets.QComboBox()
        for row in self._key_station_rows():
            self._key_station_combo.addItem(self._key_station_combo_label(row), row)
        if self._key_station_combo.count() > 0:
            self._key_station_combo.setCurrentIndex(self._current_key_station_index())
        layout.addWidget(self._key_station_combo)

        station_button_row = QtWidgets.QHBoxLayout()
        prev_button = QtWidgets.QPushButton("Focus Previous")
        prev_button.clicked.connect(lambda: self._open_adjacent_station(-1))
        station_button_row.addWidget(prev_button)
        open_station_button = QtWidgets.QPushButton("Focus Selected")
        open_station_button.clicked.connect(self._open_selected_station)
        station_button_row.addWidget(open_station_button)
        next_button = QtWidgets.QPushButton("Focus Next")
        next_button.clicked.connect(lambda: self._open_adjacent_station(1))
        station_button_row.addWidget(next_button)
        station_button_row.addStretch(1)
        layout.addLayout(station_button_row)
        focus_hint = QtWidgets.QLabel(
            "Focus buttons reopen this connection review centered on another navigation station. "
            "They do not edit Alignment, Profile, or Stations."
        )
        focus_hint.setWordWrap(True)
        focus_hint.setStyleSheet("color: #666;")
        layout.addWidget(focus_hint)

        tabs = QtWidgets.QTabWidget()

        evaluation_tab = QtWidgets.QWidget()
        evaluation_layout = QtWidgets.QVBoxLayout(evaluation_tab)
        evaluation_hint = QtWidgets.QLabel(
            "Double-click an Alignment Frame or Profile Evaluation row to highlight that station in the 3D View."
        )
        evaluation_hint.setWordWrap(True)
        evaluation_hint.setStyleSheet("color: #666;")
        evaluation_layout.addWidget(evaluation_hint)
        evaluation_layout.addWidget(QtWidgets.QLabel("Alignment Frame"))
        self._alignment_frame_table = self._table_widget(
            headers=["Station", "X", "Y", "Tangent", "Element", "Status"],
            rows=self._alignment_frame_rows(),
            empty_text="No evaluated alignment frame rows.",
        )
        evaluation_layout.addWidget(self._alignment_frame_table)
        self._connect_station_highlight_table(self._alignment_frame_table)
        evaluation_layout.addWidget(QtWidgets.QLabel("Profile Evaluation"))
        self._profile_eval_table = self._table_widget(
            headers=["Station", "Elevation", "Grade", "Segment", "Curve", "Status"],
            rows=self._profile_eval_rows(),
            empty_text="No evaluated profile rows.",
        )
        evaluation_layout.addWidget(self._profile_eval_table)
        self._connect_station_highlight_table(self._profile_eval_table)
        tabs.addTab(evaluation_tab, "Evaluation")

        geometry_tab = QtWidgets.QWidget()
        geometry_layout = QtWidgets.QVBoxLayout(geometry_tab)
        geometry_hint = QtWidgets.QLabel(
            "Double-click a Plan Geometry or Profile Lines row to highlight the start station of that range in the 3D View."
        )
        geometry_hint.setWordWrap(True)
        geometry_hint.setStyleSheet("color: #666;")
        geometry_layout.addWidget(geometry_hint)
        geometry_layout.addWidget(QtWidgets.QLabel("Plan Geometry"))
        self._plan_geometry_table = self._table_widget(
            headers=["Kind", "Start", "End", "Points"],
            rows=self._plan_geometry_rows(),
            empty_text="No plan geometry rows.",
        )
        geometry_layout.addWidget(self._plan_geometry_table)
        self._connect_range_start_highlight_table(self._plan_geometry_table, station_column=1)
        geometry_layout.addWidget(QtWidgets.QLabel("Profile Lines"))
        self._profile_lines_table = self._table_widget(
            headers=["Kind", "Points", "Station Range", "Elevation Range", "Source"],
            rows=self._profile_line_rows(),
            empty_text="No profile line rows.",
        )
        geometry_layout.addWidget(self._profile_lines_table)
        self._connect_range_start_highlight_table(self._profile_lines_table, station_column=2)
        tabs.addTab(geometry_tab, "Geometry")

        controls_tab = QtWidgets.QWidget()
        controls_layout = QtWidgets.QVBoxLayout(controls_tab)
        controls_hint = QtWidgets.QLabel(
            "Double-click a Profile Control row to highlight the nearest review station in the 3D View."
        )
        controls_hint.setWordWrap(True)
        controls_hint.setStyleSheet("color: #666;")
        controls_layout.addWidget(controls_hint)
        controls_layout.addWidget(QtWidgets.QLabel("Profile Controls"))
        self._profile_table = self._table_widget(
            headers=["Station", "Elevation", "Label"],
            rows=self._profile_control_rows(),
            empty_text="No profile control rows.",
        )
        controls_layout.addWidget(self._profile_table)
        self._select_focus_station_row(self._profile_table)
        self._connect_station_highlight_table(self._profile_table)
        tabs.addTab(controls_tab, "Profile Controls")

        if self._should_show_earthwork_section():
            earthwork_tab = QtWidgets.QWidget()
            earthwork_layout = QtWidgets.QVBoxLayout(earthwork_tab)
            earthwork_layout.addWidget(QtWidgets.QLabel("Earthwork Context"))
            area_width_row = QtWidgets.QHBoxLayout()
            area_width_row.addWidget(QtWidgets.QLabel("Section Width"))
            self._earthwork_area_width_spin = QtWidgets.QDoubleSpinBox()
            self._earthwork_area_width_spin.setDecimals(3)
            self._earthwork_area_width_spin.setRange(0.0, 1000000.0)
            self._earthwork_area_width_spin.setSingleStep(1.0)
            self._earthwork_area_width_spin.setSuffix(" m")
            try:
                self._earthwork_area_width_spin.setSpecialValueText("not set")
            except Exception:
                pass
            self._earthwork_area_width_spin.setValue(self._earthwork_area_width_value() or 0.0)
            area_width_row.addWidget(self._earthwork_area_width_spin)
            apply_area_width_button = QtWidgets.QPushButton("Apply Area Width")
            apply_area_width_button.clicked.connect(self._apply_earthwork_area_width)
            area_width_row.addWidget(apply_area_width_button)
            area_width_row.addStretch(1)
            earthwork_layout.addLayout(area_width_row)

            area_status = QtWidgets.QLabel(self._earthwork_area_hint_status_text())
            area_status.setStyleSheet("color: #666;")
            earthwork_layout.addWidget(area_status)

            attachment_rows = self._earthwork_attachment_rows()
            if attachment_rows:
                earthwork_layout.addWidget(QtWidgets.QLabel("Earthwork Attachments"))
                earthwork_layout.addWidget(
                    self._table_widget(
                        headers=["Kind", "From", "To", "Value", "Unit"],
                        rows=attachment_rows,
                        empty_text="No attached earthwork rows.",
                    )
                )
            earthwork_layout.addStretch(1)
            tabs.addTab(earthwork_tab, "Earthwork")

        layout.addWidget(tabs, 1)

        self._status_label = QtWidgets.QLabel("")
        self._status_label.setStyleSheet("color: #666;")
        layout.addWidget(self._status_label)

        button_row = QtWidgets.QHBoxLayout()
        for label, command_name in (
            ("Open Alignment Editor", "CorridorRoad_V1EditAlignment"),
            ("Open Stations", "CorridorRoad_V1GenerateStations"),
            ("Open Profile Editor", "CorridorRoad_V1EditProfile"),
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
            f"Preview source: {str(self.preview.get('preview_source_kind', '') or 'unknown')}",
            f"Alignment: {getattr(alignment_model, 'label', '') or '(missing)'}",
            f"Alignment elements: {len(list(getattr(plan_output, 'geometry_rows', []) or []))}",
            f"Plan stations: {len(list(getattr(plan_output, 'station_rows', []) or []))}",
            f"Profile: {getattr(profile_model, 'label', '') or '(missing)'}",
            f"Profile controls: {len(list(getattr(profile_output, 'pvi_rows', []) or []))}",
            f"Profile lines: {len(self._profile_line_rows())}",
            f"Earthwork attachments: {len(list(getattr(profile_output, 'earthwork_rows', []) or []))}",
            f"Navigation stations: {len(self._key_station_rows())}",
            f"Evaluated alignment stations: {len(self._alignment_frame_rows())}",
            f"Evaluated profile stations: {len(self._profile_eval_rows())}",
        ]
        bridge_counts = self._bridge_diagnostic_counts()
        lines.append(
            "Bridge diagnostics: "
            f"ok={bridge_counts.get('ok', 0)}, "
            f"warning={bridge_counts.get('warning', 0)}, "
            f"error={bridge_counts.get('error', 0)}"
        )
        area_width = self._earthwork_area_width_value()
        if area_width is not None:
            lines.append(f"Earthwork area width: {area_width:.3f} m")
        area_status = self._earthwork_area_hint_status_text()
        if area_status:
            lines.append(f"Earthwork area status: {area_status}")
        eg_result = self.preview.get("profile_tin_sample_result", None)
        if eg_result is not None:
            eg_rows = list(getattr(eg_result, "rows", []) or [])
            lines.append(
                "EG sampling: "
                f"{str(getattr(eg_result, 'status', '') or 'unknown')} "
                f"({int(getattr(eg_result, 'hit_count', 0) or 0)}/{len(eg_rows)} hits)"
            )
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

    def _review_readiness_rows(self) -> list[list[str]]:
        alignment_model = self.preview.get("alignment_model")
        profile_model = self.preview.get("profile_model")
        plan_output = self.preview.get("plan_output")
        profile_output = self.preview.get("profile_output")
        rows: list[list[str]] = []

        if alignment_model is None:
            rows.append(
                [
                    "Alignment",
                    "missing",
                    "Open Alignment Editor and create or import the v1 alignment source.",
                ]
            )
        elif not list(getattr(plan_output, "geometry_rows", []) or []):
            rows.append(
                [
                    "Alignment Geometry",
                    "not evaluated",
                    "Apply Alignment again so review geometry can be regenerated.",
                ]
            )

        station_rows = list(getattr(plan_output, "station_rows", []) or [])
        if not station_rows:
            rows.append(
                [
                    "Stations",
                    "missing",
                    "Open Stations and apply station sampling for the active alignment.",
                ]
            )

        if profile_model is None:
            rows.append(
                [
                    "Profile",
                    "missing",
                    "Open Profile and create or import the v1 profile source.",
                ]
            )
        elif not list(getattr(profile_output, "pvi_rows", []) or []):
            rows.append(
                [
                    "Profile Controls",
                    "missing",
                    "Open Profile and apply PVI or preset profile control rows.",
                ]
            )

        if station_rows and not self._key_station_rows():
            rows.append(
                [
                    "Quick Navigation Stations",
                    "missing",
                    "Reopen Plan/Profile Review after Stations are generated.",
                ]
            )

        if profile_model is not None and not self._profile_line_rows():
            rows.append(
                [
                    "Profile Lines",
                    "not evaluated",
                    "Apply Profile again so FG/EG review lines can be regenerated.",
                ]
            )

        return rows

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
            ("Earthwork Window", "earthwork_window_summary"),
            ("Earthwork Cut/Fill", "earthwork_cut_fill_summary"),
            ("Haul Zone", "haul_zone_summary"),
            ("Earthwork Area Width", "earthwork_area_width"),
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

    def _source_link_rows(self) -> list[list[str]]:
        alignment_model = self.preview.get("alignment_model")
        profile_model = self.preview.get("profile_model")
        plan_output = self.preview.get("plan_output")
        profile_output = self.preview.get("profile_output")
        tin_surface = self.preview.get("tin_surface")
        legacy_objects = dict(self.preview.get("legacy_objects", {}) or {})

        station_rows = list(getattr(plan_output, "station_rows", []) or [])
        profile_controls = list(getattr(profile_output, "pvi_rows", []) or [])

        return [
            [
                "Alignment",
                self._source_object_label(legacy_objects.get("alignment"), fallback=getattr(alignment_model, "label", "")),
                str(getattr(alignment_model, "alignment_id", "") or ""),
                self._alignment_station_range_text(alignment_model),
                "linked" if alignment_model is not None else "missing",
            ],
            [
                "Stations",
                self._source_object_label(legacy_objects.get("stationing"), fallback="PlanOutput station grid"),
                self._source_stationing_ref(legacy_objects.get("stationing")),
                self._station_rows_range_text(station_rows),
                "linked" if station_rows else "missing",
            ],
            [
                "Profile",
                self._source_object_label(legacy_objects.get("profile"), fallback=getattr(profile_model, "label", "")),
                str(getattr(profile_model, "profile_id", "") or ""),
                self._profile_control_range_text(profile_controls),
                "linked" if profile_model is not None else "missing",
            ],
            [
                "TIN",
                self._source_object_label(legacy_objects.get("tin"), fallback=getattr(tin_surface, "surface_kind", "")),
                str(getattr(tin_surface, "surface_id", "") or ""),
                self._tin_summary_text(tin_surface),
                "linked" if tin_surface is not None else "not selected",
            ],
        ]

    @staticmethod
    def _source_object_label(obj, *, fallback: object = "") -> str:
        if obj is not None:
            label = str(getattr(obj, "Label", "") or "").strip()
            name = str(getattr(obj, "Name", "") or "").strip()
            if label and name and label != name:
                return f"{label} ({name})"
            if label or name:
                return label or name
        text = str(fallback or "").strip()
        return text or "(none)"

    @staticmethod
    def _source_stationing_ref(stationing) -> str:
        if stationing is None:
            return ""
        alignment_id = str(getattr(stationing, "AlignmentId", "") or "").strip()
        if alignment_id:
            return f"alignment={alignment_id}"
        return str(getattr(stationing, "Name", "") or "")

    @staticmethod
    def _alignment_station_range_text(alignment_model) -> str:
        elements = list(getattr(alignment_model, "geometry_sequence", []) or [])
        if not elements:
            return ""
        values = []
        for element in elements:
            for attr in ("station_start", "station_end"):
                try:
                    values.append(float(getattr(element, attr)))
                except Exception:
                    pass
        if not values:
            return ""
        return f"{min(values):.3f} -> {max(values):.3f} | elements {len(elements)}"

    @staticmethod
    def _station_rows_range_text(station_rows: list[object]) -> str:
        values = []
        for row in list(station_rows or []):
            try:
                values.append(float(getattr(row, "station", 0.0) or 0.0))
            except Exception:
                pass
        if not values:
            return "0 rows"
        return f"{min(values):.3f} -> {max(values):.3f} | rows {len(values)}"

    @staticmethod
    def _profile_control_range_text(profile_controls: list[object]) -> str:
        values = []
        for row in list(profile_controls or []):
            try:
                values.append(float(getattr(row, "station", 0.0) or 0.0))
            except Exception:
                pass
        if not values:
            return "0 controls"
        return f"{min(values):.3f} -> {max(values):.3f} | controls {len(values)}"

    @staticmethod
    def _tin_summary_text(tin_surface) -> str:
        if tin_surface is None:
            return ""
        vertices = len(list(getattr(tin_surface, "vertex_rows", []) or []))
        triangles = len(list(getattr(tin_surface, "triangle_rows", []) or []))
        return f"vertices {vertices} | triangles {triangles}"

    def _connection_diagnostic_rows(self) -> list[list[str]]:
        station_connection_rows = self._station_connection_rows()
        return [
            self._source_link_diagnostic_row(),
            self._alignment_connection_diagnostic_row(station_connection_rows),
            self._stations_connection_diagnostic_row(),
            self._profile_connection_diagnostic_row(station_connection_rows),
            self._tin_connection_diagnostic_row(station_connection_rows),
            self._fg_eg_connection_diagnostic_row(station_connection_rows),
        ]

    def _source_link_diagnostic_row(self) -> list[str]:
        bridge_rows = [dict(row or {}) for row in list(self.preview.get("bridge_diagnostic_rows", []) or [])]
        issue_rows = [
            row
            for row in bridge_rows
            if str(row.get("status", "") or "").strip() not in {"", "ok", "not_applicable"}
        ]
        if not issue_rows:
            return [
                "Source Links",
                "ok",
                "Alignment/Profile source links are consistent.",
                "No action required.",
            ]
        status = "error" if any(str(row.get("status", "") or "") == "error" for row in issue_rows) else "warning"
        kinds = ", ".join(str(row.get("kind", "") or "source") for row in issue_rows[:3])
        if len(issue_rows) > 3:
            kinds += f", +{len(issue_rows) - 3} more"
        return [
            "Source Links",
            status,
            f"{len(issue_rows)} source/link diagnostic issue(s): {kinds}.",
            "Check Source Link Summary, then reopen Alignment or Profile if the linked source is wrong.",
        ]

    def _alignment_connection_diagnostic_row(self, rows: list[dict[str, object]]) -> list[str]:
        if self.preview.get("alignment_model") is None:
            return [
                "Alignment",
                "error",
                "No AlignmentModel is available for station XY evaluation.",
                "Open Alignment and create or select a v1 alignment source.",
            ]
        if not rows:
            return [
                "Alignment",
                "warning",
                "No station rows are available to evaluate Alignment XY.",
                "Open Stations and apply stationing for the active alignment.",
            ]
        bad_rows = [row for row in rows if str(row.get("alignment_status", "") or "") != "ok"]
        if not bad_rows:
            return [
                "Alignment",
                "ok",
                f"All {len(rows)} station row(s) resolve to valid Alignment XY.",
                "No action required.",
            ]
        status = "error" if len(bad_rows) == len(rows) else "warning"
        return [
            "Alignment",
            status,
            f"{len(bad_rows)} of {len(rows)} station row(s) failed Alignment XY evaluation.",
            "Open Alignment and inspect geometry gaps or station range limits.",
        ]

    def _stations_connection_diagnostic_row(self) -> list[str]:
        plan_output = self.preview.get("plan_output")
        station_rows = list(getattr(plan_output, "station_rows", []) or [])
        if not station_rows:
            return [
                "Stations",
                "error",
                "No generated station grid is available.",
                "Open Stations and click Apply to generate station rows.",
            ]
        return [
            "Stations",
            "ok",
            self._station_rows_range_text(station_rows),
            "Use the Station Connection table above for full station-grid review.",
        ]

    def _profile_connection_diagnostic_row(self, rows: list[dict[str, object]]) -> list[str]:
        if self.preview.get("profile_model") is None:
            return [
                "Profile / FG",
                "error",
                "No ProfileModel is available for finished-grade evaluation.",
                "Open Profile and create or import profile control rows.",
            ]
        if not rows:
            return [
                "Profile / FG",
                "warning",
                "No station rows are available to evaluate FG.",
                "Open Stations and apply stationing before reviewing FG continuity.",
            ]
        bad_rows = [row for row in rows if str(row.get("profile_status", "") or "") != "ok"]
        if not bad_rows:
            return [
                "Profile / FG",
                "ok",
                f"FG evaluates at all {len(rows)} station row(s).",
                "No action required.",
            ]
        status = "error" if len(bad_rows) == len(rows) else "warning"
        return [
            "Profile / FG",
            status,
            f"{len(bad_rows)} of {len(rows)} station row(s) failed FG evaluation.",
            "Open Profile and check station range, PVI rows, or vertical curve coverage.",
        ]

    def _tin_connection_diagnostic_row(self, rows: list[dict[str, object]]) -> list[str]:
        if self.preview.get("tin_surface") is None:
            return [
                "TIN / EG",
                "warning",
                "No TIN source is linked, so EG sampling is unavailable.",
                "Build or select a TIN if EG comparison is required.",
            ]
        if not rows:
            return [
                "TIN / EG",
                "warning",
                "No station rows are available for EG sampling review.",
                "Open Stations and apply stationing before EG review.",
            ]
        bad_rows = [row for row in rows if str(row.get("eg_status", "") or "") != "ok"]
        if not bad_rows:
            return [
                "TIN / EG",
                "ok",
                f"EG samples hit the TIN at all {len(rows)} station row(s).",
                "No action required.",
            ]
        status = "error" if len(bad_rows) == len(rows) else "warning"
        return [
            "TIN / EG",
            status,
            f"{len(bad_rows)} of {len(rows)} station row(s) did not produce EG elevations.",
            "Open TIN and inspect boundary, voids, or station range coverage.",
        ]

    def _fg_eg_connection_diagnostic_row(self, rows: list[dict[str, object]]) -> list[str]:
        if self.preview.get("tin_surface") is None:
            return [
                "FG-EG",
                "not_applicable",
                "FG-EG delta is unavailable because no TIN is linked.",
                "Build or select a TIN to enable FG-EG comparison.",
            ]
        deltas = []
        for row in rows:
            try:
                if row.get("delta_fg_eg", None) is not None:
                    deltas.append(float(row.get("delta_fg_eg")))
            except Exception:
                continue
        if not deltas:
            return [
                "FG-EG",
                "warning",
                "No station rows have both FG and EG elevations.",
                "Check Profile / FG and TIN / EG diagnostics first.",
            ]
        missing_count = max(0, len(rows) - len(deltas))
        status = "ok" if missing_count == 0 else "warning"
        missing_text = "" if missing_count == 0 else f"; {missing_count} row(s) missing delta"
        max_abs_delta = max(abs(value) for value in deltas)
        return [
            "FG-EG",
            status,
            f"FG-EG delta available on {len(deltas)} row(s); max abs delta {max_abs_delta:.3f} m{missing_text}.",
            "Use this as an early profile/terrain reasonableness check before section review.",
        ]

    def _bridge_diagnostic_rows(self, *, issues_only: bool = False) -> list[list[str]]:
        rows = []
        for row in list(self.preview.get("bridge_diagnostic_rows", []) or []):
            item = dict(row or {})
            status = str(item.get("status", "") or "").strip()
            if issues_only and status in {"", "ok", "not_applicable"}:
                continue
            rows.append(
                [
                    str(item.get("kind", "") or ""),
                    status,
                    str(item.get("message", "") or ""),
                    str(item.get("notes", "") or ""),
                ]
            )
        return rows

    def _bridge_diagnostic_counts(self) -> dict[str, int]:
        counts = {"ok": 0, "warning": 0, "error": 0, "not_applicable": 0}
        for row in list(self.preview.get("bridge_diagnostic_rows", []) or []):
            status = str(dict(row or {}).get("status", "") or "").strip()
            counts[status] = counts.get(status, 0) + 1
        return counts

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

    def _station_connection_table_rows(self, *, issues_only: bool = False) -> list[list[str]]:
        rows = []
        for row in self._station_connection_rows():
            if issues_only and str(row.get("overall_status", "") or "") == "ok":
                continue
            rows.append(
                [
                    f"{float(row.get('station', 0.0) or 0.0):.3f}",
                    self._format_optional_float(row.get("x", None)),
                    self._format_optional_float(row.get("y", None)),
                    str(row.get("alignment_status", "") or ""),
                    self._format_optional_float(row.get("fg_elevation", None)),
                    self._format_optional_float(row.get("fg_grade", None)),
                    str(row.get("profile_status", "") or ""),
                    self._format_optional_float(row.get("eg_elevation", None)),
                    str(row.get("eg_status", "") or ""),
                    self._format_optional_float(row.get("delta_fg_eg", None)),
                    str(row.get("notes", "") or ""),
                ]
            )
        return rows

    def _station_connection_rows(self) -> list[dict[str, object]]:
        plan_output = self.preview.get("plan_output")
        station_rows = list(getattr(plan_output, "station_rows", []) or [])
        stations = []
        for row in station_rows:
            try:
                station = float(getattr(row, "station", 0.0) or 0.0)
            except Exception:
                continue
            stations.append(
                {
                    "station": station,
                    "label": str(getattr(row, "station_label", "") or f"STA {station:.3f}"),
                    "x": getattr(row, "x", None),
                    "y": getattr(row, "y", None),
                }
            )
        if not stations:
            for row in self._key_station_rows():
                try:
                    station = float(row.get("station", 0.0) or 0.0)
                except Exception:
                    continue
                stations.append(
                    {
                        "station": station,
                        "label": str(row.get("label", "") or f"STA {station:.3f}"),
                        "x": row.get("x", None),
                        "y": row.get("y", None),
                    }
                )

        alignment_model = self.preview.get("alignment_model")
        profile_model = self.preview.get("profile_model")
        alignment_service = self._alignment_eval_service()
        profile_service = self._profile_eval_service()
        eg_rows = self._eg_sample_rows_by_station()

        result = []
        seen = set()
        for station_row in sorted(stations, key=lambda item: float(item.get("station", 0.0) or 0.0)):
            station = float(station_row.get("station", 0.0) or 0.0)
            rounded = round(station, 9)
            if rounded in seen:
                continue
            seen.add(rounded)
            item = {
                "station": station,
                "label": str(station_row.get("label", "") or f"STA {station:.3f}"),
                "x": station_row.get("x", None),
                "y": station_row.get("y", None),
                "alignment_status": "missing",
                "profile_status": "missing",
                "eg_status": "no_tin",
                "overall_status": "issue",
                "notes": "",
            }
            notes = []
            if alignment_model is not None and alignment_service is not None:
                try:
                    alignment_eval = alignment_service.evaluate_station(alignment_model, station)
                    item["alignment_status"] = str(getattr(alignment_eval, "status", "") or "")
                    if item["alignment_status"] == "ok":
                        item["x"] = getattr(alignment_eval, "x", item.get("x", None))
                        item["y"] = getattr(alignment_eval, "y", item.get("y", None))
                    else:
                        notes.append(str(getattr(alignment_eval, "notes", "") or "Alignment evaluation failed."))
                except Exception as exc:
                    item["alignment_status"] = "error"
                    notes.append(f"Alignment evaluation failed: {exc}")
            else:
                notes.append("Alignment source missing.")

            if profile_model is not None and profile_service is not None:
                try:
                    profile_eval = profile_service.evaluate_station(profile_model, station)
                    item["profile_status"] = str(getattr(profile_eval, "status", "") or "")
                    item["fg_elevation"] = getattr(profile_eval, "elevation", None)
                    item["fg_grade"] = getattr(profile_eval, "grade", None)
                    if item["profile_status"] != "ok":
                        notes.append(str(getattr(profile_eval, "notes", "") or "Profile evaluation failed."))
                except Exception as exc:
                    item["profile_status"] = "error"
                    notes.append(f"Profile evaluation failed: {exc}")
            else:
                notes.append("Profile source missing.")

            eg_row = self._nearest_eg_sample_row(eg_rows, station)
            if eg_row is not None:
                item["eg_status"] = str(getattr(eg_row, "status", "") or "")
                item["eg_elevation"] = getattr(eg_row, "elevation", None)
                if item["eg_status"] != "ok":
                    notes.append(str(getattr(eg_row, "notes", "") or "EG sample did not hit TIN."))
            elif self.preview.get("tin_surface", None) is None:
                item["eg_status"] = "no_tin"
                notes.append("EG TIN not available.")
            else:
                item["eg_status"] = "not_sampled"
                nearest = self._nearest_eg_sample_row_any(eg_rows, station)
                if nearest is not None:
                    nearest_station = float(getattr(nearest, "station", 0.0) or 0.0)
                    delta = abs(nearest_station - station)
                    notes.append(
                        f"EG sample grid mismatch. Nearest EG sample STA {nearest_station:.3f} "
                        f"(delta {delta:.3f} m)."
                    )
                else:
                    notes.append("EG not sampled for this station.")

            if item.get("fg_elevation", None) is not None and item.get("eg_elevation", None) is not None:
                try:
                    item["delta_fg_eg"] = float(item["fg_elevation"]) - float(item["eg_elevation"])
                except Exception:
                    pass

            statuses = [item["alignment_status"], item["profile_status"], item["eg_status"]]
            item["overall_status"] = "ok" if all(status == "ok" for status in statuses) else "issue"
            item["notes"] = "; ".join(note for note in notes if note)
            result.append(item)
        return result

    @staticmethod
    def _alignment_eval_service():
        try:
            from ...services.evaluation import AlignmentEvaluationService

            return AlignmentEvaluationService()
        except Exception:
            return None

    @staticmethod
    def _profile_eval_service():
        try:
            from ...services.evaluation import ProfileEvaluationService

            return ProfileEvaluationService()
        except Exception:
            return None

    def _eg_sample_rows_by_station(self) -> list[object]:
        result = self.preview.get("profile_tin_sample_result", None)
        return list(getattr(result, "rows", []) or [])

    @staticmethod
    def _nearest_eg_sample_row(rows: list[object], station: float, *, tolerance: float = 1.0e-6):
        if not rows:
            return None
        nearest = min(rows, key=lambda row: abs(float(getattr(row, "station", 0.0) or 0.0) - float(station)))
        try:
            if abs(float(getattr(nearest, "station", 0.0) or 0.0) - float(station)) <= tolerance:
                return nearest
        except Exception:
            return None
        return None

    @staticmethod
    def _nearest_eg_sample_row_any(rows: list[object], station: float):
        if not rows:
            return None
        try:
            return min(rows, key=lambda row: abs(float(getattr(row, "station", 0.0) or 0.0) - float(station)))
        except Exception:
            return None

    def _refresh_connection_table(self) -> None:
        slot = getattr(self, "_connection_table_slot", None)
        if slot is None:
            return
        while slot.count():
            item = slot.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        checkbox = getattr(self, "_connection_issues_only", None)
        issues_only = bool(checkbox.isChecked()) if checkbox is not None else False
        self._connection_table = self._table_widget(
            headers=[
                "Station",
                "X",
                "Y",
                "Alignment",
                "FG Elev.",
                "FG Grade",
                "Profile",
                "EG Elev.",
                "EG",
                "FG-EG",
                "Notes",
            ],
            rows=self._station_connection_table_rows(issues_only=issues_only),
            empty_text="No station connection rows.",
        )
        slot.addWidget(self._connection_table)
        self._apply_station_connection_row_styles(self._connection_table)
        self._connect_station_highlight_table(self._connection_table)

    def _apply_station_connection_row_styles(self, table) -> None:
        if not hasattr(table, "rowCount") or not hasattr(table, "item"):
            return
        try:
            table.setStyleSheet(
                "QTableWidget::item { color: #141414; } "
                "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
            )
        except Exception:
            pass
        for row_index in range(int(table.rowCount())):
            statuses = [
                self._table_text(table, row_index, 3),
                self._table_text(table, row_index, 6),
                self._table_text(table, row_index, 8),
            ]
            color = self._station_connection_row_color(statuses)
            if color is None:
                continue
            try:
                from freecad.Corridor_Road.qt_compat import QtGui

                brush = QtGui.QBrush(QtGui.QColor(*color))
                text_brush = QtGui.QBrush(QtGui.QColor(20, 20, 20))
                for column_index in range(int(table.columnCount())):
                    item = table.item(row_index, column_index)
                    if item is not None:
                        item.setBackground(brush)
                        item.setForeground(text_brush)
            except Exception:
                pass

    @staticmethod
    def _station_connection_row_color(statuses: list[str]) -> tuple[int, int, int] | None:
        normalized = {str(status or "").strip().lower() for status in list(statuses or [])}
        if not normalized:
            return None
        if normalized == {"ok"}:
            return (220, 245, 224)
        if normalized.intersection({"error", "missing", "failed", "blocked"}):
            return (255, 220, 220)
        if normalized.intersection({"no_tin", "not_sampled", "no_hit", "partial", "warning", "stale"}):
            return (255, 241, 205)
        return (238, 238, 238)

    @staticmethod
    def _table_text(table, row_index: int, column_index: int) -> str:
        try:
            item = table.item(int(row_index), int(column_index))
            return str(item.text() or "") if item is not None else ""
        except Exception:
            return ""

    def _key_station_combo_label(self, row: dict[str, object]) -> str:
        station = float(row.get("station", 0.0) or 0.0)
        label = str(row.get("label", "") or f"STA {station:.3f}")
        reason = str(row.get("navigation_reason", "") or "").strip()
        if not reason:
            reason = self._navigation_reason_from_kind(
                str(row.get("navigation_kind", "") or ""),
                is_current=bool(row.get("is_current", False)),
            )
        return f"{label} - {reason}" if reason else label

    @staticmethod
    def _navigation_reason_from_kind(navigation_kind: str, *, is_current: bool = False) -> str:
        if is_current:
            return "Current review focus station"
        return {
            "first": "Start of station range",
            "last": "End of station range",
            "previous": "Station before the current focus",
            "next": "Station after the current focus",
            "current": "Current review focus station",
        }.get(str(navigation_kind or "").strip(), "Review navigation station")

    def _alignment_frame_rows(self) -> list[list[str]]:
        rows = []
        for row in self._key_station_rows():
            status = str(row.get("alignment_eval_status", "") or "").strip()
            if not status:
                continue
            rows.append(
                [
                    f"{float(row.get('station', 0.0) or 0.0):.3f}",
                    self._format_optional_float(row.get("x", None)),
                    self._format_optional_float(row.get("y", None)),
                    self._format_optional_float(row.get("tangent_direction_deg", None)),
                    str(row.get("active_element_id", "") or ""),
                    status,
                ]
            )
        return rows

    def _profile_eval_rows(self) -> list[list[str]]:
        rows = []
        for row in self._key_station_rows():
            status = str(row.get("profile_eval_status", "") or "").strip()
            if not status:
                continue
            segment = str(row.get("active_profile_segment_start_id", "") or "")
            segment_end = str(row.get("active_profile_segment_end_id", "") or "")
            if segment and segment_end:
                segment = f"{segment} -> {segment_end}"
            rows.append(
                [
                    f"{float(row.get('station', 0.0) or 0.0):.3f}",
                    self._format_optional_float(row.get("profile_elevation", None)),
                    self._format_optional_float(row.get("profile_grade", None)),
                    segment,
                    str(row.get("active_vertical_curve_id", "") or ""),
                    status,
                ]
            )
        return rows

    def _plan_geometry_rows(self) -> list[list[str]]:
        return [
            [
                str(getattr(row, "kind", "") or ""),
                str(self._station_start(row)),
                str(self._station_end(row)),
                str(len(list(getattr(row, "x_values", []) or []))),
            ]
            for row in list(getattr(self.preview.get("plan_output"), "geometry_rows", []) or [])
        ]

    def _profile_line_rows(self) -> list[list[str]]:
        rows = []
        for row in list(getattr(self.preview.get("profile_output"), "line_rows", []) or []):
            stations = [float(value) for value in list(getattr(row, "station_values", []) or [])]
            elevations = [float(value) for value in list(getattr(row, "elevation_values", []) or [])]
            if not stations or not elevations:
                continue
            rows.append(
                [
                    str(getattr(row, "kind", "") or ""),
                    str(min(len(stations), len(elevations))),
                    f"{min(stations):.3f} -> {max(stations):.3f}",
                    f"{min(elevations):.3f} -> {max(elevations):.3f}",
                    str(getattr(row, "source_ref", "") or ""),
                ]
            )
        return rows

    def _profile_control_rows(self) -> list[list[str]]:
        return [
            [
                str(getattr(row, "station", "") or ""),
                str(getattr(row, "elevation", "") or ""),
                str(getattr(row, "label", "") or ""),
            ]
            for row in list(getattr(self.preview.get("profile_output"), "pvi_rows", []) or [])
        ]

    @staticmethod
    def _format_optional_float(value) -> str:
        try:
            if value is None or value == "":
                return ""
            return f"{float(value):.3f}"
        except Exception:
            return ""

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
            self._status_label.setText("No navigation station rows are available.")
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
        self._set_status_safely(f"Opening {station_label} in v1 viewer.", ok=True)
        try:
            Gui.Control.closeDialog()
        except Exception:
            pass
        Gui.runCommand("CorridorRoad_V1ReviewPlanProfile", 0)

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

    def _earthwork_area_width_value(self) -> float | None:
        candidates = [
            self.preview.get("earthwork_area_width", None),
            self.preview.get("profile_earthwork_area_width", None),
        ]
        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        candidates.extend(
            [
                viewer_context.get("earthwork_area_width", None),
                viewer_context.get("profile_earthwork_area_width", None),
                viewer_context.get("section_width", None),
            ]
        )
        for candidate in candidates:
            if candidate is None or candidate == "":
                continue
            try:
                value = float(candidate)
            except Exception:
                continue
            if value > 0.0:
                return value
        return None

    def _earthwork_area_hint_status_text(self) -> str:
        result = self.preview.get("profile_earthwork_area_hint_result", None)
        if result is None:
            if self._earthwork_area_width_value() is None:
                return "Area hints are disabled until a positive section width is applied."
            return ""
        status = str(getattr(result, "status", "") or "").strip()
        notes = str(getattr(result, "notes", "") or "").strip()
        if status and notes:
            return f"{status}: {notes}"
        return status or notes

    def _earthwork_attachment_rows(self) -> list[list[str]]:
        return [
            [
                str(getattr(row, "kind", "") or ""),
                str(getattr(row, "station_start", "") or ""),
                str(getattr(row, "station_end", "") or ""),
                str(getattr(row, "value", "") or ""),
                str(getattr(row, "unit", "") or ""),
            ]
            for row in list(getattr(self.preview.get("profile_output"), "earthwork_rows", []) or [])
        ]

    def _should_show_earthwork_section(self) -> bool:
        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        source_panel = str(viewer_context.get("source_panel", "") or "").strip().lower()
        if "earthwork" in source_panel:
            return True
        if self._earthwork_area_width_value() is not None:
            return True
        if self._earthwork_attachment_rows():
            return True
        return False

    def _set_status_safely(self, text: str, *, ok: bool = True) -> None:
        label = getattr(self, "_status_label", None)
        if label is None:
            return
        try:
            label.setText(str(text or ""))
            label.setStyleSheet("color: #666;" if ok else "color: #b33;")
        except RuntimeError:
            # The task panel can be destroyed while reopening the viewer.
            pass

    def _apply_earthwork_area_width(self) -> None:
        spin = getattr(self, "_earthwork_area_width_spin", None)
        width = float(spin.value()) if spin is not None else 0.0
        if width <= 0.0:
            self._status_label.setText("Enter a positive section width before applying earthwork area hints.")
            self._status_label.setStyleSheet("color: #b36b00;")
            return
        if Gui is None:
            self._status_label.setText("FreeCAD GUI is not available for applying earthwork area width.")
            self._status_label.setStyleSheet("color: #b33;")
            return

        legacy_objects = dict(self.preview.get("legacy_objects", {}) or {})
        alignment = legacy_objects.get("alignment")
        profile = legacy_objects.get("profile")
        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        viewer_context["earthwork_area_width"] = width

        context_payload = {
            "source": "v1_plan_profile_area_width",
            "preferred_alignment_name": str(getattr(alignment, "Name", "") or "").strip(),
            "preferred_profile_name": str(getattr(profile, "Name", "") or "").strip(),
            "viewer_context": viewer_context,
        }
        focus_station = viewer_context.get("focus_station", None)
        if focus_station is not None and focus_station != "":
            try:
                context_payload["preferred_station"] = float(focus_station)
            except Exception:
                pass
        set_ui_context(**context_payload)
        self._set_status_safely(f"Applying earthwork area width {width:.3f} m.", ok=True)
        try:
            Gui.Control.closeDialog()
        except Exception:
            pass
        Gui.runCommand("CorridorRoad_V1ReviewPlanProfile", 0)

    def _open_legacy_command(self, command_name: str) -> None:
        legacy_objects = dict(self.preview.get("legacy_objects", {}) or {})
        objects_to_select = []
        if command_name in ("CorridorRoad_V1EditAlignment", "CorridorRoad_EditAlignment"):
            objects_to_select = [legacy_objects.get("alignment")]
        elif command_name == "CorridorRoad_V1GenerateStations":
            objects_to_select = [legacy_objects.get("stationing"), legacy_objects.get("alignment")]
        elif command_name in ("CorridorRoad_V1EditProfile", "CorridorRoad_EditProfiles", "CorridorRoad_EditPVI"):
            objects_to_select = [legacy_objects.get("profile"), legacy_objects.get("alignment")]
        elif command_name == "CorridorRoad_V1EditTIN":
            objects_to_select = [legacy_objects.get("tin")]
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
        self._set_status_safely(f"Opening `{command_name}`.", ok=True)
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
        if not success:
            self._set_status_safely(message, ok=False)

    def _connect_connection_diagnostics_table(self, table) -> None:
        if not hasattr(table, "itemDoubleClicked"):
            return
        try:
            table.itemDoubleClicked.connect(lambda item: self._open_diagnostic_table_row(item))
        except Exception:
            pass

    def _open_diagnostic_table_row(self, item) -> None:
        table = item.tableWidget() if item is not None and hasattr(item, "tableWidget") else None
        if table is None or not hasattr(table, "item"):
            return
        row_index = int(item.row())
        area = self._table_text(table, row_index, 0)
        status = self._table_text(table, row_index, 1)
        command_name = self._diagnostic_area_command(area, status=status)
        if not command_name:
            self._set_status_safely(f"No source handoff is configured for diagnostic area `{area}`.", ok=False)
            return
        self._open_legacy_command(command_name)

    @staticmethod
    def _diagnostic_area_command(area: str, *, status: str = "") -> str:
        normalized = str(area or "").strip().lower()
        status_text = str(status or "").strip().lower()
        if normalized in {"alignment", "source links"}:
            return "CorridorRoad_V1EditAlignment"
        if normalized == "stations":
            return "CorridorRoad_V1GenerateStations"
        if normalized == "profile / fg":
            return "CorridorRoad_V1EditProfile"
        if normalized == "tin / eg":
            return "CorridorRoad_V1EditTIN"
        if normalized == "fg-eg":
            return "CorridorRoad_V1EditTIN" if status_text in {"not_applicable", "warning", "error"} else "CorridorRoad_V1EditProfile"
        return ""

    def _connect_station_highlight_table(self, table) -> None:
        if not hasattr(table, "itemDoubleClicked"):
            return
        try:
            table.itemDoubleClicked.connect(lambda item: self._highlight_table_station(item))
        except Exception:
            pass

    def _connect_range_start_highlight_table(self, table, *, station_column: int) -> None:
        if not hasattr(table, "itemDoubleClicked"):
            return
        try:
            table.itemDoubleClicked.connect(
                lambda item, column=int(station_column): self._highlight_table_range_start(item, column)
            )
        except Exception:
            pass

    def _highlight_table_range_start(self, item, station_column: int) -> None:
        row_index = int(item.row()) if item is not None and hasattr(item, "row") else -1
        table = item.tableWidget() if item is not None and hasattr(item, "tableWidget") else None
        station_value = self._range_start_station_from_table_row(table, row_index, station_column)
        if station_value is None:
            self._status_label.setText("No station range start is available for this row.")
            self._status_label.setStyleSheet("color: #b36b00;")
            return
        self._highlight_station_value(station_value)

    def _highlight_table_station(self, item) -> None:
        row_index = int(item.row()) if item is not None and hasattr(item, "row") else -1
        table = item.tableWidget() if item is not None and hasattr(item, "tableWidget") else None
        station_value = self._station_value_from_table_row(table, row_index)
        if station_value is None:
            self._status_label.setText("No station value is available for this row.")
            self._status_label.setStyleSheet("color: #b36b00;")
            return
        self._highlight_station_value(station_value)

    def _highlight_station_value(self, station_value: float) -> None:
        row = self._station_highlight_row(station_value)
        if row is None:
            self._status_label.setText(f"Could not resolve station {float(station_value):.3f} for 3D highlight.")
            self._status_label.setStyleSheet("color: #b36b00;")
            return
        document = getattr(App, "ActiveDocument", None) if App is not None else None
        if document is None:
            self._status_label.setText("No active document is available for station highlight.")
            self._status_label.setStyleSheet("color: #b33;")
            return
        try:
            from ...commands.cmd_review_stations import show_station_highlight

            highlight = show_station_highlight(document, row)
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
            self._status_label.setText(f"Highlighted {row.get('label', f'STA {float(station_value):.3f}')} in 3D View.")
            self._status_label.setStyleSheet("color: #666;")
        except Exception as exc:
            self._status_label.setText(f"Station highlight failed: {exc}")
            self._status_label.setStyleSheet("color: #b33;")

    def _station_highlight_row(self, station_value: float) -> dict[str, object] | None:
        try:
            target = float(station_value)
        except Exception:
            return None
        best_row = None
        best_delta = None
        for row in self._key_station_rows():
            try:
                delta = abs(float(row.get("station", 0.0) or 0.0) - target)
            except Exception:
                continue
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_row = row
        if best_row is None:
            return None
        return {
            "station": float(best_row.get("station", target) or target),
            "label": str(best_row.get("label", "") or f"STA {target:.3f}"),
            "x": float(best_row.get("x", 0.0) or 0.0),
            "y": float(best_row.get("y", 0.0) or 0.0),
            "tangent": float(best_row.get("tangent_direction_deg", best_row.get("tangent", 0.0)) or 0.0),
        }

    @staticmethod
    def _station_value_from_table_row(table, row_index: int) -> float | None:
        if table is None or row_index < 0 or not hasattr(table, "item"):
            return None
        item = table.item(int(row_index), 0)
        if item is None:
            return None
        try:
            return float(str(item.text() or "").strip())
        except Exception:
            return None

    @staticmethod
    def _range_start_station_from_table_row(table, row_index: int, station_column: int) -> float | None:
        if table is None or row_index < 0 or not hasattr(table, "item"):
            return None
        item = table.item(int(row_index), int(station_column))
        if item is None:
            return None
        text = str(item.text() or "").strip()
        if "->" in text:
            text = text.split("->", 1)[0].strip()
        try:
            return float(text)
        except Exception:
            return None

    def _station_start(self, row) -> object:
        value = getattr(row, "station_start", None)
        if value is not None:
            return value
        element = self._alignment_element_for_geometry_row(row)
        if element is None:
            return ""
        return getattr(element, "station_start", "")

    def _station_end(self, row) -> object:
        value = getattr(row, "station_end", None)
        if value is not None:
            return value
        element = self._alignment_element_for_geometry_row(row)
        if element is None:
            return ""
        return getattr(element, "station_end", "")

    def _alignment_element_for_geometry_row(self, row):
        alignment_model = self.preview.get("alignment_model")
        candidates = {
            str(getattr(row, "source_ref", "") or "").strip(),
            str(getattr(row, "row_id", "") or "").strip(),
        }
        candidates.discard("")
        for element in list(getattr(alignment_model, "geometry_sequence", []) or []):
            element_id = str(getattr(element, "element_id", "") or "").strip()
            if element_id in candidates:
                return element
        return None

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

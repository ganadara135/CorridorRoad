# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets
import math

from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
from freecad.Corridor_Road.ui.task_cross_section_viewer import CrossSectionViewerTaskPanel


class CrossSectionEditorTaskPanel(CrossSectionViewerTaskPanel):
    """MVP editor shell built on the existing cross-section viewer."""

    def __init__(self):
        self._editor_overlay_items = []
        self._editor_overlay_debug_rows = []
        self._editor_drag_state = None
        self._resolution_action_specs_cache = []
        self._editor_preview_current = False
        self._editor_preview_key = None
        self._editor_preview_reason = ""
        super().__init__()

    def _build_ui(self):
        viewer = super()._build_ui()
        viewer.setWindowTitle("CorridorRoad - Cross Section Editor")
        try:
            # The editor relies on guide geometry and the side inspector more than
            # dense canvas labels, so start with the clutter-heavy overlays off.
            self.chk_show_labels.show()
            self.chk_show_labels.setText("Show canvas labels")
            self.chk_show_labels.setChecked(False)
            self.chk_show_diagnostics.setChecked(False)
        except Exception:
            pass
        try:
            self.view._corridorroad_click_handler = self._handle_editor_canvas_click
            self.view._corridorroad_move_handler = self._handle_editor_canvas_move
            self.view._corridorroad_release_handler = self._handle_editor_canvas_release
        except Exception:
            pass

        root = QtWidgets.QWidget()
        root.setWindowTitle("CorridorRoad - Cross Section Editor")
        layout = QtWidgets.QHBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(viewer, 1)
        layout.addWidget(self._build_editor_panel())
        return root

    def _build_editor_panel(self):
        panel = QtWidgets.QGroupBox("Selection / Edit Panel")
        panel.setMinimumWidth(320)
        panel.setMaximumWidth(420)
        main = QtWidgets.QVBoxLayout(panel)
        main.setContentsMargins(8, 8, 8, 8)
        main.setSpacing(8)

        self.cmb_editor_mode = QtWidgets.QComboBox()
        self.cmb_editor_mode.addItems(["Review", "Select", "Edit"])
        main.addWidget(QtWidgets.QLabel("Mode"))
        main.addWidget(self.cmb_editor_mode)

        self.cmb_component_target = QtWidgets.QComboBox()
        main.addWidget(QtWidgets.QLabel("Target"))
        main.addWidget(self.cmb_component_target)

        self.txt_target = QtWidgets.QPlainTextEdit()
        self.txt_target.setReadOnly(True)
        self.txt_target.setMinimumHeight(180)
        main.addWidget(QtWidgets.QLabel("Target Details"))
        main.addWidget(self.txt_target)

        self.tbl_parameters = QtWidgets.QTableWidget(0, 2)
        self.tbl_parameters.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.tbl_parameters.verticalHeader().setVisible(False)
        self.tbl_parameters.horizontalHeader().setStretchLastSection(True)
        self.tbl_parameters.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl_parameters.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_parameters.setMinimumHeight(160)
        main.addWidget(QtWidgets.QLabel("Parameters"))
        main.addWidget(self.tbl_parameters)

        self.cmb_edit_parameter = QtWidgets.QComboBox()
        self.cmb_edit_parameter.addItems(
            [
                "Width",
                "Slope %",
                "Height",
                "Extra Width",
                "Back Slope %",
                "Region Side Policy",
                "Region Daylight Policy",
            ]
        )
        main.addWidget(QtWidgets.QLabel("Edit Parameter"))
        main.addWidget(self.cmb_edit_parameter)

        self.lbl_length_value = QtWidgets.QLabel("Width Value")
        self.spin_width = QtWidgets.QDoubleSpinBox()
        self.spin_width.setDecimals(3)
        self.spin_width.setRange(-1000000.0, 1000000.0)
        self.spin_width.setSingleStep(0.100)
        main.addWidget(self.lbl_length_value)
        main.addWidget(self.spin_width)

        self.lbl_percent_value = QtWidgets.QLabel("Slope Value")
        self.spin_slope = QtWidgets.QDoubleSpinBox()
        self.spin_slope.setDecimals(3)
        self.spin_slope.setRange(-1000.0, 1000.0)
        self.spin_slope.setSingleStep(1.000)
        self.spin_slope.setSuffix(" %")
        main.addWidget(self.lbl_percent_value)
        main.addWidget(self.spin_slope)

        self.cmb_region_policy = QtWidgets.QComboBox()
        main.addWidget(QtWidgets.QLabel("Region Policy"))
        main.addWidget(self.cmb_region_policy)

        self.cmb_edit_scope = QtWidgets.QComboBox()
        self.cmb_edit_scope.addItems(["Global Source", "Active Region", "Station Range", "Current Station Only"])
        main.addWidget(QtWidgets.QLabel("Scope"))
        main.addWidget(self.cmb_edit_scope)

        self.spin_edit_start_station = QtWidgets.QDoubleSpinBox()
        self.spin_edit_start_station.setDecimals(3)
        self.spin_edit_start_station.setRange(0.0, 1000000.0)
        self.spin_edit_start_station.setSingleStep(1.0)
        main.addWidget(QtWidgets.QLabel("Start Station"))
        main.addWidget(self.spin_edit_start_station)

        self.spin_edit_end_station = QtWidgets.QDoubleSpinBox()
        self.spin_edit_end_station.setDecimals(3)
        self.spin_edit_end_station.setRange(0.0, 1000000.0)
        self.spin_edit_end_station.setSingleStep(1.0)
        main.addWidget(QtWidgets.QLabel("End Station"))
        main.addWidget(self.spin_edit_end_station)

        self.spin_transition_in = QtWidgets.QDoubleSpinBox()
        self.spin_transition_in.setDecimals(3)
        self.spin_transition_in.setRange(0.0, 1000000.0)
        self.spin_transition_in.setSingleStep(1.0)
        main.addWidget(QtWidgets.QLabel("Transition In"))
        main.addWidget(self.spin_transition_in)

        self.spin_transition_out = QtWidgets.QDoubleSpinBox()
        self.spin_transition_out.setDecimals(3)
        self.spin_transition_out.setRange(0.0, 1000000.0)
        self.spin_transition_out.setSingleStep(1.0)
        main.addWidget(QtWidgets.QLabel("Transition Out"))
        main.addWidget(self.spin_transition_out)

        self.lbl_apply_state = QtWidgets.QLabel("")
        self.lbl_apply_state.setWordWrap(True)
        main.addWidget(self.lbl_apply_state)

        resolution_row = QtWidgets.QHBoxLayout()
        self.btn_resolution_primary = QtWidgets.QPushButton("")
        self.btn_resolution_secondary = QtWidgets.QPushButton("")
        self.btn_resolution_primary.setVisible(False)
        self.btn_resolution_secondary.setVisible(False)
        self.btn_resolution_primary.setEnabled(False)
        self.btn_resolution_secondary.setEnabled(False)
        resolution_row.addWidget(self.btn_resolution_primary)
        resolution_row.addWidget(self.btn_resolution_secondary)
        main.addLayout(resolution_row)

        self.txt_validation = QtWidgets.QPlainTextEdit()
        self.txt_validation.setReadOnly(True)
        self.txt_validation.setMinimumHeight(90)
        main.addWidget(QtWidgets.QLabel("Validation"))
        main.addWidget(self.txt_validation)

        self.txt_impact = QtWidgets.QPlainTextEdit()
        self.txt_impact.setReadOnly(True)
        self.txt_impact.setMinimumHeight(150)
        main.addWidget(QtWidgets.QLabel("Impact Preview"))
        main.addWidget(self.txt_impact)

        self.lbl_preview_state = QtWidgets.QLabel("Preview: no target.")
        self.lbl_preview_state.setWordWrap(True)
        main.addWidget(self.lbl_preview_state)

        row = QtWidgets.QHBoxLayout()
        self.btn_preview_impact = QtWidgets.QPushButton("Preview Impact")
        self.btn_apply_edit = QtWidgets.QPushButton("Apply")
        self.btn_apply_edit.setEnabled(False)
        row.addWidget(self.btn_preview_impact)
        row.addWidget(self.btn_apply_edit)
        main.addLayout(row)
        main.addStretch(1)

        self.cmb_component_target.currentIndexChanged.connect(self._on_editor_target_changed)
        self.cmb_editor_mode.currentIndexChanged.connect(self._on_editor_mode_changed)
        self.cmb_edit_scope.currentIndexChanged.connect(self._on_editor_scope_changed)
        self.cmb_edit_parameter.currentIndexChanged.connect(self._on_editor_parameter_changed)
        self.spin_width.valueChanged.connect(self._on_editor_value_changed)
        self.spin_slope.valueChanged.connect(self._on_editor_value_changed)
        self.cmb_region_policy.currentIndexChanged.connect(self._on_editor_value_changed)
        self.spin_edit_start_station.valueChanged.connect(self._on_editor_scope_value_changed)
        self.spin_edit_end_station.valueChanged.connect(self._on_editor_scope_value_changed)
        self.spin_transition_in.valueChanged.connect(self._on_editor_scope_value_changed)
        self.spin_transition_out.valueChanged.connect(self._on_editor_scope_value_changed)
        self.btn_preview_impact.clicked.connect(self._run_editor_impact_preview)
        self.btn_apply_edit.clicked.connect(self._apply_editor_edit)
        self.btn_resolution_primary.clicked.connect(lambda: self._run_resolution_action(0))
        self.btn_resolution_secondary.clicked.connect(lambda: self._run_resolution_action(1))
        return panel

    def _render_current_payload(self, *_args):
        super()._render_current_payload(*_args)
        self._reload_editor_targets()
        self._draw_selected_component_overlay()

    def _reload_editor_targets(self):
        if not hasattr(self, "cmb_component_target"):
            return
        current_id = ""
        current = self._current_editor_segment()
        if current:
            current_id = self._segment_key(current)
        self.cmb_component_target.blockSignals(True)
        try:
            self.cmb_component_target.clear()
            segments = self._editor_segments()
            if not segments:
                self.cmb_component_target.addItem("[No editable component target]", None)
            else:
                target_idx = 0
                for idx, seg in enumerate(segments):
                    label = self._segment_label(seg)
                    self.cmb_component_target.addItem(label, seg)
                    if current_id and self._segment_key(seg) == current_id:
                        target_idx = idx
                self.cmb_component_target.setCurrentIndex(target_idx)
        finally:
            self.cmb_component_target.blockSignals(False)
        self._refresh_editor_target()

    def _editor_segments(self):
        payload = dict(getattr(self, "_current_payload", None) or {})
        segments = list(self._component_segments_from_payload(payload) or [])
        return sorted(
            segments,
            key=lambda seg: (
                str(seg.get("scope", "") or ""),
                str(seg.get("side", "") or ""),
                float(seg.get("x0", 0.0) or 0.0),
                float(seg.get("x1", 0.0) or 0.0),
            ),
        )

    def _current_editor_segment(self):
        if not hasattr(self, "cmb_component_target"):
            return None
        data = self.cmb_component_target.currentData()
        return dict(data or {}) if data else None

    def _segment_key(self, seg):
        stable_parts = [
            str(seg.get("id", "") or "").strip(),
            str(seg.get("type", "") or "").strip().lower(),
            str(seg.get("side", "") or "").strip().lower(),
            str(seg.get("scope", "") or "").strip().lower(),
            str(seg.get("order", "") or "").strip(),
        ]
        if any(part for part in stable_parts):
            return "|".join(stable_parts)
        return "|".join(
            [
                str(seg.get("id", "") or ""),
                str(seg.get("type", "") or ""),
                str(seg.get("side", "") or ""),
                str(seg.get("scope", "") or ""),
                f"{float(seg.get('x0', 0.0) or 0.0):.6f}",
                f"{float(seg.get('x1', 0.0) or 0.0):.6f}",
            ]
        )

    def _segment_label(self, seg):
        typ = str(seg.get("type", "") or "-")
        side = str(seg.get("side", "") or "-")
        scope = self._component_scope(seg)
        cid = str(seg.get("id", "") or "-")
        span = float(seg.get("display_span", seg.get("span", 0.0)) or 0.0)
        return f"{cid} | {typ} | {side} | {scope} | {span:.3f} {self._display_unit_label()}"

    def _on_editor_mode_changed(self, *_args):
        self._refresh_editor_target()
        self._draw_selected_component_overlay()

    def _on_editor_target_changed(self, *_args):
        self._refresh_editor_target()
        self._draw_selected_component_overlay()

    def _on_editor_scope_changed(self, *_args):
        self._refresh_editor_scope_controls(force=True)
        self._refresh_editor_edit_controls(self._current_editor_segment())
        self._invalidate_editor_preview("Scope changed.")
        self._refresh_editor_apply_state()

    def _on_editor_parameter_changed(self, *_args):
        self._refresh_editor_edit_controls(self._current_editor_segment())
        self._invalidate_editor_preview("Edit parameter changed.")
        self._refresh_editor_apply_state()

    def _on_editor_value_changed(self, *_args):
        self._invalidate_editor_preview("Edit value changed.")
        self._refresh_editor_apply_state()

    def _on_editor_scope_value_changed(self, *_args):
        self._invalidate_editor_preview("Range or transition changed.")
        self._refresh_editor_apply_state()

    def _refresh_editor_target(self):
        if not hasattr(self, "txt_target"):
            return
        seg = self._current_editor_segment()
        if not seg:
            self.txt_target.setPlainText("Select a station with component segment rows to inspect it.")
            self.tbl_parameters.setRowCount(0)
            if hasattr(self, "spin_width"):
                self.spin_width.setEnabled(False)
            if hasattr(self, "spin_slope"):
                self.spin_slope.setEnabled(False)
            self._refresh_resolution_actions(None, None, {})
            self._set_editor_preview_stale(None, {}, "")
            self._refresh_editor_scope_controls(force=True)
            self._refresh_editor_apply_state()
            return
        edit_target, _edit_message = self._editor_apply_target(seg)
        payload = dict(getattr(self, "_current_payload", None) or {})
        conflict = self._editor_conflict_summary(seg, payload)
        resolution_lines = self._conflict_resolution_lines(conflict, seg, payload)
        handoff_lines = self._resolution_handoff_lines(conflict, seg, payload)
        lines = [
            f"Id: {str(seg.get('id', '-') or '-')}",
            f"Type: {str(seg.get('type', '-') or '-')}",
            f"Side: {str(seg.get('side', '-') or '-')}",
            f"Scope: {self._component_scope(seg)}",
            f"Conflict: {conflict.get('label', 'None')}",
            f"Source owner: {self._source_owner_label(seg)}",
            f"Generated source: {str(seg.get('source', '-') or '-')}",
            f"Span: {float(seg.get('display_span', seg.get('span', 0.0)) or 0.0):.3f} {self._display_unit_label()}",
            f"X0/X1: {float(seg.get('x0', 0.0) or 0.0):.3f} / {float(seg.get('x1', 0.0) or 0.0):.3f}",
            "",
            "Generated Row:",
            self._segment_generated_row(seg),
            "",
            "Raw Row Preview:",
            self._segment_raw_preview(seg),
        ]
        if resolution_lines:
            lines.extend(["", "Resolution Guide:"])
            lines.extend(f"- {row}" for row in resolution_lines)
        if handoff_lines:
            lines.extend(["", "Policy Handoff:"])
            lines.extend(f"- {row}" for row in handoff_lines)
        self.txt_target.setPlainText("\n".join(lines))
        params = [
            ("Id", str(seg.get("id", "-") or "-")),
            ("Type", str(seg.get("type", "-") or "-")),
            ("Side", str(seg.get("side", "-") or "-")),
            ("Scope", self._component_scope(seg)),
            ("Conflict", str(conflict.get("label", "None") or "None")),
            ("Resolution", str(resolution_lines[0] if resolution_lines else "-")),
            ("Handoff", str(handoff_lines[0] if handoff_lines else "-")),
            ("Source Owner", self._source_owner_label(seg)),
            ("Generated Source", str(seg.get("source", "-") or "-")),
            ("Span", f"{float(seg.get('display_span', seg.get('span', 0.0)) or 0.0):.3f} {self._display_unit_label()}"),
            ("Order", str(seg.get("order", "-") or "-")),
            ("Shape", str(seg.get("shape", "-") or "-")),
            ("Editable Now", "Yes" if edit_target else "No"),
        ]
        self.tbl_parameters.setRowCount(len(params))
        for row, (name, value) in enumerate(params):
            self.tbl_parameters.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self.tbl_parameters.setItem(row, 1, QtWidgets.QTableWidgetItem(value))
        self._refresh_editor_scope_controls(force=False)
        self._refresh_editor_edit_controls(seg)
        self._set_editor_preview_stale(seg, payload, "Preview is stale. Run Preview Impact again before applying.")
        self._refresh_editor_apply_state()

    def _refresh_editor_edit_controls(self, seg):
        self._refresh_editor_width_control(seg)
        self._refresh_editor_slope_control(seg)
        self._refresh_editor_region_policy_control(seg)

    def _refresh_editor_width_control(self, seg):
        if not hasattr(self, "spin_width"):
            return
        self.spin_width.blockSignals(True)
        try:
            parameter = self._selected_edit_parameter()
            target, _message = self._editor_apply_target(seg) if self._is_length_edit_parameter(parameter) else (None, "")
            old = float(dict(target or {}).get("old_value", dict(seg or {}).get("display_span", dict(seg or {}).get("span", 0.0))) or 0.0)
            self.spin_width.setValue(old)
            self.spin_width.setSuffix(f" {self._display_unit_label()}")
            self.spin_width.setEnabled(self._is_length_edit_parameter(parameter) and bool(target))
            if hasattr(self, "lbl_length_value"):
                self.lbl_length_value.setText(self._length_value_label(parameter))
        finally:
            self.spin_width.blockSignals(False)

    def _refresh_editor_slope_control(self, seg):
        if not hasattr(self, "spin_slope"):
            return
        self.spin_slope.blockSignals(True)
        try:
            parameter = self._selected_edit_parameter()
            target, _message = self._editor_apply_target(seg) if self._is_percent_edit_parameter(parameter) else (None, "")
            old = float(dict(target or {}).get("old_slope", dict(target or {}).get("old_value", 0.0)) or 0.0)
            self.spin_slope.setValue(old)
            self.spin_slope.setEnabled(self._is_percent_edit_parameter(parameter) and bool(target))
            if hasattr(self, "lbl_percent_value"):
                self.lbl_percent_value.setText(self._percent_value_label(parameter))
        finally:
            self.spin_slope.blockSignals(False)

    def _refresh_editor_region_policy_control(self, seg):
        if not hasattr(self, "cmb_region_policy"):
            return
        parameter = self._selected_edit_parameter()
        self.cmb_region_policy.blockSignals(True)
        try:
            self.cmb_region_policy.clear()
            if parameter == "region_side_policy":
                side = str(dict(seg or {}).get("side", "") or "").strip().lower()
                options = [
                    ("Inherit / keep", ""),
                    ("Both: stub", "stub"),
                    ("Both: berm", "berm"),
                    ("Both: trim", "trim"),
                    ("Both: wall", "wall"),
                ]
                if side in ("left", "right"):
                    options.extend(
                        [
                            (f"{side.title()}: stub", f"{side}:stub"),
                            (f"{side.title()}: berm", f"{side}:berm"),
                            (f"{side.title()}: trim", f"{side}:trim"),
                            (f"{side.title()}: wall", f"{side}:wall"),
                        ]
                    )
                for label, value in options:
                    self.cmb_region_policy.addItem(label, value)
            elif parameter == "region_daylight_policy":
                side = str(dict(seg or {}).get("side", "") or "").strip().lower()
                options = [("Inherit / daylight on", ""), ("Both: daylight off", "off")]
                if side in ("left", "right"):
                    options.append((f"{side.title()}: daylight off", f"{side}:off"))
                for label, value in options:
                    self.cmb_region_policy.addItem(label, value)
            target, _message = self._ph4_region_policy_target(seg) if parameter.startswith("region_") else (None, "")
            old_policy = str(dict(target or {}).get("old_policy", "") or "")
            idx = self.cmb_region_policy.findData(old_policy)
            if idx >= 0:
                self.cmb_region_policy.setCurrentIndex(idx)
            elif self.cmb_region_policy.count() > 0:
                self.cmb_region_policy.setCurrentIndex(0)
            self.cmb_region_policy.setEnabled(parameter.startswith("region_") and self.cmb_region_policy.count() > 0 and bool(target))
        finally:
            self.cmb_region_policy.blockSignals(False)

    def _refresh_editor_scope_controls(self, force=False):
        payload = dict(getattr(self, "_current_payload", None) or {})
        rows = sorted(
            [dict(row or {}) for row in list(getattr(self, "_station_rows", []) or [])],
            key=lambda row: float(row.get("station", 0.0) or 0.0),
        )
        station = float(payload.get("station", 0.0) or 0.0)
        prev_sta, next_sta = self._station_neighbors(station, rows)
        lo_m, hi_m = self._editor_station_limits(rows=rows, station=station)
        scope = str(self.cmb_edit_scope.currentText() or "")
        suffix = f" {self._display_unit_label()}"

        for spin in (
            self.spin_edit_start_station,
            self.spin_edit_end_station,
            self.spin_transition_in,
            self.spin_transition_out,
        ):
            spin.blockSignals(True)
            try:
                spin.setSuffix(suffix)
                spin.setRange(0.0, max(0.0, self._display_from_meters(hi_m)))
            finally:
                spin.blockSignals(False)

        context_key = (scope, round(station, 6), round(hi_m, 6))
        should_reset = bool(force or getattr(self, "_editor_scope_context_key", None) != context_key)
        if should_reset:
            if scope == "Current Station Only":
                start_m = station
                end_m = station
                tin_m = 0.0
                tout_m = 0.0
            elif scope == "Station Range":
                start_m = station
                end_m = station
                tin_m = 0.0
                tout_m = 0.0
            else:
                start_m = station
                end_m = next_sta if next_sta is not None else station
                tin_m = 0.0
                tout_m = 0.0
            self._set_length_spin_meters(self.spin_edit_start_station, start_m)
            self._set_length_spin_meters(self.spin_edit_end_station, end_m)
            self._set_length_spin_meters(self.spin_transition_in, tin_m)
            self._set_length_spin_meters(self.spin_transition_out, tout_m)

        is_range = scope == "Station Range"
        self.spin_edit_start_station.setEnabled(is_range)
        self.spin_edit_end_station.setEnabled(is_range)
        self.spin_transition_in.setEnabled(is_range)
        self.spin_transition_out.setEnabled(is_range)
        self._editor_scope_context_key = context_key

    def _set_length_spin_meters(self, spin, meters):
        if spin is None:
            return
        spin.blockSignals(True)
        try:
            spin.setValue(max(0.0, self._display_from_meters(float(meters or 0.0))))
        finally:
            spin.blockSignals(False)

    def _length_spin_meters(self, spin):
        return _units.meters_from_user_length(
            self._unit_context(),
            float(spin.value()),
            unit=self._display_unit_label(),
            use_default="display",
        )

    def _station_neighbors(self, station, rows):
        stations = [float(row.get("station", 0.0) or 0.0) for row in list(rows or [])]
        prev_sta = max([s for s in stations if s < station], default=None)
        next_sta = min([s for s in stations if s > station], default=None)
        return prev_sta, next_sta

    def _editor_station_limits(self, rows=None, station=0.0):
        rows = list(rows or [])
        hi_m = max([float(station or 0.0)] + [float(row.get("station", 0.0) or 0.0) for row in rows] + [0.0])
        sec = self._current_section_set()
        if sec is not None:
            try:
                hi_m = max(hi_m, float(getattr(sec, "EndStation", 0.0) or 0.0))
            except Exception:
                pass
            try:
                from freecad.Corridor_Road.objects.obj_section_set import _alignment_total_station_m

                src = getattr(sec, "SourceCenterlineDisplay", None)
                aln = getattr(src, "Alignment", None) if src is not None else None
                hi_m = max(hi_m, float(_alignment_total_station_m(aln) or 0.0))
            except Exception:
                pass
        return 0.0, max(1.0, hi_m)

    def _scope_station_config(self, scope, station, rows, payload):
        prev_sta, next_sta = self._station_neighbors(station, rows)
        start_sta = station
        end_sta = station
        tin = 0.0
        tout = 0.0
        if scope == "Station Range":
            start_sta = self._length_spin_meters(self.spin_edit_start_station)
            end_sta = self._length_spin_meters(self.spin_edit_end_station)
            if end_sta < start_sta:
                start_sta, end_sta = end_sta, start_sta
            tin = max(0.0, self._length_spin_meters(self.spin_transition_in))
            tout = max(0.0, self._length_spin_meters(self.spin_transition_out))
        elif scope == "Current Station Only":
            start_sta = station
            end_sta = station
        else:
            affected_rows = self._affected_station_rows(scope, station, rows, payload, config=None)
            affected_stations = [float(row.get("station", 0.0) or 0.0) for row in affected_rows]
            if affected_stations:
                start_sta = min(affected_stations)
                end_sta = max(affected_stations)
        return {
            "current_station": float(station or 0.0),
            "previous_station": prev_sta,
            "next_station": next_sta,
            "start_station": float(start_sta or 0.0),
            "end_station": float(end_sta or 0.0),
            "transition_in": float(tin or 0.0),
            "transition_out": float(tout or 0.0),
        }

    def _refresh_editor_apply_state(self, *_args):
        if not hasattr(self, "btn_apply_edit"):
            return
        seg = self._current_editor_segment()
        target, message = self._editor_apply_target(seg)
        payload = dict(getattr(self, "_current_payload", None) or {})
        preview_current = self._editor_preview_is_current(seg, payload)
        analysis = self._analyze_editor_impact(seg, payload) if seg and payload else {}
        blocked_lines = list(analysis.get("blocked", []) or [])
        enabled = bool(target) and preview_current and not blocked_lines
        if bool(target) and not preview_current:
            message = "Preview is stale. Run Preview Impact again before applying."
        elif bool(target) and blocked_lines:
            message = str(blocked_lines[0] or "Preview is blocked.")
        self.btn_apply_edit.setEnabled(enabled)
        if hasattr(self, "btn_preview_impact"):
            self.btn_preview_impact.setEnabled(bool(seg) and bool(payload))
        self._refresh_preview_status_label(seg, payload, analysis=analysis)
        conflict = self._editor_conflict_summary(seg, payload)
        resolution_lines = self._conflict_resolution_lines(conflict, seg, payload)
        handoff_lines = self._resolution_handoff_lines(conflict, seg, payload)
        if hasattr(self, "lbl_apply_state"):
            if enabled:
                phase = str(target.get("phase", "PH-4") or "PH-4")
                base = f"{phase} safe apply enabled: {target.get('description', 'edit will be written to the linked source')}."
                if resolution_lines:
                    base += f" {resolution_lines[0]}"
                if handoff_lines:
                    base += f" Next action: {handoff_lines[0]}"
                self.lbl_apply_state.setText(base)
            else:
                base = message or "Safe apply is not available for this target."
                if bool(target) and preview_current and blocked_lines:
                    base = f"Preview blocked: {message}"
                if resolution_lines:
                    base += f" {resolution_lines[0]}"
                if handoff_lines:
                    base += f" Next action: {handoff_lines[0]}"
                self.lbl_apply_state.setText(base)
        self._refresh_resolution_actions(seg, conflict, payload)
        self._refresh_editor_validation(seg=seg, target=target, message=message)
        self._draw_selected_component_overlay()

    def _current_editor_preview_key(self, seg=None, payload=None):
        seg = dict(seg or self._current_editor_segment() or {})
        payload = dict(payload or getattr(self, "_current_payload", None) or {})
        if not seg or not payload:
            return None
        return (
            self._segment_key(seg),
            round(float(payload.get("station", 0.0) or 0.0), 6),
            str(self.cmb_editor_mode.currentText() or ""),
            self._selected_edit_parameter(),
            str(self.cmb_edit_scope.currentText() or ""),
            round(float(self.spin_width.value()) if hasattr(self, "spin_width") else 0.0, 6),
            round(float(self.spin_slope.value()) if hasattr(self, "spin_slope") else 0.0, 6),
            str(self._selected_region_policy_value() or ""),
            round(float(self._length_spin_meters(self.spin_edit_start_station)) if hasattr(self, "spin_edit_start_station") else 0.0, 6),
            round(float(self._length_spin_meters(self.spin_edit_end_station)) if hasattr(self, "spin_edit_end_station") else 0.0, 6),
            round(float(self._length_spin_meters(self.spin_transition_in)) if hasattr(self, "spin_transition_in") else 0.0, 6),
            round(float(self._length_spin_meters(self.spin_transition_out)) if hasattr(self, "spin_transition_out") else 0.0, 6),
        )

    def _editor_preview_is_current(self, seg=None, payload=None):
        key = self._current_editor_preview_key(seg, payload)
        return bool(self._editor_preview_current and key is not None and key == self._editor_preview_key)

    def _preview_stale_text(self, seg=None, reason=""):
        lines = ["Preview is stale. Run Preview Impact again before applying."]
        if seg:
            lines.append(f"Target: {self._segment_label(seg)}")
        row = str(reason or self._editor_preview_reason or "").strip()
        if row:
            lines.append(f"Reason: {row}")
        return "\n".join(lines)

    def _set_editor_preview_stale(self, seg=None, payload=None, reason=""):
        self._editor_preview_current = False
        self._editor_preview_key = None
        self._editor_preview_reason = str(reason or "").strip()
        if hasattr(self, "txt_impact"):
            if seg:
                self.txt_impact.setPlainText(self._preview_stale_text(seg, reason=reason))
            elif not str(self.txt_impact.toPlainText() or "").strip():
                self.txt_impact.setPlainText("No selected edit target.")
        self._refresh_preview_status_label(seg, payload, analysis=None)

    def _invalidate_editor_preview(self, reason=""):
        seg = self._current_editor_segment()
        payload = dict(getattr(self, "_current_payload", None) or {})
        self._set_editor_preview_stale(seg, payload, reason)

    def _run_editor_impact_preview(self, *_args):
        self._refresh_editor_impact()

    def _source_owner_label(self, seg):
        scope = self._component_scope(seg)
        source = str(seg.get("source", "") or "").strip().lower()
        if source in ("cross_section_edit", "edit_plan", "crosssectioneditplan"):
            return "CrossSectionEditPlan override"
        if scope == "typical":
            return "TypicalSectionTemplate / AssemblyTemplate"
        if scope == "side_slope":
            return "RegionPlan roadside or side-slope policy"
        if scope == "daylight":
            return "RegionPlan daylight policy / terrain daylight resolver"
        if source:
            return source
        return "Unresolved generated component source"

    def _segment_generated_row(self, seg):
        return self._segment_pipe_row(seg, include_display=False)

    def _segment_raw_preview(self, seg):
        source = str(seg.get("source", "") or "").strip()
        if source:
            return f"{self._segment_pipe_row(seg, include_display=True)}|source={source}"
        return self._segment_pipe_row(seg, include_display=True)

    def _segment_pipe_row(self, seg, include_display=False):
        parts = [
            "kind=component_segment",
            f"id={str(seg.get('id', '-') or '-')}",
            f"type={str(seg.get('type', '-') or '-')}",
            f"shape={str(seg.get('shape', '-') or '-')}",
            f"side={str(seg.get('side', '-') or '-')}",
            f"scope={self._component_scope(seg)}",
            f"x0={float(seg.get('x0', 0.0) or 0.0):.3f}",
            f"x1={float(seg.get('x1', 0.0) or 0.0):.3f}",
            f"span={float(seg.get('span', 0.0) or 0.0):.3f}",
            f"order={str(seg.get('order', '-') or '-')}",
        ]
        if include_display:
            parts.append(f"displaySpan={float(seg.get('display_span', seg.get('span', 0.0)) or 0.0):.3f}{self._display_unit_label()}")
        return "|".join(parts)

    def _refresh_editor_impact(self, *_args):
        if not hasattr(self, "txt_impact"):
            return
        seg = self._current_editor_segment()
        payload = dict(getattr(self, "_current_payload", None) or {})
        if not seg or not payload:
            self._set_editor_preview_stale(None, {}, "")
            self.txt_impact.setPlainText("No selected edit target.")
            return
        analysis = self._analyze_editor_impact(seg, payload)
        warnings = list(analysis.get("warnings", []) or [])
        blocked = list(analysis.get("blocked", []) or [])
        resolution = list(analysis.get("resolution_lines", []) or [])
        actions = list(analysis.get("resolution_action_lines", []) or [])
        handoff = list(analysis.get("handoff_lines", []) or [])
        lines = [
            "Cross Section Editor impact analysis.",
            f"Target: {self._segment_label(seg)}",
            f"Parameter class: {analysis.get('parameter_class', '-')}",
            f"Requested scope: {analysis.get('scope', '-')}",
            f"Affected range: {analysis.get('range_text', '-')}",
            f"Transition: {analysis.get('transition_text', '-')}",
            f"Affected stations: {analysis.get('station_count', 0)}",
            f"Timeline: {analysis.get('timeline_text', '-')}",
            f"Boundary stations to add: {analysis.get('boundary_text', '-')}",
            f"Region owner: {analysis.get('region_owner', '-')}",
            f"Structure overlap: {analysis.get('structure_overlap', '-')}",
            f"Downstream: {analysis.get('downstream', '-')}",
            self._impact_apply_state_text(seg),
        ]
        station_preview = list(analysis.get("station_preview_lines", []) or [])
        boundary_roles = list(analysis.get("boundary_role_lines", []) or [])
        transition_preview = list(analysis.get("transition_preview_lines", []) or [])
        before_after_preview = list(analysis.get("before_after_preview_lines", []) or [])
        if station_preview:
            lines.extend(["", "Station preview:"])
            lines.extend(f"- {row}" for row in station_preview)
        if boundary_roles:
            lines.extend(["", "Boundary roles:"])
            lines.extend(f"- {row}" for row in boundary_roles)
        if transition_preview:
            lines.extend(["", "Transition preview:"])
            lines.extend(f"- {row}" for row in transition_preview)
        if before_after_preview:
            lines.extend(["", "Before / after samples:"])
            lines.extend(f"- {row}" for row in before_after_preview)
        if blocked:
            lines.extend(["", "Blocked:"])
            lines.extend(f"- {w}" for w in blocked)
        if warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {w}" for w in warnings)
        if resolution:
            lines.extend(["", "Resolution:"])
            lines.extend(f"- {w}" for w in resolution)
        if handoff:
            lines.extend(["", "Policy handoff:"])
            lines.extend(f"- {w}" for w in handoff)
        if actions:
            lines.extend(["", "Available actions:"])
            lines.extend(f"- {w}" for w in actions)
        self.txt_impact.setPlainText("\n".join(lines))
        self._editor_preview_current = True
        self._editor_preview_key = self._current_editor_preview_key(seg, payload)
        self._editor_preview_reason = ""
        self._refresh_preview_status_label(seg, payload, analysis=analysis)
        self._refresh_editor_apply_state()

    def _refresh_preview_status_label(self, seg=None, payload=None, analysis=None):
        seg = dict(seg or self._current_editor_segment() or {})
        payload = dict(payload or getattr(self, "_current_payload", None) or {})
        text = "Preview: no target."
        btn_text = "Preview Impact"
        if seg and payload:
            if analysis is None and self._editor_preview_is_current(seg, payload):
                analysis = self._analyze_editor_impact(seg, payload)
            blocked_lines = list(dict(analysis or {}).get("blocked", []) or [])
            if self._editor_preview_is_current(seg, payload):
                if blocked_lines:
                    text = f"Preview: blocked. {str(blocked_lines[0] or 'Resolve blocked items before applying.')}"
                    btn_text = "Preview Impact (Blocked)"
                else:
                    text = "Preview: current. Apply can proceed for the current editor state."
                    btn_text = "Preview Impact (Current)"
            else:
                reason = str(self._editor_preview_reason or "").strip()
                text = "Preview: stale. Run Preview Impact again before applying."
                if reason:
                    text += f" {reason}"
                btn_text = "Preview Impact (Stale)"
        if hasattr(self, "lbl_preview_state"):
            self.lbl_preview_state.setText(text)
        if hasattr(self, "btn_preview_impact"):
            self.btn_preview_impact.setText(btn_text)

    def _impact_apply_state_text(self, seg):
        target, message = self._editor_apply_target(seg)
        if target:
            phase = str(target.get("phase", "PH-4") or "PH-4")
            return f"Apply: enabled for guarded {phase} path ({target.get('description', 'source edit')})."
        return f"Apply: disabled - {message or 'Safe apply is not available for this target.'}"

    def _analyze_editor_impact(self, seg, payload):
        station = float(payload.get("station", 0.0) or 0.0)
        scope = str(self.cmb_edit_scope.currentText() or "")
        rows = sorted(
            [dict(row or {}) for row in list(getattr(self, "_station_rows", []) or [])],
            key=lambda row: float(row.get("station", 0.0) or 0.0),
        )
        if not rows:
            rows = [{"station": station, "region_summary": str(payload.get("region_summary", "") or ""), "has_structure": bool(payload.get("has_structure", False)), "structure_summary": str(payload.get("structure_summary", "") or "")}]
        scope_config = self._scope_station_config(scope, station, rows, payload)
        affected_rows = self._affected_station_rows(scope, station, rows, payload, config=scope_config)
        affected_stations = [float(row.get("station", 0.0) or 0.0) for row in affected_rows]
        prev_sta = scope_config.get("previous_station")
        next_sta = scope_config.get("next_station")
        start_sta = float(scope_config.get("start_station", station) or station)
        end_sta = float(scope_config.get("end_station", station) or station)
        transition_in = float(scope_config.get("transition_in", 0.0) or 0.0)
        transition_out = float(scope_config.get("transition_out", 0.0) or 0.0)
        region_owner = self._impact_region_owner(payload, affected_rows)
        structure_overlap = self._impact_structure_overlap(payload, affected_rows)
        parameter_class = self._parameter_class(seg)
        target, _target_message = self._editor_apply_target(seg)
        conflict = self._editor_conflict_summary(seg, payload)
        resolution_lines = self._conflict_resolution_lines(conflict, seg, payload)
        action_specs = self._resolution_action_specs(conflict, seg, payload)
        resolution_action_lines = [str(spec.get("label", "") or "").strip() for spec in action_specs if str(spec.get("label", "") or "").strip()]
        handoff_lines = self._resolution_handoff_lines(conflict, seg, payload, action_specs=action_specs)
        warnings = []
        blocked = []
        if scope == "Current Station Only" and parameter_class in ("geometry", "topology", "daylight"):
            warnings.append(
                self._impact_station_only_warning(prev_sta, station, next_sta)
            )
        if scope == "Station Range" and abs(end_sta - start_sta) <= 1e-6:
            warnings.append("Station range is currently zero-length; widen the range or use Current Station Only.")
        if structure_overlap != "none":
            warnings.append("Structure overlap should be reviewed before applying geometry edits.")
        if parameter_class == "daylight" and structure_overlap != "none":
            blocked.append("Daylight edits that overlap structures require structure/region policy handling before apply.")
        boundary_stations = self._impact_boundary_stations(
            scope,
            start_sta,
            end_sta,
            prev_sta,
            next_sta,
            transition_in=transition_in,
            transition_out=transition_out,
        )
        missing_boundary_stations = self._impact_missing_boundary_stations(rows, boundary_stations)
        if missing_boundary_stations:
            warnings.append(
                "Boundary stations missing from current sampling will be injected: "
                + ", ".join(self._fmt_station(sta) for sta in missing_boundary_stations)
            )
        continuity_warnings = self._impact_range_continuity_warnings(
            scope,
            parameter_class,
            rows,
            start_sta,
            end_sta,
            transition_in=transition_in,
            transition_out=transition_out,
        )
        warnings.extend(continuity_warnings)
        return {
            "scope": scope,
            "parameter_class": parameter_class,
            "station_count": len(affected_stations),
            "range_text": f"{self._fmt_station(start_sta)} -> {self._fmt_station(end_sta)}",
            "transition_text": f"{self._format_display_length(transition_in)} / {self._format_display_length(transition_out)} {self._display_unit_label()}",
            "timeline_text": self._impact_timeline(prev_sta, station, next_sta),
            "boundary_text": ", ".join(self._fmt_station(s) for s in boundary_stations) if boundary_stations else "-",
            "station_preview_lines": self._impact_station_preview_lines(
                scope,
                station,
                rows,
                affected_rows,
                start_sta,
                end_sta,
                transition_in=transition_in,
                transition_out=transition_out,
            ),
            "boundary_role_lines": self._impact_boundary_role_lines(
                scope,
                start_sta,
                end_sta,
                transition_in=transition_in,
                transition_out=transition_out,
            ),
            "transition_preview_lines": self._impact_transition_preview_lines(
                scope,
                station,
                target if isinstance(target, dict) else None,
                start_sta,
                end_sta,
                transition_in=transition_in,
                transition_out=transition_out,
            ),
            "before_after_preview_lines": self._impact_before_after_preview_lines(
                scope,
                station,
                rows,
                target if isinstance(target, dict) else None,
                start_sta,
                end_sta,
                transition_in=transition_in,
                transition_out=transition_out,
            ),
            "region_owner": region_owner,
            "structure_overlap": structure_overlap,
            "downstream": self._impact_downstream_text(parameter_class),
            "warnings": warnings,
            "blocked": blocked,
            "resolution_lines": resolution_lines,
            "resolution_action_lines": resolution_action_lines,
            "handoff_lines": handoff_lines,
        }

    def _affected_station_rows(self, scope, station, rows, payload, config=None):
        if scope == "Global Source":
            return list(rows)
        if scope == "Current Station Only":
            return [self._nearest_station_row(station, rows, payload)]
        if scope == "Station Range":
            cfg = dict(config or self._scope_station_config(scope, station, rows, payload) or {})
            start_sta = float(cfg.get("start_station", station) or station)
            end_sta = float(cfg.get("end_station", station) or station)
            matched = [
                row
                for row in rows
                if start_sta - 1e-6 <= float(row.get("station", 0.0) or 0.0) <= end_sta + 1e-6
            ]
            return matched if matched else [self._nearest_station_row(station, rows, payload)]
        return self._active_region_rows(station, rows, payload)

    def _nearest_station_row(self, station, rows, payload):
        if not rows:
            return dict(payload or {})
        return min(rows, key=lambda row: abs(float(row.get("station", 0.0) or 0.0) - station))

    def _active_region_rows(self, station, rows, payload):
        current = self._nearest_station_row(station, rows, payload)
        current_key = self._region_key(current, payload)
        if not current_key:
            return [current]
        current_idx = rows.index(current)
        start_idx = current_idx
        while start_idx > 0 and self._region_key(rows[start_idx - 1], payload) == current_key:
            start_idx -= 1
        end_idx = current_idx
        while end_idx + 1 < len(rows) and self._region_key(rows[end_idx + 1], payload) == current_key:
            end_idx += 1
        return list(rows[start_idx : end_idx + 1])

    def _region_key(self, row, payload):
        summary = str(row.get("region_summary", "") or "").strip()
        if summary:
            return summary
        return str(payload.get("region_summary", "") or payload.get("base_region_id", "") or "").strip()

    def _impact_region_owner(self, payload, affected_rows):
        base = str(payload.get("base_region_id", "") or "").strip()
        summary = str(payload.get("region_summary", "") or "").strip()
        if base and summary:
            return f"{base} ({summary})"
        if base or summary:
            return base or summary
        row_summaries = sorted({str(row.get("region_summary", "") or "").strip() for row in affected_rows if str(row.get("region_summary", "") or "").strip()})
        return ", ".join(row_summaries) if row_summaries else "-"

    def _impact_structure_overlap(self, payload, affected_rows):
        items = []
        current_ids = [str(v or "").strip() for v in list(payload.get("structure_ids", []) or []) if str(v or "").strip()]
        if current_ids:
            items.extend(current_ids)
        for row in affected_rows:
            if not bool(row.get("has_structure", False)):
                continue
            summary = str(row.get("structure_summary", "") or "").strip()
            items.append(summary or self._fmt_station(float(row.get("station", 0.0) or 0.0)))
        unique = []
        for item in items:
            if item and item not in unique:
                unique.append(item)
        return ", ".join(unique) if unique else "none"

    def _parameter_class(self, seg):
        scope = self._component_scope(seg)
        typ = str(seg.get("type", "") or "").strip().lower()
        if scope == "daylight" or typ == "daylight":
            return "daylight"
        if typ in ("bench", "ditch", "cut_slope", "fill_slope", "side_slope"):
            return "topology"
        return "geometry"

    def _impact_boundary_stations(self, scope, start_sta, end_sta, prev_sta, next_sta, transition_in=0.0, transition_out=0.0):
        if scope == "Global Source":
            return []
        if scope == "Current Station Only":
            return []
        out = [start_sta, end_sta]
        if scope == "Station Range":
            if transition_in > 1e-9:
                out.insert(0, max(0.0, float(start_sta) - float(transition_in)))
            if transition_out > 1e-9:
                out.append(float(end_sta) + float(transition_out))
        unique = []
        for sta in out:
            if not any(abs(float(sta) - float(v)) <= 1e-6 for v in unique):
                unique.append(float(sta))
        return unique

    def _impact_timeline(self, prev_sta, station, next_sta):
        parts = []
        parts.append(self._fmt_station(prev_sta) if prev_sta is not None else "-")
        parts.append(f"{self._fmt_station(station)}*")
        parts.append(self._fmt_station(next_sta) if next_sta is not None else "-")
        return " | ".join(parts)

    def _previous_station_value(self, rows, station):
        matches = [float(row.get("station", 0.0) or 0.0) for row in rows if float(row.get("station", 0.0) or 0.0) < float(station) - 1.0e-6]
        return max(matches) if matches else None

    def _next_station_value(self, rows, station):
        matches = [float(row.get("station", 0.0) or 0.0) for row in rows if float(row.get("station", 0.0) or 0.0) > float(station) + 1.0e-6]
        return min(matches) if matches else None

    def _impact_station_list_text(self, stations, limit=5):
        vals = []
        for sta in list(stations or []):
            if sta is None:
                continue
            fsta = float(sta)
            if any(abs(fsta - seen) <= 1.0e-6 for seen in vals):
                continue
            vals.append(fsta)
        if not vals:
            return "-"
        if len(vals) <= limit:
            return ", ".join(self._fmt_station(sta) for sta in vals)
        head = ", ".join(self._fmt_station(sta) for sta in vals[:limit])
        return f"{head}, ... ({len(vals)} total)"

    def _impact_station_preview_lines(self, scope, station, rows, affected_rows, start_sta, end_sta, transition_in=0.0, transition_out=0.0):
        if scope == "Global Source":
            return ["All resolved section stations will refresh."]
        current_row = self._nearest_station_row(station, rows, {})
        current_sta = float(current_row.get("station", station) or station)
        lines = []
        before_sta = self._previous_station_value(rows, start_sta)
        after_sta = self._next_station_value(rows, end_sta)
        if before_sta is not None:
            lines.append(f"adjacent before: {self._fmt_station(before_sta)} unchanged")
        if scope == "Station Range" and transition_in > 1.0e-9:
            lines.append(f"transition-in start: {self._fmt_station(max(0.0, start_sta - transition_in))} boundary")
        if scope in ("Station Range", "Active Region"):
            lines.append(f"range start: {self._fmt_station(start_sta)} boundary")
        lines.append(f"current selection: {self._fmt_station(current_sta)}")
        affected_stations = [float(row.get("station", 0.0) or 0.0) for row in list(affected_rows or [])]
        interior = [sta for sta in affected_stations if sta > start_sta + 1.0e-6 and sta < end_sta - 1.0e-6 and abs(sta - current_sta) > 1.0e-6]
        if interior:
            lines.append(f"interior affected: {self._impact_station_list_text(interior, limit=3)}")
        if scope in ("Station Range", "Active Region"):
            lines.append(f"range end: {self._fmt_station(end_sta)} boundary")
        if scope == "Station Range" and transition_out > 1.0e-9:
            lines.append(f"transition-out end: {self._fmt_station(end_sta + transition_out)} boundary")
        if after_sta is not None:
            lines.append(f"adjacent after: {self._fmt_station(after_sta)} unchanged")
        return lines

    def _impact_boundary_role_lines(self, scope, start_sta, end_sta, transition_in=0.0, transition_out=0.0):
        if scope not in ("Station Range", "Active Region"):
            return []
        lines = [f"{self._fmt_station(start_sta)} -> range start", f"{self._fmt_station(end_sta)} -> range end"]
        if scope == "Station Range" and transition_in > 1.0e-9:
            lines.insert(0, f"{self._fmt_station(max(0.0, start_sta - transition_in))} -> transition-in start")
        if scope == "Station Range" and transition_out > 1.0e-9:
            lines.append(f"{self._fmt_station(end_sta + transition_out)} -> transition-out end")
        return lines

    def _impact_missing_boundary_stations(self, rows, boundary_stations):
        if not rows or not boundary_stations:
            return []
        existing = [float(row.get("station", 0.0) or 0.0) for row in rows]
        missing = []
        for sta in boundary_stations:
            fsta = float(sta or 0.0)
            if any(abs(fsta - cur) <= 1.0e-6 for cur in existing):
                continue
            missing.append(fsta)
        return missing

    def _impact_station_only_warning(self, prev_sta, station, next_sta):
        neighbors = [sta for sta in (prev_sta, station, next_sta) if sta is not None]
        if len(neighbors) >= 2:
            return (
                "Station-only geometry edits can create abrupt corridor geometry between "
                + ", ".join(self._fmt_station(sta) for sta in neighbors)
                + "."
            )
        return "Station-only geometry edits can create abrupt corridor geometry."

    def _impact_range_continuity_warnings(self, scope, parameter_class, rows, start_sta, end_sta, transition_in=0.0, transition_out=0.0):
        if scope != "Station Range" or parameter_class not in ("geometry", "topology", "daylight"):
            return []
        warnings = []
        before_sta = self._previous_station_value(rows, start_sta)
        after_sta = self._next_station_value(rows, end_sta)
        if transition_in <= 1.0e-9 and before_sta is not None:
            warnings.append(
                f"Transition-in is 0; geometry may kink at the start boundary between {self._fmt_station(before_sta)} and {self._fmt_station(start_sta)}."
            )
        if transition_out <= 1.0e-9 and after_sta is not None:
            warnings.append(
                f"Transition-out is 0; geometry may kink at the end boundary between {self._fmt_station(end_sta)} and {self._fmt_station(after_sta)}."
            )
        return warnings

    @staticmethod
    def _impact_parameter_label(parameter: str) -> str:
        key = str(parameter or "").strip().lower()
        labels = {
            "width": "Width",
            "slope_pct": "Slope %",
            "cross_slope_pct": "Slope %",
            "height": "Height",
            "extra_width": "Extra Width",
            "back_slope_pct": "Back Slope %",
        }
        return labels.get(key, key or "Value")

    def _impact_parameter_value_text(self, value, unit: str):
        fval = float(value or 0.0)
        if str(unit or "").strip().lower() == "pct":
            return f"{fval:.3f} %"
        return f"{self._format_display_length(fval)} {self._display_unit_label()}"

    @staticmethod
    def _impact_transition_factor(station, start_sta, end_sta, transition_in=0.0, transition_out=0.0):
        sta = float(station or 0.0)
        start = float(start_sta or 0.0)
        end = float(end_sta or start)
        tin = max(0.0, float(transition_in or 0.0))
        tout = max(0.0, float(transition_out or 0.0))
        if sta < start - 1.0e-9:
            if tin <= 1.0e-9:
                return 0.0
            raw = (sta - (start - tin)) / tin
            return max(0.0, min(1.0, raw))
        if sta <= end + 1.0e-9:
            return 1.0
        if tout <= 1.0e-9:
            return 0.0
        raw = (sta - end) / tout
        return max(0.0, min(1.0, 1.0 - raw))

    def _impact_transition_value(self, old_value, new_value, factor):
        base = float(old_value or 0.0)
        target = float(new_value or 0.0)
        t = max(0.0, min(1.0, float(factor or 0.0)))
        return base + ((target - base) * t)

    @staticmethod
    def _impact_effect_role(station, start_sta, end_sta, transition_in=0.0, transition_out=0.0):
        sta = float(station or 0.0)
        start = float(start_sta or 0.0)
        end = float(end_sta or start)
        tin = max(0.0, float(transition_in or 0.0))
        tout = max(0.0, float(transition_out or 0.0))
        effective_start = max(0.0, start - tin)
        effective_end = end + tout
        if sta < effective_start - 1.0e-9 or sta > effective_end + 1.0e-9:
            return "unchanged"
        if sta < start - 1.0e-9:
            return "transition-in"
        if sta <= end + 1.0e-9:
            return "range-core"
        return "transition-out"

    def _impact_delta_text(self, before_value, after_value, unit: str):
        delta = float(after_value or 0.0) - float(before_value or 0.0)
        sign = "+" if delta >= 0.0 else "-"
        return f"{sign}{self._impact_parameter_value_text(abs(delta), unit)}"

    def _impact_before_after_sample_stations(self, station, rows, start_sta, end_sta, transition_in=0.0, transition_out=0.0):
        vals = []

        def _push(value):
            if value is None:
                return
            fval = float(value)
            if any(abs(fval - cur) <= 1.0e-6 for cur in vals):
                return
            vals.append(fval)

        effective_start = max(0.0, float(start_sta) - max(0.0, float(transition_in or 0.0)))
        effective_end = float(end_sta) + max(0.0, float(transition_out or 0.0))
        _push(self._previous_station_value(rows, effective_start))
        if transition_in > 1.0e-9:
            _push(effective_start)
            _push((effective_start + float(start_sta)) * 0.5)
        _push(float(start_sta))
        if abs(float(end_sta) - float(start_sta)) > 1.0e-6:
            _push((float(start_sta) + float(end_sta)) * 0.5)
        _push(float(station))
        _push(float(end_sta))
        if transition_out > 1.0e-9:
            _push(float(end_sta) + (float(transition_out) * 0.5))
            _push(effective_end)
        _push(self._next_station_value(rows, effective_end))
        return vals

    def _impact_before_after_preview_lines(self, scope, station, rows, target, start_sta, end_sta, transition_in=0.0, transition_out=0.0):
        if scope != "Station Range" or not isinstance(target, dict):
            return []
        old_value = float(target.get("old_value", 0.0) or 0.0)
        new_value = float(target.get("value", old_value) or old_value)
        unit = str(target.get("unit", "") or "")
        samples = self._impact_before_after_sample_stations(
            station,
            rows,
            start_sta,
            end_sta,
            transition_in=transition_in,
            transition_out=transition_out,
        )
        lines = []
        for sta in samples:
            factor = self._impact_transition_factor(
                sta,
                start_sta,
                end_sta,
                transition_in=transition_in,
                transition_out=transition_out,
            )
            before_value = old_value
            after_value = self._impact_transition_value(old_value, new_value, factor)
            role = self._impact_effect_role(
                sta,
                start_sta,
                end_sta,
                transition_in=transition_in,
                transition_out=transition_out,
            )
            lines.append(
                f"{self._fmt_station(sta)} | before {self._impact_parameter_value_text(before_value, unit)} | "
                f"after {self._impact_parameter_value_text(after_value, unit)} | "
                f"{self._impact_delta_text(before_value, after_value, unit)} | {role}"
            )
        return lines

    def _impact_transition_preview_lines(self, scope, station, target, start_sta, end_sta, transition_in=0.0, transition_out=0.0):
        if scope != "Station Range" or not isinstance(target, dict):
            return []
        old_value = float(target.get("old_value", 0.0) or 0.0)
        new_value = float(target.get("value", old_value) or old_value)
        unit = str(target.get("unit", "") or "")
        parameter = str(target.get("parameter", "") or "")
        if not math.isfinite(old_value) or not math.isfinite(new_value):
            return []
        label = self._impact_parameter_label(parameter)
        delta = new_value - old_value
        delta_text = self._impact_parameter_value_text(abs(delta), unit)
        direction = "+" if delta >= 0.0 else "-"
        lines = [
            f"{label}: {self._impact_parameter_value_text(old_value, unit)} -> {self._impact_parameter_value_text(new_value, unit)} ({direction}{delta_text})"
        ]
        if transition_in <= 1.0e-9 and transition_out <= 1.0e-9:
            lines.append("No transition interpolation; override switches at the range boundaries.")
        else:
            if transition_in > 1.0e-9:
                ti_start = max(0.0, float(start_sta) - float(transition_in))
                lines.append(
                    f"transition-in start: {self._fmt_station(ti_start)} -> "
                    f"{self._impact_parameter_value_text(old_value, unit)} (0%)"
                )
                ti_mid = (ti_start + float(start_sta)) * 0.5
                lines.append(
                    f"transition-in midpoint: {self._fmt_station(ti_mid)} -> "
                    f"{self._impact_parameter_value_text(self._impact_transition_value(old_value, new_value, 0.5), unit)} (50%)"
                )
                lines.append(
                    f"transition-in end: {self._fmt_station(start_sta)} -> "
                    f"{self._impact_parameter_value_text(new_value, unit)} (100%)"
                )
            if transition_out > 1.0e-9:
                to_mid = float(end_sta) + (float(transition_out) * 0.5)
                lines.append(
                    f"transition-out midpoint: {self._fmt_station(to_mid)} -> "
                    f"{self._impact_parameter_value_text(self._impact_transition_value(old_value, new_value, 0.5), unit)} (50%)"
                )
                lines.append(
                    f"transition-out end: {self._fmt_station(float(end_sta) + float(transition_out))} -> "
                    f"{self._impact_parameter_value_text(old_value, unit)} (0%)"
                )
        lines.append(
            f"range core: {self._fmt_station(start_sta)} -> {self._fmt_station(end_sta)} uses {self._impact_parameter_value_text(new_value, unit)}"
        )
        factor = self._impact_transition_factor(
            station,
            start_sta,
            end_sta,
            transition_in=transition_in,
            transition_out=transition_out,
        )
        current_value = self._impact_transition_value(old_value, new_value, factor)
        lines.append(
            f"current station blend: {self._fmt_station(station)} -> "
            f"{self._impact_parameter_value_text(current_value, unit)} ({factor * 100.0:.0f}%)"
        )
        return lines

    def _impact_downstream_text(self, parameter_class):
        sec = self._current_section_set()
        deps = self._downstream_dependents(sec)
        if parameter_class in ("geometry", "topology", "daylight"):
            if deps:
                return f"SectionSet recompute required; {len(deps)} downstream output(s) will be marked stale after apply."
            return "SectionSet recompute required; no downstream output is linked yet."
        return "SectionSet refresh required."

    def _downstream_dependents(self, sec):
        if sec is None:
            return []
        doc = getattr(sec, "Document", None) or self.doc
        if doc is None:
            return []
        direct = []
        secondary = []
        for obj in list(getattr(doc, "Objects", []) or []):
            if obj is sec:
                continue
            try:
                if getattr(obj, "SourceSectionSet", None) == sec:
                    direct.append(obj)
            except Exception:
                continue
        for src in direct:
            for obj in list(getattr(doc, "Objects", []) or []):
                if obj in direct or obj is sec:
                    continue
                try:
                    if getattr(obj, "SourceCorridor", None) == src:
                        secondary.append(obj)
                        continue
                except Exception:
                    pass
                try:
                    if getattr(obj, "SourceDesignSurface", None) == src:
                        secondary.append(obj)
                except Exception:
                    pass
        out = []
        seen = set()
        for obj in list(direct) + list(secondary):
            key = getattr(obj, "Name", id(obj))
            if key in seen:
                continue
            seen.add(key)
            out.append(obj)
        return out

    def _downstream_validation_rows(self, sec):
        deps = self._downstream_dependents(sec)
        if not deps:
            return [
                "validation|phase=PH-4|level=info|code=downstream|"
                "count=0|message=No linked downstream outputs were found."
            ]
        names = ",".join(str(getattr(obj, "Name", "") or "-") for obj in deps[:8])
        more = max(0, len(deps) - 8)
        suffix = f"|more={more}" if more else ""
        return [
            "validation|phase=PH-4|level=warn|code=downstream_stale|"
            f"count={len(deps)}|objects={names}{suffix}|message=Linked downstream outputs will need recompute after apply."
        ]

    def _mark_downstream_dependents_stale(self, sec):
        marked = []
        for obj in self._downstream_dependents(sec):
            try:
                proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
                hide_status = proxy_type == "Corridor"
                if hasattr(obj, "NeedsRecompute"):
                    obj.NeedsRecompute = True
                if not hide_status:
                    status = str(getattr(obj, "Status", "") or "")
                    if hasattr(obj, "Status") and "NEEDS_RECOMPUTE" not in status:
                        obj.Status = "NEEDS_RECOMPUTE: Source SectionSet changed."
                    label = str(getattr(obj, "Label", "") or "")
                    if hasattr(obj, "Label") and " [Recompute]" not in label:
                        obj.Label = f"{label} [Recompute]"
                try:
                    obj.touch()
                except Exception:
                    pass
                marked.append(obj)
            except Exception:
                continue
        return marked

    def _fmt_station(self, station):
        return f"STA {self._format_display_length(float(station or 0.0))} {self._display_unit_label()}"

    def _selected_edit_parameter(self):
        text = "Width"
        if hasattr(self, "cmb_edit_parameter"):
            text = str(self.cmb_edit_parameter.currentText() or "Width")
        lower = text.strip().lower()
        if lower.startswith("back slope"):
            return "back_slope"
        if lower.startswith("slope"):
            return "slope"
        if lower.startswith("height"):
            return "height"
        if lower.startswith("extra width"):
            return "extra_width"
        if "side policy" in lower:
            return "region_side_policy"
        if "daylight policy" in lower:
            return "region_daylight_policy"
        return "width"

    @staticmethod
    def _is_length_edit_parameter(parameter: str) -> bool:
        return str(parameter or "").strip().lower() in ("width", "height", "extra_width")

    @staticmethod
    def _is_width_like_parameter(parameter: str) -> bool:
        return str(parameter or "").strip().lower() in ("width", "extra_width")

    @staticmethod
    def _is_percent_edit_parameter(parameter: str) -> bool:
        return str(parameter or "").strip().lower() in ("slope", "back_slope")

    @staticmethod
    def _length_value_label(parameter: str) -> str:
        key = str(parameter or "").strip().lower()
        if key == "height":
            return "Height Value"
        if key == "extra_width":
            return "Extra Width Value"
        return "Width Value"

    @staticmethod
    def _percent_value_label(parameter: str) -> str:
        key = str(parameter or "").strip().lower()
        if key == "back_slope":
            return "Back Slope Value"
        return "Slope Value"

    def _resolved_typical_component_row(self, sec, seg):
        if sec is None or seg is None:
            return {}
        typ_obj = getattr(sec, "TypicalSectionTemplate", None)
        if typ_obj is None or not bool(getattr(sec, "UseTypicalSectionTemplate", False)):
            return {}
        try:
            from freecad.Corridor_Road.objects.obj_section_set import SectionSet

            payload = dict(getattr(self, "_current_payload", None) or {})
            station = float(payload.get("station", 0.0) or 0.0)
            runtime_ctx = SectionSet._cross_section_edit_context_at_station(sec, station)
            rows, _changed = SectionSet._resolve_typical_component_rows(typ_obj, runtime_context=runtime_ctx)
        except Exception:
            return {}
        target_id = str(dict(seg or {}).get("id", "") or "").strip().upper()
        target_side = str(dict(seg or {}).get("side", "") or "").strip().lower()
        target_type = str(dict(seg or {}).get("type", "") or "").strip().lower()
        for row in list(rows or []):
            item = dict(row or {})
            if str(item.get("Id", "") or "").strip().upper() != target_id:
                continue
            row_side = str(item.get("Side", "") or "").strip().lower()
            if target_side and row_side not in (target_side, "both"):
                continue
            row_type = str(item.get("Type", "") or "").strip().lower()
            if target_type and row_type != target_type:
                continue
            return item
        return {}

    def _selected_region_policy_value(self):
        if not hasattr(self, "cmb_region_policy"):
            return ""
        try:
            data = self.cmb_region_policy.currentData()
            if data is not None:
                return str(data or "")
        except Exception:
            pass
        return str(self.cmb_region_policy.currentText() or "").strip()

    def _editor_apply_target(self, seg):
        scope = str(self.cmb_edit_scope.currentText() or "")
        if scope in ("Station Range", "Current Station Only"):
            return self._ph5_edit_plan_target(seg)
        return self._ph4_edit_target(seg)

    def _ph4_edit_target(self, seg):
        parameter = self._selected_edit_parameter()
        if parameter == "slope":
            return self._ph4_slope_target(seg)
        if parameter.startswith("region_"):
            return self._ph4_region_policy_target(seg)
        return self._ph4_width_target(seg)

    def _ph5_edit_plan_target(self, seg):
        if not seg:
            return None, "Select a component target first."
        sec = self._current_section_set()
        if sec is None:
            return None, "No SectionSet is selected."
        parameter = self._selected_edit_parameter()
        if parameter not in ("width", "slope", "height", "extra_width", "back_slope"):
            return None, "PH-5 edit-plan apply currently supports Width, Slope %, Height, Extra Width, and Back Slope % only."
        scope = str(self.cmb_edit_scope.currentText() or "")
        if scope not in ("Station Range", "Current Station Only"):
            return None, "PH-5 edit-plan apply only supports Station Range or Current Station Only."
        source_scope = self._component_scope(seg)
        target_type = str(seg.get("type", "") or "").strip().lower()
        side = str(seg.get("side", "") or "").strip().lower()
        target_id = str(seg.get("id", "") or "").strip().upper()
        order = int(float(seg.get("order", 0) or 0))
        if source_scope == "side_slope":
            if target_type not in ("side_slope", "cut_slope", "fill_slope"):
                return None, "PH-5 edit-plan apply currently supports side-slope targets only."
            if side not in ("left", "right"):
                return None, "PH-5 edit-plan apply requires a left or right side target."
            if target_id not in ("L10", "R10"):
                if order == 10:
                    target_id = "L10" if side == "left" else "R10"
                else:
                    return None, "PH-5 edit-plan apply currently supports the primary side-slope segment only."
            if parameter not in ("width", "slope"):
                return None, "PH-5 side-slope edit-plan apply currently supports Width and Slope % only."
        elif source_scope == "typical":
            if not target_id:
                return None, "PH-5 typical-component edit-plan apply requires a stable component id."
            if side not in ("left", "right", "center", "both"):
                return None, "PH-5 typical-component edit-plan apply requires a valid typical component side."
            resolved_row = self._resolved_typical_component_row(sec, seg)
            if not resolved_row:
                return None, "PH-5 typical-component edit-plan apply could not resolve the current component row."
            if parameter in ("extra_width", "back_slope") and target_type not in ("curb", "ditch", "berm"):
                return None, f"PH-5 {parameter.replace('_', ' ')} apply is only available for curb, ditch, or berm components."
        else:
            return None, "PH-5 edit-plan apply currently supports side-slope or typical component targets only."

        payload = dict(getattr(self, "_current_payload", None) or {})
        rows = sorted(
            [dict(row or {}) for row in list(getattr(self, "_station_rows", []) or [])],
            key=lambda row: float(row.get("station", 0.0) or 0.0),
        )
        station = float(payload.get("station", 0.0) or 0.0)
        config = self._scope_station_config(scope, station, rows, payload)
        start_sta = float(config.get("start_station", station) or station)
        end_sta = float(config.get("end_station", station) or station)
        transition_in = float(config.get("transition_in", 0.0) or 0.0)
        transition_out = float(config.get("transition_out", 0.0) or 0.0)
        if scope == "Station Range" and abs(end_sta - start_sta) <= 1e-6:
            return None, "Set a wider station range or use Current Station Only."

        if parameter in ("width", "height", "extra_width"):
            value = _units.meters_from_user_length(
                self._unit_context(),
                float(self.spin_width.value()),
                unit=self._display_unit_label(),
                use_default="display",
            )
            if not math.isfinite(value):
                return None, "Length value must be finite."
            if parameter in ("width", "extra_width") and value < 0.0:
                label = "Width" if parameter == "width" else "Extra width"
                return None, f"{label} value must be non-negative."
            if source_scope == "typical":
                field_map = {
                    "width": "Width",
                    "height": "Height",
                    "extra_width": "ExtraWidth",
                }
                old_value = float(resolved_row.get(field_map.get(parameter, "Width"), 0.0) or 0.0)
            else:
                old_value = float(seg.get("span", 0.0) or 0.0)
            unit = "m"
        else:
            value = float(self.spin_slope.value())
            if not math.isfinite(value):
                return None, "Slope percent must be finite."
            if source_scope == "typical":
                field_map = {
                    "slope": "CrossSlopePct",
                    "back_slope": "BackSlopePct",
                }
                old_value = float(resolved_row.get(field_map.get(parameter, "CrossSlopePct"), 0.0) or 0.0)
            else:
                old_value = float(seg.get("slope", 0.0) or 0.0)
            unit = "pct"

        asm = getattr(sec, "AssemblyTemplate", None)
        if source_scope == "typical":
            resolved_parameter = {
                "width": "width",
                "slope": "cross_slope_pct",
                "height": "height",
                "extra_width": "extra_width",
                "back_slope": "back_slope_pct",
            }.get(parameter, "width")
        else:
            resolved_parameter = "width" if parameter == "width" else "slope_pct"
        return {
            "phase": "PH-5",
            "kind": "edit_plan",
            "scope_kind": "station" if scope == "Current Station Only" else "range",
            "parameter": resolved_parameter,
            "value": float(value),
            "old_value": float(old_value),
            "unit": unit,
            "target_id": target_id,
            "target_side": side,
            "target_type": target_type,
            "source_scope": source_scope,
            "start_station": float(start_sta),
            "end_station": float(end_sta),
            "transition_in": float(transition_in),
            "transition_out": float(transition_out),
            "bench_aware": bool(self._assembly_side_has_bench(seg, asm)) if source_scope == "side_slope" and asm is not None else False,
            "description": "override row will be written to CrossSectionEditPlan",
        }, ""

    def _ph4_width_target(self, seg):
        if not seg:
            return None, "Select a component target first."
        if str(self.cmb_edit_scope.currentText() or "") != "Global Source":
            return None, "PH-4 first apply only supports Global Source."
        source = str(seg.get("source", "") or "").strip().lower()
        sec = self._current_section_set()
        if source in ("assembly_template", "resolved_section_profile"):
            return self._ph4_assembly_width_target(seg, sec)
        if self._component_scope(seg) != "typical":
            return None, "PH-4 width apply only supports typical components or AssemblyTemplate side-slope targets."
        typ = str(seg.get("type", "") or "").strip().lower()
        if typ in ("curb", "ditch", "berm", "bench", "side_slope", "cut_slope", "fill_slope"):
            return None, f"PH-4 safe apply does not edit {typ or 'this'} width because it may involve extra width or topology."
        if source not in ("typical_summary", ""):
            return None, f"PH-4 safe apply does not support generated source '{source}'."
        typ_obj = getattr(sec, "TypicalSectionTemplate", None) if sec is not None else None
        if typ_obj is None:
            return None, "No TypicalSectionTemplate is linked to the current SectionSet."
        ids = list(getattr(typ_obj, "ComponentIds", []) or [])
        sides = list(getattr(typ_obj, "ComponentSides", []) or [])
        types = list(getattr(typ_obj, "ComponentTypes", []) or [])
        widths = list(getattr(typ_obj, "ComponentWidths", []) or [])
        target_id = str(seg.get("id", "") or "").strip()
        target_side = str(seg.get("side", "") or "").strip().lower()
        target_type = typ
        for idx, cid in enumerate(ids):
            if str(cid or "").strip() != target_id:
                continue
            row_side = str(sides[idx] if idx < len(sides) else "" or "").strip().lower()
            row_type = str(types[idx] if idx < len(types) else "" or "").strip().lower()
            if target_side and row_side != target_side:
                continue
            if target_type and row_type != target_type:
                continue
            if idx >= len(widths):
                return None, "TypicalSectionTemplate width array is shorter than component id array."
            return {
                "kind": "typical",
                "typical": typ_obj,
                "index": int(idx),
                "old_width": float(widths[idx] or 0.0),
                "description": "width will be written to the linked TypicalSectionTemplate",
            }, ""
        return None, "Selected component was not found in the linked TypicalSectionTemplate arrays."

    def _ph4_assembly_width_target(self, seg, sec):
        if sec is None:
            return None, "No SectionSet is selected."
        asm = getattr(sec, "AssemblyTemplate", None)
        if asm is None:
            return None, "No AssemblyTemplate is linked to the current SectionSet."
        typ = str(seg.get("type", "") or "").strip().lower()
        side = str(seg.get("side", "") or "").strip().lower()
        if typ == "carriageway":
            if side == "left":
                prop = "LeftWidth"
            elif side == "right":
                prop = "RightWidth"
            else:
                return None, "PH-4 AssemblyTemplate apply requires a left or right carriageway target."
        elif typ in ("side_slope", "cut_slope", "fill_slope"):
            prop, message = self._ph4_assembly_side_width_property(seg, asm)
            if not prop:
                return None, message
        else:
            return None, "PH-4 AssemblyTemplate apply only supports carriageway width and simple side-slope width."
        if not hasattr(asm, prop):
            return None, f"AssemblyTemplate does not expose {prop}."
        return {
            "kind": "assembly",
            "assembly": asm,
            "property": prop,
            "old_width": float(getattr(asm, prop, 0.0) or 0.0),
            "bench_aware": bool(self._assembly_side_has_bench(seg, asm)) if typ in ("side_slope", "cut_slope", "fill_slope") else False,
            "description": f"width will be written to AssemblyTemplate.{prop}"
            + (" while preserving configured bench rows" if bool(self._assembly_side_has_bench(seg, asm)) and typ in ("side_slope", "cut_slope", "fill_slope") else ""),
        }, ""

    def _ph4_assembly_side_width_property(self, seg, asm):
        side = str(seg.get("side", "") or "").strip().lower()
        order = int(float(seg.get("order", 0) or 0))
        if order != 10:
            return "", "PH-4 side-slope width apply only supports the primary assembly side-slope segment."
        if side == "left":
            return "LeftSideWidth", ""
        if side == "right":
            return "RightSideWidth", ""
        return "", "PH-4 side-slope width apply requires a left or right target."

    def _ph4_slope_target(self, seg):
        if not seg:
            return None, "Select a component target first."
        if str(self.cmb_edit_scope.currentText() or "") != "Global Source":
            return None, "PH-4 slope apply only supports Global Source."
        source = str(seg.get("source", "") or "").strip().lower()
        if source not in ("assembly_template", "resolved_section_profile"):
            return None, "PH-4 slope apply only supports assembly_template or resolved_section_profile sources."
        sec = self._current_section_set()
        asm = getattr(sec, "AssemblyTemplate", None) if sec is not None else None
        if asm is None:
            return None, "No AssemblyTemplate is linked to the current SectionSet."
        typ = str(seg.get("type", "") or "").strip().lower()
        if typ not in ("side_slope", "cut_slope", "fill_slope"):
            return None, "PH-4 slope apply only supports assembly side-slope targets."
        prop, message = self._ph4_assembly_side_slope_property(seg, asm)
        if not prop:
            return None, message
        if not hasattr(asm, prop):
            return None, f"AssemblyTemplate does not expose {prop}."
        return {
            "kind": "assembly_slope",
            "assembly": asm,
            "property": prop,
            "old_slope": float(getattr(asm, prop, 0.0) or 0.0),
            "bench_aware": bool(self._assembly_side_has_bench(seg, asm)),
            "description": f"slope will be written to AssemblyTemplate.{prop}"
            + (" while preserving configured bench rows" if bool(self._assembly_side_has_bench(seg, asm)) else ""),
        }, ""

    def _ph4_assembly_side_slope_property(self, seg, asm):
        side = str(seg.get("side", "") or "").strip().lower()
        order = int(float(seg.get("order", 0) or 0))
        if order != 10:
            return "", "PH-4 side-slope percent apply only supports the primary assembly side-slope segment."
        if side == "left":
            return "LeftSideSlopePct", ""
        if side == "right":
            return "RightSideSlopePct", ""
        return "", "PH-4 side-slope percent apply requires a left or right target."

    def _assembly_side_has_bench(self, seg, asm):
        side = str(dict(seg or {}).get("side", "") or "").strip().lower()
        if side == "left":
            return bool(getattr(asm, "UseLeftBench", False)) or bool(list(getattr(asm, "LeftBenchRows", []) or []))
        if side == "right":
            return bool(getattr(asm, "UseRightBench", False)) or bool(list(getattr(asm, "RightBenchRows", []) or []))
        return False

    def _ph4_region_policy_target(self, seg):
        parameter = self._selected_edit_parameter()
        if parameter not in ("region_side_policy", "region_daylight_policy"):
            return None, "Select a RegionPlan policy edit parameter."
        if not seg:
            return None, "Select a component target first."
        if str(self.cmb_edit_scope.currentText() or "") != "Active Region":
            return None, "PH-4 RegionPlan apply only supports Active Region scope."
        sec = self._current_section_set()
        if sec is None:
            return None, "No SectionSet is selected."
        if not bool(getattr(sec, "UseRegionPlan", False)):
            return None, "The current SectionSet is not using a RegionPlan."
        if not bool(getattr(sec, "ApplyRegionOverrides", False)):
            return None, "Enable ApplyRegionOverrides on the SectionSet before editing RegionPlan policies."
        region_obj = self._current_region_plan(sec)
        if region_obj is None:
            return None, "No RegionPlan is linked to the current SectionSet."
        payload = dict(getattr(self, "_current_payload", None) or {})
        base_id = str(payload.get("base_region_id", "") or "").strip()
        if not base_id:
            return None, "The current station has no active base region."
        records = list(RegionPlan.export_records_from_grouped(region_obj) or RegionPlan.records(region_obj) or [])
        for idx, rec in enumerate(records):
            if str(rec.get("Id", "") or "").strip() != base_id:
                continue
            if str(rec.get("Layer", "base") or "base").strip().lower() != "base":
                continue
            field = "SidePolicy" if parameter == "region_side_policy" else "DaylightPolicy"
            scope = self._component_scope(seg)
            if field == "SidePolicy" and scope not in ("side_slope", "daylight"):
                return None, "Region side policy edits require a side-slope or daylight target."
            if field == "DaylightPolicy" and scope != "daylight":
                return None, "Region daylight policy edits require a daylight target."
            new_policy = self._selected_region_policy_value()
            return {
                "kind": "region_policy",
                "region_plan": region_obj,
                "records": records,
                "index": int(idx),
                "region_id": base_id,
                "property": field,
                "old_policy": str(rec.get(field, "") or ""),
                "new_policy": str(new_policy or ""),
                "description": f"{field} will be written to active RegionPlan base region {base_id}",
            }, ""
        return None, f"Active base region '{base_id}' was not found in the linked RegionPlan."

    def _current_region_plan(self, sec):
        if sec is None:
            return None
        try:
            from freecad.Corridor_Road.objects.obj_section_set import resolve_region_plan_source

            resolved = resolve_region_plan_source(sec)
            if resolved is not None:
                return resolved
        except Exception:
            pass
        try:
            return getattr(sec, "RegionPlan", None)
        except Exception:
            return None

    def _clear_editor_overlay(self):
        if not hasattr(self, "scene"):
            self._editor_overlay_items = []
            self._editor_overlay_debug_rows = []
            return
        for item in list(getattr(self, "_editor_overlay_items", []) or []):
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self._editor_overlay_items = []
        self._editor_overlay_debug_rows = []

    def _add_editor_overlay_item(self, item):
        if item is None:
            return
        try:
            item.setZValue(1000.0)
        except Exception:
            pass
        self._editor_overlay_items.append(item)

    def _add_editor_overlay_debug_row(self, text):
        row = str(text or "").strip()
        if not row:
            return
        self._editor_overlay_debug_rows.append(row)

    def _editor_conflict_summary(self, seg, payload):
        payload = dict(payload or {})
        if not seg or not payload:
            return {"state": "none", "summary": "none", "label": "None", "message": ""}
        station = float(payload.get("station", 0.0) or 0.0)
        rows = sorted(
            [dict(row or {}) for row in list(getattr(self, "_station_rows", []) or [])],
            key=lambda row: float(row.get("station", 0.0) or 0.0),
        )
        if not rows:
            rows = [dict(payload)]
        scope = str(self.cmb_edit_scope.currentText() or "")
        config = self._scope_station_config(scope, station, rows, payload)
        affected_rows = self._affected_station_rows(scope, station, rows, payload, config=config)
        structure_overlap = self._impact_structure_overlap(payload, affected_rows)
        if structure_overlap == "none":
            return {"state": "none", "summary": "none", "label": "None", "message": ""}
        parameter_class = self._parameter_class(seg)
        if parameter_class == "daylight":
            return {
                "state": "blocked",
                "summary": str(structure_overlap),
                "label": f"Blocked by {structure_overlap}",
                "message": "Daylight edits that overlap structures require structure or region policy changes first.",
            }
        return {
            "state": "warning",
            "summary": str(structure_overlap),
            "label": f"Review {structure_overlap}",
            "message": "Structure overlap should be reviewed before applying geometry edits.",
        }

    def _conflict_resolution_lines(self, conflict, seg, payload):
        state = str(dict(conflict or {}).get("state", "none") or "none").strip().lower()
        migration = self._override_migration_context(seg, payload)
        lines = []
        if state == "none" and not migration:
            return []
        summary = str(dict(conflict or {}).get("summary", "") or "").strip() or "the overlapping structure span"
        scope = str(self.cmb_edit_scope.currentText() or "")
        component_scope = self._component_scope(seg)
        if state == "blocked":
            lines.append(f"Review the overlapping StructureSet span for {summary} before changing daylight behavior.")
            if scope != "Active Region":
                lines.append("Switch to Active Region if you need a Region daylight-policy override for this span.")
            else:
                lines.append("Use Region Daylight Policy to disable or redirect daylight around the blocked span.")
            lines.append("Structure safety overrides currently take precedence over local daylight edits.")
        elif state == "warning":
            lines.append("Review the before/after overlay and impact preview before apply.")
            if scope in ("Station Range", "Current Station Only"):
                lines.append("Prefer Active Region or structure-side policy changes when the conflict extends across multiple stations.")
            else:
                lines.append("Use a narrower scope only if the change is intentionally local.")
            if component_scope == "daylight":
                lines.append("If daylight behavior must change here, resolve the overlapping structure span first.")
        if migration:
            edit_id = str(migration.get("edit_id", "") or "").strip()
            if edit_id:
                lines.append(f"This target is currently driven by CrossSectionEditPlan override {edit_id}.")
            if bool(migration.get("can_prepare_region", False)):
                lines.append("If this behavior should belong to the active region, prepare a RegionPlan policy handoff before retiring the local override.")
            elif bool(migration.get("can_disable", False)):
                lines.append("Retire the local override only after confirming another source now owns this behavior.")
        return lines

    def _resolution_action_specs(self, conflict, seg, payload):
        migration = self._override_migration_context(seg, payload)
        if migration:
            specs = []
            if bool(migration.get("can_prepare_region", False)):
                if str(migration.get("preferred_action", "") or "") == "daylight":
                    specs.append(
                        {
                            "action": "prepare_region_daylight_policy",
                            "label": "Prep Daylight Migration",
                            "tooltip": "Switch to Active Region and prepare a Region Daylight Policy handoff for the local override.",
                            "policy_value": self._preferred_daylight_policy_value(seg),
                        }
                    )
                elif str(migration.get("preferred_action", "") or "") == "side":
                    specs.append(
                        {
                            "action": "prepare_region_side_policy",
                            "label": "Prep Side Policy",
                            "tooltip": "Switch to Active Region and prepare a Region Side Policy review for the local override.",
                        }
                    )
            if bool(migration.get("can_disable", False)):
                specs.append(
                    {
                        "action": "disable_local_override",
                        "label": "Disable Local Override",
                        "tooltip": "Disable the active CrossSectionEditPlan row after the new owner is ready.",
                    }
                )
            if specs:
                return specs[:2]
        state = str(dict(conflict or {}).get("state", "none") or "none").strip().lower()
        if state == "none" or not seg:
            return []
        scope = str(self.cmb_edit_scope.currentText() or "")
        parameter = self._selected_edit_parameter()
        parameter_class = self._parameter_class(seg)
        specs = []
        if state == "blocked":
            if scope != "Active Region":
                specs.append(
                    {
                        "action": "switch_scope_active_region",
                        "label": "Use Active Region",
                        "tooltip": "Switch the editor scope to Active Region for region-level conflict handling.",
                    }
                )
            specs.append(
                {
                    "action": "prepare_region_daylight_policy",
                    "label": "Prep Daylight Policy",
                    "tooltip": "Switch to Active Region and prepare a Region Daylight Policy edit for this span.",
                    "policy_value": self._preferred_daylight_policy_value(seg),
                }
            )
            return specs[:2]
        if scope != "Active Region":
            specs.append(
                {
                    "action": "switch_scope_active_region",
                    "label": "Use Active Region",
                    "tooltip": "Switch the editor scope to Active Region for region-level conflict handling.",
                }
            )
        if scope != "Current Station Only":
            specs.append(
                {
                    "action": "switch_scope_current_station",
                    "label": "Narrow To Current",
                    "tooltip": "Limit the edit scope to the current station for a tighter local review.",
                }
            )
        if parameter_class == "daylight" and parameter != "region_daylight_policy":
            specs.append(
                {
                    "action": "prepare_region_daylight_policy",
                    "label": "Prep Daylight Policy",
                    "tooltip": "Switch to Active Region and prepare a Region Daylight Policy edit for this span.",
                    "policy_value": self._preferred_daylight_policy_value(seg),
                }
            )
        return specs[:2]

    def _preferred_daylight_policy_value(self, seg):
        side = str(dict(seg or {}).get("side", "") or "").strip().lower()
        if side in ("left", "right"):
            return f"{side}:off"
        return "off"

    def _override_migration_context(self, seg, payload):
        payload = dict(payload or {})
        source = str(dict(seg or {}).get("source", "") or "").strip().lower()
        if source not in ("cross_section_edit", "edit_plan", "crosssectioneditplan"):
            return {}
        edit_ids = [tok.strip() for tok in str(dict(seg or {}).get("editId", "") or "").split(",") if tok.strip()]
        edit_id = edit_ids[0] if edit_ids else ""
        sec = self._current_section_set()
        plan_obj = None
        if sec is not None:
            try:
                from freecad.Corridor_Road.objects.obj_section_set import resolve_cross_section_edit_plan_source

                plan_obj = resolve_cross_section_edit_plan_source(sec)
            except Exception:
                plan_obj = getattr(sec, "CrossSectionEditPlan", None)
        component_scope = self._component_scope(seg)
        region_obj = self._current_region_plan(sec) if sec is not None else None
        region_id = str(payload.get("base_region_id", "") or "").strip()
        can_prepare_region = bool(
            sec is not None
            and region_obj is not None
            and bool(getattr(sec, "UseRegionPlan", False))
            and bool(getattr(sec, "ApplyRegionOverrides", False))
            and region_id
            and component_scope in ("side_slope", "daylight")
        )
        preferred_action = "daylight" if component_scope == "daylight" else ("side" if component_scope == "side_slope" else "")
        return {
            "edit_id": edit_id,
            "plan_obj": plan_obj,
            "component_scope": component_scope,
            "region_id": region_id,
            "can_prepare_region": can_prepare_region,
            "can_disable": bool(plan_obj is not None and edit_id),
            "preferred_action": preferred_action,
        }

    def _find_region_policy_index(self, policy_value):
        if not hasattr(self, "cmb_region_policy"):
            return -1
        try:
            idx = self.cmb_region_policy.findData(str(policy_value or ""))
            if idx >= 0:
                return idx
        except Exception:
            pass
        return -1

    def _set_region_policy_combo_value(self, policy_value):
        if not hasattr(self, "cmb_region_policy"):
            return False
        idx = self._find_region_policy_index(policy_value)
        if idx < 0:
            return False
        self.cmb_region_policy.setCurrentIndex(idx)
        return True

    def _resolution_handoff_lines(self, conflict, seg, payload, action_specs=None):
        payload = dict(payload or {})
        state = str(dict(conflict or {}).get("state", "none") or "none").strip().lower()
        if state == "none" and not self._override_migration_context(seg, payload):
            return []
        if not seg:
            return []
        station = float(payload.get("station", 0.0) or 0.0)
        region_id = str(payload.get("base_region_id", "") or "").strip()
        region_summary = str(payload.get("region_summary", "") or "").strip()
        region_label = region_id or region_summary or self._fmt_station(station)
        specs = list(action_specs if action_specs is not None else self._resolution_action_specs(conflict, seg, payload) or [])
        lines = []
        for spec in specs[:2]:
            action = str(spec.get("action", "") or "").strip().lower()
            if action == "switch_scope_active_region":
                lines.append(f"'{spec.get('label', 'Use Active Region')}' switches scope to Active Region for {region_label}.")
            elif action == "switch_scope_current_station":
                lines.append(f"'{spec.get('label', 'Narrow To Current')}' reduces the review span to {self._fmt_station(station)} only.")
            elif action == "prepare_region_daylight_policy":
                policy_value = str(spec.get("policy_value", self._preferred_daylight_policy_value(seg)) or "")
                policy_label = policy_value or "off"
                lines.append(f"'{spec.get('label', 'Prep Daylight Policy')}' prepares RegionPlan.DaylightPolicy = {policy_label} for {region_label}.")
            elif action == "prepare_region_side_policy":
                lines.append(f"'{spec.get('label', 'Prep Side Policy')}' switches to Active Region and prepares RegionPlan.SidePolicy review for {region_label}.")
            elif action == "disable_local_override":
                edit_id = str(self._override_migration_context(seg, payload).get("edit_id", "") or "").strip()
                lines.append(f"'{spec.get('label', 'Disable Local Override')}' turns off local override {edit_id or '<pending>'} after the new owner is ready.")
        return lines

    def _set_resolution_action_button(self, button, spec):
        if button is None:
            return
        if not spec:
            button.setText("")
            button.setToolTip("")
            button.setVisible(False)
            button.setEnabled(False)
            return
        button.setText(str(spec.get("label", "") or "Action"))
        button.setToolTip(str(spec.get("tooltip", "") or ""))
        button.setVisible(True)
        button.setEnabled(True)

    def _refresh_resolution_actions(self, seg, conflict, payload):
        specs = list(self._resolution_action_specs(conflict, seg, payload) or [])
        self._resolution_action_specs_cache = specs
        self._set_resolution_action_button(getattr(self, "btn_resolution_primary", None), specs[0] if len(specs) > 0 else None)
        self._set_resolution_action_button(getattr(self, "btn_resolution_secondary", None), specs[1] if len(specs) > 1 else None)

    def _run_resolution_action(self, index):
        specs = list(getattr(self, "_resolution_action_specs_cache", []) or [])
        if index < 0 or index >= len(specs):
            return
        spec = dict(specs[index] or {})
        action = str(spec.get("action", "") or "").strip().lower()
        if not action:
            return
        if action == "switch_scope_active_region":
            self.cmb_edit_scope.setCurrentText("Active Region")
        elif action == "switch_scope_current_station":
            self.cmb_edit_scope.setCurrentText("Current Station Only")
        elif action == "prepare_region_daylight_policy":
            self.cmb_edit_scope.setCurrentText("Active Region")
            self.cmb_edit_parameter.setCurrentText("Region Daylight Policy")
            policy_value = str(spec.get("policy_value", self._preferred_daylight_policy_value(self._current_editor_segment())) or "").strip()
            if policy_value:
                self._set_region_policy_combo_value(policy_value)
        elif action == "prepare_region_side_policy":
            self.cmb_edit_scope.setCurrentText("Active Region")
            self.cmb_edit_parameter.setCurrentText("Region Side Policy")
        elif action == "disable_local_override":
            self._disable_cross_section_edit_override(self._current_editor_segment())
            return
        else:
            return
        self._refresh_editor_target()
        if action == "prepare_region_daylight_policy":
            policy_value = str(spec.get("policy_value", self._preferred_daylight_policy_value(self._current_editor_segment())) or "").strip()
            if policy_value:
                self._set_region_policy_combo_value(policy_value)

    def _draw_selected_component_overlay(self):
        self._clear_editor_overlay()
        seg = self._current_editor_segment()
        payload = dict(getattr(self, "_current_payload", None) or {})
        if not seg or not payload or not self._editor_scope_visible(self._component_scope(seg)):
            return

        marker = self._matching_marker_row(seg, payload)
        if marker is None:
            return

        highlight = QtGui.QColor("#ffd84d")
        fill = QtGui.QColor("#ffd84d")
        fill.setAlpha(42)
        pen = QtGui.QPen(highlight)
        pen.setCosmetic(True)
        pen.setWidthF(4.0)
        pen.setStyle(QtCore.Qt.SolidLine)

        x0 = float(marker.get("x0", 0.0) or 0.0)
        x1 = float(marker.get("x1", 0.0) or 0.0)
        y_base = float(marker.get("y_base", 0.0) or 0.0)
        y_base_left = float(marker.get("y_base_left", y_base) or y_base)
        y_base_right = float(marker.get("y_base_right", y_base) or y_base)
        y_top = float(marker.get("y_top", 0.0) or 0.0)
        y_low = min(y_base_left, y_base_right, y_top)
        y_high = max(y_base_left, y_base_right, y_top)
        self._add_editor_overlay_debug_row(
            f"selected|id={str(seg.get('id', '') or '').strip()}|side={str(seg.get('side', '') or '').strip().lower()}|"
            f"x0={x0:.3f}|x1={x1:.3f}|yTop={y_top:.3f}"
        )
        if abs(y_high - y_low) > 1e-9:
            self._add_editor_overlay_item(
                self.scene.addRect(
                    min(x0, x1),
                    -y_high,
                    abs(x1 - x0),
                    y_high - y_low,
                    QtGui.QPen(QtCore.Qt.NoPen),
                    QtGui.QBrush(fill),
                )
            )
        self._add_editor_overlay_item(self.scene.addLine(x0, -y_base_left, x0, -y_top, pen))
        self._add_editor_overlay_item(self.scene.addLine(x1, -y_base_right, x1, -y_top, pen))
        self._add_editor_overlay_item(self.scene.addLine(x0, -y_top, x1, -y_top, pen))

        if bool(getattr(self, "chk_show_labels", None) and self.chk_show_labels.isChecked()):
            label = str(seg.get("id", "") or seg.get("type", "") or "").strip() or "target"
            self._add_editor_overlay_item(
                self._add_scene_label(
                    label,
                    0.5 * (x0 + x1),
                    y_top + 0.35,
                    highlight,
                    anchor="center",
                    point_size=4.2,
                    vertical_anchor="bottom",
                )
            )
        self._draw_pending_preview_overlay(seg, marker)
        self._draw_drag_handles(seg, marker)
        self._draw_conflict_overlay(seg, marker, payload)

    def _preview_overlay_target(self, seg):
        if not seg:
            return None
        target, _message = self._editor_apply_target(seg)
        if not isinstance(target, dict):
            return None
        parameter = str(target.get("parameter", "") or "").strip().lower()
        if not parameter:
            selected = self._selected_edit_parameter()
            if selected == "slope":
                parameter = "slope_pct"
            elif selected == "back_slope":
                parameter = "back_slope_pct"
            else:
                parameter = str(selected or "").strip().lower()
        kind = str(target.get("kind", "") or "").strip().lower()
        if kind == "region_policy" or parameter.startswith("region_"):
            return None
        if kind == "assembly":
            old_value = float(target.get("old_width", 0.0) or 0.0)
            new_value = _units.meters_from_user_length(
                self._unit_context(),
                float(self.spin_width.value()),
                unit=self._display_unit_label(),
                use_default="display",
            )
            unit = "m"
        elif kind == "assembly_slope":
            old_value = float(target.get("old_slope", 0.0) or 0.0)
            new_value = float(self.spin_slope.value())
            unit = "pct"
        else:
            old_value = float(target.get("old_value", 0.0) or 0.0)
            new_value = float(target.get("value", old_value) or old_value)
            unit = str(target.get("unit", "") or "")
        if not math.isfinite(old_value) or not math.isfinite(new_value):
            return None
        if abs(new_value - old_value) <= (1.0e-6 if unit != "pct" else 1.0e-5):
            return None
        return {
            "parameter": parameter,
            "old_value": float(old_value),
            "new_value": float(new_value),
            "unit": unit,
            "kind": kind,
        }

    def _preview_overlay_marker(self, seg, marker, preview):
        out = dict(marker or {})
        parameter = str(preview.get("parameter", "") or "").strip().lower()
        delta = float(preview.get("new_value", 0.0) or 0.0) - float(preview.get("old_value", 0.0) or 0.0)
        x0 = float(out.get("x0", 0.0) or 0.0)
        x1 = float(out.get("x1", 0.0) or 0.0)
        y_base = float(out.get("y_base", 0.0) or 0.0)
        y_base_left = float(out.get("y_base_left", y_base) or y_base)
        y_base_right = float(out.get("y_base_right", y_base) or y_base)
        y_top = float(out.get("y_top", 0.0) or 0.0)
        side = str(dict(seg or {}).get("side", "") or "").strip().lower()

        if parameter in ("width", "extra_width"):
            if side == "left":
                x0 -= delta
            elif side == "right":
                x1 += delta
            else:
                x0 -= 0.5 * delta
                x1 += 0.5 * delta
        elif parameter == "height":
            y_top = max(y_base_left, y_base_right) + 0.05 if y_top + delta <= max(y_base_left, y_base_right) else y_top + delta
        elif parameter in ("slope_pct", "cross_slope_pct", "back_slope_pct"):
            span = max(0.0, abs(x1 - x0))
            vertical_delta = span * (delta / 100.0)
            if side == "left":
                y_base_left += vertical_delta
            elif side == "right":
                y_base_right += vertical_delta
            else:
                y_base_right += vertical_delta

        out["x0"] = float(x0)
        out["x1"] = float(x1)
        out["y_base_left"] = float(y_base_left)
        out["y_base_right"] = float(y_base_right)
        out["y_base"] = float(min(y_base_left, y_base_right))
        out["y_top"] = float(y_top)
        return out

    def _draw_pending_preview_overlay(self, seg, marker):
        preview = self._preview_overlay_target(seg)
        if preview is None or not hasattr(self, "scene"):
            return
        overlay = self._preview_overlay_marker(seg, marker, preview)
        color = QtGui.QColor("#54d7d7")
        fill = QtGui.QColor("#54d7d7")
        fill.setAlpha(24)
        pen = QtGui.QPen(color)
        pen.setCosmetic(True)
        pen.setWidthF(2.2)
        pen.setStyle(QtCore.Qt.DashLine)

        x0 = float(overlay.get("x0", 0.0) or 0.0)
        x1 = float(overlay.get("x1", 0.0) or 0.0)
        y_base = float(overlay.get("y_base", 0.0) or 0.0)
        y_base_left = float(overlay.get("y_base_left", y_base) or y_base)
        y_base_right = float(overlay.get("y_base_right", y_base) or y_base)
        y_top = float(overlay.get("y_top", 0.0) or 0.0)
        y_low = min(y_base_left, y_base_right, y_top)
        y_high = max(y_base_left, y_base_right, y_top)

        if abs(y_high - y_low) > 1e-9:
            self._add_editor_overlay_item(
                self.scene.addRect(
                    min(x0, x1),
                    -y_high,
                    abs(x1 - x0),
                    y_high - y_low,
                    QtGui.QPen(QtCore.Qt.NoPen),
                    QtGui.QBrush(fill),
                )
            )
        self._add_editor_overlay_item(self.scene.addLine(x0, -y_base_left, x0, -y_top, pen))
        self._add_editor_overlay_item(self.scene.addLine(x1, -y_base_right, x1, -y_top, pen))
        self._add_editor_overlay_item(self.scene.addLine(x0, -y_top, x1, -y_top, pen))

        if bool(getattr(self, "chk_show_labels", None) and self.chk_show_labels.isChecked()):
            label = f"Preview {self._impact_parameter_label(preview.get('parameter', 'value'))}"
            self._add_editor_overlay_item(
                self._add_scene_label(
                    label,
                    0.5 * (x0 + x1),
                    y_top + 0.70,
                    color,
                    anchor="center",
                    point_size=3.9,
                    vertical_anchor="bottom",
                )
            )
        self._add_editor_overlay_debug_row(
            f"preview|parameter={str(preview.get('parameter', '') or '')}|unit={str(preview.get('unit', '') or '')}|"
            f"old={float(preview.get('old_value', 0.0) or 0.0):.3f}|new={float(preview.get('new_value', 0.0) or 0.0):.3f}|"
            f"x0={x0:.3f}|x1={x1:.3f}|yTop={y_top:.3f}"
        )

    def _draw_conflict_overlay(self, seg, marker, payload):
        conflict = self._editor_conflict_summary(seg, payload)
        state = str(conflict.get("state", "none") or "none").strip().lower()
        if state == "none" or not hasattr(self, "scene"):
            return
        color = QtGui.QColor("#f0b64f")
        if state == "blocked":
            color = QtGui.QColor("#e8603c")
        pen = QtGui.QPen(color)
        pen.setCosmetic(True)
        pen.setWidthF(2.4)
        pen.setStyle(QtCore.Qt.DashLine)
        x0 = float(marker.get("x0", 0.0) or 0.0)
        x1 = float(marker.get("x1", 0.0) or 0.0)
        y_base = float(marker.get("y_base", 0.0) or 0.0)
        y_base_left = float(marker.get("y_base_left", y_base) or y_base)
        y_base_right = float(marker.get("y_base_right", y_base) or y_base)
        y_top = float(marker.get("y_top", 0.0) or 0.0)
        y_low = min(y_base_left, y_base_right, y_top)
        y_high = max(y_base_left, y_base_right, y_top)
        dx = max(0.06, 0.05 * max(abs(x1 - x0), 1.0))
        dy = max(0.06, 0.05 * max(abs(y_high - y_low), 1.0))
        self._add_editor_overlay_item(
            self.scene.addRect(
                min(x0, x1) - dx,
                -(y_high + dy),
                abs(x1 - x0) + (2.0 * dx),
                (y_high - y_low) + (2.0 * dy),
                pen,
                QtGui.QBrush(QtCore.Qt.NoBrush),
            )
        )
        label = str(conflict.get("label", "") or "").strip()
        if label and bool(getattr(self, "chk_show_labels", None) and self.chk_show_labels.isChecked()):
            self._add_editor_overlay_item(
                self._add_scene_label(
                    label,
                    0.5 * (x0 + x1),
                    y_high + 1.20,
                    color,
                    anchor="center",
                    point_size=4.0,
                    vertical_anchor="bottom",
                )
            )
        self._add_editor_overlay_debug_row(
            f"conflict|state={state}|summary={str(conflict.get('summary', '') or '')}|label={str(conflict.get('label', '') or '')}"
        )

    def _drag_handle_target(self, seg):
        if str(getattr(self.cmb_editor_mode, "currentText", lambda: "")() or "") != "Edit":
            return None
        parameter = self._selected_edit_parameter()
        if not self._is_width_like_parameter(parameter):
            return None
        target, _message = self._editor_apply_target(seg)
        if not isinstance(target, dict):
            return None
        if str(target.get("kind", "") or "").strip().lower() == "region_policy":
            return None
        old_value = float(target.get("old_value", 0.0) or 0.0)
        value = _units.meters_from_user_length(
            self._unit_context(),
            float(self.spin_width.value()),
            unit=self._display_unit_label(),
            use_default="display",
        )
        return {
            "parameter": str(target.get("parameter", parameter) or parameter),
            "old_value": float(old_value),
            "value": float(value),
            "unit": "m",
        }

    def _drag_handle_context(self, seg):
        mode = str(getattr(self.cmb_editor_mode, "currentText", lambda: "")() or "")
        if mode != "Edit":
            return {"status": "blocked", "reason": "Switch to Edit mode to drag width-like parameters.", "target": None}
        parameter = self._selected_edit_parameter()
        if not self._is_width_like_parameter(parameter):
            return {"status": "blocked", "reason": "Select Width or Extra Width to drag from the canvas.", "target": None}
        target = self._drag_handle_target(seg)
        if target is None:
            _t, message = self._editor_apply_target(seg)
            return {"status": "blocked", "reason": message or "Canvas drag is not available for this target.", "target": None}
        payload = dict(getattr(self, "_current_payload", None) or {})
        rows = sorted(
            [dict(row or {}) for row in list(getattr(self, "_station_rows", []) or [])],
            key=lambda row: float(row.get("station", 0.0) or 0.0),
        )
        station = float(payload.get("station", 0.0) or 0.0)
        affected_rows = self._affected_station_rows(str(self.cmb_edit_scope.currentText() or ""), station, rows, payload, config=None)
        structure_overlap = self._impact_structure_overlap(payload, affected_rows)
        if structure_overlap != "none":
            return {
                "status": "warning",
                "reason": "Structure overlap is present; review the preview before apply.",
                "target": target,
            }
        sec = self._current_section_set()
        target_scope = str(target.get("source_scope", "") or "").strip().lower()
        target_type = str(dict(seg or {}).get("type", "") or "").strip().lower()
        if target_scope == "side_slope" or target_type in ("side_slope", "cut_slope", "fill_slope") or self._component_scope(seg) == "side_slope":
            asm = getattr(sec, "AssemblyTemplate", None) if sec is not None else None
            if asm is not None and bool(self._assembly_side_has_bench(seg, asm)):
                return {
                    "status": "warning",
                    "reason": "Bench rows are preserved; drag edits update the owning side-width only.",
                    "target": target,
                }
        return {"status": "ready", "reason": "Drag to update the pending width-like value.", "target": target}

    def _drag_handle_specs(self, seg, marker):
        ctx = self._drag_handle_context(seg)
        target = ctx.get("target")
        if target is None:
            return []
        side = str(dict(seg or {}).get("side", "") or "").strip().lower()
        y_top = float(dict(marker or {}).get("y_top", 0.0) or 0.0)
        x0 = float(dict(marker or {}).get("x0", 0.0) or 0.0)
        x1 = float(dict(marker or {}).get("x1", 0.0) or 0.0)
        handles = []
        if side == "left":
            handles.append({"edge": "left", "x": x0, "y": y_top, "direction": -1.0, "target": target, "status": ctx.get("status", "ready")})
        elif side == "right":
            handles.append({"edge": "right", "x": x1, "y": y_top, "direction": 1.0, "target": target, "status": ctx.get("status", "ready")})
        return handles

    def _draw_drag_handles(self, seg, marker):
        if not hasattr(self, "scene"):
            return
        ctx = self._drag_handle_context(seg)
        status = str(ctx.get("status", "blocked") or "blocked").strip().lower()
        reason = str(ctx.get("reason", "") or "").strip()
        color_hex = "#f6c85f"
        if status == "warning":
            color_hex = "#f0b64f"
        elif status == "blocked":
            color_hex = "#e8603c"
        self._add_editor_overlay_debug_row(f"handleState|status={status}|reason={reason}")
        handles = self._drag_handle_specs(seg, marker)
        if not handles:
            return
        radius = max(0.10, 0.006 * max(float(getattr(self._last_fit_rect, "width", lambda: 1.0)() if self._last_fit_rect is not None else 1.0), 1.0))
        fill = QtGui.QColor(color_hex)
        pen = QtGui.QPen(fill)
        pen.setCosmetic(True)
        pen.setWidthF(1.6)
        for handle in handles:
            hx = float(handle.get("x", 0.0) or 0.0)
            hy = float(handle.get("y", 0.0) or 0.0)
            self._add_editor_overlay_item(
                self.scene.addEllipse(
                    hx - radius,
                    -(hy + radius),
                    2.0 * radius,
                    2.0 * radius,
                    pen,
                    QtGui.QBrush(fill),
                )
            )
            self._add_editor_overlay_debug_row(
                f"handle|edge={str(handle.get('edge', '') or '')}|x={hx:.3f}|y={hy:.3f}|parameter={str(handle.get('target', {}).get('parameter', '') or '')}|status={str(handle.get('status', '') or '')}"
            )
        if reason and bool(getattr(self, "chk_show_labels", None) and self.chk_show_labels.isChecked()):
            self._add_editor_overlay_item(
                self._add_scene_label(
                    "Drag available" if status == "ready" else str(status.title()),
                    0.5 * (float(marker.get("x0", 0.0) or 0.0) + float(marker.get("x1", 0.0) or 0.0)),
                    float(marker.get("y_top", 0.0) or 0.0) + 0.95,
                    fill,
                    anchor="center",
                    point_size=3.9,
                    vertical_anchor="bottom",
                )
            )

    def _drag_handle_hit_threshold(self):
        return max(0.18, 0.012 * max(float(self._last_fit_rect.width()) if self._last_fit_rect is not None else 1.0, 1.0))

    def _begin_editor_drag(self, scene_pos):
        seg = self._current_editor_segment()
        payload = dict(getattr(self, "_current_payload", None) or {})
        if not seg or not payload:
            return False
        marker = self._matching_marker_row(seg, payload)
        if marker is None:
            return False
        ctx = self._drag_handle_context(seg)
        if str(ctx.get("status", "blocked") or "blocked").strip().lower() == "blocked":
            return False
        handles = self._drag_handle_specs(seg, marker)
        if not handles:
            return False
        px = float(scene_pos.x())
        py = -float(scene_pos.y())
        threshold = self._drag_handle_hit_threshold()
        best = None
        best_dist = None
        for handle in handles:
            hx = float(handle.get("x", 0.0) or 0.0)
            hy = float(handle.get("y", 0.0) or 0.0)
            dist = (((px - hx) ** 2.0) + ((py - hy) ** 2.0)) ** 0.5
            if best_dist is None or dist < best_dist:
                best = handle
                best_dist = dist
        if best is None or best_dist is None or best_dist > threshold:
            return False
        self._editor_drag_state = {
            "edge": str(best.get("edge", "") or ""),
            "origin_x": float(best.get("x", 0.0) or 0.0),
            "origin_value": float(best.get("target", {}).get("value", 0.0) or 0.0),
            "direction": float(best.get("direction", 0.0) or 0.0),
            "parameter": str(best.get("target", {}).get("parameter", "") or ""),
            "unit": str(best.get("target", {}).get("unit", "m") or "m"),
        }
        return True

    def _update_editor_drag(self, scene_pos):
        state = dict(getattr(self, "_editor_drag_state", None) or {})
        if not state:
            return False
        dx = float(scene_pos.x()) - float(state.get("origin_x", 0.0) or 0.0)
        new_value = float(state.get("origin_value", 0.0) or 0.0) + (float(state.get("direction", 0.0) or 0.0) * dx)
        parameter = str(state.get("parameter", "") or "").strip().lower()
        if parameter in ("width", "extra_width"):
            new_value = max(0.0, new_value)
        display_value = self._display_from_meters(new_value)
        self.spin_width.setValue(display_value)
        return True

    def _finish_editor_drag(self, scene_pos):
        if not getattr(self, "_editor_drag_state", None):
            return False
        self._update_editor_drag(scene_pos)
        self._editor_drag_state = None
        return True

    def _handle_editor_canvas_click(self, event, scene_pos):
        if not hasattr(self, "cmb_editor_mode"):
            return False
        if str(self.cmb_editor_mode.currentText() or "") == "Review":
            return False
        button = getattr(event, "button", lambda: None)()
        left_button = getattr(QtCore.Qt, "LeftButton", None)
        if left_button is None and hasattr(QtCore.Qt, "MouseButton"):
            left_button = getattr(QtCore.Qt.MouseButton, "LeftButton", None)
        if left_button is not None and button != left_button:
            return False
        if self._begin_editor_drag(scene_pos):
            return True
        return self._select_component_at_scene_point(scene_pos)

    def _handle_editor_canvas_move(self, event, scene_pos):
        _event = event
        return self._update_editor_drag(scene_pos)

    def _handle_editor_canvas_release(self, event, scene_pos):
        _event = event
        return self._finish_editor_drag(scene_pos)

    def _select_component_at_scene_point(self, scene_pos):
        payload = dict(getattr(self, "_current_payload", None) or {})
        if not payload or not hasattr(self, "cmb_component_target"):
            return False
        px = float(scene_pos.x())
        py = -float(scene_pos.y())
        best_idx = -1
        best_score = None
        for idx in range(self.cmb_component_target.count()):
            seg = self.cmb_component_target.itemData(idx)
            if not seg or not self._editor_scope_visible(self._component_scope(seg)):
                continue
            marker = self._matching_marker_row(dict(seg or {}), payload)
            if marker is None:
                continue
            score = self._marker_hit_score(marker, px, py)
            if best_score is None or score < best_score:
                best_score = score
                best_idx = idx
        if best_idx < 0 or best_score is None:
            return False
        threshold = self._marker_hit_threshold()
        if best_score > threshold:
            return False
        self.cmb_component_target.setCurrentIndex(best_idx)
        return True

    def _marker_hit_score(self, marker, px, py):
        x0 = float(marker.get("x0", 0.0) or 0.0)
        x1 = float(marker.get("x1", 0.0) or 0.0)
        y_base = float(marker.get("y_base", 0.0) or 0.0)
        y_base_left = float(marker.get("y_base_left", y_base) or y_base)
        y_base_right = float(marker.get("y_base_right", y_base) or y_base)
        y_top = float(marker.get("y_top", 0.0) or 0.0)
        min_x = min(x0, x1)
        max_x = max(x0, x1)
        min_y = min(y_base_left, y_base_right, y_top)
        max_y = max(y_base_left, y_base_right, y_top)
        dx = 0.0
        if px < min_x:
            dx = min_x - px
        elif px > max_x:
            dx = px - max_x
        dy = 0.0
        if py < min_y:
            dy = min_y - py
        elif py > max_y:
            dy = py - max_y
        return ((dx * dx) + (dy * dy)) ** 0.5

    def _marker_hit_threshold(self):
        rect = self._last_fit_rect if getattr(self, "_last_fit_rect", None) is not None else None
        width = float(rect.width()) if rect is not None else 1.0
        height = float(rect.height()) if rect is not None else 1.0
        return max(0.20, 0.018 * max(width, height))

    def _matching_marker_row(self, seg, payload):
        markers = list(payload.get("planned_component_marker_rows", []) or [])
        if not markers:
            return None
        scope = self._component_scope(seg)
        side = str(seg.get("side", "") or "").strip().lower()
        x0 = float(seg.get("x0", 0.0) or 0.0)
        x1 = float(seg.get("x1", 0.0) or 0.0)
        best = None
        best_score = None
        for row in markers:
            if self._component_scope(row) != scope:
                continue
            marker_side = str(row.get("side", "") or "").strip().lower()
            if side and marker_side and marker_side != side:
                continue
            rx0 = float(row.get("x0", 0.0) or 0.0)
            rx1 = float(row.get("x1", 0.0) or 0.0)
            score = abs(rx0 - x0) + abs(rx1 - x1)
            if best_score is None or score < best_score:
                best = row
                best_score = score
        return best if best_score is not None and best_score <= 1e-4 else None

    def _editor_scope_visible(self, scope):
        scope = str(scope or "").strip().lower()
        if scope == "typical" and hasattr(self, "chk_show_typical"):
            return bool(self.chk_show_typical.isChecked())
        if scope == "side_slope" and hasattr(self, "chk_show_side_slope"):
            return bool(self.chk_show_side_slope.isChecked())
        if scope == "daylight" and hasattr(self, "chk_show_daylight"):
            return bool(self.chk_show_daylight.isChecked())
        return True

    def _apply_editor_edit(self):
        seg = self._current_editor_segment()
        target, message = self._editor_apply_target(seg)
        if not target:
            QtWidgets.QMessageBox.information(None, "Cross Section Editor", message or "Safe apply is not available for this target.")
            return
        validation_rows = self._editor_validation_rows(seg=seg, target=target, message=message)
        if str(target.get("kind", "") or "") == "edit_plan":
            self._apply_ph5_edit_plan_edit(target, seg, validation_rows)
            return
        if str(target.get("kind", "") or "") == "region_policy":
            self._apply_ph4_region_policy_edit(target, seg, validation_rows)
            return
        if str(target.get("kind", "") or "") == "assembly_slope":
            self._apply_ph4_slope_edit(target, seg, validation_rows)
            return
        new_width = _units.meters_from_user_length(self._unit_context(), float(self.spin_width.value()), unit=self._display_unit_label(), use_default="display")
        txn_open = self._open_editor_transaction("Cross Section Editor PH-4 Width Edit")
        if str(target.get("kind", "") or "") == "assembly":
            source_obj = target["assembly"]
            prop = str(target.get("property", "") or "")
            old_width = float(target.get("old_width", getattr(source_obj, prop, 0.0)) or 0.0)
            setattr(source_obj, prop, max(0.0, _units.model_length_from_meters(self._unit_context(), float(new_width))))
        else:
            typ_obj = target["typical"]
            idx = int(target["index"])
            widths = list(getattr(typ_obj, "ComponentWidths", []) or [])
            if idx < 0 or idx >= len(widths):
                self._abort_editor_transaction(txn_open)
                QtWidgets.QMessageBox.warning(None, "Cross Section Editor", "TypicalSectionTemplate width row is no longer available.")
                return
            old_width = float(target.get("old_width", widths[idx]) or 0.0)
            source_obj = typ_obj
            widths[idx] = max(0.0, float(new_width))
            typ_obj.ComponentWidths = list(widths)
        try:
            source_obj.touch()
        except Exception:
            pass
        sec = self._current_section_set()
        try:
            if sec is not None:
                sec.touch()
        except Exception:
            pass
        try:
            if self.doc is not None:
                self.doc.recompute()
        except Exception as exc:
            self._abort_editor_transaction(txn_open)
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", f"Width was updated, but recompute failed:\n{exc}")
            return
        marked = self._mark_downstream_dependents_stale(sec)
        self._record_editor_edit(
            sec,
            phase="PH-4",
            parameter="width",
            scope=str(self.cmb_edit_scope.currentText() or ""),
            target=seg,
            source_obj=source_obj,
            source_property=str(target.get("property", "ComponentWidths") or "ComponentWidths"),
            old_value=old_width,
            new_value=float(new_width),
            unit="m",
        )
        self._record_editor_validation(sec, validation_rows)
        self._commit_editor_transaction(txn_open)
        self._refresh_context(preserve_station=True)
        downstream_msg = f"\nMarked downstream stale: {len(marked)} object(s)." if marked else ""
        QtWidgets.QMessageBox.information(
            None,
            "Cross Section Editor",
            f"Applied PH-4 width edit to {getattr(source_obj, 'Label', getattr(source_obj, 'Name', 'source object'))}.\n"
            f"Width: {old_width:.3f} m -> {float(new_width):.3f} m{downstream_msg}",
        )

    def _apply_ph5_edit_plan_edit(self, target, seg, validation_rows):
        sec = self._current_section_set()
        if sec is None:
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", "No SectionSet is selected.")
            return
        if not self._confirm_station_only_edit(target):
            return

        txn_open = self._open_editor_transaction("Cross Section Editor PH-5 EditPlan Override")
        try:
            plan_obj = self._ensure_cross_section_edit_plan(sec)
        except Exception as exc:
            self._abort_editor_transaction(txn_open)
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", f"CrossSectionEditPlan setup failed:\n{exc}")
            return
        if plan_obj is None:
            self._abort_editor_transaction(txn_open)
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", "CrossSectionEditPlan could not be created.")
            return

        from freecad.Corridor_Road.objects.obj_cross_section_edit_plan import CrossSectionEditPlan

        records = [dict(row or {}) for row in list(CrossSectionEditPlan.records(plan_obj) or [])]
        match_idx = self._matching_cross_section_edit_record_index(records, target)
        created = match_idx < 0
        if created:
            record = {}
            old_value = float(target.get("old_value", target.get("value", 0.0)) or 0.0)
            edit_id = self._next_cross_section_edit_id(records, target)
        else:
            record = dict(records[match_idx] or {})
            old_value = float(record.get("Value", target.get("old_value", target.get("value", 0.0))) or 0.0)
            edit_id = str(record.get("Id", "") or "") or self._next_cross_section_edit_id(records, target)

        record.update(
            {
                "Id": edit_id,
                "Enabled": True,
                "Scope": str(target.get("scope_kind", "range") or "range"),
                "StartStation": float(target.get("start_station", 0.0) or 0.0),
                "EndStation": float(target.get("end_station", target.get("start_station", 0.0)) or target.get("start_station", 0.0)),
                "TransitionIn": float(target.get("transition_in", 0.0) or 0.0),
                "TransitionOut": float(target.get("transition_out", 0.0) or 0.0),
                "TargetId": str(target.get("target_id", "") or ""),
                "TargetSide": str(target.get("target_side", "") or ""),
                "TargetType": str(target.get("target_type", "") or ""),
                "Parameter": str(target.get("parameter", "") or ""),
                "Value": float(target.get("value", 0.0) or 0.0),
                "Unit": str(target.get("unit", "") or ""),
                "SourceScope": str(target.get("source_scope", "") or ""),
                "Notes": f"Cross Section Editor {str(self.cmb_edit_scope.currentText() or '').strip()}",
            }
        )
        if created:
            records.append(record)
        else:
            records[match_idx] = record

        try:
            CrossSectionEditPlan.apply_records(plan_obj, records)
            if hasattr(sec, "CrossSectionEditPlan"):
                sec.CrossSectionEditPlan = plan_obj
            if hasattr(sec, "UseCrossSectionEditPlan"):
                sec.UseCrossSectionEditPlan = True
            plan_obj.touch()
            sec.touch()
        except Exception as exc:
            self._abort_editor_transaction(txn_open)
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", f"CrossSectionEditPlan update failed:\n{exc}")
            return

        try:
            if self.doc is not None:
                self.doc.recompute()
        except Exception as exc:
            self._abort_editor_transaction(txn_open)
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", f"Override was stored, but recompute failed:\n{exc}")
            return

        marked = self._mark_downstream_dependents_stale(sec)
        self._record_editor_edit(
            sec,
            phase="PH-5",
            parameter=str(target.get("parameter", "") or ""),
            scope=str(self.cmb_edit_scope.currentText() or ""),
            target=seg,
            source_obj=plan_obj,
            source_property=f"edit:{edit_id}",
            old_value=old_value,
            new_value=float(target.get("value", 0.0) or 0.0),
            unit=str(target.get("unit", "") or "-"),
        )
        self._record_editor_validation(sec, validation_rows)
        self._commit_editor_transaction(txn_open)
        self._refresh_context(preserve_station=True)

        scope_kind = str(target.get("scope_kind", "range") or "range")
        if scope_kind == "station":
            scope_text = self._fmt_station(float(target.get("start_station", 0.0) or 0.0))
        else:
            scope_text = (
                f"{self._fmt_station(float(target.get('start_station', 0.0) or 0.0))} -> "
                f"{self._fmt_station(float(target.get('end_station', 0.0) or 0.0))}"
            )
        downstream_msg = f"\nMarked downstream stale: {len(marked)} object(s)." if marked else ""
        QtWidgets.QMessageBox.information(
            None,
            "Cross Section Editor",
            f"{'Created' if created else 'Updated'} PH-5 CrossSectionEditPlan override {edit_id}.\n"
            f"Scope: {scope_text}\n"
            f"Value: {old_value:.3f} {target.get('unit', '')} -> {float(target.get('value', 0.0) or 0.0):.3f} {target.get('unit', '')}{downstream_msg}",
        )

    def _confirm_station_only_edit(self, target):
        if str(target.get("scope_kind", "") or "") != "station":
            return True
        result = QtWidgets.QMessageBox.question(
            None,
            "Cross Section Editor",
            "This geometry edit applies only to the current station. Adjacent stations will not be changed, and corridor geometry may kink.\n\nApply station-only override?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        return result == QtWidgets.QMessageBox.Yes

    def _matching_cross_section_edit_record_index_by_id(self, records, edit_id):
        target_id = str(edit_id or "").strip()
        if not target_id:
            return -1
        for idx, record in enumerate(list(records or [])):
            if str(dict(record or {}).get("Id", "") or "").strip() == target_id:
                return int(idx)
        return -1

    def _disable_cross_section_edit_override(self, seg):
        migration = self._override_migration_context(seg, getattr(self, "_current_payload", None) or {})
        edit_id = str(migration.get("edit_id", "") or "").strip()
        plan_obj = migration.get("plan_obj")
        sec = self._current_section_set()
        if not edit_id or plan_obj is None or sec is None:
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", "No active local override is available for migration.")
            return
        result = QtWidgets.QMessageBox.question(
            None,
            "Cross Section Editor",
            f"Disable local override {edit_id}?\n\nUse this after a RegionPlan or other durable owner is ready to replace the local exception.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if result != QtWidgets.QMessageBox.Yes:
            return
        from freecad.Corridor_Road.objects.obj_cross_section_edit_plan import CrossSectionEditPlan

        records = [dict(row or {}) for row in list(CrossSectionEditPlan.records(plan_obj) or [])]
        match_idx = self._matching_cross_section_edit_record_index_by_id(records, edit_id)
        if match_idx < 0:
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", f"Local override {edit_id} is no longer available.")
            return
        record = dict(records[match_idx] or {})
        if not bool(record.get("Enabled", True)):
            QtWidgets.QMessageBox.information(None, "Cross Section Editor", f"Local override {edit_id} is already disabled.")
            return

        txn_open = self._open_editor_transaction("Cross Section Editor PH-7 Disable Local Override")
        record["Enabled"] = "false"
        records[match_idx] = record
        try:
            CrossSectionEditPlan.apply_records(plan_obj, records)
            plan_obj.touch()
            sec.touch()
        except Exception as exc:
            self._abort_editor_transaction(txn_open)
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", f"Disabling local override failed:\n{exc}")
            return
        try:
            if self.doc is not None:
                self.doc.recompute()
        except Exception as exc:
            self._abort_editor_transaction(txn_open)
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", f"Local override was disabled, but recompute failed:\n{exc}")
            return
        marked = self._mark_downstream_dependents_stale(sec)
        self._record_editor_edit(
            sec,
            phase="PH-7",
            parameter="override_disable",
            scope=str(self.cmb_edit_scope.currentText() or ""),
            target=seg,
            source_obj=plan_obj,
            source_property=f"disable:{edit_id}",
            old_value=1.0,
            new_value=0.0,
            unit="enabled",
        )
        self._commit_editor_transaction(txn_open)
        self._refresh_context(preserve_station=True)
        downstream_msg = f"\nMarked downstream stale: {len(marked)} object(s)." if marked else ""
        QtWidgets.QMessageBox.information(
            None,
            "Cross Section Editor",
            f"Disabled local override {edit_id} in {getattr(plan_obj, 'Label', getattr(plan_obj, 'Name', 'CrossSectionEditPlan'))}.{downstream_msg}",
        )

    def _ensure_cross_section_edit_plan(self, sec):
        from freecad.Corridor_Road.objects.obj_cross_section_edit_plan import CrossSectionEditPlan, ViewProviderCrossSectionEditPlan
        from freecad.Corridor_Road.objects.obj_section_set import resolve_cross_section_edit_plan_source

        plan_obj = resolve_cross_section_edit_plan_source(sec)
        if plan_obj is not None:
            if hasattr(sec, "UseCrossSectionEditPlan"):
                sec.UseCrossSectionEditPlan = True
            return plan_obj
        if self.doc is None:
            return None
        plan_obj = self.doc.addObject("Part::FeaturePython", "CrossSectionEditPlan")
        CrossSectionEditPlan(plan_obj)
        try:
            ViewProviderCrossSectionEditPlan(plan_obj.ViewObject)
        except Exception:
            pass
        plan_obj.Label = f"{getattr(sec, 'Label', 'Section Set')} Cross Section Edit Plan"
        if hasattr(sec, "CrossSectionEditPlan"):
            sec.CrossSectionEditPlan = plan_obj
        if hasattr(sec, "UseCrossSectionEditPlan"):
            sec.UseCrossSectionEditPlan = True
        return plan_obj

    def _matching_cross_section_edit_record_index(self, records, target, tol=1e-6):
        for idx, rec in enumerate(list(records or [])):
            if str(rec.get("Scope", "") or "").strip().lower() != str(target.get("scope_kind", "") or "").strip().lower():
                continue
            if str(rec.get("Parameter", "") or "").strip().lower() != str(target.get("parameter", "") or "").strip().lower():
                continue
            if str(rec.get("TargetId", "") or "").strip().upper() != str(target.get("target_id", "") or "").strip().upper():
                continue
            if str(rec.get("TargetSide", "") or "").strip().lower() != str(target.get("target_side", "") or "").strip().lower():
                continue
            if str(rec.get("TargetType", "") or "").strip().lower() != str(target.get("target_type", "") or "").strip().lower():
                continue
            if str(rec.get("SourceScope", "") or "").strip().lower() != str(target.get("source_scope", "") or "").strip().lower():
                continue
            if abs(float(rec.get("StartStation", 0.0) or 0.0) - float(target.get("start_station", 0.0) or 0.0)) > tol:
                continue
            if abs(float(rec.get("EndStation", 0.0) or 0.0) - float(target.get("end_station", 0.0) or 0.0)) > tol:
                continue
            if abs(float(rec.get("TransitionIn", 0.0) or 0.0) - float(target.get("transition_in", 0.0) or 0.0)) > tol:
                continue
            if abs(float(rec.get("TransitionOut", 0.0) or 0.0) - float(target.get("transition_out", 0.0) or 0.0)) > tol:
                continue
            return int(idx)
        return -1

    def _next_cross_section_edit_id(self, records, target):
        parameter = str(target.get("parameter", "") or "").strip().lower()
        code = "W" if parameter == "width" else "S"
        scope = "STA" if str(target.get("scope_kind", "") or "").strip().lower() == "station" else "RNG"
        side = str(target.get("target_side", "") or "").strip().lower()
        side_code = "L" if side == "left" else "R"
        prefix = f"EDIT_{side_code}_{code}_{scope}"
        existing = {str(rec.get("Id", "") or "").strip() for rec in list(records or []) if str(rec.get("Id", "") or "").strip()}
        for idx in range(1, 10000):
            candidate = f"{prefix}_{idx:03d}"
            if candidate not in existing:
                return candidate
        return f"{prefix}_{len(existing) + 1:03d}"

    def _apply_ph4_slope_edit(self, target, seg, validation_rows):
        source_obj = target["assembly"]
        prop = str(target.get("property", "") or "")
        old_slope = float(target.get("old_slope", getattr(source_obj, prop, 0.0)) or 0.0)
        new_slope = float(self.spin_slope.value())
        txn_open = self._open_editor_transaction("Cross Section Editor PH-4 Slope Edit")
        setattr(source_obj, prop, new_slope)
        try:
            source_obj.touch()
        except Exception:
            pass
        sec = self._current_section_set()
        try:
            if sec is not None:
                sec.touch()
        except Exception:
            pass
        try:
            if self.doc is not None:
                self.doc.recompute()
        except Exception as exc:
            self._abort_editor_transaction(txn_open)
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", f"Slope was updated, but recompute failed:\n{exc}")
            return
        marked = self._mark_downstream_dependents_stale(sec)
        self._record_editor_edit(
            sec,
            phase="PH-4",
            parameter="slope_pct",
            scope=str(self.cmb_edit_scope.currentText() or ""),
            target=seg,
            source_obj=source_obj,
            source_property=prop,
            old_value=old_slope,
            new_value=new_slope,
            unit="pct",
        )
        self._record_editor_validation(sec, validation_rows)
        self._commit_editor_transaction(txn_open)
        self._refresh_context(preserve_station=True)
        downstream_msg = f"\nMarked downstream stale: {len(marked)} object(s)." if marked else ""
        QtWidgets.QMessageBox.information(
            None,
            "Cross Section Editor",
            f"Applied PH-4 slope edit to {getattr(source_obj, 'Label', getattr(source_obj, 'Name', 'AssemblyTemplate'))}.\n"
            f"Slope: {old_slope:.3f} % -> {new_slope:.3f} %{downstream_msg}",
        )

    def _apply_ph4_region_policy_edit(self, target, seg, validation_rows):
        region_obj = target["region_plan"]
        records = [dict(row or {}) for row in list(target.get("records", []) or [])]
        idx = int(target.get("index", -1))
        if idx < 0 or idx >= len(records):
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", "RegionPlan row is no longer available.")
            return
        prop = str(target.get("property", "") or "")
        old_policy = str(records[idx].get(prop, "") or "")
        new_policy = str(self._selected_region_policy_value() or "")
        txn_open = self._open_editor_transaction("Cross Section Editor PH-4 Region Policy Edit")
        records[idx][prop] = new_policy
        try:
            RegionPlan.apply_records(region_obj, records)
        except Exception as exc:
            self._abort_editor_transaction(txn_open)
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", f"RegionPlan policy update failed:\n{exc}")
            return
        try:
            region_obj.touch()
        except Exception:
            pass
        sec = self._current_section_set()
        try:
            if sec is not None:
                sec.touch()
        except Exception:
            pass
        try:
            if self.doc is not None:
                self.doc.recompute()
        except Exception as exc:
            self._abort_editor_transaction(txn_open)
            QtWidgets.QMessageBox.warning(None, "Cross Section Editor", f"RegionPlan policy was updated, but recompute failed:\n{exc}")
            return
        marked = self._mark_downstream_dependents_stale(sec)
        self._record_editor_edit(
            sec,
            phase="PH-4",
            parameter="region_policy",
            scope=str(self.cmb_edit_scope.currentText() or ""),
            target=seg,
            source_obj=region_obj,
            source_property=f"{prop}:{str(target.get('region_id', '-') or '-')}",
            old_value=0.0,
            new_value=0.0,
            unit=f"{old_policy or '<inherit>'}->{new_policy or '<inherit>'}",
        )
        self._record_editor_validation(sec, validation_rows)
        self._commit_editor_transaction(txn_open)
        self._refresh_context(preserve_station=True)
        downstream_msg = f"\nMarked downstream stale: {len(marked)} object(s)." if marked else ""
        QtWidgets.QMessageBox.information(
            None,
            "Cross Section Editor",
            f"Applied PH-4 RegionPlan policy edit to {getattr(region_obj, 'Label', getattr(region_obj, 'Name', 'RegionPlan'))}.\n"
            f"{prop}: {old_policy or '<inherit>'} -> {new_policy or '<inherit>'}{downstream_msg}",
        )

    def _open_editor_transaction(self, label):
        doc = self.doc
        if doc is None or not hasattr(doc, "openTransaction"):
            return False
        try:
            doc.openTransaction(str(label or "Cross Section Editor Edit"))
            return True
        except Exception:
            return False

    def _commit_editor_transaction(self, txn_open):
        if not txn_open or self.doc is None or not hasattr(self.doc, "commitTransaction"):
            return
        try:
            self.doc.commitTransaction()
        except Exception:
            pass

    def _abort_editor_transaction(self, txn_open):
        if not txn_open or self.doc is None or not hasattr(self.doc, "abortTransaction"):
            return
        try:
            self.doc.abortTransaction()
        except Exception:
            pass

    def _record_editor_edit(self, sec, *, phase, parameter, scope, target, source_obj, source_property, old_value, new_value, unit):
        if sec is None:
            return
        try:
            if not hasattr(sec, "CrossSectionEditorEditRows"):
                sec.addProperty("App::PropertyStringList", "CrossSectionEditorEditRows", "CrossSectionEditor", "Cross Section Editor applied edit rows")
                sec.CrossSectionEditorEditRows = []
            if not hasattr(sec, "CrossSectionEditorLastEditSummary"):
                sec.addProperty("App::PropertyString", "CrossSectionEditorLastEditSummary", "CrossSectionEditor", "Last Cross Section Editor edit summary")
                sec.CrossSectionEditorLastEditSummary = ""
        except Exception:
            return
        row = "|".join(
            [
                "cross_section_editor_edit",
                f"phase={str(phase or '-')}",
                f"parameter={str(parameter or '-')}",
                f"scope={str(scope or '-')}",
                f"targetId={str(dict(target or {}).get('id', '-') or '-')}",
                f"targetType={str(dict(target or {}).get('type', '-') or '-')}",
                f"targetSide={str(dict(target or {}).get('side', '-') or '-')}",
                f"source={getattr(source_obj, 'Name', '-')}",
                f"property={str(source_property or '-')}",
                f"old={float(old_value):.6f}",
                f"new={float(new_value):.6f}",
                f"unit={str(unit or '-')}",
            ]
        )
        try:
            rows = list(getattr(sec, "CrossSectionEditorEditRows", []) or [])
            rows.append(row)
            sec.CrossSectionEditorEditRows = rows[-100:]
            sec.CrossSectionEditorLastEditSummary = row
        except Exception:
            pass

    def _refresh_editor_validation(self, *, seg=None, target=None, message=""):
        if not hasattr(self, "txt_validation"):
            return
        rows = self._editor_validation_rows(seg=seg, target=target, message=message)
        self.txt_validation.setPlainText("\n".join(rows) if rows else "validation|level=info|code=empty|message=No validation rows.")

    def _editor_validation_rows(self, *, seg=None, target=None, message=""):
        seg = dict(seg or self._current_editor_segment() or {})
        if target is None:
            target, message = self._editor_apply_target(seg)
        parameter = self._selected_edit_parameter()
        scope = str(self.cmb_edit_scope.currentText() or "")
        phase = str(dict(target or {}).get("phase", "PH-4") or "PH-4")
        rows = [
            f"validation|phase={phase}|level=info|code=target|"
            f"id={str(seg.get('id', '-') or '-')}|type={str(seg.get('type', '-') or '-')}|side={str(seg.get('side', '-') or '-')}",
            f"validation|phase={phase}|level=info|code=request|"
            f"scope={scope or '-'}|parameter={parameter}",
        ]
        if not target:
            rows.append(
                f"validation|phase={phase}|level=block|code=apply_guard|"
                f"message={str(message or 'Safe apply is not available for this target.')}"
            )
            return rows
        rows.append(
            f"validation|phase={phase}|level=ok|code=apply_guard|"
            f"kind={str(target.get('kind', '-') or '-')}|property={str(target.get('property', 'ComponentWidths') or 'ComponentWidths')}"
        )
        source_obj = target.get("typical", target.get("assembly", target.get("region_plan", None)))
        if source_obj is None and str(target.get("kind", "") or "") == "edit_plan":
            sec = self._current_section_set()
            source_obj = getattr(sec, "CrossSectionEditPlan", None) if sec is not None else None
        source_name = getattr(source_obj, "Name", "CrossSectionEditPlan(pending)") if source_obj is not None else "CrossSectionEditPlan(pending)"
        rows.append(f"validation|phase={phase}|level=ok|code=source_owner|source={source_name}")
        if parameter in ("width", "extra_width"):
            label = "Width" if parameter == "width" else "Extra width"
            rows.append(f"validation|phase={phase}|level=ok|code=value|message={label} is finite and non-negative.")
        elif parameter == "height":
            rows.append(f"validation|phase={phase}|level=ok|code=value|message=Height is finite.")
        elif parameter in ("slope", "back_slope"):
            label = "Slope percent" if parameter == "slope" else "Back slope percent"
            rows.append(f"validation|phase={phase}|level=ok|code=value|message={label} is finite.")
        else:
            rows.append(
                f"validation|phase={phase}|level=ok|code=value|"
                f"old={str(dict(target or {}).get('old_policy', '') or '<inherit>')}|new={self._selected_region_policy_value() or '<inherit>'}|"
                "message=RegionPlan policy token is selected from the guarded PH-4 list."
            )
        if str(target.get("kind", "") or "") == "edit_plan":
            rows.append(
                f"validation|phase={phase}|level=ok|code=edit_plan_scope|scope={str(target.get('scope_kind', '-') or '-')}|"
                f"start={float(target.get('start_station', 0.0) or 0.0):.3f}|end={float(target.get('end_station', 0.0) or 0.0):.3f}|"
                f"transitionIn={float(target.get('transition_in', 0.0) or 0.0):.3f}|transitionOut={float(target.get('transition_out', 0.0) or 0.0):.3f}"
            )
            if str(target.get("scope_kind", "") or "") == "station":
                rows.append(
                    f"validation|phase={phase}|level=warn|code=station_only_geometry|station={float(target.get('start_station', 0.0) or 0.0):.3f}|"
                    "message=Station-only geometry edits may create abrupt corridor transitions."
                )
        if bool(dict(target or {}).get("bench_aware", False)):
            rows.append(
                f"validation|phase={phase}|level=warn|code=bench_aware|"
                "message=Configured bench rows are preserved; this edit changes the owning side-slope parameter, not individual bench rows."
            )
        rows.extend(self._downstream_validation_rows(self._current_section_set()))
        return rows

    def _record_editor_validation(self, sec, validation_rows):
        if sec is None:
            return
        rows = [str(row or "") for row in list(validation_rows or []) if str(row or "").strip()]
        if not rows:
            return
        try:
            if not hasattr(sec, "CrossSectionEditorValidationRows"):
                sec.addProperty("App::PropertyStringList", "CrossSectionEditorValidationRows", "CrossSectionEditor", "Cross Section Editor validation rows")
                sec.CrossSectionEditorValidationRows = []
            if not hasattr(sec, "CrossSectionEditorLastValidationSummary"):
                sec.addProperty("App::PropertyString", "CrossSectionEditorLastValidationSummary", "CrossSectionEditor", "Last Cross Section Editor validation summary")
                sec.CrossSectionEditorLastValidationSummary = ""
        except Exception:
            return
        try:
            sec.CrossSectionEditorValidationRows = rows[-100:]
            sec.CrossSectionEditorLastValidationSummary = rows[-1]
        except Exception:
            pass

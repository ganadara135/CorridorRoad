# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets
from freecad.Corridor_Road.ui.task_cross_section_viewer import CrossSectionViewerTaskPanel


class CrossSectionEditorTaskPanel(CrossSectionViewerTaskPanel):
    """MVP editor shell built on the existing cross-section viewer."""

    def __init__(self):
        self._editor_overlay_items = []
        super().__init__()

    def _build_ui(self):
        viewer = super()._build_ui()
        viewer.setWindowTitle("CorridorRoad - Cross Section Editor")
        try:
            self.view._corridorroad_click_handler = self._handle_editor_canvas_click
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

        self.cmb_edit_scope = QtWidgets.QComboBox()
        self.cmb_edit_scope.addItems(["Global Source", "Active Region", "Station Range", "Current Station Only"])
        main.addWidget(QtWidgets.QLabel("Scope"))
        main.addWidget(self.cmb_edit_scope)

        self.txt_impact = QtWidgets.QPlainTextEdit()
        self.txt_impact.setReadOnly(True)
        self.txt_impact.setMinimumHeight(150)
        main.addWidget(QtWidgets.QLabel("Impact Preview"))
        main.addWidget(self.txt_impact)

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
        self.cmb_edit_scope.currentIndexChanged.connect(self._refresh_editor_impact)
        self.btn_preview_impact.clicked.connect(self._refresh_editor_impact)
        self.btn_apply_edit.clicked.connect(self._apply_editor_edit)
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

    def _on_editor_target_changed(self, *_args):
        self._refresh_editor_target()
        self._draw_selected_component_overlay()

    def _refresh_editor_target(self):
        if not hasattr(self, "txt_target"):
            return
        seg = self._current_editor_segment()
        if not seg:
            self.txt_target.setPlainText("Select a station with component segment rows to inspect it.")
            self.tbl_parameters.setRowCount(0)
            self._refresh_editor_impact()
            return
        lines = [
            f"Id: {str(seg.get('id', '-') or '-')}",
            f"Type: {str(seg.get('type', '-') or '-')}",
            f"Side: {str(seg.get('side', '-') or '-')}",
            f"Scope: {self._component_scope(seg)}",
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
        self.txt_target.setPlainText("\n".join(lines))
        params = [
            ("Id", str(seg.get("id", "-") or "-")),
            ("Type", str(seg.get("type", "-") or "-")),
            ("Side", str(seg.get("side", "-") or "-")),
            ("Scope", self._component_scope(seg)),
            ("Source Owner", self._source_owner_label(seg)),
            ("Generated Source", str(seg.get("source", "-") or "-")),
            ("Span", f"{float(seg.get('display_span', seg.get('span', 0.0)) or 0.0):.3f} {self._display_unit_label()}"),
            ("Order", str(seg.get("order", "-") or "-")),
            ("Shape", str(seg.get("shape", "-") or "-")),
            ("Editable Now", "No"),
        ]
        self.tbl_parameters.setRowCount(len(params))
        for row, (name, value) in enumerate(params):
            self.tbl_parameters.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self.tbl_parameters.setItem(row, 1, QtWidgets.QTableWidgetItem(value))
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
            self.txt_impact.setPlainText("No selected edit target.")
            return
        analysis = self._analyze_editor_impact(seg, payload)
        warnings = list(analysis.get("warnings", []) or [])
        blocked = list(analysis.get("blocked", []) or [])
        lines = [
            "PH-3 read-only impact analysis.",
            f"Target: {self._segment_label(seg)}",
            f"Parameter class: {analysis.get('parameter_class', '-')}",
            f"Requested scope: {analysis.get('scope', '-')}",
            f"Affected range: {analysis.get('range_text', '-')}",
            f"Affected stations: {analysis.get('station_count', 0)}",
            f"Timeline: {analysis.get('timeline_text', '-')}",
            f"Boundary stations to add: {analysis.get('boundary_text', '-')}",
            f"Region owner: {analysis.get('region_owner', '-')}",
            f"Structure overlap: {analysis.get('structure_overlap', '-')}",
            f"Downstream: {analysis.get('downstream', '-')}",
            "Apply is disabled until edit storage and recompute integration are implemented.",
        ]
        if blocked:
            lines.extend(["", "Blocked:"])
            lines.extend(f"- {w}" for w in blocked)
        if warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {w}" for w in warnings)
        self.txt_impact.setPlainText("\n".join(lines))

    def _analyze_editor_impact(self, seg, payload):
        station = float(payload.get("station", 0.0) or 0.0)
        scope = str(self.cmb_edit_scope.currentText() or "")
        rows = sorted(
            [dict(row or {}) for row in list(getattr(self, "_station_rows", []) or [])],
            key=lambda row: float(row.get("station", 0.0) or 0.0),
        )
        if not rows:
            rows = [{"station": station, "region_summary": str(payload.get("region_summary", "") or ""), "has_structure": bool(payload.get("has_structure", False)), "structure_summary": str(payload.get("structure_summary", "") or "")}]
        affected_rows = self._affected_station_rows(scope, station, rows, payload)
        affected_stations = [float(row.get("station", 0.0) or 0.0) for row in affected_rows]
        all_stations = [float(row.get("station", 0.0) or 0.0) for row in rows]
        prev_sta = max([s for s in all_stations if s < station], default=None)
        next_sta = min([s for s in all_stations if s > station], default=None)
        start_sta = min(affected_stations) if affected_stations else station
        end_sta = max(affected_stations) if affected_stations else station
        region_owner = self._impact_region_owner(payload, affected_rows)
        structure_overlap = self._impact_structure_overlap(payload, affected_rows)
        parameter_class = self._parameter_class(seg)
        warnings = []
        blocked = []
        if scope == "Current Station Only" and parameter_class in ("geometry", "topology", "daylight"):
            warnings.append("Station-only geometry edits can create abrupt corridor geometry.")
        if scope == "Station Range":
            warnings.append("Station range controls are not implemented yet; PH-3 preview uses previous/current/next stations.")
        if structure_overlap != "none":
            warnings.append("Structure overlap should be reviewed before applying geometry edits.")
        if parameter_class == "daylight" and structure_overlap != "none":
            blocked.append("Daylight edits that overlap structures require structure/region policy handling before apply.")
        boundary_stations = self._impact_boundary_stations(scope, start_sta, end_sta, prev_sta, next_sta)
        return {
            "scope": scope,
            "parameter_class": parameter_class,
            "station_count": len(affected_stations),
            "range_text": f"{self._fmt_station(start_sta)} -> {self._fmt_station(end_sta)}",
            "timeline_text": self._impact_timeline(prev_sta, station, next_sta),
            "boundary_text": ", ".join(self._fmt_station(s) for s in boundary_stations) if boundary_stations else "-",
            "region_owner": region_owner,
            "structure_overlap": structure_overlap,
            "downstream": self._impact_downstream_text(parameter_class),
            "warnings": warnings,
            "blocked": blocked,
        }

    def _affected_station_rows(self, scope, station, rows, payload):
        if scope == "Global Source":
            return list(rows)
        if scope == "Current Station Only":
            return [self._nearest_station_row(station, rows, payload)]
        if scope == "Station Range":
            stations = [float(row.get("station", 0.0) or 0.0) for row in rows]
            prev_sta = max([s for s in stations if s < station], default=None)
            next_sta = min([s for s in stations if s > station], default=None)
            keep = {station}
            if prev_sta is not None:
                keep.add(prev_sta)
            if next_sta is not None:
                keep.add(next_sta)
            return [row for row in rows if float(row.get("station", 0.0) or 0.0) in keep]
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

    def _impact_boundary_stations(self, scope, start_sta, end_sta, prev_sta, next_sta):
        if scope == "Global Source":
            return []
        if scope == "Current Station Only":
            return []
        out = [start_sta, end_sta]
        if scope == "Station Range":
            if prev_sta is not None:
                out.insert(0, prev_sta)
            if next_sta is not None:
                out.append(next_sta)
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

    def _impact_downstream_text(self, parameter_class):
        if parameter_class in ("geometry", "topology", "daylight"):
            return "SectionSet recompute required; corridor output should be marked stale after apply."
        return "SectionSet refresh required."

    def _fmt_station(self, station):
        return f"STA {self._format_display_length(float(station or 0.0))} {self._display_unit_label()}"

    def _clear_editor_overlay(self):
        if not hasattr(self, "scene"):
            self._editor_overlay_items = []
            return
        for item in list(getattr(self, "_editor_overlay_items", []) or []):
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self._editor_overlay_items = []

    def _add_editor_overlay_item(self, item):
        if item is None:
            return
        try:
            item.setZValue(1000.0)
        except Exception:
            pass
        self._editor_overlay_items.append(item)

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

        label = self._segment_label(seg)
        self._add_editor_overlay_item(
            self._add_scene_label(
                label,
                0.5 * (x0 + x1),
                y_top + 0.35,
                highlight,
                anchor="center",
                point_size=4.6,
                vertical_anchor="bottom",
            )
        )

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
        return self._select_component_at_scene_point(scene_pos)

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
        QtWidgets.QMessageBox.information(
            None,
            "Cross Section Editor",
            "Editing is not enabled yet. This MVP supports selection, inspection, and impact-preview scaffolding.",
        )

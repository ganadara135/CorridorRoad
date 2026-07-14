"""Alignment editor presentation for CorridorRoad v1."""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets


def configure_alignment_editor_task_panel_runtime(bindings) -> None:
    """Bind command/controller collaborators without importing the command module."""

    protected = {
        "_AlignmentCurvePreviewWidget",
        "V1AlignmentEditorTaskPanel",
        "configure_alignment_editor_task_panel_runtime",
    }
    for name, value in dict(bindings or {}).items():
        if name.startswith("__") or name in protected:
            continue
        globals()[name] = value


# Explicit runtime collaborators are replaced by the command callback map.
ALIGNMENT_PRESETS = None
AlignmentCurvePreviewRequest = None
AlignmentCurvePreviewService = None
AlignmentModel = None
App = None
Gui = None
_compile_ip_rows_to_element_rows = None
_distance = None
_ds = None
_fit_alignment_table_height = None
_format_compiled_review_line = None
_format_float = None
_format_pi_review_line = None
_normalized_ip_rows = None
_optional_float = None
_required_float = None
alignment_compiled_summary_rows = None
alignment_element_rows = None
alignment_ip_rows = None
alignment_model_from_editor_rows = None
alignment_pi_review_rows = None
alignment_preset_placement_names = None
alignment_preset_rows_for_placement = None
alignment_rows_from_local = None
alignment_rows_to_local = None
apply_alignment_ip_rows = None
apply_clickable_tab_style = None
create_blank_v1_alignment = None
ensure_v1_alignment_properties = None
find_project = None
find_sketch_objects = None
find_v1_alignment = None
get_design_standard = None
math = None
read_alignment_csv = None
sketch_to_alignment_rows = None
to_alignment_model = None
write_alignment_csv = None


class _AlignmentCurvePreviewWidget(QtWidgets.QWidget):
    """Small read-only canvas for Alignment curve preview rows."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = None
        self._zoom_factor = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._pan_last_pos = None
        self._zoom_changed_callback = None
        self.setMinimumHeight(440)
        try:
            self.setMinimumWidth(0)
            self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        except Exception:
            pass
        self.setStyleSheet("background: #101826; border: 1px solid #40516a;")
        try:
            self.setCursor(QtCore.Qt.OpenHandCursor)
        except Exception:
            pass

    def set_result(self, result) -> None:
        self._result = result
        self.update()

    def zoom_in(self) -> None:
        self._set_zoom(self._zoom_factor * 1.25)

    def zoom_out(self) -> None:
        self._set_zoom(self._zoom_factor / 1.25)

    def reset_zoom(self) -> None:
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._pan_last_pos = None
        self._set_zoom(1.0)

    def zoom_percent(self) -> int:
        return int(round(float(self._zoom_factor) * 100.0))

    def set_zoom_changed_callback(self, callback) -> None:
        self._zoom_changed_callback = callback

    def _set_zoom(self, value: float) -> None:
        self._zoom_factor = max(0.25, min(8.0, float(value or 1.0)))
        self.update()
        try:
            if self._zoom_changed_callback is not None:
                self._zoom_changed_callback()
        except Exception:
            pass

    def wheelEvent(self, event):  # noqa: N802 - Qt override
        try:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        except Exception:
            super().wheelEvent(event)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        try:
            if event.button() == QtCore.Qt.LeftButton:
                self._pan_last_pos = event.pos()
                self.setCursor(QtCore.Qt.ClosedHandCursor)
                event.accept()
                return
        except Exception:
            pass
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override
        try:
            if self._pan_last_pos is not None and event.buttons() & QtCore.Qt.LeftButton:
                delta = event.pos() - self._pan_last_pos
                self._pan_last_pos = event.pos()
                span_x, span_y = self._current_zoomed_span()
                width = max(1.0, float(self.width()) - 48.0)
                height = max(1.0, float(self.height()) - 48.0)
                self._pan_x -= float(delta.x()) / width * span_x
                self._pan_y += float(delta.y()) / height * span_y
                self.update()
                event.accept()
                return
        except Exception:
            pass
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt override
        try:
            if event.button() == QtCore.Qt.LeftButton:
                self._pan_last_pos = None
                self.setCursor(QtCore.Qt.OpenHandCursor)
                event.accept()
                return
        except Exception:
            pass
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            painter.fillRect(self.rect(), QtGui.QColor("#101826"))
            result = self._result
            rows = list(getattr(result, "point_rows", []) or []) if result is not None else []
            if not rows:
                painter.setPen(QtGui.QColor("#9aa8bd"))
                painter.drawText(self.rect(), QtCore.Qt.AlignCenter, "No Alignment curve preview yet.")
                return
            xs = [float(row.x) for row in rows]
            ys = [float(row.y) for row in rows]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            min_x, max_x, min_y, max_y = self._zoomed_bounds(min_x, max_x, min_y, max_y)
            span_x = max(1.0, max_x - min_x)
            span_y = max(1.0, max_y - min_y)
            margin = 24.0
            width = max(1.0, float(self.width()) - 2.0 * margin)
            height = max(1.0, float(self.height()) - 2.0 * margin)
            scale = min(width / span_x, height / span_y)

            def to_point(x_value: float, y_value: float):
                x = margin + (float(x_value) - min_x) * scale + 0.5 * (width - span_x * scale)
                y = margin + (max_y - float(y_value)) * scale + 0.5 * (height - span_y * scale)
                return QtCore.QPointF(x, y)

            evaluated = sorted(
                [row for row in rows if str(row.role) == "evaluated_path"],
                key=lambda row: (str(row.element_ref), float(row.station)),
            )
            by_element: dict[str, list[object]] = {}
            for row in evaluated:
                by_element.setdefault(str(row.element_ref), []).append(row)
            for element_rows in by_element.values():
                if len(element_rows) < 2:
                    continue
                path = QtGui.QPainterPath(to_point(element_rows[0].x, element_rows[0].y))
                for row in element_rows[1:]:
                    path.lineTo(to_point(row.x, row.y))
                painter.setPen(QtGui.QPen(QtGui.QColor("#36d3ff"), 2.0))
                painter.drawPath(path)

            self._draw_arc_guides(painter, result, to_point)

            painter.setPen(QtGui.QPen(QtGui.QColor("#f7a531"), 1.5))
            painter.setBrush(QtGui.QColor("#f7a531"))
            for row in rows:
                if str(row.role) != "source_points":
                    continue
                point = to_point(row.x, row.y)
                painter.drawEllipse(point, 3.5, 3.5)

            annotations = list(getattr(result, "annotation_rows", []) or [])
            label_rects: list[object] = []
            for annotation in annotations:
                kind = str(getattr(annotation, "kind", "") or "")
                if kind not in {"PC", "PI", "PT", "Curve Center", "Radius", "Delta Angle", "Curve Direction"}:
                    continue
                point = to_point(float(annotation.x), float(annotation.y))
                color = QtGui.QColor("#ffd23f") if kind in {"PC", "PI", "PT"} else QtGui.QColor("#f5f7fb")
                painter.setPen(QtGui.QPen(color, 1.0))
                painter.setBrush(color)
                painter.drawEllipse(point, 3.0, 3.0)
                label = str(getattr(annotation, "label", "") or kind)
                value = str(getattr(annotation, "value", "") or "")
                if value:
                    label = f"{label} {value}"
                self._draw_readable_label(painter, point, label, label_rects)

            painter.setPen(QtGui.QColor("#8ca0bc"))
            painter.drawText(10, self.height() - 10, "wheel=zoom, drag=pan, cyan=evaluated path, magenta=arc guide, orange=source points")
        finally:
            painter.end()

    def _zoomed_bounds(self, min_x: float, max_x: float, min_y: float, max_y: float) -> tuple[float, float, float, float]:
        zoom = max(0.25, min(8.0, float(self._zoom_factor or 1.0)))
        center_x = 0.5 * (float(min_x) + float(max_x)) + float(self._pan_x)
        center_y = 0.5 * (float(min_y) + float(max_y)) + float(self._pan_y)
        half_x = max(1.0e-9, 0.5 * (float(max_x) - float(min_x)) / zoom)
        half_y = max(1.0e-9, 0.5 * (float(max_y) - float(min_y)) / zoom)
        return center_x - half_x, center_x + half_x, center_y - half_y, center_y + half_y

    def _current_zoomed_span(self) -> tuple[float, float]:
        result = self._result
        rows = list(getattr(result, "point_rows", []) or []) if result is not None else []
        if not rows:
            return 1.0, 1.0
        xs = [float(row.x) for row in rows]
        ys = [float(row.y) for row in rows]
        zoom = max(0.25, min(8.0, float(self._zoom_factor or 1.0)))
        return max(1.0, max(xs) - min(xs)) / zoom, max(1.0, max(ys) - min(ys)) / zoom

    def _draw_arc_guides(self, painter, result, to_point) -> None:
        annotations = list(getattr(result, "annotation_rows", []) or [])
        by_element: dict[str, dict[str, object]] = {}
        for row in annotations:
            element_ref = str(getattr(row, "element_ref", "") or "")
            kind = str(getattr(row, "kind", "") or "")
            if not element_ref or kind not in {"PC", "PT", "Curve Center", "Radius", "Curve Direction"}:
                continue
            by_element.setdefault(element_ref, {})[kind] = row

        pen = QtGui.QPen(QtGui.QColor("#ff5fd2"))
        pen.setWidthF(2.4)
        try:
            pen.setStyle(QtCore.Qt.DashLine)
        except Exception:
            pass
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)

        for values in by_element.values():
            pc = values.get("PC")
            pt = values.get("PT")
            center = values.get("Curve Center")
            if pc is None or pt is None or center is None:
                continue
            center_x = float(getattr(center, "x", 0.0) or 0.0)
            center_y = float(getattr(center, "y", 0.0) or 0.0)
            pc_x = float(getattr(pc, "x", 0.0) or 0.0)
            pc_y = float(getattr(pc, "y", 0.0) or 0.0)
            pt_x = float(getattr(pt, "x", 0.0) or 0.0)
            pt_y = float(getattr(pt, "y", 0.0) or 0.0)
            radius = _distance(center_x, center_y, pc_x, pc_y)
            if radius <= 1.0e-9:
                continue
            direction_row = values.get("Curve Direction")
            direction = str(getattr(direction_row, "value", "") or "").lower() if direction_row is not None else ""
            angles = self._arc_angles(
                math.atan2(pc_y - center_y, pc_x - center_x),
                math.atan2(pt_y - center_y, pt_x - center_x),
                direction,
            )
            if len(angles) < 2:
                continue
            path = QtGui.QPainterPath()
            first_angle = angles[0]
            path.moveTo(to_point(center_x + radius * math.cos(first_angle), center_y + radius * math.sin(first_angle)))
            for angle in angles[1:]:
                path.lineTo(to_point(center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)))
            painter.drawPath(path)

    def _arc_angles(self, start: float, end: float, direction: str) -> list[float]:
        ccw_delta = (float(end) - float(start)) % (2.0 * math.pi)
        cw_delta = -((float(start) - float(end)) % (2.0 * math.pi))
        if str(direction).lower() == "left":
            delta = ccw_delta
        elif str(direction).lower() == "right":
            delta = cw_delta
        else:
            delta = ccw_delta if ccw_delta <= math.pi else -(2.0 * math.pi - ccw_delta)
        if abs(delta) <= 1.0e-12:
            return []
        steps = max(8, min(72, int(math.ceil(abs(delta) / (math.pi / 32.0)))))
        return [float(start) + delta * float(index) / float(steps) for index in range(steps + 1)]

    def _draw_readable_label(self, painter, anchor, text: str, label_rects: list[object]) -> None:
        font_metrics = painter.fontMetrics()
        label = str(text or "")
        offsets = [
            QtCore.QPointF(7.0, -7.0),
            QtCore.QPointF(7.0, 13.0),
            QtCore.QPointF(-font_metrics.horizontalAdvance(label) - 7.0, -7.0),
            QtCore.QPointF(-font_metrics.horizontalAdvance(label) - 7.0, 13.0),
            QtCore.QPointF(7.0, 31.0),
            QtCore.QPointF(-font_metrics.horizontalAdvance(label) - 7.0, 31.0),
        ]
        chosen_rect = None
        chosen_point = None
        for offset in offsets:
            point = anchor + offset
            rect = font_metrics.boundingRect(label).translated(int(point.x()), int(point.y()))
            rect = rect.adjusted(-3, -2, 3, 2)
            if not any(rect.intersects(existing) for existing in label_rects):
                chosen_rect = rect
                chosen_point = point
                break
        if chosen_rect is None:
            extra_y = 18.0 * float(len(label_rects) % 6)
            chosen_point = anchor + QtCore.QPointF(7.0, 49.0 + extra_y)
            chosen_rect = font_metrics.boundingRect(label).translated(int(chosen_point.x()), int(chosen_point.y())).adjusted(-3, -2, 3, 2)
        painter.setBrush(QtGui.QColor(16, 24, 38, 190))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(chosen_rect)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QColor("#e6edf7"))
        painter.drawText(chosen_point, label)
        label_rects.append(chosen_rect)


class V1AlignmentEditorTaskPanel:
    """v1 alignment editor with the v0 IP-based workflow as the primary UI."""

    def __init__(self, *, alignment=None, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.alignment = alignment or find_v1_alignment(self.document)
        self.form = self._build_ui()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._apply(close_after=True)

    def reject(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("ParametricRoad v1 - Alignment")

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Alignment")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self._alignment_label = QtWidgets.QLabel(self._alignment_summary_text())
        self._alignment_label.setStyleSheet("color: #dfe8ff; background: #263142; padding: 6px;")
        layout.addWidget(self._alignment_label)

        hint = QtWidgets.QLabel(
            "Edit PI rows the same way as the previous Alignment UI. "
            "Apply compiles the PI input into v1 station geometry used by stations, profile, sections, and corridor tools."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._tabs = QtWidgets.QTabWidget()
        apply_clickable_tab_style(self._tabs, "AlignmentEditorTabs")
        try:
            self._tabs.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        except Exception:
            pass
        self._tabs.addTab(self._build_pi_tab(), "PI Geometry")
        self._tabs.addTab(self._build_compiled_tab(), "Compiled v1 Geometry")
        layout.addWidget(self._tabs)

        button_row = QtWidgets.QHBoxLayout()
        review_button = QtWidgets.QPushButton("Review Alignment")
        review_button.clicked.connect(self._open_alignment_review)
        button_row.addWidget(review_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        button_row.addWidget(apply_button)
        button_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        self._load_ip_rows()
        self._load_element_rows()
        self._load_criteria()
        self._refresh_report()
        self._refresh_curve_preview()
        return widget

    def _build_pi_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        sketch_row = QtWidgets.QHBoxLayout()
        self._sketch_combo = QtWidgets.QComboBox()
        self._sketch_combo.setMaximumWidth(280)
        refresh_sketch_button = QtWidgets.QPushButton("Refresh")
        refresh_sketch_button.clicked.connect(self._refresh_sketches)
        load_sketch_button = QtWidgets.QPushButton("Load from Sketch")
        load_sketch_button.clicked.connect(self._load_from_sketch)
        sketch_row.addWidget(QtWidgets.QLabel("Sketch:"))
        sketch_row.addWidget(self._sketch_combo, 1)
        sketch_row.addWidget(refresh_sketch_button)
        sketch_row.addWidget(load_sketch_button)
        layout.addLayout(sketch_row)

        csv_row = QtWidgets.QHBoxLayout()
        self._csv_path = QtWidgets.QLineEdit()
        self._csv_path.setPlaceholderText("Path to alignment CSV file")
        browse_csv_button = QtWidgets.QPushButton("Browse CSV")
        browse_csv_button.clicked.connect(self._browse_csv)
        load_csv_button = QtWidgets.QPushButton("Load CSV")
        load_csv_button.clicked.connect(self._load_from_csv)
        save_csv_button = QtWidgets.QPushButton("Save CSV")
        save_csv_button.clicked.connect(self._save_csv)
        self._csv_export_coords_combo = QtWidgets.QComboBox()
        self._csv_export_coords_combo.addItem("Project default", "project")
        self._csv_export_coords_combo.addItem("World E/N", "world")
        self._csv_export_coords_combo.addItem("Local X/Y", "local")
        csv_row.addWidget(QtWidgets.QLabel("CSV:"))
        csv_row.addWidget(self._csv_path, 1)
        csv_row.addWidget(browse_csv_button)
        csv_row.addWidget(load_csv_button)
        csv_row.addWidget(save_csv_button)
        csv_row.addWidget(QtWidgets.QLabel("Export coords:"))
        csv_row.addWidget(self._csv_export_coords_combo)
        layout.addLayout(csv_row)

        preset_row = QtWidgets.QHBoxLayout()
        self._preset_combo = QtWidgets.QComboBox()
        self._preset_combo.addItems(list(ALIGNMENT_PRESETS.keys()))
        self._preset_placement_combo = QtWidgets.QComboBox()
        self._preset_placement_combo.addItems(alignment_preset_placement_names())
        self._preset_placement_combo.setCurrentText("Center on terrain")
        self._preset_note = QtWidgets.QLabel("")
        self._preset_note.setWordWrap(True)
        load_preset_button = QtWidgets.QPushButton("Load Preset")
        load_preset_button.clicked.connect(self._load_selected_preset)
        self._preset_combo.currentIndexChanged.connect(self._update_preset_note)
        self._preset_placement_combo.currentIndexChanged.connect(self._update_preset_note)
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        preset_row.addWidget(self._preset_combo)
        preset_row.addWidget(QtWidgets.QLabel("Placement:"))
        preset_row.addWidget(self._preset_placement_combo)
        preset_row.addWidget(load_preset_button)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)
        layout.addWidget(self._preset_note)

        self._ip_table = QtWidgets.QTableWidget(0, 4)
        self._ip_table.setHorizontalHeaderLabels(["X", "Y", "Radius (m)", "Transition Ls (m)"])
        try:
            self._ip_table.horizontalHeader().setStretchLastSection(True)
            self._ip_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self._ip_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            _fit_alignment_table_height(self._ip_table, visible_rows=6)
        except Exception:
            pass
        layout.addWidget(self._ip_table)

        row_buttons = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Row")
        add_button.clicked.connect(self._add_ip_row)
        remove_button = QtWidgets.QPushButton("Remove Row")
        remove_button.clicked.connect(self._remove_ip_row)
        sort_button = QtWidgets.QPushButton("Sort by X/Y")
        sort_button.clicked.connect(self._sort_ip_rows)
        row_buttons.addWidget(add_button)
        row_buttons.addWidget(remove_button)
        row_buttons.addWidget(sort_button)
        row_buttons.addStretch(1)
        layout.addLayout(row_buttons)

        criteria_group = QtWidgets.QGroupBox("Geometry / Criteria")
        form = QtWidgets.QFormLayout(criteria_group)
        self._use_transition_check = QtWidgets.QCheckBox("Use transition curves (S-C-S intent)")
        self._use_transition_check.setChecked(True)
        self._spiral_segments_spin = QtWidgets.QSpinBox()
        self._spiral_segments_spin.setRange(4, 128)
        self._spiral_segments_spin.setValue(16)
        self._design_standard_label = QtWidgets.QLabel("")
        self._design_standard_label.setWordWrap(True)
        self._design_speed_spin = self._double_spin(0.0, 300.0, 60.0, 1, " km/h")
        self._superelevation_spin = self._double_spin(0.0, 20.0, 8.0, 2, " %")
        self._side_friction_spin = self._double_spin(0.01, 0.40, 0.15, 3, "")
        self._min_radius_spin = self._double_spin(0.0, 100000.0, 0.0, 3, " m")
        self._min_radius_spin.setToolTip("0 = auto from selected standard and design speed")
        self._min_tangent_spin = self._double_spin(0.0, 100000.0, 20.0, 3, " m")
        self._min_transition_spin = self._double_spin(0.0, 100000.0, 20.0, 3, " m")
        form.addRow(self._use_transition_check)
        form.addRow("Design standard:", self._design_standard_label)
        form.addRow("Spiral segments:", self._spiral_segments_spin)
        form.addRow("Design speed:", self._design_speed_spin)
        form.addRow("Superelevation e:", self._superelevation_spin)
        form.addRow("Side friction f:", self._side_friction_spin)
        form.addRow("Min radius override:", self._min_radius_spin)
        form.addRow("Min tangent length:", self._min_tangent_spin)
        form.addRow("Min transition length:", self._min_transition_spin)
        layout.addWidget(criteria_group)

        self._report = QtWidgets.QPlainTextEdit()
        self._report.setReadOnly(True)
        self._report.setFixedHeight(60)
        self._report.setPlaceholderText("Criteria messages will appear after Apply.")
        layout.addWidget(self._report)

        self._update_preset_note()
        self._refresh_sketches()
        return tab

    def _build_compiled_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        note = QtWidgets.QLabel(
            "Read-only v1 geometry compiled from PI rows. Downstream v1 tools consume this station-based geometry."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self._element_table = QtWidgets.QTableWidget(0, 7)
        self._element_table.setHorizontalHeaderLabels(
            ["Kind", "Start STA", "End STA", "Length", "Points", "X Values", "Y Values"]
        )
        self._element_table.setMinimumHeight(220)
        try:
            self._element_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._element_table, 1)
        layout.addWidget(self._build_curve_preview_group())
        return tab

    def _build_curve_preview_group(self):
        group = QtWidgets.QGroupBox("Curve Preview")
        try:
            group.setMinimumWidth(0)
            group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        except Exception:
            pass
        layout = QtWidgets.QVBoxLayout(group)
        top_row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.setToolTip("Refresh Curve Preview")
        refresh_button.clicked.connect(self._refresh_curve_preview)
        top_row.addWidget(refresh_button)
        zoom_in_button = QtWidgets.QPushButton("+")
        zoom_in_button.setToolTip("Zoom In")
        zoom_in_button.clicked.connect(self._zoom_curve_preview_in)
        top_row.addWidget(zoom_in_button)
        zoom_out_button = QtWidgets.QPushButton("-")
        zoom_out_button.setToolTip("Zoom Out")
        zoom_out_button.clicked.connect(self._zoom_curve_preview_out)
        top_row.addWidget(zoom_out_button)
        zoom_reset_button = QtWidgets.QPushButton("Reset")
        zoom_reset_button.setToolTip("Reset Zoom and Pan")
        zoom_reset_button.clicked.connect(self._reset_curve_preview_zoom)
        top_row.addWidget(zoom_reset_button)
        self._curve_preview_zoom_label = QtWidgets.QLabel("100%")
        self._curve_preview_zoom_label.setMinimumWidth(48)
        self._curve_preview_zoom_label.setStyleSheet("color: #cbd7ea;")
        top_row.addWidget(self._curve_preview_zoom_label)
        top_row.addStretch(1)
        layout.addLayout(top_row)
        legend = QtWidgets.QLabel("wheel=zoom, drag=pan | cyan=evaluated path | magenta=arc guide | orange=source points")
        legend.setStyleSheet("color: #cbd7ea;")
        legend.setWordWrap(True)
        try:
            legend.setMinimumWidth(0)
            legend.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        except Exception:
            pass
        layout.addWidget(legend)
        self._curve_preview_widget = _AlignmentCurvePreviewWidget()
        self._curve_preview_widget.set_zoom_changed_callback(self._update_curve_preview_zoom_label)
        layout.addWidget(self._curve_preview_widget)
        self._curve_preview_info = QtWidgets.QPlainTextEdit()
        self._curve_preview_info.setReadOnly(True)
        self._curve_preview_info.setMaximumHeight(96)
        try:
            self._curve_preview_info.setMinimumWidth(0)
            self._curve_preview_info.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
            self._curve_preview_info.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
        self._curve_preview_info.setStyleSheet(
            "QPlainTextEdit { background: #1b2637; color: #dfe8ff; border: 1px solid #40516a; }"
        )
        layout.addWidget(self._curve_preview_info)
        return group

    def _zoom_curve_preview_in(self) -> None:
        widget = getattr(self, "_curve_preview_widget", None)
        if widget is not None:
            widget.zoom_in()
        self._update_curve_preview_zoom_label()

    def _zoom_curve_preview_out(self) -> None:
        widget = getattr(self, "_curve_preview_widget", None)
        if widget is not None:
            widget.zoom_out()
        self._update_curve_preview_zoom_label()

    def _reset_curve_preview_zoom(self) -> None:
        widget = getattr(self, "_curve_preview_widget", None)
        if widget is not None:
            widget.reset_zoom()
        self._update_curve_preview_zoom_label()

    def _update_curve_preview_zoom_label(self) -> None:
        label = getattr(self, "_curve_preview_zoom_label", None)
        widget = getattr(self, "_curve_preview_widget", None)
        if label is not None and widget is not None:
            label.setText(f"{widget.zoom_percent()}%")

    @staticmethod
    def _double_spin(minimum: float, maximum: float, value: float, decimals: int, suffix: str):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(float(minimum), float(maximum))
        spin.setDecimals(int(decimals))
        spin.setValue(float(value))
        if suffix:
            spin.setSuffix(str(suffix))
        return spin

    def _load_ip_rows(self) -> None:
        self._ip_table.setRowCount(0)
        if self.alignment is None:
            self._set_default_starter_rows()
            _fit_alignment_table_height(self._ip_table, visible_rows=6)
            return
        for row in alignment_ip_rows(self.alignment):
            self._append_ip_row(row)
        _fit_alignment_table_height(self._ip_table, visible_rows=6)

    def _set_default_starter_rows(self) -> None:
        preset_name = "Sample Local Alignment"
        preset = ALIGNMENT_PRESETS.get(preset_name, {})
        index = self._preset_combo.findText(preset_name)
        if index >= 0:
            self._preset_combo.setCurrentIndex(index)
        self._set_ip_rows_data(list(preset.get("rows", []) or []))
        self._set_status("Starter PI rows are loaded. Apply to create the v1 alignment.", ok=True)

    def _append_ip_row(self, row: dict[str, object]) -> None:
        row_index = self._ip_table.rowCount()
        self._ip_table.insertRow(row_index)
        values = [
            _format_float(row.get("x", 0.0)),
            _format_float(row.get("y", 0.0)),
            _format_float(row.get("radius", 0.0)),
            _format_float(row.get("transition_length", 0.0)),
        ]
        for col, value in enumerate(values):
            self._ip_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
        _fit_alignment_table_height(self._ip_table, visible_rows=6)

    def _load_element_rows(self) -> None:
        self._element_table.setRowCount(0)
        for row in alignment_compiled_summary_rows(self.alignment):
            self._append_element_row(row)

    def _append_element_row(self, row: dict[str, object]) -> None:
        row_index = self._element_table.rowCount()
        self._element_table.insertRow(row_index)
        values = [
            str(row.get("kind", "") or "tangent"),
            _format_float(row.get("station_start", 0.0)),
            _format_float(row.get("station_end", 0.0)),
            _format_float(row.get("length", 0.0)),
            str(int(row.get("point_count", 0) or 0)),
            str(row.get("x_values", "") or ""),
            str(row.get("y_values", "") or ""),
        ]
        for col, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem(value)
            try:
                item.setFlags(item.flags() & ~2)
            except Exception:
                pass
            self._element_table.setItem(row_index, col, item)

    def _load_criteria(self) -> None:
        alignment = self.alignment
        if alignment is None:
            self._refresh_design_standard_label()
            return
        ensure_v1_alignment_properties(alignment)
        self._use_transition_check.setChecked(bool(getattr(alignment, "UseTransitionCurves", True)))
        self._spiral_segments_spin.setValue(int(getattr(alignment, "SpiralSegments", 16) or 16))
        self._refresh_design_standard_label()
        self._design_speed_spin.setValue(float(getattr(alignment, "DesignSpeedKph", 60.0) or 60.0))
        self._superelevation_spin.setValue(float(getattr(alignment, "SuperelevationPct", 8.0) or 8.0))
        self._side_friction_spin.setValue(float(getattr(alignment, "SideFriction", 0.15) or 0.15))
        self._min_radius_spin.setValue(float(getattr(alignment, "MinRadius", 0.0) or 0.0))
        self._min_tangent_spin.setValue(float(getattr(alignment, "MinTangentLength", 20.0) or 20.0))
        self._min_transition_spin.setValue(float(getattr(alignment, "MinTransitionLength", 20.0) or 20.0))

    def _add_ip_row(self) -> None:
        rows = self._ip_rows(allow_empty=True)
        if rows:
            last = rows[-1]
            x = float(last["x"]) + 20.0
            y = float(last["y"])
        else:
            x = 0.0
            y = 0.0
        self._append_ip_row({"x": x, "y": y, "radius": 0.0, "transition_length": 0.0})
        self._set_status("Added a new PI row. Apply when ready.", ok=True)
        self._refresh_curve_preview()

    def _remove_ip_row(self) -> None:
        row_index = self._ip_table.currentRow()
        if row_index < 0:
            row_index = self._ip_table.rowCount() - 1
        if row_index >= 0:
            self._ip_table.removeRow(row_index)
            _fit_alignment_table_height(self._ip_table, visible_rows=6)
            self._set_status("Removed selected PI row. Apply when ready.", ok=True)
            self._refresh_curve_preview()

    def _sort_ip_rows(self) -> None:
        try:
            rows, _warnings = _normalized_ip_rows(self._ip_rows(allow_empty=True), min_rows=0)
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            return
        rows.sort(key=lambda item: (float(item["x"]), float(item["y"])))
        self._ip_table.setRowCount(0)
        for row in rows:
            self._append_ip_row(row)
        _fit_alignment_table_height(self._ip_table, visible_rows=6)
        self._set_status("PI rows sorted by X/Y. Apply when ready.", ok=True)
        self._refresh_curve_preview()

    def _load_selected_preset(self) -> None:
        preset = ALIGNMENT_PRESETS.get(str(self._preset_combo.currentText() or ""), {})
        rows = list(preset.get("rows", []) or [])
        placed = alignment_preset_rows_for_placement(
            rows,
            self._selected_preset_placement(),
            terrain_center=self._selected_terrain_center_for_preset(),
            project_origin=self._project_origin_anchor(),
        )
        self._set_ip_rows_data(list(placed.get("rows", []) or []))
        self._set_status(
            f"Preset loaded ({placed.get('placement')}). {placed.get('note')} Apply to compile v1 alignment geometry.",
            ok=True,
        )
        self._refresh_curve_preview()

    def _refresh_sketches(self) -> None:
        self._sketches = find_sketch_objects(self.document)
        self._sketch_combo.clear()
        for sketch in self._sketches:
            label = str(getattr(sketch, "Label", "") or getattr(sketch, "Name", "") or "Sketch")
            name = str(getattr(sketch, "Name", "") or "")
            self._sketch_combo.addItem(f"{label} ({name})")

    def _current_sketch(self):
        index = int(self._sketch_combo.currentIndex())
        if index < 0 or index >= len(getattr(self, "_sketches", [])):
            return None
        return self._sketches[index]

    def _load_from_sketch(self) -> None:
        sketch = self._current_sketch()
        if sketch is None:
            self._set_status("No sketch is selected.", ok=False)
            return
        try:
            rows = sketch_to_alignment_rows(sketch)
            self._set_ip_rows_data(rows)
            self._set_status(f"Loaded {len(rows)} PI row(s) from sketch. Apply when ready.", ok=True)
            self._refresh_curve_preview()
        except Exception as exc:
            self._set_status(f"Sketch import failed: {exc}", ok=False)

    def _browse_csv(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select Alignment CSV",
            str(self._csv_path.text() or ""),
            "CSV Files (*.csv *.txt);;All Files (*.*)",
        )
        if str(path or "").strip():
            self._csv_path.setText(str(path))

    def _load_from_csv(self) -> None:
        path = str(self._csv_path.text() or "").strip()
        if not path:
            self._set_status("CSV path is empty.", ok=False)
            return
        try:
            info = read_alignment_csv(
                path,
                doc_or_project=self.document,
                encoding="auto",
                delimiter="auto",
                has_header="auto",
                sort_mode="input",
                drop_consecutive_duplicates=True,
                clamp_negative=True,
                enforce_endpoints=True,
            )
            rows = list(info.get("rows", []) or [])
            metadata = dict(info.get("metadata", {}) or {})
            rows, coord_policy = alignment_rows_to_local(
                self.document,
                rows,
                input_coords=str(metadata.get("coordinate_input", "") or "auto"),
            )
            if len(rows) < 2:
                raise ValueError("CSV must provide at least 2 valid rows.")
            self._set_ip_rows_data(rows)
            self._set_status(
                f"Loaded {len(rows)} PI row(s) from CSV. {coord_policy.summary()}. Apply when ready.",
                ok=True,
            )
            self._refresh_curve_preview()
        except Exception as exc:
            self._set_status(f"CSV import failed: {exc}", ok=False)

    def _save_csv(self) -> None:
        try:
            rows = self._ip_rows(allow_empty=True)
        except Exception as exc:
            self._set_status(f"CSV export failed: {exc}", ok=False)
            return
        path = str(self._csv_path.text() or "").strip() or "alignment_pi.csv"
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Save Alignment CSV",
            path,
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*.*)",
        )
        if not str(path or "").strip():
            return
        try:
            export_rows = [
                (
                    float(row["x"]),
                    float(row["y"]),
                    float(row.get("radius", 0.0) or 0.0),
                    float(row.get("transition_length", 0.0) or 0.0),
                )
                for row in rows
            ]
            export_rows, coord_policy = alignment_rows_from_local(
                self.document,
                export_rows,
                output_coords=self._selected_csv_export_coords(),
            )
            x_header = "E" if coord_policy.output_coords == "World" else "X"
            y_header = "N" if coord_policy.output_coords == "World" else "Y"
            info = write_alignment_csv(
                path,
                export_rows,
                x_header=x_header,
                y_header=y_header,
                doc_or_project=self.document,
                coordinate_metadata=coord_policy.metadata(),
            )
            self._csv_path.setText(str(path))
            self._set_status(
                f"Saved {int(info.get('written', len(export_rows)))} PI row(s) to CSV. {coord_policy.summary()}.",
                ok=True,
            )
        except Exception as exc:
            self._set_status(f"CSV export failed: {exc}", ok=False)

    def _selected_csv_export_coords(self) -> str:
        if not hasattr(self, "_csv_export_coords_combo"):
            return "project"
        value = self._csv_export_coords_combo.currentData()
        return str(value or "project")

    def _set_ip_rows_data(self, rows) -> None:
        self._ip_table.setRowCount(0)
        for x, y, radius, transition_length in list(rows or []):
            self._append_ip_row(
                {
                    "x": float(x),
                    "y": float(y),
                    "radius": float(radius),
                    "transition_length": float(transition_length),
                }
            )
        _fit_alignment_table_height(self._ip_table, visible_rows=6)

    def _update_preset_note(self) -> None:
        if not hasattr(self, "_preset_note"):
            return
        preset = ALIGNMENT_PRESETS.get(str(self._preset_combo.currentText() or ""), {})
        placement = self._selected_preset_placement()
        note = str(preset.get("note", "") or "")
        if note:
            note = f"{note} Placement: {placement}."
        else:
            note = f"Preset placement: {placement}."
        self._preset_note.setText(note)

    def _selected_preset_placement(self) -> str:
        if not hasattr(self, "_preset_placement_combo"):
            return "Pattern only"
        return str(self._preset_placement_combo.currentText() or "Pattern only").strip()

    def _selected_terrain_center_for_preset(self) -> tuple[float, float] | None:
        terrain = self._selected_terrain_for_preset()
        if terrain is None:
            return None
        try:
            if hasattr(terrain, "Mesh") and terrain.Mesh is not None:
                box = terrain.Mesh.BoundBox
            else:
                box = terrain.Shape.BoundBox
        except Exception:
            return None
        return (
            0.5 * (float(box.XMin) + float(box.XMax)),
            0.5 * (float(box.YMin) + float(box.YMax)),
        )

    def _selected_terrain_for_preset(self):
        project = find_project(self.document)
        if project is not None:
            try:
                terrain = getattr(project, "Terrain", None)
                if self._is_surface_like(terrain):
                    return terrain
            except Exception:
                pass
        if Gui is not None:
            try:
                for obj in list(Gui.Selection.getSelection() or []):
                    if self._is_surface_like(obj):
                        return obj
            except Exception:
                pass
        for obj in list(getattr(self.document, "Objects", []) or []):
            if self._is_surface_like(obj):
                return obj
        return None

    @staticmethod
    def _is_surface_like(obj) -> bool:
        if obj is None:
            return False
        try:
            from freecad.Corridor_Road.objects import surface_sampling_core as _ssc

            return bool(_ssc.is_mesh_object(obj) or _ssc.is_shape_object(obj))
        except Exception:
            return False

    def _project_origin_anchor(self) -> tuple[float, float]:
        project = find_project(self.document)
        if project is None:
            return 0.0, 0.0
        try:
            return (
                float(getattr(project, "LocalOriginX", 0.0) or 0.0),
                float(getattr(project, "LocalOriginY", 0.0) or 0.0),
            )
        except Exception:
            return 0.0, 0.0

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            input_rows = self._ip_rows(allow_empty=True)
            _normalized_ip_rows(input_rows)
            if self.alignment is None:
                self.alignment = create_blank_v1_alignment(document=self.document)
            compiled = apply_alignment_ip_rows(
                self.alignment,
                input_rows,
                use_transition_curves=bool(self._use_transition_check.isChecked()),
                spiral_segments=int(self._spiral_segments_spin.value()),
                design_standard=self._project_design_standard(),
                design_speed_kph=float(self._design_speed_spin.value()),
                superelevation_pct=float(self._superelevation_spin.value()),
                side_friction=float(self._side_friction_spin.value()),
                min_radius=float(self._min_radius_spin.value()),
                min_tangent_length=float(self._min_tangent_spin.value()),
                min_transition_length=float(self._min_transition_spin.value()),
            )
            if self.document is not None:
                try:
                    self.document.recompute()
                except Exception:
                    pass
            self._load_element_rows()
            self._refresh_report()
            self._refresh_curve_preview()
            self._refresh_design_standard_label()
            self._set_status(f"Applied {len(compiled)} compiled v1 geometry row(s).", ok=True)
            self._alignment_label.setText(self._alignment_summary_text())
            self._show_apply_complete_message(len(compiled))
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Alignment", f"Alignment was not applied.\n{exc}")
            return False

    def _show_apply_complete_message(self, compiled_count: int) -> None:
        try:
            QtWidgets.QMessageBox.information(
                self.form,
                "Alignment",
                f"Alignment has been applied successfully.\nCompiled geometry rows: {int(compiled_count)}",
            )
        except Exception:
            pass

    def _ip_rows(self, *, allow_empty: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row_index in range(self._ip_table.rowCount()):
            x_text = self._item_text(self._ip_table, row_index, 0)
            y_text = self._item_text(self._ip_table, row_index, 1)
            radius_text = self._item_text(self._ip_table, row_index, 2)
            transition_text = self._item_text(self._ip_table, row_index, 3)
            if not x_text and not y_text and not radius_text and not transition_text and allow_empty:
                continue
            rows.append(
                {
                    "x": _required_float(x_text, f"Row {row_index + 1} X"),
                    "y": _required_float(y_text, f"Row {row_index + 1} Y"),
                    "radius": _optional_float(radius_text) or 0.0,
                    "transition_length": _optional_float(transition_text) or 0.0,
                }
            )
        return rows

    @staticmethod
    def _item_text(table, row_index: int, col_index: int) -> str:
        item = table.item(row_index, col_index)
        if item is None:
            return ""
        return str(item.text() or "").strip()

    def _refresh_report(self) -> None:
        if self.alignment is None:
            self._report.setPlainText("No v1 alignment object.")
            return
        ensure_v1_alignment_properties(self.alignment)
        lines = [
            f"Design standard: {str(getattr(self.alignment, 'CriteriaStandard', '') or 'KDS')}",
            f"Status: {str(getattr(self.alignment, 'CriteriaStatus', '') or 'OK')}",
            f"Total length: {_format_float(getattr(self.alignment, 'TotalLength', 0.0))} m",
            f"PI count: {len(alignment_ip_rows(self.alignment))}",
            f"Compiled element count: {len(alignment_element_rows(self.alignment))}",
            f"Compiled curve elements: {int(getattr(self.alignment, 'CompiledCurveElementCount', 0) or 0)}",
            f"Compiled transition elements: {int(getattr(self.alignment, 'CompiledTransitionElementCount', 0) or 0)}",
            f"Display edges: {int(getattr(self.alignment, 'CompiledEdgeCount', 0) or 0)}",
            f"Display status: {str(getattr(self.alignment, 'CompiledGeometryStatus', '') or 'pending')}",
        ]
        messages = list(getattr(self.alignment, "CriteriaMessages", []) or [])
        lines.append("")
        if messages:
            lines.append("Criteria warnings:")
            lines.extend(str(message) for message in messages)
        else:
            lines.append("Criteria warnings: none")
        pi_review_rows = alignment_pi_review_rows(self.alignment)
        if pi_review_rows:
            lines.append("")
            lines.append("PI Review:")
            for row in pi_review_rows:
                lines.append(_format_pi_review_line(row))
        compiled_rows = alignment_compiled_summary_rows(self.alignment)
        if compiled_rows:
            lines.append("")
            lines.append("Compiled Geometry:")
            for row in compiled_rows:
                lines.append(_format_compiled_review_line(row))
        self._report.setPlainText("\n".join(lines))

    def _refresh_curve_preview(self) -> None:
        if not hasattr(self, "_curve_preview_widget"):
            return
        try:
            alignment_model = self._alignment_model_for_curve_preview()
            result = AlignmentCurvePreviewService().evaluate(
                AlignmentCurvePreviewRequest(alignment=alignment_model, sample_interval=5.0)
            )
            self._curve_preview_widget.set_result(result)
            self._set_curve_preview_info(result)
        except Exception as exc:
            self._curve_preview_widget.set_result(None)
            self._curve_preview_info.setPlainText(f"Curve Preview unavailable: {exc}")

    def _alignment_model_for_curve_preview(self) -> AlignmentModel:
        try:
            input_rows = self._ip_rows(allow_empty=True)
            _normalized_ip_rows(input_rows)
            compiled = _compile_ip_rows_to_element_rows(
                self.alignment,
                input_rows,
                use_transition_curves=bool(self._use_transition_check.isChecked()),
                spiral_segments=int(self._spiral_segments_spin.value()),
            )
            return alignment_model_from_editor_rows(compiled)
        except Exception:
            model = to_alignment_model(self.alignment)
            if model is None:
                raise
            return model

    def _set_curve_preview_info(self, result) -> None:
        point_rows = list(getattr(result, "point_rows", []) or [])
        annotation_rows = list(getattr(result, "annotation_rows", []) or [])
        element_rows = list(getattr(result, "element_rows", []) or [])
        diagnostic_rows = list(getattr(result, "diagnostic_rows", []) or [])
        evaluated_count = len([row for row in point_rows if str(getattr(row, "role", "") or "") == "evaluated_path"])
        source_count = len([row for row in point_rows if str(getattr(row, "role", "") or "") == "source_points"])
        pc_pi_pt_count = len(
            [
                row
                for row in annotation_rows
                if str(getattr(row, "kind", "") or "") in {"PC", "PI", "PT"}
            ]
        )
        lines = [
            f"Status: {str(getattr(result, 'status', '') or 'empty')}",
            f"Stations: {_format_float(getattr(result, 'station_start', 0.0))} -> {_format_float(getattr(result, 'station_end', 0.0))}",
            f"Points: evaluated={evaluated_count}, source={source_count}, total={len(point_rows)}",
            f"Elements: {len(element_rows)}",
            f"PC/PI/PT labels: {pc_pi_pt_count}",
        ]
        curve_rows = [
            row
            for row in element_rows
            if "curve" in str(getattr(row, "kind", "") or "").lower()
        ]
        if curve_rows:
            lines.append("")
            lines.append("Curve elements:")
            for index, row in enumerate(curve_rows[:6], start=1):
                radius = float(getattr(row, "radius", 0.0) or 0.0)
                delta = float(getattr(row, "central_angle_deg", 0.0) or 0.0)
                status = str(getattr(row, "status", "") or "ok")
                direction = str(getattr(row, "curve_direction", "") or "-")
                notes = str(getattr(row, "notes", "") or "")
                quality = "resolved" if radius > 0.0 and delta > 0.0 else "needs source geometry"
                lines.append(
                    f"{index}. {str(getattr(row, 'element_id', '') or '')} | "
                    f"{str(getattr(row, 'kind', '') or '')} | "
                    f"STA {_format_float(getattr(row, 'station_start', 0.0))}-{_format_float(getattr(row, 'station_end', 0.0))} | "
                    f"R={_format_float(radius)}m | Delta={_format_float(delta)}deg | Dir={direction} | {status}/{quality}"
                )
                if notes:
                    lines.append(f"   {notes}")
            if len(curve_rows) > 6:
                lines.append(f"... plus {len(curve_rows) - 6} more curve element(s).")
        else:
            lines.append("")
            lines.append("Curve elements: none. Preview is showing tangent geometry only.")

        estimated = [
            row
            for row in diagnostic_rows
            if str(getattr(row, "kind", "") or "") in {"alignment_curve_pc_pi_pt_estimated"}
        ]
        missing = [
            row
            for row in diagnostic_rows
            if str(getattr(row, "severity", "") or "") in {"warning", "error"}
            and str(getattr(row, "kind", "") or "") not in {"alignment_curve_pc_pi_pt_estimated"}
        ]
        if estimated:
            lines.append("")
            lines.append("Estimated labels:")
            lines.extend(f"- {row.message}" for row in estimated[:4])
        warnings = [
            f"{row.severity}: {row.kind} - {row.message}"
            for row in missing
            if str(getattr(row, "severity", "") or "") in {"warning", "error"}
        ]
        if warnings:
            lines.append("")
            lines.append("Diagnostics:")
            lines.extend(warnings[:6])
        self._curve_preview_info.setPlainText("\n".join(lines))

    def _open_alignment_review(self) -> None:
        dialog = QtWidgets.QDialog(self.form)
        dialog.setWindowTitle("Review Alignment")
        dialog.resize(760, 520)
        layout = QtWidgets.QVBoxLayout(dialog)
        note = QtWidgets.QLabel("Review the v1 alignment source input and compiled station geometry.")
        note.setWordWrap(True)
        layout.addWidget(note)
        text = QtWidgets.QPlainTextEdit()
        text.setReadOnly(True)
        self._refresh_report()
        text.setPlainText(str(self._report.toPlainText() or ""))
        layout.addWidget(text, 1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close_button)
        layout.addLayout(row)
        dialog.exec_()

    def _alignment_summary_text(self) -> str:
        if self.alignment is None:
            return "No V1Alignment is available."
        return (
            f"Alignment: {str(getattr(self.alignment, 'Label', '') or getattr(self.alignment, 'Name', '') or '')} | "
            f"AlignmentId: {str(getattr(self.alignment, 'AlignmentId', '') or '')}"
        )

    def _project_design_standard(self) -> str:
        return get_design_standard(find_project(self.document) or self.document, default=_ds.DEFAULT_STANDARD)

    def _refresh_design_standard_label(self) -> None:
        if not hasattr(self, "_design_standard_label"):
            return
        project_standard = self._project_design_standard()
        applied_standard = ""
        if self.alignment is not None:
            applied_standard = _ds.normalize_standard(
                str(getattr(self.alignment, "CriteriaStandard", "") or project_standard),
                default=project_standard,
            )
        if applied_standard and applied_standard != project_standard:
            text = f"{project_standard} (from Project Setup; last applied: {applied_standard})"
        else:
            text = f"{project_standard} (from Project Setup)"
        self._design_standard_label.setText(text)

    def _set_status(self, message: str, *, ok: bool) -> None:
        return

    def _show_message(self, title: str, message: str) -> None:
        try:
            QtWidgets.QMessageBox.information(self.form, title, message)
        except Exception:
            pass


__all__ = [
    "_AlignmentCurvePreviewWidget",
    "V1AlignmentEditorTaskPanel",
    "configure_alignment_editor_task_panel_runtime",
]

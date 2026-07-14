"""Profile editor presentation for CorridorRoad v1."""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets


def configure_profile_editor_task_panel_runtime(bindings) -> None:
    """Bind command/controller collaborators without importing the command module."""

    protected = {
        "_ProfileCurvePreviewWidget",
        "V1ProfileEditorTaskPanel",
        "configure_profile_editor_task_panel_runtime",
    }
    for name, value in dict(bindings or {}).items():
        if name.startswith("__") or name in protected:
            continue
        globals()[name] = value


# Explicit runtime collaborators are replaced by the command callback map.
App = None
Gui = None
ProfileCurvePreviewRequest = None
ProfileCurvePreviewService = None
_ds = None
_existing_control_id = None
_existing_curve_id = None
_force_profile_preview_visibility = None
_format_float = None
_format_optional_float = None
_looks_like_tin_candidate = None
_make_profile_table_compact = None
_normalized_control_rows = None
_normalized_vertical_curve_rows = None
_optional_float = None
_profile_tin_candidate_sort_key = None
_required_float = None
_tin_surface_from_candidate = None
apply_clickable_tab_style = None
apply_profile_control_rows = None
apply_profile_vertical_curve_rows = None
auto_interpolate_profile_elevation_rows = None
build_profile_editor_handoff_context = None
create_blank_v1_profile = None
export_profile_control_rows_to_csv = None
find_project = None
find_v1_alignment = None
find_v1_profile = None
find_v1_stationing = None
generate_profile_vertical_curve_rows_from_controls = None
get_design_standard = None
import_profile_control_rows_from_csv = None
os = None
profile_control_rows = None
profile_eg_sample_rows = None
profile_model_from_editor_rows = None
profile_preset_names = None
profile_preset_rows_for_station_rows = None
profile_preset_vertical_curve_rows_for_station_rows = None
profile_rows_from_stationing = None
profile_station_check_rows = None
profile_vertical_curve_rows = None
run_legacy_command = None
show_profile_preview_object = None


class _ProfileCurvePreviewWidget(QtWidgets.QWidget):
    """Small read-only 2D profile curve preview canvas."""

    def __init__(self):
        super().__init__()
        self._result = None
        self._error = ""
        self._zoom_factor = 1.0
        self._pan_station = 0.0
        self._pan_elevation = 0.0
        self._pan_last_pos = None
        self._zoom_changed_callback = None
        try:
            self.setMinimumHeight(340)
            self.setMaximumHeight(460)
            self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self.setCursor(QtCore.Qt.OpenHandCursor)
        except Exception:
            pass

    def set_result(self, result) -> None:
        self._result = result
        self._error = ""
        self.update()

    def set_error(self, message: str) -> None:
        self._result = None
        self._error = str(message or "")
        self.update()

    def zoom_in(self) -> None:
        self._set_zoom(self._zoom_factor * 1.25)

    def zoom_out(self) -> None:
        self._set_zoom(self._zoom_factor / 1.25)

    def reset_zoom(self) -> None:
        self._pan_station = 0.0
        self._pan_elevation = 0.0
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

    def wheelEvent(self, event):  # noqa: N802 - Qt override name
        try:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        except Exception:
            super().wheelEvent(event)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override name
        try:
            if event.button() == QtCore.Qt.LeftButton:
                self._pan_last_pos = event.pos()
                self.setCursor(QtCore.Qt.ClosedHandCursor)
                event.accept()
                return
        except Exception:
            pass
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override name
        try:
            if self._pan_last_pos is not None and event.buttons() & QtCore.Qt.LeftButton:
                delta = event.pos() - self._pan_last_pos
                self._pan_last_pos = event.pos()
                station_span, elevation_span = self._current_zoomed_span()
                width = max(1.0, float(self.width()) - 60.0)
                height = max(1.0, float(self.height()) - 52.0)
                self._pan_station -= float(delta.x()) / width * station_span
                self._pan_elevation += float(delta.y()) / height * elevation_span
                self.update()
                event.accept()
                return
        except Exception:
            pass
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt override name
        try:
            if event.button() == QtCore.Qt.LeftButton:
                self._pan_last_pos = None
                self.setCursor(QtCore.Qt.OpenHandCursor)
                event.accept()
                return
        except Exception:
            pass
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override name
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
            rect = self.rect()
            painter.fillRect(rect, QtGui.QColor("#101821"))
            plot = rect.adjusted(42, 18, -18, -34)
            painter.fillRect(plot, QtGui.QColor("#0c1923"))
            painter.setPen(QtGui.QPen(QtGui.QColor("#3f5264")))
            painter.drawRect(plot)
            if self._error:
                painter.setPen(QtGui.QColor("#f0c36a"))
                painter.drawText(plot.adjusted(10, 10, -10, -10), QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop | QtCore.Qt.TextWordWrap, self._error)
                return
            result = self._result
            if result is None or not list(getattr(result, "point_rows", []) or []):
                painter.setPen(QtGui.QColor("#cfd7e6"))
                painter.drawText(plot, QtCore.Qt.AlignCenter, "Curve preview is not available.")
                return
            bounds = self._zoomed_bounds(self._bounds(result))
            self._draw_grid(painter, plot, bounds)
            self._draw_curve(painter, plot, bounds, result, "source_tangent", "#f08a30", 1.8)
            self._draw_vertical_curve_guides(painter, plot, bounds, result)
            self._draw_curve(painter, plot, bounds, result, "evaluated_curve", "#2de4ee", 2.6)
            self._draw_annotations(painter, plot, bounds, result)
        finally:
            painter.end()

    def _bounds(self, result) -> tuple[float, float, float, float]:
        points = list(getattr(result, "point_rows", []) or [])
        stations = [float(getattr(row, "station", 0.0) or 0.0) for row in points]
        elevations = [float(getattr(row, "elevation", 0.0) or 0.0) for row in points]
        for row in list(getattr(result, "annotation_rows", []) or []):
            stations.append(float(getattr(row, "station", 0.0) or 0.0))
            elevations.append(float(getattr(row, "elevation", 0.0) or 0.0))
        station_min = min(stations)
        station_max = max(stations)
        elevation_min = min(elevations)
        elevation_max = max(elevations)
        station_pad = max(1.0, (station_max - station_min) * 0.04)
        elevation_pad = max(1.0, (elevation_max - elevation_min) * 0.16)
        return station_min - station_pad, station_max + station_pad, elevation_min - elevation_pad, elevation_max + elevation_pad

    def _zoomed_bounds(self, bounds: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        station_min, station_max, elevation_min, elevation_max = bounds
        zoom = max(0.25, min(8.0, float(self._zoom_factor or 1.0)))
        station_center = 0.5 * (station_min + station_max) + float(self._pan_station)
        elevation_center = 0.5 * (elevation_min + elevation_max) + float(self._pan_elevation)
        station_half = max(1.0e-9, 0.5 * (station_max - station_min) / zoom)
        elevation_half = max(1.0e-9, 0.5 * (elevation_max - elevation_min) / zoom)
        return (
            station_center - station_half,
            station_center + station_half,
            elevation_center - elevation_half,
            elevation_center + elevation_half,
        )

    def _current_zoomed_span(self) -> tuple[float, float]:
        result = self._result
        if result is None:
            return 1.0, 1.0
        station_min, station_max, elevation_min, elevation_max = self._bounds(result)
        zoom = max(0.25, min(8.0, float(self._zoom_factor or 1.0)))
        return max(1.0e-9, station_max - station_min) / zoom, max(1.0e-9, elevation_max - elevation_min) / zoom

    def _point(self, plot, bounds, station: float, elevation: float):
        station_min, station_max, elevation_min, elevation_max = bounds
        width = max(float(plot.width()), 1.0)
        height = max(float(plot.height()), 1.0)
        x = float(plot.left()) + ((float(station) - station_min) / max(station_max - station_min, 1.0e-9)) * width
        y = float(plot.bottom()) - ((float(elevation) - elevation_min) / max(elevation_max - elevation_min, 1.0e-9)) * height
        return QtCore.QPointF(x, y)

    def _draw_grid(self, painter, plot, bounds) -> None:
        station_min, station_max, elevation_min, elevation_max = bounds
        painter.setPen(QtGui.QPen(QtGui.QColor("#263746")))
        for index in range(1, 5):
            x = plot.left() + plot.width() * index / 5.0
            painter.drawLine(QtCore.QPointF(x, plot.top()), QtCore.QPointF(x, plot.bottom()))
            y = plot.top() + plot.height() * index / 5.0
            painter.drawLine(QtCore.QPointF(plot.left(), y), QtCore.QPointF(plot.right(), y))
        painter.setPen(QtGui.QColor("#8fa8bb"))
        painter.drawText(plot.left(), plot.bottom() + 18, f"STA {station_min:.1f}")
        painter.drawText(plot.right() - 90, plot.bottom() + 18, f"STA {station_max:.1f}")
        painter.drawText(4, plot.top() + 12, f"EL {elevation_max:.1f}")
        painter.drawText(4, plot.bottom(), f"EL {elevation_min:.1f}")

    def _draw_curve(self, painter, plot, bounds, result, role: str, color: str, width: float) -> None:
        rows = [
            row
            for row in list(getattr(result, "point_rows", []) or [])
            if str(getattr(row, "role", "") or "") == role
        ]
        rows.sort(key=lambda row: float(getattr(row, "station", 0.0) or 0.0))
        if len(rows) < 2:
            return
        pen = QtGui.QPen(QtGui.QColor(color))
        pen.setWidthF(width)
        painter.setPen(pen)
        previous = None
        for row in rows:
            point = self._point(plot, bounds, float(getattr(row, "station", 0.0) or 0.0), float(getattr(row, "elevation", 0.0) or 0.0))
            if previous is not None:
                painter.drawLine(previous, point)
            previous = point

    def _draw_annotations(self, painter, plot, bounds, result) -> None:
        label_rects: list[object] = []
        for row in list(getattr(result, "annotation_rows", []) or []):
            kind = str(getattr(row, "kind", "") or "")
            if kind not in {"BVC", "PVI", "EVC", "HP", "LP"}:
                continue
            point = self._point(plot, bounds, float(getattr(row, "station", 0.0) or 0.0), float(getattr(row, "elevation", 0.0) or 0.0))
            color = QtGui.QColor("#f4d35e")
            if kind == "PVI":
                color = QtGui.QColor("#f5f7fa")
            elif kind in {"HP", "LP"}:
                color = QtGui.QColor("#76e28a")
            painter.setPen(QtGui.QPen(QtGui.QColor("#101821")))
            painter.setBrush(color)
            painter.drawEllipse(point, 4.5, 4.5)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(QtGui.QColor("#e6edf7"))
            value = str(getattr(row, "value", "") or "")
            label = kind if not value else f"{kind} {value}"
            self._draw_readable_label(painter, point, label, label_rects)

    def _draw_vertical_curve_guides(self, painter, plot, bounds, result) -> None:
        points = [
            row
            for row in list(getattr(result, "point_rows", []) or [])
            if str(getattr(row, "role", "") or "") == "evaluated_curve"
        ]
        if len(points) < 2:
            return
        for curve in list(getattr(result, "curve_rows", []) or []):
            curve_id = str(getattr(curve, "curve_id", "") or "")
            station_start = float(getattr(curve, "station_start", 0.0) or 0.0)
            station_end = float(getattr(curve, "station_end", station_start) or station_start)
            if station_end < station_start:
                station_start, station_end = station_end, station_start
            curve_points = [
                row
                for row in points
                if (
                    str(getattr(row, "curve_ref", "") or "") == curve_id
                    or station_start - 1.0e-9 <= float(getattr(row, "station", 0.0) or 0.0) <= station_end + 1.0e-9
                )
            ]
            curve_points.sort(key=lambda row: float(getattr(row, "station", 0.0) or 0.0))
            if len(curve_points) < 2:
                continue
            pen = QtGui.QPen(QtGui.QColor("#a76dff"))
            pen.setWidthF(5.4)
            try:
                pen.setCapStyle(QtCore.Qt.RoundCap)
                pen.setJoinStyle(QtCore.Qt.RoundJoin)
            except Exception:
                pass
            painter.setPen(pen)
            path = QtGui.QPainterPath(
                self._point(
                    plot,
                    bounds,
                    float(getattr(curve_points[0], "station", 0.0) or 0.0),
                    float(getattr(curve_points[0], "elevation", 0.0) or 0.0),
                )
            )
            for row in curve_points[1:]:
                path.lineTo(
                    self._point(
                        plot,
                        bounds,
                        float(getattr(row, "station", 0.0) or 0.0),
                        float(getattr(row, "elevation", 0.0) or 0.0),
                    )
                )
            painter.drawPath(path)

            label_station = float(getattr(curve, "high_low_station", 0.0) or 0.0)
            label_elevation = float(getattr(curve, "high_low_elevation", 0.0) or 0.0)
            if label_station <= 0.0:
                mid_row = curve_points[len(curve_points) // 2]
                label_station = float(getattr(mid_row, "station", 0.0) or 0.0)
                label_elevation = float(getattr(mid_row, "elevation", 0.0) or 0.0)
            guide_label = self._vertical_curve_label(curve)
            label_point = self._point(plot, bounds, label_station, label_elevation)
            painter.setPen(QtGui.QColor("#f5f0ff"))
            self._draw_readable_label(painter, label_point, guide_label, [])

    @staticmethod
    def _vertical_curve_label(curve) -> str:
        high_low = str(getattr(curve, "high_low_kind", "") or "").upper()
        algebraic = float(getattr(curve, "algebraic_grade_difference", 0.0) or 0.0)
        curve_kind = str(getattr(curve, "kind", "") or "parabolic_vertical_curve").lower()
        base = "Parabola" if "parabolic" in curve_kind or "vertical_curve" in curve_kind else str(getattr(curve, "kind", "") or "Curve")
        if high_low == "HP" or algebraic < 0.0:
            return f"{base} Crest"
        if high_low == "LP" or algebraic > 0.0:
            return f"{base} Sag"
        return base

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
        painter.setBrush(QtGui.QColor(16, 24, 33, 190))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(chosen_rect)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QColor("#e6edf7"))
        painter.drawText(chosen_point, label)
        label_rects.append(chosen_rect)


class V1ProfileEditorTaskPanel:
    """Tabbed editor for v1 profile source rows and references."""

    def __init__(self, *, profile=None, document=None, preferred_alignment=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.profile = profile or find_v1_profile(self.document)
        self.preferred_alignment = preferred_alignment
        self._needs_stationing_notice = False
        self._stationing_loaded_rows = 0
        self.form = self._build_ui()
        self._refresh_curve_preview()
        if self._needs_stationing_notice:
            self._show_message(
                "Profile",
                "Stations have not been generated yet.\nOpen `Stations`, click Apply, then reopen Profile.",
            )

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
        widget.setWindowTitle("ParametricRoad v1 - Profile Editor")
        try:
            widget.setMinimumWidth(320)
            widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        except Exception:
            pass

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        try:
            layout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        except Exception:
            pass

        title = QtWidgets.QLabel("Profile Editor")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self._profile_label = QtWidgets.QLabel(self._profile_summary_text())
        self._profile_label.setStyleSheet("color: #dfe8ff; background: #263142; padding: 6px;")
        layout.addWidget(self._profile_label)

        hint = QtWidgets.QLabel(
            "Edit station/elevation PVI rows. Apply creates or updates the V1Profile source object."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        data_row = QtWidgets.QGridLayout()
        data_row.setHorizontalSpacing(8)
        data_row.setVerticalSpacing(6)
        data_row.addWidget(QtWidgets.QLabel("Profile data:"), 0, 0)
        preset_button = QtWidgets.QPushButton("Preset Data")
        preset_button.clicked.connect(self._apply_preset_data)
        data_row.addWidget(preset_button, 0, 1)
        import_button = QtWidgets.QPushButton("Import CSV")
        import_button.clicked.connect(self._import_profile_csv)
        data_row.addWidget(import_button, 0, 2)
        export_button = QtWidgets.QPushButton("Export CSV")
        export_button.clicked.connect(self._export_profile_csv)
        data_row.addWidget(export_button, 0, 3)
        interpolate_button = QtWidgets.QPushButton("Auto Interpolate Elevations")
        interpolate_button.clicked.connect(self._auto_interpolate_elevations)
        data_row.addWidget(interpolate_button, 1, 1, 1, 3)
        data_row.setColumnStretch(4, 1)
        layout.addLayout(data_row)

        self._tabs = QtWidgets.QTabWidget()
        apply_clickable_tab_style(self._tabs, "ProfileEditorTabs")
        try:
            self._tabs.setMinimumWidth(0)
        except Exception:
            pass
        self._tabs.addTab(self._build_fg_profile_tab(), "FG Profile")
        self._tabs.addTab(self._build_vertical_curves_tab(), "Vertical Curves")
        self._tabs.addTab(self._build_eg_reference_tab(), "EG Reference")
        self._tabs.addTab(self._build_station_check_tab(), "Station Check")
        layout.addWidget(self._tabs, 1)

        self._refresh_reference_tabs()
        layout.addWidget(self._build_curve_preview_group())

        button_grid = QtWidgets.QGridLayout()
        button_grid.setHorizontalSpacing(8)
        button_grid.setVerticalSpacing(6)
        show_button = QtWidgets.QPushButton("Show Profile Preview")
        show_button.clicked.connect(self._show_current_profile)
        button_grid.addWidget(show_button, 0, 0)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        button_grid.addWidget(apply_button, 0, 1)
        open_review_button = QtWidgets.QPushButton("Review Plan/Profile")
        open_review_button.clicked.connect(self._open_review)
        button_grid.addWidget(open_review_button, 0, 2)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_grid.addWidget(close_button, 0, 4)
        button_grid.setColumnStretch(3, 1)
        layout.addLayout(button_grid)

        return widget

    def _build_fg_profile_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        note = QtWidgets.QLabel("Finished-grade PVI/control rows. These rows are the editable v1 profile source.")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._table = QtWidgets.QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Station", "Elevation", "Kind"])
        self._table.setMinimumHeight(190)
        _make_profile_table_compact(self._table, [82, 86, 120])
        layout.addWidget(self._table)
        self._load_rows()

        edit_row = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add PVI")
        add_button.clicked.connect(self._add_row)
        edit_row.addWidget(add_button)
        delete_button = QtWidgets.QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_selected_rows)
        edit_row.addWidget(delete_button)
        sort_button = QtWidgets.QPushButton("Sort by Station")
        sort_button.clicked.connect(self._sort_table_rows)
        edit_row.addWidget(sort_button)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)
        return tab

    def _build_curve_preview_group(self):
        group = QtWidgets.QGroupBox("Curve Preview")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        toolbar = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh Curve Preview")
        refresh_button.clicked.connect(self._refresh_curve_preview)
        toolbar.addWidget(refresh_button)
        zoom_in_button = QtWidgets.QPushButton("Zoom In")
        zoom_in_button.clicked.connect(self._zoom_curve_preview_in)
        toolbar.addWidget(zoom_in_button)
        zoom_out_button = QtWidgets.QPushButton("Zoom Out")
        zoom_out_button.clicked.connect(self._zoom_curve_preview_out)
        toolbar.addWidget(zoom_out_button)
        zoom_reset_button = QtWidgets.QPushButton("Reset Zoom")
        zoom_reset_button.clicked.connect(self._reset_curve_preview_zoom)
        toolbar.addWidget(zoom_reset_button)
        self._curve_preview_zoom_label = QtWidgets.QLabel("100%")
        self._curve_preview_zoom_label.setMinimumWidth(48)
        self._curve_preview_zoom_label.setStyleSheet("color: #dce8f7;")
        toolbar.addWidget(self._curve_preview_zoom_label)
        toolbar.addWidget(QtWidgets.QLabel("wheel=zoom, drag=pan, cyan=evaluated curve, purple=parabola guide, orange=source tangent"))
        toolbar.addStretch(1)
        layout.addLayout(toolbar)
        self._curve_preview_widget = _ProfileCurvePreviewWidget()
        self._curve_preview_widget.set_zoom_changed_callback(self._update_curve_preview_zoom_label)
        layout.addWidget(self._curve_preview_widget)
        self._curve_preview_info = QtWidgets.QPlainTextEdit()
        self._curve_preview_info.setReadOnly(True)
        self._curve_preview_info.setMaximumHeight(96)
        self._curve_preview_info.setPlainText("Curve info will appear after preview refresh.")
        self._curve_preview_info.setStyleSheet(
            "QPlainTextEdit { color: #dce8f7; background: #162233; border: 1px solid #41546a; padding: 6px; }"
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

    def _build_vertical_curves_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        note = QtWidgets.QLabel("Vertical curve rows stored on the V1Profile source object.")
        note.setWordWrap(True)
        layout.addWidget(note)

        settings_row = QtWidgets.QHBoxLayout()
        settings_row.addWidget(QtWidgets.QLabel("Auto min length:"))
        self._curve_default_length_spin = QtWidgets.QDoubleSpinBox()
        self._curve_default_length_spin.setRange(1.0, 1000000.0)
        self._curve_default_length_spin.setDecimals(3)
        self._curve_default_length_spin.setValue(30.0)
        self._curve_default_length_spin.setSuffix(" m")
        self._curve_default_length_spin.setToolTip("Minimum curve length used by K-value Auto from PVI.")
        settings_row.addWidget(self._curve_default_length_spin)
        settings_row.addWidget(QtWidgets.QLabel("Design speed:"))
        self._curve_design_speed_spin = QtWidgets.QDoubleSpinBox()
        self._curve_design_speed_spin.setRange(10.0, 200.0)
        self._curve_design_speed_spin.setDecimals(1)
        self._curve_design_speed_spin.setValue(60.0)
        self._curve_design_speed_spin.setSuffix(" km/h")
        self._curve_design_speed_spin.setToolTip("Design speed for placeholder crest/sag K-value lookup.")
        settings_row.addWidget(self._curve_design_speed_spin)
        self._curve_design_standard_label = QtWidgets.QLabel("")
        self._curve_design_standard_label.setStyleSheet("color: #dce8f7;")
        self._curve_design_standard_label.setText(f"Standard: {self._project_design_standard()}")
        settings_row.addWidget(self._curve_design_standard_label)
        settings_row.addWidget(QtWidgets.QLabel("Max length:"))
        self._curve_max_length_spin = QtWidgets.QDoubleSpinBox()
        self._curve_max_length_spin.setRange(1.0, 1000000.0)
        self._curve_max_length_spin.setDecimals(3)
        self._curve_max_length_spin.setValue(300.0)
        self._curve_max_length_spin.setSuffix(" m")
        self._curve_max_length_spin.setToolTip("Maximum curve length allowed by Auto from PVI.")
        settings_row.addWidget(self._curve_max_length_spin)
        settings_row.addStretch(1)
        layout.addLayout(settings_row)

        self._curve_table = QtWidgets.QTableWidget(0, 4)
        self._curve_table.setHorizontalHeaderLabels(["Start STA", "End STA", "Length", "Parameter"])
        self._curve_table.setMinimumHeight(190)
        _make_profile_table_compact(self._curve_table, [82, 82, 76, 86])
        layout.addWidget(self._curve_table, 1)

        curve_buttons = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Curve")
        add_button.clicked.connect(self._add_curve_row)
        curve_buttons.addWidget(add_button)
        auto_button = QtWidgets.QPushButton("Auto from PVI")
        auto_button.clicked.connect(self._auto_curve_rows_from_pvi)
        curve_buttons.addWidget(auto_button)
        delete_button = QtWidgets.QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_selected_curve_rows)
        curve_buttons.addWidget(delete_button)
        sort_button = QtWidgets.QPushButton("Sort by Start")
        sort_button.clicked.connect(self._sort_curve_rows)
        curve_buttons.addWidget(sort_button)
        curve_buttons.addStretch(1)
        layout.addLayout(curve_buttons)
        return tab

    def _build_eg_reference_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        note = QtWidgets.QLabel("Existing ground is treated as a TIN-derived reference, not as editable FG source data.")
        note.setWordWrap(True)
        layout.addWidget(note)

        source_row = QtWidgets.QHBoxLayout()
        self._eg_surface_combo = QtWidgets.QComboBox()
        self._eg_surface_combo.setMinimumWidth(120)
        refresh_sources_button = QtWidgets.QPushButton("Refresh Sources")
        refresh_sources_button.clicked.connect(lambda _checked=False: self._refresh_tin_candidates(refresh_eg=False))
        use_selected_button = QtWidgets.QPushButton("Use Selected")
        use_selected_button.clicked.connect(self._use_selected_eg_surface)
        source_row.addWidget(QtWidgets.QLabel("TIN:"))
        source_row.addWidget(self._eg_surface_combo, 1)
        layout.addLayout(source_row)

        source_button_row = QtWidgets.QHBoxLayout()
        source_button_row.addWidget(refresh_sources_button)
        source_button_row.addWidget(use_selected_button)
        source_button_row.addStretch(1)
        layout.addLayout(source_button_row)

        sample_row = QtWidgets.QHBoxLayout()
        self._eg_interval_spin = QtWidgets.QDoubleSpinBox()
        self._eg_interval_spin.setRange(1.0, 1000000.0)
        self._eg_interval_spin.setDecimals(3)
        self._eg_interval_spin.setValue(20.0)
        self._eg_interval_spin.setSuffix(" m")
        refresh_eg_button = QtWidgets.QPushButton("Refresh EG")
        refresh_eg_button.clicked.connect(self._refresh_eg_reference)
        sample_row.addWidget(QtWidgets.QLabel("Interval:"))
        sample_row.addWidget(self._eg_interval_spin)
        sample_row.addWidget(refresh_eg_button)
        sample_row.addStretch(1)
        layout.addLayout(sample_row)

        self._eg_reference_status = QtWidgets.QLabel("")
        self._eg_reference_status.setWordWrap(True)
        layout.addWidget(self._eg_reference_status)

        self._eg_reference_table = QtWidgets.QTableWidget(0, 7)
        self._eg_reference_table.setHorizontalHeaderLabels(["Station", "X", "Y", "EG Elev.", "Status", "Face", "Notes"])
        self._eg_reference_table.setMinimumHeight(190)
        _make_profile_table_compact(self._eg_reference_table, [72, 82, 82, 74, 70, 54, 160])
        try:
            self._eg_reference_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        except Exception:
            pass
        layout.addWidget(self._eg_reference_table, 1)
        self._refresh_tin_candidates(refresh_eg=False)
        return tab

    def _build_station_check_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        note = QtWidgets.QLabel("Checks whether profile station rows are linked to the active v1 alignment station range.")
        note.setWordWrap(True)
        layout.addWidget(note)

        control_row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh Check")
        refresh_button.clicked.connect(self._refresh_station_check)
        control_row.addWidget(refresh_button)
        control_row.addStretch(1)
        layout.addLayout(control_row)

        self._station_check_status = QtWidgets.QLabel("")
        self._station_check_status.setWordWrap(True)
        layout.addWidget(self._station_check_status)

        self._station_check_table = QtWidgets.QTableWidget(0, 6)
        self._station_check_table.setHorizontalHeaderLabels(["Station", "Kind", "In Alignment", "In Stations", "Status", "Notes"])
        self._station_check_table.setMinimumHeight(190)
        _make_profile_table_compact(self._station_check_table, [72, 86, 92, 88, 66, 170])
        try:
            self._station_check_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        except Exception:
            pass
        layout.addWidget(self._station_check_table, 1)
        return tab

    def _load_rows(self) -> None:
        rows = profile_control_rows(self.profile)
        if not rows:
            rows = profile_rows_from_stationing(find_v1_stationing(self.document))
            self._stationing_loaded_rows = len(rows)
        else:
            self._stationing_loaded_rows = 0
        if not rows:
            self._needs_stationing_notice = True
        self._table.setRowCount(0)
        for row in rows:
            self._append_table_row(row)
        if self.profile is None and self._stationing_loaded_rows > 0:
            self._set_status("Station rows are loaded from V1Stationing. Fill elevations, then Apply to create the v1 profile.", ok=True)
        elif self.profile is None:
            self._set_status("No station rows are available. Generate Stations before creating a Profile.", ok=False)

    def _refresh_reference_tabs(self) -> None:
        self._load_vertical_curve_rows()
        if hasattr(self, "_eg_surface_combo"):
            self._refresh_tin_candidates(refresh_eg=False)
        if hasattr(self, "_station_check_table"):
            self._refresh_station_check()

    def _refresh_tin_candidates(self, *, refresh_eg: bool = False) -> None:
        if not hasattr(self, "_eg_surface_combo"):
            return
        current_name = ""
        current = self._current_eg_surface_object()
        if current is not None:
            current_name = str(getattr(current, "Name", "") or "")
        self._eg_surface_candidates = self._tin_candidate_objects()
        self._eg_surface_combo.clear()
        for obj in self._eg_surface_candidates:
            label = str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "TIN")
            name = str(getattr(obj, "Name", "") or "")
            self._eg_surface_combo.addItem(f"{label} ({name})")
        if current_name:
            for index, obj in enumerate(self._eg_surface_candidates):
                if str(getattr(obj, "Name", "") or "") == current_name:
                    self._eg_surface_combo.setCurrentIndex(index)
                    break
        if refresh_eg:
            self._refresh_eg_reference()
        else:
            self._set_eg_reference_idle_status()

    def _tin_candidate_objects(self) -> list[object]:
        candidates = []
        project = find_project(self.document)
        if project is not None:
            try:
                terrain = getattr(project, "Terrain", None)
                if terrain is not None:
                    candidates.append(terrain)
            except Exception:
                pass
        if Gui is not None:
            try:
                candidates.extend(list(Gui.Selection.getSelection() or []))
            except Exception:
                pass
        candidates.extend(list(getattr(self.document, "Objects", []) or []))
        result = []
        seen = set()
        for obj in sorted(candidates, key=_profile_tin_candidate_sort_key):
            name = str(getattr(obj, "Name", "") or "")
            if not name or name in seen:
                continue
            seen.add(name)
            if _looks_like_tin_candidate(obj):
                result.append(obj)
        return result

    def _set_eg_reference_idle_status(self) -> None:
        if not hasattr(self, "_eg_reference_status"):
            return
        candidate = self._current_eg_surface_object()
        candidate_label = str(getattr(candidate, "Label", "") or getattr(candidate, "Name", "") or "(none)")
        count = len(list(getattr(self, "_eg_surface_candidates", []) or []))
        self._eg_reference_status.setText(
            f"TIN sources: {count} | Selected: {candidate_label} | Click Refresh EG to sample existing ground."
        )

    def _current_eg_surface_object(self):
        candidates = list(getattr(self, "_eg_surface_candidates", []) or [])
        if not candidates or not hasattr(self, "_eg_surface_combo"):
            return None
        index = int(self._eg_surface_combo.currentIndex())
        if index < 0 or index >= len(candidates):
            return None
        return candidates[index]

    def _use_selected_eg_surface(self) -> None:
        selected = []
        if Gui is not None:
            try:
                selected = list(Gui.Selection.getSelection() or [])
            except Exception:
                selected = []
        selected_surface = None
        for obj in selected:
            if _tin_surface_from_candidate(obj) is not None:
                selected_surface = obj
                break
        if selected_surface is None:
            self._set_status("No selected TIN-capable Mesh/Shape object was found.", ok=False)
            return
        self._refresh_tin_candidates(refresh_eg=False)
        target_name = str(getattr(selected_surface, "Name", "") or "")
        for index, obj in enumerate(list(getattr(self, "_eg_surface_candidates", []) or [])):
            if str(getattr(obj, "Name", "") or "") == target_name:
                self._eg_surface_combo.setCurrentIndex(index)
                break
        self._refresh_eg_reference()

    def _refresh_eg_reference(self) -> None:
        if not hasattr(self, "_eg_reference_table"):
            return
        alignment = self.preferred_alignment or find_v1_alignment(self.document)
        interval = float(self._eg_interval_spin.value()) if hasattr(self, "_eg_interval_spin") else 20.0
        rows, status = profile_eg_sample_rows(
            self.document,
            alignment,
            self._profile_rows_for_reference(),
            interval=interval,
            surface_obj=self._current_eg_surface_object(),
        )
        self._eg_reference_table.setRowCount(0)
        for row in rows:
            row_index = self._eg_reference_table.rowCount()
            self._eg_reference_table.insertRow(row_index)
            values = [
                _format_float(row.get("station", 0.0)),
                _format_float(row.get("x", 0.0)),
                _format_float(row.get("y", 0.0)),
                _format_optional_float(row.get("elevation", None)),
                str(row.get("status", "") or ""),
                str(row.get("face_id", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                self._eg_reference_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
        candidate = self._current_eg_surface_object()
        candidate_label = str(getattr(candidate, "Label", "") or getattr(candidate, "Name", "") or "(none)")
        if hasattr(self, "_eg_reference_status"):
            self._eg_reference_status.setText(
                f"TIN: {candidate_label} | Status: {status} | EG rows: {len(rows)} | Interval: {_format_float(interval)} m"
            )

    def _refresh_station_check(self) -> None:
        if not hasattr(self, "_station_check_table"):
            return
        alignment = self.preferred_alignment or find_v1_alignment(self.document)
        stationing = find_v1_stationing(self.document)
        rows = profile_station_check_rows(
            self._profile_rows_for_reference(),
            alignment,
            stationing,
        )
        self._station_check_table.setRowCount(0)
        counts = {"OK": 0, "WARN": 0, "ERROR": 0}
        for row in rows:
            status = str(row.get("status", "") or "")
            counts[status] = counts.get(status, 0) + 1
            row_index = self._station_check_table.rowCount()
            self._station_check_table.insertRow(row_index)
            values = [
                _format_optional_float(row.get("station", None)),
                str(row.get("kind", "") or ""),
                str(row.get("in_alignment", "") or ""),
                str(row.get("in_stationing", "") or ""),
                status,
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                self._station_check_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
        if hasattr(self, "_station_check_status"):
            self._station_check_status.setText(
                f"Rows: {len(rows)} | OK: {counts.get('OK', 0)} | WARN: {counts.get('WARN', 0)} | ERROR: {counts.get('ERROR', 0)}"
            )

    def _profile_rows_for_reference(self) -> list[dict[str, object]]:
        rows = []
        for row_index in range(self._table.rowCount()):
            station_text = self._item_text(row_index, 0)
            kind_text = self._item_text(row_index, 2) or "pvi"
            station = _optional_float(station_text)
            if station is None and not station_text:
                continue
            rows.append({"station": station, "kind": kind_text.strip() or "pvi"})
        return rows

    def _load_vertical_curve_rows(self) -> None:
        if not hasattr(self, "_curve_table"):
            return
        self._curve_table.setRowCount(0)
        for row in profile_vertical_curve_rows(self.profile):
            self._append_vertical_curve_row(row)

    def _append_vertical_curve_row(self, row: dict[str, object]) -> None:
        row_index = self._curve_table.rowCount()
        self._curve_table.insertRow(row_index)
        values = [
            _format_optional_float(row.get("station_start", None)),
            _format_optional_float(row.get("station_end", None)),
            _format_optional_float(row.get("length", None)),
            _format_float(row.get("parameter", 0.0)),
        ]
        for offset, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem(value)
            self._curve_table.setItem(row_index, offset, item)

    def _append_table_row(self, row: dict[str, object]) -> None:
        row_index = self._table.rowCount()
        self._table.insertRow(row_index)
        values = [
            _format_float(row.get("station", 0.0)),
            _format_optional_float(row.get("elevation", None)),
            str(row.get("kind", "") or "pvi"),
        ]
        for col, value in enumerate(values):
            self._table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))

    def _replace_table_rows(self, rows: list[dict[str, object]]) -> None:
        normalized = _normalized_control_rows(self.profile, rows)
        self._table.setRowCount(0)
        for row in normalized:
            self._append_table_row(row)

    def _replace_vertical_curve_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_curve_table"):
            return
        normalized = _normalized_vertical_curve_rows(self.profile, rows, min_rows=0)
        self._curve_table.setRowCount(0)
        for row in normalized:
            self._append_vertical_curve_row(row)

    def _apply_preset_data(self) -> None:
        names = profile_preset_names()
        if not names:
            self._show_message("Profile", "No Profile preset data is available.")
            return
        try:
            name, ok = QtWidgets.QInputDialog.getItem(
                self.form,
                "Profile Preset Data",
                "Preset:",
                names,
                0,
                False,
            )
        except Exception:
            name, ok = names[0], True
        if not ok or not name:
            return
        try:
            station_rows = self._table_station_kind_rows()
            rows = profile_preset_rows_for_station_rows(str(name), station_rows)
            curve_rows = profile_preset_vertical_curve_rows_for_station_rows(str(name), station_rows)
            self._replace_table_rows(rows)
            self._replace_vertical_curve_rows(curve_rows)
            self._refresh_curve_preview()
            self._set_status(
                f"Loaded Profile preset data: {name} onto {len(rows)} current station row(s), with {len(curve_rows)} vertical curve row(s). Apply when ready.",
                ok=True,
            )
            self._show_message(
                "Profile",
                f"Preset data loaded: {name}\nRows: {len(rows)}\nVertical curves: {len(curve_rows)}\nStation rows were kept and elevations/curves were sampled from the preset.\nClick Apply to update the V1Profile.",
            )
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Preset data was not loaded.\n{exc}")

    def _import_profile_csv(self) -> None:
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            self.form,
            "Import Profile CSV",
            "",
            "CSV Files (*.csv *.txt);;All Files (*.*)",
        )
        if not path:
            return
        try:
            rows = import_profile_control_rows_from_csv(path)
            self._replace_table_rows(rows)
            self._refresh_curve_preview()
            self._set_status(f"Imported {len(rows)} Profile row(s) from CSV. Apply when ready.", ok=True)
            self._show_message(
                "Profile",
                f"Profile CSV imported.\nFile: {os.path.basename(str(path))}\nRows: {len(rows)}\nClick Apply to update the V1Profile.",
            )
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Profile CSV import failed.\n{exc}")

    def _export_profile_csv(self) -> None:
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            self.form,
            "Export Profile CSV",
            "profile.csv",
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if not path:
            return
        try:
            count = export_profile_control_rows_to_csv(path, self._table_rows(allow_empty=False))
            self._set_status(f"Exported {count} Profile row(s) to CSV.", ok=True)
            self._show_message("Profile", f"Profile CSV exported.\nFile: {os.path.basename(str(path))}\nRows: {count}")
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Profile CSV export failed.\n{exc}")

    def _auto_interpolate_elevations(self) -> None:
        try:
            rows = auto_interpolate_profile_elevation_rows(self._table_rows_with_optional_elevations())
            self._replace_table_rows(rows)
            self._refresh_curve_preview()
            self._set_status(
                f"Auto Interpolate Elevations filled {len(rows)} profile row(s). Apply when ready.",
                ok=True,
            )
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Profile elevations were not auto-interpolated.\n{exc}")

    def _add_row(self) -> None:
        rows = self._table_rows(allow_empty=False)
        if rows:
            last = rows[-1]
            station = float(last["station"]) + 20.0
            elevation = float(last["elevation"])
        else:
            station = 0.0
            elevation = 0.0
        self._append_table_row({"station": station, "elevation": elevation, "kind": "pvi"})
        self._refresh_curve_preview()
        self._set_status("Added a new PVI row. Apply when ready.", ok=True)

    def _delete_selected_rows(self) -> None:
        selected = sorted({item.row() for item in list(self._table.selectedItems() or [])}, reverse=True)
        if not selected and self._table.currentRow() >= 0:
            selected = [self._table.currentRow()]
        for row_index in selected:
            self._table.removeRow(row_index)
        self._refresh_curve_preview()
        self._set_status(f"Deleted {len(selected)} row(s). Apply when ready.", ok=True)

    def _sort_table_rows(self) -> None:
        try:
            rows = _normalized_control_rows(self.profile, self._table_rows(allow_empty=False), min_rows=0)
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            return
        self._table.setRowCount(0)
        for row in rows:
            self._append_table_row(row)
        self._refresh_curve_preview()
        self._set_status("Rows sorted by station. Apply when ready.", ok=True)

    def _add_curve_row(self) -> None:
        self._append_vertical_curve_row(
            {
                "kind": "parabolic_vertical_curve",
                "station_start": None,
                "station_end": None,
                "length": None,
                "parameter": 0.0,
            }
        )
        self._refresh_curve_preview()
        self._set_status("Added a blank vertical curve row. Enter Start/End/Length, then Apply.", ok=True)

    def _auto_curve_rows_from_pvi(self) -> None:
        try:
            pvi_rows = self._profile_rows_for_auto_curves()
            curve_rows, summary = generate_profile_vertical_curve_rows_from_controls(
                pvi_rows,
                default_length=self._curve_default_length(),
                min_length=self._curve_default_length(),
                max_length=self._curve_max_length(),
                design_speed_kph=self._curve_design_speed(),
                design_standard=self._project_design_standard(),
                method="k_value",
                return_diagnostics=True,
            )
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Vertical curves were not generated from PVI rows.\n{exc}")
            return
        self._curve_table.setRowCount(0)
        for row in curve_rows:
            self._append_vertical_curve_row(row)
        self._refresh_curve_preview()
        status = (
            f"Generated {int(summary.get('generated', len(curve_rows)))} K-value vertical curve row(s). "
            f"Crest={int(summary.get('crest', 0))}, Sag={int(summary.get('sag', 0))}, "
            f"clamped={int(summary.get('clamped', 0))}, skipped={int(summary.get('skipped', 0))}. Apply when ready."
        )
        self._set_status(status, ok=True)
        detail = "\n".join(str(row) for row in list(summary.get("diagnostics", []) or [])[:8])
        self._show_message(
            "Profile",
            f"{status}\n\n{detail}\n\nClick Apply to update the V1Profile.",
        )

    def _profile_rows_for_auto_curves(self) -> list[dict[str, object]]:
        missing_rows = []
        for row_index in range(self._table.rowCount()):
            station_text = self._item_text(row_index, 0)
            elevation_text = self._item_text(row_index, 1)
            if station_text and not elevation_text:
                missing_rows.append(row_index + 1)
        if missing_rows:
            raise ValueError(
                "Auto from PVI requires FG elevation values first. "
                "Enter elevations in the FG Profile tab, or use Preset Data / Import CSV before running Auto from PVI."
            )
        return self._table_rows(allow_empty=False)

    def _curve_default_length(self) -> float:
        try:
            return float(self._curve_default_length_spin.value())
        except Exception:
            return 30.0

    def _curve_design_speed(self) -> float:
        try:
            return float(self._curve_design_speed_spin.value())
        except Exception:
            return 60.0

    def _curve_max_length(self) -> float:
        try:
            return float(self._curve_max_length_spin.value())
        except Exception:
            return 300.0

    def _project_design_standard(self) -> str:
        try:
            return get_design_standard(find_project(self.document) or self.document, default=_ds.DEFAULT_STANDARD)
        except Exception:
            return _ds.DEFAULT_STANDARD

    def _delete_selected_curve_rows(self) -> None:
        selected = sorted({item.row() for item in list(self._curve_table.selectedItems() or [])}, reverse=True)
        if not selected and self._curve_table.currentRow() >= 0:
            selected = [self._curve_table.currentRow()]
        for row_index in selected:
            self._curve_table.removeRow(row_index)
        self._refresh_curve_preview()
        self._set_status(f"Deleted {len(selected)} vertical curve row(s). Apply when ready.", ok=True)

    def _sort_curve_rows(self) -> None:
        try:
            rows = _normalized_vertical_curve_rows(self.profile, self._curve_table_rows(allow_empty=True), min_rows=0)
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Vertical curve rows were not sorted.\n{exc}")
            return
        self._curve_table.setRowCount(0)
        for row in rows:
            self._append_vertical_curve_row(row)
        self._refresh_curve_preview()
        self._set_status("Vertical curve rows sorted by start station. Apply when ready.", ok=True)

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            input_rows = self._table_rows(allow_empty=False)
            curve_rows = self._curve_table_rows(allow_empty=True)
            _normalized_control_rows(self.profile, input_rows)
            _normalized_vertical_curve_rows(self.profile, curve_rows, min_rows=0)
            if self.profile is None:
                self.profile = create_blank_v1_profile(
                    document=self.document,
                    alignment=self.preferred_alignment or find_v1_alignment(self.document),
                )
            normalized = apply_profile_control_rows(self.profile, input_rows)
            normalized_curves = apply_profile_vertical_curve_rows(self.profile, curve_rows)
            if self.document is not None:
                try:
                    self.document.recompute()
                except Exception:
                    pass
            self._set_status(f"Applied {len(normalized)} PVI row(s) to V1Profile.", ok=True)
            self._profile_label.setText(self._profile_summary_text())
            self._refresh_reference_tabs()
            self._refresh_curve_preview()
            self._show_apply_complete_message(len(normalized), len(normalized_curves))
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Profile was not applied.\n{exc}")
            return False

    def _show_current_profile(self) -> None:
        try:
            input_rows = self._table_rows(allow_empty=False)
            curve_rows = self._curve_table_rows(allow_empty=True)
            alignment = self.preferred_alignment or find_v1_alignment(self.document)
            alignment_id = str(getattr(alignment, "AlignmentId", "") or "")
            profile_model = profile_model_from_editor_rows(
                input_rows,
                curve_rows,
                alignment_id=alignment_id,
            )
            preview = show_profile_preview_object(
                self.document,
                profile_model,
                alignment,
                sample_interval=10.0,
                surface_obj=self._current_eg_surface_object() if hasattr(self, "_eg_surface_combo") else None,
            )
            if self.document is not None:
                try:
                    self.document.recompute()
                except Exception:
                    pass
            if Gui is not None:
                _force_profile_preview_visibility(self.document)
                try:
                    Gui.Selection.clearSelection()
                    for name in (
                        "FinishedGradeFG_ShowPreview_Frame",
                        "FinishedGradeFG_ShowPreview_Grid",
                        "FinishedGradeFG_ShowPreview",
                        "FinishedGradeFG_ShowPreview_EG",
                    ):
                        obj = self.document.getObject(name) if self.document is not None else None
                        if obj is not None:
                            Gui.Selection.addSelection(obj)
                    if hasattr(Gui, "updateGui"):
                        Gui.updateGui()
                except Exception:
                    pass
                try:
                    view = Gui.ActiveDocument.ActiveView
                    if hasattr(view, "viewFront"):
                        view.viewFront()
                    else:
                        Gui.SendMsgToActiveView("ViewFront")
                except Exception:
                    try:
                        Gui.SendMsgToActiveView("ViewFront")
                    except Exception:
                        pass
                try:
                    if hasattr(Gui, "updateGui"):
                        Gui.updateGui()
                    view = Gui.ActiveDocument.ActiveView
                    if hasattr(view, "fitSelection"):
                        view.fitSelection()
                    else:
                        Gui.SendMsgToActiveView("ViewSelection")
                except Exception:
                    try:
                        Gui.SendMsgToActiveView("ViewSelection")
                    except Exception:
                        try:
                            Gui.SendMsgToActiveView("ViewFit")
                        except Exception:
                            pass
                try:
                    if hasattr(Gui, "updateGui"):
                        Gui.updateGui()
                except Exception:
                    pass
            self._set_status(
                f"Profile preview shown in 3D View ({int(getattr(preview, 'DisplayPointCount', 0) or 0)} points).",
                ok=True,
            )
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Profile preview was not shown.\n{exc}")

    def _refresh_curve_preview(self) -> None:
        widget = getattr(self, "_curve_preview_widget", None)
        if widget is None:
            return
        try:
            input_rows = self._table_rows(allow_empty=False)
            curve_rows = self._curve_table_rows(allow_empty=True)
            alignment = self.preferred_alignment or find_v1_alignment(self.document)
            alignment_id = str(getattr(alignment, "AlignmentId", "") or "")
            profile_model = profile_model_from_editor_rows(
                input_rows,
                curve_rows,
                alignment_id=alignment_id,
                profile_id=str(getattr(self.profile, "ProfileId", "") or "profile:curve-preview"),
                label="Profile Curve Preview",
            )
            result = ProfileCurvePreviewService().evaluate(
                ProfileCurvePreviewRequest(profile=profile_model, sample_interval=10.0)
            )
            widget.set_result(result)
            self._set_curve_preview_info(result)
        except Exception as exc:
            widget.set_error(str(exc))
            info = getattr(self, "_curve_preview_info", None)
            if info is not None:
                info.setPlainText(f"Curve preview unavailable:\n{exc}")

    def _set_curve_preview_info(self, result) -> None:
        info = getattr(self, "_curve_preview_info", None)
        if info is None:
            return
        lines: list[str] = []
        curve_rows = list(getattr(result, "curve_rows", []) or [])
        if curve_rows:
            curve = curve_rows[0]
            lines.append(
                "Curve: "
                f"{str(getattr(curve, 'curve_id', '') or '-')}"
                f" | {str(getattr(curve, 'kind', '') or '-')}"
                f" | STA {float(getattr(curve, 'station_start', 0.0) or 0.0):.3f}"
                f" - {float(getattr(curve, 'station_end', 0.0) or 0.0):.3f}"
                f" | L={float(getattr(curve, 'length', 0.0) or 0.0):.3f}"
            )
            lines.append(
                "BVC/PVI/EVC: "
                f"BVC {float(getattr(curve, 'bvc_station', 0.0) or 0.0):.3f}/EL {float(getattr(curve, 'bvc_elevation', 0.0) or 0.0):.3f}, "
                f"PVI {float(getattr(curve, 'pvi_station', 0.0) or 0.0):.3f}/EL {float(getattr(curve, 'pvi_elevation', 0.0) or 0.0):.3f}, "
                f"EVC {float(getattr(curve, 'evc_station', 0.0) or 0.0):.3f}/EL {float(getattr(curve, 'evc_elevation', 0.0) or 0.0):.3f}"
            )
            lines.append(
                "Grades: "
                f"g1={float(getattr(curve, 'grade_in', 0.0) or 0.0):.6f}, "
                f"g2={float(getattr(curve, 'grade_out', 0.0) or 0.0):.6f}, "
                f"A={float(getattr(curve, 'algebraic_grade_difference', 0.0) or 0.0):.6f}, "
                f"K={float(getattr(curve, 'k_value', 0.0) or 0.0):.3f}, "
                f"max deviation={float(getattr(curve, 'max_chord_deviation', 0.0) or 0.0):.3f}"
            )
            high_low = str(getattr(curve, "high_low_kind", "") or "")
            if high_low:
                lines.append(
                    f"{high_low}: STA {float(getattr(curve, 'high_low_station', 0.0) or 0.0):.3f}, "
                    f"EL {float(getattr(curve, 'high_low_elevation', 0.0) or 0.0):.3f}"
                )
        else:
            lines.append("Curve: no vertical curve rows. Preview shows source tangent/chord behavior.")
        diagnostics = [
            f"{str(getattr(row, 'severity', '') or '').upper()}: {str(getattr(row, 'kind', '') or '')} - {str(getattr(row, 'message', '') or '')}"
            for row in list(getattr(result, "diagnostic_rows", []) or [])
            if str(getattr(row, "severity", "") or "").lower() != "info"
        ]
        if diagnostics:
            lines.append("Diagnostics:")
            lines.extend(diagnostics[:4])
        else:
            lines.append("Diagnostics: no warnings.")
        info.setPlainText("\n".join(lines))

    def _show_apply_complete_message(self, row_count: int, curve_count: int) -> None:
        try:
            QtWidgets.QMessageBox.information(
                self.form,
                "Profile",
                f"Profile has been applied successfully.\nPVI rows: {int(row_count)}\nVertical curve rows: {int(curve_count)}",
            )
        except Exception:
            pass

    def _open_review(self) -> None:
        if self.profile is None:
            self._set_status("Apply the profile before opening Plan/Profile Review.", ok=False)
            self._show_message("Profile", "Apply the profile before opening Plan/Profile Review.")
            return
        context = build_profile_editor_handoff_context(
            self.profile,
            selected_row=self._selected_or_first_row(),
        )
        success, message = run_legacy_command(
            "CorridorRoad_V1ReviewPlanProfile",
            gui_module=Gui,
            objects_to_select=[self.profile],
            context_payload=context,
        )
        self._set_status(message, ok=success)

    def _table_rows(self, *, allow_empty: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row_index in range(self._table.rowCount()):
            station_text = self._item_text(row_index, 0)
            elevation_text = self._item_text(row_index, 1)
            kind_text = self._item_text(row_index, 2) or "pvi"
            if not station_text and not elevation_text and allow_empty:
                continue
            rows.append(
                {
                    "control_point_id": _existing_control_id(self.profile, row_index),
                    "station": _required_float(station_text, f"Row {row_index + 1} station"),
                    "elevation": _required_float(elevation_text, f"Row {row_index + 1} elevation"),
                    "kind": kind_text.strip() or "pvi",
                }
            )
        return rows

    def _table_station_kind_rows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row_index in range(self._table.rowCount()):
            station_text = self._item_text(row_index, 0)
            kind_text = self._item_text(row_index, 2) or "pvi"
            if not station_text:
                continue
            rows.append(
                {
                    "control_point_id": _existing_control_id(self.profile, row_index),
                    "station": _required_float(station_text, f"Row {row_index + 1} station"),
                    "kind": kind_text.strip() or "pvi",
                }
            )
        return rows

    def _table_rows_with_optional_elevations(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row_index in range(self._table.rowCount()):
            station_text = self._item_text(row_index, 0)
            elevation_text = self._item_text(row_index, 1)
            kind_text = self._item_text(row_index, 2) or "pvi"
            if not station_text and not elevation_text:
                continue
            rows.append(
                {
                    "control_point_id": _existing_control_id(self.profile, row_index),
                    "station": _required_float(station_text, f"Row {row_index + 1} station"),
                    "elevation": _optional_float(elevation_text),
                    "kind": kind_text.strip() or "pvi",
                }
            )
        return rows

    def _table_station_values(self) -> list[float]:
        stations: list[float] = []
        for row_index in range(self._table.rowCount()):
            station = _optional_float(self._item_text(row_index, 0))
            if station is not None:
                stations.append(float(station))
        return stations

    def _curve_table_rows(self, *, allow_empty: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row_index in range(self._curve_table.rowCount()):
            start_text = self._curve_item_text(row_index, 0)
            end_text = self._curve_item_text(row_index, 1)
            length_text = self._curve_item_text(row_index, 2)
            parameter_text = self._curve_item_text(row_index, 3)
            if allow_empty and not start_text and not end_text and not length_text:
                continue
            rows.append(
                {
                    "curve_id": _existing_curve_id(self.profile, row_index),
                    "kind": "parabolic_vertical_curve",
                    "station_start": _required_float(start_text, f"Curve row {row_index + 1} start station"),
                    "station_end": _required_float(end_text, f"Curve row {row_index + 1} end station"),
                    "length": _optional_float(length_text),
                    "parameter": _optional_float(parameter_text) or 0.0,
                }
            )
        return rows

    def _selected_or_first_row(self) -> dict[str, object]:
        rows = self._table_rows(allow_empty=True)
        if not rows:
            return {}
        row_index = self._table.currentRow()
        if row_index < 0:
            return rows[0]
        if row_index >= len(rows):
            return rows[0]
        return rows[row_index]

    def _item_text(self, row_index: int, col_index: int) -> str:
        item = self._table.item(row_index, col_index)
        if item is None:
            return ""
        return str(item.text() or "").strip()

    def _curve_item_text(self, row_index: int, col_index: int) -> str:
        widget = self._curve_table.cellWidget(row_index, col_index)
        if widget is not None and hasattr(widget, "currentText"):
            return str(widget.currentText() or "").strip()
        item = self._curve_table.item(row_index, col_index)
        if item is None:
            return ""
        return str(item.text() or "").strip()

    def _profile_summary_text(self) -> str:
        if self.profile is None:
            return "No V1Profile is available."
        return (
            f"Profile: {str(getattr(self.profile, 'Label', '') or getattr(self.profile, 'Name', '') or '')} | "
            f"ProfileId: {str(getattr(self.profile, 'ProfileId', '') or '')} | "
            f"AlignmentId: {str(getattr(self.profile, 'AlignmentId', '') or '')}"
        )

    def _set_status(self, message: str, *, ok: bool) -> None:
        return

    def _show_message(self, title: str, message: str) -> None:
        try:
            QtWidgets.QMessageBox.information(self.form, title, message)
        except Exception:
            pass


__all__ = [
    "_ProfileCurvePreviewWidget",
    "V1ProfileEditorTaskPanel",
    "configure_profile_editor_task_panel_runtime",
]

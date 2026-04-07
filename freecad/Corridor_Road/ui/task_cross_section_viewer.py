# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_all
from freecad.Corridor_Road.objects.obj_section_set import SectionSet


def _find_section_sets(doc):
    return find_all(doc, proxy_type="SectionSet", name_prefixes=("SectionSet",))


def _selected_section_target(doc):
    try:
        sel = list(Gui.Selection.getSelection() or [])
    except Exception:
        sel = []
    for obj in sel:
        if obj is None:
            continue
        try:
            if getattr(getattr(obj, "Proxy", None), "Type", "") == "SectionSet":
                return obj, None
        except Exception:
            pass
        try:
            parent = getattr(obj, "ParentSectionSet", None)
            station = getattr(obj, "Station", None)
            if parent is not None:
                return parent, station
        except Exception:
            pass
    return None, None


class _SelectionObserver:
    def __init__(self, panel):
        self.panel = panel

    def addSelection(self, *args):
        doc_name = args[0] if len(args) > 0 else ""
        obj_name = args[1] if len(args) > 1 else ""
        self.panel._sync_from_selection(doc_name, obj_name)

    def setSelection(self, *args):
        doc_name = args[0] if len(args) > 0 else ""
        obj_name = args[1] if len(args) > 1 else ""
        self.panel._sync_from_selection(doc_name, obj_name)

    def removeSelection(self, *args):
        return

    def clearSelection(self, *args):
        return


class _CrossSectionGraphicsView(QtWidgets.QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.TextAntialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return
        factor = 1.20 if delta > 0 else (1.0 / 1.20)
        self.scale(factor, factor)
        event.accept()


class CrossSectionViewerTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._loading = False
        self._section_sets = []
        self._station_rows = []
        self._last_fit_rect = None
        self._current_payload = None
        self._selection_observer = None
        self.form = self._build_ui()
        self._register_selection_observer()
        self._refresh_context()

    def getStandardButtons(self):
        return 0

    def accept(self):
        self._teardown()
        Gui.Control.closeDialog()

    def reject(self):
        self._teardown()
        Gui.Control.closeDialog()

    def _teardown(self):
        if self._selection_observer is None:
            return
        try:
            Gui.Selection.removeObserver(self._selection_observer)
        except Exception:
            pass
        self._selection_observer = None

    def _build_ui(self):
        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Cross Section Viewer")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        gb_src = QtWidgets.QGroupBox("Source")
        fs = QtWidgets.QFormLayout(gb_src)
        self.cmb_section_set = QtWidgets.QComboBox()
        self.cmb_station = QtWidgets.QComboBox()
        self.chk_sync_selection = QtWidgets.QCheckBox("Sync with 3D selection")
        self.chk_sync_selection.setChecked(True)
        self.chk_show_structures = QtWidgets.QCheckBox("Show structure overlays")
        self.chk_show_structures.setChecked(True)
        self.chk_show_labels = QtWidgets.QCheckBox("Show labels")
        self.chk_show_labels.setChecked(True)
        self.chk_show_dimensions = QtWidgets.QCheckBox("Show dimensions")
        self.chk_show_dimensions.setChecked(True)
        self.chk_show_diagnostics = QtWidgets.QCheckBox("Show diagnostics")
        self.chk_show_diagnostics.setChecked(True)
        self.chk_show_typical = QtWidgets.QCheckBox("Show typical components")
        self.chk_show_typical.setChecked(True)
        self.chk_show_side_slope = QtWidgets.QCheckBox("Show side-slope components")
        self.chk_show_side_slope.setChecked(True)
        self.chk_show_daylight = QtWidgets.QCheckBox("Show daylight markers")
        self.chk_show_daylight.setChecked(True)
        self.btn_use_selected = QtWidgets.QPushButton("Use Selected Section")
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        self.chk_show_labels.hide()
        action_row = QtWidgets.QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)
        action_row.addWidget(self.btn_use_selected)
        action_row.addWidget(self.btn_refresh)
        action_widget = QtWidgets.QWidget()
        action_widget.setLayout(action_row)
        fs.addRow("Section Set:", self.cmb_section_set)
        fs.addRow(action_widget)
        fs.addRow(self.chk_sync_selection)
        fs.addRow(self.chk_show_structures)
        fs.addRow(self.chk_show_dimensions)
        fs.addRow(self.chk_show_diagnostics)
        fs.addRow(self.chk_show_typical)
        fs.addRow(self.chk_show_side_slope)
        fs.addRow(self.chk_show_daylight)
        fs.addRow("Station:", self.cmb_station)
        main.addWidget(gb_src)

        row_nav = QtWidgets.QHBoxLayout()
        self.btn_prev = QtWidgets.QPushButton("Previous")
        self.btn_next = QtWidgets.QPushButton("Next")
        self.btn_fit = QtWidgets.QPushButton("Fit View")
        row_nav.addWidget(self.btn_prev)
        row_nav.addWidget(self.btn_next)
        row_nav.addWidget(self.btn_fit)
        main.addLayout(row_nav)

        self.scene = QtWidgets.QGraphicsScene()
        self.view = _CrossSectionGraphicsView()
        self.view.setScene(self.scene)
        self.view.setMinimumHeight(360)
        main.addWidget(self.view, 1)

        self.txt_summary = QtWidgets.QPlainTextEdit()
        self.txt_summary.setReadOnly(True)
        self.txt_summary.setMinimumHeight(110)
        main.addWidget(self.txt_summary)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_export_png = QtWidgets.QPushButton("Export PNG")
        self.btn_export_svg = QtWidgets.QPushButton("Export SVG")
        self.btn_export_sheet_svg = QtWidgets.QPushButton("Export Sheet SVG")
        self.btn_close = QtWidgets.QPushButton("Close")
        row_btn.addWidget(self.btn_export_png)
        row_btn.addWidget(self.btn_export_svg)
        row_btn.addWidget(self.btn_export_sheet_svg)
        row_btn.addStretch(1)
        row_btn.addWidget(self.btn_close)
        main.addLayout(row_btn)

        self.cmb_section_set.currentIndexChanged.connect(self._on_section_set_changed)
        self.cmb_station.currentIndexChanged.connect(self._render_current_payload)
        self.chk_show_structures.toggled.connect(self._render_current_payload)
        self.chk_show_labels.toggled.connect(self._render_current_payload)
        self.chk_show_dimensions.toggled.connect(self._render_current_payload)
        self.chk_show_diagnostics.toggled.connect(self._render_current_payload)
        self.chk_show_typical.toggled.connect(self._render_current_payload)
        self.chk_show_side_slope.toggled.connect(self._render_current_payload)
        self.chk_show_daylight.toggled.connect(self._render_current_payload)
        self.btn_use_selected.clicked.connect(self._use_selected_section)
        self.btn_refresh.clicked.connect(self._refresh_context)
        self.btn_prev.clicked.connect(self._go_previous)
        self.btn_next.clicked.connect(self._go_next)
        self.btn_fit.clicked.connect(self._fit_view)
        self.btn_export_png.clicked.connect(self._export_png)
        self.btn_export_svg.clicked.connect(self._export_svg)
        self.btn_export_sheet_svg.clicked.connect(self._export_sheet_svg)
        self.btn_close.clicked.connect(self.reject)
        return w

    def _register_selection_observer(self):
        if self._selection_observer is not None:
            return
        try:
            self._selection_observer = _SelectionObserver(self)
            Gui.Selection.addObserver(self._selection_observer)
        except Exception:
            self._selection_observer = None

    def _format_section_set(self, obj):
        return f"{obj.Label} ({obj.Name})"

    def _current_section_set(self):
        idx = int(self.cmb_section_set.currentIndex())
        if idx < 0 or idx >= len(self._section_sets):
            return None
        return self._section_sets[idx]

    def _current_station_row(self):
        idx = int(self.cmb_station.currentIndex())
        if idx < 0 or idx >= len(self._station_rows):
            return None
        return self._station_rows[idx]

    def _refresh_context(self, preserve_station=True):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            self.scene.clear()
            self.txt_summary.setPlainText("No active document.")
            return

        selected_set, selected_station = _selected_section_target(self.doc)
        current_set = self._current_section_set()
        current_station = None
        row = self._current_station_row()
        if row is not None:
            current_station = float(row.get("station", 0.0))

        preferred_set = selected_set if selected_set is not None else current_set
        preferred_station = selected_station if selected_station is not None else current_station

        self._section_sets = _find_section_sets(self.doc)
        self._loading = True
        try:
            self.cmb_section_set.clear()
            for obj in self._section_sets:
                self.cmb_section_set.addItem(self._format_section_set(obj))
            if self._section_sets:
                idx = 0
                if preferred_set is not None:
                    for i, obj in enumerate(self._section_sets):
                        if obj == preferred_set:
                            idx = i
                            break
                self.cmb_section_set.setCurrentIndex(idx)
        finally:
            self._loading = False

        self._reload_station_rows(preferred_station if preserve_station else None)

        if not self._section_sets:
            self.lbl_info.setText("No SectionSet found. Run Generate Sections first.")
            self.scene.clear()
            self.txt_summary.setPlainText("No SectionSet found.")
            return

        self.lbl_info.setText(
            "2D cross-section viewer for SectionSet wires. "
            "Use 3D SectionSlice selection or choose a station here."
        )
        self._render_current_payload()

    def _reload_station_rows(self, preferred_station=None):
        sec = self._current_section_set()
        self._station_rows = []
        self._loading = True
        try:
            self.cmb_station.clear()
            if sec is not None:
                self._station_rows = SectionSet.resolve_viewer_station_rows(sec)
                for row in self._station_rows:
                    self.cmb_station.addItem(str(row.get("label", f"STA {float(row.get('station', 0.0)):.3f}")))
                if self._station_rows:
                    idx = 0
                    if preferred_station is not None:
                        best_idx = 0
                        best_delta = None
                        for i, row in enumerate(self._station_rows):
                            delta = abs(float(row.get("station", 0.0)) - float(preferred_station))
                            if best_delta is None or delta < best_delta:
                                best_delta = delta
                                best_idx = i
                        idx = best_idx
                    self.cmb_station.setCurrentIndex(idx)
        finally:
            self._loading = False

    def _on_section_set_changed(self, _idx):
        if self._loading:
            return
        self._reload_station_rows()
        self._render_current_payload()

    def _scene_point(self, x, y):
        return QtCore.QPointF(float(x), -float(y))

    def _poly_to_path(self, points):
        if not points:
            return None
        path = QtGui.QPainterPath()
        path.moveTo(self._scene_point(points[0][0], points[0][1]))
        for x, y in points[1:]:
            path.lineTo(self._scene_point(x, y))
        return path

    @staticmethod
    def _dimension_color(role: str):
        role = str(role or "")
        color_map = {
            "overall_width": QtGui.QColor(145, 210, 160),
            "left_reach": QtGui.QColor(120, 190, 215),
            "right_reach": QtGui.QColor(120, 190, 215),
            "lane": QtGui.QColor(255, 214, 102),
            "carriageway": QtGui.QColor(255, 214, 102),
            "side_slope": QtGui.QColor(132, 210, 132),
            "cut_slope": QtGui.QColor(255, 170, 122),
            "fill_slope": QtGui.QColor(132, 210, 132),
            "shoulder": QtGui.QColor(186, 220, 132),
            "median": QtGui.QColor(214, 160, 255),
            "curb": QtGui.QColor(255, 160, 92),
            "ditch": QtGui.QColor(128, 208, 190),
            "berm": QtGui.QColor(225, 190, 120),
            "bench": QtGui.QColor(225, 190, 120),
            "sidewalk": QtGui.QColor(240, 190, 210),
            "bike_lane": QtGui.QColor(120, 225, 140),
            "green_strip": QtGui.QColor(132, 210, 132),
        }
        return QtGui.QColor(color_map.get(role, QtGui.QColor(145, 210, 160)))

    @staticmethod
    def _svg_dimension_color(role: str):
        return str(CrossSectionViewerTaskPanel._dimension_color(role).name())

    @staticmethod
    def _svg_label_color(role: str):
        role = str(role or "")
        if role.startswith("component:"):
            return CrossSectionViewerTaskPanel._svg_dimension_color(role.split(":", 1)[1])
        if role == "top_edge_right":
            return "#dcdcdc"
        if role == "structure_summary":
            return "#e8603c"
        if role == "daylight_note":
            return "#96b978"
        if role == "station_tags":
            return "#c3d7ff"
        return "#bccdeb"

    @staticmethod
    def _estimate_text_width(text, svg_font_size=0.48):
        raw = str(text or "")
        font_size = max(0.10, float(svg_font_size or 0.10))
        # Keep this estimate conservative so vertical label/value spacing does not
        # under-shoot the actual rendered text height in the viewer.
        return max(0.45, (float(len(raw)) + 0.8) * font_size * 0.84)

    @staticmethod
    def _estimate_vertical_text_bandwidth(svg_font_size=0.48, kind="label"):
        base = max(0.0, float(svg_font_size or 0.0))
        factor = 2.55 if str(kind or "label") == "value" else 3.05
        floor = 0.18 if str(kind or "label") == "value" else 0.24
        return max(float(floor), base * factor)

    @staticmethod
    def _component_vertical_clearance(
        typ="",
        label_extent=0.0,
        value_extent=0.0,
        label_svg_font_size=0.0,
        value_svg_font_size=0.0,
        height=1.0,
    ):
        typ = str(typ or "").strip().lower()
        label_extent = max(0.0, float(label_extent or 0.0))
        value_extent = max(0.0, float(value_extent or 0.0))
        clearance = max(
            0.12,
            0.28 * max(float(label_svg_font_size or 0.0), float(value_svg_font_size or 0.0), 0.12),
            3.0 * label_extent,
            0.10 * value_extent,
            0.04 * max(float(height or 0.0), 1.0),
        )
        if typ in ("bench", "cut_slope", "fill_slope", "side_slope"):
            clearance = max(
                clearance,
                0.22,
                0.20 * max(float(height or 0.0), 1.0),
                3.0 * label_extent,
                0.22 * value_extent,
            )
        elif typ in (
            "lane",
            "carriageway",
            "shoulder",
            "green_strip",
            "median",
            "curb",
            "ditch",
            "berm",
            "sidewalk",
            "bike_lane",
        ):
            clearance = max(
                clearance,
                0.14,
                0.12 * max(float(height or 0.0), 1.0),
                3.0 * label_extent,
                0.18 * value_extent,
            )
        return float(clearance)

    @staticmethod
    def _short_component_name(role: str):
        role = str(role or "").strip().lower()
        mapping = {
            "lane": "Lane",
            "carriageway": "Carr",
            "side_slope": "Slope",
            "cut_slope": "Cut",
            "fill_slope": "Fill",
            "shoulder": "Shldr",
            "median": "Med",
            "curb": "Curb",
            "ditch": "Ditch",
            "berm": "Berm",
            "bench": "Bench",
            "sidewalk": "Walk",
            "bike_lane": "Bike",
            "green_strip": "Green",
        }
        return str(mapping.get(role, role.title() if role else "Comp"))

    @staticmethod
    def _component_short_visual_label(seg):
        typ = str(seg.get("type", "") or "").strip().lower()
        shape = str(seg.get("shape", "") or "").strip().lower()
        base = CrossSectionViewerTaskPanel._short_component_name(typ)
        if typ == "ditch":
            if shape == "u":
                return "Ditch-U"
            if shape == "trapezoid":
                return "Ditch-Trap"
        return base

    @staticmethod
    def _component_label_priority(role: str):
        role = str(role or "").strip().lower()
        mapping = {
            "lane": 100,
            "carriageway": 98,
            "side_slope": 72,
            "cut_slope": 72,
            "fill_slope": 72,
            "shoulder": 95,
            "median": 88,
            "bike_lane": 82,
            "sidewalk": 78,
            "curb": 74,
            "ditch": 64,
            "berm": 58,
            "bench": 56,
            "green_strip": 46,
        }
        return int(mapping.get(role, 52))

    @staticmethod
    def _component_label_orientation(role: str):
        role = str(role or "").strip().lower()
        if role in ("shoulder", "ditch", "berm", "green_strip", "sidewalk", "bike_lane", "curb"):
            return "vertical"
        return "horizontal"

    @staticmethod
    def _label_priority(role: str):
        role = str(role or "").strip().lower()
        mapping = {
            "station_tags": 96,
            "top_edge_left": 90,
            "top_edge_right": 90,
            "structure_summary": 72,
            "daylight_note": 68,
        }
        if role.startswith("component:"):
            return CrossSectionViewerTaskPanel._component_label_priority(role.split(":", 1)[1])
        return int(mapping.get(role, 60))

    @staticmethod
    def _fit_font_scale(text: str, base_svg_font_size: float, available_span: float, min_scale: float = 0.55, orientation: str = "horizontal"):
        text = str(text or "")
        base_svg_font_size = max(0.10, float(base_svg_font_size or 0.10))
        available_span = max(0.0, float(available_span or 0.0))
        min_scale = max(0.25, min(1.0, float(min_scale or 0.55)))
        orientation = str(orientation or "horizontal").strip().lower()
        if not text:
            return 1.0
        if orientation == "vertical":
            base_need = max(0.22, base_svg_font_size * 1.65)
        else:
            base_need = CrossSectionViewerTaskPanel._estimate_text_width(text, base_svg_font_size)
        if base_need <= 1e-9:
            return 1.0
        if available_span >= base_need:
            return 1.0
        ratio = max(0.0, available_span / base_need)
        scale = max(min_scale, min(1.0, ratio * 0.98))
        if orientation == "vertical":
            fitted_need = max(0.22 * scale, base_svg_font_size * scale * 1.65)
        else:
            fitted_need = CrossSectionViewerTaskPanel._estimate_text_width(text, base_svg_font_size * scale)
        if fitted_need <= available_span + 1e-6:
            return float(scale)
        return None

    @staticmethod
    def _compact_label_text(role: str, text: str):
        raw = str(text or "").strip()
        role = str(role or "").strip()
        if not raw:
            return ""
        if role.startswith("component:"):
            return CrossSectionViewerTaskPanel._short_component_name(role.split(":", 1)[1])
        if role == "station_tags":
            return "Tags"
        if role == "top_edge_left":
            return "L Edge"
        if role == "top_edge_right":
            return "R Edge"
        if role == "structure_summary":
            return "Structure"
        if role == "daylight_note":
            return "Daylight"
        return raw

    @staticmethod
    def _compact_dimension_label(role: str, value: float):
        role = str(role or "").strip().lower()
        value = float(value or 0.0)
        if role == "overall_width":
            return f"OA {value:.2f}m"
        if role == "left_reach":
            return f"L {value:.2f}m"
        if role == "right_reach":
            return f"R {value:.2f}m"
        name = CrossSectionViewerTaskPanel._short_component_name(role)
        return f"{name} {value:.2f}m"

    @staticmethod
    def _numeric_dimension_label(value: float):
        return f"{float(value or 0.0):.2f}m"

    @staticmethod
    def _component_effective_width_from_row(row):
        typ = str(row.get("type", row.get("Type", "")) or "").strip().lower()
        width = max(0.0, float(row.get("width", row.get("Width", 0.0)) or 0.0))
        extra = max(0.0, float(row.get("extraWidth", row.get("ExtraWidth", 0.0)) or 0.0))
        if typ in ("curb", "berm"):
            return float(width + extra)
        return float(width)

    @staticmethod
    def _component_segments_from_payload(payload):
        component_rows = list(payload.get("component_rows", []) or [])
        explicit_segments = []
        for row in component_rows:
            kind = str(row.get("kind", "") or "").strip().lower()
            if kind != "component_segment":
                continue
            try:
                x0 = float(row.get("x0", 0.0) or 0.0)
                x1 = float(row.get("x1", 0.0) or 0.0)
            except Exception:
                continue
            span = abs(x1 - x0)
            if span <= 1e-9:
                continue
            explicit_segments.append(
                {
                    "side": str(row.get("side", "") or "").strip().lower() or "-",
                    "x0": float(min(x0, x1)),
                    "x1": float(max(x0, x1)),
                    "mid": float(0.5 * (x0 + x1)),
                    "span": float(span),
                    "order": int(float(row.get("order", 0) or 0)),
                    "id": str(row.get("id", "") or "").strip() or "-",
                    "type": str(row.get("type", "") or "").strip().lower() or "-",
                    "shape": str(row.get("shape", "") or "").strip().lower() or "-",
                    "label": str(row.get("label", "") or "").strip(),
                    "scope": str(row.get("scope", "") or "").strip().lower(),
                    "source": str(row.get("source", "") or "").strip(),
                }
            )
        if explicit_segments:
            return explicit_segments

        component_rows = [
            row for row in component_rows
            if str(row.get("kind", "") or "").strip().lower() == "component"
        ]
        if not component_rows:
            return []

        def _sorted(rows):
            return sorted(rows, key=lambda row: int(float(row.get("order", 0) or 0)))

        left_rows = _sorted([row for row in component_rows if str(row.get("side", "") or "").strip().lower() == "left"])
        right_rows = _sorted([row for row in component_rows if str(row.get("side", "") or "").strip().lower() == "right"])
        both_rows = _sorted([row for row in component_rows if str(row.get("side", "") or "").strip().lower() == "both"])
        left_rows.extend(dict(row, side="left") for row in both_rows)
        right_rows.extend(dict(row, side="right") for row in both_rows)

        out = []
        cur = 0.0
        for row in left_rows:
            seg_w = CrossSectionViewerTaskPanel._component_effective_width_from_row(row)
            if seg_w <= 1e-9:
                continue
            x0 = cur - seg_w
            x1 = cur
            out.append(
                {
                    "side": "left",
                    "x0": float(x0),
                    "x1": float(x1),
                    "mid": float(0.5 * (x0 + x1)),
                    "span": float(seg_w),
                    "order": int(float(row.get("order", 0) or 0)),
                    "id": str(row.get("id", "") or "").strip() or "-",
                    "type": str(row.get("type", "") or "").strip().lower() or "-",
                    "shape": str(row.get("shape", "") or "").strip().lower() or "-",
                    "scope": str(row.get("scope", "") or "").strip().lower(),
                }
            )
            cur = x0

        cur = 0.0
        for row in right_rows:
            seg_w = CrossSectionViewerTaskPanel._component_effective_width_from_row(row)
            if seg_w <= 1e-9:
                continue
            x0 = cur
            x1 = cur + seg_w
            out.append(
                {
                    "side": "right",
                    "x0": float(x0),
                    "x1": float(x1),
                    "mid": float(0.5 * (x0 + x1)),
                    "span": float(seg_w),
                    "order": int(float(row.get("order", 0) or 0)),
                    "id": str(row.get("id", "") or "").strip() or "-",
                    "type": str(row.get("type", "") or "").strip().lower() or "-",
                    "shape": str(row.get("shape", "") or "").strip().lower() or "-",
                    "scope": str(row.get("scope", "") or "").strip().lower(),
                }
            )
            cur = x1
        return out

    @staticmethod
    def _sample_section_top_y(payload, x: float, default_y: float = 0.0):
        x = float(x or 0.0)
        best_y = None
        for poly in list(dict(payload or {}).get("section_polylines", []) or []):
            pts = list(poly or [])
            if len(pts) < 2:
                continue
            for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
                x0 = float(x0)
                x1 = float(x1)
                y0 = float(y0)
                y1 = float(y1)
                if abs(x1 - x0) <= 1e-9:
                    if abs(x - x0) <= 1e-9:
                        cand = max(y0, y1)
                        best_y = cand if best_y is None else max(best_y, cand)
                    continue
                left = min(x0, x1)
                right = max(x0, x1)
                if x < left or x > right:
                    continue
                t = (x - x0) / (x1 - x0)
                cand = y0 + (t * (y1 - y0))
                best_y = cand if best_y is None else max(best_y, cand)
        if best_y is None:
            return float(default_y or 0.0)
        return float(best_y)

    @staticmethod
    def _component_full_label(seg):
        side = str(seg.get("side", "") or "").strip().lower()
        typ = str(seg.get("type", "") or "").strip().lower()
        shape = str(seg.get("shape", "") or "").strip().lower()
        side_txt = "L" if side == "left" else ("R" if side == "right" else "")
        name = {
            "lane": "Lane",
            "carriageway": "Carriageway",
            "side_slope": "Side Slope",
            "cut_slope": "Cut Slope",
            "fill_slope": "Fill Slope",
            "shoulder": "Shoulder",
            "median": "Median",
            "curb": "Curb",
            "ditch": "Ditch",
            "berm": "Berm",
            "bench": "Bench",
            "sidewalk": "Sidewalk",
            "bike_lane": "Bike Lane",
            "green_strip": "Green Strip",
        }.get(typ, typ.title() if typ else "Component")
        if typ == "ditch" and shape not in ("", "-", "v"):
            shape_txt = "U" if shape == "u" else ("Trapezoid" if shape == "trapezoid" else shape.title())
            name = f"{name} ({shape_txt})"
        return f"{side_txt} {name}".strip()

    @staticmethod
    def _component_visual_label(seg):
        explicit = str(seg.get("label", "") or seg.get("name", "") or "").strip()
        typ = str(seg.get("type", "") or "").strip().lower()
        shape = str(seg.get("shape", "") or "").strip().lower()
        if typ == "ditch" and shape not in ("", "-", "v"):
            base = explicit or "ditch"
            return f"{base}({shape})"
        if explicit:
            return explicit
        if typ:
            return typ
        return "Component"

    @staticmethod
    def _component_scope(seg):
        scope = str(seg.get("scope", "") or "").strip().lower()
        if scope:
            return scope
        typ = str(seg.get("type", "") or "").strip().lower()
        if typ in ("side_slope", "bench", "cut_slope", "fill_slope", "daylight"):
            return "side_slope"
        return "typical"

    @staticmethod
    def _component_scope_priority(scope: str):
        scope = str(scope or "").strip().lower()
        if scope == "typical":
            return 3
        if scope == "daylight":
            return 2
        if scope == "side_slope":
            return 1
        return 0

    @staticmethod
    def _component_scope_counts(rows):
        counts = {"typical": 0, "side_slope": 0, "daylight": 0, "other": 0}
        for row in list(rows or []):
            scope = CrossSectionViewerTaskPanel._component_scope(row)
            if scope in counts:
                counts[scope] += 1
            else:
                counts["other"] += 1
        return counts

    @staticmethod
    def _planned_component_scope_counts(rows):
        counts = {"typical": 0, "side_slope": 0, "daylight": 0, "other": 0}
        for row in list(rows or []):
            role = str(row.get("role", "") or "").strip()
            if not (role.startswith("component:") or role.startswith("component_value:") or role.startswith("daylight")):
                continue
            scope = str(row.get("scope", "") or "").strip().lower()
            key = scope if scope in counts else "other"
            counts[key] += 1
        return counts

    @staticmethod
    def _scope_enabled(scope: str, show_typical: bool = True, show_side_slope: bool = True, show_daylight: bool = True):
        scope = str(scope or "").strip().lower()
        if scope == "typical":
            return bool(show_typical)
        if scope == "side_slope":
            return bool(show_side_slope)
        if scope == "daylight":
            return bool(show_daylight)
        return True

    @staticmethod
    def _row_scope(row):
        row = dict(row or {})
        scope = str(row.get("scope", "") or "").strip().lower()
        if scope:
            return scope
        role = str(row.get("role", "") or "").strip().lower()
        if role.startswith("daylight") or role == "daylight_marker":
            return "daylight"
        if role.startswith("component:") or role.startswith("component_value:"):
            return "side_slope" if "side_slope" in role or "cut_slope" in role or "fill_slope" in role or "bench" in role else "typical"
        return ""

    @staticmethod
    def _filter_layout_by_scope(payload, show_typical: bool = True, show_side_slope: bool = True, show_daylight: bool = True):
        payload = dict(payload or {})

        def _keep(row):
            scope = CrossSectionViewerTaskPanel._row_scope(row)
            return CrossSectionViewerTaskPanel._scope_enabled(
                scope,
                show_typical=show_typical,
                show_side_slope=show_side_slope,
                show_daylight=show_daylight,
            )

        for key in ("planned_label_rows", "planned_component_marker_rows", "planned_summary_rows"):
            payload[key] = [dict(row) for row in list(payload.get(key, []) or []) if _keep(row)]
        return payload

    @staticmethod
    def _summary_rows_grouped(summary_rows):
        groups = {"typical": [], "side_slope": [], "daylight": [], "other": []}
        for row in list(summary_rows or []):
            scope = str(row.get("scope", "") or "").strip().lower()
            text = str(row.get("text", "") or "").strip()
            if not text:
                continue
            key = scope if scope in groups else "other"
            groups[key].append(text)
        return groups

    @staticmethod
    def _append_summary_row(summary_rows, summary_seen, *, role: str, text: str, priority: int, placement_mode: str = "summary_only", category: str = "label", scope: str = ""):
        text = str(text or "").strip()
        role = str(role or "").strip()
        if not text:
            return
        key = (str(category or "").strip(), role, text)
        if key in summary_seen:
            return
        summary_seen.add(key)
        summary_rows.append(
            {
                "kind": "summary",
                "category": str(category or "label"),
                "role": role,
                "text": text,
                "priority": int(priority or 0),
                "placement_mode": str(placement_mode or "summary_only"),
                "scope": str(scope or "").strip().lower(),
            }
        )

    @staticmethod
    def _anchored_text_span(x: float, text_width: float, anchor: str):
        x = float(x or 0.0)
        text_width = max(0.0, float(text_width or 0.0))
        anchor = str(anchor or "left")
        if anchor == "center":
            return (x - (0.5 * text_width), x + (0.5 * text_width))
        if anchor == "right":
            return (x - text_width, x)
        return (x, x + text_width)

    @staticmethod
    def _interval_overlaps(a0: float, a1: float, b0: float, b1: float, pad: float = 0.0):
        left = min(float(a0), float(a1)) - float(pad)
        right = max(float(a0), float(a1)) + float(pad)
        other_left = min(float(b0), float(b1)) - float(pad)
        other_right = max(float(b0), float(b1)) + float(pad)
        return not (right <= other_left or other_right <= left)

    @staticmethod
    def _place_text_in_band(
        occupancy,
        band_name: str,
        x: float,
        anchor: str,
        text_width: float,
        base_y: float,
        step_y: float,
        max_slots: int = 4,
        pad: float = 0.18,
        linked_bands=None,
    ):
        linked_bands = list(linked_bands or [])
        for slot in range(max(1, int(max_slots))):
            key = f"{band_name}:{slot}"
            span = CrossSectionViewerTaskPanel._anchored_text_span(x, text_width, anchor)
            conflict_spans = list(occupancy.get(key, []) or [])
            for link in linked_bands:
                link_key = f"{str(link)}:{slot}"
                if link_key != key:
                    conflict_spans.extend(list(occupancy.get(link_key, []) or []))
            conflict = False
            for other0, other1 in conflict_spans:
                if CrossSectionViewerTaskPanel._interval_overlaps(span[0], span[1], other0, other1, pad=pad):
                    conflict = True
                    break
            if conflict:
                continue
            used = occupancy.setdefault(key, [])
            used.append(span)
            return float(base_y + (slot * step_y)), int(slot)
        return None, None

    @staticmethod
    def build_layout_plan(payload):
        payload = dict(payload or {})
        bounds = dict(payload.get("bounds", {}) or {})
        xmin = float(bounds.get("xmin", -1.0))
        xmax = float(bounds.get("xmax", 1.0))
        ymin = float(bounds.get("ymin", -1.0))
        ymax = float(bounds.get("ymax", 1.0))
        width = max(1.0, float(bounds.get("width", abs(xmax - xmin)) or abs(xmax - xmin)))
        height = max(1.0, float(bounds.get("height", abs(ymax - ymin)) or abs(ymax - ymin)))
        left_extent = max(0.0, -xmin)
        right_extent = max(0.0, xmax)

        planned_title_rows = []
        station_label = str(payload.get("station_label", "") or "").strip()
        if station_label:
            planned_title_rows.append(
                {
                    "kind": "title",
                    "role": "station_title",
                    "text": station_label,
                    "x": float(xmin),
                    "y": float(ymax + (0.34 * height)),
                    "anchor": "left",
                    "svg_font_size": 0.22,
                    "viewer_point_size": 3.2,
                    "color": "#c3d7ff",
                    "rotation_deg": 0.0,
                }
            )

        occupancy = {}
        planned_summary_rows = []
        planned_component_marker_rows = []
        summary_seen = set()
        has_component_rows = bool(list(payload.get("component_rows", []) or []))
        summary_preferred_roles = {"structure_summary", "daylight_note", "station_tags"}
        has_daylight_rows = bool(list(payload.get("daylight_rows", []) or []))
        for row in planned_title_rows:
            title_span = CrossSectionViewerTaskPanel._anchored_text_span(
                float(row.get("x", xmin) or xmin),
                CrossSectionViewerTaskPanel._estimate_text_width(str(row.get("text", "") or ""), float(row.get("svg_font_size", 0.62) or 0.62)),
                str(row.get("anchor", "left") or "left"),
            )
            occupancy.setdefault("title_block:0", []).append(title_span)

        planned_labels = []
        for row in list(payload.get("label_rows", []) or []):
            role = str(row.get("role", "") or "")
            text = str(row.get("text", "") or "").strip()
            if not text:
                continue
            priority = CrossSectionViewerTaskPanel._label_priority(role)
            if role == "daylight_note" and has_daylight_rows:
                CrossSectionViewerTaskPanel._append_summary_row(
                    planned_summary_rows,
                    summary_seen,
                    role=role,
                    text=text,
                    priority=priority,
                    placement_mode="summary_only",
                    category="diagnostic_label",
                    scope="daylight",
                )
                continue
            if has_component_rows and (
                role in summary_preferred_roles
                or role in ("top_edge_left", "top_edge_right")
            ):
                CrossSectionViewerTaskPanel._append_summary_row(
                    planned_summary_rows,
                    summary_seen,
                    role=role,
                    text=text,
                    priority=priority,
                    placement_mode="summary_only",
                    category="diagnostic_label",
                )
                continue
            anchor = "left"
            base_y = ymax + (0.10 * height)
            band_name = "top_left"
            available = 0.45 * width
            orientation = "horizontal"
            rotation_deg = 0.0
            font_scale = 1.0
            if role == "top_edge_right":
                anchor = "right"
                band_name = "top_right"
                available = 0.45 * width
            elif role == "structure_summary":
                anchor = "center"
                base_y = ymax + (0.16 * height)
                band_name = "top_center"
                available = 0.58 * width
            elif role == "daylight_note":
                anchor = "left"
                base_y = ymin - (0.18 * height)
                band_name = "bottom_note"
                available = 0.55 * width
            elif role == "station_tags":
                anchor = "left"
                base_y = ymax + (0.20 * height)
                band_name = "top_left"
                available = 0.38 * width
            svg_font_size = 0.46
            full_text = text
            short_text = CrossSectionViewerTaskPanel._compact_label_text(role, text)
            chosen = full_text
            max_slots = 3 if band_name != "bottom_note" else 2
            if CrossSectionViewerTaskPanel._estimate_text_width(full_text, svg_font_size) > available:
                chosen = short_text
            fit_scale = CrossSectionViewerTaskPanel._fit_font_scale(chosen, svg_font_size, available, min_scale=0.80, orientation="horizontal")
            if fit_scale is None and chosen != short_text:
                chosen = short_text
                fit_scale = CrossSectionViewerTaskPanel._fit_font_scale(chosen, svg_font_size, available, min_scale=0.80, orientation="horizontal")
            if fit_scale is not None:
                font_scale = float(fit_scale)
            if fit_scale is None:
                chosen = short_text
                placement_mode = "summary_only"
            else:
                placement_mode = "stacked" if band_name != "bottom_note" else "outside_left"
            if placement_mode == "summary_only":
                CrossSectionViewerTaskPanel._append_summary_row(
                    planned_summary_rows,
                    summary_seen,
                    role=role,
                    text=full_text,
                    priority=priority,
                    placement_mode="summary_only",
                    category="label",
                )
                continue
            text_width = CrossSectionViewerTaskPanel._estimate_text_width(chosen, svg_font_size * font_scale)
            step_y = 0.07 * height if band_name != "bottom_note" else -0.07 * height
            y, slot = CrossSectionViewerTaskPanel._place_text_in_band(
                occupancy,
                band_name,
                float(row.get("x", 0.0) or 0.0),
                anchor,
                text_width,
                base_y,
                step_y,
                max_slots=max_slots,
                pad=0.20,
                linked_bands=["title_block"] if band_name.startswith("top_") else [],
            )
            if y is None:
                if chosen != short_text:
                    chosen = short_text
                    text_width = CrossSectionViewerTaskPanel._estimate_text_width(chosen, svg_font_size)
                    y, slot = CrossSectionViewerTaskPanel._place_text_in_band(
                        occupancy,
                        band_name,
                        float(row.get("x", 0.0) or 0.0),
                        anchor,
                        text_width,
                        base_y,
                        step_y,
                        max_slots=max_slots,
                        pad=0.20,
                        linked_bands=["title_block"] if band_name.startswith("top_") else [],
                    )
            if y is None:
                CrossSectionViewerTaskPanel._append_summary_row(
                    planned_summary_rows,
                    summary_seen,
                    role=role,
                    text=full_text,
                    priority=priority,
                    placement_mode="summary_only",
                    category="label",
                )
                continue
            planned_labels.append(
                {
                    "kind": "label",
                    "role": role,
                    "priority": priority,
                    "text": chosen,
                    "x": float(row.get("x", 0.0) or 0.0),
                    "y": float(y),
                    "anchor": anchor,
                    "orientation": orientation,
                    "rotation_deg": rotation_deg,
                    "font_scale": float(font_scale),
                    "min_font_scale": 0.80,
                    "fit_mode": "span_fit" if float(font_scale) < 0.999 else "fixed",
                    "svg_font_size": svg_font_size * font_scale,
                    "viewer_point_size": 5.2 * font_scale,
                    "color": CrossSectionViewerTaskPanel._svg_label_color(role),
                    "placement_mode": "stacked" if int(slot or 0) > 0 else placement_mode,
                    "slot": int(slot or 0),
                }
            )

        for row in list(payload.get("daylight_rows", []) or []):
            side = str(row.get("side", "") or "").strip().lower()
            scope = str(row.get("scope", "daylight") or "daylight").strip().lower() or "daylight"
            role = "daylight_marker"
            priority = 42
            x = float(row.get("x", 0.0) or 0.0)
            base_y = float(row.get("y", ymin) or ymin)
            marker_top_y = float(base_y + (0.34 * height))
            planned_component_marker_rows.append(
                {
                    "kind": "component_marker",
                    "role": role,
                    "scope": scope,
                    "side": side,
                    "x0": x,
                    "x1": x,
                    "mid": x,
                    "y_base": base_y,
                    "y_base_left": base_y,
                    "y_base_right": base_y,
                    "y_top": marker_top_y,
                    "color": "#b7d88a",
                    "tick_len": float(max(0.12, min(0.24, 0.06 * height))),
                    "stroke_width": 0.16,
                    "marker_style": "daylight_marker",
                    "cap_mode": "base",
                }
            )
            daylight_band = f"daylight_{side or 'center'}"
            text = str(row.get("label", "daylight") or "daylight")
            svg_font_size = 0.15
            font_scale = 1.0
            available = max(0.50, 0.30 * height)
            fit_scale = CrossSectionViewerTaskPanel._fit_font_scale(text, svg_font_size, available, min_scale=0.40, orientation="vertical")
            if fit_scale is not None:
                font_scale = float(fit_scale)
            y, slot = CrossSectionViewerTaskPanel._place_text_in_band(
                occupancy,
                daylight_band,
                x,
                "center",
                max(0.10, (svg_font_size * max(0.40, font_scale) * 1.30)),
                marker_top_y + (0.04 * height),
                0.14 * height,
                max_slots=2,
                pad=0.16,
                linked_bands=[f"component_label_side_slope_{side or 'center'}"],
            )
            if y is None:
                CrossSectionViewerTaskPanel._append_summary_row(
                    planned_summary_rows,
                    summary_seen,
                    role=role,
                    text="daylight",
                    priority=priority,
                    placement_mode="summary_only",
                    category="component_label",
                    scope=scope,
                )
            else:
                planned_labels.append(
                    {
                        "kind": "label",
                        "role": "daylight_label",
                        "scope": scope,
                        "priority": priority,
                        "text": text,
                        "x": x,
                        "y": float(y),
                        "anchor": "center",
                        "orientation": "vertical",
                        "rotation_deg": -90.0,
                        "font_scale": float(font_scale),
                        "min_font_scale": 0.40,
                        "fit_mode": "vertical",
                        "svg_font_size": svg_font_size * max(0.40, font_scale),
                        "viewer_point_size": 1.05 * max(0.40, font_scale),
                        "color": "#b7d88a",
                        "placement_mode": "daylight_vertical",
                        "slot": int(slot or 0),
                    }
                )

        raw_dimension_rows = list(payload.get("dimension_rows", []) or [])
        component_segments = list(CrossSectionViewerTaskPanel._component_segments_from_payload(payload) or [])
        component_segments = sorted(
            component_segments,
            key=lambda seg: (
                -CrossSectionViewerTaskPanel._component_scope_priority(
                    CrossSectionViewerTaskPanel._component_scope(seg)
                ),
                float(seg.get("x0", 0.0) or 0.0),
                float(seg.get("x1", 0.0) or 0.0),
                -CrossSectionViewerTaskPanel._component_label_priority(seg.get("type", "")),
                int(float(seg.get("order", 0) or 0)),
            ),
        )
        component_count = max(1, int(len(component_segments) or 0))
        component_crowd_scale = 1.0
        if component_count > 6:
            component_crowd_scale = max(0.45, min(1.0, 6.0 / float(component_count)))
        for seg in component_segments:
            typ = str(seg.get("type", "") or "").strip().lower()
            scope = CrossSectionViewerTaskPanel._component_scope(seg)
            role = f"component:{typ}"
            value_role = f"component_value:{typ}"
            priority = CrossSectionViewerTaskPanel._component_label_priority(typ)
            if scope == "side_slope":
                priority = max(24, priority - 18)
            full_name = CrossSectionViewerTaskPanel._component_visual_label(seg)
            short_name = CrossSectionViewerTaskPanel._component_short_visual_label(seg)
            full_text = str(full_name or short_name or typ.title() or "Comp")
            short_text = str(short_name or full_text)
            span = max(0.0, float(seg.get("span", 0.0) or 0.0))
            value_text = f"{span:.3f} m"
            side = str(seg.get("side", "") or "").strip().lower()
            band_name = f"component_label_{scope}_{side or 'center'}"
            value_band_name = f"component_value_{scope}_{side or 'center'}"
            counterpart_band = f"component_label_{'side_slope' if scope == 'typical' else 'typical'}_{side or 'center'}"
            counterpart_value_band = f"component_value_{'side_slope' if scope == 'typical' else 'typical'}_{side or 'center'}"
            svg_font_size = 0.16 * component_crowd_scale * (0.74 if scope == "side_slope" else 1.0)
            available = max(0.0, span - 0.10)
            local_top_y = CrossSectionViewerTaskPanel._sample_section_top_y(
                payload,
                float(seg.get("mid", 0.0) or 0.0),
                default_y=ymax,
            )
            base_left_y = CrossSectionViewerTaskPanel._sample_section_top_y(
                payload,
                float(seg.get("x0", 0.0) or 0.0),
                default_y=local_top_y,
            )
            base_right_y = CrossSectionViewerTaskPanel._sample_section_top_y(
                payload,
                float(seg.get("x1", 0.0) or 0.0),
                default_y=local_top_y,
            )
            orientation = "vertical"
            rotation_deg = -90.0
            chosen = None
            font_scale = None
            if available > 1e-6:
                min_full_scale = 0.22 if scope == "side_slope" else 0.34
                min_short_scale = 0.20 if scope == "side_slope" else 0.30
                vert_full_scale = CrossSectionViewerTaskPanel._fit_font_scale(full_text, svg_font_size, available, min_scale=min_full_scale, orientation="vertical")
                vert_short_scale = CrossSectionViewerTaskPanel._fit_font_scale(short_text, svg_font_size, available, min_scale=min_short_scale, orientation="vertical")
                if vert_full_scale is not None:
                    chosen = full_text
                    font_scale = vert_full_scale
                elif vert_short_scale is not None:
                    chosen = short_text
                    font_scale = vert_short_scale
            if chosen is None:
                continue
            guide_base_y = max(float(local_top_y), float(base_left_y), float(base_right_y))
            guide_top_y = float(guide_base_y + (0.82 * height))
            marker_tick = max(0.18, min(0.44, 0.10 * height))
            marker_stroke = 0.22 if typ in ("lane", "carriageway", "median") else 0.18
            marker_color = "#eef2f8" if scope == "typical" else "#d6dcc6"
            marker_row = {
                "kind": "component_marker",
                "role": role,
                "scope": scope,
                "side": side,
                "x0": float(seg.get("x0", 0.0) or 0.0),
                "x1": float(seg.get("x1", 0.0) or 0.0),
                "mid": float(seg.get("mid", 0.0) or 0.0),
                "y_base": float(local_top_y),
                "y_base_left": float(base_left_y),
                "y_base_right": float(base_right_y),
                "y_top": guide_top_y,
                "color": marker_color,
                "tick_len": float(marker_tick),
                "stroke_width": float(marker_stroke),
                "marker_style": "dimension_guide",
                "cap_mode": "both",
            }
            planned_component_marker_rows.append(marker_row)
            min_render_scale = 0.20 if scope == "side_slope" else 0.30
            label_svg_font_size = svg_font_size * max(min_render_scale, float(font_scale or 1.0))
            text_width = max(
                0.08,
                CrossSectionViewerTaskPanel._estimate_vertical_text_bandwidth(
                    label_svg_font_size,
                    kind="label",
                ),
            )
            value_svg_font_size = 0.12 * max(0.80, component_crowd_scale) * (0.66 if scope == "side_slope" else 1.0)
            value_scale = CrossSectionViewerTaskPanel._fit_font_scale(
                value_text,
                value_svg_font_size,
                available,
                min_scale=(0.18 if scope == "side_slope" else 0.30),
                orientation="vertical",
            )
            min_value_scale = 0.18 if scope == "side_slope" else 0.30
            value_text_width = 0.0
            fitted_value_svg_font_size = 0.0
            value_extent = 0.0
            if value_scale is not None:
                fitted_value_svg_font_size = value_svg_font_size * max(min_value_scale, float(value_scale or 1.0))
                value_text_width = max(
                    0.06,
                    CrossSectionViewerTaskPanel._estimate_vertical_text_bandwidth(
                        fitted_value_svg_font_size,
                        kind="value",
                    ),
                )
                value_extent = CrossSectionViewerTaskPanel._estimate_text_width(
                    value_text,
                    fitted_value_svg_font_size,
                )
            label_extent = CrossSectionViewerTaskPanel._estimate_text_width(
                chosen,
                label_svg_font_size,
            )
            block_gap = CrossSectionViewerTaskPanel._component_vertical_clearance(
                typ=typ,
                label_extent=label_extent,
                value_extent=value_extent,
                label_svg_font_size=label_svg_font_size,
                value_svg_font_size=fitted_value_svg_font_size,
                height=height,
            )
            block_extent = label_extent + ((block_gap + value_extent) if value_scale is not None else 0.0)
            guide_len = max(0.20, guide_top_y - guide_base_y)
            block_start_y = guide_base_y + (0.33 * guide_len)
            type_width_floor = 0.24 if typ in ("bench", "cut_slope", "fill_slope", "side_slope") else 0.18
            block_width = max(text_width, type_width_floor)
            block_band = f"component_block_{scope}_{side or 'center'}"
            block_max_slots = 4 if scope == "typical" else 7
            block_step_y = max(0.18 * height, block_extent + (0.10 * height))
            block_y, slot = CrossSectionViewerTaskPanel._place_text_in_band(
                occupancy,
                block_band,
                float(seg.get("mid", 0.0) or 0.0),
                "center",
                block_width,
                block_start_y,
                block_step_y,
                max_slots=block_max_slots,
                pad=0.22 if scope == "side_slope" else 0.20,
                linked_bands=(
                    ([counterpart_band, counterpart_value_band] + (["top_left"] if side == "left" else (["top_right"] if side == "right" else [])))
                    if scope == "side_slope"
                    else (["top_left"] if side == "left" else (["top_right"] if side == "right" else []))
                ),
            )
            if block_y is None and chosen != short_text:
                chosen = short_text
                font_scale = CrossSectionViewerTaskPanel._fit_font_scale(
                    chosen,
                    svg_font_size,
                    available,
                    min_scale=(0.20 if scope == "side_slope" else 0.30),
                    orientation="vertical",
                )
                label_svg_font_size = svg_font_size * max(min_render_scale, float(font_scale or 1.0))
                text_width = max(
                    0.08,
                    CrossSectionViewerTaskPanel._estimate_vertical_text_bandwidth(
                        label_svg_font_size,
                        kind="label",
                    ),
                )
                label_extent = CrossSectionViewerTaskPanel._estimate_text_width(
                    chosen,
                    label_svg_font_size,
                )
                if value_scale is not None:
                    value_extent = CrossSectionViewerTaskPanel._estimate_text_width(
                        value_text,
                        fitted_value_svg_font_size,
                    )
                else:
                    value_extent = 0.0
                block_gap = CrossSectionViewerTaskPanel._component_vertical_clearance(
                    typ=typ,
                    label_extent=label_extent,
                    value_extent=value_extent,
                    label_svg_font_size=label_svg_font_size,
                    value_svg_font_size=fitted_value_svg_font_size,
                    height=height,
                )
                block_extent = label_extent + ((block_gap + value_extent) if value_scale is not None else 0.0)
                block_width = max(text_width, type_width_floor)
                block_step_y = max(0.18 * height, block_extent + (0.10 * height))
                block_y, slot = CrossSectionViewerTaskPanel._place_text_in_band(
                    occupancy,
                    block_band,
                    float(seg.get("mid", 0.0) or 0.0),
                    "center",
                    block_width,
                    block_start_y,
                    block_step_y,
                    max_slots=block_max_slots,
                    pad=0.22 if scope == "side_slope" else 0.20,
                    linked_bands=(
                        ([counterpart_band, counterpart_value_band] + (["top_left"] if side == "left" else (["top_right"] if side == "right" else [])))
                        if scope == "side_slope"
                        else (["top_left"] if side == "left" else (["top_right"] if side == "right" else []))
                    ),
                )
            if block_y is None:
                continue
            label_y = float(block_y) + (0.50 * label_extent)
            marker_row["y_top"] = max(float(marker_row.get("y_top", guide_top_y) or guide_top_y), float(block_y) - (0.06 * height))
            planned_labels.append(
                {
                    "kind": "label",
                    "role": role,
                    "scope": scope,
                    "priority": priority,
                    "text": chosen,
                    "x": float(seg.get("mid", 0.0) or 0.0),
                    "y": float(label_y),
                    "anchor": "center",
                    "orientation": orientation,
                    "rotation_deg": rotation_deg,
                    "font_scale": float(max(min_render_scale, float(font_scale or 1.0))),
                    "min_font_scale": min_render_scale,
                    "fit_mode": "span_fit" if float(font_scale or 1.0) < 0.999 else "vertical",
                    "svg_font_size": label_svg_font_size,
                    "viewer_point_size": (0.78 if scope == "side_slope" else 1.02) * max(min_render_scale, float(font_scale or 1.0)),
                    "color": CrossSectionViewerTaskPanel._svg_label_color(role),
                    "placement_mode": "component_block" if int(slot or 0) == 0 else "stacked_block",
                    "slot": int(slot or 0),
                }
            )
            if value_scale is not None:
                extra_value_clearance = max(
                    0.12,
                    0.08 * max(float(height or 0.0), 1.0),
                    0.60 * max(float(label_svg_font_size or 0.0), float(fitted_value_svg_font_size or 0.0), 0.10),
                )
                if typ in ("bench", "cut_slope", "fill_slope", "side_slope"):
                    extra_value_clearance = max(
                        extra_value_clearance,
                        0.16,
                        0.12 * max(float(height or 0.0), 1.0),
                    )
                value_y = (
                    float(label_y)
                    + (0.50 * label_extent)
                    + block_gap
                    + extra_value_clearance
                    + (0.50 * value_extent)
                )
                planned_labels.append(
                    {
                        "kind": "label",
                        "role": value_role,
                        "scope": scope,
                        "priority": max(12, priority - 4),
                        "text": value_text,
                        "x": float(seg.get("mid", 0.0) or 0.0),
                        "y": float(value_y),
                        "anchor": "center",
                        "orientation": orientation,
                        "rotation_deg": rotation_deg,
                        "font_scale": float(max(min_value_scale, float(value_scale or 1.0))),
                        "min_font_scale": min_value_scale,
                        "fit_mode": "span_fit" if float(value_scale or 1.0) < 0.999 else "vertical",
                        "svg_font_size": fitted_value_svg_font_size,
                        "viewer_point_size": (0.70 if scope == "side_slope" else 0.92) * max(min_value_scale, float(value_scale or 1.0)),
                        "color": CrossSectionViewerTaskPanel._svg_label_color(value_role),
                        "placement_mode": "component_block_value" if int(slot or 0) == 0 else "stacked_block_value",
                        "slot": int(slot or 0),
                    }
                )
            else:
                pass

        planned_dims = []
        dim_rows = sorted(
            raw_dimension_rows,
            key=lambda row: {
                "overall_width": 30,
            }.get(str(row.get("kind", "") or ""), 10),
        )
        for row in dim_rows:
            role = str(row.get("role", row.get("kind", "")) or "")
            kind = str(row.get("kind", "") or "")
            value = float(row.get("value", 0.0) or 0.0)
            x0 = float(row.get("x0", 0.0) or 0.0)
            x1 = float(row.get("x1", 0.0) or 0.0)
            span = abs(x1 - x0)
            if span <= 1e-9:
                continue
            if kind in ("left_reach", "right_reach") or kind.startswith("component_"):
                continue
            full_text = str(row.get("label", "") or "").strip()
            short_text = CrossSectionViewerTaskPanel._compact_dimension_label(role or kind, value)
            numeric_text = CrossSectionViewerTaskPanel._numeric_dimension_label(value)
            svg_font_size = 0.26 if kind.startswith("component_") else 0.34
            full_need = CrossSectionViewerTaskPanel._estimate_text_width(full_text, svg_font_size) * 1.20
            short_need = CrossSectionViewerTaskPanel._estimate_text_width(short_text, svg_font_size) * 1.15
            numeric_need = CrossSectionViewerTaskPanel._estimate_text_width(numeric_text, svg_font_size) * 1.10
            font_scale = 1.0
            if kind == "overall_width":
                band = "overall_dim"
                base_y = ymin - (0.78 * height)
                priority = 100
                max_slots = 2
                linked_bands = []
            else:
                side_hint = "left" if x1 <= 0.0 else ("right" if x0 >= 0.0 else "center")
                band = f"component_dim_{side_hint}"
                base_y = ymin - (1.02 * height)
                priority = 60
                max_slots = 5
                linked_bands = ["overall_dim"]
            if span >= full_need:
                chosen = full_text
                placement_mode = "inside_span"
            elif span >= short_need:
                chosen = short_text
                placement_mode = "inside_span"
            elif span >= numeric_need and kind not in ("overall_width",):
                chosen = numeric_text
                placement_mode = "inside_span"
            elif kind.startswith("component_"):
                chosen = numeric_text
                placement_mode = "outside_band"
            elif kind in ("overall_width",):
                chosen = short_text
                placement_mode = "outside_band"
            else:
                continue
            text_width = CrossSectionViewerTaskPanel._estimate_text_width(chosen, svg_font_size * font_scale)
            step_y = -(0.16 * height)
            y, slot = CrossSectionViewerTaskPanel._place_text_in_band(
                occupancy,
                band,
                0.5 * (x0 + x1),
                "center",
                text_width,
                base_y,
                step_y,
                max_slots=max_slots,
                pad=0.14,
                linked_bands=linked_bands,
            )
            if y is None and chosen != short_text:
                chosen = short_text
                text_width = CrossSectionViewerTaskPanel._estimate_text_width(chosen, svg_font_size)
                y, slot = CrossSectionViewerTaskPanel._place_text_in_band(
                    occupancy,
                    band,
                    0.5 * (x0 + x1),
                    "center",
                    text_width,
                    base_y,
                    step_y,
                    max_slots=max_slots,
                    pad=0.14,
                    linked_bands=linked_bands,
                )
            if y is None and chosen != numeric_text and kind not in ("overall_width",):
                chosen = numeric_text
                text_width = CrossSectionViewerTaskPanel._estimate_text_width(chosen, svg_font_size)
                y, slot = CrossSectionViewerTaskPanel._place_text_in_band(
                    occupancy,
                    band,
                    0.5 * (x0 + x1),
                    "center",
                    text_width,
                    base_y,
                    step_y,
                    max_slots=max_slots,
                    pad=0.12,
                    linked_bands=linked_bands,
                )
            if y is None:
                if kind in ("overall_width", "left_reach", "right_reach"):
                    y = float(base_y + (max_slots * step_y))
                    slot = max_slots
                    chosen = short_text
                else:
                    continue
            planned_dims.append(
                {
                    "kind": "dimension",
                    "role": role or kind,
                    "priority": priority,
                    "band": band,
                    "x0": x0,
                    "x1": x1,
                    "y": float(y),
                    "text": chosen,
                    "orientation": "horizontal",
                    "rotation_deg": 0.0,
                    "font_scale": float(font_scale),
                    "min_font_scale": 0.70 if kind.startswith("component_") else 1.0,
                    "fit_mode": "span_fit" if float(font_scale) < 0.999 else "fixed",
                    "svg_font_size": svg_font_size * font_scale,
                    "viewer_point_size": 2.9 * font_scale,
                    "color": CrossSectionViewerTaskPanel._svg_dimension_color(role or kind),
                    "placement_mode": "stacked" if int(slot or 0) > 0 else placement_mode,
                    "value": value,
                    "span": span,
                    "slot": int(slot or 0),
                }
            )

        planned_summary_rows.sort(key=lambda row: (-int(row.get("priority", 0) or 0), str(row.get("text", "") or "")))
        return {
            "planned_title_rows": planned_title_rows,
            "planned_label_rows": planned_labels,
            "planned_dimension_rows": planned_dims,
            "planned_component_marker_rows": planned_component_marker_rows,
            "planned_summary_rows": planned_summary_rows,
        }

    def _add_scene_label(self, text, x, y, color, anchor: str = "left", point_size: float = 5.0, rotation_deg: float = 0.0, vertical_anchor: str = "bottom"):
        item = self.scene.addText(str(text or ""))
        font = item.font()
        font.setPointSizeF(max(0.35, float(point_size)))
        item.setFont(font)
        item.setDefaultTextColor(QtGui.QColor(color))
        br = item.boundingRect()
        rotation_deg = float(rotation_deg or 0.0)
        if abs(rotation_deg) > 1e-6:
            item.setTransformOriginPoint(br.center())
            item.setPos(float(x) - float(br.center().x()), -float(y) - float(br.center().y()))
            item.setRotation(rotation_deg)
            return item
        px = float(x)
        if anchor == "center":
            px -= 0.5 * float(br.width())
        elif anchor == "right":
            px -= float(br.width())
        if str(vertical_anchor or "bottom").strip().lower() == "top":
            item.setPos(px, -float(y))
        else:
            item.setPos(px, -float(y) - float(br.height()))
        return item

    def _render_current_payload(self, *_args):
        if self._loading:
            return
        sec = self._current_section_set()
        row = self._current_station_row()
        self.scene.clear()
        self._last_fit_rect = None
        self._current_payload = None

        if sec is None or row is None:
            self.txt_summary.setPlainText("Select a SectionSet and station.")
            self.scene.addText("No section selected.")
            return

        payload = SectionSet.resolve_viewer_payload(
            sec,
            index=int(row.get("index", 0)),
            include_structure_overlay=bool(self.chk_show_structures.isChecked()),
        )
        if not payload:
            self.txt_summary.setPlainText("No cross-section payload available.")
            self.scene.addText("No section payload available.")
            return
        payload = dict(payload)
        payload.update(self.build_layout_plan(payload))
        self._current_payload = dict(payload)
        payload = self._filter_layout_by_scope(
            payload,
            show_typical=bool(self.chk_show_typical.isChecked()),
            show_side_slope=bool(self.chk_show_side_slope.isChecked()),
            show_daylight=bool(self.chk_show_daylight.isChecked()),
        )

        bounds = dict(payload.get("bounds", {}) or {})
        xmin = float(bounds.get("xmin", -1.0))
        xmax = float(bounds.get("xmax", 1.0))
        ymin = float(bounds.get("ymin", -1.0))
        ymax = float(bounds.get("ymax", 1.0))
        if abs(xmax - xmin) <= 1e-9:
            xmin -= 1.0
            xmax += 1.0
        if abs(ymax - ymin) <= 1e-9:
            ymin -= 1.0
            ymax += 1.0
        dx = max(1.0, abs(xmax - xmin))
        dy = max(1.0, abs(ymax - ymin))
        margin_x = 0.10 * dx
        margin_y = 0.12 * dy

        bg_brush = QtGui.QBrush(QtGui.QColor(26, 31, 44))
        bg_pen = QtGui.QPen(QtCore.Qt.NoPen)
        self.scene.addRect(
            xmin - margin_x,
            -(ymax + margin_y),
            (xmax - xmin) + (2.0 * margin_x),
            (ymax - ymin) + (2.0 * margin_y),
            bg_pen,
            bg_brush,
        )

        axis_pen = QtGui.QPen(QtGui.QColor(110, 130, 170))
        axis_pen.setStyle(QtCore.Qt.DashLine)
        axis_pen.setWidthF(0.0)
        self.scene.addLine(
            0.0,
            -(ymax + margin_y),
            0.0,
            -(ymin - margin_y),
            axis_pen,
        )

        section_pen = QtGui.QPen(QtGui.QColor(230, 230, 230))
        section_pen.setWidthF(0.0)
        for poly in list(payload.get("section_polylines", []) or []):
            path = self._poly_to_path(poly)
            if path is not None:
                self.scene.addPath(path, section_pen)

        overlay_pen = QtGui.QPen(QtGui.QColor(232, 96, 60))
        overlay_pen.setWidthF(0.0)
        for poly in list(payload.get("overlay_polylines", []) or []):
            path = self._poly_to_path(poly)
            if path is not None:
                self.scene.addPath(path, overlay_pen)

        for row in list(payload.get("planned_title_rows", []) or []):
            self._add_scene_label(
                str(row.get("text", "") or ""),
                float(row.get("x", xmin - margin_x) or (xmin - margin_x)),
                float(row.get("y", ymax + margin_y) or (ymax + margin_y)),
                row.get("color", "#c3d7ff"),
                anchor=str(row.get("anchor", "left") or "left"),
                point_size=float(row.get("viewer_point_size", 7.5) or 7.5),
                rotation_deg=float(row.get("rotation_deg", 0.0) or 0.0),
            )

        self._draw_component_marker_rows(list(payload.get("planned_component_marker_rows", []) or []))

        if bool(self.chk_show_dimensions.isChecked()):
            self._draw_dimension_rows(list(payload.get("planned_dimension_rows", []) or []))

        if bool(self.chk_show_labels.isChecked()):
            for row in list(payload.get("planned_label_rows", []) or []):
                self._add_scene_label(
                    str(row.get("text", "") or ""),
                    float(row.get("x", 0.0) or 0.0),
                    float(row.get("y", 0.0) or 0.0),
                    row.get("color", "#bccdeb"),
                    anchor=str(row.get("anchor", "left") or "left"),
                    point_size=float(row.get("viewer_point_size", 5.2) or 5.2),
                    rotation_deg=float(row.get("rotation_deg", 0.0) or 0.0),
                )

        fit_rect = self.scene.itemsBoundingRect()
        if fit_rect.isNull() or fit_rect.width() <= 1e-9 or fit_rect.height() <= 1e-9:
            fit_rect = QtCore.QRectF(
                xmin - margin_x,
                -(ymax + margin_y),
                (xmax - xmin) + (2.0 * margin_x),
                (ymax - ymin) + (2.0 * margin_y),
            )
        else:
            dx = max(1.0, float(fit_rect.width()))
            dy = max(1.0, float(fit_rect.height()))
            fit_rect = fit_rect.adjusted(-0.08 * dx, -0.10 * dy, 0.08 * dx, 0.10 * dy)
        self._last_fit_rect = fit_rect
        self.scene.setSceneRect(self._last_fit_rect)
        self._fit_view()

        self.txt_summary.setPlainText(
            "\n".join(self._summary_lines(payload, sec=sec, include_diagnostics=bool(self.chk_show_diagnostics.isChecked())))
        )

    def _summary_lines(self, payload, sec=None, include_diagnostics=True):
        blocks = CrossSectionViewerTaskPanel._summary_blocks(payload, sec=sec, include_diagnostics=include_diagnostics)
        return CrossSectionViewerTaskPanel._flatten_summary_blocks(blocks)

    @staticmethod
    def _summary_blocks(payload, sec=None, include_diagnostics=True):
        payload = dict(payload or {})
        sec = sec
        sec_label = str(getattr(sec, "Label", "SectionSet") or "SectionSet")
        sec_name = str(getattr(sec, "Name", "SectionSet") or "SectionSet")
        blocks = []

        context_lines = [
            f"Section Set: {sec_label} ({sec_name})",
            f"Station: {float(payload.get('station', 0.0)):.3f}",
            f"Station Tags: {str(payload.get('tag_summary', '-') or '-')}",
            f"Top Edges: {str(payload.get('top_profile_edge_summary', '-') or '-')}",
            f"Polylines: section={len(list(payload.get('section_polylines', []) or []))}, "
            f"overlay={len(list(payload.get('overlay_polylines', []) or []))}",
        ]
        blocks.append(("Context", context_lines))

        component_rows = list(payload.get("component_rows", []) or [])
        component_lines = [
            f"Pavement: {float(payload.get('pavement_total_thickness', 0.0) or 0.0):.3f} m "
            f"({int(payload.get('enabled_pavement_layer_count', 0) or 0)}/{int(payload.get('pavement_layer_count', 0) or 0)} layers)",
            f"Bench Summary: {str(payload.get('bench_summary', '-') or '-')}",
        ]
        if component_rows:
            scope_counts = CrossSectionViewerTaskPanel._component_scope_counts(component_rows)
            component_lines.append(
                "Component Scopes: "
                f"typical={int(scope_counts.get('typical', 0) or 0)}, "
                f"side_slope={int(scope_counts.get('side_slope', 0) or 0)}"
            )
        visible_scope_counts = CrossSectionViewerTaskPanel._planned_component_scope_counts(
            list(payload.get("planned_label_rows", []) or [])
        )
        if sum(int(v or 0) for v in visible_scope_counts.values()) > 0:
            component_lines.append(
                "Visible Component Annotations: "
                f"typical={int(visible_scope_counts.get('typical', 0) or 0)}, "
                f"side_slope={int(visible_scope_counts.get('side_slope', 0) or 0)}, "
                f"daylight={int(visible_scope_counts.get('daylight', 0) or 0)}"
            )
        blocks.append(("Components", component_lines))

        daylight_rows = list(payload.get("daylight_rows", []) or [])
        daylight_lines = []
        if daylight_rows:
            daylight_lines.append(f"Daylight Markers: {len(daylight_rows)}")
            daylight_mode = str(payload.get("daylight_mode", "") or "").strip()
            if daylight_mode:
                daylight_lines.append(f"Daylight Mode: {daylight_mode}")
            daylight_sides = [str(row.get("side", "") or "").strip().lower() for row in daylight_rows]
            daylight_sides = [side for side in daylight_sides if side]
            if daylight_sides:
                daylight_lines.append(f"Daylight Sides: {', '.join(daylight_sides)}")
        if daylight_lines:
            blocks.append(("Daylight", daylight_lines))

        structure_lines = [
            f"Structures: {', '.join(list(payload.get('structure_ids', []) or [])) or '-'}",
            f"Structure Summary: {str(payload.get('structure_summary', '-') or '-')}",
        ]
        blocks.append(("Structures", structure_lines))

        dim_rows = list(payload.get("planned_dimension_rows", payload.get("dimension_rows", [])) or [])
        dimension_lines = []
        if dim_rows:
            for row in dim_rows:
                dimension_lines.append(str(row.get('text', row.get('label', '')) or ''))
        if dimension_lines:
            blocks.append(("Dimensions", dimension_lines))

        summary_rows = list(payload.get("planned_summary_rows", []) or [])
        fallback_lines = []
        if summary_rows:
            grouped = CrossSectionViewerTaskPanel._summary_rows_grouped(summary_rows)
            if grouped.get("typical"):
                fallback_lines.append("Typical:")
                for txt in grouped.get("typical", [])[:4]:
                    fallback_lines.append(f"  {txt}")
            if grouped.get("side_slope"):
                fallback_lines.append("Side Slope:")
                for txt in grouped.get("side_slope", [])[:4]:
                    fallback_lines.append(f"  {txt}")
            if grouped.get("daylight"):
                fallback_lines.append("Daylight:")
                for txt in grouped.get("daylight", [])[:4]:
                    fallback_lines.append(f"  {txt}")
            if grouped.get("other"):
                fallback_lines.append("Other:")
                for txt in grouped.get("other", [])[:4]:
                    fallback_lines.append(f"  {txt}")
        if fallback_lines:
            blocks.append(("Summary Fallbacks", fallback_lines))

        if include_diagnostics:
            diagnostics_lines = []
            diag = list(payload.get("diagnostic_tokens", []) or [])
            diagnostics_lines.append(f"Diagnostics: {', '.join(diag) if diag else '-'}")
            bench_rows = list(payload.get("bench_rows", []) or [])
            structure_rows = list(payload.get("structure_rows", []) or [])
            component_row_texts = [str(row.get("raw", "") or "") for row in component_rows if str(row.get("raw", "") or "")]
            if component_row_texts:
                diagnostics_lines.append("Component Segments:")
                for row_txt in component_row_texts[:6]:
                    diagnostics_lines.append(f"  {row_txt}")
            if bench_rows:
                diagnostics_lines.append("Bench Rows:")
                for row in bench_rows[:4]:
                    row_txt = str(row.get("raw", "") or "")
                    if row_txt:
                        diagnostics_lines.append(f"  {row_txt}")
            if structure_rows:
                diagnostics_lines.append("Structure Rows:")
                for row in structure_rows[:4]:
                    row_txt = str(row.get("raw", "") or "")
                    if row_txt:
                        diagnostics_lines.append(f"  {row_txt}")
            blocks.append(("Diagnostics", diagnostics_lines))
        return [(title, [line for line in list(lines or []) if str(line or "").strip()]) for title, lines in blocks if any(str(line or "").strip() for line in list(lines or []))]

    @staticmethod
    def _flatten_summary_blocks(blocks):
        lines = []
        for idx, (title, block_lines) in enumerate(list(blocks or [])):
            if idx > 0:
                lines.append("")
            lines.append(f"{title}:")
            for line in list(block_lines or []):
                lines.append(f"  {line}")
        return lines

    def _draw_dimension_rows(self, rows):
        if not rows:
            return
        for row in rows:
            color = QtGui.QColor(str(row.get("color", "") or self._svg_dimension_color(str(row.get("role", "") or ""))))
            pen = QtGui.QPen(color)
            pen.setWidthF(0.0)
            tick_pen = QtGui.QPen(color)
            tick_pen.setWidthF(0.0)
            x0 = float(row.get("x0", 0.0) or 0.0)
            x1 = float(row.get("x1", 0.0) or 0.0)
            y = float(row.get("y", 0.0) or 0.0)
            self.scene.addLine(x0, -y, x1, -y, pen)
            self.scene.addLine(x0, -(y - 0.25), x0, -(y + 0.25), tick_pen)
            self.scene.addLine(x1, -(y - 0.25), x1, -(y + 0.25), tick_pen)
            mid = 0.5 * (x0 + x1)
            label_y = y + 0.16
            vertical_anchor = "bottom"
            if str(row.get("role", "") or "") == "overall_width":
                label_y = y - 0.08
                vertical_anchor = "top"
            self._add_scene_label(
                str(row.get("text", row.get("label", "")) or ""),
                mid,
                label_y,
                color,
                anchor="center",
                point_size=float(row.get("viewer_point_size", 2.9) or 2.9),
                vertical_anchor=vertical_anchor,
            )

    def _draw_component_marker_rows(self, rows):
        if not rows:
            return
        for row in rows:
            color = QtGui.QColor(str(row.get("color", "") or "#d8d8d8"))
            pen = QtGui.QPen(color)
            pen.setCosmetic(True)
            pen.setWidthF(max(1.0, 7.0 * float(row.get("stroke_width", 0.14) or 0.14)))
            pen.setStyle(QtCore.Qt.SolidLine)
            x0 = float(row.get("x0", 0.0) or 0.0)
            x1 = float(row.get("x1", 0.0) or 0.0)
            y_base = float(row.get("y_base", 0.0) or 0.0)
            y_base_left = float(row.get("y_base_left", y_base) or y_base)
            y_base_right = float(row.get("y_base_right", y_base) or y_base)
            y_top = float(row.get("y_top", 0.0) or 0.0)
            tick_len = max(0.04, float(row.get("tick_len", 0.12) or 0.12))
            cap_mode = str(row.get("cap_mode", "both") or "both")
            marker_style = str(row.get("marker_style", "dimension_guide") or "dimension_guide")
            if marker_style == "daylight_marker":
                self.scene.addLine(x0, -y_base_left, x0, -y_top, pen)
                self.scene.addEllipse(
                    x0 - (0.35 * tick_len),
                    -y_base_left - (0.35 * tick_len),
                    0.70 * tick_len,
                    0.70 * tick_len,
                    pen,
                    QtGui.QBrush(color),
                )
                self.scene.addLine(x0 - (0.5 * tick_len), -y_top, x0 + (0.5 * tick_len), -y_top, pen)
                continue
            self.scene.addLine(x0, -y_base_left, x0, -y_top, pen)
            self.scene.addLine(x1, -y_base_right, x1, -y_top, pen)
            self.scene.addLine(x0, -y_top, x1, -y_top, pen)
            if cap_mode in ("both", "base"):
                self.scene.addLine(x0 - (0.5 * tick_len), -y_base_left, x0 + (0.5 * tick_len), -y_base_left, pen)
                self.scene.addLine(x1 - (0.5 * tick_len), -y_base_right, x1 + (0.5 * tick_len), -y_base_right, pen)
            if cap_mode in ("both", "top"):
                self.scene.addLine(x0 - (0.5 * tick_len), -y_top, x0 + (0.5 * tick_len), -y_top, pen)
                self.scene.addLine(x1 - (0.5 * tick_len), -y_top, x1 + (0.5 * tick_len), -y_top, pen)

    def _fit_view(self):
        if self._last_fit_rect is None:
            return
        try:
            self.view.fitInView(self._last_fit_rect, QtCore.Qt.KeepAspectRatio)
        except Exception:
            pass

    def _export_default_name(self, ext: str):
        sec = self._current_section_set()
        payload = dict(self._current_payload or {})
        station = float(payload.get("station", 0.0) or 0.0)
        sec_name = str(getattr(sec, "Name", "SectionSet") or "SectionSet")
        return f"{sec_name}_STA_{station:.3f}.{ext}"

    def _export_png(self):
        if not self._current_payload:
            QtWidgets.QMessageBox.information(None, "Cross Section Viewer", "No rendered section to export.")
            return
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Export Cross Section PNG",
            self._export_default_name("png"),
            "PNG Files (*.png)",
        )
        if not path:
            return
        if not str(path).lower().endswith(".png"):
            path = f"{path}.png"
        self._export_png_to_path(path)
        QtWidgets.QMessageBox.information(None, "Cross Section Viewer", f"PNG exported:\n{path}")

    def _export_svg(self):
        if not self._current_payload:
            QtWidgets.QMessageBox.information(None, "Cross Section Viewer", "No rendered section to export.")
            return
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Export Cross Section SVG",
            self._export_default_name("svg"),
            "SVG Files (*.svg)",
        )
        if not path:
            return
        if not str(path).lower().endswith(".svg"):
            path = f"{path}.svg"
        self._export_svg_to_path(path)
        QtWidgets.QMessageBox.information(None, "Cross Section Viewer", f"SVG exported:\n{path}")

    def _export_sheet_svg(self):
        if not self._current_payload:
            QtWidgets.QMessageBox.information(None, "Cross Section Viewer", "No rendered section to export.")
            return
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Export Cross Section Sheet SVG",
            self._export_default_name("sheet.svg"),
            "SVG Files (*.svg)",
        )
        if not path:
            return
        if not str(path).lower().endswith(".svg"):
            path = f"{path}.svg"
        self._export_sheet_svg_to_path(path)
        QtWidgets.QMessageBox.information(None, "Cross Section Viewer", f"Sheet SVG exported:\n{path}")

    def _export_png_to_path(self, path: str):
        rect = self._last_fit_rect if self._last_fit_rect is not None else self.scene.sceneRect()
        width = max(900, int(rect.width() * 40.0))
        height = max(520, int(rect.height() * 40.0))
        image = QtGui.QImage(width, height, QtGui.QImage.Format_ARGB32)
        image.fill(QtGui.QColor(26, 31, 44))
        painter = QtGui.QPainter(image)
        painter.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.TextAntialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )
        self.scene.render(painter, QtCore.QRectF(0.0, 0.0, float(width), float(height)), rect)
        painter.end()
        if not image.save(str(path)):
            raise Exception(f"Failed to save PNG: {path}")

    @staticmethod
    def _svg_escape(text):
        raw = str(text or "")
        return (
            raw.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    @staticmethod
    def build_svg_markup(
        payload,
        show_structures: bool = True,
        show_labels: bool = True,
        show_dimensions: bool = True,
        show_typical: bool = True,
        show_side_slope: bool = True,
        show_daylight: bool = True,
    ):
        payload = dict(payload or {})
        payload.update(CrossSectionViewerTaskPanel.build_layout_plan(payload))
        payload = CrossSectionViewerTaskPanel._filter_layout_by_scope(
            payload,
            show_typical=show_typical,
            show_side_slope=show_side_slope,
            show_daylight=show_daylight,
        )
        bounds = dict(payload.get("bounds", {}) or {})
        xmin = float(bounds.get("xmin", -1.0))
        xmax = float(bounds.get("xmax", 1.0))
        ymin = float(bounds.get("ymin", -1.0))
        ymax = float(bounds.get("ymax", 1.0))
        if abs(xmax - xmin) <= 1e-9:
            xmin -= 1.0
            xmax += 1.0
        if abs(ymax - ymin) <= 1e-9:
            ymin -= 1.0
            ymax += 1.0
        dx = max(1.0, abs(xmax - xmin))
        dy = max(1.0, abs(ymax - ymin))
        margin_x = 0.10 * dx
        margin_y = 0.14 * dy
        view_x = xmin - margin_x
        view_y = -(ymax + margin_y)
        view_w = (xmax - xmin) + (2.0 * margin_x)
        view_h = (ymax - ymin) + (2.0 * margin_y)

        def _pts(poly):
            return " ".join(f"{float(x):.3f},{-float(y):.3f}" for x, y in list(poly or []))

        lines = [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            f"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"{view_x:.3f} {view_y:.3f} {view_w:.3f} {view_h:.3f}\">",
            f"<rect x=\"{view_x:.3f}\" y=\"{view_y:.3f}\" width=\"{view_w:.3f}\" height=\"{view_h:.3f}\" fill=\"#1a1f2c\"/>",
            f"<line x1=\"0.000\" y1=\"{- (ymax + margin_y):.3f}\" x2=\"0.000\" y2=\"{- (ymin - margin_y):.3f}\" stroke=\"#6e82aa\" stroke-dasharray=\"0.4,0.4\" stroke-width=\"0.03\"/>",
        ]
        for poly in list(payload.get("section_polylines", []) or []):
            lines.append(f"<polyline fill=\"none\" stroke=\"#e6e6e6\" stroke-width=\"0.028\" points=\"{_pts(poly)}\"/>")
        if bool(show_structures):
            for poly in list(payload.get("overlay_polylines", []) or []):
                lines.append(f"<polyline fill=\"none\" stroke=\"#e8603c\" stroke-width=\"0.022\" points=\"{_pts(poly)}\"/>")
        for row in list(payload.get("planned_component_marker_rows", []) or []):
            x0 = float(row.get("x0", 0.0) or 0.0)
            x1 = float(row.get("x1", 0.0) or 0.0)
            y0 = -float(row.get("y_base", 0.0) or 0.0)
            y0_left = -float(row.get("y_base_left", row.get("y_base", 0.0)) or row.get("y_base", 0.0) or 0.0)
            y0_right = -float(row.get("y_base_right", row.get("y_base", 0.0)) or row.get("y_base", 0.0) or 0.0)
            y1 = -float(row.get("y_top", 0.0) or 0.0)
            color = str(row.get("color", "") or "#d8d8d8")
            tick = max(0.04, float(row.get("tick_len", 0.12) or 0.12))
            stroke_w = max(0.02, float(row.get("stroke_width", 0.03) or 0.03))
            cap_mode = str(row.get("cap_mode", "both") or "both")
            marker_style = str(row.get("marker_style", "dimension_guide") or "dimension_guide")
            if marker_style == "daylight_marker":
                lines.append(f"<line x1=\"{x0:.3f}\" y1=\"{y0_left:.3f}\" x2=\"{x0:.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
                lines.append(f"<circle cx=\"{x0:.3f}\" cy=\"{y0_left:.3f}\" r=\"{(0.35 * tick):.3f}\" fill=\"{color}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
                lines.append(f"<line x1=\"{(x0 - (0.5 * tick)):.3f}\" y1=\"{y1:.3f}\" x2=\"{(x0 + (0.5 * tick)):.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
                continue
            lines.append(f"<line x1=\"{x0:.3f}\" y1=\"{y0_left:.3f}\" x2=\"{x0:.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
            lines.append(f"<line x1=\"{x1:.3f}\" y1=\"{y0_right:.3f}\" x2=\"{x1:.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
            lines.append(f"<line x1=\"{x0:.3f}\" y1=\"{y1:.3f}\" x2=\"{x1:.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
            if cap_mode in ("both", "base"):
                lines.append(f"<line x1=\"{(x0 - (0.5 * tick)):.3f}\" y1=\"{y0_left:.3f}\" x2=\"{(x0 + (0.5 * tick)):.3f}\" y2=\"{y0_left:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
                lines.append(f"<line x1=\"{(x1 - (0.5 * tick)):.3f}\" y1=\"{y0_right:.3f}\" x2=\"{(x1 + (0.5 * tick)):.3f}\" y2=\"{y0_right:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
            if cap_mode in ("both", "top"):
                lines.append(f"<line x1=\"{(x0 - (0.5 * tick)):.3f}\" y1=\"{y1:.3f}\" x2=\"{(x0 + (0.5 * tick)):.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
                lines.append(f"<line x1=\"{(x1 - (0.5 * tick)):.3f}\" y1=\"{y1:.3f}\" x2=\"{(x1 + (0.5 * tick)):.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
        for row in list(payload.get("planned_title_rows", []) or []):
            title = CrossSectionViewerTaskPanel._svg_escape(str(row.get("text", "") or ""))
            tx = float(row.get('x', xmin - margin_x) or (xmin - margin_x))
            ty = -float(row.get('y', ymax + margin_y) or (ymax + margin_y))
            rot = float(row.get("rotation_deg", 0.0) or 0.0)
            transform_attr = f" transform=\"rotate({rot:.1f} {tx:.3f} {ty:.3f})\"" if abs(rot) > 1e-6 else ""
            lines.append(
                f"<text x=\"{tx:.3f}\" y=\"{ty:.3f}\" "
                f"fill=\"{row.get('color', '#c3d7ff')}\" font-size=\"{float(row.get('svg_font_size', 0.62)):.2f}\"{transform_attr}>{title}</text>"
            )
        if bool(show_dimensions):
            for row in list(payload.get("planned_dimension_rows", []) or []):
                x0 = float(row.get("x0", 0.0) or 0.0)
                x1 = float(row.get("x1", 0.0) or 0.0)
                y = -float(row.get("y", 0.0) or 0.0)
                color = str(row.get("color", "") or CrossSectionViewerTaskPanel._svg_dimension_color(str(row.get("role", "") or "")))
                lines.append(f"<line x1=\"{x0:.3f}\" y1=\"{y:.3f}\" x2=\"{x1:.3f}\" y2=\"{y:.3f}\" stroke=\"{color}\" stroke-width=\"0.03\"/>")
                lines.append(f"<line x1=\"{x0:.3f}\" y1=\"{(y-0.25):.3f}\" x2=\"{x0:.3f}\" y2=\"{(y+0.25):.3f}\" stroke=\"{color}\" stroke-width=\"0.03\"/>")
                lines.append(f"<line x1=\"{x1:.3f}\" y1=\"{(y-0.25):.3f}\" x2=\"{x1:.3f}\" y2=\"{(y+0.25):.3f}\" stroke=\"{color}\" stroke-width=\"0.03\"/>")
                label = CrossSectionViewerTaskPanel._svg_escape(str(row.get("text", row.get("label", "")) or ""))
                tx = 0.5 * (x0 + x1)
                is_overall = str(row.get("role", "") or "") == "overall_width"
                ty = y - 0.18 if not is_overall else y + 0.08
                rot = float(row.get("rotation_deg", 0.0) or 0.0)
                transform_attr = f" transform=\"rotate({rot:.1f} {tx:.3f} {ty:.3f})\"" if abs(rot) > 1e-6 else ""
                baseline_attr = " dominant-baseline=\"hanging\"" if is_overall else ""
                lines.append(f"<text x=\"{tx:.3f}\" y=\"{ty:.3f}\" fill=\"{color}\" font-size=\"{float(row.get('svg_font_size', 0.40)):.2f}\" text-anchor=\"middle\"{baseline_attr}{transform_attr}>{label}</text>")
        if bool(show_labels):
            for row in list(payload.get("planned_label_rows", []) or []):
                text = CrossSectionViewerTaskPanel._svg_escape(str(row.get("text", "") or ""))
                x = float(row.get("x", 0.0) or 0.0)
                y = -float(row.get("y", 0.0) or 0.0)
                color = str(row.get("color", "") or "#bccdeb")
                anchor = "start"
                if str(row.get("anchor", "left") or "left") == "right":
                    anchor = "end"
                elif str(row.get("anchor", "left") or "left") == "center":
                    anchor = "middle"
                rot = float(row.get("rotation_deg", 0.0) or 0.0)
                transform_attr = f" transform=\"rotate({rot:.1f} {x:.3f} {y:.3f})\"" if abs(rot) > 1e-6 else ""
                lines.append(f"<text x=\"{x:.3f}\" y=\"{y:.3f}\" fill=\"{color}\" font-size=\"{float(row.get('svg_font_size', 0.46)):.2f}\" text-anchor=\"{anchor}\"{transform_attr}>{text}</text>")
        lines.append("</svg>")
        return "\n".join(lines)

    @staticmethod
    def build_sheet_svg_markup(
        payload,
        section_set_label="SectionSet",
        show_structures: bool = True,
        show_labels: bool = True,
        show_dimensions: bool = True,
        include_diagnostics: bool = True,
        show_typical: bool = True,
        show_side_slope: bool = True,
        show_daylight: bool = True,
    ):
        payload = dict(payload or {})
        payload.update(CrossSectionViewerTaskPanel.build_layout_plan(payload))
        payload = CrossSectionViewerTaskPanel._filter_layout_by_scope(
            payload,
            show_typical=show_typical,
            show_side_slope=show_side_slope,
            show_daylight=show_daylight,
        )
        bounds = dict(payload.get("bounds", {}) or {})
        xmin = float(bounds.get("xmin", -1.0))
        xmax = float(bounds.get("xmax", 1.0))
        ymin = float(bounds.get("ymin", -1.0))
        ymax = float(bounds.get("ymax", 1.0))
        if abs(xmax - xmin) <= 1e-9:
            xmin -= 1.0
            xmax += 1.0
        if abs(ymax - ymin) <= 1e-9:
            ymin -= 1.0
            ymax += 1.0
        dx = max(1.0, abs(xmax - xmin))
        dy = max(1.0, abs(ymax - ymin))
        margin_x = 0.10 * dx
        margin_y = 0.14 * dy
        view_x = xmin - margin_x
        view_y = -(ymax + margin_y)
        view_w = (xmax - xmin) + (2.0 * margin_x)
        view_h = (ymax - ymin) + (2.0 * margin_y)

        def _pts(poly):
            return " ".join(f"{float(x):.3f},{-float(y):.3f}" for x, y in list(poly or []))

        section_label = CrossSectionViewerTaskPanel._svg_escape(str(section_set_label or "SectionSet"))
        station_label = CrossSectionViewerTaskPanel._svg_escape(str(payload.get("station_label", "STA") or "STA"))
        sheet_sec = type("SheetSectionRef", (), {"Label": section_set_label, "Name": section_set_label})()
        summary_lines = CrossSectionViewerTaskPanel._flatten_summary_blocks(
            CrossSectionViewerTaskPanel._summary_blocks(
                payload,
                sec=sheet_sec,
                include_diagnostics=include_diagnostics,
            )
        )
        summary_lines = [CrossSectionViewerTaskPanel._svg_escape(line) for line in summary_lines]

        sheet_w = 1200
        sheet_h = 780
        draw_x = 40
        draw_y = 92
        draw_w = 760
        draw_h = 550
        panel_x = 826
        panel_y = 92
        panel_w = 334
        panel_h = 550

        lines = [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{sheet_w}\" height=\"{sheet_h}\" viewBox=\"0 0 {sheet_w} {sheet_h}\">",
            f"<rect x=\"0\" y=\"0\" width=\"{sheet_w}\" height=\"{sheet_h}\" fill=\"#f4f1e8\"/>",
            f"<rect x=\"18\" y=\"18\" width=\"{sheet_w - 36}\" height=\"{sheet_h - 36}\" fill=\"none\" stroke=\"#3f4d63\" stroke-width=\"2\"/>",
            "<text x=\"40\" y=\"46\" fill=\"#223044\" font-size=\"28\" font-weight=\"600\">Cross Section Sheet</text>",
            f"<text x=\"40\" y=\"72\" fill=\"#596983\" font-size=\"15\">{section_label} | {station_label}</text>",
            f"<rect x=\"{draw_x}\" y=\"{draw_y}\" width=\"{draw_w}\" height=\"{draw_h}\" fill=\"#1a1f2c\" stroke=\"#3f4d63\" stroke-width=\"2\" rx=\"8\"/>",
            f"<svg x=\"{draw_x + 12}\" y=\"{draw_y + 12}\" width=\"{draw_w - 24}\" height=\"{draw_h - 24}\" viewBox=\"{view_x:.3f} {view_y:.3f} {view_w:.3f} {view_h:.3f}\" preserveAspectRatio=\"xMidYMid meet\">",
            f"<rect x=\"{view_x:.3f}\" y=\"{view_y:.3f}\" width=\"{view_w:.3f}\" height=\"{view_h:.3f}\" fill=\"#1a1f2c\"/>",
            f"<line x1=\"0.000\" y1=\"{- (ymax + margin_y):.3f}\" x2=\"0.000\" y2=\"{- (ymin - margin_y):.3f}\" stroke=\"#6e82aa\" stroke-dasharray=\"0.4,0.4\" stroke-width=\"0.03\"/>",
        ]
        for poly in list(payload.get("section_polylines", []) or []):
            lines.append(f"<polyline fill=\"none\" stroke=\"#e6e6e6\" stroke-width=\"0.028\" points=\"{_pts(poly)}\"/>")
        if bool(show_structures):
            for poly in list(payload.get("overlay_polylines", []) or []):
                lines.append(f"<polyline fill=\"none\" stroke=\"#e8603c\" stroke-width=\"0.022\" points=\"{_pts(poly)}\"/>")
        for row in list(payload.get("planned_component_marker_rows", []) or []):
            x0 = float(row.get("x0", 0.0) or 0.0)
            x1 = float(row.get("x1", 0.0) or 0.0)
            y0 = -float(row.get("y_base", 0.0) or 0.0)
            y0_left = -float(row.get("y_base_left", row.get("y_base", 0.0)) or row.get("y_base", 0.0) or 0.0)
            y0_right = -float(row.get("y_base_right", row.get("y_base", 0.0)) or row.get("y_base", 0.0) or 0.0)
            y1 = -float(row.get("y_top", 0.0) or 0.0)
            color = str(row.get("color", "") or "#d8d8d8")
            tick = max(0.04, float(row.get("tick_len", 0.12) or 0.12))
            stroke_w = max(0.02, float(row.get("stroke_width", 0.03) or 0.03))
            cap_mode = str(row.get("cap_mode", "both") or "both")
            marker_style = str(row.get("marker_style", "dimension_guide") or "dimension_guide")
            if marker_style == "daylight_marker":
                lines.append(f"<line x1=\"{x0:.3f}\" y1=\"{y0_left:.3f}\" x2=\"{x0:.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
                lines.append(f"<circle cx=\"{x0:.3f}\" cy=\"{y0_left:.3f}\" r=\"{(0.35 * tick):.3f}\" fill=\"{color}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
                lines.append(f"<line x1=\"{(x0 - (0.5 * tick)):.3f}\" y1=\"{y1:.3f}\" x2=\"{(x0 + (0.5 * tick)):.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
                continue
            lines.append(f"<line x1=\"{x0:.3f}\" y1=\"{y0_left:.3f}\" x2=\"{x0:.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
            lines.append(f"<line x1=\"{x1:.3f}\" y1=\"{y0_right:.3f}\" x2=\"{x1:.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
            lines.append(f"<line x1=\"{x0:.3f}\" y1=\"{y1:.3f}\" x2=\"{x1:.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
            if cap_mode in ("both", "base"):
                lines.append(f"<line x1=\"{(x0 - (0.5 * tick)):.3f}\" y1=\"{y0_left:.3f}\" x2=\"{(x0 + (0.5 * tick)):.3f}\" y2=\"{y0_left:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
                lines.append(f"<line x1=\"{(x1 - (0.5 * tick)):.3f}\" y1=\"{y0_right:.3f}\" x2=\"{(x1 + (0.5 * tick)):.3f}\" y2=\"{y0_right:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
            if cap_mode in ("both", "top"):
                lines.append(f"<line x1=\"{(x0 - (0.5 * tick)):.3f}\" y1=\"{y1:.3f}\" x2=\"{(x0 + (0.5 * tick)):.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
                lines.append(f"<line x1=\"{(x1 - (0.5 * tick)):.3f}\" y1=\"{y1:.3f}\" x2=\"{(x1 + (0.5 * tick)):.3f}\" y2=\"{y1:.3f}\" stroke=\"{color}\" stroke-width=\"{stroke_w:.3f}\"/>")
        if bool(show_dimensions):
            for row in list(payload.get("planned_dimension_rows", []) or []):
                x0 = float(row.get("x0", 0.0) or 0.0)
                x1 = float(row.get("x1", 0.0) or 0.0)
                y = -float(row.get("y", 0.0) or 0.0)
                color = str(row.get("color", "") or CrossSectionViewerTaskPanel._svg_dimension_color(str(row.get("role", "") or "")))
                label = CrossSectionViewerTaskPanel._svg_escape(str(row.get("text", row.get("label", "")) or ""))
                lines.append(f"<line x1=\"{x0:.3f}\" y1=\"{y:.3f}\" x2=\"{x1:.3f}\" y2=\"{y:.3f}\" stroke=\"{color}\" stroke-width=\"0.03\"/>")
                lines.append(f"<line x1=\"{x0:.3f}\" y1=\"{(y-0.25):.3f}\" x2=\"{x0:.3f}\" y2=\"{(y+0.25):.3f}\" stroke=\"{color}\" stroke-width=\"0.03\"/>")
                lines.append(f"<line x1=\"{x1:.3f}\" y1=\"{(y-0.25):.3f}\" x2=\"{x1:.3f}\" y2=\"{(y+0.25):.3f}\" stroke=\"{color}\" stroke-width=\"0.03\"/>")
                tx = 0.5 * (x0 + x1)
                is_overall = str(row.get("role", "") or "") == "overall_width"
                ty = y - 0.18 if not is_overall else y + 0.08
                rot = float(row.get("rotation_deg", 0.0) or 0.0)
                transform_attr = f" transform=\"rotate({rot:.1f} {tx:.3f} {ty:.3f})\"" if abs(rot) > 1e-6 else ""
                baseline_attr = " dominant-baseline=\"hanging\"" if is_overall else ""
                lines.append(f"<text x=\"{tx:.3f}\" y=\"{ty:.3f}\" fill=\"{color}\" font-size=\"{float(row.get('svg_font_size', 0.40)):.2f}\" text-anchor=\"middle\"{baseline_attr}{transform_attr}>{label}</text>")
        for row in list(payload.get("planned_title_rows", []) or []):
            title = CrossSectionViewerTaskPanel._svg_escape(str(row.get("text", "") or ""))
            tx = float(row.get('x', xmin - margin_x) or (xmin - margin_x))
            ty = -float(row.get('y', ymax + margin_y) or (ymax + margin_y))
            rot = float(row.get("rotation_deg", 0.0) or 0.0)
            transform_attr = f" transform=\"rotate({rot:.1f} {tx:.3f} {ty:.3f})\"" if abs(rot) > 1e-6 else ""
            lines.append(
                f"<text x=\"{tx:.3f}\" y=\"{ty:.3f}\" "
                f"fill=\"{row.get('color', '#c3d7ff')}\" font-size=\"{float(row.get('svg_font_size', 0.62)):.2f}\"{transform_attr}>{title}</text>"
            )
        if bool(show_labels):
            for row in list(payload.get("planned_label_rows", []) or []):
                text = CrossSectionViewerTaskPanel._svg_escape(str(row.get("text", "") or ""))
                x = float(row.get("x", 0.0) or 0.0)
                y = -float(row.get("y", 0.0) or 0.0)
                color = str(row.get("color", "") or "#bccdeb")
                anchor = "start"
                if str(row.get("anchor", "left") or "left") == "right":
                    anchor = "end"
                elif str(row.get("anchor", "left") or "left") == "center":
                    anchor = "middle"
                rot = float(row.get("rotation_deg", 0.0) or 0.0)
                transform_attr = f" transform=\"rotate({rot:.1f} {x:.3f} {y:.3f})\"" if abs(rot) > 1e-6 else ""
                lines.append(f"<text x=\"{x:.3f}\" y=\"{y:.3f}\" fill=\"{color}\" font-size=\"{float(row.get('svg_font_size', 0.46)):.2f}\" text-anchor=\"{anchor}\"{transform_attr}>{text}</text>")
        lines.extend(
            [
                "</svg>",
                f"<rect x=\"{panel_x}\" y=\"{panel_y}\" width=\"{panel_w}\" height=\"{panel_h}\" fill=\"#ffffff\" stroke=\"#3f4d63\" stroke-width=\"2\" rx=\"8\"/>",
                f"<text x=\"{panel_x + 18}\" y=\"{panel_y + 30}\" fill=\"#223044\" font-size=\"20\" font-weight=\"600\">Review Summary</text>",
            ]
        )
        for idx, line in enumerate(summary_lines):
            y = panel_y + 62 + (idx * 28)
            lines.append(f"<text x=\"{panel_x + 18}\" y=\"{y}\" fill=\"#35455f\" font-size=\"15\">{line}</text>")
        lines.extend(
            [
                "<rect x=\"40\" y=\"664\" width=\"1120\" height=\"82\" fill=\"#ffffff\" stroke=\"#3f4d63\" stroke-width=\"2\" rx=\"8\"/>",
                "<text x=\"58\" y=\"693\" fill=\"#223044\" font-size=\"18\" font-weight=\"600\">Sheet Notes</text>",
                "<text x=\"58\" y=\"721\" fill=\"#5a6a84\" font-size=\"14\">Generated from CorridorRoad Cross Section Viewer. Use this export for review sheets, markups, and scalable sharing.</text>",
                "</svg>",
            ]
        )
        return "\n".join(lines)

    def _export_svg_to_path(self, path: str):
        markup = self.build_svg_markup(
            self._current_payload,
            show_structures=bool(self.chk_show_structures.isChecked()),
            show_labels=bool(self.chk_show_labels.isChecked()),
            show_dimensions=bool(self.chk_show_dimensions.isChecked()),
            show_typical=bool(self.chk_show_typical.isChecked()),
            show_side_slope=bool(self.chk_show_side_slope.isChecked()),
            show_daylight=bool(self.chk_show_daylight.isChecked()),
        )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(markup)

    def _export_sheet_svg_to_path(self, path: str):
        sec = self._current_section_set()
        section_label = f"{getattr(sec, 'Label', 'SectionSet')} ({getattr(sec, 'Name', 'SectionSet')})" if sec is not None else "SectionSet"
        markup = self.build_sheet_svg_markup(
            self._current_payload,
            section_set_label=section_label,
            show_structures=bool(self.chk_show_structures.isChecked()),
            show_labels=bool(self.chk_show_labels.isChecked()),
            show_dimensions=bool(self.chk_show_dimensions.isChecked()),
            include_diagnostics=bool(self.chk_show_diagnostics.isChecked()),
            show_typical=bool(self.chk_show_typical.isChecked()),
            show_side_slope=bool(self.chk_show_side_slope.isChecked()),
            show_daylight=bool(self.chk_show_daylight.isChecked()),
        )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(markup)

    def _go_previous(self):
        idx = int(self.cmb_station.currentIndex())
        if idx > 0:
            self.cmb_station.setCurrentIndex(idx - 1)

    def _go_next(self):
        idx = int(self.cmb_station.currentIndex())
        if idx >= 0 and idx < (self.cmb_station.count() - 1):
            self.cmb_station.setCurrentIndex(idx + 1)

    def _use_selected_section(self):
        sec, station = _selected_section_target(self.doc)
        if sec is None:
            QtWidgets.QMessageBox.information(
                None,
                "Cross Section Viewer",
                "Select a SectionSet, SectionSlice, or SectionStructureOverlay first.",
            )
            return
        self._set_section_target(sec, station)

    def _set_section_target(self, sec, station=None):
        if sec is None:
            return
        self._loading = True
        try:
            idx = None
            for i, obj in enumerate(self._section_sets):
                if obj == sec:
                    idx = i
                    break
            if idx is None:
                self._section_sets = _find_section_sets(self.doc)
                self.cmb_section_set.clear()
                for obj in self._section_sets:
                    self.cmb_section_set.addItem(self._format_section_set(obj))
                for i, obj in enumerate(self._section_sets):
                    if obj == sec:
                        idx = i
                        break
            if idx is None:
                return
            self.cmb_section_set.setCurrentIndex(idx)
        finally:
            self._loading = False
        self._reload_station_rows(preferred_station=station)
        self._render_current_payload()

    def _sync_from_selection(self, doc_name, obj_name):
        if not bool(self.chk_sync_selection.isChecked()):
            return
        if self.doc is None:
            return
        try:
            if str(doc_name or "") not in ("", str(self.doc.Name)):
                return
            obj = self.doc.getObject(str(obj_name or ""))
        except Exception:
            obj = None
        if obj is None:
            return
        sec = None
        station = None
        try:
            if getattr(getattr(obj, "Proxy", None), "Type", "") == "SectionSet":
                sec = obj
        except Exception:
            sec = None
        if sec is None:
            try:
                sec = getattr(obj, "ParentSectionSet", None)
                station = getattr(obj, "Station", None)
            except Exception:
                sec = None
        if sec is None:
            return
        self._set_section_target(sec, station)

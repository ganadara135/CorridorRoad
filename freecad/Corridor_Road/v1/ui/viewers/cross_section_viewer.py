"""Cross section viewer for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD GUI is not available in tests.
    App = None
    Gui = None

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets
from ..common import run_legacy_command, set_ui_context


def _preview_station_label(preview: dict[str, object]) -> str:
    """Return the best available station label for one viewer payload."""

    station_row = dict(preview.get("station_row", {}) or {})
    station_label = str(station_row.get("label", "") or "").strip()
    if station_label:
        return station_label
    section_output = preview.get("section_output")
    station_value = float(getattr(section_output, "station", 0.0) or 0.0)
    return f"STA {station_value:.3f}"


def _preview_focused_component_label(preview: dict[str, object]) -> str:
    """Return a compact focused-component label for one viewer payload."""

    viewer_context = dict(preview.get("viewer_context", {}) or {})
    focused = dict(viewer_context.get("focused_component", {}) or {})
    explicit = str(focused.get("label", "") or "").strip()
    if explicit:
        return explicit
    component_type = str(focused.get("type", "") or "").strip()
    side = str(focused.get("side", "") or "").strip()
    scope = str(focused.get("scope", "") or "").strip()
    source = str(focused.get("source", "") or "").strip()
    component_id = str(focused.get("id", "") or "").strip()
    pieces = [value for value in (component_type, side, scope, source) if value and value != "-"]
    if component_id and component_id != "-":
        pieces.append(f"[{component_id}]")
    return " / ".join(pieces)


def build_handoff_target_rows(preview: dict[str, object]) -> list[list[str]]:
    """Build normalized editor-handoff rows for one section viewer payload."""

    legacy_objects = dict(preview.get("legacy_objects", {}) or {})
    inspector = dict(preview.get("source_inspector", {}) or {})
    station_label = _preview_station_label(preview)
    focused_label = _preview_focused_component_label(preview)
    focused_suffix = f" | Focus={focused_label}" if focused_label else ""

    target_specs = (
        ("Typical Section", "typical_section", inspector.get("template_label", "")),
        ("Regions", "region_plan", inspector.get("region_label", "")),
        ("Structures", "structure_set", inspector.get("structure_label", "")),
    )

    rows: list[list[str]] = []
    for target_label, object_key, owner_label in target_specs:
        obj = legacy_objects.get(object_key)
        object_label = str(
            getattr(obj, "Label", "") or getattr(obj, "Name", "") or owner_label or ""
        ).strip()
        is_ready = obj is not None or bool(object_label)
        status = "ready" if is_ready else "missing"
        context_text = f"{station_label}{focused_suffix}"
        if object_label:
            context_text = f"{context_text} | Target={object_label}"
        elif target_label == "Structures":
            fallback_section_set = legacy_objects.get("section_set")
            section_set_label = str(
                getattr(fallback_section_set, "Label", "") or getattr(fallback_section_set, "Name", "") or ""
            ).strip()
            if section_set_label:
                context_text = f"{context_text} | Via SectionSet={section_set_label}"
                status = "ready"
        rows.append(
            [
                target_label,
                status,
                object_label or "(unresolved)",
                context_text,
            ]
        )
    return rows


def build_handoff_status(preview: dict[str, object]) -> dict[str, str]:
    """Build a compact handoff status summary for the section viewer."""

    source_name = str(preview.get("source", "") or "direct_open").strip()
    rows = build_handoff_target_rows(preview)
    ready_count = sum(1 for row in rows if len(row) >= 2 and str(row[1]).strip().lower() == "ready")
    missing_labels = [str(row[0]).strip() for row in rows if len(row) >= 2 and str(row[1]).strip().lower() != "ready"]
    station_label = _preview_station_label(preview)
    if missing_labels:
        text = (
            f"Handoff Context: {station_label} | Source={source_name} | "
            f"Ready {ready_count}/{len(rows)} | Missing={', '.join(missing_labels)}"
        )
        style = "color: #b36b00;"
    else:
        text = (
            f"Handoff Context: {station_label} | Source={source_name} | "
            f"Ready {ready_count}/{len(rows)}"
        )
        style = "color: #666;"
    return {
        "text": text,
        "style": style,
    }


def build_corridor_result_review_table_rows(preview: dict[str, object]) -> list[list[str]]:
    """Build compact corridor-build result rows for section review."""

    rows = []
    for row in list(preview.get("corridor_review_rows", []) or []):
        item = dict(row or {})
        rows.append(
            [
                str(item.get("result", "") or ""),
                str(item.get("status", "") or ""),
                str(item.get("object_label", "") or item.get("object_name", "") or ""),
                str(item.get("vertex_count", "") or ""),
                str(item.get("triangle_or_point_count", "") or ""),
                str(item.get("role", "") or ""),
                str(item.get("notes", "") or ""),
            ]
        )
    return rows


def build_corridor_result_status(preview: dict[str, object]) -> dict[str, object]:
    """Summarize whether corridor build outputs are available for section review."""

    rows = [dict(row or {}) for row in list(preview.get("corridor_review_rows", []) or [])]
    if not rows:
        return {
            "state": "not_available",
            "text": "Corridor Results: not available",
            "ready_count": 0,
            "total_count": 0,
            "missing": [],
        }
    ready_count = sum(1 for row in rows if str(row.get("status", "") or "") == "ready")
    missing = [
        str(row.get("result", "") or row.get("role", "") or "").strip()
        for row in rows
        if str(row.get("status", "") or "") != "ready"
    ]
    missing = [label for label in missing if label]
    state = "ready" if ready_count == len(rows) else "partial"
    text = f"Corridor Results: {ready_count}/{len(rows)} ready"
    if missing:
        text = f"{text} | Missing={', '.join(missing)}"
    return {
        "state": state,
        "text": text,
        "ready_count": ready_count,
        "total_count": len(rows),
        "missing": missing,
    }


def corridor_result_object_name_for_row(preview: dict[str, object], row_index: int) -> str:
    """Return the document object name behind one corridor-build result row."""

    rows = [dict(row or {}) for row in list(preview.get("corridor_review_rows", []) or [])]
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Corridor result row index is out of range.")
    row = rows[int(row_index)]
    object_name = str(row.get("object_name", "") or "").strip()
    if object_name:
        return object_name
    return str(row.get("object_label", "") or "").strip()


def show_corridor_result_object_from_preview(
    preview: dict[str, object],
    row_index: int,
    *,
    document=None,
    gui_module=None,
):
    """Select and fit the 3D object referenced by one corridor result row."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document is available for corridor result focus.")
    object_name = corridor_result_object_name_for_row(preview, int(row_index))
    if not object_name:
        raise RuntimeError("Selected corridor result row has no target object.")
    obj = doc.getObject(object_name)
    if obj is None:
        raise RuntimeError(f"Corridor result object `{object_name}` was not found.")
    _select_and_fit_object(obj, gui_module=Gui if gui_module is None else gui_module)
    return obj


def section_geometry_rows(preview: dict[str, object]) -> list[object]:
    """Return drawable section geometry rows from a preview payload."""

    section_output = preview.get("section_output")
    return [
        row
        for row in list(getattr(section_output, "geometry_rows", []) or [])
        if len(list(getattr(row, "x_values", []) or [])) >= 2
        and len(list(getattr(row, "y_values", []) or [])) >= 2
    ]


def build_section_geometry_table_rows(preview: dict[str, object]) -> list[list[str]]:
    """Build compact geometry rows for the section viewer."""

    rows = []
    for row in section_geometry_rows(preview):
        x_values = [float(value) for value in list(getattr(row, "x_values", []) or [])]
        y_values = [float(value) for value in list(getattr(row, "y_values", []) or [])]
        if not x_values or not y_values:
            continue
        rows.append(
            [
                str(getattr(row, "kind", "") or ""),
                str(len(x_values)),
                f"{min(x_values):.3f} -> {max(x_values):.3f}",
                f"{min(y_values):.3f} -> {max(y_values):.3f}",
                str(getattr(row, "source_ref", "") or ""),
            ]
        )
    return rows


class _SectionGeometryPreviewWidget(QtWidgets.QWidget):
    """Tiny section polyline preview for existing-ground rows."""

    def __init__(self, rows: list[object]):
        super().__init__()
        self.rows = list(rows or [])
        self.setMinimumHeight(180)

    def paintEvent(self, event):  # noqa: N802 - Qt override name
        del event
        painter = QtGui.QPainter(self)
        try:
            rect = self.rect()
            painter.fillRect(rect, QtGui.QColor("#101821"))
            drawable_rows = self._drawable_rows()
            if not drawable_rows:
                painter.setPen(QtGui.QColor("#d6dde5"))
                painter.drawText(rect, int(QtCore.Qt.AlignCenter), "No section geometry rows.")
                return

            margin = 24
            plot = rect.adjusted(margin, margin, -margin, -margin)
            painter.setPen(QtGui.QPen(QtGui.QColor("#385064")))
            painter.drawRect(plot)

            x_values = [point[0] for row in drawable_rows for point in row["points"]]
            y_values = [point[1] for row in drawable_rows for point in row["points"]]
            x_min, x_max = min(x_values), max(x_values)
            y_min, y_max = min(y_values), max(y_values)
            if abs(x_max - x_min) < 1e-9:
                x_min -= 1.0
                x_max += 1.0
            if abs(y_max - y_min) < 1e-9:
                y_min -= 1.0
                y_max += 1.0

            axis_pen = QtGui.QPen(QtGui.QColor("#6f7f8f"))
            axis_pen.setWidth(1)
            painter.setPen(axis_pen)
            self._draw_axis_labels(painter, plot, x_min, x_max, y_min, y_max)

            for row in drawable_rows:
                pen = QtGui.QPen(QtGui.QColor(row["color"]))
                pen.setWidth(2)
                painter.setPen(pen)
                scaled_points = [
                    self._scale_point(point, plot, x_min, x_max, y_min, y_max)
                    for point in row["points"]
                ]
                for index in range(len(scaled_points) - 1):
                    painter.drawLine(scaled_points[index], scaled_points[index + 1])
        finally:
            painter.end()

    def _drawable_rows(self) -> list[dict[str, object]]:
        result = []
        for row in self.rows:
            x_values = [float(value) for value in list(getattr(row, "x_values", []) or [])]
            y_values = [float(value) for value in list(getattr(row, "y_values", []) or [])]
            count = min(len(x_values), len(y_values))
            if count < 2:
                continue
            kind = str(getattr(row, "kind", "") or "")
            color = "#55c7a5" if kind == "existing_ground_tin" else "#9fb5ff"
            result.append(
                {
                    "kind": kind,
                    "color": color,
                    "points": list(zip(x_values[:count], y_values[:count])),
                }
            )
        return result

    @staticmethod
    def _scale_point(point, plot, x_min: float, x_max: float, y_min: float, y_max: float):
        x, y = point
        px = plot.left() + ((float(x) - x_min) / (x_max - x_min)) * plot.width()
        py = plot.bottom() - ((float(y) - y_min) / (y_max - y_min)) * plot.height()
        return QtCore.QPointF(px, py)

    @staticmethod
    def _draw_axis_labels(painter, plot, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
        painter.drawText(plot.left(), plot.bottom() + 16, f"{x_min:.1f}")
        painter.drawText(plot.right() - 48, plot.bottom() + 16, f"{x_max:.1f}")
        painter.drawText(plot.left(), plot.top() - 6, f"z {y_max:.1f}")
        painter.drawText(plot.left(), plot.bottom() - 4, f"z {y_min:.1f}")


class CrossSectionViewerTaskPanel:
    """Minimal read-only v1 cross-section viewer task panel."""

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
        widget.setWindowTitle("CorridorRoad v1 - Cross Section Viewer")

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Cross Section Viewer")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self._result_state_label = QtWidgets.QLabel(self._result_state_text())
        self._result_state_label.setStyleSheet(self._result_state_style())
        layout.addWidget(self._result_state_label)

        summary = QtWidgets.QPlainTextEdit()
        summary.setReadOnly(True)
        summary.setMinimumHeight(120)
        summary.setPlainText(self._summary_text())
        layout.addWidget(summary)

        layout.addWidget(QtWidgets.QLabel("Section Geometry Preview"))
        layout.addWidget(_SectionGeometryPreviewWidget(self._section_geometry_rows()))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Points", "Offset Range", "Elevation Range", "Source"],
                rows=self._section_geometry_table_rows(),
                empty_text="No section geometry rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Components"))
        self._component_table = self._table_widget(
            headers=["Id", "Kind", "Template", "Region"],
            rows=[
                [
                    str(getattr(row, "component_id", "") or ""),
                    str(getattr(row, "kind", "") or ""),
                    str(getattr(row, "template_ref", "") or ""),
                    str(getattr(row, "region_ref", "") or ""),
                ]
                for row in list(getattr(self.preview.get("section_output"), "component_rows", []) or [])
            ],
            empty_text="No component rows.",
        )
        layout.addWidget(self._component_table)
        self._select_focused_component_row(self._component_table)

        layout.addWidget(QtWidgets.QLabel("Quantities"))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Value", "Unit", "Component"],
                rows=[
                    [
                        str(getattr(row, "quantity_kind", "") or ""),
                        str(getattr(row, "value", "") or ""),
                        str(getattr(row, "unit", "") or ""),
                        str(getattr(row, "component_ref", "") or ""),
                    ]
                    for row in list(getattr(self.preview.get("section_output"), "quantity_rows", []) or [])
                ],
                empty_text="No quantity rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Source Inspector"))
        layout.addWidget(
            self._table_widget(
                headers=["Field", "Value"],
                rows=self._source_inspector_rows(),
                empty_text="No source inspector rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Corridor Build Results"))
        self._corridor_result_table = self._table_widget(
            headers=["Result", "Status", "Object", "Vertices", "Triangles/Points", "Role", "Notes"],
            rows=self._corridor_result_review_rows(),
            empty_text="No corridor build result rows.",
        )
        layout.addWidget(self._corridor_result_table)
        self._connect_corridor_result_table(self._corridor_result_table)

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

        layout.addWidget(QtWidgets.QLabel("Terrain Review"))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Label", "Value", "Notes"],
                rows=self._terrain_review_rows(),
                empty_text="No terrain review rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Structure Review"))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Label", "Value", "Notes"],
                rows=self._structure_review_rows(),
                empty_text="No structure review rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Earthwork Hints"))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Label", "Value", "Notes"],
                rows=self._earthwork_hint_rows(),
                empty_text="No earthwork hint rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Review Markers"))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Label", "Value", "Notes"],
                rows=self._review_marker_rows(),
                empty_text="No review marker rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Diagnostics"))
        layout.addWidget(
            self._table_widget(
                headers=["Severity", "Kind", "Message", "Notes"],
                rows=self._diagnostic_review_rows(),
                empty_text="No diagnostic rows.",
            )
        )

        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        layout.addWidget(QtWidgets.QLabel("Viewer Context"))
        layout.addWidget(
            self._table_widget(
                headers=["Field", "Value"],
                rows=self._viewer_context_rows(viewer_context),
                empty_text="No viewer context rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Viewer Source Rows"))
        self._viewer_source_table = self._table_widget(
            headers=["Id", "Type", "Side", "Source", "Scope"],
            rows=[
                [
                    str(row.get("id", "") or ""),
                    str(row.get("type", "") or ""),
                    str(row.get("side", "") or ""),
                    str(row.get("source", "") or ""),
                    str(row.get("scope", "") or ""),
                ]
                for row in list(viewer_context.get("component_rows", []) or [])
            ],
            empty_text="No viewer source rows.",
        )
        layout.addWidget(self._viewer_source_table)
        self._select_focused_source_row(self._viewer_source_table)

        layout.addWidget(QtWidgets.QLabel("Editor Handoff"))
        layout.addWidget(
            self._table_widget(
                headers=["Target", "Status", "Object", "Context"],
                rows=self._handoff_target_rows(),
                empty_text="No editor handoff rows.",
            )
        )

        handoff_status = self._handoff_status()
        self._status_label = QtWidgets.QLabel(handoff_status.get("text", ""))
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(handoff_status.get("style", "color: #666;"))
        layout.addWidget(self._status_label)

        button_row = QtWidgets.QHBoxLayout()
        for label, command_name in (
            ("Open Typical Section", "CorridorRoad_EditTypicalSection"),
            ("Open Regions", "CorridorRoad_EditRegions"),
            ("Open Structures", "CorridorRoad_EditStructures"),
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
        applied_section = self.preview.get("applied_section")
        section_output = self.preview.get("section_output")
        station_row = dict(self.preview.get("station_row", {}) or {})
        station_value = float(getattr(section_output, "station", 0.0) or 0.0)
        station_label = str(station_row.get("label", f"STA {station_value:.3f}") or f"STA {station_value:.3f}")

        return "\n".join(
            [
                f"Station: {station_value}",
                f"Station Label: {station_label}",
                f"Result State: {self._result_state_value()}",
                f"Region: {getattr(applied_section, 'region_id', '') or '(none)'}",
                f"Template: {getattr(applied_section, 'template_id', '') or '(unresolved)'}",
                f"Key Stations: {len(self._key_station_rows())}",
                f"Components: {len(list(getattr(section_output, 'component_rows', []) or []))}",
                f"Quantities: {len(list(getattr(section_output, 'quantity_rows', []) or []))}",
                f"Geometry Rows: {len(self._section_geometry_rows())}",
                str(self._corridor_result_status().get("text", "")),
                f"Earthwork Hints: {len(self._earthwork_hint_rows())}",
                f"Review Markers: {len(self._review_marker_rows())}",
                f"Handoff Ready: {self._handoff_ready_count()}/{len(self._handoff_target_rows())}",
                *self._viewer_context_summary_lines(),
            ]
        )

    def _viewer_context_summary_lines(self) -> list[str]:
        viewer_context = dict(self.preview.get("viewer_context", {}) or {})
        lines = []
        focused_label = self._focused_component_label()
        if focused_label:
            lines.append(f"Focus Component: {focused_label}")
        if viewer_context.get("tag_summary"):
            lines.append(f"Station Tags: {viewer_context.get('tag_summary', '')}")
        if viewer_context.get("top_profile_edge_summary"):
            lines.append(f"Top Edges: {viewer_context.get('top_profile_edge_summary', '')}")
        if viewer_context.get("structure_summary"):
            lines.append(f"Structure Summary: {viewer_context.get('structure_summary', '')}")
        diagnostics = list(viewer_context.get("diagnostic_tokens", []) or [])
        if diagnostics:
            lines.append(f"Diagnostics: {', '.join(str(token) for token in diagnostics)}")
        return lines

    def _result_state(self) -> dict[str, object]:
        return dict(self.preview.get("result_state", {}) or {})

    def _result_state_value(self) -> str:
        return str(self._result_state().get("state", "unknown") or "unknown").strip()

    def _result_state_text(self) -> str:
        result_state = self._result_state()
        state_value = self._result_state_value()
        reason = str(result_state.get("reason", "") or "").strip()
        if reason:
            return f"Result State: {state_value} | {reason}"
        return f"Result State: {state_value}"

    def _result_state_style(self) -> str:
        state_value = self._result_state_value().lower()
        if state_value == "current":
            return "color: #1b7f3a; font-weight: bold;"
        if state_value in ("stale", "rebuild_needed"):
            return "color: #b36b00; font-weight: bold;"
        if state_value in ("error", "blocked"):
            return "color: #b33; font-weight: bold;"
        return "color: #666; font-weight: bold;"

    def _source_inspector_rows(self) -> list[list[str]]:
        inspector = dict(self.preview.get("source_inspector", {}) or {})
        mapping = [
            ("Station", "station_label"),
            ("Section Set", "section_set_label"),
            ("Template Label", "template_label"),
            ("Region Label", "region_label"),
            ("Structure Label", "structure_label"),
            ("Component Id", "component_id"),
            ("Component Kind", "component_kind"),
            ("Component Side", "component_side"),
            ("Owner Template", "owner_template"),
            ("Owner Region", "owner_region"),
            ("Owner Structure", "owner_structure"),
            ("Ownership Status", "ownership_status"),
        ]
        rows = []
        for label, key in mapping:
            value = str(inspector.get(key, "") or "").strip()
            if value:
                rows.append([label, value])
        unresolved_fields = list(inspector.get("unresolved_fields", []) or [])
        if unresolved_fields:
            rows.append(["Unresolved Fields", ", ".join(str(value) for value in unresolved_fields if str(value).strip())])
        for label, key in (("Component Count", "component_count"), ("Quantity Count", "quantity_count")):
            value = inspector.get(key, None)
            if value not in (None, ""):
                rows.append([label, str(value)])
        return rows

    def _corridor_result_review_rows(self) -> list[list[str]]:
        return build_corridor_result_review_table_rows(self.preview)

    def _corridor_result_status(self) -> dict[str, object]:
        return build_corridor_result_status(self.preview)

    def _connect_corridor_result_table(self, table) -> None:
        if not hasattr(table, "cellDoubleClicked"):
            return
        try:
            table.cellDoubleClicked.connect(lambda row_index, _column: self._show_corridor_result_row(row_index))
        except Exception:
            pass

    def _show_corridor_result_row(self, row_index: int) -> None:
        try:
            obj = show_corridor_result_object_from_preview(self.preview, int(row_index))
            label = str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "")
            self._set_status_safely(f"Focused corridor result: {label}", ok=True)
        except Exception as exc:
            self._set_status_safely(f"Corridor result was not shown: {exc}", ok=False)

    def _terrain_review_rows(self) -> list[list[str]]:
        return [
            [
                str(row.get("kind", "") or ""),
                str(row.get("label", "") or ""),
                str(row.get("value", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for row in list(self.preview.get("terrain_rows", []) or [])
        ]

    def _section_geometry_rows(self) -> list[object]:
        return section_geometry_rows(self.preview)

    def _section_geometry_table_rows(self) -> list[list[str]]:
        return build_section_geometry_table_rows(self.preview)

    def _structure_review_rows(self) -> list[list[str]]:
        return [
            [
                str(row.get("kind", "") or ""),
                str(row.get("label", "") or ""),
                str(row.get("value", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for row in list(self.preview.get("structure_rows", []) or [])
        ]

    def _diagnostic_review_rows(self) -> list[list[str]]:
        return [
            [
                str(row.get("severity", "") or ""),
                str(row.get("kind", "") or ""),
                str(row.get("message", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for row in list(self.preview.get("diagnostic_rows", []) or [])
        ]

    def _earthwork_hint_rows(self) -> list[list[str]]:
        return [
            [
                str(row.get("kind", "") or ""),
                str(row.get("label", "") or ""),
                str(row.get("value", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for row in list(self.preview.get("earthwork_hint_rows", []) or [])
        ]

    def _review_marker_rows(self) -> list[list[str]]:
        return [
            [
                str(row.get("kind", "") or ""),
                str(row.get("label", "") or ""),
                str(row.get("value", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for row in list(self.preview.get("review_marker_rows", []) or [])
        ]

    def _viewer_context_rows(self, viewer_context: dict[str, object]) -> list[list[str]]:
        rows = []
        mapping = [
            ("Section Set", "section_set_label"),
            ("Station", "station_label"),
            ("Focus Component", ""),
            ("Station Tags", "tag_summary"),
            ("Earthwork Window", "earthwork_window_summary"),
            ("Earthwork Cut/Fill", "earthwork_cut_fill_summary"),
            ("Haul Zone", "haul_zone_summary"),
            ("Top Edges", "top_profile_edge_summary"),
            ("Structure Summary", "structure_summary"),
        ]
        for label, key in mapping:
            if label == "Focus Component":
                value = self._focused_component_label()
            else:
                value = str(viewer_context.get(key, "") or "").strip()
            if value:
                rows.append([label, value])
        diagnostics = [str(token) for token in list(viewer_context.get("diagnostic_tokens", []) or []) if str(token or "").strip()]
        if diagnostics:
            rows.append(["Diagnostics", ", ".join(diagnostics)])
        for index, value in enumerate(list(viewer_context.get("structure_rows", []) or [])[:4], start=1):
            text = str(value or "").strip()
            if text:
                rows.append([f"Structure Row {index}", text])
        return rows

    def _handoff_target_rows(self) -> list[list[str]]:
        return build_handoff_target_rows(self.preview)

    def _handoff_ready_count(self) -> int:
        return sum(
            1
            for row in self._handoff_target_rows()
            if len(row) >= 2 and str(row[1] or "").strip().lower() == "ready"
        )

    def _handoff_status(self) -> dict[str, str]:
        return build_handoff_status(self.preview)

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
        section_set = legacy_objects.get("section_set")
        section_set_name = str(getattr(section_set, "Name", "") or "").strip()
        station_value = float(row.get("station", 0.0) or 0.0)
        station_label = str(row.get("label", "") or "").strip()
        context_payload = {
            "source": "v1_cross_section_navigation",
            "preferred_section_set_name": section_set_name,
            "preferred_station": station_value,
            "station_row": dict(row),
            "viewer_context": dict(self.preview.get("viewer_context", {}) or {}),
        }
        set_ui_context(**context_payload)
        self._set_status_safely(f"Opening {station_label or station_value} in v1 viewer.", ok=True)
        try:
            Gui.Control.closeDialog()
        except Exception:
            pass
        Gui.runCommand("CorridorRoad_V1ViewSections", 0)

    def _focused_component(self) -> dict[str, object]:
        return dict(dict(self.preview.get("viewer_context", {}) or {}).get("focused_component", {}) or {})

    def _focused_component_label(self) -> str:
        return _preview_focused_component_label(self.preview)

    def _focused_component_id(self) -> str:
        focused = self._focused_component()
        return str(focused.get("id", "") or "").strip()

    def _select_focused_component_row(self, table) -> None:
        focused_id = self._focused_component_id()
        if not focused_id or not hasattr(table, "rowCount"):
            return
        for row_index in range(int(table.rowCount())):
            item = table.item(row_index, 0)
            if item is None:
                continue
            if str(item.text() or "").strip() == focused_id:
                table.selectRow(row_index)
                table.scrollToItem(item)
                return

    def _select_focused_source_row(self, table) -> None:
        focused = self._focused_component()
        focused_key = str(focused.get("key", "") or "").strip()
        focused_id = str(focused.get("id", "") or "").strip()
        focused_type = str(focused.get("type", "") or "").strip()
        focused_side = str(focused.get("side", "") or "").strip()
        if not (focused_key or focused_id or focused_type):
            return
        source_rows = list(dict(self.preview.get("viewer_context", {}) or {}).get("component_rows", []) or [])
        for row_index, row in enumerate(source_rows):
            row_key = str(row.get("key", "") or "").strip()
            row_id = str(row.get("id", "") or "").strip()
            row_type = str(row.get("type", "") or "").strip()
            row_side = str(row.get("side", "") or "").strip()
            if focused_key and row_key and row_key == focused_key:
                table.selectRow(row_index)
                return
            if focused_id and row_id == focused_id and (not focused_side or row_side == focused_side):
                table.selectRow(row_index)
                return
            if focused_type and row_type == focused_type and (not focused_side or row_side == focused_side):
                table.selectRow(row_index)
                return

    def _open_legacy_command(self, command_name: str) -> None:
        legacy_objects = dict(self.preview.get("legacy_objects", {}) or {})
        objects_to_select = []
        if command_name == "CorridorRoad_EditTypicalSection":
            objects_to_select = [legacy_objects.get("typical_section")]
        elif command_name == "CorridorRoad_EditRegions":
            objects_to_select = [legacy_objects.get("region_plan")]
        elif command_name == "CorridorRoad_EditStructures":
            objects_to_select = [legacy_objects.get("section_set")]
        self._set_status_safely(f"Opening `{command_name}`.", ok=True)
        success, message = run_legacy_command(
            command_name,
            gui_module=Gui,
            objects_to_select=[obj for obj in objects_to_select if obj is not None],
            context_payload={
                "source": "v1_cross_section_viewer",
                "station_row": dict(self.preview.get("station_row", {}) or {}),
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
        table.setMinimumHeight(140)
        return table


def _select_and_fit_object(obj, *, gui_module=None) -> None:
    gui = Gui if gui_module is None else gui_module
    if gui is None or obj is None:
        return
    try:
        if hasattr(gui, "updateGui"):
            gui.updateGui()
    except Exception:
        pass
    try:
        gui.Selection.clearSelection()
        gui.Selection.addSelection(obj)
    except Exception:
        pass
    try:
        view = gui.ActiveDocument.ActiveView
        if hasattr(view, "fitSelection"):
            view.fitSelection()
        else:
            gui.SendMsgToActiveView("ViewSelection")
    except Exception:
        try:
            gui.SendMsgToActiveView("ViewSelection")
        except Exception:
            try:
                gui.SendMsgToActiveView("ViewFit")
            except Exception:
                pass


CrossSectionPreviewTaskPanel = CrossSectionViewerTaskPanel

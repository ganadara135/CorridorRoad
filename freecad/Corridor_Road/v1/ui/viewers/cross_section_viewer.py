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


def cross_section_drawing_payload(preview: dict[str, object]):
    """Return the normalized drawing payload when one is available."""

    payload = preview.get("drawing_payload")
    if payload is None:
        return None
    return payload


def cross_section_drawing_geometry_rows(preview: dict[str, object]) -> list[object]:
    """Return drawable v1 cross-section drawing geometry rows."""

    payload = cross_section_drawing_payload(preview)
    return [
        row
        for row in list(getattr(payload, "geometry_rows", []) or [])
        if len(list(getattr(row, "offset_values", []) or [])) >= 2
        and len(list(getattr(row, "elevation_values", []) or [])) >= 2
    ]


def build_cross_section_drawing_geometry_table_rows(preview: dict[str, object]) -> list[list[str]]:
    """Build compact table rows for drawing geometry."""

    rows = []
    for row in cross_section_drawing_geometry_rows(preview):
        offsets = [float(value) for value in list(getattr(row, "offset_values", []) or [])]
        elevations = [float(value) for value in list(getattr(row, "elevation_values", []) or [])]
        if not offsets or not elevations:
            continue
        rows.append(
            [
                str(getattr(row, "kind", "") or ""),
                str(getattr(row, "style_role", "") or ""),
                str(len(offsets)),
                f"{min(offsets):.3f} -> {max(offsets):.3f}",
                f"{min(elevations):.3f} -> {max(elevations):.3f}",
                str(getattr(row, "source_ref", "") or ""),
            ]
        )
    return rows


def build_cross_section_drawing_label_table_rows(preview: dict[str, object]) -> list[list[str]]:
    """Build compact table rows for drawing labels."""

    payload = cross_section_drawing_payload(preview)
    rows = []
    for row in list(getattr(payload, "label_rows", []) or []):
        rows.append(
            [
                str(getattr(row, "text", "") or ""),
                str(getattr(row, "role", "") or ""),
                f"{float(getattr(row, 'offset', 0.0) or 0.0):.3f}",
                f"{float(getattr(row, 'elevation', 0.0) or 0.0):.3f}",
                str(getattr(row, "value", "") or ""),
            ]
        )
    return rows


def build_cross_section_drawing_dimension_table_rows(preview: dict[str, object]) -> list[list[str]]:
    """Build compact table rows for drawing dimensions."""

    payload = cross_section_drawing_payload(preview)
    rows = []
    for row in list(getattr(payload, "dimension_rows", []) or []):
        unit = str(getattr(row, "unit", "") or "")
        value = float(getattr(row, "value", 0.0) or 0.0)
        rows.append(
            [
                str(getattr(row, "kind", "") or ""),
                str(getattr(row, "label", "") or ""),
                f"{float(getattr(row, 'start_offset', 0.0) or 0.0):.3f}",
                f"{float(getattr(row, 'end_offset', 0.0) or 0.0):.3f}",
                f"{value:.3f} {unit}".strip(),
            ]
        )
    return rows


def build_source_inspector_owner_rows(preview: dict[str, object]) -> list[list[str]]:
    """Build explicit source ownership rows for the section viewer."""

    inspector = dict(preview.get("source_inspector", {}) or {})
    specs = [
        (
            "Section Set",
            "section_set_status",
            "section_set_label",
            "",
            "Section station/result container used by this viewer.",
        ),
        (
            "Template",
            "template_status",
            "template_label",
            "template_source_ref",
            "Assembly template source for the focused section.",
        ),
        (
            "Region",
            "region_status",
            "region_label",
            "region_source_ref",
            "Station range policy that selected the section behavior.",
        ),
        (
            "Structure",
            "structure_status",
            "structure_label",
            "owner_structure",
            "Structure context applied to this section, if any.",
        ),
    ]
    rows = []
    for owner, status_key, label_key, ref_key, notes in specs:
        status = str(inspector.get(status_key, "") or "").strip()
        label = str(inspector.get(label_key, "") or "").strip()
        source_ref = str(inspector.get(ref_key, "") or "").strip() if ref_key else ""
        if not status:
            status = "resolved" if label else "source_ref" if source_ref else "unresolved"
        rows.append(
            [
                owner,
                status,
                label or "(unresolved)",
                source_ref or "-",
                _source_owner_note(status, notes),
            ]
        )
    return rows


def build_source_inspector_detail_rows(preview: dict[str, object]) -> list[list[str]]:
    """Build detailed selected-component source inspector rows."""

    inspector = dict(preview.get("source_inspector", {}) or {})
    mapping = [
        ("Station", "station_label"),
        ("Component Id", "component_id"),
        ("Component Kind", "component_kind"),
        ("Component Side", "component_side"),
        ("Owner Template Ref", "owner_template"),
        ("Owner Region Ref", "owner_region"),
        ("Owner Structure Ref", "owner_structure"),
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


def _source_owner_note(status: str, fallback: str) -> str:
    value = str(status or "").strip().lower()
    if value == "resolved":
        return "Object resolved. " + fallback
    if value == "source_ref":
        return "Source reference exists, but the editor object was not resolved."
    return "Missing source owner. Review build inputs before editing."


def plan_cross_section_text_layout(
    candidates: list[dict[str, object]],
    *,
    min_gap: float = 4.0,
    vertical_step: float = 12.0,
    bounds: tuple[float, float, float, float] | None = None,
    max_lanes: int = 8,
) -> list[dict[str, object]]:
    """Place text candidates while avoiding simple screen-space overlaps."""

    placed: list[dict[str, object]] = []
    ordered = sorted(
        [dict(row or {}) for row in list(candidates or [])],
        key=lambda row: (float(row.get("priority", 0.0) or 0.0), float(row.get("x", 0.0) or 0.0)),
    )
    lane_offsets = _text_layout_lane_offsets(vertical_step=vertical_step, max_lanes=max_lanes)
    for candidate in ordered:
        base_x = float(candidate.get("x", 0.0) or 0.0)
        base_y = float(candidate.get("y", 0.0) or 0.0)
        width = max(1.0, float(candidate.get("width", 1.0) or 1.0))
        height = max(1.0, float(candidate.get("height", 1.0) or 1.0))
        preferred_direction = -1.0 if float(candidate.get("preferred_direction", -1.0) or -1.0) < 0.0 else 1.0
        best_row = None
        best_lane = 0
        for lane_index, lane_offset in enumerate(lane_offsets):
            proposed = dict(candidate)
            proposed["x"] = base_x
            proposed["y"] = base_y + (lane_offset * preferred_direction)
            proposed["width"] = width
            proposed["height"] = height
            proposed = _clamp_text_layout_row(proposed, bounds)
            rect = _text_layout_rect(proposed, min_gap=min_gap)
            if not any(_rects_overlap(rect, _text_layout_rect(row, min_gap=min_gap)) for row in placed):
                best_row = proposed
                best_lane = lane_index
                break
            best_row = proposed
            best_lane = lane_index
        best_row = dict(best_row or candidate)
        best_row["lane"] = best_lane
        placed.append(best_row)
    placed.sort(key=lambda row: int(row.get("order", 0) or 0))
    return placed


def _text_layout_lane_offsets(*, vertical_step: float, max_lanes: int) -> list[float]:
    offsets = [0.0]
    for lane_index in range(1, max(1, int(max_lanes))):
        band = (lane_index + 1) // 2
        sign = 1.0 if lane_index % 2 else -1.0
        offsets.append(sign * float(band) * float(vertical_step))
    return offsets


def _clamp_text_layout_row(
    row: dict[str, object],
    bounds: tuple[float, float, float, float] | None,
) -> dict[str, object]:
    if bounds is None:
        return row
    min_x, min_y, max_x, max_y = [float(value) for value in bounds]
    width = float(row.get("width", 1.0) or 1.0)
    height = float(row.get("height", 1.0) or 1.0)
    row = dict(row)
    row["x"] = min(max(float(row.get("x", 0.0) or 0.0), min_x), max(min_x, max_x - width))
    row["y"] = min(max(float(row.get("y", 0.0) or 0.0), min_y), max(min_y, max_y - height))
    return row


def _text_layout_rect(row: dict[str, object], *, min_gap: float) -> tuple[float, float, float, float]:
    x = float(row.get("x", 0.0) or 0.0)
    y = float(row.get("y", 0.0) or 0.0)
    width = max(1.0, float(row.get("width", 1.0) or 1.0))
    height = max(1.0, float(row.get("height", 1.0) or 1.0))
    gap = max(0.0, float(min_gap or 0.0))
    return x - gap, y - gap, x + width + gap, y + height + gap


def _rects_overlap(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> bool:
    return not (
        left[2] <= right[0]
        or right[2] <= left[0]
        or left[3] <= right[1]
        or right[3] <= left[1]
    )


class _SectionGeometryPreviewWidget(QtWidgets.QWidget):
    """Drawing-style 2D section preview for v1 cross-section payloads."""

    def __init__(self, rows: list[object], *, drawing_payload=None):
        super().__init__()
        self.rows = list(rows or [])
        self.drawing_payload = drawing_payload
        self.setMinimumHeight(520)

    def paintEvent(self, event):  # noqa: N802 - Qt override name
        del event
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
            rect = self.rect()
            painter.fillRect(rect, QtGui.QColor("#101821"))
            drawable_rows = self._drawable_rows()
            if not drawable_rows:
                painter.setPen(QtGui.QColor("#d6dde5"))
                painter.drawText(rect, int(QtCore.Qt.AlignCenter), "No section geometry rows.")
                return

            plot = rect.adjusted(64, 104, -64, -142)
            painter.fillRect(plot, QtGui.QColor("#0c1923"))
            painter.setPen(QtGui.QPen(QtGui.QColor("#496577")))
            painter.drawRect(plot)
            self._draw_station_title(painter, rect)

            x_values = [point[0] for row in drawable_rows for point in row["points"]]
            y_values = [point[1] for row in drawable_rows for point in row["points"]]
            x_values.extend(self._label_offsets())
            y_values.extend(self._label_elevations())
            x_values.extend(self._dimension_offsets())
            y_values.extend(self._dimension_elevations())
            x_min, x_max = min(x_values), max(x_values)
            y_min, y_max = min(y_values), max(y_values)
            if abs(x_max - x_min) < 1e-9:
                x_min -= 4.0
                x_max += 4.0
            x_pad = max(0.5, (x_max - x_min) * 0.04)
            x_min -= x_pad
            x_max += x_pad
            if abs(y_max - y_min) < 1e-9:
                y_min -= max(1.0, (x_max - x_min) * 0.03)
                y_max += max(1.0, (x_max - x_min) * 0.03)
            y_pad = max(0.6, (y_max - y_min) * 0.20)
            y_min -= y_pad
            y_max += y_pad

            axis_pen = QtGui.QPen(QtGui.QColor("#6f7f8f"))
            axis_pen.setWidth(1)
            painter.setPen(axis_pen)
            self._draw_axis_labels(painter, plot, x_min, x_max, y_min, y_max)
            self._draw_centerline(painter, plot, x_min, x_max, y_min, y_max)

            for row in drawable_rows:
                pen = QtGui.QPen(QtGui.QColor(row["color"]))
                pen.setWidth(2 if str(row.get("kind", "") or "") != "subgrade" else 1)
                if str(row.get("style_role", "") or "") == "subgrade":
                    pen.setStyle(QtCore.Qt.DashLine)
                painter.setPen(pen)
                scaled_points = [
                    self._scale_point(point, plot, x_min, x_max, y_min, y_max)
                    for point in row["points"]
                ]
                for index in range(len(scaled_points) - 1):
                    painter.drawLine(scaled_points[index], scaled_points[index + 1])
                if row.get("closed") and len(scaled_points) > 2:
                    painter.drawLine(scaled_points[-1], scaled_points[0])
            self._draw_dimensions(painter, plot, x_min, x_max, y_min, y_max)
            self._draw_labels(painter, plot, x_min, x_max, y_min, y_max)
            self._draw_overall_banner(painter, rect)
        finally:
            painter.end()

    def _drawable_rows(self) -> list[dict[str, object]]:
        drawing_rows = self._drawing_geometry_rows()
        if drawing_rows:
            return drawing_rows
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

    def _drawing_geometry_rows(self) -> list[dict[str, object]]:
        rows = []
        for row in list(getattr(self.drawing_payload, "geometry_rows", []) or []):
            offsets = [float(value) for value in list(getattr(row, "offset_values", []) or [])]
            elevations = [float(value) for value in list(getattr(row, "elevation_values", []) or [])]
            count = min(len(offsets), len(elevations))
            if count < 2:
                continue
            style_role = str(getattr(row, "style_role", "") or "")
            kind = str(getattr(row, "kind", "") or "")
            rows.append(
                {
                    "kind": kind,
                    "style_role": style_role,
                    "color": self._style_color(style_role or kind),
                    "closed": bool(getattr(row, "closed", False)),
                    "points": list(zip(offsets[:count], elevations[:count])),
                }
            )
        return rows

    def _label_rows(self) -> list[object]:
        return list(getattr(self.drawing_payload, "label_rows", []) or [])

    def _dimension_rows(self) -> list[object]:
        return list(getattr(self.drawing_payload, "dimension_rows", []) or [])

    def _label_offsets(self) -> list[float]:
        return [float(getattr(row, "offset", 0.0) or 0.0) for row in self._label_rows()]

    def _label_elevations(self) -> list[float]:
        return [float(getattr(row, "elevation", 0.0) or 0.0) for row in self._label_rows()]

    def _dimension_offsets(self) -> list[float]:
        values = []
        for row in self._dimension_rows():
            values.extend(
                [
                    float(getattr(row, "start_offset", 0.0) or 0.0),
                    float(getattr(row, "end_offset", 0.0) or 0.0),
                ]
            )
        return values

    def _dimension_elevations(self) -> list[float]:
        return [float(getattr(row, "baseline_elevation", 0.0) or 0.0) for row in self._dimension_rows()]

    def _draw_centerline(
        self,
        painter,
        plot,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        if not (x_min <= 0.0 <= x_max):
            return
        top = self._scale_point((0.0, y_max), plot, x_min, x_max, y_min, y_max)
        bottom = self._scale_point((0.0, y_min), plot, x_min, x_max, y_min, y_max)
        pen = QtGui.QPen(QtGui.QColor("#d7dce2"))
        pen.setWidth(1)
        pen.setStyle(QtCore.Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(top, bottom)

    def _draw_labels(
        self,
        painter,
        plot,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        if not self._label_rows():
            return
        font = painter.font()
        font.setPointSize(max(7, font.pointSize() - 1))
        painter.setFont(font)
        metrics = QtGui.QFontMetrics(font)
        candidates = []
        for index, row in enumerate(self._label_rows()):
            offset = float(getattr(row, "offset", 0.0) or 0.0)
            elevation = float(getattr(row, "elevation", 0.0) or 0.0)
            point = self._scale_point((offset, elevation), plot, x_min, x_max, y_min, y_max)
            text = str(getattr(row, "text", "") or "")
            value = str(getattr(row, "value", "") or "")
            role = str(getattr(row, "role", "") or "")
            if role.startswith("component:"):
                component_font = QtGui.QFont(font)
                component_font.setPointSize(max(7, font.pointSize() - 1))
                painter.setFont(component_font)
                painter.setPen(QtGui.QPen(self._label_color(role)))
                self._draw_rotated_text(
                    painter,
                    point + QtCore.QPointF(-4.0, -8.0),
                    f"{text} {value}".strip(),
                    -90.0,
                )
                painter.setFont(font)
                continue
            if value:
                text = f"{text} {value}"
            if not text:
                continue
            width = float(metrics.horizontalAdvance(text)) if hasattr(metrics, "horizontalAdvance") else float(metrics.width(text))
            height = float(metrics.height())
            if offset < 0.0:
                text_x = float(point.x()) - width - 6.0
            else:
                text_x = float(point.x()) + 6.0
            candidates.append(
                {
                    "order": index,
                    "text": text,
                    "x": text_x,
                    "y": float(point.y()) - height - 4.0,
                    "width": width,
                    "height": height,
                    "priority": index,
                    "preferred_direction": -1.0,
                }
            )
        placed_rows = plan_cross_section_text_layout(
            candidates,
            min_gap=3.0,
            vertical_step=max(10.0, float(metrics.height()) + 2.0),
            bounds=(
                float(plot.left()) + 2.0,
                float(plot.top()) + 2.0,
                float(plot.right()) - 2.0,
                float(plot.bottom()) - 2.0,
            ),
        )
        for row in placed_rows:
            painter.setPen(QtGui.QPen(self._label_color(str(row.get("role", "") or ""))))
            painter.drawText(
                QtCore.QPointF(float(row.get("x", 0.0) or 0.0), float(row.get("y", 0.0) or 0.0) + float(row.get("height", 0.0) or 0.0)),
                str(row.get("text", "") or ""),
            )

    def _draw_dimensions(
        self,
        painter,
        plot,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        if not self._dimension_rows():
            return
        font = painter.font()
        font.setPointSize(max(7, font.pointSize() - 1))
        painter.setFont(font)
        metrics = QtGui.QFontMetrics(font)
        text_candidates = []
        for row in self._dimension_rows():
            start = float(getattr(row, "start_offset", 0.0) or 0.0)
            end = float(getattr(row, "end_offset", 0.0) or 0.0)
            baseline = float(getattr(row, "baseline_elevation", 0.0) or 0.0)
            kind = str(getattr(row, "kind", "") or "")
            role = str(getattr(row, "role", "") or "")
            color = self._dimension_color(kind, role)
            pen = QtGui.QPen(color)
            pen.setWidth(2 if kind == "overall_width" else 1)
            painter.setPen(pen)
            start_point = self._scale_point((start, baseline), plot, x_min, x_max, y_min, y_max)
            end_point = self._scale_point((end, baseline), plot, x_min, x_max, y_min, y_max)
            painter.drawLine(start_point, end_point)
            tick = 7.0 if kind == "overall_width" else 5.0
            painter.drawLine(start_point + QtCore.QPointF(0.0, -tick), start_point + QtCore.QPointF(0.0, tick))
            painter.drawLine(end_point + QtCore.QPointF(0.0, -tick), end_point + QtCore.QPointF(0.0, tick))
            value = float(getattr(row, "value", 0.0) or 0.0)
            unit = str(getattr(row, "unit", "") or "")
            label = str(getattr(row, "label", "") or "").strip()
            mid = self._scale_point(((start + end) * 0.5, baseline), plot, x_min, x_max, y_min, y_max)
            if kind == "component_width":
                painter.setPen(QtGui.QPen(color))
                section_y = self._section_elevation_at_offset((start + end) * 0.5)
                section_point = self._scale_point(((start + end) * 0.5, section_y), plot, x_min, x_max, y_min, y_max)
                painter.drawLine(section_point, mid)
                painter.drawLine(section_point + QtCore.QPointF(-7.0, 0.0), section_point + QtCore.QPointF(7.0, 0.0))
                self._draw_rotated_text(
                    painter,
                    QtCore.QPointF(float(mid.x()) - 4.0, min(float(section_point.y()), float(mid.y())) - 6.0),
                    f"{label} {value:.3f} {unit}".strip(),
                    -90.0,
                )
                continue
            text = f"{label}: {value:.3f} {unit}".strip(": ")
            width = float(metrics.horizontalAdvance(text)) if hasattr(metrics, "horizontalAdvance") else float(metrics.width(text))
            height = float(metrics.height())
            text_candidates.append(
                {
                    "order": len(text_candidates),
                    "text": text,
                    "x": float(mid.x()) - (0.5 * width),
                    "y": float(mid.y()) - height - 4.0,
                    "width": width,
                    "height": height,
                    "priority": len(text_candidates),
                    "preferred_direction": 1.0,
                }
            )
        placed_rows = plan_cross_section_text_layout(
            text_candidates,
            min_gap=3.0,
            vertical_step=max(10.0, float(metrics.height()) + 2.0),
            bounds=(
                float(plot.left()) + 2.0,
                float(plot.top()) + 2.0,
                float(plot.right()) - 2.0,
                float(plot.bottom()) - 2.0,
            ),
        )
        for row in placed_rows:
            painter.setPen(QtGui.QPen(QtGui.QColor("#c7b26a")))
            painter.drawText(
                QtCore.QPointF(float(row.get("x", 0.0) or 0.0), float(row.get("y", 0.0) or 0.0) + float(row.get("height", 0.0) or 0.0)),
                str(row.get("text", "") or ""),
            )

    def _draw_station_title(self, painter, rect) -> None:
        station_label = str(getattr(self.drawing_payload, "station_label", "") or "").strip()
        if not station_label:
            return
        painter.save()
        font = QtGui.QFont(painter.font())
        font.setPointSize(max(28, font.pointSize() + 24))
        font.setWeight(QtGui.QFont.Light)
        painter.setFont(font)
        painter.setPen(QtGui.QPen(QtGui.QColor("#bfd6ff")))
        painter.drawText(rect.left() + 92, rect.top() + 76, station_label)
        painter.restore()

    def _draw_overall_banner(self, painter, rect) -> None:
        overall_rows = [
            row
            for row in self._dimension_rows()
            if str(getattr(row, "kind", "") or "") == "overall_width"
        ]
        if not overall_rows:
            return
        painter.save()
        value = float(getattr(overall_rows[0], "value", 0.0) or 0.0)
        unit = str(getattr(overall_rows[0], "unit", "") or "m")
        text = f"Overall {value:.3f} {unit}".strip()
        font = QtGui.QFont(painter.font())
        font.setPointSize(max(30, font.pointSize() + 24))
        font.setWeight(QtGui.QFont.Light)
        painter.setFont(font)
        painter.setPen(QtGui.QPen(QtGui.QColor("#9be7ac")))
        metrics = QtGui.QFontMetrics(font)
        width = float(metrics.horizontalAdvance(text)) if hasattr(metrics, "horizontalAdvance") else float(metrics.width(text))
        painter.drawText(QtCore.QPointF(rect.center().x() - width * 0.5, rect.bottom() - 44.0), text)
        painter.restore()

    def _section_elevation_at_offset(self, offset: float) -> float:
        best_row = None
        for row in self._drawing_geometry_rows():
            kind = str(row.get("kind", "") or "")
            style_role = str(row.get("style_role", "") or "")
            if kind == "subgrade" or style_role == "subgrade":
                continue
            if best_row is None or kind == "fg":
                best_row = row
                if kind == "fg":
                    break
        if best_row is None:
            return 0.0
        points = list(best_row.get("points", []) or [])
        if not points:
            return 0.0
        target = float(offset)
        points = sorted([(float(x), float(y)) for x, y in points], key=lambda item: item[0])
        for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
            left = min(x0, x1)
            right = max(x0, x1)
            if target < left or target > right:
                continue
            if abs(x1 - x0) <= 1.0e-9:
                return max(y0, y1)
            ratio = (target - x0) / (x1 - x0)
            return y0 + (y1 - y0) * ratio
        return min(points, key=lambda item: abs(item[0] - target))[1]

    @staticmethod
    def _scale_point(point, plot, x_min: float, x_max: float, y_min: float, y_max: float):
        x, y = point
        px = plot.left() + ((float(x) - x_min) / (x_max - x_min)) * plot.width()
        py = plot.bottom() - ((float(y) - y_min) / (y_max - y_min)) * plot.height()
        return QtCore.QPointF(px, py)

    @staticmethod
    def _style_color(style_role: str) -> str:
        role = str(style_role or "").strip().lower()
        return {
            "finished_grade": "#f2f1e6",
            "fg": "#f2f1e6",
            "subgrade": "#a6adbb",
            "drainage": "#20c7e8",
            "ditch": "#20c7e8",
            "slope_face": "#72c85f",
            "existing_ground": "#55c7a5",
            "terrain": "#55c7a5",
            "existing_ground_tin": "#55c7a5",
        }.get(role, "#9fb5ff")

    @staticmethod
    def _dimension_color(kind: str, role: str):
        role_text = str(role or "").strip().lower()
        if str(kind or "").strip().lower() == "overall_width":
            return QtGui.QColor("#76b884")
        if "side_slope" in role_text:
            return QtGui.QColor("#c8f06d")
        if "ditch" in role_text:
            return QtGui.QColor("#72d6ee")
        return QtGui.QColor("#d7dce2")

    @staticmethod
    def _label_color(role: str):
        role_text = str(role or "").strip().lower()
        if "side_slope" in role_text:
            return QtGui.QColor("#c8f06d")
        if "ditch" in role_text or "drainage" in role_text:
            return QtGui.QColor("#72d6ee")
        if "subgrade" in role_text:
            return QtGui.QColor("#c2c8d2")
        if "finished_grade" in role_text:
            return QtGui.QColor("#f6f0d4")
        return QtGui.QColor("#f5f7fa")

    @staticmethod
    def _draw_rotated_text(painter, point, text: str, angle: float) -> None:
        if not str(text or "").strip():
            return
        painter.save()
        painter.translate(point)
        painter.rotate(float(angle))
        painter.drawText(QtCore.QPointF(0.0, 0.0), str(text or ""))
        painter.restore()

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

        self._add_station_navigation_widgets(layout)

        layout.addWidget(QtWidgets.QLabel("Section Drawing Preview"))
        self._drawing_preview_widget = _SectionGeometryPreviewWidget(
            self._section_geometry_rows(),
            drawing_payload=self._drawing_payload(),
        )
        layout.addWidget(self._drawing_preview_widget)
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Style", "Points", "Offset Range", "Elevation Range", "Source"],
                rows=self._drawing_geometry_table_rows(),
                empty_text="No drawing geometry rows.",
            )
        )
        layout.addWidget(QtWidgets.QLabel("Drawing Labels"))
        layout.addWidget(
            self._table_widget(
                headers=["Text", "Role", "Offset", "Elevation", "Value"],
                rows=self._drawing_label_table_rows(),
                empty_text="No drawing label rows.",
            )
        )
        layout.addWidget(QtWidgets.QLabel("Drawing Dimensions"))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Label", "Start", "End", "Value"],
                rows=self._drawing_dimension_table_rows(),
                empty_text="No drawing dimension rows.",
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
        self._source_inspector_status_label = QtWidgets.QLabel(self._source_inspector_status_text())
        self._source_inspector_status_label.setWordWrap(True)
        self._source_inspector_status_label.setStyleSheet(self._source_inspector_status_style())
        layout.addWidget(self._source_inspector_status_label)
        layout.addWidget(
            self._table_widget(
                headers=["Owner", "Status", "Object", "Source Ref", "Notes"],
                rows=self._source_inspector_owner_rows(),
                empty_text="No source owner rows.",
            )
        )
        layout.addWidget(
            self._table_widget(
                headers=["Field", "Value"],
                rows=self._source_inspector_detail_rows(),
                empty_text="No source inspector detail rows.",
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

    def _add_station_navigation_widgets(self, layout) -> None:
        layout.addWidget(QtWidgets.QLabel("Station Navigation"))
        self._station_combo = QtWidgets.QComboBox()
        for row in self._navigation_station_rows():
            label = str(row.get("label", "") or f"STA {float(row.get('station', 0.0) or 0.0):.3f}")
            if bool(row.get("is_current", False)):
                label = f"{label} [current]"
            self._station_combo.addItem(label, row)
        if self._station_combo.count() > 0:
            self._station_combo.setCurrentIndex(self._current_station_index())
        layout.addWidget(self._station_combo)

        station_button_row = QtWidgets.QHBoxLayout()
        prev_button = QtWidgets.QPushButton("Previous")
        prev_button.clicked.connect(lambda: self._open_adjacent_station(-1))
        station_button_row.addWidget(prev_button)
        open_station_button = QtWidgets.QPushButton("Open Station")
        open_station_button.clicked.connect(self._open_selected_station)
        station_button_row.addWidget(open_station_button)
        next_button = QtWidgets.QPushButton("Next")
        next_button.clicked.connect(lambda: self._open_adjacent_station(1))
        station_button_row.addWidget(next_button)
        fit_button = QtWidgets.QPushButton("Fit Drawing")
        fit_button.clicked.connect(self._fit_drawing_preview)
        station_button_row.addWidget(fit_button)
        station_button_row.addStretch(1)
        layout.addLayout(station_button_row)

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
                f"Stations: {len(self._navigation_station_rows())}",
                f"Components: {len(list(getattr(section_output, 'component_rows', []) or []))}",
                f"Quantities: {len(list(getattr(section_output, 'quantity_rows', []) or []))}",
                f"Geometry Rows: {len(self._section_geometry_rows())}",
                f"Drawing Geometry: {len(self._drawing_geometry_rows())}",
                f"Drawing Labels: {len(self._drawing_label_table_rows())}",
                f"Drawing Dimensions: {len(self._drawing_dimension_table_rows())}",
                f"Source Ownership: {self._source_inspector_status_value()}",
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

    def _source_inspector_status_value(self) -> str:
        inspector = dict(self.preview.get("source_inspector", {}) or {})
        return str(inspector.get("ownership_status", "unknown") or "unknown").strip()

    def _source_inspector_status_text(self) -> str:
        inspector = dict(self.preview.get("source_inspector", {}) or {})
        status = self._source_inspector_status_value()
        unresolved_fields = [
            str(value)
            for value in list(inspector.get("unresolved_fields", []) or [])
            if str(value or "").strip()
        ]
        if unresolved_fields:
            return f"Source Ownership: {status} | Unresolved: {', '.join(unresolved_fields)}"
        return f"Source Ownership: {status}"

    def _source_inspector_status_style(self) -> str:
        status = self._source_inspector_status_value().lower()
        if status == "resolved":
            return "color: #1b7f3a; font-weight: bold;"
        if status == "partial":
            return "color: #b36b00; font-weight: bold;"
        if status == "unresolved":
            return "color: #b33; font-weight: bold;"
        return "color: #666; font-weight: bold;"

    def _source_inspector_owner_rows(self) -> list[list[str]]:
        return build_source_inspector_owner_rows(self.preview)

    def _source_inspector_detail_rows(self) -> list[list[str]]:
        return build_source_inspector_detail_rows(self.preview)

    def _source_inspector_rows(self) -> list[list[str]]:
        """Return legacy source-inspector rows for older tests/helpers."""

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

    def _drawing_payload(self):
        return cross_section_drawing_payload(self.preview)

    def _drawing_geometry_rows(self) -> list[object]:
        return cross_section_drawing_geometry_rows(self.preview)

    def _drawing_geometry_table_rows(self) -> list[list[str]]:
        rows = build_cross_section_drawing_geometry_table_rows(self.preview)
        if rows:
            return rows
        return [
            [row[0], "", row[1], row[2], row[3], row[4]]
            for row in self._section_geometry_table_rows()
        ]

    def _drawing_label_table_rows(self) -> list[list[str]]:
        return build_cross_section_drawing_label_table_rows(self.preview)

    def _drawing_dimension_table_rows(self) -> list[list[str]]:
        return build_cross_section_drawing_dimension_table_rows(self.preview)

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

    def _navigation_station_rows(self) -> list[dict[str, object]]:
        rows = [dict(row or {}) for row in list(self.preview.get("station_rows", []) or [])]
        if not rows:
            station_row = dict(self.preview.get("station_row", {}) or {})
            if station_row:
                rows = [station_row]
        current_station = self._current_station_value()
        for index, row in enumerate(rows):
            row["index"] = int(row.get("index", index) or index)
            row["is_current"] = abs(float(row.get("station", 0.0) or 0.0) - current_station) <= 1.0e-6
        return rows

    def _current_station_value(self) -> float:
        station_row = dict(self.preview.get("station_row", {}) or {})
        if station_row.get("station", None) is not None:
            try:
                return float(station_row.get("station", 0.0) or 0.0)
            except Exception:
                pass
        section_output = self.preview.get("section_output")
        return float(getattr(section_output, "station", 0.0) or 0.0)

    def _current_station_index(self) -> int:
        rows = self._navigation_station_rows()
        for index, row in enumerate(rows):
            if bool(row.get("is_current", False)):
                return index
        return 0

    def _selected_station_row(self) -> dict[str, object] | None:
        combo = getattr(self, "_station_combo", None)
        if combo is None or combo.count() <= 0:
            rows = self._navigation_station_rows()
            return dict(rows[self._current_station_index()]) if rows else None
        data = combo.currentData()
        if isinstance(data, dict):
            return dict(data)
        rows = self._navigation_station_rows()
        index = max(0, min(combo.currentIndex(), len(rows) - 1))
        return dict(rows[index]) if rows else None

    def _open_selected_station(self) -> None:
        self._open_station_row(self._selected_station_row())

    def _open_adjacent_station(self, delta: int) -> None:
        rows = self._navigation_station_rows()
        if not rows:
            self._set_status_safely("No station rows are available.", ok=False)
            return
        current_index = self._current_station_index()
        target_index = max(0, min(current_index + int(delta), len(rows) - 1))
        self._open_station_row(rows[target_index])

    def _fit_drawing_preview(self) -> None:
        widget = getattr(self, "_drawing_preview_widget", None)
        if widget is not None:
            try:
                widget.update()
            except RuntimeError:
                pass
        self._set_status_safely("Drawing preview fit refreshed.", ok=True)

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

"""Map AppliedSection results into drawing-style cross-section payloads."""

from __future__ import annotations

from ...models.output.cross_section_drawing import (
    CrossSectionDrawingDimensionRow,
    CrossSectionDrawingGeometryRow,
    CrossSectionDrawingLabelRow,
    CrossSectionDrawingPayload,
    CrossSectionDrawingSummaryRow,
)
from ...models.result.applied_section import AppliedSection
from ...models.result.applied_section_set import AppliedSectionSet


_FG_COMPONENT_KINDS = {
    "lane",
    "shoulder",
    "median",
    "curb",
    "gutter",
    "sidewalk",
    "bike_lane",
    "green_strip",
}


class CrossSectionDrawingMapper:
    """Build v1 section drawing payloads from stable result models."""

    def map_applied_section_set(
        self,
        applied_section_set: AppliedSectionSet,
        *,
        station: float | None = None,
    ) -> CrossSectionDrawingPayload:
        """Return a drawing payload for the nearest AppliedSection station."""

        section = _nearest_applied_section(applied_section_set, station=station)
        if section is None:
            return CrossSectionDrawingPayload(
                schema_version=1,
                project_id=str(getattr(applied_section_set, "project_id", "") or ""),
                drawing_id=f"{getattr(applied_section_set, 'applied_section_set_id', '')}:empty-drawing",
                station=float(station or 0.0),
                station_label=f"STA {float(station or 0.0):.3f}",
                source_refs=[str(getattr(applied_section_set, "applied_section_set_id", "") or "")],
                result_refs=[],
                summary_rows=[
                    CrossSectionDrawingSummaryRow(
                        summary_id="cross-section-drawing:missing-section",
                        kind="missing_section",
                        label="Section",
                        value="No AppliedSection station was available.",
                    )
                ],
            )
        return self.map_applied_section(section)

    def map_applied_section(self, applied_section: AppliedSection) -> CrossSectionDrawingPayload:
        """Return drawing geometry, labels, and dimensions for one station."""

        station = float(getattr(applied_section, "station", 0.0) or 0.0)
        geometry_rows = _geometry_rows(applied_section)
        label_rows = _label_rows(applied_section, geometry_rows)
        dimension_rows = _dimension_rows(applied_section, geometry_rows)
        summary_rows = [
            CrossSectionDrawingSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:geometry-count",
                kind="geometry_count",
                label="Geometry Rows",
                value=len(geometry_rows),
            ),
            CrossSectionDrawingSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:label-count",
                kind="label_count",
                label="Label Rows",
                value=len(label_rows),
            ),
            CrossSectionDrawingSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:dimension-count",
                kind="dimension_count",
                label="Dimension Rows",
                value=len(dimension_rows),
            ),
        ]
        return CrossSectionDrawingPayload(
            schema_version=1,
            project_id=str(getattr(applied_section, "project_id", "") or ""),
            drawing_id=f"{applied_section.applied_section_id}:drawing",
            station=station,
            station_label=f"STA {station:.3f}",
            label=str(getattr(applied_section, "label", "") or ""),
            unit_context=applied_section.unit_context,
            coordinate_context=applied_section.coordinate_context,
            selection_scope={"scope_kind": "single_station", "station": station},
            source_refs=list(getattr(applied_section, "source_refs", []) or []),
            result_refs=[str(getattr(applied_section, "applied_section_id", "") or "")],
            geometry_rows=geometry_rows,
            label_rows=label_rows,
            dimension_rows=dimension_rows,
            summary_rows=summary_rows,
            diagnostic_rows=list(getattr(applied_section, "diagnostic_rows", []) or []),
        )


def _nearest_applied_section(applied_section_set: AppliedSectionSet, *, station: float | None):
    sections = list(getattr(applied_section_set, "sections", []) or [])
    if not sections:
        return None
    if station is None:
        return sorted(sections, key=lambda section: float(getattr(section, "station", 0.0) or 0.0))[0]
    target = float(station)
    return min(sections, key=lambda section: abs(float(getattr(section, "station", 0.0) or 0.0) - target))


def _geometry_rows(applied_section: AppliedSection) -> list[CrossSectionDrawingGeometryRow]:
    rows: list[CrossSectionDrawingGeometryRow] = []
    rows.extend(_point_role_geometry_rows(applied_section, "fg_surface", "finished_grade", "fg"))
    if not any(row.kind == "fg" for row in rows):
        component_fg_row = _component_fg_geometry_row(applied_section)
        rows.append(component_fg_row if component_fg_row is not None else _fallback_fg_geometry_row(applied_section))
    rows.extend(_point_role_geometry_rows(applied_section, "subgrade_surface", "subgrade", "subgrade"))
    if not any(row.kind == "subgrade" for row in rows):
        component_subgrade_row = _component_subgrade_geometry_row(applied_section)
        rows.append(
            component_subgrade_row
            if component_subgrade_row is not None
            else _fallback_subgrade_geometry_row(applied_section)
        )
    rows.extend(_point_role_geometry_rows(applied_section, "ditch_surface", "drainage", "ditch"))
    if not any(row.kind == "ditch" for row in rows):
        rows.extend(_component_ditch_geometry_rows(applied_section))
    component_slope_rows = _component_slope_face_rows(applied_section)
    rows.extend(component_slope_rows if component_slope_rows else _fallback_slope_face_rows(applied_section))
    return [row for row in rows if len(row.offset_values) >= 2 and len(row.elevation_values) >= 2]


def _point_role_geometry_rows(
    applied_section: AppliedSection,
    point_role: str,
    style_role: str,
    kind: str,
) -> list[CrossSectionDrawingGeometryRow]:
    points = [
        point
        for point in list(getattr(applied_section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == point_role
    ]
    if len(points) < 2:
        return []
    points = sorted(points, key=_point_offset)
    return [
        CrossSectionDrawingGeometryRow(
            row_id=f"{applied_section.applied_section_id}:{kind}",
            kind=kind,
            offset_values=[_point_offset(point) for point in points],
            elevation_values=[float(getattr(point, "z", 0.0) or 0.0) for point in points],
            style_role=style_role,
            source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
        )
    ]


def _fallback_fg_geometry_row(applied_section: AppliedSection) -> CrossSectionDrawingGeometryRow:
    left = max(0.0, float(getattr(applied_section, "surface_left_width", 0.0) or 0.0))
    right = max(0.0, float(getattr(applied_section, "surface_right_width", 0.0) or 0.0))
    z = _frame_elevation(applied_section)
    return CrossSectionDrawingGeometryRow(
        row_id=f"{applied_section.applied_section_id}:fg-fallback",
        kind="fg",
        offset_values=[-right, 0.0, left],
        elevation_values=[z, z, z],
        style_role="finished_grade",
        source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
    )


def _fallback_subgrade_geometry_row(applied_section: AppliedSection) -> CrossSectionDrawingGeometryRow:
    left = max(0.0, float(getattr(applied_section, "surface_left_width", 0.0) or 0.0))
    right = max(0.0, float(getattr(applied_section, "surface_right_width", 0.0) or 0.0))
    z = _frame_elevation(applied_section) - max(0.0, float(getattr(applied_section, "subgrade_depth", 0.0) or 0.0))
    return CrossSectionDrawingGeometryRow(
        row_id=f"{applied_section.applied_section_id}:subgrade-fallback",
        kind="subgrade",
        offset_values=[-right, left],
        elevation_values=[z, z],
        style_role="subgrade",
        source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
    )


def _component_fg_geometry_row(applied_section: AppliedSection) -> CrossSectionDrawingGeometryRow | None:
    spans = [
        span
        for span in _component_spans(applied_section)
        if str(span.get("kind", "") or "") in _FG_COMPONENT_KINDS
    ]
    if not spans:
        return None
    points: dict[float, float] = {0.0: _frame_elevation(applied_section)}
    for span in spans:
        points[float(span["start"])] = float(span["start_z"])
        points[float(span["end"])] = float(span["end_z"])
    if len(points) < 2:
        return None
    ordered = sorted(points.items(), key=lambda item: item[0])
    return CrossSectionDrawingGeometryRow(
        row_id=f"{applied_section.applied_section_id}:fg-components",
        kind="fg",
        offset_values=[offset for offset, _z in ordered],
        elevation_values=[z for _offset, z in ordered],
        style_role="finished_grade",
        source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
    )


def _component_subgrade_geometry_row(applied_section: AppliedSection) -> CrossSectionDrawingGeometryRow | None:
    fg_row = _component_fg_geometry_row(applied_section)
    if fg_row is None:
        return None
    depth = max(0.0, float(getattr(applied_section, "subgrade_depth", 0.0) or 0.0))
    return CrossSectionDrawingGeometryRow(
        row_id=f"{applied_section.applied_section_id}:subgrade-components",
        kind="subgrade",
        offset_values=list(fg_row.offset_values or []),
        elevation_values=[float(z) - depth for z in list(fg_row.elevation_values or [])],
        style_role="subgrade",
        source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
    )


def _component_ditch_geometry_rows(applied_section: AppliedSection) -> list[CrossSectionDrawingGeometryRow]:
    rows: list[CrossSectionDrawingGeometryRow] = []
    for span in _component_spans(applied_section):
        if str(span.get("kind", "") or "") != "ditch":
            continue
        start = float(span["start"])
        end = float(span["end"])
        start_z = float(span["start_z"])
        end_z = float(span["end_z"])
        mid_offset = 0.5 * (start + end)
        invert_z = min(start_z, end_z) - max(0.15, abs(end - start) * 0.08)
        rows.append(
            CrossSectionDrawingGeometryRow(
                row_id=f"{applied_section.applied_section_id}:ditch-{span['row_id']}",
                kind="ditch",
                offset_values=[start, mid_offset, end],
                elevation_values=[start_z, invert_z, end_z],
                style_role="drainage",
                source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
            )
        )
    return rows


def _component_slope_face_rows(applied_section: AppliedSection) -> list[CrossSectionDrawingGeometryRow]:
    rows: list[CrossSectionDrawingGeometryRow] = []
    for span in _component_spans(applied_section):
        if str(span.get("kind", "") or "") != "side_slope":
            continue
        rows.append(
            CrossSectionDrawingGeometryRow(
                row_id=f"{applied_section.applied_section_id}:slope-{span['row_id']}",
                kind="slope_face",
                offset_values=[float(span["start"]), float(span["end"])],
                elevation_values=[float(span["start_z"]), float(span["end_z"])],
                style_role="slope_face",
                source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
            )
        )
    return rows


def _fallback_slope_face_rows(applied_section: AppliedSection) -> list[CrossSectionDrawingGeometryRow]:
    rows: list[CrossSectionDrawingGeometryRow] = []
    left, left_z, right, right_z = _terminal_section_edges(applied_section)
    left_width = max(0.0, float(getattr(applied_section, "daylight_left_width", 0.0) or 0.0))
    right_width = max(0.0, float(getattr(applied_section, "daylight_right_width", 0.0) or 0.0))
    left_slope = float(getattr(applied_section, "daylight_left_slope", 0.0) or 0.0)
    right_slope = float(getattr(applied_section, "daylight_right_slope", 0.0) or 0.0)
    if left_width > 0.0:
        rows.append(
            CrossSectionDrawingGeometryRow(
                row_id=f"{applied_section.applied_section_id}:slope-left",
                kind="slope_face",
                offset_values=[left, left + left_width],
                elevation_values=[left_z, left_z + left_width * left_slope],
                style_role="slope_face",
                source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
            )
        )
    if right_width > 0.0:
        rows.append(
            CrossSectionDrawingGeometryRow(
                row_id=f"{applied_section.applied_section_id}:slope-right",
                kind="slope_face",
                offset_values=[-right, -right - right_width],
                elevation_values=[right_z, right_z + right_width * right_slope],
                style_role="slope_face",
                source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
            )
        )
    return rows


def _terminal_section_edges(applied_section: AppliedSection) -> tuple[float, float, float, float]:
    left = max(0.0, float(getattr(applied_section, "surface_left_width", 0.0) or 0.0))
    right = max(0.0, float(getattr(applied_section, "surface_right_width", 0.0) or 0.0))
    frame_z = _frame_elevation(applied_section)
    left_z = frame_z
    right_z = frame_z
    for point in list(getattr(applied_section, "point_rows", []) or []):
        if str(getattr(point, "point_role", "") or "") not in {"fg_surface", "ditch_surface"}:
            continue
        offset = _point_offset(point)
        z = float(getattr(point, "z", frame_z) or frame_z)
        if offset > left or (abs(offset - left) <= 1.0e-9 and z > left_z):
            left = offset
            left_z = z
        if offset < -right or (abs(offset + right) <= 1.0e-9 and z > right_z):
            right = abs(offset)
            right_z = z
    return left, left_z, right, right_z


def _label_rows(
    applied_section: AppliedSection,
    geometry_rows: list[CrossSectionDrawingGeometryRow],
) -> list[CrossSectionDrawingLabelRow]:
    rows = [
        CrossSectionDrawingLabelRow(
            row_id=f"{applied_section.applied_section_id}:label-centerline",
            text="CL",
            offset=0.0,
            elevation=_frame_elevation(applied_section),
            role="centerline",
            source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
        )
    ]
    for row in geometry_rows:
        offset, elevation = _row_midpoint(row)
        label = {
            "fg": "FG",
            "subgrade": "Subgrade",
            "ditch": _ditch_label(row),
            "slope_face": _slope_label(row),
        }.get(row.kind, row.kind)
        rows.append(
            CrossSectionDrawingLabelRow(
                row_id=f"{row.row_id}:label",
                text=label,
                offset=offset,
                elevation=elevation,
                role=row.style_role or row.kind,
                value=_row_value_text(row),
                source_ref=row.source_ref,
            )
        )
    for span in _component_spans(applied_section):
        width = abs(float(span["end"]) - float(span["start"]))
        if width <= 1.0e-9:
            continue
        rows.append(
            CrossSectionDrawingLabelRow(
                row_id=f"{applied_section.applied_section_id}:component-label-{span['row_id']}",
                text=_component_label(span),
                offset=0.5 * (float(span["start"]) + float(span["end"])),
                elevation=max(float(span["start_z"]), float(span["end_z"])),
                role=f"component:{span.get('kind', '')}",
                value=f"{width:.3f} m",
                source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
            )
        )
    return rows


def _dimension_rows(
    applied_section: AppliedSection,
    geometry_rows: list[CrossSectionDrawingGeometryRow],
) -> list[CrossSectionDrawingDimensionRow]:
    extents = [
        value
        for row in geometry_rows
        for value in list(row.offset_values or [])
    ]
    if not extents:
        return []
    min_offset = min(extents)
    max_offset = max(extents)
    baseline = min(
        elevation
        for row in geometry_rows
        for elevation in list(row.elevation_values or [])
    ) - 1.0
    rows = [
        CrossSectionDrawingDimensionRow(
            row_id=f"{applied_section.applied_section_id}:dim-total",
            kind="overall_width",
            start_offset=min_offset,
            end_offset=max_offset,
            baseline_elevation=baseline,
            label="Overall width",
            value=max_offset - min_offset,
            role="overall",
            source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
        )
    ]
    component_spans = [
        span
        for span in _component_spans(applied_section)
        if abs(float(span["end"]) - float(span["start"])) > 1.0e-9
    ]
    if component_spans:
        for span in component_spans:
            rows.append(
                CrossSectionDrawingDimensionRow(
                    row_id=f"{applied_section.applied_section_id}:dim-component-{span['row_id']}",
                    kind="component_width",
                    start_offset=float(span["start"]),
                    end_offset=float(span["end"]),
                    baseline_elevation=baseline - 0.35,
                    label=_component_label(span),
                    value=abs(float(span["end"]) - float(span["start"])),
                    role=f"component:{span.get('kind', '')}",
                    source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
                )
            )
        return rows

    left = max(0.0, float(getattr(applied_section, "surface_left_width", 0.0) or 0.0))
    right = max(0.0, float(getattr(applied_section, "surface_right_width", 0.0) or 0.0))
    if right > 0.0:
        rows.append(
            CrossSectionDrawingDimensionRow(
                row_id=f"{applied_section.applied_section_id}:dim-right-fg",
                kind="component_width",
                start_offset=-right,
                end_offset=0.0,
                baseline_elevation=baseline - 0.5,
                label="Right FG",
                value=right,
                role="finished_grade",
                source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
            )
        )
    if left > 0.0:
        rows.append(
            CrossSectionDrawingDimensionRow(
                row_id=f"{applied_section.applied_section_id}:dim-left-fg",
                kind="component_width",
                start_offset=0.0,
                end_offset=left,
                baseline_elevation=baseline - 0.5,
                label="Left FG",
                value=left,
                role="finished_grade",
                source_ref=str(getattr(applied_section, "applied_section_id", "") or ""),
            )
        )
    return rows


def _component_spans(applied_section: AppliedSection) -> list[dict[str, object]]:
    """Return section-local component spans with start/end elevations."""

    spans: list[dict[str, object]] = []
    base_z = _frame_elevation(applied_section)
    cursors = {
        "left": [0.0, base_z],
        "right": [0.0, base_z],
    }
    for index, component in enumerate(list(getattr(applied_section, "component_rows", []) or []), start=1):
        kind = str(getattr(component, "kind", "") or "").strip().lower()
        width = max(0.0, float(getattr(component, "width", 0.0) or 0.0))
        if not kind or width <= 1.0e-9:
            continue
        side = str(getattr(component, "side", "") or "center").strip().lower() or "center"
        slope = float(getattr(component, "slope", 0.0) or 0.0)
        sides = [side]
        if side == "both":
            sides = ["left", "right"]
        elif side == "center":
            half_width = width * 0.5
            center_z = base_z + slope * half_width
            spans.append(
                {
                    "row_id": f"{index}:center",
                    "component_id": str(getattr(component, "component_id", "") or ""),
                    "kind": kind,
                    "side": "center",
                    "start": -half_width,
                    "end": half_width,
                    "start_z": center_z,
                    "end_z": center_z,
                    "order": index,
                }
            )
            continue
        for side_name in sides:
            if side_name not in {"left", "right"}:
                continue
            cursor_offset, cursor_z = cursors[side_name]
            if side_name == "left":
                start = cursor_offset
                end = cursor_offset + width
            else:
                start = -cursor_offset
                end = -(cursor_offset + width)
            end_z = cursor_z + slope * width
            spans.append(
                {
                    "row_id": f"{index}:{side_name}",
                    "component_id": str(getattr(component, "component_id", "") or ""),
                    "kind": kind,
                    "side": side_name,
                    "start": start,
                    "end": end,
                    "start_z": cursor_z,
                    "end_z": end_z,
                    "order": index,
                }
            )
            cursors[side_name] = [cursor_offset + width, end_z]
    return spans


def _component_label(span: dict[str, object]) -> str:
    kind = str(span.get("kind", "") or "").strip().lower()
    side = str(span.get("side", "") or "").strip().lower()
    side_label = {"left": "L", "right": "R", "center": "C"}.get(side, "")
    label = {
        "lane": "lane",
        "shoulder": "shoulder",
        "median": "median",
        "curb": "curb",
        "gutter": "gutter",
        "sidewalk": "sidewalk",
        "bike_lane": "bike lane",
        "green_strip": "green strip",
        "ditch": "ditch",
        "side_slope": "daylight",
    }.get(kind, kind.replace("_", " ") or "component")
    return f"{label} {side_label}".strip()


def _point_offset(point) -> float:
    lateral = getattr(point, "lateral_offset", None)
    if lateral is not None:
        try:
            return float(lateral)
        except Exception:
            pass
    return float(getattr(point, "y", 0.0) or 0.0)


def _frame_elevation(applied_section: AppliedSection) -> float:
    frame = getattr(applied_section, "frame", None)
    if frame is None:
        return 0.0
    return float(getattr(frame, "z", 0.0) or 0.0)


def _row_midpoint(row: CrossSectionDrawingGeometryRow) -> tuple[float, float]:
    offsets = list(row.offset_values or [])
    elevations = list(row.elevation_values or [])
    if not offsets or not elevations:
        return 0.0, 0.0
    return sum(offsets) / len(offsets), sum(elevations) / len(elevations)


def _row_value_text(row: CrossSectionDrawingGeometryRow) -> str:
    offsets = list(row.offset_values or [])
    if len(offsets) < 2:
        return ""
    return f"{abs(max(offsets) - min(offsets)):.3f} m"


def _ditch_label(row: CrossSectionDrawingGeometryRow) -> str:
    offset, _elevation = _row_midpoint(row)
    side = "Left" if offset > 0.0 else "Right" if offset < 0.0 else "Center"
    return f"{side} ditch"


def _slope_label(row: CrossSectionDrawingGeometryRow) -> str:
    offset, _elevation = _row_midpoint(row)
    side = "Left" if offset > 0.0 else "Right" if offset < 0.0 else "Center"
    return f"{side} slope"

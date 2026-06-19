"""Alignment curve preview evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ...common.diagnostics import DiagnosticMessage
from ...models.result.alignment_curve_preview import (
    AlignmentCurvePreviewAnnotationRow,
    AlignmentCurvePreviewElementRow,
    AlignmentCurvePreviewPointRow,
    AlignmentCurvePreviewResult,
)
from ...models.source.alignment_model import AlignmentElement, AlignmentModel
from .alignment_evaluation_service import AlignmentEvaluationService


@dataclass(frozen=True)
class AlignmentCurvePreviewRequest:
    """Inputs for read-only Alignment curve preview evaluation."""

    alignment: AlignmentModel | None = None
    sample_interval: float = 5.0


class AlignmentCurvePreviewService:
    """Build preview rows for Alignment panel curve review."""

    def __init__(self, *, alignment_service: AlignmentEvaluationService | None = None) -> None:
        self.alignment_service = alignment_service or AlignmentEvaluationService()

    def evaluate(self, request: AlignmentCurvePreviewRequest) -> AlignmentCurvePreviewResult:
        alignment = request.alignment
        interval = max(float(getattr(request, "sample_interval", 5.0) or 5.0), 0.1)
        if alignment is None:
            return AlignmentCurvePreviewResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="blocked",
                diagnostic_rows=[
                    DiagnosticMessage("error", "alignment_curve_preview_missing_alignment", "AlignmentModel is required.")
                ],
            )
        elements = list(getattr(alignment, "geometry_sequence", []) or [])
        if not elements:
            return AlignmentCurvePreviewResult(
                schema_version=1,
                project_id=str(getattr(alignment, "project_id", "") or "corridorroad-v1"),
                alignment_id=str(getattr(alignment, "alignment_id", "") or ""),
                status="blocked",
                source_refs=list(getattr(alignment, "source_refs", []) or []),
                diagnostic_rows=[
                    DiagnosticMessage(
                        "error",
                        "alignment_curve_preview_missing_geometry",
                        "AlignmentModel has no geometry sequence.",
                    )
                ],
            )

        point_rows: list[AlignmentCurvePreviewPointRow] = []
        annotation_rows: list[AlignmentCurvePreviewAnnotationRow] = []
        element_rows: list[AlignmentCurvePreviewElementRow] = []
        diagnostics: list[DiagnosticMessage] = [
            DiagnosticMessage("info", "alignment_curve_preview_ok", "Alignment curve preview was evaluated.")
        ]
        for element in elements:
            element_rows.append(_element_row(element))
            element_points, element_diagnostics = self._element_point_rows(alignment, element, interval)
            point_rows.extend(element_points)
            annotation_rows.extend(_element_boundary_annotations(element, element_points))
            curve_annotations, curve_diagnostics = _curve_annotations(element)
            annotation_rows.extend(curve_annotations)
            diagnostics.extend(element_diagnostics)
            diagnostics.extend(curve_diagnostics)
        station_start = min(float(getattr(element, "station_start", 0.0) or 0.0) for element in elements)
        station_end = max(float(getattr(element, "station_end", 0.0) or 0.0) for element in elements)
        status = "ready" if point_rows else "blocked"
        return AlignmentCurvePreviewResult(
            schema_version=1,
            project_id=str(getattr(alignment, "project_id", "") or "corridorroad-v1"),
            alignment_id=str(getattr(alignment, "alignment_id", "") or ""),
            station_start=station_start,
            station_end=station_end,
            sample_interval=interval,
            status=status,
            point_rows=point_rows,
            annotation_rows=annotation_rows,
            element_rows=element_rows,
            source_refs=list(getattr(alignment, "source_refs", []) or []),
            diagnostic_rows=diagnostics,
        )

    def _element_point_rows(
        self,
        alignment: AlignmentModel,
        element: AlignmentElement,
        interval: float,
    ) -> tuple[list[AlignmentCurvePreviewPointRow], list[DiagnosticMessage]]:
        diagnostics: list[DiagnosticMessage] = []
        output: list[AlignmentCurvePreviewPointRow] = []
        element_id = str(getattr(element, "element_id", "") or "alignment-element")
        stations = _station_range(float(element.station_start), float(element.station_end), interval)
        for index, station in enumerate(stations, start=1):
            result = self.alignment_service.evaluate_station(alignment, station)
            if str(getattr(result, "status", "") or "") != "ok":
                continue
            output.append(
                AlignmentCurvePreviewPointRow(
                    point_id=f"{element_id}:evaluated:{index}",
                    station=float(station),
                    x=float(getattr(result, "x", 0.0) or 0.0),
                    y=float(getattr(result, "y", 0.0) or 0.0),
                    tangent_direction_deg=float(getattr(result, "tangent_direction_deg", 0.0) or 0.0),
                    role="evaluated_path",
                    element_ref=element_id,
                    notes=str(getattr(result, "notes", "") or ""),
                )
            )
        source_points = _source_points(element)
        for index, (station, x, y) in enumerate(_source_station_points(element, source_points), start=1):
            output.append(
                AlignmentCurvePreviewPointRow(
                    point_id=f"{element_id}:source:{index}",
                    station=station,
                    x=x,
                    y=y,
                    role="source_points",
                    element_ref=element_id,
                    notes="Source alignment geometry point.",
                )
            )
        kind = str(getattr(element, "kind", "") or "").lower()
        if len(source_points) < 2:
            diagnostics.append(
                DiagnosticMessage("warning", "alignment_curve_missing_geometry", f"Alignment element {element_id} has insufficient geometry payload.")
            )
        elif "curve" in kind and len(source_points) <= 2:
            diagnostics.append(
                DiagnosticMessage("warning", "alignment_curve_polyline_only", f"Curve element {element_id} is represented by too few source points.")
            )
        return output, diagnostics


def _element_row(element: AlignmentElement) -> AlignmentCurvePreviewElementRow:
    points = _source_points(element)
    direction = _curve_direction(points)
    metadata = _curve_geometry_metadata(points)
    radius = float(metadata.get("radius", 0.0) or 0.0)
    central_angle_deg = float(metadata.get("central_angle_deg", 0.0) or 0.0)
    return AlignmentCurvePreviewElementRow(
        element_id=str(getattr(element, "element_id", "") or ""),
        kind=str(getattr(element, "kind", "") or ""),
        station_start=float(getattr(element, "station_start", 0.0) or 0.0),
        station_end=float(getattr(element, "station_end", 0.0) or 0.0),
        length=float(getattr(element, "length", 0.0) or 0.0),
        point_count=len(points),
        radius=radius,
        central_angle_deg=central_angle_deg,
        curve_direction=direction,
        status="ok" if len(points) >= 2 else "warning",
        notes=_element_row_notes(element, metadata),
    )


def _element_boundary_annotations(
    element: AlignmentElement,
    rows: list[AlignmentCurvePreviewPointRow],
) -> list[AlignmentCurvePreviewAnnotationRow]:
    element_rows = [row for row in rows if row.role == "evaluated_path"]
    if not element_rows:
        return []
    element_rows.sort(key=lambda row: float(row.station))
    first = element_rows[0]
    last = element_rows[-1]
    element_id = str(getattr(element, "element_id", "") or "")
    return [
        AlignmentCurvePreviewAnnotationRow(
            annotation_id=f"{element_id}:start",
            kind="Element Start",
            label="Start",
            station=float(first.station),
            x=float(first.x),
            y=float(first.y),
            element_ref=element_id,
        ),
        AlignmentCurvePreviewAnnotationRow(
            annotation_id=f"{element_id}:end",
            kind="Element End",
            label="End",
            station=float(last.station),
            x=float(last.x),
            y=float(last.y),
            element_ref=element_id,
        ),
    ]


def _curve_annotations(
    element: AlignmentElement,
) -> tuple[list[AlignmentCurvePreviewAnnotationRow], list[DiagnosticMessage]]:
    kind = str(getattr(element, "kind", "") or "").lower()
    if not _is_curve_kind(kind):
        return [], []

    element_id = str(getattr(element, "element_id", "") or "")
    points = _source_points(element)
    station_points = _source_station_points(element, points)
    diagnostics: list[DiagnosticMessage] = []
    if len(station_points) < 3:
        return [], [
            DiagnosticMessage(
                "warning",
                "alignment_curve_pc_pi_pt_estimated",
                f"Alignment curve element {element_id} needs at least three source points for PC/PI/PT labels.",
            )
        ]

    metadata = _curve_geometry_metadata(points)
    first_station, first_x, first_y = station_points[0]
    middle_station, middle_x, middle_y = station_points[len(station_points) // 2]
    last_station, last_x, last_y = station_points[-1]
    annotations: list[AlignmentCurvePreviewAnnotationRow] = [
        AlignmentCurvePreviewAnnotationRow(
            annotation_id=f"{element_id}:pc",
            kind="PC",
            label="PC",
            station=first_station,
            x=first_x,
            y=first_y,
            element_ref=element_id,
            notes="Point of curvature inferred from the first curve source point.",
        ),
        AlignmentCurvePreviewAnnotationRow(
            annotation_id=f"{element_id}:pt",
            kind="PT",
            label="PT",
            station=last_station,
            x=last_x,
            y=last_y,
            element_ref=element_id,
            notes="Point of tangency inferred from the last curve source point.",
        ),
    ]

    pi_point = _tangent_intersection(points[0], points[1], points[-2], points[-1])
    if pi_point is None:
        pi_x, pi_y = middle_x, middle_y
        diagnostics.append(
            DiagnosticMessage(
                "warning",
                "alignment_curve_pi_fallback",
                f"Alignment curve element {element_id} PI could not be resolved from tangents; midpoint was labeled instead.",
            )
        )
    else:
        pi_x, pi_y = pi_point
    annotations.append(
        AlignmentCurvePreviewAnnotationRow(
            annotation_id=f"{element_id}:pi",
            kind="PI",
            label="PI",
            station=middle_station,
            x=pi_x,
            y=pi_y,
            element_ref=element_id,
            notes="Point of intersection inferred from entering and exiting tangents.",
        )
    )
    direction = _curve_direction(points)
    in_tangent = _segment_angle_deg(points[0], points[1])
    out_tangent = _segment_angle_deg(points[-2], points[-1])
    annotations.extend(
        [
            AlignmentCurvePreviewAnnotationRow(
                annotation_id=f"{element_id}:direction",
                kind="Curve Direction",
                label="Direction",
                station=middle_station,
                x=middle_x,
                y=middle_y,
                value=direction,
                element_ref=element_id,
                notes="Curve direction inferred from source point winding.",
            ),
            AlignmentCurvePreviewAnnotationRow(
                annotation_id=f"{element_id}:tangent-in",
                kind="Tangent In",
                label="Tangent In",
                station=first_station,
                x=first_x,
                y=first_y,
                value=f"{in_tangent:.3f} deg",
                element_ref=element_id,
                notes="Entering tangent helper inferred from the first source segment.",
            ),
            AlignmentCurvePreviewAnnotationRow(
                annotation_id=f"{element_id}:tangent-out",
                kind="Tangent Out",
                label="Tangent Out",
                station=last_station,
                x=last_x,
                y=last_y,
                value=f"{out_tangent:.3f} deg",
                element_ref=element_id,
                notes="Exiting tangent helper inferred from the last source segment.",
            ),
        ]
    )

    center_x = metadata.get("center_x")
    center_y = metadata.get("center_y")
    radius = float(metadata.get("radius", 0.0) or 0.0)
    delta = float(metadata.get("central_angle_deg", 0.0) or 0.0)
    if center_x is None or center_y is None or radius <= 0.0:
        diagnostics.append(
            DiagnosticMessage(
                "warning",
                "alignment_circular_curve_radius_missing",
                f"Alignment curve element {element_id} center/radius could not be inferred from source points.",
            )
        )
    else:
        annotations.extend(
            [
                AlignmentCurvePreviewAnnotationRow(
                    annotation_id=f"{element_id}:center",
                    kind="Curve Center",
                    label="Center",
                    station=middle_station,
                    x=float(center_x),
                    y=float(center_y),
                    element_ref=element_id,
                    notes="Circular-arc center inferred from first, middle, and last source points.",
                ),
                AlignmentCurvePreviewAnnotationRow(
                    annotation_id=f"{element_id}:radius",
                    kind="Radius",
                    label="R",
                    station=middle_station,
                    x=float(center_x),
                    y=float(center_y),
                    value=f"{radius:.3f}",
                    element_ref=element_id,
                    notes="Circular-arc radius inferred from source points.",
                ),
                AlignmentCurvePreviewAnnotationRow(
                    annotation_id=f"{element_id}:delta",
                    kind="Delta Angle",
                    label="Delta",
                    station=middle_station,
                    x=middle_x,
                    y=middle_y,
                    value=f"{delta:.3f} deg",
                    element_ref=element_id,
                    notes="Circular-arc central angle inferred from source points.",
                ),
            ]
        )
        diagnostics.append(
            DiagnosticMessage(
                "info",
                "alignment_curve_radius_delta_labeled",
                f"Alignment curve element {element_id} radius and delta angle were labeled.",
            )
        )

    diagnostics.append(
        DiagnosticMessage(
            "warning",
            "alignment_curve_pc_pi_pt_estimated",
            f"Alignment curve element {element_id} PC/PI/PT labels were estimated from available geometry.",
        )
    )
    diagnostics.append(
        DiagnosticMessage(
            "info",
            "alignment_curve_tangent_helpers_labeled",
            f"Alignment curve element {element_id} tangent helper labels were evaluated.",
        )
    )
    return annotations, diagnostics


def _station_range(start: float, end: float, interval: float) -> list[float]:
    if end < start:
        start, end = end, start
    span = float(end) - float(start)
    if span <= 1.0e-12:
        return [float(start)]
    count = max(1, int(math.ceil(span / max(float(interval), 0.1))))
    values = [float(start)]
    for index in range(1, count):
        values.append(float(start) + span * (float(index) / float(count)))
    values.append(float(end))
    return sorted({round(value, 9): value for value in values}.values())


def _source_points(element: AlignmentElement) -> list[tuple[float, float]]:
    payload = getattr(element, "geometry_payload", {}) or {}
    if not isinstance(payload, dict):
        return []
    x_values = _numeric_values(payload.get("x_values", []))
    y_values = _numeric_values(payload.get("y_values", []))
    count = min(len(x_values), len(y_values))
    return list(zip(x_values[:count], y_values[:count]))


def _source_station_points(element: AlignmentElement, points: list[tuple[float, float]]) -> list[tuple[float, float, float]]:
    if not points:
        return []
    start = float(getattr(element, "station_start", 0.0) or 0.0)
    end = float(getattr(element, "station_end", start) or start)
    if len(points) == 1:
        x, y = points[0]
        return [(start, x, y)]
    output = []
    for index, (x, y) in enumerate(points):
        station = start + (end - start) * (float(index) / float(len(points) - 1))
        output.append((station, x, y))
    return output


def _is_curve_kind(kind: str) -> bool:
    lowered = str(kind or "").lower()
    return "curve" in lowered or "arc" in lowered or "spiral" in lowered


def _element_row_notes(element: AlignmentElement, metadata: dict[str, float | None]) -> str:
    kind = str(getattr(element, "kind", "") or "").lower()
    if not _is_curve_kind(kind):
        return "Alignment element preview row."
    radius = float(metadata.get("radius", 0.0) or 0.0)
    delta = float(metadata.get("central_angle_deg", 0.0) or 0.0)
    if radius > 0.0 and delta > 0.0:
        return f"Curve metadata inferred from source points. R={radius:.3f}, delta={delta:.3f} deg."
    return "Curve metadata could not be fully inferred from source points."


def _curve_geometry_metadata(points: list[tuple[float, float]]) -> dict[str, float | None]:
    if len(points) < 3:
        return {
            "center_x": None,
            "center_y": None,
            "radius": 0.0,
            "central_angle_deg": 0.0,
        }
    first = points[0]
    middle = points[len(points) // 2]
    last = points[-1]
    center = _circle_center(first, middle, last)
    if center is None:
        return {
            "center_x": None,
            "center_y": None,
            "radius": 0.0,
            "central_angle_deg": 0.0,
        }
    center_x, center_y = center
    radius = _distance(center_x, center_y, first[0], first[1])
    if radius <= 1.0e-12:
        return {
            "center_x": center_x,
            "center_y": center_y,
            "radius": 0.0,
            "central_angle_deg": 0.0,
        }
    start_angle = math.atan2(first[1] - center_y, first[0] - center_x)
    end_angle = math.atan2(last[1] - center_y, last[0] - center_x)
    signed_delta = _signed_angle_delta(start_angle, end_angle, _curve_direction(points))
    return {
        "center_x": center_x,
        "center_y": center_y,
        "radius": radius,
        "central_angle_deg": abs(math.degrees(signed_delta)),
    }


def _circle_center(
    first: tuple[float, float],
    middle: tuple[float, float],
    last: tuple[float, float],
) -> tuple[float, float] | None:
    ax, ay = first
    bx, by = middle
    cx, cy = last
    determinant = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(determinant) <= 1.0e-12:
        return None
    ax2ay2 = ax * ax + ay * ay
    bx2by2 = bx * bx + by * by
    cx2cy2 = cx * cx + cy * cy
    center_x = (ax2ay2 * (by - cy) + bx2by2 * (cy - ay) + cx2cy2 * (ay - by)) / determinant
    center_y = (ax2ay2 * (cx - bx) + bx2by2 * (ax - cx) + cx2cy2 * (bx - ax)) / determinant
    return center_x, center_y


def _signed_angle_delta(start_angle: float, end_angle: float, direction: str) -> float:
    delta = (float(end_angle) - float(start_angle)) % (2.0 * math.pi)
    if str(direction).lower() == "right" and delta > 0.0:
        delta -= 2.0 * math.pi
    elif str(direction).lower() == "left" and delta < 0.0:
        delta += 2.0 * math.pi
    if abs(delta) > math.pi:
        delta = (2.0 * math.pi - abs(delta)) * (1.0 if delta >= 0.0 else -1.0)
    return delta


def _tangent_intersection(
    a0: tuple[float, float],
    a1: tuple[float, float],
    b0: tuple[float, float],
    b1: tuple[float, float],
) -> tuple[float, float] | None:
    x1, y1 = a0
    x2, y2 = a1
    x3, y3 = b0
    x4, y4 = b1
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denominator) <= 1.0e-12:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator
    return px, py


def _segment_angle_deg(start: tuple[float, float], end: tuple[float, float]) -> float:
    return math.degrees(math.atan2(float(end[1]) - float(start[1]), float(end[0]) - float(start[0])))


def _numeric_values(values) -> list[float]:
    output: list[float] = []
    for value in list(values or []):
        try:
            output.append(float(value))
        except Exception:
            continue
    return output


def _curve_direction(points: list[tuple[float, float]]) -> str:
    if len(points) < 3:
        return ""
    area = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        area += (float(x1) - float(x0)) * (float(y1) + float(y0))
    if abs(area) <= 1.0e-12:
        return "straight_or_unknown"
    return "left" if area < 0.0 else "right"


def _distance(x0: float, y0: float, x1: float, y1: float) -> float:
    return ((float(x1) - float(x0)) ** 2 + (float(y1) - float(y0)) ** 2) ** 0.5

"""v1 alignment source editor command."""

from __future__ import annotations

import math

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets  # noqa: F401 - runtime-injected UI collaborator

from ..ui.editors.alignment_editor import (  # noqa: F401 - runtime-injected UI collaborator
    _AlignmentCurvePreviewWidget,
    V1AlignmentEditorTaskPanel,
    configure_alignment_editor_task_panel_runtime,
)
from ..services.editing import prepare_alignment_element_rows

from ...misc.resources import icon_path
from ...objects.obj_project import (  # noqa: F401 - runtime-injected UI collaborator
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
    get_design_standard,
)
from ...objects.project_links import link_project
from ...objects import design_standards as _ds
from ...objects.csv_alignment_import import read_alignment_csv, write_alignment_csv  # noqa: F401 - runtime-injected UI collaborator
from ...objects.sketch_alignment_import import find_sketch_objects, sketch_to_alignment_rows  # noqa: F401 - runtime-injected UI collaborator
from ..services.coordinates import alignment_rows_from_local, alignment_rows_to_local  # noqa: F401 - runtime-injected UI collaborator
from ..objects.obj_alignment import (  # noqa: F401 - runtime-injected UI collaborator
    V1AlignmentObject,
    ViewProviderV1Alignment,
    ensure_v1_alignment_properties,
    find_v1_alignment,
    to_alignment_model,
)
from ..models.source.alignment_model import AlignmentElement, AlignmentModel
from ..services.evaluation import AlignmentCurvePreviewRequest, AlignmentCurvePreviewService  # noqa: F401 - runtime-injected UI collaborator
from ..ui.common.styles import apply_clickable_tab_style  # noqa: F401 - runtime-injected UI collaborator
from .selection_context import selected_alignment_profile_target


ALIGNMENT_PRESETS = {
    "Simple Tangent": {
        "note": "Straight starter with no circular curve intent.",
        "rows": [
            (0.0, 0.0, 0.0, 0.0),
            (80.0, 0.0, 0.0, 0.0),
            (160.0, 0.0, 0.0, 0.0),
        ],
    },
    "Single Curve": {
        "note": "One PI with circular-curve intent.",
        "rows": [
            (0.0, 0.0, 0.0, 0.0),
            (70.0, 0.0, 120.0, 0.0),
            (140.0, 45.0, 0.0, 0.0),
        ],
    },
    "S-C-S Curve": {
        "note": "One PI with spiral-circular-spiral intent.",
        "rows": [
            (0.0, 0.0, 0.0, 0.0),
            (80.0, 0.0, 180.0, 30.0),
            (170.0, 55.0, 0.0, 0.0),
        ],
    },
    "Reverse Curve": {
        "note": "Alternating curve intent for reverse-curve checks.",
        "rows": [
            (0.0, 0.0, 0.0, 0.0),
            (60.0, 0.0, 120.0, 20.0),
            (120.0, 45.0, 120.0, 20.0),
            (180.0, 0.0, 0.0, 0.0),
        ],
    },
    "Sample Local Alignment": {
        "note": "Multi-PI starter for quick table editing.",
        "rows": [
            (0.0, 0.0, 0.0, 0.0),
            (55.0, 0.0, 90.0, 15.0),
            (115.0, 40.0, 140.0, 20.0),
            (190.0, 60.0, 0.0, 0.0),
        ],
    },
}

ALIGNMENT_PRESET_PLACEMENTS = [
    "Pattern only",
    "Center on terrain",
    "Center on project origin",
]


def alignment_preset_placement_names() -> list[str]:
    """Return supported preset placement modes for the v1 Alignment editor."""

    return list(ALIGNMENT_PRESET_PLACEMENTS)


def _alignment_table_height(table, *, visible_rows: int = 6) -> int:
    """Return a compact fixed table height for alignment editor tables."""

    try:
        visible = max(1, int(visible_rows))
        row_count = max(int(table.rowCount()), 0)
        header_height = int(table.horizontalHeader().height()) if table.horizontalHeader() is not None else 28
        row_height = 0
        if row_count > 0:
            for row_index in range(min(row_count, visible)):
                row_height = max(row_height, int(table.rowHeight(row_index)))
        if row_height <= 0:
            row_height = int(table.verticalHeader().defaultSectionSize()) if table.verticalHeader() is not None else 28
        row_height = max(row_height, 24)
        scrollbar_height = 18 if table.horizontalScrollBarPolicy() != QtCore.Qt.ScrollBarAlwaysOff else 0
        frame = int(table.frameWidth()) * 2 if hasattr(table, "frameWidth") else 4
        return int(header_height + (visible * row_height) + scrollbar_height + frame + 6)
    except Exception:
        return 220


def _fit_alignment_table_height(table, *, visible_rows: int = 6) -> None:
    try:
        table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        table.setFixedHeight(_alignment_table_height(table, visible_rows=visible_rows))
    except Exception:
        pass


def alignment_preset_center(rows) -> tuple[float, float]:
    """Return the bounding-box center of local preset PI rows."""

    values = list(rows or [])
    if not values:
        return 0.0, 0.0
    xs = [float(row[0]) for row in values]
    ys = [float(row[1]) for row in values]
    return (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5


def alignment_preset_rows_for_placement(
    rows,
    placement: str,
    *,
    terrain_center: tuple[float, float] | None = None,
    project_origin: tuple[float, float] = (0.0, 0.0),
) -> dict[str, object]:
    """Translate preset PI rows according to a user-selected placement mode."""

    rows_in = [tuple(row) for row in list(rows or [])]
    placement_text = str(placement or "Pattern only").strip() or "Pattern only"
    source_x, source_y = alignment_preset_center(rows_in)
    target = None
    placement_used = placement_text

    if placement_text == "Center on terrain":
        if terrain_center is not None:
            target = (float(terrain_center[0]), float(terrain_center[1]))
            note = f"Terrain center used: X={target[0]:.3f}, Y={target[1]:.3f}"
        else:
            target = (float(project_origin[0]), float(project_origin[1]))
            placement_used = "Center on project origin (fallback)"
            note = "Terrain was not available; project origin was used instead."
    elif placement_text == "Center on project origin":
        target = (float(project_origin[0]), float(project_origin[1]))
        note = f"Project origin used: X={target[0]:.3f}, Y={target[1]:.3f}"
    else:
        note = "Preset kept its original pattern position."

    if target is None:
        return {"rows": rows_in, "placement": placement_used, "note": note}

    dx = float(target[0]) - float(source_x)
    dy = float(target[1]) - float(source_y)
    return {
        "rows": [(float(x) + dx, float(y) + dy, float(radius), float(ls)) for x, y, radius, ls in rows_in],
        "placement": placement_used,
        "note": note,
    }


def alignment_element_rows(alignment) -> list[dict[str, object]]:
    """Return editable geometry rows from a V1Alignment object."""

    if alignment is None:
        return []
    ensure_v1_alignment_properties(alignment)
    element_ids = list(getattr(alignment, "ElementIds", []) or [])
    kinds = list(getattr(alignment, "ElementKinds", []) or [])
    starts = _float_list(getattr(alignment, "StationStarts", []) or [])
    ends = _float_list(getattr(alignment, "StationEnds", []) or [])
    lengths = _float_list(getattr(alignment, "ElementLengths", []) or [])
    x_rows = list(getattr(alignment, "XValueRows", []) or [])
    y_rows = list(getattr(alignment, "YValueRows", []) or [])
    count = max(len(element_ids), len(kinds), len(starts), len(ends), len(x_rows), len(y_rows))
    alignment_id = str(getattr(alignment, "AlignmentId", "") or getattr(alignment, "Name", "") or "alignment:v1")
    rows: list[dict[str, object]] = []
    for index in range(count):
        station_start = float(starts[index]) if index < len(starts) else 0.0
        station_end = float(ends[index]) if index < len(ends) else station_start
        rows.append(
            {
                "element_id": (
                    str(element_ids[index])
                    if index < len(element_ids) and str(element_ids[index] or "").strip()
                    else f"{alignment_id}:element:{index + 1}"
                ),
                "kind": str(kinds[index] if index < len(kinds) and kinds[index] else "tangent"),
                "station_start": station_start,
                "station_end": station_end,
                "length": float(lengths[index]) if index < len(lengths) else max(0.0, station_end - station_start),
                "x_values": str(x_rows[index] if index < len(x_rows) else ""),
                "y_values": str(y_rows[index] if index < len(y_rows) else ""),
            }
        )
    return rows


def apply_alignment_element_rows(alignment, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Validate, sort, and write geometry rows back to a V1Alignment object."""

    if alignment is None:
        raise ValueError("No V1Alignment object is available.")
    ensure_v1_alignment_properties(alignment)
    normalized = prepare_alignment_element_rows(_normalized_element_rows(alignment, rows))
    alignment.ElementIds = [str(row["element_id"]) for row in normalized]
    alignment.ElementKinds = [str(row["kind"]) for row in normalized]
    alignment.StationStarts = [float(row["station_start"]) for row in normalized]
    alignment.StationEnds = [float(row["station_end"]) for row in normalized]
    alignment.ElementLengths = [float(row["length"]) for row in normalized]
    alignment.XValueRows = [str(row["x_values"]) for row in normalized]
    alignment.YValueRows = [str(row["y_values"]) for row in normalized]
    try:
        alignment.touch()
    except Exception:
        pass
    return normalized


def alignment_model_from_editor_rows(
    rows: list[dict[str, object]],
    *,
    alignment_id: str = "alignment:curve-preview",
    label: str = "Alignment Curve Preview",
) -> AlignmentModel:
    """Build a transient AlignmentModel from compiled editor geometry rows."""

    return AlignmentModel(
        schema_version=1,
        project_id="corridorroad-v1",
        alignment_id=str(alignment_id or "alignment:curve-preview"),
        label=str(label or "Alignment Curve Preview"),
        alignment_kind="road_centerline",
        source_refs=["alignment-editor-current-table"],
        geometry_sequence=[
            AlignmentElement(
                element_id=str(row.get("element_id", "") or f"{alignment_id}:element:{index + 1}"),
                kind=str(row.get("kind", "") or "tangent"),
                station_start=float(row.get("station_start", 0.0) or 0.0),
                station_end=float(row.get("station_end", 0.0) or 0.0),
                length=float(row.get("length", 0.0) or 0.0),
                geometry_payload={
                    "x_values": _csv_float_row(row.get("x_values", "")),
                    "y_values": _csv_float_row(row.get("y_values", "")),
                },
            )
            for index, row in enumerate(list(rows or []))
        ],
    )


def alignment_ip_rows(alignment) -> list[dict[str, float]]:
    """Return v0-style PI input rows from a V1Alignment object."""

    if alignment is None:
        return []
    ensure_v1_alignment_properties(alignment)
    points = list(getattr(alignment, "IPPoints", []) or [])
    radii = _float_list(getattr(alignment, "CurveRadii", []) or [])
    transitions = _float_list(getattr(alignment, "TransitionLengths", []) or [])
    if not points:
        return _ip_rows_from_element_rows(alignment_element_rows(alignment))
    rows: list[dict[str, float]] = []
    for index, point in enumerate(points):
        rows.append(
            {
                "x": float(getattr(point, "x", 0.0) or 0.0),
                "y": float(getattr(point, "y", 0.0) or 0.0),
                "radius": float(radii[index]) if index < len(radii) else 0.0,
                "transition_length": float(transitions[index]) if index < len(transitions) else 0.0,
            }
        )
    return rows


def alignment_compiled_summary_rows(alignment) -> list[dict[str, object]]:
    """Return review rows for compiled v1 station geometry."""

    rows: list[dict[str, object]] = []
    for index, row in enumerate(alignment_element_rows(alignment), start=1):
        x_values = _csv_float_row(row.get("x_values", ""))
        y_values = _csv_float_row(row.get("y_values", ""))
        point_count = min(len(x_values), len(y_values))
        rows.append(
            {
                "index": index,
                "kind": str(row.get("kind", "") or "tangent"),
                "station_start": float(row.get("station_start", 0.0) or 0.0),
                "station_end": float(row.get("station_end", 0.0) or 0.0),
                "length": float(row.get("length", 0.0) or 0.0),
                "point_count": point_count,
                "x_values": _format_csv_float_row(x_values),
                "y_values": _format_csv_float_row(y_values),
            }
        )
    return rows


def alignment_pi_review_rows(alignment) -> list[dict[str, object]]:
    """Return PI-centered review rows with approximate curve station data."""

    if alignment is None:
        return []
    ensure_v1_alignment_properties(alignment)
    ip_rows = alignment_ip_rows(alignment)
    curve_elements = [
        row
        for row in alignment_compiled_summary_rows(alignment)
        if str(row.get("kind", "") or "") in {"sampled_curve", "transition_curve", "circular_curve"}
    ]
    curve_info = _curve_infos_for_ip_rows(
        ip_rows,
        use_transition_curves=bool(getattr(alignment, "UseTransitionCurves", True)),
        spiral_segments=int(getattr(alignment, "SpiralSegments", 16) or 16),
    )
    review_rows: list[dict[str, object]] = []
    curve_cursor = 0
    for index, row in enumerate(ip_rows):
        input_radius = float(row.get("radius", 0.0) or 0.0)
        input_transition = float(row.get("transition_length", 0.0) or 0.0)
        info = curve_info.get(index)
        curve_element = None
        if info is not None and curve_cursor < len(curve_elements):
            curve_element = curve_elements[curve_cursor]
            curve_cursor += 1
        applied_radius = float(info.get("radius", 0.0) or 0.0) if info is not None else 0.0
        applied_transition = float(info.get("transition_length", 0.0) or 0.0) if info is not None else 0.0
        ts_station = float(curve_element.get("station_start", 0.0)) if curve_element is not None else None
        te_station = float(curve_element.get("station_end", 0.0)) if curve_element is not None else None
        sc_station = None
        cs_station = None
        if ts_station is not None and te_station is not None and applied_transition > 0.0:
            mid_station = 0.5 * (ts_station + te_station)
            sc_station = min(ts_station + applied_transition, mid_station)
            cs_station = max(te_station - applied_transition, mid_station)
        review_rows.append(
            {
                "ip_index": index + 1,
                "x": float(row.get("x", 0.0) or 0.0),
                "y": float(row.get("y", 0.0) or 0.0),
                "input_radius": input_radius,
                "input_transition": input_transition,
                "applied_radius": applied_radius,
                "applied_transition": applied_transition,
                "clamped": bool(
                    info is not None
                    and (
                        abs(applied_radius - input_radius) > 1.0e-6
                        or abs(applied_transition - input_transition) > 1.0e-6
                    )
                ),
                "ts_station": ts_station,
                "sc_station": sc_station,
                "cs_station": cs_station,
                "te_station": te_station,
                "curve_length": float(curve_element.get("length", 0.0)) if curve_element is not None else 0.0,
                "curve_point_count": int(curve_element.get("point_count", 0)) if curve_element is not None else 0,
                "kind": str(curve_element.get("kind", "endpoint" if index in {0, len(ip_rows) - 1} else "tangent_pi"))
                if curve_element is not None
                else ("endpoint" if index in {0, len(ip_rows) - 1} else "tangent_pi"),
            }
        )
    return review_rows


def apply_alignment_ip_rows(
    alignment,
    rows: list[dict[str, object]],
    *,
    use_transition_curves: bool = True,
    spiral_segments: int = 16,
    design_standard: str = "KDS",
    design_speed_kph: float = 60.0,
    superelevation_pct: float = 8.0,
    side_friction: float = 0.15,
    min_radius: float = 0.0,
    min_tangent_length: float = 20.0,
    min_transition_length: float = 20.0,
) -> list[dict[str, object]]:
    """Store v0-style PI rows and compile them into v1 station geometry rows."""

    if alignment is None:
        raise ValueError("No V1Alignment object is available.")
    ensure_v1_alignment_properties(alignment)
    normalized, warnings = _normalized_ip_rows(rows)
    compiled = _compile_ip_rows_to_element_rows(
        alignment,
        normalized,
        use_transition_curves=use_transition_curves,
        spiral_segments=spiral_segments,
    )
    criteria_messages = _criteria_messages(
        normalized,
        use_transition_curves=use_transition_curves,
        design_standard=design_standard,
        design_speed_kph=design_speed_kph,
        superelevation_pct=superelevation_pct,
        side_friction=side_friction,
        min_radius=min_radius,
        min_tangent_length=min_tangent_length,
        min_transition_length=min_transition_length,
        input_warnings=warnings,
    )

    alignment.IPPoints = [_vector(row["x"], row["y"]) for row in normalized]
    alignment.CurveRadii = [float(row["radius"]) for row in normalized]
    alignment.TransitionLengths = [float(row["transition_length"]) for row in normalized]
    alignment.UseTransitionCurves = bool(use_transition_curves)
    alignment.SpiralSegments = int(max(4, int(spiral_segments)))
    alignment.DesignSpeedKph = float(design_speed_kph)
    alignment.SuperelevationPct = float(superelevation_pct)
    alignment.SideFriction = float(side_friction)
    alignment.MinRadius = float(min_radius)
    alignment.MinTangentLength = float(min_tangent_length)
    alignment.MinTransitionLength = float(min_transition_length)
    alignment.CriteriaStandard = _ds.normalize_standard(design_standard)
    alignment.CriteriaMessages = criteria_messages
    alignment.CriteriaStatus = "OK" if not criteria_messages else f"WARN ({len(criteria_messages)})"
    alignment.TotalLength = float(compiled[-1]["station_end"]) if compiled else 0.0

    apply_alignment_element_rows(alignment, compiled)
    try:
        alignment.touch()
    except Exception:
        pass
    return compiled


def create_blank_v1_alignment(*, document=None, project=None, label: str = "Main Alignment"):
    """Create an empty v1 alignment source object for Apply-time authoring."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 alignment creation.")

    prj = project or find_project(doc)
    if prj is None:
        try:
            prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
        except Exception:
            prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        prj.Label = "Parametric Road Project"

    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    try:
        obj = doc.addObject("Part::FeaturePython", "V1Alignment")
    except Exception:
        obj = doc.addObject("App::FeaturePython", "V1Alignment")
    V1AlignmentObject(obj)
    try:
        ViewProviderV1Alignment(obj.ViewObject)
    except Exception:
        pass
    obj.Label = label
    obj.ProjectId = str(getattr(prj, "ProjectId", "") or "corridorroad-v1")
    obj.AlignmentId = f"alignment:{str(getattr(obj, 'Name', '') or 'main')}"
    obj.AlignmentKind = "road_centerline"
    link_project(prj, links={"Alignment": obj}, adopt_extra=[obj])
    return obj


def run_v1_alignment_editor_command():
    """Open the v1 alignment editor without creating sample data on open."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    preferred_alignment, _preferred_profile = selected_alignment_profile_target(Gui, document)
    alignment = find_v1_alignment(document, preferred_alignment=preferred_alignment)
    if Gui is not None and hasattr(Gui, "Control"):
        if alignment is not None:
            try:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(alignment)
            except Exception:
                pass
        Gui.Control.showDialog(V1AlignmentEditorTaskPanel(alignment=alignment, document=document))
    return alignment


class CmdV1AlignmentEditor:
    """Open the v1 alignment source editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("alignment.svg"),
            "MenuText": "Alignment",
            "ToolTip": "Create or edit the v1 alignment PI geometry and criteria",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_alignment_editor_command()


def _normalized_ip_rows(
    rows: list[dict[str, object]],
    *,
    min_rows: int = 2,
) -> tuple[list[dict[str, float]], list[str]]:
    normalized: list[dict[str, float]] = []
    warnings: list[str] = []
    for index, row in enumerate(rows):
        x = _required_float(row.get("x", None), f"Row {index + 1} X")
        y = _required_float(row.get("y", None), f"Row {index + 1} Y")
        radius = max(0.0, _optional_float(row.get("radius", 0.0)) or 0.0)
        transition_length = max(0.0, _optional_float(row.get("transition_length", 0.0)) or 0.0)
        normalized.append(
            {
                "x": float(x),
                "y": float(y),
                "radius": float(radius),
                "transition_length": float(transition_length),
            }
        )

    if len(normalized) < min_rows:
        raise ValueError(f"Alignment needs at least {min_rows} PI rows.")

    tolerance = 1.0e-6
    for index in range(len(normalized) - 1):
        current = normalized[index]
        next_row = normalized[index + 1]
        if _distance(current["x"], current["y"], next_row["x"], next_row["y"]) <= tolerance:
            raise ValueError(f"Rows {index + 1} and {index + 2} are duplicated or too close.")

    if normalized:
        if abs(float(normalized[0]["radius"])) > 1.0e-9 or abs(float(normalized[-1]["radius"])) > 1.0e-9:
            warnings.append("Endpoint radius values were forced to 0.")
        if abs(float(normalized[0]["transition_length"])) > 1.0e-9 or abs(float(normalized[-1]["transition_length"])) > 1.0e-9:
            warnings.append("Endpoint transition length values were forced to 0.")
        normalized[0]["radius"] = 0.0
        normalized[-1]["radius"] = 0.0
        normalized[0]["transition_length"] = 0.0
        normalized[-1]["transition_length"] = 0.0
    return normalized, warnings


def _compile_ip_rows_to_element_rows(
    alignment,
    rows: list[dict[str, float]],
    *,
    use_transition_curves: bool = True,
    spiral_segments: int = 16,
) -> list[dict[str, object]]:
    alignment_id = str(getattr(alignment, "AlignmentId", "") or getattr(alignment, "Name", "") or "alignment:v1")
    compiled: list[dict[str, object]] = []
    station = 0.0
    chunks = _sampled_alignment_chunks_from_ip_rows(
        rows,
        use_transition_curves=use_transition_curves,
        spiral_segments=spiral_segments,
    )
    for index, chunk in enumerate(chunks, start=1):
        points = list(chunk.get("points", []) or [])
        length = _polyline_length(points)
        if length <= 1.0e-9:
            continue
        station_start = station
        station_end = station_start + length
        compiled.append(
            {
                "element_id": f"{alignment_id}:compiled:{index}",
                "kind": str(chunk.get("kind", "") or "tangent"),
                "station_start": station_start,
                "station_end": station_end,
                "length": length,
                "x_values": _format_csv_float_row([point[0] for point in points]),
                "y_values": _format_csv_float_row([point[1] for point in points]),
            }
        )
        station = station_end
    if not compiled:
        raise ValueError("Alignment could not compile PI rows into station geometry.")
    return compiled


def _sampled_alignment_chunks_from_ip_rows(
    rows: list[dict[str, float]],
    *,
    use_transition_curves: bool,
    spiral_segments: int,
) -> list[dict[str, object]]:
    points = [(float(row["x"]), float(row["y"])) for row in rows]
    curve_infos = _curve_infos_for_ip_rows(
        rows,
        use_transition_curves=use_transition_curves,
        spiral_segments=spiral_segments,
    )
    chunks: list[dict[str, object]] = []
    current = points[0]

    for index in range(len(points) - 1):
        next_curve = curve_infos.get(index + 1)
        line_end = next_curve["in_point"] if next_curve is not None else points[index + 1]
        if _distance(current[0], current[1], line_end[0], line_end[1]) > 1.0e-9:
            chunks.append({"kind": "tangent", "points": [current, line_end]})
            current = line_end
        if next_curve is not None:
            kind = "transition_curve" if float(next_curve.get("transition_length", 0.0) or 0.0) > 0.0 else "sampled_curve"
            arc_points = list(next_curve.get("points", []) or [])
            if len(arc_points) >= 2:
                chunks.append({"kind": kind, "points": arc_points})
                current = arc_points[-1]
    return chunks


def _curve_infos_for_ip_rows(
    rows: list[dict[str, float]],
    *,
    use_transition_curves: bool,
    spiral_segments: int,
) -> dict[int, dict[str, object]]:
    infos: dict[int, dict[str, object]] = {}
    sample_count_base = max(8, int(spiral_segments or 16))
    for index in range(1, len(rows) - 1):
        previous_row = rows[index - 1]
        row = rows[index]
        next_row = rows[index + 1]
        radius = float(row.get("radius", 0.0) or 0.0)
        if radius <= 1.0e-9:
            continue

        p0 = (float(previous_row["x"]), float(previous_row["y"]))
        pi = (float(row["x"]), float(row["y"]))
        p2 = (float(next_row["x"]), float(next_row["y"]))
        incoming_length = _distance(p0[0], p0[1], pi[0], pi[1])
        outgoing_length = _distance(pi[0], pi[1], p2[0], p2[1])
        if incoming_length <= 1.0e-9 or outgoing_length <= 1.0e-9:
            continue

        incoming = ((pi[0] - p0[0]) / incoming_length, (pi[1] - p0[1]) / incoming_length)
        outgoing = ((p2[0] - pi[0]) / outgoing_length, (p2[1] - pi[1]) / outgoing_length)
        delta = math.atan2(_cross_2d(incoming, outgoing), _dot_2d(incoming, outgoing))
        abs_delta = abs(delta)
        if abs_delta <= math.radians(1.0):
            continue

        tan_half = math.tan(0.5 * abs_delta)
        if abs(tan_half) <= 1.0e-12:
            continue
        requested_transition = float(row.get("transition_length", 0.0) or 0.0) if use_transition_curves else 0.0
        requested_setback = _tangent_setback(radius, requested_transition, abs_delta)
        max_setback = 0.45 * min(incoming_length, outgoing_length)
        scale = 1.0
        if requested_setback > max_setback and requested_setback > 1.0e-9:
            scale = max_setback / requested_setback
        setback = min(requested_setback, max_setback)
        if setback <= 1.0e-9:
            continue
        effective_radius = max(1.0e-9, radius * scale)
        effective_transition = max(0.0, requested_transition * scale)
        max_transition = max(0.0, 0.80 * abs_delta * effective_radius)
        if effective_transition > max_transition:
            effective_transition = max_transition
            setback = min(_tangent_setback(effective_radius, effective_transition, abs_delta), max_setback)

        turn_sign = 1.0 if delta > 0.0 else -1.0
        in_point = (pi[0] - incoming[0] * setback, pi[1] - incoming[1] * setback)
        out_point = (pi[0] + outgoing[0] * setback, pi[1] + outgoing[1] * setback)
        arc_points = _sample_scs_or_arc_points(
            in_point,
            out_point,
            incoming,
            abs_delta=abs_delta,
            turn_sign=turn_sign,
            radius=effective_radius,
            transition_length=effective_transition,
            sample_count_base=sample_count_base,
        )
        infos[index] = {
            "in_point": in_point,
            "out_point": out_point,
            "points": arc_points,
            "radius": effective_radius,
            "transition_length": effective_transition,
        }
    return infos


def _tangent_setback(radius: float, transition_length: float, deflection_angle: float) -> float:
    radius = max(0.0, float(radius))
    transition_length = max(0.0, float(transition_length))
    theta = max(0.0, float(deflection_angle))
    if radius <= 1.0e-9 or theta <= 1.0e-9:
        return 0.0
    shift = (transition_length * transition_length) / (24.0 * radius) if transition_length > 1.0e-9 else 0.0
    return (radius + shift) * math.tan(0.5 * theta) + 0.5 * transition_length


def _sample_scs_or_arc_points(
    in_point: tuple[float, float],
    out_point: tuple[float, float],
    incoming: tuple[float, float],
    *,
    abs_delta: float,
    turn_sign: float,
    radius: float,
    transition_length: float,
    sample_count_base: int,
) -> list[tuple[float, float]]:
    if transition_length > 1.0e-9:
        return _sample_scs_points(
            in_point,
            out_point,
            incoming,
            abs_delta=abs_delta,
            turn_sign=turn_sign,
            radius=radius,
            transition_length=transition_length,
            sample_count_base=sample_count_base,
        )
    return _sample_arc_points(
        in_point,
        out_point,
        incoming,
        abs_delta=abs_delta,
        turn_sign=turn_sign,
        radius=radius,
        sample_count_base=sample_count_base,
    )


def _sample_arc_points(
    in_point: tuple[float, float],
    out_point: tuple[float, float],
    incoming: tuple[float, float],
    *,
    abs_delta: float,
    turn_sign: float,
    radius: float,
    sample_count_base: int,
) -> list[tuple[float, float]]:
    normal_in = _left_normal(incoming)
    center = (
        in_point[0] + turn_sign * radius * normal_in[0],
        in_point[1] + turn_sign * radius * normal_in[1],
    )
    start_angle = math.atan2(in_point[1] - center[1], in_point[0] - center[0])
    end_angle = start_angle + turn_sign * abs_delta
    samples = max(4, int(math.ceil(sample_count_base * abs_delta / (0.5 * math.pi))))
    points = []
    for sample_index in range(samples + 1):
        ratio = float(sample_index) / float(samples)
        angle = start_angle + (end_angle - start_angle) * ratio
        points.append((center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle)))
    points[0] = in_point
    points[-1] = out_point
    return points


def _sample_scs_points(
    in_point: tuple[float, float],
    out_point: tuple[float, float],
    incoming: tuple[float, float],
    *,
    abs_delta: float,
    turn_sign: float,
    radius: float,
    transition_length: float,
    sample_count_base: int,
) -> list[tuple[float, float]]:
    transition_length = max(0.0, min(float(transition_length), 0.80 * float(abs_delta) * float(radius)))
    circular_angle = max(0.0, float(abs_delta) - (transition_length / float(radius)))
    circular_length = float(radius) * circular_angle
    heading = math.atan2(float(incoming[1]), float(incoming[0]))
    x, y = float(in_point[0]), float(in_point[1])
    points = [(x, y)]

    def _advance(length: float, k_start: float, k_end: float, steps: int) -> None:
        nonlocal x, y, heading
        if length <= 1.0e-9 or steps <= 0:
            return
        ds = float(length) / float(steps)
        for step in range(steps):
            t0 = float(step) / float(steps)
            t1 = float(step + 1) / float(steps)
            k0 = float(k_start) + (float(k_end) - float(k_start)) * t0
            k1 = float(k_start) + (float(k_end) - float(k_start)) * t1
            d_heading = turn_sign * 0.5 * (k0 + k1) * ds
            mid_heading = heading + 0.5 * d_heading
            x += ds * math.cos(mid_heading)
            y += ds * math.sin(mid_heading)
            heading += d_heading
            points.append((x, y))

    spiral_steps = max(4, int(sample_count_base))
    circular_steps = max(2, int(math.ceil(sample_count_base * circular_angle / (0.5 * math.pi)))) if circular_length > 1.0e-9 else 0
    full_curvature = 1.0 / float(radius)
    _advance(transition_length, 0.0, full_curvature, spiral_steps)
    _advance(circular_length, full_curvature, full_curvature, circular_steps)
    _advance(transition_length, full_curvature, 0.0, spiral_steps)

    # Numerical integration plus short-layout clamping can leave a small endpoint gap.
    # Distribute the correction so adjacent tangent chunks connect exactly.
    end_x, end_y = points[-1]
    err_x = float(out_point[0]) - float(end_x)
    err_y = float(out_point[1]) - float(end_y)
    corrected = []
    count = max(1, len(points) - 1)
    for index, point in enumerate(points):
        ratio = float(index) / float(count)
        corrected.append((point[0] + err_x * ratio, point[1] + err_y * ratio))
    corrected[0] = in_point
    corrected[-1] = out_point
    return corrected


def _criteria_messages(
    rows: list[dict[str, float]],
    *,
    use_transition_curves: bool,
    design_standard: str,
    design_speed_kph: float,
    superelevation_pct: float,
    side_friction: float,
    min_radius: float,
    min_tangent_length: float,
    min_transition_length: float,
    input_warnings: list[str],
) -> list[str]:
    messages = list(input_warnings or [])
    standard = _ds.normalize_standard(design_standard)
    defaults = _ds.criteria_defaults(standard, design_speed_kph)
    radius_limit = float(min_radius) if float(min_radius) > 0.0 else float(defaults.get("min_radius", 0.0) or 0.0)
    transition_limit = max(float(min_transition_length), float(defaults.get("min_transition", 0.0) or 0.0))
    tangent_limit = max(float(min_tangent_length), float(defaults.get("min_tangent", 0.0) or 0.0))

    for index, row in enumerate(rows[1:-1], start=2):
        radius = float(row.get("radius", 0.0) or 0.0)
        transition = float(row.get("transition_length", 0.0) or 0.0)
        if radius > 0.0 and radius_limit > 0.0 and radius < radius_limit - 1.0e-6:
            messages.append(f"[RADIUS] IP#{index} R={radius:.3f}m < min {radius_limit:.3f}m.")
        if use_transition_curves and transition > 0.0 and transition < transition_limit - 1.0e-6:
            messages.append(f"[TRANSITION] IP#{index} Ls={transition:.3f}m < min {transition_limit:.3f}m.")

    for index in range(len(rows) - 1):
        a = rows[index]
        b = rows[index + 1]
        length = _distance(a["x"], a["y"], b["x"], b["y"])
        if length < tangent_limit - 1.0e-6:
            messages.append(f"[TANGENT] Segment {index + 1}-{index + 2} length={length:.3f}m < min {tangent_limit:.3f}m.")

    if any(float(row.get("radius", 0.0) or 0.0) > 0.0 for row in rows):
        messages.append("[INFO] v1 compiles PI curves as sampled station geometry; full analytic clothoid objects remain a follow-up task.")
    if superelevation_pct < 0.0 or side_friction <= 0.0:
        messages.append("[CRITERIA] Superelevation and side friction inputs should be positive.")
    return messages


def _ip_rows_from_element_rows(rows: list[dict[str, object]]) -> list[dict[str, float]]:
    out: list[dict[str, float]] = []
    for row in rows:
        x_values = _csv_float_row(row.get("x_values", ""))
        y_values = _csv_float_row(row.get("y_values", ""))
        count = min(len(x_values), len(y_values))
        for index in range(count):
            x = float(x_values[index])
            y = float(y_values[index])
            if out and _distance(out[-1]["x"], out[-1]["y"], x, y) <= 1.0e-6:
                continue
            out.append({"x": x, "y": y, "radius": 0.0, "transition_length": 0.0})
    return out


def _normalized_element_rows(
    alignment,
    rows: list[dict[str, object]],
    *,
    min_rows: int = 1,
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    alignment_id = str(getattr(alignment, "AlignmentId", "") or getattr(alignment, "Name", "") or "alignment:v1")
    for index, row in enumerate(rows):
        station_start = _required_float(row.get("station_start", None), f"Row {index + 1} start station")
        station_end = _required_float(row.get("station_end", None), f"Row {index + 1} end station")
        if station_end < station_start:
            raise ValueError(f"Row {index + 1} end station must be greater than or equal to start station.")
        x_values = _csv_float_row(row.get("x_values", ""))
        y_values = _csv_float_row(row.get("y_values", ""))
        if len(x_values) != len(y_values):
            raise ValueError(f"Row {index + 1} X/Y value counts must match.")
        if len(x_values) < 2:
            raise ValueError(f"Row {index + 1} needs at least two XY points.")
        kind = str(row.get("kind", "") or "tangent").strip() or "tangent"
        element_id = str(row.get("element_id", "") or "").strip()
        if not element_id:
            element_id = f"{alignment_id}:element:{index + 1}"
        normalized.append(
            {
                "element_id": element_id,
                "kind": kind,
                "station_start": station_start,
                "station_end": station_end,
                "length": max(0.0, station_end - station_start),
                "x_values": _format_csv_float_row(x_values),
                "y_values": _format_csv_float_row(y_values),
            }
        )
    if len(normalized) < min_rows:
        raise ValueError(f"Alignment needs at least {min_rows} geometry element row.")
    normalized.sort(key=lambda item: (float(item["station_start"]), float(item["station_end"])))
    return normalized


def _existing_element_id(alignment, row_index: int) -> str:
    ids = list(getattr(alignment, "ElementIds", []) or []) if alignment is not None else []
    if row_index < len(ids):
        return str(ids[row_index] or "")
    return ""


def _float_list(values) -> list[float]:
    result = []
    for value in list(values or []):
        result.append(_optional_float(value) or 0.0)
    return result


def _csv_float_row(text) -> list[float]:
    values = []
    for token in str(text or "").split(","):
        token = token.strip()
        if not token:
            continue
        values.append(_required_float(token, "XY value"))
    return values


def _format_csv_float_row(values: list[float]) -> str:
    return ",".join(_format_float(value) for value in values)


def _required_float(value, label: str) -> float:
    try:
        return float(value)
    except Exception:
        raise ValueError(f"{label} must be a number.") from None


def _optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _format_float(value) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"


def _format_optional_station(value) -> str:
    if value is None:
        return "-"
    return _format_float(value)


def _format_pi_review_line(row: dict[str, object]) -> str:
    curve_bits = [
        f"IP#{int(row.get('ip_index', 0) or 0)}",
        f"kind={str(row.get('kind', '') or '-')}",
        f"XY=({_format_float(row.get('x', 0.0))}, {_format_float(row.get('y', 0.0))})",
        f"R in/app={_format_float(row.get('input_radius', 0.0))}/{_format_float(row.get('applied_radius', 0.0))}",
        f"Ls in/app={_format_float(row.get('input_transition', 0.0))}/{_format_float(row.get('applied_transition', 0.0))}",
    ]
    if bool(row.get("clamped", False)):
        curve_bits.append("clamped=yes")
    if row.get("ts_station", None) is not None or row.get("te_station", None) is not None:
        curve_bits.append(
            "TS/SC/CS/ST="
            f"{_format_optional_station(row.get('ts_station', None))}/"
            f"{_format_optional_station(row.get('sc_station', None))}/"
            f"{_format_optional_station(row.get('cs_station', None))}/"
            f"{_format_optional_station(row.get('te_station', None))}"
        )
        curve_bits.append(f"curve_len={_format_float(row.get('curve_length', 0.0))}")
        curve_bits.append(f"pts={int(row.get('curve_point_count', 0) or 0)}")
    return " | ".join(curve_bits)


def _format_compiled_review_line(row: dict[str, object]) -> str:
    return (
        f"#{int(row.get('index', 0) or 0)} "
        f"{str(row.get('kind', '') or 'tangent')} | "
        f"STA {_format_float(row.get('station_start', 0.0))} -> {_format_float(row.get('station_end', 0.0))} | "
        f"L={_format_float(row.get('length', 0.0))} | "
        f"pts={int(row.get('point_count', 0) or 0)}"
    )


def _distance(x0: float, y0: float, x1: float, y1: float) -> float:
    return math.hypot(float(x1) - float(x0), float(y1) - float(y0))


def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        _distance(float(a[0]), float(a[1]), float(b[0]), float(b[1]))
        for a, b in zip(points, points[1:])
    )


def _dot_2d(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1])


def _cross_2d(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(a[0]) * float(b[1]) - float(a[1]) * float(b[0])


def _left_normal(v: tuple[float, float]) -> tuple[float, float]:
    return -float(v[1]), float(v[0])


def _vector(x: float, y: float):
    if App is not None and hasattr(App, "Vector"):
        return App.Vector(float(x), float(y), 0.0)
    return type("_Vector", (), {"x": float(x), "y": float(y), "z": 0.0})()


def _shift_last_coordinate_row(text: str, delta: float) -> str:
    values = _csv_float_row(text)
    if not values:
        return "0.0,20.0"
    last = values[-1]
    return _format_csv_float_row([last, last + float(delta)])


configure_alignment_editor_task_panel_runtime(globals())


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditAlignment", CmdV1AlignmentEditor())

"""Applied Sections generation command for CorridorRoad v1."""

from __future__ import annotations

import math

try:
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None
    Part = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtWidgets

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ..models.source.override_model import OverrideModel
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_applied_section import (
    create_or_update_v1_applied_section_set_object,
    find_v1_applied_section_set,
    to_applied_section_set,
)
from ..objects.obj_assembly import find_v1_assembly_model, list_v1_assembly_models, to_assembly_model
from ..objects.obj_profile import find_v1_profile, to_profile_model
from ..objects.obj_region import find_v1_region_model, to_region_model
from ..objects.obj_stationing import find_v1_stationing
from ..services.builders import AppliedSectionSetBuildRequest, AppliedSectionSetService


def build_document_applied_section_set(document=None, *, project=None, corridor_id: str = "corridor:main"):
    """Build an AppliedSectionSet result from the active v1 source objects."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    alignment_obj = find_v1_alignment(doc)
    profile_obj = find_v1_profile(doc)
    assembly_objs = list_v1_assembly_models(doc)
    assembly_obj = assembly_objs[0] if assembly_objs else find_v1_assembly_model(doc)
    region_obj = find_v1_region_model(doc)
    stationing_obj = find_v1_stationing(doc)

    alignment = to_alignment_model(alignment_obj)
    profile = to_profile_model(profile_obj)
    assembly_models = [model for model in (to_assembly_model(obj) for obj in assembly_objs) if model is not None]
    assembly = assembly_models[0] if assembly_models else to_assembly_model(assembly_obj)
    region_model = to_region_model(region_obj)
    stations = _station_values(stationing_obj)

    missing = []
    if alignment is None:
        missing.append("Alignment")
    if profile is None:
        missing.append("Profile")
    if assembly is None:
        missing.append("Assembly")
    if region_model is None:
        missing.append("Regions")
    if not stations:
        missing.append("Stations")
    if missing:
        raise RuntimeError("Required v1 sources are missing: " + ", ".join(missing))

    project_id = _project_id(project or find_project(doc))
    override_model = OverrideModel(
        schema_version=1,
        project_id=project_id,
        override_model_id="overrides:empty",
        alignment_id=alignment.alignment_id,
    )
    return AppliedSectionSetService().build(
        AppliedSectionSetBuildRequest(
            project_id=project_id,
            corridor_id=corridor_id,
            alignment=alignment,
            profile=profile,
            assembly=assembly,
            assembly_models=assembly_models,
            region_model=region_model,
            override_model=override_model,
            stations=stations,
            applied_section_set_id="applied-sections:main",
        )
    )


def apply_v1_applied_section_set(
    *,
    document=None,
    project=None,
    applied_section_set=None,
):
    """Persist a v1 AppliedSectionSet result object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    if prj is None:
        try:
            prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
        except Exception:
            prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        prj.Label = "CorridorRoad Project"
    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    if applied_section_set is None:
        applied_section_set = build_document_applied_section_set(doc, project=prj)
    obj = create_or_update_v1_applied_section_set_object(
        document=doc,
        project=prj,
        applied_section_set=applied_section_set,
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def applied_section_review_rows(applied_section_set) -> list[dict[str, object]]:
    """Return compact station-wise review rows for an AppliedSectionSet."""

    station_rows = list(getattr(applied_section_set, "station_rows", []) or [])
    sections = list(getattr(applied_section_set, "sections", []) or [])
    section_by_id = {str(getattr(section, "applied_section_id", "") or ""): section for section in sections}
    output: list[dict[str, object]] = []
    for station_row in station_rows:
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        frame = getattr(section, "frame", None) if section is not None else None
        diagnostic_count = len(list(getattr(section, "diagnostic_rows", []) or [])) if section is not None else 1
        component_count = len(list(getattr(section, "component_rows", []) or [])) if section is not None else 0
        output.append(
            {
                "station": float(getattr(station_row, "station", 0.0) or 0.0),
                "applied_section_id": section_id,
                "x": float(getattr(frame, "x", 0.0) or 0.0),
                "y": float(getattr(frame, "y", 0.0) or 0.0),
                "z": float(getattr(frame, "z", 0.0) or 0.0),
                "region_id": str(getattr(section, "region_id", "") or "") if section is not None else "",
                "assembly_id": str(getattr(section, "assembly_id", "") or "") if section is not None else "",
                "template_id": str(getattr(section, "template_id", "") or "") if section is not None else "",
                "surface_left_width": float(getattr(section, "surface_left_width", 0.0) or 0.0) if section is not None else 0.0,
                "surface_right_width": float(getattr(section, "surface_right_width", 0.0) or 0.0) if section is not None else 0.0,
                "subgrade_depth": float(getattr(section, "subgrade_depth", 0.0) or 0.0) if section is not None else 0.0,
                "daylight_left_width": float(getattr(section, "daylight_left_width", 0.0) or 0.0) if section is not None else 0.0,
                "daylight_right_width": float(getattr(section, "daylight_right_width", 0.0) or 0.0) if section is not None else 0.0,
                "component_count": component_count,
                "diagnostic_count": diagnostic_count,
                "status": "warn" if diagnostic_count else "ok",
            }
        )
    return output


def show_applied_section_preview_object(document, applied_section_set, row_index: int):
    """Create or update a 3D preview line for one AppliedSection row."""

    if document is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Applied Section preview.")
    station_rows = list(getattr(applied_section_set, "station_rows", []) or [])
    if row_index < 0 or row_index >= len(station_rows):
        raise IndexError("Applied Section row index is out of range.")
    section_by_id = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    station_row = station_rows[row_index]
    section = section_by_id.get(str(getattr(station_row, "applied_section_id", "") or ""))
    if section is None:
        raise ValueError("Applied Section row has no matching section result.")
    shape = applied_section_preview_shape(section)
    obj = document.getObject("V1AppliedSectionShowPreview")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1AppliedSectionShowPreview")
    station = float(getattr(section, "station", getattr(station_row, "station", 0.0)) or 0.0)
    obj.Label = f"Applied Section Preview - STA {station:.3f}"
    obj.Shape = shape
    _set_preview_string_property(obj, "CRRecordKind", "v1_applied_section_show_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1AppliedSectionShowPreview")
    _set_preview_string_property(obj, "AppliedSectionId", str(getattr(section, "applied_section_id", "") or ""))
    _set_preview_string_property(obj, "RegionId", str(getattr(section, "region_id", "") or ""))
    _set_preview_string_property(obj, "AssemblyId", str(getattr(section, "assembly_id", "") or ""))
    _set_preview_string_property(obj, "TemplateId", str(getattr(section, "template_id", "") or ""))
    _set_preview_string_property(obj, "PreviewMode", _applied_section_preview_mode(section))
    _set_preview_integer_property(obj, "PreviewPointCount", _applied_section_preview_point_count(section))
    _set_preview_float_property(obj, "Station", station)
    _style_applied_section_preview_object(obj)
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(find_project(document), obj)
    except Exception:
        pass
    try:
        document.recompute()
    except Exception:
        pass
    return obj


def applied_section_preview_shape(section):
    """Build a visible 3D cross-section preview from one AppliedSection result."""

    if App is None or Part is None:
        return None
    frame = getattr(section, "frame", None)
    if frame is None:
        raise ValueError("Applied Section preview requires a station frame.")
    polylines = _applied_section_preview_polylines(section, frame)
    all_points = [point for _role, points in polylines for point in points]
    stroke_width = _applied_section_stroke_width(all_points)
    shapes = []
    for _role, points in polylines:
        for start, end in zip(points, points[1:]):
            try:
                if (end - start).Length <= 1.0e-9:
                    continue
                stroke = _make_applied_section_segment_stroke(start, end, stroke_width)
                shapes.append(stroke if stroke is not None else Part.makeLine(start, end))
            except Exception:
                pass
    return Part.Compound(shapes) if shapes else Part.Shape()


def run_v1_applied_sections_command():
    """Open the v1 Applied Sections generation panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    panel = V1AppliedSectionsTaskPanel(document=App.ActiveDocument)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_applied_section_set(App.ActiveDocument)


class V1AppliedSectionsTaskPanel:
    """Small Apply-gated panel for building AppliedSectionSet results."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.form = self._build_ui()
        self._refresh_summary()

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
        widget.setWindowTitle("CorridorRoad v1 - Applied Sections")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Applied Sections")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel(
            "Build station-by-station AppliedSection results from Alignment, Profile, Stations, Assembly, and Regions. "
            "This does not generate corridor solids."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self._summary = QtWidgets.QPlainTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setFixedHeight(160)
        layout.addWidget(self._summary)

        self._review_table = QtWidgets.QTableWidget(0, 10)
        self._review_table.setHorizontalHeaderLabels(
            [
                "STA",
                "X",
                "Y",
                "Z",
                "Region",
                "Assembly",
                "Template",
                "L/R Width",
                "Components",
                "Status",
            ]
        )
        self._review_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._review_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._review_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        try:
            self._review_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._review_table.cellDoubleClicked.connect(lambda row, _col: self._show_review_row(row))
        layout.addWidget(self._review_table, 1)

        action_row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_summary)
        action_row.addWidget(refresh_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        action_row.addWidget(apply_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        return widget

    def _refresh_summary(self) -> None:
        try:
            station_count = len(_station_values(find_v1_stationing(self.document)))
            lines = [
                f"Alignment: {_source_status(find_v1_alignment(self.document))}",
                f"Profile: {_source_status(find_v1_profile(self.document))}",
                f"Assembly: {_assembly_source_status(self.document)}",
                f"Regions: {_source_status(find_v1_region_model(self.document))}",
                f"Stations: {station_count} row(s)",
                "",
                "Click Apply to create or update the v1 AppliedSectionSet result.",
            ]
            existing = to_applied_section_set(find_v1_applied_section_set(self.document))
            if existing is not None:
                review_rows = applied_section_review_rows(existing)
                lines.extend(
                    [
                        "",
                        f"Existing Applied Sections: {len(review_rows)} row(s)",
                        f"Existing diagnostics: {sum(int(row.get('diagnostic_count', 0) or 0) for row in review_rows)}",
                    ]
                )
                self._set_review_rows(review_rows)
            else:
                self._set_review_rows([])
            self._summary.setPlainText("\n".join(lines))
        except Exception as exc:
            self._summary.setPlainText(f"Summary failed:\n{exc}")
            self._set_review_rows([])

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            result = build_document_applied_section_set(self.document)
            obj = apply_v1_applied_section_set(document=self.document, applied_section_set=result)
            diagnostic_count = sum(len(section.diagnostic_rows) for section in result.sections)
            message = f"Applied Sections have been built.\nStations: {len(result.station_rows)}\nDiagnostics: {diagnostic_count}"
            self._summary.setPlainText(message + f"\nObject: {obj.Label}")
            self._set_review_rows(applied_section_review_rows(result))
            _show_message(self.form, "Applied Sections", message)
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._summary.setPlainText(f"Applied Sections were not built:\n{exc}")
            _show_message(self.form, "Applied Sections", f"Applied Sections were not built.\n{exc}")
            return False

    def _set_review_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_review_table"):
            return
        self._review_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._review_table.rowCount()
            self._review_table.insertRow(row_index)
            values = [
                _format_float(row.get("station", 0.0)),
                _format_float(row.get("x", 0.0)),
                _format_float(row.get("y", 0.0)),
                _format_float(row.get("z", 0.0)),
                str(row.get("region_id", "") or ""),
                str(row.get("assembly_id", "") or ""),
                str(row.get("template_id", "") or ""),
                f"{_format_float(row.get('surface_left_width', 0.0))} / {_format_float(row.get('surface_right_width', 0.0))}",
                str(int(row.get("component_count", 0) or 0)),
                _review_status_text(row),
            ]
            for col, value in enumerate(values):
                self._review_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(str(value)))

    def _show_review_row(self, row_index: int) -> None:
        try:
            applied = to_applied_section_set(find_v1_applied_section_set(self.document))
            if applied is None:
                applied = build_document_applied_section_set(self.document)
            preview = show_applied_section_preview_object(self.document, applied, int(row_index))
            if Gui is not None:
                try:
                    Gui.Selection.clearSelection()
                    Gui.Selection.addSelection(preview)
                except Exception:
                    pass
                _fit_selected_preview()
            station = float(getattr(preview, "Station", 0.0) or 0.0)
            self._summary.setPlainText(
                f"Applied Section preview shown.\nSTA: {station:.3f}\nObject: {preview.Label}\n\nDouble-click another row to inspect it."
            )
        except Exception as exc:
            self._summary.setPlainText(f"Applied Section preview was not shown:\n{exc}")
            _show_message(self.form, "Applied Sections", f"Applied Section preview was not shown.\n{exc}")


class CmdV1AppliedSections:
    """Build v1 AppliedSectionSet results."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("sections.svg"),
            "MenuText": "Applied Sections",
            "ToolTip": "Build v1 AppliedSectionSet results from alignment, profile, stations, assembly, and regions",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_applied_sections_command()


def _station_values(stationing_obj) -> list[float]:
    values = []
    for value in list(getattr(stationing_obj, "StationValues", []) or []):
        try:
            values.append(float(value))
        except Exception:
            pass
    return values


def _source_status(obj) -> str:
    if obj is None:
        return "missing"
    return str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "ok")


def _assembly_source_status(document) -> str:
    objs = list_v1_assembly_models(document)
    if not objs:
        return "missing"
    if len(objs) == 1:
        return _source_status(objs[0])
    return f"{len(objs)} assembly model(s)"


def _review_status_text(row: dict[str, object]) -> str:
    diagnostics = int(row.get("diagnostic_count", 0) or 0)
    if diagnostics:
        return f"WARN ({diagnostics})"
    return "OK"


def _applied_section_preview_polylines(section, frame):
    fg_points = _applied_section_point_role_vectors(section, "fg_surface")
    subgrade_points = _applied_section_point_role_vectors(section, "subgrade_surface")
    polylines = []
    if len(fg_points) >= 2:
        polylines.append(("fg_surface", fg_points))
    if len(subgrade_points) >= 2:
        polylines.append(("subgrade_surface", subgrade_points))
        for fg_point, subgrade_point in _matched_offset_point_pairs(section, "fg_surface", "subgrade_surface"):
            polylines.append(("subgrade_link", [fg_point, subgrade_point]))
    if fg_points:
        polylines.extend(_applied_section_daylight_polylines(section, frame, fg_points))
    if polylines:
        return polylines
    return [("fallback_section", _applied_section_preview_points(section, frame))]


def _applied_section_point_role_vectors(section, point_role: str):
    rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == point_role
    ]
    rows.sort(key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
    vectors = []
    for point in rows:
        try:
            vectors.append(App.Vector(float(point.x), float(point.y), float(point.z)))
        except Exception:
            pass
    return _unique_preview_points(vectors)


def _matched_offset_point_pairs(section, first_role: str, second_role: str):
    first = {
        round(float(getattr(point, "lateral_offset", 0.0) or 0.0), 6): point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == first_role
    }
    second = {
        round(float(getattr(point, "lateral_offset", 0.0) or 0.0), 6): point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == second_role
    }
    pairs = []
    for offset in sorted(set(first).intersection(second)):
        try:
            a = first[offset]
            b = second[offset]
            pairs.append((App.Vector(float(a.x), float(a.y), float(a.z)), App.Vector(float(b.x), float(b.y), float(b.z))))
        except Exception:
            pass
    return pairs


def _applied_section_daylight_polylines(section, frame, fg_points):
    if not fg_points:
        return []
    tangent = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal = App.Vector(-math.sin(tangent), math.cos(tangent), 0.0)
    left_daylight = max(float(getattr(section, "daylight_left_width", 0.0) or 0.0), 0.0)
    right_daylight = max(float(getattr(section, "daylight_right_width", 0.0) or 0.0), 0.0)
    left_slope = float(getattr(section, "daylight_left_slope", 0.0) or 0.0)
    right_slope = float(getattr(section, "daylight_right_slope", 0.0) or 0.0)
    polylines = []
    if left_daylight > 0.0:
        left_edge = fg_points[-1]
        polylines.append(("left_slope_face", [left_edge, left_edge + normal * left_daylight + App.Vector(0.0, 0.0, left_slope * left_daylight)]))
    if right_daylight > 0.0:
        right_edge = fg_points[0]
        polylines.append(("right_slope_face", [right_edge, right_edge - normal * right_daylight + App.Vector(0.0, 0.0, right_slope * right_daylight)]))
    return polylines


def _applied_section_preview_points(section, frame):
    x = float(getattr(frame, "x", 0.0) or 0.0)
    y = float(getattr(frame, "y", 0.0) or 0.0)
    z = float(getattr(frame, "z", 0.0) or 0.0)
    tangent = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(tangent)
    normal_y = math.cos(tangent)
    left_width = max(float(getattr(section, "surface_left_width", 0.0) or 0.0), 0.0)
    right_width = max(float(getattr(section, "surface_right_width", 0.0) or 0.0), 0.0)
    left_daylight = max(float(getattr(section, "daylight_left_width", 0.0) or 0.0), 0.0)
    right_daylight = max(float(getattr(section, "daylight_right_width", 0.0) or 0.0), 0.0)
    left_slope = float(getattr(section, "daylight_left_slope", 0.0) or 0.0)
    right_slope = float(getattr(section, "daylight_right_slope", 0.0) or 0.0)
    offsets = [
        (left_width + left_daylight, z + left_slope * left_daylight),
        (left_width, z),
        (0.0, z),
        (-right_width, z),
        (-(right_width + right_daylight), z + right_slope * right_daylight),
    ]
    points = []
    for offset, elevation in offsets:
        points.append(App.Vector(x + normal_x * offset, y + normal_y * offset, elevation))
    return _unique_preview_points(points)


def _applied_section_preview_mode(section) -> str:
    point_count = _applied_section_preview_point_count(section)
    return "section_points" if point_count else "width_fallback"


def _applied_section_preview_point_count(section) -> int:
    return len(
        [
            point
            for point in list(getattr(section, "point_rows", []) or [])
            if str(getattr(point, "point_role", "") or "") in {"fg_surface", "subgrade_surface"}
        ]
    )


def _unique_preview_points(points):
    output = []
    for point in list(points or []):
        if output and _same_preview_point(output[-1], point):
            continue
        output.append(point)
    return output


def _same_preview_point(left, right, tolerance: float = 1.0e-7) -> bool:
    try:
        return (
            abs(float(left.x) - float(right.x)) <= tolerance
            and abs(float(left.y) - float(right.y)) <= tolerance
            and abs(float(left.z) - float(right.z)) <= tolerance
        )
    except Exception:
        return False


def _applied_section_stroke_width(points) -> float:
    if not points:
        return 0.1
    xs = [float(point.x) for point in points]
    ys = [float(point.y) for point in points]
    zs = [float(point.z) for point in points]
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1.0)
    return max(0.08, min(0.35, span * 0.015))


def _make_applied_section_segment_stroke(start, end, stroke_width: float):
    width = float(stroke_width or 0.0)
    if width <= 0.0 or Part is None:
        return None
    try:
        direction = end - start
        if direction.Length <= 1.0e-9:
            return None
        tangent = App.Vector(direction)
        tangent.normalize()
        up = App.Vector(0.0, 0.0, 1.0)
        normal = tangent.cross(up)
        if normal.Length <= 1.0e-9:
            normal = App.Vector(1.0, 0.0, 0.0)
        normal.normalize()
        normal = normal * (width * 0.5)
        points = [
            start + normal,
            end + normal,
            end - normal,
            start - normal,
            start + normal,
        ]
        face = Part.Face(Part.makePolygon(points))
        return face.extrude(App.Vector(0.0, 0.0, max(0.04, width * 0.2)))
    except Exception:
        return None


def _style_applied_section_preview_object(obj) -> None:
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return
    try:
        vobj.Visibility = True
        vobj.DisplayMode = "Flat Lines"
        vobj.ShapeColor = (1.0, 0.36, 0.08)
        vobj.LineColor = (1.0, 0.36, 0.08)
        vobj.PointColor = (1.0, 0.36, 0.08)
        vobj.LineWidth = 7.0
        vobj.PointSize = 9.0
        if hasattr(vobj, "DrawStyle"):
            vobj.DrawStyle = "Solid"
        if hasattr(vobj, "Lighting"):
            try:
                vobj.Lighting = "Two side"
            except Exception:
                pass
        if hasattr(vobj, "Transparency"):
            vobj.Transparency = 0
    except Exception:
        pass


def _set_preview_string_property(obj, name: str, value: str) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_preview_float_property(obj, name: str, value: float) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyFloat", name, "CorridorRoad", name)
        setattr(obj, name, float(value or 0.0))
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyInteger", name, "CorridorRoad", name)
        setattr(obj, name, int(value or 0))
    except Exception:
        pass


def _fit_selected_preview() -> None:
    if Gui is None:
        return
    try:
        if hasattr(Gui, "updateGui"):
            Gui.updateGui()
    except Exception:
        pass
    try:
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


def _format_float(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1AppliedSections", CmdV1AppliedSections())

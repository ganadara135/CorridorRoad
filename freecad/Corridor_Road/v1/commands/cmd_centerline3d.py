"""3D Centerline review command for Parametric Road v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None
    Part = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.objects.obj_project import ensure_project_tree, find_project, route_to_v1_tree
from freecad.Corridor_Road.qt_compat import QtWidgets

from ..models.result.centerline3d import Centerline3DResult
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_profile import find_v1_profile, to_profile_model
from ..objects.obj_stationing import find_v1_stationing
from ..services.evaluation import Centerline3DEvaluationRequest, Centerline3DEvaluationService


CENTERLINE3D_COMMAND_ID = "CorridorRoad_V1Centerline3D"


def build_document_centerline3d_result(document=None) -> Centerline3DResult:
    """Evaluate the current document 3D Centerline review result."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    alignment_obj = find_v1_alignment(doc)
    profile_obj = find_v1_profile(doc)
    stationing_obj = find_v1_stationing(doc)
    project = find_project(doc)
    source_refs = [
        str(getattr(alignment_obj, "Name", "") or ""),
        str(getattr(profile_obj, "Name", "") or ""),
        str(getattr(stationing_obj, "Name", "") or ""),
    ]
    return Centerline3DEvaluationService().evaluate(
        Centerline3DEvaluationRequest(
            project_id=str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1"),
            alignment_model=to_alignment_model(alignment_obj),
            profile_model=to_profile_model(profile_obj),
            station_values=tuple(float(value) for value in list(getattr(stationing_obj, "StationValues", []) or [])),
            stationing_id=str(getattr(stationing_obj, "StationingId", "") or ""),
            source_refs=tuple(value for value in source_refs if value),
        )
    )


def show_v1_centerline3d_preview_object(
    document=None,
    *,
    result: Centerline3DResult | None = None,
    project=None,
    show_station_markers: bool = False,
):
    """Create or update the 3D Centerline review preview object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for 3D Centerline preview.")
    active_result = result or build_document_centerline3d_result(doc)
    points = [App.Vector(float(row.x), float(row.y), float(row.z)) for row in list(active_result.point_rows or ())]
    if len(points) < 2:
        raise RuntimeError("3D Centerline preview requires at least two evaluated points.")
    shape, curve_kind = _make_centerline3d_curve_shape(points)
    obj = doc.getObject("V1Centerline3DPreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1Centerline3DPreview")
    obj.Label = "3D Centerline"
    obj.Shape = shape
    _set_string(obj, "CRRecordKind", "v1_centerline3d_review")
    _set_string(obj, "V1ObjectType", "V1Centerline3DReview")
    _set_string(obj, "Centerline3DResultId", str(active_result.centerline3d_result_id or "centerline3d:main"))
    _set_string(obj, "CurveKind", curve_kind)
    _set_string(obj, "AlignmentId", str(active_result.alignment_id or ""))
    _set_string(obj, "ProfileId", str(active_result.profile_id or ""))
    _set_string(obj, "StationingId", str(active_result.stationing_id or ""))
    _set_string(obj, "ReviewStatus", str(active_result.status or "empty"))
    _set_integer(obj, "PointCount", int(active_result.point_count))
    _set_float(obj, "StationStart", float(active_result.station_start))
    _set_float(obj, "StationEnd", float(active_result.station_end))
    _set_float(obj, "ElevationMin", float(active_result.elevation_min))
    _set_float(obj, "ElevationMax", float(active_result.elevation_max))
    _set_string_list(obj, "DiagnosticRows", list(active_result.diagnostic_rows or ()))
    _style_centerline3d_preview(obj)
    try:
        prj = project or find_project(doc)
        ensure_project_tree(prj, include_references=False)
        route_to_v1_tree(prj, obj)
    except Exception:
        pass
    if show_station_markers:
        show_v1_centerline3d_station_markers(doc, result=active_result, project=project, visible=True)
    else:
        set_v1_centerline3d_station_markers_visible(doc, False)
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def show_v1_centerline3d_station_markers(
    document=None,
    *,
    result: Centerline3DResult | None = None,
    project=None,
    visible: bool = True,
):
    """Create or update optional station markers for the 3D Centerline review object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for 3D Centerline station markers.")
    active_result = result or build_document_centerline3d_result(doc)
    points = [App.Vector(float(row.x), float(row.y), float(row.z)) for row in list(active_result.point_rows or ())]
    if not points:
        raise RuntimeError("3D Centerline station markers require at least one evaluated point.")
    radius = _station_marker_radius(points)
    shapes = [_make_station_marker_shape(point, radius) for point in points]
    shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
    obj = doc.getObject("V1Centerline3DStationMarkers")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1Centerline3DStationMarkers")
    obj.Label = "3D Centerline Stations"
    obj.Shape = shape
    _set_string(obj, "CRRecordKind", "v1_centerline3d_station_markers")
    _set_string(obj, "V1ObjectType", "V1Centerline3DStationMarkers")
    _set_string(obj, "Centerline3DResultId", str(active_result.centerline3d_result_id or "centerline3d:main"))
    _set_integer(obj, "MarkerCount", len(points))
    _set_string_list(obj, "StationLabels", [f"STA {float(row.station):.3f}" for row in list(active_result.point_rows or ())])
    _style_centerline3d_station_markers(obj, visible=visible)
    try:
        prj = project or find_project(doc)
        ensure_project_tree(prj, include_references=False)
        route_to_v1_tree(prj, obj)
    except Exception:
        pass
    return obj


def set_v1_centerline3d_station_markers_visible(document=None, visible: bool = False):
    """Set optional 3D Centerline station marker visibility."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    obj = doc.getObject("V1Centerline3DStationMarkers") if doc is not None else None
    if obj is None:
        return None
    try:
        obj.ViewObject.Visibility = bool(visible)
    except Exception:
        pass
    return obj


def run_v1_centerline3d_command():
    """Open the 3D Centerline review panel."""

    panel = V1Centerline3DTaskPanel()
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


class V1Centerline3DTaskPanel:
    """Read-only task panel for the shared 3D Centerline baseline."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self._result = build_document_centerline3d_result(self.document) if self.document is not None else Centerline3DResult(status="blocked")
        self._preview_object = None
        self.form = self._build_ui()
        self._refresh_ui()

    def getStandardButtons(self):
        return 0

    def reject(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("Parametric Road v1 - 3D Centerline")
        layout = QtWidgets.QVBoxLayout(widget)
        title = QtWidgets.QLabel("3D Centerline")
        try:
            font = title.font()
            font.setPointSize(font.pointSize() + 2)
            font.setBold(True)
            title.setFont(font)
        except Exception:
            pass
        layout.addWidget(title)
        note = QtWidgets.QLabel("Review the shared station/offset/elevation baseline before Structures, Drainage, Applied Sections, and Build Corridor.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self._summary_table = QtWidgets.QTableWidget(0, 2)
        self._summary_table.setHorizontalHeaderLabels(["Item", "Value"])
        self._summary_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self._summary_table)
        self._diagnostics = QtWidgets.QPlainTextEdit()
        self._diagnostics.setReadOnly(True)
        self._diagnostics.setMinimumHeight(90)
        layout.addWidget(self._diagnostics)
        self._show_station_markers = QtWidgets.QCheckBox("Show Stations")
        self._show_station_markers.setToolTip("Show or hide station markers on the 3D Centerline.")
        self._show_station_markers.stateChanged.connect(self._toggle_station_markers)
        layout.addWidget(self._show_station_markers)
        buttons = QtWidgets.QHBoxLayout()
        refresh = QtWidgets.QPushButton("Refresh")
        refresh.clicked.connect(self._refresh)
        buttons.addWidget(refresh)
        show = QtWidgets.QPushButton("Show")
        show.clicked.connect(self._show)
        buttons.addWidget(show)
        hide = QtWidgets.QPushButton("Hide")
        hide.clicked.connect(self._hide)
        buttons.addWidget(hide)
        focus = QtWidgets.QPushButton("Focus")
        focus.clicked.connect(self._focus)
        buttons.addWidget(focus)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.reject)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        return widget

    def _refresh(self) -> None:
        self._result = build_document_centerline3d_result(self.document)
        self._refresh_ui()

    def _show(self) -> None:
        try:
            self._preview_object = show_v1_centerline3d_preview_object(
                self.document,
                result=self._result,
                show_station_markers=self._show_stations_enabled(),
            )
            self._focus()
            self._refresh_ui(
                message=(
                    "3D Centerline has been generated. "
                    f"Preview object: {str(getattr(self._preview_object, 'Name', '') or 'V1Centerline3DPreview')}; "
                    f"points={int(getattr(self._result, 'point_count', 0) or 0)}."
                )
            )
        except Exception as exc:
            self._diagnostics.setPlainText(f"3D Centerline preview was not shown:\n{exc}")

    def _hide(self) -> None:
        obj = self._preview_object or (self.document.getObject("V1Centerline3DPreview") if self.document is not None else None)
        try:
            obj.ViewObject.Visibility = False
        except Exception:
            pass
        set_v1_centerline3d_station_markers_visible(self.document, False)

    def _toggle_station_markers(self) -> None:
        if self.document is None:
            return
        if self._show_stations_enabled():
            try:
                marker_obj = show_v1_centerline3d_station_markers(self.document, result=self._result, visible=True)
                self._refresh_ui(message=f"3D Centerline station markers are shown. Markers: {int(getattr(marker_obj, 'MarkerCount', 0) or 0)}.")
            except Exception as exc:
                self._diagnostics.setPlainText(f"3D Centerline station markers were not shown:\n{exc}")
        else:
            set_v1_centerline3d_station_markers_visible(self.document, False)
            self._refresh_ui(message="3D Centerline station markers are hidden.")

    def _focus(self) -> None:
        obj = self._preview_object or (self.document.getObject("V1Centerline3DPreview") if self.document is not None else None)
        if obj is None or Gui is None:
            return
        try:
            vobj = getattr(obj, "ViewObject", None)
            if vobj is not None:
                vobj.Visibility = True
        except Exception:
            pass
        try:
            if hasattr(Gui, "updateGui"):
                Gui.updateGui()
        except Exception:
            pass
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(obj)
        except Exception:
            pass
        try:
            view = getattr(getattr(Gui, "ActiveDocument", None), "ActiveView", None)
            if view is not None and hasattr(view, "fitSelection"):
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

    def _refresh_ui(self, *, message: str = "") -> None:
        result = self._result
        rows = [
            ("Status", str(result.status or "")),
            ("Points", str(result.point_count)),
            ("Station Range", f"{result.station_start:.3f} - {result.station_end:.3f}" if result.point_count else "-"),
            ("Elevation Range", f"{result.elevation_min:.3f} - {result.elevation_max:.3f}" if result.point_count else "-"),
            ("Alignment", str(result.alignment_id or "-")),
            ("Profile", str(result.profile_id or "-")),
            ("Stationing", str(result.stationing_id or "-")),
        ]
        self._summary_table.setRowCount(len(rows))
        for row_index, (label, value) in enumerate(rows):
            self._summary_table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(label))
            self._summary_table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(value))
        try:
            self._summary_table.resizeColumnsToContents()
            self._summary_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        diagnostic_text = "\n".join(list(result.diagnostic_rows or ())) or "No diagnostics."
        if str(message or "").strip():
            diagnostic_text = f"{str(message).strip()}\n\n{diagnostic_text}"
        self._diagnostics.setPlainText(diagnostic_text)

    def _show_stations_enabled(self) -> bool:
        try:
            return bool(self._show_station_markers.isChecked())
        except Exception:
            return False


class CmdV1Centerline3D:
    """FreeCAD command wrapper for 3D Centerline review."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("centerline3d.svg"),
            "MenuText": "3D Centerline",
            "ToolTip": "Review the shared 3D Alignment/Profile centerline baseline",
        }

    def Activated(self):
        return run_v1_centerline3d_command()

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None


def _style_centerline3d_preview(obj) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = True
        vobj.LineColor = (0.05, 1.0, 0.95)
        vobj.PointColor = (1.0, 0.95, 0.1)
        vobj.LineWidth = 5.0
        vobj.PointSize = 6.0
    except Exception:
        pass


def _style_centerline3d_station_markers(obj, *, visible: bool = True) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = bool(visible)
        vobj.ShapeColor = (1.0, 0.85, 0.05)
        vobj.LineColor = (0.05, 0.05, 0.02)
        vobj.PointColor = (1.0, 0.95, 0.1)
        vobj.LineWidth = 1.5
        vobj.PointSize = 8.0
        vobj.Transparency = 0
    except Exception:
        pass


def _make_centerline3d_curve_shape(points: list[object]):
    """Return a smooth centerline review curve, falling back to polyline if needed."""

    if len(points) >= 3:
        try:
            curve = Part.BSplineCurve()
            curve.interpolate(points)
            return curve.toShape(), "bspline_interpolation"
        except Exception:
            pass
    return Part.makePolygon(points), "polyline"


def _station_marker_radius(points: list[object]) -> float:
    xs = [float(point.x) for point in points]
    ys = [float(point.y) for point in points]
    zs = [float(point.z) for point in points]
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1.0)
    return max(0.15, min(span * 0.006, 1.5))


def _make_station_marker_shape(point, radius: float):
    """Return a high-contrast 3-axis station marker instead of a round point."""

    r = max(float(radius) * 0.16, 0.035)
    length = max(float(radius) * 3.0, 0.45)
    half = length * 0.5
    center = App.Vector(float(point.x), float(point.y), float(point.z))
    parts = []
    for direction in (
        App.Vector(1.0, 0.0, 0.0),
        App.Vector(0.0, 1.0, 0.0),
        App.Vector(0.0, 0.0, 1.0),
    ):
        try:
            parts.append(Part.makeCylinder(r, length, center - direction * half, direction))
        except Exception:
            pass
    if parts:
        return Part.makeCompound(parts) if len(parts) > 1 else parts[0]
    return Part.makeSphere(max(float(radius), 0.15), center)


def _set_string(obj, name: str, value: str) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyString", name, "3D Centerline", name)
        except Exception:
            pass
    try:
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_string_list(obj, name: str, values) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyStringList", name, "3D Centerline", name)
        except Exception:
            pass
    try:
        setattr(obj, name, [str(value) for value in list(values or [])])
    except Exception:
        pass


def _set_integer(obj, name: str, value: int) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyInteger", name, "3D Centerline", name)
        except Exception:
            pass
    try:
        setattr(obj, name, int(value or 0))
    except Exception:
        pass


def _set_float(obj, name: str, value: float) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyFloat", name, "3D Centerline", name)
        except Exception:
            pass
    try:
        setattr(obj, name, float(value or 0.0))
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand(CENTERLINE3D_COMMAND_ID, CmdV1Centerline3D())

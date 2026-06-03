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
    bundles = _centerline3d_source_bundles(doc)
    if len(bundles) > 1:
        return _build_multi_alignment_centerline3d_result(doc, bundles)
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


def _build_multi_alignment_centerline3d_result(document, bundles: list[dict[str, object]]) -> Centerline3DResult:
    project = find_project(document)
    project_id = str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")
    service = Centerline3DEvaluationService()
    point_rows = []
    diagnostics: list[str] = []
    source_refs: list[str] = []
    alignment_ids: list[str] = []
    profile_ids: list[str] = []
    stationing_ids: list[str] = []
    ready_count = 0
    for bundle in list(bundles or []):
        alignment = bundle.get("alignment")
        profile = bundle.get("profile")
        stationing_obj = bundle.get("stationing_obj")
        alignment_id = str(getattr(alignment, "alignment_id", "") or "").strip()
        if alignment_id:
            alignment_ids.append(alignment_id)
        profile_id = str(getattr(profile, "profile_id", "") or "").strip()
        if profile_id:
            profile_ids.append(profile_id)
        stationing_id = str(getattr(stationing_obj, "StationingId", "") or "").strip()
        if stationing_id:
            stationing_ids.append(stationing_id)
        result = service.evaluate(
            Centerline3DEvaluationRequest(
                project_id=project_id,
                alignment_model=alignment,
                profile_model=profile,
                station_values=tuple(float(value) for value in list(getattr(stationing_obj, "StationValues", []) or [])),
                stationing_id=stationing_id,
                source_refs=tuple(
                    value
                    for value in (
                        str(getattr(bundle.get("alignment_obj"), "Name", "") or ""),
                        str(getattr(bundle.get("profile_obj"), "Name", "") or ""),
                        str(getattr(stationing_obj, "Name", "") or ""),
                    )
                    if value
                ),
            )
        )
        if str(getattr(result, "status", "") or "") == "ready":
            ready_count += 1
        point_rows.extend(list(getattr(result, "point_rows", ()) or ()))
        diagnostics.extend(
            f"{alignment_id or 'alignment'}|{row}"
            for row in list(getattr(result, "diagnostic_rows", ()) or ())
        )
        source_refs.extend(list(getattr(result, "source_refs", ()) or ()))
    status = "ready" if ready_count > 0 and len(point_rows) >= 2 else "blocked"
    if ready_count < len(bundles):
        diagnostics.append(f"warning|partial_centerline3d_bundle_count|centerline3d:multiple|Ready bundles: {ready_count}/{len(bundles)}.")
    return Centerline3DResult(
        project_id=project_id,
        centerline3d_result_id="centerline3d:multiple",
        alignment_id="alignment:multiple",
        profile_id="profile:multiple" if len(_unique_text(profile_ids)) > 1 else (_unique_text(profile_ids)[0] if profile_ids else ""),
        stationing_id="stationing:multiple" if len(_unique_text(stationing_ids)) > 1 else (_unique_text(stationing_ids)[0] if stationing_ids else ""),
        point_rows=tuple(point_rows),
        diagnostic_rows=tuple(diagnostics),
        status=status,
        source_refs=tuple(_unique_text(source_refs)),
    )


def show_v1_centerline3d_preview_object(
    document=None,
    *,
    result: Centerline3DResult | None = None,
    project=None,
    show_station_markers: bool = False,
    display_mode: str = "smooth_curve",
):
    """Create or update the 3D Centerline review preview object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for 3D Centerline preview.")
    active_result = result or build_document_centerline3d_result(doc)
    point_groups = _centerline3d_preview_point_groups(active_result)
    if sum(len(points) for points in point_groups) < 2:
        raise RuntimeError("3D Centerline preview requires at least two evaluated points.")
    shape, curve_kind = _make_centerline3d_compound_curve_shape(point_groups, display_mode=display_mode)
    obj = doc.getObject("V1Centerline3DPreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1Centerline3DPreview")
    obj.Label = "3D Centerline"
    obj.Shape = shape
    _set_string(obj, "CRRecordKind", "v1_centerline3d_review")
    _set_string(obj, "V1ObjectType", "V1Centerline3DReview")
    _set_string(obj, "Centerline3DResultId", str(active_result.centerline3d_result_id or "centerline3d:main"))
    _set_string(obj, "CurveKind", curve_kind)
    _set_string(obj, "CenterlineDisplayMode", _normalized_display_mode(display_mode))
    _set_string(obj, "AlignmentId", str(active_result.alignment_id or ""))
    _set_string_list(obj, "AlignmentIds", _centerline3d_alignment_ids(active_result))
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
        display_row = QtWidgets.QHBoxLayout()
        display_row.addWidget(QtWidgets.QLabel("Display"))
        self._display_mode_combo = QtWidgets.QComboBox()
        self._display_mode_combo.addItems(["Smooth Curve", "Polyline"])
        self._display_mode_combo.setCurrentText("Smooth Curve")
        self._display_mode_combo.setToolTip("Choose how the 3D Centerline preview is drawn. This does not change station/frame calculations.")
        display_row.addWidget(self._display_mode_combo)
        display_row.addStretch(1)
        layout.addLayout(display_row)
        buttons = QtWidgets.QHBoxLayout()
        show = QtWidgets.QPushButton("Show")
        show.clicked.connect(self._show)
        buttons.addWidget(show)
        hide = QtWidgets.QPushButton("Hide")
        hide.clicked.connect(self._hide)
        buttons.addWidget(hide)
        focus = QtWidgets.QPushButton("Focus")
        focus.clicked.connect(self._focus)
        buttons.addWidget(focus)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(self._apply)
        buttons.addWidget(apply_button)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.reject)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        return widget

    def _apply(self) -> None:
        self._result = build_document_centerline3d_result(self.document)
        self._show()

    def _show(self) -> None:
        try:
            self._preview_object = show_v1_centerline3d_preview_object(
                self.document,
                result=self._result,
                show_station_markers=self._show_stations_enabled(),
                display_mode=self._selected_display_mode(),
            )
            self._focus()
            self._refresh_ui(
                message=(
                    "3D Centerline has been generated. "
                    f"Preview object: {str(getattr(self._preview_object, 'Name', '') or 'V1Centerline3DPreview')}; "
                    f"points={int(getattr(self._result, 'point_count', 0) or 0)}; "
                    f"display={_display_mode_label(getattr(self._preview_object, 'CenterlineDisplayMode', 'smooth_curve'))}."
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
            ("Display", _display_mode_label(self._selected_display_mode())),
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

    def _selected_display_mode(self) -> str:
        try:
            return _normalized_display_mode(str(self._display_mode_combo.currentText() or "Smooth Curve"))
        except Exception:
            return "smooth_curve"


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


def _centerline3d_source_bundles(document) -> list[dict[str, object]]:
    alignments = [(obj, to_alignment_model(obj)) for obj in list(getattr(document, "Objects", []) or [])]
    alignments = [(obj, model) for obj, model in alignments if model is not None]
    profiles = [(obj, to_profile_model(obj)) for obj in list(getattr(document, "Objects", []) or [])]
    profiles = [(obj, model) for obj, model in profiles if model is not None]
    stationings = [
        obj
        for obj in list(getattr(document, "Objects", []) or [])
        if str(getattr(obj, "V1ObjectType", "") or "") == "V1Stationing"
        or str(getattr(getattr(obj, "Proxy", None), "Type", "") or "") == "V1Stationing"
        or str(getattr(obj, "Name", "") or "").startswith("V1Stationing")
    ]
    output: list[dict[str, object]] = []
    for alignment_obj, alignment in alignments:
        alignment_id = str(getattr(alignment, "alignment_id", "") or getattr(alignment_obj, "AlignmentId", "") or "").strip()
        if not alignment_id:
            continue
        profile_obj, profile = _model_object_for_alignment(profiles, alignment_id)
        stationing_obj = _stationing_for_alignment(stationings, alignment_id)
        if profile is None or stationing_obj is None:
            continue
        output.append(
            {
                "alignment_obj": alignment_obj,
                "alignment": alignment,
                "profile_obj": profile_obj,
                "profile": profile,
                "stationing_obj": stationing_obj,
            }
        )
    return output


def _model_object_for_alignment(rows: list[tuple[object, object]], alignment_id: str):
    target = str(alignment_id or "").strip()
    fallback = (None, None)
    for obj, model in list(rows or []):
        model_alignment_id = str(getattr(model, "alignment_id", "") or "").strip()
        if fallback == (None, None) and not model_alignment_id:
            fallback = (obj, model)
        if model_alignment_id == target:
            return obj, model
    return fallback if len(rows) == 1 else (None, None)


def _stationing_for_alignment(rows: list[object], alignment_id: str):
    target = str(alignment_id or "").strip()
    fallback = None
    for obj in list(rows or []):
        obj_alignment_id = str(getattr(obj, "AlignmentId", "") or "").strip()
        if fallback is None and not obj_alignment_id:
            fallback = obj
        if obj_alignment_id == target:
            return obj
    return fallback if len(rows) == 1 else None


def _centerline3d_preview_point_groups(result: Centerline3DResult) -> list[list[object]]:
    groups: list[list[object]] = []
    group_by_alignment: dict[str, list[object]] = {}
    for row in list(getattr(result, "point_rows", ()) or ()):
        alignment_id = str(getattr(row, "source_alignment_ref", "") or getattr(result, "alignment_id", "") or "").strip()
        if not alignment_id:
            alignment_id = "__unassigned__"
        if alignment_id not in group_by_alignment:
            group_by_alignment[alignment_id] = []
            groups.append(group_by_alignment[alignment_id])
        group_by_alignment[alignment_id].append(App.Vector(float(row.x), float(row.y), float(row.z)))
    return [group for group in groups if group]


def _centerline3d_alignment_ids(result: Centerline3DResult) -> list[str]:
    values = [
        str(getattr(row, "source_alignment_ref", "") or "")
        for row in list(getattr(result, "point_rows", ()) or ())
        if str(getattr(row, "source_alignment_ref", "") or "")
    ]
    if not values and str(getattr(result, "alignment_id", "") or ""):
        values.append(str(getattr(result, "alignment_id", "") or ""))
    return _unique_text(values)


def _unique_text(values) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


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


def _make_centerline3d_curve_shape(points: list[object], *, display_mode: str = "smooth_curve"):
    """Return a smooth centerline review curve, falling back to polyline if needed."""

    cleaned = _clean_centerline_points(points)
    if len(cleaned) < 2:
        raise RuntimeError("3D Centerline preview requires at least two distinct evaluated points.")
    if _normalized_display_mode(display_mode) == "polyline":
        return Part.makePolygon(cleaned), "polyline"
    if len(cleaned) >= 3:
        try:
            curve = Part.BSplineCurve()
            curve.interpolate(cleaned)
            return curve.toShape(), "bspline_interpolation"
        except Exception:
            pass
        try:
            curve = Part.BSplineCurve()
            curve.approximate(cleaned)
            return curve.toShape(), "bspline_approximation"
        except Exception:
            pass
    return Part.makePolygon(cleaned), "polyline"


def _make_centerline3d_compound_curve_shape(point_groups: list[list[object]], *, display_mode: str = "smooth_curve"):
    shapes = []
    curve_kinds: list[str] = []
    for points in list(point_groups or []):
        if len(points) < 2:
            continue
        shape, curve_kind = _make_centerline3d_curve_shape(points, display_mode=display_mode)
        shapes.append(shape)
        curve_kinds.append(curve_kind)
    if not shapes:
        raise RuntimeError("3D Centerline preview requires at least two distinct evaluated points.")
    shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
    if len(set(curve_kinds)) == 1:
        return shape, curve_kinds[0]
    return shape, "compound"


def _clean_centerline_points(points: list[object]) -> list[object]:
    cleaned = []
    previous_key = None
    for point in list(points or []):
        key = (round(float(point.x), 9), round(float(point.y), 9), round(float(point.z), 9))
        if key == previous_key:
            continue
        cleaned.append(point)
        previous_key = key
    return cleaned


def _normalized_display_mode(value: str) -> str:
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if text in {"polyline", "line", "segmented"}:
        return "polyline"
    return "smooth_curve"


def _display_mode_label(value: str) -> str:
    return "Polyline" if _normalized_display_mode(value) == "polyline" else "Smooth Curve"


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

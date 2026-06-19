"""3D Centerline review command for Parametric Road v1."""

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
from freecad.Corridor_Road.objects.obj_project import ensure_project_tree, find_project, route_to_v1_tree
from freecad.Corridor_Road.qt_compat import QtWidgets

from ..models.result.centerline3d import Centerline3DResult
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_profile import find_v1_profile, to_profile_model
from ..objects.obj_stationing import find_v1_stationing
from ..services.evaluation import (
    AlignmentEvaluationService,
    Centerline3DEvaluationRequest,
    Centerline3DEvaluationService,
    Centerline3DSourceGeometryService,
    ProfileEvaluationService,
)
from ..services.evaluation.centerline3d_source_geometry_service import (
    _arc_fit_max_radial_error as _source_geometry_arc_fit_max_radial_error,
    _arc_fit_quality_from_points as _source_geometry_arc_fit_quality_from_points,
    _arc_fit_tolerance as _source_geometry_arc_fit_tolerance,
    _arc_xy_from_source_element as _source_geometry_arc_xy_from_source_element,
    _circle_center_from_three_points as _source_geometry_circle_center_from_three_points,
    _clean_xy_pairs as _source_geometry_clean_xy_pairs,
    _distance2d as _source_geometry_distance2d,
    _fit_plan_arc_from_points as _source_geometry_fit_plan_arc_from_points,
    _horizontal_source_point as _source_geometry_horizontal_source_point,
    _normalized_arc_fit_tolerances as _source_geometry_normalized_arc_fit_tolerances,
    _numeric_source_values as _source_geometry_numeric_source_values,
    _point_line_distance as _source_geometry_point_line_distance,
    _positive_angle_delta as _source_geometry_positive_angle_delta,
)


CENTERLINE3D_COMMAND_ID = "CorridorRoad_V1Centerline3D"
ARC_FIT_ABSOLUTE_TOLERANCE = 0.05
ARC_FIT_RELATIVE_TOLERANCE = 0.001
SOURCE_GEOMETRY_CURVE_SAMPLE_MAX_SPACING = 1.0


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
    display_mode: str = "source_geometry",
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
    source_geometry_sample_spacing: float = SOURCE_GEOMETRY_CURVE_SAMPLE_MAX_SPACING,
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
    normalized_display_mode = _normalized_display_mode(display_mode)
    arc_fit_absolute_tolerance, arc_fit_relative_tolerance = _normalized_arc_fit_tolerances(
        arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance,
    )
    source_geometry_sample_spacing = _normalized_source_geometry_sample_spacing(source_geometry_sample_spacing)
    shape, curve_kind, source_status, source_message, source_summary = _make_centerline3d_preview_shape(
        active_result,
        point_groups=point_groups,
        display_mode=normalized_display_mode,
        document=doc,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
        source_geometry_sample_spacing=source_geometry_sample_spacing,
    )
    obj = doc.getObject("V1Centerline3DPreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1Centerline3DPreview")
    obj.Label = "3D Centerline"
    obj.Shape = shape
    _set_string(obj, "CRRecordKind", "v1_centerline3d_review")
    _set_string(obj, "V1ObjectType", "V1Centerline3DReview")
    _set_string(obj, "Centerline3DResultId", str(active_result.centerline3d_result_id or "centerline3d:main"))
    _set_string(obj, "CurveKind", curve_kind)
    _set_string(obj, "CenterlineDisplayMode", normalized_display_mode)
    _set_string(obj, "SourceGeometryStatus", source_status)
    _set_string(obj, "SourceGeometryMessage", source_message)
    _set_integer(obj, "SourceGeometryIntervalCount", int(source_summary.get("interval_count", 0)))
    _set_integer(obj, "SourceGeometryLineIntervalCount", int(source_summary.get("line_count", 0)))
    _set_integer(obj, "SourceGeometryArcFitIntervalCount", int(source_summary.get("arc_fit_count", 0)))
    _set_integer(obj, "SourceGeometrySampledCurveIntervalCount", int(source_summary.get("sampled_curve_count", 0)))
    _set_integer(obj, "SourceGeometryPartArcIntervalCount", int(source_summary.get("part_arc_count", 0)))
    _set_integer(obj, "SourceGeometryArcFit3DSampledIntervalCount", int(source_summary.get("arc_fit_3d_sampled_count", 0)))
    _set_integer(obj, "SourceGeometryArcFitRejectedIntervalCount", int(source_summary.get("arc_fit_rejected_count", 0)))
    _set_float(obj, "SourceGeometryArcFitAbsoluteTolerance", arc_fit_absolute_tolerance)
    _set_float(obj, "SourceGeometryArcFitRelativeTolerance", arc_fit_relative_tolerance)
    _set_float(obj, "SourceGeometrySampleSpacing", source_geometry_sample_spacing)
    _set_string_list(obj, "SourceGeometryIntervalRows", list(source_summary.get("interval_rows", []) or []))
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
        self._display_mode_combo.addItems(["Source Geometry", "B-spline", "Polyline"])
        self._display_mode_combo.setCurrentText("Source Geometry")
        self._display_mode_combo.setToolTip(
            "Source Geometry draws from Alignment/Profile source segments. "
            "B-spline smooths evaluated centerline points. "
            "Polyline shows raw evaluated centerline points."
        )
        display_row.addWidget(self._display_mode_combo)
        display_row.addStretch(1)
        layout.addLayout(display_row)
        tolerance_row = QtWidgets.QHBoxLayout()
        tolerance_row.addWidget(QtWidgets.QLabel("Arc-fit tolerance"))
        self._arc_fit_abs_tol_spin = QtWidgets.QDoubleSpinBox()
        self._arc_fit_abs_tol_spin.setDecimals(4)
        self._arc_fit_abs_tol_spin.setRange(0.0, 100.0)
        self._arc_fit_abs_tol_spin.setSingleStep(0.01)
        self._arc_fit_abs_tol_spin.setValue(float(ARC_FIT_ABSOLUTE_TOLERANCE))
        self._arc_fit_abs_tol_spin.setToolTip("Absolute radial error tolerance for Source Geometry arc-fit preview.")
        tolerance_row.addWidget(QtWidgets.QLabel("Abs"))
        tolerance_row.addWidget(self._arc_fit_abs_tol_spin)
        self._arc_fit_rel_tol_spin = QtWidgets.QDoubleSpinBox()
        self._arc_fit_rel_tol_spin.setDecimals(6)
        self._arc_fit_rel_tol_spin.setRange(0.0, 1.0)
        self._arc_fit_rel_tol_spin.setSingleStep(0.0005)
        self._arc_fit_rel_tol_spin.setValue(float(ARC_FIT_RELATIVE_TOLERANCE))
        self._arc_fit_rel_tol_spin.setToolTip("Relative radial error tolerance multiplied by fitted arc radius.")
        tolerance_row.addWidget(QtWidgets.QLabel("Rel"))
        tolerance_row.addWidget(self._arc_fit_rel_tol_spin)
        tolerance_row.addWidget(QtWidgets.QLabel("Sample spacing"))
        self._source_geometry_sample_spacing_spin = QtWidgets.QDoubleSpinBox()
        self._source_geometry_sample_spacing_spin.setDecimals(2)
        self._source_geometry_sample_spacing_spin.setRange(0.25, 20.0)
        self._source_geometry_sample_spacing_spin.setSingleStep(0.25)
        self._source_geometry_sample_spacing_spin.setValue(float(SOURCE_GEOMETRY_CURVE_SAMPLE_MAX_SPACING))
        self._source_geometry_sample_spacing_spin.setSuffix(" m")
        self._source_geometry_sample_spacing_spin.setToolTip(
            "Maximum station spacing for Source Geometry sampled curve intervals. Lower values draw smoother curves but create more preview segments."
        )
        tolerance_row.addWidget(self._source_geometry_sample_spacing_spin)
        tolerance_row.addStretch(1)
        layout.addLayout(tolerance_row)
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
        if self._show():
            _show_info(
                self.form,
                "3D Centerline",
                (
                    "3D Centerline has been generated.\n"
                    f"Preview object: {str(getattr(self._preview_object, 'Name', '') or 'V1Centerline3DPreview')}\n"
                    f"Points: {int(getattr(self._result, 'point_count', 0) or 0)}"
                ),
            )

    def _show(self) -> bool:
        try:
            self._preview_object = show_v1_centerline3d_preview_object(
                self.document,
                result=self._result,
                show_station_markers=self._show_stations_enabled(),
                display_mode=self._selected_display_mode(),
                arc_fit_absolute_tolerance=self._selected_arc_fit_absolute_tolerance(),
                arc_fit_relative_tolerance=self._selected_arc_fit_relative_tolerance(),
                source_geometry_sample_spacing=self._selected_source_geometry_sample_spacing(),
            )
            self._focus()
            self._refresh_ui(
                message=(
                    "3D Centerline has been generated. "
                    f"Preview object: {str(getattr(self._preview_object, 'Name', '') or 'V1Centerline3DPreview')}; "
                    f"points={int(getattr(self._result, 'point_count', 0) or 0)}; "
                    f"display={_display_mode_label(getattr(self._preview_object, 'CenterlineDisplayMode', 'source_geometry'))}."
                    f"{_source_geometry_message_suffix(self._preview_object)}"
                )
            )
            return True
        except Exception as exc:
            self._diagnostics.setPlainText(f"3D Centerline preview was not shown:\n{exc}")
            return False

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
        preview = getattr(self, "_preview_object", None)
        if preview is not None and _normalized_display_mode(getattr(preview, "CenterlineDisplayMode", "")) == "source_geometry":
            rows.extend(
                [
                    ("Source Geometry", str(getattr(preview, "SourceGeometryStatus", "") or "-")),
                    ("Source Intervals", str(int(getattr(preview, "SourceGeometryIntervalCount", 0) or 0))),
                    ("Line / Arc / Sampled", _source_geometry_count_label(preview)),
                    ("PartArc / 3D ArcSampled", _source_geometry_arc_shape_count_label(preview)),
                    ("ArcFit Accepted / Rejected", _source_geometry_arc_fit_status_count_label(preview)),
                    ("ArcFit Tol abs / rel", _source_geometry_arc_fit_tolerance_label(preview)),
                    ("Source Sample Spacing", _source_geometry_sample_spacing_label(preview)),
                ]
            )
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
        source_interval_text = _source_geometry_interval_rows_text(getattr(self, "_preview_object", None))
        if source_interval_text:
            diagnostic_text = f"{diagnostic_text}\n\n{source_interval_text}"
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
            return _normalized_display_mode(str(self._display_mode_combo.currentText() or "Source Geometry"))
        except Exception:
            return "source_geometry"

    def _selected_arc_fit_absolute_tolerance(self) -> float:
        try:
            return max(0.0, float(self._arc_fit_abs_tol_spin.value()))
        except Exception:
            return float(ARC_FIT_ABSOLUTE_TOLERANCE)

    def _selected_arc_fit_relative_tolerance(self) -> float:
        try:
            return max(0.0, float(self._arc_fit_rel_tol_spin.value()))
        except Exception:
            return float(ARC_FIT_RELATIVE_TOLERANCE)

    def _selected_source_geometry_sample_spacing(self) -> float:
        try:
            return _normalized_source_geometry_sample_spacing(self._source_geometry_sample_spacing_spin.value())
        except Exception:
            return float(SOURCE_GEOMETRY_CURVE_SAMPLE_MAX_SPACING)


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


def _make_centerline3d_preview_shape(
    result: Centerline3DResult,
    *,
    point_groups: list[list[object]],
    display_mode: str = "source_geometry",
    document=None,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
    source_geometry_sample_spacing: float = SOURCE_GEOMETRY_CURVE_SAMPLE_MAX_SPACING,
):
    if _normalized_display_mode(display_mode) == "source_geometry":
        try:
            shape, source_summary = _make_centerline3d_source_geometry_shape(
                document,
                result,
                arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
                arc_fit_relative_tolerance=arc_fit_relative_tolerance,
                source_geometry_sample_spacing=source_geometry_sample_spacing,
            )
            return (
                shape,
                "source_geometry",
                "ready",
                (
                    "Source Geometry built from "
                    f"{int(source_summary.get('interval_count', 0))} source intervals "
                    f"(line={int(source_summary.get('line_count', 0))}, "
                    f"arc-fit={int(source_summary.get('arc_fit_count', 0))}, "
                f"sampled={int(source_summary.get('sampled_curve_count', 0))})."
            ),
            source_summary,
            )
        except Exception as exc:
            shape, curve_kind = _make_centerline3d_compound_curve_shape(point_groups, display_mode="bspline")
            reason = str(exc) or "Unknown source geometry error."
            return (
                shape,
                f"source_geometry_fallback_{curve_kind}",
                "fallback",
                f"Source Geometry failed; B-spline fallback was used. Reason: {reason}",
                _empty_source_geometry_summary(),
            )
    if _normalized_display_mode(display_mode) == "bspline":
        return (
            *_make_centerline3d_compound_curve_shape(point_groups, display_mode=display_mode),
            "not_applicable",
            "",
            _empty_source_geometry_summary(),
        )
    shape, curve_kind = _make_centerline3d_compound_curve_shape(point_groups, display_mode=display_mode)
    return shape, curve_kind, "not_applicable", "", _empty_source_geometry_summary()


def _empty_source_geometry_summary() -> dict[str, object]:
    return {
        "interval_count": 0,
        "line_count": 0,
        "arc_fit_count": 0,
        "sampled_curve_count": 0,
        "part_arc_count": 0,
        "arc_fit_3d_sampled_count": 0,
        "arc_fit_rejected_count": 0,
        "interval_rows": [],
    }


def _make_centerline3d_source_geometry_shape(
    document,
    result: Centerline3DResult,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
    source_geometry_sample_spacing: float = SOURCE_GEOMETRY_CURVE_SAMPLE_MAX_SPACING,
):
    if document is None:
        raise RuntimeError("Document is required for Source Geometry display.")
    alignment_obj = find_v1_alignment(document)
    profile_obj = find_v1_profile(document)
    if alignment_obj is None:
        raise RuntimeError("No V1 Alignment object was found.")
    if profile_obj is None:
        raise RuntimeError("No V1 Profile object was found.")
    alignment = to_alignment_model(alignment_obj)
    profile = to_profile_model(profile_obj)
    boundaries = _centerline3d_source_geometry_boundaries(alignment, profile, result)
    if len(boundaries) < 2:
        raise RuntimeError("At least two source geometry station boundaries are required.")
    alignment_service = AlignmentEvaluationService()
    profile_service = ProfileEvaluationService()
    source_geometry_service = Centerline3DSourceGeometryService(
        alignment_service=alignment_service,
        profile_service=profile_service,
    )
    shapes = []
    source_summary = _empty_source_geometry_summary()
    for start, end in zip(boundaries, boundaries[1:]):
        if float(end) <= float(start) + 1.0e-9:
            continue
        points = _centerline3d_source_geometry_points(
            alignment,
            profile,
            source_geometry_service,
            start,
            end,
            arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
            arc_fit_relative_tolerance=arc_fit_relative_tolerance,
            source_geometry_sample_spacing=source_geometry_sample_spacing,
        )
        if len(points) < 2:
            continue
        interval_kind = _centerline3d_source_interval_kind(
            alignment,
            profile,
            start,
            end,
            arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
            arc_fit_relative_tolerance=arc_fit_relative_tolerance,
        )
        if interval_kind == "line":
            shapes.append(Part.makeLine(points[0], points[-1]))
            source_summary["line_count"] += 1
            shape_kind = "line"
        else:
            shape_kind = _centerline3d_source_shape_kind(interval_kind, points)
            shapes.append(_make_source_interval_curve_shape(points, shape_kind=shape_kind))
            if interval_kind == "arc_fit":
                source_summary["arc_fit_count"] += 1
                if shape_kind == "part_arc":
                    source_summary["part_arc_count"] += 1
                elif shape_kind == "arc_fit_3d_sampled":
                    source_summary["arc_fit_3d_sampled_count"] += 1
            else:
                source_summary["sampled_curve_count"] += 1
                if _centerline3d_interval_has_rejected_arc_fit(
                    alignment,
                    start,
                    end,
                    arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
                    arc_fit_relative_tolerance=arc_fit_relative_tolerance,
                ):
                    source_summary["arc_fit_rejected_count"] += 1
        source_summary["interval_count"] += 1
        source_summary["interval_rows"].append(
            _centerline3d_source_interval_row_text(
                alignment,
                profile,
                start,
                end,
                interval_kind,
                len(points),
                shape_kind=shape_kind,
                arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
                arc_fit_relative_tolerance=arc_fit_relative_tolerance,
            )
        )
    if not shapes:
        raise RuntimeError("No source geometry intervals could be evaluated.")
    return (Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]), source_summary


def _centerline3d_source_geometry_boundaries(alignment, profile, result: Centerline3DResult) -> list[float]:
    point_rows = list(getattr(result, "point_rows", []) or [])
    if point_rows:
        station_start = min(float(getattr(row, "station", 0.0) or 0.0) for row in point_rows)
        station_end = max(float(getattr(row, "station", 0.0) or 0.0) for row in point_rows)
    else:
        station_start = float(getattr(result, "station_start", 0.0) or 0.0)
        station_end = float(getattr(result, "station_end", 0.0) or 0.0)
    boundaries = {station_start, station_end}
    for element in list(getattr(alignment, "geometry_sequence", []) or []):
        _add_clipped_station_boundary(boundaries, getattr(element, "station_start", station_start), station_start, station_end)
        _add_clipped_station_boundary(boundaries, getattr(element, "station_end", station_end), station_start, station_end)
    for control in list(getattr(profile, "control_rows", []) or []):
        _add_clipped_station_boundary(boundaries, getattr(control, "station", station_start), station_start, station_end)
    for curve in list(getattr(profile, "vertical_curve_rows", []) or []):
        raw_start = float(getattr(curve, "station_start", station_start) or station_start)
        raw_end = float(getattr(curve, "station_end", station_end) or station_end)
        _add_clipped_station_boundary(boundaries, raw_start, station_start, station_end)
        _add_clipped_station_boundary(boundaries, raw_end, station_start, station_end)
        effective_start, effective_end = _centerline3d_effective_vertical_curve_range(profile, raw_start, raw_end)
        _add_clipped_station_boundary(boundaries, effective_start, station_start, station_end)
        _add_clipped_station_boundary(boundaries, effective_end, station_start, station_end)
    return _unique_sorted_station_values(boundaries)


def _centerline3d_source_geometry_points(
    alignment,
    profile,
    source_geometry_service: Centerline3DSourceGeometryService,
    start: float,
    end: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
    source_geometry_sample_spacing: float = SOURCE_GEOMETRY_CURVE_SAMPLE_MAX_SPACING,
) -> list[object]:
    stations = _centerline3d_source_interval_stations(start, end, sample_spacing=source_geometry_sample_spacing)
    points = []
    for station in stations:
        frame = source_geometry_service.evaluate_station(
            alignment,
            profile,
            station,
            arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
            arc_fit_relative_tolerance=arc_fit_relative_tolerance,
        )
        if str(getattr(frame, "status", "") or "") not in {"ok", "warning"}:
            continue
        points.append(
            App.Vector(
                float(getattr(frame, "x", 0.0) or 0.0),
                float(getattr(frame, "y", 0.0) or 0.0),
                float(getattr(frame, "z", 0.0) or 0.0),
            )
        )
    return _clean_centerline_points(points)


def _centerline3d_horizontal_source_point(
    alignment,
    alignment_service: AlignmentEvaluationService,
    station: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> tuple[float, float] | None:
    return _source_geometry_horizontal_source_point(
        alignment,
        alignment_service,
        station,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )


def _centerline3d_arc_xy_from_source_element(
    alignment,
    station: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> tuple[float, float] | None:
    return _source_geometry_arc_xy_from_source_element(
        alignment,
        station,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )


def _centerline3d_active_alignment_element(alignment, station: float):
    for element in list(getattr(alignment, "geometry_sequence", []) or []):
        station_start = float(getattr(element, "station_start", 0.0) or 0.0)
        station_end = float(getattr(element, "station_end", 0.0) or 0.0)
        if station_end < station_start:
            station_start, station_end = station_end, station_start
        if station_start - 1.0e-9 <= float(station) <= station_end + 1.0e-9:
            return element
    return None


def _centerline3d_element_is_curve(element) -> bool:
    kind = str(getattr(element, "kind", "") or "").lower()
    payload = getattr(element, "geometry_payload", {}) or {}
    x_values = list(payload.get("x_values", []) or []) if isinstance(payload, dict) else []
    y_values = list(payload.get("y_values", []) or []) if isinstance(payload, dict) else []
    return "curve" in kind or "arc" in kind or min(len(x_values), len(y_values)) > 2


def _fit_plan_arc_from_points(points: list[tuple[float, float]]) -> tuple[float, float, float, float, float] | None:
    return _source_geometry_fit_plan_arc_from_points(points)


def _circle_center_from_three_points(
    first: tuple[float, float],
    middle: tuple[float, float],
    last: tuple[float, float],
) -> tuple[float, float] | None:
    return _source_geometry_circle_center_from_three_points(first, middle, last)


def _positive_angle_delta(start: float, end: float) -> float:
    return _source_geometry_positive_angle_delta(start, end)


def _point_line_distance(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    return _source_geometry_point_line_distance(point, start, end)


def _clean_xy_pairs(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return _source_geometry_clean_xy_pairs(points)


def _numeric_source_values(values) -> list[float]:
    return _source_geometry_numeric_source_values(values)


def _distance2d(x0: float, y0: float, x1: float, y1: float) -> float:
    return _source_geometry_distance2d(x0, y0, x1, y1)


def _centerline3d_source_interval_stations(
    start: float,
    end: float,
    *,
    sample_spacing: float = SOURCE_GEOMETRY_CURVE_SAMPLE_MAX_SPACING,
) -> list[float]:
    span = max(float(end) - float(start), 0.0)
    if span <= 1.0e-9:
        return [float(start), float(end)]
    spacing = _normalized_source_geometry_sample_spacing(sample_spacing)
    sample_count = min(max(2, int(math.ceil(span / spacing)) + 1), 2048)
    return [float(start) + span * float(index) / float(sample_count - 1) for index in range(sample_count)]


def _centerline3d_source_interval_is_line(alignment, profile, start: float, end: float) -> bool:
    return not _centerline3d_span_overlaps_horizontal_curve(alignment, start, end) and not _centerline3d_span_overlaps_vertical_curve(profile, start, end)


def _centerline3d_source_interval_kind(
    alignment,
    profile,
    start: float,
    end: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> str:
    if _centerline3d_source_interval_is_line(alignment, profile, start, end):
        return "line"
    if _centerline3d_span_overlaps_horizontal_curve(alignment, start, end) and _centerline3d_interval_has_arc_fit(
        alignment,
        start,
        end,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    ):
        return "arc_fit"
    return "sampled_curve"


def _centerline3d_source_interval_row_text(
    alignment,
    profile,
    start: float,
    end: float,
    interval_kind: str,
    point_count: int,
    *,
    shape_kind: str,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> str:
    horizontal_mode = _centerline3d_horizontal_interval_mode(
        alignment,
        start,
        end,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )
    vertical_mode = "vertical_curve" if _centerline3d_span_overlaps_vertical_curve(profile, start, end) else "tangent"
    reason = _centerline3d_source_interval_reason(interval_kind, horizontal_mode, vertical_mode)
    arc_details = (
        _centerline3d_arc_fit_detail_label(
            alignment,
            start,
            end,
            arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
            arc_fit_relative_tolerance=arc_fit_relative_tolerance,
        )
        if _centerline3d_span_overlaps_horizontal_curve(alignment, start, end)
        else ""
    )
    return (
        f"{interval_kind}|{float(start):.3f}|{float(end):.3f}|points={int(point_count)}|"
        f"horizontal={horizontal_mode}|vertical={vertical_mode}|shape={shape_kind}|reason={reason}"
        f"{arc_details}"
    )


def _centerline3d_horizontal_interval_mode(
    alignment,
    start: float,
    end: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> str:
    if not _centerline3d_span_overlaps_horizontal_curve(alignment, start, end):
        return "tangent"
    if _centerline3d_interval_has_arc_fit(
        alignment,
        start,
        end,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    ):
        return "arc_fit"
    if _centerline3d_interval_has_rejected_arc_fit(
        alignment,
        start,
        end,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    ):
        return "arc_fit_rejected"
    return "sampled_curve"


def _centerline3d_source_interval_reason(interval_kind: str, horizontal_mode: str, vertical_mode: str) -> str:
    if interval_kind == "line":
        return "horizontal_tangent_and_vertical_tangent"
    if horizontal_mode == "arc_fit" and vertical_mode == "tangent":
        return "horizontal_arc_fit"
    if horizontal_mode == "arc_fit" and vertical_mode == "vertical_curve":
        return "horizontal_arc_fit_with_vertical_curve"
    if horizontal_mode == "arc_fit_rejected":
        return "arc_fit_rejected_radial_error"
    if vertical_mode == "vertical_curve":
        return "vertical_curve_requires_sampled_3d_curve"
    return "horizontal_curve_requires_sampled_3d_curve"


def _centerline3d_interval_has_arc_fit(
    alignment,
    start: float,
    end: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> bool:
    station = 0.5 * (float(start) + float(end))
    element = _centerline3d_active_alignment_element(alignment, station)
    if element is None or not _centerline3d_element_is_curve(element):
        return False
    payload = getattr(element, "geometry_payload", {}) or {}
    if not isinstance(payload, dict):
        return False
    points = list(zip(_numeric_source_values(payload.get("x_values", [])), _numeric_source_values(payload.get("y_values", []))))
    return bool(
        _arc_fit_quality_from_points(
            points,
            arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
            arc_fit_relative_tolerance=arc_fit_relative_tolerance,
        ).get("accepted", False)
    )


def _centerline3d_interval_has_rejected_arc_fit(
    alignment,
    start: float,
    end: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> bool:
    quality = _centerline3d_arc_fit_quality(
        alignment,
        start,
        end,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )
    return quality.get("arc") is not None and not bool(quality.get("accepted", False))


def _centerline3d_arc_fit_detail_label(
    alignment,
    start: float,
    end: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> str:
    quality = _centerline3d_arc_fit_quality(
        alignment,
        start,
        end,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )
    arc = quality.get("arc")
    if arc is None:
        return ""
    center_x, center_y, radius, _start_angle, sweep_angle = arc
    radial_error = float(quality.get("radial_error", 0.0) or 0.0)
    tolerance = float(quality.get("tolerance", 0.0) or 0.0)
    status = "accepted" if bool(quality.get("accepted", False)) else "rejected"
    return (
        f"|arc_fit_status={status}|arc_radius={float(radius):.3f}|"
        f"arc_sweep_deg={math.degrees(float(sweep_angle)):.3f}|"
        f"arc_radial_error={radial_error:.6f}|arc_tolerance={tolerance:.6f}"
    )


def _centerline3d_arc_fit_quality(
    alignment,
    start: float,
    end: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> dict[str, object]:
    station = 0.5 * (float(start) + float(end))
    element = _centerline3d_active_alignment_element(alignment, station)
    if element is None:
        return {"accepted": False, "arc": None, "radial_error": 0.0, "tolerance": 0.0}
    payload = getattr(element, "geometry_payload", {}) or {}
    if not isinstance(payload, dict):
        return {"accepted": False, "arc": None, "radial_error": 0.0, "tolerance": 0.0}
    points = list(zip(_numeric_source_values(payload.get("x_values", [])), _numeric_source_values(payload.get("y_values", []))))
    return _arc_fit_quality_from_points(
        points,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )


def _arc_fit_quality_from_points(
    points: list[tuple[float, float]],
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> dict[str, object]:
    return _source_geometry_arc_fit_quality_from_points(
        points,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )


def _arc_fit_tolerance(
    radius: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> float:
    return _source_geometry_arc_fit_tolerance(
        radius,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )


def _normalized_arc_fit_tolerances(absolute: float, relative: float) -> tuple[float, float]:
    return _source_geometry_normalized_arc_fit_tolerances(absolute, relative)


def _normalized_source_geometry_sample_spacing(value: float) -> float:
    try:
        return max(0.01, float(value))
    except Exception:
        return float(SOURCE_GEOMETRY_CURVE_SAMPLE_MAX_SPACING)


def _arc_fit_max_radial_error(points: list[tuple[float, float]], center_x: float, center_y: float, radius: float) -> float:
    return _source_geometry_arc_fit_max_radial_error(points, center_x, center_y, radius)


def _centerline3d_span_overlaps_horizontal_curve(alignment, start: float, end: float) -> bool:
    for element in list(getattr(alignment, "geometry_sequence", []) or []):
        element_start = float(getattr(element, "station_start", 0.0) or 0.0)
        element_end = float(getattr(element, "station_end", 0.0) or 0.0)
        if element_end < element_start:
            element_start, element_end = element_end, element_start
        if element_end < float(start) + 1.0e-9 or element_start > float(end) - 1.0e-9:
            continue
        kind = str(getattr(element, "kind", "") or "").lower()
        payload = getattr(element, "geometry_payload", {}) or {}
        x_values = list(payload.get("x_values", []) or []) if isinstance(payload, dict) else []
        y_values = list(payload.get("y_values", []) or []) if isinstance(payload, dict) else []
        if "curve" in kind or "arc" in kind or min(len(x_values), len(y_values)) > 2:
            return True
    return False


def _centerline3d_span_overlaps_vertical_curve(profile, start: float, end: float) -> bool:
    for curve in list(getattr(profile, "vertical_curve_rows", []) or []):
        curve_start, curve_end = _centerline3d_effective_vertical_curve_range(
            profile,
            float(getattr(curve, "station_start", 0.0) or 0.0),
            float(getattr(curve, "station_end", 0.0) or 0.0),
        )
        if curve_end < curve_start:
            curve_start, curve_end = curve_end, curve_start
        if curve_end >= float(start) + 1.0e-9 and curve_start <= float(end) - 1.0e-9:
            return True
    return False


def _centerline3d_effective_vertical_curve_range(profile, station_start: float, station_end: float) -> tuple[float, float]:
    controls = sorted(list(getattr(profile, "control_rows", []) or []), key=lambda row: float(getattr(row, "station", 0.0) or 0.0))
    start = min(float(station_start), float(station_end))
    end = max(float(station_start), float(station_end))
    if len(controls) < 3:
        return start, end
    center = 0.5 * (start + end)
    candidates = [
        control
        for control in controls[1:-1]
        if start - 1.0e-6 <= float(getattr(control, "station", 0.0) or 0.0) <= end + 1.0e-6
    ]
    if not candidates:
        return start, end
    pvi_candidates = [control for control in candidates if "pvi" in str(getattr(control, "kind", "") or "").lower()]
    pvi = min(pvi_candidates or candidates, key=lambda row: abs(float(getattr(row, "station", 0.0) or 0.0) - center))
    length = end - start
    pvi_station = float(getattr(pvi, "station", center) or center)
    return pvi_station - 0.5 * length, pvi_station + 0.5 * length


def _centerline3d_source_shape_kind(interval_kind: str, points: list[object]) -> str:
    if interval_kind == "arc_fit" and _centerline3d_points_have_constant_z(points):
        return "part_arc"
    if interval_kind == "arc_fit":
        return "arc_fit_3d_sampled"
    return "sampled_curve"


def _centerline3d_points_have_constant_z(points: list[object]) -> bool:
    cleaned = _clean_centerline_points(points)
    if len(cleaned) < 2:
        return False
    z0 = float(getattr(cleaned[0], "z", 0.0) or 0.0)
    return all(abs(float(getattr(point, "z", 0.0) or 0.0) - z0) <= 1.0e-6 for point in cleaned)


def _make_source_interval_curve_shape(points: list[object], *, shape_kind: str = "sampled_curve"):
    cleaned = _clean_centerline_points(points)
    if len(cleaned) < 3:
        return Part.makePolygon(cleaned)
    if str(shape_kind or "") == "part_arc":
        try:
            return Part.Arc(cleaned[0], cleaned[len(cleaned) // 2], cleaned[-1]).toShape()
        except Exception:
            pass
    return Part.makePolygon(cleaned)


def _add_clipped_station_boundary(boundaries: set[float], value, station_start: float, station_end: float) -> None:
    try:
        station = float(value)
    except Exception:
        return
    if float(station_start) - 1.0e-9 <= station <= float(station_end) + 1.0e-9:
        boundaries.add(station)


def _unique_sorted_station_values(values) -> list[float]:
    output = []
    seen = set()
    for value in sorted(float(item) for item in list(values or [])):
        key = round(value, 9)
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _make_centerline3d_curve_shape(points: list[object], *, display_mode: str = "bspline"):
    """Return a faithful centerline review curve from evaluated point rows."""

    cleaned = _clean_centerline_points(points)
    if len(cleaned) < 2:
        raise RuntimeError("3D Centerline preview requires at least two distinct evaluated points.")
    if _normalized_display_mode(display_mode) == "polyline":
        return Part.makePolygon(cleaned), "polyline"
    if len(cleaned) >= 3:
        smoothed = _smooth_centerline_display_points(cleaned)
        if len(smoothed) >= 3:
            try:
                curve = Part.BSplineCurve()
                curve.buildFromPoles(smoothed)
                return curve.toShape(), "bspline_smoothed"
            except Exception:
                pass
        try:
            curve = Part.BSplineCurve()
            curve.interpolate(cleaned)
            return curve.toShape(), "bspline_interpolation"
        except Exception:
            pass
    return Part.makePolygon(cleaned), "evaluated_polyline"


def _make_centerline3d_compound_curve_shape(point_groups: list[list[object]], *, display_mode: str = "bspline"):
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


def _smooth_centerline_display_points(points: list[object], *, passes: int = 2, max_points: int = 1600) -> list[object]:
    """Return display-only points softened enough to avoid interpolation zigzags."""

    smoothed = _clean_centerline_points(points)
    if len(smoothed) < 3:
        return smoothed
    for _index in range(max(0, int(passes))):
        if len(smoothed) < 3 or len(smoothed) * 2 + 2 > int(max_points):
            break
        next_points = [smoothed[0]]
        for left, right in zip(smoothed, smoothed[1:]):
            next_points.append(_mix_centerline_point(left, right, 0.75, 0.25))
            next_points.append(_mix_centerline_point(left, right, 0.25, 0.75))
        next_points.append(smoothed[-1])
        smoothed = _clean_centerline_points(next_points)
    return smoothed


def _mix_centerline_point(left: object, right: object, left_weight: float, right_weight: float):
    return App.Vector(
        float(left.x) * float(left_weight) + float(right.x) * float(right_weight),
        float(left.y) * float(left_weight) + float(right.y) * float(right_weight),
        float(left.z) * float(left_weight) + float(right.z) * float(right_weight),
    )


def _normalized_display_mode(value: str) -> str:
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if text in {"polyline", "line", "segmented"}:
        return "polyline"
    if text in {"bspline", "b_spline", "b_spline_curve", "smooth_curve", "smooth"}:
        return "bspline"
    if text in {"source_geometry", "source", "geometry", "source_geometry_preview"}:
        return "source_geometry"
    return "source_geometry"


def _display_mode_label(value: str) -> str:
    mode = _normalized_display_mode(value)
    if mode == "polyline":
        return "Polyline"
    if mode == "bspline":
        return "B-spline"
    return "Source Geometry"


def _source_geometry_message_suffix(obj) -> str:
    try:
        if _normalized_display_mode(getattr(obj, "CenterlineDisplayMode", "")) != "source_geometry":
            return ""
        status = str(getattr(obj, "SourceGeometryStatus", "") or "")
        message = str(getattr(obj, "SourceGeometryMessage", "") or "")
        if status in {"ready", "fallback"} and message:
            return f" Source Geometry: {message}"
    except Exception:
        pass
    return ""


def _source_geometry_count_label(obj) -> str:
    try:
        return (
            f"{int(getattr(obj, 'SourceGeometryLineIntervalCount', 0) or 0)} / "
            f"{int(getattr(obj, 'SourceGeometryArcFitIntervalCount', 0) or 0)} / "
            f"{int(getattr(obj, 'SourceGeometrySampledCurveIntervalCount', 0) or 0)}"
        )
    except Exception:
        return "0 / 0 / 0"


def _source_geometry_arc_shape_count_label(obj) -> str:
    try:
        return (
            f"{int(getattr(obj, 'SourceGeometryPartArcIntervalCount', 0) or 0)} / "
            f"{int(getattr(obj, 'SourceGeometryArcFit3DSampledIntervalCount', 0) or 0)}"
        )
    except Exception:
        return "0 / 0"


def _source_geometry_arc_fit_status_count_label(obj) -> str:
    try:
        accepted = int(getattr(obj, "SourceGeometryArcFitIntervalCount", 0) or 0)
        rejected = int(getattr(obj, "SourceGeometryArcFitRejectedIntervalCount", 0) or 0)
        return f"{accepted} / {rejected}"
    except Exception:
        return "0 / 0"


def _source_geometry_arc_fit_tolerance_label(obj) -> str:
    try:
        absolute = float(getattr(obj, "SourceGeometryArcFitAbsoluteTolerance", 0.0) or 0.0)
        relative = float(getattr(obj, "SourceGeometryArcFitRelativeTolerance", 0.0) or 0.0)
        return f"{absolute:.6f} / {relative:.6f}"
    except Exception:
        return "0.000000 / 0.000000"


def _source_geometry_sample_spacing_label(obj) -> str:
    try:
        spacing = float(getattr(obj, "SourceGeometrySampleSpacing", 0.0) or 0.0)
        return f"{spacing:.2f} m"
    except Exception:
        return "0.00 m"


def _source_geometry_interval_rows_text(obj) -> str:
    try:
        if obj is None or _normalized_display_mode(getattr(obj, "CenterlineDisplayMode", "")) != "source_geometry":
            return ""
        rows = [str(row) for row in list(getattr(obj, "SourceGeometryIntervalRows", []) or []) if str(row or "").strip()]
        if not rows:
            return ""
        return "Source Geometry intervals:\n" + "\n".join(rows)
    except Exception:
        return ""


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


def _show_info(parent, title: str, message: str) -> None:
    if QtWidgets is None:
        return
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand(CENTERLINE3D_COMMAND_ID, CmdV1Centerline3D())

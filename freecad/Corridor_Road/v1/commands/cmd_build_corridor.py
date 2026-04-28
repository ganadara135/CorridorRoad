"""Build Corridor command helpers for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.qt_compat import QtWidgets

from ...objects.obj_project import CorridorRoadProject, ensure_project_properties, ensure_project_tree, find_project
from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..objects.obj_corridor import create_or_update_v1_corridor_model_object, find_v1_corridor_model
from ..objects.obj_region import find_v1_region_model
from ..objects.obj_surface import create_or_update_v1_surface_model_object, find_v1_surface_model
from ..services.builders import (
    CorridorDesignSurfaceGeometryRequest,
    CorridorModelBuildRequest,
    CorridorModelService,
    CorridorSurfaceBuildRequest,
    CorridorSurfaceGeometryService,
    CorridorSurfaceService,
)
from ..services.mapping.tin_mesh_preview_mapper import TINMeshPreviewMapper


CORRIDOR_BUILD_REVIEW_OBJECTS = (
    ("centerline", "3D Centerline", "V1CorridorCenterline3DPreview"),
    ("design", "Design Surface", "V1CorridorDesignSurfacePreview"),
    ("subgrade", "Subgrade Surface", "V1CorridorSubgradeSurfacePreview"),
    ("daylight", "Slope Face Surface", "V1CorridorDaylightSurfacePreview"),
    ("drainage", "Drainage Surface", "V1CorridorDrainageSurfacePreview"),
)


def document_has_v1_applied_sections(document=None) -> bool:
    """Return True when a document has a v1 AppliedSectionSet result."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    return find_v1_applied_section_set(doc) is not None


def build_document_corridor_model(document=None, *, project=None, corridor_id: str = "corridor:main"):
    """Build a CorridorModel result from the document's v1 AppliedSectionSet."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        raise RuntimeError("A v1 AppliedSectionSet is required before Build Corridor.")
    region_obj = find_v1_region_model(doc)
    return CorridorModelService().build(
        CorridorModelBuildRequest(
            project_id=_project_id(project or find_project(doc)),
            corridor_id=corridor_id,
            applied_section_set=applied_section_set,
            region_model_ref=str(getattr(region_obj, "RegionModelId", "") or ""),
        )
    )


def build_document_corridor_surface_model(
    document=None,
    *,
    project=None,
    corridor_model=None,
    surface_model_id: str = "surface:main",
):
    """Build the first corridor-derived SurfaceModel result from Applied Sections."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        raise RuntimeError("A v1 AppliedSectionSet is required before corridor surfaces.")
    corridor = corridor_model or build_document_corridor_model(doc, project=project)
    return CorridorSurfaceService().build(
        CorridorSurfaceBuildRequest(
            project_id=_project_id(project or find_project(doc)),
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_model_id=surface_model_id,
        )
    )


def apply_v1_corridor_model(*, document=None, project=None, corridor_model=None, build_surfaces: bool = True):
    """Persist a v1 CorridorModel result object."""

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
    if corridor_model is None:
        corridor_model = build_document_corridor_model(doc, project=prj)
    surface_model = None
    if build_surfaces:
        surface_model = build_document_corridor_surface_model(doc, project=prj, corridor_model=corridor_model)
        corridor_model.surface_build_refs = [str(getattr(surface_model, "surface_model_id", "") or "surface:main")]
    obj = create_or_update_v1_corridor_model_object(document=doc, project=prj, corridor_model=corridor_model)
    if surface_model is not None:
        create_or_update_v1_surface_model_object(document=doc, project=prj, surface_model=surface_model)
        create_corridor_centerline_3d_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            applied_section_set_ref=str(getattr(corridor_model, "applied_section_set_ref", "") or ""),
        )
        create_corridor_design_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        create_corridor_subgrade_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        create_corridor_daylight_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        create_corridor_drainage_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def corridor_build_review_rows(document=None) -> list[dict[str, object]]:
    """Return display-ready Build Corridor result rows from document preview objects."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows: list[dict[str, object]] = []
    for role, title, object_name in CORRIDOR_BUILD_REVIEW_OBJECTS:
        obj = doc.getObject(object_name) if doc is not None else None
        rows.append(_corridor_build_review_row(role, title, object_name, obj))
    return rows


def show_corridor_build_review_object(document=None, row_index: int = 0):
    """Select and fit one Build Corridor review object by review-table row index."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = corridor_build_review_rows(doc)
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Build Corridor review row index is out of range.")
    row = rows[row_index]
    object_name = str(row.get("object_name", "") or "")
    obj = doc.getObject(object_name) if doc is not None and object_name else None
    if obj is None:
        raise RuntimeError(f"{row.get('result', 'Result')} has not been built yet.")
    _select_and_fit_object(obj)
    return obj


def create_corridor_centerline_3d_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    applied_section_set_ref: str = "",
):
    """Create or update a spline-based 3D centerline preview from AppliedSection frames."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    try:
        import FreeCAD as AppModule
        import Part
    except Exception:
        return None

    points, stations = _centerline_points_from_applied_sections(applied_section_set, AppModule)
    if len(points) < 2:
        return None
    shape, curve_kind = _make_centerline_shape(points, Part)
    obj = doc.getObject("V1CorridorCenterline3DPreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1CorridorCenterline3DPreview")
    try:
        obj.Shape = shape
        obj.Label = "Corridor 3D Centerline"
    except Exception:
        return obj
    _set_preview_property(obj, "CRRecordKind", "v1_corridor_centerline_preview")
    _set_preview_property(obj, "V1ObjectType", "V1CorridorCenterlinePreview")
    _set_preview_property(obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
    _set_preview_property(
        obj,
        "AppliedSectionSetId",
        str(applied_section_set_ref or getattr(applied_section_set, "applied_section_set_id", "") or ""),
    )
    _set_preview_property(obj, "DisplayCurveKind", curve_kind)
    _set_preview_integer_property(obj, "PointCount", len(points))
    if stations:
        _set_preview_float_property(obj, "StationStart", min(stations))
        _set_preview_float_property(obj, "StationEnd", max(stations))
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.LineColor = (0.0, 0.85, 1.0)
            vobj.PointColor = (0.0, 0.85, 1.0)
            vobj.ShapeColor = (0.0, 0.85, 1.0)
            vobj.LineWidth = 5.0
            vobj.PointSize = 6.0
    except Exception:
        pass
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(doc), obj)
    except Exception:
        pass
    return obj


def create_corridor_design_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
):
    """Create or update the first design-surface mesh preview for a corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    surface_id = _surface_id(surface_model, "design_surface") or f"{corridor_model.corridor_id}:design"
    try:
        tin_surface = CorridorSurfaceGeometryService().build_design_surface(
            CorridorDesignSurfaceGeometryRequest(
                project_id=_project_id(project or find_project(doc)),
                corridor=corridor_model,
                applied_section_set=applied_section_set,
                surface_id=surface_id,
            )
        )
    except Exception:
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorDesignSurfacePreview",
        label_prefix="Corridor Design Surface",
        surface_role="design",
    )
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _set_preview_property(preview_obj, "CRRecordKind", "v1_corridor_surface_preview")
        _set_preview_property(preview_obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceId", surface_id)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
    return preview_obj


def create_corridor_subgrade_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
):
    """Create or update the first subgrade-surface mesh preview for a corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    surface_id = _surface_id(surface_model, "subgrade_surface") or f"{corridor_model.corridor_id}:subgrade"
    try:
        tin_surface = CorridorSurfaceGeometryService().build_subgrade_surface(
            CorridorDesignSurfaceGeometryRequest(
                project_id=_project_id(project or find_project(doc)),
                corridor=corridor_model,
                applied_section_set=applied_section_set,
                surface_id=surface_id,
            )
        )
    except Exception:
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorSubgradeSurfacePreview",
        label_prefix="Corridor Subgrade Surface",
        surface_role="subgrade",
    )
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _set_preview_property(preview_obj, "CRRecordKind", "v1_corridor_surface_preview")
        _set_preview_property(preview_obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceId", surface_id)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
    return preview_obj


def create_corridor_daylight_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
):
    """Create or update the first slope-face mesh preview for a corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    surface_id = _surface_id(surface_model, "daylight_surface") or f"{corridor_model.corridor_id}:daylight"
    try:
        tin_surface = CorridorSurfaceGeometryService().build_daylight_surface(
            CorridorDesignSurfaceGeometryRequest(
                project_id=_project_id(project or find_project(doc)),
                corridor=corridor_model,
                applied_section_set=applied_section_set,
                surface_id=surface_id,
                existing_ground_surface=_resolve_corridor_existing_ground_tin_surface(doc),
            )
        )
    except Exception:
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorDaylightSurfacePreview",
        label_prefix="Corridor Slope Face Surface",
        surface_role="daylight",
    )
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _set_preview_property(preview_obj, "CRRecordKind", "v1_corridor_surface_preview")
        _set_preview_property(preview_obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceId", surface_id)
        _attach_surface_quality_properties(preview_obj, tin_surface)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
        _create_slope_face_diagnostic_markers(
            document=doc,
            project=project or find_project(doc),
            surface=tin_surface,
            corridor_model=corridor_model,
        )
    return preview_obj


def create_corridor_drainage_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
):
    """Create or update the first ditch/drainage mesh preview for a corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    surface_id = _surface_id(surface_model, "drainage_surface")
    if not surface_id:
        _remove_preview_object(doc, "V1CorridorDrainageSurfacePreview")
        return None
    try:
        tin_surface = CorridorSurfaceGeometryService().build_drainage_surface(
            CorridorDesignSurfaceGeometryRequest(
                project_id=_project_id(project or find_project(doc)),
                corridor=corridor_model,
                applied_section_set=applied_section_set,
                surface_id=surface_id,
            )
        )
    except Exception:
        _remove_preview_object(doc, "V1CorridorDrainageSurfacePreview")
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorDrainageSurfacePreview",
        label_prefix="Corridor Drainage Surface",
        surface_role="drainage",
    )
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _set_preview_property(preview_obj, "CRRecordKind", "v1_corridor_surface_preview")
        _set_preview_property(preview_obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceId", surface_id)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
    return preview_obj


def run_v1_build_corridor_command():
    """Open the v1 Build Corridor panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    panel = V1BuildCorridorTaskPanel(document=App.ActiveDocument)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_corridor_model(App.ActiveDocument)


class V1BuildCorridorTaskPanel:
    """Small Apply-gated panel for v1 CorridorModel creation."""

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
        widget.setWindowTitle("CorridorRoad v1 - Build Corridor")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        title = QtWidgets.QLabel("Build Corridor")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        note = QtWidgets.QLabel(
            "Build the v1 CorridorModel from Applied Sections and create the first corridor-derived SurfaceModel. Solids remain a later physical-component step."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self._summary = QtWidgets.QPlainTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setFixedHeight(150)
        layout.addWidget(self._summary)
        self._review_table = QtWidgets.QTableWidget(0, 7)
        self._review_table.setHorizontalHeaderLabels(
            [
                "Result",
                "Status",
                "Object",
                "Vertices",
                "Triangles/Points",
                "Role",
                "Notes",
            ]
        )
        self._review_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._review_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._review_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        try:
            self._review_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._review_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_review_row(row_index))
        layout.addWidget(self._review_table, 1)
        row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_summary)
        row.addWidget(refresh_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        row.addWidget(apply_button)
        show_button = QtWidgets.QPushButton("Show Selected")
        show_button.clicked.connect(self._show_selected_row)
        row.addWidget(show_button)
        row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        row.addWidget(close_button)
        layout.addLayout(row)
        return widget

    def _refresh_summary(self):
        applied_obj = find_v1_applied_section_set(self.document)
        applied = to_applied_section_set(applied_obj)
        if applied is None:
            self._summary.setPlainText("Applied Sections: missing\nRun Applied Sections before Build Corridor.")
            self._set_review_rows(corridor_build_review_rows(self.document))
            return
        self._summary.setPlainText(
            "\n".join(
                [
                    f"Applied Sections: {applied.applied_section_set_id}",
                    f"Stations: {len(applied.station_rows)}",
                    f"Alignment: {applied.alignment_id}",
                    "",
                    "Click Apply to create or update the v1 CorridorModel.",
                ]
            )
        )
        self._set_review_rows(corridor_build_review_rows(self.document))

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            result = build_document_corridor_model(self.document)
            obj = apply_v1_corridor_model(document=self.document, corridor_model=result)
            surface_obj = find_v1_surface_model(self.document)
            surface_count = int(getattr(surface_obj, "SurfaceCount", 0) or 0) if surface_obj is not None else 0
            message = f"CorridorModel has been built.\nStations: {len(result.station_rows)}\nSurface rows: {surface_count}"
            self._summary.setPlainText(message + f"\nObject: {obj.Label}")
            self._set_review_rows(corridor_build_review_rows(self.document))
            _show_message(self.form, "Build Corridor", message)
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._summary.setPlainText(f"CorridorModel was not built:\n{exc}")
            _show_message(self.form, "Build Corridor", f"CorridorModel was not built.\n{exc}")
            return False

    def _set_review_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_review_table"):
            return
        self._review_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._review_table.rowCount()
            self._review_table.insertRow(row_index)
            values = [
                str(row.get("result", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("object_label", "") or row.get("object_name", "") or ""),
                str(row.get("vertex_count", "") or ""),
                str(row.get("triangle_or_point_count", "") or ""),
                str(row.get("role", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                self._review_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))

    def _show_selected_row(self) -> None:
        rows = self._review_table.selectionModel().selectedRows() if hasattr(self, "_review_table") else []
        if not rows:
            _show_message(self.form, "Build Corridor", "Select one review row first.")
            return
        self._show_review_row(int(rows[0].row()))

    def _show_review_row(self, row_index: int) -> None:
        try:
            obj = show_corridor_build_review_object(self.document, int(row_index))
            self._summary.setPlainText(f"Review object shown.\nObject: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}")
        except Exception as exc:
            _show_message(self.form, "Build Corridor", f"Review object was not shown.\n{exc}")


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _surface_id(surface_model, surface_kind: str) -> str:
    for row in list(getattr(surface_model, "surface_rows", []) or []):
        if str(getattr(row, "surface_kind", "") or "") == surface_kind:
            return str(getattr(row, "surface_id", "") or "")
    return ""


def _corridor_build_review_row(role: str, title: str, object_name: str, obj) -> dict[str, object]:
    if obj is None:
        return {
            "role": role,
            "result": title,
            "object_name": object_name,
            "object_label": "",
            "status": "missing",
            "vertex_count": "",
            "triangle_or_point_count": "",
            "notes": "Not built yet.",
        }
    if role == "centerline":
        point_count = int(getattr(obj, "PointCount", 0) or 0)
        curve_kind = str(getattr(obj, "DisplayCurveKind", "") or "")
        return {
            "role": role,
            "result": title,
            "object_name": str(getattr(obj, "Name", "") or object_name),
            "object_label": str(getattr(obj, "Label", "") or object_name),
            "status": "ready",
            "vertex_count": "",
            "triangle_or_point_count": point_count,
            "notes": f"Curve: {curve_kind or 'unknown'}",
        }
    vertex_count = int(getattr(obj, "VertexCount", 0) or 0)
    triangle_count = int(getattr(obj, "TriangleCount", 0) or 0)
    notes = str(getattr(obj, "SlopeFaceDiagnosticSummary", "") or "")
    if not notes:
        surface_kind = str(getattr(obj, "SurfaceKind", "") or "")
        notes = f"Surface kind: {surface_kind or 'unknown'}"
    return {
        "role": role,
        "result": title,
        "object_name": str(getattr(obj, "Name", "") or object_name),
        "object_label": str(getattr(obj, "Label", "") or object_name),
        "status": "ready" if vertex_count > 0 and triangle_count > 0 else "empty",
        "vertex_count": vertex_count,
        "triangle_or_point_count": triangle_count,
        "notes": notes,
    }


def _set_preview_property(obj, name: str, value: str) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyInteger", name, "CorridorRoad", name)
        setattr(obj, name, int(value or 0))
    except Exception:
        pass


def _set_preview_float_property(obj, name: str, value: float) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyFloat", name, "CorridorRoad", name)
        setattr(obj, name, float(value or 0.0))
    except Exception:
        pass


def _remove_preview_object(document, object_name: str) -> None:
    try:
        obj = document.getObject(object_name)
        if obj is not None:
            document.removeObject(obj.Name)
    except Exception:
        pass


def _centerline_points_from_applied_sections(applied_section_set, app_module):
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    rows = sorted(
        list(getattr(applied_section_set, "station_rows", []) or []),
        key=lambda row: float(getattr(row, "station", 0.0) or 0.0),
    )
    points = []
    stations = []
    for row in rows:
        section = sections.get(str(getattr(row, "applied_section_id", "") or ""))
        frame = getattr(section, "frame", None) if section is not None else None
        if frame is None:
            continue
        try:
            point = app_module.Vector(float(frame.x), float(frame.y), float(frame.z))
            station = float(getattr(frame, "station", getattr(row, "station", 0.0)) or 0.0)
        except Exception:
            continue
        if points and _same_centerline_point(points[-1], point):
            continue
        points.append(point)
        stations.append(station)
    return points, stations


def _same_centerline_point(left, right, tolerance: float = 1.0e-7) -> bool:
    try:
        return (
            abs(float(left.x) - float(right.x)) <= tolerance
            and abs(float(left.y) - float(right.y)) <= tolerance
            and abs(float(left.z) - float(right.z)) <= tolerance
        )
    except Exception:
        return False


def _select_and_fit_object(obj) -> None:
    if Gui is None or obj is None:
        return
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


def _make_centerline_shape(points, part_module):
    if len(points) < 2:
        return part_module.Shape(), "empty"
    if len(points) == 2:
        return part_module.makeLine(points[0], points[1]), "line"
    try:
        curve = part_module.BSplineCurve()
        curve.interpolate(points)
        return curve.toShape(), "spline"
    except Exception:
        edges = []
        for idx in range(len(points) - 1):
            try:
                edges.append(part_module.makeLine(points[idx], points[idx + 1]))
            except Exception:
                pass
        if not edges:
            return part_module.Shape(), "empty"
        return part_module.makeCompound(edges), "polyline_fallback"


def _attach_surface_quality_properties(obj, surface) -> None:
    quality = {str(getattr(row, "kind", "") or ""): getattr(row, "value", 0) for row in list(getattr(surface, "quality_rows", []) or [])}
    _set_preview_integer_property(obj, "EGTieInHitCount", int(float(quality.get("eg_tie_in_hit_count", 0) or 0)))
    _set_preview_integer_property(obj, "EGTieInMissCount", int(float(quality.get("eg_tie_in_miss_count", 0) or 0)))
    _set_preview_integer_property(obj, "EGIntersectionCount", int(float(quality.get("eg_intersection_count", 0) or 0)))
    _set_preview_integer_property(obj, "EGOuterEdgeSampleCount", int(float(quality.get("eg_outer_edge_sample_count", 0) or 0)))
    _set_preview_integer_property(obj, "SlopeFaceFallbackCount", int(float(quality.get("slope_face_fallback_count", 0) or 0)))
    _set_preview_integer_property(obj, "SlopeFaceNoExistingGroundCount", int(float(quality.get("slope_face_no_existing_ground_count", 0) or 0)))
    _set_preview_integer_property(obj, "SlopeFaceNoEGHitCount", int(float(quality.get("slope_face_no_eg_hit_count", 0) or 0)))
    summary = (
        f"EG intersections: {int(float(quality.get('eg_intersection_count', 0) or 0))}, "
        f"outer-edge samples: {int(float(quality.get('eg_outer_edge_sample_count', 0) or 0))}, "
        f"fallbacks: {int(float(quality.get('slope_face_fallback_count', 0) or 0))}, "
        f"no EG TIN: {int(float(quality.get('slope_face_no_existing_ground_count', 0) or 0))}, "
        f"no EG hit: {int(float(quality.get('slope_face_no_eg_hit_count', 0) or 0))}, "
        f"hits: {int(float(quality.get('eg_tie_in_hit_count', 0) or 0))}, "
        f"misses: {int(float(quality.get('eg_tie_in_miss_count', 0) or 0))}"
    )
    _set_preview_property(obj, "SlopeFaceDiagnosticSummary", summary)


def _create_slope_face_diagnostic_markers(*, document=None, project=None, surface=None, corridor_model=None):
    """Create visible 3D markers for slope-face EG tie-in states."""

    if document is None or surface is None:
        return []
    status_points = _slope_face_status_points(surface)
    if not status_points:
        _remove_slope_face_diagnostic_markers(document)
        return []
    marker_specs = [
        ("intersection", "ReviewIssueSlopeFaceIntersectionMarkers", "Slope Face EG Intersections", (0.10, 0.85, 0.25)),
        ("sampled_outer_edge", "ReviewIssueSlopeFaceSampledEdgeMarkers", "Slope Face Outer Edge Samples", (1.00, 0.72, 0.10)),
        ("fallback", "ReviewIssueSlopeFaceFallbackMarkers", "Slope Face Fallback / No Hit", (1.00, 0.18, 0.12)),
    ]
    radius = _marker_radius([point for points in status_points.values() for point in points])
    created = []
    for status_key, object_name, label, color in marker_specs:
        points = status_points.get(status_key, [])
        obj = _create_marker_compound(
            document=document,
            object_name=object_name,
            label=label,
            points=points,
            radius=radius,
            color=color,
            surface=surface,
            corridor_model=corridor_model,
        )
        if obj is not None:
            created.append(obj)
            try:
                from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

                route_to_v1_tree(project or find_project(document), obj)
            except Exception:
                pass
    return created


def _remove_slope_face_diagnostic_markers(document) -> None:
    for name in (
        "ReviewIssueSlopeFaceIntersectionMarkers",
        "ReviewIssueSlopeFaceSampledEdgeMarkers",
        "ReviewIssueSlopeFaceFallbackMarkers",
    ):
        try:
            obj = document.getObject(name)
            if obj is not None:
                document.removeObject(obj.Name)
        except Exception:
            pass


def _slope_face_status_points(surface) -> dict[str, list[tuple[float, float, float]]]:
    points: dict[str, list[tuple[float, float, float]]] = {
        "intersection": [],
        "sampled_outer_edge": [],
        "fallback": [],
    }
    for vertex in list(getattr(surface, "vertex_rows", []) or []):
        vertex_id = str(getattr(vertex, "vertex_id", "") or "")
        if not vertex_id.endswith(":outer"):
            continue
        status = str(getattr(vertex, "notes", "") or "")
        if status == "intersection":
            key = "intersection"
        elif status == "sampled_outer_edge":
            key = "sampled_outer_edge"
        else:
            key = "fallback"
        points[key].append((float(vertex.x), float(vertex.y), float(vertex.z)))
    return points


def _create_marker_compound(
    *,
    document,
    object_name: str,
    label: str,
    points: list[tuple[float, float, float]],
    radius: float,
    color: tuple[float, float, float],
    surface,
    corridor_model,
):
    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    obj = document.getObject(object_name)
    if not points:
        if obj is not None:
            try:
                document.removeObject(obj.Name)
            except Exception:
                pass
        return None
    shapes = []
    for x, y, z in points:
        try:
            shapes.append(Part.makeSphere(float(radius), AppModule.Vector(float(x), float(y), float(z))))
        except Exception:
            pass
    if not shapes:
        return None
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    try:
        obj.Shape = Part.makeCompound(shapes)
        obj.Label = label
    except Exception:
        return obj
    _set_preview_property(obj, "CRRecordKind", "v1_review_issue")
    _set_preview_property(obj, "V1ObjectType", "ReviewIssue")
    _set_preview_property(obj, "IssueKind", "slope_face_tie_in")
    _set_preview_property(obj, "SurfaceId", str(getattr(surface, "surface_id", "") or ""))
    _set_preview_property(obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
    _set_preview_integer_property(obj, "MarkerCount", len(points))
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.ShapeColor = color
            vobj.PointColor = color
            vobj.LineColor = color
            vobj.Transparency = 0
    except Exception:
        pass
    return obj


def _marker_radius(points: list[tuple[float, float, float]]) -> float:
    if not points:
        return 0.5
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    return max(0.15, min(2.0, float(span or 1.0) * 0.015))


def _resolve_corridor_existing_ground_tin_surface(document):
    """Resolve an EG TIN for corridor slope-face tie-in without selecting corridor previews."""

    if document is None:
        return None
    try:
        from .cmd_review_tin import _tin_surface_candidate_sort_key, _tin_surface_from_object
        from ..models.result.tin_surface import TINSurface
    except Exception:
        return None

    candidates = []
    if Gui is not None:
        try:
            candidates.extend(list(Gui.Selection.getSelection() or []))
        except Exception:
            pass
    project = find_project(document)
    if project is not None:
        try:
            terrain = getattr(project, "Terrain", None)
            if terrain is not None:
                candidates.append(terrain)
        except Exception:
            pass
    candidates.extend(list(getattr(document, "Objects", []) or []))

    seen = set()
    for obj in sorted(candidates, key=_tin_surface_candidate_sort_key):
        name = str(getattr(obj, "Name", "") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        if _skip_corridor_existing_ground_candidate(obj):
            continue
        try:
            surface = _tin_surface_from_object(obj, max_triangles=250000)
        except Exception:
            surface = None
        if isinstance(surface, TINSurface):
            return surface
    return None


def _skip_corridor_existing_ground_candidate(obj) -> bool:
    if obj is None:
        return True
    record_kind = str(getattr(obj, "CRRecordKind", "") or "")
    if record_kind == "v1_corridor_surface_preview":
        return True
    if record_kind == "v1_review_issue":
        return True
    if record_kind.startswith("profile_show_preview"):
        return True
    surface_role = str(getattr(obj, "SurfaceRole", "") or "").lower()
    if surface_role in {"design", "subgrade", "daylight", "drainage"}:
        return True
    surface_kind = str(getattr(obj, "SurfaceKind", "") or "").lower()
    if surface_kind in {"design_surface", "subgrade_surface", "daylight_surface", "drainage_surface"}:
        return True
    v1_type = str(getattr(obj, "V1ObjectType", "") or "")
    if v1_type in {"V1Alignment", "V1Profile", "V1Stationing", "V1CorridorModel", "V1SurfaceModel", "ReviewIssue"}:
        return True
    preview_role = str(getattr(obj, "PreviewRole", "") or "").lower()
    if preview_role in {"boundary", "void"}:
        return True
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    if name.startswith("ReviewIssue"):
        return True
    if name.startswith(("CRV1_TIN_Boundary_Rectangle_Preview", "CRV1_TIN_Void_Rectangle_Preview")):
        return True
    if label.startswith(("TIN Boundary Rectangle Preview", "TIN Void Rectangle Preview")):
        return True
    return False


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass

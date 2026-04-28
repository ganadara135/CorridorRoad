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
    try:
        doc.recompute()
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
        row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_summary)
        row.addWidget(refresh_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        row.addWidget(apply_button)
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

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            result = build_document_corridor_model(self.document)
            obj = apply_v1_corridor_model(document=self.document, corridor_model=result)
            surface_obj = find_v1_surface_model(self.document)
            surface_count = int(getattr(surface_obj, "SurfaceCount", 0) or 0) if surface_obj is not None else 0
            message = f"CorridorModel has been built.\nStations: {len(result.station_rows)}\nSurface rows: {surface_count}"
            self._summary.setPlainText(message + f"\nObject: {obj.Label}")
            _show_message(self.form, "Build Corridor", message)
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._summary.setPlainText(f"CorridorModel was not built:\n{exc}")
            _show_message(self.form, "Build Corridor", f"CorridorModel was not built.\n{exc}")
            return False


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _surface_id(surface_model, surface_kind: str) -> str:
    for row in list(getattr(surface_model, "surface_rows", []) or []):
        if str(getattr(row, "surface_kind", "") or "") == surface_kind:
            return str(getattr(row, "surface_id", "") or "")
    return ""


def _set_preview_property(obj, name: str, value: str) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass

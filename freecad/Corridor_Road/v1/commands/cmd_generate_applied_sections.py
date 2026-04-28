"""Applied Sections generation command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

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
)
from ..objects.obj_assembly import find_v1_assembly_model, to_assembly_model
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
    assembly_obj = find_v1_assembly_model(doc)
    region_obj = find_v1_region_model(doc)
    stationing_obj = find_v1_stationing(doc)

    alignment = to_alignment_model(alignment_obj)
    profile = to_profile_model(profile_obj)
    assembly = to_assembly_model(assembly_obj)
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
                f"Assembly: {_source_status(find_v1_assembly_model(self.document))}",
                f"Regions: {_source_status(find_v1_region_model(self.document))}",
                f"Stations: {station_count} row(s)",
                "",
                "Click Apply to create or update the v1 AppliedSectionSet result.",
            ]
            self._summary.setPlainText("\n".join(lines))
        except Exception as exc:
            self._summary.setPlainText(f"Summary failed:\n{exc}")

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            result = build_document_applied_section_set(self.document)
            obj = apply_v1_applied_section_set(document=self.document, applied_section_set=result)
            diagnostic_count = sum(len(section.diagnostic_rows) for section in result.sections)
            message = f"Applied Sections have been built.\nStations: {len(result.station_rows)}\nDiagnostics: {diagnostic_count}"
            self._summary.setPlainText(message + f"\nObject: {obj.Label}")
            _show_message(self.form, "Applied Sections", message)
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._summary.setPlainText(f"Applied Sections were not built:\n{exc}")
            _show_message(self.form, "Applied Sections", f"Applied Sections were not built.\n{exc}")
            return False


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


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1AppliedSections", CmdV1AppliedSections())

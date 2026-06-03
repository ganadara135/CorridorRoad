"""Civil 3D LandXML import command for Parametric Road v1."""

from __future__ import annotations

from pathlib import Path

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is unavailable in plain Python.
    App = None
try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCADGui is unavailable in plain Python.
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path, resource_path
from freecad.Corridor_Road.qt_compat import QtWidgets

from ..exchange.landxml_alignment_mapper import create_or_update_alignment_from_landxml_candidate
from ..exchange.landxml_import import scan_landxml_file
from ..exchange.landxml_import_contracts import LandXMLImportResult
from ..exchange.landxml_profile_mapper import create_or_update_profile_from_landxml_candidate
from ..exchange.landxml_surface_mapper import create_or_update_surface_from_landxml_candidate
from ..objects.obj_landxml_import import create_or_update_v1_landxml_import_object


LANDXML_IMPORT_COMMAND_ID = "CorridorRoad_V1ImportLandXML"
SUPPORTED_FORMAT_TEXT = "Supported source: Autodesk Civil 3D LandXML"
SUPPORTED_CONTENT_TEXT = "Supported content: Alignment, Profile, TIN Surface, CgPoints"
UNSUPPORTED_TEXT = "Not supported in this phase: OpenRoads LandXML, full Corridor reconstruction, Pipe Networks, Assemblies, Regions"
NEXT_WORKFLOW_TEXT = (
    "Next workflow: LandXML Import -> Stations -> 3D Centerline -> Superelevation -> "
    "Assembly -> Regions -> Structures/Drainage -> Build Sections"
)
LANDXML_PRESETS = {
    "Civil 3D Starter Road": {
        "path": ("presets", "landxml", "civil3d_starter_road.xml"),
        "note": "Larger Civil 3D sample with a multi-element alignment, finished-grade profile, EG TIN surface, and CgPoints.",
    },
}


def landxml_preset_names() -> list[str]:
    """Return user-facing LandXML preset names."""

    return list(LANDXML_PRESETS.keys())


def landxml_preset_path(preset_name: str) -> str:
    """Return an absolute package path for a named LandXML preset."""

    preset = LANDXML_PRESETS.get(str(preset_name or "").strip())
    if not preset:
        return ""
    return resource_path(*preset["path"])


class V1LandXMLImportTaskPanel:
    """Small scan-first Civil 3D LandXML import panel."""

    def __init__(self, *, document=None, project=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.project = project or _find_project(self.document)
        self.result: LandXMLImportResult | None = None

        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle("Import LandXML")
        layout = QtWidgets.QVBoxLayout(self.form)

        title = QtWidgets.QLabel("Import Civil 3D LandXML")
        try:
            title.setStyleSheet("font-weight: 600; font-size: 15px;")
        except Exception:
            pass
        layout.addWidget(title)

        self.lbl_supported = QtWidgets.QLabel(
            "\n".join([SUPPORTED_FORMAT_TEXT, SUPPORTED_CONTENT_TEXT, UNSUPPORTED_TEXT])
        )
        self.lbl_supported.setWordWrap(True)
        layout.addWidget(self.lbl_supported)

        self.lbl_next_workflow = QtWidgets.QLabel(NEXT_WORKFLOW_TEXT)
        self.lbl_next_workflow.setWordWrap(True)
        try:
            self.lbl_next_workflow.setStyleSheet("color: #78f0a0;")
        except Exception:
            pass
        layout.addWidget(self.lbl_next_workflow)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        self.cbo_preset = QtWidgets.QComboBox()
        self.cbo_preset.addItems(landxml_preset_names())
        preset_row.addWidget(self.cbo_preset)
        self.btn_preset = QtWidgets.QPushButton("Preset Data")
        preset_row.addWidget(self.btn_preset)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        file_row = QtWidgets.QHBoxLayout()
        file_row.addWidget(QtWidgets.QLabel("File:"))
        self.txt_file = QtWidgets.QLineEdit()
        file_row.addWidget(self.txt_file, 1)
        self.btn_browse = QtWidgets.QPushButton("Browse")
        file_row.addWidget(self.btn_browse)
        layout.addLayout(file_row)

        actions = QtWidgets.QHBoxLayout()
        self.btn_scan = QtWidgets.QPushButton("Scan File")
        self.btn_import = QtWidgets.QPushButton("Import Selected")
        self.btn_close = QtWidgets.QPushButton("Close")
        actions.addWidget(self.btn_scan)
        actions.addWidget(self.btn_import)
        actions.addStretch(1)
        actions.addWidget(self.btn_close)
        layout.addLayout(actions)

        self.txt_summary = QtWidgets.QTextEdit()
        self.txt_summary.setReadOnly(True)
        self.txt_summary.setMinimumHeight(150)
        layout.addWidget(self.txt_summary)

        self.txt_diagnostics = QtWidgets.QTextEdit()
        self.txt_diagnostics.setReadOnly(True)
        self.txt_diagnostics.setMinimumHeight(140)
        layout.addWidget(self.txt_diagnostics)

        self.btn_import.setEnabled(False)
        self.btn_preset.clicked.connect(self._load_selected_preset)
        self.btn_browse.clicked.connect(self._browse)
        self.btn_scan.clicked.connect(self.scan_file)
        self.btn_import.clicked.connect(self.import_selected)
        self.btn_close.clicked.connect(self.reject)
        self._set_summary("Select a Civil 3D LandXML file, then click Scan File.")
        self._set_diagnostics("")

    def accept(self):
        return True

    def reject(self):
        if Gui is not None:
            try:
                Gui.Control.closeDialog()
            except Exception:
                pass
        return True

    def _browse(self):
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self.form,
            "Select Civil 3D LandXML",
            "",
            "LandXML Files (*.xml *.landxml);;XML Files (*.xml);;All Files (*.*)",
        )
        if path:
            self.txt_file.setText(str(path))

    def _load_selected_preset(self):
        preset_name = str(self.cbo_preset.currentText() or "").strip()
        path = landxml_preset_path(preset_name)
        if not path:
            self._set_summary("No LandXML preset is selected.")
            self._set_diagnostics("warning: Select a LandXML preset first.")
            self.btn_import.setEnabled(False)
            return None
        if not Path(path).exists():
            self._set_summary(f"LandXML preset file is missing: {preset_name}")
            self._set_diagnostics(f"error: Preset file not found: {path}")
            self.btn_import.setEnabled(False)
            return None
        self.txt_file.setText(path)
        result = self.scan_file()
        if result is not None:
            note = str(LANDXML_PRESETS.get(preset_name, {}).get("note", "") or "")
            self._set_summary(f"Preset Data loaded: {preset_name}\n{note}\n\n{_summary_text(result)}")
        return result

    def scan_file(self):
        path = str(self.txt_file.text() or "").strip()
        if not path:
            self._set_summary("No LandXML file selected.")
            self._set_diagnostics("warning: Select a .xml or .landxml file first.")
            self.btn_import.setEnabled(False)
            return None
        result = scan_landxml_file(path)
        self.result = result
        self._set_summary(_summary_text(result))
        self._set_diagnostics(_diagnostic_text(result))
        self.btn_import.setEnabled(bool(result.summary.supported_producer))
        return result

    def import_selected(self):
        if self.result is None:
            self.scan_file()
        result = self.result
        if result is None:
            return None
        if not result.summary.supported_producer:
            self._set_diagnostics(_diagnostic_text(result) + "\nerror: Unsupported producer. Import is disabled.")
            self.btn_import.setEnabled(False)
            return None
        try:
            created = import_landxml_result_into_document(result, self.document, project=self.project)
        except Exception as exc:
            self._set_diagnostics(_diagnostic_text(result) + f"\nerror: {exc}")
            return None
        lines = ["Import completed.", "", "Created or updated:"] + [f"- {line}" for line in created]
        if result.summary.cgpoint_count:
            lines.extend(["", f"CgPoints detected: {result.summary.cgpoint_count} (source object import is planned after surface/profile MVP)."])
        self._set_summary("\n".join(lines))
        self._set_diagnostics(_diagnostic_text(result))
        return created

    def _set_summary(self, text: str) -> None:
        self.txt_summary.setPlainText(str(text or ""))

    def _set_diagnostics(self, text: str) -> None:
        self.txt_diagnostics.setPlainText(str(text or ""))


def import_landxml_file_into_document(path: str, document=None, *, project=None) -> list[str]:
    """Scan and import one supported Civil 3D LandXML file into a FreeCAD document."""

    return import_landxml_result_into_document(scan_landxml_file(path), document, project=project)


def import_landxml_result_into_document(
    result: LandXMLImportResult,
    document=None,
    *,
    project=None,
) -> list[str]:
    """Import parsed LandXML candidates into v1 document objects."""

    if result is None:
        raise ValueError("No LandXML scan result is available.")
    if not result.summary.supported_producer:
        raise ValueError("Unsupported LandXML producer. Only Autodesk Civil 3D LandXML is supported in this phase.")
    if document is None:
        document = getattr(App, "ActiveDocument", None) if App is not None else None
    if document is None:
        raise RuntimeError("No active FreeCAD document is available.")

    created: list[str] = []
    for alignment in result.alignments:
        obj = create_or_update_alignment_from_landxml_candidate(document, alignment, project=project)
        created.append(f"Alignment: {str(getattr(obj, 'Label', '') or getattr(obj, 'Name', '') or alignment.name)}")
    for profile in result.profiles:
        obj = create_or_update_profile_from_landxml_candidate(document, profile, project=project)
        created.append(f"Profile: {str(getattr(obj, 'Label', '') or getattr(obj, 'Name', '') or profile.name)}")
    for surface in result.surfaces:
        imported = create_or_update_surface_from_landxml_candidate(document, surface, project=project)
        created.append(f"TIN Surface: {str(getattr(imported.surface_model_object, 'Label', '') or surface.name)}")
    create_or_update_v1_landxml_import_object(
        document,
        project=project,
        result=result,
        created_refs=created,
    )
    try:
        document.recompute()
    except Exception:
        pass
    return created


class CmdV1ImportLandXML:
    """Open the Civil 3D LandXML import panel."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("landxml_import.svg"),
            "MenuText": "Import LandXML",
            "ToolTip": "Import supported Autodesk Civil 3D LandXML Alignment, Profile, TIN Surface, and CgPoints data",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        if Gui is None:
            return
        panel = V1LandXMLImportTaskPanel()
        Gui.Control.showDialog(panel)


def _summary_text(result: LandXMLImportResult) -> str:
    summary = result.summary
    status = "Supported" if summary.supported_producer else "Not supported in this phase"
    return "\n".join(
        [
            SUPPORTED_FORMAT_TEXT,
            SUPPORTED_CONTENT_TEXT,
            UNSUPPORTED_TEXT,
            "",
            f"Producer: {summary.detected_producer or 'Unknown'}",
            f"Producer Status: {status}",
            f"LandXML Version: {summary.landxml_version or '-'}",
            f"Linear Unit: {summary.linear_unit or '-'}",
            "",
            "Detected Content:",
            f"- Alignments: {summary.alignment_count}",
            f"- Profiles: {summary.profile_count}",
            f"- TIN Surfaces: {summary.surface_count}",
            f"- CgPoints: {summary.cgpoint_count}",
            "",
            "Import action:",
            "- Supported producer: Import Selected creates/updates Alignment, Profile, and TIN Surface objects.",
            "- Unsupported producer: diagnostics only; import remains disabled.",
        ]
    )


def _diagnostic_text(result: LandXMLImportResult) -> str:
    if not result.diagnostics:
        return "Diagnostics: none"
    lines = ["Diagnostics:"]
    for row in result.diagnostics:
        context = f" | {row.context}" if row.context else ""
        lines.append(f"{row.severity}: {row.code}: {row.message}{context}")
    return "\n".join(lines)


def _find_project(document):
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if str(getattr(obj, "Name", "") or "").startswith("CorridorRoadProject"):
            return obj
    return None


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand(LANDXML_IMPORT_COMMAND_ID, CmdV1ImportLandXML())

"""Watertight Solids final-stage command for CorridorRoad v1."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from types import SimpleNamespace

try:
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None
    Part = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from ..objects.obj_applied_section import find_v1_applied_section_set
from ..objects.obj_applied_section import to_applied_section_set
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_corridor import find_v1_corridor_model, to_corridor_model
from ..objects.obj_drainage import find_v1_drainage_model, to_drainage_model
from ..objects.obj_intersection import find_v1_intersection_model, to_intersection_model
from ..objects.obj_intersection_trim_boundary import (
    create_or_update_v1_intersection_trim_boundary_result_object,
    find_v1_intersection_trim_boundary_result,
    to_intersection_trim_boundary_result,
)
from ..objects.obj_region import find_v1_region_model, to_region_model
from ..objects.obj_structure import find_v1_structure_model, to_structure_model
from ..objects.obj_surface import find_v1_surface_model
from ..objects.obj_watertight_solid import create_or_update_v1_watertight_solid_output_object
from ..objects.obj_simulation_qa import create_or_update_v1_simulation_qa_output_object
from ..objects.obj_simulation_package import create_or_update_v1_simulation_package_output_object, find_v1_simulation_package_output
from ..exchange import export_simulation_package_to_json
from ..models.output.watertight_solid_output import WatertightSolidOutput, WatertightSolidOutputRow, WatertightSolidSegmentRow
from ..models.result.intersection_trim_boundary import IntersectionTrimBoundaryPair, IntersectionTrimBoundaryResult
from ..services.builders import (
    AppliedSectionSolidProfileService,
    SolidEdgeNetworkBuildRequest,
    SolidEdgeNetworkService,
    SolidProfileBuildRequest,
    SolidTargetDiscoveryRequest,
    SolidTargetDiscoveryService,
    StructureSolidBuildRequest,
    StructureSolidOutputService,
    WatertightSimulationQaBuildRequest,
    WatertightSimulationQaService,
    WatertightSimulationQaSolidInput,
    WatertightSimulationPackageBuildRequest,
    WatertightSimulationPackageService,
)
from ..services.evaluation.drainage_resolution_service import build_drainage_pipeline_segment_candidates
from ..services.mapping import (
    DrainageReviewMapper,
    WatertightSolidOutputMapper,
    WatertightSolidOutputMappingRequest,
    WatertightSolidPartMapper,
)


WATERTIGHT_SOLIDS_COMMAND_ID = "CorridorRoad_V1WatertightSolids"
WATERTIGHT_SOLIDS_BLOCKED_MESSAGE = "Run Build Corridor before generating watertight solids."


@dataclass(frozen=True)
class WatertightSolidPrerequisiteStatus:
    """Readiness summary for the v1 Watertight Solids final stage."""

    document_ready: bool = False
    applied_sections_ready: bool = False
    corridor_model_ready: bool = False
    surface_model_ready: bool = False
    build_parametric_ready: bool = True
    build_parametric_diagnostic_count: int = 0
    ready: bool = False
    messages: tuple[str, ...] = ()

    def table_rows(self) -> list[tuple[str, str, str]]:
        """Return display rows for the prerequisite table."""

        return [
            ("Document", _ready_label(self.document_ready), "Open FreeCAD document."),
            ("Applied Sections", _ready_label(self.applied_sections_ready), "Generate Applied Sections."),
            ("CorridorModel", _ready_label(self.corridor_model_ready), "Run Build Corridor."),
            ("SurfaceModel", _ready_label(self.surface_model_ready), "Build Corridor surface result."),
            (
                "Build Parametric Diagnostics",
                _ready_label(self.build_parametric_ready),
                "Resolve blocking Build Parametric diagnostics." if not self.build_parametric_ready else "No blocking Build Parametric diagnostics.",
            ),
        ]


@dataclass
class WatertightSolidTargetPanelState:
    """Mutable UI state for one discovered solid target row."""

    target_id: str
    target_row: object
    enabled: bool = False
    validation_status: str = "not_validated"
    profile_count: int = 0
    face_count: int = 0
    edge_count: int = 0
    build_status: str = "not_built"
    volume: float = 0.0
    output_object_ref: str = ""
    validation_message: str = ""
    profile_set: object | None = None
    edge_network: object | None = None
    part_result: object | None = None
    watertight_output: object | None = None
    output_object: object | None = None


@dataclass(frozen=True)
class DrainagePipelineNetworkShapeResult:
    """Part shape plus network fuse metadata for Drainage pipeline builds."""

    shape: object
    fuse_mode: str = "compound_fallback"
    connector_count: int = 0
    structure_body_count: int = 0
    port_connector_count: int = 0
    endpoint_trim_count: int = 0
    structure_port_terminal_count: int = 0
    structure_port_contact_status: str = "not_checked"
    notes: str = ""


@dataclass(frozen=True)
class DrainageWatertightHandoffSummary:
    """Drainage-specific readiness summary for Watertight Solid handoff."""

    source_status: str = "missing"
    flow_route_count: int = 0
    capture_only_route_count: int = 0
    pipe_candidate_count: int = 0
    unresolved_port_route_count: int = 0
    missing_element_route_count: int = 0
    lined_ditch_target_count: int = 0
    pipe_segment_target_count: int = 0
    pipeline_network_target_count: int = 0
    structure_body_target_count: int = 0
    built_drainage_output_count: int = 0
    network_fuse_status: str = "not_available"

    @property
    def readiness_status(self) -> str:
        if self.source_status != "ready":
            return "missing"
        if self.unresolved_port_route_count > 0 or self.missing_element_route_count > 0:
            return "blocked"
        if self.pipe_candidate_count <= 0 and self.lined_ditch_target_count <= 0:
            return "check"
        return "ready"


@dataclass(frozen=True)
class IntersectionWatertightHandoffSummary:
    """Intersection-specific readiness summary for Watertight Solid handoff."""

    source_status: str = "missing"
    intersection_id: str = ""
    target_count: int = 0
    pavement_target_count: int = 0
    subgrade_target_count: int = 0
    slope_target_count: int = 0
    curb_return_target_count: int = 0
    triangulation_mode: str = ""
    surface_boundary_strategy: str = ""
    exclusion_boundary_strategy: str = ""
    exclusion_practical_aligned: bool = False
    edge_blend_face_count: int = 0
    curb_return_arc_count: int = 0
    curb_return_arc_segment_count: int = 0
    min_triangle_quality: float = 0.0
    skinny_triangle_count: int = 0
    patch_boundary_status: str = ""
    review_summary: str = ""
    patch_quality_summary: str = ""

    @property
    def readiness_status(self) -> str:
        if self.source_status != "ready":
            return "missing"
        if self.target_count <= 0:
            return "missing"
        if not self.surface_boundary_strategy:
            return "check"
        if self.patch_boundary_status and self.patch_boundary_status.lower() not in {"yes", "true", "1", "closed"}:
            return "blocked"
        if self.skinny_triangle_count > 0:
            return "check"
        if self.exclusion_boundary_strategy and not self.exclusion_practical_aligned:
            return "check"
        return "ready"


def watertight_solid_prerequisite_status(document=None) -> WatertightSolidPrerequisiteStatus:
    """Return whether the current document can open the Watertight Solids build path."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return WatertightSolidPrerequisiteStatus(
            document_ready=False,
            messages=("Open a FreeCAD document before generating watertight solids.",),
        )
    applied_ready = find_v1_applied_section_set(doc) is not None
    corridor_ready = find_v1_corridor_model(doc) is not None
    surface_ready = find_v1_surface_model(doc) is not None
    build_parametric = _build_parametric_prerequisite_summary(doc)
    messages: list[str] = []
    if not applied_ready:
        messages.append("Generate Applied Sections before Watertight Solids.")
    if not corridor_ready:
        messages.append("Run Build Corridor to create a CorridorModel.")
    if not surface_ready:
        messages.append("Run Build Corridor to create a SurfaceModel.")
    for diagnostic in build_parametric["diagnostics"]:
        messages.append(str(diagnostic))
    ready = bool(applied_ready and corridor_ready and surface_ready and build_parametric["ready"])
    if ready:
        messages.append("Build Corridor prerequisites are ready. Solid target discovery is available.")
    else:
        messages.insert(0, WATERTIGHT_SOLIDS_BLOCKED_MESSAGE)
    return WatertightSolidPrerequisiteStatus(
        document_ready=True,
        applied_sections_ready=applied_ready,
        corridor_model_ready=corridor_ready,
        surface_model_ready=surface_ready,
        build_parametric_ready=bool(build_parametric["ready"]),
        build_parametric_diagnostic_count=len(build_parametric["diagnostics"]),
        ready=ready,
        messages=tuple(messages),
    )


def _build_parametric_prerequisite_summary(document) -> dict[str, object]:
    """Return blocking Build Parametric diagnostics for Watertight Solids."""

    if document is None:
        return {"ready": False, "diagnostics": ["Open a FreeCAD document before checking Build Parametric outputs."]}
    try:
        from .cmd_build_corridor import corridor_build_review_rows
    except Exception:
        return {"ready": True, "diagnostics": []}
    try:
        rows = corridor_build_review_rows(document)
    except Exception as exc:
        return {"ready": False, "diagnostics": [f"Build Parametric diagnostics could not be read: {exc}"]}
    blocking_roles = {"design", "subgrade", "daylight"}
    diagnostics: list[str] = []
    for row in list(rows or []):
        role = str(row.get("role", "") or "")
        status = str(row.get("status", "") or "")
        notes = str(row.get("notes", "") or "")
        if role in blocking_roles and status == "error":
            diagnostics.append(f"Build Parametric {role} preview is blocking Watertight Solids: {notes}")
        elif role in blocking_roles and status == "missing" and notes and notes != "Not built yet.":
            diagnostics.append(f"Build Parametric {role} preview is missing: {notes}")
    return {"ready": not diagnostics, "diagnostics": diagnostics}


def _route_existing_watertight_solid_outputs_to_tree(document=None) -> int:
    """Route existing Watertight Solid output objects into the v1 tree."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return 0
    project = find_project(doc)
    if project is None:
        return 0
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree
    except Exception:
        return 0
    routed = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if _is_watertight_output_object(obj):
            try:
                if route_to_v1_tree(project, obj) is not None:
                    routed += 1
            except Exception:
                pass
    return routed


def discover_watertight_solid_targets(document=None):
    """Return the currently discoverable watertight solid target model."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    applied_obj = find_v1_applied_section_set(doc)
    corridor_obj = find_v1_corridor_model(doc)
    region_obj = find_v1_region_model(doc)
    intersection_obj = find_v1_intersection_model(doc)
    structure_obj = find_v1_structure_model(doc)
    drainage_obj = find_v1_drainage_model(doc)
    applied = to_applied_section_set(applied_obj)
    corridor = to_corridor_model(corridor_obj)
    region_model = to_region_model(region_obj)
    intersection_model = to_intersection_model(intersection_obj)
    structure_model = to_structure_model(structure_obj)
    drainage_model = to_drainage_model(drainage_obj)
    target_model = SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id=str(getattr(applied, "project_id", "") or getattr(corridor, "project_id", "") or "corridorroad-v1"),
            corridor_ref=str(getattr(corridor, "corridor_id", "") or "corridor:main"),
            applied_section_set=applied,
            corridor_model=corridor,
            region_model=region_model,
            intersection_model=intersection_model,
            structure_model=structure_model,
            drainage_model=drainage_model,
        )
    )
    return _annotate_intersection_watertight_handoff_targets(target_model, doc)


class V1WatertightSolidsTaskPanel:
    """Placeholder task panel for the final v1 Watertight Solids stage."""

    def __init__(self, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        _route_existing_watertight_solid_outputs_to_tree(self.document)
        self._status_model = watertight_solid_prerequisite_status(self.document)
        self._target_model = discover_watertight_solid_targets(self.document)
        self._target_state_by_id: dict[str, WatertightSolidTargetPanelState] = {}
        self._selected_target_id = ""
        self._updating_target_table = False
        self.form = self._build_ui()

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - Watertight Solids")
        layout = QtWidgets.QVBoxLayout(widget)

        title = QtWidgets.QLabel("Watertight Solids")
        try:
            title.setStyleSheet("font-size: 18px; font-weight: 600;")
        except Exception:
            pass
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Final topology-first solid stage. Build Corridor must run first.")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self._prerequisite_table = QtWidgets.QTableWidget(0, 3)
        self._prerequisite_table.setHorizontalHeaderLabels(["Prerequisite", "Status", "Next Action"])
        self._prerequisite_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self._prerequisite_table)
        self._set_prerequisite_rows(self._status_model)

        self._target_table = QtWidgets.QTableWidget(0, 14)
        self._target_table.setHorizontalHeaderLabels(
            [
                "Enabled",
                "Target",
                "Family",
                "Scope",
                "Source",
                "Status",
                "Validation",
                "Profiles",
                "Faces",
                "Edges",
                "Build",
                "Volume",
                "Output",
                "Diagnostics",
            ]
        )
        self._target_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._target_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._target_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._target_table.itemSelectionChanged.connect(self._target_selection_changed)
        self._target_table.itemChanged.connect(self._target_item_changed)
        self._target_table.itemDoubleClicked.connect(self._focus_target_row_output)
        layout.addWidget(self._target_table, 1)
        self._set_target_rows(list(getattr(self._target_model, "target_rows", []) or []))

        qa_label = QtWidgets.QLabel("Simulation QA")
        layout.addWidget(qa_label)

        self._qa_tabs = QtWidgets.QTabWidget()
        self._qa_family_table = QtWidgets.QTableWidget(0, 4)
        self._qa_family_table.setHorizontalHeaderLabels(["Family", "Status", "Outputs", "Volume"])
        self._qa_family_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._qa_family_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._qa_tabs.addTab(self._qa_family_table, "Families")

        self._qa_diagnostic_table = QtWidgets.QTableWidget(0, 4)
        self._qa_diagnostic_table.setHorizontalHeaderLabels(["Severity", "Kind", "Source", "Message"])
        self._qa_diagnostic_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._qa_diagnostic_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._qa_tabs.addTab(self._qa_diagnostic_table, "Diagnostics")
        layout.addWidget(self._qa_tabs)
        self._refresh_simulation_qa_tables()

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setMinimumHeight(92)
        self._status.setPlainText(self._status_text())
        layout.addWidget(self._status)

        button_group = QtWidgets.QVBoxLayout()
        button_group.setSpacing(6)
        button_row = QtWidgets.QHBoxLayout()
        self._refresh_button = QtWidgets.QPushButton("Refresh")
        self._refresh_button.clicked.connect(self._refresh)
        button_row.addWidget(self._refresh_button)
        self._validate_button = QtWidgets.QPushButton("Validate")
        self._validate_button.setEnabled(False)
        self._validate_button.setToolTip("Select an available solid target to validate.")
        self._validate_button.clicked.connect(self._validate_selected_target)
        button_row.addWidget(self._validate_button)
        self._build_selected_button = QtWidgets.QPushButton("Build Selected")
        self._build_selected_button.setEnabled(False)
        self._build_selected_button.setToolTip("Build Selected is enabled after target validation is wired.")
        self._build_selected_button.clicked.connect(self._build_selected_target)
        button_row.addWidget(self._build_selected_button)
        self._build_enabled_button = QtWidgets.QPushButton("Build Enabled")
        self._build_enabled_button.setEnabled(False)
        self._build_enabled_button.setToolTip("Bulk build is enabled after validation/build execution is wired.")
        self._build_enabled_button.clicked.connect(self._build_enabled_targets)
        button_row.addWidget(self._build_enabled_button)
        self._build_package_button = QtWidgets.QPushButton("Build Package")
        self._build_package_button.setEnabled(False)
        self._build_package_button.setToolTip("Create or update the Simulation Package manifest from built solids and Simulation QA.")
        self._build_package_button.clicked.connect(self._build_simulation_package)
        button_row.addWidget(self._build_package_button)
        button_row.addStretch(1)
        button_group.addLayout(button_row)

        secondary_button_row = QtWidgets.QHBoxLayout()
        self._export_package_button = QtWidgets.QPushButton("Export Package")
        self._export_package_button.setEnabled(False)
        self._export_package_button.setToolTip("Export the persisted Simulation Package manifest to JSON.")
        self._export_package_button.clicked.connect(self._export_simulation_package_json)
        secondary_button_row.addWidget(self._export_package_button)
        self._show_button = QtWidgets.QPushButton("Show Solid")
        self._show_button.setEnabled(False)
        self._show_button.setToolTip("Show the selected built solid output.")
        self._show_button.clicked.connect(self._show_selected_solid)
        secondary_button_row.addWidget(self._show_button)
        self._hide_button = QtWidgets.QPushButton("Hide Solid")
        self._hide_button.setEnabled(False)
        self._hide_button.setToolTip("Hide the selected built solid output.")
        self._hide_button.clicked.connect(self._hide_selected_solid)
        secondary_button_row.addWidget(self._hide_button)
        self._focus_button = QtWidgets.QPushButton("Focus Solid")
        self._focus_button.setEnabled(False)
        self._focus_button.setToolTip("Select and focus the selected built solid output.")
        self._focus_button.clicked.connect(self._focus_selected_solid)
        secondary_button_row.addWidget(self._focus_button)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(_close_dialog)
        secondary_button_row.addWidget(close_button)
        secondary_button_row.addStretch(1)
        button_group.addLayout(secondary_button_row)
        layout.addLayout(button_group)

        self._update_action_state()
        return widget

    def _refresh(self) -> None:
        _route_existing_watertight_solid_outputs_to_tree(self.document)
        self._status_model = watertight_solid_prerequisite_status(self.document)
        self._target_model = discover_watertight_solid_targets(self.document)
        self._set_prerequisite_rows(self._status_model)
        self._set_target_rows(list(getattr(self._target_model, "target_rows", []) or []))
        self._refresh_simulation_qa_tables()
        self._status.setPlainText(self._status_text())

    def _set_prerequisite_rows(self, status: WatertightSolidPrerequisiteStatus) -> None:
        rows = status.table_rows()
        self._prerequisite_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                self._prerequisite_table.setItem(row_index, col_index, QtWidgets.QTableWidgetItem(str(value)))
        _stretch_last_column(self._prerequisite_table)

    def _set_target_rows(self, rows: list[object]) -> None:
        previous_selected_target_id = self._selected_target_id
        previous_state_by_id = dict(self._target_state_by_id)
        self._updating_target_table = True
        self._selected_target_id = ""
        self._target_state_by_id = {}
        self._target_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            target_id = _target_id(row)
            previous_state = previous_state_by_id.get(target_id)
            enabled = bool(getattr(previous_state, "enabled", getattr(row, "enabled", False)))
            state = WatertightSolidTargetPanelState(
                target_id=target_id,
                target_row=row,
                enabled=enabled,
                validation_status=str(getattr(previous_state, "validation_status", "not_validated") or "not_validated"),
                profile_count=int(getattr(previous_state, "profile_count", 0) or 0),
                face_count=int(getattr(previous_state, "face_count", 0) or 0),
                edge_count=int(getattr(previous_state, "edge_count", 0) or 0),
                build_status=str(getattr(previous_state, "build_status", "not_built") or "not_built"),
                volume=float(getattr(previous_state, "volume", 0.0) or 0.0),
                output_object_ref=str(getattr(previous_state, "output_object_ref", "") or ""),
                validation_message=str(getattr(previous_state, "validation_message", "") or ""),
                profile_set=getattr(previous_state, "profile_set", None),
                edge_network=getattr(previous_state, "edge_network", None),
                part_result=getattr(previous_state, "part_result", None),
                watertight_output=getattr(previous_state, "watertight_output", None),
                output_object=getattr(previous_state, "output_object", None),
            )
            self._target_state_by_id[target_id] = state
            values = [
                "Yes" if enabled else "No",
                _target_display_label(row),
                _target_family_label(row),
                _target_scope_text(row),
                _target_source_text(row),
                str(getattr(row, "readiness_status", "")),
                _validation_status_text(state),
                _count_text(state.profile_count),
                _count_text(state.face_count),
                _count_text(state.edge_count),
                _build_status_text(state),
                _volume_text(state.volume),
                state.output_object_ref or "-",
                _target_diagnostic_text(row, self._target_model, state),
            ]
            for col_index, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setData(_qt_user_role(), target_id)
                if col_index == 0:
                    item.setFlags((item.flags() | _qt_item_is_user_checkable()) & ~_qt_item_is_editable())
                    item.setCheckState(_qt_checked_state(enabled))
                else:
                    item.setFlags(item.flags() & ~_qt_item_is_editable())
                self._target_table.setItem(row_index, col_index, item)
        _stretch_last_column(self._target_table)
        self._updating_target_table = False
        self._restore_target_selection(previous_selected_target_id)
        self._update_action_state()

    def _status_text(self) -> str:
        lines = list(self._status_model.messages)
        target_count = len(list(getattr(self._target_model, "target_rows", []) or []))
        diagnostic_count = len(list(getattr(self._target_model, "target_diagnostic_rows", []) or []))
        enabled_count = sum(1 for state in self._target_state_by_id.values() if state.enabled)
        selected_state = self._selected_target_state()
        lines.append("")
        lines.append(f"Solid targets: {target_count}")
        lines.append(f"Target diagnostics: {diagnostic_count}")
        lines.append(f"Enabled targets: {enabled_count}")
        if selected_state is not None:
            lines.append(f"Selected target: {_target_display_label(selected_state.target_row)}")
            lines.append(
                "Selected validation: "
                f"{_validation_status_text(selected_state)}; "
                f"profiles={selected_state.profile_count}; "
                f"faces={selected_state.face_count}; "
                f"edges={selected_state.edge_count}"
            )
            lines.append(
                "Selected build: "
                f"{_build_status_text(selected_state)}; "
                f"volume={_volume_text(selected_state.volume)}; "
                f"output={selected_state.output_object_ref or '-'}"
            )
            if selected_state.validation_message:
                lines.append(f"Selected diagnostics: {selected_state.validation_message}")
        else:
            lines.append("Selected target: -")
        qa_lines = _simulation_ready_qa_lines(self.document)
        if qa_lines:
            lines.append("")
            lines.extend(qa_lines)
        drainage_qa_lines = _drainage_watertight_handoff_lines(self.document, self._target_model)
        if drainage_qa_lines:
            lines.append("")
            lines.extend(drainage_qa_lines)
        intersection_qa_lines = _intersection_watertight_handoff_lines(self.document, self._target_model)
        if intersection_qa_lines:
            lines.append("")
            lines.extend(intersection_qa_lines)
        return "\n".join(lines)

    def _restore_target_selection(self, target_id: str) -> None:
        if not target_id:
            return
        for row_index in range(self._target_table.rowCount()):
            item = self._target_table.item(row_index, 1)
            if item is not None and str(item.data(_qt_user_role()) or "") == target_id:
                self._target_table.selectRow(row_index)
                return

    def _target_selection_changed(self) -> None:
        if self._updating_target_table:
            return
        selected_items = self._target_table.selectedItems()
        if not selected_items:
            self._selected_target_id = ""
        else:
            item = self._target_table.item(selected_items[0].row(), 1) or selected_items[0]
            self._selected_target_id = str(item.data(_qt_user_role()) or "")
        self._update_action_state()
        self._status.setPlainText(self._status_text())

    def _target_item_changed(self, item) -> None:
        if self._updating_target_table or item is None or item.column() != 0:
            return
        target_id = str(item.data(_qt_user_role()) or "")
        state = self._target_state_by_id.get(target_id)
        if state is None:
            return
        state.enabled = item.checkState() == _qt_checked_state(True)
        item.setText("Yes" if state.enabled else "No")
        self._update_action_state()
        self._status.setPlainText(self._status_text())

    def _selected_target_state(self) -> WatertightSolidTargetPanelState | None:
        if not self._selected_target_id:
            return None
        return self._target_state_by_id.get(self._selected_target_id)

    def _update_action_state(self) -> None:
        if not hasattr(self, "_validate_button"):
            return
        selected_state = self._selected_target_state()
        selected_available = bool(
            self._status_model.ready
            and selected_state is not None
            and str(getattr(selected_state.target_row, "readiness_status", "") or "") == "available"
        )
        self._validate_button.setEnabled(selected_available)
        self._validate_button.setToolTip(
            "Validate the selected target topology."
            if selected_available
            else "Select an available solid target to validate."
        )
        self._build_selected_button.setEnabled(False)
        self._build_selected_button.setToolTip(
            "Build the selected validated target."
            if selected_available and selected_state is not None and selected_state.validation_status == "ok"
            else "Validate the selected target before building a solid."
        )
        self._build_enabled_button.setEnabled(False)
        enabled_available_count = len(self._enabled_available_target_states())
        self._build_enabled_button.setToolTip(
            f"Build {enabled_available_count} enabled target(s)."
            if enabled_available_count > 0
            else "Enable one or more available solid targets before bulk build."
        )
        if selected_available and selected_state is not None and selected_state.validation_status == "ok":
            self._build_selected_button.setEnabled(True)
        if self._status_model.ready and enabled_available_count > 0:
            self._build_enabled_button.setEnabled(True)
        if hasattr(self, "_build_package_button"):
            self._build_package_button.setEnabled(self._status_model.ready and bool(_watertight_output_objects(self.document)))
        if hasattr(self, "_export_package_button"):
            self._export_package_button.setEnabled(find_v1_simulation_package_output(self.document) is not None)
        output_obj = self._output_object_for_state(selected_state)
        output_ready = output_obj is not None
        for button in (getattr(self, "_show_button", None), getattr(self, "_hide_button", None), getattr(self, "_focus_button", None)):
            if button is not None:
                button.setEnabled(output_ready)

    def _validate_selected_target(self) -> None:
        selected_state = self._selected_target_state()
        if selected_state is None:
            return
        self._validate_target_state(selected_state)

    def _validate_target_state(self, selected_state: WatertightSolidTargetPanelState) -> bool:
        if not self._status_model.ready:
            selected_state.validation_status = "error"
            selected_state.validation_message = WATERTIGHT_SOLIDS_BLOCKED_MESSAGE
            self._refresh_target_row(selected_state.target_id)
            return False
        if str(getattr(selected_state.target_row, "readiness_status", "") or "") != "available":
            selected_state.validation_status = "blocked"
            selected_state.validation_message = _target_diagnostic_text(
                selected_state.target_row,
                self._target_model,
                selected_state,
            )
            self._refresh_target_row(selected_state.target_id)
            return False
        if _is_structure_body_target(selected_state.target_row):
            return self._validate_structure_body_target_state(selected_state)
        if _is_drainage_pipeline_target(selected_state.target_row):
            return self._validate_drainage_pipeline_target_state(selected_state)
        if _is_intersection_patch_target(selected_state.target_row):
            return self._validate_intersection_patch_target_state(selected_state)

        try:
            applied_obj = find_v1_applied_section_set(self.document)
            corridor_obj = find_v1_corridor_model(self.document)
            applied = to_applied_section_set(applied_obj)
            corridor = to_corridor_model(corridor_obj)
            if applied is None or corridor is None:
                raise RuntimeError("Applied Sections and CorridorModel are required for watertight solid validation.")
            project_id = str(getattr(applied, "project_id", "") or getattr(corridor, "project_id", "") or "corridorroad-v1")
            corridor_ref = str(getattr(corridor, "corridor_id", "") or getattr(applied, "corridor_id", "") or "corridor:main")
            profile_set = AppliedSectionSolidProfileService().build(
                SolidProfileBuildRequest(
                    project_id=project_id,
                    solid_target=selected_state.target_row,
                    applied_section_set=applied,
                    corridor_ref=corridor_ref,
                )
            )
            profile_set = _profile_set_on_centerline3d(self.document, profile_set)
            edge_network = SolidEdgeNetworkService().build(
                SolidEdgeNetworkBuildRequest(
                    project_id=project_id,
                    profile_set=profile_set,
                )
            )
            selected_state.profile_set = profile_set
            selected_state.edge_network = edge_network
            selected_state.profile_count = len(list(getattr(profile_set, "profile_rows", []) or []))
            selected_state.face_count = int(getattr(edge_network, "face_count", 0) or 0)
            selected_state.edge_count = int(getattr(edge_network, "edge_count", 0) or 0)
            has_errors = any(_diagnostic_severity(row) == "error" for row in list(getattr(profile_set, "diagnostic_rows", []) or []))
            has_errors = has_errors or str(getattr(edge_network, "validation_status", "") or "") != "ok"
            selected_state.validation_status = "error" if has_errors else "ok"
            selected_state.validation_message = _validation_diagnostic_text(profile_set, edge_network)
            if selected_state.validation_status != "ok":
                selected_state.build_status = "blocked"
        except Exception as exc:
            selected_state.profile_set = None
            selected_state.edge_network = None
            selected_state.profile_count = 0
            selected_state.face_count = 0
            selected_state.edge_count = 0
            selected_state.validation_status = "error"
            selected_state.build_status = "blocked"
            selected_state.validation_message = f"Validation failed: {exc}"
        self._refresh_target_row(selected_state.target_id)
        return selected_state.validation_status == "ok"

    def _validate_structure_body_target_state(self, selected_state: WatertightSolidTargetPanelState) -> bool:
        try:
            external_context = _external_structure_body_shape_context(self.document, selected_state.target_row)
            if external_context is not None:
                structure_model, structure_row, shape, external_obj = external_context
                connection_status, connection_message = _external_structure_connection_point_validation(
                    structure_model,
                    structure_row,
                    shape,
                )
                selected_state.profile_set = external_obj
                selected_state.edge_network = structure_row
                selected_state.profile_count = 1
                selected_state.face_count = _shape_count(shape, "Faces")
                selected_state.edge_count = _shape_count(shape, "Edges")
                selected_state.volume = float(getattr(shape, "Volume", 0.0) or 0.0)
                selected_state.validation_status = "ok" if selected_state.volume > 0.0 and connection_status == "ok" else "error"
                selected_state.validation_message = (
                    "External Structure body shape candidate ready; "
                    f"structure={str(getattr(structure_row, 'structure_id', '') or '')}; "
                    f"geometry_ref={str(getattr(structure_row, 'geometry_ref', '') or '')}; "
                    f"faces={selected_state.face_count}; volume={selected_state.volume:.6g}; "
                    f"{connection_message}"
                )
                if selected_state.validation_status != "ok":
                    selected_state.build_status = "blocked"
                self._refresh_target_row(selected_state.target_id)
                return selected_state.validation_status == "ok"

            structure_output, solid_row = _structure_body_output_context(self.document, selected_state.target_row)
            selected_state.profile_set = structure_output
            selected_state.edge_network = solid_row
            selected_state.profile_count = 1
            selected_state.face_count = 6
            selected_state.edge_count = 12
            selected_state.volume = float(getattr(solid_row, "volume", 0.0) or 0.0)
            selected_state.validation_status = "ok" if selected_state.volume > 0.0 else "error"
            selected_state.validation_message = (
                "Structure body solid candidate ready; "
                f"structure={str(getattr(solid_row, 'structure_id', '') or '')}; "
                f"kind={str(getattr(solid_row, 'solid_kind', '') or '')}; "
                f"width={float(getattr(solid_row, 'width', 0.0) or 0.0):.3f}; "
                f"height={float(getattr(solid_row, 'height', 0.0) or 0.0):.3f}; "
                f"length={float(getattr(solid_row, 'length', 0.0) or 0.0):.3f}."
            )
            if selected_state.validation_status != "ok":
                selected_state.build_status = "blocked"
        except Exception as exc:
            selected_state.profile_set = None
            selected_state.edge_network = None
            selected_state.profile_count = 0
            selected_state.face_count = 0
            selected_state.edge_count = 0
            selected_state.volume = 0.0
            selected_state.validation_status = "error"
            selected_state.build_status = "blocked"
            selected_state.validation_message = f"Structure body validation failed: {exc}"
        self._refresh_target_row(selected_state.target_id)
        return selected_state.validation_status == "ok"

    def _validate_drainage_pipeline_target_state(self, selected_state: WatertightSolidTargetPanelState) -> bool:
        try:
            if _is_drainage_pipeline_network_target(selected_state.target_row):
                _output, network_row, geometry_rows, solid_rows, junction_rows = _drainage_pipeline_network_output_context(self.document, selected_state.target_row)
                point_count = sum(len(list(getattr(row, "centerline_points", []) or [])) for row in geometry_rows)
                cap_count = sum(int(getattr(row, "cap_count", 0) or 0) for row in solid_rows)
                connector_count = _network_connector_count(junction_rows)
                selected_state.profile_set = geometry_rows
                selected_state.edge_network = network_row
                selected_state.profile_count = point_count
                selected_state.face_count = max(0, sum(max(0, len(list(getattr(row, "centerline_points", []) or [])) - 1) * 3 for row in geometry_rows) + cap_count + connector_count)
                selected_state.edge_count = selected_state.face_count
                selected_state.volume = float(getattr(network_row, "volume", 0.0) or 0.0)
                selected_state.validation_status = "ok" if str(getattr(network_row, "validation_status", "") or "") == "ready" else "error"
                selected_state.validation_message = (
                    "Drainage pipeline network candidate ready; "
                    f"segments={int(getattr(network_row, 'segment_count', 0) or 0)}; "
                    f"junctions={int(getattr(network_row, 'junction_count', 0) or 0)}; "
                    f"connectors={connector_count}; "
                    f"caps={cap_count}; length={float(getattr(network_row, 'length', 0.0) or 0.0):.3f}; "
                    f"fuse_mode=compound_first_slice."
                )
                if selected_state.validation_status != "ok":
                    selected_state.build_status = "blocked"
                self._refresh_target_row(selected_state.target_id)
                return selected_state.validation_status == "ok"

            _output, geometry_row, solid_row = _drainage_pipeline_output_context(self.document, selected_state.target_row)
            point_count = len(list(getattr(geometry_row, "centerline_points", []) or []))
            cap_count = int(getattr(solid_row, "cap_count", 0) or 0)
            selected_state.profile_set = geometry_row
            selected_state.edge_network = solid_row
            selected_state.profile_count = point_count
            selected_state.face_count = max(0, (point_count - 1) * 3 + cap_count)
            selected_state.edge_count = max(0, (point_count - 1) * 3 + cap_count)
            selected_state.volume = float(getattr(solid_row, "volume", 0.0) or 0.0)
            selected_state.validation_status = "ok" if str(getattr(solid_row, "status", "") or "") == "ready" else "error"
            selected_state.validation_message = (
                "Drainage pipeline solid candidate ready; "
                f"points={point_count}; caps={cap_count}; length={float(getattr(solid_row, 'length', 0.0) or 0.0):.3f}; "
                f"coordinate_mode={str(getattr(solid_row, 'coordinate_mode', '') or '')}."
            )
            if selected_state.validation_status != "ok":
                selected_state.build_status = "blocked"
        except Exception as exc:
            selected_state.profile_set = None
            selected_state.edge_network = None
            selected_state.profile_count = 0
            selected_state.face_count = 0
            selected_state.edge_count = 0
            selected_state.volume = 0.0
            selected_state.validation_status = "error"
            selected_state.build_status = "blocked"
            selected_state.validation_message = f"Drainage pipeline validation failed: {exc}"
        self._refresh_target_row(selected_state.target_id)
        return selected_state.validation_status == "ok"

    def _validate_intersection_patch_target_state(self, selected_state: WatertightSolidTargetPanelState) -> bool:
        try:
            patch = _intersection_patch_context(self.document, selected_state.target_row)
            quality_errors = [
                str(row.get("message", "") or "")
                for row in list(patch.get("quality_diagnostics", []) or [])
                if str(row.get("severity", "") or "") == "error"
            ]
            if quality_errors:
                raise RuntimeError("; ".join(quality_errors))
            selected_state.profile_set = patch
            selected_state.edge_network = patch
            selected_state.profile_count = int(patch.get("boundary_count", 0) or 0)
            selected_state.face_count = max(0, int(patch.get("boundary_count", 0) or 0) * 2)
            selected_state.edge_count = max(0, int(patch.get("boundary_count", 0) or 0) * 3)
            selected_state.volume = 0.0
            selected_state.validation_status = "ok"
            boundary_strategy = str(patch.get("surface_boundary_strategy", "") or patch.get("triangulation_mode", "") or "-")
            edge_blend_count = int(patch.get("edge_blend_face_count", 0) or 0)
            selected_state.validation_message = (
                "Intersection patch solid candidate ready; "
                f"intersection={patch.get('intersection_id', '')}; "
                f"boundary_points={int(patch.get('boundary_count', 0) or 0)}; "
                f"control_regions={patch.get('control_region_count', 0)}; "
                f"area_xy={float(patch.get('area_xy', 0.0) or 0.0):.3f}; "
                f"min_edge={float(patch.get('min_edge_length', 0.0) or 0.0):.3f}; "
                f"depth={float(patch.get('depth', 0.0) or 0.0):.3f}; "
                f"boundary={boundary_strategy}; "
                f"edge_blend_faces={edge_blend_count}."
            )
        except Exception as exc:
            selected_state.profile_set = None
            selected_state.edge_network = None
            selected_state.profile_count = 0
            selected_state.face_count = 0
            selected_state.edge_count = 0
            selected_state.volume = 0.0
            selected_state.validation_status = "error"
            selected_state.build_status = "blocked"
            selected_state.validation_message = f"Intersection patch validation failed: {exc}"
        self._refresh_target_row(selected_state.target_id)
        return selected_state.validation_status == "ok"

    def _build_selected_target(self) -> None:
        selected_state = self._selected_target_state()
        if selected_state is None:
            return
        if self._build_target_state(selected_state):
            self._refresh_simulation_qa_output()

    def _build_target_state(self, selected_state: WatertightSolidTargetPanelState) -> bool:
        if _is_structure_body_target(selected_state.target_row):
            return self._build_structure_body_target_state(selected_state)
        if _is_drainage_pipeline_target(selected_state.target_row):
            return self._build_drainage_pipeline_target_state(selected_state)
        if _is_intersection_patch_target(selected_state.target_row):
            return self._build_intersection_patch_target_state(selected_state)
        if selected_state.validation_status != "ok" or selected_state.profile_set is None or selected_state.edge_network is None:
            if not self._validate_target_state(selected_state):
                return False
        try:
            profile_set = selected_state.profile_set
            edge_network = selected_state.edge_network
            part_result = WatertightSolidPartMapper().map_edge_network(edge_network, profile_set)
            selected_state.part_result = part_result
            selected_state.volume = float(getattr(part_result, "volume", 0.0) or 0.0)
            selected_state.face_count = int(getattr(part_result, "face_count", 0) or selected_state.face_count)
            selected_state.edge_count = int(getattr(part_result, "edge_count", 0) or selected_state.edge_count)
            selected_state.validation_message = _build_diagnostic_text(selected_state.validation_message, part_result)
            if str(getattr(part_result, "validation_status", "") or "") != "ok":
                selected_state.build_status = "error"
                self._refresh_target_row(selected_state.target_id)
                return False

            applied = to_applied_section_set(find_v1_applied_section_set(self.document))
            corridor = to_corridor_model(find_v1_corridor_model(self.document))
            project_id = str(getattr(profile_set, "project_id", "") or getattr(applied, "project_id", "") or "corridorroad-v1")
            corridor_id = str(getattr(corridor, "corridor_id", "") or getattr(profile_set, "corridor_ref", "") or "corridor:main")
            object_name = _solid_output_object_name(selected_state.target_id)
            output = WatertightSolidOutputMapper().map_result(
                WatertightSolidOutputMappingRequest(
                    project_id=project_id,
                    corridor_id=corridor_id,
                    solid_target=selected_state.target_row,
                    profile_set=profile_set,
                    edge_network=edge_network,
                    part_result=part_result,
                    generated_object_ref=object_name,
                )
            )
            obj = create_or_update_v1_watertight_solid_output_object(
                document=self.document,
                watertight_solid_output=output,
                shape=getattr(part_result, "solid_shape", None),
                project=find_project(self.document),
                object_name=object_name,
                label=f"Watertight Solid - {_target_display_label(selected_state.target_row)}",
            )
            selected_state.watertight_output = output
            selected_state.output_object = obj
            selected_state.output_object_ref = str(getattr(obj, "Name", "") or object_name)
            selected_state.build_status = "built"
        except Exception as exc:
            selected_state.build_status = "error"
            selected_state.validation_message = f"Build failed: {exc}"
        self._refresh_target_row(selected_state.target_id)
        return selected_state.build_status == "built"

    def _build_intersection_patch_target_state(self, selected_state: WatertightSolidTargetPanelState) -> bool:
        if selected_state.validation_status != "ok":
            if not self._validate_intersection_patch_target_state(selected_state):
                return False
        try:
            patch = selected_state.profile_set if isinstance(selected_state.profile_set, dict) else _intersection_patch_context(self.document, selected_state.target_row)
            shape = _intersection_patch_solid_shape(patch)
            object_name = _solid_output_object_name(selected_state.target_id)
            output = _intersection_patch_watertight_output(
                selected_state.target_row,
                patch=patch,
                shape=shape,
                generated_object_ref=object_name,
            )
            obj = create_or_update_v1_watertight_solid_output_object(
                document=self.document,
                watertight_solid_output=output,
                shape=shape,
                project=find_project(self.document),
                object_name=object_name,
                label=f"Watertight Solid - {_target_display_label(selected_state.target_row)}",
            )
            selected_state.profile_set = patch
            selected_state.edge_network = patch
            selected_state.watertight_output = output
            selected_state.output_object = obj
            selected_state.output_object_ref = str(getattr(obj, "Name", "") or object_name)
            selected_state.volume = float(getattr(shape, "Volume", 0.0) or 0.0)
            selected_state.face_count = _shape_count(shape, "Faces")
            selected_state.edge_count = _shape_count(shape, "Edges")
            selected_state.build_status = "built"
            selected_state.validation_message = (
                "Intersection patch solid built; "
                f"intersection={patch.get('intersection_id', '')}; "
                f"boundary_points={int(patch.get('boundary_count', 0) or 0)}; "
                f"volume={selected_state.volume:.6g}."
            )
        except Exception as exc:
            selected_state.build_status = "error"
            selected_state.validation_message = f"Intersection patch build failed: {exc}"
        self._refresh_target_row(selected_state.target_id)
        return selected_state.build_status == "built"

    def _build_structure_body_target_state(self, selected_state: WatertightSolidTargetPanelState) -> bool:
        if selected_state.validation_status != "ok":
            if not self._validate_structure_body_target_state(selected_state):
                return False
        try:
            external_context = _external_structure_body_shape_context(self.document, selected_state.target_row)
            if external_context is not None:
                structure_model, structure_row, shape, external_obj = external_context
                object_name = _solid_output_object_name(selected_state.target_id)
                output = _external_structure_body_watertight_output(
                    selected_state.target_row,
                    structure_model=structure_model,
                    structure_row=structure_row,
                    external_obj=external_obj,
                    shape=shape,
                    generated_object_ref=object_name,
                )
                obj = create_or_update_v1_watertight_solid_output_object(
                    document=self.document,
                    watertight_solid_output=output,
                    shape=shape,
                    project=find_project(self.document),
                    object_name=object_name,
                    label=f"Watertight Solid - {_target_display_label(selected_state.target_row)}",
                )
                selected_state.profile_set = external_obj
                selected_state.edge_network = structure_row
                selected_state.watertight_output = output
                selected_state.output_object = obj
                selected_state.output_object_ref = str(getattr(obj, "Name", "") or object_name)
                selected_state.volume = float(getattr(shape, "Volume", 0.0) or 0.0)
                selected_state.face_count = _shape_count(shape, "Faces")
                selected_state.edge_count = _shape_count(shape, "Edges")
                selected_state.build_status = "built"
                selected_state.validation_message = (
                    "External Structure body shape reused; "
                    f"structure={str(getattr(structure_row, 'structure_id', '') or '')}; "
                    f"geometry_ref={str(getattr(structure_row, 'geometry_ref', '') or '')}; "
                    f"volume={selected_state.volume:.6g}."
                )
                self._refresh_target_row(selected_state.target_id)
                return selected_state.build_status == "built"

            structure_output, solid_row = _structure_body_output_context(self.document, selected_state.target_row)
            shape = _structure_body_solid_shape(
                solid_row,
                structure_model=to_structure_model(find_v1_structure_model(self.document)),
            )
            object_name = _solid_output_object_name(selected_state.target_id)
            output = _structure_body_watertight_output(
                selected_state.target_row,
                structure_output=structure_output,
                solid_row=solid_row,
                shape=shape,
                generated_object_ref=object_name,
            )
            obj = create_or_update_v1_watertight_solid_output_object(
                document=self.document,
                watertight_solid_output=output,
                shape=shape,
                project=find_project(self.document),
                object_name=object_name,
                label=f"Watertight Solid - {_target_display_label(selected_state.target_row)}",
            )
            selected_state.profile_set = structure_output
            selected_state.edge_network = solid_row
            selected_state.watertight_output = output
            selected_state.output_object = obj
            selected_state.output_object_ref = str(getattr(obj, "Name", "") or object_name)
            selected_state.volume = float(getattr(shape, "Volume", 0.0) or getattr(solid_row, "volume", 0.0) or 0.0)
            selected_state.face_count = _shape_count(shape, "Faces")
            selected_state.edge_count = _shape_count(shape, "Edges")
            selected_state.build_status = "built"
            selected_state.validation_message = (
                "Structure body solid built; "
                f"structure={str(getattr(solid_row, 'structure_id', '') or '')}; "
                f"volume={selected_state.volume:.6g}."
            )
        except Exception as exc:
            selected_state.build_status = "error"
            selected_state.validation_message = f"Structure body build failed: {exc}"
        self._refresh_target_row(selected_state.target_id)
        return selected_state.build_status == "built"

    def _build_drainage_pipeline_target_state(self, selected_state: WatertightSolidTargetPanelState) -> bool:
        if selected_state.validation_status != "ok":
            if not self._validate_drainage_pipeline_target_state(selected_state):
                return False
        try:
            if _is_drainage_pipeline_network_target(selected_state.target_row):
                drainage_output, network_row, geometry_rows, solid_rows, junction_rows = _drainage_pipeline_network_output_context(self.document, selected_state.target_row)
                dependency_count = self._build_structure_body_dependencies_for_network(junction_rows)
                structure_refs = _network_note_refs(junction_rows, "structure_refs")
                structure_body_shape_map = _built_structure_body_shape_map_for_refs(self.document, structure_refs)
                structure_body_shapes, structure_body_object_refs = _structure_body_shape_map_values(structure_body_shape_map)
                connection_point_map = _structure_connection_point_map(self.document)
                shape_result = _drainage_pipeline_network_solid_shape(
                    geometry_rows,
                    junction_rows=junction_rows,
                    structure_body_shapes=structure_body_shapes,
                    structure_body_shape_map=structure_body_shape_map,
                    connection_point_map=connection_point_map,
                )
                shape = getattr(shape_result, "shape", shape_result)
                selected_state.volume = max(float(getattr(shape, "Volume", 0.0) or 0.0), float(getattr(network_row, "volume", 0.0) or 0.0))
                selected_state.face_count = max(_shape_count(shape, "Faces"), selected_state.face_count)
                selected_state.edge_count = max(_shape_count(shape, "Edges"), selected_state.edge_count)
                object_name = _solid_output_object_name(selected_state.target_id)
                output = _drainage_pipeline_network_watertight_output(
                    selected_state.target_row,
                    drainage_output=drainage_output,
                    network_row=network_row,
                    geometry_rows=geometry_rows,
                    solid_rows=solid_rows,
                    junction_rows=junction_rows,
                    shape=shape,
                    fuse_mode=str(getattr(shape_result, "fuse_mode", "") or ""),
                    connector_count=int(getattr(shape_result, "connector_count", 0) or 0),
                    structure_body_count=int(getattr(shape_result, "structure_body_count", 0) or 0),
                    port_connector_count=int(getattr(shape_result, "port_connector_count", 0) or 0),
                    endpoint_trim_count=int(getattr(shape_result, "endpoint_trim_count", 0) or 0),
                    structure_port_terminal_count=int(getattr(shape_result, "structure_port_terminal_count", 0) or 0),
                    structure_port_contact_status=str(getattr(shape_result, "structure_port_contact_status", "") or ""),
                    structure_body_object_refs=structure_body_object_refs,
                    fuse_notes=str(getattr(shape_result, "notes", "") or ""),
                    generated_object_ref=object_name,
                )
                obj = create_or_update_v1_watertight_solid_output_object(
                    document=self.document,
                    watertight_solid_output=output,
                    shape=shape,
                    project=find_project(self.document),
                    object_name=object_name,
                    label=f"Watertight Solid - {_target_display_label(selected_state.target_row)}",
                )
                selected_state.watertight_output = output
                selected_state.output_object = obj
                selected_state.output_object_ref = str(getattr(obj, "Name", "") or object_name)
                selected_state.build_status = "built"
                selected_state.validation_message = (
                    "Drainage pipeline network solid candidate built; "
                    f"network={str(getattr(network_row, 'network_id', '') or '')}; "
                    f"segments={int(getattr(network_row, 'segment_count', 0) or 0)}; "
                    f"connectors={int(getattr(shape_result, 'connector_count', 0) or 0)}; "
                    f"structure_bodies={int(getattr(shape_result, 'structure_body_count', 0) or 0)}; "
                    f"port_connectors={int(getattr(shape_result, 'port_connector_count', 0) or 0)}; "
                    f"endpoint_trims={int(getattr(shape_result, 'endpoint_trim_count', 0) or 0)}; "
                    f"structure_port_terminals={int(getattr(shape_result, 'structure_port_terminal_count', 0) or 0)}; "
                    f"structure_port_status={str(getattr(shape_result, 'structure_port_contact_status', '') or '')}; "
                    f"dependencies_built={dependency_count}; "
                    f"fuse_mode={str(getattr(shape_result, 'fuse_mode', '') or '')}; "
                    f"volume={selected_state.volume:.6g}."
                )
                self._refresh_target_row(selected_state.target_id)
                return selected_state.build_status == "built"

            drainage_output, geometry_row, solid_row = _drainage_pipeline_output_context(self.document, selected_state.target_row)
            shape = _drainage_pipeline_solid_shape(geometry_row)
            selected_state.volume = float(getattr(solid_row, "volume", 0.0) or 0.0)
            selected_state.face_count = max(_shape_count(shape, "Faces"), selected_state.face_count)
            selected_state.edge_count = max(_shape_count(shape, "Edges"), selected_state.edge_count)
            object_name = _solid_output_object_name(selected_state.target_id)
            output = _drainage_pipeline_watertight_output(
                selected_state.target_row,
                drainage_output=drainage_output,
                geometry_row=geometry_row,
                solid_row=solid_row,
                shape=shape,
                generated_object_ref=object_name,
            )
            obj = create_or_update_v1_watertight_solid_output_object(
                document=self.document,
                watertight_solid_output=output,
                shape=shape,
                project=find_project(self.document),
                object_name=object_name,
                label=f"Watertight Solid - {_target_display_label(selected_state.target_row)}",
            )
            selected_state.watertight_output = output
            selected_state.output_object = obj
            selected_state.output_object_ref = str(getattr(obj, "Name", "") or object_name)
            selected_state.build_status = "built"
            selected_state.validation_message = (
                "Drainage pipeline capped pipe solid candidate built; "
                f"solid={str(getattr(solid_row, 'solid_row_id', '') or '')}; "
                f"volume={selected_state.volume:.6g}."
            )
        except Exception as exc:
            selected_state.build_status = "error"
            selected_state.validation_message = f"Drainage pipeline build failed: {exc}"
        self._refresh_target_row(selected_state.target_id)
        return selected_state.build_status == "built"

    def _build_structure_body_dependencies_for_network(self, junction_rows) -> int:
        built_count = 0
        for structure_ref in _network_note_refs(junction_rows, "structure_refs"):
            existing_shapes, _object_refs = _built_structure_body_shapes_for_refs(self.document, [structure_ref])
            if existing_shapes:
                continue
            dependency_state = self._structure_body_target_state_for_ref(structure_ref)
            if dependency_state is None:
                continue
            if self._build_structure_body_target_state(dependency_state):
                built_count += 1
        return built_count

    def _structure_body_target_state_for_ref(self, structure_ref: str) -> WatertightSolidTargetPanelState | None:
        target_ref = str(structure_ref or "").strip()
        if not target_ref:
            return None
        for state in self._target_state_by_id.values():
            if not _is_structure_body_target(state.target_row):
                continue
            if str(getattr(state.target_row, "readiness_status", "") or "") != "available":
                continue
            if str(getattr(state.target_row, "structure_ref", "") or "") == target_ref:
                return state
        return None

    def _build_enabled_targets(self) -> None:
        states = _ordered_build_states(self._enabled_available_target_states())
        if not states:
            self._status.setPlainText(self._status_text() + "\n\nNo enabled available targets to build.")
            return
        built_count = 0
        failed_count = 0
        total_volume = 0.0
        for state in states:
            if self._build_target_state(state):
                built_count += 1
                total_volume += float(state.volume or 0.0)
            else:
                failed_count += 1
        self._refresh_simulation_qa_output()
        self._update_action_state()
        self._status.setPlainText(
            self._status_text()
            + f"\n\nBuild Enabled summary: built={built_count}; failed={failed_count}; targets={len(states)}; volume={_volume_text(total_volume)}"
        )

    def _refresh_simulation_qa_output(self):
        qa_output = _build_simulation_qa_output(self.document)
        self._set_simulation_qa_rows(qa_output)
        _create_or_update_intersection_trim_boundary_result_object(self.document)
        _create_or_update_intersection_trim_preview_object(self.document)
        _create_or_update_intersection_trim_application_preview_object(self.document)
        _create_or_update_intersection_trim_application_output_object(self.document)
        _create_or_update_intersection_trim_closure_surface_preview_object(self.document)
        _create_or_update_intersection_trim_closure_surface_output_object(self.document)
        _create_or_update_intersection_trim_closure_cell_output_object(self.document)
        _create_or_update_intersection_trim_shell_candidate_output_object(self.document)
        _create_or_update_intersection_trim_fuse_candidate_output_object(self.document)
        _create_or_update_intersection_trim_shell_reconstruction_output_object(self.document)
        _create_or_update_intersection_trim_solid_reconstruction_output_object(self.document)
        try:
            return create_or_update_v1_simulation_qa_output_object(
                document=self.document,
                simulation_qa_output=qa_output,
                project=find_project(self.document),
                object_name="V1SimulationQaOutput",
                label="Simulation QA - Watertight Solids",
            )
        except Exception:
            return None

    def _build_simulation_package(self) -> None:
        qa_output = _build_simulation_qa_output(self.document)
        self._set_simulation_qa_rows(qa_output)
        package_output = _build_simulation_package_output(self.document, qa_output=qa_output)
        try:
            obj = create_or_update_v1_simulation_package_output_object(
                document=self.document,
                simulation_package_output=package_output,
                project=find_project(self.document),
                object_name="V1SimulationPackageOutput",
                label="Simulation Package - Watertight Solids",
            )
            self._update_action_state()
            self._status.setPlainText(
                self._status_text()
                + (
                    f"\n\nSimulation package: {str(getattr(obj, 'Name', '') or '')}; "
                    f"status={str(getattr(package_output, 'package_status', '') or '')}; "
                    f"outputs={int(getattr(package_output, 'output_count', 0) or 0)}; "
                    f"volume={_volume_text(float(getattr(package_output, 'total_volume', 0.0) or 0.0))}"
                )
            )
        except Exception as exc:
            self._status.setPlainText(self._status_text() + f"\n\nSimulation package was not built: {exc}")

    def _export_simulation_package_json(self) -> bool:
        try:
            path, _filter = QtWidgets.QFileDialog.getSaveFileName(
                self.form,
                "Export Simulation Package",
                "simulation_package.json",
                "JSON Files (*.json);;All Files (*)",
            )
            if not path:
                return False
            info = export_document_simulation_package_json(path, document=self.document)
            self._status.setPlainText(
                self._status_text()
                + (
                    "\n\nSimulation package JSON has been exported."
                    f"\nPath: {info['path']}"
                    f"\nPackage: {info['simulation_package_output_id']}"
                    f"\nStatus: {info['package_status']}"
                    f"\nOutputs: {info['output_count']}"
                    f"\nSolid rows: {info['solid_row_count']}"
                    f"\nGeometry files: {info.get('geometry_file_count', 0)}"
                    f"\nGeometry export: {info.get('geometry_export_status', 'not_available')}"
                    f"\nGeometry folder: {info.get('geometry_directory', '-') or '-'}"
                    f"\nDiagnostics: {info['diagnostic_count']}"
                    f"\nVolume: {_volume_text(float(info['total_volume'] or 0.0))}"
                )
            )
            return True
        except Exception as exc:
            self._status.setPlainText(self._status_text() + f"\n\nSimulation package JSON was not exported: {exc}")
            return False

    def _refresh_simulation_qa_tables(self) -> None:
        self._set_simulation_qa_rows(_build_simulation_qa_output(self.document))

    def _set_simulation_qa_rows(self, qa_output) -> None:
        family_rows = list(getattr(qa_output, "family_rows", []) or [])
        self._qa_family_table.setRowCount(len(family_rows))
        for row_index, row in enumerate(family_rows):
            values = [
                str(getattr(row, "family", "") or ""),
                str(getattr(row, "status", "") or ""),
                str(int(getattr(row, "output_count", 0) or 0)),
                _volume_text(float(getattr(row, "total_volume", 0.0) or 0.0)),
            ]
            for col_index, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(item.flags() & ~_qt_item_is_editable())
                self._qa_family_table.setItem(row_index, col_index, item)
        _stretch_last_column(self._qa_family_table)

        diagnostic_rows = list(getattr(qa_output, "diagnostic_rows", []) or [])
        self._qa_diagnostic_table.setRowCount(len(diagnostic_rows))
        for row_index, row in enumerate(diagnostic_rows):
            values = [
                str(getattr(row, "severity", "") or ""),
                str(getattr(row, "kind", "") or ""),
                str(getattr(row, "source_ref", "") or ""),
                str(getattr(row, "message", "") or ""),
            ]
            for col_index, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(item.flags() & ~_qt_item_is_editable())
                self._qa_diagnostic_table.setItem(row_index, col_index, item)
        _stretch_last_column(self._qa_diagnostic_table)

    def _enabled_available_target_states(self) -> list[WatertightSolidTargetPanelState]:
        return [
            state
            for state in self._target_state_by_id.values()
            if state.enabled and str(getattr(state.target_row, "readiness_status", "") or "") == "available"
        ]

    def _show_selected_solid(self) -> None:
        state = self._selected_target_state()
        obj = self._output_object_for_state(state)
        if obj is None:
            self._status.setPlainText(self._status_text() + "\n\nNo built output object is available to show.")
            return
        visible_changed = _set_object_visibility(obj, True)
        suffix = "" if visible_changed else "; visibility=not_available"
        self._status.setPlainText(
            self._status_text()
            + f"\n\nShown solid: {str(getattr(obj, 'Name', '') or '')}; {_target_context_text(state.target_row)}{suffix}"
        )

    def _hide_selected_solid(self) -> None:
        state = self._selected_target_state()
        obj = self._output_object_for_state(state)
        if obj is None:
            self._status.setPlainText(self._status_text() + "\n\nNo built output object is available to hide.")
            return
        visible_changed = _set_object_visibility(obj, False)
        suffix = "" if visible_changed else "; visibility=not_available"
        self._status.setPlainText(
            self._status_text()
            + f"\n\nHidden solid: {str(getattr(obj, 'Name', '') or '')}; {_target_context_text(state.target_row)}{suffix}"
        )

    def _focus_selected_solid(self) -> None:
        state = self._selected_target_state()
        self._focus_state_output(state)

    def _focus_target_row_output(self, item) -> None:
        state = self._target_state_from_item(item)
        if state is None:
            return
        self._selected_target_id = state.target_id
        self._restore_target_selection(state.target_id)
        self._focus_state_output(state)

    def _focus_state_output(self, state: WatertightSolidTargetPanelState | None) -> None:
        obj = self._output_object_for_state(state)
        if obj is None:
            self._status.setPlainText(self._status_text() + "\n\nNo built output object is available to focus.")
            return
        _set_object_visibility(obj, True)
        focused = _focus_document_object(obj)
        state_label = str(getattr(obj, "Name", "") or "")
        self._status.setPlainText(
            self._status_text()
            + f"\n\nFocused solid: {state_label}; {_target_context_text(state.target_row)}; gui_focus={'yes' if focused else 'not_available'}"
        )

    def _target_state_from_item(self, item) -> WatertightSolidTargetPanelState | None:
        if item is None:
            return None
        target_id = str(item.data(_qt_user_role()) or "")
        return self._target_state_by_id.get(target_id)

    def _output_object_for_state(self, state: WatertightSolidTargetPanelState | None):
        if state is None:
            return None
        obj = getattr(state, "output_object", None)
        if obj is not None:
            return obj
        object_ref = str(getattr(state, "output_object_ref", "") or "")
        if self.document is not None and object_ref:
            try:
                obj = self.document.getObject(object_ref)
            except Exception:
                obj = None
        if obj is not None:
            state.output_object = obj
        return obj

    def _refresh_target_row(self, target_id: str) -> None:
        self._updating_target_table = True
        for row_index in range(self._target_table.rowCount()):
            item = self._target_table.item(row_index, 1)
            if item is None or str(item.data(_qt_user_role()) or "") != target_id:
                continue
            state = self._target_state_by_id.get(target_id)
            if state is None:
                break
            values = {
                0: "Yes" if state.enabled else "No",
                6: _validation_status_text(state),
                7: _count_text(state.profile_count),
                8: _count_text(state.face_count),
                9: _count_text(state.edge_count),
                10: _build_status_text(state),
                11: _volume_text(state.volume),
                12: state.output_object_ref or "-",
                13: _target_diagnostic_text(state.target_row, self._target_model, state),
            }
            for column, value in values.items():
                cell = self._target_table.item(row_index, column)
                if cell is not None:
                    cell.setText(value)
            break
        self._updating_target_table = False
        self._update_action_state()
        self._status.setPlainText(self._status_text())


class CmdV1WatertightSolids:
    """Open the v1 Watertight Solids placeholder stage."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("watertight_solids.svg"),
            "MenuText": "Watertight Solids",
            "ToolTip": "Generate topology-first watertight solid outputs after Build Corridor",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_watertight_solids_command()


def run_v1_watertight_solids_command(document=None):
    """Open the v1 Watertight Solids task panel and return it for tests."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    panel = V1WatertightSolidsTaskPanel(document=doc)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


def apply_v1_simulation_package(*, document=None, project=None, package_output=None):
    """Persist the current Watertight Solids simulation package manifest."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    active_package_output = package_output or _build_simulation_package_output(doc)
    obj = create_or_update_v1_simulation_package_output_object(
        document=doc,
        simulation_package_output=active_package_output,
        project=prj,
        object_name="V1SimulationPackageOutput",
        label="Simulation Package - Watertight Solids",
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def export_document_simulation_package_json(
    path: str,
    *,
    document=None,
    project=None,
    simulation_package=None,
) -> dict[str, object]:
    """Export the current persisted Watertight Solids simulation package to JSON."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    package_obj = find_v1_simulation_package_output(doc, preferred_output=simulation_package)
    if package_obj is None:
        package_obj = apply_v1_simulation_package(document=doc, project=project)
    return export_simulation_package_to_json(path, package_obj, document=doc)


def _ready_label(value: bool) -> str:
    return "Ready" if bool(value) else "Missing"


def _target_id(row: object) -> str:
    target_id = str(getattr(row, "target_id", "") or "")
    if target_id:
        return target_id
    return "|".join(
        [
            str(getattr(row, "target_family", "") or ""),
            str(getattr(row, "scope_kind", "") or ""),
            str(getattr(row, "region_ref", "") or ""),
            f"{float(getattr(row, 'station_start', 0.0) or 0.0):.3f}",
            f"{float(getattr(row, 'station_end', 0.0) or 0.0):.3f}",
        ]
    )


def _target_display_label(row: object) -> str:
    family = str(getattr(row, "target_family", "") or "").strip().lower()
    component_ref = str(getattr(row, "component_ref", "") or "").strip()
    subassembly_ref = str(getattr(row, "subassembly_ref", "") or "").strip()
    active_or_compatibility_ref = _target_subassembly_or_compatibility_display_ref(row)
    region_ref = str(getattr(row, "region_ref", "") or "").strip()
    structure_ref = str(getattr(row, "structure_ref", "") or "").strip()
    drainage_ref = str(getattr(row, "drainage_ref", "") or "").strip()
    if family == "road_body_envelope":
        return "Road Body Envelope"
    if family == "region_body":
        return f"Region Body - {region_ref}" if region_ref else "Region Body"
    if family == "pavement_layer_body":
        return f"Pavement Layer - {active_or_compatibility_ref}" if active_or_compatibility_ref else "Pavement Layer"
    if family == "subbase_body":
        return f"Subbase - {active_or_compatibility_ref}" if active_or_compatibility_ref else "Subbase"
    if family == "shoulder_body":
        return f"Shoulder - {active_or_compatibility_ref}" if active_or_compatibility_ref else "Shoulder"
    if family == "lined_ditch_body":
        ref = drainage_ref or active_or_compatibility_ref
        return f"Drainage Lined Ditch Solid - {ref}" if ref else "Drainage Lined Ditch Solid"
    if family == "drainage_pipeline_body":
        flow_route_ref = str(getattr(row, "flow_route_ref", "") or "").strip()
        return f"Drainage Pipe Segment Solid - {flow_route_ref or drainage_ref}" if flow_route_ref or drainage_ref else "Drainage Pipe Segment Solid"
    if family == "drainage_pipeline_network_body":
        return f"Drainage Pipe Network Solid - {drainage_ref}" if drainage_ref else "Drainage Pipe Network Solid"
    if family == "intersection_patch_body":
        source_refs = list(getattr(row, "source_refs", []) or [])
        intersection_ref = next((str(ref) for ref in source_refs if str(ref).startswith("intersection:")), "")
        return f"Intersection Patch Solid - {intersection_ref}" if intersection_ref else "Intersection Patch Solid"
    if family in {"intersection_pavement_body", "intersection_subgrade_body", "intersection_slope_body", "intersection_curb_return_body"}:
        source_refs = list(getattr(row, "source_refs", []) or [])
        intersection_ref = next((str(ref) for ref in source_refs if str(ref).startswith("intersection:")), "")
        zone_ref = active_or_compatibility_ref or next((str(ref) for ref in source_refs if "surface-zone" in str(ref)), "")
        label = {
            "intersection_pavement_body": "Intersection Pavement Solid",
            "intersection_subgrade_body": "Intersection Subgrade Solid",
            "intersection_slope_body": "Intersection Slope Solid",
            "intersection_curb_return_body": "Intersection Curb-Return Solid",
        }.get(family, "Intersection Zone Solid")
        suffix = " - ".join(value for value in (intersection_ref, zone_ref) if value)
        return f"{label} - {suffix}" if suffix else label
    if family == "structure_body":
        return f"Structure Body Solid - {structure_ref}" if structure_ref else "Structure Body Solid"
    return str(getattr(row, "target_family", "") or _target_id(row))


def _target_subassembly_or_compatibility_display_ref(row: object) -> str:
    subassembly_ref = str(getattr(row, "subassembly_ref", "") or "").strip()
    if subassembly_ref:
        return subassembly_ref
    component_ref = str(getattr(row, "component_ref", "") or "").strip()
    if component_ref:
        return f"compatibility:{component_ref}"
    return ""


def _target_family_label(row: object) -> str:
    family = str(getattr(row, "target_family", "") or "").strip().lower()
    if family in {"road_body_envelope", "region_body"}:
        return "Envelope"
    if family in {"pavement_layer_body", "subbase_body", "shoulder_body"}:
        return "Subassembly"
    if family == "lined_ditch_body":
        return "Drainage: Lined Ditch"
    if family == "drainage_pipeline_body":
        return "Drainage: Pipe Segment"
    if family == "drainage_pipeline_network_body":
        return "Drainage: Pipe Network"
    if family == "intersection_patch_body":
        return "Intersection Patch"
    if family in {"intersection_pavement_body", "intersection_subgrade_body", "intersection_slope_body", "intersection_curb_return_body"}:
        return {
            "intersection_pavement_body": "Intersection: Pavement",
            "intersection_subgrade_body": "Intersection: Subgrade",
            "intersection_slope_body": "Intersection: Slope",
            "intersection_curb_return_body": "Intersection: Curb-Return",
        }.get(family, "Intersection Zone")
    if family in {"structure_body"}:
        return "Structure Body"
    return family or "-"


def _target_scope_text(row: object) -> str:
    scope = str(getattr(row, "scope_kind", "") or "")
    region_ref = str(getattr(row, "region_ref", "") or "")
    station_start = float(getattr(row, "station_start", 0.0) or 0.0)
    station_end = float(getattr(row, "station_end", 0.0) or 0.0)
    if region_ref:
        return f"{region_ref} | STA {station_start:.3f}-{station_end:.3f}"
    if scope:
        return f"{_target_scope_label(scope)} | STA {station_start:.3f}-{station_end:.3f}"
    return f"STA {station_start:.3f}-{station_end:.3f}"


def _target_scope_label(scope_kind: object) -> str:
    scope = str(scope_kind or "").strip().lower()
    if scope in {"assembly_subassembly", "assembly_component"}:
        return "Subassembly"
    if scope == "whole_corridor":
        return "Whole Corridor"
    if scope == "station_range":
        return "Station Range"
    if scope == "region":
        return "Region"
    if scope == "structure":
        return "Structure"
    if scope == "drainage":
        return "Drainage"
    if scope == "intersection":
        return "Intersection"
    return str(scope_kind or "")


def _target_source_text(row: object) -> str:
    subassembly_ref = str(getattr(row, "subassembly_ref", "") or "")
    component_ref = str(getattr(row, "component_ref", "") or "")
    compatibility_ref = f"compatibility:{component_ref}" if component_ref and not subassembly_ref else ""
    values = [
        str(getattr(row, "assembly_ref", "") or ""),
        str(getattr(row, "structure_ref", "") or ""),
        str(getattr(row, "drainage_ref", "") or ""),
        str(getattr(row, "flow_route_ref", "") or ""),
        subassembly_ref,
        compatibility_ref,
        str(getattr(row, "material_ref", "") or ""),
    ]
    text = ", ".join(value for value in values if value)
    return text or ", ".join(str(value) for value in list(getattr(row, "source_refs", []) or []) if str(value))


def _target_context_text(row: object) -> str:
    values = [f"target={_target_display_label(row)}"]
    drainage_ref = str(getattr(row, "drainage_ref", "") or "")
    if drainage_ref:
        values.append(f"drainage={drainage_ref}")
        side = _side_from_ref(drainage_ref)
        if side:
            values.append(f"side={side}")
    component_ref = str(getattr(row, "component_ref", "") or "")
    subassembly_ref = str(getattr(row, "subassembly_ref", "") or "")
    if subassembly_ref:
        values.append(f"subassembly={subassembly_ref}")
    if component_ref and not subassembly_ref:
        values.append(f"compatibility_ref={component_ref}")
    material_ref = str(getattr(row, "material_ref", "") or "")
    if material_ref:
        values.append(f"material={material_ref}")
    return "; ".join(values)


def _is_drainage_pipeline_target(row: object) -> bool:
    return str(getattr(row, "target_family", "") or "").strip().lower() in {"drainage_pipeline_body", "drainage_pipeline_network_body"}


def _is_drainage_pipeline_network_target(row: object) -> bool:
    return str(getattr(row, "target_family", "") or "").strip().lower() == "drainage_pipeline_network_body"


def _is_structure_body_target(row: object) -> bool:
    return str(getattr(row, "target_family", "") or "").strip().lower() == "structure_body"


def _is_intersection_patch_target(row: object) -> bool:
    return str(getattr(row, "target_family", "") or "").strip().lower() == "intersection_patch_body"


def _is_intersection_watertight_target(row: object) -> bool:
    return str(getattr(row, "target_family", "") or "").strip().lower() in {
        "intersection_patch_body",
        "intersection_pavement_body",
        "intersection_subgrade_body",
        "intersection_slope_body",
        "intersection_curb_return_body",
    }


def _intersection_patch_context(document, target_row) -> dict[str, object]:
    if document is None:
        raise RuntimeError("A FreeCAD document is required for Intersection patch solid output.")
    applied = to_applied_section_set(find_v1_applied_section_set(document))
    if applied is None:
        raise RuntimeError("Applied Sections are required for Intersection patch solid output.")
    intersection_id = _intersection_target_ref(target_row)
    control_refs = _unique_refs(str(getattr(target_row, "region_ref", "") or "").split(","))
    preview_context = _intersection_patch_preview_context(document, intersection_id, target_row, control_refs)
    if preview_context is not None:
        return preview_context
    points: list[dict[str, object]] = []
    seen_xy: set[tuple[float, float]] = set()
    for section in list(getattr(applied, "sections", []) or []):
        section_intersection = str(getattr(section, "active_intersection_id", "") or "").strip()
        section_region = str(getattr(section, "region_id", "") or "").strip()
        if intersection_id and section_intersection != intersection_id and section_region not in control_refs:
            continue
        for point in list(getattr(section, "point_rows", []) or []):
            if str(getattr(point, "point_role", "") or "") != "fg_surface":
                continue
            x = float(getattr(point, "x", 0.0) or 0.0)
            y = float(getattr(point, "y", 0.0) or 0.0)
            z = float(getattr(point, "z", 0.0) or 0.0)
            key = (round(x, 6), round(y, 6))
            if key in seen_xy:
                continue
            seen_xy.add(key)
            points.append(
                {
                    "x": x,
                    "y": y,
                    "z": z,
                    "station": float(getattr(section, "station", 0.0) or 0.0),
                    "section_ref": str(getattr(section, "applied_section_id", "") or ""),
                    "region_ref": section_region,
                }
            )
    if len(points) < 3:
        raise RuntimeError("Intersection patch solid needs at least three unique fg_surface boundary points.")
    centroid_x = sum(float(point["x"]) for point in points) / len(points)
    centroid_y = sum(float(point["y"]) for point in points) / len(points)
    ordered = sorted(points, key=lambda point: math.atan2(float(point["y"]) - centroid_y, float(point["x"]) - centroid_x))
    area_xy = abs(_polygon_area_xy(ordered))
    min_edge_length = _polygon_min_edge_length_xy(ordered)
    quality_diagnostics = _intersection_patch_quality_diagnostics(
        ordered,
        area_xy=area_xy,
        min_edge_length=min_edge_length,
    )
    stations = [float(point.get("station", 0.0) or 0.0) for point in ordered]
    return {
        "intersection_id": intersection_id,
        "control_refs": control_refs,
        "boundary_points": ordered,
        "boundary_count": len(ordered),
        "area_xy": area_xy,
        "min_edge_length": min_edge_length,
        "quality_diagnostics": quality_diagnostics,
        "control_region_count": len(control_refs),
        "station_start": min(stations) if stations else float(getattr(target_row, "station_start", 0.0) or 0.0),
        "station_end": max(stations) if stations else float(getattr(target_row, "station_end", 0.0) or 0.0),
        "depth": _intersection_patch_depth(target_row),
        "source_refs": _unique_refs([intersection_id, *control_refs, *list(getattr(target_row, "source_refs", []) or [])]),
        "boundary_source": "applied_section_fg_surface",
    }


def _intersection_patch_preview_context(document, intersection_id: str, target_row, control_refs: list[str]) -> dict[str, object] | None:
    preview = document.getObject("V1CorridorIntersectionSurfacePreview") if document is not None else None
    if preview is None:
        return None
    preview_intersection = str(getattr(preview, "IntersectionId", "") or "").strip()
    if intersection_id and preview_intersection and preview_intersection != intersection_id:
        return None
    boundary_closed = str(getattr(preview, "IntersectionPatchBoundaryClosed", "") or "").strip().lower()
    if boundary_closed and boundary_closed not in {"yes", "true", "1"}:
        raise RuntimeError("intersection_patch_boundary_open: refined Intersection patch boundary is not closed.")
    diagnostic_count = int(getattr(preview, "IntersectionPatchBoundaryDiagnosticCount", 0) or 0)
    if diagnostic_count:
        diagnostics = [
            str(value or "")
            for value in list(getattr(preview, "IntersectionPatchBoundaryDiagnostics", []) or [])
            if str(value or "")
        ]
        message = diagnostics[0] if diagnostics else f"{diagnostic_count} patch boundary diagnostic(s)."
        raise RuntimeError(f"intersection_patch_boundary_diagnostics: {message}")
    ordered_count = int(getattr(preview, "IntersectionPatchBoundaryOrderedPointCount", 0) or 0)
    points = _intersection_patch_preview_boundary_points(preview, max(ordered_count, 0))
    if len(points) < 3:
        return None
    area_xy = abs(_polygon_area_xy(points))
    min_edge_length = _polygon_min_edge_length_xy(points)
    quality_diagnostics = _intersection_patch_quality_diagnostics(
        points,
        area_xy=area_xy,
        min_edge_length=min_edge_length,
    )
    source_refs = _unique_refs(
        [
            intersection_id,
            *control_refs,
            *list(getattr(target_row, "source_refs", []) or []),
            str(getattr(preview, "Name", "") or ""),
            str(getattr(preview, "TieInEdgePreviewRef", "") or ""),
            str(getattr(preview, "IntersectionBoundaryPreviewRef", "") or ""),
            str(getattr(preview, "IntersectionExclusionZoneRef", "") or ""),
        ]
    )
    return {
        "intersection_id": intersection_id or preview_intersection,
        "control_refs": control_refs,
        "boundary_points": points,
        "boundary_count": len(points),
        "area_xy": area_xy,
        "min_edge_length": min_edge_length,
        "quality_diagnostics": quality_diagnostics,
        "control_region_count": len(control_refs),
        "station_start": float(getattr(target_row, "station_start", 0.0) or 0.0),
        "station_end": float(getattr(target_row, "station_end", 0.0) or 0.0),
        "depth": _intersection_patch_depth(target_row),
        "source_refs": source_refs,
        "boundary_source": "refined_intersection_surface_preview",
        "triangulation_mode": str(getattr(preview, "PatchTriangulationMode", "") or ""),
        "surface_boundary_strategy": str(getattr(preview, "PatchBoundaryStrategy", "") or getattr(preview, "PatchTriangulationMode", "") or ""),
        "edge_blend_face_count": int(getattr(preview, "PatchEdgeBlendFaceCount", 0) or 0),
        "curb_return_arc_count": int(getattr(preview, "PatchCurbReturnArcCount", 0) or 0),
        "curb_return_arc_sample_count": int(getattr(preview, "PatchCurbReturnArcSampleCount", 0) or 0),
        "curb_return_arc_segment_count": int(getattr(preview, "PatchCurbReturnArcSegmentCount", 0) or 0),
    }


def _intersection_patch_preview_boundary_points(preview, ordered_count: int) -> list[dict[str, object]]:
    points = _intersection_patch_preview_mesh_points(preview)
    if not points:
        points = _intersection_patch_preview_shape_points(preview)
    if ordered_count > 0 and len(points) >= ordered_count:
        points = points[:ordered_count]
    return _dedupe_patch_xy_points(points)


def _intersection_patch_preview_mesh_points(preview) -> list[dict[str, object]]:
    mesh = getattr(preview, "Mesh", None)
    if mesh is None:
        return []
    try:
        topology = mesh.Topology
        raw_points = list(topology[0] or [])
    except Exception:
        raw_points = []
    points: list[dict[str, object]] = []
    for index, point in enumerate(raw_points, start=1):
        try:
            points.append({"x": float(point.x), "y": float(point.y), "z": float(point.z), "source": f"preview-mesh:{index}"})
        except Exception:
            try:
                points.append({"x": float(point[0]), "y": float(point[1]), "z": float(point[2]), "source": f"preview-mesh:{index}"})
            except Exception:
                continue
    return points


def _intersection_patch_preview_shape_points(preview) -> list[dict[str, object]]:
    shape = getattr(preview, "Shape", None)
    vertexes = list(getattr(shape, "Vertexes", []) or []) if shape is not None else []
    points: list[dict[str, object]] = []
    for index, vertex in enumerate(vertexes, start=1):
        try:
            point = vertex.Point
            points.append({"x": float(point.x), "y": float(point.y), "z": float(point.z), "source": f"preview-shape:{index}"})
        except Exception:
            continue
    return points


def _dedupe_patch_xy_points(points: list[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    seen: set[tuple[float, float]] = set()
    for point in list(points or []):
        key = (round(float(point.get("x", 0.0) or 0.0), 6), round(float(point.get("y", 0.0) or 0.0), 6))
        if key in seen:
            continue
        seen.add(key)
        output.append(point)
    return output


def _intersection_patch_solid_shape(patch: dict[str, object]):
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Intersection patch solid build.")
    points = list(patch.get("boundary_points", []) or [])
    if len(points) < 3:
        raise RuntimeError("Intersection patch solid needs at least three boundary points.")
    depth = max(float(patch.get("depth", 0.0) or 0.0), 0.05)
    top = [App.Vector(float(point["x"]), float(point["y"]), float(point["z"])) for point in points]
    bottom = [App.Vector(point.x, point.y, point.z - depth) for point in top]
    center_top = App.Vector(
        sum(point.x for point in top) / len(top),
        sum(point.y for point in top) / len(top),
        sum(point.z for point in top) / len(top),
    )
    center_bottom = App.Vector(center_top.x, center_top.y, center_top.z - depth)
    faces = []
    for index, current in enumerate(top):
        nxt = top[(index + 1) % len(top)]
        bottom_current = bottom[index]
        bottom_next = bottom[(index + 1) % len(bottom)]
        faces.append(Part.Face(Part.makePolygon([center_top, current, nxt, center_top])))
        faces.append(Part.Face(Part.makePolygon([center_bottom, bottom_next, bottom_current, center_bottom])))
        faces.append(Part.Face(Part.makePolygon([current, bottom_current, bottom_next, nxt, current])))
    shell = Part.Shell(faces)
    solid = Part.Solid(shell)
    if solid is None or _shape_count(solid, "Solids") <= 0:
        raise RuntimeError("FreeCAD Part failed to create an Intersection patch solid.")
    return solid


def _intersection_patch_watertight_output(target_row, *, patch: dict[str, object], shape, generated_object_ref: str) -> WatertightSolidOutput:
    target_id = str(getattr(target_row, "target_id", "") or "")
    output_object_id = f"watertight-solid:{_safe_object_id(target_id)}"
    source_refs = _unique_refs([target_id, *list(patch.get("source_refs", []) or []), *list(getattr(target_row, "source_refs", []) or [])])
    volume = float(getattr(shape, "Volume", 0.0) or 0.0)
    solid = WatertightSolidOutputRow(
        output_object_id=output_object_id,
        target_id=target_id,
        target_family=str(getattr(target_row, "target_family", "") or "intersection_patch_body"),
        scope_kind=str(getattr(target_row, "scope_kind", "") or "intersection"),
        station_start=float(patch.get("station_start", getattr(target_row, "station_start", 0.0)) or 0.0),
        station_end=float(patch.get("station_end", getattr(target_row, "station_end", 0.0)) or 0.0),
        source_refs=source_refs,
        generated_object_ref=str(generated_object_ref or ""),
        validation_status="ok" if volume > 0.0 else "error",
        is_watertight=volume > 0.0,
        is_valid_solid=volume > 0.0,
        volume=volume,
        face_count=_shape_count(shape, "Faces"),
        edge_count=_shape_count(shape, "Edges"),
        profile_count=int(patch.get("boundary_count", 0) or 0),
        region_ref=str(getattr(target_row, "region_ref", "") or ""),
        subassembly_ref=str(getattr(target_row, "subassembly_ref", "") or ""),
        material_ref=str(getattr(target_row, "material_ref", "") or "intersection-patch"),
        path_source=str(patch.get("boundary_source", "") or "intersection_patch_fg_surface"),
        notes=(
            f"Intersection patch solid from {patch.get('boundary_source', 'fg_surface boundary')}; intersection={patch.get('intersection_id', '')}; "
            f"boundary_points={int(patch.get('boundary_count', 0) or 0)}; "
            f"area_xy={float(patch.get('area_xy', 0.0) or 0.0):.3f}; "
            f"min_edge={float(patch.get('min_edge_length', 0.0) or 0.0):.3f}; "
            f"depth={float(patch.get('depth', 0.0) or 0.0):.3f}; "
            f"boundary={str(patch.get('surface_boundary_strategy', '') or patch.get('triangulation_mode', '') or '-')}; "
            f"edge_blend_faces={int(patch.get('edge_blend_face_count', 0) or 0)}; "
            f"curb_return_arcs={int(patch.get('curb_return_arc_count', 0) or 0)}."
        ),
    )
    segment = WatertightSolidSegmentRow(
        segment_id=f"{output_object_id}:segment:1",
        parent_output_object_id=output_object_id,
        station_start=solid.station_start,
        station_end=solid.station_end,
        notes=f"intersection={patch.get('intersection_id', '')};control_regions={','.join(list(patch.get('control_refs', []) or []))}",
    )
    return WatertightSolidOutput(
        schema_version=1,
        project_id="corridorroad-v1",
        watertight_solid_output_id="watertight-solids:intersection-patch",
        corridor_id="corridor:main",
        label="Watertight Solids",
        selection_scope={"scope_kind": str(getattr(target_row, "scope_kind", "") or ""), "target_id": target_id},
        source_refs=source_refs,
        result_refs=[str(generated_object_ref or "")],
        solid_rows=[solid],
        segment_rows=[segment],
    )


def _intersection_target_ref(target_row) -> str:
    for ref in list(getattr(target_row, "source_refs", []) or []):
        text = str(ref or "").strip()
        if text.startswith("intersection:"):
            return text
    target_id = str(getattr(target_row, "target_id", "") or "")
    if "intersection-" in target_id:
        return "intersection:" + target_id.split("intersection-", 1)[1].replace("-", "-")
    return ""


def _intersection_patch_quality_diagnostics(
    boundary_points: list[dict[str, object]],
    *,
    area_xy: float,
    min_edge_length: float,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if len(boundary_points) < 3:
        rows.append(
            {
                "severity": "error",
                "kind": "intersection_patch_boundary_too_few_points",
                "message": "Intersection patch solid needs at least three unique boundary points.",
            }
        )
    if float(area_xy or 0.0) <= 1.0e-6:
        rows.append(
            {
                "severity": "error",
                "kind": "intersection_patch_boundary_zero_area",
                "message": "Intersection patch boundary area is zero or too small.",
            }
        )
    if len(boundary_points) >= 3 and float(min_edge_length or 0.0) <= 1.0e-6:
        rows.append(
            {
                "severity": "error",
                "kind": "intersection_patch_boundary_degenerate_edge",
                "message": "Intersection patch boundary contains a zero-length or near-zero edge.",
            }
        )
    return rows


def _polygon_area_xy(points: list[dict[str, object]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, current in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        area += float(current.get("x", 0.0) or 0.0) * float(nxt.get("y", 0.0) or 0.0)
        area -= float(nxt.get("x", 0.0) or 0.0) * float(current.get("y", 0.0) or 0.0)
    return area / 2.0


def _polygon_min_edge_length_xy(points: list[dict[str, object]]) -> float:
    if len(points) < 2:
        return 0.0
    lengths: list[float] = []
    for index, current in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        dx = float(nxt.get("x", 0.0) or 0.0) - float(current.get("x", 0.0) or 0.0)
        dy = float(nxt.get("y", 0.0) or 0.0) - float(current.get("y", 0.0) or 0.0)
        lengths.append(math.hypot(dx, dy))
    return min(lengths) if lengths else 0.0


def _intersection_patch_depth(target_row) -> float:
    try:
        return max(float(getattr(target_row, "thickness", 0.0) or 0.0), 0.50)
    except Exception:
        return 0.50


def _structure_body_output_context(document, target_row):
    if document is None:
        raise RuntimeError("A FreeCAD document is required for Structure body solid output.")
    applied = to_applied_section_set(find_v1_applied_section_set(document))
    corridor = to_corridor_model(find_v1_corridor_model(document))
    structure_model = to_structure_model(find_v1_structure_model(document))
    if corridor is None or structure_model is None:
        raise RuntimeError("CorridorModel and StructureModel are required for Structure body solid output.")
    structure_ref = str(getattr(target_row, "structure_ref", "") or "")
    output = StructureSolidOutputService().build(
        StructureSolidBuildRequest(
            project_id=str(getattr(corridor, "project_id", "") or getattr(structure_model, "project_id", "") or "corridorroad-v1"),
            corridor=corridor,
            structure_model=structure_model,
            applied_section_set=applied,
            active_structure_refs=[structure_ref] if structure_ref else [],
            structure_solid_output_id="structure-solids:watertight",
        )
    )
    solid_rows = [
        row for row in list(getattr(output, "solid_rows", []) or [])
        if not structure_ref or str(getattr(row, "structure_id", "") or "") == structure_ref
    ]
    if not solid_rows:
        diagnostic_text = "; ".join(
            str(getattr(row, "message", "") or "")
            for row in list(getattr(output, "diagnostic_rows", []) or [])
            if str(getattr(row, "message", "") or "")
        )
        raise RuntimeError(diagnostic_text or f"Structure {structure_ref} did not produce a solid output row.")
    return output, solid_rows[0]


def _external_structure_body_shape_context(document, target_row):
    if document is None:
        return None
    structure_model = to_structure_model(find_v1_structure_model(document))
    if structure_model is None:
        return None
    structure_ref = str(getattr(target_row, "structure_ref", "") or "")
    structure_row = _structure_row_by_ref(structure_model, structure_ref)
    if structure_row is None or _structure_geometry_source_mode(structure_row) != "external_ref":
        return None
    geometry_ref = str(getattr(structure_row, "geometry_ref", "") or "").strip()
    if not geometry_ref:
        raise RuntimeError(f"External Structure {structure_ref} has no geometry_ref.")
    external_obj = _find_document_object_by_ref(document, geometry_ref)
    if external_obj is None:
        raise RuntimeError(f"External Structure geometry_ref {geometry_ref} was not found in the document.")
    shape = getattr(external_obj, "Shape", None)
    if shape is None or (_shape_count(shape, "Solids") <= 0 and _shape_count(shape, "Faces") <= 0):
        raise RuntimeError(f"External Structure geometry_ref {geometry_ref} has no usable Shape.")
    try:
        shape = shape.copy()
    except Exception:
        pass
    return structure_model, structure_row, shape, external_obj


def _find_document_object_by_ref(document, ref: str):
    text = str(ref or "").strip()
    if not text:
        return None
    candidates = [text]
    if ":" in text:
        candidates.append(text.split(":")[-1])
    for candidate in candidates:
        try:
            obj = document.getObject(candidate)
            if obj is not None:
                return obj
        except Exception:
            pass
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        label = str(getattr(obj, "Label", "") or "")
        if text in {name, label}:
            return obj
        if ":" in text and text.split(":")[-1] in {name, label}:
            return obj
    return None


def _external_structure_connection_point_validation(structure_model, structure_row, shape) -> tuple[str, str]:
    structure_ref = str(getattr(structure_row, "structure_id", "") or "")
    points = [
        point for point in list(getattr(structure_model, "connection_point_rows", []) or [])
        if str(getattr(point, "structure_ref", "") or "") == structure_ref
    ]
    if not _external_structure_requires_connection_points(structure_row):
        return "ok", f"connection_point_status=not_required; connection_point_count={len(points)}."
    if not points:
        return "error", "connection_point_status=missing; connection_point_count=0."
    bbox = getattr(shape, "BoundBox", None)
    if bbox is None:
        return "error", f"connection_point_status=shape_bbox_missing; connection_point_count={len(points)}."
    outside: list[str] = []
    max_distance = 0.0
    for point in points:
        vector = _connection_point_world_vector(point)
        tolerance = _connection_point_shape_tolerance(point)
        distance = _bound_box_distance_to_point(bbox, vector)
        max_distance = max(max_distance, distance)
        if distance > tolerance:
            outside.append(str(getattr(point, "connection_point_id", "") or "connection-point"))
    if outside:
        return (
            "error",
            "connection_point_status=outside_shape; "
            f"connection_point_count={len(points)}; outside_connection_points={len(outside)}; "
            f"max_bbox_distance={max_distance:.3f}; refs={','.join(outside)}.",
        )
    return (
        "ok",
        "connection_point_status=ok; "
        f"connection_point_count={len(points)}; outside_connection_points=0; max_bbox_distance={max_distance:.3f}.",
    )


def _external_structure_requires_connection_points(structure_row) -> bool:
    values = [
        str(getattr(structure_row, "structure_kind", "") or ""),
        str(getattr(structure_row, "structure_role", "") or ""),
        str(getattr(structure_row, "native_type", "") or ""),
    ]
    drainage_tokens = {
        "box_culvert",
        "culvert",
        "drainage_crossing",
        "drainage_node",
        "headwall",
        "inlet",
        "junction_box",
        "manhole",
        "outlet",
        "pipe_culvert",
    }
    return any(value.strip().lower() in drainage_tokens for value in values)


def _connection_point_world_vector(point):
    z_value = getattr(point, "invert_elevation", None)
    if z_value is None:
        z_value = getattr(point, "elevation", None)
    return App.Vector(
        float(getattr(point, "station", 0.0) or 0.0),
        float(getattr(point, "offset", 0.0) or 0.0),
        float(z_value if z_value is not None else 0.0),
    )


def _connection_point_shape_tolerance(point) -> float:
    size = max(
        float(getattr(point, "diameter", 0.0) or 0.0),
        float(getattr(point, "width", 0.0) or 0.0),
        float(getattr(point, "height", 0.0) or 0.0),
        0.02,
    )
    return max(size / 2.0, 0.02)


def _bound_box_distance_to_point(bbox, point) -> float:
    dx = _axis_distance(float(point.x), float(getattr(bbox, "XMin", 0.0)), float(getattr(bbox, "XMax", 0.0)))
    dy = _axis_distance(float(point.y), float(getattr(bbox, "YMin", 0.0)), float(getattr(bbox, "YMax", 0.0)))
    dz = _axis_distance(float(point.z), float(getattr(bbox, "ZMin", 0.0)), float(getattr(bbox, "ZMax", 0.0)))
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def _axis_distance(value: float, minimum: float, maximum: float) -> float:
    if value < minimum:
        return minimum - value
    if value > maximum:
        return value - maximum
    return 0.0


def _drainage_pipeline_output_context(document, target_row):
    alignment_model = to_alignment_model(find_v1_alignment(document))
    drainage_model = to_drainage_model(find_v1_drainage_model(document))
    structure_model = to_structure_model(find_v1_structure_model(document))
    if drainage_model is None or structure_model is None:
        raise RuntimeError("DrainageModel and StructureModel are required for Drainage pipeline solid output.")
    coordinate_frame = _centerline3d_coordinate_frame(document)
    output = DrainageReviewMapper().map(
        drainage_model=drainage_model,
        alignment_model=alignment_model,
        structure_model=structure_model,
        project_id=str(getattr(drainage_model, "project_id", "") or "corridorroad-v1"),
        station_offset_to_xy=coordinate_frame.get("adapter"),
        coordinate_mode=str(coordinate_frame.get("coordinate_mode", "") or ""),
    )
    segment_ref = str(getattr(target_row, "drainage_ref", "") or "").strip()
    flow_route_ref = str(getattr(target_row, "flow_route_ref", "") or "").strip()
    geometry_row = None
    for row in list(getattr(output, "pipeline_geometry_rows", []) or []):
        if segment_ref and str(getattr(row, "pipeline_segment_id", "") or "") == segment_ref:
            geometry_row = row
            break
        if flow_route_ref and str(getattr(row, "flow_route_ref", "") or "") == flow_route_ref:
            geometry_row = row
            break
    if geometry_row is None:
        raise RuntimeError("No matching Drainage pipeline geometry row is available for the selected target.")
    solid_row = None
    for row in list(getattr(output, "pipeline_solid_rows", []) or []):
        if str(getattr(row, "pipeline_segment_id", "") or "") == str(getattr(geometry_row, "pipeline_segment_id", "") or ""):
            solid_row = row
            break
    if solid_row is None:
        raise RuntimeError("No matching Drainage pipeline solid candidate row is available for the selected target.")
    return output, geometry_row, solid_row


def _drainage_pipeline_network_output_context(document, target_row):
    alignment_model = to_alignment_model(find_v1_alignment(document))
    drainage_model = to_drainage_model(find_v1_drainage_model(document))
    structure_model = to_structure_model(find_v1_structure_model(document))
    if drainage_model is None or structure_model is None:
        raise RuntimeError("DrainageModel and StructureModel are required for Drainage pipeline network solid output.")
    coordinate_frame = _centerline3d_coordinate_frame(document)
    output = DrainageReviewMapper().map(
        drainage_model=drainage_model,
        alignment_model=alignment_model,
        structure_model=structure_model,
        project_id=str(getattr(drainage_model, "project_id", "") or "corridorroad-v1"),
        station_offset_to_xy=coordinate_frame.get("adapter"),
        coordinate_mode=str(coordinate_frame.get("coordinate_mode", "") or ""),
    )
    network_ref = str(getattr(target_row, "drainage_ref", "") or "").strip() or "drainage-pipeline-network:main"
    network_row = None
    for row in list(getattr(output, "pipeline_network_rows", []) or []):
        if str(getattr(row, "network_id", "") or "") == network_ref:
            network_row = row
            break
    if network_row is None:
        raise RuntimeError("No matching Drainage pipeline network row is available for the selected target.")
    solid_refs = set(str(value) for value in list(getattr(network_row, "solid_row_refs", []) or []) if str(value))
    solid_rows = [
        row for row in list(getattr(output, "pipeline_solid_rows", []) or [])
        if str(getattr(row, "solid_row_id", "") or "") in solid_refs
    ]
    geometry_refs = set(str(getattr(row, "geometry_row_ref", "") or "") for row in solid_rows if str(getattr(row, "geometry_row_ref", "") or ""))
    geometry_rows = [
        row for row in list(getattr(output, "pipeline_geometry_rows", []) or [])
        if str(getattr(row, "geometry_row_id", "") or "") in geometry_refs
    ]
    if not geometry_rows or not solid_rows:
        raise RuntimeError("Drainage pipeline network has no matching geometry or solid candidate rows.")
    junction_rows = [
        row for row in list(getattr(output, "pipeline_junction_rows", []) or [])
        if str(getattr(row, "network_ref", "") or "") == network_ref
    ]
    return output, network_row, geometry_rows, solid_rows, junction_rows


def _centerline3d_coordinate_frame(document) -> dict[str, object]:
    try:
        from .cmd_centerline3d import build_document_centerline3d_result
        from ..services.evaluation import Centerline3DFrameService

        result = build_document_centerline3d_result(document)
    except Exception:
        return {"adapter": None, "coordinate_mode": ""}
    point_rows = list(getattr(result, "point_rows", []) or [])
    if str(getattr(result, "status", "") or "") != "ready" or len(point_rows) < 2:
        return {"adapter": None, "coordinate_mode": ""}
    frame_service = Centerline3DFrameService()

    def _adapter(station: float, offset: float) -> tuple[float, float, float]:
        frame = frame_service.resolve_station_offset(result, station, offset)
        return float(frame.x), float(frame.y), float(frame.z)

    return {"adapter": _adapter, "coordinate_mode": "centerline3d_result"}


def _profile_set_on_centerline3d(document, profile_set):
    frame = _centerline3d_coordinate_frame(document)
    adapter = frame.get("adapter")
    if adapter is None:
        return profile_set
    converted_profiles = []
    changed = False
    for profile in list(getattr(profile_set, "profile_rows", []) or []):
        station = float(getattr(profile, "station", 0.0) or 0.0)
        converted_nodes = []
        for node in list(getattr(profile, "node_rows", []) or []):
            offset = float(getattr(node, "lateral_offset", 0.0) or 0.0)
            vertical_offset = float(getattr(node, "vertical_offset", 0.0) or 0.0)
            try:
                x, y, center_z = adapter(station, offset)
            except Exception:
                converted_nodes.append(node)
                continue
            converted_nodes.append(
                replace(
                    node,
                    x=float(x),
                    y=float(y),
                    z=float(center_z) + vertical_offset,
                )
            )
            changed = True
        notes = str(getattr(profile, "notes", "") or "")
        if changed and "path_source=centerline3d_result" not in notes:
            notes = (notes + ";path_source=centerline3d_result").strip(";")
        converted_profiles.append(replace(profile, node_rows=converted_nodes, notes=notes))
    if not changed:
        return profile_set
    source_refs = _unique_refs([*list(getattr(profile_set, "source_refs", []) or []), "centerline3d_result"])
    return replace(profile_set, profile_rows=converted_profiles, source_refs=source_refs)


def _structure_body_solid_shape(solid_row, *, structure_model=None):
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Structure body solid build.")
    width = float(getattr(solid_row, "width", 0.0) or 0.0)
    height = float(getattr(solid_row, "height", 0.0) or 0.0)
    start = App.Vector(
        float(getattr(solid_row, "start_x", getattr(solid_row, "placement_x", 0.0)) or 0.0),
        float(getattr(solid_row, "start_y", getattr(solid_row, "placement_y", 0.0)) or 0.0),
        float(getattr(solid_row, "start_z", getattr(solid_row, "placement_z", 0.0)) or 0.0),
    )
    end = App.Vector(
        float(getattr(solid_row, "end_x", 0.0) or 0.0),
        float(getattr(solid_row, "end_y", 0.0) or 0.0),
        float(getattr(solid_row, "end_z", 0.0) or 0.0),
    )
    direction = end.sub(start)
    length = float(getattr(solid_row, "length", 0.0) or 0.0)
    if direction.Length <= 1.0e-9:
        direction = App.Vector(max(length, 1.0), 0.0, 0.0)
    if length <= 1.0e-9:
        length = direction.Length
    if width <= 0.0 or height <= 0.0 or length <= 0.0:
        raise RuntimeError("Structure body dimensions must be greater than zero.")
    circular_profile = _circular_structure_body_profile(solid_row, structure_model)
    if circular_profile is not None:
        inner_diameter, outer_diameter, wall_thickness = circular_profile
        try:
            if wall_thickness > 0.0 and outer_diameter > inner_diameter:
                return _hollow_circular_structure_body_shape(
                    start,
                    direction,
                    length,
                    inner_diameter=inner_diameter,
                    outer_diameter=outer_diameter,
                )
            return Part.makeCylinder(inner_diameter / 2.0, length, start, direction)
        except Exception:
            pass
    drainage_endpoint_shape = _drainage_endpoint_structure_body_shape(
        solid_row,
        structure_model,
        start=start,
        direction=direction,
        length=length,
        width=width,
        height=height,
    )
    if drainage_endpoint_shape is not None:
        return drainage_endpoint_shape
    shape = _oriented_local_box_shape(
        0.0,
        -width / 2.0,
        -height / 2.0,
        length,
        width,
        height,
        start=start,
        direction=direction,
    )
    return shape


def _oriented_local_box_shape(x: float, y: float, z: float, dx: float, dy: float, dz: float, *, start, direction):
    shape = Part.makeBox(dx, dy, dz, App.Vector(x, y, z))
    try:
        shape.Placement = App.Placement(start, App.Rotation(App.Vector(1.0, 0.0, 0.0), direction))
        return shape
    except Exception:
        return Part.makeBox(dx, dy, dz, start)


def _drainage_endpoint_structure_body_shape(solid_row, structure_model, *, start, direction, length: float, width: float, height: float):
    profile = _drainage_endpoint_structure_profile(solid_row, structure_model)
    if profile is None:
        return None
    kind, diameter = profile
    if kind == "inlet":
        return _inlet_box_structure_body_shape(start, direction, length=length, width=width, height=height)
    if kind in {"outlet", "headwall"}:
        return _headwall_structure_body_shape(
            start,
            direction,
            length=length,
            width=width,
            height=height,
            opening_diameter=diameter,
        )
    return None


def _inlet_box_structure_body_shape(start, direction, *, length: float, width: float, height: float):
    outer = _oriented_local_box_shape(
        0.0,
        -width / 2.0,
        -height / 2.0,
        length,
        width,
        height,
        start=start,
        direction=direction,
    )
    chamber_length = max(length * 0.60, min(length, 0.10))
    chamber_width = max(width * 0.60, min(width, 0.10))
    chamber_height = max(height * 0.70, min(height, 0.10))
    if chamber_length >= length or chamber_width >= width or chamber_height >= height:
        return outer
    chamber = _oriented_local_box_shape(
        (length - chamber_length) / 2.0,
        -chamber_width / 2.0,
        -chamber_height / 2.0,
        chamber_length,
        chamber_width,
        chamber_height,
        start=start,
        direction=direction,
    )
    try:
        shape = outer.cut(chamber)
        return shape.removeSplitter()
    except Exception:
        return outer


def _headwall_structure_body_shape(start, direction, *, length: float, width: float, height: float, opening_diameter: float):
    body = _oriented_local_box_shape(
        0.0,
        -width / 2.0,
        -height / 2.0,
        length,
        width,
        height,
        start=start,
        direction=direction,
    )
    radius = max(float(opening_diameter or 0.0) / 2.0, min(width, height) * 0.18)
    if radius <= 0.0 or radius * 2.0 >= min(width, height):
        return body
    try:
        unit = App.Vector(float(direction.x), float(direction.y), float(direction.z))
        if unit.Length <= 1.0e-9:
            return body
        unit.normalize()
        epsilon = min(max(radius * 0.25, 0.01), max(float(length) * 0.05, 0.01))
        cutter_start = App.Vector(
            float(start.x) - float(unit.x) * epsilon,
            float(start.y) - float(unit.y) * epsilon,
            float(start.z) - float(unit.z) * epsilon,
        )
        cutter = Part.makeCylinder(radius, float(length) + 2.0 * epsilon, cutter_start, direction)
        shape = body.cut(cutter)
        return shape.removeSplitter()
    except Exception:
        return body


def _hollow_circular_structure_body_shape(start, direction, length: float, *, inner_diameter: float, outer_diameter: float):
    outer = Part.makeCylinder(outer_diameter / 2.0, length, start, direction)
    unit = App.Vector(float(direction.x), float(direction.y), float(direction.z))
    if unit.Length <= 1.0e-9:
        return outer
    unit.normalize()
    epsilon = min(max(outer_diameter * 0.1, 0.01), max(float(length) * 0.05, 0.01))
    inner_start = App.Vector(
        float(start.x) - float(unit.x) * epsilon,
        float(start.y) - float(unit.y) * epsilon,
        float(start.z) - float(unit.z) * epsilon,
    )
    inner = Part.makeCylinder(inner_diameter / 2.0, float(length) + 2.0 * epsilon, inner_start, direction)
    hollow = outer.cut(inner)
    try:
        hollow = hollow.removeSplitter()
    except Exception:
        pass
    return hollow


def _circular_structure_body_profile(solid_row, structure_model) -> tuple[float, float, float] | None:
    if structure_model is None:
        return None
    structure_ref = str(getattr(solid_row, "structure_id", "") or getattr(solid_row, "structure_ref", "") or "")
    spec_ref = str(getattr(solid_row, "geometry_spec_id", "") or "")
    structure_row = _structure_row_by_ref(structure_model, structure_ref)
    spec = _geometry_spec_by_ref(structure_model, spec_ref)
    culvert = _culvert_spec_by_ref(structure_model, spec_ref)
    native_type = str(getattr(structure_row, "native_type", "") or "").strip().lower()
    shape_kind = str(getattr(spec, "shape_kind", "") or "").strip().lower()
    barrel_shape = str(getattr(culvert, "barrel_shape", "") or "").strip().lower()
    if native_type != "pipe_culvert" and shape_kind != "circular" and barrel_shape != "circular":
        return None
    inner_diameter = float(getattr(culvert, "diameter", 0.0) or 0.0)
    if inner_diameter <= 0.0:
        inner_diameter = max(
            float(getattr(solid_row, "width", 0.0) or 0.0),
            float(getattr(solid_row, "height", 0.0) or 0.0),
            float(getattr(spec, "width", 0.0) or 0.0) if spec is not None else 0.0,
            float(getattr(spec, "height", 0.0) or 0.0) if spec is not None else 0.0,
        )
    inner_diameter = max(inner_diameter, 0.0)
    if inner_diameter <= 0.0:
        return None
    wall_thickness = max(float(getattr(culvert, "wall_thickness", 0.0) or 0.0), 0.0)
    outer_diameter = inner_diameter + 2.0 * wall_thickness if wall_thickness > 0.0 else inner_diameter
    return inner_diameter, outer_diameter, wall_thickness


def _drainage_endpoint_structure_profile(solid_row, structure_model) -> tuple[str, float] | None:
    if structure_model is None:
        return None
    structure_ref = str(getattr(solid_row, "structure_id", "") or getattr(solid_row, "structure_ref", "") or "")
    spec_ref = str(getattr(solid_row, "geometry_spec_id", "") or "")
    structure_row = _structure_row_by_ref(structure_model, structure_ref)
    spec = _geometry_spec_by_ref(structure_model, spec_ref)
    kind = _drainage_endpoint_kind(structure_row, spec, solid_row)
    if not kind:
        return None
    diameter = 0.0
    for point in list(getattr(structure_model, "connection_point_rows", []) or []):
        if str(getattr(point, "structure_ref", "") or "") != structure_ref:
            continue
        diameter = max(diameter, float(getattr(point, "diameter", 0.0) or 0.0))
    return kind, diameter


def _drainage_endpoint_kind(structure_row, spec, solid_row) -> str:
    values = [
        str(getattr(structure_row, "native_type", "") or ""),
        str(getattr(structure_row, "structure_kind", "") or ""),
        str(getattr(spec, "shape_kind", "") or ""),
        str(getattr(solid_row, "solid_kind", "") or ""),
        str(getattr(solid_row, "notes", "") or ""),
    ]
    for value in values:
        text = value.strip().lower()
        if text in {"inlet", "inlet_box", "catch_basin", "inlet_body_solid"} or "drainage_native_kind=inlet" in text:
            return "inlet"
        if text in {"outlet", "outlet_headwall", "outlet_body_solid"} or "drainage_native_kind=outlet" in text:
            return "outlet"
        if text in {"headwall", "headwall_body_solid"} or "drainage_native_kind=headwall" in text:
            return "headwall"
    return ""


def _structure_row_by_ref(structure_model, structure_ref: str):
    for row in list(getattr(structure_model, "structure_rows", []) or []):
        if str(getattr(row, "structure_id", "") or "") == str(structure_ref or ""):
            return row
    return None


def _geometry_spec_by_ref(structure_model, geometry_spec_ref: str):
    for row in list(getattr(structure_model, "geometry_spec_rows", []) or []):
        if str(getattr(row, "geometry_spec_id", "") or "") == str(geometry_spec_ref or ""):
            return row
    return None


def _culvert_spec_by_ref(structure_model, geometry_spec_ref: str):
    for row in list(getattr(structure_model, "culvert_geometry_spec_rows", []) or []):
        if str(getattr(row, "geometry_spec_ref", "") or "") == str(geometry_spec_ref or ""):
            return row
    return None


def _structure_geometry_source_mode(row) -> str:
    mode = str(getattr(row, "geometry_source_mode", "") or "").strip().lower()
    if mode in {"native", "external_ref"}:
        return mode
    reference_mode = str(getattr(row, "reference_mode", "") or "").strip().lower()
    geometry_ref = str(getattr(row, "geometry_ref", "") or "").strip()
    if reference_mode in {"source_ref", "reference_geometry", "external_ref"} or geometry_ref:
        return "external_ref"
    return "native"


def _structure_body_watertight_output(
    target_row,
    *,
    structure_output,
    solid_row,
    shape,
    generated_object_ref: str,
) -> WatertightSolidOutput:
    target_id = str(getattr(target_row, "target_id", "") or "")
    output_object_id = f"watertight-solid:{_safe_object_id(target_id)}"
    structure_ref = str(getattr(solid_row, "structure_id", "") or getattr(target_row, "structure_ref", "") or "")
    source_refs = _unique_refs(
        [
            target_id,
            str(getattr(structure_output, "structure_solid_output_id", "") or ""),
            str(getattr(structure_output, "structure_model_id", "") or ""),
            str(getattr(solid_row, "output_object_id", "") or ""),
            structure_ref,
            str(getattr(solid_row, "geometry_spec_id", "") or ""),
            *list(getattr(target_row, "source_refs", []) or []),
            *list(getattr(structure_output, "source_refs", []) or []),
            *list(getattr(structure_output, "result_refs", []) or []),
        ]
    )
    shape_volume = float(getattr(shape, "Volume", 0.0) or 0.0)
    volume = shape_volume if shape_volume > 0.0 else max(float(getattr(solid_row, "volume", 0.0) or 0.0), 0.0)
    solid = WatertightSolidOutputRow(
        output_object_id=output_object_id,
        target_id=target_id,
        target_family=str(getattr(target_row, "target_family", "") or "structure_body"),
        scope_kind=str(getattr(target_row, "scope_kind", "") or "structure"),
        station_start=float(getattr(solid_row, "station_start", getattr(target_row, "station_start", 0.0)) or 0.0),
        station_end=float(getattr(solid_row, "station_end", getattr(target_row, "station_end", 0.0)) or 0.0),
        source_refs=source_refs,
        generated_object_ref=str(generated_object_ref or ""),
        validation_status="ok",
        is_watertight=True,
        is_valid_solid=True,
        volume=volume,
        face_count=_shape_count(shape, "Faces"),
        edge_count=_shape_count(shape, "Edges"),
        profile_count=1,
        region_ref=str(getattr(solid_row, "region_ref", "") or ""),
        assembly_ref=str(getattr(solid_row, "assembly_ref", "") or ""),
        subassembly_ref=str(getattr(target_row, "subassembly_ref", "") or ""),
        structure_ref=structure_ref,
        material_ref=str(getattr(target_row, "material_ref", "") or getattr(solid_row, "material", "") or ""),
        path_source=str(getattr(solid_row, "path_source", "") or ""),
        notes=(
            f"Structure body solid from {str(getattr(solid_row, 'output_object_id', '') or '')}; "
            f"solid_kind={str(getattr(solid_row, 'solid_kind', '') or '')}; "
            f"path_source={str(getattr(solid_row, 'path_source', '') or '')}."
        ),
    )
    segment = WatertightSolidSegmentRow(
        segment_id=f"{output_object_id}:segment:1",
        parent_output_object_id=output_object_id,
        station_start=float(getattr(solid_row, "station_start", getattr(target_row, "station_start", 0.0)) or 0.0),
        station_end=float(getattr(solid_row, "station_end", getattr(target_row, "station_end", 0.0)) or 0.0),
        notes=f"structure_id={structure_ref};geometry_spec_id={str(getattr(solid_row, 'geometry_spec_id', '') or '')}",
    )
    return WatertightSolidOutput(
        schema_version=1,
        project_id=str(getattr(structure_output, "project_id", "") or "corridorroad-v1"),
        watertight_solid_output_id="watertight-solids:structure-body",
        corridor_id=str(getattr(structure_output, "corridor_id", "") or "corridor:main"),
        label="Watertight Solids",
        selection_scope={"scope_kind": str(getattr(target_row, "scope_kind", "") or ""), "target_id": target_id},
        source_refs=source_refs,
        result_refs=_unique_refs(
            [
                str(getattr(structure_output, "structure_solid_output_id", "") or ""),
                str(getattr(solid_row, "output_object_id", "") or ""),
            ]
        ),
        solid_rows=[solid],
        segment_rows=[segment],
    )


def _drainage_pipeline_solid_shape(geometry_row):
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Drainage pipeline solid build.")
    points = [
        App.Vector(float(point[0]), float(point[1]), float(point[2]))
        for point in list(getattr(geometry_row, "centerline_points", []) or [])
        if len(point) >= 3
    ]
    diameter = max(float(getattr(geometry_row, "diameter", 0.0) or 0.0), 0.0)
    if len(points) < 2 or diameter <= 0.0:
        raise RuntimeError("Drainage pipeline solid needs at least two centerline points and a positive diameter.")
    shapes = []
    for point0, point1 in zip(points, points[1:]):
        direction = point1.sub(point0)
        length = direction.Length
        if length <= 1.0e-9:
            continue
        shapes.append(Part.makeCylinder(diameter / 2.0, length, point0, direction))
    if not shapes:
        raise RuntimeError("Drainage pipeline solid has no usable pipe segments.")
    if len(shapes) == 1:
        return shapes[0]
    return Part.Compound(shapes)


def _drainage_pipeline_network_solid_shape(
    geometry_rows,
    *,
    junction_rows=None,
    structure_body_shapes=None,
    structure_body_shape_map=None,
    connection_point_map=None,
):
    if Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Drainage pipeline network solid build.")
    active_geometry_rows, active_junction_rows, endpoint_trim_count = _trim_network_geometry_rows_to_structure_ports(
        geometry_rows,
        junction_rows,
        structure_body_shape_map or {},
    )
    pipe_shapes = []
    for geometry_row in list(active_geometry_rows or []):
        shape = _drainage_pipeline_solid_shape(geometry_row)
        if shape is not None:
            pipe_shapes.append(shape)
    connector_shapes = _drainage_pipeline_network_connector_shapes(active_junction_rows, active_geometry_rows)
    port_connector_shapes = _drainage_pipeline_network_port_connector_shapes(
        active_junction_rows,
        active_geometry_rows,
        structure_body_shape_map or {},
        connection_point_map or {},
    )
    valid_structure_shapes = [
        shape for shape in list(structure_body_shapes or [])
        if shape is not None and (_shape_count(shape, "Solids") > 0 or _shape_count(shape, "Faces") > 0)
    ]
    port_contact = _structure_port_contact_status(
        active_junction_rows,
        structure_body_shape_map or {},
        port_connector_count=len(port_connector_shapes),
        endpoint_trim_count=endpoint_trim_count,
    )
    shapes = pipe_shapes + connector_shapes + port_connector_shapes + valid_structure_shapes
    if not shapes:
        raise RuntimeError("Drainage pipeline network has no usable pipe segment shapes.")
    if len(shapes) == 1:
        return DrainagePipelineNetworkShapeResult(
            shape=shapes[0],
            fuse_mode="single_segment",
            connector_count=len(connector_shapes),
            structure_body_count=len(valid_structure_shapes),
            port_connector_count=len(port_connector_shapes),
            endpoint_trim_count=endpoint_trim_count,
            structure_port_terminal_count=port_contact["terminal_count"],
            structure_port_contact_status=port_contact["status"],
            notes=(
                f"shape_count=1;pipe_count={len(pipe_shapes)};"
                f"connector_count={len(connector_shapes)};port_connector_count={len(port_connector_shapes)};"
                f"endpoint_trim_count={endpoint_trim_count};structure_body_count={len(valid_structure_shapes)};"
                f"{port_contact['notes']}"
            ),
        )
    fused = _try_boolean_fuse_shapes(shapes)
    if fused is not None:
        return DrainagePipelineNetworkShapeResult(
            shape=fused,
            fuse_mode="boolean_fuse",
            connector_count=len(connector_shapes),
            structure_body_count=len(valid_structure_shapes),
            port_connector_count=len(port_connector_shapes),
            endpoint_trim_count=endpoint_trim_count,
            structure_port_terminal_count=port_contact["terminal_count"],
            structure_port_contact_status=port_contact["status"],
            notes=(
                f"shape_count={len(shapes)};pipe_count={len(pipe_shapes)};"
                f"connector_count={len(connector_shapes)};port_connector_count={len(port_connector_shapes)};"
                f"endpoint_trim_count={endpoint_trim_count};structure_body_count={len(valid_structure_shapes)};"
                f"{port_contact['notes']};fallback=no"
            ),
        )
    return DrainagePipelineNetworkShapeResult(
        shape=Part.Compound(shapes),
        fuse_mode="compound_fallback",
        connector_count=len(connector_shapes),
        structure_body_count=len(valid_structure_shapes),
        port_connector_count=len(port_connector_shapes),
        endpoint_trim_count=endpoint_trim_count,
        structure_port_terminal_count=port_contact["terminal_count"],
        structure_port_contact_status=port_contact["status"],
        notes=(
            f"shape_count={len(shapes)};pipe_count={len(pipe_shapes)};"
            f"connector_count={len(connector_shapes)};port_connector_count={len(port_connector_shapes)};"
            f"endpoint_trim_count={endpoint_trim_count};structure_body_count={len(valid_structure_shapes)};"
            f"{port_contact['notes']};fallback=yes"
        ),
    )


def _structure_port_contact_status(
    junction_rows,
    structure_body_shape_map: dict[str, list[tuple[object, str]]],
    *,
    port_connector_count: int,
    endpoint_trim_count: int,
) -> dict[str, object]:
    terminal_count = 0
    direct_contact_count = 0
    missing_structure_body_count = 0
    for junction in list(junction_rows or []):
        if str(getattr(junction, "junction_kind", "") or "") != "terminal":
            continue
        notes = str(getattr(junction, "notes", "") or "")
        structure_refs = _split_ref_text(_note_value(notes, "structure_refs"))
        if not structure_refs:
            continue
        terminal_count += 1
        point = _junction_point_vector(junction)
        if point is None:
            continue
        matched = False
        for structure_ref in structure_refs:
            for structure_shape, _object_ref in list(structure_body_shape_map.get(structure_ref, []) or []):
                bbox = getattr(structure_shape, "BoundBox", None)
                if bbox is not None and _bound_box_contains_point(bbox, point, tolerance=0.05):
                    matched = True
                    break
            if matched:
                break
        if matched:
            direct_contact_count += 1
        else:
            missing_structure_body_count += 1
    if terminal_count <= 0:
        status = "not_checked"
    elif not structure_body_shape_map:
        status = "pending_structure_body"
    elif int(port_connector_count or 0) > 0:
        status = "bridged"
    elif int(endpoint_trim_count or 0) > 0:
        status = "trimmed"
    elif direct_contact_count >= terminal_count:
        status = "direct"
    else:
        status = "gap"
    return {
        "terminal_count": terminal_count,
        "status": status,
        "notes": (
            f"structure_port_terminal_count={terminal_count};"
            f"structure_port_direct_contact_count={direct_contact_count};"
            f"structure_port_missing_body_count={missing_structure_body_count};"
            f"structure_port_contact_status={status}"
        ),
    }


def _drainage_pipeline_network_connector_shapes(junction_rows, geometry_rows) -> list[object]:
    if App is None or Part is None:
        return []
    geometry_by_segment = {
        str(getattr(row, "pipeline_segment_id", "") or ""): row
        for row in list(geometry_rows or [])
        if str(getattr(row, "pipeline_segment_id", "") or "")
    }
    shapes = []
    for junction in list(junction_rows or []):
        junction_kind = str(getattr(junction, "junction_kind", "") or "")
        notes = str(getattr(junction, "notes", "") or "")
        if junction_kind == "terminal" and not _note_value(notes, "connection_point_refs"):
            continue
        segment_refs = list(getattr(junction, "pipeline_segment_refs", []) or [])
        radius = _junction_connector_radius(segment_refs, geometry_by_segment)
        if radius <= 0.0:
            continue
        point = getattr(junction, "point", (0.0, 0.0, 0.0))
        try:
            center = App.Vector(float(point[0]), float(point[1]), float(point[2]))
        except Exception:
            continue
        try:
            shapes.append(Part.makeSphere(radius, center))
        except Exception:
            continue
    return shapes


def _trim_network_geometry_rows_to_structure_ports(geometry_rows, junction_rows, structure_body_shape_map: dict[str, list[tuple[object, str]]]):
    if App is None or not structure_body_shape_map:
        return list(geometry_rows or []), list(junction_rows or []), 0
    geometry_by_segment = {
        str(getattr(row, "pipeline_segment_id", "") or ""): row
        for row in list(geometry_rows or [])
        if str(getattr(row, "pipeline_segment_id", "") or "")
    }
    replacement_points: dict[str, list[tuple[float, float, float]]] = {}
    replacement_junction_points: dict[str, tuple[float, float, float]] = {}
    trim_count = 0
    for junction in list(junction_rows or []):
        if str(getattr(junction, "junction_kind", "") or "") != "terminal":
            continue
        notes = str(getattr(junction, "notes", "") or "")
        structure_refs = _split_ref_text(_note_value(notes, "structure_refs"))
        segment_refs = list(getattr(junction, "pipeline_segment_refs", []) or [])
        if not structure_refs or not segment_refs:
            continue
        junction_point = _junction_point_vector(junction)
        if junction_point is None:
            continue
        for segment_ref in segment_refs:
            segment_id = str(segment_ref or "")
            geometry = geometry_by_segment.get(segment_id)
            points = _geometry_row_vectors(geometry)
            endpoint_index = _matching_endpoint_index(points, junction_point)
            if endpoint_index < 0:
                continue
            pipe_direction = _pipe_direction_from_endpoint(points, endpoint_index)
            if pipe_direction is None:
                continue
            trim_point = None
            for structure_ref in structure_refs:
                for structure_shape, _object_ref in list(structure_body_shape_map.get(structure_ref, []) or []):
                    candidate = _trim_point_to_structure_exit(junction_point, pipe_direction, structure_shape)
                    if candidate is not None:
                        trim_point = candidate
                        break
                if trim_point is not None:
                    break
            if trim_point is None:
                continue
            next_points = list(replacement_points.get(segment_id) or _point_tuples(points))
            next_points[endpoint_index] = _vector_tuple(trim_point)
            replacement_points[segment_id] = next_points
            junction_id = _junction_replacement_key(junction)
            replacement_junction_points[junction_id] = _vector_tuple(trim_point)
            trim_count += 1
    if not replacement_points:
        return list(geometry_rows or []), list(junction_rows or []), 0
    trimmed_geometry_rows = [
        _replace_row(row, centerline_points=replacement_points.get(str(getattr(row, "pipeline_segment_id", "") or ""), getattr(row, "centerline_points", [])))
        for row in list(geometry_rows or [])
    ]
    trimmed_junction_rows = [
        _replace_row(row, point=replacement_junction_points.get(_junction_replacement_key(row), getattr(row, "point", (0.0, 0.0, 0.0))))
        for row in list(junction_rows or [])
    ]
    return trimmed_geometry_rows, trimmed_junction_rows, trim_count


def _trim_point_to_structure_exit(point, pipe_direction, structure_shape):
    bbox = getattr(structure_shape, "BoundBox", None)
    if bbox is None or not _bound_box_contains_point(bbox, point, tolerance=0.0):
        return None
    try:
        direction = App.Vector(float(pipe_direction.x), float(pipe_direction.y), float(pipe_direction.z))
        if direction.Length <= 1.0e-9:
            return None
        direction.normalize()
        distance = _ray_bound_box_hit_distance(point, direction, bbox)
        if distance <= 1.0e-9:
            return None
        return App.Vector(
            float(point.x) + float(direction.x) * distance,
            float(point.y) + float(direction.y) * distance,
            float(point.z) + float(direction.z) * distance,
        )
    except Exception:
        return None


def _geometry_row_vectors(geometry_row) -> list[object]:
    output = []
    for point in list(getattr(geometry_row, "centerline_points", []) or []):
        if len(point) < 3:
            continue
        try:
            output.append(App.Vector(float(point[0]), float(point[1]), float(point[2])))
        except Exception:
            continue
    return output


def _matching_endpoint_index(points: list[object], target) -> int:
    if len(points) < 2:
        return -1
    if points[0].sub(target).Length <= 1.0e-6:
        return 0
    if points[-1].sub(target).Length <= 1.0e-6:
        return len(points) - 1
    return -1


def _pipe_direction_from_endpoint(points: list[object], endpoint_index: int):
    if len(points) < 2:
        return None
    if int(endpoint_index) == 0:
        return points[1].sub(points[0])
    return points[-2].sub(points[-1])


def _point_tuples(points: list[object]) -> list[tuple[float, float, float]]:
    return [_vector_tuple(point) for point in list(points or [])]


def _vector_tuple(point) -> tuple[float, float, float]:
    return (float(point.x), float(point.y), float(point.z))


def _junction_replacement_key(junction) -> str:
    junction_row_id = str(getattr(junction, "junction_row_id", "") or "")
    if junction_row_id:
        return junction_row_id
    point = getattr(junction, "point", (0.0, 0.0, 0.0))
    try:
        return f"point:{float(point[0]):.9f}:{float(point[1]):.9f}:{float(point[2]):.9f}"
    except Exception:
        return str(id(junction))


def _replace_row(row, **changes):
    try:
        return replace(row, **changes)
    except Exception:
        try:
            data = dict(vars(row))
            data.update(changes)
            return SimpleNamespace(**data)
        except Exception:
            for key, value in changes.items():
                try:
                    setattr(row, key, value)
                except Exception:
                    pass
            return row


def _drainage_pipeline_network_port_connector_shapes(
    junction_rows,
    geometry_rows,
    structure_body_shape_map: dict[str, list[tuple[object, str]]],
    connection_point_map: dict[str, object],
) -> list[object]:
    if App is None or Part is None or not structure_body_shape_map:
        return []
    geometry_by_segment = {
        str(getattr(row, "pipeline_segment_id", "") or ""): row
        for row in list(geometry_rows or [])
        if str(getattr(row, "pipeline_segment_id", "") or "")
    }
    shapes: list[object] = []
    for junction in list(junction_rows or []):
        if str(getattr(junction, "junction_kind", "") or "") != "terminal":
            continue
        notes = str(getattr(junction, "notes", "") or "")
        structure_refs = _split_ref_text(_note_value(notes, "structure_refs"))
        connection_point_refs = _split_ref_text(_note_value(notes, "connection_point_refs"))
        if not structure_refs:
            continue
        point = _junction_point_vector(junction)
        if point is None:
            continue
        segment_refs = list(getattr(junction, "pipeline_segment_refs", []) or [])
        fallback_radius = _junction_connector_radius(segment_refs, geometry_by_segment)
        connection_point = _first_connection_point(connection_point_refs, connection_point_map)
        radius = _connection_point_connector_radius(connection_point, fallback_radius)
        terminal_direction = _terminal_pipe_outward_direction(point, segment_refs, geometry_by_segment)
        if radius <= 0.0:
            continue
        for structure_ref in structure_refs:
            for structure_shape, _object_ref in list(structure_body_shape_map.get(structure_ref, []) or []):
                connector = _port_bridge_connector_shape(
                    point,
                    structure_shape,
                    radius,
                    connection_point=connection_point,
                    terminal_direction=terminal_direction,
                )
                if connector is not None:
                    shapes.append(connector)
                    break
    return shapes


def _port_bridge_connector_shape(point, structure_shape, radius: float, *, connection_point=None, terminal_direction=None):
    if App is None or Part is None or structure_shape is None:
        return None
    bbox = getattr(structure_shape, "BoundBox", None)
    if bbox is None:
        return None
    if _bound_box_contains_point(bbox, point, tolerance=max(radius, 0.0)):
        return None
    direction = _port_connector_direction(point, bbox, connection_point=connection_point, terminal_direction=terminal_direction)
    length = float(getattr(direction, "Length", 0.0) or 0.0)
    if length <= 1.0e-9:
        return None
    try:
        return Part.makeCylinder(max(radius, 0.001), length, point, direction)
    except Exception:
        return None


def _port_connector_direction(point, bbox, *, connection_point=None, terminal_direction=None):
    center = _bound_box_center_vector(bbox)
    preferred = _connection_point_direction_vector(connection_point)
    if preferred is None:
        preferred = terminal_direction
    ray_direction = _ray_to_bound_box_direction(point, bbox, preferred)
    if ray_direction is not None:
        return ray_direction
    return center.sub(point)


def _ray_to_bound_box_direction(point, bbox, direction):
    if direction is None:
        return None
    try:
        unit = App.Vector(float(direction.x), float(direction.y), float(direction.z))
        if unit.Length <= 1.0e-9:
            return None
        unit.normalize()
        hit = _ray_bound_box_hit_distance(point, unit, bbox)
        if hit <= 1.0e-9:
            return None
        return App.Vector(unit.x * hit, unit.y * hit, unit.z * hit)
    except Exception:
        return None


def _ray_bound_box_hit_distance(origin, unit, bbox) -> float:
    t_min = -1.0e100
    t_max = 1.0e100
    for origin_value, direction_value, min_value, max_value in (
        (float(origin.x), float(unit.x), float(getattr(bbox, "XMin", 0.0)), float(getattr(bbox, "XMax", 0.0))),
        (float(origin.y), float(unit.y), float(getattr(bbox, "YMin", 0.0)), float(getattr(bbox, "YMax", 0.0))),
        (float(origin.z), float(unit.z), float(getattr(bbox, "ZMin", 0.0)), float(getattr(bbox, "ZMax", 0.0))),
    ):
        if abs(direction_value) <= 1.0e-12:
            if origin_value < min_value or origin_value > max_value:
                return 0.0
            continue
        t1 = (min_value - origin_value) / direction_value
        t2 = (max_value - origin_value) / direction_value
        t_near = min(t1, t2)
        t_far = max(t1, t2)
        t_min = max(t_min, t_near)
        t_max = min(t_max, t_far)
        if t_min > t_max:
            return 0.0
    if t_max <= 1.0e-9:
        return 0.0
    return max(t_max, t_min, 0.0)


def _connection_point_direction_vector(connection_point):
    text = (
        str(getattr(connection_point, "direction", "") or "")
        or str(getattr(connection_point, "point_role", "") or "")
    ).strip().lower()
    if not text:
        return None
    if text in {"downstream", "station_forward", "forward", "+station"}:
        return App.Vector(1.0, 0.0, 0.0)
    if text in {"upstream", "station_backward", "backward", "-station"}:
        return App.Vector(-1.0, 0.0, 0.0)
    if text in {"left", "offset_left", "+offset"}:
        return App.Vector(0.0, 1.0, 0.0)
    if text in {"right", "offset_right", "-offset"}:
        return App.Vector(0.0, -1.0, 0.0)
    if text in {"up", "vertical_up"}:
        return App.Vector(0.0, 0.0, 1.0)
    if text in {"down", "vertical_down"}:
        return App.Vector(0.0, 0.0, -1.0)
    return None


def _terminal_pipe_outward_direction(point, segment_refs: list[str], geometry_by_segment: dict[str, object]):
    for segment_ref in list(segment_refs or []):
        geometry = geometry_by_segment.get(str(segment_ref or ""))
        points = [
            App.Vector(float(raw[0]), float(raw[1]), float(raw[2]))
            for raw in list(getattr(geometry, "centerline_points", []) or [])
            if len(raw) >= 3
        ] if geometry is not None else []
        if len(points) < 2:
            continue
        if points[0].sub(point).Length <= 1.0e-6:
            return points[0].sub(points[1])
        if points[-1].sub(point).Length <= 1.0e-6:
            return points[-1].sub(points[-2])
    return None


def _first_connection_point(connection_point_refs: list[str], connection_point_map: dict[str, object]):
    for ref in list(connection_point_refs or []):
        point = connection_point_map.get(str(ref or ""))
        if point is not None:
            return point
    return None


def _connection_point_connector_radius(connection_point, fallback_radius: float) -> float:
    if connection_point is not None:
        diameter = float(getattr(connection_point, "diameter", 0.0) or 0.0)
        if diameter > 0.0:
            return diameter / 2.0
        width = float(getattr(connection_point, "width", 0.0) or 0.0)
        height = float(getattr(connection_point, "height", 0.0) or 0.0)
        if width > 0.0 or height > 0.0:
            return max(width, height) / 2.0
    return float(fallback_radius or 0.0)


def _junction_point_vector(junction):
    point = getattr(junction, "point", (0.0, 0.0, 0.0))
    try:
        return App.Vector(float(point[0]), float(point[1]), float(point[2]))
    except Exception:
        return None


def _bound_box_contains_point(bbox, point, *, tolerance: float = 0.0) -> bool:
    tol = max(float(tolerance or 0.0), 0.0)
    try:
        return (
            float(getattr(bbox, "XMin", 0.0)) - tol <= float(point.x) <= float(getattr(bbox, "XMax", 0.0)) + tol
            and float(getattr(bbox, "YMin", 0.0)) - tol <= float(point.y) <= float(getattr(bbox, "YMax", 0.0)) + tol
            and float(getattr(bbox, "ZMin", 0.0)) - tol <= float(point.z) <= float(getattr(bbox, "ZMax", 0.0)) + tol
        )
    except Exception:
        return False


def _bound_box_center_vector(bbox):
    return App.Vector(
        (float(getattr(bbox, "XMin", 0.0)) + float(getattr(bbox, "XMax", 0.0))) / 2.0,
        (float(getattr(bbox, "YMin", 0.0)) + float(getattr(bbox, "YMax", 0.0))) / 2.0,
        (float(getattr(bbox, "ZMin", 0.0)) + float(getattr(bbox, "ZMax", 0.0))) / 2.0,
    )


def _junction_connector_radius(segment_refs: list[str], geometry_by_segment: dict[str, object]) -> float:
    diameters = []
    for segment_ref in list(segment_refs or []):
        geometry = geometry_by_segment.get(str(segment_ref or ""))
        if geometry is None:
            continue
        diameter = float(getattr(geometry, "diameter", 0.0) or 0.0)
        if diameter > 0.0:
            diameters.append(diameter)
    if not diameters:
        return 0.0
    return max(diameters) / 2.0


def _network_connector_count(junction_rows) -> int:
    count = 0
    for row in list(junction_rows or []):
        kind = str(getattr(row, "junction_kind", "") or "")
        if kind == "junction":
            count += 1
            continue
        if kind == "terminal" and _note_value(str(getattr(row, "notes", "") or ""), "connection_point_refs"):
            count += 1
    return count


def _built_structure_body_shapes_for_refs(document, structure_refs: list[str]) -> tuple[list[object], list[str]]:
    return _structure_body_shape_map_values(_built_structure_body_shape_map_for_refs(document, structure_refs))


def _structure_connection_point_map(document) -> dict[str, object]:
    structure_model = to_structure_model(find_v1_structure_model(document))
    return {
        str(getattr(row, "connection_point_id", "") or ""): row
        for row in list(getattr(structure_model, "connection_point_rows", []) or [])
        if str(getattr(row, "connection_point_id", "") or "")
    } if structure_model is not None else {}


def _built_structure_body_shape_map_for_refs(document, structure_refs: list[str]) -> dict[str, list[tuple[object, str]]]:
    if document is None:
        return {}
    requested_refs = {str(ref or "").strip() for ref in list(structure_refs or []) if str(ref or "").strip()}
    if not requested_refs:
        return {}
    shape_map: dict[str, list[tuple[object, str]]] = {ref: [] for ref in requested_refs}
    for obj in list(getattr(document, "Objects", []) or []):
        if str(getattr(obj, "V1ObjectType", "") or "") != "V1WatertightSolidOutput":
            continue
        if "structure_body" not in {str(value or "").strip() for value in list(getattr(obj, "TargetFamilies", []) or [])}:
            continue
        obj_structure_refs = _split_object_ref_values(getattr(obj, "StructureRefs", []))
        if not requested_refs.intersection(obj_structure_refs):
            continue
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        if _shape_count(shape, "Solids") <= 0 and _shape_count(shape, "Faces") <= 0:
            continue
        object_ref = str(getattr(obj, "Name", "") or "")
        for ref in requested_refs.intersection(obj_structure_refs):
            shape_map.setdefault(ref, []).append((shape, object_ref))
    return {ref: values for ref, values in shape_map.items() if values}


def _structure_body_shape_map_values(shape_map: dict[str, list[tuple[object, str]]]) -> tuple[list[object], list[str]]:
    shapes: list[object] = []
    object_refs: list[str] = []
    seen_shapes: set[int] = set()
    for values in list((shape_map or {}).values()):
        for shape, object_ref in list(values or []):
            shape_key = id(shape)
            if shape_key not in seen_shapes:
                shapes.append(shape)
                seen_shapes.add(shape_key)
            if object_ref:
                object_refs.append(object_ref)
    return shapes, _unique_refs(object_refs)


def _split_object_ref_values(values) -> set[str]:
    refs: set[str] = set()
    for value in list(values or []):
        for part in str(value or "").replace(";", ",").split(","):
            text = part.strip()
            if text:
                refs.add(text)
    return refs


def _network_note_refs(rows, key: str) -> list[str]:
    values: list[str] = []
    for row in list(rows or []):
        text = _note_value(str(getattr(row, "notes", "") or ""), key)
        if not text:
            continue
        values.extend(_split_ref_text(text))
    return _unique_refs(values)


def _split_ref_text(text: str) -> list[str]:
    return [part.strip() for part in str(text or "").replace(";", ",").split(",") if part.strip()]


def _note_value(notes: str, key: str) -> str:
    prefix = str(key or "") + "="
    for token in str(notes or "").split(";"):
        if token.startswith(prefix):
            return token[len(prefix) :]
    return ""


def _try_boolean_fuse_shapes(shapes: list[object]):
    if len(shapes) < 2:
        return shapes[0] if shapes else None
    first = shapes[0]
    rest = shapes[1:]
    for method_name in ("multiFuse", "fuse"):
        try:
            method = getattr(first, method_name, None)
            if method is None:
                continue
            fused = method(rest) if method_name == "multiFuse" else first
            if method_name == "fuse":
                for shape in rest:
                    fused = fused.fuse(shape)
            if _shape_count(fused, "Solids") <= 0 and _shape_count(fused, "Faces") <= 0:
                continue
            try:
                fused = fused.removeSplitter()
            except Exception:
                pass
            return fused
        except Exception:
            continue
    return None


def _drainage_pipeline_watertight_output(
    target_row,
    *,
    drainage_output,
    geometry_row,
    solid_row,
    shape,
    generated_object_ref: str,
) -> WatertightSolidOutput:
    target_id = str(getattr(target_row, "target_id", "") or "")
    output_object_id = f"watertight-solid:{_safe_object_id(target_id)}"
    face_count = _shape_count(shape, "Faces")
    edge_count = _shape_count(shape, "Edges")
    volume = max(float(getattr(solid_row, "volume", 0.0) or 0.0), 0.0)
    source_refs = _unique_refs(
        [
            target_id,
            str(getattr(geometry_row, "geometry_row_id", "") or ""),
            str(getattr(solid_row, "solid_row_id", "") or ""),
            str(getattr(solid_row, "pipeline_segment_id", "") or ""),
            str(getattr(solid_row, "flow_route_ref", "") or ""),
            *list(getattr(target_row, "source_refs", []) or []),
            *list(getattr(drainage_output, "source_refs", []) or []),
            *list(getattr(drainage_output, "result_refs", []) or []),
        ]
    )
    solid = WatertightSolidOutputRow(
        output_object_id=output_object_id,
        target_id=target_id,
        target_family=str(getattr(target_row, "target_family", "") or ""),
        scope_kind=str(getattr(target_row, "scope_kind", "") or ""),
        station_start=float(getattr(target_row, "station_start", getattr(solid_row, "station_start", 0.0)) or 0.0),
        station_end=float(getattr(target_row, "station_end", getattr(solid_row, "station_end", 0.0)) or 0.0),
        source_refs=source_refs,
        generated_object_ref=str(generated_object_ref or ""),
        validation_status="ok",
        is_watertight=bool(getattr(solid_row, "is_capped", False)),
        is_valid_solid=bool(getattr(solid_row, "is_capped", False)),
        volume=volume,
        face_count=face_count,
        edge_count=edge_count,
        profile_count=len(list(getattr(geometry_row, "centerline_points", []) or [])),
        subassembly_ref=str(getattr(target_row, "subassembly_ref", "") or ""),
        drainage_ref=str(getattr(target_row, "drainage_ref", "") or ""),
        flow_route_ref=str(getattr(target_row, "flow_route_ref", "") or ""),
        material_ref=str(getattr(target_row, "material_ref", "") or ""),
        path_source=str(getattr(solid_row, "coordinate_mode", "") or ""),
        notes=(
            f"Drainage pipeline solid candidate from {str(getattr(solid_row, 'solid_row_id', '') or '')}; "
            f"coordinate_mode={str(getattr(solid_row, 'coordinate_mode', '') or '')}; "
            f"cap_count={int(getattr(solid_row, 'cap_count', 0) or 0)}."
        ),
    )
    segment = WatertightSolidSegmentRow(
        segment_id=f"{output_object_id}:segment:1",
        parent_output_object_id=output_object_id,
        station_start=float(getattr(solid_row, "station_start", getattr(target_row, "station_start", 0.0)) or 0.0),
        station_end=float(getattr(solid_row, "station_end", getattr(target_row, "station_end", 0.0)) or 0.0),
        notes=f"pipeline_segment_id={str(getattr(solid_row, 'pipeline_segment_id', '') or '')}",
    )
    return WatertightSolidOutput(
        schema_version=1,
        project_id=str(getattr(drainage_output, "project_id", "") or "corridorroad-v1"),
        watertight_solid_output_id="watertight-solids:drainage-pipeline",
        corridor_id="corridor:main",
        label="Watertight Solids",
        selection_scope={"scope_kind": str(getattr(target_row, "scope_kind", "") or ""), "target_id": target_id},
        source_refs=source_refs,
        result_refs=_unique_refs(
            [
                str(getattr(drainage_output, "drainage_output_id", "") or ""),
                str(getattr(geometry_row, "geometry_row_id", "") or ""),
                str(getattr(solid_row, "solid_row_id", "") or ""),
            ]
        ),
        solid_rows=[solid],
        segment_rows=[segment],
    )


def _drainage_pipeline_network_watertight_output(
    target_row,
    *,
    drainage_output,
    network_row,
    geometry_rows,
    solid_rows,
    junction_rows,
    shape,
    generated_object_ref: str,
    fuse_mode: str = "compound_fallback",
    connector_count: int = 0,
    structure_body_count: int = 0,
    port_connector_count: int = 0,
    endpoint_trim_count: int = 0,
    structure_port_terminal_count: int = 0,
    structure_port_contact_status: str = "",
    structure_body_object_refs: list[str] | None = None,
    fuse_notes: str = "",
) -> WatertightSolidOutput:
    target_id = str(getattr(target_row, "target_id", "") or "")
    output_object_id = f"watertight-solid:{_safe_object_id(target_id)}"
    face_count = _shape_count(shape, "Faces")
    edge_count = _shape_count(shape, "Edges")
    volume = max(float(getattr(shape, "Volume", 0.0) or 0.0), float(getattr(network_row, "volume", 0.0) or 0.0), 0.0)
    segment_refs = _unique_refs([str(getattr(row, "pipeline_segment_id", "") or "") for row in list(solid_rows or [])])
    flow_route_refs = _unique_refs([str(getattr(row, "flow_route_ref", "") or "") for row in list(solid_rows or [])])
    connection_point_refs = _network_note_refs(junction_rows, "connection_point_refs")
    structure_refs = _network_note_refs(junction_rows, "structure_refs")
    active_structure_body_object_refs = _unique_refs(structure_body_object_refs or [])
    source_refs = _unique_refs(
        [
            target_id,
            str(getattr(network_row, "network_row_id", "") or ""),
            str(getattr(network_row, "network_id", "") or ""),
            *list(getattr(network_row, "solid_row_refs", []) or []),
            *segment_refs,
            *flow_route_refs,
            *connection_point_refs,
            *structure_refs,
            *active_structure_body_object_refs,
            *list(getattr(target_row, "source_refs", []) or []),
            *list(getattr(drainage_output, "source_refs", []) or []),
            *list(getattr(drainage_output, "result_refs", []) or []),
        ]
    )
    all_capped = bool(solid_rows) and all(bool(getattr(row, "is_capped", False)) for row in list(solid_rows or []))
    active_fuse_mode = str(fuse_mode or "compound_fallback")
    solid = WatertightSolidOutputRow(
        output_object_id=output_object_id,
        target_id=target_id,
        target_family=str(getattr(target_row, "target_family", "") or ""),
        scope_kind=str(getattr(target_row, "scope_kind", "") or ""),
        station_start=float(getattr(target_row, "station_start", 0.0) or 0.0),
        station_end=float(getattr(target_row, "station_end", 0.0) or 0.0),
        source_refs=source_refs,
        generated_object_ref=str(generated_object_ref or ""),
        validation_status="ok",
        is_watertight=all_capped,
        is_valid_solid=all_capped,
        volume=volume,
        face_count=face_count,
        edge_count=edge_count,
        profile_count=sum(len(list(getattr(row, "centerline_points", []) or [])) for row in list(geometry_rows or [])),
        subassembly_ref=str(getattr(target_row, "subassembly_ref", "") or ""),
        structure_ref=",".join(structure_refs),
        drainage_ref=str(getattr(target_row, "drainage_ref", "") or ""),
        flow_route_ref=",".join(flow_route_refs),
        material_ref=str(getattr(target_row, "material_ref", "") or ""),
        path_source=str(getattr(network_row, "coordinate_mode", "") or ""),
        notes=(
            f"Drainage pipeline network solid candidate from {str(getattr(network_row, 'network_id', '') or '')}; "
            f"segments={len(segment_refs)}; junctions={int(getattr(network_row, 'junction_count', 0) or 0)}; "
            f"connector_count={int(connector_count or 0)}; "
            f"port_connector_count={int(port_connector_count or 0)}; "
            f"port_connector_status={'added' if int(port_connector_count or 0) > 0 else 'not_needed'}; "
            f"endpoint_trim_count={int(endpoint_trim_count or 0)}; "
            f"endpoint_trim_status={'applied' if int(endpoint_trim_count or 0) > 0 else 'not_needed'}; "
            f"structure_port_terminal_count={int(structure_port_terminal_count or 0)}; "
            f"structure_port_contact_status={str(structure_port_contact_status or 'not_checked')}; "
            f"structure_body_count={int(structure_body_count or 0)}; "
            f"structure_fuse_status={'included' if int(structure_body_count or 0) > 0 else 'pending'}; "
            f"structure_body_object_refs={','.join(active_structure_body_object_refs)}; "
            f"structure_refs={','.join(structure_refs)}; "
            f"connection_point_refs={','.join(connection_point_refs)}; "
            f"fuse_mode={active_fuse_mode}; {str(fuse_notes or '').strip()}"
        ),
    )
    segment_rows = []
    for index, solid_row in enumerate(list(solid_rows or []), start=1):
        segment_rows.append(
            WatertightSolidSegmentRow(
                segment_id=f"{output_object_id}:segment:{index}",
                parent_output_object_id=output_object_id,
                station_start=float(getattr(solid_row, "station_start", getattr(target_row, "station_start", 0.0)) or 0.0),
                station_end=float(getattr(solid_row, "station_end", getattr(target_row, "station_end", 0.0)) or 0.0),
                notes=f"pipeline_segment_id={str(getattr(solid_row, 'pipeline_segment_id', '') or '')}",
            )
        )
    return WatertightSolidOutput(
        schema_version=1,
        project_id=str(getattr(drainage_output, "project_id", "") or "corridorroad-v1"),
        watertight_solid_output_id="watertight-solids:drainage-pipeline-network",
        corridor_id="corridor:main",
        label="Watertight Solids",
        selection_scope={"scope_kind": str(getattr(target_row, "scope_kind", "") or ""), "target_id": target_id},
        source_refs=source_refs,
        result_refs=_unique_refs(
            [
                str(getattr(drainage_output, "drainage_output_id", "") or ""),
                str(getattr(network_row, "network_row_id", "") or ""),
                *list(getattr(network_row, "solid_row_refs", []) or []),
            ]
        ),
        solid_rows=[solid],
        segment_rows=segment_rows,
    )


def _external_structure_body_watertight_output(
    target_row,
    *,
    structure_model,
    structure_row,
    external_obj,
    shape,
    generated_object_ref: str,
) -> WatertightSolidOutput:
    target_id = str(getattr(target_row, "target_id", "") or "")
    output_object_id = f"watertight-solid:{_safe_object_id(target_id)}"
    structure_ref = str(getattr(structure_row, "structure_id", "") or getattr(target_row, "structure_ref", "") or "")
    geometry_ref = str(getattr(structure_row, "geometry_ref", "") or "")
    source_refs = _unique_refs(
        [
            target_id,
            str(getattr(structure_model, "structure_model_id", "") or ""),
            structure_ref,
            geometry_ref,
            str(getattr(external_obj, "Name", "") or ""),
            *list(getattr(target_row, "source_refs", []) or []),
        ]
    )
    volume = float(getattr(shape, "Volume", 0.0) or 0.0)
    station_start = float(getattr(target_row, "station_start", getattr(getattr(structure_row, "placement", None), "station_start", 0.0)) or 0.0)
    station_end = float(getattr(target_row, "station_end", getattr(getattr(structure_row, "placement", None), "station_end", station_start)) or station_start)
    solid = WatertightSolidOutputRow(
        output_object_id=output_object_id,
        target_id=target_id,
        target_family=str(getattr(target_row, "target_family", "") or "structure_body"),
        scope_kind=str(getattr(target_row, "scope_kind", "") or "structure"),
        station_start=station_start,
        station_end=station_end,
        source_refs=source_refs,
        generated_object_ref=str(generated_object_ref or ""),
        validation_status="ok",
        is_watertight=_shape_count(shape, "Solids") > 0,
        is_valid_solid=_shape_count(shape, "Solids") > 0,
        volume=volume,
        face_count=_shape_count(shape, "Faces"),
        edge_count=_shape_count(shape, "Edges"),
        profile_count=1,
        subassembly_ref=str(getattr(target_row, "subassembly_ref", "") or ""),
        structure_ref=structure_ref,
        path_source="external_ref",
        notes=(
            "External Structure body shape reused; "
            f"geometry_ref={geometry_ref}; "
            f"external_object={str(getattr(external_obj, 'Name', '') or '')}."
        ),
    )
    segment = WatertightSolidSegmentRow(
        segment_id=f"{output_object_id}:segment:1",
        parent_output_object_id=output_object_id,
        station_start=station_start,
        station_end=station_end,
        notes=f"structure_id={structure_ref};geometry_ref={geometry_ref}",
    )
    return WatertightSolidOutput(
        schema_version=1,
        project_id=str(getattr(structure_model, "project_id", "") or "corridorroad-v1"),
        watertight_solid_output_id="watertight-solids:structure-body",
        corridor_id="corridor:main",
        label="Watertight Solids",
        selection_scope={"scope_kind": str(getattr(target_row, "scope_kind", "") or ""), "target_id": target_id},
        source_refs=source_refs,
        result_refs=_unique_refs([str(getattr(external_obj, "Name", "") or ""), geometry_ref]),
        solid_rows=[solid],
        segment_rows=[segment],
    )


def _shape_count(shape, attr_name: str) -> int:
    try:
        return len(list(getattr(shape, attr_name, []) or []))
    except Exception:
        return 0


def _shape_edge_closure_diagnostics(shape) -> dict[str, int | str]:
    edge_keys: dict[tuple[tuple[float, float, float], tuple[float, float, float]], int] = {}
    try:
        edges = list(getattr(shape, "Edges", []) or [])
    except Exception:
        edges = []
    for edge in edges:
        key = _edge_endpoint_key(edge)
        if key is None:
            continue
        edge_keys[key] = edge_keys.get(key, 0) + 1
    open_edge_count = sum(1 for count in edge_keys.values() if count == 1)
    shared_edge_count = sum(1 for count in edge_keys.values() if count > 1)
    face_count = _shape_count(shape, "Faces")
    return {
        "closure_status": "closed" if face_count > 0 and open_edge_count == 0 else "open",
        "face_count": face_count,
        "edge_count": len(edge_keys),
        "open_edge_count": open_edge_count,
        "shared_edge_count": shared_edge_count,
    }


def _edge_endpoint_key(edge):
    try:
        vertices = list(getattr(edge, "Vertexes", []) or [])
    except Exception:
        vertices = []
    if len(vertices) < 2:
        return None
    start = _rounded_vertex_xyz(vertices[0])
    end = _rounded_vertex_xyz(vertices[-1])
    if start is None or end is None:
        return None
    return tuple(sorted((start, end)))


def _rounded_vertex_xyz(vertex) -> tuple[float, float, float] | None:
    try:
        point = vertex.Point
        return (round(float(point.x), 6), round(float(point.y), 6), round(float(point.z), 6))
    except Exception:
        return None


def _side_from_ref(value: str) -> str:
    text = str(value or "").strip().lower()
    if "right" in text:
        return "right"
    if "left" in text:
        return "left"
    return ""


def _target_diagnostic_text(row: object, target_model: object, state: WatertightSolidTargetPanelState | None = None) -> str:
    diagnostic_refs = set(str(value) for value in list(getattr(row, "diagnostic_refs", []) or []) if str(value))
    diagnostics = [
        diagnostic for diagnostic in list(getattr(target_model, "target_diagnostic_rows", []) or [])
        if str(getattr(diagnostic, "diagnostic_id", "") or "") in diagnostic_refs
    ]
    messages: list[str] = []
    if diagnostics:
        messages.extend(str(getattr(diagnostic, "message", "") or "") for diagnostic in diagnostics)
    if state is not None and str(getattr(state, "validation_message", "") or ""):
        messages.append(str(state.validation_message))
    if messages:
        return "; ".join(value for value in messages if value)
    return str(getattr(row, "notes", "") or "")


def _drainage_watertight_handoff_lines(document, target_model=None) -> list[str]:
    summary = drainage_watertight_handoff_summary(document, target_model=target_model)
    return [
        "Drainage Solid QA:",
        (
            f"status={summary.readiness_status}; source={summary.source_status}; "
            f"flow_routes={summary.flow_route_count}; capture_only={summary.capture_only_route_count}; "
            f"pipe_candidates={summary.pipe_candidate_count}; unresolved_ports={summary.unresolved_port_route_count}; "
            f"missing_elements={summary.missing_element_route_count}"
        ),
        (
            f"targets: lined_ditch={summary.lined_ditch_target_count}; pipe_segments={summary.pipe_segment_target_count}; "
            f"pipeline_networks={summary.pipeline_network_target_count}; structure_bodies={summary.structure_body_target_count}; "
            f"built_drainage_outputs={summary.built_drainage_output_count}; network_fuse={summary.network_fuse_status}"
        ),
    ]


def _intersection_watertight_handoff_lines(document, target_model=None) -> list[str]:
    summary = intersection_watertight_handoff_summary(document, target_model=target_model)
    if summary.source_status == "missing" and summary.target_count <= 0:
        return []
    return [
        "Intersection Solid QA:",
        (
            f"status={summary.readiness_status}; source={summary.source_status}; "
            f"targets={summary.target_count}; intersection={summary.intersection_id or '-'}; "
            f"triangulation={summary.triangulation_mode or '-'}; boundary={summary.surface_boundary_strategy or '-'}; "
            f"edge_blend_faces={summary.edge_blend_face_count}; curb_return_arcs={summary.curb_return_arc_count}; "
            f"arc_segments={summary.curb_return_arc_segment_count}; min_triangle_quality={summary.min_triangle_quality:.3f}; "
            f"skinny_triangles={summary.skinny_triangle_count}"
        ),
        (
            f"clipping_boundary={summary.exclusion_boundary_strategy or '-'}; "
            f"aligned={'practical' if summary.exclusion_practical_aligned else 'check'}; "
            f"patch_boundary={summary.patch_boundary_status or '-'}; "
            f"zone_targets: pavement={summary.pavement_target_count}; subgrade={summary.subgrade_target_count}; "
            f"slope={summary.slope_target_count}; curb_return={summary.curb_return_target_count}"
        ),
    ]


def intersection_watertight_handoff_summary(document=None, *, target_model=None) -> IntersectionWatertightHandoffSummary:
    """Return Intersection readiness focused on Watertight Solid simulation handoff."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return IntersectionWatertightHandoffSummary(source_status="missing")
    active_target_model = target_model
    target_rows = list(getattr(active_target_model, "target_rows", []) or []) if active_target_model is not None else []
    target_count = sum(1 for row in target_rows if _is_intersection_watertight_target(row))
    preview = _intersection_surface_preview_object(doc)
    if preview is None:
        return IntersectionWatertightHandoffSummary(source_status="missing", target_count=target_count)
    exclusion_strategy, practical_aligned = _intersection_exclusion_handoff_status(doc)
    return IntersectionWatertightHandoffSummary(
        source_status="ready",
        intersection_id=str(getattr(preview, "IntersectionId", "") or ""),
        target_count=target_count,
        pavement_target_count=_solid_target_family_count(target_rows, "intersection_pavement_body"),
        subgrade_target_count=_solid_target_family_count(target_rows, "intersection_subgrade_body"),
        slope_target_count=_solid_target_family_count(target_rows, "intersection_slope_body"),
        curb_return_target_count=_solid_target_family_count(target_rows, "intersection_curb_return_body"),
        triangulation_mode=str(getattr(preview, "PatchTriangulationMode", "") or ""),
        surface_boundary_strategy=str(getattr(preview, "PatchBoundaryStrategy", "") or getattr(preview, "PatchTriangulationMode", "") or ""),
        exclusion_boundary_strategy=exclusion_strategy,
        exclusion_practical_aligned=practical_aligned,
        edge_blend_face_count=int(getattr(preview, "PatchEdgeBlendFaceCount", 0) or 0),
        curb_return_arc_count=int(getattr(preview, "PatchCurbReturnArcCount", 0) or 0),
        curb_return_arc_segment_count=int(getattr(preview, "PatchCurbReturnArcSegmentCount", 0) or 0),
        min_triangle_quality=float(getattr(preview, "PatchMinTriangleQuality", 0.0) or 0.0),
        skinny_triangle_count=int(getattr(preview, "PatchSkinnyTriangleCount", 0) or 0),
        patch_boundary_status=str(getattr(preview, "IntersectionPatchBoundaryClosed", "") or ""),
        review_summary=str(getattr(preview, "IntersectionReviewSummary", "") or ""),
        patch_quality_summary=str(getattr(preview, "IntersectionPatchQualitySummary", "") or ""),
    )


def _annotate_intersection_watertight_handoff_targets(target_model, document):
    rows = list(getattr(target_model, "target_rows", []) or [])
    if not rows:
        return target_model
    summary = intersection_watertight_handoff_summary(document, target_model=target_model)
    if summary.source_status != "ready":
        return target_model
    annotated_rows = []
    changed = False
    source_refs = _intersection_handoff_source_refs(summary)
    notes = _intersection_handoff_target_notes(summary)
    for row in rows:
        if not _is_intersection_patch_target(row):
            annotated_rows.append(row)
            continue
        annotated_rows.append(
            replace(
                row,
                source_refs=_unique_refs(list(getattr(row, "source_refs", []) or []) + source_refs),
                notes=_join_notes(str(getattr(row, "notes", "") or ""), notes),
            )
        )
        changed = True
    if not changed:
        return target_model
    try:
        return replace(target_model, target_rows=annotated_rows)
    except Exception:
        try:
            target_model.target_rows = annotated_rows
        except Exception:
            pass
        return target_model


def _intersection_handoff_source_refs(summary: IntersectionWatertightHandoffSummary) -> list[str]:
    return _unique_refs(
        [
            "V1CorridorIntersectionSurfacePreview",
            "V1CorridorDesignSurfacePreview",
            "V1CorridorDaylightSurfacePreview",
            summary.intersection_id,
            f"intersection-boundary:{summary.surface_boundary_strategy}" if summary.surface_boundary_strategy else "",
        ]
    )


def _intersection_handoff_target_notes(summary: IntersectionWatertightHandoffSummary) -> str:
    return (
        "IntersectionHandoff: "
        f"status={summary.readiness_status}; "
        f"triangulation={summary.triangulation_mode or '-'}; "
        f"boundary={summary.surface_boundary_strategy or '-'}; "
        f"clipping_boundary={summary.exclusion_boundary_strategy or '-'}; "
        f"aligned={'practical' if summary.exclusion_practical_aligned else 'check'}; "
        f"edge_blend_faces={summary.edge_blend_face_count}; "
        f"curb_return_arcs={summary.curb_return_arc_count}; "
        f"arc_segments={summary.curb_return_arc_segment_count}."
    )


def _intersection_surface_preview_object(document):
    if document is None:
        return None
    try:
        return document.getObject("V1CorridorIntersectionSurfacePreview")
    except Exception:
        return None


def _intersection_exclusion_handoff_status(document) -> tuple[str, bool]:
    strategies: list[str] = []
    aligned_values: list[bool] = []
    for object_name in ("V1CorridorDesignSurfacePreview", "V1CorridorDaylightSurfacePreview"):
        try:
            obj = document.getObject(object_name)
        except Exception:
            obj = None
        if obj is None:
            continue
        strategy = str(getattr(obj, "IntersectionExclusionBoundaryStrategy", "") or "")
        if strategy:
            strategies.append(strategy)
        raw_aligned = str(getattr(obj, "IntersectionExclusionPracticalBoundaryAligned", "") or "").strip().lower()
        if raw_aligned:
            aligned_values.append(raw_aligned in {"1", "true", "yes", "practical"})
    return ",".join(_unique_refs(strategies)), bool(aligned_values) and all(aligned_values)


def _join_notes(existing: str, addition: str) -> str:
    existing_text = str(existing or "").strip()
    addition_text = str(addition or "").strip()
    if not existing_text:
        return addition_text
    if not addition_text or addition_text in existing_text:
        return existing_text
    return f"{existing_text} {addition_text}"


def drainage_watertight_handoff_summary(document=None, *, target_model=None) -> DrainageWatertightHandoffSummary:
    """Return Drainage readiness focused on Watertight Solid simulation handoff."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return DrainageWatertightHandoffSummary(source_status="missing")
    drainage_obj = find_v1_drainage_model(doc)
    structure_obj = find_v1_structure_model(doc)
    drainage_model = to_drainage_model(drainage_obj)
    structure_model = to_structure_model(structure_obj)
    source_status = "ready" if drainage_model is not None and structure_model is not None else "missing"
    candidates = build_drainage_pipeline_segment_candidates(drainage_model, structure_model)
    statuses = [str(getattr(row, "status", "") or "") for row in candidates]
    active_target_model = target_model or discover_watertight_solid_targets(doc)
    target_rows = list(getattr(active_target_model, "target_rows", []) or [])
    network_targets = [row for row in target_rows if str(getattr(row, "target_family", "") or "") == "drainage_pipeline_network_body"]
    network_fuse_status = _drainage_network_fuse_status(doc, network_targets)
    return DrainageWatertightHandoffSummary(
        source_status=source_status,
        flow_route_count=len(list(getattr(drainage_model, "flow_route_rows", []) or [])) if drainage_model is not None else 0,
        capture_only_route_count=statuses.count("capture_only"),
        pipe_candidate_count=statuses.count("ready"),
        unresolved_port_route_count=sum(1 for value in statuses if value in {"missing_connection_point_ref", "missing_connection_point"}),
        missing_element_route_count=statuses.count("missing_element"),
        lined_ditch_target_count=_solid_target_family_count(target_rows, "lined_ditch_body"),
        pipe_segment_target_count=_solid_target_family_count(target_rows, "drainage_pipeline_body"),
        pipeline_network_target_count=len(network_targets),
        structure_body_target_count=_solid_target_family_count(target_rows, "structure_body"),
        built_drainage_output_count=_built_drainage_output_count(doc),
        network_fuse_status=network_fuse_status,
    )


def _solid_target_family_count(rows: list[object], family: str) -> int:
    return sum(1 for row in rows if str(getattr(row, "target_family", "") or "") == family)


def _built_drainage_output_count(document) -> int:
    count = 0
    for obj in _watertight_output_objects(document):
        families = {str(value or "") for value in list(getattr(obj, "TargetFamilies", []) or [])}
        if families.intersection({"lined_ditch_body", "drainage_pipeline_body", "drainage_pipeline_network_body"}):
            count += 1
    return count


def _drainage_network_fuse_status(document, network_targets: list[object]) -> str:
    network_outputs = [
        obj for obj in _watertight_output_objects(document)
        if "drainage_pipeline_network_body" in {str(value or "") for value in list(getattr(obj, "TargetFamilies", []) or [])}
    ]
    if network_outputs:
        diagnostic_notes = []
        for obj in network_outputs:
            diagnostic_notes.extend(str(value or "") for value in list(getattr(obj, "DiagnosticNotes", []) or []) if str(value or ""))
        if any("compound_fallback" in value for value in diagnostic_notes):
            return "compound_fallback"
        return "built"
    if network_targets:
        return "compound_first_slice"
    return "not_available"


def _simulation_ready_qa_lines(document) -> list[str]:
    qa = _build_simulation_qa_output(document)
    families = [str(getattr(row, "family", "") or "") for row in list(getattr(qa, "family_rows", []) or []) if str(getattr(row, "family", "") or "")]
    return [
        "Simulation QA:",
        (
            f"outputs={int(getattr(qa, 'output_count', 0) or 0)}; families={','.join(families) or '-'}; "
            f"road_body={str(getattr(qa, 'road_body_status', '') or 'missing')}; "
            f"terrain={str(getattr(qa, 'terrain_status', '') or 'missing')}; "
            f"drainage={str(getattr(qa, 'drainage_status', '') or 'missing')}; "
            f"structure={str(getattr(qa, 'structure_status', '') or 'missing')}"
        ),
        (
            f"solid_validity={str(getattr(qa, 'solid_validity_status', '') or 'check')}; "
            f"invalid_outputs={int(getattr(qa, 'invalid_output_count', 0) or 0)}; "
            f"zero_volume_outputs={int(getattr(qa, 'zero_volume_output_count', 0) or 0)}; "
            f"geometry_contact={str(getattr(qa, 'geometry_contact_status', '') or 'not_checked')}; "
            f"contact_issues={int(getattr(qa, 'contact_issue_count', 0) or 0)}; "
            f"terrain_domain={str(getattr(qa, 'terrain_domain_status', '') or 'not_checked')}; "
            f"terrain_issues={int(getattr(qa, 'terrain_issue_count', 0) or 0)}; "
            f"port_connection={str(getattr(qa, 'port_connection_status', '') or 'not_checked')}; "
            f"port_issues={int(getattr(qa, 'port_issue_count', 0) or 0)}; "
            f"total_volume={_volume_text(float(getattr(qa, 'total_volume', 0.0) or 0.0))}; "
            f"simulation_ready={'yes' if bool(getattr(qa, 'simulation_ready', False)) else 'no'}; "
            f"missing={','.join(list(getattr(qa, 'missing_contexts', []) or [])) or '-'}"
        ),
    ]


def _build_simulation_qa_output(document):
    return WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id=_document_project_id(document),
            output_refs=[str(getattr(obj, "Name", "") or "") for obj in _watertight_output_objects(document)],
            solid_inputs=_simulation_qa_solid_inputs(document),
            terrain_ready=_terrain_context_ready(document),
            terrain_bound_box=_terrain_context_bound_box_tuple(document),
        )
    )


def _create_or_update_intersection_trim_preview_object(document, *, tolerance: float = 0.05):
    if document is None or Part is None or App is None:
        return None
    result = _intersection_trim_boundary_result_for_preview(document, tolerance=tolerance)
    candidates = _intersection_trim_ready_preview_candidates(result)
    candidate_count = len(list(getattr(result, "boundary_pair_rows", []) or [])) if result is not None else 0
    ready_count = int(getattr(result, "ready_pair_count", 0) or len(candidates)) if result is not None else len(candidates)
    blocked_count = int(getattr(result, "blocked_pair_count", 0) or 0) if result is not None else 0
    application_status = str(getattr(result, "application_status", "") or ("ready" if candidates else "empty"))
    obj = document.getObject("V1WatertightIntersectionTrimPreview")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1WatertightIntersectionTrimPreview")
    _set_object_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "V1WatertightIntersectionTrimPreview")
    _set_object_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1_watertight_trim_preview")
    _set_object_property(obj, "App::PropertyString", "PreviewStatus", "Preview", application_status)
    _set_object_property(obj, "App::PropertyString", "ApplicationStatus", "Preview", application_status)
    _set_object_property(obj, "App::PropertyInteger", "CandidateEdgePairCount", "Preview", candidate_count)
    _set_object_property(obj, "App::PropertyInteger", "ReadyEdgePairCount", "Preview", ready_count)
    _set_object_property(obj, "App::PropertyInteger", "BlockedEdgePairCount", "Preview", blocked_count)
    _set_object_property(obj, "App::PropertyFloat", "Tolerance", "Preview", float(tolerance or 0.0))
    _set_object_property(
        obj,
        "App::PropertyString",
        "PreviewDiagnostic",
        "Preview",
        (
            f"Intersection patch trim edge pairs: ready={ready_count}, blocked={blocked_count}, total={candidate_count}."
            if candidates
            else "No ready intersection patch trim edge pairs were found."
        ),
    )
    _set_object_property(
        obj,
        "App::PropertyStringList",
        "SourceRefs",
        "Traceability",
        list(getattr(result, "source_refs", []) or [])
        if result is not None
        else _unique_refs([ref for candidate in candidates for ref in (candidate["patch_ref"], candidate["road_ref"])]),
    )
    shapes = []
    for candidate in candidates:
        patch_segment = candidate["patch_segment"]
        road_segment = candidate["road_segment"]
        shapes.append(_line_shape_from_segment(patch_segment))
        shapes.append(_line_shape_from_segment(road_segment))
        shapes.append(_line_shape_from_points(_segment_midpoint(patch_segment), _segment_midpoint(road_segment)))
    try:
        obj.Shape = Part.makeCompound([shape for shape in shapes if shape is not None]) if shapes else Part.Shape()
    except Exception:
        obj.Shape = Part.Shape()
    try:
        obj.Label = "Intersection Ready Trim Preview"
    except Exception:
        pass
    vobj = getattr(obj, "ViewObject", None)
    if vobj is not None:
        try:
            vobj.LineColor = (1.0, 0.72, 0.05)
            vobj.ShapeColor = (1.0, 0.72, 0.05)
            vobj.LineWidth = 4.0
            vobj.Visibility = bool(candidates)
        except Exception:
            pass
    try:
        project = find_project(document)
        if project is not None:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
    except Exception:
        pass
    return obj


def _intersection_trim_boundary_result_for_preview(document, *, tolerance: float = 0.05) -> IntersectionTrimBoundaryResult | None:
    if document is None:
        return None
    existing = to_intersection_trim_boundary_result(find_v1_intersection_trim_boundary_result(document))
    if existing is not None:
        return existing
    return _build_intersection_trim_boundary_result(document, tolerance=tolerance)


def _intersection_trim_ready_preview_candidates(result: IntersectionTrimBoundaryResult | None) -> list[dict[str, object]]:
    if result is None:
        return []
    candidates: list[dict[str, object]] = []
    for row in list(getattr(result, "boundary_pair_rows", []) or []):
        if str(getattr(row, "status", "") or "") != "ready_to_trim":
            continue
        candidates.append(
            {
                "patch_ref": str(getattr(row, "patch_output_ref", "") or ""),
                "road_ref": str(getattr(row, "road_output_ref", "") or ""),
                "patch_segment": tuple(float(value) for value in getattr(row, "patch_segment_xyz", ()) or ()),
                "road_segment": tuple(float(value) for value in getattr(row, "road_segment_xyz", ()) or ()),
                "distance": float(getattr(row, "distance_xy", 0.0) or 0.0),
            }
        )
    return candidates


def _create_or_update_intersection_trim_application_preview_object(document, *, tolerance: float = 0.05):
    if document is None or Part is None or App is None:
        return None
    result = _intersection_trim_boundary_result_for_preview(document, tolerance=tolerance)
    candidates = _intersection_trim_ready_preview_candidates(result)
    obj = document.getObject("V1WatertightIntersectionTrimApplicationPreview")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1WatertightIntersectionTrimApplicationPreview")
    application_status = str(getattr(result, "application_status", "") or ("ready" if candidates else "empty"))
    applied_shapes: list[object] = []
    applied_count = 0
    for candidate in candidates:
        patch_segment = tuple(float(value) for value in candidate["patch_segment"])
        road_segment = tuple(float(value) for value in candidate["road_segment"])
        shapes = _intersection_trim_application_shapes(patch_segment, road_segment)
        if shapes:
            applied_shapes.extend(shapes)
            applied_count += 1
    _set_object_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "V1WatertightIntersectionTrimApplicationPreview")
    _set_object_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1_watertight_trim_application_preview")
    _set_object_property(obj, "App::PropertyString", "ApplicationStatus", "Application", application_status)
    _set_object_property(obj, "App::PropertyInteger", "ReadyPairCount", "Application", len(candidates))
    _set_object_property(obj, "App::PropertyInteger", "AppliedPairCount", "Application", applied_count)
    _set_object_property(obj, "App::PropertyFloat", "Tolerance", "Application", float(tolerance or 0.0))
    _set_object_property(
        obj,
        "App::PropertyString",
        "ApplicationDiagnostic",
        "Application",
        (
            f"Intersection trim application preview built from ready pairs: applied={applied_count}; ready={len(candidates)}."
            if applied_count
            else "No ready intersection trim pair could be converted into application guide geometry."
        ),
    )
    _set_object_property(
        obj,
        "App::PropertyStringList",
        "SourceRefs",
        "Traceability",
        list(getattr(result, "source_refs", []) or []) if result is not None else [],
    )
    try:
        obj.Shape = Part.makeCompound([shape for shape in applied_shapes if shape is not None]) if applied_shapes else Part.Shape()
    except Exception:
        obj.Shape = Part.Shape()
    try:
        obj.Label = "Intersection Trim Application Preview"
    except Exception:
        pass
    vobj = getattr(obj, "ViewObject", None)
    if vobj is not None:
        try:
            vobj.LineColor = (0.15, 0.95, 1.0)
            vobj.ShapeColor = (0.15, 0.95, 1.0)
            vobj.LineWidth = 5.0
            vobj.Visibility = bool(applied_shapes)
        except Exception:
            pass
    try:
        project = find_project(document)
        if project is not None:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
    except Exception:
        pass
    return obj


def _intersection_trim_application_shapes(
    patch_segment: tuple[float, float, float, float, float, float],
    road_segment: tuple[float, float, float, float, float, float],
) -> list[object]:
    patch_start = (patch_segment[0], patch_segment[1], patch_segment[2])
    patch_end = (patch_segment[3], patch_segment[4], patch_segment[5])
    road_start = (road_segment[0], road_segment[1], road_segment[2])
    road_end = (road_segment[3], road_segment[4], road_segment[5])
    road_for_patch_start = _closest_point_on_segment_xyz(patch_start, road_start, road_end)
    road_for_patch_end = _closest_point_on_segment_xyz(patch_end, road_start, road_end)
    shapes = [
        _line_shape_from_points(patch_start, patch_end),
        _line_shape_from_points(road_for_patch_start, road_for_patch_end),
        _line_shape_from_points(patch_start, road_for_patch_start),
        _line_shape_from_points(patch_end, road_for_patch_end),
    ]
    return [shape for shape in shapes if shape is not None]


def _create_or_update_intersection_trim_application_output_object(document, *, tolerance: float = 0.05):
    if document is None or Part is None or App is None:
        return None
    result_obj = find_v1_intersection_trim_boundary_result(document)
    result = _intersection_trim_boundary_result_for_preview(document, tolerance=tolerance)
    candidates = _intersection_trim_ready_preview_candidates(result)
    obj = document.getObject("V1WatertightIntersectionTrimApplicationOutput")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1WatertightIntersectionTrimApplicationOutput")
    applied_shapes: list[object] = []
    applied_pair_count = 0
    for candidate in candidates:
        patch_segment = tuple(float(value) for value in candidate["patch_segment"])
        road_segment = tuple(float(value) for value in candidate["road_segment"])
        shapes = _intersection_trim_application_shapes(patch_segment, road_segment)
        if shapes:
            applied_shapes.extend(shapes)
            applied_pair_count += 1
    output_status = "ready" if applied_pair_count else "empty"
    _set_object_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "V1WatertightIntersectionTrimApplicationOutput")
    _set_object_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1_watertight_trim_application_output")
    _set_object_property(obj, "App::PropertyString", "OutputStatus", "Trim Application Output", output_status)
    _set_object_property(obj, "App::PropertyString", "TrimBoundaryResultRef", "Trim Application Output", str(getattr(result_obj, "Name", "") or ""))
    _set_object_property(obj, "App::PropertyInteger", "ReadyPairCount", "Trim Application Output", len(candidates))
    _set_object_property(obj, "App::PropertyInteger", "AppliedPairCount", "Trim Application Output", applied_pair_count)
    _set_object_property(obj, "App::PropertyInteger", "AppliedEdgeCount", "Trim Application Output", len(applied_shapes))
    _set_object_property(obj, "App::PropertyFloat", "Tolerance", "Trim Application Output", float(tolerance or 0.0))
    _set_object_property(
        obj,
        "App::PropertyString",
        "OutputDiagnostic",
        "Trim Application Output",
        (
            f"Intersection trim application output built: applied_pairs={applied_pair_count}; "
            f"applied_edges={len(applied_shapes)}; ready_pairs={len(candidates)}."
            if applied_pair_count
            else "No ready intersection trim pair could be promoted to a trim application output."
        ),
    )
    source_refs = list(getattr(result, "source_refs", []) or []) if result is not None else []
    _set_object_property(obj, "App::PropertyStringList", "SourceRefs", "Traceability", source_refs)
    try:
        obj.Shape = Part.makeCompound(applied_shapes) if applied_shapes else Part.Shape()
    except Exception:
        obj.Shape = Part.Shape()
    try:
        obj.Label = "Intersection Trim Application Output"
    except Exception:
        pass
    vobj = getattr(obj, "ViewObject", None)
    if vobj is not None:
        try:
            vobj.LineColor = (0.0, 0.75, 0.95)
            vobj.ShapeColor = (0.0, 0.75, 0.95)
            vobj.LineWidth = 3.0
            vobj.Visibility = bool(applied_shapes)
        except Exception:
            pass
    try:
        project = find_project(document)
        if project is not None:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
    except Exception:
        pass
    return obj


def _create_or_update_intersection_trim_closure_surface_preview_object(document, *, tolerance: float = 0.05):
    if document is None or Part is None or App is None:
        return None
    result = _intersection_trim_boundary_result_for_preview(document, tolerance=tolerance)
    candidates = _intersection_trim_ready_preview_candidates(result)
    obj = document.getObject("V1WatertightIntersectionTrimClosureSurfacePreview")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1WatertightIntersectionTrimClosureSurfacePreview")
    faces = _intersection_trim_closure_faces_from_result(result)
    closure_status = "ready" if faces else "empty"
    _set_object_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "V1WatertightIntersectionTrimClosureSurfacePreview")
    _set_object_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1_watertight_trim_closure_surface_preview")
    _set_object_property(obj, "App::PropertyString", "ClosureStatus", "Closure Surface", closure_status)
    _set_object_property(obj, "App::PropertyInteger", "ReadyPairCount", "Closure Surface", len(candidates))
    _set_object_property(obj, "App::PropertyInteger", "ClosureFaceCount", "Closure Surface", len(faces))
    _set_object_property(obj, "App::PropertyFloat", "Tolerance", "Closure Surface", float(tolerance or 0.0))
    _set_object_property(
        obj,
        "App::PropertyString",
        "ClosureDiagnostic",
        "Closure Surface",
        (
            f"Intersection trim closure surface preview built: faces={len(faces)}; ready_pairs={len(candidates)}."
            if faces
            else "No ready intersection trim pair could be converted into a closure surface."
        ),
    )
    _set_object_property(
        obj,
        "App::PropertyStringList",
        "SourceRefs",
        "Traceability",
        list(getattr(result, "source_refs", []) or []) if result is not None else [],
    )
    try:
        obj.Shape = Part.makeCompound(faces) if faces else Part.Shape()
    except Exception:
        obj.Shape = Part.Shape()
    try:
        obj.Label = "Intersection Trim Closure Surface Preview"
    except Exception:
        pass
    vobj = getattr(obj, "ViewObject", None)
    if vobj is not None:
        try:
            vobj.LineColor = (0.05, 0.65, 1.0)
            vobj.ShapeColor = (0.05, 0.65, 1.0)
            vobj.Transparency = 35
            vobj.LineWidth = 2.0
            vobj.Visibility = bool(faces)
        except Exception:
            pass
    try:
        project = find_project(document)
        if project is not None:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
    except Exception:
        pass
    return obj


def _create_or_update_intersection_trim_closure_surface_output_object(document, *, tolerance: float = 0.05):
    if document is None or Part is None or App is None:
        return None
    result = _intersection_trim_boundary_result_for_preview(document, tolerance=tolerance)
    faces = _intersection_trim_closure_faces_from_result(result)
    obj = document.getObject("V1WatertightIntersectionTrimClosureSurfaceOutput")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1WatertightIntersectionTrimClosureSurfaceOutput")
    output_status = "ready" if faces else "empty"
    result_ref = str(getattr(find_v1_intersection_trim_boundary_result(document), "Name", "") or "")
    _set_object_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "V1WatertightIntersectionTrimClosureSurfaceOutput")
    _set_object_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1_watertight_trim_closure_surface_output")
    _set_object_property(obj, "App::PropertyString", "OutputStatus", "Closure Surface Output", output_status)
    _set_object_property(obj, "App::PropertyString", "TrimBoundaryResultRef", "Closure Surface Output", result_ref)
    _set_object_property(obj, "App::PropertyInteger", "ReadyPairCount", "Closure Surface Output", int(getattr(result, "ready_pair_count", 0) or 0) if result is not None else 0)
    _set_object_property(obj, "App::PropertyInteger", "ClosureFaceCount", "Closure Surface Output", len(faces))
    _set_object_property(obj, "App::PropertyFloat", "Tolerance", "Closure Surface Output", float(tolerance or 0.0))
    _set_object_property(
        obj,
        "App::PropertyString",
        "OutputDiagnostic",
        "Closure Surface Output",
        (
            f"Intersection trim closure surface output built: faces={len(faces)}."
            if faces
            else "No ready intersection trim closure surface output was built."
        ),
    )
    _set_object_property(
        obj,
        "App::PropertyStringList",
        "SourceRefs",
        "Traceability",
        list(getattr(result, "source_refs", []) or []) if result is not None else [],
    )
    try:
        obj.Shape = Part.makeCompound(faces) if faces else Part.Shape()
    except Exception:
        obj.Shape = Part.Shape()
    try:
        obj.Label = "Intersection Trim Closure Surface Output"
    except Exception:
        pass
    vobj = getattr(obj, "ViewObject", None)
    if vobj is not None:
        try:
            vobj.LineColor = (0.0, 0.45, 0.95)
            vobj.ShapeColor = (0.0, 0.45, 0.95)
            vobj.Transparency = 15
            vobj.LineWidth = 2.0
            vobj.Visibility = bool(faces)
        except Exception:
            pass
    try:
        project = find_project(document)
        if project is not None:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
    except Exception:
        pass
    return obj


def _create_or_update_intersection_trim_closure_cell_output_object(document, *, tolerance: float = 0.05):
    if document is None or Part is None or App is None:
        return None
    result = _intersection_trim_boundary_result_for_preview(document, tolerance=tolerance)
    faces = _intersection_trim_closure_cell_faces_from_result(result, depth=max(float(tolerance or 0.0), 0.05))
    obj = document.getObject("V1WatertightIntersectionTrimClosureCellOutput")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1WatertightIntersectionTrimClosureCellOutput")
    output_status = "ready" if faces else "empty"
    result_ref = str(getattr(find_v1_intersection_trim_boundary_result(document), "Name", "") or "")
    diagnostics = _shape_edge_closure_diagnostics(Part.makeCompound(faces) if faces else Part.Shape())
    _set_object_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "V1WatertightIntersectionTrimClosureCellOutput")
    _set_object_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1_watertight_trim_closure_cell_output")
    _set_object_property(obj, "App::PropertyString", "OutputStatus", "Closure Cell Output", output_status)
    _set_object_property(obj, "App::PropertyString", "TrimBoundaryResultRef", "Closure Cell Output", result_ref)
    _set_object_property(obj, "App::PropertyInteger", "ReadyPairCount", "Closure Cell Output", int(getattr(result, "ready_pair_count", 0) or 0) if result is not None else 0)
    _set_object_property(obj, "App::PropertyInteger", "ClosureCellFaceCount", "Closure Cell Output", len(faces))
    _set_object_property(obj, "App::PropertyString", "ShellClosureStatus", "Closure Cell Output", str(diagnostics["closure_status"]))
    _set_object_property(obj, "App::PropertyInteger", "OpenEdgeCount", "Closure Cell Output", int(diagnostics["open_edge_count"]))
    _set_object_property(obj, "App::PropertyFloat", "CellDepth", "Closure Cell Output", max(float(tolerance or 0.0), 0.05))
    _set_object_property(
        obj,
        "App::PropertyString",
        "OutputDiagnostic",
        "Closure Cell Output",
        (
            f"Intersection trim closure cell output built: faces={len(faces)}; "
            f"shell_status={diagnostics['closure_status']}; open_edges={diagnostics['open_edge_count']}."
            if faces
            else "No ready intersection trim closure cell output was built."
        ),
    )
    _set_object_property(
        obj,
        "App::PropertyStringList",
        "SourceRefs",
        "Traceability",
        list(getattr(result, "source_refs", []) or []) if result is not None else [],
    )
    try:
        obj.Shape = Part.makeCompound(faces) if faces else Part.Shape()
    except Exception:
        obj.Shape = Part.Shape()
    try:
        obj.Label = "Intersection Trim Closure Cell Output"
    except Exception:
        pass
    vobj = getattr(obj, "ViewObject", None)
    if vobj is not None:
        try:
            vobj.LineColor = (0.0, 0.85, 0.55)
            vobj.ShapeColor = (0.0, 0.85, 0.55)
            vobj.Transparency = 25
            vobj.LineWidth = 2.0
            vobj.Visibility = bool(faces)
        except Exception:
            pass
    try:
        project = find_project(document)
        if project is not None:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
    except Exception:
        pass
    return obj


def _create_or_update_intersection_trim_shell_candidate_output_object(document, *, tolerance: float = 0.05):
    if document is None or Part is None or App is None:
        return None
    result_obj = find_v1_intersection_trim_boundary_result(document)
    result = _intersection_trim_boundary_result_for_preview(document, tolerance=tolerance)
    application_obj = _create_or_update_intersection_trim_application_output_object(document, tolerance=tolerance)
    closure_obj = _create_or_update_intersection_trim_closure_surface_output_object(document, tolerance=tolerance)
    closure_cell_obj = _create_or_update_intersection_trim_closure_cell_output_object(document, tolerance=tolerance)
    source_refs = list(getattr(result, "source_refs", []) or []) if result is not None else []
    source_objects = [
        obj
        for ref in source_refs
        for obj in [document.getObject(str(ref or ""))]
        if obj is not None and _is_watertight_output_object(obj)
    ]
    shapes = [getattr(obj, "Shape", None) for obj in source_objects]
    closure_shape = getattr(closure_obj, "Shape", None) if closure_obj is not None else None
    closure_cell_shape = getattr(closure_cell_obj, "Shape", None) if closure_cell_obj is not None else None
    if closure_shape is not None and _shape_count(closure_shape, "Faces") > 0:
        shapes.append(closure_shape)
    if closure_cell_shape is not None and _shape_count(closure_cell_shape, "Faces") > 0:
        shapes.append(closure_cell_shape)
    valid_shapes = [shape for shape in shapes if shape is not None and (_shape_count(shape, "Faces") > 0 or _shape_count(shape, "Edges") > 0)]
    obj = document.getObject("V1WatertightIntersectionTrimShellCandidateOutput")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1WatertightIntersectionTrimShellCandidateOutput")
    shell_status = "ready" if valid_shapes and closure_shape is not None and _shape_count(closure_shape, "Faces") > 0 else "empty"
    try:
        candidate_shape = Part.makeCompound(valid_shapes) if valid_shapes else Part.Shape()
    except Exception:
        candidate_shape = Part.Shape()
    closure_diagnostics = _shape_edge_closure_diagnostics(candidate_shape)
    _set_object_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "V1WatertightIntersectionTrimShellCandidateOutput")
    _set_object_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1_watertight_trim_shell_candidate_output")
    _set_object_property(obj, "App::PropertyString", "ShellCandidateStatus", "Shell Candidate", shell_status)
    _set_object_property(obj, "App::PropertyString", "ShellClosureStatus", "Shell Candidate", str(closure_diagnostics["closure_status"]))
    _set_object_property(obj, "App::PropertyString", "TrimBoundaryResultRef", "Shell Candidate", str(getattr(result_obj, "Name", "") or ""))
    _set_object_property(obj, "App::PropertyString", "TrimApplicationOutputRef", "Shell Candidate", str(getattr(application_obj, "Name", "") or ""))
    _set_object_property(obj, "App::PropertyString", "ClosureSurfaceOutputRef", "Shell Candidate", str(getattr(closure_obj, "Name", "") or ""))
    _set_object_property(obj, "App::PropertyString", "ClosureCellOutputRef", "Shell Candidate", str(getattr(closure_cell_obj, "Name", "") or ""))
    _set_object_property(obj, "App::PropertyInteger", "SourceOutputCount", "Shell Candidate", len(source_objects))
    _set_object_property(obj, "App::PropertyInteger", "ClosureFaceCount", "Shell Candidate", _shape_count(closure_shape, "Faces"))
    _set_object_property(obj, "App::PropertyInteger", "ClosureCellFaceCount", "Shell Candidate", _shape_count(closure_cell_shape, "Faces"))
    _set_object_property(obj, "App::PropertyInteger", "CandidateShapeCount", "Shell Candidate", len(valid_shapes))
    _set_object_property(obj, "App::PropertyInteger", "ShellFaceCount", "Shell Candidate", int(closure_diagnostics["face_count"]))
    _set_object_property(obj, "App::PropertyInteger", "ShellEdgeCount", "Shell Candidate", int(closure_diagnostics["edge_count"]))
    _set_object_property(obj, "App::PropertyInteger", "OpenEdgeCount", "Shell Candidate", int(closure_diagnostics["open_edge_count"]))
    _set_object_property(obj, "App::PropertyInteger", "SharedEdgeCount", "Shell Candidate", int(closure_diagnostics["shared_edge_count"]))
    _set_object_property(
        obj,
        "App::PropertyStringList",
        "SourceOutputRefs",
        "Traceability",
        [str(getattr(source_obj, "Name", "") or "") for source_obj in source_objects],
    )
    _set_object_property(obj, "App::PropertyStringList", "SourceRefs", "Traceability", source_refs)
    _set_object_property(
        obj,
        "App::PropertyString",
        "ShellCandidateDiagnostic",
        "Shell Candidate",
        (
            f"Intersection trim shell candidate output built: source_outputs={len(source_objects)}; "
            f"closure_faces={_shape_count(closure_shape, 'Faces')}; "
            f"closure_cell_faces={_shape_count(closure_cell_shape, 'Faces')}; shapes={len(valid_shapes)}; "
            f"shell_status={closure_diagnostics['closure_status']}; "
            f"open_edges={closure_diagnostics['open_edge_count']}; "
            f"shared_edges={closure_diagnostics['shared_edge_count']}."
            if shell_status == "ready"
            else "Intersection trim shell candidate output is empty because required source or closure geometry is missing."
        ),
    )
    obj.Shape = candidate_shape
    try:
        obj.Label = "Intersection Trim Shell Candidate Output"
    except Exception:
        pass
    vobj = getattr(obj, "ViewObject", None)
    if vobj is not None:
        try:
            vobj.LineColor = (0.2, 0.35, 1.0)
            vobj.ShapeColor = (0.2, 0.35, 1.0)
            vobj.Transparency = 45
            vobj.LineWidth = 2.0
            vobj.Visibility = bool(valid_shapes)
        except Exception:
            pass
    try:
        project = find_project(document)
        if project is not None:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
    except Exception:
        pass
    return obj


def _create_or_update_intersection_trim_fuse_candidate_output_object(document, *, tolerance: float = 0.05):
    if document is None or Part is None or App is None:
        return None
    shell_candidate_obj = _create_or_update_intersection_trim_shell_candidate_output_object(document, tolerance=tolerance)
    closure_cell_ref = str(getattr(shell_candidate_obj, "ClosureCellOutputRef", "") or "")
    source_refs = list(getattr(shell_candidate_obj, "SourceOutputRefs", []) or []) if shell_candidate_obj is not None else []
    fuse_source_refs = [ref for ref in source_refs if str(ref)]
    if closure_cell_ref:
        fuse_source_refs.append(closure_cell_ref)
    source_shapes = [
        getattr(obj, "Shape", None)
        for ref in fuse_source_refs
        for obj in [document.getObject(str(ref or ""))]
        if obj is not None
    ]
    valid_shapes = [shape for shape in source_shapes if shape is not None and (_shape_count(shape, "Faces") > 0 or _shape_count(shape, "Edges") > 0)]
    fuse_shape = None
    fuse_status = "empty"
    fuse_note = "No fuse candidate source shapes are available."
    if valid_shapes:
        fuse_shape = valid_shapes[0]
        fuse_status = "compound_candidate"
        fuse_note = "Fuse candidate compound created; Boolean fuse was not required."
        try:
            for shape in valid_shapes[1:]:
                fuse_shape = fuse_shape.fuse(shape)
            fuse_status = "fused"
            fuse_note = f"Boolean fuse completed for {len(valid_shapes)} source shapes."
        except Exception as exc:
            try:
                fuse_shape = Part.makeCompound(valid_shapes)
            except Exception:
                fuse_shape = Part.Shape()
            fuse_status = "fuse_failed_compound"
            fuse_note = f"Boolean fuse failed; compound candidate retained for review: {exc}"
    else:
        fuse_shape = Part.Shape()
    diagnostics = _shape_edge_closure_diagnostics(fuse_shape)
    obj = document.getObject("V1WatertightIntersectionTrimFuseCandidateOutput")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1WatertightIntersectionTrimFuseCandidateOutput")
    _set_object_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "V1WatertightIntersectionTrimFuseCandidateOutput")
    _set_object_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1_watertight_trim_fuse_candidate_output")
    _set_object_property(obj, "App::PropertyString", "FuseCandidateStatus", "Fuse Candidate", fuse_status)
    _set_object_property(obj, "App::PropertyString", "ShellCandidateOutputRef", "Fuse Candidate", str(getattr(shell_candidate_obj, "Name", "") or ""))
    _set_object_property(obj, "App::PropertyString", "ClosureCellOutputRef", "Fuse Candidate", closure_cell_ref)
    _set_object_property(obj, "App::PropertyInteger", "FuseSourceCount", "Fuse Candidate", len(valid_shapes))
    _set_object_property(obj, "App::PropertyInteger", "FuseFaceCount", "Fuse Candidate", _shape_count(fuse_shape, "Faces"))
    _set_object_property(obj, "App::PropertyInteger", "FuseEdgeCount", "Fuse Candidate", _shape_count(fuse_shape, "Edges"))
    _set_object_property(obj, "App::PropertyString", "ShellClosureStatus", "Fuse Candidate", str(diagnostics["closure_status"]))
    _set_object_property(obj, "App::PropertyInteger", "OpenEdgeCount", "Fuse Candidate", int(diagnostics["open_edge_count"]))
    _set_object_property(
        obj,
        "App::PropertyStringList",
        "FuseSourceRefs",
        "Traceability",
        fuse_source_refs,
    )
    _set_object_property(
        obj,
        "App::PropertyStringList",
        "SourceRefs",
        "Traceability",
        list(getattr(shell_candidate_obj, "SourceRefs", []) or []) if shell_candidate_obj is not None else [],
    )
    _set_object_property(
        obj,
        "App::PropertyString",
        "FuseDiagnostic",
        "Fuse Candidate",
        (
            f"{fuse_note} faces={_shape_count(fuse_shape, 'Faces')}; edges={_shape_count(fuse_shape, 'Edges')}; "
            f"shell_status={diagnostics['closure_status']}; open_edges={diagnostics['open_edge_count']}."
        ),
    )
    try:
        obj.Shape = fuse_shape
    except Exception:
        obj.Shape = Part.Shape()
    try:
        obj.Label = "Intersection Trim Fuse Candidate Output"
    except Exception:
        pass
    vobj = getattr(obj, "ViewObject", None)
    if vobj is not None:
        try:
            vobj.LineColor = (1.0, 0.35, 0.05)
            vobj.ShapeColor = (1.0, 0.35, 0.05)
            vobj.Transparency = 40
            vobj.LineWidth = 2.0
            vobj.Visibility = bool(valid_shapes)
        except Exception:
            pass
    try:
        project = find_project(document)
        if project is not None:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
    except Exception:
        pass
    return obj


def _create_or_update_intersection_trim_shell_reconstruction_output_object(document, *, tolerance: float = 0.05):
    if document is None or Part is None or App is None:
        return None
    candidate_obj = _create_or_update_intersection_trim_shell_candidate_output_object(document, tolerance=tolerance)
    closure_cell_obj = _create_or_update_intersection_trim_closure_cell_output_object(document, tolerance=tolerance)
    closure_cell_shape = getattr(closure_cell_obj, "Shape", None) if closure_cell_obj is not None else None
    candidate_shape = getattr(candidate_obj, "Shape", None) if candidate_obj is not None else None
    closure_cell_faces = list(getattr(closure_cell_shape, "Faces", []) or []) if closure_cell_shape is not None else []
    candidate_faces = list(getattr(candidate_shape, "Faces", []) or []) if candidate_shape is not None else []
    faces = closure_cell_faces or candidate_faces
    obj = document.getObject("V1WatertightIntersectionTrimShellReconstructionOutput")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1WatertightIntersectionTrimShellReconstructionOutput")
    shell_shape = None
    reconstruction_note = ""
    if faces:
        try:
            shell_shape = Part.Shell(faces)
            reconstruction_note = "Part.Shell created from shell candidate faces."
        except Exception as exc:
            shell_shape = Part.makeCompound(faces)
            reconstruction_note = f"Part.Shell creation failed; face compound used for diagnostics: {exc}"
    else:
        shell_shape = Part.Shape()
        reconstruction_note = "No shell candidate faces are available."
    diagnostic_shape = Part.makeCompound(faces) if faces else Part.Shape()
    diagnostics = _shape_edge_closure_diagnostics(diagnostic_shape)
    reconstruction_status = "empty"
    if faces:
        reconstruction_status = "closed" if str(diagnostics["closure_status"]) == "closed" else "open"
    _set_object_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "V1WatertightIntersectionTrimShellReconstructionOutput")
    _set_object_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1_watertight_trim_shell_reconstruction_output")
    _set_object_property(obj, "App::PropertyString", "ReconstructionStatus", "Shell Reconstruction", reconstruction_status)
    _set_object_property(obj, "App::PropertyString", "ShellClosureStatus", "Shell Reconstruction", str(diagnostics["closure_status"]))
    _set_object_property(obj, "App::PropertyString", "ShellCandidateOutputRef", "Shell Reconstruction", str(getattr(candidate_obj, "Name", "") or ""))
    _set_object_property(obj, "App::PropertyString", "ClosureCellOutputRef", "Shell Reconstruction", str(getattr(closure_cell_obj, "Name", "") or ""))
    _set_object_property(obj, "App::PropertyInteger", "InputFaceCount", "Shell Reconstruction", len(faces))
    _set_object_property(obj, "App::PropertyInteger", "ClosureCellFaceCount", "Shell Reconstruction", len(closure_cell_faces))
    _set_object_property(obj, "App::PropertyInteger", "ShellFaceCount", "Shell Reconstruction", int(diagnostics["face_count"]))
    _set_object_property(obj, "App::PropertyInteger", "ShellEdgeCount", "Shell Reconstruction", int(diagnostics["edge_count"]))
    _set_object_property(obj, "App::PropertyInteger", "OpenEdgeCount", "Shell Reconstruction", int(diagnostics["open_edge_count"]))
    _set_object_property(obj, "App::PropertyInteger", "SharedEdgeCount", "Shell Reconstruction", int(diagnostics["shared_edge_count"]))
    _set_object_property(
        obj,
        "App::PropertyString",
        "ReconstructionDiagnostic",
        "Shell Reconstruction",
        (
            f"Intersection trim shell reconstruction output built: input_faces={len(faces)}; "
            f"shell_status={diagnostics['closure_status']}; open_edges={diagnostics['open_edge_count']}; "
            f"shared_edges={diagnostics['shared_edge_count']}; {reconstruction_note}"
        ),
    )
    _set_object_property(
        obj,
        "App::PropertyStringList",
        "SourceRefs",
        "Traceability",
        list(getattr(candidate_obj, "SourceRefs", []) or []) if candidate_obj is not None else [],
    )
    try:
        obj.Shape = shell_shape
    except Exception:
        obj.Shape = Part.Shape()
    try:
        obj.Label = "Intersection Trim Shell Reconstruction Output"
    except Exception:
        pass
    vobj = getattr(obj, "ViewObject", None)
    if vobj is not None:
        try:
            vobj.LineColor = (0.55, 0.2, 1.0)
            vobj.ShapeColor = (0.55, 0.2, 1.0)
            vobj.Transparency = 30
            vobj.LineWidth = 2.0
            vobj.Visibility = bool(faces)
        except Exception:
            pass
    try:
        project = find_project(document)
        if project is not None:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
    except Exception:
        pass
    return obj


def _create_or_update_intersection_trim_solid_reconstruction_output_object(document, *, tolerance: float = 0.05):
    if document is None or Part is None or App is None:
        return None
    shell_obj = _create_or_update_intersection_trim_shell_reconstruction_output_object(document, tolerance=tolerance)
    shell_shape = getattr(shell_obj, "Shape", None) if shell_obj is not None else None
    shell_status = str(getattr(shell_obj, "ShellClosureStatus", "") or "")
    open_edge_count = int(getattr(shell_obj, "OpenEdgeCount", 0) or 0) if shell_obj is not None else 0
    obj = document.getObject("V1WatertightIntersectionTrimSolidReconstructionOutput")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1WatertightIntersectionTrimSolidReconstructionOutput")
    solid_shape = Part.Shape()
    solid_status = "empty"
    solid_note = "No shell reconstruction output is available."
    if shell_shape is not None and _shape_count(shell_shape, "Faces") > 0:
        if shell_status == "closed" and open_edge_count == 0:
            try:
                solid_shape = Part.Solid(shell_shape)
                solid_status = "solid"
                solid_note = "Part.Solid created from closed shell reconstruction output."
            except Exception as exc:
                solid_shape = shell_shape
                solid_status = "error"
                solid_note = f"Part.Solid failed from closed shell reconstruction output: {exc}"
        else:
            solid_status = "blocked_open_shell"
            solid_note = f"Solid reconstruction blocked because shell is open: open_edges={open_edge_count}."
            solid_shape = shell_shape
    face_count = _shape_count(solid_shape, "Faces")
    edge_count = _shape_count(solid_shape, "Edges")
    volume = 0.0
    try:
        volume = float(getattr(solid_shape, "Volume", 0.0) or 0.0)
    except Exception:
        volume = 0.0
    _set_object_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "V1WatertightIntersectionTrimSolidReconstructionOutput")
    _set_object_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1_watertight_trim_solid_reconstruction_output")
    _set_object_property(obj, "App::PropertyString", "SolidReconstructionStatus", "Solid Reconstruction", solid_status)
    _set_object_property(obj, "App::PropertyString", "ShellReconstructionOutputRef", "Solid Reconstruction", str(getattr(shell_obj, "Name", "") or ""))
    _set_object_property(obj, "App::PropertyString", "ShellClosureStatus", "Solid Reconstruction", shell_status)
    _set_object_property(obj, "App::PropertyInteger", "OpenEdgeCount", "Solid Reconstruction", open_edge_count)
    _set_object_property(obj, "App::PropertyInteger", "SolidFaceCount", "Solid Reconstruction", face_count)
    _set_object_property(obj, "App::PropertyInteger", "SolidEdgeCount", "Solid Reconstruction", edge_count)
    _set_object_property(obj, "App::PropertyFloat", "SolidVolume", "Solid Reconstruction", volume)
    _set_object_property(obj, "App::PropertyString", "SolidDiagnostic", "Solid Reconstruction", solid_note)
    _set_object_property(
        obj,
        "App::PropertyStringList",
        "SourceRefs",
        "Traceability",
        list(getattr(shell_obj, "SourceRefs", []) or []) if shell_obj is not None else [],
    )
    try:
        obj.Shape = solid_shape
    except Exception:
        obj.Shape = Part.Shape()
    try:
        obj.Label = "Intersection Trim Solid Reconstruction Output"
    except Exception:
        pass
    vobj = getattr(obj, "ViewObject", None)
    if vobj is not None:
        try:
            vobj.LineColor = (0.85, 0.15, 0.95)
            vobj.ShapeColor = (0.85, 0.15, 0.95)
            vobj.Transparency = 20 if solid_status == "solid" else 55
            vobj.LineWidth = 2.0
            vobj.Visibility = bool(face_count)
        except Exception:
            pass
    try:
        project = find_project(document)
        if project is not None:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
    except Exception:
        pass
    return obj


def _intersection_trim_closure_faces_from_result(result: IntersectionTrimBoundaryResult | None) -> list[object]:
    faces: list[object] = []
    for candidate in _intersection_trim_ready_preview_candidates(result):
        patch_segment = tuple(float(value) for value in candidate["patch_segment"])
        road_segment = tuple(float(value) for value in candidate["road_segment"])
        face = _intersection_trim_closure_face(patch_segment, road_segment)
        if face is not None:
            faces.append(face)
    return faces


def _intersection_trim_closure_cell_faces_from_result(result: IntersectionTrimBoundaryResult | None, *, depth: float) -> list[object]:
    faces: list[object] = []
    for candidate in _intersection_trim_ready_preview_candidates(result):
        patch_segment = tuple(float(value) for value in candidate["patch_segment"])
        road_segment = tuple(float(value) for value in candidate["road_segment"])
        cell_faces = _intersection_trim_closure_cell_faces(patch_segment, road_segment, depth=depth)
        faces.extend(face for face in cell_faces if face is not None)
    return faces


def _intersection_trim_closure_cell_faces(
    patch_segment: tuple[float, float, float, float, float, float],
    road_segment: tuple[float, float, float, float, float, float],
    *,
    depth: float,
) -> list[object]:
    top = _intersection_trim_closure_quad_points(patch_segment, road_segment)
    if len(top) < 3:
        return []
    dz = abs(float(depth or 0.0)) or 0.05
    bottom = [(point[0], point[1], point[2] - dz) for point in top]
    face_point_rows = [
        top,
        list(reversed(bottom)),
    ]
    for index, point in enumerate(top):
        next_index = (index + 1) % len(top)
        face_point_rows.append([point, top[next_index], bottom[next_index], bottom[index]])
    return [_face_from_xyz_points(points) for points in face_point_rows]


def _intersection_trim_closure_face(
    patch_segment: tuple[float, float, float, float, float, float],
    road_segment: tuple[float, float, float, float, float, float],
):
    points = _intersection_trim_closure_quad_points(patch_segment, road_segment)
    if len(points) < 3:
        return None
    return _face_from_xyz_points(points)


def _intersection_trim_closure_quad_points(
    patch_segment: tuple[float, float, float, float, float, float],
    road_segment: tuple[float, float, float, float, float, float],
) -> list[tuple[float, float, float]]:
    patch_start = (patch_segment[0], patch_segment[1], patch_segment[2])
    patch_end = (patch_segment[3], patch_segment[4], patch_segment[5])
    road_start = (road_segment[0], road_segment[1], road_segment[2])
    road_end = (road_segment[3], road_segment[4], road_segment[5])
    road_for_patch_start = _closest_point_on_segment_xyz(patch_start, road_start, road_end)
    road_for_patch_end = _closest_point_on_segment_xyz(patch_end, road_start, road_end)
    return _dedupe_xyz_points([patch_start, patch_end, road_for_patch_end, road_for_patch_start])


def _face_from_xyz_points(points: list[tuple[float, float, float]]):
    if len(points) < 3 or Part is None or App is None:
        return None
    try:
        vectors = [App.Vector(*point) for point in points]
        vectors.append(vectors[0])
        return Part.Face(Part.makePolygon(vectors))
    except Exception:
        return None


def _dedupe_xyz_points(points: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    output: list[tuple[float, float, float]] = []
    seen: set[tuple[float, float, float]] = set()
    for point in points:
        key = (round(float(point[0]), 9), round(float(point[1]), 9), round(float(point[2]), 9))
        if key in seen:
            continue
        seen.add(key)
        output.append((float(point[0]), float(point[1]), float(point[2])))
    return output


def _create_or_update_intersection_trim_boundary_result_object(document, *, tolerance: float = 0.05):
    if document is None:
        return None
    result = _build_intersection_trim_boundary_result(document, tolerance=tolerance)
    try:
        obj = create_or_update_v1_intersection_trim_boundary_result_object(
            document=document,
            trim_boundary_result=result,
            project=find_project(document),
            object_name="V1IntersectionTrimBoundaryResult",
            label="Intersection Trim Boundary Result",
        )
        _link_intersection_trim_boundary_result_to_outputs(document, obj)
        return obj
    except Exception:
        return None


def _link_intersection_trim_boundary_result_to_outputs(document, result_obj) -> int:
    """Attach trim-boundary result refs to the related Watertight Solid output objects."""

    if document is None or result_obj is None:
        return 0
    result_ref = str(getattr(result_obj, "Name", "") or "")
    if not result_ref:
        return 0
    output_refs = _unique_refs(
        [
            *list(getattr(result_obj, "PatchOutputRefs", []) or []),
            *list(getattr(result_obj, "RoadOutputRefs", []) or []),
        ]
    )
    linked = 0
    for output_ref in output_refs:
        obj = document.getObject(str(output_ref or ""))
        if obj is None or not _is_watertight_output_object(obj):
            continue
        try:
            existing = [str(ref) for ref in list(getattr(obj, "ResultRefs", []) or []) if str(ref)]
            if result_ref not in existing:
                obj.ResultRefs = [*existing, result_ref]
            _set_object_property(obj, "App::PropertyString", "IntersectionTrimBoundaryResultRef", "Intersection Trim", result_ref)
            _set_object_property(
                obj,
                "App::PropertyString",
                "IntersectionTrimApplicationStatus",
                "Intersection Trim",
                str(getattr(result_obj, "ApplicationStatus", "") or "not_evaluated"),
            )
            _set_object_property(
                obj,
                "App::PropertyInteger",
                "IntersectionTrimBoundaryPairCount",
                "Intersection Trim",
                int(getattr(result_obj, "BoundaryPairCount", 0) or 0),
            )
            _set_object_property(
                obj,
                "App::PropertyInteger",
                "IntersectionTrimReadyPairCount",
                "Intersection Trim",
                int(getattr(result_obj, "ReadyPairCount", 0) or 0),
            )
            try:
                obj.touch()
            except Exception:
                pass
            linked += 1
        except Exception:
            continue
    return linked


def _build_intersection_trim_boundary_result(document, *, tolerance: float = 0.05) -> IntersectionTrimBoundaryResult:
    candidates = _intersection_trim_preview_candidates(document, tolerance=tolerance)
    rows: list[IntersectionTrimBoundaryPair] = []
    ready_count = 0
    blocked_count = 0
    for index, candidate in enumerate(candidates, start=1):
        distance = float(candidate.get("distance", 0.0) or 0.0)
        patch_segment = tuple(float(value) for value in candidate["patch_segment"])
        road_segment = tuple(float(value) for value in candidate["road_segment"])
        status, status_note = _intersection_trim_pair_status(
            patch_segment,
            road_segment,
            distance_xy=distance,
            tolerance=tolerance,
        )
        if status == "ready_to_trim":
            ready_count += 1
        else:
            blocked_count += 1
        rows.append(
            IntersectionTrimBoundaryPair(
                boundary_pair_id=f"intersection-trim-boundary:{index}",
                patch_output_ref=str(candidate.get("patch_ref", "") or ""),
                road_output_ref=str(candidate.get("road_ref", "") or ""),
                distance_xy=distance,
                patch_segment_xyz=patch_segment,
                road_segment_xyz=road_segment,
                status=status,
                notes=(
                    f"Candidate patch/road trim edge pair; distance_xy={distance:.3f}; "
                    f"tolerance={float(tolerance or 0.0):.3f}; {status_note}"
                ),
            )
        )
    application_status = "ready" if ready_count > 0 and blocked_count == 0 else "partial" if ready_count > 0 else "blocked" if rows else "empty"
    return IntersectionTrimBoundaryResult(
        schema_version=1,
        project_id=_document_project_id(document),
        label="Intersection Trim Boundary Result",
        source_refs=_unique_refs([ref for row in rows for ref in (row.patch_output_ref, row.road_output_ref)]),
        trim_boundary_result_id="intersection-trim-boundaries:watertight",
        tolerance=float(tolerance or 0.0),
        application_status=application_status,
        ready_pair_count=ready_count,
        blocked_pair_count=blocked_count,
        boundary_pair_rows=rows,
    )


def _intersection_trim_pair_status(
    patch_segment: tuple[float, float, float, float, float, float],
    road_segment: tuple[float, float, float, float, float, float],
    *,
    distance_xy: float,
    tolerance: float,
) -> tuple[str, str]:
    patch_length = _segment_xyz_length(patch_segment)
    road_length = _segment_xyz_length(road_segment)
    tol = max(float(tolerance or 0.0), 0.0)
    if patch_length <= 1.0e-6:
        return "blocked", "patch edge is degenerate."
    if road_length <= 1.0e-6:
        return "blocked", "road edge is degenerate."
    if float(distance_xy or 0.0) > tol:
        return "blocked", "edge-pair distance exceeds trim tolerance."
    return "ready_to_trim", f"ready for future clip/trim; patch_length={patch_length:.3f}; road_length={road_length:.3f}."


def _segment_xyz_length(segment: tuple[float, float, float, float, float, float]) -> float:
    return math.sqrt(
        (float(segment[3]) - float(segment[0])) ** 2
        + (float(segment[4]) - float(segment[1])) ** 2
        + (float(segment[5]) - float(segment[2])) ** 2
    )


def _intersection_trim_preview_candidates(document, *, tolerance: float) -> list[dict[str, object]]:
    road_objects = [
        obj for obj in _watertight_output_objects(document)
        if _object_has_target_family(obj, {"road_body_envelope", "region_body"})
    ]
    patch_objects = [
        obj for obj in _watertight_output_objects(document)
        if _object_has_target_family(obj, {"intersection_patch_body"})
    ]
    if not road_objects or not patch_objects:
        return []
    tol = max(float(tolerance or 0.0), 0.0)
    candidates: list[dict[str, object]] = []
    for patch_obj in patch_objects:
        patch_segments = _shape_edge_xyz_segments(getattr(patch_obj, "Shape", None))
        if not patch_segments:
            continue
        for road_obj in road_objects:
            road_segments = _shape_edge_xyz_segments(getattr(road_obj, "Shape", None))
            if not road_segments:
                continue
            for patch_segment in patch_segments:
                for road_segment in road_segments:
                    distance = _segment_xy_distance_from_xyz(patch_segment, road_segment)
                    if distance <= tol:
                        candidates.append(
                            {
                                "patch_ref": str(getattr(patch_obj, "Name", "") or ""),
                                "road_ref": str(getattr(road_obj, "Name", "") or ""),
                                "patch_segment": patch_segment,
                                "road_segment": road_segment,
                                "distance": distance,
                            }
                        )
                        if len(candidates) >= 120:
                            return candidates
    return candidates


def _build_simulation_package_output(document, *, qa_output=None):
    active_qa_output = qa_output or _build_simulation_qa_output(document)
    return WatertightSimulationPackageService().build(
        WatertightSimulationPackageBuildRequest(
            project_id=_document_project_id(document),
            package_output_id="simulation-package:watertight-solids",
            simulation_qa_output=active_qa_output,
            output_refs=[str(getattr(obj, "Name", "") or "") for obj in _watertight_output_objects(document)],
            solid_inputs=_simulation_qa_solid_inputs(document),
            terrain_ref=_terrain_context_ref(document),
            terrain_bound_box=_terrain_context_bound_box_tuple(document),
            drainage_readiness=_drainage_watertight_handoff_dict(
                drainage_watertight_handoff_summary(document, target_model=discover_watertight_solid_targets(document))
            ),
            intersection_trim=_intersection_trim_handoff_dict(document),
        )
    )


def _drainage_watertight_handoff_dict(summary: DrainageWatertightHandoffSummary) -> dict[str, object]:
    return {
        "readiness_status": summary.readiness_status,
        "source_status": summary.source_status,
        "flow_route_count": summary.flow_route_count,
        "capture_only_route_count": summary.capture_only_route_count,
        "pipe_candidate_count": summary.pipe_candidate_count,
        "unresolved_port_route_count": summary.unresolved_port_route_count,
        "missing_element_route_count": summary.missing_element_route_count,
        "lined_ditch_target_count": summary.lined_ditch_target_count,
        "pipe_segment_target_count": summary.pipe_segment_target_count,
        "pipeline_network_target_count": summary.pipeline_network_target_count,
        "structure_body_target_count": summary.structure_body_target_count,
        "built_drainage_output_count": summary.built_drainage_output_count,
        "network_fuse_status": summary.network_fuse_status,
    }


def _intersection_trim_handoff_dict(document) -> dict[str, object]:
    if document is None:
        return {"status": "not_available"}
    result_obj = _create_or_update_intersection_trim_boundary_result_object(document)
    result = to_intersection_trim_boundary_result(result_obj)
    if result is None:
        return {"status": "not_available"}
    application_obj = _create_or_update_intersection_trim_application_output_object(document)
    closure_surface_obj = _create_or_update_intersection_trim_closure_surface_output_object(document)
    closure_cell_obj = _create_or_update_intersection_trim_closure_cell_output_object(document)
    shell_candidate_obj = _create_or_update_intersection_trim_shell_candidate_output_object(document)
    fuse_obj = _create_or_update_intersection_trim_fuse_candidate_output_object(document)
    shell_reconstruction_obj = _create_or_update_intersection_trim_shell_reconstruction_output_object(document)
    solid_reconstruction_obj = _create_or_update_intersection_trim_solid_reconstruction_output_object(document)
    handoff_chain_refs = _intersection_trim_handoff_chain_refs(
        result_obj,
        application_obj,
        closure_surface_obj,
        closure_cell_obj,
        shell_candidate_obj,
        fuse_obj,
        shell_reconstruction_obj,
        solid_reconstruction_obj,
    )
    handoff_stage_statuses = _intersection_trim_handoff_stage_statuses(
        result_obj=result_obj,
        application_obj=application_obj,
        closure_surface_obj=closure_surface_obj,
        closure_cell_obj=closure_cell_obj,
        shell_candidate_obj=shell_candidate_obj,
        fuse_obj=fuse_obj,
        shell_reconstruction_obj=shell_reconstruction_obj,
        solid_reconstruction_obj=solid_reconstruction_obj,
    )
    _link_intersection_trim_handoff_chain_to_outputs(
        document,
        result_obj=result_obj,
        handoff_chain_refs=handoff_chain_refs,
        handoff_stage_statuses=handoff_stage_statuses,
    )
    pair_rows = [
        {
            "boundary_pair_id": str(getattr(row, "boundary_pair_id", "") or ""),
            "status": str(getattr(row, "status", "") or ""),
            "patch_output_ref": str(getattr(row, "patch_output_ref", "") or ""),
            "road_output_ref": str(getattr(row, "road_output_ref", "") or ""),
            "distance_xy": float(getattr(row, "distance_xy", 0.0) or 0.0),
            "patch_segment_xyz": tuple(float(value) for value in getattr(row, "patch_segment_xyz", ()) or ()),
            "road_segment_xyz": tuple(float(value) for value in getattr(row, "road_segment_xyz", ()) or ()),
        }
        for row in list(getattr(result, "boundary_pair_rows", []) or [])
        if str(getattr(row, "status", "") or "") == "ready_to_trim"
    ]
    return {
        "status": str(getattr(result, "application_status", "") or "not_available"),
        "result_ref": str(getattr(result_obj, "Name", "") or ""),
        "boundary_pair_count": len(list(getattr(result, "boundary_pair_rows", []) or [])),
        "ready_pair_count": int(getattr(result, "ready_pair_count", 0) or 0),
        "blocked_pair_count": int(getattr(result, "blocked_pair_count", 0) or 0),
        "pair_rows": pair_rows,
        "fuse_status": str(getattr(fuse_obj, "FuseCandidateStatus", "") or "not_available"),
        "fuse_candidate_ref": str(getattr(fuse_obj, "Name", "") or ""),
        "fuse_source_count": int(getattr(fuse_obj, "FuseSourceCount", 0) or 0),
        "fuse_face_count": int(getattr(fuse_obj, "FuseFaceCount", 0) or 0),
        "fuse_open_edge_count": int(getattr(fuse_obj, "OpenEdgeCount", 0) or 0),
        "fuse_source_refs": [str(ref) for ref in list(getattr(fuse_obj, "FuseSourceRefs", []) or []) if str(ref)],
        "handoff_chain_refs": handoff_chain_refs,
        "handoff_stage_statuses": handoff_stage_statuses,
    }


def _intersection_trim_handoff_chain_refs(*objects) -> list[str]:
    return _unique_refs(str(getattr(obj, "Name", "") or "") for obj in objects if obj is not None)


def _intersection_trim_handoff_stage_statuses(
    *,
    result_obj,
    application_obj,
    closure_surface_obj,
    closure_cell_obj,
    shell_candidate_obj,
    fuse_obj,
    shell_reconstruction_obj,
    solid_reconstruction_obj,
) -> list[str]:
    return [
        f"trim_boundary={str(getattr(result_obj, 'ApplicationStatus', '') or 'not_available')}",
        f"trim_application={str(getattr(application_obj, 'OutputStatus', '') or 'not_available')}",
        f"closure_surface={str(getattr(closure_surface_obj, 'OutputStatus', '') or 'not_available')}",
        f"closure_cell={str(getattr(closure_cell_obj, 'OutputStatus', '') or 'not_available')}",
        f"shell_candidate={str(getattr(shell_candidate_obj, 'ShellCandidateStatus', '') or 'not_available')}",
        f"fuse_candidate={str(getattr(fuse_obj, 'FuseCandidateStatus', '') or 'not_available')}",
        f"shell_reconstruction={str(getattr(shell_reconstruction_obj, 'ReconstructionStatus', '') or 'not_available')}",
        f"solid_reconstruction={str(getattr(solid_reconstruction_obj, 'SolidReconstructionStatus', '') or 'not_available')}",
    ]


def _link_intersection_trim_handoff_chain_to_outputs(
    document,
    *,
    result_obj,
    handoff_chain_refs: list[str],
    handoff_stage_statuses: list[str],
) -> int:
    if document is None or result_obj is None:
        return 0
    output_refs = _unique_refs(
        [
            *list(getattr(result_obj, "PatchOutputRefs", []) or []),
            *list(getattr(result_obj, "RoadOutputRefs", []) or []),
        ]
    )
    linked = 0
    for output_ref in output_refs:
        obj = document.getObject(str(output_ref or ""))
        if obj is None or not _is_watertight_output_object(obj):
            continue
        _set_object_property(obj, "App::PropertyStringList", "IntersectionTrimHandoffChainRefs", "Intersection Trim", handoff_chain_refs)
        _set_object_property(obj, "App::PropertyStringList", "IntersectionTrimHandoffStageStatuses", "Intersection Trim", handoff_stage_statuses)
        try:
            obj.IntersectionTrimHandoffChainRefs = list(handoff_chain_refs)
            obj.IntersectionTrimHandoffStageStatuses = list(handoff_stage_statuses)
            obj.touch()
        except Exception:
            pass
        linked += 1
    return linked


def _simulation_qa_solid_inputs(document) -> list[WatertightSimulationQaSolidInput]:
    rows: list[WatertightSimulationQaSolidInput] = []
    for obj in _watertight_output_objects(document):
        rows.append(
            WatertightSimulationQaSolidInput(
                output_ref=str(getattr(obj, "Name", "") or ""),
                target_families=[str(value or "") for value in list(getattr(obj, "TargetFamilies", []) or [])],
                volumes=[float(value or 0.0) for value in list(getattr(obj, "Volumes", []) or [])],
                valid_solid_statuses=[str(value or "").strip().lower() == "true" for value in list(getattr(obj, "ValidSolidStatuses", []) or [])],
                shape_valid=_watertight_output_object_shape_is_valid(obj),
                bound_box=_shape_bound_box_tuple(getattr(obj, "Shape", None)),
                edge_xy_segments=_shape_edge_xy_segments(getattr(obj, "Shape", None)),
                subassembly_refs=[str(value or "") for value in list(getattr(obj, "SubassemblyRefs", []) or [])],
                structure_refs=[str(value or "") for value in list(getattr(obj, "StructureRefs", []) or [])],
                flow_route_refs=[str(value or "") for value in list(getattr(obj, "FlowRouteRefs", []) or [])],
                source_refs=[str(value or "") for value in list(getattr(obj, "SourceRefs", []) or [])],
            )
        )
    return rows


def _document_project_id(document) -> str:
    project = find_project(document)
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _watertight_output_objects(document) -> list[object]:
    if document is None:
        return []
    return [obj for obj in list(getattr(document, "Objects", []) or []) if _is_watertight_output_object(obj)]


def _is_watertight_output_object(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1WatertightSolidOutput":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_watertight_solid_output":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    return proxy_type == "V1WatertightSolidOutput"


def _watertight_output_object_is_valid(obj) -> bool:
    statuses = [str(value or "").strip().lower() for value in list(getattr(obj, "ValidSolidStatuses", []) or [])]
    if statuses and any(value != "true" for value in statuses):
        return False
    return _watertight_output_object_shape_is_valid(obj)


def _watertight_output_object_shape_is_valid(obj) -> bool:
    shape = getattr(obj, "Shape", None)
    if shape is None:
        return False
    return _shape_count(shape, "Solids") > 0 and float(getattr(shape, "Volume", 0.0) or 0.0) > 0.0


def _shape_bound_box_tuple(shape) -> tuple[float, float, float, float, float, float] | None:
    bbox = getattr(shape, "BoundBox", None)
    if bbox is None:
        return None
    return (
        float(getattr(bbox, "XMin", 0.0) or 0.0),
        float(getattr(bbox, "XMax", 0.0) or 0.0),
        float(getattr(bbox, "YMin", 0.0) or 0.0),
        float(getattr(bbox, "YMax", 0.0) or 0.0),
        float(getattr(bbox, "ZMin", 0.0) or 0.0),
        float(getattr(bbox, "ZMax", 0.0) or 0.0),
    )


def _shape_edge_xy_segments(shape) -> list[tuple[float, float, float, float]]:
    segments: list[tuple[float, float, float, float]] = []
    if shape is None:
        return segments
    for edge in list(getattr(shape, "Edges", []) or []):
        vertices = list(getattr(edge, "Vertexes", []) or [])
        if len(vertices) < 2:
            continue
        first = getattr(vertices[0], "Point", None)
        last = getattr(vertices[-1], "Point", None)
        if first is None or last is None:
            continue
        try:
            x1 = float(getattr(first, "x", 0.0) or 0.0)
            y1 = float(getattr(first, "y", 0.0) or 0.0)
            x2 = float(getattr(last, "x", 0.0) or 0.0)
            y2 = float(getattr(last, "y", 0.0) or 0.0)
        except Exception:
            continue
        if (x1, y1) == (x2, y2):
            continue
        segments.append((x1, y1, x2, y2))
    return segments


def _shape_edge_xyz_segments(shape) -> list[tuple[float, float, float, float, float, float]]:
    segments: list[tuple[float, float, float, float, float, float]] = []
    if shape is None:
        return segments
    for edge in list(getattr(shape, "Edges", []) or []):
        vertices = list(getattr(edge, "Vertexes", []) or [])
        if len(vertices) < 2:
            continue
        first = getattr(vertices[0], "Point", None)
        last = getattr(vertices[-1], "Point", None)
        if first is None or last is None:
            continue
        try:
            x1 = float(getattr(first, "x", 0.0) or 0.0)
            y1 = float(getattr(first, "y", 0.0) or 0.0)
            z1 = float(getattr(first, "z", 0.0) or 0.0)
            x2 = float(getattr(last, "x", 0.0) or 0.0)
            y2 = float(getattr(last, "y", 0.0) or 0.0)
            z2 = float(getattr(last, "z", 0.0) or 0.0)
        except Exception:
            continue
        if (x1, y1, z1) == (x2, y2, z2):
            continue
        segments.append((x1, y1, z1, x2, y2, z2))
    return segments


def _object_has_target_family(obj, families: set[str]) -> bool:
    return bool({str(value or "").strip() for value in list(getattr(obj, "TargetFamilies", []) or [])} & families)


def _segment_xy_distance_from_xyz(
    left: tuple[float, float, float, float, float, float],
    right: tuple[float, float, float, float, float, float],
) -> float:
    return _segment_xy_distance_2d((left[0], left[1], left[3], left[4]), (right[0], right[1], right[3], right[4]))


def _segment_xy_distance_2d(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    ax, ay, bx, by = [float(value) for value in left]
    cx, cy, dx, dy = [float(value) for value in right]
    if _segments_xy_intersect_2d((ax, ay), (bx, by), (cx, cy), (dx, dy)):
        return 0.0
    return min(
        _point_to_segment_xy_distance_2d((ax, ay), (cx, cy), (dx, dy)),
        _point_to_segment_xy_distance_2d((bx, by), (cx, cy), (dx, dy)),
        _point_to_segment_xy_distance_2d((cx, cy), (ax, ay), (bx, by)),
        _point_to_segment_xy_distance_2d((dx, dy), (ax, ay), (bx, by)),
    )


def _segments_xy_intersect_2d(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    def orient(p, q, r) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on_segment(p, q, r) -> bool:
        return (
            min(p[0], r[0]) - 1e-9 <= q[0] <= max(p[0], r[0]) + 1e-9
            and min(p[1], r[1]) - 1e-9 <= q[1] <= max(p[1], r[1]) + 1e-9
        )

    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = orient(c, d, a)
    o4 = orient(c, d, b)
    if (o1 > 0.0) != (o2 > 0.0) and (o3 > 0.0) != (o4 > 0.0):
        return True
    if abs(o1) <= 1e-9 and on_segment(a, c, b):
        return True
    if abs(o2) <= 1e-9 and on_segment(a, d, b):
        return True
    if abs(o3) <= 1e-9 and on_segment(c, a, d):
        return True
    if abs(o4) <= 1e-9 and on_segment(c, b, d):
        return True
    return False


def _point_to_segment_xy_distance_2d(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    px, py = point
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return ((px - sx) ** 2 + (py - sy) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
    nx = sx + t * dx
    ny = sy + t * dy
    return ((px - nx) ** 2 + (py - ny) ** 2) ** 0.5


def _closest_point_on_segment_xyz(
    point: tuple[float, float, float],
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[float, float, float]:
    px, py, pz = [float(value) for value in point]
    sx, sy, sz = [float(value) for value in start]
    ex, ey, ez = [float(value) for value in end]
    dx = ex - sx
    dy = ey - sy
    dz = ez - sz
    length_sq = dx * dx + dy * dy + dz * dz
    if length_sq <= 1.0e-12:
        return (sx, sy, sz)
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy + (pz - sz) * dz) / length_sq))
    return (sx + t * dx, sy + t * dy, sz + t * dz)


def _line_shape_from_segment(segment: tuple[float, float, float, float, float, float]):
    return _line_shape_from_points((segment[0], segment[1], segment[2]), (segment[3], segment[4], segment[5]))


def _line_shape_from_points(start: tuple[float, float, float], end: tuple[float, float, float]):
    if Part is None or App is None:
        return None
    try:
        return Part.makeLine(App.Vector(*start), App.Vector(*end))
    except Exception:
        return None


def _segment_midpoint(segment: tuple[float, float, float, float, float, float]) -> tuple[float, float, float]:
    return (
        (float(segment[0]) + float(segment[3])) * 0.5,
        (float(segment[1]) + float(segment[4])) * 0.5,
        (float(segment[2]) + float(segment[5])) * 0.5,
    )


def _set_object_property(obj, property_type: str, name: str, group: str, value) -> None:
    if obj is None:
        return
    if not hasattr(obj, name):
        try:
            obj.addProperty(property_type, name, group, name)
        except Exception:
            pass
    try:
        setattr(obj, name, value)
    except Exception:
        pass


def _terrain_context_ready(document) -> bool:
    project = find_project(document)
    terrain = getattr(project, "Terrain", None) if project is not None else None
    if terrain is not None and _terrain_object_has_geometry(terrain):
        return True
    design_terrain = getattr(project, "DesignTerrain", None) if project is not None else None
    if design_terrain is not None and _terrain_object_has_geometry(design_terrain):
        return True
    if document is None:
        return False
    for obj in list(getattr(document, "Objects", []) or []):
        record_kind = str(getattr(obj, "CRRecordKind", "") or "")
        proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
        name = str(getattr(obj, "Name", "") or "")
        if record_kind in {"v1_surface_model", "surface_model"} or proxy_type in {"DesignTerrain", "V1SurfaceModel", "SurfaceModel"} or name.startswith(("DesignTerrain", "V1SurfaceModel", "SurfaceModel")):
            if _terrain_object_has_geometry(obj) or record_kind in {"v1_surface_model", "surface_model"}:
                return True
    return False


def _terrain_context_bound_box_tuple(document) -> tuple[float, float, float, float, float, float] | None:
    project = find_project(document)
    for obj in [getattr(project, "Terrain", None), getattr(project, "DesignTerrain", None)] if project is not None else []:
        bbox = _terrain_object_bound_box_tuple(obj)
        if bbox is not None:
            return bbox
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        record_kind = str(getattr(obj, "CRRecordKind", "") or "")
        proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
        name = str(getattr(obj, "Name", "") or "")
        if record_kind in {"v1_surface_model", "surface_model", "tin_surface_result"} or proxy_type in {"DesignTerrain", "V1SurfaceModel", "SurfaceModel"} or name.startswith(("DesignTerrain", "V1SurfaceModel", "SurfaceModel")):
            bbox = _terrain_object_bound_box_tuple(obj)
            if bbox is not None:
                return bbox
    return None


def _terrain_context_ref(document) -> str:
    project = find_project(document)
    for obj in [getattr(project, "Terrain", None), getattr(project, "DesignTerrain", None)] if project is not None else []:
        if obj is not None and _terrain_object_has_geometry(obj):
            return str(getattr(obj, "Name", "") or getattr(obj, "Label", "") or "")
    if document is None:
        return ""
    for obj in list(getattr(document, "Objects", []) or []):
        record_kind = str(getattr(obj, "CRRecordKind", "") or "")
        proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
        name = str(getattr(obj, "Name", "") or "")
        if record_kind in {"v1_surface_model", "surface_model", "tin_surface_result"} or proxy_type in {"DesignTerrain", "V1SurfaceModel", "SurfaceModel"} or name.startswith(("DesignTerrain", "V1SurfaceModel", "SurfaceModel")):
            if _terrain_object_has_geometry(obj):
                return name or str(getattr(obj, "Label", "") or "")
    for obj in list(getattr(document, "Objects", []) or []):
        record_kind = str(getattr(obj, "CRRecordKind", "") or "")
        proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
        name = str(getattr(obj, "Name", "") or "")
        if record_kind in {"v1_surface_model", "surface_model", "tin_surface_result"} or proxy_type in {"DesignTerrain", "V1SurfaceModel", "SurfaceModel"} or name.startswith(("DesignTerrain", "V1SurfaceModel", "SurfaceModel")):
            return name or str(getattr(obj, "Label", "") or "")
    return ""


def _terrain_object_bound_box_tuple(obj) -> tuple[float, float, float, float, float, float] | None:
    if obj is None:
        return None
    shape_bbox = _shape_bound_box_tuple(getattr(obj, "Shape", None))
    if shape_bbox is not None:
        return shape_bbox
    return _shape_bound_box_tuple(getattr(obj, "Mesh", None))


def _terrain_object_has_geometry(obj) -> bool:
    shape = getattr(obj, "Shape", None)
    if shape is not None and (_shape_count(shape, "Faces") > 0 or _shape_count(shape, "Solids") > 0):
        return True
    mesh = getattr(obj, "Mesh", None)
    if mesh is not None:
        try:
            return int(getattr(mesh, "CountFacets", 0) or 0) > 0
        except Exception:
            return True
    return False


def _validation_status_text(state: WatertightSolidTargetPanelState) -> str:
    status = str(getattr(state, "validation_status", "") or "not_validated")
    if status == "ok":
        return "ok"
    if status == "error":
        return "error"
    if status == "blocked":
        return "blocked"
    return "not_validated"


def _build_status_text(state: WatertightSolidTargetPanelState) -> str:
    status = str(getattr(state, "build_status", "") or "not_built")
    if status in {"built", "error", "blocked"}:
        return status
    return "not_built"


def _ordered_build_states(states: list[WatertightSolidTargetPanelState]) -> list[WatertightSolidTargetPanelState]:
    return sorted(states, key=lambda state: (_build_order_rank(state.target_row), state.target_id))


def _build_order_rank(row: object) -> int:
    family = str(getattr(row, "target_family", "") or "").strip().lower()
    if family == "structure_body":
        return 0
    if family == "drainage_pipeline_network_body":
        return 3
    if family == "drainage_pipeline_body":
        return 2
    return 1


def _count_text(value: int) -> str:
    count = int(value or 0)
    return str(count) if count > 0 else "-"


def _volume_text(value: float) -> str:
    volume = float(value or 0.0)
    return f"{volume:.6g}" if volume > 0.0 else "-"


def _validation_diagnostic_text(profile_set: object, edge_network: object) -> str:
    diagnostics = [
        *list(getattr(profile_set, "diagnostic_rows", []) or []),
        *list(getattr(edge_network, "diagnostic_rows", []) or []),
    ]
    if not diagnostics:
        return "Topology validation passed."
    messages: list[str] = []
    for row in diagnostics[:4]:
        severity = _diagnostic_severity(row)
        kind = str(getattr(row, "kind", "") or "").strip()
        message = str(getattr(row, "message", "") or "").strip()
        if kind and message:
            messages.append(f"{severity}:{kind}: {message}")
        elif message:
            messages.append(f"{severity}: {message}")
        elif kind:
            messages.append(f"{severity}:{kind}")
    remaining = len(diagnostics) - len(messages)
    if remaining > 0:
        messages.append(f"+{remaining} more diagnostics")
    return "; ".join(messages)


def _build_diagnostic_text(existing_message: str, part_result: object) -> str:
    diagnostics = list(getattr(part_result, "diagnostic_rows", []) or [])
    part_status = str(getattr(part_result, "validation_status", "") or "")
    if not diagnostics and part_status == "ok":
        return "Solid build passed."
    messages = [str(existing_message or "").strip()] if str(existing_message or "").strip() else []
    for row in diagnostics[:4]:
        severity = _diagnostic_severity(row)
        kind = str(getattr(row, "kind", "") or "").strip()
        message = str(getattr(row, "message", "") or "").strip()
        if kind and message:
            messages.append(f"{severity}:{kind}: {message}")
        elif message:
            messages.append(f"{severity}: {message}")
        elif kind:
            messages.append(f"{severity}:{kind}")
    remaining = len(diagnostics) - min(len(diagnostics), 4)
    if remaining > 0:
        messages.append(f"+{remaining} more build diagnostics")
    return "; ".join(value for value in messages if value)


def _diagnostic_severity(row: object) -> str:
    return str(getattr(row, "severity", "") or "").strip().lower()


def _solid_output_object_name(target_id: str) -> str:
    return f"V1WatertightSolidOutput_{_safe_object_id(target_id)}"


def _safe_object_id(value: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(value or "").strip())
    safe = "_".join(part for part in safe.split("_") if part)
    return safe or "target"


def _unique_refs(values) -> list[str]:
    refs: list[str] = []
    for value in list(values or []):
        text = str(value or "").strip()
        if text and text not in refs:
            refs.append(text)
    return refs


def _set_object_visibility(obj, visible: bool) -> bool:
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return False
    try:
        vobj.Visibility = bool(visible)
        return True
    except Exception:
        return False


def _focus_document_object(obj) -> bool:
    if obj is None or Gui is None:
        return False
    try:
        selection = getattr(Gui, "Selection", None)
        if selection is not None:
            try:
                selection.clearSelection()
            except Exception:
                pass
            try:
                selection.addSelection(obj)
            except Exception:
                try:
                    selection.addSelection(str(getattr(getattr(obj, "Document", None), "Name", "") or ""), str(getattr(obj, "Name", "") or ""))
                except Exception:
                    pass
        active_doc = getattr(Gui, "ActiveDocument", None)
        view = getattr(active_doc, "ActiveView", None)
        if view is not None and hasattr(view, "fitSelection"):
            view.fitSelection()
            return True
        if hasattr(Gui, "SendMsgToActiveView"):
            Gui.SendMsgToActiveView("ViewSelection")
            return True
    except Exception:
        return False
    return False


def _stretch_last_column(table) -> None:
    try:
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
    except Exception:
        pass


def _qt_item_is_user_checkable():
    return _qt_item_flag("ItemIsUserCheckable")


def _qt_item_is_editable():
    return _qt_item_flag("ItemIsEditable")


def _qt_user_role():
    return _qt_data_role("UserRole")


def _qt_checked_state(value: bool):
    return _qt_check_state("Checked" if value else "Unchecked")


def _qt_item_flag(name: str):
    item_flag = getattr(QtCore.Qt, "ItemFlag", None)
    if item_flag is not None and hasattr(item_flag, name):
        return getattr(item_flag, name)
    return getattr(QtCore.Qt, name)


def _qt_data_role(name: str):
    item_data_role = getattr(QtCore.Qt, "ItemDataRole", None)
    if item_data_role is not None and hasattr(item_data_role, name):
        return getattr(item_data_role, name)
    return getattr(QtCore.Qt, name)


def _qt_check_state(name: str):
    check_state = getattr(QtCore.Qt, "CheckState", None)
    if check_state is not None and hasattr(check_state, name):
        return getattr(check_state, name)
    return getattr(QtCore.Qt, name)


def _close_dialog() -> None:
    if Gui is None:
        return
    try:
        Gui.Control.closeDialog()
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand(WATERTIGHT_SOLIDS_COMMAND_ID, CmdV1WatertightSolids())

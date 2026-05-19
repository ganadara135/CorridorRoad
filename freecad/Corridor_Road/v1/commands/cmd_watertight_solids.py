"""Watertight Solids final-stage command for CorridorRoad v1."""

from __future__ import annotations

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
from ..objects.obj_region import find_v1_region_model, to_region_model
from ..objects.obj_structure import find_v1_structure_model, to_structure_model
from ..objects.obj_surface import find_v1_surface_model
from ..objects.obj_watertight_solid import create_or_update_v1_watertight_solid_output_object
from ..objects.obj_simulation_qa import create_or_update_v1_simulation_qa_output_object
from ..objects.obj_simulation_package import create_or_update_v1_simulation_package_output_object, find_v1_simulation_package_output
from ..exchange import export_simulation_package_to_json
from ..models.output.watertight_solid_output import WatertightSolidOutput, WatertightSolidOutputRow, WatertightSolidSegmentRow
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
    ready: bool = False
    messages: tuple[str, ...] = ()

    def table_rows(self) -> list[tuple[str, str, str]]:
        """Return display rows for the prerequisite table."""

        return [
            ("Document", _ready_label(self.document_ready), "Open FreeCAD document."),
            ("Applied Sections", _ready_label(self.applied_sections_ready), "Generate Applied Sections."),
            ("CorridorModel", _ready_label(self.corridor_model_ready), "Run Build Corridor."),
            ("SurfaceModel", _ready_label(self.surface_model_ready), "Build Corridor surface result."),
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
    notes: str = ""


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
    messages: list[str] = []
    if not applied_ready:
        messages.append("Generate Applied Sections before Watertight Solids.")
    if not corridor_ready:
        messages.append("Run Build Corridor to create a CorridorModel.")
    if not surface_ready:
        messages.append("Run Build Corridor to create a SurfaceModel.")
    ready = bool(applied_ready and corridor_ready and surface_ready)
    if ready:
        messages.append("Build Corridor prerequisites are ready. Solid target discovery is available.")
    else:
        messages.insert(0, WATERTIGHT_SOLIDS_BLOCKED_MESSAGE)
    return WatertightSolidPrerequisiteStatus(
        document_ready=True,
        applied_sections_ready=applied_ready,
        corridor_model_ready=corridor_ready,
        surface_model_ready=surface_ready,
        ready=ready,
        messages=tuple(messages),
    )


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
    structure_obj = find_v1_structure_model(doc)
    drainage_obj = find_v1_drainage_model(doc)
    applied = to_applied_section_set(applied_obj)
    corridor = to_corridor_model(corridor_obj)
    region_model = to_region_model(region_obj)
    structure_model = to_structure_model(structure_obj)
    drainage_model = to_drainage_model(drainage_obj)
    return SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id=str(getattr(applied, "project_id", "") or getattr(corridor, "project_id", "") or "corridorroad-v1"),
            corridor_ref=str(getattr(corridor, "corridor_id", "") or "corridor:main"),
            applied_section_set=applied,
            corridor_model=corridor,
            region_model=region_model,
            structure_model=structure_model,
            drainage_model=drainage_model,
        )
    )


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
            "Pixmap": icon_path("corridor.svg"),
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
    region_ref = str(getattr(row, "region_ref", "") or "").strip()
    structure_ref = str(getattr(row, "structure_ref", "") or "").strip()
    drainage_ref = str(getattr(row, "drainage_ref", "") or "").strip()
    if family == "road_body_envelope":
        return "Road Body Envelope"
    if family == "region_body":
        return f"Region Body - {region_ref}" if region_ref else "Region Body"
    if family == "pavement_layer_body":
        return f"Pavement Layer - {component_ref}" if component_ref else "Pavement Layer"
    if family == "subbase_body":
        return f"Subbase - {component_ref}" if component_ref else "Subbase"
    if family == "shoulder_body":
        return f"Shoulder - {component_ref}" if component_ref else "Shoulder"
    if family == "lined_ditch_body":
        return f"Lined Ditch - {drainage_ref or component_ref}" if drainage_ref or component_ref else "Lined Ditch"
    if family == "drainage_pipeline_body":
        flow_route_ref = str(getattr(row, "flow_route_ref", "") or "").strip()
        return f"Drainage Pipeline - {flow_route_ref or drainage_ref}" if flow_route_ref or drainage_ref else "Drainage Pipeline"
    if family == "drainage_pipeline_network_body":
        return f"Drainage Pipeline Network - {drainage_ref}" if drainage_ref else "Drainage Pipeline Network"
    if family == "structure_body":
        return f"Structure Body - {structure_ref}" if structure_ref else "Structure Body"
    return str(getattr(row, "target_family", "") or _target_id(row))


def _target_family_label(row: object) -> str:
    family = str(getattr(row, "target_family", "") or "").strip().lower()
    if family in {"road_body_envelope", "region_body"}:
        return "Envelope"
    if family in {"pavement_layer_body", "subbase_body", "shoulder_body"}:
        return "Assembly Component"
    if family in {"lined_ditch_body", "drainage_pipeline_body", "drainage_pipeline_network_body"}:
        return "Drainage"
    if family in {"structure_body"}:
        return "Structure"
    return family or "-"


def _target_scope_text(row: object) -> str:
    scope = str(getattr(row, "scope_kind", "") or "")
    region_ref = str(getattr(row, "region_ref", "") or "")
    station_start = float(getattr(row, "station_start", 0.0) or 0.0)
    station_end = float(getattr(row, "station_end", 0.0) or 0.0)
    if region_ref:
        return f"{region_ref} | STA {station_start:.3f}-{station_end:.3f}"
    if scope:
        return f"{scope} | STA {station_start:.3f}-{station_end:.3f}"
    return f"STA {station_start:.3f}-{station_end:.3f}"


def _target_source_text(row: object) -> str:
    values = [
        str(getattr(row, "assembly_ref", "") or ""),
        str(getattr(row, "structure_ref", "") or ""),
        str(getattr(row, "drainage_ref", "") or ""),
        str(getattr(row, "component_ref", "") or ""),
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
    if component_ref:
        values.append(f"component={component_ref}")
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
            notes=(
                f"shape_count=1;pipe_count={len(pipe_shapes)};"
                f"connector_count={len(connector_shapes)};port_connector_count={len(port_connector_shapes)};"
                f"endpoint_trim_count={endpoint_trim_count};structure_body_count={len(valid_structure_shapes)}"
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
            notes=(
                f"shape_count={len(shapes)};pipe_count={len(pipe_shapes)};"
                f"connector_count={len(connector_shapes)};port_connector_count={len(port_connector_shapes)};"
                f"endpoint_trim_count={endpoint_trim_count};structure_body_count={len(valid_structure_shapes)};fallback=no"
            ),
        )
    return DrainagePipelineNetworkShapeResult(
        shape=Part.Compound(shapes),
        fuse_mode="compound_fallback",
        connector_count=len(connector_shapes),
        structure_body_count=len(valid_structure_shapes),
        port_connector_count=len(port_connector_shapes),
        endpoint_trim_count=endpoint_trim_count,
        notes=(
            f"shape_count={len(shapes)};pipe_count={len(pipe_shapes)};"
            f"connector_count={len(connector_shapes)};port_connector_count={len(port_connector_shapes)};"
            f"endpoint_trim_count={endpoint_trim_count};structure_body_count={len(valid_structure_shapes)};fallback=yes"
        ),
    )


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
        )
    )


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

"""Watertight Solids final-stage command for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from ..objects.obj_applied_section import find_v1_applied_section_set
from ..objects.obj_applied_section import to_applied_section_set
from ..objects.obj_corridor import find_v1_corridor_model, to_corridor_model
from ..objects.obj_drainage import find_v1_drainage_model, to_drainage_model
from ..objects.obj_region import find_v1_region_model, to_region_model
from ..objects.obj_structure import find_v1_structure_model, to_structure_model
from ..objects.obj_surface import find_v1_surface_model
from ..objects.obj_watertight_solid import create_or_update_v1_watertight_solid_output_object
from ..services.builders import (
    AppliedSectionSolidProfileService,
    SolidEdgeNetworkBuildRequest,
    SolidEdgeNetworkService,
    SolidProfileBuildRequest,
    SolidTargetDiscoveryRequest,
    SolidTargetDiscoveryService,
)
from ..services.mapping import (
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

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setMinimumHeight(92)
        self._status.setPlainText(self._status_text())
        layout.addWidget(self._status)

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
        self._show_button = QtWidgets.QPushButton("Show Solid")
        self._show_button.setEnabled(False)
        self._show_button.setToolTip("Show the selected built solid output.")
        self._show_button.clicked.connect(self._show_selected_solid)
        button_row.addWidget(self._show_button)
        self._hide_button = QtWidgets.QPushButton("Hide Solid")
        self._hide_button.setEnabled(False)
        self._hide_button.setToolTip("Hide the selected built solid output.")
        self._hide_button.clicked.connect(self._hide_selected_solid)
        button_row.addWidget(self._hide_button)
        self._focus_button = QtWidgets.QPushButton("Focus Solid")
        self._focus_button.setEnabled(False)
        self._focus_button.setToolTip("Select and focus the selected built solid output.")
        self._focus_button.clicked.connect(self._focus_selected_solid)
        button_row.addWidget(self._focus_button)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(_close_dialog)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        self._update_action_state()
        return widget

    def _refresh(self) -> None:
        self._status_model = watertight_solid_prerequisite_status(self.document)
        self._target_model = discover_watertight_solid_targets(self.document)
        self._set_prerequisite_rows(self._status_model)
        self._set_target_rows(list(getattr(self._target_model, "target_rows", []) or []))
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

    def _build_selected_target(self) -> None:
        selected_state = self._selected_target_state()
        if selected_state is None:
            return
        self._build_target_state(selected_state)

    def _build_target_state(self, selected_state: WatertightSolidTargetPanelState) -> bool:
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

    def _build_enabled_targets(self) -> None:
        states = self._enabled_available_target_states()
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
        self._update_action_state()
        self._status.setPlainText(
            self._status_text()
            + f"\n\nBuild Enabled summary: built={built_count}; failed={failed_count}; targets={len(states)}; volume={_volume_text(total_volume)}"
        )

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
    if family == "structure_body":
        return f"Structure Body - {structure_ref}" if structure_ref else "Structure Body"
    return str(getattr(row, "target_family", "") or _target_id(row))


def _target_family_label(row: object) -> str:
    family = str(getattr(row, "target_family", "") or "").strip().lower()
    if family in {"road_body_envelope", "region_body"}:
        return "Envelope"
    if family in {"pavement_layer_body", "subbase_body", "shoulder_body"}:
        return "Assembly Component"
    if family in {"lined_ditch_body"}:
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

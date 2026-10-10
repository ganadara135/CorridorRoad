"""Project Setup editor presentation for CorridorRoad v1."""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtWidgets

from ...services.editing.project_setup_service import (
    COORDINATE_WORKFLOWS,
    CRS_PRESETS,
    MIN_TIN_MAX_TRIANGLES,
    SETUP_STATUS_CHOICES,
    ProjectSetupDraft,
    coordinate_workflow_note,
    crs_preset_note,
    locked_field_labels,
    recommended_coordinate_workflow,
    unit_policy_note,
    uses_custom_linear_unit,
)
from ....objects import design_standards as _standards
from ....objects import unit_policy as _units


def configure_project_setup_task_panel_runtime(bindings) -> None:
    """Bind command/controller collaborators without importing the command module."""

    protected = {
        "V1ProjectSetupTaskPanel",
        "configure_project_setup_task_panel_runtime",
    }
    for name, value in dict(bindings or {}).items():
        if name.startswith("__") or name in protected:
            continue
        globals()[name] = value


# Explicit runtime collaborators are replaced by the command callback map.
Gui = None
apply_v1_project_setup = None
list_corridorroad_projects = None
project_setup_draft_from_project = None


class V1ProjectSetupTaskPanel:
    """Edit one CorridorRoadProject's units, design standard, CRS and origin. Writes only on Apply."""

    def __init__(self, *, document=None, preferred_project=None):
        self.document = document
        self.preferred_project = preferred_project
        self._projects = []
        self._loading = False
        self.form = self._build_ui()
        self._refresh_context(preferred=preferred_project)

    def getStandardButtons(self):
        return 0

    def accept(self):
        self._close()

    def reject(self):
        self._close()

    def _close(self):
        if Gui is not None and hasattr(Gui, "Control"):
            Gui.Control.closeDialog()

    def _build_ui(self):
        w = QtWidgets.QWidget()
        w.setWindowTitle("ParametricRoad - Project Setup")

        root = QtWidgets.QVBoxLayout(w)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        root.addWidget(self.lbl_info)

        gb_src = QtWidgets.QGroupBox("Project")
        fs = QtWidgets.QFormLayout(gb_src)
        self.cmb_project = QtWidgets.QComboBox()
        self.cmb_design_standard = QtWidgets.QComboBox()
        self.cmb_design_standard.addItems(list(_standards.SUPPORTED_STANDARDS))
        self.cmb_linear_display = QtWidgets.QComboBox()
        self.cmb_linear_display.addItems(list(_units.DISPLAY_LINEAR_UNITS))
        self.cmb_linear_import = QtWidgets.QComboBox()
        self.cmb_linear_import.addItems(list(_units.LINEAR_UNITS))
        self.cmb_linear_export = QtWidgets.QComboBox()
        self.cmb_linear_export.addItems(list(_units.LINEAR_UNITS))
        self.sp_custom_linear_scale = QtWidgets.QDoubleSpinBox()
        self.sp_custom_linear_scale.setRange(1e-9, 1.0e9)
        self.sp_custom_linear_scale.setDecimals(9)
        self.sp_custom_linear_scale.setValue(1.0)
        self.sp_tin_max_triangles = QtWidgets.QSpinBox()
        self.sp_tin_max_triangles.setRange(MIN_TIN_MAX_TRIANGLES, 10000000)
        self.sp_tin_max_triangles.setSingleStep(10000)
        self.sp_tin_max_triangles.setValue(250000)
        self.sp_tin_max_triangles.setSuffix(" triangles")
        self.lbl_unit_policy_info = QtWidgets.QLabel("")
        self.lbl_unit_policy_info.setWordWrap(True)
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fs.addRow("Target Project:", self.cmb_project)
        fs.addRow("Design Standard:", self.cmb_design_standard)
        fs.addRow("Display Unit:", self.cmb_linear_display)
        fs.addRow("Default Import Unit:", self.cmb_linear_import)
        fs.addRow("Default Export Unit:", self.cmb_linear_export)
        fs.addRow("Custom Unit Scale:", self.sp_custom_linear_scale)
        fs.addRow("TIN Conversion Limit:", self.sp_tin_max_triangles)
        fs.addRow("", self.lbl_unit_policy_info)
        fs.addRow(self.btn_refresh)
        root.addWidget(gb_src)

        gb_coord = QtWidgets.QGroupBox("Coordinate System")
        fc = QtWidgets.QFormLayout(gb_coord)
        self.cmb_epsg = QtWidgets.QComboBox()
        self.cmb_epsg.setEditable(True)
        self.cmb_epsg.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.cmb_epsg.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_epsg.setMinimumContentsLength(24)
        for label, code, description in CRS_PRESETS:
            self.cmb_epsg.addItem(label or "[Custom / Blank]", {"code": code, "desc": description})
        line_edit = self.cmb_epsg.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("Select a preset or type e.g. EPSG:5186")
        self.lbl_epsg_info = QtWidgets.QLabel("")
        self.lbl_epsg_info.setWordWrap(True)
        self.cmb_coord_workflow = QtWidgets.QComboBox()
        self.cmb_coord_workflow.addItems(list(COORDINATE_WORKFLOWS))
        self.chk_auto_coord_reco = QtWidgets.QCheckBox("Auto-apply recommended modes in task panels")
        self.chk_auto_coord_reco.setChecked(True)
        self.lbl_coord_workflow_info = QtWidgets.QLabel("")
        self.lbl_coord_workflow_info.setWordWrap(True)
        self.ed_h_datum = QtWidgets.QLineEdit()
        self.ed_h_datum.setPlaceholderText("Horizontal datum (optional)")
        self.ed_v_datum = QtWidgets.QLineEdit()
        self.ed_v_datum.setPlaceholderText("Vertical datum (optional)")

        self.sp_e = QtWidgets.QDoubleSpinBox()
        self.sp_n = QtWidgets.QDoubleSpinBox()
        self.sp_z = QtWidgets.QDoubleSpinBox()
        self.sp_lx = QtWidgets.QDoubleSpinBox()
        self.sp_ly = QtWidgets.QDoubleSpinBox()
        self.sp_lz = QtWidgets.QDoubleSpinBox()
        for spin in (self.sp_e, self.sp_n, self.sp_z, self.sp_lx, self.sp_ly, self.sp_lz):
            spin.setRange(-1.0e12, 1.0e12)
            spin.setDecimals(3)
            spin.setValue(0.0)

        self.sp_rot = QtWidgets.QDoubleSpinBox()
        self.sp_rot.setRange(-3600.0, 3600.0)
        self.sp_rot.setDecimals(6)
        self.sp_rot.setValue(0.0)
        self.sp_rot.setSuffix(" deg")

        self.chk_locked = QtWidgets.QCheckBox("Lock coordinate setup")
        self.chk_locked.setChecked(False)

        self.cmb_status = QtWidgets.QComboBox()
        self.cmb_status.setEditable(True)
        self.cmb_status.addItems(list(SETUP_STATUS_CHOICES))
        self.cmb_status.setCurrentText("Uninitialized")

        fc.addRow("CRS / EPSG:", self.cmb_epsg)
        fc.addRow("", self.lbl_epsg_info)
        fc.addRow("Coordinate Workflow:", self.cmb_coord_workflow)
        fc.addRow("", self.lbl_coord_workflow_info)
        fc.addRow(self.chk_auto_coord_reco)
        fc.addRow("Horizontal Datum:", self.ed_h_datum)
        fc.addRow("Vertical Datum:", self.ed_v_datum)
        fc.addRow("Project Origin E:", self.sp_e)
        fc.addRow("Project Origin N:", self.sp_n)
        fc.addRow("Project Origin Z:", self.sp_z)
        fc.addRow("Local Origin X:", self.sp_lx)
        fc.addRow("Local Origin Y:", self.sp_ly)
        fc.addRow("Local Origin Z:", self.sp_lz)
        fc.addRow("North Rotation:", self.sp_rot)
        fc.addRow(self.chk_locked)
        fc.addRow("Setup Status:", self.cmb_status)
        root.addWidget(gb_coord)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Apply Setup")
        self.btn_close = QtWidgets.QPushButton("Close")
        row_btn.addWidget(self.btn_apply)
        row_btn.addWidget(self.btn_close)
        root.addLayout(row_btn)

        self.lbl_result = QtWidgets.QLabel("Idle")
        self.lbl_result.setWordWrap(True)
        root.addWidget(self.lbl_result)

        self.btn_refresh.clicked.connect(self._on_refresh)
        self.cmb_project.currentIndexChanged.connect(self._on_project_changed)
        self.cmb_linear_display.currentIndexChanged.connect(self._on_linear_unit_changed)
        self.cmb_linear_import.currentIndexChanged.connect(self._on_linear_unit_changed)
        self.cmb_linear_export.currentIndexChanged.connect(self._on_linear_unit_changed)
        self.sp_custom_linear_scale.valueChanged.connect(self._on_linear_unit_changed)
        self.cmb_epsg.currentIndexChanged.connect(self._on_epsg_changed)
        self.cmb_epsg.editTextChanged.connect(self._on_epsg_changed)
        self.cmb_coord_workflow.currentIndexChanged.connect(self._on_coord_workflow_changed)
        self.chk_auto_coord_reco.toggled.connect(self._on_coord_workflow_changed)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_close.clicked.connect(self.reject)
        return w

    # Draft <-> widgets

    def _draft_from_widgets(self) -> ProjectSetupDraft:
        return ProjectSetupDraft(
            design_standard=self.cmb_design_standard.currentText(),
            linear_unit_display=self.cmb_linear_display.currentText(),
            linear_unit_import=self.cmb_linear_import.currentText(),
            linear_unit_export=self.cmb_linear_export.currentText(),
            custom_linear_unit_scale=float(self.sp_custom_linear_scale.value()),
            tin_max_triangles=int(self.sp_tin_max_triangles.value()),
            crs_epsg=self._current_epsg_value(),
            coordinate_workflow=self.cmb_coord_workflow.currentText(),
            auto_apply_coordinate_recommendations=bool(self.chk_auto_coord_reco.isChecked()),
            horizontal_datum=self.ed_h_datum.text(),
            vertical_datum=self.ed_v_datum.text(),
            project_origin_e=float(self.sp_e.value()),
            project_origin_n=float(self.sp_n.value()),
            project_origin_z=float(self.sp_z.value()),
            local_origin_x=float(self.sp_lx.value()),
            local_origin_y=float(self.sp_ly.value()),
            local_origin_z=float(self.sp_lz.value()),
            north_rotation_deg=float(self.sp_rot.value()),
            coord_setup_locked=bool(self.chk_locked.isChecked()),
            coord_setup_status=self.cmb_status.currentText(),
        )

    def _show_draft(self, draft: ProjectSetupDraft) -> None:
        self._loading = True
        try:
            self._set_epsg_value(draft.crs_epsg)
            self.cmb_design_standard.setCurrentText(
                _standards.normalize_standard(draft.design_standard, default=_standards.DEFAULT_STANDARD)
            )
            _set_combo_text(self.cmb_linear_display, draft.linear_unit_display)
            _set_combo_text(self.cmb_linear_import, draft.linear_unit_import)
            _set_combo_text(self.cmb_linear_export, draft.linear_unit_export)
            self.sp_custom_linear_scale.setValue(float(draft.custom_linear_unit_scale))
            self.sp_tin_max_triangles.setValue(int(draft.tin_max_triangles))
            self.cmb_coord_workflow.setCurrentText(draft.coordinate_workflow)
            self.chk_auto_coord_reco.setChecked(bool(draft.auto_apply_coordinate_recommendations))
            self.ed_h_datum.setText(draft.horizontal_datum)
            self.ed_v_datum.setText(draft.vertical_datum)
            self.sp_e.setValue(float(draft.project_origin_e))
            self.sp_n.setValue(float(draft.project_origin_n))
            self.sp_z.setValue(float(draft.project_origin_z))
            self.sp_lx.setValue(float(draft.local_origin_x))
            self.sp_ly.setValue(float(draft.local_origin_y))
            self.sp_lz.setValue(float(draft.local_origin_z))
            self.sp_rot.setValue(float(draft.north_rotation_deg))
            self.chk_locked.setChecked(bool(draft.coord_setup_locked))
            self.cmb_status.setCurrentText(draft.coord_setup_status)
        finally:
            self._loading = False
        # Show the stored workflow as stored: a CRS recommends a workflow only when the user edits it.
        self._update_epsg_info(follow_recommendation=False)
        self._update_unit_policy_info()

    # CRS combo: preset rows carry their code; anything else is typed text.

    def _current_epsg_value(self) -> str:
        text = str(self.cmb_epsg.currentText() or "").strip()
        index = int(self.cmb_epsg.currentIndex())
        if 0 <= index < self.cmb_epsg.count():
            data = self.cmb_epsg.itemData(index)
            if isinstance(data, dict):
                code = str(data.get("code", "") or "").strip()
                if code and text == str(self.cmb_epsg.itemText(index) or "").strip():
                    return code
        return text

    def _set_epsg_value(self, value: str) -> None:
        code = str(value or "").strip()
        for index in range(self.cmb_epsg.count()):
            data = self.cmb_epsg.itemData(index)
            if isinstance(data, dict) and code and str(data.get("code", "") or "").strip() == code:
                self.cmb_epsg.setCurrentIndex(index)
                return
        self.cmb_epsg.setCurrentIndex(0)
        self.cmb_epsg.setEditText(code)

    # Help text

    def _update_unit_policy_info(self) -> None:
        draft = self._draft_from_widgets()
        uses_custom = uses_custom_linear_unit(draft)
        self.sp_custom_linear_scale.setEnabled(uses_custom)
        self.sp_custom_linear_scale.setSuffix(" meter(s) / custom-unit" if uses_custom else "")
        self.lbl_unit_policy_info.setText(unit_policy_note(draft))

    def _update_epsg_info(self, *, follow_recommendation: bool = True) -> None:
        epsg = self._current_epsg_value()
        self.lbl_epsg_info.setText(crs_preset_note(epsg))
        if follow_recommendation and self.cmb_coord_workflow.currentText() != "Custom":
            # Follow the CRS until the user picks Custom; this only changes the widget, not the project.
            self._loading = True
            try:
                self.cmb_coord_workflow.setCurrentText(recommended_coordinate_workflow(epsg))
            finally:
                self._loading = False
        self._update_coord_workflow_info()

    def _update_coord_workflow_info(self) -> None:
        workflow = str(self.cmb_coord_workflow.currentText() or "").strip()
        workflow = workflow or recommended_coordinate_workflow(self._current_epsg_value())
        self.lbl_coord_workflow_info.setText(
            coordinate_workflow_note(workflow, auto_apply=bool(self.chk_auto_coord_reco.isChecked()))
        )

    def _on_epsg_changed(self, *_args) -> None:
        if not self._loading:
            self._update_epsg_info()

    def _on_coord_workflow_changed(self, *_args) -> None:
        if not self._loading:
            self._update_coord_workflow_info()

    def _on_linear_unit_changed(self, *_args) -> None:
        if not self._loading:
            self._update_unit_policy_info()

    # Project selection

    def _current_project(self):
        index = int(self.cmb_project.currentIndex())
        if 0 <= index < len(self._projects):
            return self._projects[index]
        return None

    def _refresh_context(self, preferred=None) -> None:
        if self.document is None:
            self._projects = []
            self.cmb_project.clear()
            self.lbl_info.setText("No active document.")
            self.lbl_result.setText("No active document.")
            return
        self._projects = list(list_corridorroad_projects(self.document))
        self._loading = True
        try:
            self.cmb_project.clear()
            for project in self._projects:
                self.cmb_project.addItem(f"{project.Label} ({project.Name})")
            index = self._projects.index(preferred) if preferred in self._projects else (0 if self._projects else -1)
            self.cmb_project.setCurrentIndex(index)
        finally:
            self._loading = False
        if not self._projects:
            self.lbl_info.setText("No CorridorRoadProject found. Run New/Project Setup first.")
            self.lbl_result.setText("No project.")
            return
        self.lbl_info.setText(
            f"CorridorRoadProject: {len(self._projects)} found.\n"
            "Coordinates and linear units are configured separately. Stored geometry stays meter-native."
        )
        self._load_project()

    def _load_project(self) -> None:
        project = self._current_project()
        if project is None:
            return
        self._show_draft(project_setup_draft_from_project(project))
        self.lbl_result.setText("Loaded.")

    def _on_project_changed(self, *_args) -> None:
        if not self._loading:
            self._load_project()

    def _on_refresh(self) -> None:
        self._refresh_context(preferred=self._current_project())

    # Apply

    def _apply(self) -> None:
        project = self._current_project()
        if project is None:
            QtWidgets.QMessageBox.warning(None, "Project Setup", "No CorridorRoadProject selected.")
            return
        try:
            result = apply_v1_project_setup(project, self._draft_from_widgets())
        except Exception as exc:
            self.lbl_result.setText(f"ERROR: {exc}")
            return
        if not result.applied:
            fields = ", ".join(locked_field_labels(result.blocked_fields))
            QtWidgets.QMessageBox.warning(
                None,
                "Project Setup",
                "Coordinate setup is locked.\n"
                f"Changed: {fields}.\n"
                "Uncheck 'Lock coordinate setup' to unlock, then apply again.",
            )
            self.lbl_result.setText(f"Blocked: setup is locked ({fields}).")
            return
        self._show_draft(result.draft)
        self.lbl_result.setText(result.summary)
        QtWidgets.QMessageBox.information(None, "Project Setup", "Project coordinate and unit setup has been applied.")


def _set_combo_text(combo, value: str) -> None:
    index = combo.findText(str(value or "").strip())
    combo.setCurrentIndex(index if index >= 0 else 0)

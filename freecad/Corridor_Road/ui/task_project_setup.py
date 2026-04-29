# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui
from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects import design_standards as _ds
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties


_CRS_PRESETS = [
    ("", "", ""),
    ("WGS 84 (EPSG:4326)", "EPSG:4326", "Global geographic coordinates"),
    ("WGS 84 / Pseudo-Mercator (EPSG:3857)", "EPSG:3857", "Common web map projection"),
    ("WGS 84 / UTM zone 51N (EPSG:32651)", "EPSG:32651", "UTM zone 51N"),
    ("WGS 84 / UTM zone 52N (EPSG:32652)", "EPSG:32652", "UTM zone 52N"),
    ("WGS 84 / UTM zone 53N (EPSG:32653)", "EPSG:32653", "UTM zone 53N"),
    ("Korea 2000 / Central Belt (EPSG:5181)", "EPSG:5181", "Korea local projected CRS"),
    ("Korea 2000 / West Belt 2010 (EPSG:5185)", "EPSG:5185", "Korea local projected CRS"),
    ("Korea 2000 / Central Belt 2010 (EPSG:5186)", "EPSG:5186", "Korea local projected CRS"),
    ("Korea 2000 / East Belt 2010 (EPSG:5187)", "EPSG:5187", "Korea local projected CRS"),
]

_COORD_WORKFLOW_VALUES = ["World-first", "Local-first", "Custom"]


def _find_projects(doc):
    out = []
    if doc is None:
        return out
    for o in doc.Objects:
        if str(getattr(o, "Name", "") or "").startswith("CorridorRoadProject"):
            out.append(o)
    return out


class ProjectSetupTaskPanel:
    def __init__(self, preferred_project=None):
        self.doc = App.ActiveDocument
        self._projects = []
        self._loading = False
        self._preferred = preferred_project
        self.form = self._build_ui()
        self._refresh_context(preferred=preferred_project)

    def getStandardButtons(self):
        return 0

    def accept(self):
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()

    def _build_ui(self):
        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Project Setup")

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
        self.cmb_design_standard.addItems(list(_ds.SUPPORTED_STANDARDS))
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
        self.sp_tin_max_triangles.setRange(1000, 10000000)
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
        for label, code, desc in _CRS_PRESETS:
            text = label or "[Custom / Blank]"
            self.cmb_epsg.addItem(text, {"code": code, "desc": desc})
        try:
            self.cmb_epsg.lineEdit().setPlaceholderText("Select a preset or type e.g. EPSG:5186")
        except Exception:
            pass
        self.lbl_epsg_info = QtWidgets.QLabel("")
        self.lbl_epsg_info.setWordWrap(True)
        self.cmb_coord_workflow = QtWidgets.QComboBox()
        self.cmb_coord_workflow.addItems(_COORD_WORKFLOW_VALUES)
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
        for s in (self.sp_e, self.sp_n, self.sp_z, self.sp_lx, self.sp_ly, self.sp_lz):
            s.setRange(-1.0e12, 1.0e12)
            s.setDecimals(3)
            s.setValue(0.0)

        self.sp_rot = QtWidgets.QDoubleSpinBox()
        self.sp_rot.setRange(-3600.0, 3600.0)
        self.sp_rot.setDecimals(6)
        self.sp_rot.setValue(0.0)
        self.sp_rot.setSuffix(" deg")

        self.chk_locked = QtWidgets.QCheckBox("Lock coordinate setup")
        self.chk_locked.setChecked(False)

        self.cmb_status = QtWidgets.QComboBox()
        self.cmb_status.setEditable(True)
        self.cmb_status.addItems(["Uninitialized", "Initialized", "Validated"])
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
        self.cmb_epsg.currentIndexChanged.connect(self._on_epsg_combo_changed)
        self.cmb_epsg.editTextChanged.connect(self._on_epsg_edit_changed)
        self.cmb_coord_workflow.currentIndexChanged.connect(self._on_coord_workflow_changed)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_close.clicked.connect(self.reject)
        return w

    def _current_linear_display_unit(self) -> str:
        return str(self.cmb_linear_display.currentText() or _units.DEFAULT_LINEAR_UNIT).strip().lower() or _units.DEFAULT_LINEAR_UNIT

    def _current_linear_import_unit(self) -> str:
        return str(self.cmb_linear_import.currentText() or _units.DEFAULT_LINEAR_UNIT).strip().lower() or _units.DEFAULT_LINEAR_UNIT

    def _current_linear_export_unit(self) -> str:
        return str(self.cmb_linear_export.currentText() or _units.DEFAULT_LINEAR_UNIT).strip().lower() or _units.DEFAULT_LINEAR_UNIT

    def _set_combo_text(self, combo, value: str, default_text: str):
        text = str(value or "").strip()
        idx = combo.findText(text)
        if idx < 0:
            idx = combo.findText(str(default_text or "").strip())
        if idx < 0:
            idx = 0
        combo.setCurrentIndex(idx)

    def _update_unit_policy_info(self):
        display_unit = self._current_linear_display_unit()
        import_unit = self._current_linear_import_unit()
        export_unit = self._current_linear_export_unit()
        custom_scale = float(self.sp_custom_linear_scale.value())
        uses_custom = import_unit == "custom" or export_unit == "custom"
        self.sp_custom_linear_scale.setEnabled(uses_custom)
        if uses_custom:
            self.sp_custom_linear_scale.setSuffix(" meter(s) / custom-unit")
        else:
            self.sp_custom_linear_scale.setSuffix("")

        info = (
            "Stored geometry stays in meters. Display Unit controls task-panel/report formatting. "
            "Default Import Unit is used when incoming files or pasted values do not declare a unit. "
            "Default Export Unit controls CSV/report output formatting."
        )
        if uses_custom:
            info += f" Custom conversion uses {custom_scale:.9f} meter(s) per custom unit."
        else:
            info += " Standard project units use built-in meter/millimeter conversions."
        self.lbl_unit_policy_info.setText(info)

    def _recommended_workflow_from_epsg(self, epsg_value: str) -> str:
        return "World-first" if str(epsg_value or "").strip() else "Local-first"

    def _current_epsg_value(self):
        text = str(self.cmb_epsg.currentText() or "").strip()
        idx = int(self.cmb_epsg.currentIndex())
        if 0 <= idx < self.cmb_epsg.count():
            data = self.cmb_epsg.itemData(idx)
            if isinstance(data, dict):
                code = str(data.get("code", "") or "").strip()
                label = str(self.cmb_epsg.itemText(idx) or "").strip()
                if code and text == label:
                    return code
        return text

    def _set_epsg_value(self, value: str):
        code = str(value or "").strip()
        idx = -1
        for i in range(self.cmb_epsg.count()):
            data = self.cmb_epsg.itemData(i)
            if isinstance(data, dict) and str(data.get("code", "") or "").strip() == code:
                idx = i
                break
        if idx >= 0:
            self.cmb_epsg.setCurrentIndex(idx)
        else:
            self.cmb_epsg.setCurrentIndex(0)
            self.cmb_epsg.setEditText(code)
        self._update_epsg_info()

    def _update_epsg_info(self):
        text = self._current_epsg_value()
        idx = int(self.cmb_epsg.currentIndex())
        info = ""
        if 0 <= idx < self.cmb_epsg.count():
            data = self.cmb_epsg.itemData(idx)
            if isinstance(data, dict):
                code = str(data.get("code", "") or "").strip()
                desc = str(data.get("desc", "") or "").strip()
                label = str(self.cmb_epsg.itemText(idx) or "").strip()
                if code and text == code:
                    info = f"Preset selected: {label}"
                    if desc:
                        info += f" - {desc}"
        if not info:
            if text:
                info = f"Custom CRS/EPSG input: {text}"
            else:
                info = "Select a common preset or enter a custom CRS/EPSG code."
        self.lbl_epsg_info.setText(info)
        if not self._loading and self.cmb_coord_workflow.currentText() != "Custom":
            self.cmb_coord_workflow.setCurrentText(self._recommended_workflow_from_epsg(text))
        self._update_coord_workflow_info()

    def _update_coord_workflow_info(self):
        workflow = str(self.cmb_coord_workflow.currentText() or "").strip() or self._recommended_workflow_from_epsg(self._current_epsg_value())
        if workflow == "World-first":
            msg = "Recommended input mode: World coordinates. Terrain and alignment panels will default to World mode."
        elif workflow == "Local-first":
            msg = "Recommended input mode: Local coordinates. Terrain and alignment panels will default to Local mode."
        else:
            msg = "Recommended input mode: Custom. Task panels keep their own coordinate choice unless changed manually."
        if not bool(self.chk_auto_coord_reco.isChecked()):
            msg += " Auto-apply is off, so this is only guidance."
        self.lbl_coord_workflow_info.setText(msg)

    def _on_epsg_combo_changed(self, _idx):
        if self._loading:
            return
        self._update_epsg_info()

    def _on_epsg_edit_changed(self, _text):
        if self._loading:
            return
        self._update_epsg_info()

    def _on_coord_workflow_changed(self, _idx):
        if self._loading:
            return
        self._update_coord_workflow_info()

    def _on_linear_unit_changed(self, *_args):
        if self._loading:
            return
        self._update_unit_policy_info()

    @staticmethod
    def _fmt_project(o):
        return f"{o.Label} ({o.Name})"

    def _current_project(self):
        i = int(self.cmb_project.currentIndex())
        if i < 0 or i >= len(self._projects):
            return None
        return self._projects[i]

    def _refresh_context(self, preferred=None):
        if self.doc is None:
            self._projects = []
            self.cmb_project.clear()
            self.lbl_info.setText("No active document.")
            self.lbl_result.setText("No active document.")
            return

        self._projects = _find_projects(self.doc)
        self._loading = True
        try:
            self.cmb_project.clear()
            for p in self._projects:
                self.cmb_project.addItem(self._fmt_project(p))

            idx = -1
            if preferred is not None:
                for i, p in enumerate(self._projects):
                    if p == preferred:
                        idx = i
                        break
            if idx < 0 and self._projects:
                idx = 0
            self.cmb_project.setCurrentIndex(idx)
        finally:
            self._loading = False

        if not self._projects:
            self.lbl_info.setText("No CorridorRoadProject found. Run New Project first.")
            self.lbl_result.setText("No project.")
            return

        self.lbl_info.setText(
            f"CorridorRoadProject: {len(self._projects)} found.\n"
            "Coordinates and linear units are configured separately. Stored geometry stays meter-native."
        )
        self._load_project()

    def _load_project(self):
        prj = self._current_project()
        if prj is None:
            return
        ensure_project_properties(prj)

        self._loading = True
        try:
            self._set_epsg_value(str(getattr(prj, "CRSEPSG", "") or ""))
            self.cmb_design_standard.setCurrentText(_ds.normalize_standard(getattr(prj, "DesignStandard", _ds.DEFAULT_STANDARD)))
            unit_settings = _units.resolve_project_unit_settings(prj)
            self._set_combo_text(self.cmb_linear_display, str(unit_settings.get("display", "m")), "m")
            self._set_combo_text(self.cmb_linear_import, str(unit_settings.get("import", "m")), "m")
            self._set_combo_text(self.cmb_linear_export, str(unit_settings.get("export", "m")), "m")
            self.sp_custom_linear_scale.setValue(float(unit_settings.get("custom_scale", 1.0)))
            self.sp_tin_max_triangles.setValue(
                max(1000, int(getattr(prj, "TINConversionMaxTriangles", 250000) or 250000))
            )
            workflow = str(getattr(prj, "CoordinateWorkflow", "") or "").strip()
            if workflow not in _COORD_WORKFLOW_VALUES:
                workflow = self._recommended_workflow_from_epsg(str(getattr(prj, "CRSEPSG", "") or ""))
            self.cmb_coord_workflow.setCurrentText(workflow)
            self.chk_auto_coord_reco.setChecked(bool(getattr(prj, "AutoApplyCoordinateRecommendations", True)))
            self.ed_h_datum.setText(str(getattr(prj, "HorizontalDatum", "") or ""))
            self.ed_v_datum.setText(str(getattr(prj, "VerticalDatum", "") or ""))
            self.sp_e.setValue(float(getattr(prj, "ProjectOriginE", 0.0)))
            self.sp_n.setValue(float(getattr(prj, "ProjectOriginN", 0.0)))
            self.sp_z.setValue(float(getattr(prj, "ProjectOriginZ", 0.0)))
            self.sp_lx.setValue(float(getattr(prj, "LocalOriginX", 0.0)))
            self.sp_ly.setValue(float(getattr(prj, "LocalOriginY", 0.0)))
            self.sp_lz.setValue(float(getattr(prj, "LocalOriginZ", 0.0)))
            self.sp_rot.setValue(float(getattr(prj, "NorthRotationDeg", 0.0)))
            self.chk_locked.setChecked(bool(getattr(prj, "CoordSetupLocked", False)))
            self.cmb_status.setCurrentText(str(getattr(prj, "CoordSetupStatus", "Uninitialized") or "Uninitialized"))
        finally:
            self._loading = False

        self._update_epsg_info()
        self._update_coord_workflow_info()
        self._update_unit_policy_info()
        self.lbl_result.setText("Loaded.")

    def _on_project_changed(self):
        if self._loading:
            return
        self._load_project()

    def _on_refresh(self):
        self._refresh_context(preferred=self._current_project())

    @staticmethod
    def _f_eq(a: float, b: float, tol: float = 1e-9):
        return abs(float(a) - float(b)) <= float(tol)

    def _is_locked_change_attempt(self, prj):
        if not bool(getattr(prj, "CoordSetupLocked", False)):
            return False
        if not bool(self.chk_locked.isChecked()):
            return False

        if str(getattr(prj, "CRSEPSG", "") or "") != str(self._current_epsg_value() or ""):
            return True
        if str(getattr(prj, "HorizontalDatum", "") or "") != str(self.ed_h_datum.text() or ""):
            return True
        if str(getattr(prj, "VerticalDatum", "") or "") != str(self.ed_v_datum.text() or ""):
            return True
        if str(getattr(prj, "CoordinateWorkflow", "") or "") != str(self.cmb_coord_workflow.currentText() or ""):
            return True
        if bool(getattr(prj, "AutoApplyCoordinateRecommendations", True)) != bool(self.chk_auto_coord_reco.isChecked()):
            return True
        if not self._f_eq(getattr(prj, "ProjectOriginE", 0.0), self.sp_e.value()):
            return True
        if not self._f_eq(getattr(prj, "ProjectOriginN", 0.0), self.sp_n.value()):
            return True
        if not self._f_eq(getattr(prj, "ProjectOriginZ", 0.0), self.sp_z.value()):
            return True
        if not self._f_eq(getattr(prj, "LocalOriginX", 0.0), self.sp_lx.value()):
            return True
        if not self._f_eq(getattr(prj, "LocalOriginY", 0.0), self.sp_ly.value()):
            return True
        if not self._f_eq(getattr(prj, "LocalOriginZ", 0.0), self.sp_lz.value()):
            return True
        if not self._f_eq(getattr(prj, "NorthRotationDeg", 0.0), self.sp_rot.value()):
            return True
        return False

    def _apply(self):
        prj = self._current_project()
        if prj is None:
            QtWidgets.QMessageBox.warning(None, "Project Setup", "No CorridorRoadProject selected.")
            return

        ensure_project_properties(prj)

        if self._is_locked_change_attempt(prj):
            QtWidgets.QMessageBox.warning(
                None,
                "Project Setup",
                "Coordinate setup is locked.\nUncheck 'Lock coordinate setup' to unlock, then apply again.",
            )
            self.lbl_result.setText("Blocked: setup is locked.")
            return

        try:
            prj.CRSEPSG = str(self._current_epsg_value() or "").strip()
            prj.DesignStandard = _ds.normalize_standard(self.cmb_design_standard.currentText(), default=_ds.DEFAULT_STANDARD)
            prj.LinearUnitDisplay = self._current_linear_display_unit()
            prj.LinearUnitImportDefault = self._current_linear_import_unit()
            prj.LinearUnitExportDefault = self._current_linear_export_unit()
            prj.CustomLinearUnitScale = float(self.sp_custom_linear_scale.value())
            prj.TINConversionMaxTriangles = int(self.sp_tin_max_triangles.value())
            workflow = str(self.cmb_coord_workflow.currentText() or "").strip()
            if workflow not in _COORD_WORKFLOW_VALUES:
                workflow = self._recommended_workflow_from_epsg(prj.CRSEPSG)
            prj.CoordinateWorkflow = workflow
            prj.AutoApplyCoordinateRecommendations = bool(self.chk_auto_coord_reco.isChecked())
            prj.HorizontalDatum = str(self.ed_h_datum.text() or "").strip()
            prj.VerticalDatum = str(self.ed_v_datum.text() or "").strip()
            prj.ProjectOriginE = float(self.sp_e.value())
            prj.ProjectOriginN = float(self.sp_n.value())
            prj.ProjectOriginZ = float(self.sp_z.value())
            prj.LocalOriginX = float(self.sp_lx.value())
            prj.LocalOriginY = float(self.sp_ly.value())
            prj.LocalOriginZ = float(self.sp_lz.value())
            prj.NorthRotationDeg = float(self.sp_rot.value())
            prj.CoordSetupLocked = bool(self.chk_locked.isChecked())
            st = str(self.cmb_status.currentText() or "").strip()
            prj.CoordSetupStatus = st if st else "Initialized"

            prj.touch()
            if self.doc is not None:
                self.doc.recompute()
            self._update_unit_policy_info()

            self.lbl_result.setText(
                f"Applied: Display='{prj.LinearUnitDisplay}', Import='{prj.LinearUnitImportDefault}', Export='{prj.LinearUnitExportDefault}', "
                f"CustomScale={float(prj.CustomLinearUnitScale):.9f}, Standard='{prj.DesignStandard}', EPSG='{prj.CRSEPSG}', "
                f"Workflow='{prj.CoordinateWorkflow}', TINLimit={int(prj.TINConversionMaxTriangles)}, "
                f"NorthRot={float(prj.NorthRotationDeg):.6f}, Locked={bool(prj.CoordSetupLocked)}"
            )
            QtWidgets.QMessageBox.information(
                None,
                "Project Setup",
                "Project coordinate and unit setup has been applied.",
            )
        except Exception as ex:
            self.lbl_result.setText(f"ERROR: {ex}")

import FreeCAD as App
import FreeCADGui as Gui
from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects import design_standards as _ds
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties


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
        self.sp_scale = QtWidgets.QDoubleSpinBox()
        self.sp_scale.setRange(1e-6, 1.0e9)
        self.sp_scale.setDecimals(6)
        self.sp_scale.setValue(1.0)
        self.cmb_design_standard = QtWidgets.QComboBox()
        self.cmb_design_standard.addItems(list(_ds.SUPPORTED_STANDARDS))
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fs.addRow("Target Project:", self.cmb_project)
        fs.addRow("Length Scale:", self.sp_scale)
        fs.addRow("Design Standard:", self.cmb_design_standard)
        fs.addRow(self.btn_refresh)
        root.addWidget(gb_src)

        gb_coord = QtWidgets.QGroupBox("Coordinate System")
        fc = QtWidgets.QFormLayout(gb_coord)
        self.ed_epsg = QtWidgets.QLineEdit()
        self.ed_epsg.setPlaceholderText("e.g. EPSG:5186")
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

        fc.addRow("CRS / EPSG:", self.ed_epsg)
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
        row_btn.addStretch(1)
        row_btn.addWidget(self.btn_close)
        root.addLayout(row_btn)

        self.lbl_result = QtWidgets.QLabel("Idle")
        self.lbl_result.setWordWrap(True)
        root.addWidget(self.lbl_result)

        self.btn_refresh.clicked.connect(self._on_refresh)
        self.cmb_project.currentIndexChanged.connect(self._on_project_changed)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_close.clicked.connect(self.reject)
        return w

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

        self.lbl_info.setText(f"CorridorRoadProject: {len(self._projects)} found.")
        self._load_project()

    def _load_project(self):
        prj = self._current_project()
        if prj is None:
            return
        ensure_project_properties(prj)

        self._loading = True
        try:
            self.ed_epsg.setText(str(getattr(prj, "CRSEPSG", "") or ""))
            self.sp_scale.setValue(float(getattr(prj, "LengthScale", 1.0)))
            self.cmb_design_standard.setCurrentText(_ds.normalize_standard(getattr(prj, "DesignStandard", _ds.DEFAULT_STANDARD)))
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

        if str(getattr(prj, "CRSEPSG", "") or "") != str(self.ed_epsg.text() or ""):
            return True
        if str(getattr(prj, "HorizontalDatum", "") or "") != str(self.ed_h_datum.text() or ""):
            return True
        if str(getattr(prj, "VerticalDatum", "") or "") != str(self.ed_v_datum.text() or ""):
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
            prj.CRSEPSG = str(self.ed_epsg.text() or "").strip()
            prj.LengthScale = float(self.sp_scale.value())
            prj.DesignStandard = _ds.normalize_standard(self.cmb_design_standard.currentText(), default=_ds.DEFAULT_STANDARD)
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

            self.lbl_result.setText(
                f"Applied: Scale={float(prj.LengthScale):.6f}, Standard='{prj.DesignStandard}', EPSG='{prj.CRSEPSG}', "
                f"NorthRot={float(prj.NorthRotationDeg):.6f}, Locked={bool(prj.CoordSetupLocked)}"
            )
            QtWidgets.QMessageBox.information(
                None,
                "Project Setup",
                "Project coordinate setup has been applied.",
            )
        except Exception as ex:
            self.lbl_result.setText(f"ERROR: {ex}")

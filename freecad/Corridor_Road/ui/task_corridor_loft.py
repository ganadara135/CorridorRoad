import FreeCAD as App
import FreeCADGui as Gui
from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_all, find_project
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft, ViewProviderCorridorLoft, ensure_corridor_loft_properties
from freecad.Corridor_Road.objects.obj_project import get_length_scale
from freecad.Corridor_Road.objects.project_links import link_project


def _find_section_sets(doc):
    return find_all(doc, proxy_type="SectionSet", name_prefixes=("SectionSet",))


def _find_corridor_lofts(doc):
    return find_all(doc, proxy_type="CorridorLoft", name_prefixes=("CorridorLoft",))


class CorridorLoftTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._scale = get_length_scale(self.doc, default=1.0)
        self._sections = []
        self._corridors = []
        self._loading = False
        self.form = self._build_ui()
        self._refresh_context()

    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Close)

    def accept(self):
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()

    def _build_ui(self):
        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Corridor Loft")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        gb_src = QtWidgets.QGroupBox("Source")
        fs = QtWidgets.QFormLayout(gb_src)
        self.cmb_section = QtWidgets.QComboBox()
        self.cmb_target = QtWidgets.QComboBox()
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fs.addRow("Section Set:", self.cmb_section)
        fs.addRow("Target Corridor Loft:", self.cmb_target)
        fs.addRow(self.btn_refresh)
        main.addWidget(gb_src)

        gb_opt = QtWidgets.QGroupBox("Options")
        form_opts = QtWidgets.QFormLayout(gb_opt)
        self.spin_min_spacing = QtWidgets.QDoubleSpinBox()
        self.spin_min_spacing.setRange(0.0, 10000.0 * self._scale)
        self.spin_min_spacing.setDecimals(3)
        self.spin_min_spacing.setValue(0.50 * self._scale)
        self.chk_ruled = QtWidgets.QCheckBox("Use ruled loft")
        self.chk_ruled.setChecked(False)
        self.chk_auto = QtWidgets.QCheckBox("Auto update on source changes")
        self.chk_auto.setChecked(True)
        form_opts.addRow("Min Section Spacing:", self.spin_min_spacing)
        form_opts.addRow(self.chk_ruled)
        form_opts.addRow(self.chk_auto)
        main.addWidget(gb_opt)

        self.btn_build = QtWidgets.QPushButton("Build Corridor Loft")
        main.addWidget(self.btn_build)

        gb_run = QtWidgets.QGroupBox("Run")
        fr = QtWidgets.QFormLayout(gb_run)
        self.lbl_status = QtWidgets.QLabel("Idle")
        self.lbl_status.setWordWrap(True)
        fr.addRow("Status:", self.lbl_status)
        main.addWidget(gb_run)

        self.btn_refresh.clicked.connect(self._refresh_context)
        self.cmb_target.currentIndexChanged.connect(self._on_target_changed)
        self.btn_build.clicked.connect(self._build)
        return w

    @staticmethod
    def _fmt_obj(prefix: str, obj):
        return f"[{prefix}] {obj.Label} ({obj.Name})"

    def _fill_sections(self, selected=None):
        self.cmb_section.clear()
        for o in self._sections:
            self.cmb_section.addItem(self._fmt_obj("SectionSet", o))
        if not self._sections:
            return
        idx = 0
        if selected is not None:
            for i, o in enumerate(self._sections):
                if o == selected:
                    idx = i
                    break
        self.cmb_section.setCurrentIndex(idx)

    def _fill_targets(self, selected=None):
        self.cmb_target.clear()
        self.cmb_target.addItem("[New] Create new Corridor Loft")
        for o in self._corridors:
            self.cmb_target.addItem(self._fmt_obj("CorridorLoft", o))
        idx = 0
        if selected is not None:
            for i, o in enumerate(self._corridors):
                if o == selected:
                    idx = i + 1
                    break
        self.cmb_target.setCurrentIndex(idx)

    def _current_section(self):
        i = int(self.cmb_section.currentIndex())
        if i < 0 or i >= len(self._sections):
            return None
        return self._sections[i]

    def _current_target(self):
        i = int(self.cmb_target.currentIndex())
        if i <= 0:
            return None
        j = i - 1
        if j < 0 or j >= len(self._corridors):
            return None
        return self._corridors[j]

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return

        self._loading = True
        try:
            self._sections = _find_section_sets(self.doc)
            self._corridors = _find_corridor_lofts(self.doc)

            prj = find_project(self.doc)
            selected_sec = getattr(prj, "SectionSet", None) if prj is not None else None
            selected_cor = getattr(prj, "CorridorLoft", None) if prj is not None else None

            self._fill_sections(selected=selected_sec)
            self._fill_targets(selected=selected_cor)

            self.lbl_info.setText(
                f"SectionSet: {len(self._sections)} found, CorridorLoft: {len(self._corridors)} found."
            )
        finally:
            self._loading = False
        self._on_target_changed()

    def _on_target_changed(self):
        if self._loading:
            return
        cor = self._current_target()
        if cor is None:
            self.spin_min_spacing.setValue(0.50 * self._scale)
            self.chk_ruled.setChecked(False)
            self.chk_auto.setChecked(True)
            self.lbl_status.setText("New corridor will be created.")
            return

        try:
            ensure_corridor_loft_properties(cor)
        except Exception:
            pass
        try:
            self.spin_min_spacing.setValue(float(getattr(cor, "MinSectionSpacing", 0.50 * self._scale)))
        except Exception:
            self.spin_min_spacing.setValue(0.50 * self._scale)
        self.chk_ruled.setChecked(bool(getattr(cor, "UseRuled", False)))
        self.chk_auto.setChecked(bool(getattr(cor, "AutoUpdate", True)))
        self.lbl_status.setText(str(getattr(cor, "Status", "Ready")))

    def _ensure_target_corridor(self):
        cor = self._current_target()
        if cor is not None:
            return cor

        cor = self.doc.addObject("Part::FeaturePython", "CorridorLoft")
        CorridorLoft(cor)
        ViewProviderCorridorLoft(cor.ViewObject)
        cor.Label = "Corridor Loft"
        return cor

    def _build(self):
        if self.doc is None:
            QtWidgets.QMessageBox.warning(None, "Corridor Loft", "No active document.")
            return

        sec = self._current_section()
        if sec is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Corridor Loft",
                "No SectionSet found. Run Generate Sections first.",
            )
            return

        try:
            cor = self._ensure_target_corridor()
            ensure_corridor_loft_properties(cor)
            cor.SourceSectionSet = sec
            cor.UseRuled = bool(self.chk_ruled.isChecked())
            cor.AutoUpdate = bool(self.chk_auto.isChecked())
            if hasattr(cor, "MinSectionSpacing"):
                cor.MinSectionSpacing = float(self.spin_min_spacing.value())
            cor.touch()

            prj = find_project(self.doc)
            if prj is not None:
                link_project(
                    prj,
                    links={"CorridorLoft": cor},
                    links_if_empty={"SectionSet": sec},
                    adopt_extra=[cor, sec],
                )

            self.doc.recompute()
            self.lbl_status.setText(str(getattr(cor, "Status", "OK")))
            n = len(list(getattr(sec, "StationValues", []) or []))
            QtWidgets.QMessageBox.information(
                None,
                "Corridor Loft",
                f"Corridor loft build completed.\nSections used: {n}\nStatus: {getattr(cor, 'Status', 'OK')}",
            )
            self._refresh_context()
            try:
                Gui.ActiveDocument.ActiveView.fitAll()
            except Exception:
                pass
        except Exception as ex:
            self.lbl_status.setText(f"ERROR: {ex}")

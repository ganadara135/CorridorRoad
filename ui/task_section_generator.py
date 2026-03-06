# CorridorRoad/ui/task_section_generator.py
import FreeCAD as App
import FreeCADGui as Gui

from PySide2 import QtWidgets

from objects.obj_assembly_template import (
    AssemblyTemplate,
    ViewProviderAssemblyTemplate,
    ensure_assembly_template_properties,
)
from objects.doc_query import find_first, find_project
from objects.project_links import link_project
from objects.obj_section_set import SectionSet, ViewProviderSectionSet
from objects.obj_project import get_length_scale


def _find_first_by_proxy_type(doc, type_name: str):
    return find_first(doc, proxy_type=type_name, name_prefixes=(type_name,))


def _find_alignment(doc):
    return find_first(doc, name_prefixes=("HorizontalAlignment",))


def _find_project(doc):
    return find_project(doc)


def _is_mesh_obj(obj):
    try:
        return hasattr(obj, "Mesh") and obj.Mesh is not None and int(obj.Mesh.CountFacets) > 0
    except Exception:
        return False


def _find_terrain_sources(doc):
    out = []
    if doc is None:
        return out
    for o in doc.Objects:
        if _is_mesh_obj(o):
            out.append(o)
    return out


def _selected_mesh_terrain():
    try:
        sel = list(Gui.Selection.getSelection() or [])
        for o in sel:
            if _is_mesh_obj(o):
                return o
    except Exception:
        pass
    return None


def _find_source_centerline_display(doc):
    return find_first(doc, proxy_type="Centerline3DDisplay", name_prefixes=("Centerline3DDisplay",))


class SectionGeneratorTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._terrains = []
        self.form = self._build_ui()
        self._refresh_context()

    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Close)

    def accept(self):
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()

    def _build_ui(self):
        scale = get_length_scale(self.doc, default=1.0)

        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Generate Sections")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        gb_mode = QtWidgets.QGroupBox("Section Mode")
        fm = QtWidgets.QFormLayout(gb_mode)
        self.cmb_mode = QtWidgets.QComboBox()
        self.cmb_mode.addItems(["Range", "Manual"])
        fm.addRow("Mode:", self.cmb_mode)

        self.spin_start = QtWidgets.QDoubleSpinBox()
        self.spin_start.setRange(0.0, 1.0e9)
        self.spin_start.setDecimals(3)
        self.spin_start.setValue(0.0)
        self.spin_end = QtWidgets.QDoubleSpinBox()
        self.spin_end.setRange(0.0, 1.0e9)
        self.spin_end.setDecimals(3)
        self.spin_end.setValue(100.0 * scale)
        self.spin_itv = QtWidgets.QDoubleSpinBox()
        self.spin_itv.setRange(0.001, 1.0e6)
        self.spin_itv.setDecimals(3)
        self.spin_itv.setValue(20.0 * scale)
        fm.addRow("Start Station:", self.spin_start)
        fm.addRow("End Station:", self.spin_end)
        fm.addRow("Interval:", self.spin_itv)

        self.txt_manual = QtWidgets.QPlainTextEdit()
        self.txt_manual.setPlaceholderText("Manual stations (comma/space/newline), e.g. 0, 20, 37.5, 80")
        self.txt_manual.setFixedHeight(80)
        fm.addRow("Manual Stations:", self.txt_manual)
        self.chk_include_ip_keys = QtWidgets.QCheckBox("Include Alignment IP Key Stations (Range)")
        self.chk_include_ip_keys.setChecked(True)
        fm.addRow(self.chk_include_ip_keys)
        self.chk_include_sccs_keys = QtWidgets.QCheckBox("Include Alignment TS/SC/CS/ST Key Stations (Range)")
        self.chk_include_sccs_keys.setChecked(False)
        fm.addRow(self.chk_include_sccs_keys)
        self.chk_include_struct_keys = QtWidgets.QCheckBox("Include Structure/Crossing Key Stations")
        self.chk_include_struct_keys.setChecked(False)
        self.txt_struct_stations = QtWidgets.QLineEdit()
        self.txt_struct_stations.setPlaceholderText("e.g. 25, 78.5, 120")
        fm.addRow(self.chk_include_struct_keys)
        fm.addRow("Structure/Crossing Stations:", self.txt_struct_stations)
        main.addWidget(gb_mode)

        gb_opt = QtWidgets.QGroupBox("Options")
        fo = QtWidgets.QFormLayout(gb_opt)
        self.chk_create_new = QtWidgets.QCheckBox("Create new SectionSet")
        self.chk_create_new.setChecked(True)
        self.chk_children = QtWidgets.QCheckBox("Create child sections in tree")
        self.chk_children.setChecked(True)
        self.chk_place_at_start = QtWidgets.QCheckBox("Place template at centerline start (Recommended)")
        self.chk_place_at_start.setChecked(True)
        self.spin_tpl_x = QtWidgets.QDoubleSpinBox()
        self.spin_tpl_x.setRange(-1.0e9, 1.0e9)
        self.spin_tpl_x.setDecimals(3)
        self.spin_tpl_x.setValue(0.0)
        self.spin_tpl_y = QtWidgets.QDoubleSpinBox()
        self.spin_tpl_y.setRange(-1.0e9, 1.0e9)
        self.spin_tpl_y.setDecimals(3)
        self.spin_tpl_y.setValue(0.0)
        self.spin_tpl_z = QtWidgets.QDoubleSpinBox()
        self.spin_tpl_z.setRange(-1.0e9, 1.0e9)
        self.spin_tpl_z.setDecimals(3)
        self.spin_tpl_z.setValue(0.0)
        self.spin_h_left = QtWidgets.QDoubleSpinBox()
        self.spin_h_left.setRange(0.0, 100.0 * scale)
        self.spin_h_left.setDecimals(3)
        self.spin_h_left.setValue(0.300 * scale)
        self.spin_h_right = QtWidgets.QDoubleSpinBox()
        self.spin_h_right.setRange(0.0, 100.0 * scale)
        self.spin_h_right.setDecimals(3)
        self.spin_h_right.setValue(0.300 * scale)
        self.chk_side = QtWidgets.QCheckBox("Use side slopes")
        self.chk_side.setChecked(False)
        self.spin_side_w_left = QtWidgets.QDoubleSpinBox()
        self.spin_side_w_left.setRange(0.0, 1000.0 * scale)
        self.spin_side_w_left.setDecimals(3)
        self.spin_side_w_left.setValue(2.0 * scale)
        self.spin_side_w_right = QtWidgets.QDoubleSpinBox()
        self.spin_side_w_right.setRange(0.0, 1000.0 * scale)
        self.spin_side_w_right.setDecimals(3)
        self.spin_side_w_right.setValue(2.0 * scale)
        self.spin_side_s_left = QtWidgets.QDoubleSpinBox()
        self.spin_side_s_left.setRange(-1000.0, 1000.0)
        self.spin_side_s_left.setDecimals(3)
        self.spin_side_s_left.setValue(50.0)
        self.spin_side_s_right = QtWidgets.QDoubleSpinBox()
        self.spin_side_s_right.setRange(-1000.0, 1000.0)
        self.spin_side_s_right.setDecimals(3)
        self.spin_side_s_right.setValue(50.0)
        self.chk_daylight = QtWidgets.QCheckBox("Daylight Auto (SectionSet)")
        self.chk_daylight.setChecked(True)
        self.cmb_day_terrain = QtWidgets.QComboBox()
        self.btn_pick_day_terrain = QtWidgets.QPushButton("Use Selected Terrain")
        self.spin_day_step = QtWidgets.QDoubleSpinBox()
        self.spin_day_step.setRange(0.2 * scale, 100.0 * scale)
        self.spin_day_step.setDecimals(3)
        self.spin_day_step.setValue(1.0 * scale)
        self.spin_day_max_w = QtWidgets.QDoubleSpinBox()
        self.spin_day_max_w.setRange(1.0 * scale, 10000.0 * scale)
        self.spin_day_max_w.setDecimals(3)
        self.spin_day_max_w.setValue(200.0 * scale)
        self.btn_make_assembly = QtWidgets.QPushButton("Create Assembly Template")
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fo.addRow(self.chk_create_new)
        fo.addRow(self.chk_children)
        fo.addRow(self.chk_place_at_start)
        fo.addRow("Template X:", self.spin_tpl_x)
        fo.addRow("Template Y:", self.spin_tpl_y)
        fo.addRow("Template Z:", self.spin_tpl_z)
        fo.addRow("Height Left:", self.spin_h_left)
        fo.addRow("Height Right:", self.spin_h_right)
        fo.addRow(self.chk_side)
        fo.addRow("Side Width Left:", self.spin_side_w_left)
        fo.addRow("Side Width Right:", self.spin_side_w_right)
        fo.addRow("Side Slope Left (%):", self.spin_side_s_left)
        fo.addRow("Side Slope Right (%):", self.spin_side_s_right)
        fo.addRow(self.chk_daylight)
        fo.addRow("Daylight Terrain (Mesh):", self.cmb_day_terrain)
        fo.addRow(self.btn_pick_day_terrain)
        fo.addRow("Daylight Search Step:", self.spin_day_step)
        fo.addRow("Daylight Max Search Width:", self.spin_day_max_w)
        fo.addRow(self.btn_make_assembly)
        fo.addRow(self.btn_refresh)
        main.addWidget(gb_opt)

        self.btn_generate = QtWidgets.QPushButton("Generate Sections Now")
        main.addWidget(self.btn_generate)

        self.cmb_mode.currentTextChanged.connect(self._update_mode_ui)
        self.chk_include_struct_keys.toggled.connect(self._update_mode_ui)
        self.chk_place_at_start.toggled.connect(self._update_template_pos_ui)
        self.chk_side.toggled.connect(self._update_side_ui)
        self.chk_daylight.toggled.connect(self._update_side_ui)
        self.btn_pick_day_terrain.clicked.connect(self._use_selected_day_terrain)
        self.btn_make_assembly.clicked.connect(self._create_assembly_template)
        self.btn_refresh.clicked.connect(self._refresh_context)
        self.btn_generate.clicked.connect(self._generate)

        self._update_mode_ui()
        self._update_template_pos_ui()
        self._update_side_ui()
        return w

    def _update_mode_ui(self):
        is_range = (self.cmb_mode.currentText() == "Range")
        self.spin_start.setEnabled(is_range)
        self.spin_end.setEnabled(is_range)
        self.spin_itv.setEnabled(is_range)
        self.txt_manual.setEnabled(not is_range)
        self.chk_include_ip_keys.setEnabled(is_range)
        self.chk_include_sccs_keys.setEnabled(is_range)
        self.txt_struct_stations.setEnabled(bool(self.chk_include_struct_keys.isChecked()))

    def _update_template_pos_ui(self):
        use_start = bool(self.chk_place_at_start.isChecked())
        self.spin_tpl_x.setEnabled(not use_start)
        self.spin_tpl_y.setEnabled(not use_start)
        self.spin_tpl_z.setEnabled(not use_start)

    def _update_side_ui(self):
        on = bool(self.chk_side.isChecked())
        scale = get_length_scale(self.doc, default=1.0)
        if on:
            if float(self.spin_side_w_left.value()) <= 1e-9:
                self.spin_side_w_left.setValue(2.0 * scale)
            if float(self.spin_side_w_right.value()) <= 1e-9:
                self.spin_side_w_right.setValue(2.0 * scale)
        self.spin_side_w_left.setEnabled(on)
        self.spin_side_w_right.setEnabled(on)
        self.spin_side_s_left.setEnabled(on)
        self.spin_side_s_right.setEnabled(on)
        self.chk_daylight.setEnabled(on)
        self.cmb_day_terrain.setEnabled(on and bool(self.chk_daylight.isChecked()))
        self.btn_pick_day_terrain.setEnabled(on and bool(self.chk_daylight.isChecked()))
        self.spin_day_step.setEnabled(on and bool(self.chk_daylight.isChecked()))
        self.spin_day_max_w.setEnabled(on and bool(self.chk_daylight.isChecked()))

    def _format_obj(self, obj):
        return f"[Mesh] {obj.Label} ({obj.Name})"

    def _fill_combo(self, combo, objects, selected=None):
        combo.clear()
        for i, o in enumerate(objects):
            combo.addItem(self._format_obj(o), i)
        if not objects:
            return
        idx = 0
        if selected is not None:
            for i, o in enumerate(objects):
                if o == selected:
                    idx = i
                    break
        combo.setCurrentIndex(idx)

    def _current_daylight_terrain(self):
        i = int(self.cmb_day_terrain.currentIndex())
        if i < 0 or i >= len(self._terrains):
            return None
        return self._terrains[i]

    def _use_selected_day_terrain(self):
        sel = _selected_mesh_terrain()
        if sel is None:
            QtWidgets.QMessageBox.information(
                None,
                "Generate Sections",
                "No terrain mesh selected. Select a Mesh object first.",
            )
            return
        for i, o in enumerate(self._terrains):
            if o == sel:
                self.cmb_day_terrain.setCurrentIndex(i)
                return
        self._refresh_context()

    def _set_suspend_recompute(self, obj, flag: bool):
        try:
            pr = getattr(obj, "Proxy", None)
            if pr is not None and hasattr(pr, "_suspend_recompute"):
                pr._suspend_recompute = bool(flag)
        except Exception:
            pass

    def _apply_assembly_ui_values(self, asm):
        if asm is None:
            return
        if hasattr(asm, "HeightLeft"):
            asm.HeightLeft = float(self.spin_h_left.value())
        if hasattr(asm, "HeightRight"):
            asm.HeightRight = float(self.spin_h_right.value())
        if hasattr(asm, "UseSideSlopes"):
            asm.UseSideSlopes = bool(self.chk_side.isChecked())
        if hasattr(asm, "LeftSideWidth"):
            asm.LeftSideWidth = float(self.spin_side_w_left.value())
        if hasattr(asm, "RightSideWidth"):
            asm.RightSideWidth = float(self.spin_side_w_right.value())
        if hasattr(asm, "LeftSideSlopePct"):
            asm.LeftSideSlopePct = float(self.spin_side_s_left.value())
        if hasattr(asm, "RightSideSlopePct"):
            asm.RightSideSlopePct = float(self.spin_side_s_right.value())
        if hasattr(asm, "UseDaylightToTerrain"):
            asm.UseDaylightToTerrain = bool(self.chk_daylight.isChecked())
        if hasattr(asm, "DaylightSearchStep"):
            asm.DaylightSearchStep = float(self.spin_day_step.value())
        if hasattr(asm, "DaylightMaxSearchWidth"):
            asm.DaylightMaxSearchWidth = float(self.spin_day_max_w.value())

    def _resolve_template_base(self):
        if bool(self.chk_place_at_start.isChecked()):
            src = _find_source_centerline_display(self.doc)
            if src is not None and getattr(src, "Alignment", None) is not None:
                try:
                    from objects.obj_alignment import HorizontalAlignment
                    p0 = HorizontalAlignment.point_at_station(src.Alignment, 0.0)
                    return App.Vector(float(p0.x), float(p0.y), float(p0.z))
                except Exception:
                    pass
        return App.Vector(
            float(self.spin_tpl_x.value()),
            float(self.spin_tpl_y.value()),
            float(self.spin_tpl_z.value()),
        )

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return

        src = _find_source_centerline_display(self.doc)
        asm = _find_first_by_proxy_type(self.doc, "AssemblyTemplate")
        sec = _find_first_by_proxy_type(self.doc, "SectionSet")
        aln = _find_alignment(self.doc)
        prj = _find_project(self.doc)
        self._terrains = _find_terrain_sources(self.doc)

        pref_terrain = None
        if sec is not None and hasattr(sec, "TerrainMesh"):
            pref_terrain = getattr(sec, "TerrainMesh", None)
        if pref_terrain is None and prj is not None and hasattr(prj, "Terrain"):
            pref_terrain = getattr(prj, "Terrain", None)
        sel_terrain = _selected_mesh_terrain()
        if sel_terrain is not None:
            pref_terrain = sel_terrain
        self._fill_combo(self.cmb_day_terrain, self._terrains, pref_terrain)

        if sec is not None:
            try:
                if hasattr(sec, "DaylightAuto"):
                    self.chk_daylight.setChecked(bool(sec.DaylightAuto))
                if hasattr(sec, "IncludeAlignmentIPStations"):
                    self.chk_include_ip_keys.setChecked(bool(sec.IncludeAlignmentIPStations))
                if hasattr(sec, "IncludeAlignmentSCCSStations"):
                    self.chk_include_sccs_keys.setChecked(bool(sec.IncludeAlignmentSCCSStations))
                if hasattr(sec, "IncludeStructureStations"):
                    self.chk_include_struct_keys.setChecked(bool(sec.IncludeStructureStations))
                if hasattr(sec, "StructureStationText"):
                    self.txt_struct_stations.setText(str(sec.StructureStationText or ""))
            except Exception:
                pass

        if asm is not None:
            try:
                ensure_assembly_template_properties(asm)
                if hasattr(asm, "HeightLeft"):
                    self.spin_h_left.setValue(float(asm.HeightLeft))
                if hasattr(asm, "HeightRight"):
                    self.spin_h_right.setValue(float(asm.HeightRight))
                if hasattr(asm, "UseSideSlopes"):
                    self.chk_side.setChecked(bool(asm.UseSideSlopes))
                if hasattr(asm, "LeftSideWidth"):
                    self.spin_side_w_left.setValue(float(asm.LeftSideWidth))
                if hasattr(asm, "RightSideWidth"):
                    self.spin_side_w_right.setValue(float(asm.RightSideWidth))
                if hasattr(asm, "LeftSideSlopePct"):
                    self.spin_side_s_left.setValue(float(asm.LeftSideSlopePct))
                if hasattr(asm, "RightSideSlopePct"):
                    self.spin_side_s_right.setValue(float(asm.RightSideSlopePct))
                # Backward-compat fallback: if SectionSet.DaylightAuto is not available,
                # keep using legacy AssemblyTemplate.UseDaylightToTerrain.
                if (sec is None or (not hasattr(sec, "DaylightAuto"))) and hasattr(asm, "UseDaylightToTerrain"):
                    self.chk_daylight.setChecked(bool(asm.UseDaylightToTerrain))
                if hasattr(asm, "DaylightSearchStep"):
                    self.spin_day_step.setValue(float(asm.DaylightSearchStep))
                if hasattr(asm, "DaylightMaxSearchWidth"):
                    self.spin_day_max_w.setValue(float(asm.DaylightMaxSearchWidth))
            except Exception:
                pass

        if src is not None and getattr(src, "Alignment", None) is not None and getattr(src.Alignment, "Shape", None):
            try:
                total = float(src.Alignment.Shape.Length)
                self.spin_end.setValue(max(self.spin_end.value(), total))
            except Exception:
                pass
        elif aln is not None and getattr(aln, "Shape", None):
            try:
                total = float(aln.Shape.Length)
                self.spin_end.setValue(max(self.spin_end.value(), total))
            except Exception:
                pass

        msg = []
        msg.append(f"Centerline Display: {'FOUND' if src else 'NOT FOUND'}")
        msg.append(f"Assembly Template: {'FOUND' if asm else 'NOT FOUND'}")
        msg.append(f"Section Set: {'FOUND' if sec else 'NOT FOUND'}")
        msg.append(f"Terrain candidates: {len(self._terrains)} found (Mesh)")
        if pref_terrain is not None:
            msg.append(f"Daylight terrain: {pref_terrain.Label} ({pref_terrain.Name})")
        msg.append("")
        msg.append("Workflow:")
        msg.append("1) Select mode (Range or Manual)")
        msg.append("2) Generate to create/update SectionSet")
        msg.append("   - Range mode can include PI and TS/SC/CS/ST key stations automatically")
        msg.append("   - Structure/Crossing key stations can be merged from text list")
        msg.append("3) Side slopes are optional (AssemblyTemplate.UseSideSlopes)")
        msg.append("4) Daylight Auto uses Terrain source (Project.Terrain / SectionSet.TerrainMesh, Mesh or Shape)")
        self.lbl_info.setText("\n".join(msg))
        self._update_side_ui()
        self._update_mode_ui()

    def _create_assembly_template(self):
        if self.doc is None:
            return
        asm = _find_first_by_proxy_type(self.doc, "AssemblyTemplate")
        if asm is not None:
            try:
                self._set_suspend_recompute(asm, True)
                asm.Placement.Base = self._resolve_template_base()
                self._apply_assembly_ui_values(asm)
                asm.touch()
            finally:
                self._set_suspend_recompute(asm, False)
            try:
                self.doc.recompute()
            except Exception:
                pass
            return

        asm = self.doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        ViewProviderAssemblyTemplate(asm.ViewObject)
        asm.Label = "Assembly Template"
        try:
            self._set_suspend_recompute(asm, True)
            asm.Placement.Base = self._resolve_template_base()
            self._apply_assembly_ui_values(asm)
        except Exception:
            pass
        finally:
            self._set_suspend_recompute(asm, False)
        asm.touch()
        self.doc.recompute()

        prj = _find_project(self.doc)
        if prj is not None:
            link_project(prj, links={"AssemblyTemplate": asm}, adopt_extra=[asm])

        self._refresh_context()

    def _resolve_source_display(self):
        src = _find_source_centerline_display(self.doc)
        if src is None:
            raise Exception("Centerline3DDisplay not found. Run 'Generate 3D Centerline' first.")
        return src

    def _resolve_assembly(self):
        asm = _find_first_by_proxy_type(self.doc, "AssemblyTemplate")
        if asm is not None:
            try:
                self._set_suspend_recompute(asm, True)
                asm.Placement.Base = self._resolve_template_base()
                self._apply_assembly_ui_values(asm)
                asm.touch()
            except Exception:
                pass
            finally:
                self._set_suspend_recompute(asm, False)
            return asm

        # Auto-create for first run convenience
        asm = self.doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        ViewProviderAssemblyTemplate(asm.ViewObject)
        asm.Label = "Assembly Template"
        try:
            self._set_suspend_recompute(asm, True)
            asm.Placement.Base = self._resolve_template_base()
            self._apply_assembly_ui_values(asm)
        except Exception:
            pass
        finally:
            self._set_suspend_recompute(asm, False)
        asm.touch()
        self.doc.recompute()
        return asm

    def _resolve_section_set(self):
        if bool(self.chk_create_new.isChecked()):
            return None
        return _find_first_by_proxy_type(self.doc, "SectionSet")

    def _create_or_get_section_set(self):
        sec = self._resolve_section_set()
        if sec is not None:
            return sec

        sec = self.doc.addObject("Part::FeaturePython", "SectionSet")
        SectionSet(sec)
        ViewProviderSectionSet(sec.ViewObject)
        sec.Label = "Section Set"
        return sec

    def _clear_children(self, sec_obj):
        SectionSet.clear_child_sections(sec_obj)

    def _rebuild_children(self, sec_obj):
        if not bool(getattr(sec_obj, "CreateChildSections", True)):
            return
        SectionSet.rebuild_child_sections(sec_obj)

    def _generate(self):
        if self.doc is None:
            return

        src = self._resolve_source_display()
        asm = self._resolve_assembly()
        sec = self._create_or_get_section_set()

        try:
            self._set_suspend_recompute(sec, True)
            sec.SourceCenterlineDisplay = src
            sec.AssemblyTemplate = asm
            sec.Mode = self.cmb_mode.currentText()
            sec.StartStation = float(self.spin_start.value())
            sec.EndStation = float(self.spin_end.value())
            sec.Interval = float(self.spin_itv.value())
            sec.StationText = str(self.txt_manual.toPlainText() or "")
            if hasattr(sec, "IncludeAlignmentIPStations"):
                sec.IncludeAlignmentIPStations = bool(self.chk_include_ip_keys.isChecked())
            if hasattr(sec, "IncludeAlignmentSCCSStations"):
                sec.IncludeAlignmentSCCSStations = bool(self.chk_include_sccs_keys.isChecked())
            if hasattr(sec, "IncludeStructureStations"):
                sec.IncludeStructureStations = bool(self.chk_include_struct_keys.isChecked())
            if hasattr(sec, "StructureStationText"):
                sec.StructureStationText = str(self.txt_struct_stations.text() or "")
            sec.CreateChildSections = bool(self.chk_children.isChecked())
            if hasattr(sec, "DaylightAuto"):
                sec.DaylightAuto = bool(self.chk_daylight.isChecked())
            try:
                if hasattr(sec, "TerrainMesh"):
                    terr = self._current_daylight_terrain()
                    if terr is not None:
                        sec.TerrainMesh = terr
                    else:
                        prj0 = _find_project(self.doc)
                        if prj0 is not None and hasattr(prj0, "Terrain"):
                            sec.TerrainMesh = prj0.Terrain
            except Exception:
                pass
            sec.touch()
        finally:
            self._set_suspend_recompute(sec, False)

        self.doc.recompute()

        self._clear_children(sec)
        self._rebuild_children(sec)
        sec.touch()
        self.doc.recompute()

        prj = _find_project(self.doc)
        if prj is not None:
            link_project(
                prj,
                links={
                    "Centerline3DDisplay": src,
                    "AssemblyTemplate": asm,
                    "SectionSet": sec,
                },
                adopt_extra=[src, asm, sec],
            )

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass

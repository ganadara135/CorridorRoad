# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/ui/task_section_generator.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects.obj_assembly_template import (
    AssemblyTemplate,
    ViewProviderAssemblyTemplate,
    _parse_bench_row,
    ensure_assembly_template_properties,
)
from freecad.Corridor_Road.objects.obj_typical_section_template import TypicalSectionTemplate, ViewProviderTypicalSectionTemplate
from freecad.Corridor_Road.objects.doc_query import find_all, find_first, find_project
from freecad.Corridor_Road.objects.project_links import link_project
from freecad.Corridor_Road.objects.obj_section_set import (
    SectionSet,
    ViewProviderSectionSet,
    ensure_section_set_properties,
    region_plan_usage_enabled,
    resolve_region_plan_source,
    set_region_plan_source,
)
from freecad.Corridor_Road.objects.obj_project import assign_project_region_plan, find_region_plan_objects, get_length_scale
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan as RegionPlanSource
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet as StructureSetSource
from freecad.Corridor_Road.ui.common.coord_ui import coord_hint_text, should_default_world_mode


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


def _selected_terrain_source():
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


def _find_structure_sets(doc):
    return find_all(doc, proxy_type="StructureSet", name_prefixes=("StructureSet",))


def _find_region_sets(doc):
    return find_region_plan_objects(doc)


def _find_typical_section_templates(doc):
    return find_all(doc, proxy_type="TypicalSectionTemplate", name_prefixes=("TypicalSectionTemplate",))


class SectionGeneratorTaskPanel:
    _BENCH_HEADERS = ("Drop", "Width", "Slope", "Post-Slope")

    @staticmethod
    def _normalize_bench_row(row):
        if isinstance(row, dict) and ("post_slope" in row):
            try:
                return {
                    "drop": max(0.0, float(row.get("drop", 0.0) or 0.0)),
                    "width": max(0.0, float(row.get("width", 0.0) or 0.0)),
                    "slope": float(row.get("slope", 0.0) or 0.0),
                    "post_slope": float(row.get("post_slope", 0.0) or 0.0),
                }
            except Exception:
                return None
        return _parse_bench_row(row, 0.0)

    @classmethod
    def _bench_row_to_line(cls, row) -> str:
        parsed = cls._normalize_bench_row(row)
        if parsed is None:
            return ""
        return "{drop:.3f},{width:.3f},{slope:.3f},{post_slope:.3f}".format(**parsed)

    @classmethod
    def _bench_row_to_storage(cls, row) -> str:
        parsed = cls._normalize_bench_row(row)
        if parsed is None:
            return ""
        return "drop={drop:.6f}|width={width:.6f}|slope={slope:.6f}|post={post_slope:.6f}".format(**parsed)

    def _default_bench_row(self, side: str):
        scale = get_length_scale(self.doc, default=1.0)
        side_key = str(side or "").strip().lower()
        post = float(self.spin_side_s_left.value()) if side_key == "left" else float(self.spin_side_s_right.value())
        return {
            "drop": 1.0 * scale,
            "width": 1.5 * scale,
            "slope": 0.0,
            "post_slope": post,
        }

    def _bench_table(self, side: str):
        return self.tbl_left_bench_rows if str(side or "").strip().lower() == "left" else self.tbl_right_bench_rows

    def _bench_repeat_checkbox(self, side: str):
        return self.chk_left_bench_to_daylight if str(side or "").strip().lower() == "left" else self.chk_right_bench_to_daylight

    def _insert_bench_table_row(self, side: str, row_data=None, row_index=None):
        table = self._bench_table(side)
        row = dict(self._normalize_bench_row(row_data) or self._default_bench_row(side))
        if row_index is None or int(row_index) < 0 or int(row_index) > table.rowCount():
            row_index = table.rowCount()
        table.insertRow(int(row_index))
        values = (
            float(row.get("drop", 0.0) or 0.0),
            float(row.get("width", 0.0) or 0.0),
            float(row.get("slope", 0.0) or 0.0),
            float(row.get("post_slope", 0.0) or 0.0),
        )
        for col, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem(f"{float(value):.3f}")
            table.setItem(int(row_index), col, item)
        table.setCurrentCell(int(row_index), 0)

    def _bench_rows_from_table(self, side: str):
        table = self._bench_table(side)
        fallback_post = float(self.spin_side_s_left.value()) if str(side or "").strip().lower() == "left" else float(self.spin_side_s_right.value())
        rows = []
        for row in range(int(table.rowCount())):
            vals = []
            for col in range(4):
                item = table.item(row, col)
                vals.append("" if item is None else str(item.text() or "").strip())
            if not any(vals):
                continue
            parsed = _parse_bench_row(",".join(vals), fallback_post)
            if parsed is not None:
                rows.append(parsed)
        return rows

    def _set_bench_table_rows(self, side: str, rows):
        table = self._bench_table(side)
        table.setRowCount(0)
        for row in list(rows or []):
            self._insert_bench_table_row(side, row)

    def _trim_bench_rows_to_first(self, side: str):
        table = self._bench_table(side)
        if int(table.rowCount()) <= 0:
            self._insert_bench_table_row(side, self._default_bench_row(side))
        rows = self._bench_rows_from_table(side)
        keep = rows[:1] if rows else [self._default_bench_row(side)]
        self._set_bench_table_rows(side, keep)

    def _on_bench_repeat_to_daylight_toggled(self, side: str, checked: bool):
        if self._loading:
            return
        if bool(checked):
            self._trim_bench_rows_to_first(side)
        self._update_side_ui()

    def _add_bench_row(self, side: str):
        table = self._bench_table(side)
        cur = int(table.currentRow())
        if cur < 0:
            cur = table.rowCount() - 1
        self._insert_bench_table_row(side, row_index=cur + 1)

    def _remove_bench_row(self, side: str):
        table = self._bench_table(side)
        cur = int(table.currentRow())
        if cur < 0:
            cur = table.rowCount() - 1
        if cur >= 0:
            table.removeRow(cur)

    def _assembly_bench_rows(self, asm, side: str):
        side_key = str(side or "").strip().lower()
        if asm is None:
            return []
        if side_key == "left":
            stored = list(getattr(asm, "LeftBenchRows", []) or [])
            primary = {
                "drop": float(getattr(asm, "LeftBenchDrop", 0.0) or 0.0),
                "width": float(getattr(asm, "LeftBenchWidth", 0.0) or 0.0),
                "slope": float(getattr(asm, "LeftBenchSlopePct", 0.0) or 0.0),
                "post": float(getattr(asm, "LeftPostBenchSlopePct", getattr(asm, "LeftSideSlopePct", 0.0)) or getattr(asm, "LeftSideSlopePct", 0.0)),
            }
        else:
            stored = list(getattr(asm, "RightBenchRows", []) or [])
            primary = {
                "drop": float(getattr(asm, "RightBenchDrop", 0.0) or 0.0),
                "width": float(getattr(asm, "RightBenchWidth", 0.0) or 0.0),
                "slope": float(getattr(asm, "RightBenchSlopePct", 0.0) or 0.0),
                "post": float(getattr(asm, "RightPostBenchSlopePct", getattr(asm, "RightSideSlopePct", 0.0)) or getattr(asm, "RightSideSlopePct", 0.0)),
            }
        rows = []
        for row in stored:
            parsed = _parse_bench_row(row, float(primary.get("post", 0.0) or 0.0))
            if parsed is not None:
                rows.append(parsed)
        if rows:
            return rows
        parsed_primary = _parse_bench_row(primary, float(primary.get("post", 0.0) or 0.0))
        if parsed_primary is not None:
            rows.append(parsed_primary)
        repeat_flag = bool(getattr(asm, "LeftBenchRepeatToDaylight", False)) if side_key == "left" else bool(getattr(asm, "RightBenchRepeatToDaylight", False))
        if repeat_flag and rows:
            return rows[:1]
        return rows

    def __init__(self):
        self.doc = App.ActiveDocument
        self._terrains = []
        self._structures = []
        self._regions = []
        self._typicals = []
        self._project = None
        self._coord_mode_initialized = False
        self._loading = False
        self.form = self._build_ui()
        self._refresh_context()

    def getStandardButtons(self):
        return 0

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
        self.chk_include_struct_keys.setVisible(False)
        self.txt_struct_stations.setVisible(False)
        main.addWidget(gb_mode)

        gb_struct = QtWidgets.QGroupBox("StructureSet Integration")
        form_struct = QtWidgets.QFormLayout(gb_struct)
        self.chk_use_structure_set = QtWidgets.QCheckBox("Use linked StructureSet")
        self.chk_use_structure_set.setChecked(False)
        self.cmb_structure_source = QtWidgets.QComboBox()
        self.chk_struct_start_end = QtWidgets.QCheckBox("Include start/end stations")
        self.chk_struct_start_end.setChecked(True)
        self.chk_struct_centers = QtWidgets.QCheckBox("Include center stations")
        self.chk_struct_centers.setChecked(True)
        self.chk_struct_transition = QtWidgets.QCheckBox("Include transition stations")
        self.chk_struct_transition.setChecked(True)
        self.chk_struct_transition_auto = QtWidgets.QCheckBox("Auto transition distance")
        self.chk_struct_transition_auto.setChecked(True)
        self.spin_struct_transition = QtWidgets.QDoubleSpinBox()
        self.spin_struct_transition.setRange(0.0, 1.0e6)
        self.spin_struct_transition.setDecimals(3)
        self.spin_struct_transition.setValue(5.0 * scale)
        self.chk_struct_tagged_children = QtWidgets.QCheckBox("Add structure tags to child sections")
        self.chk_struct_tagged_children.setChecked(True)
        self.chk_struct_apply_overrides = QtWidgets.QCheckBox("Apply structure overrides (reserved)")
        self.chk_struct_apply_overrides.setChecked(False)
        self.lbl_struct_note = QtWidgets.QLabel(
            "When enabled, StructureSet stations are merged into section generation.\n"
            "Transition stations can be added automatically around structure boundaries.\n"
            "Auto transition distance uses structure type and size to derive the boundary spacing.\n"
            "The old manual Structure/Crossing station text workflow is no longer used."
        )
        self.lbl_struct_note.setWordWrap(True)
        form_struct.addRow(self.chk_use_structure_set)
        form_struct.addRow("Structure Source:", self.cmb_structure_source)
        form_struct.addRow(self.chk_struct_start_end)
        form_struct.addRow(self.chk_struct_centers)
        form_struct.addRow(self.chk_struct_transition)
        form_struct.addRow(self.chk_struct_transition_auto)
        form_struct.addRow("Transition Distance:", self.spin_struct_transition)
        form_struct.addRow(self.chk_struct_tagged_children)
        form_struct.addRow(self.chk_struct_apply_overrides)
        form_struct.addRow(self.lbl_struct_note)
        main.addWidget(gb_struct)

        gb_region = QtWidgets.QGroupBox("Region Plan Integration")
        form_region = QtWidgets.QFormLayout(gb_region)
        self.chk_use_region_plan = QtWidgets.QCheckBox("Use linked Region Plan")
        self.chk_use_region_plan.setChecked(False)
        self.cmb_region_source = QtWidgets.QComboBox()
        self.chk_region_boundaries = QtWidgets.QCheckBox("Include region boundaries")
        self.chk_region_boundaries.setChecked(True)
        self.chk_region_transitions = QtWidgets.QCheckBox("Include region transitions")
        self.chk_region_transitions.setChecked(True)
        self.chk_region_apply_overrides = QtWidgets.QCheckBox("Apply region section rules")
        self.chk_region_apply_overrides.setChecked(False)
        self.lbl_region_note = QtWidgets.QLabel(
            "When enabled, the linked Region Plan start/end stations are merged into section generation.\n"
            "TransitionIn/TransitionOut can add extra stations before and after region spans.\n"
            "Optional region section rules currently apply side-policy and daylight-policy overrides."
        )
        self.lbl_region_note.setWordWrap(True)
        form_region.addRow(self.chk_use_region_plan)
        form_region.addRow("Region Plan Source:", self.cmb_region_source)
        form_region.addRow(self.chk_region_boundaries)
        form_region.addRow(self.chk_region_transitions)
        form_region.addRow(self.chk_region_apply_overrides)
        form_region.addRow(self.lbl_region_note)
        main.addWidget(gb_region)

        gb_typ = QtWidgets.QGroupBox("Typical Section Integration")
        form_typ = QtWidgets.QFormLayout(gb_typ)
        self.chk_use_typical = QtWidgets.QCheckBox("Use Typical Section Template")
        self.chk_use_typical.setChecked(False)
        self.cmb_typical_source = QtWidgets.QComboBox()
        self.lbl_typ_note = QtWidgets.QLabel(
            "When enabled, the Typical Section Template defines the finished-grade top profile.\n"
            "Assembly Template still provides corridor depth, side slopes, and daylight defaults."
        )
        self.lbl_typ_note.setWordWrap(True)
        form_typ.addRow(self.chk_use_typical)
        form_typ.addRow("Typical Section Source:", self.cmb_typical_source)
        form_typ.addRow(self.lbl_typ_note)
        main.addWidget(gb_typ)

        gb_opt = QtWidgets.QGroupBox("Options")
        form_opts = QtWidgets.QFormLayout(gb_opt)
        self.chk_create_new = QtWidgets.QCheckBox("Create new SectionSet")
        self.chk_create_new.setChecked(True)
        self.chk_children = QtWidgets.QCheckBox("Create child sections in tree")
        self.chk_children.setChecked(True)
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
        self.chk_left_bench = QtWidgets.QCheckBox("Use Left Bench")
        self.chk_right_bench = QtWidgets.QCheckBox("Use Right Bench")
        self.tbl_left_bench_rows = QtWidgets.QTableWidget(0, 4)
        self.tbl_left_bench_rows.setHorizontalHeaderLabels(list(self._BENCH_HEADERS))
        self.tbl_left_bench_rows.verticalHeader().setVisible(False)
        self.tbl_left_bench_rows.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_left_bench_rows.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tbl_left_bench_rows.setMinimumHeight(110)
        self.tbl_left_bench_rows.horizontalHeader().setStretchLastSection(True)
        self.tbl_right_bench_rows = QtWidgets.QTableWidget(0, 4)
        self.tbl_right_bench_rows.setHorizontalHeaderLabels(list(self._BENCH_HEADERS))
        self.tbl_right_bench_rows.verticalHeader().setVisible(False)
        self.tbl_right_bench_rows.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_right_bench_rows.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tbl_right_bench_rows.setMinimumHeight(110)
        self.tbl_right_bench_rows.horizontalHeader().setStretchLastSection(True)
        self.btn_add_left_bench_row = QtWidgets.QPushButton("Add Row")
        self.btn_remove_left_bench_row = QtWidgets.QPushButton("Remove Row")
        self.btn_add_right_bench_row = QtWidgets.QPushButton("Add Row")
        self.btn_remove_right_bench_row = QtWidgets.QPushButton("Remove Row")
        self.chk_left_bench_to_daylight = QtWidgets.QCheckBox("Repeat first row to daylight")
        self.chk_right_bench_to_daylight = QtWidgets.QCheckBox("Repeat first row to daylight")
        self.chk_daylight = QtWidgets.QCheckBox("Daylight Auto (SectionSet)")
        self.chk_daylight.setChecked(True)
        self.cmb_day_terrain = QtWidgets.QComboBox()
        self.cmb_day_coords = QtWidgets.QComboBox()
        self.cmb_day_coords.addItems(["Local", "World"])
        self.lbl_coord_hint = QtWidgets.QLabel("")
        self.lbl_coord_hint.setWordWrap(True)
        self.btn_pick_day_terrain = QtWidgets.QPushButton("Use Selected Terrain")
        self.spin_day_step = QtWidgets.QDoubleSpinBox()
        self.spin_day_step.setRange(0.2 * scale, 100.0 * scale)
        self.spin_day_step.setDecimals(3)
        self.spin_day_step.setValue(1.0 * scale)
        self.spin_day_max_w = QtWidgets.QDoubleSpinBox()
        self.spin_day_max_w.setRange(1.0 * scale, 10000.0 * scale)
        self.spin_day_max_w.setDecimals(3)
        self.spin_day_max_w.setValue(200.0 * scale)
        self.spin_day_max_delta = QtWidgets.QDoubleSpinBox()
        self.spin_day_max_delta.setRange(0.0, 1000.0 * scale)
        self.spin_day_max_delta.setDecimals(3)
        self.spin_day_max_delta.setValue(6.0 * scale)
        self.btn_make_assembly = QtWidgets.QPushButton("Create/Update Assembly Template")
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        form_opts.addRow(self.chk_create_new)
        form_opts.addRow(self.chk_children)
        form_opts.addRow(self.chk_side)
        form_opts.addRow("Side Width Left:", self.spin_side_w_left)
        form_opts.addRow("Side Width Right:", self.spin_side_w_right)
        form_opts.addRow("Side Slope Left (%):", self.spin_side_s_left)
        form_opts.addRow("Side Slope Right (%):", self.spin_side_s_right)
        row_left_bench_btns = QtWidgets.QHBoxLayout()
        row_left_bench_btns.addWidget(self.btn_add_left_bench_row)
        row_left_bench_btns.addWidget(self.btn_remove_left_bench_row)
        row_left_bench_btns.addStretch(1)
        w_left_bench_btns = QtWidgets.QWidget()
        w_left_bench_btns.setLayout(row_left_bench_btns)
        row_right_bench_btns = QtWidgets.QHBoxLayout()
        row_right_bench_btns.addWidget(self.btn_add_right_bench_row)
        row_right_bench_btns.addWidget(self.btn_remove_right_bench_row)
        row_right_bench_btns.addStretch(1)
        w_right_bench_btns = QtWidgets.QWidget()
        w_right_bench_btns.setLayout(row_right_bench_btns)
        form_opts.addRow(self.chk_left_bench)
        form_opts.addRow("Left Bench Rows:", self.tbl_left_bench_rows)
        form_opts.addRow("", self.chk_left_bench_to_daylight)
        form_opts.addRow("", w_left_bench_btns)
        form_opts.addRow(self.chk_right_bench)
        form_opts.addRow("Right Bench Rows:", self.tbl_right_bench_rows)
        form_opts.addRow("", self.chk_right_bench_to_daylight)
        form_opts.addRow("", w_right_bench_btns)
        form_opts.addRow(self.chk_daylight)
        form_opts.addRow("Daylight Terrain (Mesh):", self.cmb_day_terrain)
        row_coords = QtWidgets.QHBoxLayout()
        row_coords.addWidget(self.cmb_day_coords)
        row_coords.addWidget(self.lbl_coord_hint, 1)
        w_coords = QtWidgets.QWidget()
        w_coords.setLayout(row_coords)
        form_opts.addRow("Daylight Terrain Coords:", w_coords)
        form_opts.addRow(self.btn_pick_day_terrain)
        form_opts.addRow("Daylight Search Step:", self.spin_day_step)
        form_opts.addRow("Daylight Max Search Width:", self.spin_day_max_w)
        form_opts.addRow("Daylight Max Width Delta:", self.spin_day_max_delta)
        form_opts.addRow(self.btn_make_assembly)
        form_opts.addRow(self.btn_refresh)
        main.addWidget(gb_opt)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_generate = QtWidgets.QPushButton("Generate Sections Now")
        self.btn_close = QtWidgets.QPushButton("Close")
        row_btn.addWidget(self.btn_generate)
        row_btn.addWidget(self.btn_close)
        main.addLayout(row_btn)

        self.cmb_mode.currentTextChanged.connect(self._update_mode_ui)
        self.chk_use_structure_set.toggled.connect(self._update_structure_ui)
        self.chk_use_region_plan.toggled.connect(self._update_region_ui)
        self.chk_use_typical.toggled.connect(self._update_typical_ui)
        self.chk_struct_transition.toggled.connect(self._update_structure_ui)
        self.chk_struct_transition_auto.toggled.connect(self._update_structure_ui)
        self.chk_side.toggled.connect(self._update_side_ui)
        self.chk_left_bench.toggled.connect(self._update_side_ui)
        self.chk_right_bench.toggled.connect(self._update_side_ui)
        self.chk_left_bench_to_daylight.toggled.connect(lambda v: self._on_bench_repeat_to_daylight_toggled("left", v))
        self.chk_right_bench_to_daylight.toggled.connect(lambda v: self._on_bench_repeat_to_daylight_toggled("right", v))
        self.btn_add_left_bench_row.clicked.connect(lambda: self._add_bench_row("left"))
        self.btn_remove_left_bench_row.clicked.connect(lambda: self._remove_bench_row("left"))
        self.btn_add_right_bench_row.clicked.connect(lambda: self._add_bench_row("right"))
        self.btn_remove_right_bench_row.clicked.connect(lambda: self._remove_bench_row("right"))
        self.chk_daylight.toggled.connect(self._update_side_ui)
        self.cmb_day_coords.currentIndexChanged.connect(self._on_day_coord_changed)
        self.cmb_day_terrain.currentIndexChanged.connect(self._on_day_terrain_changed)
        self.btn_pick_day_terrain.clicked.connect(self._use_selected_day_terrain)
        self.btn_make_assembly.clicked.connect(self._create_assembly_template)
        self.btn_refresh.clicked.connect(self._refresh_context)
        self.btn_generate.clicked.connect(self._generate)
        self.btn_close.clicked.connect(self.reject)

        self._update_mode_ui()
        self._update_structure_ui()
        self._update_region_ui()
        self._update_typical_ui()
        self._update_side_ui()
        return w

    def _coord_context_obj(self):
        if self._project is not None:
            return self._project
        return self.doc

    def _update_coord_hint(self):
        self.lbl_coord_hint.setText(coord_hint_text(self._coord_context_obj()))

    def _apply_default_coord_mode(self):
        if self._coord_mode_initialized:
            return
        self._loading = True
        try:
            if should_default_world_mode(self._coord_context_obj()):
                self.cmb_day_coords.setCurrentText("World")
            else:
                self.cmb_day_coords.setCurrentText("Local")
        finally:
            self._loading = False
        self._coord_mode_initialized = True

    def _on_day_coord_changed(self, _v):
        if self._loading:
            return
        self._update_coord_hint()

    def _terrain_declared_world_mode(self, terrain_obj):
        if terrain_obj is None:
            return None
        try:
            mode = str(getattr(terrain_obj, "OutputCoords", "") or "")
            if mode == "World":
                return True
            if mode == "Local":
                return False
        except Exception:
            pass
        try:
            if getattr(terrain_obj, "Proxy", None) and getattr(terrain_obj.Proxy, "Type", "") == "PointCloudDEM":
                return False
        except Exception:
            pass
        return None

    def _sync_day_coord_mode_from_selected_terrain(self):
        terr = self._current_daylight_terrain()
        auto_world = self._terrain_declared_world_mode(terr)
        if auto_world is None:
            return
        self._loading = True
        try:
            self.cmb_day_coords.setCurrentText("World" if auto_world else "Local")
        finally:
            self._loading = False

    def _on_day_terrain_changed(self, _v):
        if self._loading:
            return
        self._sync_day_coord_mode_from_selected_terrain()
        self._update_coord_hint()

    def _update_mode_ui(self):
        is_range = (self.cmb_mode.currentText() == "Range")
        self.spin_start.setEnabled(is_range)
        self.spin_end.setEnabled(is_range)
        self.spin_itv.setEnabled(is_range)
        self.txt_manual.setEnabled(not is_range)
        self.chk_include_ip_keys.setEnabled(is_range)
        self.chk_include_sccs_keys.setEnabled(is_range)

    def _update_structure_ui(self):
        on = bool(self.chk_use_structure_set.isChecked())
        self.cmb_structure_source.setEnabled(on)
        self.chk_struct_start_end.setEnabled(on)
        self.chk_struct_centers.setEnabled(on)
        self.chk_struct_transition.setEnabled(on)
        self.chk_struct_transition_auto.setEnabled(on and bool(self.chk_struct_transition.isChecked()))
        self.spin_struct_transition.setEnabled(
            on and bool(self.chk_struct_transition.isChecked()) and (not bool(self.chk_struct_transition_auto.isChecked()))
        )
        self.chk_struct_tagged_children.setEnabled(on)
        self.chk_struct_apply_overrides.setEnabled(on)

    def _update_region_ui(self):
        on = bool(self.chk_use_region_plan.isChecked())
        self.cmb_region_source.setEnabled(on and len(self._regions) > 0)
        self.chk_region_boundaries.setEnabled(on)
        self.chk_region_transitions.setEnabled(on)

    def _update_typical_ui(self):
        on = bool(self.chk_use_typical.isChecked())
        self.cmb_typical_source.setEnabled(on and len(self._typicals) > 0)

    def _update_side_ui(self):
        on = bool(self.chk_side.isChecked())
        scale = get_length_scale(self.doc, default=1.0)
        if on:
            if float(self.spin_side_w_left.value()) <= 1e-9:
                self.spin_side_w_left.setValue(2.0 * scale)
            if float(self.spin_side_w_right.value()) <= 1e-9:
                self.spin_side_w_right.setValue(2.0 * scale)
        left_bench_on = on and bool(self.chk_left_bench.isChecked())
        right_bench_on = on and bool(self.chk_right_bench.isChecked())
        if left_bench_on:
            if int(self.tbl_left_bench_rows.rowCount()) <= 0:
                self._insert_bench_table_row("left", self._default_bench_row("left"))
        if right_bench_on:
            if int(self.tbl_right_bench_rows.rowCount()) <= 0:
                self._insert_bench_table_row("right", self._default_bench_row("right"))
        self.spin_side_w_left.setEnabled(on)
        self.spin_side_w_right.setEnabled(on)
        self.spin_side_s_left.setEnabled(on)
        self.spin_side_s_right.setEnabled(on)
        self.chk_left_bench.setEnabled(on)
        self.chk_right_bench.setEnabled(on)
        self.chk_left_bench_to_daylight.setEnabled(left_bench_on)
        self.chk_right_bench_to_daylight.setEnabled(right_bench_on)
        self.tbl_left_bench_rows.setEnabled(left_bench_on)
        self.tbl_right_bench_rows.setEnabled(right_bench_on)
        left_repeat = left_bench_on and bool(self.chk_left_bench_to_daylight.isChecked())
        right_repeat = right_bench_on and bool(self.chk_right_bench_to_daylight.isChecked())
        self.btn_add_left_bench_row.setEnabled(left_bench_on and (not left_repeat))
        self.btn_remove_left_bench_row.setEnabled(left_bench_on and (not left_repeat))
        self.btn_add_right_bench_row.setEnabled(right_bench_on and (not right_repeat))
        self.btn_remove_right_bench_row.setEnabled(right_bench_on and (not right_repeat))
        self.chk_daylight.setEnabled(on)
        self.cmb_day_terrain.setEnabled(on and bool(self.chk_daylight.isChecked()))
        self.cmb_day_coords.setEnabled(on and bool(self.chk_daylight.isChecked()))
        self.btn_pick_day_terrain.setEnabled(on and bool(self.chk_daylight.isChecked()))
        self.spin_day_step.setEnabled(on and bool(self.chk_daylight.isChecked()))
        self.spin_day_max_w.setEnabled(on and bool(self.chk_daylight.isChecked()))
        self.spin_day_max_delta.setEnabled(on and bool(self.chk_daylight.isChecked()))

    def _format_obj(self, obj):
        return f"[Mesh] {obj.Label} ({obj.Name})"

    def _format_structure_obj(self, obj):
        return f"[StructureSet] {obj.Label} ({obj.Name})"

    def _format_region_obj(self, obj):
        return f"[Region Plan] {obj.Label} ({obj.Name})"

    def _format_typical_obj(self, obj):
        return f"[TypicalSectionTemplate] {obj.Label} ({obj.Name})"

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

    def _fill_structure_combo(self, combo, objects, selected=None, kind="structure"):
        combo.clear()
        combo.addItem("[None]")
        for o in objects:
            if kind == "typical":
                combo.addItem(self._format_typical_obj(o))
            elif kind == "region":
                combo.addItem(self._format_region_obj(o))
            else:
                combo.addItem(self._format_structure_obj(o))
        idx = 0
        if selected is not None:
            for i, o in enumerate(objects):
                if o == selected:
                    idx = i + 1
                    break
        combo.setCurrentIndex(idx)

    def _current_daylight_terrain(self):
        i = int(self.cmb_day_terrain.currentIndex())
        if i < 0 or i >= len(self._terrains):
            return None
        return self._terrains[i]

    def _current_structure_source(self):
        i = int(self.cmb_structure_source.currentIndex()) - 1
        if i < 0 or i >= len(self._structures):
            return None
        return self._structures[i]

    def _current_region_source(self):
        i = int(self.cmb_region_source.currentIndex()) - 1
        if i < 0 or i >= len(self._regions):
            return None
        return self._regions[i]

    def _current_typical_source(self):
        i = int(self.cmb_typical_source.currentIndex()) - 1
        if i < 0 or i >= len(self._typicals):
            return None
        return self._typicals[i]

    def _use_selected_day_terrain(self):
        sel = _selected_terrain_source()
        if sel is None:
            QtWidgets.QMessageBox.information(
                None,
                "Generate Sections",
                "No terrain source selected. Select a Mesh object first.",
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
        if hasattr(asm, "UseLeftBench"):
            asm.UseLeftBench = bool(self.chk_left_bench.isChecked())
        if hasattr(asm, "UseRightBench"):
            asm.UseRightBench = bool(self.chk_right_bench.isChecked())
        left_rows = self._bench_rows_from_table("left")
        right_rows = self._bench_rows_from_table("right")
        if bool(self.chk_left_bench.isChecked()) and not left_rows:
            left_rows = [self._default_bench_row("left")]
        if bool(self.chk_right_bench.isChecked()) and not right_rows:
            right_rows = [self._default_bench_row("right")]
        left_rows = [row for row in left_rows if row is not None]
        right_rows = [row for row in right_rows if row is not None]
        if bool(self.chk_left_bench_to_daylight.isChecked()) and left_rows:
            left_rows = left_rows[:1]
        if bool(self.chk_right_bench_to_daylight.isChecked()) and right_rows:
            right_rows = right_rows[:1]
        if hasattr(asm, "LeftBenchDrop"):
            asm.LeftBenchDrop = float(left_rows[0].get("drop", 0.0) or 0.0) if left_rows else 0.0
        if hasattr(asm, "RightBenchDrop"):
            asm.RightBenchDrop = float(right_rows[0].get("drop", 0.0) or 0.0) if right_rows else 0.0
        if hasattr(asm, "LeftBenchWidth"):
            asm.LeftBenchWidth = float(left_rows[0].get("width", 0.0) or 0.0) if left_rows else 0.0
        if hasattr(asm, "RightBenchWidth"):
            asm.RightBenchWidth = float(right_rows[0].get("width", 0.0) or 0.0) if right_rows else 0.0
        if hasattr(asm, "LeftBenchSlopePct"):
            asm.LeftBenchSlopePct = float(left_rows[0].get("slope", 0.0) or 0.0) if left_rows else 0.0
        if hasattr(asm, "RightBenchSlopePct"):
            asm.RightBenchSlopePct = float(right_rows[0].get("slope", 0.0) or 0.0) if right_rows else 0.0
        if hasattr(asm, "LeftPostBenchSlopePct"):
            asm.LeftPostBenchSlopePct = float(left_rows[0].get("post_slope", self.spin_side_s_left.value()) or self.spin_side_s_left.value()) if left_rows else float(self.spin_side_s_left.value())
        if hasattr(asm, "RightPostBenchSlopePct"):
            asm.RightPostBenchSlopePct = float(right_rows[0].get("post_slope", self.spin_side_s_right.value()) or self.spin_side_s_right.value()) if right_rows else float(self.spin_side_s_right.value())
        if hasattr(asm, "LeftBenchRows"):
            asm.LeftBenchRows = [str(self._bench_row_to_storage(row)).strip() for row in left_rows if str(self._bench_row_to_storage(row)).strip()]
        if hasattr(asm, "RightBenchRows"):
            asm.RightBenchRows = [str(self._bench_row_to_storage(row)).strip() for row in right_rows if str(self._bench_row_to_storage(row)).strip()]
        if hasattr(asm, "LeftBenchRepeatToDaylight"):
            asm.LeftBenchRepeatToDaylight = bool(self.chk_left_bench_to_daylight.isChecked())
        if hasattr(asm, "RightBenchRepeatToDaylight"):
            asm.RightBenchRepeatToDaylight = bool(self.chk_right_bench_to_daylight.isChecked())
        if hasattr(asm, "UseDaylightToTerrain"):
            asm.UseDaylightToTerrain = bool(self.chk_daylight.isChecked())
        if hasattr(asm, "DaylightSearchStep"):
            asm.DaylightSearchStep = float(self.spin_day_step.value())
        if hasattr(asm, "DaylightMaxSearchWidth"):
            asm.DaylightMaxSearchWidth = float(self.spin_day_max_w.value())
        if hasattr(asm, "DaylightMaxWidthDelta"):
            asm.DaylightMaxWidthDelta = float(self.spin_day_max_delta.value())

    def _resolve_template_base(self):
        src = _find_source_centerline_display(self.doc)
        if src is not None and getattr(src, "Alignment", None) is not None:
            try:
                from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
                p0 = HorizontalAlignment.point_at_station(src.Alignment, 0.0)
                return App.Vector(float(p0.x), float(p0.y), float(p0.z))
            except Exception:
                pass
        return App.Vector(0.0, 0.0, 0.0)

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return

        src = _find_source_centerline_display(self.doc)
        asm = _find_first_by_proxy_type(self.doc, "AssemblyTemplate")
        sec = _find_first_by_proxy_type(self.doc, "SectionSet")
        aln = _find_alignment(self.doc)
        prj = _find_project(self.doc)
        self._structures = _find_structure_sets(self.doc)
        self._regions = _find_region_sets(self.doc)
        self._typicals = _find_typical_section_templates(self.doc)
        self._project = prj
        self._apply_default_coord_mode()
        self._update_coord_hint()
        self._terrains = _find_terrain_sources(self.doc)

        pref_terrain = None
        if sec is not None and hasattr(sec, "TerrainMesh"):
            pref_terrain = getattr(sec, "TerrainMesh", None)
        if pref_terrain is None and prj is not None and hasattr(prj, "Terrain"):
            pref_terrain = getattr(prj, "Terrain", None)
        if pref_terrain is not None and (not _is_mesh_obj(pref_terrain)):
            pref_terrain = None
        sel_terrain = _selected_terrain_source()
        if sel_terrain is not None:
            pref_terrain = sel_terrain
        self._fill_combo(self.cmb_day_terrain, self._terrains, pref_terrain)
        self._sync_day_coord_mode_from_selected_terrain()

        pref_structure = None
        if sec is not None and hasattr(sec, "StructureSet"):
            pref_structure = getattr(sec, "StructureSet", None)
        if pref_structure is None and prj is not None and hasattr(prj, "StructureSet"):
            pref_structure = getattr(prj, "StructureSet", None)
        self._fill_structure_combo(self.cmb_structure_source, self._structures, pref_structure)

        pref_region = None
        if sec is not None:
            pref_region = resolve_region_plan_source(sec)
        if pref_region is None and prj is not None:
            pref_region = getattr(prj, "RegionPlan", None) if hasattr(prj, "RegionPlan") else None
        self._fill_structure_combo(self.cmb_region_source, self._regions, pref_region, kind="region")

        pref_typical = None
        if sec is not None and hasattr(sec, "TypicalSectionTemplate"):
            pref_typical = getattr(sec, "TypicalSectionTemplate", None)
        if pref_typical is None and prj is not None and hasattr(prj, "TypicalSectionTemplate"):
            pref_typical = getattr(prj, "TypicalSectionTemplate", None)
        self._fill_structure_combo(self.cmb_typical_source, self._typicals, pref_typical, kind="typical")

        if sec is not None:
            try:
                ensure_section_set_properties(sec)
                if hasattr(sec, "Mode"):
                    self.cmb_mode.setCurrentText(str(sec.Mode or "Range"))
                if hasattr(sec, "StartStation"):
                    self.spin_start.setValue(float(sec.StartStation))
                if hasattr(sec, "EndStation"):
                    self.spin_end.setValue(float(sec.EndStation))
                if hasattr(sec, "Interval"):
                    self.spin_itv.setValue(float(sec.Interval))
                if hasattr(sec, "StationText"):
                    self.txt_manual.setPlainText(str(sec.StationText or ""))
                if hasattr(sec, "DaylightAuto"):
                    self.chk_daylight.setChecked(bool(sec.DaylightAuto))
                if hasattr(sec, "TerrainMeshCoords"):
                    mode = str(getattr(sec, "TerrainMeshCoords", "Local") or "Local")
                    self._loading = True
                    try:
                        self.cmb_day_coords.setCurrentText("World" if mode == "World" else "Local")
                    finally:
                        self._loading = False
                if hasattr(sec, "IncludeAlignmentIPStations"):
                    self.chk_include_ip_keys.setChecked(bool(sec.IncludeAlignmentIPStations))
                if hasattr(sec, "IncludeAlignmentSCCSStations"):
                    self.chk_include_sccs_keys.setChecked(bool(sec.IncludeAlignmentSCCSStations))
                if hasattr(sec, "UseStructureSet"):
                    self.chk_use_structure_set.setChecked(bool(sec.UseStructureSet))
                self.chk_use_region_plan.setChecked(bool(region_plan_usage_enabled(sec)))
                if hasattr(sec, "ApplyRegionOverrides"):
                    self.chk_region_apply_overrides.setChecked(bool(sec.ApplyRegionOverrides))
                if hasattr(sec, "UseTypicalSectionTemplate"):
                    self.chk_use_typical.setChecked(bool(sec.UseTypicalSectionTemplate))
                if hasattr(sec, "IncludeStructureStartEnd"):
                    self.chk_struct_start_end.setChecked(bool(sec.IncludeStructureStartEnd))
                if hasattr(sec, "IncludeStructureCenters"):
                    self.chk_struct_centers.setChecked(bool(sec.IncludeStructureCenters))
                if hasattr(sec, "IncludeStructureTransitionStations"):
                    self.chk_struct_transition.setChecked(bool(sec.IncludeStructureTransitionStations))
                if hasattr(sec, "AutoStructureTransitionDistance"):
                    self.chk_struct_transition_auto.setChecked(bool(sec.AutoStructureTransitionDistance))
                if hasattr(sec, "StructureTransitionDistance"):
                    self.spin_struct_transition.setValue(float(sec.StructureTransitionDistance))
                if hasattr(sec, "CreateStructureTaggedChildren"):
                    self.chk_struct_tagged_children.setChecked(bool(sec.CreateStructureTaggedChildren))
                if hasattr(sec, "ApplyStructureOverrides"):
                    self.chk_struct_apply_overrides.setChecked(bool(sec.ApplyStructureOverrides))
                if hasattr(sec, "IncludeRegionBoundaries"):
                    self.chk_region_boundaries.setChecked(bool(sec.IncludeRegionBoundaries))
                if hasattr(sec, "IncludeRegionTransitions"):
                    self.chk_region_transitions.setChecked(bool(sec.IncludeRegionTransitions))
            except Exception:
                pass

        if asm is not None:
            try:
                ensure_assembly_template_properties(asm)
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
                if hasattr(asm, "UseLeftBench"):
                    self.chk_left_bench.setChecked(bool(asm.UseLeftBench))
                if hasattr(asm, "UseRightBench"):
                    self.chk_right_bench.setChecked(bool(asm.UseRightBench))
                if hasattr(asm, "LeftBenchRepeatToDaylight"):
                    self.chk_left_bench_to_daylight.setChecked(bool(asm.LeftBenchRepeatToDaylight))
                if hasattr(asm, "RightBenchRepeatToDaylight"):
                    self.chk_right_bench_to_daylight.setChecked(bool(asm.RightBenchRepeatToDaylight))
                self._set_bench_table_rows("left", self._assembly_bench_rows(asm, "left"))
                self._set_bench_table_rows("right", self._assembly_bench_rows(asm, "right"))
                if bool(self.chk_left_bench_to_daylight.isChecked()):
                    self._trim_bench_rows_to_first("left")
                if bool(self.chk_right_bench_to_daylight.isChecked()):
                    self._trim_bench_rows_to_first("right")
                # Backward-compat fallback: if SectionSet.DaylightAuto is not available,
                # keep using legacy AssemblyTemplate.UseDaylightToTerrain.
                if (sec is None or (not hasattr(sec, "DaylightAuto"))) and hasattr(asm, "UseDaylightToTerrain"):
                    self.chk_daylight.setChecked(bool(asm.UseDaylightToTerrain))
                if hasattr(asm, "DaylightSearchStep"):
                    self.spin_day_step.setValue(float(asm.DaylightSearchStep))
                if hasattr(asm, "DaylightMaxSearchWidth"):
                    self.spin_day_max_w.setValue(float(asm.DaylightMaxSearchWidth))
                if hasattr(asm, "DaylightMaxWidthDelta"):
                    self.spin_day_max_delta.setValue(float(asm.DaylightMaxWidthDelta))
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
        msg.append(f"StructureSet sources: {len(self._structures)} found")
        msg.append(f"Region plan sources: {len(self._regions)} found")
        msg.append(f"Typical section templates: {len(self._typicals)} found")
        msg.append(f"Terrain candidates: {len(self._terrains)} found (Mesh only)")
        if pref_terrain is not None:
            msg.append(f"Daylight terrain: {pref_terrain.Label} ({pref_terrain.Name})")
        if pref_structure is not None:
            msg.append(f"Structure source: {pref_structure.Label} ({pref_structure.Name})")
        if pref_region is not None:
            msg.append(f"Region plan source: {pref_region.Label} ({pref_region.Name})")
        if pref_typical is not None:
            msg.append(f"Typical section source: {pref_typical.Label} ({pref_typical.Name})")
        msg.append(f"Daylight terrain coords: {self.cmb_day_coords.currentText()}")
        msg.append("")
        msg.append("Workflow:")
        msg.append("1) Select mode (Range or Manual)")
        msg.append("2) Generate to create/update SectionSet")
        msg.append("   - Range mode can include PI and TS/SC/CS/ST key stations automatically")
        msg.append("   - StructureSet integration can merge start/end/center and optional transition stations")
        msg.append("   - Region Plan integration can merge region boundaries and optional transition stations")
        msg.append("   - Typical Section Template can replace the simple top-profile width model")
        msg.append("3) Side slopes are optional (AssemblyTemplate.UseSideSlopes)")
        msg.append("   - Height Left/Right and other template geometry values are edited in the Assembly Template property editor")
        msg.append("4) Daylight Auto uses Terrain source (Project.Terrain / SectionSet.TerrainMesh, Mesh only)")
        msg.append("   - Daylight terrain coordinate mode can be Local or World")
        self.lbl_info.setText("\n".join(msg))
        self._sync_day_coord_mode_from_selected_terrain()
        self._update_side_ui()
        self._update_mode_ui()
        self._update_structure_ui()
        self._update_region_ui()
        self._update_typical_ui()

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

    def _resolve_typical_section(self):
        typ = self._current_typical_source()
        if typ is not None:
            return typ
        typ = _find_first_by_proxy_type(self.doc, "TypicalSectionTemplate")
        if typ is not None:
            return typ
        typ = self.doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
        TypicalSectionTemplate(typ)
        ViewProviderTypicalSectionTemplate(typ.ViewObject)
        typ.Label = "Typical Section Template"
        typ.touch()
        self.doc.recompute()
        return typ

    def _resolve_section_set(self):
        if bool(self.chk_create_new.isChecked()):
            return None
        return _find_first_by_proxy_type(self.doc, "SectionSet")

    def _create_or_get_section_set(self):
        sec = self._resolve_section_set()
        if sec is not None:
            try:
                ensure_section_set_properties(sec)
            except Exception:
                pass
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

    def _preflight_warnings(self, src, asm, struct_src, reg_src, typ_src):
        warnings = []
        if src is None or asm is None:
            return warnings

        if bool(self.chk_daylight.isChecked()) and self._current_daylight_terrain() is None:
            prj0 = _find_project(self.doc)
            fallback_terrain = getattr(prj0, "Terrain", None) if prj0 is not None and hasattr(prj0, "Terrain") else None
            if not _is_mesh_obj(fallback_terrain):
                warnings.append("Daylight Auto is enabled without a mesh terrain source. Section generation will fall back to fixed side widths.")

        if bool(self.chk_use_structure_set.isChecked()) and struct_src is not None:
            if bool(self.chk_struct_apply_overrides.isChecked()):
                warnings.append("Apply structure overrides is still partial/reserved behavior. Daylight and side-slope edits may remain simplified.")
            try:
                ext_count = sum(
                    1
                    for rec in list(StructureSetSource.records(struct_src) or [])
                    if str(rec.get("GeometryMode", "") or "").strip().lower() == "external_shape"
                )
            except Exception:
                ext_count = 0
            if ext_count > 0:
                warnings.append(
                    f"StructureSet contains {int(ext_count)} external_shape record(s). Current section/corridor logic can use only an indirect bounding-box proxy when the source loads; direct solid consumption is still unsupported."
                )

        if bool(self.chk_use_typical.isChecked()) and typ_src is not None:
            warnings.append("Typical Section replaces the simple top-profile source, while Assembly Template still controls corridor depth and daylight defaults.")

        if bool(self.chk_use_region_plan.isChecked()) and reg_src is not None:
            try:
                reg_issues = list(RegionPlanSource.validate(reg_src) or [])
            except Exception:
                reg_issues = []
            if reg_issues:
                warnings.append(f"Region Plan reports {len(reg_issues)} validation warning(s). Review region overlaps, gaps, or zero-length spans if the station list looks unexpected.")

        return warnings

    def _generate(self):
        if self.doc is None:
            return

        src = self._resolve_source_display()
        asm = self._resolve_assembly()
        sec = self._create_or_get_section_set()
        struct_src = self._current_structure_source()
        reg_src = self._current_region_source()
        typ_src = self._resolve_typical_section() if bool(self.chk_use_typical.isChecked()) else self._current_typical_source()

        if bool(self.chk_use_structure_set.isChecked()) and struct_src is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Generate Sections",
                "Use StructureSet is enabled, but no StructureSet source is selected.",
            )
            return
        if bool(self.chk_use_region_plan.isChecked()) and reg_src is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Generate Sections",
                "Use Region Plan is enabled, but no Region Plan source is selected.",
            )
            return
        if bool(self.chk_use_typical.isChecked()) and typ_src is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Generate Sections",
                "Use Typical Section Template is enabled, but no Typical Section source is selected.",
            )
            return

        preflight = self._preflight_warnings(src, asm, struct_src, reg_src, typ_src)
        if preflight:
            reply = QtWidgets.QMessageBox.question(
                None,
                "Generate Sections",
                "Generate with warnings?\n\n" + "\n".join([f"- {line}" for line in preflight]),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        try:
            self._set_suspend_recompute(sec, True)
            sec.SourceCenterlineDisplay = src
            sec.AssemblyTemplate = asm
            if hasattr(sec, "TypicalSectionTemplate"):
                sec.TypicalSectionTemplate = typ_src
            if hasattr(sec, "UseTypicalSectionTemplate"):
                sec.UseTypicalSectionTemplate = bool(self.chk_use_typical.isChecked())
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
                sec.IncludeStructureStations = False
            if hasattr(sec, "StructureStationText"):
                sec.StructureStationText = ""
            if hasattr(sec, "StructureSet"):
                sec.StructureSet = struct_src
            if hasattr(sec, "UseStructureSet"):
                sec.UseStructureSet = bool(self.chk_use_structure_set.isChecked())
            if hasattr(sec, "IncludeStructureStartEnd"):
                sec.IncludeStructureStartEnd = bool(self.chk_struct_start_end.isChecked())
            if hasattr(sec, "IncludeStructureCenters"):
                sec.IncludeStructureCenters = bool(self.chk_struct_centers.isChecked())
            if hasattr(sec, "IncludeStructureTransitionStations"):
                sec.IncludeStructureTransitionStations = bool(self.chk_struct_transition.isChecked())
            if hasattr(sec, "AutoStructureTransitionDistance"):
                sec.AutoStructureTransitionDistance = bool(self.chk_struct_transition_auto.isChecked())
            if hasattr(sec, "StructureTransitionDistance"):
                sec.StructureTransitionDistance = float(self.spin_struct_transition.value())
            if hasattr(sec, "CreateStructureTaggedChildren"):
                sec.CreateStructureTaggedChildren = bool(self.chk_struct_tagged_children.isChecked())
            if hasattr(sec, "ApplyStructureOverrides"):
                sec.ApplyStructureOverrides = bool(self.chk_struct_apply_overrides.isChecked())
            set_region_plan_source(sec, reg_src, enabled=bool(self.chk_use_region_plan.isChecked()))
            if hasattr(sec, "ApplyRegionOverrides"):
                sec.ApplyRegionOverrides = bool(self.chk_region_apply_overrides.isChecked())
            if hasattr(sec, "IncludeRegionBoundaries"):
                sec.IncludeRegionBoundaries = bool(self.chk_region_boundaries.isChecked())
            if hasattr(sec, "IncludeRegionTransitions"):
                sec.IncludeRegionTransitions = bool(self.chk_region_transitions.isChecked())
            sec.CreateChildSections = bool(self.chk_children.isChecked())
            if hasattr(sec, "DaylightAuto"):
                sec.DaylightAuto = bool(self.chk_daylight.isChecked())
            if hasattr(sec, "TerrainMeshCoords"):
                sec.TerrainMeshCoords = str(self.cmb_day_coords.currentText() or "Local")
            try:
                if hasattr(sec, "TerrainMesh"):
                    terr = self._current_daylight_terrain()
                    if terr is not None and _is_mesh_obj(terr):
                        sec.TerrainMesh = terr
                    else:
                        prj0 = _find_project(self.doc)
                        if prj0 is not None and hasattr(prj0, "Terrain") and _is_mesh_obj(prj0.Terrain):
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
            assign_project_region_plan(prj, reg_src)
            link_project(
                prj,
                links={
                    "Centerline3DDisplay": src,
                    "AssemblyTemplate": asm,
                    "TypicalSectionTemplate": typ_src,
                    "RegionPlan": reg_src,
                    "SectionSet": sec,
                },
                adopt_extra=[src, asm, typ_src, reg_src, sec],
            )

        n = len(list(getattr(sec, "StationValues", []) or []))
        struct_count = int(getattr(sec, "ResolvedStructureCount", 0) or 0)
        region_count = int(getattr(sec, "ResolvedRegionCount", 0) or 0)
        msg = [
            "Section generation completed.",
            f"Resolved stations: {n}",
        ]
        if bool(self.chk_use_structure_set.isChecked()):
            if struct_src is not None:
                msg.append(f"Structure source: {struct_src.Label} ({struct_src.Name})")
            msg.append(f"Merged structure stations: {struct_count}")
            if bool(self.chk_struct_apply_overrides.isChecked()):
                msg.append(f"Override-enabled stations: {max(0, int(getattr(sec, 'StructureOverrideHitCount', 0) or 0))}")
        if bool(self.chk_use_region_plan.isChecked()):
            if reg_src is not None:
                msg.append(f"Region plan source: {reg_src.Label} ({reg_src.Name})")
            msg.append(f"Merged region stations: {region_count}")
            if bool(self.chk_region_apply_overrides.isChecked()):
                msg.append(f"Region override-enabled stations: {max(0, int(getattr(sec, 'RegionOverrideHitCount', 0) or 0))}")
        if bool(self.chk_use_typical.isChecked()) and typ_src is not None:
            msg.append(f"Typical section source: {typ_src.Label} ({typ_src.Name})")
        QtWidgets.QMessageBox.information(
            None,
            "Generate Sections",
            "\n".join(msg),
        )

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass

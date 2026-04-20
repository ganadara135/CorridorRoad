# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_project
from freecad.Corridor_Road.objects import coord_transform as _ct
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_project import (
    assign_project_corridor,
    ensure_corridor_object,
    find_corridor_objects,
    resolve_project_corridor,
)
from freecad.Corridor_Road.objects.obj_cut_fill_calc import CutFillCalc, ViewProviderCutFillCalc, ensure_cut_fill_calc_properties
from freecad.Corridor_Road.objects.project_links import link_project
from freecad.Corridor_Road.ui.common.coord_ui import coord_hint_text, should_default_world_mode
from freecad.Corridor_Road.ui.common.perf_quality import (
    QUALITY_PRESETS,
    apply_preset_to_widgets,
    build_quality_presets,
    estimate_triangle_checks,
    get_preset_values,
    guess_preset_name,
    update_estimate_label,
)


def _is_mesh_obj(obj):
    try:
        return hasattr(obj, "Mesh") and obj.Mesh is not None and int(obj.Mesh.CountFacets) > 0
    except Exception:
        return False


def _find_corridors(doc):
    return find_corridor_objects(doc)


def _find_cut_fill_calc(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        try:
            if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "CutFillCalc":
                return o
        except Exception:
            pass
        if o.Name.startswith("CutFillCalc"):
            return o
    return None


def _find_surface_sources(doc):
    if doc is None:
        return []
    return [o for o in doc.Objects if _is_mesh_obj(o)]


def _selected_surface():
    try:
        sel = list(Gui.Selection.getSelection() or [])
        for o in sel:
            if _is_mesh_obj(o):
                return o
    except Exception:
        pass
    return None


class CutFillCalcTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._project = None
        self._quality_presets = build_quality_presets(
            self._display_scale(),
            {
                "Fast": 120000,
                "Balanced": 200000,
                "Precise": 500000,
            },
        )
        self._corridors = []
        self._surfaces = []
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
        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Cut-Fill Calc")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        gb_src = QtWidgets.QGroupBox("Source")
        fs = QtWidgets.QFormLayout(gb_src)
        self.cmb_corridor = QtWidgets.QComboBox()
        self.cmb_surface = QtWidgets.QComboBox()
        self.cmb_surface_coords = QtWidgets.QComboBox()
        self.cmb_surface_coords.addItems(["Local", "World"])
        self.lbl_coord_hint = QtWidgets.QLabel("")
        self.lbl_coord_hint.setWordWrap(True)
        self.btn_pick_sel = QtWidgets.QPushButton("Use Selected Mesh")
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fs.addRow("Design Corridor:", self.cmb_corridor)
        fs.addRow("Existing Mesh:", self.cmb_surface)
        row_coords = QtWidgets.QHBoxLayout()
        row_coords.addWidget(self.cmb_surface_coords)
        row_coords.addWidget(self.lbl_coord_hint, 1)
        w_coords = QtWidgets.QWidget()
        w_coords.setLayout(row_coords)
        fs.addRow("Existing Mesh Coords:", w_coords)
        fs.addRow(self.btn_pick_sel)
        fs.addRow(self.btn_refresh)
        main.addWidget(gb_src)

        gb_opt = QtWidgets.QGroupBox("Comparison")
        form_opts = QtWidgets.QFormLayout(gb_opt)
        unit = self._display_unit()
        display_scale = self._display_scale()
        self.cmb_quality = QtWidgets.QComboBox()
        self.cmb_quality.addItems(list(QUALITY_PRESETS))
        self.cmb_quality.setCurrentText("Balanced")
        self.spin_cell = QtWidgets.QDoubleSpinBox()
        self.spin_cell.setRange(0.2 * display_scale, 10000.0 * display_scale)
        self.spin_cell.setDecimals(3)
        self.spin_cell.setSuffix(f" {unit}")
        self.spin_cell.setValue(self._meters_to_display(1.0))
        self.spin_max_samples = QtWidgets.QSpinBox()
        self.spin_max_samples.setRange(1000, 2000000000)
        self.spin_max_samples.setValue(200000)
        self.spin_max_tri_src = QtWidgets.QSpinBox()
        self.spin_max_tri_src.setRange(1000, 2000000000)
        self.spin_max_tri_src.setValue(150000)
        self.spin_max_cand = QtWidgets.QSpinBox()
        self.spin_max_cand.setRange(100, 2000000000)
        self.spin_max_cand.setValue(2500)
        self.spin_max_checks = QtWidgets.QSpinBox()
        self.spin_max_checks.setRange(100000, 2000000000)
        self.spin_max_checks.setSingleStep(10000000)
        self.spin_max_checks.setValue(250000000)
        self.spin_min_facets = QtWidgets.QSpinBox()
        self.spin_min_facets.setRange(1, 2000000000)
        self.spin_min_facets.setValue(100)
        self.chk_use_bounds = QtWidgets.QCheckBox("Use corridor bounds")
        self.chk_use_bounds.setChecked(True)
        self.cmb_domain_coords = QtWidgets.QComboBox()
        self.cmb_domain_coords.addItems(["Local", "World"])
        self.cmb_domain_coords.setCurrentText("Local")
        self.spin_margin = QtWidgets.QDoubleSpinBox()
        self.spin_margin.setRange(0.0, 1000000.0 * display_scale)
        self.spin_margin.setDecimals(3)
        self.spin_margin.setSuffix(f" {unit}")
        self.spin_margin.setValue(self._meters_to_display(5.0))
        self.spin_nodata_warn = QtWidgets.QDoubleSpinBox()
        self.spin_nodata_warn.setRange(0.0, 100.0)
        self.spin_nodata_warn.setDecimals(1)
        self.spin_nodata_warn.setSuffix(" %")
        self.spin_nodata_warn.setValue(5.0)
        self.spin_xmin = QtWidgets.QDoubleSpinBox()
        self.spin_xmax = QtWidgets.QDoubleSpinBox()
        self.spin_ymin = QtWidgets.QDoubleSpinBox()
        self.spin_ymax = QtWidgets.QDoubleSpinBox()
        for s in (self.spin_xmin, self.spin_xmax, self.spin_ymin, self.spin_ymax):
            s.setRange(-1.0e9, 1.0e9)
            s.setDecimals(3)
            s.setSuffix(f" {unit}")
            s.setValue(0.0)

        self.chk_auto = QtWidgets.QCheckBox("Auto update on source changes")
        self.chk_auto.setChecked(True)
        self.lbl_sign = QtWidgets.QLabel("Sign: delta=Design-Existing, +Fill / -Cut")
        self.lbl_est = QtWidgets.QLabel("Estimate: -")
        self.lbl_est.setWordWrap(True)

        form_opts.addRow("Quality Preset:", self.cmb_quality)
        form_opts.addRow(f"Cell Size ({unit}):", self.spin_cell)
        form_opts.addRow("Max Samples:", self.spin_max_samples)
        form_opts.addRow("Max Triangles/Source:", self.spin_max_tri_src)
        form_opts.addRow("Max Candidate Triangles:", self.spin_max_cand)
        form_opts.addRow("Max Triangle Checks:", self.spin_max_checks)
        form_opts.addRow("Min Mesh Facets:", self.spin_min_facets)
        form_opts.addRow(self.chk_use_bounds)
        form_opts.addRow("Manual Domain Coords:", self.cmb_domain_coords)
        form_opts.addRow(f"Domain Margin ({unit}):", self.spin_margin)
        form_opts.addRow("NoData Warn:", self.spin_nodata_warn)
        form_opts.addRow("X Min:", self.spin_xmin)
        form_opts.addRow("X Max:", self.spin_xmax)
        form_opts.addRow("Y Min:", self.spin_ymin)
        form_opts.addRow("Y Max:", self.spin_ymax)
        form_opts.addRow(self.chk_auto)
        form_opts.addRow(self.lbl_sign)
        form_opts.addRow("Estimate:", self.lbl_est)
        main.addWidget(gb_opt)

        gb_vis = QtWidgets.QGroupBox("3D Display")
        fv = QtWidgets.QFormLayout(gb_vis)
        self.chk_show_map = QtWidgets.QCheckBox("Show Cut/Fill Map in 3D")
        self.chk_show_map.setChecked(True)
        self.spin_deadband = QtWidgets.QDoubleSpinBox()
        self.spin_deadband.setRange(0.0, 100.0 * display_scale)
        self.spin_deadband.setDecimals(3)
        self.spin_deadband.setSuffix(f" {unit}")
        self.spin_deadband.setValue(self._meters_to_display(0.02))
        self.spin_clamp = QtWidgets.QDoubleSpinBox()
        self.spin_clamp.setRange(0.001 * display_scale, 10000.0 * display_scale)
        self.spin_clamp.setDecimals(3)
        self.spin_clamp.setSuffix(f" {unit}")
        self.spin_clamp.setValue(self._meters_to_display(2.0))
        self.spin_zoff = QtWidgets.QDoubleSpinBox()
        self.spin_zoff.setRange(-1000.0 * display_scale, 1000.0 * display_scale)
        self.spin_zoff.setDecimals(3)
        self.spin_zoff.setSuffix(f" {unit}")
        self.spin_zoff.setValue(self._meters_to_display(0.05))
        self.spin_max_vis = QtWidgets.QSpinBox()
        self.spin_max_vis.setRange(1000, 2000000000)
        self.spin_max_vis.setValue(40000)
        self.lbl_palette = QtWidgets.QLabel("Palette: Cut=Red, Fill=Blue, Neutral=Light Gray, NoData=Gray")
        self.lbl_palette.setWordWrap(True)
        fv.addRow(self.chk_show_map)
        fv.addRow(f"Deadband |delta| ({unit}):", self.spin_deadband)
        fv.addRow(f"Clamp |delta| ({unit}):", self.spin_clamp)
        fv.addRow(f"Visual Z Offset ({unit}):", self.spin_zoff)
        fv.addRow("Max Visual Cells:", self.spin_max_vis)
        fv.addRow(self.lbl_palette)
        main.addWidget(gb_vis)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_generate = QtWidgets.QPushButton("Run Cut-Fill Calc")
        self.btn_close = QtWidgets.QPushButton("Close")
        row_btn.addWidget(self.btn_generate)
        row_btn.addWidget(self.btn_close)
        main.addLayout(row_btn)

        gb_run = QtWidgets.QGroupBox("Run")
        fr = QtWidgets.QFormLayout(gb_run)
        self.lbl_run = QtWidgets.QLabel("Idle")
        self.pbar = QtWidgets.QProgressBar()
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        fr.addRow("Status:", self.lbl_run)
        fr.addRow("Progress:", self.pbar)
        fr.addRow(self.btn_cancel)
        main.addWidget(gb_run)

        self._cancel_requested = False
        self._running = False

        self.chk_use_bounds.toggled.connect(self._update_bounds_ui)
        self.btn_pick_sel.clicked.connect(self._use_selected_surface)
        self.btn_refresh.clicked.connect(self._refresh_context)
        self.btn_generate.clicked.connect(self._generate)
        self.btn_close.clicked.connect(self.reject)
        self.btn_cancel.clicked.connect(self._request_cancel)
        self.cmb_corridor.currentIndexChanged.connect(self._on_source_changed)
        self.cmb_surface.currentIndexChanged.connect(self._on_source_changed)
        self.cmb_surface_coords.currentIndexChanged.connect(self._on_surface_coord_changed)
        self.cmb_quality.currentTextChanged.connect(self._on_quality_changed)
        self.spin_cell.valueChanged.connect(self._on_opt_changed)
        self.spin_max_samples.valueChanged.connect(self._on_opt_changed)
        self.spin_max_tri_src.valueChanged.connect(self._on_opt_changed)
        self.spin_max_cand.valueChanged.connect(self._on_opt_changed)
        self.spin_max_checks.valueChanged.connect(self._on_opt_changed)
        self.spin_margin.valueChanged.connect(self._on_source_changed)
        self.spin_xmin.valueChanged.connect(self._on_source_changed)
        self.spin_xmax.valueChanged.connect(self._on_source_changed)
        self.spin_ymin.valueChanged.connect(self._on_source_changed)
        self.spin_ymax.valueChanged.connect(self._on_source_changed)
        self.chk_use_bounds.toggled.connect(self._on_source_changed)
        self.cmb_domain_coords.currentIndexChanged.connect(self._on_source_changed)

        self._update_bounds_ui()
        return w

    def _coord_context_obj(self):
        if self._project is not None:
            return self._project
        return self.doc

    def _display_unit(self):
        return _units.get_linear_display_unit(self._project or self.doc)

    def _display_scale(self):
        return max(1.0e-9, _units.user_length_from_meters(self._project or self.doc, 1.0))

    def _meters_to_display(self, meters):
        return _units.user_length_from_meters(self._project or self.doc, meters)

    def _display_to_meters(self, value):
        return _units.meters_from_user_length(self._project or self.doc, value, use_default="display")

    def _build_completion_message(self, cmp_obj):
        return "\n".join(
            [
                str(getattr(cmp_obj, "Status", "Done") or "Done"),
                f"Display unit: {self._display_unit()}",
                f"CutVolume: {_units.format_internal_volume(self._project or self.doc, float(getattr(cmp_obj, 'CutVolume', 0.0) or 0.0))}",
                f"FillVolume: {_units.format_internal_volume(self._project or self.doc, float(getattr(cmp_obj, 'FillVolume', 0.0) or 0.0))}",
                f"Delta(min/max/mean): "
                f"{_units.format_internal_length(self._project or self.doc, float(getattr(cmp_obj, 'DeltaMin', 0.0) or 0.0))} / "
                f"{_units.format_internal_length(self._project or self.doc, float(getattr(cmp_obj, 'DeltaMax', 0.0) or 0.0))} / "
                f"{_units.format_internal_length(self._project or self.doc, float(getattr(cmp_obj, 'DeltaMean', 0.0) or 0.0))}",
                f"Samples(valid/total): {int(getattr(cmp_obj, 'ValidCount', 0))} / {int(getattr(cmp_obj, 'SampleCount', 0))}",
                f"NoData(area/ratio): {_units.format_internal_area(self._project or self.doc, float(getattr(cmp_obj, 'NoDataArea', 0.0) or 0.0))} / "
                f"{100.0 * float(getattr(cmp_obj, 'NoDataRatio', 0.0)):.2f}%",
                f"CellSize: {_units.format_length(self._project or self.doc, float(getattr(cmp_obj, 'CellSize', 0.0) or 0.0))}",
                f"DomainCoords: {str(getattr(cmp_obj, 'DomainCoords', 'Local'))}",
                f"ExistingSurfaceCoords: {str(getattr(cmp_obj, 'ExistingSurfaceCoords', 'Local'))}",
                f"MaxTriangles/Source: {int(getattr(cmp_obj, 'MaxTrianglesPerSource', 0))}",
                f"MaxCandidateTriangles: {int(getattr(cmp_obj, 'MaxCandidateTriangles', 0))}",
                f"MaxTriangleChecks: {int(getattr(cmp_obj, 'MaxTriangleChecks', 0))}",
                f"Sign: {str(getattr(cmp_obj, 'SignConvention', 'delta=Design-Existing, +Fill/-Cut'))}",
                f"Display: show_map={bool(getattr(cmp_obj, 'ShowDeltaMap', True))}, "
                f"deadband={_units.format_length(self._project or self.doc, float(getattr(cmp_obj, 'DeltaDeadband', 0.0) or 0.0))}, "
                f"clamp={_units.format_length(self._project or self.doc, float(getattr(cmp_obj, 'DeltaClamp', 0.0) or 0.0))}",
            ]
        )

    def _use_world_surface_mode(self):
        return str(self.cmb_surface_coords.currentText() or "Local") == "World"

    def _update_coord_hint(self):
        self.lbl_coord_hint.setText(coord_hint_text(self._coord_context_obj()))

    def _apply_default_coord_mode(self):
        if self._coord_mode_initialized:
            return
        self._loading = True
        try:
            if should_default_world_mode(self._coord_context_obj()):
                self.cmb_surface_coords.setCurrentText("World")
            else:
                self.cmb_surface_coords.setCurrentText("Local")
        finally:
            self._loading = False
        self._coord_mode_initialized = True

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

    def _current_corridor(self):
        i = int(self.cmb_corridor.currentIndex())
        if i < 0 or i >= len(self._corridors):
            return None
        return self._corridors[i]

    def _current_surface(self):
        i = int(self.cmb_surface.currentIndex())
        if i < 0 or i >= len(self._surfaces):
            return None
        return self._surfaces[i]

    def _update_bounds_ui(self):
        use_bounds = bool(self.chk_use_bounds.isChecked())
        self.spin_margin.setEnabled(use_bounds)
        self.cmb_domain_coords.setEnabled(not use_bounds)
        self.spin_xmin.setEnabled(not use_bounds)
        self.spin_xmax.setEnabled(not use_bounds)
        self.spin_ymin.setEnabled(not use_bounds)
        self.spin_ymax.setEnabled(not use_bounds)

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return

        self._corridors = _find_corridors(self.doc)
        self._surfaces = _find_surface_sources(self.doc)
        prj = find_project(self.doc)
        self._project = prj
        self._apply_default_coord_mode()
        self._update_coord_hint()
        cmp_obj = _find_cut_fill_calc(self.doc)
        if cmp_obj is not None:
            try:
                ensure_cut_fill_calc_properties(cmp_obj)
            except Exception:
                pass
            try:
                if str(getattr(cmp_obj, "Label", "")) in ("", "Existing/Design Surface Comparison"):
                    cmp_obj.Label = "Cut-Fill Calc"
            except Exception:
                pass

        preferred_corridor = None
        preferred_surface = None
        if prj is not None:
            preferred_corridor = resolve_project_corridor(prj)
            preferred_surface = getattr(prj, "Terrain", None)

        if cmp_obj is not None:
            try:
                if getattr(cmp_obj, "SourceCorridor", None) is not None:
                    preferred_corridor = ensure_corridor_object(cmp_obj.SourceCorridor)
                if getattr(cmp_obj, "ExistingSurface", None) is not None:
                    preferred_surface = cmp_obj.ExistingSurface
            except Exception:
                pass

            self._loading = True
            try:
                if hasattr(cmp_obj, "CellSize"):
                    self.spin_cell.setValue(self._meters_to_display(float(cmp_obj.CellSize)))
                if hasattr(cmp_obj, "MaxSamples"):
                    self.spin_max_samples.setValue(int(cmp_obj.MaxSamples))
                if hasattr(cmp_obj, "MaxTrianglesPerSource"):
                    self.spin_max_tri_src.setValue(int(cmp_obj.MaxTrianglesPerSource))
                if hasattr(cmp_obj, "MaxCandidateTriangles"):
                    self.spin_max_cand.setValue(int(cmp_obj.MaxCandidateTriangles))
                if hasattr(cmp_obj, "MaxTriangleChecks"):
                    self.spin_max_checks.setValue(int(cmp_obj.MaxTriangleChecks))
                if hasattr(cmp_obj, "MinMeshFacets"):
                    self.spin_min_facets.setValue(int(cmp_obj.MinMeshFacets))
                if hasattr(cmp_obj, "UseCorridorBounds"):
                    self.chk_use_bounds.setChecked(bool(cmp_obj.UseCorridorBounds))
                if hasattr(cmp_obj, "DomainCoords"):
                    dmode = str(getattr(cmp_obj, "DomainCoords", "Local") or "Local")
                    self.cmb_domain_coords.setCurrentText("World" if dmode == "World" else "Local")
                if hasattr(cmp_obj, "DomainMargin"):
                    self.spin_margin.setValue(self._meters_to_display(float(cmp_obj.DomainMargin)))
                if hasattr(cmp_obj, "NoDataWarnRatio"):
                    self.spin_nodata_warn.setValue(100.0 * float(cmp_obj.NoDataWarnRatio))
                if hasattr(cmp_obj, "ShowDeltaMap"):
                    self.chk_show_map.setChecked(bool(cmp_obj.ShowDeltaMap))
                if hasattr(cmp_obj, "DeltaDeadband"):
                    self.spin_deadband.setValue(self._meters_to_display(float(cmp_obj.DeltaDeadband)))
                if hasattr(cmp_obj, "DeltaClamp"):
                    self.spin_clamp.setValue(self._meters_to_display(float(cmp_obj.DeltaClamp)))
                if hasattr(cmp_obj, "VisualZOffset"):
                    self.spin_zoff.setValue(self._meters_to_display(float(cmp_obj.VisualZOffset)))
                if hasattr(cmp_obj, "MaxVisualCells"):
                    self.spin_max_vis.setValue(int(cmp_obj.MaxVisualCells))
                if hasattr(cmp_obj, "XMin"):
                    self.spin_xmin.setValue(self._meters_to_display(float(cmp_obj.XMin)))
                if hasattr(cmp_obj, "XMax"):
                    self.spin_xmax.setValue(self._meters_to_display(float(cmp_obj.XMax)))
                if hasattr(cmp_obj, "YMin"):
                    self.spin_ymin.setValue(self._meters_to_display(float(cmp_obj.YMin)))
                if hasattr(cmp_obj, "YMax"):
                    self.spin_ymax.setValue(self._meters_to_display(float(cmp_obj.YMax)))
                if hasattr(cmp_obj, "AutoUpdate"):
                    self.chk_auto.setChecked(bool(cmp_obj.AutoUpdate))
                if hasattr(cmp_obj, "ExistingSurfaceCoords"):
                    mode = str(getattr(cmp_obj, "ExistingSurfaceCoords", "Local") or "Local")
                    self.cmb_surface_coords.setCurrentText("World" if mode == "World" else "Local")
            finally:
                self._loading = False

        sel_surface = _selected_surface()
        if sel_surface is not None:
            preferred_surface = sel_surface

        self._fill_combo(self.cmb_corridor, self._corridors, preferred_corridor)
        self._fill_combo(self.cmb_surface, self._surfaces, preferred_surface)
        self._update_bounds_ui()

        msg = []
        msg.append(f"Corridor: {len(self._corridors)} found")
        msg.append(f"Mesh sources: {len(self._surfaces)} found")
        msg.append(f"Existing mesh coords: {'World' if self._use_world_surface_mode() else 'Local'}")
        msg.append(f"Manual X/Y domain coords: {self.cmb_domain_coords.currentText()}")
        if cmp_obj is not None:
            msg.append("Cut-Fill Calc object: FOUND (will update)")
            try:
                msg.append(f"Last status: {getattr(cmp_obj, 'Status', '')}")
            except Exception:
                pass
        else:
            msg.append("Cut-Fill Calc object: NOT FOUND (will create)")
        self.lbl_info.setText("\n".join(msg))
        self._loading = True
        try:
            self.cmb_quality.setCurrentText(self._guess_quality_preset())
        finally:
            self._loading = False
        self._update_estimate_hint()

    def _on_surface_coord_changed(self, _v):
        if self._loading:
            return
        self._update_coord_hint()
        self._on_source_changed(_v)

    def _use_selected_surface(self):
        sel = _selected_surface()
        if sel is None:
            QtWidgets.QMessageBox.information(
                None,
                "Cut-Fill Calc",
                "No mesh selected. Select a Mesh object in tree or 3D view first.",
            )
            return
        for i, o in enumerate(self._surfaces):
            if o == sel:
                self.cmb_surface.setCurrentIndex(i)
                self._update_estimate_hint()
                return
        self._refresh_context()

    def _create_or_get_cut_fill_calc(self):
        cmp_obj = _find_cut_fill_calc(self.doc)
        if cmp_obj is not None:
            try:
                ensure_cut_fill_calc_properties(cmp_obj)
            except Exception:
                pass
            try:
                if str(getattr(cmp_obj, "Label", "")) in ("", "Existing/Design Surface Comparison", "Cut-Fill Calc"):
                    cmp_obj.Label = "Cut-Fill Calc"
            except Exception:
                pass
            return cmp_obj

        cmp_obj = self.doc.addObject("Part::FeaturePython", "CutFillCalc")
        CutFillCalc(cmp_obj)
        ViewProviderCutFillCalc(cmp_obj.ViewObject)
        cmp_obj.Label = "Cut-Fill Calc"
        return cmp_obj

    def _generate(self):
        if bool(getattr(self, "_running", False)):
            QtWidgets.QMessageBox.information(None, "Cut-Fill Calc", "Already running.")
            return

        if self.doc is None:
            return

        corridor = self._current_corridor()
        if corridor is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Cut-Fill Calc",
                "No Corridor selected. Run Build Corridor first.",
            )
            return

        mesh = self._current_surface()
        if mesh is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Cut-Fill Calc",
                "No Existing Mesh selected.",
            )
            return

        mesh_facets = self._mesh_facets(mesh)
        min_facets = int(self.spin_min_facets.value())
        if mesh_facets < min_facets:
            QtWidgets.QMessageBox.warning(
                None,
                "Cut-Fill Calc",
                f"Existing mesh facets {mesh_facets} < Min Mesh Facets {min_facets}.",
            )
            return
        if not self._mesh_xy_valid(mesh):
            QtWidgets.QMessageBox.warning(
                None,
                "Cut-Fill Calc",
                "Existing mesh XY bounds are degenerate.",
            )
            return

        # Pre-check sample budget to avoid long blocking runs.
        est = self._estimate_samples(corridor)
        max_samples = int(self.spin_max_samples.value())
        if est is not None and est > max_samples:
            QtWidgets.QMessageBox.warning(
                None,
                "Cut-Fill Calc",
                f"Estimated samples {est} exceed Max Samples {max_samples}.\n"
                "Increase Cell Size, reduce domain, or raise Max Samples.",
            )
            return
        est_checks = self._estimate_triangle_checks(corridor, mesh, est_samples=est)
        max_checks = int(self.spin_max_checks.value())
        if est_checks is not None and est_checks > max_checks:
            QtWidgets.QMessageBox.warning(
                None,
                "Cut-Fill Calc",
                f"Estimated triangle checks {est_checks} exceed Max Triangle Checks {max_checks}.\n"
                "Increase Cell Size, reduce domain, or lower triangle limits.",
            )
            return

        cmp_obj = self._create_or_get_cut_fill_calc()
        proxy = getattr(cmp_obj, "Proxy", None)
        self._running = True
        self._cancel_requested = False
        self.btn_cancel.setEnabled(True)
        self.btn_generate.setEnabled(False)
        self.lbl_run.setText("Running")
        self.pbar.setValue(0)

        if proxy is not None:
            try:
                proxy._progress_cb = self._on_progress
            except Exception:
                pass

        try:
            if proxy is not None:
                try:
                    proxy._bulk_updating = True
                except Exception:
                    pass
            try:
                cmp_obj.SourceCorridor = corridor
                cmp_obj.ExistingSurface = mesh
                if hasattr(cmp_obj, "ExistingSurfaceCoords"):
                    cmp_obj.ExistingSurfaceCoords = "World" if self._use_world_surface_mode() else "Local"
                cmp_obj.CellSize = self._display_to_meters(float(self.spin_cell.value()))
                cmp_obj.MaxSamples = int(self.spin_max_samples.value())
                if hasattr(cmp_obj, "MaxTrianglesPerSource"):
                    cmp_obj.MaxTrianglesPerSource = int(self.spin_max_tri_src.value())
                if hasattr(cmp_obj, "MaxCandidateTriangles"):
                    cmp_obj.MaxCandidateTriangles = int(self.spin_max_cand.value())
                if hasattr(cmp_obj, "MaxTriangleChecks"):
                    cmp_obj.MaxTriangleChecks = int(self.spin_max_checks.value())
                cmp_obj.MinMeshFacets = int(self.spin_min_facets.value())
                cmp_obj.UseCorridorBounds = bool(self.chk_use_bounds.isChecked())
                if hasattr(cmp_obj, "DomainCoords"):
                    cmp_obj.DomainCoords = str(self.cmb_domain_coords.currentText() or "Local")
                cmp_obj.DomainMargin = self._display_to_meters(float(self.spin_margin.value()))
                cmp_obj.NoDataWarnRatio = float(self.spin_nodata_warn.value()) / 100.0
                cmp_obj.ShowDeltaMap = bool(self.chk_show_map.isChecked())
                cmp_obj.DeltaDeadband = self._display_to_meters(float(self.spin_deadband.value()))
                cmp_obj.DeltaClamp = self._display_to_meters(float(self.spin_clamp.value()))
                cmp_obj.VisualZOffset = self._display_to_meters(float(self.spin_zoff.value()))
                cmp_obj.MaxVisualCells = int(self.spin_max_vis.value())
                cmp_obj.XMin = self._display_to_meters(float(self.spin_xmin.value()))
                cmp_obj.XMax = self._display_to_meters(float(self.spin_xmax.value()))
                cmp_obj.YMin = self._display_to_meters(float(self.spin_ymin.value()))
                cmp_obj.YMax = self._display_to_meters(float(self.spin_ymax.value()))
                cmp_obj.AutoUpdate = bool(self.chk_auto.isChecked())
                # Set force trigger while bulk flag is active to prevent early onChanged recompute.
                cmp_obj.RebuildNow = True
            finally:
                if proxy is not None:
                    try:
                        proxy._bulk_updating = False
                    except Exception:
                        pass

            prj = find_project(self.doc)
            if prj is not None:
                assign_project_corridor(prj, corridor)
                link_project(
                    prj,
                    links={
                        "Terrain": mesh,
                        "CutFillCalc": cmp_obj,
                    },
                    adopt_extra=[corridor, mesh, cmp_obj],
                )

            cmp_obj.touch()
            if proxy is not None:
                proxy.execute(cmp_obj)
                try:
                    cmp_obj.purgeTouched()
                except Exception:
                    pass
            else:
                self.doc.recompute()
        finally:
            if proxy is not None:
                try:
                    proxy._progress_cb = None
                except Exception:
                    pass
            self._running = False
            self.btn_cancel.setEnabled(False)
            self.btn_generate.setEnabled(True)

        try:
            status = str(getattr(cmp_obj, "Status", "Done"))
        except Exception:
            status = "Done"

        if status.startswith("CANCELED"):
            self.lbl_run.setText(status)
        elif status.startswith("ERROR"):
            self.lbl_run.setText(status)
        else:
            self.lbl_run.setText("Completed")
            self.pbar.setValue(100)

        QtWidgets.QMessageBox.information(None, "Cut-Fill Calc", self._build_completion_message(cmp_obj))

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass

        self._refresh_context()

    def _mesh_facets(self, mesh_obj):
        try:
            return int(getattr(getattr(mesh_obj, "Mesh", None), "CountFacets", 0))
        except Exception:
            return 0

    def _mesh_xy_valid(self, mesh_obj):
        try:
            bb = mesh_obj.Mesh.BoundBox
            return float(bb.XLength) > 1e-9 and float(bb.YLength) > 1e-9
        except Exception:
            return False

    def _manual_domain_local_bbox(self):
        x0 = self._display_to_meters(float(self.spin_xmin.value()))
        x1 = self._display_to_meters(float(self.spin_xmax.value()))
        y0 = self._display_to_meters(float(self.spin_ymin.value()))
        y1 = self._display_to_meters(float(self.spin_ymax.value()))
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0

        if str(self.cmb_domain_coords.currentText() or "Local") != "World":
            return (
                _units.model_length_from_meters(self._project or self.doc, x0),
                _units.model_length_from_meters(self._project or self.doc, x1),
                _units.model_length_from_meters(self._project or self.doc, y0),
                _units.model_length_from_meters(self._project or self.doc, y1),
            )

        return _ct.world_xy_bounds_to_local(x0, x1, y0, y1, doc_or_obj=self._coord_context_obj())

    def _estimate_samples(self, corridor):
        try:
            cell = _units.model_length_from_meters(self._project or self.doc, self._display_to_meters(float(self.spin_cell.value())))
            if cell <= 1e-9:
                return None

            if bool(self.chk_use_bounds.isChecked()):
                bb = corridor.Shape.BoundBox
                margin = _units.model_length_from_meters(self._project or self.doc, self._display_to_meters(float(self.spin_margin.value())))
                xmin = float(bb.XMin - margin)
                xmax = float(bb.XMax + margin)
                ymin = float(bb.YMin - margin)
                ymax = float(bb.YMax + margin)
            else:
                xmin, xmax, ymin, ymax = self._manual_domain_local_bbox()

            if xmax < xmin:
                xmin, xmax = xmax, xmin
            if ymax < ymin:
                ymin, ymax = ymax, ymin
            if (xmax - xmin) <= 1e-9 or (ymax - ymin) <= 1e-9:
                return 0

            nx = int((xmax - xmin) / cell)
            ny = int((ymax - ymin) / cell)
            return int(max(0, nx) * max(0, ny))
        except Exception:
            return None

    def _preset_values(self, name: str):
        return get_preset_values(self._quality_presets, name)

    def _apply_quality_preset(self, name: str):
        vals = self._preset_values(name)
        if vals is None:
            return
        self._loading = True
        try:
            apply_preset_to_widgets(
                vals,
                self.spin_cell,
                self.spin_max_samples,
                self.spin_max_tri_src,
                self.spin_max_cand,
                self.spin_max_checks,
            )
        finally:
            self._loading = False

    def _guess_quality_preset(self):
        return guess_preset_name(
            self._quality_presets,
            cell=float(self.spin_cell.value()),
            max_samples=int(self.spin_max_samples.value()),
            max_tri=int(self.spin_max_tri_src.value()),
            max_cand=int(self.spin_max_cand.value()),
            max_checks=int(self.spin_max_checks.value()),
            scale=float(self._display_scale()),
        )

    def _estimate_triangle_checks(self, corridor, mesh, est_samples=None):
        try:
            if corridor is None or mesh is None:
                return None
            if est_samples is None:
                est_samples = self._estimate_samples(corridor)
            if est_samples is None:
                return None
            cell = _units.model_length_from_meters(self._project or self.doc, self._display_to_meters(float(self.spin_cell.value())))
            if bool(self.chk_use_bounds.isChecked()):
                bb = corridor.Shape.BoundBox
                margin = _units.model_length_from_meters(self._project or self.doc, self._display_to_meters(float(self.spin_margin.value())))
                xmin = float(bb.XMin - margin)
                xmax = float(bb.XMax + margin)
                ymin = float(bb.YMin - margin)
                ymax = float(bb.YMax + margin)
            else:
                xmin, xmax, ymin, ymax = self._manual_domain_local_bbox()
            area = max(1e-9, float(xmax - xmin) * float(ymax - ymin))
            max_tri_src = int(self.spin_max_tri_src.value())
            max_cand = int(self.spin_max_cand.value())
            tri_exist = min(max_tri_src, self._mesh_facets(mesh))
            tri_design = min(max_tri_src, max(1, tri_exist))
            return estimate_triangle_checks(est_samples, cell, area, tri_design, tri_exist, max_cand)
        except Exception:
            return None

    def _update_estimate_hint(self):
        corridor = self._current_corridor()
        mesh = self._current_surface()
        est_s = self._estimate_samples(corridor) if corridor is not None else None
        est_c = self._estimate_triangle_checks(corridor, mesh, est_samples=est_s) if (corridor is not None and mesh is not None) else None
        update_estimate_label(
            self.lbl_est,
            est_s,
            est_c,
            int(self.spin_max_samples.value()),
            int(self.spin_max_checks.value()),
            "Estimate: select valid corridor/mesh to compute estimate",
        )

    def _on_quality_changed(self, name):
        if self._loading:
            return
        if str(name) != "Custom":
            self._apply_quality_preset(str(name))
        self._update_estimate_hint()

    def _on_opt_changed(self, _v):
        if self._loading:
            return
        if str(self.cmb_quality.currentText()) != "Custom":
            self._loading = True
            try:
                self.cmb_quality.setCurrentText("Custom")
            finally:
                self._loading = False
        self._update_estimate_hint()

    def _on_source_changed(self, _v):
        self._update_estimate_hint()

    def _request_cancel(self):
        self._cancel_requested = True
        self.lbl_run.setText("Cancel requested...")

    def _on_progress(self, pct, message):
        try:
            self.pbar.setValue(int(max(0.0, min(100.0, float(pct)))))
        except Exception:
            pass
        try:
            self.lbl_run.setText(str(message or "Running"))
        except Exception:
            pass
        try:
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass
        return bool(self._cancel_requested)

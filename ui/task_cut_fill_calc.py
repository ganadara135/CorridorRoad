import FreeCAD as App
import FreeCADGui as Gui

from PySide2 import QtWidgets

from objects.obj_project import CorridorRoadProject, ensure_project_properties, get_length_scale
from objects.obj_cut_fill_calc import CutFillCalc, ViewProviderCutFillCalc


def _find_project(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o
    return None


def _is_mesh_obj(obj):
    try:
        return hasattr(obj, "Mesh") and obj.Mesh is not None and int(obj.Mesh.CountFacets) > 0
    except Exception:
        return False


def _is_shape_obj(obj):
    try:
        return hasattr(obj, "Shape") and obj.Shape is not None and (not obj.Shape.isNull()) and len(list(obj.Shape.Faces)) > 0
    except Exception:
        return False


def _is_surface_source(obj):
    return _is_mesh_obj(obj) or _is_shape_obj(obj)


def _is_corridor_obj(obj):
    if obj is None:
        return False
    try:
        if getattr(obj, "Proxy", None) and getattr(obj.Proxy, "Type", "") == "CorridorLoft":
            return True
    except Exception:
        pass
    return bool(obj.Name.startswith("CorridorLoft"))


def _find_corridors(doc):
    out = []
    if doc is None:
        return out
    for o in doc.Objects:
        if _is_corridor_obj(o):
            out.append(o)
    return out


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
    return [o for o in doc.Objects if _is_surface_source(o)]


def _selected_surface():
    try:
        sel = list(Gui.Selection.getSelection() or [])
        for o in sel:
            if _is_surface_source(o):
                return o
    except Exception:
        pass
    return None


class CutFillCalcTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._scale = get_length_scale(self.doc, default=1.0)
        self._corridors = []
        self._surfaces = []
        self._loading = False
        self.form = self._build_ui()
        self._refresh_context()

    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

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
        self.btn_pick_sel = QtWidgets.QPushButton("Use Selected Surface")
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fs.addRow("Design Corridor:", self.cmb_corridor)
        fs.addRow("Existing Surface (Mesh/Shape):", self.cmb_surface)
        fs.addRow(self.btn_pick_sel)
        fs.addRow(self.btn_refresh)
        main.addWidget(gb_src)

        gb_opt = QtWidgets.QGroupBox("Comparison")
        fo = QtWidgets.QFormLayout(gb_opt)
        self.spin_cell = QtWidgets.QDoubleSpinBox()
        self.spin_cell.setRange(0.2 * self._scale, 10000.0 * self._scale)
        self.spin_cell.setDecimals(3)
        self.spin_cell.setValue(1.0 * self._scale)
        self.spin_max_samples = QtWidgets.QSpinBox()
        self.spin_max_samples.setRange(1000, 2000000000)
        self.spin_max_samples.setValue(200000)
        self.spin_min_facets = QtWidgets.QSpinBox()
        self.spin_min_facets.setRange(1, 2000000000)
        self.spin_min_facets.setValue(100)
        self.chk_use_bounds = QtWidgets.QCheckBox("Use corridor bounds")
        self.chk_use_bounds.setChecked(True)
        self.spin_margin = QtWidgets.QDoubleSpinBox()
        self.spin_margin.setRange(0.0, 1000000.0 * self._scale)
        self.spin_margin.setDecimals(3)
        self.spin_margin.setValue(5.0 * self._scale)
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
            s.setValue(0.0)

        self.chk_auto = QtWidgets.QCheckBox("Auto update on source changes")
        self.chk_auto.setChecked(True)
        self.lbl_sign = QtWidgets.QLabel("Sign: delta=Design-Existing, +Fill / -Cut")

        fo.addRow("Cell Size (scaled):", self.spin_cell)
        fo.addRow("Max Samples:", self.spin_max_samples)
        fo.addRow("Min Mesh Facets:", self.spin_min_facets)
        fo.addRow(self.chk_use_bounds)
        fo.addRow("Domain Margin (scaled):", self.spin_margin)
        fo.addRow("NoData Warn:", self.spin_nodata_warn)
        fo.addRow("X Min:", self.spin_xmin)
        fo.addRow("X Max:", self.spin_xmax)
        fo.addRow("Y Min:", self.spin_ymin)
        fo.addRow("Y Max:", self.spin_ymax)
        fo.addRow(self.chk_auto)
        fo.addRow(self.lbl_sign)
        main.addWidget(gb_opt)

        gb_vis = QtWidgets.QGroupBox("3D Display")
        fv = QtWidgets.QFormLayout(gb_vis)
        self.chk_show_map = QtWidgets.QCheckBox("Show Cut/Fill Map in 3D")
        self.chk_show_map.setChecked(True)
        self.spin_deadband = QtWidgets.QDoubleSpinBox()
        self.spin_deadband.setRange(0.0, 100.0 * self._scale)
        self.spin_deadband.setDecimals(3)
        self.spin_deadband.setValue(0.02 * self._scale)
        self.spin_clamp = QtWidgets.QDoubleSpinBox()
        self.spin_clamp.setRange(0.001 * self._scale, 10000.0 * self._scale)
        self.spin_clamp.setDecimals(3)
        self.spin_clamp.setValue(2.0 * self._scale)
        self.spin_zoff = QtWidgets.QDoubleSpinBox()
        self.spin_zoff.setRange(-1000.0 * self._scale, 1000.0 * self._scale)
        self.spin_zoff.setDecimals(3)
        self.spin_zoff.setValue(0.05 * self._scale)
        self.spin_max_vis = QtWidgets.QSpinBox()
        self.spin_max_vis.setRange(1000, 2000000000)
        self.spin_max_vis.setValue(40000)
        self.lbl_palette = QtWidgets.QLabel("Palette: Cut=Red, Fill=Blue, Neutral=Light Gray, NoData=Gray")
        self.lbl_palette.setWordWrap(True)
        fv.addRow(self.chk_show_map)
        fv.addRow("Deadband |delta| (scaled):", self.spin_deadband)
        fv.addRow("Clamp |delta| (scaled):", self.spin_clamp)
        fv.addRow("Visual Z Offset (scaled):", self.spin_zoff)
        fv.addRow("Max Visual Cells:", self.spin_max_vis)
        fv.addRow(self.lbl_palette)
        main.addWidget(gb_vis)

        self.btn_generate = QtWidgets.QPushButton("Run Cut-Fill Calc")
        main.addWidget(self.btn_generate)

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
        self.btn_cancel.clicked.connect(self._request_cancel)

        self._update_bounds_ui()
        return w

    def _format_obj(self, obj):
        tag = "Shape"
        if _is_mesh_obj(obj):
            tag = "Mesh"
        return f"[{tag}] {obj.Label} ({obj.Name})"

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
        prj = _find_project(self.doc)
        cmp_obj = _find_cut_fill_calc(self.doc)
        if cmp_obj is not None:
            try:
                if str(getattr(cmp_obj, "Label", "")) in ("", "Existing/Design Surface Comparison"):
                    cmp_obj.Label = "Cut-Fill Calc"
            except Exception:
                pass

        preferred_corridor = None
        preferred_surface = None
        if prj is not None:
            preferred_corridor = getattr(prj, "CorridorLoft", None)
            preferred_surface = getattr(prj, "Terrain", None)

        if cmp_obj is not None:
            try:
                if getattr(cmp_obj, "SourceCorridor", None) is not None:
                    preferred_corridor = cmp_obj.SourceCorridor
                if getattr(cmp_obj, "ExistingSurface", None) is not None:
                    preferred_surface = cmp_obj.ExistingSurface
            except Exception:
                pass

            self._loading = True
            try:
                if hasattr(cmp_obj, "CellSize"):
                    self.spin_cell.setValue(float(cmp_obj.CellSize))
                if hasattr(cmp_obj, "MaxSamples"):
                    self.spin_max_samples.setValue(int(cmp_obj.MaxSamples))
                if hasattr(cmp_obj, "MinMeshFacets"):
                    self.spin_min_facets.setValue(int(cmp_obj.MinMeshFacets))
                if hasattr(cmp_obj, "UseCorridorBounds"):
                    self.chk_use_bounds.setChecked(bool(cmp_obj.UseCorridorBounds))
                if hasattr(cmp_obj, "DomainMargin"):
                    self.spin_margin.setValue(float(cmp_obj.DomainMargin))
                if hasattr(cmp_obj, "NoDataWarnRatio"):
                    self.spin_nodata_warn.setValue(100.0 * float(cmp_obj.NoDataWarnRatio))
                if hasattr(cmp_obj, "ShowDeltaMap"):
                    self.chk_show_map.setChecked(bool(cmp_obj.ShowDeltaMap))
                if hasattr(cmp_obj, "DeltaDeadband"):
                    self.spin_deadband.setValue(float(cmp_obj.DeltaDeadband))
                if hasattr(cmp_obj, "DeltaClamp"):
                    self.spin_clamp.setValue(float(cmp_obj.DeltaClamp))
                if hasattr(cmp_obj, "VisualZOffset"):
                    self.spin_zoff.setValue(float(cmp_obj.VisualZOffset))
                if hasattr(cmp_obj, "MaxVisualCells"):
                    self.spin_max_vis.setValue(int(cmp_obj.MaxVisualCells))
                if hasattr(cmp_obj, "XMin"):
                    self.spin_xmin.setValue(float(cmp_obj.XMin))
                if hasattr(cmp_obj, "XMax"):
                    self.spin_xmax.setValue(float(cmp_obj.XMax))
                if hasattr(cmp_obj, "YMin"):
                    self.spin_ymin.setValue(float(cmp_obj.YMin))
                if hasattr(cmp_obj, "YMax"):
                    self.spin_ymax.setValue(float(cmp_obj.YMax))
                if hasattr(cmp_obj, "AutoUpdate"):
                    self.chk_auto.setChecked(bool(cmp_obj.AutoUpdate))
            finally:
                self._loading = False

        sel_surface = _selected_surface()
        if sel_surface is not None:
            preferred_surface = sel_surface

        self._fill_combo(self.cmb_corridor, self._corridors, preferred_corridor)
        self._fill_combo(self.cmb_surface, self._surfaces, preferred_surface)
        self._update_bounds_ui()

        msg = []
        msg.append(f"CorridorLoft: {len(self._corridors)} found")
        msg.append(f"Surface sources: {len(self._surfaces)} found (Mesh/Shape)")
        if cmp_obj is not None:
            msg.append("Cut-Fill Calc object: FOUND (will update)")
            try:
                msg.append(f"Last status: {getattr(cmp_obj, 'Status', '')}")
            except Exception:
                pass
        else:
            msg.append("Cut-Fill Calc object: NOT FOUND (will create)")
        self.lbl_info.setText("\n".join(msg))

    def _use_selected_surface(self):
        sel = _selected_surface()
        if sel is None:
            QtWidgets.QMessageBox.information(
                None,
                "Cut-Fill Calc",
                "No valid surface selected. Select Mesh/Shape object in tree or 3D view first.",
            )
            return
        for i, o in enumerate(self._surfaces):
            if o == sel:
                self.cmb_surface.setCurrentIndex(i)
                return
        self._refresh_context()

    def _create_or_get_cut_fill_calc(self):
        cmp_obj = _find_cut_fill_calc(self.doc)
        if cmp_obj is not None:
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
                "No CorridorLoft selected. Run Generate Corridor Loft first.",
            )
            return

        source = self._current_surface()
        if source is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Cut-Fill Calc",
                "No Existing Surface selected.",
            )
            return

        # Existing source quality gate.
        if _is_mesh_obj(source):
            mesh_facets = self._mesh_facets(source)
            min_facets = int(self.spin_min_facets.value())
            if mesh_facets < min_facets:
                QtWidgets.QMessageBox.warning(
                    None,
                    "Cut-Fill Calc",
                    f"Existing mesh facets {mesh_facets} < Min Mesh Facets {min_facets}.",
                )
                return
            if not self._mesh_xy_valid(source):
                QtWidgets.QMessageBox.warning(
                    None,
                    "Cut-Fill Calc",
                    "Existing mesh XY bounds are degenerate.",
                )
                return
        elif not self._shape_xy_valid(source):
            QtWidgets.QMessageBox.warning(
                None,
                "Cut-Fill Calc",
                "Existing shape XY bounds are degenerate.",
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
                cmp_obj.ExistingSurface = source
                cmp_obj.CellSize = float(self.spin_cell.value())
                cmp_obj.MaxSamples = int(self.spin_max_samples.value())
                cmp_obj.MinMeshFacets = int(self.spin_min_facets.value())
                cmp_obj.UseCorridorBounds = bool(self.chk_use_bounds.isChecked())
                cmp_obj.DomainMargin = float(self.spin_margin.value())
                cmp_obj.NoDataWarnRatio = float(self.spin_nodata_warn.value()) / 100.0
                cmp_obj.ShowDeltaMap = bool(self.chk_show_map.isChecked())
                cmp_obj.DeltaDeadband = float(self.spin_deadband.value())
                cmp_obj.DeltaClamp = float(self.spin_clamp.value())
                cmp_obj.VisualZOffset = float(self.spin_zoff.value())
                cmp_obj.MaxVisualCells = int(self.spin_max_vis.value())
                cmp_obj.XMin = float(self.spin_xmin.value())
                cmp_obj.XMax = float(self.spin_xmax.value())
                cmp_obj.YMin = float(self.spin_ymin.value())
                cmp_obj.YMax = float(self.spin_ymax.value())
                cmp_obj.AutoUpdate = bool(self.chk_auto.isChecked())
                # Set force trigger while bulk flag is active to prevent early onChanged recompute.
                cmp_obj.RebuildNow = True
            finally:
                if proxy is not None:
                    try:
                        proxy._bulk_updating = False
                    except Exception:
                        pass

            prj = _find_project(self.doc)
            if prj is not None:
                ensure_project_properties(prj)
                if hasattr(prj, "CorridorLoft"):
                    prj.CorridorLoft = corridor
                if hasattr(prj, "Terrain"):
                    prj.Terrain = source
                if hasattr(prj, "CutFillCalc"):
                    prj.CutFillCalc = cmp_obj
                CorridorRoadProject.adopt(prj, corridor)
                CorridorRoadProject.adopt(prj, source)
                CorridorRoadProject.adopt(prj, cmp_obj)

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

        msg = [
            status,
            f"CutVolume: {float(getattr(cmp_obj, 'CutVolume', 0.0)):.3f} (scaled^3)",
            f"FillVolume: {float(getattr(cmp_obj, 'FillVolume', 0.0)):.3f} (scaled^3)",
            f"Delta(min/max/mean): "
            f"{float(getattr(cmp_obj, 'DeltaMin', 0.0)):.3f} / "
            f"{float(getattr(cmp_obj, 'DeltaMax', 0.0)):.3f} / "
            f"{float(getattr(cmp_obj, 'DeltaMean', 0.0)):.3f}",
            f"Samples(valid/total): {int(getattr(cmp_obj, 'ValidCount', 0))} / {int(getattr(cmp_obj, 'SampleCount', 0))}",
            f"NoData(area/ratio): {float(getattr(cmp_obj, 'NoDataArea', 0.0)):.3f} (scaled^2) / "
            f"{100.0 * float(getattr(cmp_obj, 'NoDataRatio', 0.0)):.2f}%",
            f"CellSize: {float(getattr(cmp_obj, 'CellSize', 0.0)):.3f} (scaled)",
            f"Sign: {str(getattr(cmp_obj, 'SignConvention', 'delta=Design-Existing, +Fill/-Cut'))}",
            f"Display: show_map={bool(getattr(cmp_obj, 'ShowDeltaMap', True))}, "
            f"deadband={float(getattr(cmp_obj, 'DeltaDeadband', 0.0)):.3f} (scaled), "
            f"clamp={float(getattr(cmp_obj, 'DeltaClamp', 0.0)):.3f} (scaled)",
        ]
        QtWidgets.QMessageBox.information(None, "Cut-Fill Calc", "\n".join(msg))

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

    def _shape_xy_valid(self, shape_obj):
        try:
            bb = shape_obj.Shape.BoundBox
            return float(bb.XLength) > 1e-9 and float(bb.YLength) > 1e-9
        except Exception:
            return False

    def _estimate_samples(self, corridor):
        try:
            cell = float(self.spin_cell.value())
            if cell <= 1e-9:
                return None

            if bool(self.chk_use_bounds.isChecked()):
                bb = corridor.Shape.BoundBox
                margin = float(self.spin_margin.value())
                xmin = float(bb.XMin - margin)
                xmax = float(bb.XMax + margin)
                ymin = float(bb.YMin - margin)
                ymax = float(bb.YMax + margin)
            else:
                xmin = float(self.spin_xmin.value())
                xmax = float(self.spin_xmax.value())
                ymin = float(self.spin_ymin.value())
                ymax = float(self.spin_ymax.value())

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

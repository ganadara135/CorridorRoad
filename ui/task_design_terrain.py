import FreeCAD as App
import FreeCADGui as Gui
from PySide2 import QtWidgets

from objects.obj_design_terrain import DesignTerrain, ViewProviderDesignTerrain
from objects.obj_project import CorridorRoadProject, ensure_project_properties, get_length_scale


def _is_mesh_obj(obj):
    try:
        return hasattr(obj, "Mesh") and obj.Mesh is not None and int(obj.Mesh.CountFacets) > 0
    except Exception:
        return False


def _is_shape_obj(obj):
    try:
        return hasattr(obj, "Shape") and obj.Shape is not None and (not obj.Shape.isNull())
    except Exception:
        return False


def _is_terrain_source(obj):
    return _is_mesh_obj(obj) or _is_shape_obj(obj)


def _find_project(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o
    return None


def _find_design_surfaces(doc):
    out = []
    if doc is None:
        return out
    for o in doc.Objects:
        try:
            if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignGradingSurface":
                out.append(o)
                continue
        except Exception:
            pass
        if o.Name.startswith("DesignGradingSurface"):
            out.append(o)
    return out


def _find_design_terrain(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        try:
            if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignTerrain":
                return o
        except Exception:
            pass
        if o.Name.startswith("DesignTerrain"):
            return o
    return None


def _find_terrain_sources(doc):
    out = []
    if doc is None:
        return out
    for o in doc.Objects:
        try:
            if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignTerrain":
                continue
        except Exception:
            pass
        if o.Name.startswith("DesignTerrain"):
            continue
        if _is_terrain_source(o):
            out.append(o)
    return out


def _selected_terrain():
    try:
        sel = list(Gui.Selection.getSelection() or [])
        for o in sel:
            try:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignTerrain":
                    continue
            except Exception:
                pass
            if o.Name.startswith("DesignTerrain"):
                continue
            if _is_terrain_source(o):
                return o
    except Exception:
        pass
    return None


def _source_bounds(src_obj):
    if _is_mesh_obj(src_obj):
        return src_obj.Mesh.BoundBox
    if _is_shape_obj(src_obj):
        return src_obj.Shape.BoundBox
    raise Exception("Invalid terrain source bounds.")


class DesignTerrainTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._scale = get_length_scale(self.doc, default=1.0)
        self._surfaces = []
        self._terrains = []
        self._loading = False
        self._running = False
        self._cancel_requested = False
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
        w.setWindowTitle("CorridorRoad - Design Terrain")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        gb_src = QtWidgets.QGroupBox("Source")
        fs = QtWidgets.QFormLayout(gb_src)
        self.cmb_dsg = QtWidgets.QComboBox()
        self.cmb_eg = QtWidgets.QComboBox()
        self.btn_pick_sel = QtWidgets.QPushButton("Use Selected Terrain")
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fs.addRow("Design Grading Surface:", self.cmb_dsg)
        fs.addRow("Existing Terrain (Mesh/Shape):", self.cmb_eg)
        fs.addRow(self.btn_pick_sel)
        fs.addRow(self.btn_refresh)
        main.addWidget(gb_src)

        gb_opt = QtWidgets.QGroupBox("Options")
        fo = QtWidgets.QFormLayout(gb_opt)
        self.spin_cell = QtWidgets.QDoubleSpinBox()
        self.spin_cell.setRange(0.2 * self._scale, 10000.0 * self._scale)
        self.spin_cell.setDecimals(3)
        self.spin_cell.setValue(1.0 * self._scale)
        self.spin_max_samples = QtWidgets.QSpinBox()
        self.spin_max_samples.setRange(1000, 2000000000)
        self.spin_max_samples.setValue(250000)
        self.spin_margin = QtWidgets.QDoubleSpinBox()
        self.spin_margin.setRange(0.0, 1000000.0 * self._scale)
        self.spin_margin.setDecimals(3)
        self.spin_margin.setValue(0.0)
        self.chk_auto = QtWidgets.QCheckBox("Auto update on source changes")
        self.chk_auto.setChecked(True)
        fo.addRow("Cell Size (scaled):", self.spin_cell)
        fo.addRow("Max Samples:", self.spin_max_samples)
        fo.addRow("Domain Margin (scaled):", self.spin_margin)
        fo.addRow(self.chk_auto)
        main.addWidget(gb_opt)

        self.btn_build = QtWidgets.QPushButton("Build Design Terrain")
        main.addWidget(self.btn_build)

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

        self.btn_pick_sel.clicked.connect(self._use_selected_terrain)
        self.btn_refresh.clicked.connect(self._refresh_context)
        self.btn_build.clicked.connect(self._build)
        self.btn_cancel.clicked.connect(self._request_cancel)
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

    def _current_dsg(self):
        i = int(self.cmb_dsg.currentIndex())
        if i < 0 or i >= len(self._surfaces):
            return None
        return self._surfaces[i]

    def _current_eg(self):
        i = int(self.cmb_eg.currentIndex())
        if i < 0 or i >= len(self._terrains):
            return None
        return self._terrains[i]

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return

        self._surfaces = _find_design_surfaces(self.doc)
        self._terrains = _find_terrain_sources(self.doc)
        prj = _find_project(self.doc)
        dtm = _find_design_terrain(self.doc)

        pref_dsg = None
        pref_eg = None
        if prj is not None:
            pref_dsg = getattr(prj, "DesignGradingSurface", None)
            pref_eg = getattr(prj, "Terrain", None)

        if dtm is not None:
            try:
                if getattr(dtm, "SourceDesignSurface", None) is not None:
                    pref_dsg = dtm.SourceDesignSurface
                if getattr(dtm, "ExistingTerrain", None) is not None:
                    pref_eg = dtm.ExistingTerrain
            except Exception:
                pass

            self._loading = True
            try:
                if hasattr(dtm, "CellSize"):
                    self.spin_cell.setValue(float(dtm.CellSize))
                if hasattr(dtm, "MaxSamples"):
                    self.spin_max_samples.setValue(int(dtm.MaxSamples))
                if hasattr(dtm, "DomainMargin"):
                    self.spin_margin.setValue(float(dtm.DomainMargin))
                if hasattr(dtm, "AutoUpdate"):
                    self.chk_auto.setChecked(bool(dtm.AutoUpdate))
            finally:
                self._loading = False

        sel = _selected_terrain()
        if sel is not None:
            pref_eg = sel

        self._fill_combo(self.cmb_dsg, self._surfaces, pref_dsg)
        self._fill_combo(self.cmb_eg, self._terrains, pref_eg)

        msg = []
        msg.append(f"DesignGradingSurface: {len(self._surfaces)} found")
        msg.append(f"Terrain candidates: {len(self._terrains)} found (Mesh/Shape)")
        if dtm is not None:
            msg.append("DesignTerrain object: FOUND (will update)")
            try:
                msg.append(f"Last status: {getattr(dtm, 'Status', '')}")
            except Exception:
                pass
        else:
            msg.append("DesignTerrain object: NOT FOUND (will create)")
        self.lbl_info.setText("\n".join(msg))

    def _use_selected_terrain(self):
        sel = _selected_terrain()
        if sel is None:
            QtWidgets.QMessageBox.information(
                None,
                "Design Terrain",
                "No terrain source selected. Select Mesh/Shape object first.",
            )
            return
        for i, o in enumerate(self._terrains):
            if o == sel:
                self.cmb_eg.setCurrentIndex(i)
                return
        self._refresh_context()

    def _estimate_samples(self, eg_obj):
        try:
            cell = float(self.spin_cell.value())
            if cell <= 1e-9:
                return None
            margin = float(self.spin_margin.value())
            bb = _source_bounds(eg_obj)
            xmin = float(bb.XMin - margin)
            xmax = float(bb.XMax + margin)
            ymin = float(bb.YMin - margin)
            ymax = float(bb.YMax + margin)
            if (xmax - xmin) <= 1e-9 or (ymax - ymin) <= 1e-9:
                return 0
            nx = int((xmax - xmin) / cell)
            ny = int((ymax - ymin) / cell)
            return int(max(0, nx) * max(0, ny))
        except Exception:
            return None

    def _create_or_get_design_terrain(self):
        dtm = _find_design_terrain(self.doc)
        if dtm is not None:
            return dtm
        dtm = self.doc.addObject("Part::FeaturePython", "DesignTerrain")
        DesignTerrain(dtm)
        ViewProviderDesignTerrain(dtm.ViewObject)
        dtm.Label = "Design Terrain"
        return dtm

    def _build(self):
        if bool(getattr(self, "_running", False)):
            QtWidgets.QMessageBox.information(None, "Design Terrain", "Already running.")
            return

        if self.doc is None:
            return

        dsg = self._current_dsg()
        if dsg is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Design Terrain",
                "No Design Grading Surface selected.",
            )
            return

        eg = self._current_eg()
        if eg is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Design Terrain",
                "No Existing Terrain selected.",
            )
            return

        est = self._estimate_samples(eg)
        max_samples = int(self.spin_max_samples.value())
        if est is not None and est > max_samples:
            QtWidgets.QMessageBox.warning(
                None,
                "Design Terrain",
                f"Estimated samples {est} exceed Max Samples {max_samples}.\n"
                "Increase Cell Size, reduce margin, or raise Max Samples.",
            )
            return

        dtm = self._create_or_get_design_terrain()
        proxy = getattr(dtm, "Proxy", None)
        self._running = True
        self._cancel_requested = False
        self.btn_cancel.setEnabled(True)
        self.btn_build.setEnabled(False)
        self.lbl_run.setText("Running")
        self.pbar.setValue(0)

        if proxy is not None:
            try:
                proxy._progress_cb = self._on_progress
            except Exception:
                pass

        try:
            if proxy is not None and hasattr(proxy, "_bulk_updating"):
                proxy._bulk_updating = True
            dtm.SourceDesignSurface = dsg
            dtm.ExistingTerrain = eg
            dtm.CellSize = float(self.spin_cell.value())
            dtm.MaxSamples = int(self.spin_max_samples.value())
            dtm.DomainMargin = float(self.spin_margin.value())
            dtm.AutoUpdate = bool(self.chk_auto.isChecked())
            dtm.RebuildNow = True
        finally:
            if proxy is not None and hasattr(proxy, "_bulk_updating"):
                proxy._bulk_updating = False

        prj = _find_project(self.doc)
        if prj is not None:
            ensure_project_properties(prj)
            if hasattr(prj, "Terrain"):
                prj.Terrain = eg
            if hasattr(prj, "DesignGradingSurface"):
                prj.DesignGradingSurface = dsg
            if hasattr(prj, "DesignTerrain"):
                prj.DesignTerrain = dtm
            CorridorRoadProject.adopt(prj, dsg)
            CorridorRoadProject.adopt(prj, eg)
            CorridorRoadProject.adopt(prj, dtm)

        dtm.touch()
        try:
            if proxy is not None:
                proxy.execute(dtm)
                try:
                    dtm.purgeTouched()
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
            self.btn_build.setEnabled(True)

        status = str(getattr(dtm, "Status", "Done"))
        self.lbl_run.setText(status)
        if status.startswith("CANCELED"):
            pass
        elif status.startswith("ERROR"):
            pass
        else:
            self.pbar.setValue(100)

        msg = [
            status,
            f"ExistingTerrain: {eg.Label} ({eg.Name})",
            f"Samples(valid/total): {int(getattr(dtm, 'ValidCount', 0))} / {int(getattr(dtm, 'SampleCount', 0))}",
            f"NoDataArea: {float(getattr(dtm, 'NoDataArea', 0.0)):.3f} (scaled^2)",
            f"CellSize: {float(getattr(dtm, 'CellSize', 0.0)):.3f} (scaled)",
        ]
        QtWidgets.QMessageBox.information(None, "Design Terrain", "\n".join(msg))

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass
        self._refresh_context()

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

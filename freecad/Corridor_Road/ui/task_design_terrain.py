# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui
from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects import coord_transform as _ct
from freecad.Corridor_Road.objects.doc_query import find_project
from freecad.Corridor_Road.objects.obj_design_terrain import DesignTerrain, ViewProviderDesignTerrain, ensure_design_terrain_properties
from freecad.Corridor_Road.objects.obj_project import get_length_scale
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


def _find_design_surfaces(doc):
    out = []
    if doc is None:
        return out
    for o in doc.Objects:
        is_dsg = False
        try:
            if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignGradingSurface":
                is_dsg = True
        except Exception:
            pass
        if (not is_dsg) and o.Name.startswith("DesignGradingSurface"):
            is_dsg = True
        if is_dsg and _is_mesh_obj(o):
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
        if _is_mesh_obj(o):
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
            if _is_mesh_obj(o):
                return o
    except Exception:
        pass
    return None


def _source_bounds(src_obj):
    if not _is_mesh_obj(src_obj):
        raise Exception("Invalid terrain source bounds.")
    return src_obj.Mesh.BoundBox


class DesignTerrainTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._scale = get_length_scale(self.doc, default=1.0)
        self._quality_presets = build_quality_presets(
            self._scale,
            {
                "Fast": 150000,
                "Balanced": 250000,
                "Precise": 700000,
            },
        )
        self._surfaces = []
        self._terrains = []
        self._project = None
        self._coord_mode_initialized = False
        self._loading = False
        self._running = False
        self._cancel_requested = False
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
        self.cmb_eg_coords = QtWidgets.QComboBox()
        self.cmb_eg_coords.addItems(["Local", "World"])
        self.lbl_coord_hint = QtWidgets.QLabel("")
        self.lbl_coord_hint.setWordWrap(True)
        self.btn_pick_sel = QtWidgets.QPushButton("Use Selected Terrain")
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fs.addRow("Design Grading Surface:", self.cmb_dsg)
        fs.addRow("Existing Terrain (Mesh):", self.cmb_eg)
        row_coords = QtWidgets.QHBoxLayout()
        row_coords.addWidget(self.cmb_eg_coords)
        row_coords.addWidget(self.lbl_coord_hint, 1)
        w_coords = QtWidgets.QWidget()
        w_coords.setLayout(row_coords)
        fs.addRow("Existing Terrain Coords:", w_coords)
        fs.addRow(self.btn_pick_sel)
        fs.addRow(self.btn_refresh)
        main.addWidget(gb_src)

        gb_opt = QtWidgets.QGroupBox("Options")
        form_opts = QtWidgets.QFormLayout(gb_opt)
        self.cmb_quality = QtWidgets.QComboBox()
        self.cmb_quality.addItems(list(QUALITY_PRESETS))
        self.cmb_quality.setCurrentText("Balanced")
        self.spin_cell = QtWidgets.QDoubleSpinBox()
        self.spin_cell.setRange(0.2 * self._scale, 10000.0 * self._scale)
        self.spin_cell.setDecimals(3)
        self.spin_cell.setValue(1.0 * self._scale)
        self.spin_max_samples = QtWidgets.QSpinBox()
        self.spin_max_samples.setRange(1000, 2000000000)
        self.spin_max_samples.setValue(250000)
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
        self.spin_margin = QtWidgets.QDoubleSpinBox()
        self.spin_margin.setRange(0.0, 1000000.0 * self._scale)
        self.spin_margin.setDecimals(3)
        self.spin_margin.setValue(0.0)
        self.chk_auto = QtWidgets.QCheckBox("Auto update on source changes")
        self.chk_auto.setChecked(True)
        self.lbl_est = QtWidgets.QLabel("Estimate: -")
        self.lbl_est.setWordWrap(True)
        self.lbl_est.setTextInteractionFlags(self.lbl_est.textInteractionFlags())
        form_opts.addRow("Quality Preset:", self.cmb_quality)
        form_opts.addRow("Cell Size (scaled):", self.spin_cell)
        form_opts.addRow("Max Samples:", self.spin_max_samples)
        form_opts.addRow("Max Triangles/Source:", self.spin_max_tri_src)
        form_opts.addRow("Max Candidate Triangles:", self.spin_max_cand)
        form_opts.addRow("Max Triangle Checks:", self.spin_max_checks)
        form_opts.addRow("Domain Margin (scaled):", self.spin_margin)
        form_opts.addRow(self.chk_auto)
        form_opts.addRow("Estimate:", self.lbl_est)
        main.addWidget(gb_opt)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_build = QtWidgets.QPushButton("Build Design Terrain")
        self.btn_close = QtWidgets.QPushButton("Close")
        row_btn.addWidget(self.btn_build)
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

        self.btn_pick_sel.clicked.connect(self._use_selected_terrain)
        self.btn_refresh.clicked.connect(self._refresh_context)
        self.btn_build.clicked.connect(self._build)
        self.btn_close.clicked.connect(self.reject)
        self.btn_cancel.clicked.connect(self._request_cancel)
        self.cmb_dsg.currentIndexChanged.connect(self._on_source_changed)
        self.cmb_eg.currentIndexChanged.connect(self._on_source_changed)
        self.cmb_eg_coords.currentIndexChanged.connect(self._on_existing_coord_changed)
        self.cmb_quality.currentTextChanged.connect(self._on_quality_changed)
        self.spin_cell.valueChanged.connect(self._on_opt_changed)
        self.spin_max_samples.valueChanged.connect(self._on_opt_changed)
        self.spin_max_tri_src.valueChanged.connect(self._on_opt_changed)
        self.spin_max_cand.valueChanged.connect(self._on_opt_changed)
        self.spin_max_checks.valueChanged.connect(self._on_opt_changed)
        self.spin_margin.valueChanged.connect(self._on_opt_changed)
        return w

    def _coord_context_obj(self):
        if self._project is not None:
            return self._project
        return self.doc

    def _use_world_existing_mode(self):
        return str(self.cmb_eg_coords.currentText() or "Local") == "World"

    def _update_coord_hint(self):
        self.lbl_coord_hint.setText(coord_hint_text(self._coord_context_obj()))

    def _apply_default_coord_mode(self):
        if self._coord_mode_initialized:
            return
        self._loading = True
        try:
            if should_default_world_mode(self._coord_context_obj()):
                self.cmb_eg_coords.setCurrentText("World")
            else:
                self.cmb_eg_coords.setCurrentText("Local")
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
        prj = find_project(self.doc)
        self._project = prj
        self._apply_default_coord_mode()
        self._update_coord_hint()
        dtm = _find_design_terrain(self.doc)
        if dtm is not None:
            try:
                ensure_design_terrain_properties(dtm)
            except Exception:
                pass

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
                if hasattr(dtm, "MaxTrianglesPerSource"):
                    self.spin_max_tri_src.setValue(int(dtm.MaxTrianglesPerSource))
                if hasattr(dtm, "MaxCandidateTriangles"):
                    self.spin_max_cand.setValue(int(dtm.MaxCandidateTriangles))
                if hasattr(dtm, "MaxTriangleChecks"):
                    self.spin_max_checks.setValue(int(dtm.MaxTriangleChecks))
                if hasattr(dtm, "DomainMargin"):
                    self.spin_margin.setValue(float(dtm.DomainMargin))
                if hasattr(dtm, "AutoUpdate"):
                    self.chk_auto.setChecked(bool(dtm.AutoUpdate))
                if hasattr(dtm, "ExistingTerrainCoords"):
                    mode = str(getattr(dtm, "ExistingTerrainCoords", "Local") or "Local")
                    self.cmb_eg_coords.setCurrentText("World" if mode == "World" else "Local")
            finally:
                self._loading = False

        sel = _selected_terrain()
        if sel is not None:
            pref_eg = sel

        self._fill_combo(self.cmb_dsg, self._surfaces, pref_dsg)
        self._fill_combo(self.cmb_eg, self._terrains, pref_eg)

        msg = []
        msg.append(f"DesignGradingSurface: {len(self._surfaces)} found")
        msg.append(f"Terrain candidates: {len(self._terrains)} found (Mesh only)")
        msg.append(f"Existing terrain coords: {'World' if self._use_world_existing_mode() else 'Local'}")
        if dtm is not None:
            msg.append("DesignTerrain object: FOUND (will update)")
            try:
                msg.append(f"Last status: {getattr(dtm, 'Status', '')}")
            except Exception:
                pass
        else:
            msg.append("DesignTerrain object: NOT FOUND (will create)")
        self.lbl_info.setText("\n".join(msg))
        self._loading = True
        try:
            self.cmb_quality.setCurrentText(self._guess_quality_preset())
        finally:
            self._loading = False
        self._update_estimate_hint()

    def _on_existing_coord_changed(self, _v):
        if self._loading:
            return
        self._update_coord_hint()
        self._on_source_changed(_v)

    def _use_selected_terrain(self):
        sel = _selected_terrain()
        if sel is None:
            QtWidgets.QMessageBox.information(
                None,
                "Design Terrain",
                "No terrain source selected. Select a Mesh object first.",
            )
            return
        for i, o in enumerate(self._terrains):
            if o == sel:
                self.cmb_eg.setCurrentIndex(i)
                self._update_estimate_hint()
                return
        self._refresh_context()

    def _estimate_samples(self, eg_obj):
        try:
            cell = float(self.spin_cell.value())
            if cell <= 1e-9:
                return None
            margin = float(self.spin_margin.value())
            xmin, xmax, ymin, ymax = self._existing_bounds_local(eg_obj)
            xmin = float(xmin - margin)
            xmax = float(xmax + margin)
            ymin = float(ymin - margin)
            ymax = float(ymax + margin)
            if (xmax - xmin) <= 1e-9 or (ymax - ymin) <= 1e-9:
                return 0
            nx = int((xmax - xmin) / cell)
            ny = int((ymax - ymin) / cell)
            return int(max(0, nx) * max(0, ny))
        except Exception:
            return None

    def _mesh_facets(self, mesh_obj):
        try:
            return int(getattr(getattr(mesh_obj, "Mesh", None), "CountFacets", 0))
        except Exception:
            return 0

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
            scale=float(self._scale),
        )

    def _estimate_triangle_checks(self, dsg_obj, eg_obj, est_samples=None):
        try:
            if dsg_obj is None or eg_obj is None:
                return None
            if est_samples is None:
                est_samples = self._estimate_samples(eg_obj)
            if est_samples is None:
                return None
            cell = float(self.spin_cell.value())
            margin = float(self.spin_margin.value())
            xmin, xmax, ymin, ymax = self._existing_bounds_local(eg_obj)
            xmin = float(xmin - margin)
            xmax = float(xmax + margin)
            ymin = float(ymin - margin)
            ymax = float(ymax + margin)
            area = max(1e-9, float(xmax - xmin) * float(ymax - ymin))
            max_tri_src = int(self.spin_max_tri_src.value())
            max_cand = int(self.spin_max_cand.value())
            tri_d = min(max_tri_src, self._mesh_facets(dsg_obj))
            tri_e = min(max_tri_src, self._mesh_facets(eg_obj))
            return estimate_triangle_checks(est_samples, cell, area, tri_d, tri_e, max_cand)
        except Exception:
            return None

    def _existing_bounds_local(self, eg_obj):
        bb = _source_bounds(eg_obj)
        xmin = float(bb.XMin)
        xmax = float(bb.XMax)
        ymin = float(bb.YMin)
        ymax = float(bb.YMax)
        if not self._use_world_existing_mode():
            return xmin, xmax, ymin, ymax

        return _ct.world_xy_bounds_to_local(xmin, xmax, ymin, ymax, doc_or_obj=self._coord_context_obj())

    def _update_estimate_hint(self):
        dsg = self._current_dsg()
        eg = self._current_eg()
        est_s = self._estimate_samples(eg) if eg is not None else None
        est_c = self._estimate_triangle_checks(dsg, eg, est_samples=est_s) if (dsg is not None and eg is not None) else None
        update_estimate_label(
            self.lbl_est,
            est_s,
            est_c,
            int(self.spin_max_samples.value()),
            int(self.spin_max_checks.value()),
            "Estimate: select valid sources to compute estimate",
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

    def _create_or_get_design_terrain(self):
        dtm = _find_design_terrain(self.doc)
        if dtm is not None:
            try:
                ensure_design_terrain_properties(dtm)
            except Exception:
                pass
            return dtm
        dtm = self.doc.addObject("Mesh::FeaturePython", "DesignTerrain")
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
        est_checks = self._estimate_triangle_checks(dsg, eg, est_samples=est)
        max_checks = int(self.spin_max_checks.value())
        if est_checks is not None and est_checks > max_checks:
            QtWidgets.QMessageBox.warning(
                None,
                "Design Terrain",
                f"Estimated triangle checks {est_checks} exceed Max Triangle Checks {max_checks}.\n"
                "Increase Cell Size, reduce margin, or lower triangle limits.",
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
            if hasattr(dtm, "ExistingTerrainCoords"):
                dtm.ExistingTerrainCoords = "World" if self._use_world_existing_mode() else "Local"
            dtm.CellSize = float(self.spin_cell.value())
            dtm.MaxSamples = int(self.spin_max_samples.value())
            if hasattr(dtm, "MaxTrianglesPerSource"):
                dtm.MaxTrianglesPerSource = int(self.spin_max_tri_src.value())
            if hasattr(dtm, "MaxCandidateTriangles"):
                dtm.MaxCandidateTriangles = int(self.spin_max_cand.value())
            if hasattr(dtm, "MaxTriangleChecks"):
                dtm.MaxTriangleChecks = int(self.spin_max_checks.value())
            dtm.DomainMargin = float(self.spin_margin.value())
            dtm.AutoUpdate = bool(self.chk_auto.isChecked())
            dtm.RebuildNow = True
        finally:
            if proxy is not None and hasattr(proxy, "_bulk_updating"):
                proxy._bulk_updating = False

        prj = find_project(self.doc)
        if prj is not None:
            link_project(
                prj,
                links={
                    "Terrain": eg,
                    "DesignGradingSurface": dsg,
                    "DesignTerrain": dtm,
                },
                adopt_extra=[dsg, eg, dtm],
            )

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
            f"ExistingTerrainCoords: {str(getattr(dtm, 'ExistingTerrainCoords', 'Local'))}",
            f"Samples(valid/total): {int(getattr(dtm, 'ValidCount', 0))} / {int(getattr(dtm, 'SampleCount', 0))}",
            f"NoDataArea: {float(getattr(dtm, 'NoDataArea', 0.0)):.3f} (scaled^2)",
            f"CellSize: {float(getattr(dtm, 'CellSize', 0.0)):.3f} (scaled)",
            f"MaxTriangles/Source: {int(getattr(dtm, 'MaxTrianglesPerSource', 0))}",
            f"MaxCandidateTriangles: {int(getattr(dtm, 'MaxCandidateTriangles', 0))}",
            f"MaxTriangleChecks: {int(getattr(dtm, 'MaxTriangleChecks', 0))}",
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

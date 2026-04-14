# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui
from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.doc_query import find_all, find_first, find_project
from freecad.Corridor_Road.objects.obj_project import find_region_plan_objects
from freecad.Corridor_Road.objects.project_links import link_project
from freecad.Corridor_Road.objects.obj_centerline3d_display import (
    Centerline3DDisplay,
    ViewProviderCenterline3DDisplay,
    ensure_centerline3d_display_properties,
)


def _find_alignments(doc):
    return find_all(doc, proxy_type="HorizontalAlignment", name_prefixes=("HorizontalAlignment",))


def _find_stationings(doc):
    return find_all(doc, proxy_type="Stationing", name_prefixes=("Stationing",))


def _find_vertical_alignments(doc):
    return find_all(doc, proxy_type="VerticalAlignment", name_prefixes=("VerticalAlignment",))


def _find_profile_bundles(doc):
    return find_all(doc, proxy_type="ProfileBundle", name_prefixes=("ProfileBundle",))


def _find_centerline3d_display(doc):
    return find_all(doc, proxy_type="Centerline3DDisplay", name_prefixes=("Centerline3DDisplay",))


def _find_centerline3d_engine(doc):
    return find_first(
        doc,
        proxy_type="Centerline3D",
        name_prefixes=("Centerline3D",),
        predicate=lambda o: not str(getattr(o, "Name", "")).startswith("Centerline3DDisplay"),
    )


def _find_structure_sets(doc):
    return find_all(doc, proxy_type="StructureSet", name_prefixes=("StructureSet",))


def _find_region_plans(doc):
    return find_region_plan_objects(doc)


class Centerline3DTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._project = None
        self._loading = False
        self._alignments = []
        self._stationings = []
        self._verticals = []
        self._profiles = []
        self._structures = []
        self._regions = []
        self._displays = []
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
        w.setWindowTitle("CorridorRoad - 3D Centerline Display")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        gb_src = QtWidgets.QGroupBox("Sources")
        fs = QtWidgets.QFormLayout(gb_src)
        self.cmb_alignment = QtWidgets.QComboBox()
        self.cmb_stationing = QtWidgets.QComboBox()
        self.cmb_vertical = QtWidgets.QComboBox()
        self.cmb_profile = QtWidgets.QComboBox()
        self.cmb_region = QtWidgets.QComboBox()
        self.cmb_structure = QtWidgets.QComboBox()
        self.chk_use_stationing = QtWidgets.QCheckBox("Use Stationing values when available")
        self.chk_use_stationing.setChecked(True)
        self.cmb_elevation = QtWidgets.QComboBox()
        self.cmb_elevation.addItems(["Auto", "VerticalAlignment", "ProfileBundleFG", "FlatZero"])
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fs.addRow("Alignment:", self.cmb_alignment)
        fs.addRow("Stationing:", self.cmb_stationing)
        fs.addRow("Vertical Alignment:", self.cmb_vertical)
        fs.addRow("ProfileBundle:", self.cmb_profile)
        fs.addRow("RegionPlan:", self.cmb_region)
        fs.addRow("StructureSet:", self.cmb_structure)
        fs.addRow(self.chk_use_stationing)
        fs.addRow("Elevation Source:", self.cmb_elevation)
        fs.addRow(self.btn_refresh)
        main.addWidget(gb_src)

        gb_display = QtWidgets.QGroupBox("Display")
        fd = QtWidgets.QFormLayout(gb_display)
        self.cmb_target = QtWidgets.QComboBox()
        self.chk_show_wire = QtWidgets.QCheckBox("Show sampled 3D centerline wire")
        self.chk_show_wire.setChecked(True)
        self.chk_use_keys = QtWidgets.QCheckBox("Use key stations for segmentation")
        self.chk_use_keys.setChecked(True)
        self.chk_segment_regions = QtWidgets.QCheckBox("Split by region boundaries and transitions")
        self.chk_segment_regions.setChecked(True)
        self.chk_segment_structures = QtWidgets.QCheckBox("Split by structure boundaries and transitions")
        self.chk_segment_structures.setChecked(True)
        self.cmb_quality = QtWidgets.QComboBox()
        self.cmb_quality.addItems(["Fast", "Normal", "Fine", "Ultra"])
        self.cmb_quality.setCurrentText("Normal")
        fd.addRow("Target Display:", self.cmb_target)
        fd.addRow(self.chk_show_wire)
        fd.addRow(self.chk_use_keys)
        fd.addRow(self.chk_segment_regions)
        fd.addRow(self.chk_segment_structures)
        fd.addRow("Display Quality:", self.cmb_quality)
        main.addWidget(gb_display)

        gb_sampling = QtWidgets.QGroupBox("Sampling")
        fo = QtWidgets.QFormLayout(gb_sampling)
        unit = self._display_unit()
        scale = self._display_scale()
        self.spin_err = QtWidgets.QDoubleSpinBox()
        self.spin_err.setRange(0.0001 * scale, 1000.0 * scale)
        self.spin_err.setDecimals(4)
        self.spin_err.setSuffix(f" {unit}")
        self.spin_err.setValue(self._meters_to_display(0.02))
        self.spin_min = QtWidgets.QDoubleSpinBox()
        self.spin_min.setRange(0.001 * scale, 1000.0 * scale)
        self.spin_min.setDecimals(4)
        self.spin_min.setSuffix(f" {unit}")
        self.spin_min.setValue(self._meters_to_display(0.5))
        self.spin_max = QtWidgets.QDoubleSpinBox()
        self.spin_max.setRange(0.001 * scale, 10000.0 * scale)
        self.spin_max.setDecimals(4)
        self.spin_max.setSuffix(f" {unit}")
        self.spin_max.setValue(self._meters_to_display(10.0))
        fo.addRow(f"Max Chord Error ({unit}):", self.spin_err)
        fo.addRow(f"Min Step ({unit}):", self.spin_min)
        fo.addRow(f"Max Step ({unit}):", self.spin_max)
        main.addWidget(gb_sampling)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_generate = QtWidgets.QPushButton("Build 3D Centerline Display")
        self.btn_close = QtWidgets.QPushButton("Close")
        row_btn.addWidget(self.btn_generate)
        row_btn.addWidget(self.btn_close)
        main.addLayout(row_btn)

        gb_run = QtWidgets.QGroupBox("Run")
        fr = QtWidgets.QFormLayout(gb_run)
        self.lbl_status = QtWidgets.QLabel("Idle")
        self.lbl_status.setWordWrap(True)
        fr.addRow("Status:", self.lbl_status)
        main.addWidget(gb_run)

        self.btn_refresh.clicked.connect(self._refresh_context)
        self.cmb_target.currentIndexChanged.connect(self._on_target_changed)
        self.btn_generate.clicked.connect(self._build)
        self.btn_close.clicked.connect(self.reject)
        return w

    @staticmethod
    def _fmt_obj(prefix: str, obj):
        return f"[{prefix}] {obj.Label} ({obj.Name})"

    def _display_unit(self):
        return _units.get_linear_display_unit(self._project or self.doc)

    def _display_scale(self):
        return max(1.0e-9, _units.user_length_from_meters(self._project or self.doc, 1.0))

    def _meters_to_display(self, meters):
        return _units.user_length_from_meters(self._project or self.doc, meters)

    def _display_to_meters(self, value):
        return _units.meters_from_user_length(self._project or self.doc, value, use_default="display")

    def _set_combo_to_object(self, combo, target_obj):
        if combo is None:
            return
        for idx in range(combo.count()):
            if combo.itemData(idx) == target_obj:
                combo.setCurrentIndex(idx)
                return
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    def _current_obj(self, combo):
        if combo is None or combo.currentIndex() < 0:
            return None
        return combo.itemData(combo.currentIndex())

    def _populate_optional_combo(self, combo, objects, prefix: str, include_none_label: str):
        combo.clear()
        combo.addItem(include_none_label, None)
        for obj in list(objects or []):
            combo.addItem(self._fmt_obj(prefix, obj), obj)

    def _populate_required_combo(self, combo, objects, prefix: str):
        combo.clear()
        for obj in list(objects or []):
            combo.addItem(self._fmt_obj(prefix, obj), obj)

    def _populate_target_combo(self, current_display=None):
        self.cmb_target.clear()
        self.cmb_target.addItem("[New] Create new 3D centerline display", None)
        for obj in list(self._displays or []):
            self.cmb_target.addItem(self._fmt_obj("Display", obj), obj)
        self._set_combo_to_object(self.cmb_target, current_display)

    def _load_from_display(self, obj):
        if obj is None:
            return
        self._loading = True
        try:
            self._set_combo_to_object(self.cmb_alignment, getattr(obj, "Alignment", None))
            self._set_combo_to_object(self.cmb_stationing, getattr(obj, "Stationing", None))
            self._set_combo_to_object(self.cmb_vertical, getattr(obj, "VerticalAlignment", None))
            self._set_combo_to_object(self.cmb_profile, getattr(obj, "ProfileBundle", None))
            self._set_combo_to_object(self.cmb_region, getattr(obj, "RegionPlanSource", None))
            self._set_combo_to_object(self.cmb_structure, getattr(obj, "StructureSetSource", None))
            self.chk_use_stationing.setChecked(bool(getattr(obj, "UseStationing", True)))
            self.chk_show_wire.setChecked(bool(getattr(obj, "ShowWire", True)))
            self.chk_use_keys.setChecked(bool(getattr(obj, "UseKeyStations", True)))
            self.chk_segment_regions.setChecked(bool(getattr(obj, "SegmentByRegions", True)))
            self.chk_segment_structures.setChecked(bool(getattr(obj, "SegmentByStructures", True)))
            self.cmb_elevation.setCurrentText(str(getattr(obj, "ElevationSource", "Auto") or "Auto"))
            self.cmb_quality.setCurrentText(str(getattr(obj, "DisplayQuality", "Normal") or "Normal"))
            self.spin_err.setValue(self._meters_to_display(float(getattr(obj, "MaxChordError", 0.02) or 0.02)))
            self.spin_min.setValue(self._meters_to_display(float(getattr(obj, "MinStep", 0.5) or 0.5)))
            self.spin_max.setValue(self._meters_to_display(float(getattr(obj, "MaxStep", 10.0) or 10.0)))
        finally:
            self._loading = False

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return
        self._project = find_project(self.doc)
        self._alignments = _find_alignments(self.doc)
        self._stationings = _find_stationings(self.doc)
        self._verticals = _find_vertical_alignments(self.doc)
        self._profiles = _find_profile_bundles(self.doc)
        self._regions = _find_region_plans(self.doc)
        self._structures = _find_structure_sets(self.doc)
        self._displays = _find_centerline3d_display(self.doc)

        current_display = self._current_obj(self.cmb_target)
        self._populate_required_combo(self.cmb_alignment, self._alignments, "Alignment")
        self._populate_optional_combo(self.cmb_stationing, self._stationings, "Stationing", "[None] No stationing")
        self._populate_optional_combo(self.cmb_vertical, self._verticals, "VA", "[None] No vertical alignment")
        self._populate_optional_combo(self.cmb_profile, self._profiles, "Profile", "[None] No profile bundle")
        self._populate_optional_combo(self.cmb_region, self._regions, "RegionPlan", "[None] Auto-detect from project")
        self._populate_optional_combo(self.cmb_structure, self._structures, "StructureSet", "[None] Auto-detect from project")
        self._populate_target_combo(current_display=current_display)

        if self._alignments:
            if self.cmb_alignment.currentIndex() < 0:
                self.cmb_alignment.setCurrentIndex(0)

        chosen_display = self._current_obj(self.cmb_target)
        if chosen_display is not None:
            self._load_from_display(chosen_display)
        else:
            self._loading = True
            try:
                pref_region = getattr(self._project, "RegionPlan", None) if self._project is not None and hasattr(self._project, "RegionPlan") else None
                if pref_region is None and self._regions:
                    pref_region = self._regions[0]
                pref_structure = getattr(self._project, "StructureSet", None) if self._project is not None and hasattr(self._project, "StructureSet") else None
                if pref_structure is None and self._structures:
                    pref_structure = self._structures[0]
                self._set_combo_to_object(self.cmb_region, pref_region)
                self._set_combo_to_object(self.cmb_structure, pref_structure)
                self.chk_use_stationing.setChecked(bool(self._stationings))
                self.cmb_elevation.setCurrentText("Auto" if (self._verticals or self._profiles) else "FlatZero")
                self.chk_segment_regions.setChecked(pref_region is not None)
                self.chk_segment_structures.setChecked(pref_structure is not None)
                self.cmb_quality.setCurrentText("Normal")
                self.spin_err.setValue(self._meters_to_display(0.02))
                self.spin_min.setValue(self._meters_to_display(0.5))
                self.spin_max.setValue(self._meters_to_display(10.0))
            finally:
                self._loading = False

        info = [
            f"Alignment: {len(self._alignments)} found",
            f"Stationing: {len(self._stationings)} found",
            f"VerticalAlignment: {len(self._verticals)} found",
            f"ProfileBundle: {len(self._profiles)} found",
            f"RegionPlan: {len(self._regions)} found",
            f"StructureSet: {len(self._structures)} found",
            f"Centerline Display: {len(self._displays)} found",
            "This command builds a sampled display wire only. Station-based frames remain the engineering source of truth.",
            "Choose Display Quality first for normal review work. Region/structure split controls only affect display segmentation and diagnostics.",
        ]
        self.lbl_info.setText("\n".join(info))
        self._update_status()

    def _on_target_changed(self, *_args):
        if self._loading:
            return
        obj = self._current_obj(self.cmb_target)
        if obj is not None:
            self._load_from_display(obj)
        self._update_status()

    def _status_text(self, obj):
        if obj is None:
            return "Ready to build sampled display wire."
        lines = [str(getattr(obj, "Status", "Ready") or "Ready")]
        sample_count = int(getattr(obj, "SampleCount", 0) or 0)
        segment_count = int(getattr(obj, "SegmentCount", 0) or 0)
        quality = str(getattr(obj, "DisplayQuality", "Normal") or "Normal")
        policy = str(getattr(obj, "SamplingPolicySummary", "-") or "-")
        split_summary = str(getattr(obj, "SegmentSplitSourceSummary", "-") or "-")
        lines.append(f"Samples: {sample_count} | Segments: {segment_count} | Quality: {quality}")
        if policy != "-":
            lines.append(f"Sampling: {policy}")
        if split_summary != "-":
            lines.append(f"Split Sources: {split_summary}")
        return "\n".join(lines)

    def _update_status(self):
        self.lbl_status.setText(self._status_text(self._current_obj(self.cmb_target)))

    def _ensure_display(self):
        disp = self._current_obj(self.cmb_target)
        if disp is not None:
            ensure_centerline3d_display_properties(disp)
            return disp
        disp = self.doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
        Centerline3DDisplay(disp)
        if getattr(disp, "ViewObject", None) is not None:
            ViewProviderCenterline3DDisplay(disp.ViewObject)
        disp.Label = "3D Centerline (H+V)"
        self._displays = list(self._displays or []) + [disp]
        self._populate_target_combo(current_display=disp)
        return disp

    def _cleanup_legacy_engine(self, disp):
        cl = _find_centerline3d_engine(self.doc)
        if cl is None:
            return
        if hasattr(disp, "SourceCenterline") and getattr(disp, "SourceCenterline", None) == cl:
            disp.SourceCenterline = None
        prj = self._project
        if prj is not None and hasattr(prj, "Centerline3D") and getattr(prj, "Centerline3D", None) == cl:
            prj.Centerline3D = None
        try:
            self.doc.removeObject(cl.Name)
        except Exception:
            pass

    def _build_completion_message(self, disp):
        lines = [
            "3D centerline display build completed.",
            f"Sampled stations: {int(getattr(disp, 'SampleCount', 0) or 0)}",
            f"Planned segments: {int(getattr(disp, 'SegmentCount', 0) or 0)}",
            f"Display quality: {str(getattr(disp, 'DisplayQuality', 'Normal') or 'Normal')}",
        ]
        policy = str(getattr(disp, "SamplingPolicySummary", "-") or "-")
        split_summary = str(getattr(disp, "SegmentSplitSourceSummary", "-") or "-")
        if policy != "-":
            lines.append(f"Sampling: {policy}")
        if split_summary != "-":
            lines.append(f"Split sources: {split_summary}")
        lines.append("Design frames remain station-based.")
        return "\n".join(lines)

    def _build(self):
        if self.doc is None:
            raise Exception("No active document.")

        aln = self._current_obj(self.cmb_alignment)
        if aln is None:
            raise Exception("No HorizontalAlignment found. Create/Edit alignment first.")

        st = self._current_obj(self.cmb_stationing)
        va = self._current_obj(self.cmb_vertical)
        pb = self._current_obj(self.cmb_profile)
        region = self._current_obj(self.cmb_region)
        structure = self._current_obj(self.cmb_structure)
        disp = self._ensure_display()

        ensure_centerline3d_display_properties(disp)
        disp.Alignment = aln
        disp.Stationing = st
        disp.VerticalAlignment = va
        disp.ProfileBundle = pb
        disp.RegionPlanSource = region
        disp.StructureSetSource = structure
        disp.UseStationing = bool(self.chk_use_stationing.isChecked()) and (st is not None)
        disp.ElevationSource = str(self.cmb_elevation.currentText() or "Auto")
        disp.ShowWire = bool(self.chk_show_wire.isChecked())
        disp.UseKeyStations = bool(self.chk_use_keys.isChecked())
        disp.SegmentByRegions = bool(self.chk_segment_regions.isChecked()) and (region is not None or bool(self._regions))
        disp.SegmentByStructures = bool(self.chk_segment_structures.isChecked()) and (structure is not None or bool(self._structures))
        disp.DisplayQuality = str(self.cmb_quality.currentText() or "Normal")
        disp.MaxChordError = self._display_to_meters(float(self.spin_err.value()))
        disp.MinStep = self._display_to_meters(float(self.spin_min.value()))
        disp.MaxStep = self._display_to_meters(float(self.spin_max.value()))
        disp.SourceCenterline = None
        disp.touch()

        self._cleanup_legacy_engine(disp)

        prj = self._project
        if prj is not None:
            link_project(
                prj,
                links={"Centerline3DDisplay": disp},
                links_if_empty={"Alignment": aln, "Stationing": st},
                adopt_extra=[disp],
            )

        struct = structure
        if struct is None and prj is not None and hasattr(prj, "StructureSet"):
            struct = getattr(prj, "StructureSet", None)
        if struct is None:
            structs = _find_structure_sets(self.doc)
            struct = structs[0] if structs else None
        if struct is not None:
            try:
                struct.touch()
            except Exception:
                pass

        self.doc.recompute()
        self._populate_target_combo(current_display=disp)
        self._update_status()

        QtWidgets.QMessageBox.information(
            None,
            "3D Centerline Display",
            self._build_completion_message(disp),
        )

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass

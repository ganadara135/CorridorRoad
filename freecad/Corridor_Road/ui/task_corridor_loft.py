# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui
from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_all, find_project
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft, ViewProviderCorridorLoft, ensure_corridor_loft_properties
from freecad.Corridor_Road.objects.obj_project import (
    assign_project_corridor,
    find_corridor_objects,
    resolve_project_corridor,
)
from freecad.Corridor_Road.objects.obj_section_set import region_plan_usage_enabled
from freecad.Corridor_Road.objects.project_links import link_project


def _find_section_sets(doc):
    return find_all(doc, proxy_type="SectionSet", name_prefixes=("SectionSet",))


def _find_corridor_lofts(doc):
    return find_corridor_objects(doc)


class CorridorTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._sections = []
        self._corridors = []
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
        w.setWindowTitle("CorridorRoad - Corridor")

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
        fs.addRow("Target Corridor:", self.cmb_target)
        fs.addRow(self.btn_refresh)
        main.addWidget(gb_src)

        gb_opt = QtWidgets.QGroupBox("Options")
        form_opts = QtWidgets.QFormLayout(gb_opt)
        unit = self._display_unit()
        display_scale = self._display_scale()
        self.spin_min_spacing = QtWidgets.QDoubleSpinBox()
        self.spin_min_spacing.setRange(0.0, 10000.0 * display_scale)
        self.spin_min_spacing.setDecimals(3)
        self.spin_min_spacing.setSuffix(f" {unit}")
        self.spin_min_spacing.setValue(self._meters_to_display(0.50))
        self.chk_ruled = QtWidgets.QCheckBox("Use ruled surface")
        self.chk_ruled.setChecked(False)
        self.chk_auto_ruled_typical = QtWidgets.QCheckBox("Auto-use ruled surface for Typical Section")
        self.chk_auto_ruled_typical.setChecked(True)
        self.chk_fix_orientation = QtWidgets.QCheckBox("Auto-fix flipped sections")
        self.chk_fix_orientation.setChecked(True)
        self.chk_structure_split = QtWidgets.QCheckBox("Split at structure zones")
        self.chk_structure_split.setChecked(True)
        self.chk_structure_modes = QtWidgets.QCheckBox("Use structure corridor modes")
        self.chk_structure_modes.setChecked(True)
        self.chk_region_modes = QtWidgets.QCheckBox("Use region corridor modes")
        self.chk_region_modes.setChecked(True)
        self.cmb_default_structure_mode = QtWidgets.QComboBox()
        self.cmb_default_structure_mode.addItems(["none", "split_only", "skip_zone"])
        self.cmb_default_structure_mode.setCurrentText("split_only")
        self.spin_notch_transition_scale = QtWidgets.QDoubleSpinBox()
        self.spin_notch_transition_scale.setRange(0.1, 10.0)
        self.spin_notch_transition_scale.setDecimals(2)
        self.spin_notch_transition_scale.setSingleStep(0.1)
        self.spin_notch_transition_scale.setValue(1.0)
        self.chk_auto = QtWidgets.QCheckBox("Auto update on source changes")
        self.chk_auto.setChecked(True)
        form_opts.addRow(f"Min Section Spacing ({unit}):", self.spin_min_spacing)
        form_opts.addRow(self.chk_ruled)
        form_opts.addRow(self.chk_auto_ruled_typical)
        form_opts.addRow(self.chk_fix_orientation)
        form_opts.addRow(self.chk_structure_split)
        form_opts.addRow(self.chk_structure_modes)
        form_opts.addRow(self.chk_region_modes)
        form_opts.addRow("Default structure corridor mode:", self.cmb_default_structure_mode)
        form_opts.addRow("Notch transition scale:", self.spin_notch_transition_scale)
        form_opts.addRow(self.chk_auto)
        main.addWidget(gb_opt)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_build = QtWidgets.QPushButton("Build Corridor")
        self.btn_close = QtWidgets.QPushButton("Close")
        row_btn.addWidget(self.btn_build)
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
        self.btn_build.clicked.connect(self._build)
        self.btn_close.clicked.connect(self.reject)
        return w

    @staticmethod
    def _fmt_obj(prefix: str, obj):
        return f"[{prefix}] {obj.Label} ({obj.Name})"

    def _display_unit(self):
        return _units.get_linear_display_unit(self.doc)

    def _display_scale(self):
        return max(1.0e-9, _units.user_length_from_meters(self.doc, 1.0))

    def _meters_to_display(self, meters):
        return _units.user_length_from_meters(self.doc, meters)

    def _display_to_meters(self, value):
        return _units.meters_from_user_length(self.doc, value, use_default="display")

    @staticmethod
    def _status_text(cor):
        if cor is None:
            return "Ready"
        base_status = str(getattr(cor, "Status", "Ready") or "Ready")
        diag_summary = str(getattr(cor, "DiagnosticSummary", "-") or "-")
        diag_classes = str(getattr(cor, "DiagnosticClassSummary", "-") or "-")
        profile_contract = str(getattr(cor, "ProfileContractSource", "-") or "-")
        segment_profile_contracts = str(getattr(cor, "SegmentProfileContractSummary", "-") or "-")
        segment_package_summary = str(getattr(cor, "SegmentPackageSummary", "-") or "-")
        kept_segments = int(getattr(cor, "CorridorSegmentCount", 0) or 0)
        package_count = int(getattr(cor, "SegmentPackageCount", 0) or 0)
        object_count = int(getattr(cor, "SegmentObjectCount", 0) or 0)
        skipped_segments = int(getattr(cor, "SkippedSegmentCount", 0) or 0)
        mode_summary = str(getattr(cor, "ResolvedCombinedCorridorModeSummary", "-") or "-")
        lines = [base_status]
        if diag_summary != "-":
            lines.append(f"Diagnostics: {diag_summary}")
        if diag_classes != "-":
            lines.append(f"Classes: {diag_classes}")
        if profile_contract != "-" or segment_profile_contracts != "-":
            lines.append(
                f"Profile contract: result={profile_contract}, packages={segment_profile_contracts}"
            )
        if segment_package_summary != "-":
            lines.append(f"Package summary: {segment_package_summary}")
        lines.append(
            f"Segments: kept={kept_segments}, packages={package_count}, objects={object_count}, skipped={skipped_segments}"
        )
        if mode_summary != "-":
            lines.append(f"Modes: {mode_summary}")
        return "\n".join(lines)

    def _build_completion_message(self, cor, sec):
        n = len(list(getattr(sec, "StationValues", []) or []))
        src_schema = int(getattr(sec, "SectionSchemaVersion", 1) or 1)
        top_profile = str(getattr(sec, "TopProfileSource", "assembly_simple") or "assembly_simple")
        top_edges = str(getattr(sec, "TopProfileEdgeSummary", "-") or "-")
        advanced_components = int(getattr(cor, "TypicalSectionAdvancedComponentCount", 0) or 0)
        pavement_layers = int(getattr(cor, "PavementLayerCount", 0) or 0)
        pavement_layers_enabled = int(getattr(cor, "EnabledPavementLayerCount", 0) or 0)
        pavement_total = float(getattr(cor, "PavementTotalThickness", 0.0) or 0.0)
        pt_count = int(getattr(cor, "PointCountPerSection", 0) or 0)
        ruled_mode = str(getattr(cor, "ResolvedRuledMode", "off") or "off")
        structure_seg_count = int(getattr(cor, "StructureSegmentCount", 0) or 0)
        corridor_segment_count = int(getattr(cor, "CorridorSegmentCount", 0) or 0)
        segment_package_count = int(getattr(cor, "SegmentPackageCount", 0) or 0)
        segment_object_count = int(getattr(cor, "SegmentObjectCount", 0) or 0)
        skipped_segment_count = int(getattr(cor, "SkippedSegmentCount", 0) or 0)
        segment_kind_summary = str(getattr(cor, "SegmentKindSummary", "-") or "-")
        segment_source_summary = str(getattr(cor, "SegmentSourceSummary", "-") or "-")
        segment_driver_source_summary = str(getattr(cor, "SegmentDriverSourceSummary", "-") or "-")
        segment_driver_mode_summary = str(getattr(cor, "SegmentDriverModeSummary", "-") or "-")
        segment_profile_contract_summary = str(getattr(cor, "SegmentProfileContractSummary", "-") or "-")
        segment_package_summary = str(getattr(cor, "SegmentPackageSummary", "-") or "-")
        segment_display_summary = str(getattr(cor, "SegmentDisplaySummary", "-") or "-")
        profile_contract_source = str(getattr(cor, "ProfileContractSource", "-") or "-")
        diag_summary = str(getattr(cor, "DiagnosticSummary", "-") or "-")
        diag_classes = str(getattr(cor, "DiagnosticClassSummary", "-") or "-")
        diag_source = str(getattr(cor, "SourceDiagnostic", "-") or "-")
        diag_connectivity = str(getattr(cor, "ConnectivityDiagnostic", "-") or "-")
        diag_packaging = str(getattr(cor, "PackagingDiagnostic", "-") or "-")
        diag_policy = str(getattr(cor, "PolicyDiagnostic", "-") or "-")
        skipped_ranges = list(getattr(cor, "SkippedStationRanges", []) or [])
        corridor_mode_summary = str(getattr(cor, "ResolvedStructureCorridorModeSummary", "-") or "-")
        region_corridor_mode_summary = str(getattr(cor, "ResolvedRegionCorridorModeSummary", "-") or "-")
        combined_corridor_mode_summary = str(getattr(cor, "ResolvedCombinedCorridorModeSummary", "-") or "-")
        corridor_warning_count = len(list(getattr(cor, "ResolvedStructureCorridorWarnings", []) or []))
        region_corridor_warning_count = len(list(getattr(cor, "ResolvedRegionCorridorWarnings", []) or []))
        combined_corridor_warning_count = len(list(getattr(cor, "ResolvedCombinedCorridorWarnings", []) or []))
        skip_boundary_behavior = str(getattr(cor, "ResolvedSkipBoundaryBehavior", "-") or "-")
        skip_boundary_states = list(getattr(cor, "ResolvedSkipBoundaryStates", []) or [])
        segment_summary_rows = list(getattr(cor, "SegmentSummaryRows", []) or [])
        notch_count = int(getattr(cor, "ResolvedStructureNotchCount", 0) or 0)
        notch_station_count = int(getattr(cor, "ResolvedNotchStationCount", 0) or 0)
        notch_schema_name = str(getattr(cor, "ResolvedNotchSchemaName", "-") or "-")
        notch_profile_summary = str(getattr(cor, "ResolvedNotchProfileSummary", "-") or "-")
        notch_build_mode = str(getattr(cor, "ResolvedNotchBuildMode", "-") or "-")
        notch_cutter_count = int(getattr(cor, "ResolvedNotchCutterCount", 0) or 0)
        closed_profile_schema = int(getattr(cor, "ClosedProfileSchemaVersion", 1) or 1)
        skip_marker_count = int(getattr(cor, "SkipMarkerCount", 0) or 0)
        return (
            f"Corridor build completed.\n"
            f"Display unit: {self._display_unit()}\n"
            f"Sections used: {n}\n"
            f"Points per section: {pt_count}\n"
            f"Source section schema: {src_schema}\n"
            f"Top profile source: {top_profile}\n"
            f"Top profile edges: {top_edges}\n"
            f"Typical advanced components: {advanced_components}\n"
            f"Pavement layers: {pavement_layers_enabled}/{pavement_layers}\n"
            f"Pavement total thickness: {_units.format_internal_length(self.doc, pavement_total)}\n"
            f"Output mode: surface\n"
            f"Ruled mode: {ruled_mode}\n"
            f"Corridor-aware segments: {structure_seg_count}\n"
            f"Segment packages: {segment_package_count}\n"
            f"Segment objects: {segment_object_count}\n"
            f"Kept corridor segments: {corridor_segment_count}\n"
            f"Skipped segment rows: {skipped_segment_count}\n"
            f"Segment summary rows: {len(segment_summary_rows)}\n"
            f"Segment kinds: {segment_kind_summary}\n"
            f"Segment drivers: {segment_source_summary}\n"
            f"Segment driver sources: {segment_driver_source_summary}\n"
            f"Segment driver modes: {segment_driver_mode_summary}\n"
            f"Segment profile contracts: {segment_profile_contract_summary}\n"
            f"Segment package summary: {segment_package_summary}\n"
            f"Segment display: {segment_display_summary}\n"
            f"Profile contract source: {profile_contract_source}\n"
            f"Diagnostic summary: {diag_summary}\n"
            f"Diagnostic classes: {diag_classes}\n"
            f"Source diagnostic: {diag_source}\n"
            f"Connectivity diagnostic: {diag_connectivity}\n"
            f"Packaging diagnostic: {diag_packaging}\n"
            f"Policy diagnostic: {diag_policy}\n"
            f"Effective corridor modes: {combined_corridor_mode_summary}\n"
            f"Effective corridor warnings: {combined_corridor_warning_count}\n"
            f"Structure corridor modes: {corridor_mode_summary}\n"
            f"Structure corridor warnings: {corridor_warning_count}\n"
            f"Region corridor modes: {region_corridor_mode_summary}\n"
            f"Region corridor warnings: {region_corridor_warning_count}\n"
            f"Skipped corridor ranges: {len(skipped_ranges)}\n"
            f"Skip boundary behavior: {skip_boundary_behavior}\n"
            f"Skip boundary states: {len(skip_boundary_states)}\n"
            f"Skip boundary markers: {skip_marker_count}\n"
            f"Applied notches: {notch_count}\n"
            f"Notch-aware stations: {notch_station_count}\n"
            f"Notch schema: {notch_schema_name}\n"
            f"Notch profile summary: {notch_profile_summary}\n"
            f"Notch build mode: {notch_build_mode}\n"
            f"Notch cutter count: {notch_cutter_count}\n"
            f"Profile schema: {closed_profile_schema}\n"
            f"Status: {getattr(cor, 'Status', 'OK')}"
        )

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
        self.cmb_target.addItem("[New] Create new Corridor")
        for o in self._corridors:
            self.cmb_target.addItem(self._fmt_obj("Corridor", o))
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

    def _repair_corridor_object(self, cor):
        if cor is None:
            return None
        try:
            CorridorLoft(cor)
        except Exception:
            try:
                ensure_corridor_loft_properties(cor)
            except Exception:
                return None
        try:
            ViewProviderCorridorLoft(cor.ViewObject)
        except Exception:
            pass
        return cor

    def _candidate_corridors(self):
        out = []
        seen = set()

        def _add(o):
            if o is None:
                return
            key = getattr(o, "Name", None) or str(id(o))
            if key in seen:
                return
            seen.add(key)
            out.append(o)

        prj = find_project(self.doc)
        if prj is not None:
            _add(resolve_project_corridor(prj))
        for o in self._corridors:
            _add(o)
        return out

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
            selected_cor = resolve_project_corridor(prj) if prj is not None else None

            self._fill_sections(selected=selected_sec)
            self._fill_targets(selected=selected_cor)

            self.lbl_info.setText(
                f"SectionSet: {len(self._sections)} found, Corridor: {len(self._corridors)} found."
            )
        finally:
            self._loading = False
        self._on_target_changed()

    def _on_target_changed(self):
        if self._loading:
            return
        cor = self._current_target()
        if cor is None:
            self.spin_min_spacing.setValue(self._meters_to_display(0.50))
            self.chk_ruled.setChecked(False)
            self.chk_auto_ruled_typical.setChecked(True)
            self.chk_fix_orientation.setChecked(True)
            self.chk_structure_split.setChecked(True)
            self.chk_structure_modes.setChecked(True)
            self.chk_region_modes.setChecked(True)
            self.cmb_default_structure_mode.setCurrentText("split_only")
            self.spin_notch_transition_scale.setValue(1.0)
            self.chk_auto.setChecked(True)
            self.lbl_status.setText("New corridor will be created.")
            return

        try:
            ensure_corridor_loft_properties(cor)
        except Exception:
            pass
        try:
            self.spin_min_spacing.setValue(self._meters_to_display(float(getattr(cor, "MinSectionSpacing", 0.50) or 0.50)))
        except Exception:
            self.spin_min_spacing.setValue(self._meters_to_display(0.50))
        self.chk_ruled.setChecked(bool(getattr(cor, "UseRuled", False)))
        self.chk_auto_ruled_typical.setChecked(bool(getattr(cor, "AutoUseRuledForTypicalSection", True)))
        self.chk_fix_orientation.setChecked(bool(getattr(cor, "AutoFixSectionOrientation", True)))
        self.chk_structure_split.setChecked(bool(getattr(cor, "SplitAtStructureZones", True)))
        self.chk_structure_modes.setChecked(bool(getattr(cor, "UseStructureCorridorModes", True)))
        self.chk_region_modes.setChecked(bool(getattr(cor, "UseRegionCorridorModes", True)))
        self.cmb_default_structure_mode.setCurrentText(str(getattr(cor, "DefaultStructureCorridorMode", "split_only") or "split_only"))
        self.spin_notch_transition_scale.setValue(float(getattr(cor, "NotchTransitionScale", 1.0) or 1.0))
        self.chk_auto.setChecked(bool(getattr(cor, "AutoUpdate", True)))
        self.lbl_status.setText(self._status_text(cor))

    def _ensure_target_corridor(self):
        cor = self._current_target()
        if cor is not None:
            repaired = self._repair_corridor_object(cor)
            if repaired is not None:
                return repaired

        sec = self._current_section()
        for cand in self._candidate_corridors():
            try:
                if sec is not None and getattr(cand, "SourceSectionSet", None) == sec:
                    repaired = self._repair_corridor_object(cand)
                    if repaired is not None:
                        return repaired
            except Exception:
                pass

        for cand in self._candidate_corridors():
            repaired = self._repair_corridor_object(cand)
            if repaired is not None:
                return repaired

        cor = self.doc.addObject("Part::FeaturePython", "CorridorLoft")
        CorridorLoft(cor)
        ViewProviderCorridorLoft(cor.ViewObject)
        cor.Label = "Corridor"
        return cor

    def _preflight_warnings(self, sec):
        warnings = []
        if sec is None:
            return warnings

        try:
            if bool(self.chk_structure_modes.isChecked()) and bool(getattr(sec, "UseStructureSet", False)):
                fallback_mode = str(self.cmb_default_structure_mode.currentText() or "split_only")
                rows = CorridorLoft._resolve_structure_corridor_records(sec, fallback_mode=fallback_mode)
                _detail_rows, corridor_warning_rows, mode_summary, spans = CorridorLoft._describe_structure_corridor_records(rows)
                if any(str(mode or "").strip().lower() == "skip_zone" for _s0, _s1, mode in list(spans or [])):
                    warnings.append(
                        "skip_zone omits corridor body across active spans. Skip boundary caps are deferred in this phase and only skip markers are generated."
                    )
                if corridor_warning_rows:
                    warnings.append(
                        f"Structure corridor span resolution reported {len(list(corridor_warning_rows or []))} warning(s). Review StructureSet diagnostics if the result looks unexpected."
                    )
                if str(mode_summary or "-") not in ("", "-"):
                    warnings.append(f"Resolved structure corridor modes: {mode_summary}")
        except Exception:
            pass
        try:
            if bool(self.chk_region_modes.isChecked()) and bool(region_plan_usage_enabled(sec)):
                rows = CorridorLoft._resolve_region_corridor_records(sec)
                _detail_rows, region_warning_rows, mode_summary, spans = CorridorLoft._describe_region_corridor_records(rows)
                if any(str(mode or "").strip().lower() == "skip_zone" for _s0, _s1, mode in list(spans or [])):
                    warnings.append(
                        "Region skip_zone omits corridor body across active spans and uses the same deferred skip-boundary behavior as structure skip zones."
                    )
                if region_warning_rows:
                    warnings.append(
                        f"Region corridor span resolution reported {len(list(region_warning_rows or []))} warning(s). Review Region Plan corridor policies if the result looks unexpected."
                    )
                if str(mode_summary or "-") not in ("", "-"):
                    warnings.append(f"Resolved region corridor modes: {mode_summary}")
        except Exception:
            pass
        return warnings

    def _build(self):
        if self.doc is None:
            QtWidgets.QMessageBox.warning(None, "Corridor", "No active document.")
            return

        sec = self._current_section()
        if sec is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Corridor",
                "No SectionSet found. Run Generate Sections first.",
            )
            return

        preflight = self._preflight_warnings(sec)
        if preflight:
            reply = QtWidgets.QMessageBox.question(
                None,
                "Corridor",
                "Build corridor with warnings?\n\n" + "\n".join([f"- {line}" for line in preflight]),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                self.lbl_status.setText("Build cancelled after warning review.")
                return

        try:
            cor = self._ensure_target_corridor()
            ensure_corridor_loft_properties(cor)
            cor.SourceSectionSet = sec
            cor.UseRuled = bool(self.chk_ruled.isChecked())
            cor.AutoUseRuledForTypicalSection = bool(self.chk_auto_ruled_typical.isChecked())
            cor.AutoFixSectionOrientation = bool(self.chk_fix_orientation.isChecked())
            cor.SplitAtStructureZones = bool(self.chk_structure_split.isChecked())
            cor.UseStructureCorridorModes = bool(self.chk_structure_modes.isChecked())
            cor.UseRegionCorridorModes = bool(self.chk_region_modes.isChecked())
            cor.DefaultStructureCorridorMode = str(self.cmb_default_structure_mode.currentText() or "split_only")
            cor.NotchTransitionScale = float(self.spin_notch_transition_scale.value())
            cor.AutoUpdate = bool(self.chk_auto.isChecked())
            if hasattr(cor, "MinSectionSpacing"):
                cor.MinSectionSpacing = self._display_to_meters(float(self.spin_min_spacing.value()))
            cor.touch()

            prj = find_project(self.doc)
            if prj is not None:
                assign_project_corridor(prj, cor)
                link_project(
                    prj,
                    links_if_empty={"SectionSet": sec},
                    adopt_extra=[cor, sec],
                )

            self.doc.recompute()
            CorridorLoft.refresh_if_needed(cor, max_passes=2)
            marker_objs = []
            segment_objs = []
            try:
                marker_objs = [
                    o
                    for o in list(getattr(self.doc, "Objects", []) or [])
                    if str(getattr(o, "Name", "") or "").startswith("CorridorSkipMarker")
                    and getattr(o, "ParentCorridorLoft", None) == cor
                ]
            except Exception:
                marker_objs = []
            try:
                segment_objs = [
                    o
                    for o in list(getattr(self.doc, "Objects", []) or [])
                    if str(getattr(o, "Name", "") or "").startswith("CorridorSegment")
                    and getattr(o, "ParentCorridorLoft", None) == cor
                ]
            except Exception:
                segment_objs = []
            if prj is not None:
                try:
                    assign_project_corridor(prj, cor)
                    link_project(
                        prj,
                        links_if_empty={"SectionSet": sec},
                        adopt_extra=[cor, sec] + list(marker_objs) + list(segment_objs),
                    )
                except Exception:
                    pass
            self.lbl_status.setText(self._status_text(cor))
            QtWidgets.QMessageBox.information(
                None,
                "Corridor",
                self._build_completion_message(cor, sec),
            )
            self._refresh_context()
            try:
                Gui.ActiveDocument.ActiveView.fitAll()
            except Exception:
                pass
        except Exception as ex:
            self.lbl_status.setText(f"ERROR: {ex}")


# Legacy class alias retained for compatibility with older imports/tests.
CorridorLoftTaskPanel = CorridorTaskPanel

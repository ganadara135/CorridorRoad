"""Intersection source command for Parametric Road v1."""

from __future__ import annotations

from dataclasses import replace

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is unavailable in plain Python.
    App = None
try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCADGui is unavailable in plain Python.
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtWidgets

from ...objects.obj_project import CorridorRoadProject, ensure_project_tree, ensure_project_viewprovider, find_project
from ..models.source.drainage_model import DrainageElementRow, DrainageFlowRoute, DrainageModel, DrainagePolicySet
from ..models.source.intersection_model import IntersectionEdgePolicyRow
from ..models.source.superelevation_model import SuperelevationConstraint, SuperelevationModel
from .cmd_intersection_editor import (
    AlignmentIntersectionDetectionService,
    alignment_model_by_ref,
    build_intersection_model_from_sources,
    create_starter_intersection_sources,
    intersection_ref_for_kind,
    list_v1_alignment_choices,
    list_intersection_control_region_choices,
    set_intersection_edge_network_preview_visible,
    show_intersection_edge_network_preview,
    validate_existing_alignment_selection,
)
from ..objects.obj_drainage import create_or_update_v1_drainage_model_object
from ..objects.obj_intersection import create_or_update_v1_intersection_model_object
from ..objects.obj_superelevation import create_or_update_v1_superelevation_source_object


INTERSECTION_PRESETS_COMMAND_ID = "CorridorRoad_V1IntersectionPresets"

INTERSECTION_PRESET_ROWS: tuple[dict[str, object], ...] = (
    {
        "label": "T Intersection - Basic",
        "kind": "t_intersection",
        "legs": 3,
        "edge_note": "2 curb-return corners",
        "grading": "blend_primary_side",
        "drainage": "review_low_points",
        "summary": "Creates one primary road and one side-road source set for a basic T intersection.",
    },
    {
        "label": "Cross Intersection - Basic",
        "kind": "cross_intersection",
        "legs": 4,
        "edge_note": "4 curb-return corners",
        "grading": "blend_primary_side",
        "drainage": "review_low_points",
        "summary": "Creates primary and secondary through-road source sets for a four-leg intersection.",
    },
    {
        "label": "Skewed Intersection - Basic",
        "kind": "skewed_intersection",
        "legs": 4,
        "edge_note": "4 skew-aware curb-return corners",
        "grading": "blend_primary_side",
        "drainage": "review_low_points",
        "summary": "Creates primary and skewed secondary through-road source sets for a four-leg starter.",
    },
    {
        "label": "Urban Curb/Gutter - Basic",
        "kind": "urban_curb_gutter_intersection",
        "legs": 4,
        "edge_note": "curb, gutter, sidewalk, and inlet source hints",
        "grading": "blend_primary_side",
        "drainage": "curb_gutter_inlets",
        "summary": "Creates urban street source sets with curb, gutter, sidewalk, and inlet handoff intent.",
    },
    {
        "label": "Drainage-Sensitive Sag - Basic",
        "kind": "drainage_sag_intersection",
        "legs": 4,
        "edge_note": "sag low-point, inlet, and flow-route handoff hints",
        "grading": "blend_primary_side",
        "drainage": "sag_low_point_inlets",
        "summary": "Creates sag-profile source sets with low-point and drainage handoff intent.",
    },
    {
        "label": "Y Intersection - Basic",
        "kind": "y_intersection",
        "legs": 3,
        "edge_note": "2 diverging branch corners",
        "grading": "blend_primary_side",
        "drainage": "review_low_points",
        "summary": "Creates one primary approach and two branch source sets for a basic Y intersection.",
    },
    {
        "label": "Roundabout - Single Lane",
        "kind": "roundabout",
        "legs": 4,
        "edge_note": "single-lane circular edge intent",
        "grading": "roundabout_radial_crossfall",
        "drainage": "outside_gutter",
        "summary": "Creates crossing approach source sets for a compact single-lane roundabout starter.",
    },
)

DESIGN_VEHICLES = ("passenger_car", "single_unit_truck", "bus_or_small_truck")
GRADING_POLICIES = (
    "blend_primary_side",
    "flatten_intersection",
    "keep_primary_crown",
    "roundabout_radial_crossfall",
)
DRAINAGE_MODES = ("review_low_points", "outside_gutter", "central_island", "curb_gutter_inlets", "sag_low_point_inlets")
PRESET_SOURCE_MODES = ("Create From Preset", "Use Existing Alignments")


def intersection_preset_labels() -> list[str]:
    """Return user-facing labels for the preset source panel."""

    return [str(row["label"]) for row in INTERSECTION_PRESET_ROWS]


def intersection_preset_kind_from_label(label: str) -> str:
    """Resolve one preset panel label to an internal intersection kind."""

    normalized = str(label or "").strip().lower()
    for row in INTERSECTION_PRESET_ROWS:
        if normalized == str(row.get("label", "") or "").strip().lower():
            return str(row.get("kind", "") or "")
    return ""


def intersection_preset_row_from_label(label: str) -> dict[str, object]:
    """Return one preset metadata row by label."""

    normalized = str(label or "").strip().lower()
    for row in INTERSECTION_PRESET_ROWS:
        if normalized == str(row.get("label", "") or "").strip().lower():
            return dict(row)
    return dict(INTERSECTION_PRESET_ROWS[0])


def run_v1_intersection_presets_command():
    """Open the v1 Intersection task panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    panel = V1IntersectionPresetsTaskPanel(document=App.ActiveDocument)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


class V1IntersectionPresetsTaskPanel:
    """Preset-driven source starter panel for v1 intersections."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.project = _ensure_intersection_preset_project(self.document)
        self._last_created_sources: list[str] = []
        self._last_detection = None
        self._last_applied_intersection = ""
        self._last_edge_network_preview = ""
        self._alignment_choices = list_v1_alignment_choices(self.document) if self.document is not None else []
        self.form = self._build_ui()
        _route_intersection_preset_objects(self.document, project=self.project)
        self._update_capability_note()
        self._update_source_mode_controls()
        self._update_status("Select a source mode, then create or link intersection source objects.")

    def getStandardButtons(self):
        return 0

    def accept(self):
        return True

    def reject(self):
        if Gui is not None:
            try:
                Gui.Control.closeDialog()
            except Exception:
                pass
        return True

    def _build_ui(self):
        root = QtWidgets.QWidget()
        root.setWindowTitle("Parametric Road v1 - Intersection")
        layout = QtWidgets.QVBoxLayout(root)

        title = QtWidgets.QLabel("Intersection")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        intro = QtWidgets.QLabel(
            "Create editable source objects for intersection starter design. "
            "Create From Preset also prepares the Assembly / Subassembly source used by Regions and Build Sections."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QtWidgets.QFormLayout()
        self._source_mode_combo = QtWidgets.QComboBox()
        for value in PRESET_SOURCE_MODES:
            self._source_mode_combo.addItem(value, value)
        self._source_mode_combo.currentIndexChanged.connect(self._on_source_mode_changed)
        form.addRow("Source Mode:", self._source_mode_combo)

        self._preset_combo = QtWidgets.QComboBox()
        for row in INTERSECTION_PRESET_ROWS:
            self._preset_combo.addItem(str(row["label"]), str(row["kind"]))
        form.addRow("Preset:", self._preset_combo)

        self._design_vehicle_combo = QtWidgets.QComboBox()
        for value in DESIGN_VEHICLES:
            self._design_vehicle_combo.addItem(value, value)
        form.addRow("Design Vehicle:", self._design_vehicle_combo)

        self._radius_spin = QtWidgets.QDoubleSpinBox()
        self._radius_spin.setRange(1.0, 200.0)
        self._radius_spin.setDecimals(3)
        self._radius_spin.setSuffix(" m")
        self._radius_spin.setValue(12.0)
        form.addRow("Radius / Diameter:", self._radius_spin)

        self._control_length_spin = QtWidgets.QDoubleSpinBox()
        self._control_length_spin.setRange(1.0, 500.0)
        self._control_length_spin.setDecimals(3)
        self._control_length_spin.setSuffix(" m")
        self._control_length_spin.setValue(24.0)
        form.addRow("Control Length:", self._control_length_spin)

        self._grading_combo = QtWidgets.QComboBox()
        for value in GRADING_POLICIES:
            self._grading_combo.addItem(value, value)
        form.addRow("Grading Policy:", self._grading_combo)

        self._drainage_combo = QtWidgets.QComboBox()
        for value in DRAINAGE_MODES:
            self._drainage_combo.addItem(value, value)
        form.addRow("Drainage Mode:", self._drainage_combo)
        self._preset_combo.currentIndexChanged.connect(self._update_capability_note)
        layout.addLayout(form)

        self._existing_group = QtWidgets.QGroupBox("Existing Alignment Link")
        existing_layout = QtWidgets.QFormLayout(self._existing_group)
        self._primary_alignment_combo = QtWidgets.QComboBox()
        self._secondary_alignment_combo = QtWidgets.QComboBox()
        _populate_alignment_combo(self._primary_alignment_combo, self._alignment_choices)
        _populate_alignment_combo(self._secondary_alignment_combo, self._alignment_choices)
        if len(self._alignment_choices) > 1:
            self._secondary_alignment_combo.setCurrentIndex(1)
        self._primary_alignment_combo.currentIndexChanged.connect(self._update_status)
        self._secondary_alignment_combo.currentIndexChanged.connect(self._update_status)
        existing_layout.addRow("Primary Alignment:", self._primary_alignment_combo)
        existing_layout.addRow("Secondary Alignment:", self._secondary_alignment_combo)
        layout.addWidget(self._existing_group)

        self._capability_note = QtWidgets.QLabel("")
        self._capability_note.setWordWrap(True)
        layout.addWidget(self._capability_note)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setMinimumHeight(190)
        layout.addWidget(self._status)

        buttons = QtWidgets.QHBoxLayout()
        self._create_button = QtWidgets.QPushButton("Create Sources")
        self._create_button.clicked.connect(self._create_sources)
        buttons.addWidget(self._create_button)
        self._refresh_alignments_button = QtWidgets.QPushButton("Refresh Alignments")
        self._refresh_alignments_button.clicked.connect(self._refresh_alignment_choices)
        buttons.addWidget(self._refresh_alignments_button)
        self._auto_detect_button = QtWidgets.QPushButton("Auto Detect")
        self._auto_detect_button.clicked.connect(self._auto_detect_existing_alignment_intersection)
        buttons.addWidget(self._auto_detect_button)
        self._apply_existing_button = QtWidgets.QPushButton("Apply")
        self._apply_existing_button.clicked.connect(self._apply_existing_alignment_intersection)
        buttons.addWidget(self._apply_existing_button)
        self._preview_edge_button = QtWidgets.QPushButton("Preview Edge Network")
        self._preview_edge_button.clicked.connect(self._preview_edge_network)
        buttons.addWidget(self._preview_edge_button)
        self._hide_edge_button = QtWidgets.QPushButton("Hide Edge Network")
        self._hide_edge_button.clicked.connect(self._hide_edge_network)
        buttons.addWidget(self._hide_edge_button)
        self._hide_sources_button = QtWidgets.QPushButton("Hide Preset Sources")
        self._hide_sources_button.clicked.connect(self._hide_preset_sources)
        buttons.addWidget(self._hide_sources_button)
        self._show_sources_button = QtWidgets.QPushButton("Show Preset Sources")
        self._show_sources_button.clicked.connect(self._show_preset_sources)
        buttons.addWidget(self._show_sources_button)
        buttons.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        return root

    def _selected_label(self) -> str:
        return str(self._preset_combo.currentText() or "")

    def _selected_kind(self) -> str:
        data = self._preset_combo.currentData()
        return str(data or intersection_preset_kind_from_label(self._selected_label()))

    def _selected_source_mode(self) -> str:
        try:
            return str(self._source_mode_combo.currentData() or self._source_mode_combo.currentText() or "")
        except Exception:
            return PRESET_SOURCE_MODES[0]

    def _selected_primary_alignment_ref(self) -> str:
        return _combo_data_or_text(self._primary_alignment_combo)

    def _selected_secondary_alignment_ref(self) -> str:
        return _combo_data_or_text(self._secondary_alignment_combo)

    def _selected_options(self) -> dict[str, object]:
        return {
            "design_vehicle": str(self._design_vehicle_combo.currentText() or ""),
            "radius": float(self._radius_spin.value()),
            "control_length": float(self._control_length_spin.value()),
            "grading_policy": str(self._grading_combo.currentText() or ""),
            "drainage_mode": str(self._drainage_combo.currentText() or ""),
        }

    def _on_source_mode_changed(self):
        self._update_source_mode_controls()
        self._update_status()

    def _update_source_mode_controls(self):
        use_existing = self._selected_source_mode() == "Use Existing Alignments"
        try:
            self._existing_group.setVisible(use_existing)
            self._refresh_alignments_button.setVisible(use_existing)
            self._auto_detect_button.setVisible(use_existing)
            self._apply_existing_button.setVisible(use_existing)
            self._preview_edge_button.setVisible(True)
            self._hide_edge_button.setVisible(True)
            self._create_button.setVisible(not use_existing)
        except Exception:
            pass

    def _refresh_alignment_choices(self):
        self._alignment_choices = list_v1_alignment_choices(self.document) if self.document is not None else []
        _populate_alignment_combo(self._primary_alignment_combo, self._alignment_choices)
        _populate_alignment_combo(self._secondary_alignment_combo, self._alignment_choices)
        if len(self._alignment_choices) > 1:
            self._secondary_alignment_combo.setCurrentIndex(1)
        self._update_status("Alignment choices refreshed.")

    def _update_capability_note(self, *args):
        del args
        row = intersection_preset_row_from_label(self._selected_label())
        if str(row.get("kind", "")) == "roundabout":
            self._radius_spin.setValue(36.0)
            self._control_length_spin.setValue(30.0)
            self._grading_combo.setCurrentText("roundabout_radial_crossfall")
            self._drainage_combo.setCurrentText("outside_gutter")
        elif str(row.get("kind", "")) == "cross_intersection":
            self._radius_spin.setValue(10.0)
            self._control_length_spin.setValue(28.0)
            self._grading_combo.setCurrentText("blend_primary_side")
            self._drainage_combo.setCurrentText("review_low_points")
        elif str(row.get("kind", "")) == "skewed_intersection":
            self._radius_spin.setValue(11.0)
            self._control_length_spin.setValue(30.0)
            self._grading_combo.setCurrentText("blend_primary_side")
            self._drainage_combo.setCurrentText("review_low_points")
        elif str(row.get("kind", "")) == "urban_curb_gutter_intersection":
            self._radius_spin.setValue(8.0)
            self._control_length_spin.setValue(28.0)
            self._grading_combo.setCurrentText("blend_primary_side")
            self._drainage_combo.setCurrentText("curb_gutter_inlets")
        elif str(row.get("kind", "")) == "drainage_sag_intersection":
            self._radius_spin.setValue(9.0)
            self._control_length_spin.setValue(32.0)
            self._grading_combo.setCurrentText("blend_primary_side")
            self._drainage_combo.setCurrentText("sag_low_point_inlets")
        elif str(row.get("kind", "")) == "y_intersection":
            self._radius_spin.setValue(15.0)
            self._control_length_spin.setValue(26.0)
            self._grading_combo.setCurrentText("blend_primary_side")
            self._drainage_combo.setCurrentText("review_low_points")
        else:
            self._radius_spin.setValue(12.0)
            self._control_length_spin.setValue(24.0)
            self._grading_combo.setCurrentText("blend_primary_side")
            self._drainage_combo.setCurrentText("review_low_points")
        self._capability_note.setText(
            "Capability: "
            f"{row.get('summary', '')} "
            f"legs={row.get('legs', '-')}; {row.get('edge_note', '-')}; "
            f"grading={row.get('grading', '-')}; drainage={row.get('drainage', '-')}."
        )

    def _create_sources(self):
        try:
            created = create_intersection_preset_sources(
                self.document,
                preset_label=self._selected_label(),
                **self._selected_options(),
            )
            self._last_created_sources = created
            _route_intersection_preset_objects(self.document, project=_ensure_intersection_preset_project(self.document))
            _refresh_intersection_tree_view(self.document)
            self._update_status("Preset source creation complete, including Assembly / Subassembly source.")
            _show_message(
                self.form,
                "Intersection",
                "Preset source creation complete.\n\nCreated sources include Assembly / Subassembly intent.\nNext: review/apply the source model, then Build Sections.",
            )
        except Exception as exc:
            self._update_status(f"Preset source creation failed: {exc}")
            _show_message(self.form, "Intersection", f"Preset source creation failed:\n{exc}")

    def _auto_detect_existing_alignment_intersection(self):
        errors = validate_existing_alignment_selection(
            self._selected_primary_alignment_ref(),
            self._selected_secondary_alignment_ref(),
        )
        if errors:
            self._last_detection = None
            self._update_status("Auto Detect blocked by Alignment selection errors.")
            return
        primary = alignment_model_by_ref(self.document, self._selected_primary_alignment_ref())
        secondary = alignment_model_by_ref(self.document, self._selected_secondary_alignment_ref())
        if primary is None or secondary is None:
            self._last_detection = None
            self._update_status("Auto Detect failed: selected Alignment source could not be loaded.")
            return
        self._last_detection = AlignmentIntersectionDetectionService().detect(primary, secondary)
        self._update_status("Auto Detect completed.")

    def _apply_existing_alignment_intersection(self):
        try:
            obj, control_region_count = create_intersection_from_existing_alignments(
                self.document,
                preset_label=self._selected_label(),
                primary_alignment_ref=self._selected_primary_alignment_ref(),
                secondary_alignment_ref=self._selected_secondary_alignment_ref(),
                detection_result=self._last_detection,
                **self._selected_options(),
            )
            self._last_applied_intersection = f"{getattr(obj, 'Label', '') or getattr(obj, 'Name', '')} | {getattr(obj, 'IntersectionModelId', '')}"
            self._update_status("Existing Alignment intersection applied.")
            _show_message(
                self.form,
                "Intersection",
                (
                    "Intersection has been applied from existing Alignments.\n\n"
                    f"Object: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')}\n"
                    f"IntersectionModel: {getattr(obj, 'IntersectionModelId', '')}\n"
                    f"Control Regions: {control_region_count}"
                ),
            )
        except Exception as exc:
            self._last_applied_intersection = ""
            self._update_status(f"Apply failed: {exc}")
            _show_message(self.form, "Intersection", f"Intersection was not applied.\n{exc}")

    def _preview_edge_network(self):
        try:
            if self._selected_source_mode() == "Use Existing Alignments":
                model, control_region_count = build_existing_alignment_intersection_model(
                    self.document,
                    preset_label=self._selected_label(),
                    primary_alignment_ref=self._selected_primary_alignment_ref(),
                    secondary_alignment_ref=self._selected_secondary_alignment_ref(),
                    detection_result=self._last_detection,
                    **self._selected_options(),
                )
                status_prefix = "Existing Alignment"
                detection_result = self._last_detection
            else:
                model, control_region_count, detection_result = build_preset_source_intersection_model(
                    self.document,
                    preset_label=self._selected_label(),
                    **self._selected_options(),
                )
                self._last_detection = detection_result
                status_prefix = "Preset"
            obj = show_intersection_edge_network_preview(
                self.document,
                intersection_model=model,
                detection_result=detection_result,
                project=find_project(self.document),
            )
            _route_intersection_preset_objects(self.document, project=find_project(self.document))
            self._last_edge_network_preview = f"{getattr(obj, 'Label', '') or getattr(obj, 'Name', '')} | {getattr(obj, 'Name', '')} | regions={control_region_count}"
            if Gui is not None:
                try:
                    Gui.Selection.clearSelection()
                    Gui.Selection.addSelection(obj)
                except Exception:
                    pass
            self._update_status(f"{status_prefix} edge network preview shown.")
        except Exception as exc:
            self._last_edge_network_preview = ""
            self._update_status(f"Edge Network preview failed: {exc}")

    def _hide_edge_network(self):
        obj = set_intersection_edge_network_preview_visible(self.document, False)
        _route_intersection_preset_objects(self.document, project=find_project(self.document))
        if obj is None:
            self._update_status("No Edge Network preview exists.")
            return
        self._update_status("Edge Network preview hidden.")

    def _hide_preset_sources(self):
        count = _set_intersection_preset_sources_visible(self.document, visible=False)
        self._update_status(f"Preset source objects hidden: {count}.")

    def _show_preset_sources(self):
        count = _set_intersection_preset_sources_visible(self.document, visible=True)
        self._update_status(f"Preset source objects shown: {count}.")

    def _update_status(self, *args, prefix: str = ""):
        if args and not prefix and isinstance(args[0], str):
            prefix = args[0]
        row = intersection_preset_row_from_label(self._selected_label())
        source_mode = self._selected_source_mode()
        primary_ref = self._selected_primary_alignment_ref() if hasattr(self, "_primary_alignment_combo") else ""
        secondary_ref = self._selected_secondary_alignment_ref() if hasattr(self, "_secondary_alignment_combo") else ""
        alignment_errors = (
            validate_existing_alignment_selection(primary_ref, secondary_ref)
            if source_mode == "Use Existing Alignments"
            else []
        )
        intersection_ref = intersection_ref_for_kind(self._selected_kind())
        control_regions = list_intersection_control_region_choices(self.document, intersection_ref) if self.document is not None else []
        lines = []
        if prefix:
            lines.extend([prefix, ""])
        lines.extend(
            [
                f"Source Mode: {source_mode}",
                f"Preset: {self._selected_label()} ({self._selected_kind()})",
                f"Design Vehicle: {self._design_vehicle_combo.currentText()}",
                f"Radius / Diameter: {self._radius_spin.value():.3f} m",
                f"Control Length: {self._control_length_spin.value():.3f} m",
                f"Grading Policy: {self._grading_combo.currentText()}",
                f"Drainage Mode: {self._drainage_combo.currentText()}",
                f"Primary Alignment: {primary_ref or '-'}",
                f"Secondary Alignment: {secondary_ref or '-'}",
                f"Alignment Validation: {'ok' if not alignment_errors else 'error'}",
                *[f"- {error}" for error in alignment_errors],
                "",
                "Auto Detect:",
                *(_format_detection_lines(self._last_detection) or ["- Not run."]),
                "",
                f"Control Regions ({intersection_ref}):",
                *(
                    [f"- {item.get('label', '-')}" for item in control_regions]
                    if control_regions
                    else ["- No linked control Regions found."]
                ),
                "",
                "Created Sources:",
                *([f"- {line}" for line in self._last_created_sources] if self._last_created_sources else ["- Not created."]),
                "",
                "Applied IntersectionModel:",
                f"- {self._last_applied_intersection or 'Not applied.'}",
                "",
                "Edge Network Preview:",
                f"- {self._last_edge_network_preview or 'Not shown.'}",
                "",
                "Next workflow:",
                "- Build Sections: generate applied section context",
                "- Build Parametric: generate and review corridor/intersection outputs",
                "",
                "Note:",
                "- Create From Preset creates editable Alignment/Profile/Station/Region and Assembly/Subassembly sources.",
                "- Existing Alignments mode links user-created Alignment and Region sources in this panel.",
                "- Final surface-zone and roundabout geometry expansion remain planned follow-up phases.",
            ]
        )
        self._status.setPlainText("\n".join(str(line) for line in lines if line is not None))


def create_intersection_preset_sources(
    document,
    *,
    preset_label: str,
    design_vehicle: str = "",
    radius: float | None = None,
    control_length: float | None = None,
    grading_policy: str = "",
    drainage_mode: str = "",
) -> list[str]:
    """Create editable source objects for one named Intersection Preset."""

    kind = intersection_preset_kind_from_label(preset_label)
    if not kind:
        raise ValueError(f"Unsupported Intersection Preset: {preset_label}")
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document is available.")
    project = _ensure_intersection_preset_project(doc)
    created = create_starter_intersection_sources(doc, kind, project=project)
    row = intersection_preset_row_from_label(preset_label)
    created.extend(
        _create_preset_intersection_model(
            doc,
            intersection_kind=kind,
            design_vehicle=design_vehicle,
            radius=radius,
            control_length=control_length,
            grading_policy=grading_policy or str(row.get("grading", "") or ""),
            drainage_mode=drainage_mode or str(row.get("drainage", "") or ""),
            project=project,
        )
    )
    _route_intersection_preset_objects(doc, project=project)
    try:
        doc.recompute()
    except Exception:
        pass
    _refresh_intersection_tree_view(doc)
    return created


def _ensure_intersection_preset_project(document):
    """Ensure the active document has a v1 project tree before preset sources are created."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return None
    project = find_project(doc)
    if project is None:
        try:
            project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
            CorridorRoadProject(project)
            project.Label = "Parametric Road Project"
        except Exception:
            project = None
    if project is not None:
        try:
            ensure_project_tree(project, include_references=False)
        except Exception:
            pass
        try:
            ensure_project_viewprovider(project)
        except Exception:
            pass
    return project


def _refresh_intersection_tree_view(document) -> None:
    """Best-effort refresh so newly-created preset sources appear in the Tree view."""

    if document is None:
        return
    try:
        document.recompute()
    except Exception:
        pass
    try:
        if App is not None and getattr(App, "ActiveDocument", None) is not document:
            App.setActiveDocument(str(getattr(document, "Name", "") or ""))
    except Exception:
        pass
    try:
        if Gui is not None and hasattr(Gui, "updateGui"):
            Gui.updateGui()
    except Exception:
        pass


def build_existing_alignment_intersection_model(
    document,
    *,
    preset_label: str,
    primary_alignment_ref: str,
    secondary_alignment_ref: str,
    detection_result=None,
    design_vehicle: str = "",
    radius: float | None = None,
    control_length: float | None = None,
    grading_policy: str = "",
    drainage_mode: str = "",
):
    """Build an IntersectionModel contract from user-selected existing Alignments."""

    kind = intersection_preset_kind_from_label(preset_label)
    if not kind:
        raise ValueError(f"Unsupported Intersection Preset: {preset_label}")
    errors = validate_existing_alignment_selection(primary_alignment_ref, secondary_alignment_ref)
    if errors:
        raise ValueError("; ".join(errors))
    if alignment_model_by_ref(document, primary_alignment_ref) is None:
        raise ValueError(f"Primary Alignment source was not found: {primary_alignment_ref}")
    if alignment_model_by_ref(document, secondary_alignment_ref) is None:
        raise ValueError(f"Secondary Alignment source was not found: {secondary_alignment_ref}")
    control_regions = list_intersection_control_region_choices(document, intersection_ref_for_kind(kind))
    if not control_regions:
        raise ValueError("No intersection-tagged control Regions were found.")
    model = build_intersection_model_from_sources(
        intersection_kind=kind,
        source_mode="Use Existing Alignments",
        primary_alignment_ref=primary_alignment_ref,
        secondary_alignment_ref=secondary_alignment_ref,
        control_region_choices=control_regions,
        detection_result=detection_result,
        project_id=_project_id(find_project(document)),
    )
    row = intersection_preset_row_from_label(preset_label)
    _apply_preset_policy_options(
        model,
        design_vehicle=design_vehicle,
        radius=radius,
        control_length=control_length,
        grading_policy=grading_policy or str(row.get("grading", "") or ""),
        drainage_mode=drainage_mode or str(row.get("drainage", "") or ""),
    )
    _apply_preset_source_completeness_status(model, preset_label=preset_label)
    return model, len(control_regions)


def build_preset_source_intersection_model(
    document,
    *,
    preset_label: str,
    design_vehicle: str = "",
    radius: float | None = None,
    control_length: float | None = None,
    grading_policy: str = "",
    drainage_mode: str = "",
):
    """Build a preview-only IntersectionModel from previously created preset sources."""

    kind = intersection_preset_kind_from_label(preset_label)
    if not kind:
        raise ValueError(f"Unsupported Intersection Preset: {preset_label}")
    control_regions = list_intersection_control_region_choices(document, intersection_ref_for_kind(kind))
    if not control_regions:
        raise ValueError("Create Sources first; no intersection-tagged control Regions were found.")
    primary_ref, secondary_ref = _primary_secondary_refs_from_control_regions(control_regions)
    if not primary_ref or not secondary_ref:
        raise ValueError("Primary/Secondary Alignment refs could not be resolved from preset control Regions.")
    if alignment_model_by_ref(document, primary_ref) is None:
        raise ValueError(f"Primary Alignment source was not found: {primary_ref}")
    if alignment_model_by_ref(document, secondary_ref) is None:
        raise ValueError(f"Secondary Alignment source was not found: {secondary_ref}")
    detection_result = _detect_preset_alignment_intersection(
        document,
        primary_alignment_ref=primary_ref,
        secondary_alignment_ref=secondary_ref,
    )
    model = build_intersection_model_from_sources(
        intersection_kind=kind,
        source_mode="Create Starter Sources",
        primary_alignment_ref=primary_ref,
        secondary_alignment_ref=secondary_ref,
        control_region_choices=control_regions,
        detection_result=detection_result,
        project_id=_project_id(find_project(document)),
    )
    row = intersection_preset_row_from_label(preset_label)
    _apply_preset_policy_options(
        model,
        design_vehicle=design_vehicle,
        radius=radius,
        control_length=control_length,
        grading_policy=grading_policy or str(row.get("grading", "") or ""),
        drainage_mode=drainage_mode or str(row.get("drainage", "") or ""),
    )
    _apply_preset_source_completeness_status(model, preset_label=preset_label)
    return model, len(control_regions), detection_result


def create_intersection_from_existing_alignments(
    document,
    *,
    preset_label: str,
    primary_alignment_ref: str,
    secondary_alignment_ref: str,
    detection_result=None,
    design_vehicle: str = "",
    radius: float | None = None,
    control_length: float | None = None,
    grading_policy: str = "",
    drainage_mode: str = "",
):
    """Create or update an IntersectionModel object from existing Alignment selections."""

    if document is None:
        raise RuntimeError("No active document is available.")
    project = find_project(document)
    model, control_region_count = build_existing_alignment_intersection_model(
        document,
        preset_label=preset_label,
        primary_alignment_ref=primary_alignment_ref,
        secondary_alignment_ref=secondary_alignment_ref,
        detection_result=detection_result,
        design_vehicle=design_vehicle,
        radius=radius,
        control_length=control_length,
        grading_policy=grading_policy,
        drainage_mode=drainage_mode,
    )
    obj = create_or_update_v1_intersection_model_object(
        document,
        intersection_model=model,
        project=project,
        label="Intersections",
    )
    try:
        document.recompute()
    except Exception:
        pass
    return obj, control_region_count


def _apply_preset_source_completeness_status(model, *, preset_label: str) -> None:
    """Mark preset-authored source rows as explicit review-required defaults."""

    kind = intersection_preset_kind_from_label(preset_label) or str(preset_label or "").strip()
    if kind not in {"t_intersection", "cross_intersection", "skewed_intersection", "urban_curb_gutter_intersection", "drainage_sag_intersection", "y_intersection"}:
        return
    preset_ref = f"intersection-preset:{kind}:source-completeness"
    try:
        model.source_refs = _unique_text_values([*list(getattr(model, "source_refs", []) or []), preset_ref])
    except Exception:
        pass
    note = f"Preset source completeness: default/draft row requires review before final design; source_completeness_ref={preset_ref}."
    model.intersection_rows = [
        replace(
            row,
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "intersection_rows", []) or [])
    ]
    model.anchor_rows = [
        replace(
            row,
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(getattr(row, "diagnostic_rows", []) or [], "preset_anchor_review_required"),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "anchor_rows", []) or [])
    ]
    model.control_area_rows = [
        replace(
            row,
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(getattr(row, "diagnostic_rows", []) or [], "preset_control_area_review_required"),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "control_area_rows", []) or [])
    ]
    model.corner_rows = [
        replace(
            row,
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(getattr(row, "diagnostic_rows", []) or [], "preset_corner_review_required"),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "corner_rows", []) or [])
    ]
    model.edge_policy_rows = [
        replace(
            row,
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(getattr(row, "diagnostic_rows", []) or [], "preset_edge_family_review_required"),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "edge_policy_rows", []) or [])
    ]
    model.lane_connection_rows = [
        replace(
            row,
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(getattr(row, "diagnostic_rows", []) or [], "preset_lane_connection_review_required"),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "lane_connection_rows", []) or [])
    ]
    model.grading_policy_rows = [
        replace(
            row,
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(getattr(row, "diagnostic_rows", []) or [], "preset_grading_policy_review_required"),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "grading_policy_rows", []) or [])
    ]
    model.drainage_policy_rows = [
        replace(
            row,
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(getattr(row, "diagnostic_rows", []) or [], "preset_drainage_policy_review_required"),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "drainage_policy_rows", []) or [])
    ]
    if kind == "y_intersection":
        branch_ref = f"intersection-preset:{kind}:branch-review"
        try:
            model.source_refs = _unique_text_values([*list(getattr(model, "source_refs", []) or []), branch_ref])
        except Exception:
            pass
        branch_note = (
            "Y preset branch defaults require approach angle and diverge/merge movement review; "
            f"branch_review_ref={branch_ref}."
        )
        model.intersection_rows = [
            replace(
                row,
                notes=_append_note(str(getattr(row, "notes", "") or ""), branch_note),
            )
            for row in list(getattr(model, "intersection_rows", []) or [])
        ]
        model.corner_rows = [
            replace(
                row,
                diagnostic_rows=_append_diagnostics(
                    getattr(row, "diagnostic_rows", []) or [],
                    "preset_y_branch_geometry_review_required",
                ),
                notes=_append_note(str(getattr(row, "notes", "") or ""), branch_note),
            )
            for row in list(getattr(model, "corner_rows", []) or [])
        ]
        model.lane_connection_rows = [
            replace(
                row,
                diagnostic_rows=_append_diagnostics(
                    getattr(row, "diagnostic_rows", []) or [],
                    "preset_y_diverge_merge_review_required",
                ),
                notes=_append_note(str(getattr(row, "notes", "") or ""), branch_note),
            )
            for row in list(getattr(model, "lane_connection_rows", []) or [])
        ]
    if kind == "skewed_intersection":
        skew_ref = f"intersection-preset:{kind}:skew-review"
        try:
            model.source_refs = _unique_text_values([*list(getattr(model, "source_refs", []) or []), skew_ref])
        except Exception:
            pass
        skew_note = (
            "Skewed preset defaults require skew angle, corner radius, and grading transition review; "
            f"skew_review_ref={skew_ref}."
        )
        model.intersection_rows = [
            replace(
                row,
                notes=_append_note(str(getattr(row, "notes", "") or ""), skew_note),
            )
            for row in list(getattr(model, "intersection_rows", []) or [])
        ]
        model.corner_rows = [
            replace(
                row,
                diagnostic_rows=_append_diagnostics(
                    getattr(row, "diagnostic_rows", []) or [],
                    "preset_skew_corner_geometry_review_required",
                ),
                notes=_append_note(str(getattr(row, "notes", "") or ""), skew_note),
            )
            for row in list(getattr(model, "corner_rows", []) or [])
        ]
        model.edge_policy_rows = [
            replace(
                row,
                diagnostic_rows=_append_diagnostics(
                    getattr(row, "diagnostic_rows", []) or [],
                    "preset_skew_edge_family_review_required",
                ),
                notes=_append_note(str(getattr(row, "notes", "") or ""), skew_note),
            )
            for row in list(getattr(model, "edge_policy_rows", []) or [])
        ]
    if kind == "urban_curb_gutter_intersection":
        urban_ref = f"intersection-preset:{kind}:urban-curb-gutter-review"
        try:
            model.source_refs = _unique_text_values([*list(getattr(model, "source_refs", []) or []), urban_ref])
        except Exception:
            pass
        _apply_urban_curb_gutter_source_rows(model, urban_ref=urban_ref)
    if kind == "drainage_sag_intersection":
        sag_ref = f"intersection-preset:{kind}:sag-drainage-review"
        try:
            model.source_refs = _unique_text_values([*list(getattr(model, "source_refs", []) or []), sag_ref])
        except Exception:
            pass
        _apply_drainage_sag_source_rows(model, sag_ref=sag_ref)


def _apply_drainage_sag_source_rows(model, *, sag_ref: str = "") -> None:
    """Add sag low-point, inlet, and flow-route review defaults."""

    intersection_rows = list(getattr(model, "intersection_rows", []) or [])
    if not intersection_rows:
        return
    intersection_id = str(getattr(intersection_rows[0], "intersection_id", "") or "intersection:sag")
    note = (
        "Drainage-sensitive sag preset defaults require inlet, flow-route, hydraulic sizing, and outlet review; "
        f"sag_review_ref={sag_ref}."
    )
    model.intersection_rows = [
        replace(
            row,
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in intersection_rows
    ]
    sag_low_point_refs = [
        f"drainage:sag-low-point:{intersection_id}:primary",
        f"drainage:sag-low-point:{intersection_id}:secondary",
    ]
    inlet_refs = [
        f"drainage:sag-inlet-candidate:{intersection_id}:left",
        f"drainage:sag-inlet-candidate:{intersection_id}:right",
    ]
    flow_refs = [f"flow-route:sag-intersection:{intersection_id}:outlet-review"]
    model.grading_policy_rows = [
        replace(
            row,
            low_point_strategy="sag_low_point_review",
            diagnostic_rows=_append_diagnostics(
                getattr(row, "diagnostic_rows", []) or [],
                "preset_sag_profile_review_required",
                "preset_sag_low_point_review_required",
            ),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "grading_policy_rows", []) or [])
    ]
    model.drainage_policy_rows = [
        replace(
            row,
            capture_mode="sag_low_point_inlets",
            inlet_spacing=35.0,
            drainage_element_refs=_unique_text_values([*list(getattr(row, "drainage_element_refs", []) or []), *inlet_refs]),
            flow_route_refs=_unique_text_values([*list(getattr(row, "flow_route_refs", []) or []), *flow_refs]),
            inlet_candidate_refs=_unique_text_values([*list(getattr(row, "inlet_candidate_refs", []) or []), *inlet_refs]),
            low_point_refs=_unique_text_values([*list(getattr(row, "low_point_refs", []) or []), *sag_low_point_refs]),
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(
                getattr(row, "diagnostic_rows", []) or [],
                "preset_sag_inlet_review_required",
                "preset_sag_flow_route_review_required",
                "preset_sag_hydraulic_sizing_required",
            ),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "drainage_policy_rows", []) or [])
    ]


def _apply_urban_curb_gutter_source_rows(model, *, urban_ref: str = "") -> None:
    """Add source-visible curb, gutter, sidewalk, and inlet handoff defaults."""

    intersection_rows = list(getattr(model, "intersection_rows", []) or [])
    if not intersection_rows:
        return
    intersection_id = str(getattr(intersection_rows[0], "intersection_id", "") or "intersection:urban")
    note = (
        "Urban curb/gutter preset defaults require curb return, sidewalk, inlet, and low-point review; "
        f"urban_review_ref={urban_ref}."
    )
    model.intersection_rows = [
        replace(
            row,
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in intersection_rows
    ]
    intersection_rows = list(getattr(model, "intersection_rows", []) or [])
    existing_policy_ids = {str(getattr(row, "policy_id", "") or "") for row in list(getattr(model, "edge_policy_rows", []) or [])}
    extra_edges = []
    for index, leg in enumerate(list(getattr(intersection_rows[0], "leg_rows", []) or []), start=1):
        leg_ref = str(getattr(leg, "leg_id", "") or "")
        for role, offset, subassembly_kind, diagnostic in (
            ("curb_edge", 3.8, "curb", "preset_urban_curb_review_required"),
            ("gutter_edge", 4.2, "gutter", "preset_urban_gutter_review_required"),
            ("sidewalk_edge", 6.0, "sidewalk", "preset_urban_sidewalk_review_required"),
        ):
            policy_id = f"edge-policy:{intersection_id}:leg:{index:02d}:{role.replace('_edge', '')}"
            if policy_id in existing_policy_ids:
                continue
            existing_policy_ids.add(policy_id)
            extra_edges.append(
                IntersectionEdgePolicyRow(
                    policy_id=policy_id,
                    intersection_id=intersection_id,
                    leg_ref=leg_ref,
                    edge_role=role,
                    side="both",
                    offset_rule="urban_curb_gutter_offset",
                    offset_value=offset,
                    elevation_rule="from_grading_policy",
                    source_policy_ref=str(getattr(leg, "arm_policy_ref", "") or ""),
                    edge_family_intent=subassembly_kind,
                    source_method="urban_preset_default",
                    approval_status="draft",
                    subassembly_kind=subassembly_kind,
                    diagnostic_rows=[
                        "edge_family_subassembly_defaulted",
                        "edge_family_approval_pending",
                        diagnostic,
                    ],
                    notes=note,
                )
            )
    model.edge_policy_rows = [*list(getattr(model, "edge_policy_rows", []) or []), *extra_edges]
    gutter_refs = [
        str(getattr(row, "policy_id", "") or "")
        for row in list(getattr(model, "edge_policy_rows", []) or [])
        if str(getattr(row, "edge_role", "") or "") == "gutter_edge"
    ]
    inlet_refs = [f"drainage:urban-inlet-candidate:{index:02d}" for index in range(1, min(len(gutter_refs), 4) + 1)]
    low_point_refs = [f"drainage:urban-low-point:{index:02d}" for index in range(1, min(len(gutter_refs), 4) + 1)]
    model.drainage_policy_rows = [
        replace(
            row,
            capture_mode="curb_gutter_inlets",
            inlet_spacing=45.0,
            gutter_edge_refs=_unique_text_values([*list(getattr(row, "gutter_edge_refs", []) or []), *gutter_refs]),
            inlet_candidate_refs=_unique_text_values([*list(getattr(row, "inlet_candidate_refs", []) or []), *inlet_refs]),
            low_point_refs=_unique_text_values([*list(getattr(row, "low_point_refs", []) or []), *low_point_refs]),
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(
                getattr(row, "diagnostic_rows", []) or [],
                "preset_urban_inlet_review_required",
                "preset_urban_low_point_review_required",
            ),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "drainage_policy_rows", []) or [])
    ]


def _append_diagnostics(values, *diagnostics: str) -> list[str]:
    return _unique_text_values([*[str(value) for value in list(values or [])], *diagnostics])


def _append_note(existing: str, addition: str) -> str:
    existing_text = str(existing or "").strip()
    addition_text = str(addition or "").strip()
    if not existing_text:
        return addition_text
    if not addition_text or addition_text in existing_text:
        return existing_text
    return f"{existing_text} {addition_text}"


def _unique_text_values(values) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _create_preset_intersection_model(
    document,
    *,
    intersection_kind: str,
    design_vehicle: str = "",
    radius: float | None = None,
    control_length: float | None = None,
    grading_policy: str = "",
    drainage_mode: str = "",
    project=None,
) -> list[str]:
    """Create an IntersectionModel object from the newly-created preset control Regions."""

    control_regions = list_intersection_control_region_choices(
        document,
        intersection_ref_for_kind(intersection_kind),
    )
    if not control_regions:
        return ["IntersectionModel: not created | no intersection-tagged control Regions were found"]
    primary_ref, secondary_ref = _primary_secondary_refs_from_control_regions(control_regions)
    if not primary_ref or not secondary_ref:
        return ["IntersectionModel: not created | primary/secondary Alignment refs could not be resolved"]
    detection_result = _detect_preset_alignment_intersection(
        document,
        primary_alignment_ref=primary_ref,
        secondary_alignment_ref=secondary_ref,
    )
    model = build_intersection_model_from_sources(
        intersection_kind=intersection_kind,
        source_mode="Create Starter Sources",
        primary_alignment_ref=primary_ref,
        secondary_alignment_ref=secondary_ref,
        control_region_choices=control_regions,
        detection_result=detection_result,
        project_id=_project_id(project),
    )
    _apply_preset_policy_options(
        model,
        design_vehicle=design_vehicle,
        radius=radius,
        control_length=control_length,
        grading_policy=grading_policy,
        drainage_mode=drainage_mode,
    )
    _apply_preset_source_completeness_status(model, preset_label=intersection_kind)
    obj = create_or_update_v1_intersection_model_object(
        document,
        intersection_model=model,
        project=project,
        label="Intersections",
    )
    details = [
        f"IntersectionModel: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')} | {getattr(obj, 'IntersectionModelId', '')}",
        f"IntersectionModel refs: primary={primary_ref}; secondary={secondary_ref}; control_regions={len(control_regions)}",
        "Source completeness: preset default/draft rows require review before final design.",
    ]
    if detection_result is not None:
        details.append(
            "IntersectionModel detect: "
            f"{str(getattr(detection_result, 'status', '') or '-')} | "
            f"primary STA {float(getattr(detection_result, 'primary_station', 0.0) or 0.0):.3f}; "
            f"secondary STA {float(getattr(detection_result, 'secondary_station', 0.0) or 0.0):.3f}"
        )
    details.extend(
        _create_preset_superelevation_source(
            document,
            intersection_kind=intersection_kind,
            primary_alignment_ref=primary_ref,
            secondary_alignment_ref=secondary_ref,
            control_region_choices=control_regions,
            grading_policy=grading_policy,
            project=project,
        )
    )
    details.extend(
        _create_preset_drainage_source(
            document,
            intersection_kind=intersection_kind,
            primary_alignment_ref=primary_ref,
            secondary_alignment_ref=secondary_ref,
            control_region_choices=control_regions,
            drainage_mode=drainage_mode,
            project=project,
        )
    )
    return details


def _apply_preset_policy_options(
    model,
    *,
    design_vehicle: str = "",
    radius: float | None = None,
    control_length: float | None = None,
    grading_policy: str = "",
    drainage_mode: str = "",
) -> None:
    """Apply user-visible preset policy options to the created source model."""

    vehicle = str(design_vehicle or "").strip()
    if vehicle:
        model.arm_policy_rows = [
            replace(
                row,
                design_vehicle_ref=vehicle,
                notes=(
                    str(getattr(row, "notes", "") or "").strip()
                    + f" Preset design vehicle option: {vehicle}."
                ).strip(),
            )
            for row in list(getattr(model, "arm_policy_rows", []) or [])
        ]
    radius_value = _positive_float_or_none(radius)
    if radius_value is not None:
        model.curb_return_policy_rows = [
            replace(
                row,
                radius=radius_value,
                notes=(
                    str(getattr(row, "notes", "") or "").strip()
                    + f" Preset radius option: {radius_value:.3f}m."
                ).strip(),
            )
            for row in list(getattr(model, "curb_return_policy_rows", []) or [])
        ]
    control_length_value = _positive_float_or_none(control_length)
    if control_length_value is not None:
        _apply_control_length_to_model(model, control_length_value)
    grading = str(grading_policy or "").strip()
    if grading:
        model.grading_policy_rows = [
            replace(
                row,
                mode=grading,
                crown_behavior=_grading_crown_behavior(grading),
                tie_in_rule=_grading_tie_in_rule(grading),
                crossfall_transition=_grading_crossfall_transition(grading),
                notes=(
                    str(getattr(row, "notes", "") or "").strip()
                    + f" Preset grading policy option: {grading}."
                ).strip(),
            )
            for row in list(getattr(model, "grading_policy_rows", []) or [])
        ]
    drainage = str(drainage_mode or "").strip()
    if drainage:
        model.drainage_policy_rows = [
            replace(
                row,
                capture_mode=drainage,
                notes=(
                    str(getattr(row, "notes", "") or "").strip()
                    + f" Preset drainage mode option: {drainage}."
                ).strip(),
            )
            for row in list(getattr(model, "drainage_policy_rows", []) or [])
        ]


def _grading_crown_behavior(mode: str) -> str:
    text = str(mode or "").strip()
    if text == "keep_primary_crown":
        return "preserve_primary_crown"
    if text == "blend_primary_side":
        return "blend_primary_side_crowns"
    if text == "roundabout_radial_crossfall":
        return "radial_crown"
    if text == "use_normal_superelevation":
        return "normal_superelevation"
    return "flatten"


def _grading_tie_in_rule(mode: str) -> str:
    text = str(mode or "").strip()
    if text == "keep_primary_crown":
        return "tie_to_primary_profile"
    if text == "use_normal_superelevation":
        return "normal_section_transition"
    return "blend_to_leg_profiles"


def _grading_crossfall_transition(mode: str) -> str:
    text = str(mode or "").strip()
    if text == "use_normal_superelevation":
        return "from_superelevation"
    if text == "roundabout_radial_crossfall":
        return "radial"
    return "linear"


def _positive_float_or_none(value) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if number <= 0.0:
        return None
    return number


def _apply_control_length_to_model(model, control_length: float) -> None:
    """Constrain control-area station ranges around each alignment's intersection station."""

    half = max(float(control_length or 0.0), 0.0) * 0.5
    if half <= 0.0:
        return
    centers = _intersection_station_centers(model)
    model.control_area_rows = [
        replace(
            row,
            station_ranges=_control_length_ranges_for_area(row, centers, half),
            influence_ranges=_control_length_ranges_for_area(row, centers, half * 1.25),
            notes=(
                str(getattr(row, "notes", "") or "").strip()
                + f" Preset control length option: {control_length:.3f}m."
            ).strip(),
        )
        for row in list(getattr(model, "control_area_rows", []) or [])
    ]
    model.intersection_rows = [
        replace(
            row,
            leg_rows=[
                replace(leg, **_control_length_leg_span(leg, centers, half))
                for leg in list(getattr(row, "leg_rows", []) or [])
            ],
            notes=(
                str(getattr(row, "notes", "") or "").strip()
                + f" Preset control length option: {control_length:.3f}m."
            ).strip(),
        )
        for row in list(getattr(model, "intersection_rows", []) or [])
    ]


def _intersection_station_centers(model) -> dict[str, float]:
    output: dict[str, float] = {}
    for row in list(getattr(model, "intersection_rows", []) or []):
        primary = str(getattr(row, "primary_alignment_ref", "") or "").strip()
        if primary:
            output[primary] = float(getattr(row, "primary_station", 0.0) or 0.0)
        for alignment_ref, station in dict(getattr(row, "secondary_station_refs", {}) or {}).items():
            key = str(alignment_ref or "").strip()
            if key:
                output[key] = float(station or 0.0)
    return output


def _station_center_for_alignment(centers: dict[str, float], alignment_ref: str, fallback) -> float:
    key = str(alignment_ref or "").strip()
    if key in centers:
        return float(centers[key])
    try:
        return float(fallback or 0.0)
    except Exception:
        return 0.0


def _control_length_ranges_for_area(row, centers: dict[str, float], half_length: float) -> list[tuple[float, float]]:
    center = _station_center_for_alignment(centers, str(getattr(row, "alignment_ref", "") or ""), 0.0)
    start = center - float(half_length)
    end = center + float(half_length)
    return [_clamp_station_span(start, end, list(getattr(row, "station_ranges", []) or []))]


def _control_length_leg_span(leg, centers: dict[str, float], half_length: float) -> dict[str, float]:
    center = _station_center_for_alignment(
        centers,
        str(getattr(leg, "alignment_ref", "") or ""),
        _midpoint(
            getattr(leg, "approach_station_start", 0.0),
            getattr(leg, "approach_station_end", 0.0),
        ),
    )
    start = center - float(half_length)
    end = center + float(half_length)
    clamped_start, clamped_end = _clamp_station_span(
        start,
        end,
        [(getattr(leg, "approach_station_start", 0.0), getattr(leg, "approach_station_end", 0.0))],
    )
    return {
        "approach_station_start": clamped_start,
        "approach_station_end": clamped_end,
    }


def _clamp_station_span(start: float, end: float, bounds: list[tuple[object, object]]) -> tuple[float, float]:
    proposed_start = min(float(start), float(end))
    proposed_end = max(float(start), float(end))
    valid_bounds = []
    for bound_start, bound_end in list(bounds or []):
        try:
            low = min(float(bound_start), float(bound_end))
            high = max(float(bound_start), float(bound_end))
        except Exception:
            continue
        if high > low:
            valid_bounds.append((low, high))
    if not valid_bounds:
        return proposed_start, proposed_end
    low = min(item[0] for item in valid_bounds)
    high = max(item[1] for item in valid_bounds)
    clamped_start = max(low, proposed_start)
    clamped_end = min(high, proposed_end)
    if clamped_end <= clamped_start:
        return proposed_start, proposed_end
    return clamped_start, clamped_end


def _midpoint(start, end) -> float:
    try:
        return (float(start) + float(end)) * 0.5
    except Exception:
        return 0.0


def _create_preset_superelevation_source(
    document,
    *,
    intersection_kind: str,
    primary_alignment_ref: str,
    secondary_alignment_ref: str,
    control_region_choices: list[dict[str, object]],
    grading_policy: str = "",
    project=None,
) -> list[str]:
    """Store a preset-owned Superelevation handoff source without inventing crossfall rows."""

    model = SuperelevationModel(
        schema_version=1,
        project_id=_project_id(project),
        label="Intersection Preset Superelevation",
        superelevation_id=f"superelevation:intersection-preset-{_safe_id(intersection_kind)}",
        alignment_id=str(primary_alignment_ref or ""),
        profile_id="",
        superelevation_kind="intersection_superelevation_handoff",
        control_rows=[],
        transition_rows=[],
        constraint_rows=[
            SuperelevationConstraint(
                constraint_id=f"constraint:intersection:{_safe_id(intersection_kind)}:grading-override",
                kind="intersection_grading_override",
                value=str(grading_policy or "intersection_override"),
                unit="policy",
                hard_or_soft="soft",
            ),
            SuperelevationConstraint(
                constraint_id=f"constraint:intersection:{_safe_id(intersection_kind)}:auto-calculate",
                kind="requires_auto_calculate_review",
                value="true",
                unit="boolean",
                hard_or_soft="soft",
            ),
        ],
        source_refs=[
            str(primary_alignment_ref or ""),
            str(secondary_alignment_ref or ""),
            *[str(row.get("control_region_ref", "") or "") for row in control_region_choices],
        ],
        diagnostic_rows=[
            "info:intersection_preset_superelevation_handoff: use Superelevation Auto Calculate before final Build Parametric review."
        ],
    )
    obj = create_or_update_v1_superelevation_source_object(
        document=document,
        project=project,
        superelevation_model=model,
        object_name="V1IntersectionPresetSuperelevation",
        label="Intersection Preset Superelevation",
    )
    return [
        f"Superelevation: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')} | {getattr(obj, 'SuperelevationId', '')}",
        "Superelevation rows: controls=0; transitions=0; constraints=2",
    ]


def _create_preset_drainage_source(
    document,
    *,
    intersection_kind: str,
    primary_alignment_ref: str,
    secondary_alignment_ref: str,
    control_region_choices: list[dict[str, object]],
    drainage_mode: str = "",
    project=None,
) -> list[str]:
    """Store a preset-owned Drainage low-point handoff source."""

    intersection_ref = intersection_ref_for_kind(intersection_kind)
    capture_mode = str(drainage_mode or "review_low_points")
    low_point_id = f"drainage:intersection-low-point-{_safe_id(intersection_kind)}"
    outlet_hint_id = f"drainage:intersection-outlet-hint-{_safe_id(intersection_kind)}"
    policy_id = f"drainage-policy:intersection-low-point-{_safe_id(intersection_kind)}"
    start, end = _control_region_station_range(control_region_choices)
    element_rows = [
        DrainageElementRow(
            drainage_element_id=low_point_id,
            element_kind="inlet_reference",
            alignment_ref=str(primary_alignment_ref or ""),
            intersection_ref=intersection_ref,
            side="both",
            station_start=start,
            station_end=end,
            policy_set_ref=policy_id,
        ),
        DrainageElementRow(
            drainage_element_id=outlet_hint_id,
            element_kind="outfall_reference",
            alignment_ref=str(secondary_alignment_ref or primary_alignment_ref or ""),
            intersection_ref=intersection_ref,
            side="outside",
            station_start=start,
            station_end=end,
            policy_set_ref=policy_id,
        ),
    ]
    if str(intersection_kind or "") == "urban_curb_gutter_intersection":
        for index, side in enumerate(("left", "right", "upstream", "downstream"), start=1):
            element_rows.append(
                DrainageElementRow(
                    drainage_element_id=f"drainage:urban-inlet-candidate:{index:02d}",
                    element_kind="inlet_candidate",
                    alignment_ref=str(primary_alignment_ref or ""),
                    intersection_ref=intersection_ref,
                    side=side,
                    station_start=start,
                    station_end=end,
                    policy_set_ref=policy_id,
                )
            )
    if str(intersection_kind or "") == "drainage_sag_intersection":
        for index, side in enumerate(("primary", "secondary"), start=1):
            element_rows.append(
                DrainageElementRow(
                    drainage_element_id=f"drainage:sag-low-point:{index:02d}",
                    element_kind="sag_low_point",
                    alignment_ref=str(primary_alignment_ref if index == 1 else secondary_alignment_ref or primary_alignment_ref),
                    intersection_ref=intersection_ref,
                    side=side,
                    station_start=start,
                    station_end=end,
                    policy_set_ref=policy_id,
                )
            )
        for index, side in enumerate(("left", "right"), start=1):
            element_rows.append(
                DrainageElementRow(
                    drainage_element_id=f"drainage:sag-inlet-candidate:{index:02d}",
                    element_kind="inlet_candidate",
                    alignment_ref=str(primary_alignment_ref or ""),
                    intersection_ref=intersection_ref,
                    side=side,
                    station_start=start,
                    station_end=end,
                    policy_set_ref=policy_id,
                )
            )
    model = DrainageModel(
        schema_version=1,
        project_id=_project_id(project),
        label="Intersection Preset Drainage",
        drainage_model_id=f"drainage:intersection-preset-{_safe_id(intersection_kind)}",
        element_rows=element_rows,
        policy_rows=[
            DrainagePolicySet(
                policy_set_id=policy_id,
                flow_intent="edge_runoff_capture",
                min_grade_rule="review",
                low_point_rule=capture_mode,
                collection_rule="intersection_control_area",
                discharge_rule="requires_drainage_design",
                earthwork_priority="preserve_intersection_surface",
            )
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id=f"flow-route:intersection-{_safe_id(intersection_kind)}-01",
                from_element_ref=low_point_id,
                to_element_ref=outlet_hint_id,
                outlet_ref=outlet_hint_id,
                direction="review",
                risk_level="critical" if str(intersection_kind or "") == "drainage_sag_intersection" else "high",
                notes=(
                    "Sag preset handoff only; replace inlet/outlet hints with hydraulic sizing and real Structures."
                    if str(intersection_kind or "") == "drainage_sag_intersection"
                    else "Preset handoff only; replace with real inlet/outfall Structures during drainage design."
                ),
            )
        ],
        source_refs=[
            intersection_ref,
            str(primary_alignment_ref or ""),
            str(secondary_alignment_ref or ""),
            *[str(row.get("control_region_ref", "") or "") for row in control_region_choices],
        ],
    )
    obj = create_or_update_v1_drainage_model_object(
        document=document,
        project=project,
        drainage_model=model,
        object_name="V1IntersectionPresetDrainage",
        label="Intersection Preset Drainage",
    )
    return [
        f"Drainage: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')} | {getattr(obj, 'DrainageModelId', '')}",
        f"Drainage rows: elements={len(element_rows)}; policies=1; flow_routes=1",
    ]


def _primary_secondary_refs_from_control_regions(control_regions: list[dict[str, object]]) -> tuple[str, str]:
    primary = ""
    secondary = ""
    refs: list[str] = []
    for row in list(control_regions or []):
        ref = str(row.get("alignment_ref", "") or "").strip()
        if not ref or ref in refs:
            continue
        refs.append(ref)
        text = " ".join(
            [
                str(row.get("region_model_ref", "") or ""),
                str(row.get("region_id", "") or ""),
                ref,
            ]
        ).lower()
        if not primary and "primary" in text:
            primary = ref
        elif not secondary and ("secondary" in text or "side" in text or "branch" in text):
            secondary = ref
    if not primary and refs:
        primary = refs[0]
    if not secondary:
        secondary = next((ref for ref in refs if ref != primary), "")
    return primary, secondary


def _detect_preset_alignment_intersection(document, *, primary_alignment_ref: str, secondary_alignment_ref: str):
    primary = alignment_model_by_ref(document, primary_alignment_ref)
    secondary = alignment_model_by_ref(document, secondary_alignment_ref)
    if primary is None or secondary is None:
        return None
    try:
        return AlignmentIntersectionDetectionService().detect(primary, secondary)
    except Exception:
        return None


def _route_intersection_preset_objects(document, *, project=None) -> None:
    """Route preset-created intersection source objects into the Intersections tree folder."""

    if document is None:
        return
    if project is None:
        project = find_project(document)
    if project is None:
        return
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree
    except Exception:
        return
    for obj in list(getattr(document, "Objects", []) or []):
        if not _is_intersection_preset_tree_object(obj):
            continue
        try:
            route_to_v1_tree(project, obj)
        except Exception:
            pass


def _set_intersection_preset_sources_visible(document, *, visible: bool) -> int:
    """Set preset-created source/review object visibility without relying on Tree folder propagation."""

    if document is None:
        return 0
    count = 0
    for obj in list(getattr(document, "Objects", []) or []):
        if not _is_intersection_preset_display_object(obj):
            continue
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            continue
        try:
            vobj.Visibility = bool(visible)
            count += 1
        except Exception:
            pass
    try:
        if Gui is not None and hasattr(Gui, "updateGui"):
            Gui.updateGui()
    except Exception:
        pass
    return count


def _is_intersection_preset_display_object(obj) -> bool:
    if _is_intersection_preset_tree_object(obj):
        return True
    record_kind = str(getattr(obj, "CRRecordKind", "") or "")
    if record_kind == "v1_centerline3d_review":
        alignment_id = str(getattr(obj, "AlignmentId", "") or "")
        alignment_ids = [str(value or "") for value in list(getattr(obj, "AlignmentIds", []) or [])]
        return any("alignment:intersection" in value for value in [alignment_id, *alignment_ids])
    return False


def _is_intersection_preset_tree_object(obj) -> bool:
    if obj is None:
        return False
    label = str(getattr(obj, "Label", "") or "")
    record_kind = str(getattr(obj, "CRRecordKind", "") or "")
    if record_kind in {
        "v1_intersection_model",
        "v1_intersection_review_overlay",
        "v1_intersection_edge_network_preview",
    }:
        return True
    if str(getattr(obj, "SuperelevationKind", "") or "") == "intersection_superelevation_handoff":
        return True
    if str(getattr(obj, "SuperelevationId", "") or "").startswith("superelevation:intersection-preset-"):
        return True
    if str(getattr(obj, "DrainageModelId", "") or "").startswith("drainage:intersection-preset-"):
        return True
    return label.startswith("Intersection ") and (
        label.endswith(" FG Profile")
        or label.endswith(" Stations")
        or label.endswith(" Regions")
        or label in {"Intersection Main Road", "Intersection Side Road"}
    )


def _control_region_station_range(control_regions: list[dict[str, object]]) -> tuple[float, float]:
    starts = [float(row.get("station_start", 0.0) or 0.0) for row in list(control_regions or [])]
    ends = [float(row.get("station_end", 0.0) or 0.0) for row in list(control_regions or [])]
    values = starts + ends
    if not values:
        return 0.0, 0.0
    return min(values), max(values)


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in str(value or "preset").lower()).strip("-") or "preset"


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _populate_alignment_combo(combo, choices: list[tuple[str, str]]) -> None:
    combo.clear()
    combo.addItem("", "")
    for alignment_id, label in list(choices or []):
        combo.addItem(f"{label} | {alignment_id}", alignment_id)


def _combo_data_or_text(combo) -> str:
    try:
        data = combo.currentData()
        if data:
            return str(data)
    except Exception:
        pass
    text = str(combo.currentText() or "").strip()
    if "|" in text:
        text = text.rsplit("|", 1)[-1].strip()
    return text


def _format_detection_lines(result) -> list[str]:
    if result is None:
        return []
    return [
        f"- Status: {getattr(result, 'status', '-')}",
        f"- XY: {float(getattr(result, 'x', 0.0) or 0.0):.3f}, {float(getattr(result, 'y', 0.0) or 0.0):.3f}",
        f"- Primary STA: {float(getattr(result, 'primary_station', 0.0) or 0.0):.3f}",
        f"- Secondary STA: {float(getattr(result, 'secondary_station', 0.0) or 0.0):.3f}",
        f"- Distance: {float(getattr(result, 'distance', 0.0) or 0.0):.3f}",
        f"- Notes: {getattr(result, 'notes', '') or '-'}",
    ]


class CmdV1IntersectionPresets:
    """Open the v1 Intersection source starter panel."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("intersections.svg"),
            "MenuText": "Intersection",
            "ToolTip": "Create or link v1 intersection source contracts from presets or existing Alignments",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_intersection_presets_command()


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand(INTERSECTION_PRESETS_COMMAND_ID, CmdV1IntersectionPresets())

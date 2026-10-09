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
    validate_existing_alignment_selection,
)
from ..objects.obj_drainage import create_or_update_v1_drainage_model_object
from ..commands.cmd_intersection_editor import resolve_intersection_review_leg_refs
from ..services.editing import (
    build_control_region_overlay,
    intersection_preset_default_rows,
    adopt_edge_families_from_subassembly,
    apply_intersection_review,
    intersection_review_rows,
    intersection_review_summary,
)
from ..objects.obj_intersection import (
    create_or_update_v1_intersection_model_object,
    find_v1_intersection_model,
    store_intersection_spec,
    stored_intersection_spec,
    to_intersection_model,
)
from ..objects.obj_alignment import to_alignment_model
from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..services.builders.intersection_kernel_context_service import spec_from_intersection_model, spec_kind_for_model_kind
from ..services.builders.intersection_kernel_surface_service import intersection_geometry_from_models
from ..services.editing.intersection_spec_editing_service import (
    SPEC_ANCHOR_METHODS,
    SPEC_CIRCULATIONS,
    SPEC_GRADING_MODES,
    IntersectionSpecForm,
    LegFormRow,
    form_from_spec,
    leg_rows_for_result,
    spec_check_lines,
    spec_from_form,
)
from ..models.source.intersection_spec import INTERSECTION_SPEC_KINDS
from ..objects.obj_region import create_or_update_v1_region_model_object, to_region_model
from ..objects.obj_superelevation import create_or_update_v1_superelevation_source_object, to_superelevation_model
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


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
        self._alignment_choices = list_v1_alignment_choices(self.document) if self.document is not None else []
        self.form = self._build_ui()
        _route_intersection_preset_objects(self.document, project=self.project)
        self._select_preset_of_existing_intersection()
        self._update_capability_note()
        self._update_source_mode_controls()
        self._update_status("Select a source mode, then create or link intersection source objects.")
        # a document that already has an Intersection opens with its spec in the Parametric Spec
        # group; reading it writes nothing
        if find_v1_intersection_model(self.document) is not None:
            self._load_spec(report=False)

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

        layout.addWidget(self._build_spec_group())

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setMinimumHeight(190)
        layout.addWidget(self._status)

        review_label = QtWidgets.QLabel("Source review (legs, anchors, control areas, policies):")
        layout.addWidget(review_label)
        self._review_table = QtWidgets.QTableWidget(0, 5)
        self._review_table.setHorizontalHeaderLabels(["Row", "Id", "Approval", "Missing", "Note"])
        self._review_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._review_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._review_table.setMinimumHeight(150)
        layout.addWidget(self._review_table)
        self._review_summary = QtWidgets.QLabel("")
        layout.addWidget(self._review_summary)

        review_buttons = QtWidgets.QHBoxLayout()
        self._refresh_review_button = QtWidgets.QPushButton("Refresh Review")
        self._refresh_review_button.clicked.connect(self._refresh_review_table)
        review_buttons.addWidget(self._refresh_review_button)
        self._accept_review_button = QtWidgets.QPushButton("Accept Reviewed Rows")
        self._accept_review_button.clicked.connect(self._accept_reviewed_rows)
        review_buttons.addWidget(self._accept_review_button)
        self._adopt_edge_families_button = QtWidgets.QPushButton("Adopt Edge Families From Subassembly")
        self._adopt_edge_families_button.setToolTip(
            "Marks the preset's edge policies as derived from the starter Assembly. "
            "Do this only after reviewing that Assembly; it is not part of Accept Reviewed Rows."
        )
        self._adopt_edge_families_button.clicked.connect(self._adopt_edge_families)
        review_buttons.addWidget(self._adopt_edge_families_button)
        review_buttons.addStretch(1)
        layout.addLayout(review_buttons)

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
        buttons.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        source_visibility_buttons = QtWidgets.QHBoxLayout()
        self._hide_sources_button = QtWidgets.QPushButton("Hide Preset Sources")
        self._hide_sources_button.clicked.connect(self._hide_preset_sources)
        source_visibility_buttons.addWidget(self._hide_sources_button)
        self._show_sources_button = QtWidgets.QPushButton("Show Preset Sources")
        self._show_sources_button.clicked.connect(self._show_preset_sources)
        source_visibility_buttons.addWidget(self._show_sources_button)
        source_visibility_buttons.addStretch(1)
        layout.addLayout(source_visibility_buttons)
        return root

    def _refresh_review_table(self) -> None:
        """Show every leg, anchor and control area row with what it still needs."""

        rows = []
        try:
            model = to_intersection_model(find_v1_intersection_model(self.document))
            rows = intersection_review_rows(model)
        except Exception as error:
            self._review_summary.setText(f"Source review unavailable: {error}")
            self._review_table.setRowCount(0)
            return
        self._review_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            values = (
                row.kind,
                row.row_id,
                row.approval_status,
                ", ".join(row.missing_fields),
                row.notes,
            )
            for column, value in enumerate(values):
                self._review_table.setItem(index, column, QtWidgets.QTableWidgetItem(str(value)))
        self._review_summary.setText(intersection_review_summary(rows))

    def _accept_reviewed_rows(self) -> None:
        """Fill the leg refs the document already holds and accept the complete rows."""

        try:
            obj = find_v1_intersection_model(self.document)
            model = to_intersection_model(obj)
            if model is None:
                _show_message(self.form, "Intersections", "Create or apply an Intersection source first.")
                return
            leg_refs = resolve_intersection_review_leg_refs(self.document, model)
            prepared = apply_intersection_review(model, leg_refs=leg_refs)
            create_or_update_v1_intersection_model_object(
                self.document,
                intersection_model=prepared.model,
                project=find_project(self.document),
                label="Intersections",
            )
            self.document.recompute()
        except Exception as error:
            _show_message(self.form, "Intersections", f"Source review could not be applied:\n{error}")
            return
        self._refresh_review_table()
        lines = [
            "Accepted %d row(s)." % len(prepared.accepted_row_ids),
        ]
        if prepared.incomplete_row_ids:
            lines.append("Still incomplete: %s" % ", ".join(prepared.incomplete_row_ids))
            lines.extend(str(diagnostic) for diagnostic in prepared.diagnostics)
            lines.append("")
            lines.append("A row is not accepted while a field it needs is missing, because a ref that names")
            lines.append("nothing would leave the same gap behind a reviewed status.")
        _show_message(self.form, "Intersections", "\n".join(lines))

    def _confirm_edge_family_adoption(self) -> bool:
        """Ask the user to own the claim that the edge families come from the Assembly."""

        try:
            answer = QtWidgets.QMessageBox.question(
                self.form,
                "Intersections",
                "Mark the edge policies as derived from the Assembly?\n\n"
                "This states that you have reviewed the starter Assembly and Subassembly "
                "and that they are the source of the intersection edge families.",
            )
        except Exception:
            return False
        return answer == QtWidgets.QMessageBox.Yes

    def _adopt_edge_families(self) -> None:
        """Change the preset edge policies' source method, as its own decision."""

        try:
            obj = find_v1_intersection_model(self.document)
            model = to_intersection_model(obj)
            if model is None:
                _show_message(self.form, "Intersections", "Create or apply an Intersection source first.")
                return
            if not self._confirm_edge_family_adoption():
                return
            prepared = adopt_edge_families_from_subassembly(model)
            create_or_update_v1_intersection_model_object(
                self.document,
                intersection_model=prepared.model,
                project=find_project(self.document),
                label="Intersections",
            )
            self.document.recompute()
        except Exception as error:
            _show_message(self.form, "Intersections", f"Edge families could not be adopted:\n{error}")
            return
        self._refresh_review_table()
        lines = ["Adopted %d edge policy row(s) from the Subassembly." % len(prepared.accepted_row_ids)]
        lines.extend(str(diagnostic) for diagnostic in prepared.diagnostics)
        _show_message(self.form, "Intersections", "\n".join(lines))

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
        self._sync_spec_kind_to_preset()

    def _select_preset_of_existing_intersection(self) -> None:
        """Point the Preset combo at the kind of the document's Intersection, if there is one."""

        model = to_intersection_model(find_v1_intersection_model(self.document)) if self.document is not None else None
        rows = list(getattr(model, "intersection_rows", []) or [])
        if not rows:
            return
        kind = str(getattr(rows[0], "intersection_kind", "") or "")
        for index in range(self._preset_combo.count()):
            if str(self._preset_combo.itemData(index) or "") == kind:
                self._preset_combo.setCurrentIndex(index)
                return

    def _sync_spec_kind_to_preset(self) -> None:
        """The spec's kind follows the Preset until a spec is loaded from the document; a loaded
        spec keeps the kind its Intersection source was built with."""

        if not hasattr(self, "_spec_kind_combo") or self._spec_base is not None:
            return
        spec_kind = spec_kind_for_model_kind(self._selected_kind())
        if spec_kind:
            _select_combo_data(self._spec_kind_combo, spec_kind)
            self._update_spec_kind_controls()

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
            self._reload_spec_after_source_change()
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
            created_details: list[str] = []
            obj, control_region_count = create_intersection_from_existing_alignments(
                self.document,
                preset_label=self._selected_label(),
                primary_alignment_ref=self._selected_primary_alignment_ref(),
                secondary_alignment_ref=self._selected_secondary_alignment_ref(),
                detection_result=self._last_detection,
                details=created_details,
                **self._selected_options(),
            )
            self._last_applied_intersection = f"{getattr(obj, 'Label', '') or getattr(obj, 'Name', '')} | {getattr(obj, 'IntersectionModelId', '')}"
            self._update_status("Existing Alignment intersection applied.")
            self._reload_spec_after_source_change()
            _show_message(
                self.form,
                "Intersection",
                (
                    "Intersection has been applied from existing Alignments.\n\n"
                    f"Object: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')}\n"
                    f"IntersectionModel: {getattr(obj, 'IntersectionModelId', '')}\n"
                    f"Control Regions: {control_region_count}\n\n"
                    + "\n".join(created_details)
                ),
            )
        except Exception as exc:
            self._last_applied_intersection = ""
            self._update_status(f"Apply failed: {exc}")
            _show_message(self.form, "Intersection", f"Intersection was not applied.\n{exc}")

    def _hide_preset_sources(self):
        count = _set_intersection_preset_sources_visible(self.document, visible=False)
        self._update_status(f"Preset source objects hidden: {count}.")

    def _show_preset_sources(self):
        count = _set_intersection_preset_sources_visible(self.document, visible=True)
        self._update_status(f"Preset source objects shown: {count}.")

    # -- parametric spec (plan phase R7b) ---------------------------------------------------

    def _build_spec_group(self):
        """The parametric spec of the document's intersection, edited directly.

        Load Spec reads the stored spec (or the one the rows give); Check Spec runs the kernel on it
        with the current Applied Sections and lists every value with its origin; Apply Spec stores it.
        A radius or width of 0 means the kernel's default.
        """

        group = QtWidgets.QGroupBox("Parametric Spec")
        outer = QtWidgets.QVBoxLayout(group)
        form = QtWidgets.QFormLayout()

        self._spec_kind_combo = QtWidgets.QComboBox()
        for value in INTERSECTION_SPEC_KINDS:
            self._spec_kind_combo.addItem(value, value)
        self._spec_kind_combo.currentIndexChanged.connect(self._update_spec_kind_controls)
        # the kind is the Intersection source's: it follows the Preset, then the loaded spec
        self._spec_kind_combo.setEnabled(False)
        self._spec_kind_combo.setToolTip("Follows the Preset; after Create Sources or Apply, the Intersection source's kind.")
        form.addRow("Kind:", self._spec_kind_combo)

        self._spec_primary_combo = QtWidgets.QComboBox()
        self._spec_secondary_combo = QtWidgets.QComboBox()
        _populate_alignment_combo(self._spec_primary_combo, self._alignment_choices)
        _populate_alignment_combo(self._spec_secondary_combo, self._alignment_choices)
        form.addRow("Primary Road:", self._spec_primary_combo)
        form.addRow("Secondary Road:", self._spec_secondary_combo)

        self._spec_anchor_combo = QtWidgets.QComboBox()
        for value in SPEC_ANCHOR_METHODS:
            self._spec_anchor_combo.addItem(value, value)
        self._spec_anchor_combo.currentIndexChanged.connect(self._update_spec_kind_controls)
        form.addRow("Anchor:", self._spec_anchor_combo)
        self._spec_primary_station = _spec_spin(0.0, 1.0e7, " m")
        self._spec_secondary_station = _spec_spin(0.0, 1.0e7, " m")
        form.addRow("Primary Station:", self._spec_primary_station)
        form.addRow("Secondary Station:", self._spec_secondary_station)

        self._spec_corner_radius = _spec_spin(0.0, 500.0, " m")
        form.addRow("Corner Radius (0 = default):", self._spec_corner_radius)
        self._spec_grading_combo = QtWidgets.QComboBox()
        for value in SPEC_GRADING_MODES:
            self._spec_grading_combo.addItem(value or "(default)", value)
        form.addRow("Grading Mode:", self._spec_grading_combo)
        outer.addLayout(form)

        self._spec_ring_group = QtWidgets.QGroupBox("Roundabout Ring")
        ring = QtWidgets.QFormLayout(self._spec_ring_group)
        self._spec_inscribed = _spec_spin(0.0, 500.0, " m")
        self._spec_circulatory = _spec_spin(0.0, 500.0, " m")
        self._spec_apron = _spec_spin(0.0, 100.0, " m")
        self._spec_entry = _spec_spin(0.0, 500.0, " m")
        self._spec_exit = _spec_spin(0.0, 500.0, " m")
        self._spec_circulation_combo = QtWidgets.QComboBox()
        for value in SPEC_CIRCULATIONS:
            self._spec_circulation_combo.addItem(value, value)
        ring.addRow("Inscribed Radius:", self._spec_inscribed)
        ring.addRow("Circulatory Width:", self._spec_circulatory)
        ring.addRow("Outer Apron Width:", self._spec_apron)
        ring.addRow("Entry Radius (0 = default):", self._spec_entry)
        ring.addRow("Exit Radius (0 = default):", self._spec_exit)
        ring.addRow("Circulation:", self._spec_circulation_combo)
        outer.addWidget(self._spec_ring_group)

        outer.addWidget(QtWidgets.QLabel("Legs (Check Spec lists them; untick to close one, radii for a roundabout approach):"))
        self._spec_leg_table = QtWidgets.QTableWidget(0, 5)
        self._spec_leg_table.setHorizontalHeaderLabels(["Road", "Side", "Open", "Entry R", "Exit R"])
        self._spec_leg_table.setMinimumHeight(110)
        outer.addWidget(self._spec_leg_table)

        buttons = QtWidgets.QHBoxLayout()
        self._spec_load_button = QtWidgets.QPushButton("Load Spec")
        self._spec_load_button.clicked.connect(self._load_spec)
        buttons.addWidget(self._spec_load_button)
        self._spec_check_button = QtWidgets.QPushButton("Check Spec")
        self._spec_check_button.clicked.connect(self._check_spec)
        buttons.addWidget(self._spec_check_button)
        self._spec_apply_button = QtWidgets.QPushButton("Apply Spec")
        self._spec_apply_button.clicked.connect(self._apply_spec)
        buttons.addWidget(self._spec_apply_button)
        buttons.addStretch(1)
        outer.addLayout(buttons)
        self._spec_base = None
        self._update_spec_kind_controls()
        return group

    def _update_spec_kind_controls(self, *args) -> None:
        self._spec_ring_group.setVisible(_combo_data_or_text(self._spec_kind_combo) == "roundabout")
        manual = _combo_data_or_text(self._spec_anchor_combo) == "manual"
        self._spec_primary_station.setEnabled(manual)
        self._spec_secondary_station.setEnabled(manual)

    def _spec_form(self) -> IntersectionSpecForm:
        legs = []
        for row in range(self._spec_leg_table.rowCount()):
            def text(column, row=row):
                item = self._spec_leg_table.item(row, column)
                return item.text() if item is not None else ""
            open_item = self._spec_leg_table.item(row, 2)
            legs.append(
                LegFormRow(
                    text(0),
                    text(1),
                    open_item is None or open_item.checkState() == _checked(),
                    _float_text(text(3)),
                    _float_text(text(4)),
                )
            )
        return IntersectionSpecForm(
            intersection_id=str(getattr(self._spec_base, "intersection_id", "") or ""),
            kind=_combo_data_or_text(self._spec_kind_combo),
            primary_road=_combo_data_or_text(self._spec_primary_combo),
            secondary_road=_combo_data_or_text(self._spec_secondary_combo),
            anchor_method=_combo_data_or_text(self._spec_anchor_combo),
            primary_station=float(self._spec_primary_station.value()),
            secondary_station=float(self._spec_secondary_station.value()),
            corner_radius_m=float(self._spec_corner_radius.value()),
            grading_mode=str(self._spec_grading_combo.currentData() or ""),
            inscribed_radius_m=float(self._spec_inscribed.value()),
            circulatory_width_m=float(self._spec_circulatory.value()),
            apron_width_m=float(self._spec_apron.value()),
            entry_radius_m=float(self._spec_entry.value()),
            exit_radius_m=float(self._spec_exit.value()),
            circulation=_combo_data_or_text(self._spec_circulation_combo),
            leg_rows=legs,
        )

    def _fill_spec_widgets(self, form: IntersectionSpecForm) -> None:
        _select_combo_data(self._spec_kind_combo, form.kind)
        _select_combo_data(self._spec_primary_combo, form.primary_road)
        _select_combo_data(self._spec_secondary_combo, form.secondary_road)
        _select_combo_data(self._spec_anchor_combo, form.anchor_method)
        self._spec_primary_station.setValue(form.primary_station)
        self._spec_secondary_station.setValue(form.secondary_station)
        self._spec_corner_radius.setValue(form.corner_radius_m)
        _select_combo_data(self._spec_grading_combo, form.grading_mode)
        self._spec_inscribed.setValue(form.inscribed_radius_m)
        self._spec_circulatory.setValue(form.circulatory_width_m)
        self._spec_apron.setValue(form.apron_width_m)
        self._spec_entry.setValue(form.entry_radius_m)
        self._spec_exit.setValue(form.exit_radius_m)
        _select_combo_data(self._spec_circulation_combo, form.circulation)
        self._fill_spec_leg_table(form.leg_rows)
        self._update_spec_kind_controls()

    def _fill_spec_leg_table(self, rows: list[LegFormRow]) -> None:
        self._spec_leg_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, value in enumerate((row.road_ref, row.side)):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(item.flags() & ~_editable_flag())
                self._spec_leg_table.setItem(index, column, item)
            open_item = QtWidgets.QTableWidgetItem("")
            open_item.setFlags(open_item.flags() | _checkable_flag())
            open_item.setCheckState(_checked() if row.enabled else _unchecked())
            self._spec_leg_table.setItem(index, 2, open_item)
            self._spec_leg_table.setItem(index, 3, QtWidgets.QTableWidgetItem(f"{row.entry_radius_m:g}"))
            self._spec_leg_table.setItem(index, 4, QtWidgets.QTableWidgetItem(f"{row.exit_radius_m:g}"))

    def _reload_spec_after_source_change(self) -> None:
        """Show the spec of the Intersection source just created or applied: a new source replaces
        whatever spec the group held, so the group starts from the new rows."""

        self._spec_base = None
        self._load_spec(report=False)

    def _load_spec(self, report: bool = True) -> bool:
        obj = find_v1_intersection_model(self.document)
        if obj is None:
            if report:
                self._status.setPlainText("No Intersection source in this document. Create one from a preset or from existing Alignments first.")
            return False
        # the new source may have added Alignments; refreshing them here keeps the status text
        self._alignment_choices = list_v1_alignment_choices(self.document) if self.document is not None else []
        _populate_alignment_combo(self._spec_primary_combo, self._alignment_choices)
        _populate_alignment_combo(self._spec_secondary_combo, self._alignment_choices)
        spec = stored_intersection_spec(obj)
        origin = "stored spec"
        if spec is None:
            spec = spec_from_intersection_model(to_intersection_model(obj))
            origin = "spec read from the intersection rows (not stored yet)"
        if spec is None:
            if report:
                self._status.setPlainText("The Intersection source holds no intersection row.")
            return False
        self._spec_base = spec
        self._fill_spec_widgets(form_from_spec(spec))
        if report:
            self._status.setPlainText(f"Loaded the {origin}: {spec.intersection_id}.")
        return True

    def _check_spec(self):
        spec, errors = spec_from_form(self._spec_form(), base=self._spec_base)
        if spec is None:
            self._status.setPlainText("The spec is not complete:\n" + "\n".join(errors))
            return None
        applied = to_applied_section_set(find_v1_applied_section_set(self.document))
        if applied is None:
            self._status.setPlainText("Run Applied Sections first: the kernel takes the roads' pavement widths from them.")
            return None
        alignments = [model for model in (to_alignment_model(obj) for obj in list(getattr(self.document, "Objects", []) or [])) if model is not None]
        result = intersection_geometry_from_models(to_intersection_model(find_v1_intersection_model(self.document)), alignments, applied, spec=spec)
        self._fill_spec_leg_table(leg_rows_for_result(result, self._spec_form()))
        self._status.setPlainText("\n".join(spec_check_lines(result)))
        return result

    def _apply_spec(self) -> bool:
        obj = find_v1_intersection_model(self.document)
        if obj is None:
            self._status.setPlainText("No Intersection source in this document.")
            return False
        spec, errors = spec_from_form(self._spec_form(), base=self._spec_base)
        if spec is None:
            self._status.setPlainText("The spec was not stored:\n" + "\n".join(errors))
            return False
        store_intersection_spec(obj, spec)
        self._spec_base = spec
        self._status.setPlainText(
            f"Stored the spec of {spec.intersection_id}.\n"
            "Next: Applied Sections (Build Sections), then Build Parametric."
        )
        return True

    def _update_status(self, *args, prefix: str = ""):
        if args and not prefix and isinstance(args[0], str):
            prefix = args[0]
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
                *_preset_default_summary_lines(self.document),
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


# The preset's Control Length spin box defaults to this, so an existing-Alignment apply
# that passes no length uses the same span.
EXISTING_ALIGNMENT_DEFAULT_CONTROL_LENGTH = 24.0


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


def _preset_default_summary_lines(document) -> list[str]:
    """Return the preset-default checklist for the panel, or nothing before Apply."""

    try:
        model = to_intersection_model(find_v1_intersection_model(document))
    except Exception:
        return []
    rows = intersection_preset_default_rows(model)
    if not rows:
        return []
    lines = ["", "Preset defaults in the document:"]
    for row in rows:
        lines.append(
            "- %s: %s  [%s] %s" % (row.label, row.value, row.carrier, row.review_state)
        )
    unreviewable = [row.label for row in rows if not row.reviewable]
    if unreviewable:
        lines.append("  (no review state for: %s)" % ", ".join(unreviewable))
    return lines


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
    details: list[str] | None = None,
):
    """Create or update an IntersectionModel object from existing Alignment selections.

    The same source set the preset writes is created around the Alignments the user
    selected: intersection control Regions as overlay rows on their existing Region
    models, one Superelevation handoff source for each road that has none, and the
    Drainage handoff source. `details`, when given, receives one line for each.
    """

    if document is None:
        raise RuntimeError("No active document is available.")
    project = find_project(document)
    detail_lines = details if details is not None else []
    detail_lines.extend(
        ensure_existing_alignment_control_regions(
            document,
            preset_label=preset_label,
            primary_alignment_ref=primary_alignment_ref,
            secondary_alignment_ref=secondary_alignment_ref,
            detection_result=detection_result,
            control_length=control_length,
            project=project,
        )
    )
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
    store_intersection_spec(obj, spec_from_intersection_model(model))
    kind = intersection_preset_kind_from_label(preset_label)
    control_regions = list_intersection_control_region_choices(document, intersection_ref_for_kind(kind))
    detail_lines.extend(
        _create_preset_superelevation_source(
            document,
            intersection_kind=kind,
            primary_alignment_ref=primary_alignment_ref,
            secondary_alignment_ref=secondary_alignment_ref,
            control_region_choices=control_regions,
            grading_policy=grading_policy or str(intersection_preset_row_from_label(preset_label).get("grading", "") or ""),
            project=project,
            skip_alignment_refs=_alignments_with_superelevation_source(
                document,
                (primary_alignment_ref, secondary_alignment_ref),
            ),
        )
    )
    detail_lines.extend(
        _create_preset_drainage_source(
            document,
            intersection_kind=kind,
            primary_alignment_ref=primary_alignment_ref,
            secondary_alignment_ref=secondary_alignment_ref,
            control_region_choices=control_regions,
            drainage_mode=drainage_mode or str(intersection_preset_row_from_label(preset_label).get("drainage", "") or ""),
            project=project,
        )
    )
    try:
        document.recompute()
    except Exception:
        pass
    return obj, control_region_count


def ensure_existing_alignment_control_regions(
    document,
    *,
    preset_label: str,
    primary_alignment_ref: str,
    secondary_alignment_ref: str,
    detection_result=None,
    control_length: float | None = None,
    project=None,
) -> list[str]:
    """Add an intersection control Region overlay row to each selected Alignment's Regions.

    Existing intersection-tagged Regions are respected and nothing is added, so applying
    twice, or applying after hand-authored control Regions, changes no Region source. The
    user's own rows are never edited: each overlay is a new row with a higher priority.
    Both Regions are built before either is written, so a refusal leaves the document as it was.
    """

    kind = intersection_preset_kind_from_label(preset_label)
    if not kind:
        raise ValueError(f"Unsupported Intersection Preset: {preset_label}")
    intersection_ref = intersection_ref_for_kind(kind)
    if list_intersection_control_region_choices(document, intersection_ref):
        return ["Control Regions: kept the existing intersection-tagged Regions"]
    detection = detection_result or _detect_preset_alignment_intersection(
        document,
        primary_alignment_ref=primary_alignment_ref,
        secondary_alignment_ref=secondary_alignment_ref,
    )
    length = _positive_float_or_none(control_length) or EXISTING_ALIGNMENT_DEFAULT_CONTROL_LENGTH
    status = str(getattr(detection, "status", "") or "")
    if detection is None or status not in {"intersection", "nearest"}:
        raise ValueError(
            "The two Alignments could not be placed against each other, so no control Region station "
            "is known. Run Auto Detect and check both Alignments have geometry."
        )
    # Roads that do not meet are not an intersection. Within one control length the
    # nearest approach is still inside the junction's own control area.
    if status == "nearest" and float(getattr(detection, "distance", 0.0) or 0.0) > length:
        raise ValueError(
            "The two Alignments do not meet: their nearest approach is %.3f m, more than the %.3f m control length."
            % (float(getattr(detection, "distance", 0.0) or 0.0), length)
        )
    plans = []
    for role, alignment_ref, station in (
        ("primary", primary_alignment_ref, float(getattr(detection, "primary_station", 0.0) or 0.0)),
        ("secondary", secondary_alignment_ref, float(getattr(detection, "secondary_station", 0.0) or 0.0)),
    ):
        region_obj = _region_object_for_alignment(document, alignment_ref)
        if region_obj is None:
            raise ValueError(
                f"Alignment {alignment_ref} has no Region model. Author its Regions first so the "
                "intersection control Region can inherit their Assembly."
            )
        overlay = build_control_region_overlay(
            to_region_model(region_obj),
            station=station,
            control_length=length,
            intersection_ref=intersection_ref,
            role=role,
            kind=kind,
        )
        plans.append((region_obj, overlay, role, alignment_ref, station))
    lines = []
    for region_obj, overlay, role, alignment_ref, station in plans:
        create_or_update_v1_region_model_object(
            document,
            overlay.model,
            project=project,
            object_name=str(getattr(region_obj, "Name", "") or "V1RegionModel"),
            label=str(getattr(region_obj, "Label", "") or "Regions"),
        )
        lines.append(
            "Control Region: %s | alignment=%s | STA %.3f-%.3f | around crossing STA %.3f | inherits %s"
            % (
                overlay.row.region_id,
                alignment_ref,
                overlay.row.station_start,
                overlay.row.station_end,
                station,
                overlay.base_region_id or "no covering row",
            )
        )
    return lines


def _region_object_for_alignment(document, alignment_ref: str):
    """Return the first Region model object that belongs to the Alignment."""

    target = str(alignment_ref or "").strip()
    for obj in list(getattr(document, "Objects", []) or []):
        model = to_region_model(obj)
        if model is not None and str(getattr(model, "alignment_id", "") or "") == target:
            return obj
    return None


def _alignments_with_superelevation_source(document, alignment_refs) -> list[str]:
    """Return which of the Alignments already carry a Superelevation source."""

    wanted = {str(ref or "").strip() for ref in alignment_refs}
    found: list[str] = []
    for obj in list(getattr(document, "Objects", []) or []):
        model = to_superelevation_model(obj)
        alignment_id = str(getattr(model, "alignment_id", "") or "") if model is not None else ""
        if alignment_id in wanted and alignment_id not in found:
            found.append(alignment_id)
    return found


def _apply_preset_source_completeness_status(model, *, preset_label: str) -> None:
    """Mark preset-authored source rows as explicit review-required defaults."""

    kind = intersection_preset_kind_from_label(preset_label) or str(preset_label or "").strip()
    if kind not in {"t_intersection", "cross_intersection", "roundabout"}:
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
    model.curb_return_policy_rows = [
        replace(
            row,
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(getattr(row, "diagnostic_rows", []) or [], "preset_curb_return_policy_review_required"),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "curb_return_policy_rows", []) or [])
    ]
    model.arm_policy_rows = [
        replace(
            row,
            approval_status=str(getattr(row, "approval_status", "") or "draft"),
            diagnostic_rows=_append_diagnostics(getattr(row, "diagnostic_rows", []) or [], "preset_arm_policy_review_required"),
            notes=_append_note(str(getattr(row, "notes", "") or ""), note),
        )
        for row in list(getattr(model, "arm_policy_rows", []) or [])
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
    store_intersection_spec(obj, spec_from_intersection_model(model))
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
    if _model_intersection_kind(model) == "roundabout":
        _ensure_roundabout_source_policy_rows(model, radius=radius_value)


def _model_intersection_kind(model) -> str:
    rows = list(getattr(model, "intersection_rows", []) or [])
    if not rows:
        return ""
    return str(getattr(rows[0], "intersection_kind", "") or "").strip()


def _model_intersection_id(model) -> str:
    rows = list(getattr(model, "intersection_rows", []) or [])
    if not rows:
        return ""
    return str(getattr(rows[0], "intersection_id", "") or "").strip()


def _ensure_roundabout_source_policy_rows(model, *, radius: float | None = None) -> None:
    """Add explicit source policy rows for the Roundabout starter contract.

    The first implementation slice keeps the values in EdgePolicy rows so existing
    object serialization can carry them without introducing a new source model
    family mid-stream.
    """

    intersection_id = _model_intersection_id(model)
    if not intersection_id:
        return
    outer_radius = _positive_float_or_none(radius) or _first_curb_return_radius(model) or 18.0
    central_island_radius = max(outer_radius * 0.45, 1.0)
    circulatory_lane_width = max(outer_radius - central_island_radius, 1.0)
    approach_connector_length = max(outer_radius * 1.25, 12.0)
    apron_width = max(circulatory_lane_width * 0.15, 0.5)
    slope_face_width = max(apron_width, 0.5)
    subgrade_depth = 0.30
    policy_rows = [
        IntersectionEdgePolicyRow(
            policy_id=f"roundabout-policy:{intersection_id}:central-island-radius",
            intersection_id=intersection_id,
            edge_role="central_island_edge",
            side="inside",
            offset_rule="roundabout_central_island_radius",
            offset_value=central_island_radius,
            elevation_rule="roundabout_radial_crossfall",
            edge_family_intent="roundabout",
            source_method="preset_explicit",
            approval_status="accepted",
            diagnostic_rows=[],
            notes=f"roundabout_policy=central_island_radius; radius={central_island_radius:.3f}m",
        ),
        IntersectionEdgePolicyRow(
            policy_id=f"roundabout-policy:{intersection_id}:circulatory-outer-radius",
            intersection_id=intersection_id,
            edge_role="circulatory_outer_edge",
            side="outside",
            offset_rule="roundabout_circulatory_outer_radius",
            offset_value=outer_radius,
            elevation_rule="roundabout_radial_crossfall",
            edge_family_intent="roundabout",
            source_method="preset_explicit",
            approval_status="accepted",
            diagnostic_rows=[],
            notes=(
                f"roundabout_policy=circulatory_outer_radius; radius={outer_radius:.3f}m; "
                f"lane_width={circulatory_lane_width:.3f}m"
            ),
        ),
        IntersectionEdgePolicyRow(
            policy_id=f"roundabout-policy:{intersection_id}:outer-apron-width",
            intersection_id=intersection_id,
            edge_role="outer_apron_edge",
            side="outside",
            offset_rule="roundabout_outer_apron_width",
            offset_value=apron_width,
            elevation_rule="roundabout_radial_crossfall",
            edge_family_intent="roundabout",
            source_method="preset_explicit",
            approval_status="accepted",
            diagnostic_rows=[],
            notes=f"roundabout_policy=outer_apron_width; width={apron_width:.3f}m",
        ),
        IntersectionEdgePolicyRow(
            policy_id=f"roundabout-policy:{intersection_id}:slope-face-width",
            intersection_id=intersection_id,
            edge_role="slope_face_edge",
            side="outside",
            offset_rule="roundabout_slope_face_width",
            offset_value=slope_face_width,
            elevation_rule="from_grading_policy",
            edge_family_intent="roundabout",
            source_method="preset_explicit",
            approval_status="accepted",
            diagnostic_rows=[],
            notes=f"roundabout_policy=slope_face_width; width={slope_face_width:.3f}m",
        ),
        IntersectionEdgePolicyRow(
            policy_id=f"roundabout-policy:{intersection_id}:approach-connector-length",
            intersection_id=intersection_id,
            edge_role="entry_exit_edge",
            side="both",
            offset_rule="roundabout_approach_connector_length",
            offset_value=approach_connector_length,
            elevation_rule="from_grading_policy",
            edge_family_intent="roundabout",
            source_method="preset_explicit",
            approval_status="accepted",
            diagnostic_rows=[],
            notes=f"roundabout_policy=approach_connector_length; length={approach_connector_length:.3f}m",
        ),
        IntersectionEdgePolicyRow(
            policy_id=f"roundabout-policy:{intersection_id}:subgrade-depth",
            intersection_id=intersection_id,
            edge_role="subgrade_edge",
            side="both",
            offset_rule="roundabout_subgrade_depth",
            offset_value=subgrade_depth,
            elevation_rule="below_roundabout_finished_grade",
            edge_family_intent="roundabout",
            source_method="preset_explicit",
            approval_status="accepted",
            diagnostic_rows=[],
            notes=f"roundabout_policy=subgrade_depth; depth={subgrade_depth:.3f}m",
        ),
    ]
    existing = {
        str(getattr(row, "policy_id", "") or ""): row
        for row in list(getattr(model, "edge_policy_rows", []) or [])
    }
    for row in policy_rows:
        existing[str(getattr(row, "policy_id", "") or "")] = row
    model.edge_policy_rows = list(existing.values())
    new_refs = [str(getattr(row, "policy_id", "") or "") for row in policy_rows]
    model.intersection_rows = [
        replace(
            row,
            policy_refs=_unique_policy_refs([*list(getattr(row, "policy_refs", []) or []), *new_refs]),
            notes=(
                str(getattr(row, "notes", "") or "").strip()
                + " Roundabout explicit source policy rows added."
            ).strip(),
        )
        for row in list(getattr(model, "intersection_rows", []) or [])
    ]


def _first_curb_return_radius(model) -> float | None:
    for row in list(getattr(model, "curb_return_policy_rows", []) or []):
        value = _positive_float_or_none(getattr(row, "radius", 0.0))
        if value is not None:
            return value
    return None


def _unique_policy_refs(values) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


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
    skip_alignment_refs=(),
) -> list[str]:
    """Store a preset-owned Superelevation handoff source without inventing crossfall rows.

    A road listed in `skip_alignment_refs` already has a Superelevation source of its own,
    so it gets no handoff source and keeps what its author wrote.
    """

    # One source per participating road. Applied Sections pairs superelevation by
    # alignment_id, so a single source keyed on the primary would leave the side road
    # with no source at all.
    participating = [
        ref
        for ref in (str(primary_alignment_ref or "").strip(), str(secondary_alignment_ref or "").strip())
        if ref
    ]
    details: list[str] = []
    skipped = {str(ref or "").strip() for ref in skip_alignment_refs}
    for index, alignment_ref in enumerate(participating, start=1):
        role = "primary" if index == 1 else "secondary"
        if alignment_ref in skipped:
            details.append(f"Superelevation: kept the existing source | alignment={alignment_ref}")
            continue
        model = SuperelevationModel(
            schema_version=1,
            project_id=_project_id(project),
            label=f"Intersection Preset Superelevation ({role})",
            superelevation_id=(
                f"superelevation:intersection-preset-{_safe_id(intersection_kind)}:{_safe_id(role)}"
            ),
            alignment_id=alignment_ref,
            profile_id="",
            superelevation_kind="intersection_superelevation_handoff",
            control_rows=[],
            transition_rows=[],
            constraint_rows=[
                SuperelevationConstraint(
                    constraint_id=(
                        f"constraint:intersection:{_safe_id(intersection_kind)}:{_safe_id(role)}:grading-override"
                    ),
                    kind="intersection_grading_override",
                    value=str(grading_policy or "intersection_override"),
                    unit="policy",
                    hard_or_soft="soft",
                ),
                SuperelevationConstraint(
                    constraint_id=(
                        f"constraint:intersection:{_safe_id(intersection_kind)}:{_safe_id(role)}:auto-calculate"
                    ),
                    kind="requires_auto_calculate_review",
                    value="true",
                    unit="boolean",
                    hard_or_soft="soft",
                ),
            ],
            source_refs=[
                alignment_ref,
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
            object_name=f"V1IntersectionPresetSuperelevation{_safe_id(role).title().replace('-', '')}",
            label=f"Intersection Preset Superelevation ({role})",
        )
        details.append(
            "Superelevation: %s | %s | alignment=%s"
            % (
                getattr(obj, "Label", "") or getattr(obj, "Name", ""),
                getattr(obj, "SuperelevationId", ""),
                alignment_ref,
            )
        )
    details.append(
        "Superelevation rows per road: controls=0; transitions=0; constraints=2 (%d road(s))"
        % (len(participating) - len([ref for ref in participating if ref in skipped]))
    )
    return details


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
                risk_level="high",
                notes="Preset handoff only; replace with real inlet/outfall Structures during drainage design.",
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
    for obj in list(getattr(document, "Objects", []) or []):
        if not _is_intersection_preset_tree_object(obj):
            continue
        try:
            route_object_to_project_tree(project, obj)
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


def _spec_spin(minimum: float, maximum: float, suffix: str):
    spin = QtWidgets.QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(3)
    spin.setSuffix(suffix)
    return spin


def _select_combo_data(combo, value: str) -> None:
    index = combo.findData(value)
    if index < 0:
        index = combo.findText(str(value or ""))
    if index >= 0:
        combo.setCurrentIndex(index)


def _float_text(text: str) -> float:
    try:
        return float(str(text or "0").strip() or 0.0)
    except ValueError:
        return -1.0


def _qt_flag(group: str, name: str):
    from freecad.Corridor_Road.qt_compat import QtCore

    holder = getattr(QtCore.Qt, group, QtCore.Qt)
    return getattr(holder, name, getattr(QtCore.Qt, name))


def _checked():
    return _qt_flag("CheckState", "Checked")


def _unchecked():
    return _qt_flag("CheckState", "Unchecked")


def _editable_flag():
    return _qt_flag("ItemFlag", "ItemIsEditable")


def _checkable_flag():
    return _qt_flag("ItemFlag", "ItemIsUserCheckable")


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

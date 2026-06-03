"""Intersection source editor command for Parametric Road v1."""

from __future__ import annotations

from math import hypot

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is unavailable in plain Python.
    App = None
try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCADGui is unavailable in plain Python.
    Gui = None
try:
    import Part
except Exception:  # pragma: no cover - Part is unavailable in plain Python.
    Part = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtWidgets

from ..models.source.intersection_model import (
    IntersectionControlArea,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
    intersection_kind_from_label,
    intersection_preset_labels,
)
from ..objects.obj_alignment import to_alignment_model
from ..objects.obj_alignment import V1AlignmentObject, ViewProviderV1Alignment
from ..objects.obj_profile import create_sample_v1_profile
from ..objects.obj_intersection import create_or_update_v1_intersection_model_object
from ..objects.obj_region import create_or_update_v1_region_model_object, to_region_model
from ..objects.obj_stationing import create_v1_stationing
from ..objects.obj_assembly import find_v1_assembly_model, to_assembly_model
from ..models.source.region_model import RegionModel, RegionRow
from ..services.evaluation.intersection_alignment_detection_service import AlignmentIntersectionDetectionService
from ...objects.obj_project import find_project, route_to_v1_tree


INTERSECTION_COMMAND_ID = "CorridorRoad_V1EditIntersections"
INTERSECTION_SOURCE_MODES = ("Use Existing Alignments", "Create Starter Sources")
NEXT_INTERSECTION_WORKFLOW_TEXT = (
    "Workflow: Regions -> Intersections -> Structures -> Drainage -> Build Sections"
)


def list_v1_alignment_choices(document) -> list[tuple[str, str]]:
    """Return selectable v1 Alignment choices as ``(alignment_id, label)`` rows."""

    choices: list[tuple[str, str]] = []
    if document is None:
        return choices
    seen: set[str] = set()
    for obj in list(getattr(document, "Objects", []) or []):
        model = to_alignment_model(obj)
        if model is None:
            continue
        alignment_id = str(getattr(model, "alignment_id", "") or "").strip()
        if not alignment_id or alignment_id in seen:
            continue
        seen.add(alignment_id)
        label = str(getattr(model, "label", "") or getattr(obj, "Label", "") or alignment_id)
        choices.append((alignment_id, label))
    return choices


def alignment_model_by_ref(document, alignment_ref: str):
    """Return one AlignmentModel by v1 Alignment id."""

    target = str(alignment_ref or "").strip()
    if document is None or not target:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        model = to_alignment_model(obj)
        if model is not None and str(getattr(model, "alignment_id", "") or "") == target:
            return model
    return None


def validate_existing_alignment_selection(primary_alignment_ref: str, secondary_alignment_ref: str) -> list[str]:
    """Return validation errors for Existing Alignments mode."""

    primary = str(primary_alignment_ref or "").strip()
    secondary = str(secondary_alignment_ref or "").strip()
    errors: list[str] = []
    if not primary:
        errors.append("Primary Alignment is required.")
    if not secondary:
        errors.append("Secondary Alignment is required.")
    if primary and secondary and primary == secondary:
        errors.append("Primary and Secondary Alignment must be different.")
    return errors


def intersection_ref_for_kind(intersection_kind: str) -> str:
    """Return the first-slice Intersection ref used by starter control Regions."""

    kind = str(intersection_kind or "").strip() or "intersection"
    return f"intersection:starter-{kind}"


def list_intersection_control_region_choices(document, intersection_ref: str = "") -> list[dict[str, object]]:
    """Return Region rows that are already tagged as intersection control Regions."""

    target_ref = str(intersection_ref or "").strip()
    choices: list[dict[str, object]] = []
    if document is None:
        return choices
    for obj in list(getattr(document, "Objects", []) or []):
        region_model = to_region_model(obj)
        if region_model is None:
            continue
        model_id = str(getattr(region_model, "region_model_id", "") or "")
        alignment_id = str(getattr(region_model, "alignment_id", "") or "")
        for row in list(getattr(region_model, "region_rows", []) or []):
            row_intersection_ref = str(getattr(row, "intersection_ref", "") or "").strip()
            if not row_intersection_ref:
                continue
            if target_ref and row_intersection_ref != target_ref:
                continue
            region_id = str(getattr(row, "region_id", "") or "")
            choices.append(
                {
                    "control_region_ref": _control_region_ref(model_id, region_id),
                    "region_model_ref": model_id,
                    "region_id": region_id,
                    "alignment_ref": alignment_id,
                    "intersection_ref": row_intersection_ref,
                    "station_start": float(getattr(row, "station_start", 0.0) or 0.0),
                    "station_end": float(getattr(row, "station_end", 0.0) or 0.0),
                    "label": (
                        f"{region_id} | {alignment_id or '-'} | "
                        f"STA {float(getattr(row, 'station_start', 0.0) or 0.0):.3f}-"
                        f"{float(getattr(row, 'station_end', 0.0) or 0.0):.3f}"
                    ),
                }
            )
    return sorted(
        choices,
        key=lambda row: (
            str(row.get("alignment_ref", "")),
            float(row.get("station_start", 0.0)),
            str(row.get("region_id", "")),
        ),
    )


def build_intersection_model_from_sources(
    *,
    intersection_kind: str,
    source_mode: str,
    primary_alignment_ref: str,
    secondary_alignment_ref: str,
    control_region_choices: list[dict[str, object]],
    detection_result=None,
    project_id: str = "corridorroad-v1",
) -> IntersectionModel:
    """Build a durable first-slice IntersectionModel from panel selections and Region refs."""

    kind = str(intersection_kind or "").strip()
    intersection_id = intersection_ref_for_kind(kind)
    control_refs = [str(row.get("control_region_ref", "") or "") for row in control_region_choices]
    control_refs = [ref for ref in control_refs if ref]
    secondary_refs = [str(secondary_alignment_ref or "").strip()] if str(secondary_alignment_ref or "").strip() else []
    primary_station = float(getattr(detection_result, "primary_station", 0.0) or 0.0) if detection_result is not None else 0.0
    secondary_station = float(getattr(detection_result, "secondary_station", 0.0) or 0.0) if detection_result is not None else 0.0
    x = float(getattr(detection_result, "x", 0.0) or 0.0) if detection_result is not None else 0.0
    y = float(getattr(detection_result, "y", 0.0) or 0.0) if detection_result is not None else 0.0
    control_area_rows = _control_area_rows_from_region_choices(intersection_id, control_region_choices)
    leg_rows = _leg_rows_from_region_choices(intersection_id, control_region_choices)
    row = IntersectionRow(
        intersection_id=intersection_id,
        intersection_kind=kind,
        intersection_index=1,
        primary_alignment_ref=str(primary_alignment_ref or "").strip(),
        secondary_alignment_refs=secondary_refs,
        intersection_point_x=x,
        intersection_point_y=y,
        primary_station=primary_station,
        secondary_station_refs={secondary_refs[0]: secondary_station} if secondary_refs else {},
        control_region_refs=control_refs,
        leg_rows=leg_rows,
        control_area_ref=f"{intersection_id}:control-area",
        source_mode=_source_mode_id(source_mode),
        notes="Created by Intersections panel control Region linking.",
    )
    return IntersectionModel(
        schema_version=1,
        project_id=project_id,
        label="Intersections",
        intersection_model_id="intersections:main",
        intersection_rows=[row],
        control_area_rows=control_area_rows,
    )


def show_intersection_review_overlay(
    document,
    *,
    intersection_kind: str,
    primary_alignment_ref: str,
    secondary_alignment_ref: str,
    control_region_choices: list[dict[str, object]],
    detection_result=None,
    project=None,
):
    """Create or update the first-slice 3D review overlay for one intersection."""

    if document is None:
        raise RuntimeError("No active document is available.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Intersection review overlay.")

    alignment_by_ref = {
        str(ref): alignment_model_by_ref(document, str(ref))
        for ref in _unique_text_values(
            [
                primary_alignment_ref,
                secondary_alignment_ref,
                *[str(row.get("alignment_ref", "") or "") for row in control_region_choices],
            ]
        )
    }
    shapes: list[object] = []
    control_refs: list[str] = []
    for row in control_region_choices:
        alignment_ref = str(row.get("alignment_ref", "") or "")
        alignment = alignment_by_ref.get(alignment_ref)
        points = _alignment_station_span_points(
            alignment,
            float(row.get("station_start", 0.0) or 0.0),
            float(row.get("station_end", 0.0) or 0.0),
        )
        if len(points) >= 2:
            for first, second in zip(points[:-1], points[1:]):
                shapes.append(Part.makeLine(first, second))
            control_refs.append(str(row.get("control_region_ref", "") or ""))

    point = _intersection_review_point(detection_result)
    if point is None and control_region_choices:
        first_row = control_region_choices[0]
        alignment = alignment_by_ref.get(str(first_row.get("alignment_ref", "") or ""))
        point = _alignment_point_at_station(alignment, float(first_row.get("station_start", 0.0) or 0.0))
    if point is not None:
        shapes.extend(_intersection_point_marker_shapes(point, radius=3.0))

    if not shapes:
        raise RuntimeError("No Intersection review geometry could be created.")

    obj = document.getObject("V1IntersectionReviewOverlay")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1IntersectionReviewOverlay")
    obj.Label = "Intersection Review Overlay"
    obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
    _set_preview_property(obj, "CRRecordKind", "v1_intersection_review_overlay")
    _set_preview_property(obj, "V1ObjectType", "V1IntersectionReviewOverlay")
    _set_preview_property(obj, "IntersectionKind", str(intersection_kind or ""))
    _set_preview_property(obj, "PrimaryAlignmentRef", str(primary_alignment_ref or ""))
    _set_preview_property(obj, "SecondaryAlignmentRef", str(secondary_alignment_ref or ""))
    _set_preview_string_list_property(obj, "ControlRegionRefs", _unique_text_values(control_refs))
    _set_preview_integer_property(obj, "ShapePartCount", len(shapes))
    _style_intersection_review_overlay(obj, visible=True)
    try:
        prj = project or find_project(document)
        if prj is not None:
            route_to_v1_tree(prj, obj)
    except Exception:
        pass
    try:
        document.recompute()
    except Exception:
        pass
    return obj


def set_intersection_review_overlay_visible(document, visible: bool):
    """Set the Intersection review overlay visibility."""

    obj = document.getObject("V1IntersectionReviewOverlay") if document is not None else None
    if obj is None:
        return None
    try:
        obj.ViewObject.Visibility = bool(visible)
    except Exception:
        pass
    return obj


def starter_intersection_source_specs(intersection_kind: str) -> dict[str, object]:
    """Return starter source geometry specs for one supported intersection kind."""

    kind = str(intersection_kind or "").strip()
    if kind == "t_intersection":
        return {
            "kind": kind,
            "alignments": [
                {"role": "primary", "label": "Intersection Main Road", "points": [(-120.0, 0.0), (120.0, 0.0)]},
                {"role": "secondary", "label": "Intersection Side Road", "points": [(0.0, -100.0), (0.0, 0.0)]},
            ],
        }
    if kind == "cross_intersection":
        return {
            "kind": kind,
            "alignments": [
                {"role": "primary", "label": "Cross Main Road", "points": [(-120.0, 0.0), (120.0, 0.0)]},
                {"role": "secondary", "label": "Cross Road", "points": [(0.0, -120.0), (0.0, 120.0)]},
            ],
        }
    if kind == "y_intersection":
        return {
            "kind": kind,
            "alignments": [
                {"role": "primary", "label": "Y Main Approach", "points": [(0.0, -120.0), (0.0, 0.0)]},
                {"role": "secondary", "label": "Y Branch Road", "points": [(0.0, 0.0), (90.0, 90.0)]},
            ],
        }
    raise ValueError(f"Unsupported starter intersection kind: {intersection_kind}")


def create_starter_intersection_sources(document, intersection_kind: str, *, project=None) -> list[str]:
    """Create editable starter source objects for one intersection type."""

    if App is None:
        raise RuntimeError("FreeCAD is required to create starter intersection sources.")
    doc = document or getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available.")
    prj = project or find_project(doc)
    specs = starter_intersection_source_specs(intersection_kind)
    created: list[str] = []
    assembly_ref, template_ref = _ensure_starter_assembly_for_intersections(doc, project=prj, created=created)
    for index, alignment_spec in enumerate(list(specs.get("alignments", []) or []), start=1):
        role = str(alignment_spec.get("role", "") or f"road-{index}")
        label = str(alignment_spec.get("label", "") or f"Intersection Road {index}")
        points = [(float(x), float(y)) for x, y in list(alignment_spec.get("points", []) or [])]
        alignment_id = _unique_alignment_id(doc, f"alignment:intersection-{role}")
        alignment = _create_alignment_source_from_points(
            doc,
            label=label,
            alignment_id=alignment_id,
            points=points,
            project=prj,
        )
        created.append(f"Alignment: {alignment.Label} | {alignment.AlignmentId}")
        profile = create_sample_v1_profile(
            doc,
            project=prj,
            alignment=alignment,
            label=f"{label} FG Profile",
            create_alignment_if_missing=False,
        )
        _update_profile_to_alignment_length(profile, _polyline_length(points))
        created.append(f"Profile: {profile.Label} | {profile.ProfileId}")
        stationing = create_v1_stationing(
            doc,
            project=prj,
            alignment=alignment,
            interval=20.0,
            label=f"{label} Stations",
        )
        created.append(f"Stations: {stationing.Label} | {stationing.StationingId}")
        region = create_or_update_v1_region_model_object(
            doc,
            project=prj,
            region_model=_starter_region_model_for_alignment(
                alignment_id=str(getattr(alignment, "AlignmentId", "") or ""),
                intersection_kind=intersection_kind,
                role=role,
                length=_polyline_length(points),
                project_id=_project_id(prj),
                assembly_ref=assembly_ref,
                template_ref=template_ref,
            ),
            object_name=f"V1IntersectionRegionModel_{_safe_name(role)}",
            label=f"{label} Regions",
        )
        created.append(f"Regions: {region.Label} | {region.RegionModelId}")
    try:
        doc.recompute()
    except Exception:
        pass
    centerline_status = _create_starter_centerline3d_preview(doc, project=prj)
    if centerline_status:
        created.append(centerline_status)
    return created


def _create_starter_centerline3d_preview(document, *, project=None) -> str:
    try:
        from .cmd_centerline3d import build_document_centerline3d_result, show_v1_centerline3d_preview_object

        result = build_document_centerline3d_result(document)
        obj = show_v1_centerline3d_preview_object(
            document,
            result=result,
            project=project,
            show_station_markers=False,
            display_mode="smooth_curve",
        )
        alignment_count = len(
            {
                str(getattr(row, "source_alignment_ref", "") or "")
                for row in list(getattr(result, "point_rows", ()) or ())
                if str(getattr(row, "source_alignment_ref", "") or "")
            }
        )
        return (
            f"3D Centerline: {str(getattr(obj, 'Label', '') or getattr(obj, 'Name', '') or '3D Centerline')} "
            f"| {str(getattr(result, 'centerline3d_result_id', '') or 'centerline3d:main')} "
            f"| alignments={alignment_count} | points={int(getattr(result, 'point_count', 0) or 0)}"
        )
    except Exception as exc:
        return f"3D Centerline: not generated | {exc}"


def run_v1_intersection_editor_command():
    """Open the v1 Intersection source editor shell."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    panel = V1IntersectionEditorTaskPanel(document=App.ActiveDocument)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


class V1IntersectionEditorTaskPanel:
    """First-slice Intersection source editor shell."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self._alignment_choices = list_v1_alignment_choices(self.document)
        self.form = self._build_ui()
        self._last_detection = None
        self._last_created_sources: list[str] = []
        self._last_applied_intersection = ""
        self._last_overlay = ""
        self._update_status()

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

    def selected_intersection_kind(self) -> str:
        """Return the internal intersection kind selected in the panel."""

        return intersection_kind_from_label(str(self._type_combo.currentText() or ""))

    def selected_source_mode(self) -> str:
        """Return the selected source mode label."""

        return str(self._source_mode_combo.currentText() or INTERSECTION_SOURCE_MODES[0])

    def selected_primary_alignment_ref(self) -> str:
        """Return the selected primary Alignment ref."""

        return _combo_data_or_text(self._primary_alignment_combo)

    def selected_secondary_alignment_ref(self) -> str:
        """Return the selected secondary Alignment ref."""

        return _combo_data_or_text(self._secondary_alignment_combo)

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("Parametric Road v1 - Intersections")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Intersections")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel(
            "Define at-grade junction source intent. Select the intersection type first; "
            "use Auto Detect, link control Regions, then review the junction overlay before Build Sections."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        workflow = QtWidgets.QLabel(NEXT_INTERSECTION_WORKFLOW_TEXT)
        workflow.setWordWrap(True)
        try:
            workflow.setStyleSheet("color: #78f0a0;")
        except Exception:
            pass
        layout.addWidget(workflow)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Intersection Type:"))
        self._type_combo = QtWidgets.QComboBox()
        self._type_combo.addItems(intersection_preset_labels())
        self._type_combo.currentIndexChanged.connect(self._update_status)
        preset_row.addWidget(self._type_combo)
        self._preset_button = QtWidgets.QPushButton("Preset Data")
        self._preset_button.clicked.connect(self._load_preset_data)
        preset_row.addWidget(self._preset_button)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        source_row = QtWidgets.QHBoxLayout()
        source_row.addWidget(QtWidgets.QLabel("Source Mode:"))
        self._source_mode_combo = QtWidgets.QComboBox()
        self._source_mode_combo.addItems(INTERSECTION_SOURCE_MODES)
        self._source_mode_combo.currentIndexChanged.connect(self._on_source_mode_changed)
        source_row.addWidget(self._source_mode_combo)
        self._create_sources_button = QtWidgets.QPushButton("Create Starter Sources")
        self._create_sources_button.clicked.connect(self._create_starter_sources)
        source_row.addWidget(self._create_sources_button)
        source_row.addStretch(1)
        layout.addLayout(source_row)

        self._alignment_note = QtWidgets.QLabel(
            "Existing Alignments mode will use selected primary and secondary Alignment sources. "
            "Starter Sources mode will create editable Alignment/Profile/Station/Region source drafts in a later phase."
        )
        self._alignment_note.setWordWrap(True)
        layout.addWidget(self._alignment_note)

        alignment_row = QtWidgets.QHBoxLayout()
        alignment_row.addWidget(QtWidgets.QLabel("Primary Alignment:"))
        self._primary_alignment_combo = QtWidgets.QComboBox()
        _populate_alignment_combo(self._primary_alignment_combo, self._alignment_choices)
        self._primary_alignment_combo.currentIndexChanged.connect(self._update_status)
        alignment_row.addWidget(self._primary_alignment_combo)
        alignment_row.addWidget(QtWidgets.QLabel("Secondary Alignment:"))
        self._secondary_alignment_combo = QtWidgets.QComboBox()
        _populate_alignment_combo(self._secondary_alignment_combo, self._alignment_choices)
        if len(self._alignment_choices) > 1:
            self._secondary_alignment_combo.setCurrentIndex(1)
        self._secondary_alignment_combo.currentIndexChanged.connect(self._update_status)
        alignment_row.addWidget(self._secondary_alignment_combo)
        layout.addLayout(alignment_row)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setMinimumHeight(130)
        layout.addWidget(self._status, 1)

        action_row = QtWidgets.QHBoxLayout()
        auto_detect_button = QtWidgets.QPushButton("Auto Detect")
        auto_detect_button.clicked.connect(self._auto_detect_intersection)
        action_row.addWidget(auto_detect_button)
        preview_button = QtWidgets.QPushButton("Preview Selection")
        preview_button.clicked.connect(self._show_review_overlay)
        action_row.addWidget(preview_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        overlay_action_row = QtWidgets.QHBoxLayout()
        hide_button = QtWidgets.QPushButton("Hide Overlay")
        hide_button.clicked.connect(self._hide_review_overlay)
        overlay_action_row.addWidget(hide_button)
        focus_button = QtWidgets.QPushButton("Focus Overlay")
        focus_button.clicked.connect(self._focus_review_overlay)
        overlay_action_row.addWidget(focus_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(self._apply_intersection_model)
        overlay_action_row.addWidget(apply_button)
        overlay_action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        overlay_action_row.addWidget(close_button)
        layout.addLayout(overlay_action_row)
        self._update_source_mode_controls()
        return widget

    def _load_preset_data(self) -> None:
        self._update_status(prefix="Preset Data loaded for panel draft only.")

    def _on_source_mode_changed(self) -> None:
        self._update_source_mode_controls()
        self._update_status()

    def _update_source_mode_controls(self) -> None:
        show_create = self.selected_source_mode() == "Create Starter Sources"
        try:
            self._create_sources_button.setVisible(show_create)
        except Exception:
            pass

    def _auto_detect_intersection(self) -> None:
        errors = validate_existing_alignment_selection(
            self.selected_primary_alignment_ref(),
            self.selected_secondary_alignment_ref(),
        )
        if errors:
            self._last_detection = None
            self._update_status(prefix="Auto Detect blocked by Alignment selection errors.")
            return
        primary = alignment_model_by_ref(self.document, self.selected_primary_alignment_ref())
        secondary = alignment_model_by_ref(self.document, self.selected_secondary_alignment_ref())
        if primary is None or secondary is None:
            self._last_detection = None
            self._update_status(prefix="Auto Detect failed: selected Alignment source could not be loaded.")
            return
        self._last_detection = AlignmentIntersectionDetectionService().detect(primary, secondary)
        self._update_status(prefix="Auto Detect completed.")

    def _create_starter_sources(self) -> None:
        if self.selected_source_mode() != "Create Starter Sources":
            self._update_status(prefix="Switch Source Mode to Create Starter Sources before creating source drafts.")
            return
        try:
            self._last_created_sources = create_starter_intersection_sources(
                self.document,
                self.selected_intersection_kind(),
            )
            self._alignment_choices = list_v1_alignment_choices(self.document)
            _populate_alignment_combo(self._primary_alignment_combo, self._alignment_choices)
            _populate_alignment_combo(self._secondary_alignment_combo, self._alignment_choices)
            if len(self._alignment_choices) > 1:
                self._secondary_alignment_combo.setCurrentIndex(1)
            self._update_status(prefix="Starter Sources created.")
        except Exception as exc:
            self._last_created_sources = []
            self._update_status(prefix=f"Starter Sources were not created: {exc}")

    def _apply_intersection_model(self) -> None:
        kind = self.selected_intersection_kind()
        primary_ref = self.selected_primary_alignment_ref()
        secondary_ref = self.selected_secondary_alignment_ref()
        errors = validate_existing_alignment_selection(primary_ref, secondary_ref)
        if errors:
            self._last_applied_intersection = ""
            message = "Intersection was not applied because Alignment selection has errors.\n" + "\n".join(f"- {error}" for error in errors)
            self._update_status(prefix="Apply blocked by Alignment selection errors.")
            _show_message(self.form, "Intersections", message)
            return
        control_regions = list_intersection_control_region_choices(self.document, intersection_ref_for_kind(kind))
        if not control_regions:
            self._last_applied_intersection = ""
            message = "Intersection was not applied.\nNo intersection-tagged control Regions were found."
            self._update_status(prefix="Apply blocked: no intersection-tagged control Regions were found.")
            _show_message(self.form, "Intersections", message)
            return
        try:
            model = build_intersection_model_from_sources(
                intersection_kind=kind,
                source_mode=self.selected_source_mode(),
                primary_alignment_ref=primary_ref,
                secondary_alignment_ref=secondary_ref,
                control_region_choices=control_regions,
                detection_result=self._last_detection,
                project_id=_project_id(find_project(self.document)),
            )
            obj = create_or_update_v1_intersection_model_object(
                self.document,
                intersection_model=model,
                project=find_project(self.document),
                label="Intersections",
            )
            try:
                self.document.recompute()
            except Exception:
                pass
            self._last_applied_intersection = f"{obj.Label} | {obj.IntersectionModelId}"
            self._update_status(prefix="IntersectionModel applied.")
            _show_message(
                self.form,
                "Intersections",
                (
                    "Intersection has been applied.\n"
                    f"Object: {obj.Label}\n"
                    f"IntersectionModel: {obj.IntersectionModelId}\n"
                    f"Control Regions: {len(control_regions)}"
                ),
            )
        except Exception as exc:
            self._last_applied_intersection = ""
            self._update_status(prefix=f"Apply failed: {exc}")
            _show_message(self.form, "Intersections", f"Intersection was not applied.\n{exc}")

    def _show_review_overlay(self) -> None:
        kind = self.selected_intersection_kind()
        control_regions = list_intersection_control_region_choices(self.document, intersection_ref_for_kind(kind))
        if not control_regions:
            self._last_overlay = ""
            self._update_status(prefix="Preview blocked: no intersection-tagged control Regions were found.")
            return
        try:
            obj = show_intersection_review_overlay(
                self.document,
                intersection_kind=kind,
                primary_alignment_ref=self.selected_primary_alignment_ref(),
                secondary_alignment_ref=self.selected_secondary_alignment_ref(),
                control_region_choices=control_regions,
                detection_result=self._last_detection,
                project=find_project(self.document),
            )
            self._last_overlay = f"{obj.Label} | {obj.Name}"
            if Gui is not None:
                try:
                    Gui.Selection.clearSelection()
                    Gui.Selection.addSelection(obj)
                except Exception:
                    pass
            self._update_status(prefix="Intersection review overlay shown.")
        except Exception as exc:
            self._last_overlay = ""
            self._update_status(prefix=f"Preview failed: {exc}")

    def _hide_review_overlay(self) -> None:
        obj = set_intersection_review_overlay_visible(self.document, False)
        self._update_status(prefix="Intersection review overlay hidden." if obj is not None else "No Intersection review overlay exists.")

    def _focus_review_overlay(self) -> None:
        obj = set_intersection_review_overlay_visible(self.document, True)
        if obj is None:
            self._update_status(prefix="No Intersection review overlay exists.")
            return
        if Gui is not None:
            try:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(obj)
                Gui.SendMsgToActiveView("ViewSelection")
            except Exception:
                pass
        self._last_overlay = f"{obj.Label} | {obj.Name}"
        self._update_status(prefix="Intersection review overlay focused.")

    def _update_status(self, *args, prefix: str = "") -> None:
        del args
        kind = self.selected_intersection_kind() if hasattr(self, "_type_combo") else ""
        label = str(self._type_combo.currentText() or "") if hasattr(self, "_type_combo") else ""
        source_mode = self.selected_source_mode() if hasattr(self, "_source_mode_combo") else ""
        primary_ref = self.selected_primary_alignment_ref() if hasattr(self, "_primary_alignment_combo") else ""
        secondary_ref = self.selected_secondary_alignment_ref() if hasattr(self, "_secondary_alignment_combo") else ""
        alignment_errors = (
            validate_existing_alignment_selection(primary_ref, secondary_ref)
            if source_mode == "Use Existing Alignments"
            else []
        )
        detection_lines = _format_detection_lines(self._last_detection) if hasattr(self, "_last_detection") else []
        created_lines = list(getattr(self, "_last_created_sources", []) or [])
        intersection_ref = intersection_ref_for_kind(kind)
        control_regions = list_intersection_control_region_choices(self.document, intersection_ref)
        applied_line = str(getattr(self, "_last_applied_intersection", "") or "")
        overlay_line = str(getattr(self, "_last_overlay", "") or "")
        lines = []
        if prefix:
            lines.append(prefix)
            lines.append("")
        lines.extend(
            [
                "Intersections shell is ready.",
                f"Selected Type: {label} ({kind or 'unresolved'})",
                f"Source Mode: {source_mode}",
                f"Primary Alignment: {primary_ref or '-'}",
                f"Secondary Alignment: {secondary_ref or '-'}",
                "",
                f"Validation: {'ok' if not alignment_errors else 'error'}",
                *[f"- {error}" for error in alignment_errors],
                "",
                "Auto Detect:",
                *(detection_lines or ["- Not run."]),
                "",
                f"Control Regions ({intersection_ref}):",
                *(
                    [
                        f"- {row.get('label', '-')}"
                        for row in control_regions
                    ]
                    if control_regions
                    else ["- No linked control Regions found."]
                ),
                "",
                "Starter Sources:",
                *([f"- {line}" for line in created_lines] if created_lines else ["- Not created."]),
                "",
                "Applied IntersectionModel:",
                f"- {applied_line or 'Not applied.'}",
                "",
                "3D Review Overlay:",
                f"- {overlay_line or 'Not shown.'}",
                "",
                "Next planned actions:",
                "- review the 3D overlay for point, legs, and control spans",
                "- rebuild Sections so intersection context can be carried downstream",
                "- check Build Parametric diagnostics for intersection-controlled Regions",
            ]
        )
        self._status.setPlainText("\n".join(lines))


class CmdV1IntersectionEditor:
    """Open the v1 Intersection source editor shell."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("intersections.svg"),
            "MenuText": "Intersections",
            "ToolTip": "Define v1 at-grade intersection type, source mode, and junction source intent",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_intersection_editor_command()


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand(INTERSECTION_COMMAND_ID, CmdV1IntersectionEditor())


def _populate_alignment_combo(combo, choices: list[tuple[str, str]]) -> None:
    combo.clear()
    combo.addItem("", "")
    for alignment_id, label in choices:
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
        f"- Status: {result.status}",
        f"- XY: {result.x:.3f}, {result.y:.3f}",
        f"- Primary STA: {result.primary_station:.3f}",
        f"- Secondary STA: {result.secondary_station:.3f}",
        f"- Distance: {result.distance:.3f}",
        f"- Notes: {result.notes}",
    ]


def _control_region_ref(region_model_ref: str, region_id: str) -> str:
    model_ref = str(region_model_ref or "").strip()
    row_ref = str(region_id or "").strip()
    if model_ref and row_ref:
        return f"{model_ref}/{row_ref}"
    return row_ref or model_ref


def _control_area_rows_from_region_choices(
    intersection_id: str,
    control_region_choices: list[dict[str, object]],
) -> list[IntersectionControlArea]:
    by_alignment: dict[str, list[dict[str, object]]] = {}
    for row in control_region_choices:
        alignment_ref = str(row.get("alignment_ref", "") or "")
        by_alignment.setdefault(alignment_ref, []).append(row)
    rows: list[IntersectionControlArea] = []
    for index, (alignment_ref, region_rows) in enumerate(sorted(by_alignment.items()), start=1):
        rows.append(
            IntersectionControlArea(
                control_area_id=f"{intersection_id}:control-area:{index:02d}",
                intersection_id=intersection_id,
                alignment_ref=alignment_ref,
                station_ranges=[
                    (
                        float(row.get("station_start", 0.0) or 0.0),
                        float(row.get("station_end", 0.0) or 0.0),
                    )
                    for row in region_rows
                ],
                influence_ranges=[
                    (
                        float(row.get("station_start", 0.0) or 0.0),
                        float(row.get("station_end", 0.0) or 0.0),
                    )
                    for row in region_rows
                ],
                control_region_refs=[str(row.get("control_region_ref", "") or "") for row in region_rows],
                notes="Linked from Region rows tagged with intersection_ref.",
            )
        )
    return rows


def _leg_rows_from_region_choices(
    intersection_id: str,
    control_region_choices: list[dict[str, object]],
) -> list[IntersectionLegRow]:
    rows: list[IntersectionLegRow] = []
    for index, row in enumerate(control_region_choices, start=1):
        start = float(row.get("station_start", 0.0) or 0.0)
        end = float(row.get("station_end", 0.0) or 0.0)
        region_id = str(row.get("region_id", "") or "")
        alignment_ref = str(row.get("alignment_ref", "") or "")
        rows.append(
            IntersectionLegRow(
                leg_id=f"{intersection_id}:leg:{index:02d}",
                intersection_id=intersection_id,
                leg_role=_leg_role_from_region_id(region_id, index),
                alignment_ref=alignment_ref,
                region_ref=str(row.get("control_region_ref", "") or ""),
                approach_station_start=min(start, end),
                approach_station_end=max(start, end),
                priority=index,
                notes="Linked from intersection control Region.",
            )
        )
    return rows


def _leg_role_from_region_id(region_id: str, index: int) -> str:
    text = str(region_id or "").lower()
    if "primary" in text:
        return "primary_control"
    if "secondary" in text or "side" in text:
        return "secondary_control"
    return f"control_region_{index:02d}"


def _source_mode_id(source_mode: str) -> str:
    text = str(source_mode or "").strip().lower()
    if "starter" in text:
        return "create_starter_sources"
    return "use_existing_alignments"


def _intersection_review_point(detection_result):
    if detection_result is None or App is None:
        return None
    try:
        return App.Vector(
            float(getattr(detection_result, "x", 0.0) or 0.0),
            float(getattr(detection_result, "y", 0.0) or 0.0),
            0.0,
        )
    except Exception:
        return None


def _intersection_point_marker_shapes(point, *, radius: float) -> list[object]:
    if App is None or Part is None or point is None:
        return []
    shapes: list[object] = []
    try:
        shapes.append(Part.makeSphere(max(float(radius) * 0.55, 0.5), point))
    except Exception:
        pass
    axes = (
        (App.Vector(radius, 0.0, 0.0), App.Vector(-radius, 0.0, 0.0)),
        (App.Vector(0.0, radius, 0.0), App.Vector(0.0, -radius, 0.0)),
        (App.Vector(0.0, 0.0, radius), App.Vector(0.0, 0.0, -radius)),
    )
    for positive, negative in axes:
        try:
            shapes.append(Part.makeLine(point + negative, point + positive))
        except Exception:
            pass
    return shapes


def _alignment_station_span_points(alignment_model, station_start: float, station_end: float) -> list[object]:
    if alignment_model is None or App is None:
        return []
    start = min(float(station_start), float(station_end))
    end = max(float(station_start), float(station_end))
    samples = [start, end]
    if end > start:
        step = max((end - start) / 6.0, 1.0)
        value = start + step
        while value < end - 1.0e-9:
            samples.append(value)
            value += step
    samples = sorted(set(round(value, 6) for value in samples))
    return [point for point in (_alignment_point_at_station(alignment_model, station) for station in samples) if point is not None]


def _alignment_point_at_station(alignment_model, station: float):
    if alignment_model is None or App is None:
        return None
    target = float(station)
    for element in list(getattr(alignment_model, "geometry_sequence", []) or []):
        start = float(getattr(element, "station_start", 0.0) or 0.0)
        end = float(getattr(element, "station_end", start) or start)
        if target < min(start, end) - 1.0e-6 or target > max(start, end) + 1.0e-6:
            continue
        points = _alignment_element_points(element)
        if len(points) < 2:
            continue
        length = max(float(getattr(element, "length", 0.0) or 0.0), abs(end - start))
        local = 0.0 if length <= 1.0e-9 else max(0.0, min(length, target - start))
        return _point_on_polyline(points, local)
    points = []
    for element in list(getattr(alignment_model, "geometry_sequence", []) or []):
        points.extend(_alignment_element_points(element))
    if not points:
        return None
    return points[0] if target <= 0.0 else points[-1]


def _alignment_element_points(element) -> list[object]:
    payload = dict(getattr(element, "geometry_payload", {}) or {})
    x_values = list(payload.get("x_values", []) or [])
    y_values = list(payload.get("y_values", []) or [])
    points = []
    for x, y in zip(x_values, y_values):
        try:
            points.append(App.Vector(float(x), float(y), 0.0))
        except Exception:
            continue
    return points


def _point_on_polyline(points: list[object], distance: float):
    if not points:
        return None
    remaining = max(float(distance), 0.0)
    for first, second in zip(points[:-1], points[1:]):
        segment = second - first
        length = float(getattr(segment, "Length", 0.0) or 0.0)
        if length <= 1.0e-9:
            continue
        if remaining <= length:
            return first + segment.multiply(remaining / length)
        remaining -= length
    return points[-1]


def _style_intersection_review_overlay(obj, *, visible: bool) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = bool(visible)
            vobj.ShapeColor = (1.0, 0.72, 0.05)
            vobj.LineColor = (1.0, 0.72, 0.05)
            vobj.PointColor = (1.0, 0.72, 0.05)
            vobj.LineWidth = 7.0
            vobj.PointSize = 8.0
            vobj.Transparency = 0
    except Exception:
        pass


def _set_preview_property(obj, name: str, value: str) -> None:
    if obj is None:
        return
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "Review", name)
        setattr(obj, name, str(value))
    except Exception:
        pass


def _set_preview_string_list_property(obj, name: str, values: list[str]) -> None:
    if obj is None:
        return
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyStringList", name, "Review", name)
        setattr(obj, name, [str(value) for value in list(values or [])])
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    if obj is None:
        return
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyInteger", name, "Review", name)
        setattr(obj, name, int(value))
    except Exception:
        pass


def _unique_text_values(values: list[object]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _create_alignment_source_from_points(document, *, label: str, alignment_id: str, points: list[tuple[float, float]], project=None):
    try:
        obj = document.addObject("Part::FeaturePython", "V1Alignment")
    except Exception:
        obj = document.addObject("App::FeaturePython", "V1Alignment")
    V1AlignmentObject(obj)
    try:
        ViewProviderV1Alignment(obj.ViewObject)
    except Exception:
        pass
    length = _polyline_length(points)
    obj.Label = label
    obj.ProjectId = _project_id(project)
    obj.AlignmentId = alignment_id
    obj.AlignmentKind = "road_centerline"
    obj.ElementIds = [f"{alignment_id}:starter:1"]
    obj.ElementKinds = ["tangent" if len(points) == 2 else "sampled_curve"]
    obj.StationStarts = [0.0]
    obj.StationEnds = [length]
    obj.ElementLengths = [length]
    obj.XValueRows = [",".join(f"{x:.3f}" for x, _y in points)]
    obj.YValueRows = [",".join(f"{y:.3f}" for _x, y in points)]
    obj.TotalLength = length
    obj.CriteriaStatus = "starter"
    obj.CriteriaMessages = ["Created by Intersections starter source workflow."]
    try:
        obj.touch()
    except Exception:
        pass
    if project is not None:
        try:
            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def _unique_alignment_id(document, base_alignment_id: str) -> str:
    base = str(base_alignment_id or "alignment:intersection").strip() or "alignment:intersection"
    existing = {
        str(getattr(model, "alignment_id", "") or "")
        for model in (to_alignment_model(obj) for obj in list(getattr(document, "Objects", []) or []))
        if model is not None
    }
    if base not in existing:
        return base
    index = 2
    while f"{base}-{index}" in existing:
        index += 1
    return f"{base}-{index}"


def _update_profile_to_alignment_length(profile, length: float) -> None:
    profile.ControlPointIds = [
        f"{profile.ProfileId}:pvi:1",
        f"{profile.ProfileId}:pvi:2",
        f"{profile.ProfileId}:pvi:3",
    ]
    profile.ControlStations = [0.0, max(float(length) * 0.5, 0.0), max(float(length), 0.0)]
    profile.ControlElevations = [60.0, 60.8, 60.2]
    profile.ControlKinds = ["grade_break", "pvi", "grade_break"]
    profile.VerticalCurveIds = [f"{profile.ProfileId}:curve:1"]
    profile.VerticalCurveKinds = ["parabolic_vertical_curve"]
    mid = max(float(length) * 0.5, 0.0)
    curve_half = min(15.0, max(float(length) * 0.15, 0.0))
    profile.VerticalCurveStationStarts = [max(mid - curve_half, 0.0)]
    profile.VerticalCurveStationEnds = [min(mid + curve_half, max(float(length), 0.0))]
    profile.VerticalCurveLengths = [max(profile.VerticalCurveStationEnds[0] - profile.VerticalCurveStationStarts[0], 0.0)]
    profile.VerticalCurveParameters = [-0.02]
    try:
        profile.touch()
    except Exception:
        pass


def _starter_region_model_for_alignment(
    *,
    alignment_id: str,
    intersection_kind: str,
    role: str,
    length: float,
    project_id: str,
    assembly_ref: str = "",
    template_ref: str = "",
) -> RegionModel:
    control_start = max(float(length) * 0.4, 0.0)
    control_end = min(float(length) * 0.6, float(length))
    if role == "secondary" and intersection_kind == "t_intersection":
        control_start = 0.0
        control_end = min(float(length) * 0.35, float(length))
    rows: list[RegionRow] = []
    if control_start > 1.0e-9:
        rows.append(
            RegionRow(
                region_id=f"region:{role}-approach",
                region_index=len(rows) + 1,
                station_start=0.0,
                station_end=control_start,
                assembly_ref=assembly_ref,
                template_ref=template_ref,
                priority=10,
                notes="Starter normal approach Region created by Intersections.",
            )
        )
    if control_end > control_start + 1.0e-9:
        rows.append(
            RegionRow(
                region_id=f"region:{role}-intersection",
                region_index=len(rows) + 1,
                station_start=control_start,
                station_end=control_end,
                assembly_ref=assembly_ref,
                template_ref=template_ref,
                priority=80,
                intersection_ref=f"intersection:starter-{intersection_kind}",
                notes="Starter intersection control Region created by Intersections.",
            )
        )
    if float(length) > control_end + 1.0e-9:
        rows.append(
            RegionRow(
                region_id=f"region:{role}-departure",
                region_index=len(rows) + 1,
                station_start=control_end,
                station_end=float(length),
                assembly_ref=assembly_ref,
                template_ref=template_ref,
                priority=10,
                notes="Starter normal departure Region created by Intersections.",
            )
        )
    return RegionModel(
        schema_version=1,
        project_id=project_id,
        region_model_id=f"regions:intersection-{role}",
        alignment_id=alignment_id,
        label=f"Intersection {role.title()} Regions",
        region_rows=rows,
    )


def _ensure_starter_assembly_for_intersections(document, *, project=None, created: list[str] | None = None) -> tuple[str, str]:
    """Ensure starter intersection sources have an Assembly source for Build Sections."""

    existing_obj = find_v1_assembly_model(document)
    existing_model = to_assembly_model(existing_obj) if existing_obj is not None else None
    if existing_model is not None:
        assembly_id = str(getattr(existing_model, "assembly_id", "") or "").strip()
        template_id = str(getattr(existing_model, "active_template_id", "") or "").strip()
        if assembly_id:
            return assembly_id, template_id
    try:
        from .cmd_assembly_editor import apply_v1_assembly_model, starter_assembly_model_from_document

        model = starter_assembly_model_from_document(document=document, project=project)
        obj = apply_v1_assembly_model(
            document=document,
            project=project,
            assembly_model=model,
            object_name="V1IntersectionStarterAssembly",
        )
        if created is not None:
            created.append(f"Assembly: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')} | {model.assembly_id}")
        return str(getattr(model, "assembly_id", "") or ""), str(getattr(model, "active_template_id", "") or "")
    except Exception:
        return "", ""


def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(points, points[1:]))


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value or "source")).strip("_") or "source"


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass

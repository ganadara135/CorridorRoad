"""Structure editor command for CorridorRoad v1."""

from __future__ import annotations

import math

try:
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None
    Part = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ..models.source.structure_model import (
    BridgeGeometrySpec,
    CulvertGeometrySpec,
    RetainingWallGeometrySpec,
    StructureConnectionPoint,
    StructureGeometrySpec,
    StructureInfluenceZone,
    StructureInteractionRule,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..objects.obj_exchange_package import find_v1_exchange_package
from ..objects.obj_stationing import find_v1_stationing
from ..objects.obj_structure import (
    create_or_update_v1_structure_model_object,
    find_v1_structure_model,
    to_structure_model,
    validate_structure_model,
)
from ..services.evaluation import AlignmentEvaluationService


STRUCTURE_GEOMETRY_SPEC_REF_ROLE = QtCore.Qt.UserRole
try:
    STRUCTURE_GEOMETRY_REF_ROLE = int(QtCore.Qt.UserRole) + 1
    STRUCTURE_GEOMETRY_SOURCE_ROLE = int(QtCore.Qt.UserRole) + 2
    STRUCTURE_NATIVE_TYPE_ROLE = int(QtCore.Qt.UserRole) + 3
except Exception:  # pragma: no cover - PySide enum compatibility fallback.
    STRUCTURE_GEOMETRY_REF_ROLE = 257
    STRUCTURE_GEOMETRY_SOURCE_ROLE = 258
    STRUCTURE_NATIVE_TYPE_ROLE = 259

STRUCTURE_KIND_CHOICES = ["bridge", "culvert", "retaining_wall", "wall", "utility", "custom"]
STRUCTURE_ROLE_CHOICES = ["active", "interface", "clearance_control", "split_zone", "reference"]
LENGTH_MODE_CHOICES = ["station_range", "explicit_length", "reference_geometry"]
VERTICAL_POSITION_MODE_CHOICES = ["profile_frame", "absolute_elevation", "terrain_relative", "structure_reference"]
GEOMETRY_SOURCE_CHOICES = ["native", "external_ref"]
NATIVE_TYPE_CHOICES = [
    "",
    "box_culvert",
    "pipe_culvert",
    "bridge_deck",
    "retaining_wall",
    "headwall",
    "inlet",
    "outlet",
]


STRUCTURE_PRESETS = {
    "Empty": {
        "note": "Create a blank v1 StructureModel source object.",
        "rows": [],
    },
    "Bridge Segment": {
        "note": "One bridge structure covering the middle of the available station range.",
        "rows": [
            {
                "id": "structure:bridge-01",
                "kind": "bridge",
                "role": "interface",
                "start": 0.35,
                "end": 0.65,
                "offset": 0.0,
                "geometry": "",
                "spec": "geometry-spec:bridge-01",
                "native_type": "bridge_deck",
                "width": 10.0,
                "height": 1.2,
                "shape": "deck_slab",
                "material": "concrete",
                "bridge": {
                    "deck_width": 10.0,
                    "deck_thickness": 1.2,
                    "girder_depth": 1.8,
                    "barrier_height": 1.1,
                    "clearance_height": 5.0,
                    "approach_slab_length": 6.0,
                    "bearing_elevation_mode": "profile_frame",
                },
                "notes": "Bridge deck/source handoff.",
            }
        ],
    },
    "Culvert Crossing": {
        "note": "One culvert influence band around the center station.",
        "rows": [
            {
                "id": "structure:culvert-01",
                "kind": "culvert",
                "role": "clearance_control",
                "start": 0.45,
                "end": 0.55,
                "offset": 0.0,
                "geometry": "",
                "spec": "geometry-spec:culvert-01",
                "native_type": "box_culvert",
                "width": 3.0,
                "height": 2.0,
                "shape": "box",
                "material": "concrete",
                "culvert": {
                    "barrel_shape": "box",
                    "barrel_count": 1,
                    "span": 3.0,
                    "rise": 2.0,
                    "wall_thickness": 0.3,
                    "headwall_type": "straight",
                    "wingwall_type": "none",
                },
                "notes": "Culvert section interaction zone.",
            }
        ],
    },
    "Drainage Structures": {
        "note": "Drainage-related structures for connecting Drainage Element Structure Ref rows.",
        "rows": [
            {
                "id": "structure:culvert-01",
                "kind": "culvert",
                "role": "clearance_control",
                "start": 0.45,
                "end": 0.55,
                "offset": 0.0,
                "geometry": "",
                "spec": "geometry-spec:culvert-01",
                "native_type": "box_culvert",
                "width": 3.0,
                "height": 2.0,
                "shape": "box",
                "material": "concrete",
                "culvert": {
                    "barrel_shape": "box",
                    "barrel_count": 1,
                    "span": 3.0,
                    "rise": 2.0,
                    "wall_thickness": 0.3,
                    "headwall_type": "straight",
                    "wingwall_type": "short",
                },
                "notes": "Cross-drain culvert referenced by Drainage flow routes.",
                "connection_points": [
                    {"role": "upstream", "at": "start", "direction": "upstream"},
                    {"role": "downstream", "at": "end", "direction": "downstream"},
                ],
            },
            {
                "id": "structure:inlet-01",
                "kind": "utility",
                "role": "reference",
                "start": 0.30,
                "end": 0.32,
                "offset": -4.5,
                "geometry": "",
                "spec": "geometry-spec:inlet-01",
                "native_type": "inlet",
                "width": 1.0,
                "height": 1.0,
                "shape": "inlet_box",
                "material": "concrete",
                "notes": "Drainage inlet/catch-basin reference structure.",
                "connection_points": [
                    {"role": "inlet", "at": "start", "shape": "inlet", "direction": "in"},
                    {
                        "role": "pipe_out",
                        "id": "connection:inlet-01:pipe-out",
                        "at": "end",
                        "diameter": 0.6,
                        "shape": "circular",
                        "direction": "out",
                    },
                ],
            },
            {
                "id": "structure:outlet-01",
                "kind": "utility",
                "role": "reference",
                "start": 0.88,
                "end": 0.90,
                "offset": -6.0,
                "geometry": "",
                "spec": "geometry-spec:outlet-01",
                "native_type": "outlet",
                "width": 1.5,
                "height": 1.2,
                "shape": "outlet_headwall",
                "material": "concrete",
                "notes": "Drainage outlet/headwall reference structure.",
                "connection_points": [
                    {
                        "role": "pipe_in",
                        "id": "connection:outlet-01:pipe-in",
                        "at": "start",
                        "diameter": 0.8,
                        "shape": "circular",
                        "direction": "in",
                    },
                    {"role": "discharge", "at": "end", "shape": "outlet", "direction": "out"},
                ],
            },
        ],
    },
    "Retaining Wall": {
        "note": "One retaining wall zone on the right side of the corridor.",
        "rows": [
            {
                "id": "structure:retaining-wall-01",
                "kind": "retaining_wall",
                "role": "interface",
                "start": 0.20,
                "end": 0.80,
                "offset": 7.5,
                "geometry": "",
                "spec": "geometry-spec:retaining-wall-01",
                "native_type": "retaining_wall",
                "width": 0.9,
                "height": 3.0,
                "shape": "wall",
                "material": "concrete",
                "retaining_wall": {
                    "wall_height": 3.0,
                    "wall_thickness": 0.9,
                    "footing_width": 2.0,
                    "footing_thickness": 0.45,
                    "retained_side": "right",
                    "top_elevation_mode": "profile_frame",
                    "bottom_elevation_mode": "terrain_relative",
                    "coping_height": 0.2,
                },
                "notes": "Retaining wall source handoff.",
            }
        ],
    },
}


def structure_preset_names() -> list[str]:
    """Return available v1 Structure preset names."""

    return list(STRUCTURE_PRESETS.keys())


def starter_structure_model_from_document(document=None, *, project=None, alignment=None) -> StructureModel:
    """Build one non-destructive starter StructureModel."""

    return structure_preset_model_from_document("Bridge Segment", document=document, project=project, alignment=alignment)


def structure_preset_model_from_document(
    preset_name: str,
    document=None,
    *,
    project=None,
    alignment=None,
) -> StructureModel:
    """Build a non-destructive StructureModel from a named preset."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    preset = STRUCTURE_PRESETS.get(str(preset_name or "").strip())
    if preset is None:
        raise ValueError(f"Unknown Structure preset: {preset_name}")
    prj = project or find_project(doc)
    alignment_obj = alignment or find_v1_alignment(doc)
    station_start, station_end = _document_station_range(doc, alignment_obj)
    alignment_id = str(getattr(alignment_obj, "AlignmentId", "") or "")
    structure_rows = _preset_structure_rows(
        preset,
        station_start=station_start,
        station_end=station_end,
        alignment_id=alignment_id,
    )
    geometry_spec_rows = _preset_geometry_spec_rows(preset)
    culvert_geometry_spec_rows = _preset_culvert_geometry_spec_rows(preset)
    return StructureModel(
        schema_version=1,
        project_id=_project_id(prj),
        structure_model_id="structures:main",
        alignment_id=alignment_id,
        label="Structures",
        structure_rows=structure_rows,
        geometry_spec_rows=geometry_spec_rows,
        bridge_geometry_spec_rows=_preset_bridge_geometry_spec_rows(preset),
        culvert_geometry_spec_rows=culvert_geometry_spec_rows,
        retaining_wall_geometry_spec_rows=_preset_retaining_wall_geometry_spec_rows(preset),
        connection_point_rows=_preset_connection_point_rows(
            preset,
            structure_rows=structure_rows,
            geometry_spec_rows=geometry_spec_rows,
            culvert_geometry_spec_rows=culvert_geometry_spec_rows,
        ),
        interaction_rule_rows=[],
        influence_zone_rows=[],
    )


def apply_v1_structure_model(
    *,
    document=None,
    project=None,
    structure_model: StructureModel,
):
    """Validate and persist a v1 StructureModel source object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    if prj is None:
        try:
            prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
        except Exception:
            prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        prj.Label = "Parametric Road Project"
    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    obj = create_or_update_v1_structure_model_object(
        document=doc,
        project=prj,
        structure_model=structure_model,
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def show_v1_structure_preview_object(document, structure_model: StructureModel, *, project=None):
    """Create or update a 3D preview object from v1 StructureModel source rows."""

    if document is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Structure preview.")
    rows = list(getattr(structure_model, "structure_rows", []) or [])
    if not rows:
        raise ValueError("Structure preview requires at least one Structure row.")
    shape = _make_structure_preview_shape(document, structure_model)
    obj = document.getObject("V1StructureShowPreview")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1StructureShowPreview")
    obj.Label = "Structures 3D Preview"
    obj.Shape = shape
    _set_preview_string_property(obj, "CRRecordKind", "v1_structure_show_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1StructureShowPreview")
    _set_preview_string_property(obj, "StructureModelId", str(getattr(structure_model, "structure_model_id", "") or ""))
    _set_preview_integer_property(obj, "StructureCount", len(rows))
    _set_preview_string_property(obj, "PreviewPathSource", _structure_preview_path_source_name(document))
    context = _structure_preview_context(structure_model)
    _set_preview_integer_property(obj, "GeometrySpecCount", len(context["geometry_specs"]))
    _set_preview_string_property(obj, "PreviewGeometrySource", "geometry_spec" if context["geometry_specs"] else "fallback")
    _set_preview_string_list_property(obj, "PreviewReviewNotes", _structure_preview_review_notes(structure_model, context))
    _style_structure_preview_object(obj)
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(document), obj)
    except Exception:
        pass
    try:
        document.recompute()
    except Exception:
        pass
    return obj


def show_v1_structure_connection_points_preview_object(
    document,
    structure_model: StructureModel,
    *,
    structure_ref: str = "",
    connection_point_ref: str = "",
    project=None,
):
    """Create or update a 3D review object for Structure connection points."""

    if document is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Structure connection point preview.")
    points = _filtered_connection_points(
        list(getattr(structure_model, "connection_point_rows", []) or []),
        structure_ref=structure_ref,
        connection_point_ref=connection_point_ref,
    )
    if not points:
        raise ValueError("Connection point preview requires at least one connection point row.")
    shapes = []
    for point in points:
        x, y, z = _connection_point_xyz(document, point)
        radius = _connection_point_marker_radius(point)
        shapes.append(Part.makeSphere(radius, App.Vector(float(x), float(y), float(z))))
    shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
    obj = document.getObject("V1StructureConnectionPointPreview")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1StructureConnectionPointPreview")
    obj.Label = "Structure Connection Points"
    obj.Shape = shape
    _set_preview_string_property(obj, "CRRecordKind", "v1_structure_connection_point_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1StructureConnectionPointPreview")
    _set_preview_string_property(obj, "StructureModelId", str(getattr(structure_model, "structure_model_id", "") or ""))
    _set_preview_string_property(obj, "StructureRef", str(structure_ref or ""))
    _set_preview_string_property(obj, "ConnectionPointRef", str(connection_point_ref or ""))
    _set_preview_integer_property(obj, "ConnectionPointCount", len(points))
    _set_preview_string_list_property(
        obj,
        "ConnectionPointIds",
        [str(getattr(point, "connection_point_id", "") or "") for point in points],
    )
    _style_connection_point_preview_object(obj)
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(document), obj)
    except Exception:
        pass
    try:
        document.recompute()
    except Exception:
        pass
    return obj


def run_v1_structure_editor_command():
    """Open the v1 Structure editor panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    panel = V1StructureEditorTaskPanel(document=document)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_structure_model(document)


class V1StructureEditorTaskPanel:
    """Table-based v1 Structure source editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.structure_obj = find_v1_structure_model(self.document)
        self._geometry_spec_rows: list[StructureGeometrySpec] = []
        self._bridge_geometry_spec_rows: list[BridgeGeometrySpec] = []
        self._culvert_geometry_spec_rows: list[CulvertGeometrySpec] = []
        self._retaining_wall_geometry_spec_rows: list[RetainingWallGeometrySpec] = []
        self._connection_point_rows: list[StructureConnectionPoint] = []
        self._active_detail_structure_id = ""
        self._active_detail_spec_ref = ""
        self._loading_selected_detail = False
        self.form = self._build_ui()
        self._load_existing_rows()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._apply(close_after=True)

    def reject(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - Structures")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Structures")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel(
            "Define station-bounded v1 structure source rows. Apply stores source intent only; "
            "rebuild Applied Sections to reflect structure context in section results."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        self._preset_combo = QtWidgets.QComboBox()
        self._preset_combo.addItems(structure_preset_names())
        preset_row.addWidget(self._preset_combo)
        load_preset_button = QtWidgets.QPushButton("Load Preset")
        load_preset_button.clicked.connect(self._load_selected_preset)
        preset_row.addWidget(load_preset_button)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        self._preset_note = QtWidgets.QLabel("")
        self._preset_note.setWordWrap(True)
        layout.addWidget(self._preset_note)
        self._preset_combo.currentIndexChanged.connect(self._update_preset_note)

        self._table = QtWidgets.QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["Structure Id", "Kind", "Role", "Start STA", "End STA", "Offset", "Notes"]
        )
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        self._table.itemSelectionChanged.connect(self._load_selected_detail)
        self._table.cellDoubleClicked.connect(self._activate_structure_detail_row)
        try:
            self._table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._table, 1)

        edit_row = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Structure")
        add_button.clicked.connect(self._add_structure_row)
        edit_row.addWidget(add_button)
        delete_button = QtWidgets.QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_selected_rows)
        edit_row.addWidget(delete_button)
        sort_button = QtWidgets.QPushButton("Sort by Station")
        sort_button.clicked.connect(self._sort_rows)
        edit_row.addWidget(sort_button)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)

        self._geometry_table = QtWidgets.QTableWidget(0, 12)
        self._geometry_table.setHorizontalHeaderLabels(
            [
                "Spec Id",
                "Structure Ref",
                "Shape",
                "Width",
                "Height",
                "Length Mode",
                "Skew",
                "Vertical Mode",
                "Base Elev",
                "Top Elev",
                "Material",
                "Notes",
            ]
        )
        self._geometry_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._geometry_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._geometry_table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        try:
            self._geometry_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._geometry_table.setVisible(False)

        detail_group = QtWidgets.QGroupBox("Selected Structure Detail")
        detail_layout = QtWidgets.QVBoxLayout(detail_group)
        self._detail_summary = QtWidgets.QLabel("No structure row is selected.")
        detail_layout.addWidget(self._detail_summary)
        detail_form = QtWidgets.QFormLayout()
        self._geometry_source_combo = QtWidgets.QComboBox()
        self._geometry_source_combo.addItems(GEOMETRY_SOURCE_CHOICES)
        self._geometry_source_combo.setToolTip("Native creates a simple Parametric Road body. External Ref uses a referenced body plus explicit connection-point mapping.")
        self._geometry_source_combo.currentIndexChanged.connect(self._handle_geometry_source_changed)
        detail_form.addRow("Geometry Source", self._geometry_source_combo)
        self._native_type_combo = QtWidgets.QComboBox()
        self._native_type_combo.addItems(NATIVE_TYPE_CHOICES)
        self._native_type_combo.setToolTip("Simple native structure type used to drive practical dimensions and default connection points.")
        self._native_type_combo.currentIndexChanged.connect(self._handle_native_type_changed)
        detail_form.addRow("Native Type", self._native_type_combo)
        self._geometry_ref_field = QtWidgets.QLineEdit()
        self._geometry_ref_field.setToolTip("Optional external or detailed geometry reference. Native geometry dimensions are edited in this detail area.")
        self._geometry_ref_field.textEdited.connect(lambda _text: self._sync_selected_detail_to_row())
        detail_form.addRow("External Geometry Ref", self._geometry_ref_field)
        self._common_shape_label = QtWidgets.QLabel("Shape (auto)")
        self._common_shape_label.setToolTip("Auto-filled from Native Type. Edit only when a custom native shape key is needed.")
        self._common_shape_field = QtWidgets.QLineEdit()
        self._common_shape_field.setPlaceholderText("Auto from Native Type")
        self._common_shape_field.setToolTip(
            "Auto-filled from Native Type and used by generated structure geometry. "
            "Leave the default unless this structure needs a custom native shape key."
        )
        detail_form.addRow(self._common_shape_label, self._common_shape_field)
        self._common_width_field = QtWidgets.QLineEdit()
        detail_form.addRow("Width", self._common_width_field)
        self._common_height_field = QtWidgets.QLineEdit()
        detail_form.addRow("Height", self._common_height_field)
        self._common_vertical_mode_combo = QtWidgets.QComboBox()
        self._common_vertical_mode_combo.setEditable(True)
        self._common_vertical_mode_combo.addItems(VERTICAL_POSITION_MODE_CHOICES)
        detail_form.addRow("Vertical Mode", self._common_vertical_mode_combo)
        self._common_base_elev_field = QtWidgets.QLineEdit()
        detail_form.addRow("Base Elev", self._common_base_elev_field)
        self._common_top_elev_field = QtWidgets.QLineEdit()
        detail_form.addRow("Top Elev", self._common_top_elev_field)
        self._common_skew_field = QtWidgets.QLineEdit()
        detail_form.addRow("Skew", self._common_skew_field)
        self._common_material_field = QtWidgets.QLineEdit()
        detail_form.addRow("Material", self._common_material_field)
        self._common_notes_field = QtWidgets.QLineEdit()
        detail_form.addRow("Geometry Notes", self._common_notes_field)
        self._detail_labels = []
        self._detail_fields = []
        for _index in range(10):
            label = QtWidgets.QLabel("")
            field = QtWidgets.QLineEdit()
            detail_form.addRow(label, field)
            self._detail_labels.append(label)
            self._detail_fields.append(field)
        detail_layout.addLayout(detail_form)

        self._connection_label = QtWidgets.QLabel("Drainage Connection Points")
        self._connection_label.setToolTip("Stable source endpoints for Drainage pipe/channel connectivity.")
        detail_layout.addWidget(self._connection_label)
        self._connection_table = QtWidgets.QTableWidget(0, 12)
        self._connection_table.setHorizontalHeaderLabels(
            [
                "Point ID",
                "Role",
                "STA",
                "Offset",
                "Elev",
                "Invert",
                "Shape",
                "Width",
                "Height",
                "Diameter",
                "Direction",
                "Notes",
            ]
        )
        self._connection_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._connection_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._connection_table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        self._connection_table.cellDoubleClicked.connect(lambda row_index, _col: self._preview_connection_point_row(row_index))
        try:
            self._connection_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        detail_layout.addWidget(self._connection_table, 1)

        connection_action_row = QtWidgets.QHBoxLayout()
        add_point_button = QtWidgets.QPushButton("Add Point")
        add_point_button.clicked.connect(self._add_connection_point)
        connection_action_row.addWidget(add_point_button)
        delete_point_button = QtWidgets.QPushButton("Delete Point")
        delete_point_button.clicked.connect(self._delete_connection_points)
        connection_action_row.addWidget(delete_point_button)
        pick_point_button = QtWidgets.QPushButton("Pick From 3D")
        pick_point_button.clicked.connect(self._pick_connection_point_from_3d)
        connection_action_row.addWidget(pick_point_button)
        derive_points_button = QtWidgets.QPushButton("Derive Defaults")
        derive_points_button.clicked.connect(self._derive_default_connection_points)
        connection_action_row.addWidget(derive_points_button)
        preview_points_button = QtWidgets.QPushButton("Preview Points")
        preview_points_button.clicked.connect(self._preview_connection_points)
        connection_action_row.addWidget(preview_points_button)
        connection_action_row.addStretch(1)
        detail_layout.addLayout(connection_action_row)

        detail_action_row = QtWidgets.QHBoxLayout()
        self._apply_detail_button = QtWidgets.QPushButton("Apply Selected Detail")
        self._apply_detail_button.setToolTip("Apply geometry detail and Drainage Connection Points for the selected Structure row.")
        self._apply_detail_button.clicked.connect(self._apply_selected_detail)
        detail_action_row.addWidget(self._apply_detail_button)
        detail_action_row.addStretch(1)
        detail_layout.addLayout(detail_action_row)
        layout.addWidget(detail_group)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setFixedHeight(100)
        self._status.setPlainText("No structure source object is selected.")
        layout.addWidget(self._status)

        action_row = QtWidgets.QHBoxLayout()
        validate_button = QtWidgets.QPushButton("Validate")
        validate_button.clicked.connect(self._validate)
        action_row.addWidget(validate_button)
        self._save_button = QtWidgets.QPushButton("Save")
        self._save_button.setToolTip("Save the current Structure source rows without creating a 3D preview.")
        self._save_button.clicked.connect(lambda: self._apply(close_after=False, show_preview=False))
        action_row.addWidget(self._save_button)
        self._preview_button = QtWidgets.QPushButton("Preview 3D")
        self._preview_button.setToolTip("Create a temporary 3D preview from the current panel values without saving.")
        self._preview_button.clicked.connect(self._show_preview)
        action_row.addWidget(self._preview_button)
        self._save_preview_button = QtWidgets.QPushButton("Save + Preview")
        self._save_preview_button.setToolTip("Save the current Structure source rows, then create a 3D preview.")
        self._save_preview_button.clicked.connect(lambda: self._apply(close_after=False, show_preview=True))
        action_row.addWidget(self._save_preview_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        self._update_preset_note()
        return widget

    def _load_existing_rows(self) -> None:
        model = to_structure_model(self.structure_obj)
        if model is None:
            return
        self._geometry_spec_rows = list(getattr(model, "geometry_spec_rows", []) or [])
        self._bridge_geometry_spec_rows = list(getattr(model, "bridge_geometry_spec_rows", []) or [])
        self._culvert_geometry_spec_rows = list(getattr(model, "culvert_geometry_spec_rows", []) or [])
        self._retaining_wall_geometry_spec_rows = list(getattr(model, "retaining_wall_geometry_spec_rows", []) or [])
        self._connection_point_rows = list(getattr(model, "connection_point_rows", []) or [])
        self._replace_rows(model.structure_rows)
        self._replace_geometry_specs(self._geometry_spec_rows)
        self._select_first_structure_row()
        self._set_status(f"Loaded {len(model.structure_rows)} Structure row(s) from {self.structure_obj.Label}.")

    def _load_selected_preset(self) -> None:
        try:
            preset_name = str(self._preset_combo.currentText() or "Bridge Segment")
            model = structure_preset_model_from_document(preset_name, document=self.document)
            self._geometry_spec_rows = list(getattr(model, "geometry_spec_rows", []) or [])
            self._bridge_geometry_spec_rows = list(getattr(model, "bridge_geometry_spec_rows", []) or [])
            self._culvert_geometry_spec_rows = list(getattr(model, "culvert_geometry_spec_rows", []) or [])
            self._retaining_wall_geometry_spec_rows = list(getattr(model, "retaining_wall_geometry_spec_rows", []) or [])
            self._connection_point_rows = list(getattr(model, "connection_point_rows", []) or [])
            self._replace_rows(model.structure_rows)
            self._replace_geometry_specs(self._geometry_spec_rows)
            self._select_first_structure_row()
            self._set_status(f"Structure preset loaded: {preset_name}. Apply when ready.")
        except Exception as exc:
            self._set_status(f"Structure preset was not loaded:\n{exc}")

    def _update_preset_note(self) -> None:
        if not hasattr(self, "_preset_note"):
            return
        preset = STRUCTURE_PRESETS.get(str(self._preset_combo.currentText() or ""), {})
        self._preset_note.setText(str(preset.get("note", "") or ""))

    def _replace_rows(self, rows: list[StructureRow]) -> None:
        self._table.setRowCount(0)
        for row in rows:
            self._append_row(row)

    def _replace_geometry_specs(self, rows: list[StructureGeometrySpec]) -> None:
        self._geometry_table.setRowCount(0)
        for row in rows:
            self._append_geometry_spec(row)

    def _append_row(self, row: StructureRow | None = None) -> None:
        row = row or StructureRow(
            structure_id=f"structure:{self._table.rowCount() + 1}",
            structure_kind="bridge",
            structure_role="interface",
            placement=StructurePlacement(
                placement_id=f"placement:{self._table.rowCount() + 1}",
                alignment_id=_alignment_id(self.document),
                station_start=0.0,
                station_end=100.0,
            ),
            geometry_spec_ref=f"geometry-spec:{self._table.rowCount() + 1}",
        )
        index = self._table.rowCount()
        self._table.insertRow(index)
        values = [
            _display_structure_ref(row.structure_id),
            row.structure_kind,
            row.structure_role,
            _format_float(row.placement.station_start),
            _format_float(row.placement.station_end),
            _format_float(row.placement.offset),
            "",
        ]
        for col, value in enumerate(values):
            if col == 1:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(STRUCTURE_KIND_CHOICES)
                combo.setCurrentText(str(value or "bridge"))
                self._table.setCellWidget(index, col, combo)
            elif col == 2:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(STRUCTURE_ROLE_CHOICES)
                combo.setCurrentText(str(value or "interface"))
                self._table.setCellWidget(index, col, combo)
            else:
                item = QtWidgets.QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(STRUCTURE_GEOMETRY_SPEC_REF_ROLE, str(getattr(row, "geometry_spec_ref", "") or ""))
                    item.setData(STRUCTURE_GEOMETRY_REF_ROLE, str(getattr(row, "geometry_ref", "") or ""))
                    item.setData(STRUCTURE_GEOMETRY_SOURCE_ROLE, _geometry_source_mode(row))
                    item.setData(STRUCTURE_NATIVE_TYPE_ROLE, str(getattr(row, "native_type", "") or ""))
                self._table.setItem(index, col, item)

    def _append_geometry_spec(self, row: StructureGeometrySpec | None = None) -> None:
        row = row or StructureGeometrySpec(
            geometry_spec_id=f"geometry-spec:{self._geometry_table.rowCount() + 1}",
            structure_ref=f"structure:{self._geometry_table.rowCount() + 1}",
            shape_kind="deck_slab",
            width=10.0,
            height=1.2,
        )
        index = self._geometry_table.rowCount()
        self._geometry_table.insertRow(index)
        values = [
            row.geometry_spec_id,
            row.structure_ref,
            row.shape_kind,
            _format_float(row.width),
            _format_float(row.height),
            row.length_mode,
            _format_float(row.skew_angle_deg),
            row.vertical_position_mode,
            _format_optional_float(row.base_elevation),
            _format_optional_float(row.top_elevation),
            row.material,
            row.notes,
        ]
        for col, value in enumerate(values):
            if col == 5:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(LENGTH_MODE_CHOICES)
                combo.setCurrentText(str(value or "station_range"))
                self._geometry_table.setCellWidget(index, col, combo)
            elif col == 7:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(VERTICAL_POSITION_MODE_CHOICES)
                combo.setCurrentText(str(value or "profile_frame"))
                self._geometry_table.setCellWidget(index, col, combo)
            else:
                self._geometry_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))

    def _add_structure_row(self) -> None:
        self._append_row()
        self._add_missing_geometry_specs()
        self._table.selectRow(max(0, self._table.rowCount() - 1))
        self._set_status("Added a Structure row. Edit values, then Validate or Apply.")

    def _delete_selected_rows(self) -> None:
        rows = sorted({item.row() for item in list(self._table.selectedItems() or [])}, reverse=True)
        if not rows and self._table.currentRow() >= 0:
            rows = [self._table.currentRow()]
        for row_index in rows:
            self._table.removeRow(row_index)
        self._load_selected_detail()
        self._set_status(f"Deleted {len(rows)} Structure row(s).")

    def _add_missing_geometry_specs(self) -> None:
        existing_spec_ids = {str(row.geometry_spec_id) for row in self._geometry_spec_table_rows(allow_blank=True)}
        existing_structure_refs = {str(row.structure_ref) for row in self._geometry_spec_table_rows(allow_blank=True)}
        added = 0
        for row in self._table_rows():
            structure_ref = str(row.structure_id)
            spec_ref = str(row.geometry_spec_ref or f"geometry-spec:{structure_ref.split(':')[-1]}")
            if spec_ref in existing_spec_ids or structure_ref in existing_structure_refs:
                continue
            self._append_geometry_spec(
                StructureGeometrySpec(
                    geometry_spec_id=spec_ref,
                    structure_ref=structure_ref,
                    shape_kind=_default_shape_kind(row.structure_kind),
                    width=_default_geometry_width(row.structure_kind),
                    height=_default_geometry_height(row.structure_kind),
                    length_mode="station_range",
                    vertical_position_mode="profile_frame",
                    style_role=str(row.structure_kind),
                )
            )
            added += 1
        self._set_status(f"Added {added} missing Geometry Spec row(s).")

    def _delete_selected_geometry_specs(self) -> None:
        rows = sorted({item.row() for item in list(self._geometry_table.selectedItems() or [])}, reverse=True)
        if not rows and self._geometry_table.currentRow() >= 0:
            rows = [self._geometry_table.currentRow()]
        for row_index in rows:
            self._geometry_table.removeRow(row_index)
        self._set_status(f"Deleted {len(rows)} Geometry Spec row(s).")

    def _add_connection_point(self) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before adding a connection point.")
            return
        self._append_connection_point(
            StructureConnectionPoint(
                connection_point_id=f"connection:{str(row.structure_id).split(':')[-1]}:{self._connection_table.rowCount() + 1}",
                structure_ref=str(row.structure_id),
                point_role="inlet",
                station=float(getattr(row.placement, "station_start", 0.0) or 0.0),
                offset=float(getattr(row.placement, "offset", 0.0) or 0.0),
                region_ref="",
            )
        )
        self._set_status(f"Added a connection point for {row.structure_id}.")

    def _delete_connection_points(self) -> None:
        rows = sorted({item.row() for item in list(self._connection_table.selectedItems() or [])}, reverse=True)
        if not rows and self._connection_table.currentRow() >= 0:
            rows = [self._connection_table.currentRow()]
        for row_index in rows:
            self._connection_table.removeRow(row_index)
        if self._active_detail_structure_id:
            self._sync_connection_points_from_table(self._active_detail_structure_id)
        self._set_status(f"Deleted {len(rows)} connection point row(s).")

    def _derive_default_connection_points(self) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before deriving connection points.")
            return
        points = _derive_default_connection_points_for_row(row, self._geometry_spec_for_structure(row), self._culvert_spec_for_structure(row))
        if not points:
            self._set_status(f"No default connection point rule is defined for {row.structure_kind}.")
            return
        self._replace_connection_points(points)
        self._sync_connection_points_from_table(str(row.structure_id))
        self._set_status(f"Derived {len(points)} connection point row(s) for {row.structure_id}.")

    def _pick_connection_point_from_3d(self) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before picking a connection point.")
            return
        try:
            point = _selected_3d_point()
            station, offset = _station_offset_from_point(self.document, point)
            target_row = self._connection_table.currentRow()
            if target_row < 0:
                self._add_connection_point()
                target_row = self._connection_table.rowCount() - 1
            self._set_connection_cell(target_row, 2, _format_float(station))
            self._set_connection_cell(target_row, 3, _format_float(offset))
            self._set_connection_cell(target_row, 4, _format_float(float(getattr(point, "z", 0.0) or 0.0)))
            self._set_connection_cell(target_row, 5, _format_float(float(getattr(point, "z", 0.0) or 0.0)))
            notes = _item_text(self._connection_table, target_row, 11)
            if "picked_from_3d" not in notes:
                self._set_connection_cell(target_row, 11, (notes + "; " if notes else "") + "picked_from_3d")
            self._sync_connection_points_from_table(str(row.structure_id))
            self._set_status(
                "Picked 3D point into connection point row: "
                f"STA {station:.3f}, Offset {offset:.3f}, Elev {float(getattr(point, 'z', 0.0) or 0.0):.3f}."
            )
        except Exception as exc:
            self._set_status(f"3D point was not picked:\n{exc}")

    def _preview_connection_points(self) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before previewing connection points.")
            return
        try:
            model = self._model_from_table()
            preview = show_v1_structure_connection_points_preview_object(
                self.document,
                model,
                structure_ref=str(row.structure_id),
            )
            self._focus_preview_object(preview)
            self._set_status(f"Connection point preview shown for {row.structure_id}.")
        except Exception as exc:
            self._set_status(f"Connection point preview was not shown:\n{exc}")

    def _preview_connection_point_row(self, row_index: int) -> None:
        row = self._current_structure_row()
        if row is None:
            self._set_status("Select a Structure row before previewing a connection point.")
            return
        try:
            model = self._model_from_table()
            connection_ref = _item_text(self._connection_table, row_index, 0)
            preview = show_v1_structure_connection_points_preview_object(
                self.document,
                model,
                structure_ref=str(row.structure_id),
                connection_point_ref=connection_ref,
            )
            self._focus_preview_object(preview)
            self._set_status(f"Connection point preview shown: {connection_ref}.")
        except Exception as exc:
            self._set_status(f"Connection point preview was not shown:\n{exc}")

    def _connection_points_for_structure(self, structure_ref: str) -> list[StructureConnectionPoint]:
        expected = str(structure_ref or "")
        return [
            row
            for row in list(self._connection_point_rows or [])
            if str(getattr(row, "structure_ref", "") or "") == expected
        ]

    def _replace_connection_points(self, rows: list[StructureConnectionPoint]) -> None:
        self._connection_table.setRowCount(0)
        for row in rows:
            self._append_connection_point(row)

    def _append_connection_point(self, row: StructureConnectionPoint) -> None:
        index = self._connection_table.rowCount()
        self._connection_table.insertRow(index)
        values = [
            row.connection_point_id,
            row.point_role,
            _format_float(row.station),
            _format_float(row.offset),
            _format_optional_float(row.elevation),
            _format_optional_float(row.invert_elevation),
            row.shape_kind,
            _format_float(row.width),
            _format_float(row.height),
            _format_float(row.diameter),
            row.direction,
            row.notes,
        ]
        for col, value in enumerate(values):
            self._connection_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))

    def _set_connection_cell(self, row_index: int, col: int, value: str) -> None:
        item = self._connection_table.item(row_index, col)
        if item is None:
            item = QtWidgets.QTableWidgetItem("")
            self._connection_table.setItem(row_index, col, item)
        item.setText(str(value or ""))

    def _sync_connection_points_from_table(self, structure_ref: str) -> None:
        structure_ref = str(structure_ref or "")
        if not structure_ref:
            return
        retained = [
            row
            for row in list(self._connection_point_rows or [])
            if str(getattr(row, "structure_ref", "") or "") != structure_ref
        ]
        retained.extend(self._connection_point_table_rows(structure_ref))
        self._connection_point_rows = retained

    def _connection_point_table_rows(self, structure_ref: str) -> list[StructureConnectionPoint]:
        rows: list[StructureConnectionPoint] = []
        for row_index in range(self._connection_table.rowCount()):
            point_id = _item_text(self._connection_table, row_index, 0) or f"connection:{structure_ref.split(':')[-1]}:{row_index + 1}"
            rows.append(
                StructureConnectionPoint(
                    connection_point_id=point_id,
                    structure_ref=structure_ref,
                    point_role=_item_text(self._connection_table, row_index, 1) or "inlet",
                    station=_required_float(_item_text(self._connection_table, row_index, 2), f"Connection point row {row_index + 1} STA"),
                    offset=_required_float(_item_text(self._connection_table, row_index, 3) or "0", f"Connection point row {row_index + 1} offset"),
                    elevation=_optional_float_text(_item_text(self._connection_table, row_index, 4)),
                    invert_elevation=_optional_float_text(_item_text(self._connection_table, row_index, 5)),
                    shape_kind=_item_text(self._connection_table, row_index, 6),
                    width=_required_float(_item_text(self._connection_table, row_index, 7) or "0", f"Connection point row {row_index + 1} width"),
                    height=_required_float(_item_text(self._connection_table, row_index, 8) or "0", f"Connection point row {row_index + 1} height"),
                    diameter=_required_float(_item_text(self._connection_table, row_index, 9) or "0", f"Connection point row {row_index + 1} diameter"),
                    direction=_item_text(self._connection_table, row_index, 10),
                    connection_order=row_index + 1,
                    region_ref="",
                    notes=_item_text(self._connection_table, row_index, 11),
                )
            )
        return rows

    def _structure_row_by_id(self, structure_ref: str) -> StructureRow | None:
        expected = str(structure_ref or "")
        for row_index in range(self._table.rowCount()):
            if _source_structure_ref(_item_text(self._table, row_index, 0)) == expected:
                return self._structure_row_from_table_index(row_index)
        return None

    def _geometry_spec_for_structure(self, row: StructureRow) -> StructureGeometrySpec | None:
        spec_ref = str(getattr(row, "geometry_spec_ref", "") or "")
        for spec in self._geometry_spec_table_rows(allow_blank=True):
            if str(getattr(spec, "geometry_spec_id", "") or "") == spec_ref:
                return spec
        return None

    def _culvert_spec_for_structure(self, row: StructureRow) -> CulvertGeometrySpec | None:
        spec_ref = str(getattr(row, "geometry_spec_ref", "") or "")
        for spec in list(self._culvert_geometry_spec_rows or []):
            if str(getattr(spec, "geometry_spec_ref", "") or "") == spec_ref:
                return spec
        return None

    def _sort_rows(self) -> None:
        try:
            current_id = self._current_structure_id()
            rows = sorted(self._table_rows(), key=lambda row: (row.placement.station_start, row.placement.station_end, row.structure_id))
            self._replace_rows(rows)
            self._select_structure_id(current_id)
            self._set_status("Structure rows sorted by station.")
        except Exception as exc:
            self._set_status(f"Structure rows were not sorted:\n{exc}")

    def _activate_structure_detail_row(self, row_index: int, _column: int = 0) -> None:
        if row_index < 0 or row_index >= self._table.rowCount():
            return
        try:
            self._table.blockSignals(True)
            self._table.setCurrentCell(row_index, 0)
            self._table.selectRow(row_index)
        finally:
            self._table.blockSignals(False)
        self._load_selected_detail()

    def _load_selected_detail(self) -> None:
        if not self._loading_selected_detail and self._active_detail_structure_id:
            self._sync_common_geometry_detail_to_specs(self._active_detail_structure_id, self._active_detail_spec_ref)
            self._sync_connection_points_from_table(self._active_detail_structure_id)
        self._loading_selected_detail = True
        try:
            row = self._current_structure_row()
            if row is None:
                self._active_detail_structure_id = ""
                self._active_detail_spec_ref = ""
                self._detail_summary.setText("No structure row is selected.")
                self._geometry_source_combo.setEnabled(False)
                self._native_type_combo.setEnabled(False)
                self._geometry_source_combo.setCurrentText("native")
                self._native_type_combo.setCurrentText("")
                self._geometry_ref_field.setText("")
                self._geometry_ref_field.setEnabled(False)
                self._load_common_geometry_detail(None, "")
                self._connection_table.setRowCount(0)
                for label, field in zip(self._detail_labels, self._detail_fields):
                    label.setText("")
                    label.hide()
                    field.setText("")
                    field.hide()
                return
            source_mode = _geometry_source_mode(row)
            native_type = str(getattr(row, "native_type", "") or "")
            self._geometry_source_combo.setEnabled(True)
            self._geometry_source_combo.setCurrentText(source_mode)
            self._native_type_combo.setEnabled(source_mode == "native")
            self._native_type_combo.setCurrentText(native_type if native_type in NATIVE_TYPE_CHOICES else "")
            self._geometry_ref_field.setEnabled(source_mode != "native")
            self._geometry_ref_field.setText(str(getattr(row, "geometry_ref", "") or ""))
            spec_ref = self._ensure_row_geometry_spec_ref(self._table.currentRow(), row)
            self._active_detail_structure_id = str(row.structure_id)
            self._active_detail_spec_ref = spec_ref
            self._load_common_geometry_detail(row, spec_ref)
            self._replace_connection_points(self._connection_points_for_structure(row.structure_id))
            kind = str(row.structure_kind or "").strip().lower()
            self._detail_summary.setText(f"{_display_structure_ref(row.structure_id)} | {kind or 'custom'} | {spec_ref}")
            self._load_type_specific_detail(row, spec_ref)
        finally:
            self._loading_selected_detail = False

    def _apply_selected_detail(self) -> None:
        try:
            row_index = self._table.currentRow()
            row = self._current_structure_row()
            if row is None or row_index < 0:
                self._set_status("Select a Structure row before applying detail fields.")
                return
            self._set_row_geometry_source_mode(row_index, str(self._geometry_source_combo.currentText() or "native"))
            self._set_row_native_type(row_index, str(self._native_type_combo.currentText() or ""))
            self._set_row_geometry_ref(row_index, str(self._geometry_ref_field.text() or "").strip())
            spec_ref = self._ensure_row_geometry_spec_ref(row_index, row)
            self._add_or_update_common_spec_for_row(row, spec_ref)
            kind = str(row.structure_kind or "").strip().lower()
            native_type = str(self._native_type_combo.currentText() or "").strip().lower()
            detail_family = _detail_spec_family(native_type, kind)
            fields = _native_detail_field_specs(native_type, kind)
            values = {
                key: str(self._detail_fields[index].text() or "").strip()
                for index, (key, _label) in enumerate(fields)
            }
            values = _detail_values_with_native_defaults(native_type, values)
            if not fields:
                self._sync_connection_points_from_table(str(row.structure_id))
                self._load_selected_detail()
                self._set_status(
                    f"Selected detail applied for {row.structure_id}. Apply the model to persist changes."
                )
                return
            if detail_family == "bridge":
                self._bridge_geometry_spec_rows = _replace_kind_spec(
                    self._bridge_geometry_spec_rows,
                    _bridge_spec_from_detail(spec_ref, values),
                )
            elif detail_family == "culvert":
                self._culvert_geometry_spec_rows = _replace_kind_spec(
                    self._culvert_geometry_spec_rows,
                    _culvert_spec_from_detail(spec_ref, values),
                )
            elif detail_family == "retaining_wall":
                self._retaining_wall_geometry_spec_rows = _replace_kind_spec(
                    self._retaining_wall_geometry_spec_rows,
                    _retaining_wall_spec_from_detail(spec_ref, values),
                )
            else:
                self._set_status(f"No kind-specific detail fields are defined for {kind or 'custom'}.")
                return
            self._sync_connection_points_from_table(str(row.structure_id))
            self._load_selected_detail()
            self._set_status(
                f"Selected detail applied for {row.structure_id}. Apply the model to persist changes."
            )
        except Exception as exc:
            self._set_status(f"Structure detail was not applied:\n{exc}")

    def _handle_native_type_changed(self, _index: int) -> None:
        if getattr(self, "_loading_selected_detail", False):
            return
        self._sync_selected_detail_to_row()
        row = self._current_structure_row()
        if row is None:
            return
        spec_ref = self._ensure_row_geometry_spec_ref(self._table.currentRow(), row)
        self._apply_native_type_common_defaults(row)
        self._load_type_specific_detail(row, spec_ref)

    def _handle_geometry_source_changed(self, _index: int) -> None:
        source_mode = str(self._geometry_source_combo.currentText() or "native")
        self._geometry_ref_field.setEnabled(source_mode != "native")
        self._native_type_combo.setEnabled(source_mode == "native")
        self._set_common_geometry_detail_enabled(source_mode == "native")
        self._sync_selected_detail_to_row()

    def _load_type_specific_detail(self, row: StructureRow, spec_ref: str) -> None:
        kind = str(row.structure_kind or "").strip().lower()
        native_type = str(getattr(row, "native_type", "") or "").strip().lower()
        detail_family = _detail_spec_family(native_type, kind)
        values = _kind_detail_values(
            detail_family,
            spec_ref,
            self._bridge_geometry_spec_rows,
            self._culvert_geometry_spec_rows,
            self._retaining_wall_geometry_spec_rows,
        )
        values = _detail_values_with_native_defaults(native_type, values)
        fields = _native_detail_field_specs(native_type, kind)
        for index, (key, label_text) in enumerate(fields):
            self._detail_labels[index].setText(label_text)
            self._detail_labels[index].show()
            self._detail_fields[index].setText(str(values.get(key, "")))
            self._detail_fields[index].show()
        for index in range(len(fields), len(self._detail_fields)):
            self._detail_labels[index].setText("")
            self._detail_labels[index].hide()
            self._detail_fields[index].setText("")
            self._detail_fields[index].hide()

    def _common_geometry_fields(self):
        return [
            self._common_shape_field,
            self._common_width_field,
            self._common_height_field,
            self._common_vertical_mode_combo,
            self._common_base_elev_field,
            self._common_top_elev_field,
            self._common_skew_field,
            self._common_material_field,
            self._common_notes_field,
        ]

    def _set_common_geometry_detail_enabled(self, enabled: bool) -> None:
        for field in self._common_geometry_fields():
            try:
                field.setEnabled(enabled)
            except Exception:
                pass

    def _load_common_geometry_detail(self, row: StructureRow | None, spec_ref: str) -> None:
        if row is None:
            self._common_shape_field.setText("")
            self._common_width_field.setText("")
            self._common_height_field.setText("")
            self._common_vertical_mode_combo.setCurrentText("profile_frame")
            self._common_base_elev_field.setText("")
            self._common_top_elev_field.setText("")
            self._common_skew_field.setText("")
            self._common_material_field.setText("")
            self._common_notes_field.setText("")
            self._set_common_geometry_detail_enabled(False)
            return
        spec = self._common_geometry_spec_for_ref(spec_ref)
        native_type = str(getattr(row, "native_type", "") or "").strip().lower()
        self._set_common_geometry_detail_enabled(_geometry_source_mode(row) == "native")
        self._common_shape_field.setText(str(getattr(spec, "shape_kind", "") or _default_shape_kind_for_native(native_type, row.structure_kind)))
        self._common_width_field.setText(_format_float(getattr(spec, "width", 0.0) or _default_geometry_width_for_native(native_type, row.structure_kind)))
        self._common_height_field.setText(_format_float(getattr(spec, "height", 0.0) or _default_geometry_height_for_native(native_type, row.structure_kind)))
        self._common_vertical_mode_combo.setCurrentText(str(getattr(spec, "vertical_position_mode", "") or "profile_frame"))
        self._common_base_elev_field.setText(_format_optional_float(getattr(spec, "base_elevation", None)))
        self._common_top_elev_field.setText(_format_optional_float(getattr(spec, "top_elevation", None)))
        self._common_skew_field.setText(_format_float(getattr(spec, "skew_angle_deg", 0.0) or 0.0))
        self._common_material_field.setText(str(getattr(spec, "material", "") or ""))
        self._common_notes_field.setText(str(getattr(spec, "notes", "") or ""))

    def _common_geometry_spec_for_ref(self, spec_ref: str) -> StructureGeometrySpec | None:
        for spec in self._geometry_spec_table_rows(allow_blank=True):
            if str(getattr(spec, "geometry_spec_id", "") or "") == str(spec_ref or ""):
                return spec
        return None

    def _sync_common_geometry_detail_to_specs(self, structure_ref: str, spec_ref: str) -> None:
        if getattr(self, "_loading_selected_detail", False):
            return
        if not structure_ref or not spec_ref or not hasattr(self, "_common_shape_field"):
            return
        row = self._current_structure_row()
        if row is None or str(getattr(row, "structure_id", "") or "") != str(structure_ref):
            row = None
            for candidate in self._table_rows():
                if str(candidate.structure_id) == str(structure_ref):
                    row = candidate
                    break
        if row is None:
            return
        existing = self._common_geometry_spec_for_ref(spec_ref)
        spec = StructureGeometrySpec(
            geometry_spec_id=spec_ref,
            structure_ref=structure_ref,
            shape_kind=str(self._common_shape_field.text() or "").strip() or _default_shape_kind_for_native(getattr(row, "native_type", ""), row.structure_kind),
            width=_required_float(str(self._common_width_field.text() or ""), "Selected Structure Detail Width"),
            height=_required_float(str(self._common_height_field.text() or ""), "Selected Structure Detail Height"),
            length_mode=str(getattr(existing, "length_mode", "") or "station_range"),
            skew_angle_deg=_required_float(str(self._common_skew_field.text() or "0"), "Selected Structure Detail Skew"),
            vertical_position_mode=str(self._common_vertical_mode_combo.currentText() or "profile_frame"),
            base_elevation=_optional_float_text(str(self._common_base_elev_field.text() or "")),
            top_elevation=_optional_float_text(str(self._common_top_elev_field.text() or "")),
            material=str(self._common_material_field.text() or "").strip(),
            style_role=str(getattr(existing, "style_role", "") or row.structure_kind),
            notes=str(self._common_notes_field.text() or "").strip(),
        )
        specs = self._geometry_spec_table_rows(allow_blank=True)
        for index, candidate in enumerate(specs):
            if str(candidate.geometry_spec_id) == str(spec_ref):
                specs[index] = spec
                self._replace_geometry_specs(specs)
                return
        specs.append(spec)
        self._replace_geometry_specs(specs)

    def _apply_native_type_common_defaults(self, row: StructureRow) -> None:
        native_type = str(self._native_type_combo.currentText() or "").strip().lower()
        if not native_type:
            return
        self._common_shape_field.setText(_default_shape_kind_for_native(native_type, row.structure_kind))
        self._common_width_field.setText(_format_float(_default_geometry_width_for_native(native_type, row.structure_kind)))
        self._common_height_field.setText(_format_float(_default_geometry_height_for_native(native_type, row.structure_kind)))

    def _validate(self) -> None:
        try:
            model = self._model_from_table()
            self._set_status(_format_validation_result(model, document=self.document))
        except Exception as exc:
            self._set_status(f"Structure validation failed:\n{exc}")

    def _apply(self, *, close_after: bool = False, show_preview: bool = False) -> bool:
        try:
            model = self._model_from_table()
            diagnostics = validate_structure_model(model)
            if any(str(row).startswith("error|") for row in diagnostics):
                self._set_status(_format_validation_result(model, document=self.document))
                _show_message(self.form, "Structures", "Structures were not applied because validation has errors.")
                return False
            self.structure_obj = apply_v1_structure_model(document=self.document, structure_model=model)
            preview_text = ""
            if show_preview and list(model.structure_rows or []):
                preview = show_v1_structure_preview_object(self.document, model)
                self._focus_preview_object(preview)
                preview_text = f"\n3D Preview: {preview.Label}"
            self._set_status(_format_validation_result(model, document=self.document) + f"\n\nApplied to: {self.structure_obj.Label}{preview_text}")
            _show_message(self.form, "Structures", f"Structures have been applied.\nRows: {len(model.structure_rows)}")
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(f"Structures were not applied:\n{exc}")
            _show_message(self.form, "Structures", f"Structures were not applied.\n{exc}")
            return False

    def _show_preview(self) -> None:
        try:
            model = self._model_from_table()
            diagnostics = validate_structure_model(model)
            if any(str(row).startswith("error|") for row in diagnostics):
                self._set_status(_format_validation_result(model, document=self.document))
                return
            preview = show_v1_structure_preview_object(self.document, model)
            self._focus_preview_object(preview)
            self._set_status(_format_validation_result(model, document=self.document) + f"\n\n3D Preview shown: {preview.Label}")
        except Exception as exc:
            self._set_status(f"Structure preview was not shown:\n{exc}")

    def _focus_preview_object(self, preview) -> None:
        if Gui is None or preview is None:
            return
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(preview)
        except Exception:
            pass
        try:
            view = getattr(getattr(Gui, "ActiveDocument", None), "ActiveView", None)
            if view is not None and hasattr(view, "fitSelection"):
                view.fitSelection()
        except Exception:
            pass

    def _model_from_table(self) -> StructureModel:
        self._sync_selected_detail_to_row()
        if self._active_detail_structure_id:
            self._sync_common_geometry_detail_to_specs(self._active_detail_structure_id, self._active_detail_spec_ref)
            self._sync_connection_points_from_table(self._active_detail_structure_id)
        existing = to_structure_model(self.structure_obj)
        alignment = find_v1_alignment(self.document)
        structure_rows = self._table_rows()
        structure_ids = {str(row.structure_id) for row in structure_rows}
        geometry_spec_rows = [
            row
            for row in self._geometry_spec_table_rows()
            if str(getattr(row, "structure_ref", "") or "") in structure_ids
        ]
        return StructureModel(
            schema_version=1,
            project_id=_project_id(find_project(self.document)),
            structure_model_id=str(getattr(existing, "structure_model_id", "") or "structures:main"),
            alignment_id=str(getattr(existing, "alignment_id", "") or getattr(alignment, "AlignmentId", "") or ""),
            label="Structures",
            structure_rows=structure_rows,
            geometry_spec_rows=geometry_spec_rows,
            bridge_geometry_spec_rows=_filter_kind_specs(
                self._bridge_geometry_spec_rows or getattr(existing, "bridge_geometry_spec_rows", []),
                geometry_spec_rows,
            ),
            culvert_geometry_spec_rows=_filter_kind_specs(
                self._culvert_geometry_spec_rows or getattr(existing, "culvert_geometry_spec_rows", []),
                geometry_spec_rows,
            ),
            retaining_wall_geometry_spec_rows=_filter_kind_specs(
                self._retaining_wall_geometry_spec_rows or getattr(existing, "retaining_wall_geometry_spec_rows", []),
                geometry_spec_rows,
            ),
            connection_point_rows=[
                row
                for row in self._connection_point_rows
                if str(getattr(row, "structure_ref", "") or "") in structure_ids
            ],
            interaction_rule_rows=[],
            influence_zone_rows=[],
        )

    def _table_rows(self) -> list[StructureRow]:
        rows: list[StructureRow] = []
        alignment_id = _alignment_id(self.document)
        for row_index in range(self._table.rowCount()):
            structure_id = _source_structure_ref(_item_text(self._table, row_index, 0) or f"{row_index + 1}")
            kind = _item_text(self._table, row_index, 1) or "bridge"
            role = _item_text(self._table, row_index, 2) or "interface"
            station_start = _required_float(_item_text(self._table, row_index, 3), f"Row {row_index + 1} start STA")
            station_end = _required_float(_item_text(self._table, row_index, 4), f"Row {row_index + 1} end STA")
            offset = _required_float(_item_text(self._table, row_index, 5) or "0", f"Row {row_index + 1} offset")
            geometry_ref = self._row_geometry_ref(row_index)
            geometry_source_mode = self._row_geometry_source_mode(row_index)
            rows.append(
                StructureRow(
                    structure_id=structure_id,
                    structure_kind=kind,
                    structure_role=role,
                    placement=StructurePlacement(
                        placement_id=f"placement:{row_index + 1}",
                        alignment_id=alignment_id,
                        station_start=station_start,
                        station_end=station_end,
                        offset=offset,
                        region_ref="",
                    ),
                    geometry_spec_ref=_item_user_data(self._table, row_index, 0, STRUCTURE_GEOMETRY_SPEC_REF_ROLE),
                    geometry_ref=geometry_ref,
                    reference_mode="native" if geometry_source_mode == "native" else "source_ref",
                    geometry_source_mode=geometry_source_mode,
                    native_type=self._row_native_type(row_index),
                )
            )
        return rows

    def _current_structure_id(self) -> str:
        row = self._current_structure_row()
        return str(getattr(row, "structure_id", "") or "") if row is not None else ""

    def _current_structure_row(self) -> StructureRow | None:
        row_index = self._table.currentRow()
        if row_index < 0 and self._table.selectedItems():
            row_index = self._table.selectedItems()[0].row()
        if row_index < 0 or row_index >= self._table.rowCount():
            return None
        return self._structure_row_from_table_index(row_index)

    def _structure_row_from_table_index(self, row_index: int) -> StructureRow:
        alignment_id = _alignment_id(self.document)
        structure_id = _source_structure_ref(_item_text(self._table, row_index, 0) or f"{row_index + 1}")
        kind = _item_text(self._table, row_index, 1) or "bridge"
        role = _item_text(self._table, row_index, 2) or "interface"
        station_start = _required_float(_item_text(self._table, row_index, 3), f"Row {row_index + 1} start STA")
        station_end = _required_float(_item_text(self._table, row_index, 4), f"Row {row_index + 1} end STA")
        offset = _required_float(_item_text(self._table, row_index, 5) or "0", f"Row {row_index + 1} offset")
        geometry_ref = self._row_geometry_ref(row_index)
        geometry_source_mode = self._row_geometry_source_mode(row_index)
        return StructureRow(
            structure_id=structure_id,
            structure_kind=kind,
            structure_role=role,
            placement=StructurePlacement(
                placement_id=f"placement:{row_index + 1}",
                alignment_id=alignment_id,
                station_start=station_start,
                station_end=station_end,
                offset=offset,
                region_ref="",
            ),
            geometry_spec_ref=_item_user_data(self._table, row_index, 0, STRUCTURE_GEOMETRY_SPEC_REF_ROLE),
            geometry_ref=geometry_ref,
            reference_mode="native" if geometry_source_mode == "native" else "source_ref",
            geometry_source_mode=geometry_source_mode,
            native_type=self._row_native_type(row_index),
        )

    def _select_first_structure_row(self) -> None:
        if self._table.rowCount() > 0:
            self._table.selectRow(0)
        self._load_selected_detail()

    def _select_structure_id(self, structure_id: str) -> None:
        expected = _source_structure_ref(structure_id)
        for row_index in range(self._table.rowCount()):
            if _source_structure_ref(_item_text(self._table, row_index, 0)) == expected:
                self._table.selectRow(row_index)
                return
        self._select_first_structure_row()

    def _ensure_row_geometry_spec_ref(self, row_index: int, row: StructureRow) -> str:
        spec_ref = str(getattr(row, "geometry_spec_ref", "") or "")
        if not spec_ref:
            spec_ref = f"geometry-spec:{str(row.structure_id).split(':')[-1]}"
            item = self._table.item(row_index, 0)
            if item is not None:
                item.setData(STRUCTURE_GEOMETRY_SPEC_REF_ROLE, spec_ref)
        return spec_ref

    def _row_geometry_ref(self, row_index: int) -> str:
        return _item_user_data(self._table, row_index, 0, STRUCTURE_GEOMETRY_REF_ROLE)

    def _set_row_geometry_ref(self, row_index: int, geometry_ref: str) -> None:
        item = self._table.item(row_index, 0)
        if item is not None:
            item.setData(STRUCTURE_GEOMETRY_REF_ROLE, str(geometry_ref or "").strip())

    def _row_geometry_source_mode(self, row_index: int) -> str:
        mode = _item_user_data(self._table, row_index, 0, STRUCTURE_GEOMETRY_SOURCE_ROLE)
        return mode if mode in GEOMETRY_SOURCE_CHOICES else "native"

    def _set_row_geometry_source_mode(self, row_index: int, mode: str) -> None:
        item = self._table.item(row_index, 0)
        if item is not None:
            item.setData(STRUCTURE_GEOMETRY_SOURCE_ROLE, mode if mode in GEOMETRY_SOURCE_CHOICES else "native")

    def _row_native_type(self, row_index: int) -> str:
        return _item_user_data(self._table, row_index, 0, STRUCTURE_NATIVE_TYPE_ROLE)

    def _set_row_native_type(self, row_index: int, native_type: str) -> None:
        item = self._table.item(row_index, 0)
        if item is not None:
            item.setData(STRUCTURE_NATIVE_TYPE_ROLE, str(native_type or "").strip())

    def _sync_selected_detail_to_row(self) -> None:
        row_index = self._table.currentRow()
        if row_index < 0 or row_index >= self._table.rowCount():
            return
        if getattr(self, "_loading_selected_detail", False):
            return
        if not hasattr(self, "_geometry_ref_field"):
            return
        self._set_row_geometry_source_mode(row_index, str(self._geometry_source_combo.currentText() or "native"))
        self._set_row_native_type(row_index, str(self._native_type_combo.currentText() or ""))
        self._set_row_geometry_ref(row_index, str(self._geometry_ref_field.text() or "").strip())

    def _add_or_update_common_spec_for_row(self, row: StructureRow, spec_ref: str) -> None:
        if str(row.structure_id) == str(self._active_detail_structure_id or ""):
            self._sync_common_geometry_detail_to_specs(str(row.structure_id), spec_ref)
            return
        specs = self._geometry_spec_table_rows(allow_blank=True)
        for index, spec in enumerate(specs):
            if spec.geometry_spec_id == spec_ref:
                specs[index] = StructureGeometrySpec(
                    geometry_spec_id=spec.geometry_spec_id,
                    structure_ref=row.structure_id,
                    shape_kind=spec.shape_kind or _default_shape_kind(row.structure_kind),
                    width=spec.width if spec.width > 0.0 else _default_geometry_width(row.structure_kind),
                    height=spec.height if spec.height > 0.0 else _default_geometry_height(row.structure_kind),
                    length_mode=spec.length_mode,
                    skew_angle_deg=spec.skew_angle_deg,
                    vertical_position_mode=spec.vertical_position_mode,
                    base_elevation=spec.base_elevation,
                    top_elevation=spec.top_elevation,
                    material=spec.material,
                    style_role=spec.style_role or row.structure_kind,
                    notes=spec.notes,
                )
                self._replace_geometry_specs(specs)
                return
        specs.append(
            StructureGeometrySpec(
                geometry_spec_id=spec_ref,
                structure_ref=row.structure_id,
                shape_kind=_default_shape_kind(row.structure_kind),
                width=_default_geometry_width(row.structure_kind),
                height=_default_geometry_height(row.structure_kind),
                length_mode="station_range",
                vertical_position_mode="profile_frame",
                style_role=row.structure_kind,
            )
        )
        self._replace_geometry_specs(specs)

    def _geometry_spec_table_rows(self, *, allow_blank: bool = False) -> list[StructureGeometrySpec]:
        rows: list[StructureGeometrySpec] = []
        for row_index in range(self._geometry_table.rowCount()):
            geometry_spec_id = _item_text(self._geometry_table, row_index, 0) or f"geometry-spec:{row_index + 1}"
            structure_ref = _item_text(self._geometry_table, row_index, 1)
            if not allow_blank and not structure_ref:
                raise ValueError(f"Geometry Spec row {row_index + 1} Structure Ref is required.")
            rows.append(
                StructureGeometrySpec(
                    geometry_spec_id=geometry_spec_id,
                    structure_ref=structure_ref,
                    shape_kind=_item_text(self._geometry_table, row_index, 2),
                    width=_required_float(_item_text(self._geometry_table, row_index, 3) or "0", f"Geometry Spec row {row_index + 1} width"),
                    height=_required_float(_item_text(self._geometry_table, row_index, 4) or "0", f"Geometry Spec row {row_index + 1} height"),
                    length_mode=_item_text(self._geometry_table, row_index, 5) or "station_range",
                    skew_angle_deg=_required_float(_item_text(self._geometry_table, row_index, 6) or "0", f"Geometry Spec row {row_index + 1} skew"),
                    vertical_position_mode=_item_text(self._geometry_table, row_index, 7) or "profile_frame",
                    base_elevation=_optional_float_text(_item_text(self._geometry_table, row_index, 8)),
                    top_elevation=_optional_float_text(_item_text(self._geometry_table, row_index, 9)),
                    material=_item_text(self._geometry_table, row_index, 10),
                    notes=_item_text(self._geometry_table, row_index, 11),
                )
            )
        return rows

    def _set_status(self, text: str) -> None:
        self._status.setPlainText(str(text or ""))


class CmdV1StructureEditor:
    """Open the v1 Structure source editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("edit_structures.svg"),
            "MenuText": "Structures",
            "ToolTip": "Define v1 corridor structures by station range and source references",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_structure_editor_command()


def _preset_structure_rows(
    preset: dict,
    *,
    station_start: float,
    station_end: float,
    alignment_id: str,
) -> list[StructureRow]:
    span = max(float(station_end) - float(station_start), 0.0)
    if span <= 0.0:
        span = 100.0
        station_end = float(station_start) + span
    rows: list[StructureRow] = []
    for index, spec in enumerate(list(preset.get("rows", []) or []), start=1):
        start_ratio = max(0.0, min(1.0, float(spec.get("start", 0.0) or 0.0)))
        end_ratio = max(0.0, min(1.0, float(spec.get("end", 1.0) or 1.0)))
        start_sta = float(station_start) + span * start_ratio
        end_sta = float(station_start) + span * end_ratio
        if end_sta < start_sta:
            start_sta, end_sta = end_sta, start_sta
        structure_id = str(spec.get("id", "") or f"structure:{index}")
        rows.append(
            StructureRow(
                structure_id=structure_id,
                structure_kind=str(spec.get("kind", "") or "bridge"),
                structure_role=str(spec.get("role", "") or "interface"),
                placement=StructurePlacement(
                    placement_id=f"placement:{index}",
                    alignment_id=alignment_id,
                    station_start=start_sta,
                    station_end=end_sta,
                    offset=float(spec.get("offset", 0.0) or 0.0),
                ),
                geometry_spec_ref=str(spec.get("spec", "") or ""),
                geometry_ref=str(spec.get("geometry", "") or ""),
                reference_mode="native",
                geometry_source_mode="native",
                native_type=str(spec.get("native_type", "") or _native_type_from_preset_spec(spec)),
            )
        )
    return rows


def _preset_geometry_spec_rows(preset: dict) -> list[StructureGeometrySpec]:
    rows: list[StructureGeometrySpec] = []
    for spec in list(preset.get("rows", []) or []):
        geometry_spec_id = str(spec.get("spec", "") or "")
        structure_id = str(spec.get("id", "") or "")
        if not geometry_spec_id or not structure_id:
            continue
        rows.append(
            StructureGeometrySpec(
                geometry_spec_id=geometry_spec_id,
                structure_ref=structure_id,
                shape_kind=str(spec.get("shape", "") or ""),
                width=float(spec.get("width", 0.0) or 0.0),
                height=float(spec.get("height", 0.0) or 0.0),
                length_mode="station_range",
                material=str(spec.get("material", "") or ""),
                style_role=str(spec.get("kind", "") or ""),
                notes=str(spec.get("notes", "") or ""),
            )
        )
    return rows


def _preset_bridge_geometry_spec_rows(preset: dict) -> list[BridgeGeometrySpec]:
    rows: list[BridgeGeometrySpec] = []
    for spec in list(preset.get("rows", []) or []):
        values = dict(spec.get("bridge", {}) or {})
        geometry_spec_ref = str(spec.get("spec", "") or "")
        if not geometry_spec_ref or not values:
            continue
        rows.append(
            BridgeGeometrySpec(
                geometry_spec_ref=geometry_spec_ref,
                deck_width=float(values.get("deck_width", 0.0) or 0.0),
                deck_thickness=float(values.get("deck_thickness", 0.0) or 0.0),
                girder_depth=float(values.get("girder_depth", 0.0) or 0.0),
                barrier_height=float(values.get("barrier_height", 0.0) or 0.0),
                clearance_height=float(values.get("clearance_height", 0.0) or 0.0),
                abutment_start_offset=float(values.get("abutment_start_offset", 0.0) or 0.0),
                abutment_end_offset=float(values.get("abutment_end_offset", 0.0) or 0.0),
                pier_station_refs=list(values.get("pier_station_refs", []) or []),
                approach_slab_length=float(values.get("approach_slab_length", 0.0) or 0.0),
                bearing_elevation_mode=str(values.get("bearing_elevation_mode", "") or ""),
            )
        )
    return rows


def _preset_culvert_geometry_spec_rows(preset: dict) -> list[CulvertGeometrySpec]:
    rows: list[CulvertGeometrySpec] = []
    for spec in list(preset.get("rows", []) or []):
        values = dict(spec.get("culvert", {}) or {})
        geometry_spec_ref = str(spec.get("spec", "") or "")
        if not geometry_spec_ref or not values:
            continue
        rows.append(
            CulvertGeometrySpec(
                geometry_spec_ref=geometry_spec_ref,
                barrel_shape=str(values.get("barrel_shape", "box") or "box"),
                barrel_count=int(values.get("barrel_count", 1) or 1),
                span=float(values.get("span", 0.0) or 0.0),
                rise=float(values.get("rise", 0.0) or 0.0),
                diameter=float(values.get("diameter", 0.0) or 0.0),
                wall_thickness=float(values.get("wall_thickness", 0.0) or 0.0),
                length=float(values.get("length", 0.0) or 0.0),
                invert_elevation=_optional_float_text(values.get("invert_elevation", "")),
                inlet_skew_angle_deg=float(values.get("inlet_skew_angle_deg", 0.0) or 0.0),
                outlet_skew_angle_deg=float(values.get("outlet_skew_angle_deg", 0.0) or 0.0),
                headwall_type=str(values.get("headwall_type", "") or ""),
                wingwall_type=str(values.get("wingwall_type", "") or ""),
            )
        )
    return rows


def _preset_retaining_wall_geometry_spec_rows(preset: dict) -> list[RetainingWallGeometrySpec]:
    rows: list[RetainingWallGeometrySpec] = []
    for spec in list(preset.get("rows", []) or []):
        values = dict(spec.get("retaining_wall", {}) or {})
        geometry_spec_ref = str(spec.get("spec", "") or "")
        if not geometry_spec_ref or not values:
            continue
        rows.append(
            RetainingWallGeometrySpec(
                geometry_spec_ref=geometry_spec_ref,
                wall_height=float(values.get("wall_height", 0.0) or 0.0),
                wall_thickness=float(values.get("wall_thickness", 0.0) or 0.0),
                footing_width=float(values.get("footing_width", 0.0) or 0.0),
                footing_thickness=float(values.get("footing_thickness", 0.0) or 0.0),
                retained_side=str(values.get("retained_side", "") or ""),
                top_elevation_mode=str(values.get("top_elevation_mode", "") or ""),
                bottom_elevation_mode=str(values.get("bottom_elevation_mode", "") or ""),
                batter_slope=float(values.get("batter_slope", 0.0) or 0.0),
                coping_height=float(values.get("coping_height", 0.0) or 0.0),
                drainage_layer_ref=str(values.get("drainage_layer_ref", "") or ""),
            )
        )
    return rows


def _preset_connection_point_rows(
    preset: dict,
    *,
    structure_rows: list[StructureRow],
    geometry_spec_rows: list[StructureGeometrySpec],
    culvert_geometry_spec_rows: list[CulvertGeometrySpec],
) -> list[StructureConnectionPoint]:
    rows: list[StructureConnectionPoint] = []
    structure_by_ref = {str(getattr(row, "structure_id", "") or ""): row for row in structure_rows}
    geometry_by_ref = {str(getattr(row, "structure_ref", "") or ""): row for row in geometry_spec_rows}
    culvert_by_ref = {
        str(getattr(row, "geometry_spec_ref", "") or ""): row for row in culvert_geometry_spec_rows
    }
    for spec in list(preset.get("rows", []) or []):
        structure_ref = str(spec.get("id", "") or "")
        structure_row = structure_by_ref.get(structure_ref)
        if structure_row is None:
            continue
        geometry_spec = geometry_by_ref.get(structure_ref)
        culvert_spec = culvert_by_ref.get(str(getattr(structure_row, "geometry_spec_ref", "") or ""))
        point_specs = list(spec.get("connection_points", []) or [])
        if not point_specs:
            continue
        for order, point_spec in enumerate(point_specs, start=1):
            point = _preset_connection_point_from_spec(
                point_spec,
                structure_row=structure_row,
                geometry_spec=geometry_spec,
                culvert_spec=culvert_spec,
                connection_order=order,
            )
            if point is not None:
                rows.append(point)
    return rows


def _preset_connection_point_from_spec(
    spec: dict,
    *,
    structure_row: StructureRow,
    geometry_spec: StructureGeometrySpec | None,
    culvert_spec: CulvertGeometrySpec | None,
    connection_order: int,
) -> StructureConnectionPoint | None:
    role = str(spec.get("role", "") or "").strip()
    structure_ref = str(getattr(structure_row, "structure_id", "") or "")
    placement = getattr(structure_row, "placement", None)
    if not role or not structure_ref or placement is None:
        return None
    start = float(getattr(placement, "station_start", 0.0) or 0.0)
    end = float(getattr(placement, "station_end", start) or start)
    at = str(spec.get("at", "") or "center").strip().lower()
    if at == "start":
        station = start
    elif at == "end":
        station = end
    else:
        station = (start + end) * 0.5
    station = float(spec.get("station", station) or station)
    offset = float(spec.get("offset", getattr(placement, "offset", 0.0)) or 0.0)
    width = float(spec.get("width", getattr(geometry_spec, "width", 0.0)) or 0.0)
    height = float(spec.get("height", getattr(geometry_spec, "height", 0.0)) or 0.0)
    diameter = float(spec.get("diameter", 0.0) or 0.0)
    shape = str(spec.get("shape", getattr(geometry_spec, "shape_kind", "")) or "")
    if culvert_spec is not None and not diameter:
        barrel_shape = str(getattr(culvert_spec, "barrel_shape", "") or "").strip().lower()
        diameter = float(getattr(culvert_spec, "diameter", 0.0) or 0.0)
        if barrel_shape == "circular" or diameter:
            shape = shape or "circular"
            width = 0.0
            height = 0.0
        else:
            width = float(getattr(culvert_spec, "span", 0.0) or width)
            height = float(getattr(culvert_spec, "rise", 0.0) or height)
            shape = shape or "box"
    if diameter:
        width = float(spec.get("width", 0.0) or 0.0)
        height = float(spec.get("height", 0.0) or 0.0)
    base_id = structure_ref.split(":")[-1]
    point_id = str(spec.get("id", "") or f"connection:{base_id}:{role.replace('_', '-')}")
    invert = spec.get("invert_elevation", None)
    return StructureConnectionPoint(
        connection_point_id=point_id,
        structure_ref=structure_ref,
        point_role=role,
        station=station,
        offset=offset,
        elevation=_optional_float_text(spec.get("elevation", "")),
        invert_elevation=_optional_float_text(invert) if invert is not None else None,
        diameter=diameter,
        width=width,
        height=height,
        shape_kind=shape,
        direction=str(spec.get("direction", "") or ""),
        connection_order=connection_order,
        region_ref="",
        notes=str(spec.get("notes", "") or ""),
    )


def _native_type_from_preset_spec(spec: dict) -> str:
    explicit = str(spec.get("native_type", "") or "").strip()
    if explicit:
        return explicit
    kind = str(spec.get("kind", "") or "").strip().lower()
    shape = str(spec.get("shape", "") or "").strip().lower()
    culvert = dict(spec.get("culvert", {}) or {})
    if kind == "bridge":
        return "bridge_deck"
    if kind in {"retaining_wall", "wall"}:
        return "retaining_wall"
    if kind == "culvert":
        barrel_shape = str(culvert.get("barrel_shape", "") or "").strip().lower()
        if barrel_shape == "circular" or shape == "circular":
            return "pipe_culvert"
        return "box_culvert"
    if "inlet" in shape:
        return "inlet"
    if "outlet" in shape:
        return "outlet"
    if "headwall" in shape:
        return "headwall"
    return ""


def _filter_kind_specs(rows, geometry_spec_rows: list[StructureGeometrySpec]) -> list:
    geometry_spec_ids = {str(row.geometry_spec_id) for row in geometry_spec_rows}
    return [
        row
        for row in list(rows or [])
        if str(getattr(row, "geometry_spec_ref", "") or "") in geometry_spec_ids
    ]


def _replace_kind_spec(rows, new_row):
    output = []
    replaced = False
    new_ref = str(getattr(new_row, "geometry_spec_ref", "") or "")
    for row in list(rows or []):
        if str(getattr(row, "geometry_spec_ref", "") or "") == new_ref:
            output.append(new_row)
            replaced = True
        else:
            output.append(row)
    if not replaced:
        output.append(new_row)
    return output


def _kind_detail_field_specs(structure_kind: str) -> list[tuple[str, str]]:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        return [
            ("deck_width", "Deck Width"),
            ("deck_thickness", "Deck Thickness"),
            ("girder_depth", "Girder Depth"),
            ("barrier_height", "Barrier Height"),
            ("clearance_height", "Clearance Height"),
            ("abutment_start_offset", "Abutment Start Offset"),
            ("abutment_end_offset", "Abutment End Offset"),
            ("pier_station_refs", "Pier Station Refs"),
            ("approach_slab_length", "Approach Slab Length"),
            ("bearing_elevation_mode", "Bearing Elevation Mode"),
        ]
    if kind == "culvert":
        return [
            ("barrel_shape", "Barrel Shape"),
            ("barrel_count", "Barrel Count"),
            ("span", "Span"),
            ("rise", "Rise"),
            ("diameter", "Diameter"),
            ("wall_thickness", "Wall Thickness"),
            ("length", "Length"),
            ("invert_elevation", "Invert Elevation"),
            ("headwall_type", "Headwall Type"),
            ("wingwall_type", "Wingwall Type"),
        ]
    if kind in {"retaining_wall", "wall"}:
        return [
            ("wall_height", "Wall Height"),
            ("wall_thickness", "Wall Thickness"),
            ("footing_width", "Footing Width"),
            ("footing_thickness", "Footing Thickness"),
            ("retained_side", "Retained Side"),
            ("top_elevation_mode", "Top Elevation Mode"),
            ("bottom_elevation_mode", "Bottom Elevation Mode"),
            ("batter_slope", "Batter Slope"),
            ("coping_height", "Coping Height"),
            ("drainage_layer_ref", "Drainage Layer Ref"),
        ]
    return []


def _native_detail_field_specs(native_type: str, structure_kind: str) -> list[tuple[str, str]]:
    native = str(native_type or "").strip().lower()
    if native == "box_culvert":
        return [
            ("barrel_count", "Barrel Count"),
            ("span", "Opening Width"),
            ("rise", "Opening Height"),
            ("wall_thickness", "Wall Thickness"),
            ("length", "Length"),
            ("invert_elevation", "Invert Elevation"),
            ("headwall_type", "Headwall Type"),
            ("wingwall_type", "Wingwall Type"),
        ]
    if native == "pipe_culvert":
        return [
            ("barrel_count", "Barrel Count"),
            ("diameter", "Pipe Diameter"),
            ("wall_thickness", "Wall Thickness"),
            ("length", "Length"),
            ("invert_elevation", "Invert Elevation"),
            ("headwall_type", "End Treatment"),
        ]
    if native == "bridge_deck":
        return [
            ("deck_width", "Deck Width"),
            ("deck_thickness", "Deck Thickness"),
            ("girder_depth", "Girder Depth"),
            ("barrier_height", "Barrier Height"),
            ("clearance_height", "Clearance Height"),
            ("approach_slab_length", "Approach Slab Length"),
        ]
    if native == "retaining_wall":
        return [
            ("wall_height", "Wall Height"),
            ("wall_thickness", "Wall Thickness"),
            ("footing_width", "Footing Width"),
            ("footing_thickness", "Footing Thickness"),
            ("retained_side", "Retained Side"),
            ("batter_slope", "Batter Slope"),
            ("coping_height", "Coping Height"),
        ]
    if native == "headwall":
        return [
            ("span", "Opening Width"),
            ("rise", "Opening Height"),
            ("wall_thickness", "Wall Thickness"),
            ("invert_elevation", "Invert Elevation"),
            ("headwall_type", "Headwall Type"),
            ("wingwall_type", "Wingwall Type"),
        ]
    if native == "inlet":
        return [
            ("span", "Inlet Width"),
            ("rise", "Inlet Depth"),
            ("diameter", "Outlet Pipe Diameter"),
            ("wall_thickness", "Wall Thickness"),
            ("invert_elevation", "Invert Elevation"),
            ("headwall_type", "Grate/Cover Type"),
        ]
    if native == "outlet":
        return [
            ("span", "Outlet Width"),
            ("rise", "Outlet Height"),
            ("diameter", "Inlet Pipe Diameter"),
            ("wall_thickness", "Wall Thickness"),
            ("invert_elevation", "Invert Elevation"),
            ("wingwall_type", "Apron/Wingwall Type"),
        ]
    return _kind_detail_field_specs(structure_kind)


def _detail_spec_family(native_type: str, structure_kind: str) -> str:
    native = str(native_type or "").strip().lower()
    if native in {"box_culvert", "pipe_culvert", "headwall", "inlet", "outlet"}:
        return "culvert"
    if native == "bridge_deck":
        return "bridge"
    if native == "retaining_wall":
        return "retaining_wall"
    kind = str(structure_kind or "").strip().lower()
    if kind in {"wall", "retaining_wall"}:
        return "retaining_wall"
    return kind


def _detail_values_with_native_defaults(native_type: str, values: dict[str, str]) -> dict[str, str]:
    native = str(native_type or "").strip().lower()
    output = dict(values or {})
    if native == "box_culvert":
        output["barrel_shape"] = "box"
        output["diameter"] = "0"
    elif native == "pipe_culvert":
        output["barrel_shape"] = "circular"
        output["span"] = "0"
        output["rise"] = "0"
    elif native == "headwall":
        output["barrel_shape"] = "box"
        output.setdefault("length", "0")
        output["diameter"] = "0"
    elif native == "inlet":
        output["barrel_shape"] = "inlet"
        output.setdefault("length", "0")
    elif native == "outlet":
        output["barrel_shape"] = "outlet"
        output.setdefault("length", "0")
        output.setdefault("headwall_type", "")
    return output


def _effective_native_type(
    row: StructureRow,
    geometry_spec: StructureGeometrySpec | None = None,
    culvert_spec: CulvertGeometrySpec | None = None,
) -> str:
    native_type = str(getattr(row, "native_type", "") or "").strip().lower()
    if native_type:
        return native_type
    kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
    shape = str(getattr(geometry_spec, "shape_kind", "") or "").strip().lower() if geometry_spec is not None else ""
    if kind == "bridge":
        return "bridge_deck"
    if kind in {"retaining_wall", "wall"}:
        return "retaining_wall"
    if kind == "culvert":
        barrel_shape = str(getattr(culvert_spec, "barrel_shape", "") or "").strip().lower() if culvert_spec is not None else ""
        return "pipe_culvert" if barrel_shape == "circular" or shape == "circular" else "box_culvert"
    if "inlet" in shape:
        return "inlet"
    if "outlet" in shape:
        return "outlet"
    if "headwall" in shape:
        return "headwall"
    return ""


def _kind_detail_values(
    structure_kind: str,
    geometry_spec_ref: str,
    bridge_rows: list[BridgeGeometrySpec],
    culvert_rows: list[CulvertGeometrySpec],
    retaining_wall_rows: list[RetainingWallGeometrySpec],
) -> dict[str, str]:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        row = _find_kind_spec(bridge_rows, geometry_spec_ref) or BridgeGeometrySpec(geometry_spec_ref=geometry_spec_ref)
        return {
            "deck_width": _format_float(row.deck_width),
            "deck_thickness": _format_float(row.deck_thickness),
            "girder_depth": _format_float(row.girder_depth),
            "barrier_height": _format_float(row.barrier_height),
            "clearance_height": _format_float(row.clearance_height),
            "abutment_start_offset": _format_float(row.abutment_start_offset),
            "abutment_end_offset": _format_float(row.abutment_end_offset),
            "pier_station_refs": ", ".join(list(row.pier_station_refs or [])),
            "approach_slab_length": _format_float(row.approach_slab_length),
            "bearing_elevation_mode": row.bearing_elevation_mode,
        }
    if kind == "culvert":
        row = _find_kind_spec(culvert_rows, geometry_spec_ref) or CulvertGeometrySpec(geometry_spec_ref=geometry_spec_ref)
        return {
            "barrel_shape": row.barrel_shape,
            "barrel_count": str(int(row.barrel_count)),
            "span": _format_float(row.span),
            "rise": _format_float(row.rise),
            "diameter": _format_float(row.diameter),
            "wall_thickness": _format_float(row.wall_thickness),
            "length": _format_float(row.length),
            "invert_elevation": _format_optional_float(row.invert_elevation),
            "headwall_type": row.headwall_type,
            "wingwall_type": row.wingwall_type,
        }
    if kind in {"retaining_wall", "wall"}:
        row = _find_kind_spec(retaining_wall_rows, geometry_spec_ref) or RetainingWallGeometrySpec(geometry_spec_ref=geometry_spec_ref)
        return {
            "wall_height": _format_float(row.wall_height),
            "wall_thickness": _format_float(row.wall_thickness),
            "footing_width": _format_float(row.footing_width),
            "footing_thickness": _format_float(row.footing_thickness),
            "retained_side": row.retained_side,
            "top_elevation_mode": row.top_elevation_mode,
            "bottom_elevation_mode": row.bottom_elevation_mode,
            "batter_slope": _format_float(row.batter_slope),
            "coping_height": _format_float(row.coping_height),
            "drainage_layer_ref": row.drainage_layer_ref,
        }
    return {}


def _find_kind_spec(rows, geometry_spec_ref: str):
    for row in list(rows or []):
        if str(getattr(row, "geometry_spec_ref", "") or "") == str(geometry_spec_ref or ""):
            return row
    return None


def _bridge_spec_from_detail(geometry_spec_ref: str, values: dict[str, str]) -> BridgeGeometrySpec:
    return BridgeGeometrySpec(
        geometry_spec_ref=geometry_spec_ref,
        deck_width=_required_float(values.get("deck_width", "0"), "Deck Width"),
        deck_thickness=_required_float(values.get("deck_thickness", "0"), "Deck Thickness"),
        girder_depth=_required_float(values.get("girder_depth", "0"), "Girder Depth"),
        barrier_height=_required_float(values.get("barrier_height", "0"), "Barrier Height"),
        clearance_height=_required_float(values.get("clearance_height", "0"), "Clearance Height"),
        abutment_start_offset=_required_float(values.get("abutment_start_offset", "0"), "Abutment Start Offset"),
        abutment_end_offset=_required_float(values.get("abutment_end_offset", "0"), "Abutment End Offset"),
        pier_station_refs=_csv_text_values(values.get("pier_station_refs", "")),
        approach_slab_length=_required_float(values.get("approach_slab_length", "0"), "Approach Slab Length"),
        bearing_elevation_mode=str(values.get("bearing_elevation_mode", "") or ""),
    )


def _culvert_spec_from_detail(geometry_spec_ref: str, values: dict[str, str]) -> CulvertGeometrySpec:
    return CulvertGeometrySpec(
        geometry_spec_ref=geometry_spec_ref,
        barrel_shape=str(values.get("barrel_shape", "box") or "box"),
        barrel_count=int(_required_float(values.get("barrel_count", "1"), "Barrel Count")),
        span=_required_float(values.get("span", "0"), "Span"),
        rise=_required_float(values.get("rise", "0"), "Rise"),
        diameter=_required_float(values.get("diameter", "0"), "Diameter"),
        wall_thickness=_required_float(values.get("wall_thickness", "0"), "Wall Thickness"),
        length=_required_float(values.get("length", "0"), "Length"),
        invert_elevation=_optional_float_text(values.get("invert_elevation", "")),
        headwall_type=str(values.get("headwall_type", "") or ""),
        wingwall_type=str(values.get("wingwall_type", "") or ""),
    )


def _retaining_wall_spec_from_detail(geometry_spec_ref: str, values: dict[str, str]) -> RetainingWallGeometrySpec:
    return RetainingWallGeometrySpec(
        geometry_spec_ref=geometry_spec_ref,
        wall_height=_required_float(values.get("wall_height", "0"), "Wall Height"),
        wall_thickness=_required_float(values.get("wall_thickness", "0"), "Wall Thickness"),
        footing_width=_required_float(values.get("footing_width", "0"), "Footing Width"),
        footing_thickness=_required_float(values.get("footing_thickness", "0"), "Footing Thickness"),
        retained_side=str(values.get("retained_side", "") or ""),
        top_elevation_mode=str(values.get("top_elevation_mode", "") or ""),
        bottom_elevation_mode=str(values.get("bottom_elevation_mode", "") or ""),
        batter_slope=_required_float(values.get("batter_slope", "0"), "Batter Slope"),
        coping_height=_required_float(values.get("coping_height", "0"), "Coping Height"),
        drainage_layer_ref=str(values.get("drainage_layer_ref", "") or ""),
    )


def _csv_text_values(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _document_station_range(document, alignment_obj=None) -> tuple[float, float]:
    stationing = find_v1_stationing(document)
    stations = list(getattr(stationing, "StationValues", []) or []) if stationing is not None else []
    values = []
    for station in stations:
        try:
            values.append(float(station))
        except Exception:
            pass
    if values:
        return min(values), max(values)
    try:
        total_length = float(getattr(alignment_obj, "TotalLength", 0.0) or 0.0)
        if total_length > 0.0:
            return 0.0, total_length
    except Exception:
        pass
    return 0.0, 100.0


def _format_validation_result(structure_model: StructureModel, *, document=None) -> str:
    diagnostics = validate_structure_model(structure_model)
    status = "error" if any(str(row).startswith("error|") for row in diagnostics) else "warning" if diagnostics else "ok"
    lines = ["Validation status: " + status]
    if not diagnostics:
        lines.append("No diagnostics.")
    else:
        lines.append("Diagnostics:")
        lines.extend(f"- {row}" for row in diagnostics)
    package_obj = find_v1_exchange_package(document)
    if package_obj is not None:
        lines.append(
            "Export readiness: "
            + str(getattr(package_obj, "ExportReadinessStatus", "") or "unknown")
            + f" ({int(getattr(package_obj, 'ExportDiagnosticCount', 0) or 0)} diagnostics)"
        )
    else:
        lines.append("Export readiness: not built")
    lines.append(f"Structure rows: {len(list(structure_model.structure_rows or []))}")
    return "\n".join(lines)


def _make_structure_preview_shape(document, structure_model: StructureModel):
    rows = list(getattr(structure_model, "structure_rows", []) or [])
    path = _structure_preview_path_source(document)
    context = _structure_preview_context(structure_model)
    shapes = []
    for row in rows:
        shape = _structure_row_preview_shape(row, path, context)
        if shape is not None:
            shapes.append(shape)
    if not shapes:
        return Part.Shape()
    return Part.Compound(shapes)


def _structure_row_preview_shape(row: StructureRow, path: dict[str, object], context: dict[str, object]):
    placement = getattr(row, "placement", None)
    if placement is None:
        return None
    start_sta = float(getattr(placement, "station_start", 0.0) or 0.0)
    end_sta = float(getattr(placement, "station_end", start_sta) or start_sta)
    if end_sta < start_sta:
        start_sta, end_sta = end_sta, start_sta
    offset = float(getattr(placement, "offset", 0.0) or 0.0)
    profile = _structure_preview_profile(row, context)
    base_z = _structure_preview_base_z(row, context)
    stations = _structure_preview_sample_stations(start_sta, end_sta, path)
    points = [_station_offset_xyz(path, station, offset, base_z) for station in stations]
    segment_shapes = []
    for point0, point1 in zip(points, points[1:]):
        segment = _structure_segment_preview_shape(point0, point1, profile)
        if segment is not None:
            segment_shapes.append(segment)
    if not segment_shapes:
        return None
    return Part.Compound(segment_shapes)


def _structure_segment_preview_shape(point0, point1, profile: dict[str, object]):
    shape_kind = str(profile.get("shape_kind", "") or "").strip().lower()
    if shape_kind in {"circular", "pipe", "round"}:
        return _structure_segment_cylinder(point0, point1, float(profile.get("diameter", 0.0) or 0.0))
    return _structure_segment_prism(
        point0,
        point1,
        float(profile.get("half_width", 0.0) or 0.0),
        float(profile.get("height", 0.0) or 0.0),
    )


def _structure_segment_prism(point0, point1, half_width: float, height: float):
    x0, y0, z0 = point0
    x1, y1, z1 = point1
    dx = float(x1) - float(x0)
    dy = float(y1) - float(y0)
    length = math.hypot(dx, dy)
    if length <= 1.0e-9:
        return None
    nx = -dy / length
    ny = dx / length
    z_base0 = float(z0)
    z_base1 = float(z1)
    corners = [
        App.Vector(x0 + nx * half_width, y0 + ny * half_width, z_base0),
        App.Vector(x1 + nx * half_width, y1 + ny * half_width, z_base1),
        App.Vector(x1 - nx * half_width, y1 - ny * half_width, z_base1),
        App.Vector(x0 - nx * half_width, y0 - ny * half_width, z_base0),
        App.Vector(x0 + nx * half_width, y0 + ny * half_width, z_base0),
    ]
    try:
        face = Part.Face(Part.makePolygon(corners))
        return face.extrude(App.Vector(0.0, 0.0, height))
    except Exception:
        try:
            return Part.makePolygon(corners)
        except Exception:
            return None


def _structure_segment_cylinder(point0, point1, diameter: float):
    x0, y0, z0 = point0
    x1, y1, z1 = point1
    radius = max(float(diameter) / 2.0, 0.1)
    base = App.Vector(float(x0), float(y0), float(z0) + radius)
    direction = App.Vector(float(x1) - float(x0), float(y1) - float(y0), float(z1) - float(z0))
    length = direction.Length
    if length <= 1.0e-9:
        return None
    try:
        return Part.makeCylinder(radius, length, base, direction)
    except Exception:
        return _structure_segment_prism(point0, point1, radius, radius * 2.0)


def _structure_preview_path_source(document) -> dict[str, object]:
    centerline = _applied_section_centerline_path_source(document)
    if centerline is not None:
        return centerline
    alignment_adapter = _station_offset_adapter(document)
    if alignment_adapter is not None:
        return {
            "source": "alignment",
            "adapter": lambda station, offset: (*_station_offset_xy(alignment_adapter, station, offset), 0.0),
            "stations": [],
        }
    return {
        "source": "station_offset_fallback",
        "adapter": lambda station, offset: (float(station), float(offset), 0.0),
        "stations": [],
    }


def _structure_preview_path_source_name(document) -> str:
    return str(_structure_preview_path_source(document).get("source", "") or "")


def _applied_section_centerline_path_source(document) -> dict[str, object] | None:
    applied_obj = find_v1_applied_section_set(document)
    applied = to_applied_section_set(applied_obj)
    if applied is None:
        return None
    frames = []
    for section in list(getattr(applied, "sections", []) or []):
        frame = getattr(section, "frame", None)
        if frame is None:
            continue
        frames.append(
            {
                "station": float(getattr(frame, "station", getattr(section, "station", 0.0)) or 0.0),
                "x": float(getattr(frame, "x", 0.0) or 0.0),
                "y": float(getattr(frame, "y", 0.0) or 0.0),
                "z": float(getattr(frame, "z", 0.0) or 0.0),
                "tangent": float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0),
            }
        )
    frames.sort(key=lambda row: row["station"])
    if len(frames) < 2:
        return None

    def _adapter(station: float, offset: float) -> tuple[float, float, float]:
        return _interpolate_centerline_station_offset(frames, station, offset)

    return {
        "source": "3d_centerline",
        "adapter": _adapter,
        "stations": [row["station"] for row in frames],
    }


def _interpolate_centerline_station_offset(frames: list[dict[str, float]], station: float, offset: float) -> tuple[float, float, float]:
    station = float(station)
    lower = frames[0]
    upper = frames[-1]
    for index in range(len(frames) - 1):
        current = frames[index]
        next_row = frames[index + 1]
        if current["station"] <= station <= next_row["station"]:
            lower = current
            upper = next_row
            break
    span = max(float(upper["station"]) - float(lower["station"]), 0.0)
    ratio = 0.0 if span <= 1.0e-9 else max(0.0, min(1.0, (station - float(lower["station"])) / span))
    x = float(lower["x"]) + (float(upper["x"]) - float(lower["x"])) * ratio
    y = float(lower["y"]) + (float(upper["y"]) - float(lower["y"])) * ratio
    z = float(lower["z"]) + (float(upper["z"]) - float(lower["z"])) * ratio
    dx = float(upper["x"]) - float(lower["x"])
    dy = float(upper["y"]) - float(lower["y"])
    length = math.hypot(dx, dy)
    if length > 1.0e-9:
        nx = -dy / length
        ny = dx / length
    else:
        heading = math.radians(float(lower.get("tangent", 0.0) or 0.0))
        nx = -math.sin(heading)
        ny = math.cos(heading)
    return x + float(offset) * nx, y + float(offset) * ny, z


def _structure_preview_sample_stations(start_sta: float, end_sta: float, path: dict[str, object]) -> list[float]:
    span = max(float(end_sta) - float(start_sta), 0.0)
    if span <= 1.0e-9:
        return [float(start_sta), float(start_sta) + 1.0]
    count = max(2, min(32, int(math.ceil(span / 10.0)) + 1))
    values = [float(start_sta) + span * index / float(count - 1) for index in range(count)]
    for station in list(path.get("stations", []) or []):
        value = float(station)
        if float(start_sta) < value < float(end_sta):
            values.append(value)
    return sorted({round(value, 9) for value in values})


def _station_offset_adapter(document):
    alignment_obj = find_v1_alignment(document)
    alignment_model = to_alignment_model(alignment_obj) if alignment_obj is not None else None
    if alignment_model is None:
        return None
    try:
        return AlignmentEvaluationService().station_offset_adapter(alignment_model)
    except Exception:
        return None


def _station_offset_xy(adapter, station: float, offset: float) -> tuple[float, float]:
    if adapter is not None:
        try:
            x, y = adapter(float(station), float(offset))
            return float(x), float(y)
        except Exception:
            pass
    return float(station), float(offset)


def _station_offset_xyz(path: dict[str, object], station: float, offset: float, base_z: float) -> tuple[float, float, float]:
    adapter = path.get("adapter", None)
    if adapter is not None:
        try:
            x, y, z = adapter(float(station), float(offset))
            return float(x), float(y), float(z) + float(base_z)
        except Exception:
            pass
    return float(station), float(offset), float(base_z)


def _structure_preview_context(structure_model: StructureModel) -> dict[str, object]:
    geometry_specs = {
        str(row.geometry_spec_id): row
        for row in list(getattr(structure_model, "geometry_spec_rows", []) or [])
    }
    return {
        "geometry_specs": geometry_specs,
        "bridge_specs": {
            str(row.geometry_spec_ref): row
            for row in list(getattr(structure_model, "bridge_geometry_spec_rows", []) or [])
        },
        "culvert_specs": {
            str(row.geometry_spec_ref): row
            for row in list(getattr(structure_model, "culvert_geometry_spec_rows", []) or [])
        },
        "retaining_wall_specs": {
            str(row.geometry_spec_ref): row
            for row in list(getattr(structure_model, "retaining_wall_geometry_spec_rows", []) or [])
        },
    }


def _structure_geometry_spec_for_row(row: StructureRow, context: dict[str, object]) -> StructureGeometrySpec | None:
    specs = context.get("geometry_specs", {})
    if not isinstance(specs, dict):
        return None
    spec_ref = str(getattr(row, "geometry_spec_ref", "") or "")
    spec = specs.get(spec_ref)
    if spec is not None:
        return spec
    structure_id = str(getattr(row, "structure_id", "") or "")
    for candidate in specs.values():
        if str(getattr(candidate, "structure_ref", "") or "") == structure_id:
            return candidate
    return None


def _kind_spec_for_ref(values, geometry_spec_ref: str):
    if not isinstance(values, dict):
        return None
    return values.get(str(geometry_spec_ref or ""))


def _structure_preview_review_notes(structure_model: StructureModel, context: dict[str, object]) -> list[str]:
    notes = []
    for row in list(getattr(structure_model, "structure_rows", []) or []):
        structure_id = str(getattr(row, "structure_id", "") or "")
        spec = _structure_geometry_spec_for_row(row, context)
        if spec is None:
            notes.append(f"warning|geometry_spec|{structure_id}|Preview used fallback dimensions because no native geometry spec was found.")
            continue
        if float(getattr(spec, "skew_angle_deg", 0.0) or 0.0) != 0.0:
            notes.append(f"warning|skew_angle|{structure_id}|Preview records skew but does not yet skew generated review geometry.")
        kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
        spec_ref = str(getattr(spec, "geometry_spec_id", "") or "")
        if kind == "culvert":
            culvert = _kind_spec_for_ref(context.get("culvert_specs", {}), spec_ref)
            barrel_shape = str(getattr(culvert, "barrel_shape", "") or getattr(spec, "shape_kind", "") or "")
            if barrel_shape and barrel_shape not in {"box", "rectangular", "circular"}:
                notes.append(f"warning|culvert_shape|{structure_id}|Preview uses a simplified envelope for unsupported culvert shape {barrel_shape}.")
        elif kind not in {"bridge", "retaining_wall", "wall", "utility", "custom"}:
            notes.append(f"warning|structure_kind|{structure_id}|Preview uses a generic envelope for unsupported structure kind {kind}.")
    return notes


def _structure_preview_size(row: StructureRow, context: dict[str, object] | None = None) -> tuple[float, float]:
    profile = _structure_preview_profile(row, context)
    return float(profile.get("half_width", 0.0) or 0.0), float(profile.get("height", 0.0) or 0.0)


def _structure_preview_profile(row: StructureRow, context: dict[str, object] | None = None) -> dict[str, object]:
    context = context or {}
    spec = _structure_geometry_spec_for_row(row, context)
    culvert = _kind_spec_for_ref(context.get("culvert_specs", {}), getattr(row, "geometry_spec_ref", ""))
    width = float(getattr(spec, "width", 0.0) or 0.0) if spec is not None else 0.0
    height = float(getattr(spec, "height", 0.0) or 0.0) if spec is not None else 0.0
    shape_kind = str(getattr(spec, "shape_kind", "") or "")
    kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
    native_type = _effective_native_type(row, spec, culvert)
    if kind == "bridge":
        bridge = _kind_spec_for_ref(context.get("bridge_specs", {}), getattr(row, "geometry_spec_ref", ""))
        width = float(getattr(bridge, "deck_width", 0.0) or width or 10.0) if bridge is not None else width
        height = float(getattr(bridge, "deck_thickness", 0.0) or height or 1.2) if bridge is not None else height
        return {"shape_kind": shape_kind or "deck_slab", "half_width": max(width, 10.0) / 2.0, "height": max(height, 1.2)}
    if kind == "culvert":
        diameter = 0.0
        if culvert is not None:
            barrel_shape = str(getattr(culvert, "barrel_shape", "") or "").strip().lower()
            diameter = float(getattr(culvert, "diameter", 0.0) or 0.0)
            if barrel_shape == "circular" or native_type == "pipe_culvert" or shape_kind == "circular":
                diameter = diameter or width or height or 1.0
                return {
                    "shape_kind": "circular",
                    "diameter": max(diameter, 0.2),
                    "half_width": max(diameter, 0.2) / 2.0,
                    "height": max(diameter, 0.2),
                }
            width = float(getattr(culvert, "span", 0.0) or width or 3.0)
            height = float(getattr(culvert, "rise", 0.0) or height or 1.5)
            shape_kind = barrel_shape or shape_kind
        if native_type == "pipe_culvert" or shape_kind == "circular":
            diameter = width or height or 1.0
            return {
                "shape_kind": "circular",
                "diameter": max(diameter, 0.2),
                "half_width": max(diameter, 0.2) / 2.0,
                "height": max(diameter, 0.2),
            }
        return {"shape_kind": shape_kind or "box", "half_width": max(width, 3.0) / 2.0, "height": max(height, 1.5)}
    if native_type in {"headwall", "inlet", "outlet"}:
        if culvert is not None:
            width = float(getattr(culvert, "span", 0.0) or width or _default_geometry_width_for_native(native_type, kind))
            height = float(getattr(culvert, "rise", 0.0) or height or _default_geometry_height_for_native(native_type, kind))
        return {
            "shape_kind": native_type,
            "half_width": max(width, _default_geometry_width_for_native(native_type, kind)) / 2.0,
            "height": max(height, _default_geometry_height_for_native(native_type, kind)),
        }
    if kind in {"retaining_wall", "wall"}:
        wall = _kind_spec_for_ref(context.get("retaining_wall_specs", {}), getattr(row, "geometry_spec_ref", ""))
        if wall is not None:
            width = float(getattr(wall, "wall_thickness", 0.0) or width or 0.9)
            height = float(getattr(wall, "wall_height", 0.0) or height or 3.0)
        return {"shape_kind": shape_kind or "wall", "half_width": max(width, 0.9) / 2.0, "height": max(height, 3.0)}
    if kind == "utility":
        return {"shape_kind": shape_kind or "envelope", "half_width": max(width, 1.5) / 2.0, "height": max(height, 0.75)}
    return {"shape_kind": shape_kind or "envelope", "half_width": max(width, 4.0) / 2.0, "height": max(height, 1.0)}


def _structure_preview_base_z(row: StructureRow, context: dict[str, object] | None = None) -> float:
    context = context or {}
    spec = _structure_geometry_spec_for_row(row, context)
    base_elevation = getattr(spec, "base_elevation", None) if spec is not None else None
    if base_elevation is not None:
        try:
            return float(base_elevation)
        except Exception:
            pass
    culvert = _kind_spec_for_ref(context.get("culvert_specs", {}), getattr(row, "geometry_spec_ref", ""))
    invert_elevation = getattr(culvert, "invert_elevation", None) if culvert is not None else None
    if invert_elevation is not None:
        try:
            return float(invert_elevation)
        except Exception:
            pass
    placement = getattr(row, "placement", None)
    value = str(getattr(placement, "elevation_reference", "") or "").strip() if placement is not None else ""
    try:
        return float(value)
    except Exception:
        return 0.0


def _style_structure_preview_object(obj) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = True
        vobj.ShapeColor = (0.45, 0.68, 0.95)
        vobj.LineColor = (0.08, 0.18, 0.32)
        vobj.PointColor = (0.95, 0.85, 0.20)
        vobj.Transparency = 35
        vobj.LineWidth = 2.0
    except Exception:
        pass


def _style_connection_point_preview_object(obj) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = True
        vobj.ShapeColor = (0.15, 0.95, 0.65)
        vobj.LineColor = (0.02, 0.35, 0.20)
        vobj.PointColor = (0.95, 0.95, 0.20)
        vobj.Transparency = 10
        vobj.LineWidth = 2.0
    except Exception:
        pass


def _set_preview_string_property(obj, name: str, value: str) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
        except Exception:
            pass
    try:
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyInteger", name, "CorridorRoad", name)
        except Exception:
            pass
    try:
        setattr(obj, name, int(value or 0))
    except Exception:
        pass


def _set_preview_string_list_property(obj, name: str, values: list[str]) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyStringList", name, "CorridorRoad", name)
        except Exception:
            pass
    try:
        setattr(obj, name, [str(value) for value in list(values or [])])
    except Exception:
        pass


def _alignment_id(document) -> str:
    alignment = find_v1_alignment(document)
    return str(getattr(alignment, "AlignmentId", "") or "")


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _required_float(value: object, label: str) -> float:
    try:
        return float(value)
    except Exception:
        raise ValueError(f"{label} must be a number.") from None


def _item_text(table, row: int, col: int) -> str:
    widget = table.cellWidget(row, col)
    if widget is not None and hasattr(widget, "currentText"):
        return str(widget.currentText() or "").strip()
    item = table.item(row, col)
    return str(item.text() if item is not None else "").strip()


def _item_user_data(table, row: int, col: int, role=QtCore.Qt.UserRole) -> str:
    item = table.item(row, col)
    if item is None:
        return ""
    try:
        return str(item.data(role) or "").strip()
    except Exception:
        return ""


def _display_structure_ref(value: object) -> str:
    text = str(value or "").strip()
    prefix = "structure:"
    return text[len(prefix):] if text.startswith(prefix) else text


def _source_structure_ref(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if text.startswith("structure:") else f"structure:{text}"


def _geometry_source_mode(row: StructureRow) -> str:
    mode = str(getattr(row, "geometry_source_mode", "") or "").strip().lower()
    if mode in GEOMETRY_SOURCE_CHOICES:
        return mode
    reference_mode = str(getattr(row, "reference_mode", "") or "").strip().lower()
    geometry_ref = str(getattr(row, "geometry_ref", "") or "").strip()
    if reference_mode in {"source_ref", "reference_geometry", "external_ref"} or geometry_ref:
        return "external_ref"
    return "native"


def _selected_3d_point():
    if Gui is None:
        raise RuntimeError("FreeCAD GUI selection is required for Pick From 3D.")
    selection_ex = []
    try:
        selection_ex = list(Gui.Selection.getSelectionEx() or [])
    except Exception:
        selection_ex = []
    for selection in selection_ex:
        for sub_object in list(getattr(selection, "SubObjects", []) or []):
            point = _point_from_shape_like(sub_object)
            if point is not None:
                return point
        obj = getattr(selection, "Object", None)
        point = _point_from_shape_like(getattr(obj, "Shape", None))
        if point is not None:
            return point
        point = _point_from_shape_like(obj)
        if point is not None:
            return point
    try:
        for obj in list(Gui.Selection.getSelection() or []):
            point = _point_from_shape_like(getattr(obj, "Shape", None))
            if point is not None:
                return point
            point = _point_from_shape_like(obj)
            if point is not None:
                return point
    except Exception:
        pass
    raise RuntimeError("Select a vertex, edge, face, or object in the 3D View first.")


def _point_from_shape_like(value):
    if value is None:
        return None
    point = getattr(value, "Point", None)
    if point is not None:
        return point
    center = getattr(value, "CenterOfMass", None)
    if center is not None:
        return center
    vertexes = list(getattr(value, "Vertexes", []) or [])
    if vertexes:
        return getattr(vertexes[0], "Point", None)
    bound_box = getattr(value, "BoundBox", None)
    if bound_box is not None:
        center = getattr(bound_box, "Center", None)
        if center is not None:
            return center
    placement = getattr(value, "Placement", None)
    base = getattr(placement, "Base", None)
    if base is not None:
        return base
    return None


def _station_offset_from_point(document, point) -> tuple[float, float]:
    alignment = to_alignment_model(find_v1_alignment(document))
    if alignment is None:
        return float(getattr(point, "x", 0.0) or 0.0), float(getattr(point, "y", 0.0) or 0.0)
    projected = _project_xy_to_alignment(alignment, float(getattr(point, "x", 0.0) or 0.0), float(getattr(point, "y", 0.0) or 0.0))
    if projected is None:
        return float(getattr(point, "x", 0.0) or 0.0), float(getattr(point, "y", 0.0) or 0.0)
    return projected


def _project_xy_to_alignment(alignment, x: float, y: float) -> tuple[float, float] | None:
    best = None
    for element in list(getattr(alignment, "geometry_sequence", []) or []):
        x_values = _numeric_values(getattr(element, "geometry_payload", {}).get("x_values", []))
        y_values = _numeric_values(getattr(element, "geometry_payload", {}).get("y_values", []))
        points = list(zip(x_values, y_values))
        if len(points) < 2:
            continue
        geometry_length = _polyline_length(points)
        station_length = float(getattr(element, "station_end", 0.0) or 0.0) - float(getattr(element, "station_start", 0.0) or 0.0)
        if geometry_length <= 1.0e-12 or station_length <= 1.0e-12:
            continue
        traversed = 0.0
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            dx = float(x1) - float(x0)
            dy = float(y1) - float(y0)
            seg_len_sq = dx * dx + dy * dy
            if seg_len_sq <= 1.0e-12:
                continue
            raw_t = ((float(x) - float(x0)) * dx + (float(y) - float(y0)) * dy) / seg_len_sq
            t = min(max(raw_t, 0.0), 1.0)
            px = float(x0) + dx * t
            py = float(y0) + dy * t
            dist_sq = (float(x) - px) ** 2 + (float(y) - py) ** 2
            seg_len = seg_len_sq ** 0.5
            geometry_offset = traversed + seg_len * t
            station = float(getattr(element, "station_start", 0.0) or 0.0) + (geometry_offset / geometry_length) * station_length
            normal_x = -dy / seg_len
            normal_y = dx / seg_len
            offset = (float(x) - px) * normal_x + (float(y) - py) * normal_y
            if best is None or dist_sq < best[0]:
                best = (dist_sq, station, offset)
            traversed += seg_len
    if best is None:
        return None
    return float(best[1]), float(best[2])


def _numeric_values(values) -> list[float]:
    result: list[float] = []
    for value in list(values or []):
        try:
            result.append(float(value))
        except Exception:
            continue
    return result


def _polyline_length(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        total += ((float(x1) - float(x0)) ** 2 + (float(y1) - float(y0)) ** 2) ** 0.5
    return total


def _filtered_connection_points(
    rows: list[StructureConnectionPoint],
    *,
    structure_ref: str = "",
    connection_point_ref: str = "",
) -> list[StructureConnectionPoint]:
    structure_ref = str(structure_ref or "")
    connection_point_ref = str(connection_point_ref or "")
    output = []
    for row in list(rows or []):
        if structure_ref and str(getattr(row, "structure_ref", "") or "") != structure_ref:
            continue
        if connection_point_ref and str(getattr(row, "connection_point_id", "") or "") != connection_point_ref:
            continue
        output.append(row)
    return output


def _connection_point_xyz(document, point: StructureConnectionPoint) -> tuple[float, float, float]:
    station = float(getattr(point, "station", 0.0) or 0.0)
    offset = float(getattr(point, "offset", 0.0) or 0.0)
    z_value = getattr(point, "invert_elevation", None)
    if z_value is None:
        z_value = getattr(point, "elevation", None)
    z = float(z_value if z_value is not None else 0.0)
    alignment = to_alignment_model(find_v1_alignment(document))
    if alignment is None:
        return station, offset, z
    try:
        x, y = AlignmentEvaluationService().station_offset_to_xy(alignment, station, offset)
        return float(x), float(y), z
    except Exception:
        return station, offset, z


def _connection_point_marker_radius(point: StructureConnectionPoint) -> float:
    diameter = float(getattr(point, "diameter", 0.0) or 0.0)
    width = float(getattr(point, "width", 0.0) or 0.0)
    height = float(getattr(point, "height", 0.0) or 0.0)
    reference_size = max(diameter, width, height, 0.5)
    return max(0.2, min(reference_size * 0.2, 1.5))


def _derive_default_connection_points_for_row(
    row: StructureRow,
    geometry_spec: StructureGeometrySpec | None,
    culvert_spec: CulvertGeometrySpec | None,
) -> list[StructureConnectionPoint]:
    structure_ref = str(getattr(row, "structure_id", "") or "")
    if not structure_ref:
        return []
    placement = getattr(row, "placement", None)
    if placement is None:
        return []
    kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
    start = float(getattr(placement, "station_start", 0.0) or 0.0)
    end = float(getattr(placement, "station_end", start) or start)
    offset = float(getattr(placement, "offset", 0.0) or 0.0)
    region_ref = ""
    base_id = structure_ref.split(":")[-1]
    width = float(getattr(geometry_spec, "width", 0.0) or 0.0)
    height = float(getattr(geometry_spec, "height", 0.0) or 0.0)
    shape = str(getattr(geometry_spec, "shape_kind", "") or "")
    invert = getattr(culvert_spec, "invert_elevation", None) if culvert_spec is not None else None
    diameter = 0.0
    native_type = _effective_native_type(row, geometry_spec, culvert_spec)
    if culvert_spec is not None:
        barrel_shape = str(getattr(culvert_spec, "barrel_shape", "") or "").strip().lower()
        diameter = float(getattr(culvert_spec, "diameter", 0.0) or 0.0)
        if barrel_shape == "circular" or native_type == "pipe_culvert":
            shape = "circular"
            diameter = float(diameter or width or height or 0.0)
            width = 0.0
            height = 0.0
        else:
            shape = shape or "box"
            width = float(getattr(culvert_spec, "span", 0.0) or width)
            height = float(getattr(culvert_spec, "rise", 0.0) or height)
    if kind == "culvert" or native_type in {"box_culvert", "pipe_culvert"}:
        return [
            StructureConnectionPoint(
                connection_point_id=f"connection:{base_id}:upstream",
                structure_ref=structure_ref,
                point_role="upstream",
                station=start,
                offset=offset,
                invert_elevation=invert,
                diameter=diameter,
                width=width,
                height=height,
                shape_kind=shape or "box",
                direction="upstream",
                connection_order=1,
                region_ref=region_ref,
            ),
            StructureConnectionPoint(
                connection_point_id=f"connection:{base_id}:downstream",
                structure_ref=structure_ref,
                point_role="downstream",
                station=end,
                offset=offset,
                invert_elevation=invert,
                diameter=diameter,
                width=width,
                height=height,
                shape_kind=shape or "box",
                direction="downstream",
                connection_order=2,
                region_ref=region_ref,
            ),
        ]
    if kind == "inlet" or native_type == "inlet":
        return [
            StructureConnectionPoint(
                connection_point_id=f"connection:{base_id}:inlet",
                structure_ref=structure_ref,
                point_role="inlet",
                station=start,
                offset=offset,
                invert_elevation=invert,
                diameter=0.0,
                width=width,
                height=height,
                shape_kind=shape or "box",
                direction="in",
                connection_order=1,
                region_ref=region_ref,
            ),
            StructureConnectionPoint(
                connection_point_id=f"connection:{base_id}:pipe-out",
                structure_ref=structure_ref,
                point_role="pipe_out",
                station=end,
                offset=offset,
                invert_elevation=invert,
                diameter=diameter,
                width=0.0 if diameter else width,
                height=0.0 if diameter else height,
                shape_kind="circular" if diameter else shape or "box",
                direction="out",
                connection_order=2,
                region_ref=region_ref,
            ),
        ]
    if kind == "headwall" or native_type == "headwall":
        return [
            StructureConnectionPoint(
                connection_point_id=f"connection:{base_id}:pipe-in",
                structure_ref=structure_ref,
                point_role="pipe_in",
                station=start,
                offset=offset,
                invert_elevation=invert,
                diameter=diameter,
                width=0.0 if diameter else width,
                height=0.0 if diameter else height,
                shape_kind="circular" if diameter else shape or "box",
                direction="in",
                connection_order=1,
                region_ref=region_ref,
            ),
            StructureConnectionPoint(
                connection_point_id=f"connection:{base_id}:discharge",
                structure_ref=structure_ref,
                point_role="discharge",
                station=end,
                offset=offset,
                invert_elevation=invert,
                width=width,
                height=height,
                shape_kind=shape or "headwall",
                direction="out",
                connection_order=2,
                region_ref=region_ref,
            ),
        ]
    if kind == "outlet" or native_type == "outlet":
        return [
            StructureConnectionPoint(
                connection_point_id=f"connection:{base_id}:pipe-in",
                structure_ref=structure_ref,
                point_role="pipe_in",
                station=start,
                offset=offset,
                invert_elevation=invert,
                diameter=diameter,
                width=0.0 if diameter else width,
                height=0.0 if diameter else height,
                shape_kind="circular" if diameter else shape or "box",
                direction="in",
                connection_order=1,
                region_ref=region_ref,
            ),
            StructureConnectionPoint(
                connection_point_id=f"connection:{base_id}:discharge",
                structure_ref=structure_ref,
                point_role="discharge",
                station=end,
                offset=offset,
                invert_elevation=invert,
                width=width,
                height=height,
                shape_kind=shape or "box",
                direction="out",
                connection_order=2,
                region_ref=region_ref,
            ),
        ]
    return []


def _format_float(value: float) -> str:
    return f"{float(value):.3f}"


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return _format_float(float(value))


def _optional_float_text(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _required_float(text, "Optional elevation")


def _default_shape_kind(structure_kind: str) -> str:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        return "deck_slab"
    if kind == "culvert":
        return "box"
    if kind in {"retaining_wall", "wall"}:
        return "wall"
    if kind == "utility":
        return "envelope"
    return "envelope"


def _default_shape_kind_for_native(native_type: str, structure_kind: str) -> str:
    native = str(native_type or "").strip().lower()
    if native == "box_culvert":
        return "box"
    if native == "pipe_culvert":
        return "circular"
    if native == "bridge_deck":
        return "deck_slab"
    if native == "retaining_wall":
        return "wall"
    if native == "headwall":
        return "headwall"
    if native == "inlet":
        return "inlet"
    if native == "outlet":
        return "outlet"
    return _default_shape_kind(structure_kind)


def _default_geometry_width(structure_kind: str) -> float:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        return 10.0
    if kind == "culvert":
        return 3.0
    if kind in {"retaining_wall", "wall"}:
        return 0.9
    if kind == "utility":
        return 1.5
    return 4.0


def _default_geometry_width_for_native(native_type: str, structure_kind: str) -> float:
    native = str(native_type or "").strip().lower()
    if native == "box_culvert":
        return 3.0
    if native == "pipe_culvert":
        return 1.0
    if native == "bridge_deck":
        return 10.0
    if native == "retaining_wall":
        return 0.9
    if native == "headwall":
        return 4.0
    if native == "inlet":
        return 1.2
    if native == "outlet":
        return 1.5
    return _default_geometry_width(structure_kind)


def _default_geometry_height(structure_kind: str) -> float:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        return 1.2
    if kind == "culvert":
        return 2.0
    if kind in {"retaining_wall", "wall"}:
        return 3.0
    if kind == "utility":
        return 1.5
    return 1.0


def _default_geometry_height_for_native(native_type: str, structure_kind: str) -> float:
    native = str(native_type or "").strip().lower()
    if native == "box_culvert":
        return 2.0
    if native == "pipe_culvert":
        return 1.0
    if native == "bridge_deck":
        return 1.2
    if native == "retaining_wall":
        return 3.0
    if native == "headwall":
        return 2.0
    if native == "inlet":
        return 1.2
    if native == "outlet":
        return 1.2
    return _default_geometry_height(structure_kind)


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditStructures", CmdV1StructureEditor())

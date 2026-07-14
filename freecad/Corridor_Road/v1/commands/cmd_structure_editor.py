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
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..objects.obj_exchange_package import find_v1_exchange_package
from ..objects.obj_stationing import find_v1_stationing
from ..objects.obj_structure import (  # noqa: F401 - runtime-injected UI collaborator
    create_or_update_v1_structure_model_object,
    find_v1_structure_model,
    to_structure_model,
    validate_structure_model,
)
from ..services.evaluation import AlignmentEvaluationService
from ..services.editing import prepare_structure_edit
from ..ui.editors.structure_editor import (
    V1StructureEditorTaskPanel,
    configure_structure_editor_task_panel_runtime,
)


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
        "note": "Practical station-banded roadside drainage chain: ditch sections drain to local inlets, inlet pipes connect to one pipe culvert, and the culvert discharges to an outlet headwall.",
        "rows": [
            {
                "id": "structure:inlet-01",
                "kind": "utility",
                "role": "reference",
                "start": 0.23,
                "end": 0.25,
                "offset": -5.2,
                "geometry": "",
                "spec": "geometry-spec:inlet-01",
                "native_type": "inlet",
                "width": 1.8,
                "height": 1.8,
                "shape": "catch_basin",
                "material": "concrete",
                "notes": "Roadside inlet collecting the first ditch station band.",
                "connection_points": [
                    {
                        "role": "inlet",
                        "id": "connection:inlet-01:ditch-in",
                        "at": "start",
                        "width": 1.8,
                        "height": 0.8,
                        "shape": "ditch_inlet",
                        "direction": "in",
                    },
                    {
                        "role": "pipe_out",
                        "id": "connection:inlet-01:pipe-out",
                        "at": "end",
                        "diameter": 1.0,
                        "shape": "circular",
                        "direction": "out",
                    },
                ],
            },
            {
                "id": "structure:inlet-02",
                "kind": "utility",
                "role": "reference",
                "start": 0.37,
                "end": 0.39,
                "offset": -5.2,
                "geometry": "",
                "spec": "geometry-spec:inlet-02",
                "native_type": "inlet",
                "width": 1.8,
                "height": 1.8,
                "shape": "catch_basin",
                "material": "concrete",
                "notes": "Roadside inlet collecting the second ditch station band.",
                "connection_points": [
                    {
                        "role": "inlet",
                        "id": "connection:inlet-02:ditch-in",
                        "at": "start",
                        "width": 1.8,
                        "height": 0.8,
                        "shape": "ditch_inlet",
                        "direction": "in",
                    },
                    {
                        "role": "pipe_in",
                        "id": "connection:inlet-02:pipe-in",
                        "at": "start",
                        "diameter": 0.9,
                        "shape": "circular",
                        "direction": "in",
                    },
                    {
                        "role": "pipe_out",
                        "id": "connection:inlet-02:pipe-out",
                        "at": "end",
                        "diameter": 0.9,
                        "shape": "circular",
                        "direction": "out",
                    },
                ],
            },
            {
                "id": "structure:inlet-03",
                "kind": "utility",
                "role": "reference",
                "start": 0.51,
                "end": 0.53,
                "offset": -5.2,
                "geometry": "",
                "spec": "geometry-spec:inlet-03",
                "native_type": "inlet",
                "width": 1.8,
                "height": 1.8,
                "shape": "catch_basin",
                "material": "concrete",
                "notes": "Roadside inlet collecting the third ditch station band before the culvert.",
                "connection_points": [
                    {
                        "role": "inlet",
                        "id": "connection:inlet-03:ditch-in",
                        "at": "start",
                        "width": 1.8,
                        "height": 0.8,
                        "shape": "ditch_inlet",
                        "direction": "in",
                    },
                    {
                        "role": "pipe_in",
                        "id": "connection:inlet-03:pipe-in",
                        "at": "start",
                        "diameter": 0.9,
                        "shape": "circular",
                        "direction": "in",
                    },
                    {
                        "role": "pipe_out",
                        "id": "connection:inlet-03:pipe-out",
                        "at": "end",
                        "diameter": 1.2,
                        "shape": "circular",
                        "direction": "out",
                    },
                ],
            },
            {
                "id": "structure:culvert-01",
                "kind": "culvert",
                "role": "clearance_control",
                "start": 0.62,
                "end": 0.72,
                "offset": 0.0,
                "geometry": "",
                "spec": "geometry-spec:culvert-01",
                "native_type": "pipe_culvert",
                "width": 1.2,
                "height": 1.2,
                "shape": "circular_pipe",
                "material": "concrete",
                "culvert": {
                    "barrel_shape": "circular",
                    "barrel_count": 1,
                    "diameter": 1.2,
                    "wall_thickness": 0.15,
                    "length": 12.0,
                    "headwall_type": "flared",
                    "wingwall_type": "short",
                },
                "notes": "Circular pipe culvert/cross-drain carrying collected ditch flow under the road.",
                "connection_points": [
                    {
                        "role": "pipe_in",
                        "id": "connection:culvert-01:pipe-in",
                        "at": "start",
                        "offset": 0.0,
                        "diameter": 1.2,
                        "shape": "circular",
                        "direction": "in",
                    },
                    {
                        "role": "pipe_out",
                        "id": "connection:culvert-01:pipe-out",
                        "at": "end",
                        "offset": 0.0,
                        "diameter": 1.2,
                        "shape": "circular",
                        "direction": "out",
                    },
                ],
            },
            {
                "id": "structure:outlet-01",
                "kind": "utility",
                "role": "reference",
                "start": 0.78,
                "end": 0.82,
                "offset": 6.4,
                "geometry": "",
                "spec": "geometry-spec:outlet-01",
                "native_type": "outlet",
                "width": 2.8,
                "height": 2.0,
                "shape": "outlet_headwall",
                "material": "concrete",
                "notes": "Outlet headwall and outfall discharge point downstream of the culvert.",
                "connection_points": [
                    {
                        "role": "pipe_in",
                        "id": "connection:outlet-01:pipe-in",
                        "at": "start",
                        "diameter": 1.2,
                        "shape": "circular",
                        "direction": "in",
                    },
                    {
                        "role": "discharge",
                        "id": "connection:outlet-01:outfall",
                        "at": "end",
                        "width": 2.4,
                        "height": 1.0,
                        "shape": "outfall",
                        "direction": "out",
                    },
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
    prepared = prepare_structure_edit(structure_model)
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
        structure_model=prepared.model,
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
    row_preview_objects = _create_structure_row_preview_objects(
        document,
        structure_model,
        path=_structure_preview_path_source(document),
        context=context,
        project=project,
    )
    _set_preview_string_list_property(obj, "LinkedPreviewObjects", [row.Name for row in row_preview_objects])
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


def _create_structure_row_preview_objects(
    document,
    structure_model: StructureModel,
    *,
    path: dict[str, object],
    context: dict[str, object],
    project=None,
) -> list[object]:
    objects: list[object] = []
    for row in list(getattr(structure_model, "structure_rows", []) or []):
        structure_id = str(getattr(row, "structure_id", "") or "")
        if not structure_id:
            continue
        shape = _structure_row_preview_shape(row, path, context)
        if shape is None:
            continue
        object_name = "V1StructurePreview_" + _safe_object_suffix(structure_id)
        obj = document.getObject(object_name)
        if obj is None:
            obj = document.addObject("Part::Feature", object_name)
        obj.Label = "Structure - " + _display_structure_ref(structure_id)
        obj.Shape = shape
        _set_preview_string_property(obj, "CRRecordKind", "v1_structure_row_preview")
        _set_preview_string_property(obj, "V1ObjectType", "V1StructureRowPreview")
        _set_preview_string_property(obj, "StructureModelId", str(getattr(structure_model, "structure_model_id", "") or ""))
        _set_preview_string_property(obj, "StructureRef", structure_id)
        _set_preview_string_property(obj, "PreviewPathSource", str(path.get("source", "") or ""))
        _style_structure_preview_object(obj)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(document), obj)
        except Exception:
            pass
        objects.append(obj)
    return objects


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
        shapes.append(_connection_point_marker_shape(point, float(x), float(y), float(z)))
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
    elevation = spec.get("elevation", "")
    invert = spec.get("invert_elevation", None)
    notes = str(spec.get("notes", "") or "")
    if _optional_float_text(elevation) is None and (invert is None or _optional_float_text(invert) is None):
        notes = (notes + ";vertical_source=centerline3d").strip(";")
    return StructureConnectionPoint(
        connection_point_id=point_id,
        structure_ref=structure_ref,
        point_role=role,
        station=station,
        offset=offset,
        elevation=_optional_float_text(elevation),
        invert_elevation=_optional_float_text(invert) if invert is not None else None,
        diameter=diameter,
        width=width,
        height=height,
        shape_kind=shape,
        direction=str(spec.get("direction", "") or ""),
        connection_order=connection_order,
        region_ref="",
        notes=notes,
    )


def _normalized_connection_point_rows_for_structures(
    connection_point_rows: list[StructureConnectionPoint],
    structure_rows: list[StructureRow],
) -> list[StructureConnectionPoint]:
    structures = {
        str(getattr(row, "structure_id", "") or "").strip(): row
        for row in list(structure_rows or [])
        if str(getattr(row, "structure_id", "") or "").strip()
    }
    output: list[StructureConnectionPoint] = []
    for point in list(connection_point_rows or []):
        structure = structures.get(str(getattr(point, "structure_ref", "") or "").strip())
        if structure is None:
            output.append(point)
            continue
        placement = getattr(structure, "placement", None)
        if placement is None:
            output.append(point)
            continue
        start = float(getattr(placement, "station_start", 0.0) or 0.0)
        end = float(getattr(placement, "station_end", start) or start)
        lower = min(start, end)
        upper = max(start, end)
        station = float(getattr(point, "station", 0.0) or 0.0)
        tolerance = 1.0e-6
        if lower - tolerance <= station <= upper + tolerance:
            output.append(point)
            continue
        output.append(
            StructureConnectionPoint(
                connection_point_id=str(getattr(point, "connection_point_id", "") or ""),
                structure_ref=str(getattr(point, "structure_ref", "") or ""),
                point_role=str(getattr(point, "point_role", "") or ""),
                station=_station_for_connection_point_inside_structure(point, lower=lower, upper=upper),
                offset=float(getattr(point, "offset", 0.0) or 0.0),
                elevation=getattr(point, "elevation", None),
                invert_elevation=getattr(point, "invert_elevation", None),
                diameter=float(getattr(point, "diameter", 0.0) or 0.0),
                width=float(getattr(point, "width", 0.0) or 0.0),
                height=float(getattr(point, "height", 0.0) or 0.0),
                shape_kind=str(getattr(point, "shape_kind", "") or ""),
                direction=str(getattr(point, "direction", "") or ""),
                connection_order=int(getattr(point, "connection_order", 0) or 0),
                region_ref=str(getattr(point, "region_ref", "") or ""),
                notes=str(getattr(point, "notes", "") or ""),
            )
        )
    return output


def _station_for_connection_point_inside_structure(point: StructureConnectionPoint, *, lower: float, upper: float) -> float:
    role = str(getattr(point, "point_role", "") or "").strip().lower()
    direction = str(getattr(point, "direction", "") or "").strip().lower()
    point_id = str(getattr(point, "connection_point_id", "") or "").strip().lower()
    if direction == "out" or role in {"pipe_out", "discharge", "outlet", "downstream"} or "outfall" in point_id:
        return float(upper)
    if direction == "in" or role in {"pipe_in", "inlet", "upstream"}:
        return float(lower)
    station = float(getattr(point, "station", 0.0) or 0.0)
    return min(max(station, float(lower)), float(upper))


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
        _set_default_detail_value(output, "barrel_count", "1")
        _set_default_detail_value(output, "span", "3.000")
        _set_default_detail_value(output, "rise", "2.000")
        _set_default_detail_value(output, "wall_thickness", "0.300")
        output["diameter"] = "0"
    elif native == "pipe_culvert":
        output["barrel_shape"] = "circular"
        _set_default_detail_value(output, "barrel_count", "1")
        _set_default_detail_value(output, "diameter", "1.200")
        _set_default_detail_value(output, "wall_thickness", "0.120")
        output["span"] = "0"
        output["rise"] = "0"
    elif native == "headwall":
        output["barrel_shape"] = "box"
        _set_default_detail_value(output, "span", "2.800")
        _set_default_detail_value(output, "rise", "2.000")
        _set_default_detail_value(output, "diameter", "1.200")
        _set_default_detail_value(output, "wall_thickness", "0.300")
        output.setdefault("length", "0")
    elif native == "inlet":
        output["barrel_shape"] = "inlet"
        _set_default_detail_value(output, "span", "1.800")
        _set_default_detail_value(output, "rise", "1.800")
        _set_default_detail_value(output, "diameter", "0.900")
        _set_default_detail_value(output, "wall_thickness", "0.200")
        output.setdefault("length", "0")
    elif native == "outlet":
        output["barrel_shape"] = "outlet"
        _set_default_detail_value(output, "span", "2.800")
        _set_default_detail_value(output, "rise", "2.000")
        _set_default_detail_value(output, "diameter", "1.200")
        _set_default_detail_value(output, "wall_thickness", "0.300")
        output.setdefault("length", "0")
        output.setdefault("headwall_type", "")
    return output


def _set_default_detail_value(values: dict[str, str], key: str, default: str) -> None:
    text = str(values.get(key, "") or "").strip()
    if not text:
        values[key] = default
        return
    try:
        if float(text) == 0.0:
            values[key] = default
    except Exception:
        pass


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
    diagnostics = _structure_editor_diagnostics(structure_model, document=document)
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


def _selected_structure_diagnostics(structure_model: StructureModel, structure_ref: str, spec_ref: str = "", *, document=None) -> list[str]:
    structure_ref = str(structure_ref or "").strip()
    spec_ref = str(spec_ref or "").strip()
    if not structure_ref:
        return []
    point_refs = {
        str(getattr(row, "connection_point_id", "") or "").strip()
        for row in list(getattr(structure_model, "connection_point_rows", []) or [])
        if str(getattr(row, "structure_ref", "") or "").strip() == structure_ref
    }
    tokens = {structure_ref, structure_ref.split(":")[-1]}
    if spec_ref:
        tokens.add(spec_ref)
    tokens.update(point_refs)
    diagnostics = []
    for row in _structure_editor_diagnostics(structure_model, document=document):
        text = str(row)
        if any(token and token in text for token in tokens):
            diagnostics.append(text)
    return diagnostics


def _structure_editor_diagnostics(structure_model: StructureModel, *, document=None) -> list[str]:
    diagnostics = list(validate_structure_model(structure_model))
    diagnostics.extend(_external_geometry_mapping_diagnostics(structure_model, document=document))
    return diagnostics


def _external_geometry_mapping_diagnostics(structure_model: StructureModel, *, document=None) -> list[str]:
    if document is None:
        return []
    points_by_structure: dict[str, list[StructureConnectionPoint]] = {}
    for point in list(getattr(structure_model, "connection_point_rows", []) or []):
        structure_ref = str(getattr(point, "structure_ref", "") or "").strip()
        if structure_ref:
            points_by_structure.setdefault(structure_ref, []).append(point)
    diagnostics: list[str] = []
    for row in list(getattr(structure_model, "structure_rows", []) or []):
        if _geometry_source_mode(row) != "external_ref":
            continue
        structure_ref = str(getattr(row, "structure_id", "") or "").strip()
        geometry_ref = str(getattr(row, "geometry_ref", "") or "").strip()
        if not geometry_ref:
            continue
        external_obj = _external_geometry_object(document, geometry_ref)
        if external_obj is None:
            diagnostics.append(
                f"warning|external_geometry_ref_unresolved|{structure_ref}|External geometry reference was not found in the document: {geometry_ref}."
            )
            continue
        bbox = getattr(getattr(external_obj, "Shape", None), "BoundBox", None) or getattr(external_obj, "BoundBox", None)
        if bbox is None:
            diagnostics.append(
                f"warning|external_geometry_bounds_unavailable|{structure_ref}|External geometry reference has no bounding box for connection-point validation."
            )
            continue
        for point in points_by_structure.get(structure_ref, []):
            if not _connection_point_inside_external_bounds(point, bbox):
                point_id = str(getattr(point, "connection_point_id", "") or structure_ref)
                diagnostics.append(
                    f"error|external_connection_point_outside_geometry_bounds|{point_id}|Mapped connection point is outside the external Structure body bounds."
                )
    return diagnostics


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
    if _structure_preview_uses_single_segment(row, profile):
        stations = [start_sta, end_sta]
    else:
        stations = _structure_preview_sample_stations(start_sta, end_sta, path)
    points = [_station_offset_xyz(path, station, offset, base_z) for station in stations]
    segment_shapes = []
    for point0, point1 in zip(points, points[1:]):
        segment = _structure_segment_preview_shape(point0, point1, profile)
        if segment is not None:
            segment_shapes.append(segment)
    segment_shapes.extend(_structure_native_detail_preview_shapes(row, path, context, profile, base_z=base_z))
    if not segment_shapes:
        return None
    return Part.Compound(segment_shapes)


def _structure_preview_uses_single_segment(row: StructureRow, profile: dict[str, object]) -> bool:
    kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
    native_type = str(getattr(row, "native_type", "") or "").strip().lower()
    shape_kind = str(profile.get("shape_kind", "") or "").strip().lower()
    return kind == "culvert" and (native_type == "pipe_culvert" or shape_kind in {"circular", "pipe", "round"})


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
    centerline_result = _centerline3d_result_path_source(document)
    if centerline_result is not None:
        return centerline_result
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


def _centerline3d_result_path_source(document) -> dict[str, object] | None:
    try:
        from .cmd_centerline3d import build_document_centerline3d_result
        from ..services.evaluation import Centerline3DFrameService

        result = build_document_centerline3d_result(document)
    except Exception:
        return None
    point_rows = list(getattr(result, "point_rows", []) or [])
    if str(getattr(result, "status", "") or "") != "ready" or len(point_rows) < 2:
        return None
    frame_service = Centerline3DFrameService()

    def _adapter(station: float, offset: float) -> tuple[float, float, float]:
        frame = frame_service.resolve_station_offset(result, station, offset)
        return float(frame.x), float(frame.y), float(frame.z)

    return {
        "source": "centerline3d_result",
        "adapter": _adapter,
        "stations": [float(getattr(row, "station", 0.0) or 0.0) for row in point_rows],
    }


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
        "source": "applied_section_frame",
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
    connection_points_by_structure: dict[str, list[StructureConnectionPoint]] = {}
    for point in list(getattr(structure_model, "connection_point_rows", []) or []):
        structure_ref = str(getattr(point, "structure_ref", "") or "")
        if structure_ref:
            connection_points_by_structure.setdefault(structure_ref, []).append(point)
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
        "connection_points_by_structure": connection_points_by_structure,
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


def _structure_native_detail_preview_shapes(
    row: StructureRow,
    path: dict[str, object],
    context: dict[str, object],
    profile: dict[str, object],
    *,
    base_z: float,
) -> list[object]:
    native_type = str(getattr(row, "native_type", "") or "").strip().lower()
    shape_kind = str(profile.get("shape_kind", "") or "").strip().lower()
    if native_type == "inlet" or shape_kind in {"inlet", "catch_basin"}:
        return _inlet_detail_preview_shapes(row, path, context, profile, base_z=base_z)
    if native_type == "pipe_culvert" or shape_kind in {"circular", "pipe", "round"}:
        return _pipe_culvert_endpoint_detail_preview_shapes(row, path, context, profile, base_z=base_z)
    if native_type in {"outlet", "headwall"} or shape_kind in {"outlet", "outlet_headwall", "headwall"}:
        return _outlet_headwall_detail_preview_shapes(row, path, context, profile, base_z=base_z)
    return []


def _inlet_detail_preview_shapes(
    row: StructureRow,
    path: dict[str, object],
    context: dict[str, object],
    profile: dict[str, object],
    *,
    base_z: float,
) -> list[object]:
    placement = getattr(row, "placement", None)
    if placement is None:
        return []
    start_sta = float(getattr(placement, "station_start", 0.0) or 0.0)
    end_sta = float(getattr(placement, "station_end", start_sta) or start_sta)
    if end_sta < start_sta:
        start_sta, end_sta = end_sta, start_sta
    offset = float(getattr(placement, "offset", 0.0) or 0.0)
    point0 = _station_offset_xyz(path, start_sta, offset, base_z)
    point1 = _station_offset_xyz(path, end_sta, offset, base_z)
    frame = _preview_segment_frame(point0, point1)
    if frame is None:
        return []
    tangent, normal, length = frame
    half_width = max(float(profile.get("half_width", 0.0) or 0.0), 0.6)
    height = max(float(profile.get("height", 0.0) or 0.0), 0.6)
    top_z = max(float(point0[2]), float(point1[2])) + height
    shapes: list[object] = []

    lid = _structure_segment_prism(
        (point0[0], point0[1], top_z),
        (point1[0], point1[1], top_z),
        half_width * 0.92,
        0.08,
    )
    if lid is not None:
        shapes.append(lid)

    grate_count = 3
    for index in range(1, grate_count + 1):
        ratio = index / float(grate_count + 1)
        center = (
            float(point0[0]) + tangent[0] * length * ratio,
            float(point0[1]) + tangent[1] * length * ratio,
            top_z + 0.10,
        )
        bar = _preview_cylinder_between(
            (
                center[0] - normal[0] * half_width * 0.78,
                center[1] - normal[1] * half_width * 0.78,
                center[2],
            ),
            (
                center[0] + normal[0] * half_width * 0.78,
                center[1] + normal[1] * half_width * 0.78,
                center[2],
            ),
            0.035,
        )
        if bar is not None:
            shapes.append(bar)

    structure_id = str(getattr(row, "structure_id", "") or "")
    connection_points = list(context.get("connection_points_by_structure", {}).get(structure_id, []) or [])
    for point in connection_points:
        role = str(getattr(point, "point_role", "") or "").strip().lower()
        point_sta = float(getattr(point, "station", end_sta) or end_sta)
        point_offset = float(getattr(point, "offset", offset) or offset)
        px, py, pz = _station_offset_xyz(path, point_sta, point_offset, base_z)
        diameter = max(float(getattr(point, "diameter", 0.0) or 0.0), 0.0)
        if role in {"pipe_in", "pipe_out"}:
            direction = tangent if role == "pipe_out" else (-tangent[0], -tangent[1])
            radius = max(diameter / 2.0, 0.18)
            stub_length = max(min(radius * 1.2, 0.8), 0.35)
            z = _connection_point_display_z(point, float(pz)) + radius
            stub = _preview_cylinder_between(
                (px, py, z),
                (px + direction[0] * stub_length, py + direction[1] * stub_length, z),
                radius,
            )
            if stub is not None:
                shapes.append(stub)
        elif role in {"inlet", "ditch_in", "ditch-in"}:
            mouth_center_z = float(pz) + height * 0.45
            mouth = _structure_segment_prism(
                (
                    px - normal[0] * half_width * 0.65,
                    py - normal[1] * half_width * 0.65,
                    mouth_center_z,
                ),
                (
                    px + normal[0] * half_width * 0.65,
                    py + normal[1] * half_width * 0.65,
                    mouth_center_z,
                ),
                0.08,
                0.18,
            )
            if mouth is not None:
                shapes.append(mouth)
    return shapes


def _outlet_headwall_detail_preview_shapes(
    row: StructureRow,
    path: dict[str, object],
    context: dict[str, object],
    profile: dict[str, object],
    *,
    base_z: float,
) -> list[object]:
    placement = getattr(row, "placement", None)
    if placement is None:
        return []
    start_sta = float(getattr(placement, "station_start", 0.0) or 0.0)
    end_sta = float(getattr(placement, "station_end", start_sta) or start_sta)
    if end_sta < start_sta:
        start_sta, end_sta = end_sta, start_sta
    offset = float(getattr(placement, "offset", 0.0) or 0.0)
    point0 = _station_offset_xyz(path, start_sta, offset, base_z)
    point1 = _station_offset_xyz(path, end_sta, offset, base_z)
    frame = _preview_segment_frame(point0, point1)
    if frame is None:
        return []
    tangent, normal, length = frame
    half_width = max(float(profile.get("half_width", 0.0) or 0.0), 0.8)
    height = max(float(profile.get("height", 0.0) or 0.0), 0.8)
    shapes: list[object] = []

    headwall_center = (
        float(point1[0]) - tangent[0] * min(length * 0.15, 0.6),
        float(point1[1]) - tangent[1] * min(length * 0.15, 0.6),
        float(point1[2]),
    )
    wall = _structure_segment_prism(
        (
            headwall_center[0] - normal[0] * half_width,
            headwall_center[1] - normal[1] * half_width,
            headwall_center[2],
        ),
        (
            headwall_center[0] + normal[0] * half_width,
            headwall_center[1] + normal[1] * half_width,
            headwall_center[2],
        ),
        0.12,
        height * 1.12,
    )
    if wall is not None:
        shapes.append(wall)

    apron_length = max(min(length * 0.45, 2.2), 0.8)
    apron_width = half_width * 0.75
    apron = _structure_segment_prism(
        (
            float(point1[0]),
            float(point1[1]),
            float(point1[2]) - 0.04,
        ),
        (
            float(point1[0]) + tangent[0] * apron_length,
            float(point1[1]) + tangent[1] * apron_length,
            float(point1[2]) - 0.04,
        ),
        apron_width,
        0.08,
    )
    if apron is not None:
        shapes.append(apron)

    for side in (-1.0, 1.0):
        sidewall = _structure_segment_prism(
            (
                float(point1[0]) + normal[0] * apron_width * side,
                float(point1[1]) + normal[1] * apron_width * side,
                float(point1[2]),
            ),
            (
                float(point1[0]) + tangent[0] * apron_length + normal[0] * apron_width * side * 1.25,
                float(point1[1]) + tangent[1] * apron_length + normal[1] * apron_width * side * 1.25,
                float(point1[2]),
            ),
            0.06,
            height * 0.35,
        )
        if sidewall is not None:
            shapes.append(sidewall)

    structure_id = str(getattr(row, "structure_id", "") or "")
    connection_points = list(context.get("connection_points_by_structure", {}).get(structure_id, []) or [])
    for point in connection_points:
        role = str(getattr(point, "point_role", "") or "").strip().lower()
        point_sta = float(getattr(point, "station", start_sta if role == "pipe_in" else end_sta) or 0.0)
        point_offset = float(getattr(point, "offset", offset) or offset)
        px, py, pz = _station_offset_xyz(path, point_sta, point_offset, base_z)
        if role == "pipe_in":
            radius = max(float(getattr(point, "diameter", 0.0) or 0.0) / 2.0, 0.18)
            z = _connection_point_display_z(point, float(pz)) + radius
            stub = _preview_cylinder_between(
                (px - tangent[0] * radius * 1.2, py - tangent[1] * radius * 1.2, z),
                (px + tangent[0] * radius * 0.8, py + tangent[1] * radius * 0.8, z),
                radius,
            )
            if stub is not None:
                shapes.append(stub)
        elif role in {"discharge", "outlet"}:
            mouth_width = max(float(getattr(point, "width", 0.0) or 0.0), half_width)
            mouth_height = max(float(getattr(point, "height", 0.0) or 0.0), height * 0.35)
            mouth_z = _connection_point_display_z(point, float(pz)) + mouth_height * 0.35
            mouth = _structure_segment_prism(
                (
                    px - normal[0] * mouth_width * 0.5,
                    py - normal[1] * mouth_width * 0.5,
                    mouth_z,
                ),
                (
                    px + normal[0] * mouth_width * 0.5,
                    py + normal[1] * mouth_width * 0.5,
                    mouth_z,
                ),
                0.10,
                mouth_height * 0.45,
            )
            if mouth is not None:
                shapes.append(mouth)
    return shapes


def _pipe_culvert_endpoint_detail_preview_shapes(
    row: StructureRow,
    path: dict[str, object],
    context: dict[str, object],
    profile: dict[str, object],
    *,
    base_z: float,
) -> list[object]:
    culvert = _kind_spec_for_ref(context.get("culvert_specs", {}), getattr(row, "geometry_spec_ref", ""))
    headwall_type = str(getattr(culvert, "headwall_type", "") or "").strip().lower() if culvert is not None else ""
    wingwall_type = str(getattr(culvert, "wingwall_type", "") or "").strip().lower() if culvert is not None else ""
    if not headwall_type and not wingwall_type:
        return []
    placement = getattr(row, "placement", None)
    if placement is None:
        return []
    start_sta = float(getattr(placement, "station_start", 0.0) or 0.0)
    end_sta = float(getattr(placement, "station_end", start_sta) or start_sta)
    if end_sta < start_sta:
        start_sta, end_sta = end_sta, start_sta
    offset = float(getattr(placement, "offset", 0.0) or 0.0)
    point0 = _station_offset_xyz(path, start_sta, offset, base_z)
    point1 = _station_offset_xyz(path, end_sta, offset, base_z)
    frame = _preview_segment_frame(point0, point1)
    if frame is None:
        return []
    tangent, normal, _length = frame
    diameter = max(float(profile.get("diameter", 0.0) or profile.get("height", 0.0) or 0.0), 0.4)
    half_width = max(diameter * 0.9, 0.6)
    wall_height = max(diameter * 1.45, 0.9)
    shapes: list[object] = []

    endpoints = [
        (point0, (-tangent[0], -tangent[1])),
        (point1, tangent),
    ]
    for endpoint, outward in endpoints:
        wall = _structure_segment_prism(
            (
                float(endpoint[0]) - normal[0] * half_width,
                float(endpoint[1]) - normal[1] * half_width,
                float(endpoint[2]) - diameter * 0.08,
            ),
            (
                float(endpoint[0]) + normal[0] * half_width,
                float(endpoint[1]) + normal[1] * half_width,
                float(endpoint[2]) - diameter * 0.08,
            ),
            0.14,
            wall_height,
        )
        if wall is not None:
            shapes.append(wall)

        if wingwall_type and wingwall_type not in {"none", "no", "false"}:
            wing_length = max(diameter * (1.35 if wingwall_type in {"flared", "long"} else 0.95), 0.8)
            wing_height = wall_height * 0.62
            for side in (-1.0, 1.0):
                wing = _structure_segment_prism(
                    (
                        float(endpoint[0]) + normal[0] * half_width * side,
                        float(endpoint[1]) + normal[1] * half_width * side,
                        float(endpoint[2]) - diameter * 0.05,
                    ),
                    (
                        float(endpoint[0]) + outward[0] * wing_length + normal[0] * half_width * side * 1.35,
                        float(endpoint[1]) + outward[1] * wing_length + normal[1] * half_width * side * 1.35,
                        float(endpoint[2]) - diameter * 0.05,
                    ),
                    0.07,
                    wing_height,
                )
                if wing is not None:
                    shapes.append(wing)
    return shapes


def _preview_segment_frame(point0, point1) -> tuple[tuple[float, float], tuple[float, float], float] | None:
    dx = float(point1[0]) - float(point0[0])
    dy = float(point1[1]) - float(point0[1])
    length = math.hypot(dx, dy)
    if length <= 1.0e-9:
        return None
    tangent = (dx / length, dy / length)
    normal = (-tangent[1], tangent[0])
    return tangent, normal, length


def _preview_cylinder_between(point0, point1, radius: float):
    base = App.Vector(float(point0[0]), float(point0[1]), float(point0[2]))
    direction = App.Vector(
        float(point1[0]) - float(point0[0]),
        float(point1[1]) - float(point0[1]),
        float(point1[2]) - float(point0[2]),
    )
    if direction.Length <= 1.0e-9:
        return None
    try:
        return Part.makeCylinder(max(float(radius), 0.02), direction.Length, base, direction)
    except Exception:
        try:
            return Part.makePolygon([base, base.add(direction)])
        except Exception:
            return None


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
        vobj.ShapeColor = (1.0, 0.68, 0.05)
        vobj.LineColor = (0.05, 0.05, 0.02)
        vobj.PointColor = (1.0, 0.95, 0.05)
        vobj.Transparency = 0
        vobj.LineWidth = 4.0
        vobj.PointSize = 8.0
        try:
            vobj.DisplayMode = "Shaded"
        except Exception:
            pass
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


def _safe_object_suffix(value: object) -> str:
    text = str(value or "").strip()
    output = []
    for char in text:
        output.append(char if char.isalnum() else "_")
    return "".join(output).strip("_") or "unknown"


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


def _selected_3d_object():
    if Gui is None:
        raise RuntimeError("FreeCAD GUI selection is required for Pick External.")
    try:
        selection = list(Gui.Selection.getSelection() or [])
    except Exception:
        selection = []
    for obj in selection:
        if obj is not None:
            return obj
    try:
        selection_ex = list(Gui.Selection.getSelectionEx() or [])
    except Exception:
        selection_ex = []
    for selection_item in selection_ex:
        obj = getattr(selection_item, "Object", None)
        if obj is not None:
            return obj
    raise RuntimeError("Select one FreeCAD object in the 3D View or tree first.")


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


def _external_geometry_object(document, geometry_ref: str):
    if document is None:
        return None
    ref = str(geometry_ref or "").strip()
    if not ref:
        return None
    candidates = [ref]
    if ":" in ref:
        candidates.append(ref.split(":", 1)[1])
    if hasattr(document, "getObject"):
        for candidate in candidates:
            try:
                obj = document.getObject(candidate)
            except Exception:
                obj = None
            if obj is not None:
                return obj
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        label = str(getattr(obj, "Label", "") or "")
        if ref in {name, label} or any(candidate and candidate in {name, label} for candidate in candidates):
            return obj
    return None


def _connection_point_inside_external_bounds(point: StructureConnectionPoint, bbox, *, tolerance: float = 0.05) -> bool:
    x = float(getattr(point, "station", 0.0) or 0.0)
    y = float(getattr(point, "offset", 0.0) or 0.0)
    z_value = getattr(point, "elevation", None)
    if z_value is None:
        z_value = getattr(point, "invert_elevation", None)
    checks = [
        (float(getattr(bbox, "XMin", 0.0) or 0.0) - tolerance) <= x <= (float(getattr(bbox, "XMax", 0.0) or 0.0) + tolerance),
        (float(getattr(bbox, "YMin", 0.0) or 0.0) - tolerance) <= y <= (float(getattr(bbox, "YMax", 0.0) or 0.0) + tolerance),
    ]
    if z_value is not None:
        z = float(z_value)
        checks.append(
            (float(getattr(bbox, "ZMin", 0.0) or 0.0) - tolerance) <= z <= (float(getattr(bbox, "ZMax", 0.0) or 0.0) + tolerance)
        )
    return all(checks)


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
    path = _centerline3d_result_path_source(document)
    if path is not None:
        try:
            x, y, centerline_z = _station_offset_xyz(path, station, offset, 0.0)
            z = _connection_point_display_z(point, float(z_value if z_value is not None else centerline_z))
            return float(x), float(y), z
        except Exception:
            pass
    z = _connection_point_display_z(point, float(z_value if z_value is not None else 0.0))
    alignment = to_alignment_model(find_v1_alignment(document))
    if alignment is None:
        return station, offset, z
    try:
        x, y = AlignmentEvaluationService().station_offset_to_xy(alignment, station, offset)
        return float(x), float(y), z
    except Exception:
        return station, offset, z


def _connection_point_display_z(point: StructureConnectionPoint, z: float) -> float:
    diameter = float(getattr(point, "diameter", 0.0) or 0.0)
    shape_kind = str(getattr(point, "shape_kind", "") or "").strip().lower()
    if diameter <= 0.0:
        return float(z)
    if shape_kind and shape_kind not in {"circular", "pipe", "round", "circular_pipe"}:
        return float(z)
    return float(z) + diameter / 2.0


def _connection_point_marker_radius(point: StructureConnectionPoint) -> float:
    diameter = float(getattr(point, "diameter", 0.0) or 0.0)
    width = float(getattr(point, "width", 0.0) or 0.0)
    height = float(getattr(point, "height", 0.0) or 0.0)
    reference_size = max(diameter, width, height, 0.8)
    return max(0.55, min(reference_size * 0.38, 2.2))


def _connection_point_marker_shape(point: StructureConnectionPoint, x: float, y: float, z: float):
    radius = _connection_point_marker_radius(point)
    center = App.Vector(float(x), float(y), float(z))
    return Part.makeSphere(radius, center)


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


def _mark_auto_native_connection_points(points: list[StructureConnectionPoint]) -> list[StructureConnectionPoint]:
    marked = []
    for point in list(points or []):
        notes = str(getattr(point, "notes", "") or "").strip()
        if "auto_native_default" not in notes:
            notes = (notes + "; " if notes else "") + "auto_native_default"
        marked.append(
            StructureConnectionPoint(
                connection_point_id=point.connection_point_id,
                structure_ref=point.structure_ref,
                point_role=point.point_role,
                station=point.station,
                offset=point.offset,
                elevation=point.elevation,
                invert_elevation=point.invert_elevation,
                shape_kind=point.shape_kind,
                width=point.width,
                height=point.height,
                diameter=point.diameter,
                direction=point.direction,
                connection_order=point.connection_order,
                region_ref=point.region_ref,
                notes=notes,
            )
        )
    return marked


def _format_float(value: float) -> str:
    return f"{float(value):.3f}"


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return _format_float(float(value))


def _optional_float_text(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
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
        return "catch_basin"
    if native == "outlet":
        return "outlet_headwall"
    return _default_shape_kind(structure_kind)


def _default_structure_kind_for_native(native_type: str) -> str:
    native = str(native_type or "").strip().lower()
    if native in {"box_culvert", "pipe_culvert"}:
        return "culvert"
    if native == "bridge_deck":
        return "bridge"
    if native == "retaining_wall":
        return "retaining_wall"
    if native in {"inlet", "outlet", "headwall"}:
        return "utility"
    return ""


def _default_structure_role_for_native(native_type: str) -> str:
    native = str(native_type or "").strip().lower()
    if native in {"box_culvert", "pipe_culvert"}:
        return "clearance_control"
    if native == "bridge_deck":
        return "interface"
    if native == "retaining_wall":
        return "active"
    if native in {"inlet", "outlet", "headwall"}:
        return "reference"
    return ""


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
        return 1.2
    if native == "bridge_deck":
        return 10.0
    if native == "retaining_wall":
        return 0.9
    if native == "headwall":
        return 4.0
    if native == "inlet":
        return 1.8
    if native == "outlet":
        return 2.8
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
        return 1.2
    if native == "bridge_deck":
        return 1.2
    if native == "retaining_wall":
        return 3.0
    if native == "headwall":
        return 2.0
    if native == "inlet":
        return 1.8
    if native == "outlet":
        return 2.0
    return _default_geometry_height(structure_kind)


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


configure_structure_editor_task_panel_runtime(globals())


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditStructures", CmdV1StructureEditor())

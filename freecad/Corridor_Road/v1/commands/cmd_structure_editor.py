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
    RetainingWallGeometrySpec,
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
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


STRUCTURE_GEOMETRY_SPEC_REF_ROLE = QtCore.Qt.UserRole
try:
    STRUCTURE_GEOMETRY_REF_ROLE = int(QtCore.Qt.UserRole) + 1
    STRUCTURE_GEOMETRY_SOURCE_ROLE = int(QtCore.Qt.UserRole) + 2
    STRUCTURE_NATIVE_TYPE_ROLE = int(QtCore.Qt.UserRole) + 3
except Exception:  # pragma: no cover - PySide enum compatibility fallback.
    STRUCTURE_GEOMETRY_REF_ROLE = 257
    STRUCTURE_GEOMETRY_SOURCE_ROLE = 258
    STRUCTURE_NATIVE_TYPE_ROLE = 259

STRUCTURE_KIND_CHOICES = ["bridge", "retaining_wall", "wall", "utility", "custom"]
STRUCTURE_ROLE_CHOICES = ["active", "interface", "clearance_control", "split_zone", "reference"]
LENGTH_MODE_CHOICES = ["station_range", "explicit_length", "reference_geometry"]
VERTICAL_POSITION_MODE_CHOICES = ["profile_frame", "absolute_elevation", "terrain_relative", "structure_reference"]
GEOMETRY_SOURCE_CHOICES = ["native", "external_ref"]
NATIVE_TYPE_CHOICES = [
    "",
    "bridge_deck",
    "retaining_wall",
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
    return StructureModel(
        schema_version=1,
        project_id=_project_id(prj),
        structure_model_id="structures:main",
        alignment_id=alignment_id,
        label="Structures",
        structure_rows=structure_rows,
        geometry_spec_rows=geometry_spec_rows,
        bridge_geometry_spec_rows=_preset_bridge_geometry_spec_rows(preset),
        retaining_wall_geometry_spec_rows=_preset_retaining_wall_geometry_spec_rows(preset),
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
        route_object_to_project_tree(project or find_project(document), obj)
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
            route_object_to_project_tree(project or find_project(document), obj)
        except Exception:
            pass
        objects.append(obj)
    return objects


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


def _native_type_from_preset_spec(spec: dict) -> str:
    explicit = str(spec.get("native_type", "") or "").strip()
    if explicit:
        return explicit
    kind = str(spec.get("kind", "") or "").strip().lower()
    if kind == "bridge":
        return "bridge_deck"
    if kind in {"retaining_wall", "wall"}:
        return "retaining_wall"
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
    return _kind_detail_field_specs(structure_kind)


def _detail_spec_family(native_type: str, structure_kind: str) -> str:
    native = str(native_type or "").strip().lower()
    if native == "bridge_deck":
        return "bridge"
    if native == "retaining_wall":
        return "retaining_wall"
    kind = str(structure_kind or "").strip().lower()
    if kind in {"wall", "retaining_wall"}:
        return "retaining_wall"
    return kind


def _detail_values_with_native_defaults(native_type: str, values: dict[str, str]) -> dict[str, str]:
    """The detail values of a native type; bridge decks and retaining walls need no extra defaults."""

    return dict(values or {})


def _kind_detail_values(
    structure_kind: str,
    geometry_spec_ref: str,
    bridge_rows: list[BridgeGeometrySpec],
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
    tokens = {structure_ref, structure_ref.split(":")[-1]}
    if spec_ref:
        tokens.add(spec_ref)
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
    diagnostics: list[str] = []
    for row in list(getattr(structure_model, "structure_rows", []) or []):
        if _geometry_source_mode(row) != "external_ref":
            continue
        structure_ref = str(getattr(row, "structure_id", "") or "").strip()
        geometry_ref = str(getattr(row, "geometry_ref", "") or "").strip()
        if not geometry_ref:
            continue
        if _external_geometry_object(document, geometry_ref) is None:
            diagnostics.append(
                f"warning|external_geometry_ref_unresolved|{structure_ref}|External geometry reference was not found in the document: {geometry_ref}."
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
    return {
        "geometry_specs": geometry_specs,
        "bridge_specs": {
            str(row.geometry_spec_ref): row
            for row in list(getattr(structure_model, "bridge_geometry_spec_rows", []) or [])
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
        if kind not in {"bridge", "retaining_wall", "wall", "utility", "custom"}:
            notes.append(f"warning|structure_kind|{structure_id}|Preview uses a generic envelope for unsupported structure kind {kind}.")
    return notes


def _structure_preview_profile(row: StructureRow, context: dict[str, object] | None = None) -> dict[str, object]:
    context = context or {}
    spec = _structure_geometry_spec_for_row(row, context)
    width = float(getattr(spec, "width", 0.0) or 0.0) if spec is not None else 0.0
    height = float(getattr(spec, "height", 0.0) or 0.0) if spec is not None else 0.0
    shape_kind = str(getattr(spec, "shape_kind", "") or "")
    kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
    if kind == "bridge":
        bridge = _kind_spec_for_ref(context.get("bridge_specs", {}), getattr(row, "geometry_spec_ref", ""))
        width = float(getattr(bridge, "deck_width", 0.0) or width or 10.0) if bridge is not None else width
        height = float(getattr(bridge, "deck_thickness", 0.0) or height or 1.2) if bridge is not None else height
        return {"shape_kind": shape_kind or "deck_slab", "half_width": max(width, 10.0) / 2.0, "height": max(height, 1.2)}
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
    if kind in {"retaining_wall", "wall"}:
        return "wall"
    return "envelope"


def _default_shape_kind_for_native(native_type: str, structure_kind: str) -> str:
    native = str(native_type or "").strip().lower()
    if native == "bridge_deck":
        return "deck_slab"
    if native == "retaining_wall":
        return "wall"
    return _default_shape_kind(structure_kind)


def _default_structure_kind_for_native(native_type: str) -> str:
    native = str(native_type or "").strip().lower()
    if native == "bridge_deck":
        return "bridge"
    if native == "retaining_wall":
        return "retaining_wall"
    return ""


def _default_structure_role_for_native(native_type: str) -> str:
    native = str(native_type or "").strip().lower()
    if native == "bridge_deck":
        return "interface"
    if native == "retaining_wall":
        return "active"
    return ""


def _default_geometry_width(structure_kind: str) -> float:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        return 10.0
    if kind in {"retaining_wall", "wall"}:
        return 0.9
    if kind == "utility":
        return 1.5
    return 4.0


def _default_geometry_width_for_native(native_type: str, structure_kind: str) -> float:
    native = str(native_type or "").strip().lower()
    if native == "bridge_deck":
        return 10.0
    if native == "retaining_wall":
        return 0.9
    return _default_geometry_width(structure_kind)


def _default_geometry_height(structure_kind: str) -> float:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        return 1.2
    if kind in {"retaining_wall", "wall"}:
        return 3.0
    if kind == "utility":
        return 1.5
    return 1.0


def _default_geometry_height_for_native(native_type: str, structure_kind: str) -> float:
    native = str(native_type or "").strip().lower()
    if native == "bridge_deck":
        return 1.2
    if native == "retaining_wall":
        return 3.0
    return _default_geometry_height(structure_kind)


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


configure_structure_editor_task_panel_runtime(globals())


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditStructures", CmdV1StructureEditor())

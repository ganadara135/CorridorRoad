"""FreeCAD source object for v1 StructureModel rows."""

from __future__ import annotations

import json
from dataclasses import asdict

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.structure_model import (
    BridgeGeometrySpec,
    RetainingWallGeometrySpec,
    StructureConnectionPoint,
    StructureGeometrySpec,
    StructureModel,
    StructurePlacement,
    StructureRow,
    is_removed_drainage_structure,
)
from .persistence_payload_adapter import ensure_model_payload_properties, read_model_payload, write_model_payload
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


# Interaction rules and influence zones were removed on 2026-11-08: they decided no geometry. An
# object saved before still has these properties until it is next written.
_RETIRED_PROPERTIES = (
    "RuleIds",
    "RuleStructureRefs",
    "RuleKinds",
    "RuleTargetScopes",
    "RuleParameters",
    "RuleValues",
    "RuleUnits",
    "RulePriorities",
    "InfluenceZoneIds",
    "InfluenceStructureRefs",
    "InfluenceZoneKinds",
    "InfluenceStationStarts",
    "InfluenceStationEnds",
    "InfluenceOffsetMins",
    "InfluenceOffsetMaxes",
    # culvert specs moved to Drainage on 2026-11-08
    "CulvertGeometrySpecRows",
)

CIRCULAR_CONNECTION_ROLES = {"pipe_in", "pipe_out", "upstream", "downstream"}


class V1StructureModelObject:
    """Document object proxy that stores a v1 StructureModel contract."""

    Type = "V1StructureModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_structure_properties(obj)

    def execute(self, obj):
        ensure_v1_structure_properties(obj)
        return


class ViewProviderV1StructureModel:
    """Simple view provider for v1 Structure source objects."""

    Type = "ViewProviderV1StructureModel"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("structures.svg")
        except Exception:
            return ""


def ensure_v1_structure_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 StructureModel source properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "StructureModelId", "CorridorRoad", "v1 structure model id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "linked alignment id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "StructureCount", "Structures", "structure row count")
    _add_property(obj, "App::PropertyStringList", "StructureIds", "Structures", "structure ids")
    _add_property(obj, "App::PropertyStringList", "StructureKinds", "Structures", "structure kinds")
    _add_property(obj, "App::PropertyStringList", "StructureRoles", "Structures", "structure roles")
    _add_property(obj, "App::PropertyStringList", "PlacementIds", "Placements", "placement ids")
    _add_property(obj, "App::PropertyStringList", "PlacementAlignmentIds", "Placements", "placement alignment ids")
    _add_property(obj, "App::PropertyStringList", "PlacementRegionRefs", "Placements", "placement region refs")
    _add_property(obj, "App::PropertyFloatList", "StationStarts", "Placements", "structure start stations")
    _add_property(obj, "App::PropertyFloatList", "StationEnds", "Placements", "structure end stations")
    _add_property(obj, "App::PropertyFloatList", "Offsets", "Placements", "structure offsets")
    _add_property(obj, "App::PropertyStringList", "ElevationReferences", "Placements", "elevation references")
    _add_property(obj, "App::PropertyStringList", "OrientationModes", "Placements", "orientation modes")
    _add_property(obj, "App::PropertyStringList", "GeometrySpecRefs", "Geometry Specs", "native geometry spec refs")
    _add_property(obj, "App::PropertyStringList", "GeometrySpecIds", "Geometry Specs", "geometry spec ids")
    _add_property(obj, "App::PropertyStringList", "GeometrySpecStructureRefs", "Geometry Specs", "geometry spec structure refs")
    _add_property(obj, "App::PropertyStringList", "GeometrySpecShapeKinds", "Geometry Specs", "geometry spec shape kinds")
    _add_property(obj, "App::PropertyFloatList", "GeometrySpecWidths", "Geometry Specs", "geometry spec widths")
    _add_property(obj, "App::PropertyFloatList", "GeometrySpecHeights", "Geometry Specs", "geometry spec heights")
    _add_property(obj, "App::PropertyStringList", "GeometrySpecLengthModes", "Geometry Specs", "geometry spec length modes")
    _add_property(obj, "App::PropertyFloatList", "GeometrySpecSkewAngles", "Geometry Specs", "geometry spec skew angles")
    _add_property(obj, "App::PropertyStringList", "GeometrySpecVerticalPositionModes", "Geometry Specs", "geometry spec vertical position modes")
    _add_property(obj, "App::PropertyFloatList", "GeometrySpecBaseElevations", "Geometry Specs", "geometry spec base elevations")
    _add_property(obj, "App::PropertyFloatList", "GeometrySpecTopElevations", "Geometry Specs", "geometry spec top elevations")
    _add_property(obj, "App::PropertyStringList", "GeometrySpecMaterials", "Geometry Specs", "geometry spec materials")
    _add_property(obj, "App::PropertyStringList", "GeometrySpecStyleRoles", "Geometry Specs", "geometry spec style roles")
    _add_property(obj, "App::PropertyStringList", "GeometrySpecNotes", "Geometry Specs", "geometry spec notes")
    _add_property(obj, "App::PropertyStringList", "BridgeGeometrySpecRows", "Kind Geometry Specs", "bridge-specific geometry spec rows")
    _add_property(obj, "App::PropertyStringList", "RetainingWallGeometrySpecRows", "Kind Geometry Specs", "retaining-wall-specific geometry spec rows")
    _add_property(obj, "App::PropertyStringList", "GeometryRefs", "References", "geometry refs")
    _add_property(obj, "App::PropertyStringList", "ReferenceModes", "References", "reference modes")
    _add_property(obj, "App::PropertyStringList", "GeometrySourceModes", "References", "geometry source modes")
    _add_property(obj, "App::PropertyStringList", "NativeTypes", "References", "native structure geometry types")
    _add_property(obj, "App::PropertyStringList", "ConnectionPointRows", "Connection Points", "structure connection point rows")
    _add_property(obj, "App::PropertyString", "ValidationStatus", "Diagnostics", "structure validation status")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRows", "Diagnostics", "structure diagnostics")
    ensure_model_payload_properties(obj, add_property=_add_property)

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1StructureModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "StructureModelId", "") or ""):
        obj.StructureModelId = f"structures:{str(getattr(obj, 'Name', '') or 'v1-structures')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_structure_model"
    if not str(getattr(obj, "ValidationStatus", "") or ""):
        obj.ValidationStatus = "empty"


def create_or_update_v1_structure_model_object(
    document=None,
    structure_model: StructureModel | None = None,
    *,
    project=None,
    object_name: str = "V1StructureModel",
    label: str = "Structures",
):
    """Create or update the durable v1 StructureModel source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 StructureModel creation.")
    if structure_model is None:
        structure_model = StructureModel(schema_version=1, project_id=_project_id(project), structure_model_id="structures:main")

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1StructureModelObject(obj)
        try:
            ViewProviderV1StructureModel(obj.ViewObject)
        except Exception:
            pass
    else:
        V1StructureModelObject(obj)
    update_v1_structure_model_object(obj, structure_model, label=label)

    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_structure_model_object(obj, structure_model: StructureModel, *, label: str = "Structures"):
    """Write StructureModel rows into an existing FreeCAD object."""

    _remove_properties(obj, _RETIRED_PROPERTIES)
    ensure_v1_structure_properties(obj)
    rows = list(getattr(structure_model, "structure_rows", []) or [])
    geometry_spec_rows = list(getattr(structure_model, "geometry_spec_rows", []) or [])
    bridge_geometry_spec_rows = list(getattr(structure_model, "bridge_geometry_spec_rows", []) or [])
    retaining_wall_geometry_spec_rows = list(getattr(structure_model, "retaining_wall_geometry_spec_rows", []) or [])
    connection_point_rows = list(getattr(structure_model, "connection_point_rows", []) or [])
    diagnostics = validate_structure_model(structure_model)

    obj.Label = label
    obj.SchemaVersion = int(getattr(structure_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(structure_model, "project_id", "") or "corridorroad-v1")
    obj.StructureModelId = str(getattr(structure_model, "structure_model_id", "") or getattr(obj, "StructureModelId", "") or "structures:main")
    obj.AlignmentId = str(getattr(structure_model, "alignment_id", "") or "")
    obj.CRRecordKind = "v1_structure_model"
    obj.StructureCount = len(rows)
    obj.StructureIds = [str(row.structure_id) for row in rows]
    obj.StructureKinds = [str(row.structure_kind) for row in rows]
    obj.StructureRoles = [str(row.structure_role) for row in rows]
    obj.PlacementIds = [str(row.placement.placement_id) for row in rows]
    obj.PlacementAlignmentIds = [str(row.placement.alignment_id) for row in rows]
    obj.PlacementRegionRefs = [str(getattr(row.placement, "region_ref", "") or "") for row in rows]
    obj.StationStarts = [float(row.placement.station_start) for row in rows]
    obj.StationEnds = [float(row.placement.station_end) for row in rows]
    obj.Offsets = [float(row.placement.offset) for row in rows]
    obj.ElevationReferences = [str(row.placement.elevation_reference) for row in rows]
    obj.OrientationModes = [str(row.placement.orientation_mode) for row in rows]
    obj.GeometrySpecRefs = [str(getattr(row, "geometry_spec_ref", "") or "") for row in rows]
    obj.GeometrySpecIds = [str(row.geometry_spec_id) for row in geometry_spec_rows]
    obj.GeometrySpecStructureRefs = [str(row.structure_ref) for row in geometry_spec_rows]
    obj.GeometrySpecShapeKinds = [str(row.shape_kind) for row in geometry_spec_rows]
    obj.GeometrySpecWidths = [float(row.width) for row in geometry_spec_rows]
    obj.GeometrySpecHeights = [float(row.height) for row in geometry_spec_rows]
    obj.GeometrySpecLengthModes = [str(row.length_mode) for row in geometry_spec_rows]
    obj.GeometrySpecSkewAngles = [float(row.skew_angle_deg) for row in geometry_spec_rows]
    obj.GeometrySpecVerticalPositionModes = [str(row.vertical_position_mode) for row in geometry_spec_rows]
    obj.GeometrySpecBaseElevations = [_optional_float_value(row.base_elevation) for row in geometry_spec_rows]
    obj.GeometrySpecTopElevations = [_optional_float_value(row.top_elevation) for row in geometry_spec_rows]
    obj.GeometrySpecMaterials = [str(row.material) for row in geometry_spec_rows]
    obj.GeometrySpecStyleRoles = [str(row.style_role) for row in geometry_spec_rows]
    obj.GeometrySpecNotes = [str(row.notes) for row in geometry_spec_rows]
    obj.BridgeGeometrySpecRows = [_json_row(row) for row in bridge_geometry_spec_rows]
    obj.RetainingWallGeometrySpecRows = [_json_row(row) for row in retaining_wall_geometry_spec_rows]
    obj.GeometryRefs = [str(row.geometry_ref) for row in rows]
    obj.ReferenceModes = [str(row.reference_mode) for row in rows]
    obj.GeometrySourceModes = [str(getattr(row, "geometry_source_mode", "") or _geometry_source_mode(row)) for row in rows]
    obj.NativeTypes = [str(getattr(row, "native_type", "") or "") for row in rows]
    obj.ConnectionPointRows = [_json_row(row) for row in connection_point_rows]
    obj.ValidationStatus = _validation_status(diagnostics)
    obj.DiagnosticRows = diagnostics
    write_model_payload(
        obj,
        structure_model,
        model_type="StructureModel",
        row_fields=(
            "structure_rows",
            "geometry_spec_rows",
            "bridge_geometry_spec_rows",
            "retaining_wall_geometry_spec_rows",
            "connection_point_rows",
        ),
        required_refs=("project_id", "structure_model_id"),
    )
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_structure_model(obj) -> StructureModel | None:
    """Build a StructureModel from a v1 Structure FreeCAD object."""

    if not _is_v1_structure_model(obj):
        return None
    ensure_v1_structure_properties(obj)
    payload_result = read_model_payload(obj, expected_model_type="StructureModel", model_class=StructureModel)
    if payload_result is not None:
        return payload_result.model if payload_result.accepted else None
    ids = list(getattr(obj, "StructureIds", []) or [])
    starts = _float_list(getattr(obj, "StationStarts", []) or [])
    ends = _float_list(getattr(obj, "StationEnds", []) or [])
    count = max(len(ids), len(starts), len(ends))
    rows: list[StructureRow] = []
    for index in range(count):
        placement = StructurePlacement(
            placement_id=_list_value(getattr(obj, "PlacementIds", []), index, f"placement:{index + 1}"),
            alignment_id=_list_value(getattr(obj, "PlacementAlignmentIds", []), index, str(getattr(obj, "AlignmentId", "") or "")),
            station_start=_float_list_value(starts, index, 0.0),
            station_end=_float_list_value(ends, index, 0.0),
            offset=_float_list_value(getattr(obj, "Offsets", []), index, 0.0),
            elevation_reference=_list_value(getattr(obj, "ElevationReferences", []), index, ""),
            orientation_mode=_list_value(getattr(obj, "OrientationModes", []), index, "alignment"),
            region_ref=_list_value(getattr(obj, "PlacementRegionRefs", []), index, ""),
        )
        rows.append(
            StructureRow(
                structure_id=_list_value(ids, index, f"structure:{index + 1}"),
                structure_kind=_list_value(getattr(obj, "StructureKinds", []), index, "bridge"),
                structure_role=_list_value(getattr(obj, "StructureRoles", []), index, "active"),
                placement=placement,
                geometry_spec_ref=_list_value(getattr(obj, "GeometrySpecRefs", []), index, ""),
                geometry_ref=_list_value(getattr(obj, "GeometryRefs", []), index, ""),
                reference_mode=_list_value(getattr(obj, "ReferenceModes", []), index, "native"),
                geometry_source_mode=_list_value(getattr(obj, "GeometrySourceModes", []), index, ""),
                native_type=_list_value(getattr(obj, "NativeTypes", []), index, ""),
            )
        )

    geometry_spec_rows: list[StructureGeometrySpec] = []
    geometry_spec_ids = list(getattr(obj, "GeometrySpecIds", []) or [])
    base_elevations = _float_list(getattr(obj, "GeometrySpecBaseElevations", []) or [])
    top_elevations = _float_list(getattr(obj, "GeometrySpecTopElevations", []) or [])
    for index, geometry_spec_id in enumerate(geometry_spec_ids):
        geometry_spec_rows.append(
            StructureGeometrySpec(
                geometry_spec_id=str(geometry_spec_id),
                structure_ref=_list_value(getattr(obj, "GeometrySpecStructureRefs", []), index, ""),
                shape_kind=_list_value(getattr(obj, "GeometrySpecShapeKinds", []), index, ""),
                width=_float_list_value(getattr(obj, "GeometrySpecWidths", []), index, 0.0),
                height=_float_list_value(getattr(obj, "GeometrySpecHeights", []), index, 0.0),
                length_mode=_list_value(getattr(obj, "GeometrySpecLengthModes", []), index, "station_range"),
                skew_angle_deg=_float_list_value(getattr(obj, "GeometrySpecSkewAngles", []), index, 0.0),
                vertical_position_mode=_list_value(getattr(obj, "GeometrySpecVerticalPositionModes", []), index, "profile_frame"),
                base_elevation=_none_if_blank_offset(base_elevations, index),
                top_elevation=_none_if_blank_offset(top_elevations, index),
                material=_list_value(getattr(obj, "GeometrySpecMaterials", []), index, ""),
                style_role=_list_value(getattr(obj, "GeometrySpecStyleRoles", []), index, ""),
                notes=_list_value(getattr(obj, "GeometrySpecNotes", []), index, ""),
            )
        )

    bridge_geometry_spec_rows = [
        BridgeGeometrySpec(**row)
        for row in _json_rows(getattr(obj, "BridgeGeometrySpecRows", []) or [])
    ]
    retaining_wall_geometry_spec_rows = [
        RetainingWallGeometrySpec(**row)
        for row in _json_rows(getattr(obj, "RetainingWallGeometrySpecRows", []) or [])
    ]
    connection_point_rows = [
        StructureConnectionPoint(**row)
        for row in _json_rows(getattr(obj, "ConnectionPointRows", []) or [])
    ]

    return StructureModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        structure_model_id=str(getattr(obj, "StructureModelId", "") or "structures:main"),
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        label=str(getattr(obj, "Label", "") or "Structures"),
        structure_rows=rows,
        geometry_spec_rows=geometry_spec_rows,
        bridge_geometry_spec_rows=bridge_geometry_spec_rows,
        retaining_wall_geometry_spec_rows=retaining_wall_geometry_spec_rows,
        connection_point_rows=connection_point_rows,
    )


def find_v1_structure_model(document, preferred_structure_model=None):
    """Find a v1 StructureModel object in a document."""

    if _is_v1_structure_model(preferred_structure_model):
        return preferred_structure_model
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_structure_model(obj):
            return obj
    return None


def validate_structure_model(structure_model: StructureModel, *, region_model=None) -> list[str]:
    """Return compact diagnostics for obvious StructureModel authoring issues."""

    rows = list(getattr(structure_model, "structure_rows", []) or [])
    geometry_spec_rows = list(getattr(structure_model, "geometry_spec_rows", []) or [])
    bridge_geometry_spec_rows = list(getattr(structure_model, "bridge_geometry_spec_rows", []) or [])
    retaining_wall_geometry_spec_rows = list(getattr(structure_model, "retaining_wall_geometry_spec_rows", []) or [])
    connection_point_rows = list(getattr(structure_model, "connection_point_rows", []) or [])
    geometry_specs_by_id = {
        str(getattr(row, "geometry_spec_id", "") or ""): row
        for row in geometry_spec_rows
    }
    bridge_specs_by_ref = {
        str(getattr(row, "geometry_spec_ref", "") or ""): row
        for row in bridge_geometry_spec_rows
    }
    retaining_wall_specs_by_ref = {
        str(getattr(row, "geometry_spec_ref", "") or ""): row
        for row in retaining_wall_geometry_spec_rows
    }
    regions_by_id = _regions_by_id(region_model)
    diagnostics: list[str] = []
    seen = set()
    for index, row in enumerate(rows, start=1):
        structure_id = str(getattr(row, "structure_id", "") or "").strip()
        kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
        geometry_spec_ref = str(getattr(row, "geometry_spec_ref", "") or "").strip()
        geometry_ref = str(getattr(row, "geometry_ref", "") or "").strip()
        geometry_source_mode = _geometry_source_mode(row)
        placement = getattr(row, "placement", None)
        if not structure_id:
            diagnostics.append(f"warning|structure_id|row:{index}|Structure id is empty.")
        elif structure_id in seen:
            diagnostics.append(f"warning|structure_id|{structure_id}|Structure id is duplicated.")
        seen.add(structure_id)
        if geometry_source_mode == "native" and not geometry_spec_ref:
            diagnostics.append(f"error|geometry_spec_missing|{structure_id or index}|Native structure is missing a geometry spec reference.")
        if geometry_source_mode == "external_ref" and not geometry_ref:
            diagnostics.append(f"error|external_geometry_ref_missing|{structure_id or index}|External Ref structure is missing an external geometry reference.")
        if geometry_spec_ref and geometry_spec_ref not in geometry_specs_by_id:
            diagnostics.append(f"error|geometry_spec_ref|{structure_id or index}|Structure references a missing geometry spec.")
        if geometry_ref and geometry_spec_ref and geometry_source_mode == "native":
            diagnostics.append(f"warning|geometry_reference_conflict|{structure_id or index}|Structure has both native geometry spec and external geometry reference.")
        if kind == "bridge" and geometry_spec_ref and geometry_spec_ref not in bridge_specs_by_ref:
            diagnostics.append(f"error|bridge_geometry_spec_missing|{structure_id or index}|Bridge structure is missing bridge-specific geometry spec fields.")
        elif kind in {"retaining_wall", "wall"} and geometry_spec_ref and geometry_spec_ref not in retaining_wall_specs_by_ref:
            diagnostics.append(f"error|retaining_wall_geometry_spec_missing|{structure_id or index}|Retaining wall structure is missing retaining-wall-specific geometry spec fields.")
        if placement is None:
            diagnostics.append(f"error|placement|{structure_id or index}|Structure placement is missing.")
            continue
        start = float(getattr(placement, "station_start", 0.0) or 0.0)
        end = float(getattr(placement, "station_end", 0.0) or 0.0)
        if end < start:
            diagnostics.append(f"error|station_range|{structure_id or index}|Station end is before station start.")
        region_ref = str(getattr(placement, "region_ref", "") or "").strip()
        if region_ref and regions_by_id:
            region = regions_by_id.get(region_ref)
            if region is None:
                diagnostics.append(f"error|structure_region_ref|{structure_id or index}|Structure references a missing Region.")
            else:
                region_start = float(getattr(region, "station_start", 0.0) or 0.0)
                region_end = float(getattr(region, "station_end", 0.0) or 0.0)
                if start < region_start or end > region_end:
                    diagnostics.append(
                        f"error|structure_outside_region_station_range|{structure_id or index}|Structure station range must stay inside the referenced Region boundary."
                    )
        if is_removed_drainage_structure(row):
            diagnostics.append(
                f"warning|structure_moved_to_drainage|{structure_id or index}|"
                "Culverts and drainage structures are modelled in Drainage; this row is dropped when the Structure is applied."
            )
    seen_specs = set()
    structure_ids = {str(getattr(row, "structure_id", "") or "") for row in rows}
    for index, spec in enumerate(geometry_spec_rows, start=1):
        geometry_spec_id = str(getattr(spec, "geometry_spec_id", "") or "").strip()
        structure_ref = str(getattr(spec, "structure_ref", "") or "").strip()
        if not geometry_spec_id:
            diagnostics.append(f"warning|geometry_spec_id|row:{index}|Geometry spec id is empty.")
        elif geometry_spec_id in seen_specs:
            diagnostics.append(f"warning|geometry_spec_id|{geometry_spec_id}|Geometry spec id is duplicated.")
        seen_specs.add(geometry_spec_id)
        if structure_ref and structure_ref not in structure_ids:
            diagnostics.append(f"warning|geometry_spec_ref|{geometry_spec_id or index}|Geometry spec references an unknown structure.")
        width = float(getattr(spec, "width", 0.0) or 0.0)
        height = float(getattr(spec, "height", 0.0) or 0.0)
        if width <= 0.0:
            diagnostics.append(f"error|geometry_width|{geometry_spec_id or index}|Geometry spec width must be greater than zero.")
        if height <= 0.0:
            diagnostics.append(f"error|geometry_height|{geometry_spec_id or index}|Geometry spec height must be greater than zero.")
        skew = float(getattr(spec, "skew_angle_deg", 0.0) or 0.0)
        if skew != 0.0:
            diagnostics.append(f"warning|unsupported_skew_angle|{geometry_spec_id or index}|Current preview builder records skew but does not apply skewed geometry.")
    spec_ids = {str(getattr(row, "geometry_spec_id", "") or "") for row in geometry_spec_rows}
    for spec in bridge_geometry_spec_rows:
        spec_ref = str(getattr(spec, "geometry_spec_ref", "") or "")
        if spec_ref and spec_ref not in spec_ids:
            diagnostics.append(f"warning|bridge_geometry_spec_ref|{spec_ref}|Bridge geometry spec references an unknown common geometry spec.")
        _validate_positive(diagnostics, "bridge_deck_width", spec_ref, getattr(spec, "deck_width", 0.0), "Bridge deck width must be greater than zero.")
        _validate_positive(diagnostics, "bridge_deck_thickness", spec_ref, getattr(spec, "deck_thickness", 0.0), "Bridge deck thickness must be greater than zero.")
        _validate_non_negative(diagnostics, "bridge_clearance_height", spec_ref, getattr(spec, "clearance_height", 0.0), "Bridge clearance height must not be negative.")
    for spec in retaining_wall_geometry_spec_rows:
        spec_ref = str(getattr(spec, "geometry_spec_ref", "") or "")
        if spec_ref and spec_ref not in spec_ids:
            diagnostics.append(f"warning|retaining_wall_geometry_spec_ref|{spec_ref}|Retaining wall geometry spec references an unknown common geometry spec.")
        _validate_positive(diagnostics, "wall_height", spec_ref, getattr(spec, "wall_height", 0.0), "Retaining wall height must be greater than zero.")
        _validate_positive(diagnostics, "wall_thickness", spec_ref, getattr(spec, "wall_thickness", 0.0), "Retaining wall thickness must be greater than zero.")
        retained_side = str(getattr(spec, "retained_side", "") or "").strip().lower()
        if retained_side and retained_side not in {"left", "right", "inside", "outside"}:
            diagnostics.append(f"warning|wall_retained_side|{spec_ref}|Retaining wall retained side is not a recommended value.")
    diagnostics.extend(_connection_point_row_diagnostics(connection_point_rows, structure_ids))
    return diagnostics


def _geometry_source_mode(row: StructureRow) -> str:
    mode = str(getattr(row, "geometry_source_mode", "") or "").strip().lower()
    if mode in {"native", "external_ref"}:
        return mode
    reference_mode = str(getattr(row, "reference_mode", "") or "").strip().lower()
    geometry_ref = str(getattr(row, "geometry_ref", "") or "").strip()
    if reference_mode in {"source_ref", "reference_geometry", "external_ref"} or geometry_ref:
        return "external_ref"
    return "native"


def _connection_point_row_diagnostics(
    connection_point_rows: list[StructureConnectionPoint],
    structure_ids: set[str],
) -> list[str]:
    diagnostics: list[str] = []
    seen = set()
    for index, point in enumerate(connection_point_rows, start=1):
        point_id = str(getattr(point, "connection_point_id", "") or "").strip()
        structure_ref = str(getattr(point, "structure_ref", "") or "").strip()
        if not point_id:
            diagnostics.append(f"warning|connection_point_id|row:{index}|Connection point id is empty.")
        elif point_id in seen:
            diagnostics.append(f"warning|connection_point_id|{point_id}|Connection point id is duplicated.")
        seen.add(point_id)
        if structure_ref not in structure_ids:
            diagnostics.append(f"error|connection_point_structure_ref|{point_id or index}|Connection point references a missing Structure.")
        role = str(getattr(point, "point_role", "") or "").strip()
        if not role:
            diagnostics.append(f"warning|connection_point_role|{point_id or index}|Connection point role is empty.")
        elif not _is_recommended_connection_role(role):
            diagnostics.append(f"warning|connection_point_role|{point_id or index}|Connection point role is not a recommended Structure connection role.")
        if (
            getattr(point, "invert_elevation", None) is None
            and getattr(point, "elevation", None) is None
            and not _uses_centerline3d_vertical_source(point)
        ):
            diagnostics.append(f"warning|connection_point_elevation|{point_id or index}|Connection point should define invert or connection elevation.")
        shape_kind = str(getattr(point, "shape_kind", "") or "").strip().lower()
        diameter = float(getattr(point, "diameter", 0.0) or 0.0)
        width = float(getattr(point, "width", 0.0) or 0.0)
        height = float(getattr(point, "height", 0.0) or 0.0)
        if _needs_circular_size(role=role, shape_kind=shape_kind) and diameter <= 0.0:
            diagnostics.append(f"error|connection_point_diameter|{point_id or index}|Circular pipe connection points must define a positive diameter.")
        if _needs_box_size(shape_kind=shape_kind) and (width <= 0.0 or height <= 0.0):
            diagnostics.append(f"error|connection_point_size|{point_id or index}|Box or open-channel connection points must define positive width and height.")
    return diagnostics


def _uses_centerline3d_vertical_source(point: StructureConnectionPoint) -> bool:
    notes = str(getattr(point, "notes", "") or "").strip().lower()
    return "vertical_source=centerline3d" in notes or "elevation_source=centerline3d" in notes


def _regions_by_id(region_model) -> dict[str, object]:
    rows = list(getattr(region_model, "region_rows", []) or []) if region_model is not None else []
    return {
        str(getattr(row, "region_id", "") or ""): row
        for row in rows
        if str(getattr(row, "region_id", "") or "")
    }


def _is_recommended_connection_role(role: str) -> bool:
    return role in {
        "inlet",
        "outlet",
        "upstream",
        "downstream",
        "left_port",
        "right_port",
        "pipe_in",
        "pipe_out",
        "overflow",
        "discharge",
    }


def _needs_circular_size(*, role: str, shape_kind: str) -> bool:
    return shape_kind == "circular" or role in CIRCULAR_CONNECTION_ROLES


def _needs_box_size(*, shape_kind: str) -> bool:
    return shape_kind in {"box", "rectangular", "ditch_inlet", "outfall", "headwall", "open_channel"}


def _validation_status(diagnostics: list[str]) -> str:
    if any(str(row).startswith("error|") for row in list(diagnostics or [])):
        return "error"
    if diagnostics:
        return "warning"
    return "ok"


def _is_v1_structure_model(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1StructureModel":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_structure_model":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1StructureModel" or name.startswith("V1StructureModel")


def _remove_properties(obj, names: tuple[str, ...]) -> None:
    for name in names:
        if obj is not None and hasattr(obj, name):
            try:
                obj.removeProperty(name)
            except Exception:
                pass


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _validate_positive(diagnostics: list[str], kind: str, row_ref: str, value: object, message: str) -> None:
    if float(value or 0.0) <= 0.0:
        diagnostics.append(f"error|{kind}|{row_ref}|{message}")


def _validate_non_negative(diagnostics: list[str], kind: str, row_ref: str, value: object, message: str) -> None:
    if float(value or 0.0) < 0.0:
        diagnostics.append(f"error|{kind}|{row_ref}|{message}")


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _list_value(values, index: int, default: str = "") -> str:
    try:
        values_list = list(values or [])
        return str(values_list[index]) if index < len(values_list) else str(default)
    except Exception:
        return str(default)


def _float_list(values) -> list[float]:
    output = []
    for value in list(values or []):
        try:
            output.append(float(value))
        except Exception:
            output.append(0.0)
    return output


def _float_list_value(values, index: int, default: float = 0.0) -> float:
    return float(_float_list(values)[index]) if index < len(_float_list(values)) else float(default)


def _optional_float_value(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def _none_if_blank_offset(values: list[float], index: int) -> float | None:
    if index >= len(values):
        return None
    return float(values[index])


def _json_row(row) -> str:
    return json.dumps(asdict(row), sort_keys=True, separators=(",", ":"))


def _json_rows(values) -> list[dict]:
    rows = []
    for value in list(values or []):
        try:
            decoded = json.loads(str(value))
            if isinstance(decoded, dict):
                rows.append(decoded)
        except Exception:
            pass
    return rows

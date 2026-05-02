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
    CulvertGeometrySpec,
    RetainingWallGeometrySpec,
    StructureGeometrySpec,
    StructureInfluenceZone,
    StructureInteractionRule,
    StructureModel,
    StructurePlacement,
    StructureRow,
)


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
    _add_property(obj, "App::PropertyStringList", "CulvertGeometrySpecRows", "Kind Geometry Specs", "culvert-specific geometry spec rows")
    _add_property(obj, "App::PropertyStringList", "RetainingWallGeometrySpecRows", "Kind Geometry Specs", "retaining-wall-specific geometry spec rows")
    _add_property(obj, "App::PropertyStringList", "GeometryRefs", "References", "geometry refs")
    _add_property(obj, "App::PropertyStringList", "ReferenceModes", "References", "reference modes")
    _add_property(obj, "App::PropertyStringList", "RuleIds", "Interaction Rules", "interaction rule ids")
    _add_property(obj, "App::PropertyStringList", "RuleStructureRefs", "Interaction Rules", "rule structure refs")
    _add_property(obj, "App::PropertyStringList", "RuleKinds", "Interaction Rules", "rule kinds")
    _add_property(obj, "App::PropertyStringList", "RuleTargetScopes", "Interaction Rules", "rule target scopes")
    _add_property(obj, "App::PropertyStringList", "RuleParameters", "Interaction Rules", "rule parameters")
    _add_property(obj, "App::PropertyStringList", "RuleValues", "Interaction Rules", "rule values")
    _add_property(obj, "App::PropertyStringList", "RuleUnits", "Interaction Rules", "rule units")
    _add_property(obj, "App::PropertyIntegerList", "RulePriorities", "Interaction Rules", "rule priorities")
    _add_property(obj, "App::PropertyStringList", "InfluenceZoneIds", "Influence Zones", "influence zone ids")
    _add_property(obj, "App::PropertyStringList", "InfluenceStructureRefs", "Influence Zones", "influence structure refs")
    _add_property(obj, "App::PropertyStringList", "InfluenceZoneKinds", "Influence Zones", "influence zone kinds")
    _add_property(obj, "App::PropertyFloatList", "InfluenceStationStarts", "Influence Zones", "influence start stations")
    _add_property(obj, "App::PropertyFloatList", "InfluenceStationEnds", "Influence Zones", "influence end stations")
    _add_property(obj, "App::PropertyFloatList", "InfluenceOffsetMins", "Influence Zones", "influence min offsets")
    _add_property(obj, "App::PropertyFloatList", "InfluenceOffsetMaxes", "Influence Zones", "influence max offsets")
    _add_property(obj, "App::PropertyString", "ValidationStatus", "Diagnostics", "structure validation status")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRows", "Diagnostics", "structure diagnostics")

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
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_structure_model_object(obj, structure_model: StructureModel, *, label: str = "Structures"):
    """Write StructureModel rows into an existing FreeCAD object."""

    ensure_v1_structure_properties(obj)
    rows = list(getattr(structure_model, "structure_rows", []) or [])
    geometry_spec_rows = list(getattr(structure_model, "geometry_spec_rows", []) or [])
    bridge_geometry_spec_rows = list(getattr(structure_model, "bridge_geometry_spec_rows", []) or [])
    culvert_geometry_spec_rows = list(getattr(structure_model, "culvert_geometry_spec_rows", []) or [])
    retaining_wall_geometry_spec_rows = list(getattr(structure_model, "retaining_wall_geometry_spec_rows", []) or [])
    rule_rows = list(getattr(structure_model, "interaction_rule_rows", []) or [])
    zone_rows = list(getattr(structure_model, "influence_zone_rows", []) or [])
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
    obj.CulvertGeometrySpecRows = [_json_row(row) for row in culvert_geometry_spec_rows]
    obj.RetainingWallGeometrySpecRows = [_json_row(row) for row in retaining_wall_geometry_spec_rows]
    obj.GeometryRefs = [str(row.geometry_ref) for row in rows]
    obj.ReferenceModes = [str(row.reference_mode) for row in rows]
    obj.RuleIds = [str(row.interaction_rule_id) for row in rule_rows]
    obj.RuleStructureRefs = [str(row.structure_ref) for row in rule_rows]
    obj.RuleKinds = [str(row.rule_kind) for row in rule_rows]
    obj.RuleTargetScopes = [str(row.target_scope) for row in rule_rows]
    obj.RuleParameters = [str(row.parameter) for row in rule_rows]
    obj.RuleValues = [str(row.value) for row in rule_rows]
    obj.RuleUnits = [str(row.unit) for row in rule_rows]
    obj.RulePriorities = [int(row.priority) for row in rule_rows]
    obj.InfluenceZoneIds = [str(row.influence_zone_id) for row in zone_rows]
    obj.InfluenceStructureRefs = [str(row.structure_ref) for row in zone_rows]
    obj.InfluenceZoneKinds = [str(row.zone_kind) for row in zone_rows]
    obj.InfluenceStationStarts = [float(row.station_start) for row in zone_rows]
    obj.InfluenceStationEnds = [float(row.station_end) for row in zone_rows]
    obj.InfluenceOffsetMins = [_optional_float_value(row.offset_min) for row in zone_rows]
    obj.InfluenceOffsetMaxes = [_optional_float_value(row.offset_max) for row in zone_rows]
    obj.ValidationStatus = _validation_status(diagnostics)
    obj.DiagnosticRows = diagnostics
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
    culvert_geometry_spec_rows = [
        CulvertGeometrySpec(**row)
        for row in _json_rows(getattr(obj, "CulvertGeometrySpecRows", []) or [])
    ]
    retaining_wall_geometry_spec_rows = [
        RetainingWallGeometrySpec(**row)
        for row in _json_rows(getattr(obj, "RetainingWallGeometrySpecRows", []) or [])
    ]

    rule_rows: list[StructureInteractionRule] = []
    rule_ids = list(getattr(obj, "RuleIds", []) or [])
    for index, rule_id in enumerate(rule_ids):
        rule_rows.append(
            StructureInteractionRule(
                interaction_rule_id=str(rule_id),
                structure_ref=_list_value(getattr(obj, "RuleStructureRefs", []), index, ""),
                rule_kind=_list_value(getattr(obj, "RuleKinds", []), index, "section_handoff"),
                target_scope=_list_value(getattr(obj, "RuleTargetScopes", []), index, "section"),
                parameter=_list_value(getattr(obj, "RuleParameters", []), index, ""),
                value=_list_value(getattr(obj, "RuleValues", []), index, ""),
                unit=_list_value(getattr(obj, "RuleUnits", []), index, ""),
                priority=_int_list_value(getattr(obj, "RulePriorities", []), index, 0),
            )
        )

    zone_rows: list[StructureInfluenceZone] = []
    zone_ids = list(getattr(obj, "InfluenceZoneIds", []) or [])
    offset_mins = _float_list(getattr(obj, "InfluenceOffsetMins", []) or [])
    offset_maxes = _float_list(getattr(obj, "InfluenceOffsetMaxes", []) or [])
    for index, zone_id in enumerate(zone_ids):
        zone_rows.append(
            StructureInfluenceZone(
                influence_zone_id=str(zone_id),
                structure_ref=_list_value(getattr(obj, "InfluenceStructureRefs", []), index, ""),
                zone_kind=_list_value(getattr(obj, "InfluenceZoneKinds", []), index, "influence"),
                station_start=_float_list_value(getattr(obj, "InfluenceStationStarts", []), index, 0.0),
                station_end=_float_list_value(getattr(obj, "InfluenceStationEnds", []), index, 0.0),
                offset_min=_none_if_blank_offset(offset_mins, index),
                offset_max=_none_if_blank_offset(offset_maxes, index),
            )
        )
    return StructureModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        structure_model_id=str(getattr(obj, "StructureModelId", "") or "structures:main"),
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        label=str(getattr(obj, "Label", "") or "Structures"),
        structure_rows=rows,
        geometry_spec_rows=geometry_spec_rows,
        bridge_geometry_spec_rows=bridge_geometry_spec_rows,
        culvert_geometry_spec_rows=culvert_geometry_spec_rows,
        retaining_wall_geometry_spec_rows=retaining_wall_geometry_spec_rows,
        interaction_rule_rows=rule_rows,
        influence_zone_rows=zone_rows,
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


def validate_structure_model(structure_model: StructureModel) -> list[str]:
    """Return compact diagnostics for obvious StructureModel authoring issues."""

    rows = list(getattr(structure_model, "structure_rows", []) or [])
    geometry_spec_rows = list(getattr(structure_model, "geometry_spec_rows", []) or [])
    bridge_geometry_spec_rows = list(getattr(structure_model, "bridge_geometry_spec_rows", []) or [])
    culvert_geometry_spec_rows = list(getattr(structure_model, "culvert_geometry_spec_rows", []) or [])
    retaining_wall_geometry_spec_rows = list(getattr(structure_model, "retaining_wall_geometry_spec_rows", []) or [])
    geometry_specs_by_id = {
        str(getattr(row, "geometry_spec_id", "") or ""): row
        for row in geometry_spec_rows
    }
    bridge_specs_by_ref = {
        str(getattr(row, "geometry_spec_ref", "") or ""): row
        for row in bridge_geometry_spec_rows
    }
    culvert_specs_by_ref = {
        str(getattr(row, "geometry_spec_ref", "") or ""): row
        for row in culvert_geometry_spec_rows
    }
    retaining_wall_specs_by_ref = {
        str(getattr(row, "geometry_spec_ref", "") or ""): row
        for row in retaining_wall_geometry_spec_rows
    }
    diagnostics: list[str] = []
    seen = set()
    for index, row in enumerate(rows, start=1):
        structure_id = str(getattr(row, "structure_id", "") or "").strip()
        kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
        geometry_spec_ref = str(getattr(row, "geometry_spec_ref", "") or "").strip()
        geometry_ref = str(getattr(row, "geometry_ref", "") or "").strip()
        reference_mode = str(getattr(row, "reference_mode", "") or "").strip().lower()
        placement = getattr(row, "placement", None)
        if not structure_id:
            diagnostics.append(f"warning|structure_id|row:{index}|Structure id is empty.")
        elif structure_id in seen:
            diagnostics.append(f"warning|structure_id|{structure_id}|Structure id is duplicated.")
        seen.add(structure_id)
        if reference_mode == "native" and not geometry_spec_ref:
            diagnostics.append(f"error|geometry_spec_missing|{structure_id or index}|Native structure is missing a geometry spec reference.")
        if geometry_spec_ref and geometry_spec_ref not in geometry_specs_by_id:
            diagnostics.append(f"error|geometry_spec_ref|{structure_id or index}|Structure references a missing geometry spec.")
        if geometry_ref and geometry_spec_ref and reference_mode in {"native", "source_ref", "reference_geometry"}:
            diagnostics.append(f"warning|geometry_reference_conflict|{structure_id or index}|Structure has both native geometry spec and external geometry reference.")
        if kind == "bridge" and geometry_spec_ref and geometry_spec_ref not in bridge_specs_by_ref:
            diagnostics.append(f"error|bridge_geometry_spec_missing|{structure_id or index}|Bridge structure is missing bridge-specific geometry spec fields.")
        elif kind == "culvert" and geometry_spec_ref and geometry_spec_ref not in culvert_specs_by_ref:
            diagnostics.append(f"error|culvert_geometry_spec_missing|{structure_id or index}|Culvert structure is missing culvert-specific geometry spec fields.")
        elif kind in {"retaining_wall", "wall"} and geometry_spec_ref and geometry_spec_ref not in retaining_wall_specs_by_ref:
            diagnostics.append(f"error|retaining_wall_geometry_spec_missing|{structure_id or index}|Retaining wall structure is missing retaining-wall-specific geometry spec fields.")
        if placement is None:
            diagnostics.append(f"error|placement|{structure_id or index}|Structure placement is missing.")
            continue
        start = float(getattr(placement, "station_start", 0.0) or 0.0)
        end = float(getattr(placement, "station_end", 0.0) or 0.0)
        if end < start:
            diagnostics.append(f"error|station_range|{structure_id or index}|Station end is before station start.")
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
    for spec in culvert_geometry_spec_rows:
        spec_ref = str(getattr(spec, "geometry_spec_ref", "") or "")
        if spec_ref and spec_ref not in spec_ids:
            diagnostics.append(f"warning|culvert_geometry_spec_ref|{spec_ref}|Culvert geometry spec references an unknown common geometry spec.")
        _validate_positive_int(diagnostics, "culvert_barrel_count", spec_ref, getattr(spec, "barrel_count", 0), "Culvert barrel count must be greater than zero.")
        barrel_shape = str(getattr(spec, "barrel_shape", "") or "").strip().lower()
        if barrel_shape in {"box", "pipe_arch", "custom_profile"}:
            _validate_positive(diagnostics, "culvert_span", spec_ref, getattr(spec, "span", 0.0), "Culvert span must be greater than zero.")
            _validate_positive(diagnostics, "culvert_rise", spec_ref, getattr(spec, "rise", 0.0), "Culvert rise must be greater than zero.")
        elif barrel_shape == "circular":
            _validate_positive(diagnostics, "culvert_diameter", spec_ref, getattr(spec, "diameter", 0.0), "Circular culvert diameter must be greater than zero.")
        else:
            diagnostics.append(f"warning|culvert_barrel_shape|{spec_ref}|Culvert barrel shape is not a recommended value.")
        _validate_non_negative(diagnostics, "culvert_wall_thickness", spec_ref, getattr(spec, "wall_thickness", 0.0), "Culvert wall thickness must not be negative.")
    for spec in retaining_wall_geometry_spec_rows:
        spec_ref = str(getattr(spec, "geometry_spec_ref", "") or "")
        if spec_ref and spec_ref not in spec_ids:
            diagnostics.append(f"warning|retaining_wall_geometry_spec_ref|{spec_ref}|Retaining wall geometry spec references an unknown common geometry spec.")
        _validate_positive(diagnostics, "wall_height", spec_ref, getattr(spec, "wall_height", 0.0), "Retaining wall height must be greater than zero.")
        _validate_positive(diagnostics, "wall_thickness", spec_ref, getattr(spec, "wall_thickness", 0.0), "Retaining wall thickness must be greater than zero.")
        retained_side = str(getattr(spec, "retained_side", "") or "").strip().lower()
        if retained_side and retained_side not in {"left", "right", "inside", "outside"}:
            diagnostics.append(f"warning|wall_retained_side|{spec_ref}|Retaining wall retained side is not a recommended value.")
    return diagnostics


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


def _validate_positive_int(diagnostics: list[str], kind: str, row_ref: str, value: object, message: str) -> None:
    try:
        parsed = int(value or 0)
    except Exception:
        parsed = 0
    if parsed <= 0:
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


def _int_list_value(values, index: int, default: int = 0) -> int:
    try:
        values_list = list(values or [])
        return int(values_list[index]) if index < len(values_list) else int(default)
    except Exception:
        return int(default)


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

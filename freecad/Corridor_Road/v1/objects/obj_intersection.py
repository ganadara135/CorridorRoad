"""FreeCAD source object for v1 IntersectionModel rows."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.intersection_model import (
    IntersectionAnchorRow,
    IntersectionArmPolicyRow,
    IntersectionControlArea,
    IntersectionCornerRow,
    IntersectionCurbReturnPolicyRow,
    IntersectionDrainagePolicyRow,
    IntersectionEdgePolicyRow,
    IntersectionGradingPolicyRow,
    IntersectionLaneConnectionRow,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
    IntersectionSlopeFacePolicyRow,
)
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


class V1IntersectionModelObject:
    """Document object proxy that stores a v1 IntersectionModel contract."""

    Type = "IntersectionModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_intersection_properties(obj)

    def execute(self, obj):
        ensure_v1_intersection_properties(obj)
        return


class ViewProviderV1IntersectionModel:
    """Simple view provider for v1 Intersection source objects."""

    Type = "ViewProviderV1IntersectionModel"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("intersections.svg")
        except Exception:
            return ""


def ensure_v1_intersection_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 IntersectionModel source properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "IntersectionModelId", "CorridorRoad", "v1 intersection model id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyString", "AnchorRowsJson", "Intersections", "intersection anchor rows")
    _add_property(obj, "App::PropertyString", "IntersectionRowsJson", "Intersections", "intersection rows")
    _add_property(obj, "App::PropertyString", "ControlAreaRowsJson", "Intersections", "intersection control area rows")
    _add_property(obj, "App::PropertyString", "CornerRowsJson", "Intersections", "intersection corner source rows")
    _add_property(obj, "App::PropertyString", "ArmPolicyRowsJson", "Intersections", "intersection arm policy rows")
    _add_property(obj, "App::PropertyString", "CurbReturnPolicyRowsJson", "Intersections", "intersection curb return policy rows")
    _add_property(obj, "App::PropertyString", "EdgePolicyRowsJson", "Intersections", "intersection edge policy rows")
    _add_property(obj, "App::PropertyString", "LaneConnectionRowsJson", "Intersections", "intersection lane connection rows")
    _add_property(obj, "App::PropertyString", "GradingPolicyRowsJson", "Intersections", "intersection grading policy rows")
    _add_property(obj, "App::PropertyString", "SlopeFacePolicyRowsJson", "Intersections", "intersection slope-face policy rows")
    _add_property(obj, "App::PropertyString", "DrainagePolicyRowsJson", "Intersections", "intersection drainage policy rows")
    _add_property(obj, "App::PropertyStringList", "ControlRegionRefs", "Intersections", "linked control region refs")
    _add_property(obj, "App::PropertyInteger", "AnchorCount", "Summary", "anchor row count")
    _add_property(obj, "App::PropertyInteger", "IntersectionCount", "Summary", "intersection row count")
    _add_property(obj, "App::PropertyInteger", "ControlAreaCount", "Summary", "control area row count")
    _add_property(obj, "App::PropertyInteger", "CornerCount", "Summary", "corner row count")
    _add_property(obj, "App::PropertyInteger", "ArmPolicyCount", "Summary", "arm policy row count")
    _add_property(obj, "App::PropertyInteger", "CurbReturnPolicyCount", "Summary", "curb return policy row count")
    _add_property(obj, "App::PropertyInteger", "EdgePolicyCount", "Summary", "edge policy row count")
    _add_property(obj, "App::PropertyInteger", "LaneConnectionCount", "Summary", "lane connection row count")
    _add_property(obj, "App::PropertyInteger", "GradingPolicyCount", "Summary", "grading policy row count")
    _add_property(obj, "App::PropertyInteger", "SlopeFacePolicyCount", "Summary", "slope-face policy row count")
    _add_property(obj, "App::PropertyInteger", "DrainagePolicyCount", "Summary", "drainage policy row count")
    _add_property(obj, "App::PropertyString", "LastValidationStatus", "Diagnostics", "last validation status")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Traceability", "source refs")
    _add_property(obj, "App::PropertyStringList", "ResultRefs", "Traceability", "result refs")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1IntersectionModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "IntersectionModelId", "") or ""):
        obj.IntersectionModelId = f"intersections:{str(getattr(obj, 'Name', '') or 'main')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_intersection_model"
    if not str(getattr(obj, "AnchorRowsJson", "") or ""):
        obj.AnchorRowsJson = "[]"
    if not str(getattr(obj, "IntersectionRowsJson", "") or ""):
        obj.IntersectionRowsJson = "[]"
    if not str(getattr(obj, "ControlAreaRowsJson", "") or ""):
        obj.ControlAreaRowsJson = "[]"
    if not str(getattr(obj, "CornerRowsJson", "") or ""):
        obj.CornerRowsJson = "[]"
    if not str(getattr(obj, "ArmPolicyRowsJson", "") or ""):
        obj.ArmPolicyRowsJson = "[]"
    if not str(getattr(obj, "CurbReturnPolicyRowsJson", "") or ""):
        obj.CurbReturnPolicyRowsJson = "[]"
    if not str(getattr(obj, "EdgePolicyRowsJson", "") or ""):
        obj.EdgePolicyRowsJson = "[]"
    if not str(getattr(obj, "LaneConnectionRowsJson", "") or ""):
        obj.LaneConnectionRowsJson = "[]"
    if not str(getattr(obj, "GradingPolicyRowsJson", "") or ""):
        obj.GradingPolicyRowsJson = "[]"
    if not str(getattr(obj, "SlopeFacePolicyRowsJson", "") or ""):
        obj.SlopeFacePolicyRowsJson = "[]"
    if not str(getattr(obj, "DrainagePolicyRowsJson", "") or ""):
        obj.DrainagePolicyRowsJson = "[]"
    if not str(getattr(obj, "LastValidationStatus", "") or ""):
        obj.LastValidationStatus = "empty"


def create_or_update_v1_intersection_model_object(
    document=None,
    intersection_model: IntersectionModel | None = None,
    *,
    project=None,
    object_name: str = "V1IntersectionModel",
    label: str = "Intersections",
):
    """Create or update the durable v1 IntersectionModel source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 IntersectionModel creation.")
    if intersection_model is None:
        intersection_model = IntersectionModel(
            schema_version=1,
            project_id=_project_id(project),
            intersection_model_id="intersections:main",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1IntersectionModelObject(obj)
        try:
            ViewProviderV1IntersectionModel(obj.ViewObject)
        except Exception:
            pass
    else:
        V1IntersectionModelObject(obj)
    update_v1_intersection_model_object(obj, intersection_model, label=label)

    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_intersection_model_object(obj, intersection_model: IntersectionModel, *, label: str = "Intersections"):
    """Write IntersectionModel rows into an existing FreeCAD object."""

    ensure_v1_intersection_properties(obj)
    anchor_rows = list(getattr(intersection_model, "anchor_rows", []) or [])
    intersection_rows = list(getattr(intersection_model, "intersection_rows", []) or [])
    control_area_rows = list(getattr(intersection_model, "control_area_rows", []) or [])
    corner_rows = list(getattr(intersection_model, "corner_rows", []) or [])
    arm_policy_rows = list(getattr(intersection_model, "arm_policy_rows", []) or [])
    curb_return_policy_rows = list(getattr(intersection_model, "curb_return_policy_rows", []) or [])
    edge_policy_rows = list(getattr(intersection_model, "edge_policy_rows", []) or [])
    lane_connection_rows = list(getattr(intersection_model, "lane_connection_rows", []) or [])
    grading_policy_rows = list(getattr(intersection_model, "grading_policy_rows", []) or [])
    slope_face_policy_rows = list(getattr(intersection_model, "slope_face_policy_rows", []) or [])
    drainage_policy_rows = list(getattr(intersection_model, "drainage_policy_rows", []) or [])
    control_refs: list[str] = []
    for row in intersection_rows:
        for ref in list(getattr(row, "control_region_refs", []) or []):
            if ref and ref not in control_refs:
                control_refs.append(str(ref))

    obj.Label = label or str(getattr(intersection_model, "label", "") or "Intersections")
    obj.SchemaVersion = int(getattr(intersection_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(intersection_model, "project_id", "") or "corridorroad-v1")
    obj.IntersectionModelId = str(
        getattr(intersection_model, "intersection_model_id", "") or getattr(obj, "IntersectionModelId", "") or "intersections:main"
    )
    obj.CRRecordKind = "v1_intersection_model"
    obj.AnchorRowsJson = _json_dumps(anchor_rows)
    obj.IntersectionRowsJson = _json_dumps(intersection_rows)
    obj.ControlAreaRowsJson = _json_dumps(control_area_rows)
    obj.CornerRowsJson = _json_dumps(corner_rows)
    obj.ArmPolicyRowsJson = _json_dumps(arm_policy_rows)
    obj.CurbReturnPolicyRowsJson = _json_dumps(curb_return_policy_rows)
    obj.EdgePolicyRowsJson = _json_dumps(edge_policy_rows)
    obj.LaneConnectionRowsJson = _json_dumps(lane_connection_rows)
    obj.GradingPolicyRowsJson = _json_dumps(grading_policy_rows)
    obj.SlopeFacePolicyRowsJson = _json_dumps(slope_face_policy_rows)
    obj.DrainagePolicyRowsJson = _json_dumps(drainage_policy_rows)
    obj.ControlRegionRefs = control_refs
    obj.SourceRefs = [str(ref) for ref in list(getattr(intersection_model, "source_refs", []) or []) if str(ref)]
    obj.ResultRefs = [str(ref) for ref in list(getattr(intersection_model, "result_refs", []) or []) if str(ref)]
    obj.AnchorCount = len(anchor_rows)
    obj.IntersectionCount = len(intersection_rows)
    obj.ControlAreaCount = len(control_area_rows)
    obj.CornerCount = len(corner_rows)
    obj.ArmPolicyCount = len(arm_policy_rows)
    obj.CurbReturnPolicyCount = len(curb_return_policy_rows)
    obj.EdgePolicyCount = len(edge_policy_rows)
    obj.LaneConnectionCount = len(lane_connection_rows)
    obj.GradingPolicyCount = len(grading_policy_rows)
    obj.SlopeFacePolicyCount = len(slope_face_policy_rows)
    obj.DrainagePolicyCount = len(drainage_policy_rows)
    obj.LastValidationStatus = "stored" if intersection_rows else "empty"
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_intersection_model(obj) -> IntersectionModel | None:
    """Build an IntersectionModel from a v1 Intersection FreeCAD object."""

    if not _is_v1_intersection_model(obj):
        return None
    ensure_v1_intersection_properties(obj)
    return IntersectionModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        label=str(getattr(obj, "Label", "") or "Intersections"),
        intersection_model_id=str(getattr(obj, "IntersectionModelId", "") or "intersections:main"),
        source_refs=[str(ref) for ref in list(getattr(obj, "SourceRefs", []) or []) if str(ref)],
        result_refs=[str(ref) for ref in list(getattr(obj, "ResultRefs", []) or []) if str(ref)],
        anchor_rows=[_anchor_row_from_json(row, index) for index, row in enumerate(_json_list(obj.AnchorRowsJson))],
        intersection_rows=[_intersection_row_from_json(row, index) for index, row in enumerate(_json_list(obj.IntersectionRowsJson))],
        control_area_rows=[_control_area_from_json(row, index) for index, row in enumerate(_json_list(obj.ControlAreaRowsJson))],
        corner_rows=[_corner_row_from_json(row, index) for index, row in enumerate(_json_list(obj.CornerRowsJson))],
        arm_policy_rows=[_arm_policy_from_json(row, index) for index, row in enumerate(_json_list(obj.ArmPolicyRowsJson))],
        curb_return_policy_rows=[
            _curb_return_policy_from_json(row, index)
            for index, row in enumerate(_json_list(obj.CurbReturnPolicyRowsJson))
        ],
        edge_policy_rows=[_edge_policy_from_json(row, index) for index, row in enumerate(_json_list(obj.EdgePolicyRowsJson))],
        lane_connection_rows=[
            _lane_connection_from_json(row, index)
            for index, row in enumerate(_json_list(obj.LaneConnectionRowsJson))
        ],
        grading_policy_rows=[
            _grading_policy_from_json(row, index)
            for index, row in enumerate(_json_list(obj.GradingPolicyRowsJson))
        ],
        slope_face_policy_rows=[
            _slope_face_policy_from_json(row, index)
            for index, row in enumerate(_json_list(obj.SlopeFacePolicyRowsJson))
        ],
        drainage_policy_rows=[
            _drainage_policy_from_json(row, index)
            for index, row in enumerate(_json_list(obj.DrainagePolicyRowsJson))
        ],
    )


def find_v1_intersection_model(document, preferred_intersection_model=None):
    """Find a v1 IntersectionModel object in a document."""

    if _is_v1_intersection_model(preferred_intersection_model):
        return preferred_intersection_model
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_intersection_model(obj):
            return obj
    return None


def _anchor_row_from_json(row: dict[str, object], index: int) -> IntersectionAnchorRow:
    return IntersectionAnchorRow(
        anchor_id=str(row.get("anchor_id", "") or f"anchor:{index + 1}"),
        intersection_id=str(row.get("intersection_id", "") or ""),
        source_method=str(row.get("source_method", "") or "detected"),
        approval_status=str(row.get("approval_status", "") or "draft"),
        primary_alignment_ref=str(row.get("primary_alignment_ref", "") or ""),
        primary_station=_float_value(row.get("primary_station", 0.0)),
        secondary_station_refs={str(key): _float_value(value) for key, value in _dict(row.get("secondary_station_refs", {})).items()},
        point_x=_float_value(row.get("point_x", 0.0)),
        point_y=_float_value(row.get("point_y", 0.0)),
        point_z=_float_value(row.get("point_z", 0.0)),
        tolerance=_float_value(row.get("tolerance", 0.0)),
        diagnostic_rows=[str(value) for value in _any_list(row.get("diagnostic_rows", []))],
        notes=str(row.get("notes", "") or ""),
    )


def _intersection_row_from_json(row: dict[str, object], index: int) -> IntersectionRow:
    leg_rows = [
        IntersectionLegRow(
            leg_id=str(leg.get("leg_id", "") or f"leg:{leg_index + 1}"),
            leg_role=str(leg.get("leg_role", "") or ""),
            alignment_ref=str(leg.get("alignment_ref", "") or ""),
            intersection_id=str(leg.get("intersection_id", "") or row.get("intersection_id", "")),
            profile_ref=str(leg.get("profile_ref", "") or ""),
            centerline3d_ref=str(leg.get("centerline3d_ref", "") or ""),
            region_ref=str(leg.get("region_ref", "") or ""),
            approach_station_start=_float_value(leg.get("approach_station_start", 0.0)),
            approach_station_end=_float_value(leg.get("approach_station_end", 0.0)),
            source_method=str(leg.get("source_method", "") or "manual"),
            approval_status=str(leg.get("approval_status", "") or "accepted"),
            span_source=str(leg.get("span_source", "") or "explicit"),
            arm_policy_ref=str(leg.get("arm_policy_ref", "") or ""),
            edge_policy_refs=[str(value) for value in _any_list(leg.get("edge_policy_refs", []))],
            grading_policy_ref=str(leg.get("grading_policy_ref", "") or ""),
            priority=_int_value(leg.get("priority", leg_index + 1), leg_index + 1),
            diagnostic_rows=[str(value) for value in _any_list(leg.get("diagnostic_rows", []))],
            notes=str(leg.get("notes", "") or ""),
        )
        for leg_index, leg in enumerate(_dict_list(row.get("leg_rows", [])))
    ]
    return IntersectionRow(
        intersection_id=str(row.get("intersection_id", "") or f"intersection:{index + 1}"),
        intersection_kind=str(row.get("intersection_kind", "") or ""),
        intersection_index=_int_value(row.get("intersection_index", index + 1), index + 1),
        primary_alignment_ref=str(row.get("primary_alignment_ref", "") or ""),
        secondary_alignment_refs=[str(value) for value in _any_list(row.get("secondary_alignment_refs", []))],
        intersection_point_x=_float_value(row.get("intersection_point_x", 0.0)),
        intersection_point_y=_float_value(row.get("intersection_point_y", 0.0)),
        intersection_point_z=_float_value(row.get("intersection_point_z", 0.0)),
        primary_station=_float_value(row.get("primary_station", 0.0)),
        secondary_station_refs={str(key): _float_value(value) for key, value in _dict(row.get("secondary_station_refs", {})).items()},
        control_region_refs=[str(value) for value in _any_list(row.get("control_region_refs", []))],
        leg_rows=leg_rows,
        control_area_ref=str(row.get("control_area_ref", "") or ""),
        grading_policy_ref=str(row.get("grading_policy_ref", "") or ""),
        drainage_ref=str(row.get("drainage_ref", "") or ""),
        design_criteria_ref=str(row.get("design_criteria_ref", "") or ""),
        source_mode=str(row.get("source_mode", "") or "use_existing_alignments"),
        policy_refs=[str(value) for value in _any_list(row.get("policy_refs", []))],
        notes=str(row.get("notes", "") or ""),
    )


def _control_area_from_json(row: dict[str, object], index: int) -> IntersectionControlArea:
    return IntersectionControlArea(
        control_area_id=str(row.get("control_area_id", "") or f"control-area:{index + 1}"),
        intersection_id=str(row.get("intersection_id", "") or ""),
        alignment_ref=str(row.get("alignment_ref", "") or ""),
        station_ranges=_range_list(row.get("station_ranges", [])),
        influence_ranges=_range_list(row.get("influence_ranges", [])),
        control_region_refs=[str(value) for value in _any_list(row.get("control_region_refs", []))],
        source_method=str(row.get("source_method", "") or "manual"),
        approval_status=str(row.get("approval_status", "") or "accepted"),
        intent_status=str(row.get("intent_status", "") or "intersection_owned"),
        source_region_refs=[str(value) for value in _any_list(row.get("source_region_refs", []))],
        turn_lane_policy_ref=str(row.get("turn_lane_policy_ref", "") or ""),
        curb_return_policy_ref=str(row.get("curb_return_policy_ref", "") or ""),
        grading_policy_ref=str(row.get("grading_policy_ref", "") or ""),
        drainage_policy_ref=str(row.get("drainage_policy_ref", "") or ""),
        diagnostic_rows=[str(value) for value in _any_list(row.get("diagnostic_rows", []))],
        notes=str(row.get("notes", "") or ""),
    )


def _corner_row_from_json(row: dict[str, object], index: int) -> IntersectionCornerRow:
    return IntersectionCornerRow(
        corner_id=str(row.get("corner_id", "") or f"corner:{index + 1}"),
        intersection_id=str(row.get("intersection_id", "") or ""),
        control_area_ref=str(row.get("control_area_ref", "") or ""),
        from_leg_ref=str(row.get("from_leg_ref", "") or ""),
        to_leg_ref=str(row.get("to_leg_ref", "") or ""),
        side=str(row.get("side", "") or ""),
        quadrant=str(row.get("quadrant", "") or ""),
        curb_return_policy_ref=str(row.get("curb_return_policy_ref", "") or ""),
        source_method=str(row.get("source_method", "") or "manual"),
        approval_status=str(row.get("approval_status", "") or "accepted"),
        diagnostic_rows=[str(value) for value in _any_list(row.get("diagnostic_rows", []))],
        notes=str(row.get("notes", "") or ""),
    )


def _curb_return_policy_from_json(row: dict[str, object], index: int) -> IntersectionCurbReturnPolicyRow:
    return IntersectionCurbReturnPolicyRow(
        policy_id=str(row.get("policy_id", "") or f"curb-return:policy-{index + 1}"),
        intersection_id=str(row.get("intersection_id", "") or ""),
        radius=_float_value(row.get("radius", 0.0)),
        side=str(row.get("side", "") or "all"),
        edge_role=str(row.get("edge_role", "") or "pavement_edge"),
        long_edge_factor=_float_value(row.get("long_edge_factor", 2.5), 2.5),
        max_boundary_edge_length=_float_value(row.get("max_boundary_edge_length", 0.0)),
        approach_leg_refs=[str(value) for value in _any_list(row.get("approach_leg_refs", []))],
        corner_refs=[str(value) for value in _any_list(row.get("corner_refs", []))],
        status=str(row.get("status", "") or "active"),
        notes=str(row.get("notes", "") or ""),
    )


def _arm_policy_from_json(row: dict[str, object], index: int) -> IntersectionArmPolicyRow:
    return IntersectionArmPolicyRow(
        policy_id=str(row.get("policy_id", "") or f"arm-policy:policy-{index + 1}"),
        intersection_id=str(row.get("intersection_id", "") or ""),
        leg_ref=str(row.get("leg_ref", "") or ""),
        arm_role=str(row.get("arm_role", "") or ""),
        design_speed_kph=_float_value(row.get("design_speed_kph", 0.0)),
        design_vehicle_ref=str(row.get("design_vehicle_ref", "") or ""),
        lane_count=_int_value(row.get("lane_count", 1), 1),
        lane_width=_float_value(row.get("lane_width", 3.5), 3.5),
        shoulder_width=_float_value(row.get("shoulder_width", 0.0)),
        median_width=_float_value(row.get("median_width", 0.0)),
        turn_lane_policy_ref=str(row.get("turn_lane_policy_ref", "") or ""),
        status=str(row.get("status", "") or "active"),
        notes=str(row.get("notes", "") or ""),
    )


def _edge_policy_from_json(row: dict[str, object], index: int) -> IntersectionEdgePolicyRow:
    return IntersectionEdgePolicyRow(
        policy_id=str(row.get("policy_id", "") or f"edge-policy:policy-{index + 1}"),
        intersection_id=str(row.get("intersection_id", "") or ""),
        leg_ref=str(row.get("leg_ref", "") or ""),
        edge_role=str(row.get("edge_role", "") or "pavement_edge"),
        side=str(row.get("side", "") or "both"),
        offset_rule=str(row.get("offset_rule", "") or ""),
        offset_value=_float_value(row.get("offset_value", 0.0)),
        elevation_rule=str(row.get("elevation_rule", "") or "from_crossfall"),
        profile_ref=str(row.get("profile_ref", "") or ""),
        source_policy_ref=str(row.get("source_policy_ref", "") or ""),
        edge_family_intent=str(row.get("edge_family_intent", "") or ""),
        source_method=str(row.get("source_method", "") or "manual"),
        approval_status=str(row.get("approval_status", "") or "accepted"),
        assembly_ref=str(row.get("assembly_ref", "") or ""),
        template_ref=str(row.get("template_ref", "") or ""),
        subassembly_ref=str(row.get("subassembly_ref", "") or ""),
        subassembly_kind=str(row.get("subassembly_kind", "") or ""),
        diagnostic_rows=[str(value) for value in _any_list(row.get("diagnostic_rows", []))],
        status=str(row.get("status", "") or "active"),
        notes=str(row.get("notes", "") or ""),
    )


def _lane_connection_from_json(row: dict[str, object], index: int) -> IntersectionLaneConnectionRow:
    return IntersectionLaneConnectionRow(
        connection_id=str(row.get("connection_id", "") or f"lane-connection:{index + 1}"),
        intersection_id=str(row.get("intersection_id", "") or ""),
        movement_type=str(row.get("movement_type", "") or "through"),
        from_leg_ref=str(row.get("from_leg_ref", "") or ""),
        to_leg_ref=str(row.get("to_leg_ref", "") or ""),
        from_edge_policy_ref=str(row.get("from_edge_policy_ref", "") or ""),
        to_edge_policy_ref=str(row.get("to_edge_policy_ref", "") or ""),
        from_lane_index=_int_value(row.get("from_lane_index", 1), 1),
        to_lane_index=_int_value(row.get("to_lane_index", 1), 1),
        source_method=str(row.get("source_method", "") or "manual"),
        approval_status=str(row.get("approval_status", "") or "accepted"),
        diagnostic_rows=[str(value) for value in _any_list(row.get("diagnostic_rows", []))],
        notes=str(row.get("notes", "") or ""),
    )


def _grading_policy_from_json(row: dict[str, object], index: int) -> IntersectionGradingPolicyRow:
    return IntersectionGradingPolicyRow(
        policy_id=str(row.get("policy_id", "") or f"grading:policy-{index + 1}"),
        intersection_id=str(row.get("intersection_id", "") or ""),
        mode=str(row.get("mode", "") or "flatten_intersection"),
        target_crossfall_percent=_float_value(row.get("target_crossfall_percent", 0.0)),
        primary_alignment_ref=str(row.get("primary_alignment_ref", "") or ""),
        secondary_alignment_refs=[str(value) for value in _any_list(row.get("secondary_alignment_refs", []))],
        controlling_profile_ref=str(row.get("controlling_profile_ref", "") or ""),
        crown_behavior=str(row.get("crown_behavior", "") or "flatten"),
        tie_in_rule=str(row.get("tie_in_rule", "") or "blend_to_leg_profiles"),
        crossfall_transition=str(row.get("crossfall_transition", "") or "linear"),
        low_point_strategy=str(row.get("low_point_strategy", "") or "review_low_points"),
        source_method=str(row.get("source_method", "") or "manual"),
        approval_status=str(row.get("approval_status", "") or "accepted"),
        diagnostic_rows=[str(value) for value in _any_list(row.get("diagnostic_rows", []))],
        status=str(row.get("status", "") or "active"),
        notes=str(row.get("notes", "") or ""),
    )


def _slope_face_policy_from_json(row: dict[str, object], index: int) -> IntersectionSlopeFacePolicyRow:
    return IntersectionSlopeFacePolicyRow(
        policy_id=str(row.get("policy_id", "") or f"slope-face:policy-{index + 1}"),
        intersection_id=str(row.get("intersection_id", "") or ""),
        policy_name=str(row.get("policy_name", "") or "Default Intersection Slope Face Policy"),
        tie_slope_overlap_m=_float_value(row.get("tie_slope_overlap_m", 0.5), 0.5),
        slope_face_width_offset_m=_float_value(row.get("slope_face_width_offset_m", 0.0)),
        blend_angle_deg=_float_value(row.get("blend_angle_deg", 0.0)),
        max_panel_extension_m=_float_value(row.get("max_panel_extension_m", 3.0), 3.0),
        min_panel_width_m=_float_value(row.get("min_panel_width_m", 0.25), 0.25),
        enabled=bool(row.get("enabled", True)),
        diagnostic_level=str(row.get("diagnostic_level", "") or "normal"),
        source_method=str(row.get("source_method", "") or "manual"),
        approval_status=str(row.get("approval_status", "") or "accepted"),
        diagnostic_rows=[str(value) for value in _any_list(row.get("diagnostic_rows", []))],
        status=str(row.get("status", "") or "active"),
        notes=str(row.get("notes", "") or ""),
    )


def _drainage_policy_from_json(row: dict[str, object], index: int) -> IntersectionDrainagePolicyRow:
    return IntersectionDrainagePolicyRow(
        policy_id=str(row.get("policy_id", "") or f"drainage-policy:policy-{index + 1}"),
        intersection_id=str(row.get("intersection_id", "") or ""),
        capture_mode=str(row.get("capture_mode", "") or "review_low_points"),
        inlet_spacing=_float_value(row.get("inlet_spacing", 0.0)),
        low_point_tolerance=_float_value(row.get("low_point_tolerance", 0.05), 0.05),
        gutter_edge_refs=[str(value) for value in _any_list(row.get("gutter_edge_refs", []))],
        drainage_element_refs=[str(value) for value in _any_list(row.get("drainage_element_refs", []))],
        flow_route_refs=[str(value) for value in _any_list(row.get("flow_route_refs", []))],
        inlet_candidate_refs=[str(value) for value in _any_list(row.get("inlet_candidate_refs", []))],
        low_point_refs=[str(value) for value in _any_list(row.get("low_point_refs", []))],
        intent_status=str(row.get("intent_status", "") or "hint_only"),
        source_method=str(row.get("source_method", "") or "manual"),
        approval_status=str(row.get("approval_status", "") or "accepted"),
        diagnostic_rows=[str(value) for value in _any_list(row.get("diagnostic_rows", []))],
        status=str(row.get("status", "") or "active"),
        notes=str(row.get("notes", "") or ""),
    )


def _is_v1_intersection_model(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1IntersectionModel":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_intersection_model":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "IntersectionModel" or name.startswith("V1IntersectionModel")


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _json_dumps(value: object) -> str:
    if isinstance(value, list):
        data = [_as_plain_json(row) for row in value]
    else:
        data = _as_plain_json(value)
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _as_plain_json(value: object):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _as_plain_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_as_plain_json(item) for item in value]
    return value


def _json_list(text: object) -> list[dict[str, object]]:
    try:
        data = json.loads(str(text or "[]"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _range_list(value: object) -> list[tuple[float, float]]:
    output: list[tuple[float, float]] = []
    for row in _any_list(value):
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            output.append((_float_value(row[0]), _float_value(row[1])))
    return output


def _dict_list(value: object) -> list[dict[str, object]]:
    return [row for row in _any_list(value) if isinstance(row, dict)]


def _any_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _dict(value: object) -> dict[object, object]:
    return value if isinstance(value, dict) else {}


def _float_value(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _int_value(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")

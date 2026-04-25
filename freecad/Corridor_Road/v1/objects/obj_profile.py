"""FreeCAD source object for v1 profile models."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.profile_model import (
    ProfileControlPoint,
    ProfileModel,
    VerticalCurveRow,
)
from .obj_alignment import (
    create_sample_v1_alignment,
    find_v1_alignment,
    to_alignment_model,
)


class V1ProfileObject:
    """Document object proxy that stores a v1 ProfileModel contract."""

    Type = "V1Profile"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_profile_properties(obj)

    def execute(self, obj):
        ensure_v1_profile_properties(obj)
        return


def ensure_v1_profile_properties(obj) -> None:
    """Ensure the FreeCAD object has the minimal v1 profile properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "ProfileId", "CorridorRoad", "v1 profile id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "linked v1 alignment id")
    _add_property(obj, "App::PropertyString", "ProfileKind", "CorridorRoad", "v1 profile kind")
    _add_property(obj, "App::PropertyStringList", "ControlPointIds", "Controls", "profile control ids")
    _add_property(obj, "App::PropertyFloatList", "ControlStations", "Controls", "profile control stations")
    _add_property(obj, "App::PropertyFloatList", "ControlElevations", "Controls", "profile control elevations")
    _add_property(obj, "App::PropertyStringList", "ControlKinds", "Controls", "profile control kinds")
    _add_property(obj, "App::PropertyStringList", "VerticalCurveIds", "Vertical Curves", "vertical curve ids")
    _add_property(obj, "App::PropertyStringList", "VerticalCurveKinds", "Vertical Curves", "vertical curve kinds")
    _add_property(obj, "App::PropertyFloatList", "VerticalCurveStationStarts", "Vertical Curves", "curve start stations")
    _add_property(obj, "App::PropertyFloatList", "VerticalCurveStationEnds", "Vertical Curves", "curve end stations")
    _add_property(obj, "App::PropertyFloatList", "VerticalCurveLengths", "Vertical Curves", "curve lengths")
    _add_property(obj, "App::PropertyFloatList", "VerticalCurveParameters", "Vertical Curves", "curve parameters")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1Profile"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "ProfileId", "") or ""):
        obj.ProfileId = f"profile:{str(getattr(obj, 'Name', '') or 'v1-profile')}"
    if not str(getattr(obj, "ProfileKind", "") or ""):
        obj.ProfileKind = "finished_grade"


def create_sample_v1_profile(
    document=None,
    *,
    project=None,
    alignment=None,
    label: str = "Finished Grade Profile",
    create_alignment_if_missing: bool = True,
):
    """Create a practical sample v1 profile source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 profile creation.")

    alignment_obj = alignment or find_v1_alignment(doc)
    if alignment_obj is None and create_alignment_if_missing:
        alignment_obj = create_sample_v1_alignment(doc, project=project)
    alignment_model = to_alignment_model(alignment_obj) if alignment_obj is not None else None
    alignment_id = str(getattr(alignment_model, "alignment_id", "") or "")

    obj = doc.addObject("App::FeaturePython", "V1Profile")
    V1ProfileObject(obj)
    obj.Label = label
    obj.ProjectId = _project_id(project)
    obj.ProfileId = f"profile:{str(getattr(obj, 'Name', '') or 'fg')}"
    obj.AlignmentId = alignment_id
    obj.ProfileKind = "finished_grade"
    obj.ControlPointIds = [
        f"{obj.ProfileId}:pvi:1",
        f"{obj.ProfileId}:pvi:2",
        f"{obj.ProfileId}:pvi:3",
    ]
    obj.ControlStations = [0.0, 90.0, 180.0]
    obj.ControlElevations = [12.0, 15.0, 13.5]
    obj.ControlKinds = ["grade_break", "pvi", "grade_break"]
    obj.VerticalCurveIds = [f"{obj.ProfileId}:curve:1"]
    obj.VerticalCurveKinds = ["parabolic_vertical_curve"]
    obj.VerticalCurveStationStarts = [75.0]
    obj.VerticalCurveStationEnds = [105.0]
    obj.VerticalCurveLengths = [30.0]
    obj.VerticalCurveParameters = [-0.05]
    try:
        obj.touch()
    except Exception:
        pass

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def find_v1_profile(document, preferred_profile=None):
    """Find a v1 profile object in a document, honoring an explicit preferred object."""

    if _is_v1_profile(preferred_profile):
        return preferred_profile
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_profile(obj):
            return obj
    return None


def to_profile_model(obj) -> ProfileModel | None:
    """Convert one v1 FreeCAD profile source object to a ProfileModel."""

    if not _is_v1_profile(obj):
        return None
    ensure_v1_profile_properties(obj)
    profile_id = str(getattr(obj, "ProfileId", "") or getattr(obj, "Name", "") or "profile:v1")
    control_ids = list(getattr(obj, "ControlPointIds", []) or [])
    control_stations = _float_list(getattr(obj, "ControlStations", []) or [])
    control_elevations = _float_list(getattr(obj, "ControlElevations", []) or [])
    control_kinds = list(getattr(obj, "ControlKinds", []) or [])
    control_count = min(len(control_stations), len(control_elevations))
    control_rows = [
        ProfileControlPoint(
            control_point_id=(
                str(control_ids[index])
                if index < len(control_ids) and control_ids[index]
                else f"{profile_id}:pvi:{index + 1}"
            ),
            station=float(control_stations[index]),
            elevation=float(control_elevations[index]),
            kind=str(control_kinds[index] if index < len(control_kinds) and control_kinds[index] else "pvi"),
        )
        for index in range(control_count)
    ]

    curve_ids = list(getattr(obj, "VerticalCurveIds", []) or [])
    curve_kinds = list(getattr(obj, "VerticalCurveKinds", []) or [])
    starts = _float_list(getattr(obj, "VerticalCurveStationStarts", []) or [])
    ends = _float_list(getattr(obj, "VerticalCurveStationEnds", []) or [])
    lengths = _float_list(getattr(obj, "VerticalCurveLengths", []) or [])
    parameters = _float_list(getattr(obj, "VerticalCurveParameters", []) or [])
    curve_count = min(len(starts), len(ends))
    vertical_curve_rows = [
        VerticalCurveRow(
            vertical_curve_id=(
                str(curve_ids[index])
                if index < len(curve_ids) and curve_ids[index]
                else f"{profile_id}:curve:{index + 1}"
            ),
            kind=str(
                curve_kinds[index]
                if index < len(curve_kinds) and curve_kinds[index]
                else "parabolic_vertical_curve"
            ),
            station_start=float(starts[index]),
            station_end=float(ends[index]),
            curve_length=(
                float(lengths[index])
                if index < len(lengths)
                else max(0.0, float(ends[index]) - float(starts[index]))
            ),
            curve_parameter=float(parameters[index]) if index < len(parameters) else 0.0,
        )
        for index in range(curve_count)
    ]

    return ProfileModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        profile_id=profile_id,
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        label=str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "v1 Profile"),
        profile_kind=str(getattr(obj, "ProfileKind", "") or "finished_grade"),
        source_refs=[str(getattr(obj, "Name", "") or profile_id)],
        control_rows=control_rows,
        vertical_curve_rows=vertical_curve_rows,
    )


def _is_v1_profile(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1Profile":
        return True
    proxy = getattr(obj, "Proxy", None)
    if str(getattr(proxy, "Type", "") or "") == "V1Profile":
        return True
    return str(getattr(obj, "Name", "") or "").startswith("V1Profile")


def _add_property(obj, type_name: str, name: str, group: str, doc: str) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty(type_name, name, group, doc)
    except Exception:
        pass


def _float_list(values) -> list[float]:
    rows = []
    for value in list(values or []):
        try:
            rows.append(float(value))
        except Exception:
            rows.append(0.0)
    return rows


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "Name", "") or getattr(project, "Label", "") or "corridorroad-v1")

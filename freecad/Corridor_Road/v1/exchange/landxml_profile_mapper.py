"""Map Civil 3D LandXML profile candidates into v1 profile objects."""

from __future__ import annotations

import re

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.profile_model import ProfileControlPoint, ProfileModel
from .landxml_import_contracts import LandXMLProfileCandidate


def profile_model_from_landxml_candidate(
    candidate: LandXMLProfileCandidate,
    *,
    project_id: str = "corridorroad-v1",
    alignment_id: str = "",
) -> ProfileModel:
    """Normalize one LandXML profile candidate into a ProfileModel."""

    profile_id = _profile_id(candidate)
    linked_alignment_id = str(alignment_id or _alignment_id_from_candidate(candidate) or "")
    control_rows = [
        ProfileControlPoint(
            control_point_id=f"{profile_id}:pvi:{index:03d}",
            station=float(point.station),
            elevation=float(point.elevation),
            kind=str(point.kind or "pvi"),
        )
        for index, point in enumerate(sorted(candidate.points, key=lambda row: float(row.station)), start=1)
    ]
    return ProfileModel(
        schema_version=1,
        project_id=str(project_id or "corridorroad-v1"),
        label=str(candidate.name or candidate.profile_id or "LandXML Profile"),
        profile_id=profile_id,
        alignment_id=linked_alignment_id,
        profile_kind="finished_grade",
        source_refs=[f"landxml:{candidate.profile_id or candidate.name}"],
        control_rows=control_rows,
        vertical_curve_rows=[],
    )


def create_or_update_profile_from_landxml_candidate(
    document,
    candidate: LandXMLProfileCandidate,
    *,
    project=None,
    alignment_id: str = "",
):
    """Create or update a FreeCAD v1 profile object from a LandXML candidate."""

    if document is None:
        if App is None:
            raise RuntimeError("FreeCAD is required to create a v1 profile object.")
        document = getattr(App, "ActiveDocument", None)
    if document is None:
        raise RuntimeError("No active document is available for LandXML profile import.")

    project_id = _project_id(project)
    model = profile_model_from_landxml_candidate(candidate, project_id=project_id, alignment_id=alignment_id)
    obj = _find_profile_object_by_id(document, model.profile_id)
    if obj is None:
        obj = _new_profile_object(document)
    _write_profile_model_to_object(obj, model)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    try:
        obj.touch()
    except Exception:
        pass
    try:
        document.recompute()
    except Exception:
        pass
    return obj


def _write_profile_model_to_object(obj, model: ProfileModel) -> None:
    from ..objects.obj_profile import V1ProfileObject, ViewProviderV1Profile, ensure_v1_profile_properties

    if getattr(obj, "Proxy", None) is None:
        V1ProfileObject(obj)
    else:
        ensure_v1_profile_properties(obj)
    try:
        ViewProviderV1Profile(obj.ViewObject)
    except Exception:
        pass
    obj.Label = model.label or "LandXML Profile"
    obj.ProjectId = model.project_id
    obj.ProfileId = model.profile_id
    obj.AlignmentId = model.alignment_id
    obj.ProfileKind = model.profile_kind or "finished_grade"
    obj.ControlPointIds = [row.control_point_id for row in model.control_rows]
    obj.ControlStations = [float(row.station) for row in model.control_rows]
    obj.ControlElevations = [float(row.elevation) for row in model.control_rows]
    obj.ControlKinds = [str(row.kind or "pvi") for row in model.control_rows]
    obj.VerticalCurveIds = [row.vertical_curve_id for row in model.vertical_curve_rows]
    obj.VerticalCurveKinds = [row.kind for row in model.vertical_curve_rows]
    obj.VerticalCurveStationStarts = [float(row.station_start) for row in model.vertical_curve_rows]
    obj.VerticalCurveStationEnds = [float(row.station_end) for row in model.vertical_curve_rows]
    obj.VerticalCurveLengths = [float(row.curve_length) for row in model.vertical_curve_rows]
    obj.VerticalCurveParameters = [float(row.curve_parameter) for row in model.vertical_curve_rows]
    obj.DisplayStatus = "pending"


def _new_profile_object(document):
    from ..objects.obj_profile import V1ProfileObject, ViewProviderV1Profile

    try:
        obj = document.addObject("Part::FeaturePython", "V1Profile")
    except Exception:
        obj = document.addObject("App::FeaturePython", "V1Profile")
    V1ProfileObject(obj)
    try:
        ViewProviderV1Profile(obj.ViewObject)
    except Exception:
        pass
    return obj


def _find_profile_object_by_id(document, profile_id: str):
    for obj in list(getattr(document, "Objects", []) or []):
        if str(getattr(obj, "ProfileId", "") or "") == profile_id:
            return obj
    return None


def _profile_id(candidate: LandXMLProfileCandidate) -> str:
    raw = candidate.profile_id or candidate.name or "landxml-profile"
    return f"profile:{_slug(raw)}"


def _alignment_id_from_candidate(candidate: LandXMLProfileCandidate) -> str:
    raw = str(candidate.alignment_id or "").strip()
    return f"alignment:{_slug(raw)}" if raw else ""


def _slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(text or "").strip()).strip("-")
    return slug or "landxml-profile"


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "Name", "") or getattr(project, "Label", "") or "corridorroad-v1")

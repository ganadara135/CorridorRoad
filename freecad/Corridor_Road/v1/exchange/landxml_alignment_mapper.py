"""Map Civil 3D LandXML alignment candidates into v1 alignment objects."""

from __future__ import annotations

import re

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.alignment_model import AlignmentElement, AlignmentModel
from .landxml_import_contracts import LandXMLAlignmentCandidate, LandXMLAlignmentElementCandidate
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


def alignment_model_from_landxml_candidate(
    candidate: LandXMLAlignmentCandidate,
    *,
    project_id: str = "corridorroad-v1",
) -> AlignmentModel:
    """Normalize one LandXML alignment candidate into an AlignmentModel."""

    alignment_id = _alignment_id(candidate)
    station = float(candidate.start_station or 0.0)
    elements: list[AlignmentElement] = []
    for index, element in enumerate(candidate.elements, start=1):
        kind = _v1_kind(element)
        length = float(element.length or 0.0)
        station_start = station
        station_end = station_start + max(0.0, length)
        station = station_end
        x_values, y_values = _xy_values(element)
        elements.append(
            AlignmentElement(
                element_id=f"{alignment_id}:element:{index:03d}",
                kind=kind,
                station_start=station_start,
                station_end=station_end,
                length=length,
                geometry_payload={
                    "x_values": x_values,
                    "y_values": y_values,
                    "source_kind": element.kind,
                    "source_payload": dict(element.payload or {}),
                    "style_role": kind,
                },
            )
        )
    return AlignmentModel(
        schema_version=1,
        project_id=str(project_id or "corridorroad-v1"),
        label=str(candidate.name or candidate.alignment_id or "LandXML Alignment"),
        alignment_id=alignment_id,
        alignment_kind="road_centerline",
        source_refs=[f"landxml:{candidate.alignment_id or candidate.name}"],
        geometry_sequence=elements,
    )


def create_or_update_alignment_from_landxml_candidate(
    document,
    candidate: LandXMLAlignmentCandidate,
    *,
    project=None,
):
    """Create or update a FreeCAD v1 alignment object from a LandXML candidate."""

    if document is None:
        if App is None:
            raise RuntimeError("FreeCAD is required to create a v1 alignment object.")
        document = getattr(App, "ActiveDocument", None)
    if document is None:
        raise RuntimeError("No active document is available for LandXML alignment import.")

    project_id = _project_id(project)
    model = alignment_model_from_landxml_candidate(candidate, project_id=project_id)
    obj = _find_alignment_object_by_id(document, model.alignment_id)
    if obj is None:
        obj = _new_alignment_object(document)
    _write_alignment_model_to_object(obj, model)

    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
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


def _write_alignment_model_to_object(obj, model: AlignmentModel) -> None:
    from ..objects.obj_alignment import V1AlignmentObject, ViewProviderV1Alignment, ensure_v1_alignment_properties

    if getattr(obj, "Proxy", None) is None:
        V1AlignmentObject(obj)
    else:
        ensure_v1_alignment_properties(obj)
    try:
        ViewProviderV1Alignment(obj.ViewObject)
    except Exception:
        pass
    obj.Label = model.label or "LandXML Alignment"
    obj.ProjectId = model.project_id
    obj.AlignmentId = model.alignment_id
    obj.AlignmentKind = model.alignment_kind or "road_centerline"
    obj.ElementIds = [row.element_id for row in model.geometry_sequence]
    obj.ElementKinds = [row.kind for row in model.geometry_sequence]
    obj.StationStarts = [float(row.station_start) for row in model.geometry_sequence]
    obj.StationEnds = [float(row.station_end) for row in model.geometry_sequence]
    obj.ElementLengths = [float(row.length) for row in model.geometry_sequence]
    obj.XValueRows = [_csv(row.geometry_payload.get("x_values", [])) for row in model.geometry_sequence]
    obj.YValueRows = [_csv(row.geometry_payload.get("y_values", [])) for row in model.geometry_sequence]
    points = _model_points(model)
    if App is not None:
        obj.IPPoints = [App.Vector(float(x), float(y), 0.0) for x, y in points]
    obj.TotalLength = sum(float(row.length or 0.0) for row in model.geometry_sequence)
    obj.CriteriaMessages = []
    obj.CriteriaStatus = "OK"
    obj.CompiledGeometryStatus = "pending"


def _new_alignment_object(document):
    from ..objects.obj_alignment import V1AlignmentObject, ViewProviderV1Alignment

    try:
        obj = document.addObject("Part::FeaturePython", "V1Alignment")
    except Exception:
        obj = document.addObject("App::FeaturePython", "V1Alignment")
    V1AlignmentObject(obj)
    try:
        ViewProviderV1Alignment(obj.ViewObject)
    except Exception:
        pass
    return obj


def _find_alignment_object_by_id(document, alignment_id: str):
    for obj in list(getattr(document, "Objects", []) or []):
        if str(getattr(obj, "AlignmentId", "") or "") == alignment_id:
            return obj
    return None


def _alignment_id(candidate: LandXMLAlignmentCandidate) -> str:
    raw = candidate.alignment_id or candidate.name or "landxml-alignment"
    return f"alignment:{_slug(raw)}"


def _slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(text or "").strip()).strip("-")
    return slug or "landxml-alignment"


def _v1_kind(element: LandXMLAlignmentElementCandidate) -> str:
    kind = str(element.kind or "").lower()
    if kind == "line":
        return "tangent"
    if kind == "curve":
        return "circular_curve"
    if kind == "spiral":
        return "transition_curve"
    return "sampled_curve"


def _xy_values(element: LandXMLAlignmentElementCandidate) -> tuple[list[float], list[float]]:
    start = _point(element.payload.get("start"))
    end = _point(element.payload.get("end"))
    if start and end:
        return [start[0], end[0]], [start[1], end[1]]
    return [], []


def _point(value) -> tuple[float, float] | None:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return float(value[0]), float(value[1])
        except Exception:
            return None
    return None


def _csv(values) -> str:
    return ",".join(f"{float(value):.12g}" for value in list(values or []))


def _model_points(model: AlignmentModel) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for row in list(model.geometry_sequence or []):
        x_values = list(row.geometry_payload.get("x_values", []) or [])
        y_values = list(row.geometry_payload.get("y_values", []) or [])
        for x, y in zip(x_values, y_values):
            point = (float(x), float(y))
            if points and abs(points[-1][0] - point[0]) <= 1.0e-9 and abs(points[-1][1] - point[1]) <= 1.0e-9:
                continue
            points.append(point)
    return points


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "Name", "") or getattr(project, "Label", "") or "corridorroad-v1")
